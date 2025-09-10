# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Error Recovery Manager for Caption Generation

Implements comprehensive error handling and recovery strategies for caption generation operations.
"""

import logging
import time
import asyncio
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Categories of errors for different handling strategies"""
    AUTHENTICATION = "authentication"
    PLATFORM = "platform"
    RESOURCE = "resource"
    VALIDATION = "validation"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"

class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"
    FAIL_FAST = "fail_fast"
    FALLBACK = "fallback"
    NOTIFY_ADMIN = "notify_admin"
    IGNORE = "ignore"

@dataclass
class ErrorInfo:
    """Information about an error occurrence"""
    category: ErrorCategory
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    recoverable: bool = True

@dataclass
class RecoveryConfig:
    """Configuration for error recovery"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    strategy: RecoveryStrategy = RecoveryStrategy.RETRY

class ErrorRecoveryManager:
    """Manages error handling and recovery for caption generation operations"""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_configs = self._initialize_recovery_configs()
        self.error_history: List[ErrorInfo] = []
        self.admin_notifications: List[Dict[str, Any]] = []
    
    def _initialize_error_patterns(self) -> Dict[str, ErrorCategory]:
        """Initialize error pattern matching for categorization"""
        return {
            # Authentication errors
            'unauthorized': ErrorCategory.AUTHENTICATION,
            'authentication failed': ErrorCategory.AUTHENTICATION,
            'invalid token': ErrorCategory.AUTHENTICATION,
            'token expired': ErrorCategory.AUTHENTICATION,
            'access denied': ErrorCategory.AUTHENTICATION,
            
            # Platform errors
            'platform connection': ErrorCategory.PLATFORM,
            'api rate limit': ErrorCategory.PLATFORM,
            'service unavailable': ErrorCategory.PLATFORM,
            'platform not found': ErrorCategory.PLATFORM,
            'instance not accessible': ErrorCategory.PLATFORM,
            
            # Resource errors
            'out of memory': ErrorCategory.RESOURCE,
            'disk space': ErrorCategory.RESOURCE,
            'resource exhausted': ErrorCategory.RESOURCE,
            'timeout': ErrorCategory.RESOURCE,
            'ollama not available': ErrorCategory.RESOURCE,
            
            # Validation errors
            'validation error': ErrorCategory.VALIDATION,
            'invalid input': ErrorCategory.VALIDATION,
            'malformed data': ErrorCategory.VALIDATION,
            'schema validation': ErrorCategory.VALIDATION,
            
            # Network errors
            'connection refused': ErrorCategory.NETWORK,
            'network unreachable': ErrorCategory.NETWORK,
            'dns resolution': ErrorCategory.NETWORK,
            'connection timeout': ErrorCategory.NETWORK,
            'ssl error': ErrorCategory.NETWORK,
            
            # System errors
            'database error': ErrorCategory.SYSTEM,
            'file system error': ErrorCategory.SYSTEM,
            'permission denied': ErrorCategory.SYSTEM,
            'system overload': ErrorCategory.SYSTEM,
        }
    
    def _initialize_recovery_configs(self) -> Dict[ErrorCategory, RecoveryConfig]:
        """Initialize recovery configurations for each error category"""
        return {
            ErrorCategory.AUTHENTICATION: RecoveryConfig(
                max_retries=1,
                strategy=RecoveryStrategy.FAIL_FAST
            ),
            ErrorCategory.PLATFORM: RecoveryConfig(
                max_retries=3,
                base_delay=2.0,
                max_delay=30.0,
                strategy=RecoveryStrategy.RETRY
            ),
            ErrorCategory.RESOURCE: RecoveryConfig(
                max_retries=5,
                base_delay=5.0,
                max_delay=120.0,
                backoff_multiplier=1.5,
                strategy=RecoveryStrategy.RETRY
            ),
            ErrorCategory.VALIDATION: RecoveryConfig(
                max_retries=0,
                strategy=RecoveryStrategy.FAIL_FAST
            ),
            ErrorCategory.NETWORK: RecoveryConfig(
                max_retries=4,
                base_delay=1.0,
                max_delay=60.0,
                strategy=RecoveryStrategy.RETRY
            ),
            ErrorCategory.SYSTEM: RecoveryConfig(
                max_retries=2,
                base_delay=10.0,
                strategy=RecoveryStrategy.NOTIFY_ADMIN
            ),
            ErrorCategory.UNKNOWN: RecoveryConfig(
                max_retries=1,
                strategy=RecoveryStrategy.NOTIFY_ADMIN
            )
        }
    
    def categorize_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorCategory:
        """Categorize an error based on its message and context"""
        error_message = str(error).lower()
        
        # Check for specific error patterns
        for pattern, category in self.error_patterns.items():
            if pattern in error_message:
                return category
        
        # Check error type
        error_type = type(error).__name__.lower()
        if 'auth' in error_type or 'permission' in error_type:
            return ErrorCategory.AUTHENTICATION
        elif 'connection' in error_type or 'network' in error_type:
            return ErrorCategory.NETWORK
        elif 'validation' in error_type or 'value' in error_type:
            return ErrorCategory.VALIDATION
        elif 'resource' in error_type or 'memory' in error_type:
            return ErrorCategory.RESOURCE
        
        return ErrorCategory.UNKNOWN
    
    def create_error_info(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """Create ErrorInfo object from exception"""
        category = self.categorize_error(error, context)
        
        return ErrorInfo(
            category=category,
            message=str(error),
            details={
                'error_type': type(error).__name__,
                'context': context or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            },
            timestamp=datetime.now(timezone.utc),
            recoverable=self._is_recoverable(category, error)
        )
    
    def _is_recoverable(self, category: ErrorCategory, error: Exception) -> bool:
        """Determine if an error is recoverable"""
        non_recoverable_categories = {
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.VALIDATION
        }
        
        if category in non_recoverable_categories:
            return False
        
        # Check for specific non-recoverable errors
        error_message = str(error).lower()
        non_recoverable_patterns = [
            'permission denied',
            'access forbidden',
            'invalid credentials',
            'malformed request'
        ]
        
        for pattern in non_recoverable_patterns:
            if pattern in error_message:
                return False
        
        return True
    
    async def handle_error(
        self,
        error: Exception,
        operation: Callable,
        context: Dict[str, Any] = None,
        *args,
        **kwargs
    ) -> Any:
        """Handle an error with appropriate recovery strategy"""
        error_info = self.create_error_info(error, context)
        self.error_history.append(error_info)
        
        logger.error(f"Error in caption generation: {sanitize_for_log(str(error))}")
        
        # Get recovery configuration
        config = self.recovery_configs.get(error_info.category, self.recovery_configs[ErrorCategory.UNKNOWN])
        
        # Execute recovery strategy
        if config.strategy == RecoveryStrategy.FAIL_FAST:
            return await self._fail_fast(error_info)
        elif config.strategy == RecoveryStrategy.RETRY:
            return await self._retry_with_backoff(error_info, operation, config, *args, **kwargs)
        elif config.strategy == RecoveryStrategy.NOTIFY_ADMIN:
            return await self._notify_admin_and_fail(error_info)
        elif config.strategy == RecoveryStrategy.FALLBACK:
            return await self._fallback_strategy(error_info, operation, *args, **kwargs)
        else:
            return await self._fail_fast(error_info)
    
    async def _fail_fast(self, error_info: ErrorInfo) -> None:
        """Fail fast strategy - immediately raise the error"""
        logger.error(f"Failing fast for {error_info.category.value} error: {sanitize_for_log(error_info.message)}")
        raise Exception(self._get_user_friendly_message(error_info))
    
    async def _retry_with_backoff(
        self,
        error_info: ErrorInfo,
        operation: Callable,
        config: RecoveryConfig,
        *args,
        **kwargs
    ) -> Any:
        """Retry operation with exponential backoff"""
        if error_info.retry_count >= config.max_retries:
            logger.error(f"Max retries exceeded for {error_info.category.value} error")
            raise Exception(self._get_user_friendly_message(error_info))
        
        # Calculate delay with exponential backoff
        delay = min(
            config.base_delay * (config.backoff_multiplier ** error_info.retry_count),
            config.max_delay
        )
        
        logger.info(f"Retrying operation after {delay}s (attempt {error_info.retry_count + 1}/{config.max_retries})")
        
        await asyncio.sleep(delay)
        error_info.retry_count += 1
        
        try:
            return await operation(*args, **kwargs)
        except Exception as retry_error:
            return await self.handle_error(retry_error, operation, error_info.details.get('context'), *args, **kwargs)
    
    async def _notify_admin_and_fail(self, error_info: ErrorInfo) -> None:
        """Notify admin and fail the operation"""
        notification = {
            'type': 'system_error',
            'category': error_info.category.value,
            'message': error_info.message,
            'details': error_info.details,
            'timestamp': error_info.timestamp.isoformat(),
            'requires_attention': True
        }
        
        self.admin_notifications.append(notification)
        logger.critical(f"Admin notification: {error_info.category.value} error requires attention")
        
        raise Exception(self._get_user_friendly_message(error_info))
    
    async def _fallback_strategy(self, error_info: ErrorInfo, operation: Callable, *args, **kwargs) -> Any:
        """Implement fallback strategy (placeholder for future implementation)"""
        logger.warning(f"Fallback strategy not implemented for {error_info.category.value}")
        return await self._fail_fast(error_info)
    
    def _get_user_friendly_message(self, error_info: ErrorInfo) -> str:
        """Generate user-friendly error message"""
        category_messages = {
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials and try again.",
            ErrorCategory.PLATFORM: "Platform connection issue. The service may be temporarily unavailable.",
            ErrorCategory.RESOURCE: "System resources are currently unavailable. Please try again later.",
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your settings and try again.",
            ErrorCategory.NETWORK: "Network connection issue. Please check your internet connection.",
            ErrorCategory.SYSTEM: "System error occurred. The administrators have been notified.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again or contact support."
        }
        
        return category_messages.get(error_info.category, "An error occurred during caption generation.")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        if not self.error_history:
            return {'total_errors': 0}
        
        category_counts = {}
        recent_errors = []
        
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Recent errors (last hour)
            if (datetime.now(timezone.utc) - error.timestamp).total_seconds() < 3600:
                recent_errors.append({
                    'category': category,
                    'message': error.message,
                    'timestamp': error.timestamp.isoformat()
                })
        
        return {
            'total_errors': len(self.error_history),
            'category_breakdown': category_counts,
            'recent_errors': recent_errors,
            'admin_notifications': len(self.admin_notifications)
        }
    
    def get_admin_notifications(self, unread_only: bool = True) -> List[Dict[str, Any]]:
        """Get admin notifications"""
        if unread_only:
            return [n for n in self.admin_notifications if n.get('read', False) is False]
        return self.admin_notifications.copy()
    
    def mark_notification_read(self, notification_index: int) -> bool:
        """Mark an admin notification as read"""
        try:
            if 0 <= notification_index < len(self.admin_notifications):
                self.admin_notifications[notification_index]['read'] = True
                return True
        except (IndexError, KeyError):
            pass
        return False
    
    def clear_old_errors(self, hours: int = 24) -> int:
        """Clear error history older than specified hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        old_count = len(self.error_history)
        self.error_history = [
            error for error in self.error_history
            if error.timestamp > cutoff_time
        ]
        
        cleared_count = old_count - len(self.error_history)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old error records")
        
        return cleared_count

# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()

def handle_caption_error(context: Dict[str, Any] = None):
    """Decorator for handling caption generation errors"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return await error_recovery_manager.handle_error(e, func, context, *args, **kwargs)
        return wrapper
    return decorator