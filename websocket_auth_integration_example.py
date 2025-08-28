# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Authentication Integration Example

This example demonstrates how to integrate the WebSocket Authentication Handler
with the existing WebSocket Factory and other components to create a complete
WebSocket authentication system.
"""

import logging
from flask import Flask
from flask_socketio import SocketIO, emit, disconnect

# Import the WebSocket components
from config import Config
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2
from redis_session_backend import RedisSessionBackend
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler, AuthenticationResult

logger = logging.getLogger(__name__)


def create_authenticated_websocket_app():
    """
    Create a Flask application with authenticated WebSocket support
    
    Returns:
        Tuple of (Flask app, SocketIO instance, WebSocket auth handler)
    """
    # Initialize Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # Initialize core components
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Initialize Redis session backend
    redis_backend = RedisSessionBackend(
        host='localhost',
        port=6379,
        db=0,
        password=None
    )
    
    # Initialize session manager
    session_manager = SessionManagerV2(db_manager, redis_backend)
    
    # Initialize WebSocket components
    ws_config_manager = WebSocketConfigManager(config)
    cors_manager = CORSManager(ws_config_manager)
    ws_factory = WebSocketFactory(ws_config_manager, cors_manager)
    
    # Initialize authentication handler
    auth_handler = WebSocketAuthHandler(
        db_manager=db_manager,
        session_manager=session_manager,
        rate_limit_window=300,  # 5 minutes
        max_attempts_per_window=10,
        max_attempts_per_ip=50
    )
    
    # Create SocketIO instance
    socketio = ws_factory.create_socketio_instance(app)
    
    # Setup authenticated event handlers
    setup_authenticated_handlers(socketio, auth_handler)
    
    return app, socketio, auth_handler


def setup_authenticated_handlers(socketio: SocketIO, auth_handler: WebSocketAuthHandler):
    """
    Setup authenticated WebSocket event handlers
    
    Args:
        socketio: SocketIO instance
        auth_handler: WebSocket authentication handler
    """
    
    @socketio.on('connect', namespace='/')
    def handle_user_connect(auth=None):
        """Handle user namespace connection with authentication"""
        try:
            logger.info("User attempting to connect to WebSocket")
            
            # Authenticate the connection
            result, auth_context = auth_handler.authenticate_connection(auth, namespace='/')
            
            if result != AuthenticationResult.SUCCESS:
                logger.warning(f"User connection authentication failed: {result.value}")
                auth_handler.handle_authentication_failure(result, namespace='/')
                return False
            
            logger.info(f"User {auth_context.username} connected successfully")
            
            # Send welcome message with user context
            emit('connection_success', {
                'message': 'Connected successfully',
                'user': {
                    'username': auth_context.username,
                    'role': auth_context.role.value,
                    'permissions': auth_context.permissions
                },
                'platform': {
                    'id': auth_context.platform_connection_id,
                    'name': auth_context.platform_name,
                    'type': auth_context.platform_type
                } if auth_context.platform_connection_id else None
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error in user connect handler: {e}")
            return False
    
    @socketio.on('connect', namespace='/admin')
    def handle_admin_connect(auth=None):
        """Handle admin namespace connection with authentication and authorization"""
        try:
            logger.info("Admin attempting to connect to WebSocket")
            
            # Authenticate the connection
            result, auth_context = auth_handler.authenticate_connection(auth, namespace='/admin')
            
            if result != AuthenticationResult.SUCCESS:
                logger.warning(f"Admin connection authentication failed: {result.value}")
                auth_handler.handle_authentication_failure(result, namespace='/admin')
                return False
            
            # Check admin authorization
            if not auth_handler.authorize_admin_access(auth_context):
                logger.warning(f"Admin authorization failed for user {auth_context.username}")
                auth_handler.handle_authentication_failure(
                    AuthenticationResult.INSUFFICIENT_PRIVILEGES, 
                    namespace='/admin'
                )
                return False
            
            logger.info(f"Admin {auth_context.username} connected successfully")
            
            # Send admin welcome message
            emit('admin_connection_success', {
                'message': 'Admin connected successfully',
                'user': {
                    'username': auth_context.username,
                    'role': auth_context.role.value,
                    'permissions': auth_context.permissions
                },
                'admin_features': {
                    'system_management': 'system_management' in auth_context.permissions,
                    'user_management': 'user_management' in auth_context.permissions,
                    'security_monitoring': 'security_monitoring' in auth_context.permissions
                }
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error in admin connect handler: {e}")
            return False
    
    @socketio.on('disconnect', namespace='/')
    def handle_user_disconnect():
        """Handle user disconnection"""
        logger.info("User disconnected from WebSocket")
    
    @socketio.on('disconnect', namespace='/admin')
    def handle_admin_disconnect():
        """Handle admin disconnection"""
        logger.info("Admin disconnected from WebSocket")
    
    @socketio.on('ping', namespace='/')
    def handle_user_ping(data):
        """Handle user ping with session validation"""
        try:
            # Extract session info from the ping data or Flask session
            session_id = data.get('session_id') if data else None
            user_id = data.get('user_id') if data else None
            
            if session_id and user_id:
                # Validate session is still active
                if auth_handler.validate_user_session(user_id, session_id):
                    emit('pong', {'status': 'ok', 'timestamp': data.get('timestamp')})
                else:
                    emit('session_expired', {'message': 'Session has expired'})
                    disconnect()
            else:
                emit('pong', {'status': 'ok'})
                
        except Exception as e:
            logger.error(f"Error in user ping handler: {e}")
            emit('error', {'message': 'Ping failed'})
    
    @socketio.on('admin_action', namespace='/admin')
    def handle_admin_action(data):
        """Handle admin actions with permission checking"""
        try:
            # This would need to extract auth context from the connection
            # For demonstration, we'll show the permission checking pattern
            
            action = data.get('action')
            required_permission = {
                'system_restart': 'system_management',
                'user_management': 'user_management',
                'view_logs': 'security_monitoring'
            }.get(action)
            
            # In a real implementation, you'd get the auth context from the connection
            # For now, we'll emit a response showing the pattern
            emit('admin_action_response', {
                'action': action,
                'status': 'permission_check_required',
                'required_permission': required_permission,
                'message': f'Action {action} requires {required_permission} permission'
            })
            
        except Exception as e:
            logger.error(f"Error in admin action handler: {e}")
            emit('error', {'message': 'Admin action failed'})


def demo_authentication_stats(auth_handler: WebSocketAuthHandler):
    """
    Demonstrate authentication statistics monitoring
    
    Args:
        auth_handler: WebSocket authentication handler
    """
    print("\n=== WebSocket Authentication Statistics ===")
    
    stats = auth_handler.get_authentication_stats()
    
    print(f"Rate Limit Window: {stats['rate_limit_window_seconds']} seconds")
    print(f"Max Attempts per User: {stats['max_attempts_per_user']}")
    print(f"Max Attempts per IP: {stats['max_attempts_per_ip']}")
    print(f"Active Users in Window: {stats['active_users_in_window']}")
    print(f"Active IPs in Window: {stats['active_ips_in_window']}")
    print(f"Security Events in Window: {stats['security_events_in_window']}")
    
    if stats['security_event_types']:
        print("\nSecurity Event Types:")
        for event_type, count in stats['security_event_types'].items():
            print(f"  - {event_type}: {count}")
    
    print(f"Total Connection Sessions: {stats['total_connection_sessions']}")


def demo_permission_system(auth_handler: WebSocketAuthHandler):
    """
    Demonstrate the permission system
    
    Args:
        auth_handler: WebSocket authentication handler
    """
    print("\n=== WebSocket Permission System ===")
    
    from models import UserRole
    
    roles = [UserRole.ADMIN, UserRole.MODERATOR, UserRole.REVIEWER, UserRole.VIEWER]
    
    for role in roles:
        permissions = auth_handler.get_user_permissions(role)
        print(f"\n{role.value.upper()} permissions:")
        if permissions:
            for permission in permissions:
                print(f"  - {permission}")
        else:
            print("  - No special permissions")


if __name__ == '__main__':
    """
    Run the WebSocket authentication integration example
    """
    print("WebSocket Authentication Integration Example")
    print("=" * 50)
    
    try:
        # Create authenticated WebSocket app
        app, socketio, auth_handler = create_authenticated_websocket_app()
        
        # Demonstrate authentication statistics
        demo_authentication_stats(auth_handler)
        
        # Demonstrate permission system
        demo_permission_system(auth_handler)
        
        print("\n=== Integration Complete ===")
        print("WebSocket authentication handler successfully integrated!")
        print("\nKey Features Implemented:")
        print("✓ Session-based authentication")
        print("✓ Role-based authorization")
        print("✓ Admin privilege verification")
        print("✓ Rate limiting (user and IP-based)")
        print("✓ Security event logging")
        print("✓ Namespace separation (user vs admin)")
        print("✓ Permission-based access control")
        print("✓ Authentication statistics monitoring")
        
        print("\nTo run the WebSocket server:")
        print("socketio.run(app, host='127.0.0.1', port=5000, debug=True)")
        
    except Exception as e:
        logger.error(f"Error in WebSocket authentication integration: {e}")
        print(f"Integration failed: {e}")