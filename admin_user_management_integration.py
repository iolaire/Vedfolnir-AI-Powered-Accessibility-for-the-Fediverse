# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin User Management Integration

This module integrates the admin user management system with the unified notification
framework, providing real-time notifications for user operations via WebSocket.
"""

import logging
from typing import Dict, Any, Optional
from flask import Flask

from unified_notification_manager import UnifiedNotificationManager
from admin_user_management_notification_handler import AdminUserManagementNotificationHandler

logger = logging.getLogger(__name__)


class AdminUserManagementIntegration:
    """
    Integration service for admin user management notifications
    
    Provides seamless integration between admin user management operations
    and the unified notification system for real-time admin notifications.
    """
    
    def __init__(self, notification_manager: UnifiedNotificationManager):
        """
        Initialize admin user management integration
        
        Args:
            notification_manager: Unified notification manager instance
        """
        self.notification_manager = notification_manager
        self.notification_handler = AdminUserManagementNotificationHandler(notification_manager)
        
        logger.info("Admin User Management Integration initialized")
    
    def initialize_app_integration(self, app: Flask) -> Dict[str, Any]:
        """
        Initialize Flask app integration for user management notifications
        
        Args:
            app: Flask application instance
            
        Returns:
            Dictionary containing integration status and configuration
        """
        try:
            # Register notification handler in app config
            app.config['admin_user_management_notification_handler'] = self.notification_handler
            
            # Register integration service
            app.config['admin_user_management_integration'] = self
            
            logger.info("Admin user management notification integration registered with Flask app")
            
            return {
                'success': True,
                'handler_registered': True,
                'integration_active': True,
                'supported_operations': [
                    'user_created',
                    'user_updated', 
                    'user_deleted',
                    'user_role_changed',
                    'user_status_changed',
                    'user_password_reset',
                    'user_permissions_changed'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize app integration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_notification_handler(self) -> AdminUserManagementNotificationHandler:
        """
        Get the notification handler instance
        
        Returns:
            AdminUserManagementNotificationHandler instance
        """
        return self.notification_handler
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get current integration status and statistics
        
        Returns:
            Dictionary containing integration status
        """
        try:
            handler_stats = self.notification_handler.get_notification_stats()
            
            return {
                'integration_active': True,
                'notification_handler_status': 'active',
                'handler_stats': handler_stats,
                'supported_operations': list(self.notification_handler.operation_types.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting integration status: {e}")
            return {
                'integration_active': False,
                'error': str(e)
            }


def create_admin_user_management_integration(
    notification_manager: UnifiedNotificationManager
) -> AdminUserManagementIntegration:
    """
    Factory function to create admin user management integration
    
    Args:
        notification_manager: Unified notification manager instance
        
    Returns:
        AdminUserManagementIntegration instance
    """
    return AdminUserManagementIntegration(notification_manager)


def initialize_admin_user_management_notifications(
    app: Flask, 
    notification_manager: UnifiedNotificationManager
) -> Dict[str, Any]:
    """
    Initialize admin user management notifications for Flask app
    
    Args:
        app: Flask application instance
        notification_manager: Unified notification manager instance
        
    Returns:
        Dictionary containing initialization results
    """
    try:
        # Create integration service
        integration = create_admin_user_management_integration(notification_manager)
        
        # Initialize app integration
        result = integration.initialize_app_integration(app)
        
        if result['success']:
            logger.info("Admin user management notifications initialized successfully")
        else:
            logger.error(f"Failed to initialize admin user management notifications: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error initializing admin user management notifications: {e}")
        return {
            'success': False,
            'error': str(e)
        }