# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Management Error Handling and Recovery

This module provides comprehensive error handling and recovery mechanisms
for platform management operations, integrating with the unified notification system
to provide real-time error reporting and recovery guidance.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone

from flask import current_app
from flask_login import current_user

from platform_management_notification_integration import (
    PlatformManagementNotificationService,
    get_platform_notification_service
)
from models import NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class PlatformErrorType(Enum):
    """Platform operation error types"""
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    MAINTENANCE_ERROR = "maintenance_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


class PlatformErrorSeverity(Enum):
    """Platform error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PlatformError:
    """Platform operation error information"""
    error_type: PlatformErrorType
    severity: PlatformErrorSeverity
    message: str
    details: Optional[str] = None
    platform_name: Optional[str] = None
    operation_type: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    recovery_suggestions: Optional[List[str]] = None
    requires_user_action: bool = False
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []


class PlatformErrorHandler:
    """
    Comprehensive error handler for platform management operations
    
    Provides error classification, recovery suggestions, and real-time
    notification of errors via the unified WebSocket system.
    """
    
    def __init__(self, notification_service: Optional[PlatformManagementNotificationService] = None):
        """
        Initialize platform error handler
        
        Args:
            notification_service: Platform notification service instance
        """
        self.notification_service = notification_service or get_platform_notification_service()
        
        # Error classification patterns
        self._error_patterns = {
            PlatformErrorType.CONNECTION_ERROR: [
                'connection refused', 'connection timeout', 'connection failed',
                'network unreachable', 'host unreachable', 'dns resolution failed'
            ],
            PlatformErrorType.AUTHENTICATION_ERROR: [
                'invalid token', 'token expired', 'unauthorized', 'invalid credentials',
                'authentication failed', 'access denied', 'invalid api key'
            ],
            PlatformErrorType.AUTHORIZATION_ERROR: [
                'forbidden', 'insufficient permissions', 'access denied',
                'not authorized', 'permission denied'
            ],
            PlatformErrorType.VALIDATION_ERROR: [
                'validation failed', 'invalid input', 'bad request',
                'missing required field', 'invalid format'
            ],
            PlatformErrorType.NETWORK_ERROR: [
                'network error', 'socket error', 'ssl error',
                'certificate error', 'proxy error'
            ],
            PlatformErrorType.SERVER_ERROR: [
                'internal server error', 'server error', 'service unavailable',
                'bad gateway', 'gateway timeout'
            ],
            PlatformErrorType.TIMEOUT_ERROR: [
                'timeout', 'request timeout', 'read timeout',
                'connection timeout', 'operation timeout'
            ],
            PlatformErrorType.RATE_LIMIT_ERROR: [
                'rate limit', 'too many requests', 'quota exceeded',
                'throttled', 'rate exceeded'
            ],
            PlatformErrorType.MAINTENANCE_ERROR: [
                'maintenance mode', 'service maintenance', 'temporarily unavailable',
                'scheduled maintenance', 'system maintenance'
            ]
        }
        
        # Recovery suggestions by error type
        self._recovery_suggestions = {
            PlatformErrorType.CONNECTION_ERROR: [
                "Check your internet connection",
                "Verify the platform instance URL is correct",
                "Try again in a few minutes",
                "Contact the platform administrator if the issue persists"
            ],
            PlatformErrorType.AUTHENTICATION_ERROR: [
                "Update your access token in platform settings",
                "Re-authenticate with the platform",
                "Check if your account is still active",
                "Verify your credentials are correct"
            ],
            PlatformErrorType.AUTHORIZATION_ERROR: [
                "Check your account permissions on the platform",
                "Contact the platform administrator for access",
                "Verify your account has the required privileges"
            ],
            PlatformErrorType.VALIDATION_ERROR: [
                "Check all required fields are filled correctly",
                "Verify the format of URLs and usernames",
                "Review the platform connection settings"
            ],
            PlatformErrorType.NETWORK_ERROR: [
                "Check your network connection",
                "Try using a different network",
                "Check if a firewall is blocking the connection",
                "Contact your network administrator"
            ],
            PlatformErrorType.SERVER_ERROR: [
                "The platform server is experiencing issues",
                "Try again in a few minutes",
                "Check the platform's status page",
                "Contact the platform support team"
            ],
            PlatformErrorType.TIMEOUT_ERROR: [
                "The operation took too long to complete",
                "Try again with a stable internet connection",
                "Check if the platform is experiencing high load"
            ],
            PlatformErrorType.RATE_LIMIT_ERROR: [
                "You've made too many requests recently",
                "Wait a few minutes before trying again",
                "Check your API usage limits"
            ],
            PlatformErrorType.MAINTENANCE_ERROR: [
                "The platform is currently under maintenance",
                "Try again after the maintenance window",
                "Check the platform's status page for updates"
            ]
        }
        
        logger.info("Platform error handler initialized")
    
    def classify_error(self, error_message: str, error_details: Optional[str] = None) -> PlatformErrorType:
        """
        Classify error based on message content
        
        Args:
            error_message: Error message to classify
            error_details: Additional error details
            
        Returns:
            Classified error type
        """
        try:
            # Combine message and details for classification
            full_text = (error_message + ' ' + (error_details or '')).lower()
            
            # Check patterns for each error type
            for error_type, patterns in self._error_patterns.items():
                for pattern in patterns:
                    if pattern in full_text:
                        return error_type
            
            # Default to unknown error
            return PlatformErrorType.UNKNOWN_ERROR
            
        except Exception as e:
            logger.error(f"Error classifying platform error: {e}")
            return PlatformErrorType.UNKNOWN_ERROR
    
    def determine_severity(self, error_type: PlatformErrorType, 
                          operation_type: str) -> PlatformErrorSeverity:
        """
        Determine error severity based on type and operation
        
        Args:
            error_type: Type of error
            operation_type: Type of operation that failed
            
        Returns:
            Error severity level
        """
        try:
            # Critical errors that prevent core functionality
            if error_type in [PlatformErrorType.AUTHENTICATION_ERROR, 
                            PlatformErrorType.AUTHORIZATION_ERROR]:
                return PlatformErrorSeverity.CRITICAL
            
            # High severity errors that impact user experience
            if error_type in [PlatformErrorType.CONNECTION_ERROR,
                            PlatformErrorType.SERVER_ERROR]:
                return PlatformErrorSeverity.HIGH
            
            # Medium severity errors that are temporary
            if error_type in [PlatformErrorType.TIMEOUT_ERROR,
                            PlatformErrorType.RATE_LIMIT_ERROR,
                            PlatformErrorType.MAINTENANCE_ERROR]:
                return PlatformErrorSeverity.MEDIUM
            
            # Low severity errors that are user-correctable
            if error_type in [PlatformErrorType.VALIDATION_ERROR,
                            PlatformErrorType.CONFIGURATION_ERROR]:
                return PlatformErrorSeverity.LOW
            
            # Default to medium severity
            return PlatformErrorSeverity.MEDIUM
            
        except Exception as e:
            logger.error(f"Error determining severity: {e}")
            return PlatformErrorSeverity.MEDIUM
    
    def create_platform_error(self, error_message: str, operation_type: str,
                            platform_name: Optional[str] = None,
                            error_details: Optional[str] = None,
                            error_code: Optional[str] = None) -> PlatformError:
        """
        Create comprehensive platform error object
        
        Args:
            error_message: Primary error message
            operation_type: Type of operation that failed
            platform_name: Name of platform (if applicable)
            error_details: Additional error details
            error_code: Error code (if applicable)
            
        Returns:
            PlatformError object with classification and recovery suggestions
        """
        try:
            # Classify error
            error_type = self.classify_error(error_message, error_details)
            
            # Determine severity
            severity = self.determine_severity(error_type, operation_type)
            
            # Get recovery suggestions
            recovery_suggestions = self._recovery_suggestions.get(error_type, [
                "Try the operation again",
                "Check your platform settings",
                "Contact support if the issue persists"
            ])
            
            # Determine if user action is required
            requires_user_action = error_type in [
                PlatformErrorType.AUTHENTICATION_ERROR,
                PlatformErrorType.AUTHORIZATION_ERROR,
                PlatformErrorType.VALIDATION_ERROR,
                PlatformErrorType.CONFIGURATION_ERROR
            ]
            
            # Set action URL and text for actionable errors
            action_url = None
            action_text = None
            if requires_user_action:
                action_url = '/platform_management'
                if error_type == PlatformErrorType.AUTHENTICATION_ERROR:
                    action_text = 'Update Credentials'
                elif error_type == PlatformErrorType.VALIDATION_ERROR:
                    action_text = 'Fix Settings'
                else:
                    action_text = 'Review Settings'
            
            return PlatformError(
                error_type=error_type,
                severity=severity,
                message=error_message,
                details=error_details,
                platform_name=platform_name,
                operation_type=operation_type,
                error_code=error_code,
                recovery_suggestions=recovery_suggestions,
                requires_user_action=requires_user_action,
                action_url=action_url,
                action_text=action_text
            )
            
        except Exception as e:
            logger.error(f"Error creating platform error object: {e}")
            # Return basic error object as fallback
            return PlatformError(
                error_type=PlatformErrorType.UNKNOWN_ERROR,
                severity=PlatformErrorSeverity.MEDIUM,
                message=error_message,
                details=error_details,
                platform_name=platform_name,
                operation_type=operation_type
            )
    
    def handle_platform_error(self, error: Exception, operation_type: str,
                            platform_name: Optional[str] = None,
                            user_id: Optional[int] = None) -> PlatformError:
        """
        Handle platform operation error with notification
        
        Args:
            error: Exception that occurred
            operation_type: Type of operation that failed
            platform_name: Name of platform (if applicable)
            user_id: User ID (defaults to current user)
            
        Returns:
            PlatformError object with error details
        """
        try:
            # Extract error information
            error_message = str(error)
            error_details = None
            error_code = None
            
            # Get additional error details if available
            if hasattr(error, 'response'):
                # HTTP error with response
                response = error.response
                if hasattr(response, 'status_code'):
                    error_code = str(response.status_code)
                if hasattr(response, 'text'):
                    error_details = response.text[:500]  # Limit details length
            elif hasattr(error, 'args') and len(error.args) > 1:
                # Multiple error arguments
                error_details = str(error.args[1])[:500]
            
            # Create platform error object
            platform_error = self.create_platform_error(
                error_message=error_message,
                operation_type=operation_type,
                platform_name=platform_name,
                error_details=error_details,
                error_code=error_code
            )
            
            # Send notification if service is available
            if self.notification_service:
                self._send_error_notification(platform_error, user_id)
            
            # Log error with full details
            self._log_platform_error(platform_error, error)
            
            return platform_error
            
        except Exception as e:
            logger.error(f"Error handling platform error: {e}")
            # Return basic error as fallback
            return PlatformError(
                error_type=PlatformErrorType.UNKNOWN_ERROR,
                severity=PlatformErrorSeverity.HIGH,
                message="An unexpected error occurred",
                operation_type=operation_type,
                platform_name=platform_name
            )
    
    def _send_error_notification(self, platform_error: PlatformError, 
                               user_id: Optional[int] = None) -> bool:
        """
        Send error notification via WebSocket
        
        Args:
            platform_error: Platform error to notify about
            user_id: Target user ID
            
        Returns:
            True if notification sent successfully
        """
        try:
            if user_id is None:
                if hasattr(current_user, 'id'):
                    user_id = current_user.id
                else:
                    logger.warning("No user ID available for error notification")
                    return False
            
            # Determine notification based on error type
            if platform_error.error_type == PlatformErrorType.AUTHENTICATION_ERROR:
                return self.notification_service.send_platform_authentication_error(
                    user_id=user_id,
                    platform_name=platform_error.platform_name or 'Unknown Platform',
                    error_type=platform_error.error_type.value,
                    error_details=platform_error.message
                )
            else:
                # Send general platform error notification
                from platform_management_notification_integration import (
                    create_platform_operation_result
                )
                
                result = create_platform_operation_result(
                    success=False,
                    message=platform_error.message,
                    operation_type=platform_error.operation_type or 'platform_operation',
                    error_details=platform_error.details
                )
                
                return self.notification_service.send_platform_connection_notification(
                    user_id, result
                )
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False
    
    def _log_platform_error(self, platform_error: PlatformError, 
                          original_error: Exception) -> None:
        """
        Log platform error with comprehensive details
        
        Args:
            platform_error: Platform error object
            original_error: Original exception
        """
        try:
            log_data = {
                'error_type': platform_error.error_type.value,
                'severity': platform_error.severity.value,
                'message': platform_error.message,
                'platform_name': platform_error.platform_name,
                'operation_type': platform_error.operation_type,
                'error_code': platform_error.error_code,
                'user_id': getattr(current_user, 'id', None) if hasattr(current_user, 'id') else None,
                'timestamp': platform_error.timestamp.isoformat() if platform_error.timestamp else None
            }
            
            # Log based on severity
            if platform_error.severity == PlatformErrorSeverity.CRITICAL:
                logger.critical(f"Critical platform error: {log_data}")
            elif platform_error.severity == PlatformErrorSeverity.HIGH:
                logger.error(f"High severity platform error: {log_data}")
            elif platform_error.severity == PlatformErrorSeverity.MEDIUM:
                logger.warning(f"Medium severity platform error: {log_data}")
            else:
                logger.info(f"Low severity platform error: {log_data}")
            
            # Log stack trace for debugging
            if platform_error.severity in [PlatformErrorSeverity.CRITICAL, PlatformErrorSeverity.HIGH]:
                logger.debug(f"Platform error stack trace: {traceback.format_exception(type(original_error), original_error, original_error.__traceback__)}")
            
        except Exception as e:
            logger.error(f"Error logging platform error: {e}")
    
    def get_error_recovery_info(self, platform_error: PlatformError) -> Dict[str, Any]:
        """
        Get error recovery information for client
        
        Args:
            platform_error: Platform error object
            
        Returns:
            Dictionary with recovery information
        """
        try:
            return {
                'error_type': platform_error.error_type.value,
                'severity': platform_error.severity.value,
                'message': platform_error.message,
                'recovery_suggestions': platform_error.recovery_suggestions,
                'requires_user_action': platform_error.requires_user_action,
                'action_url': platform_error.action_url,
                'action_text': platform_error.action_text,
                'can_retry': platform_error.error_type not in [
                    PlatformErrorType.AUTHENTICATION_ERROR,
                    PlatformErrorType.AUTHORIZATION_ERROR,
                    PlatformErrorType.VALIDATION_ERROR
                ],
                'retry_delay': self._get_retry_delay(platform_error.error_type)
            }
            
        except Exception as e:
            logger.error(f"Error getting recovery info: {e}")
            return {
                'error_type': 'unknown_error',
                'severity': 'medium',
                'message': platform_error.message,
                'recovery_suggestions': ['Try again later'],
                'requires_user_action': False,
                'can_retry': True,
                'retry_delay': 5
            }
    
    def _get_retry_delay(self, error_type: PlatformErrorType) -> int:
        """
        Get recommended retry delay in seconds
        
        Args:
            error_type: Type of error
            
        Returns:
            Retry delay in seconds
        """
        retry_delays = {
            PlatformErrorType.RATE_LIMIT_ERROR: 60,  # 1 minute
            PlatformErrorType.SERVER_ERROR: 30,     # 30 seconds
            PlatformErrorType.TIMEOUT_ERROR: 15,    # 15 seconds
            PlatformErrorType.NETWORK_ERROR: 10,    # 10 seconds
            PlatformErrorType.CONNECTION_ERROR: 5,  # 5 seconds
        }
        
        return retry_delays.get(error_type, 5)  # Default 5 seconds


# Global error handler instance
_error_handler = None


def get_platform_error_handler() -> PlatformErrorHandler:
    """
    Get platform error handler instance
    
    Returns:
        PlatformErrorHandler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = PlatformErrorHandler()
    return _error_handler


def handle_platform_operation_error(error: Exception, operation_type: str,
                                  platform_name: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
    """
    Convenience function to handle platform operation errors
    
    Args:
        error: Exception that occurred
        operation_type: Type of operation that failed
        platform_name: Name of platform (if applicable)
        
    Returns:
        Tuple of (error response dict, HTTP status code)
    """
    try:
        error_handler = get_platform_error_handler()
        platform_error = error_handler.handle_platform_error(
            error, operation_type, platform_name
        )
        
        # Get recovery information
        recovery_info = error_handler.get_error_recovery_info(platform_error)
        
        # Determine HTTP status code based on error type
        status_codes = {
            PlatformErrorType.AUTHENTICATION_ERROR: 401,
            PlatformErrorType.AUTHORIZATION_ERROR: 403,
            PlatformErrorType.VALIDATION_ERROR: 400,
            PlatformErrorType.RATE_LIMIT_ERROR: 429,
            PlatformErrorType.SERVER_ERROR: 502,
            PlatformErrorType.MAINTENANCE_ERROR: 503,
            PlatformErrorType.TIMEOUT_ERROR: 504,
        }
        
        status_code = status_codes.get(platform_error.error_type, 500)
        
        # Create error response
        error_response = {
            'success': False,
            'error': platform_error.message,
            'error_details': platform_error.details,
            'error_info': recovery_info
        }
        
        return error_response, status_code
        
    except Exception as e:
        logger.error(f"Error in platform operation error handler: {e}")
        return {
            'success': False,
            'error': 'An unexpected error occurred',
            'error_details': str(e)
        }, 500