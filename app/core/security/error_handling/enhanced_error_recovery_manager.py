# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Error Recovery Manager for Multi-Tenant Caption Management

Extends the existing error recovery system with enhanced categorization, 
user-friendly messaging, pattern detection, and administrative escalation.
"""

import logging
import time
import asyncio
import json
from enum import Enum
from typing import Optional, Dict, Any, Callable, List, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

from error_recovery_manager import ErrorRecoveryManager, ErrorCategory, RecoveryStrategy, ErrorInfo, RecoveryConfig
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class EnhancedErrorCategory(Enum):
    """Enhanced error categories for multi-tenant management"""
    USER = "user"                    # User-caused errors (invalid input, permissions)
    SYSTEM = "system"               # System-level errors (database, filesystem)
    PLATFORM = "platform"          # Platform API errors (rate limits, connectivity)
    ADMINISTRATIVE = "administrative"  # Admin action errors
    AUTHENTICATION = "authentication"  # Auth/credential errors
    RESOURCE = "resource"           # Resource exhaustion errors
    VALIDATION = "validation"       # Input validation errors
    NETWORK = "network"            # Network connectivity errors
    UNKNOWN = "unknown"            # Unclassified errors

class EscalationLevel(Enum):
    """Escalation levels for administrative attention"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class EnhancedErrorInfo(ErrorInfo):
    """Enhanced error information with additional context"""
    user_id: Optional[int] = None
    admin_user_id: Optional[int] = None
    platform_connection_id: Optional[int] = None
    task_id: Optional[str] = None
    escalation_level: EscalationLevel = EscalationLevel.NONE
    pattern_matched: Optional[str] = None
    recovery_suggestions: List[str] = None
    admin_notified: bool = False
    
    def __post_init__(self):
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []

@dataclass
class ErrorPattern:
    """Error pattern for detection and escalation"""
    pattern: str
    category: EnhancedErrorCategory
    escalation_level: EscalationLevel
    frequency_threshold: int = 5  # Escalate after N occurrences
    time_window_minutes: int = 60  # Within N minutes
    recovery_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []

class EnhancedErrorRecoveryManager(ErrorRecoveryManager):
    """Enhanced error recovery manager with multi-tenant capabilities"""
    
    def __init__(self):
        super().__init__()
        self.enhanced_error_patterns = self._initialize_enhanced_error_patterns()
        self.enhanced_recovery_configs = self._initialize_enhanced_recovery_configs()
        self.error_pattern_tracker = defaultdict(lambda: deque(maxlen=100))
        self.escalation_history: List[Dict[str, Any]] = []
        self.admin_escalations: List[Dict[str, Any]] = []
        
    def _initialize_enhanced_error_patterns(self) -> List[ErrorPattern]:
        """Initialize enhanced error patterns for detection and escalation"""
        return [
            # User errors
            ErrorPattern(
                pattern="invalid.*input",
                category=EnhancedErrorCategory.USER,
                escalation_level=EscalationLevel.NONE,
                recovery_suggestions=[
                    "Please check your input and try again",
                    "Ensure all required fields are filled correctly",
                    "Verify your settings match the platform requirements"
                ]
            ),
            ErrorPattern(
                pattern="invalid.*user",
                category=EnhancedErrorCategory.USER,
                escalation_level=EscalationLevel.NONE,
                recovery_suggestions=[
                    "Please check your user settings",
                    "Verify your account information is correct"
                ]
            ),
            ErrorPattern(
                pattern="user.*quota",
                category=EnhancedErrorCategory.USER,
                escalation_level=EscalationLevel.MEDIUM,
                recovery_suggestions=[
                    "You have reached your usage limit",
                    "Wait for your quota to reset or contact an administrator"
                ]
            ),           
 ErrorPattern(
                pattern="permission denied",
                category=EnhancedErrorCategory.USER,
                escalation_level=EscalationLevel.LOW,
                frequency_threshold=3,
                recovery_suggestions=[
                    "Check your account permissions",
                    "Contact your administrator for access",
                    "Verify you're logged into the correct account"
                ]
            ),
            ErrorPattern(
                pattern="quota exceeded",
                category=EnhancedErrorCategory.USER,
                escalation_level=EscalationLevel.MEDIUM,
                frequency_threshold=2,
                recovery_suggestions=[
                    "You have reached your usage limit",
                    "Wait for your quota to reset or contact an administrator",
                    "Consider upgrading your account if available"
                ]
            ),
            
            # System errors
            ErrorPattern(
                pattern="database.*error",
                category=EnhancedErrorCategory.SYSTEM,
                escalation_level=EscalationLevel.HIGH,
                frequency_threshold=2,
                time_window_minutes=30,
                recovery_suggestions=[
                    "A system error occurred. Please try again in a few minutes",
                    "If the problem persists, contact support",
                    "The system administrators have been notified"
                ]
            ),
            ErrorPattern(
                pattern="out of memory",
                category=EnhancedErrorCategory.SYSTEM,
                escalation_level=EscalationLevel.CRITICAL,
                frequency_threshold=1,
                recovery_suggestions=[
                    "System resources are currently unavailable",
                    "Please try again later when system load is lower",
                    "Contact support if this problem continues"
                ]
            ),
            ErrorPattern(
                pattern="disk.*full",
                category=EnhancedErrorCategory.SYSTEM,
                escalation_level=EscalationLevel.CRITICAL,
                frequency_threshold=1,
                recovery_suggestions=[
                    "System storage is full",
                    "Please contact an administrator immediately",
                    "New operations may fail until storage is freed"
                ]
            ),
            
            # Platform errors
            ErrorPattern(
                pattern="rate limit.*exceeded",
                category=EnhancedErrorCategory.PLATFORM,
                escalation_level=EscalationLevel.LOW,
                frequency_threshold=10,
                recovery_suggestions=[
                    "Platform rate limit reached. Please wait before trying again",
                    "Consider reducing the frequency of your requests",
                    "The system will automatically retry after the limit resets"
                ]
            ),
            ErrorPattern(
                pattern="platform.*unavailable",
                category=EnhancedErrorCategory.PLATFORM,
                escalation_level=EscalationLevel.MEDIUM,
                frequency_threshold=3,
                recovery_suggestions=[
                    "The platform is temporarily unavailable",
                    "Please try again in a few minutes",
                    "Check the platform's status page for updates"
                ]
            ),
            ErrorPattern(
                pattern="api.*deprecated",
                category=EnhancedErrorCategory.PLATFORM,
                escalation_level=EscalationLevel.HIGH,
                frequency_threshold=1,
                recovery_suggestions=[
                    "The platform API has changed",
                    "System administrators need to update the integration",
                    "Contact support for assistance"
                ]
            ),
            
            # Administrative errors
            ErrorPattern(
                pattern="admin.*unauthorized",
                category=EnhancedErrorCategory.ADMINISTRATIVE,
                escalation_level=EscalationLevel.HIGH,
                frequency_threshold=1,
                recovery_suggestions=[
                    "Administrative action not authorized",
                    "Verify your admin privileges",
                    "Contact a system administrator"
                ]
            ),
            ErrorPattern(
                pattern="configuration.*invalid",
                category=EnhancedErrorCategory.ADMINISTRATIVE,
                escalation_level=EscalationLevel.MEDIUM,
                frequency_threshold=2,
                recovery_suggestions=[
                    "System configuration error detected",
                    "Please check the system settings",
                    "Contact technical support for configuration help"
                ]
            ),
            
            # Authentication errors
            ErrorPattern(
                pattern="token.*expired",
                category=EnhancedErrorCategory.AUTHENTICATION,
                escalation_level=EscalationLevel.LOW,
                recovery_suggestions=[
                    "Your session has expired. Please log in again",
                    "Refresh your platform connection",
                    "Check your account credentials"
                ]
            ),
            ErrorPattern(
                pattern="authentication.*failed",
                category=EnhancedErrorCategory.AUTHENTICATION,
                escalation_level=EscalationLevel.MEDIUM,
                frequency_threshold=5,
                recovery_suggestions=[
                    "Authentication failed. Please check your credentials",
                    "Verify your username and password",
                    "Contact support if you continue having login issues"
                ]
            ),
            
            # Resource errors
            ErrorPattern(
                pattern="ollama.*unavailable",
                category=EnhancedErrorCategory.RESOURCE,
                escalation_level=EscalationLevel.HIGH,
                frequency_threshold=2,
                recovery_suggestions=[
                    "AI service is currently unavailable",
                    "Please try again in a few minutes",
                    "System administrators have been notified"
                ]
            ),
            ErrorPattern(
                pattern="timeout.*exceeded",
                category=EnhancedErrorCategory.RESOURCE,
                escalation_level=EscalationLevel.MEDIUM,
                frequency_threshold=5,
                recovery_suggestions=[
                    "Operation timed out due to high system load",
                    "Please try again with a smaller batch size",
                    "Consider trying during off-peak hours"
                ]
            )
        ]
    
    def _initialize_enhanced_recovery_configs(self) -> Dict[EnhancedErrorCategory, RecoveryConfig]:
        """Initialize enhanced recovery configurations"""
        return {
            EnhancedErrorCategory.USER: RecoveryConfig(
                max_retries=1,
                base_delay=1.0,
                strategy=RecoveryStrategy.FAIL_FAST
            ),
            EnhancedErrorCategory.SYSTEM: RecoveryConfig(
                max_retries=2,
                base_delay=10.0,
                max_delay=300.0,
                backoff_multiplier=3.0,
                strategy=RecoveryStrategy.NOTIFY_ADMIN
            ),
            EnhancedErrorCategory.PLATFORM: RecoveryConfig(
                max_retries=5,
                base_delay=2.0,
                max_delay=120.0,
                backoff_multiplier=2.0,
                strategy=RecoveryStrategy.RETRY
            ),
            EnhancedErrorCategory.ADMINISTRATIVE: RecoveryConfig(
                max_retries=1,
                base_delay=1.0,
                strategy=RecoveryStrategy.NOTIFY_ADMIN
            ),
            EnhancedErrorCategory.AUTHENTICATION: RecoveryConfig(
                max_retries=1,
                base_delay=1.0,
                strategy=RecoveryStrategy.FAIL_FAST
            ),
            EnhancedErrorCategory.RESOURCE: RecoveryConfig(
                max_retries=3,
                base_delay=5.0,
                max_delay=180.0,
                backoff_multiplier=2.5,
                strategy=RecoveryStrategy.RETRY
            ),
            EnhancedErrorCategory.VALIDATION: RecoveryConfig(
                max_retries=0,
                strategy=RecoveryStrategy.FAIL_FAST
            ),
            EnhancedErrorCategory.NETWORK: RecoveryConfig(
                max_retries=4,
                base_delay=1.0,
                max_delay=60.0,
                strategy=RecoveryStrategy.RETRY
            ),
            EnhancedErrorCategory.UNKNOWN: RecoveryConfig(
                max_retries=1,
                base_delay=5.0,
                strategy=RecoveryStrategy.NOTIFY_ADMIN
            )
        }
    
    def enhanced_categorize_error(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None
    ) -> Tuple[EnhancedErrorCategory, Optional[ErrorPattern]]:
        """Enhanced error categorization with pattern matching"""
        error_message = str(error).lower()
        context = context or {}
        
        # Check for specific error patterns
        for pattern in self.enhanced_error_patterns:
            import re
            if re.search(pattern.pattern, error_message, re.IGNORECASE):
                return pattern.category, pattern
        
        # Check context for additional categorization hints
        if context.get('admin_action'):
            return EnhancedErrorCategory.ADMINISTRATIVE, None
        
        if context.get('user_input_error'):
            return EnhancedErrorCategory.USER, None
        
        # Fall back to basic categorization
        basic_category = self.categorize_error(error, context)
        enhanced_category = self._map_basic_to_enhanced_category(basic_category)
        
        return enhanced_category, None
    
    def _map_basic_to_enhanced_category(self, basic_category: ErrorCategory) -> EnhancedErrorCategory:
        """Map basic error categories to enhanced categories"""
        mapping = {
            ErrorCategory.AUTHENTICATION: EnhancedErrorCategory.AUTHENTICATION,
            ErrorCategory.PLATFORM: EnhancedErrorCategory.PLATFORM,
            ErrorCategory.RESOURCE: EnhancedErrorCategory.RESOURCE,
            ErrorCategory.VALIDATION: EnhancedErrorCategory.VALIDATION,
            ErrorCategory.NETWORK: EnhancedErrorCategory.NETWORK,
            ErrorCategory.SYSTEM: EnhancedErrorCategory.SYSTEM,
            ErrorCategory.UNKNOWN: EnhancedErrorCategory.UNKNOWN
        }
        return mapping.get(basic_category, EnhancedErrorCategory.UNKNOWN)
    
    def create_enhanced_error_info(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None
    ) -> EnhancedErrorInfo:
        """Create enhanced error information with additional context"""
        context = context or {}
        category, pattern = self.enhanced_categorize_error(error, context)
        
        # Determine escalation level
        escalation_level = EscalationLevel.NONE
        recovery_suggestions = []
        pattern_matched = None
        
        if pattern:
            escalation_level = pattern.escalation_level
            recovery_suggestions = pattern.recovery_suggestions.copy()
            pattern_matched = pattern.pattern
            
            # Check if pattern frequency threshold is exceeded
            if self._should_escalate_pattern(pattern, error):
                escalation_level = self._increase_escalation_level(escalation_level)
        
        return EnhancedErrorInfo(
            category=category,
            message=str(error),
            details={
                'error_type': type(error).__name__,
                'context': context,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'escalation_level': escalation_level.value,
                'pattern_matched': pattern_matched
            },
            timestamp=datetime.now(timezone.utc),
            recoverable=self._is_enhanced_recoverable(category, error, escalation_level),
            user_id=context.get('user_id'),
            admin_user_id=context.get('admin_user_id'),
            platform_connection_id=context.get('platform_connection_id'),
            task_id=context.get('task_id'),
            escalation_level=escalation_level,
            pattern_matched=pattern_matched,
            recovery_suggestions=recovery_suggestions
        )
    
    def _should_escalate_pattern(self, pattern: ErrorPattern, error: Exception) -> bool:
        """Check if error pattern should be escalated based on frequency"""
        pattern_key = pattern.pattern
        current_time = datetime.now(timezone.utc)
        
        # Add current error to tracker
        self.error_pattern_tracker[pattern_key].append(current_time)
        
        # Count recent occurrences within time window
        cutoff_time = current_time - timedelta(minutes=pattern.time_window_minutes)
        recent_count = sum(
            1 for timestamp in self.error_pattern_tracker[pattern_key]
            if timestamp > cutoff_time
        )
        
        return recent_count >= pattern.frequency_threshold
    
    def _increase_escalation_level(self, current_level: EscalationLevel) -> EscalationLevel:
        """Increase escalation level by one step"""
        levels = [
            EscalationLevel.NONE,
            EscalationLevel.LOW,
            EscalationLevel.MEDIUM,
            EscalationLevel.HIGH,
            EscalationLevel.CRITICAL
        ]
        
        try:
            current_index = levels.index(current_level)
            if current_index < len(levels) - 1:
                return levels[current_index + 1]
        except ValueError:
            pass
        
        return current_level
    
    def _is_enhanced_recoverable(
        self, 
        category: EnhancedErrorCategory, 
        error: Exception, 
        escalation_level: EscalationLevel
    ) -> bool:
        """Determine if an enhanced error is recoverable"""
        # Critical errors are generally not recoverable
        if escalation_level == EscalationLevel.CRITICAL:
            return False
        
        # User and validation errors are typically not recoverable
        non_recoverable_categories = {
            EnhancedErrorCategory.USER,
            EnhancedErrorCategory.VALIDATION,
            EnhancedErrorCategory.AUTHENTICATION
        }
        
        if category in non_recoverable_categories:
            return False
        
        # Administrative errors depend on context
        if category == EnhancedErrorCategory.ADMINISTRATIVE:
            return escalation_level in [EscalationLevel.NONE, EscalationLevel.LOW]
        
        return True 
   
    async def handle_enhanced_error(
        self,
        error: Exception,
        operation: Callable,
        context: Dict[str, Any] = None,
        *args,
        **kwargs
    ) -> Any:
        """Handle an error with enhanced recovery strategies"""
        enhanced_error_info = self.create_enhanced_error_info(error, context)
        self.error_history.append(enhanced_error_info)
        
        # Log error with enhanced details
        await self._log_enhanced_error(enhanced_error_info)
        
        # Check for escalation
        if enhanced_error_info.escalation_level != EscalationLevel.NONE:
            await self._handle_escalation(enhanced_error_info)
        
        # Get recovery configuration
        config = self.enhanced_recovery_configs.get(
            enhanced_error_info.category, 
            self.enhanced_recovery_configs[EnhancedErrorCategory.UNKNOWN]
        )
        
        # Execute recovery strategy
        if config.strategy == RecoveryStrategy.FAIL_FAST:
            return await self._enhanced_fail_fast(enhanced_error_info)
        elif config.strategy == RecoveryStrategy.RETRY:
            return await self._enhanced_retry_with_backoff(
                enhanced_error_info, operation, config, *args, **kwargs
            )
        elif config.strategy == RecoveryStrategy.NOTIFY_ADMIN:
            return await self._enhanced_notify_admin_and_fail(enhanced_error_info)
        else:
            return await self._enhanced_fail_fast(enhanced_error_info)
    
    async def _log_enhanced_error(self, error_info: EnhancedErrorInfo) -> None:
        """Log enhanced error information"""
        log_data = {
            'category': error_info.category.value,
            'escalation_level': error_info.escalation_level.value,
            'pattern_matched': error_info.pattern_matched,
            'user_id': error_info.user_id,
            'task_id': error_info.task_id,
            'message': sanitize_for_log(error_info.message),
            'recovery_suggestions_count': len(error_info.recovery_suggestions)
        }
        
        if error_info.escalation_level in [EscalationLevel.HIGH, EscalationLevel.CRITICAL]:
            logger.critical(f"Critical error detected: {json.dumps(log_data)}")
        elif error_info.escalation_level == EscalationLevel.MEDIUM:
            logger.warning(f"Medium priority error: {json.dumps(log_data)}")
        else:
            logger.error(f"Error occurred: {json.dumps(log_data)}")
    
    async def _handle_escalation(self, error_info: EnhancedErrorInfo) -> None:
        """Handle error escalation to administrators"""
        escalation_data = {
            'timestamp': error_info.timestamp.isoformat(),
            'category': error_info.category.value,
            'escalation_level': error_info.escalation_level.value,
            'pattern_matched': error_info.pattern_matched,
            'user_id': error_info.user_id,
            'task_id': error_info.task_id,
            'message': error_info.message,
            'recovery_suggestions': error_info.recovery_suggestions,
            'requires_immediate_attention': error_info.escalation_level == EscalationLevel.CRITICAL
        }
        
        self.escalation_history.append(escalation_data)
        
        # Add to admin notifications if high priority
        if error_info.escalation_level in [EscalationLevel.HIGH, EscalationLevel.CRITICAL]:
            admin_notification = {
                'type': 'error_escalation',
                'severity': error_info.escalation_level.value,
                'category': error_info.category.value,
                'message': f"Error escalation: {error_info.message}",
                'details': escalation_data,
                'timestamp': error_info.timestamp.isoformat(),
                'requires_attention': True,
                'read': False
            }
            
            self.admin_notifications.append(admin_notification)
            error_info.admin_notified = True
            
            logger.critical(
                f"ADMIN ESCALATION [{error_info.escalation_level.value.upper()}]: "
                f"{error_info.category.value} error requires attention - "
                f"{sanitize_for_log(error_info.message)}"
            )
    
    async def _enhanced_fail_fast(self, error_info: EnhancedErrorInfo) -> None:
        """Enhanced fail fast strategy with user-friendly messaging"""
        user_message = self._generate_user_friendly_message(error_info)
        
        logger.error(
            f"Failing fast for {error_info.category.value} error: "
            f"{sanitize_for_log(error_info.message)}"
        )
        
        # Create detailed error response
        error_response = {
            'success': False,
            'error_category': error_info.category.value,
            'user_message': user_message,
            'recovery_suggestions': error_info.recovery_suggestions,
            'escalation_level': error_info.escalation_level.value,
            'timestamp': error_info.timestamp.isoformat()
        }
        
        raise Exception(json.dumps(error_response))
    
    async def _enhanced_retry_with_backoff(
        self,
        error_info: EnhancedErrorInfo,
        operation: Callable,
        config: RecoveryConfig,
        *args,
        **kwargs
    ) -> Any:
        """Enhanced retry with exponential backoff and user feedback"""
        if error_info.retry_count >= config.max_retries:
            logger.error(
                f"Max retries exceeded for {error_info.category.value} error: "
                f"{sanitize_for_log(error_info.message)}"
            )
            return await self._enhanced_fail_fast(error_info)
        
        # Calculate delay with exponential backoff
        delay = min(
            config.base_delay * (config.backoff_multiplier ** error_info.retry_count),
            config.max_delay
        )
        
        logger.info(
            f"Retrying {error_info.category.value} operation after {delay}s "
            f"(attempt {error_info.retry_count + 1}/{config.max_retries})"
        )
        
        await asyncio.sleep(delay)
        error_info.retry_count += 1
        
        try:
            return await operation(*args, **kwargs)
        except Exception as retry_error:
            # Update context with retry information
            retry_context = error_info.details.get('context', {}).copy()
            retry_context['retry_attempt'] = error_info.retry_count
            retry_context['original_error'] = error_info.message
            
            return await self.handle_enhanced_error(
                retry_error, operation, retry_context, *args, **kwargs
            )
    
    async def _enhanced_notify_admin_and_fail(self, error_info: EnhancedErrorInfo) -> None:
        """Enhanced admin notification with detailed context"""
        await self._handle_escalation(error_info)
        
        user_message = self._generate_user_friendly_message(error_info)
        
        logger.critical(
            f"Admin notification required for {error_info.category.value} error: "
            f"{sanitize_for_log(error_info.message)}"
        )
        
        # Create detailed error response
        error_response = {
            'success': False,
            'error_category': error_info.category.value,
            'user_message': user_message,
            'recovery_suggestions': error_info.recovery_suggestions,
            'admin_notified': True,
            'escalation_level': error_info.escalation_level.value,
            'timestamp': error_info.timestamp.isoformat()
        }
        
        raise Exception(json.dumps(error_response))
    
    def _generate_user_friendly_message(self, error_info: EnhancedErrorInfo) -> str:
        """Generate user-friendly error message with recovery suggestions"""
        # Base messages by category
        category_messages = {
            EnhancedErrorCategory.USER: "There was an issue with your request.",
            EnhancedErrorCategory.SYSTEM: "A system error occurred.",
            EnhancedErrorCategory.PLATFORM: "There was a problem connecting to the platform.",
            EnhancedErrorCategory.ADMINISTRATIVE: "An administrative error occurred.",
            EnhancedErrorCategory.AUTHENTICATION: "Authentication failed.",
            EnhancedErrorCategory.RESOURCE: "System resources are currently unavailable.",
            EnhancedErrorCategory.VALIDATION: "The provided information is invalid.",
            EnhancedErrorCategory.NETWORK: "A network connection error occurred.",
            EnhancedErrorCategory.UNKNOWN: "An unexpected error occurred."
        }
        
        base_message = category_messages.get(
            error_info.category, 
            "An error occurred during processing."
        )
        
        # Add escalation context
        if error_info.escalation_level == EscalationLevel.CRITICAL:
            base_message += " This is a critical issue that requires immediate attention."
        elif error_info.escalation_level == EscalationLevel.HIGH:
            base_message += " This issue has been escalated to administrators."
        elif error_info.escalation_level == EscalationLevel.MEDIUM:
            base_message += " This issue is being monitored."
        
        # Add recovery suggestions if available
        if error_info.recovery_suggestions:
            suggestions_text = " Here's what you can try: " + "; ".join(error_info.recovery_suggestions)
            base_message += suggestions_text
        
        return base_message
    
    def get_enhanced_error_statistics(self) -> Dict[str, Any]:
        """Get enhanced error statistics for monitoring"""
        if not self.error_history:
            return {
                'total_errors': 0,
                'escalations': 0,
                'admin_notifications': 0
            }
        
        # Count by enhanced categories
        category_counts = defaultdict(int)
        escalation_counts = defaultdict(int)
        pattern_counts = defaultdict(int)
        
        recent_errors = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        for error in self.error_history:
            if isinstance(error, EnhancedErrorInfo):
                category_counts[error.category.value] += 1
                escalation_counts[error.escalation_level.value] += 1
                
                if error.pattern_matched:
                    pattern_counts[error.pattern_matched] += 1
                
                # Recent errors (last hour)
                if error.timestamp > cutoff_time:
                    recent_errors.append({
                        'category': error.category.value,
                        'escalation_level': error.escalation_level.value,
                        'pattern_matched': error.pattern_matched,
                        'message': error.message,
                        'timestamp': error.timestamp.isoformat(),
                        'user_id': error.user_id,
                        'task_id': error.task_id
                    })
        
        return {
            'total_errors': len(self.error_history),
            'category_breakdown': dict(category_counts),
            'escalation_breakdown': dict(escalation_counts),
            'pattern_breakdown': dict(pattern_counts),
            'recent_errors': recent_errors,
            'escalations_total': len(self.escalation_history),
            'admin_notifications': len([n for n in self.admin_notifications if not n.get('read', False)]),
            'critical_errors': escalation_counts[EscalationLevel.CRITICAL.value],
            'high_priority_errors': escalation_counts[EscalationLevel.HIGH.value]
        }
    
    def get_escalation_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get escalation history for the specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            escalation for escalation in self.escalation_history
            if datetime.fromisoformat(escalation['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    def clear_old_escalations(self, hours: int = 168) -> int:  # Default 1 week
        """Clear old escalation history"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        old_count = len(self.escalation_history)
        self.escalation_history = [
            escalation for escalation in self.escalation_history
            if datetime.fromisoformat(escalation['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
        
        cleared_count = old_count - len(self.escalation_history)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old escalation records")
        
        return cleared_count

# Global enhanced error recovery manager instance
enhanced_error_recovery_manager = EnhancedErrorRecoveryManager()

def handle_enhanced_caption_error(context: Dict[str, Any] = None):
    """Decorator for handling caption generation errors with enhanced recovery"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return await enhanced_error_recovery_manager.handle_enhanced_error(
                    e, func, context, *args, **kwargs
                )
        return wrapper
    return decorator