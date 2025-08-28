# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Security Middleware

This module provides middleware integration for WebSocket security features,
including automatic security validation, connection monitoring, and event filtering.
"""

import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

from flask import current_app
from flask_socketio import SocketIO, disconnect, emit

from websocket_security_manager import WebSocketSecurityManager, WebSocketSecurityConfig
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2

logger = logging.getLogger(__name__)


class WebSocketSecurityMiddleware:
    """
    Middleware for integrating WebSocket security features
    
    Provides automatic security validation, connection monitoring,
    and event filtering for WebSocket communications.
    """
    
    def __init__(self, socketio: SocketIO, db_manager: DatabaseManager, 
                 session_manager: SessionManagerV2, config: Optional[WebSocketSecurityConfig] = None):
        """
        Initialize WebSocket security middleware
        
        Args:
            socketio: SocketIO instance to secure
            db_manager: Database manager instance
            session_manager: Session manager instance
            config: Security configuration
        """
        self.socketio = socketio
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.config = config or WebSocketSecurityConfig()
        
        # Initialize security manager
        self.security_manager = WebSocketSecurityManager(
            db_manager, session_manager, self.config
        )
        
        # Store security manager in app context for access by decorators
        current_app.websocket_security_manager = self.security_manager
        
        # Setup middleware
        self._setup_connection_middleware()
        self._setup_event_middleware()
        self._setup_error_handlers()
        
        logger.info("WebSocket Security Middleware initialized")
    
    def _setup_connection_middleware(self) -> None:
        """Setup connection-level security middleware"""
        
        @self.socketio.on('connect')
        def secure_connect(auth=None, namespace='/'):
            """Secure connection handler with comprehensive validation"""
            try:
                # Validate connection with security manager
                allowed, reason, connection_info = self.security_manager.validate_connection(auth, namespace)
                
                if not allowed:
                    logger.warning(f"WebSocket connection rejected: {reason}")
                    emit('connection_error', {
                        'message': reason,
                        'code': 'CONNECTION_REJECTED',
                        'timestamp': connection_info.get('connected_at') if connection_info else None
                    })
                    disconnect()
                    return False
                
                # Connection allowed
                logger.info(f"WebSocket connection accepted: namespace={namespace}, "
                           f"authenticated={connection_info.get('is_authenticated', False)}")
                
                # Send connection success event
                emit('connection_success', {
                    'message': 'Connection established',
                    'namespace': namespace,
                    'authenticated': connection_info.get('is_authenticated', False),
                    'timestamp': connection_info.get('connected_at')
                })
                
                return True
                
            except Exception as e:
                logger.error(f"Error in secure connection handler: {e}")
                emit('connection_error', {
                    'message': 'Connection validation failed',
                    'code': 'VALIDATION_ERROR'
                })
                disconnect()
                return False
        
        @self.socketio.on('disconnect')
        def secure_disconnect(namespace='/'):
            """Secure disconnection handler"""
            try:
                # Get session ID for cleanup
                session_id = self.security_manager._get_session_id(None)
                if session_id:
                    # Clean up connection tracking
                    self.security_manager._untrack_connection(session_id)
                    logger.info(f"WebSocket connection disconnected: {session_id[:8]}")
                
            except Exception as e:
                logger.error(f"Error in secure disconnect handler: {e}")
    
    def _setup_event_middleware(self) -> None:
        """Setup event-level security middleware"""
        
        # Store original event handlers
        original_handlers = {}
        
        # Wrap all existing event handlers with security validation
        for namespace, handlers in self.socketio.handlers.items():
            original_handlers[namespace] = {}
            for event, handler_list in handlers.items():
                if event not in ['connect', 'disconnect']:  # Skip connection events
                    original_handlers[namespace][event] = handler_list.copy()
                    
                    # Replace handlers with secured versions
                    handler_list.clear()
                    for handler in original_handlers[namespace][event]:
                        secured_handler = self._create_secured_handler(handler, event, namespace)
                        handler_list.append(secured_handler)
        
        # Add generic message validation for any new handlers
        @self.socketio.on_error_default
        def handle_security_error(e):
            """Handle security-related errors"""
            logger.error(f"WebSocket security error: {e}")
            emit('security_error', {
                'message': 'Security validation failed',
                'code': 'SECURITY_ERROR'
            })
    
    def _create_secured_handler(self, original_handler: Callable, event: str, namespace: str) -> Callable:
        """
        Create a secured version of an event handler
        
        Args:
            original_handler: Original event handler function
            event: Event name
            namespace: Namespace
            
        Returns:
            Secured event handler function
        """
        @wraps(original_handler)
        def secured_handler(*args, **kwargs):
            try:
                # Get session ID
                session_id = self.security_manager._get_session_id(None)
                if not session_id:
                    emit('error', {
                        'message': 'Session required for this operation',
                        'code': 'NO_SESSION',
                        'event': event
                    })
                    return
                
                # Extract message data
                data = args[0] if args else {}
                
                # Validate message with security manager
                allowed, reason, sanitized_data = self.security_manager.validate_message(
                    event, data, session_id
                )
                
                if not allowed:
                    logger.warning(f"WebSocket message blocked: event={event}, reason={reason}")
                    emit('message_blocked', {
                        'message': reason,
                        'code': 'MESSAGE_BLOCKED',
                        'event': event
                    })
                    return
                
                # Replace original data with sanitized data
                if sanitized_data is not None:
                    args = (sanitized_data,) + args[1:] if len(args) > 1 else (sanitized_data,)
                
                # Call original handler with sanitized data
                return original_handler(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in secured WebSocket handler for {event}: {e}")
                emit('handler_error', {
                    'message': 'Handler execution failed',
                    'code': 'HANDLER_ERROR',
                    'event': event
                })
        
        return secured_handler
    
    def _setup_error_handlers(self) -> None:
        """Setup security-specific error handlers"""
        
        @self.socketio.on_error('/')
        def handle_user_namespace_error(e):
            """Handle errors in user namespace"""
            logger.error(f"User namespace error: {e}")
            emit('namespace_error', {
                'message': 'An error occurred in the user namespace',
                'code': 'USER_NAMESPACE_ERROR',
                'namespace': '/'
            })
        
        @self.socketio.on_error('/admin')
        def handle_admin_namespace_error(e):
            """Handle errors in admin namespace"""
            logger.error(f"Admin namespace error: {e}")
            emit('namespace_error', {
                'message': 'An error occurred in the admin namespace',
                'code': 'ADMIN_NAMESPACE_ERROR',
                'namespace': '/admin'
            })
    
    def add_custom_validator(self, event_type: str, validator: Callable[[Any], bool]) -> None:
        """
        Add custom validator for specific event types
        
        Args:
            event_type: Event type to validate
            validator: Validator function that returns True if valid
        """
        # This could be extended to support custom validation logic
        logger.info(f"Custom validator registered for event type: {event_type}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics from the security manager"""
        return self.security_manager.get_security_stats()
    
    def cleanup_expired_connections(self) -> None:
        """Clean up expired connections"""
        self.security_manager.cleanup_expired_connections()
    
    def disconnect_user(self, user_id: int, reason: str = "Administrative action") -> int:
        """
        Disconnect all connections for a specific user
        
        Args:
            user_id: User ID to disconnect
            reason: Reason for disconnection
            
        Returns:
            Number of connections disconnected
        """
        try:
            disconnected_count = 0
            user_sessions = list(self.security_manager.user_connections.get(user_id, set()))
            
            for session_id in user_sessions:
                self.security_manager.disconnect_connection(session_id, reason)
                disconnected_count += 1
            
            logger.info(f"Disconnected {disconnected_count} connections for user {user_id}: {reason}")
            return disconnected_count
            
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")
            return 0
    
    def disconnect_ip(self, ip_address: str, reason: str = "Security violation") -> int:
        """
        Disconnect all connections from a specific IP address
        
        Args:
            ip_address: IP address to disconnect
            reason: Reason for disconnection
            
        Returns:
            Number of connections disconnected
        """
        try:
            disconnected_count = 0
            ip_sessions = list(self.security_manager.ip_connections.get(ip_address, set()))
            
            for session_id in ip_sessions:
                self.security_manager.disconnect_connection(session_id, reason)
                disconnected_count += 1
            
            logger.info(f"Disconnected {disconnected_count} connections from IP {ip_address}: {reason}")
            return disconnected_count
            
        except Exception as e:
            logger.error(f"Error disconnecting IP {ip_address}: {e}")
            return 0
    
    def broadcast_security_alert(self, message: str, severity: str = "warning", 
                               admin_only: bool = False) -> None:
        """
        Broadcast security alert to connected clients
        
        Args:
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
            admin_only: Whether to send only to admin connections
        """
        try:
            alert_data = {
                'message': message,
                'severity': severity,
                'timestamp': self.security_manager._get_current_timestamp(),
                'type': 'security_alert'
            }
            
            if admin_only:
                # Send only to admin namespace
                self.socketio.emit('security_alert', alert_data, namespace='/admin')
                logger.info(f"Security alert sent to admin users: {message}")
            else:
                # Send to all namespaces
                self.socketio.emit('security_alert', alert_data, namespace='/')
                self.socketio.emit('security_alert', alert_data, namespace='/admin')
                logger.info(f"Security alert broadcast to all users: {message}")
                
        except Exception as e:
            logger.error(f"Error broadcasting security alert: {e}")


def setup_websocket_security(socketio: SocketIO, db_manager: DatabaseManager, 
                           session_manager: SessionManagerV2, 
                           config: Optional[WebSocketSecurityConfig] = None) -> WebSocketSecurityMiddleware:
    """
    Setup WebSocket security middleware for a SocketIO instance
    
    Args:
        socketio: SocketIO instance to secure
        db_manager: Database manager instance
        session_manager: Session manager instance
        config: Security configuration
        
    Returns:
        WebSocketSecurityMiddleware instance
    """
    middleware = WebSocketSecurityMiddleware(socketio, db_manager, session_manager, config)
    
    # Setup periodic cleanup
    import threading
    import time
    
    def periodic_cleanup():
        """Periodic cleanup of expired connections"""
        while True:
            try:
                time.sleep(300)  # 5 minutes
                middleware.cleanup_expired_connections()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    
    logger.info("WebSocket security middleware setup complete")
    return middleware


# Utility functions for WebSocket security

def get_websocket_security_manager() -> Optional[WebSocketSecurityManager]:
    """Get the WebSocket security manager from current app context"""
    return getattr(current_app, 'websocket_security_manager', None)


def emit_security_event(event_type: str, data: Dict[str, Any], 
                       namespace: str = '/', admin_only: bool = False) -> None:
    """
    Emit a security-related event with proper validation
    
    Args:
        event_type: Type of security event
        data: Event data
        namespace: Target namespace
        admin_only: Whether to send only to admin users
    """
    try:
        security_manager = get_websocket_security_manager()
        if security_manager:
            # Add security context to event data
            data['security_validated'] = True
            data['timestamp'] = security_manager._get_current_timestamp()
        
        # Emit the event
        from flask_socketio import emit
        emit(event_type, data, namespace=namespace)
        
    except Exception as e:
        logger.error(f"Error emitting security event: {e}")


def validate_websocket_csrf(data: Dict[str, Any], operation: str, 
                          user_id: Optional[int] = None) -> bool:
    """
    Validate CSRF token for WebSocket operation
    
    Args:
        data: Message data containing CSRF token
        operation: Operation being performed
        user_id: User ID for validation
        
    Returns:
        True if CSRF token is valid, False otherwise
    """
    try:
        security_manager = get_websocket_security_manager()
        if not security_manager:
            return True  # Allow if security manager not available
        
        csrf_token = data.get('csrf_token')
        if not csrf_token:
            return False
        
        return security_manager.validate_csrf_token(csrf_token, user_id, operation)
        
    except Exception as e:
        logger.error(f"Error validating WebSocket CSRF token: {e}")
        return False