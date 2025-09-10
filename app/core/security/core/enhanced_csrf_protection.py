# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced CSRF Protection for User Management

Provides comprehensive CSRF protection with additional security measures for user management operations.
"""

import hmac
import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, g, abort, current_app
# REMOVED: Flask session import - using Redis sessions only
# DISABLED: Flask-WTF CSRF imports - using custom Redis-aware CSRF system
# from flask_wtf.csrf import CSRFProtect, ValidationError

# Define ValidationError locally since we're not using Flask-WTF
class ValidationError(Exception):
    """CSRF validation error"""
    pass
from sqlalchemy.orm import Session
from app.core.security.monitoring.security_event_logger import get_security_event_logger, SecurityEventType

logger = logging.getLogger(__name__)

class EnhancedCSRFProtection:
    """Enhanced CSRF protection with additional security measures"""
    
    def __init__(self, app=None, db_session: Optional[Session] = None):
        self.app = app
        self.db_session = db_session
        # DISABLED: Flask-WTF CSRF - using custom Redis-aware CSRF system
        # self.csrf = CSRFProtect()
        self.csrf = None  # Disabled Flask-WTF CSRF
        self.security_logger = None
        
        # CSRF token storage (in production, use Redis or database)
        self.token_storage: Dict[str, Dict[str, Any]] = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize enhanced CSRF protection with Flask app"""
        self.app = app
        self.csrf.init_app(app)
        
        # Configure CSRF settings
        app.config.setdefault('WTF_CSRF_TIME_LIMIT', 3600)  # 1 hour
        app.config.setdefault('WTF_CSRF_SSL_STRICT', True)
        app.config.setdefault('WTF_CSRF_CHECK_DEFAULT', True)
        
        # Set up custom CSRF error handler
        @app.errorhandler(400)
        def csrf_error(e):
            if isinstance(e.description, ValidationError):
                return self._handle_csrf_error(e.description)
            return e
    
    def generate_csrf_token(self, user_id: Optional[int] = None, operation: Optional[str] = None) -> str:
        """
        Generate a CSRF token with additional context
        
        Args:
            user_id: User ID for user-specific tokens
            operation: Specific operation this token is for
            
        Returns:
            CSRF token string
        """
        try:
            # Generate base token
            base_token = secrets.token_urlsafe(32)
            timestamp = int(time.time())
            
            # Create token data
            token_data = {
                'token': base_token,
                'timestamp': timestamp,
                'user_id': user_id,
                'operation': operation,
                'ip_address': request.remote_addr if request else None,
                'user_agent_hash': self._hash_user_agent() if request else None
            }
            
            # Create signed token
            signed_token = self._sign_token_data(token_data)
            
            # Store token data
            self.token_storage[signed_token] = token_data
            
            # Clean up old tokens
            self._cleanup_expired_tokens()
            
            return signed_token
            
        except Exception as e:
            logger.error(f"Error generating CSRF token: {e}")
            # Fall back to standard CSRF token generation
            return secrets.token_urlsafe(32)
    
    def validate_csrf_token(
        self,
        token: str,
        user_id: Optional[int] = None,
        operation: Optional[str] = None,
        strict_validation: bool = True
    ) -> bool:
        """
        Validate a CSRF token with additional context checks
        
        Args:
            token: CSRF token to validate
            user_id: Expected user ID
            operation: Expected operation
            strict_validation: Whether to perform strict validation
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Check if token exists in storage
            if token not in self.token_storage:
                self._log_csrf_failure("token_not_found", user_id, operation)
                return False
            
            token_data = self.token_storage[token]
            
            # Check token expiration
            token_age = time.time() - token_data['timestamp']
            max_age = current_app.config.get('WTF_CSRF_TIME_LIMIT', 3600)
            
            if token_age > max_age:
                self._log_csrf_failure("token_expired", user_id, operation)
                del self.token_storage[token]
                return False
            
            # Verify token signature
            if not self._verify_token_signature(token, token_data):
                self._log_csrf_failure("invalid_signature", user_id, operation)
                return False
            
            if strict_validation:
                # Check user ID match
                if user_id and token_data['user_id'] != user_id:
                    self._log_csrf_failure("user_id_mismatch", user_id, operation)
                    return False
                
                # Check operation match
                if operation and token_data['operation'] and token_data['operation'] != operation:
                    self._log_csrf_failure("operation_mismatch", user_id, operation)
                    return False
                
                # Check IP address consistency
                if request and token_data['ip_address'] != request.remote_addr:
                    self._log_csrf_failure("ip_address_mismatch", user_id, operation)
                    return False
                
                # Check user agent consistency
                if request and token_data['user_agent_hash'] != self._hash_user_agent():
                    self._log_csrf_failure("user_agent_mismatch", user_id, operation)
                    return False
            
            # Token is valid - remove it (one-time use)
            del self.token_storage[token]
            return True
            
        except Exception as e:
            logger.error(f"Error validating CSRF token: {e}")
            self._log_csrf_failure("validation_error", user_id, operation)
            return False
    
    def get_csrf_token_for_form(self, operation: Optional[str] = None) -> str:
        """Get CSRF token for use in forms"""
        user_id = None
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user.id
        
        return self.generate_csrf_token(user_id=user_id, operation=operation)
    
    def _sign_token_data(self, token_data: Dict[str, Any]) -> str:
        """Create a signed token from token data"""
        # Create a string representation of the token data
        data_string = f"{token_data['token']}:{token_data['timestamp']}:{token_data.get('user_id', '')}:{token_data.get('operation', '')}"
        
        # Sign with app secret key
        secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
        signature = hmac.new(
            secret_key.encode(),
            data_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{token_data['token']}.{signature}"
    
    def _verify_token_signature(self, signed_token: str, token_data: Dict[str, Any]) -> bool:
        """Verify the signature of a token"""
        try:
            token_part, signature = signed_token.rsplit('.', 1)
            
            # Recreate the expected signature
            data_string = f"{token_data['token']}:{token_data['timestamp']}:{token_data.get('user_id', '')}:{token_data.get('operation', '')}"
            secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
            expected_signature = hmac.new(
                secret_key.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def _hash_user_agent(self) -> str:
        """Create a hash of the user agent for consistency checking"""
        user_agent = request.headers.get('User-Agent', '')
        return hashlib.sha256(user_agent.encode()).hexdigest()[:16]
    
    def _cleanup_expired_tokens(self) -> None:
        """Clean up expired tokens from storage"""
        try:
            current_time = time.time()
            max_age = current_app.config.get('WTF_CSRF_TIME_LIMIT', 3600)
            
            expired_tokens = [
                token for token, data in self.token_storage.items()
                if current_time - data['timestamp'] > max_age
            ]
            
            for token in expired_tokens:
                del self.token_storage[token]
                
        except Exception as e:
            logger.error(f"Error cleaning up expired CSRF tokens: {e}")
    
    def _log_csrf_failure(self, failure_type: str, user_id: Optional[int], operation: Optional[str]) -> None:
        """Log CSRF validation failures"""
        try:
            if self.security_logger:
                self.security_logger.log_csrf_failure(
                    endpoint=operation or request.endpoint if request else 'unknown',
                    user_id=user_id
                )
            
            # Log additional details
            logger.warning(f"CSRF validation failed: {failure_type}, user_id={user_id}, operation={operation}")
            
        except Exception as e:
            logger.error(f"Error logging CSRF failure: {e}")
    
    def _handle_csrf_error(self, error: ValidationError) -> tuple:
        """Handle CSRF validation errors"""
        user_id = None
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user.id
        
        self._log_csrf_failure("csrf_validation_error", user_id, request.endpoint if request else None)
        
        return {
            'error': 'CSRF token validation failed',
            'message': 'Your session has expired or the request is invalid. Please refresh the page and try again.'
        }, 403

def enhanced_csrf_protect(
    operation: Optional[str] = None,
    strict_validation: bool = True,
    require_user: bool = False
):
    """
    Enhanced CSRF protection decorator
    
    Args:
        operation: Specific operation this protection is for
        strict_validation: Whether to perform strict validation
        require_user: Whether to require an authenticated user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                try:
                    # Get database session
                    from database import get_db_session
                    db_session = get_db_session()
                    
                    csrf_protection = EnhancedCSRFProtection(db_session=db_session)
                    csrf_protection.security_logger = get_security_event_logger(db_session)
                    
                    # Get CSRF token from request
                    csrf_token = (
                        request.form.get('csrf_token') or
                        request.headers.get('X-CSRFToken') or
                        request.headers.get('X-CSRF-Token')
                    )
                    
                    if not csrf_token:
                        csrf_protection._log_csrf_failure("missing_token", None, operation)
                        abort(403, description="CSRF token is missing")
                    
                    # Get user ID if available
                    user_id = None
                    if hasattr(g, 'current_user') and g.current_user:
                        user_id = g.current_user.id
                    elif require_user:
                        abort(401, description="Authentication required")
                    
                    # Validate CSRF token
                    if not csrf_protection.validate_csrf_token(
                        csrf_token, user_id, operation, strict_validation
                    ):
                        abort(403, description="CSRF token validation failed")
                    
                    db_session.close()
                        
                except Exception as e:
                    logger.error(f"Error in enhanced CSRF protection: {e}")
                    # DISABLED: Flask-WTF fallback - using custom Redis-aware system only
                    # from flask_wtf.csrf import validate_csrf
                    logger.warning("Enhanced CSRF protection disabled - using custom Redis-aware system")
                    # No fallback to Flask-WTF CSRF
                    abort(403, description="CSRF token validation failed")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def csrf_protect_user_management(operation: str):
    """CSRF protection specifically for user management operations"""
    return enhanced_csrf_protect(operation=operation, strict_validation=True, require_user=True)

def csrf_protect_admin_operation(operation: str):
    """CSRF protection for admin operations"""
    def decorator(f):
        @enhanced_csrf_protect(operation=f"admin_{operation}", strict_validation=True, require_user=True)
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Additional admin role check
            if not hasattr(g, 'current_user') or not g.current_user or g.current_user.role.value != 'admin':
                abort(403, description="Admin access required")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def csrf_protect_sensitive_operation(operation: str):
    """CSRF protection for sensitive operations with maximum security"""
    return enhanced_csrf_protect(operation=operation, strict_validation=True, require_user=True)

# Template helper function
def generate_csrf_token_for_template(operation: Optional[str] = None) -> str:
    """Generate CSRF token for use in templates"""
    try:
        from database import get_db_session
        db_session = get_db_session()
        
        csrf_protection = EnhancedCSRFProtection(db_session=db_session)
        token = csrf_protection.get_csrf_token_for_form(operation)
        
        db_session.close()
        return token
        
    except Exception as e:
        logger.error(f"Error generating CSRF token for template: {e}")
        # Fall back to generating a simple token
        return secrets.token_urlsafe(32)