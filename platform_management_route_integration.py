# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Management Route Integration

This module provides integration helpers for updating platform management routes
to use the unified WebSocket notification system instead of legacy flash messages
and JSON responses.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from flask import jsonify, current_app
from flask_login import current_user

from platform_management_notification_integration import (
    PlatformManagementNotificationService,
    PlatformOperationResult,
    create_platform_operation_result,
    get_platform_notification_service
)

logger = logging.getLogger(__name__)


class PlatformRouteNotificationIntegrator:
    """
    Integrates platform management routes with the unified notification system
    
    Provides helper methods to send notifications for platform operations
    while maintaining backward compatibility with existing JSON responses.
    """
    
    def __init__(self):
        """Initialize platform route notification integrator"""
        self.notification_service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize notification service from app context"""
        try:
            self.notification_service = get_platform_notification_service()
            if self.notification_service:
                logger.info("Platform route notification integrator initialized")
            else:
                logger.warning("Platform notification service not available")
        except Exception as e:
            logger.error(f"Error initializing platform route notification integrator: {e}")
    
    def handle_add_platform_response(self, success: bool, message: str, 
                                   platform_data: Optional[Dict[str, Any]] = None,
                                   is_first_platform: bool = False,
                                   error_details: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Handle add platform operation response with notifications
        
        Args:
            success: Whether operation was successful
            message: Operation result message
            platform_data: Platform data if successful
            is_first_platform: Whether this is the user's first platform
            error_details: Detailed error information if failed
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Create operation result
            result = create_platform_operation_result(
                success=success,
                message=message,
                operation_type='add_platform',
                platform_data=platform_data,
                error_details=error_details,
                requires_refresh=is_first_platform
            )
            
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                notification_sent = self.notification_service.send_platform_connection_notification(
                    current_user.id, result
                )
                if not notification_sent:
                    logger.warning("Failed to send add platform notification")
            
            # Prepare JSON response
            response_data = {
                'success': success,
                'message': message,
                'is_first_platform': is_first_platform,
                'requires_refresh': is_first_platform
            }
            
            if success and platform_data:
                response_data['platform'] = platform_data
                response_data['session_updated'] = is_first_platform
            
            if not success and error_details:
                response_data['error'] = error_details
            
            status_code = 200 if success else 400
            return response_data, status_code
            
        except Exception as e:
            logger.error(f"Error handling add platform response: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500
    
    def handle_switch_platform_response(self, success: bool, message: str,
                                      platform_data: Optional[Dict[str, Any]] = None,
                                      from_platform: Optional[str] = None,
                                      error_message: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Handle switch platform operation response with notifications
        
        Args:
            success: Whether operation was successful
            message: Operation result message
            platform_data: New platform data if successful
            from_platform: Previous platform name
            error_message: Error message if failed
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                to_platform = platform_data.get('name') if platform_data else 'Unknown'
                notification_sent = self.notification_service.send_platform_switch_notification(
                    current_user.id, from_platform, to_platform, success, error_message
                )
                if not notification_sent:
                    logger.warning("Failed to send switch platform notification")
            
            # Prepare JSON response
            response_data = {
                'success': success,
                'message': message
            }
            
            if success and platform_data:
                response_data['platform'] = platform_data
            
            if not success and error_message:
                response_data['error'] = error_message
            
            status_code = 200 if success else 500
            return response_data, status_code
            
        except Exception as e:
            logger.error(f"Error handling switch platform response: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500
    
    def handle_test_platform_response(self, success: bool, message: str,
                                    platform_name: str,
                                    platform_info: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], int]:
        """
        Handle test platform connection response with notifications
        
        Args:
            success: Whether test was successful
            message: Test result message
            platform_name: Name of tested platform
            platform_info: Platform information
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                status = 'active' if success else 'error'
                notification_sent = self.notification_service.send_platform_status_notification(
                    current_user.id, platform_name, status, message
                )
                if not notification_sent:
                    logger.warning("Failed to send test platform notification")
            
            # Prepare JSON response
            response_data = {
                'success': success,
                'message': message
            }
            
            if platform_info:
                response_data['platform_info'] = platform_info
            
            return response_data, 200
            
        except Exception as e:
            logger.error(f"Error handling test platform response: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500
    
    def handle_edit_platform_response(self, success: bool, message: str,
                                    platform_name: str,
                                    change_details: Optional[str] = None,
                                    error_details: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Handle edit platform operation response with notifications
        
        Args:
            success: Whether operation was successful
            message: Operation result message
            platform_name: Name of edited platform
            change_details: Details of changes made
            error_details: Error details if failed
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                if success:
                    notification_sent = self.notification_service.send_platform_configuration_change_notification(
                        current_user.id, platform_name, 'edit', change_details or message
                    )
                else:
                    # Create operation result for error notification
                    result = create_platform_operation_result(
                        success=False,
                        message=message,
                        operation_type='edit_platform',
                        error_details=error_details
                    )
                    notification_sent = self.notification_service.send_platform_connection_notification(
                        current_user.id, result
                    )
                
                if not notification_sent:
                    logger.warning("Failed to send edit platform notification")
            
            # Prepare JSON response
            response_data = {
                'success': success,
                'message': message
            }
            
            if not success and error_details:
                response_data['error'] = error_details
            
            status_code = 200 if success else 400
            return response_data, status_code
            
        except Exception as e:
            logger.error(f"Error handling edit platform response: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500
    
    def handle_delete_platform_response(self, success: bool, message: str,
                                      platform_name: str,
                                      error_details: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Handle delete platform operation response with notifications
        
        Args:
            success: Whether operation was successful
            message: Operation result message
            platform_name: Name of deleted platform
            error_details: Error details if failed
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Create operation result
            result = create_platform_operation_result(
                success=success,
                message=message,
                operation_type='delete_platform',
                platform_data={'name': platform_name} if success else None,
                error_details=error_details,
                requires_refresh=success
            )
            
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                notification_sent = self.notification_service.send_platform_connection_notification(
                    current_user.id, result
                )
                if not notification_sent:
                    logger.warning("Failed to send delete platform notification")
            
            # Prepare JSON response
            response_data = {
                'success': success,
                'message': message
            }
            
            if not success and error_details:
                response_data['error'] = error_details
            
            status_code = 200 if success else 400
            return response_data, status_code
            
        except Exception as e:
            logger.error(f"Error handling delete platform response: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500
    
    def handle_authentication_error(self, platform_name: str, error_type: str,
                                  error_details: str) -> Tuple[Dict[str, Any], int]:
        """
        Handle platform authentication error with notifications
        
        Args:
            platform_name: Name of platform with auth error
            error_type: Type of authentication error
            error_details: Detailed error message
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                notification_sent = self.notification_service.send_platform_authentication_error(
                    current_user.id, platform_name, error_type, error_details
                )
                if not notification_sent:
                    logger.warning("Failed to send authentication error notification")
            
            # Prepare JSON response
            response_data = {
                'success': False,
                'error': f'Authentication failed for {platform_name}: {error_details}',
                'error_type': 'authentication',
                'platform_name': platform_name,
                'requires_action': True,
                'action_text': 'Update Credentials',
                'action_url': '/platform_management'
            }
            
            return response_data, 401
            
        except Exception as e:
            logger.error(f"Error handling authentication error: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500
    
    def handle_maintenance_mode_response(self, operation_type: str,
                                       maintenance_info: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Handle maintenance mode response with notifications
        
        Args:
            operation_type: Type of operation that was blocked
            maintenance_info: Maintenance mode information
            
        Returns:
            Tuple of (JSON response dict, HTTP status code)
        """
        try:
            # Send WebSocket notification
            if self.notification_service and hasattr(current_user, 'id'):
                notification_sent = self.notification_service.send_maintenance_mode_notification(
                    current_user.id, operation_type, maintenance_info
                )
                if not notification_sent:
                    logger.warning("Failed to send maintenance mode notification")
            
            # Prepare JSON response
            response_data = {
                'success': False,
                'maintenance_active': True,
                'maintenance_info': maintenance_info,
                'operation_info': {
                    'title': 'Service Temporarily Unavailable',
                    'description': f'Platform {operation_type} is temporarily disabled during maintenance.',
                    'icon': '🔧',
                    'suggestion': 'Please try again after maintenance is complete.'
                },
                'error': f'Platform {operation_type} is temporarily unavailable during maintenance'
            }
            
            return response_data, 503
            
        except Exception as e:
            logger.error(f"Error handling maintenance mode response: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500


# Global instance for use in routes
_route_integrator = None


def get_platform_route_integrator() -> PlatformRouteNotificationIntegrator:
    """
    Get platform route notification integrator instance
    
    Returns:
        PlatformRouteNotificationIntegrator instance
    """
    global _route_integrator
    if _route_integrator is None:
        _route_integrator = PlatformRouteNotificationIntegrator()
    return _route_integrator


def send_platform_operation_notification(operation_type: str, success: bool, 
                                       message: str, **kwargs) -> bool:
    """
    Convenience function to send platform operation notification
    
    Args:
        operation_type: Type of platform operation
        success: Whether operation was successful
        message: Operation result message
        **kwargs: Additional operation-specific parameters
        
    Returns:
        True if notification sent successfully
    """
    try:
        integrator = get_platform_route_integrator()
        
        # Route to appropriate handler based on operation type
        if operation_type == 'add_platform':
            response_data, status_code = integrator.handle_add_platform_response(
                success, message, **kwargs
            )
        elif operation_type == 'switch_platform':
            response_data, status_code = integrator.handle_switch_platform_response(
                success, message, **kwargs
            )
        elif operation_type == 'test_platform':
            platform_name = kwargs.get('platform_name', 'Unknown')
            response_data, status_code = integrator.handle_test_platform_response(
                success, message, platform_name, **kwargs
            )
        elif operation_type == 'edit_platform':
            platform_name = kwargs.get('platform_name', 'Unknown')
            response_data, status_code = integrator.handle_edit_platform_response(
                success, message, platform_name, **kwargs
            )
        elif operation_type == 'delete_platform':
            platform_name = kwargs.get('platform_name', 'Unknown')
            response_data, status_code = integrator.handle_delete_platform_response(
                success, message, platform_name, **kwargs
            )
        else:
            logger.warning(f"Unknown platform operation type: {operation_type}")
            return False
        
        return response_data.get('success', False)
        
    except Exception as e:
        logger.error(f"Error sending platform operation notification: {e}")
        return False