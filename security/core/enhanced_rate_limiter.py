# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Rate Limiting for User Management Operations

Provides comprehensive rate limiting with different strategies for various user management operations.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from functools import wraps
from flask import request, abort, g
from sqlalchemy.orm import Session
from models import UserAuditLog
from security.monitoring.security_event_logger import get_security_event_logger, SecurityEventType

logger = logging.getLogger(__name__)


class RateLimitStrategy:
    """Base class for rate limiting strategies"""
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
    
    def is_allowed(self, key: str, storage: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed and return updated storage"""
        raise NotImplementedError


class SlidingWindowRateLimit(RateLimitStrategy):
    """Sliding window rate limiting strategy"""
    
    def is_allowed(self, key: str, storage: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Get or create request history for this key
        if key not in storage:
            storage[key] = []
        
        # Remove old requests outside the window
        storage[key] = [req_time for req_time in storage[key] if req_time > window_start]
        
        # Check if we're within the limit
        if len(storage[key]) >= self.limit:
            return False, storage
        
        # Add current request
        storage[key].append(current_time)
        return True, storage


class TokenBucketRateLimit(RateLimitStrategy):
    """Token bucket rate limiting strategy"""
    
    def __init__(self, limit: int, window_seconds: int, refill_rate: Optional[float] = None):
        super().__init__(limit, window_seconds)
        self.refill_rate = refill_rate or (limit / window_seconds)
    
    def is_allowed(self, key: str, storage: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        current_time = time.time()
        
        # Get or create bucket for this key
        if key not in storage:
            storage[key] = {
                'tokens': self.limit,
                'last_refill': current_time
            }
        
        bucket = storage[key]
        
        # Refill tokens based on time elapsed
        time_elapsed = current_time - bucket['last_refill']
        tokens_to_add = time_elapsed * self.refill_rate
        bucket['tokens'] = min(self.limit, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = current_time
        
        # Check if we have tokens available
        if bucket['tokens'] < 1:
            return False, storage
        
        # Consume a token
        bucket['tokens'] -= 1
        return True, storage


class AdaptiveRateLimit(RateLimitStrategy):
    """Adaptive rate limiting that adjusts based on user behavior"""
    
    def __init__(self, base_limit: int, window_seconds: int, penalty_multiplier: float = 0.5):
        super().__init__(base_limit, window_seconds)
        self.penalty_multiplier = penalty_multiplier
    
    def is_allowed(self, key: str, storage: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Get or create data for this key
        if key not in storage:
            storage[key] = {
                'requests': [],
                'violations': 0,
                'last_violation': 0
            }
        
        data = storage[key]
        
        # Remove old requests
        data['requests'] = [req_time for req_time in data['requests'] if req_time > window_start]
        
        # Calculate current limit based on violations
        current_limit = self.limit
        if data['violations'] > 0:
            # Reduce limit based on past violations
            penalty_factor = self.penalty_multiplier ** data['violations']
            current_limit = max(1, int(self.limit * penalty_factor))
        
        # Check if we're within the current limit
        if len(data['requests']) >= current_limit:
            # Record violation
            data['violations'] += 1
            data['last_violation'] = current_time
            return False, storage
        
        # Add current request
        data['requests'].append(current_time)
        
        # Reduce violations over time (forgiveness)
        if data['violations'] > 0 and current_time - data['last_violation'] > self.window_seconds * 2:
            data['violations'] = max(0, data['violations'] - 1)
        
        return True, storage


class EnhancedRateLimiter:
    """Enhanced rate limiter with multiple strategies and user management focus"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.storage: Dict[str, Dict[str, Any]] = {}
        self.security_logger = get_security_event_logger(db_session)
        
        # Define rate limiting rules for different operations
        self.rules = {
            # Authentication operations
            'login': SlidingWindowRateLimit(5, 300),  # 5 attempts per 5 minutes per IP
            'login_user': SlidingWindowRateLimit(10, 3600),  # 10 attempts per hour per user
            'registration': SlidingWindowRateLimit(3, 3600),  # 3 registrations per hour per IP
            'password_reset': SlidingWindowRateLimit(3, 3600),  # 3 resets per hour per IP
            'password_reset_user': SlidingWindowRateLimit(5, 86400),  # 5 resets per day per user
            
            # Email operations
            'email_verification': SlidingWindowRateLimit(10, 3600),  # 10 verifications per hour per IP
            'resend_verification': TokenBucketRateLimit(3, 300),  # 3 resends per 5 minutes, refill gradually
            
            # Profile operations
            'profile_update': SlidingWindowRateLimit(10, 3600),  # 10 updates per hour per user
            'profile_delete': SlidingWindowRateLimit(1, 86400),  # 1 deletion attempt per day per user
            'data_export': SlidingWindowRateLimit(5, 3600),  # 5 exports per hour per user
            
            # Admin operations
            'admin_user_create': SlidingWindowRateLimit(20, 3600),  # 20 user creations per hour per admin
            'admin_user_update': SlidingWindowRateLimit(50, 3600),  # 50 user updates per hour per admin
            'admin_password_reset': SlidingWindowRateLimit(30, 3600),  # 30 password resets per hour per admin
            
            # Security-sensitive operations
            'csrf_failure': AdaptiveRateLimit(5, 300),  # Adaptive limiting for CSRF failures
            'input_validation_failure': AdaptiveRateLimit(10, 300),  # Adaptive limiting for validation failures
            
            # General API operations
            'api_general': TokenBucketRateLimit(100, 60, 2.0),  # 100 requests per minute, refill at 2/second
        }
    
    def check_rate_limit(
        self,
        operation: str,
        identifier: Optional[str] = None,
        user_id: Optional[int] = None,
        fallback_to_ip: bool = True
    ) -> bool:
        """
        Check if an operation is within rate limits
        
        Args:
            operation: The operation being performed
            identifier: Custom identifier (if not provided, uses IP or user_id)
            user_id: User ID for user-specific limits
            fallback_to_ip: Whether to fall back to IP-based limiting if no user_id
            
        Returns:
            True if allowed, False if rate limited
        """
        try:
            # Determine the rate limiting rule
            rule = self.rules.get(operation)
            if not rule:
                # Default to general API rate limiting
                rule = self.rules['api_general']
            
            # Determine the key for rate limiting
            key = self._get_rate_limit_key(operation, identifier, user_id, fallback_to_ip)
            if not key:
                # If we can't determine a key, allow the request
                return True
            
            # Check the rate limit
            allowed, self.storage = rule.is_allowed(key, self.storage)
            
            if not allowed:
                # Log rate limit exceeded
                self.security_logger.log_rate_limit_exceeded(
                    endpoint=operation,
                    limit_type=type(rule).__name__,
                    user_id=user_id
                )
                
                # Log to audit trail
                self._log_rate_limit_violation(operation, key, user_id)
            
            return allowed
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {operation}: {e}")
            # On error, allow the request to avoid blocking legitimate users
            return True
    
    def get_rate_limit_info(self, operation: str, identifier: str) -> Dict[str, Any]:
        """Get current rate limit status for an operation and identifier"""
        try:
            rule = self.rules.get(operation, self.rules['api_general'])
            key = f"{operation}:{identifier}"
            
            if key not in self.storage:
                return {
                    'limit': rule.limit,
                    'remaining': rule.limit,
                    'reset_time': int(time.time() + rule.window_seconds)
                }
            
            if isinstance(rule, SlidingWindowRateLimit):
                current_time = time.time()
                window_start = current_time - rule.window_seconds
                requests = self.storage[key]
                active_requests = [req for req in requests if req > window_start]
                
                return {
                    'limit': rule.limit,
                    'remaining': max(0, rule.limit - len(active_requests)),
                    'reset_time': int(min(active_requests) + rule.window_seconds) if active_requests else int(current_time)
                }
            
            elif isinstance(rule, TokenBucketRateLimit):
                bucket = self.storage[key]
                return {
                    'limit': rule.limit,
                    'remaining': int(bucket['tokens']),
                    'reset_time': int(time.time() + (rule.limit - bucket['tokens']) / rule.refill_rate)
                }
            
            return {'limit': rule.limit, 'remaining': 0, 'reset_time': int(time.time() + rule.window_seconds)}
            
        except Exception as e:
            logger.error(f"Error getting rate limit info: {e}")
            return {'limit': 100, 'remaining': 100, 'reset_time': int(time.time() + 3600)}
    
    def reset_rate_limit(self, operation: str, identifier: str) -> bool:
        """Reset rate limit for a specific operation and identifier (admin function)"""
        try:
            key = f"{operation}:{identifier}"
            if key in self.storage:
                del self.storage[key]
                return True
            return False
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
            return False
    
    def cleanup_expired_entries(self) -> None:
        """Clean up expired rate limit entries"""
        try:
            current_time = time.time()
            keys_to_remove = []
            
            for key, data in self.storage.items():
                operation = key.split(':', 1)[0]
                rule = self.rules.get(operation, self.rules['api_general'])
                
                if isinstance(data, list):
                    # Sliding window data
                    window_start = current_time - rule.window_seconds
                    active_requests = [req for req in data if req > window_start]
                    if not active_requests:
                        keys_to_remove.append(key)
                    else:
                        self.storage[key] = active_requests
                
                elif isinstance(data, dict) and 'last_refill' in data:
                    # Token bucket data - keep recent buckets
                    if current_time - data['last_refill'] > rule.window_seconds * 2:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.storage[key]
                
        except Exception as e:
            logger.error(f"Error cleaning up rate limit entries: {e}")
    
    def _get_rate_limit_key(
        self,
        operation: str,
        identifier: Optional[str],
        user_id: Optional[int],
        fallback_to_ip: bool
    ) -> Optional[str]:
        """Generate a rate limiting key"""
        if identifier:
            return f"{operation}:{identifier}"
        
        # For user-specific operations, prefer user_id
        if user_id and operation.endswith('_user') or operation in ['profile_update', 'profile_delete', 'data_export']:
            return f"{operation}:user_{user_id}"
        
        # For IP-based operations or fallback
        if fallback_to_ip and request:
            ip_address = self._get_client_ip()
            return f"{operation}:ip_{ip_address}"
        
        return None
    
    def _get_client_ip(self) -> str:
        """Get the real client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or 'unknown'
    
    def _log_rate_limit_violation(self, operation: str, key: str, user_id: Optional[int]) -> None:
        """Log rate limit violation to audit trail"""
        try:
            UserAuditLog.log_action(
                session=self.db_session,
                action=f"rate_limit_exceeded_{operation}",
                user_id=user_id,
                details=f"Rate limit exceeded for key: {key}",
                ip_address=self._get_client_ip() if request else None,
                user_agent=request.headers.get('User-Agent') if request else None
            )
        except Exception as e:
            logger.error(f"Error logging rate limit violation: {e}")


def rate_limit_user_management(
    operation: str,
    identifier: Optional[str] = None,
    user_id: Optional[int] = None,
    fallback_to_ip: bool = True
):
    """
    Decorator for rate limiting user management operations
    
    Args:
        operation: The operation being rate limited
        identifier: Custom identifier for rate limiting
        user_id: User ID for user-specific limits
        fallback_to_ip: Whether to fall back to IP-based limiting
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get database session
            from database import get_db_session
            db_session = get_db_session()
            
            try:
                rate_limiter = EnhancedRateLimiter(db_session)
                
                # Determine user_id if not provided
                actual_user_id = user_id
                if not actual_user_id and hasattr(g, 'current_user') and g.current_user:
                    actual_user_id = g.current_user.id
                
                # Check rate limit
                if not rate_limiter.check_rate_limit(operation, identifier, actual_user_id, fallback_to_ip):
                    logger.warning(f"Rate limit exceeded for operation {operation}")
                    abort(429, description="Rate limit exceeded. Please try again later.")
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in rate limiting decorator: {e}")
                # On error, allow the request to proceed
                return f(*args, **kwargs)
            finally:
                db_session.close()
        
        return decorated_function
    return decorator


# Convenience decorators for common operations
def rate_limit_login(f):
    """Rate limit login attempts"""
    return rate_limit_user_management('login')(f)


def rate_limit_registration(f):
    """Rate limit registration attempts"""
    return rate_limit_user_management('registration')(f)


def rate_limit_password_reset(f):
    """Rate limit password reset requests"""
    return rate_limit_user_management('password_reset')(f)


def rate_limit_profile_operations(f):
    """Rate limit profile operations"""
    return rate_limit_user_management('profile_update')(f)


def rate_limit_admin_operations(operation: str):
    """Rate limit admin operations"""
    def decorator(f):
        return rate_limit_user_management(f"admin_{operation}")(f)
    return decorator