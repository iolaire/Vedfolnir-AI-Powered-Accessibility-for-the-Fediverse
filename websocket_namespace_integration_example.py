# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Namespace Integration Example

This example demonstrates how to integrate the WebSocket namespace manager
with the WebSocket factory and authentication handler to create a complete
WebSocket system with user and admin separation.
"""

import logging
from flask import Flask
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_websocket_system():
    """
    Create a complete WebSocket system with namespace management
    
    Returns:
        Tuple of (Flask app, SocketIO instance, namespace manager)
    """
    try:
        # Create Flask app
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'your-secret-key-here'
        
        # Initialize configuration and dependencies
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = SessionManagerV2(db_manager)
        
        # Create WebSocket components
        config_manager = WebSocketConfigManager(config)
        cors_manager = CORSManager(config_manager)
        auth_handler = WebSocketAuthHandler(db_manager, session_manager)
        
        # Create WebSocket factory
        websocket_factory = WebSocketFactory(config_manager, cors_manager)
        
        # Create SocketIO instance
        socketio = websocket_factory.create_socketio_instance(app)
        
        # Create namespace manager
        namespace_manager = WebSocketNamespaceManager(socketio, auth_handler)
        
        logger.info("WebSocket system created successfully")
        return app, socketio, namespace_manager
        
    except Exception as e:
        logger.error(f"Failed to create WebSocket system: {e}")
        raise


def register_custom_event_handlers(namespace_manager):
    """
    Register custom event handlers for user and admin namespaces
    
    Args:
        namespace_manager: WebSocket namespace manager instance
    """
    try:
        # User namespace event handlers
        user_handlers = {
            'caption_progress': handle_caption_progress,
            'platform_status': handle_platform_status,
            'user_activity': handle_user_activity
        }
        
        namespace_manager.register_event_handlers('/', user_handlers)
        
        # Admin namespace event handlers
        admin_handlers = {
            'system_status': handle_system_status,
            'user_management': handle_user_management,
            'maintenance_operations': handle_maintenance_operations
        }
        
        namespace_manager.register_event_handlers('/admin', admin_handlers)
        
        logger.info("Custom event handlers registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register event handlers: {e}")
        raise


def handle_caption_progress(data):
    """Handle caption generation progress updates"""
    try:
        logger.info(f"Caption progress update: {data}")
        
        # Process caption progress data
        progress = data.get('progress', 0)
        caption_id = data.get('caption_id')
        
        # Broadcast progress to relevant users
        # Implementation would depend on specific requirements
        
        return {'success': True, 'progress': progress}
        
    except Exception as e:
        logger.error(f"Error handling caption progress: {e}")
        return {'success': False, 'error': str(e)}


def handle_platform_status(data):
    """Handle platform status updates"""
    try:
        logger.info(f"Platform status update: {data}")
        
        # Process platform status data
        platform_id = data.get('platform_id')
        status = data.get('status')
        
        # Update platform status and notify users
        # Implementation would depend on specific requirements
        
        return {'success': True, 'status': status}
        
    except Exception as e:
        logger.error(f"Error handling platform status: {e}")
        return {'success': False, 'error': str(e)}


def handle_user_activity(data):
    """Handle user activity events"""
    try:
        logger.info(f"User activity: {data}")
        
        # Process user activity data
        activity_type = data.get('activity_type')
        activity_data = data.get('activity_data', {})
        
        # Log user activity and broadcast to relevant users
        # Implementation would depend on specific requirements
        
        return {'success': True, 'activity_logged': True}
        
    except Exception as e:
        logger.error(f"Error handling user activity: {e}")
        return {'success': False, 'error': str(e)}


def handle_system_status(data):
    """Handle system status requests (admin only)"""
    try:
        logger.info(f"System status request: {data}")
        
        # Get system status information
        status_type = data.get('status_type', 'general')
        
        # Collect system status data
        system_status = {
            'cpu_usage': 45.2,  # Example data
            'memory_usage': 67.8,
            'active_connections': 150,
            'processing_queue': 23
        }
        
        return {'success': True, 'system_status': system_status}
        
    except Exception as e:
        logger.error(f"Error handling system status: {e}")
        return {'success': False, 'error': str(e)}


def handle_user_management(data):
    """Handle user management operations (admin only)"""
    try:
        logger.info(f"User management operation: {data}")
        
        # Process user management request
        operation = data.get('operation')
        user_id = data.get('user_id')
        
        # Perform user management operation
        # Implementation would depend on specific requirements
        
        return {'success': True, 'operation': operation, 'user_id': user_id}
        
    except Exception as e:
        logger.error(f"Error handling user management: {e}")
        return {'success': False, 'error': str(e)}


def handle_maintenance_operations(data):
    """Handle maintenance operations (admin only)"""
    try:
        logger.info(f"Maintenance operation: {data}")
        
        # Process maintenance request
        operation_type = data.get('operation_type')
        parameters = data.get('parameters', {})
        
        # Perform maintenance operation
        # Implementation would depend on specific requirements
        
        return {'success': True, 'operation_type': operation_type}
        
    except Exception as e:
        logger.error(f"Error handling maintenance operation: {e}")
        return {'success': False, 'error': str(e)}


def setup_room_management(namespace_manager):
    """
    Set up custom rooms for different purposes
    
    Args:
        namespace_manager: WebSocket namespace manager instance
    """
    try:
        # Create user-specific rooms
        namespace_manager.create_room('caption_updates', '/', 'updates', 0, {
            'description': 'Caption generation updates',
            'auto_join': True
        })
        
        namespace_manager.create_room('platform_notifications', '/', 'notifications', 0, {
            'description': 'Platform-specific notifications',
            'auto_join': False
        })
        
        # Create admin-specific rooms
        namespace_manager.create_room('system_alerts', '/admin', 'alerts', 0, {
            'description': 'Critical system alerts',
            'auto_join': True
        })
        
        namespace_manager.create_room('maintenance_coordination', '/admin', 'coordination', 0, {
            'description': 'Maintenance operation coordination',
            'auto_join': False
        })
        
        logger.info("Custom rooms created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create custom rooms: {e}")
        raise


def demonstrate_broadcasting(namespace_manager):
    """
    Demonstrate different broadcasting capabilities
    
    Args:
        namespace_manager: WebSocket namespace manager instance
    """
    try:
        # Broadcast to all users in user namespace
        namespace_manager.broadcast_to_namespace('/', 'system_announcement', {
            'message': 'System maintenance scheduled for tonight',
            'priority': 'medium',
            'timestamp': '2025-08-27T10:00:00Z'
        })
        
        # Broadcast to specific room
        namespace_manager.broadcast_to_room('caption_updates', 'batch_complete', {
            'batch_id': 'batch_123',
            'processed_count': 50,
            'success_count': 48,
            'error_count': 2
        })
        
        # Broadcast to admin namespace only
        namespace_manager.broadcast_to_namespace('/admin', 'admin_alert', {
            'alert_type': 'performance',
            'message': 'High CPU usage detected',
            'severity': 'warning'
        })
        
        logger.info("Broadcasting demonstrations completed")
        
    except Exception as e:
        logger.error(f"Error during broadcasting demonstration: {e}")


def get_system_statistics(namespace_manager):
    """
    Get comprehensive system statistics
    
    Args:
        namespace_manager: WebSocket namespace manager instance
        
    Returns:
        Dictionary containing system statistics
    """
    try:
        # Get manager status
        manager_status = namespace_manager.get_manager_status()
        
        # Get namespace-specific stats
        user_stats = namespace_manager.get_namespace_stats('/')
        admin_stats = namespace_manager.get_namespace_stats('/admin')
        
        return {
            'manager_status': manager_status,
            'user_namespace': user_stats,
            'admin_namespace': admin_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting system statistics: {e}")
        return {'error': str(e)}


def main():
    """
    Main function demonstrating the complete WebSocket namespace system
    """
    try:
        logger.info("Starting WebSocket namespace integration example")
        
        # Create WebSocket system
        app, socketio, namespace_manager = create_websocket_system()
        
        # Register custom event handlers
        register_custom_event_handlers(namespace_manager)
        
        # Set up custom rooms
        setup_room_management(namespace_manager)
        
        # Demonstrate broadcasting capabilities
        demonstrate_broadcasting(namespace_manager)
        
        # Get and display system statistics
        stats = get_system_statistics(namespace_manager)
        logger.info(f"System statistics: {stats}")
        
        logger.info("WebSocket namespace integration example completed successfully")
        
        # In a real application, you would start the Flask-SocketIO server here:
        # socketio.run(app, host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == '__main__':
    main()