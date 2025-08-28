# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Error Handler

This module provides comprehensive error handling for WebSocket connections,
integrating with the error detection system to provide actionable responses.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from flask_socketio import SocketIO, emit, disconnect
from flask import request, session

from websocket_error_detector import (
    WebSocketErrorDetector, 
    WebSocketErrorInfo, 
    WebSocketErrorCategory,
    WebSocketErrorSeverity
)


class WebSocketErrorHandler:
    """
    Comprehensive error handler for WebSocket connections
    
    This class provides:
    - Integration with error detection system
    - Automatic error response generation
    - Client notification and recovery guidance
    - Error logging and monitoring
    - Fallback mechanisms for different error types
    """
    
    def __init__(self, socketio: SocketIO, error_detector: Optional[WebSocketErrorDetector] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler
        
        Args:
            socketio: SocketIO instance for error communication
            error_detector: Error detection system
            logger: Logger for error reporting
        """
        self.socketio = socketio
        self.error_detector = error_detector or WebSocketErrorDetector()
        self.logger = logger or logging.getLogger(__name__)
        
        # Error handling callbacks
        self._error_callbacks: Dict[WebSocketErrorCategory, List[Callable]] = {}
        
        # Recovery strategies
        self._recovery_strategies: Dict[WebSocketErrorCategory, Callable] = {}
        
        # Initialize default recovery strategies
        self._initialize_recovery_strategies()
        
        # Setup SocketIO error handlers
        self._setup_socketio_handlers()
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, namespace: str = '/') -> WebSocketErrorInfo:
        """
        Handle a WebSocket error comprehensively
        
        Args:
            error: Exception that occurred
            context: Additional context information
            namespace: SocketIO namespace where error occurred
            
        Returns:
            WebSocketErrorInfo: Processed error information
        """
        # Detect and categorize the error
        error_info = self.error_detector.detect_error(error, context)
        
        # Add handler context
        error_info.context.update({
            'namespace': namespace,
            'handler': 'WebSocketErrorHandler',
            'client_id': request.sid if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        })
        
        # Execute error callbacks
        self._execute_error_callbacks(error_info)
        
        # Attempt recovery
        self._attempt_recovery(error_info, namespace)
        
        # Notify client
        self._notify_client(error_info, namespace)
        
        # Log for monitoring
        self._log_error_for_monitoring(error_info)
        
        return error_info
    
    def handle_cors_error(self, origin: str, allowed_origins: List[str], namespace: str = '/') -> WebSocketErrorInfo:
        """
        Handle CORS-specific errors
        
        Args:
            origin: Request origin that failed validation
            allowed_origins: List of allowed origins
            namespace: SocketIO namespace
            
        Returns:
            WebSocketErrorInfo: CORS error information
        """
        # Detect CORS error
        error_info = self.error_detector.detect_cors_error(origin, allowed_origins)
        
        # Add CORS-specific context
        error_info.context.update({
            'namespace': namespace,
            'error_type': 'cors_validation',
            'client_id': request.sid if request else None
        })
        
        # CORS-specific recovery
        self._handle_cors_recovery(error_info, namespace)
        
        # Notify client with CORS-specific guidance
        self._notify_cors_error(error_info, namespace)
        
        return error_info
    
    def handle_authentication_error(self, user_id: Optional[int], session_data: Optional[Dict], namespace: str = '/') -> WebSocketErrorInfo:
        """
        Handle authentication-specific errors
        
        Args:
            user_id: User ID if available
            session_data: Session information
            namespace: SocketIO namespace
            
        Returns:
            WebSocketErrorInfo: Authentication error information
        """
        # Detect authentication error
        error_info = self.error_detector.detect_authentication_error(user_id, session_data)
        
        # Add authentication-specific context
        error_info.context.update({
            'namespace': namespace,
            'error_type': 'authentication_failure',
            'client_id': request.sid if request else None,
            'session_id': session.get('session_id') if session else None
        })
        
        # Authentication-specific recovery
        self._handle_auth_recovery(error_info, namespace)
        
        # Notify client with authentication guidance
        self._notify_auth_error(error_info, namespace)
        
        return error_info
    
    def handle_connection_error(self, connection_info: Dict, namespace: str = '/') -> WebSocketErrorInfo:
        """
        Handle connection and network errors
        
        Args:
            connection_info: Connection details
            namespace: SocketIO namespace
            
        Returns:
            WebSocketErrorInfo: Connection error information
        """
        # Detect network error
        error_info = self.error_detector.detect_network_error(connection_info)
        
        # Add connection-specific context
        error_info.context.update({
            'namespace': namespace,
            'error_type': 'connection_failure',
            'client_id': request.sid if request else None
        })
        
        # Connection-specific recovery
        self._handle_connection_recovery(error_info, namespace)
        
        # Notify client with connection guidance
        self._notify_connection_error(error_info, namespace)
        
        return error_info
    
    def register_error_callback(self, category: WebSocketErrorCategory, callback: Callable[[WebSocketErrorInfo], None]) -> None:
        """
        Register a callback for specific error categories
        
        Args:
            category: Error category to handle
            callback: Function to call when error occurs
        """
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)
    
    def register_recovery_strategy(self, category: WebSocketErrorCategory, strategy: Callable[[WebSocketErrorInfo, str], bool]) -> None:
        """
        Register a recovery strategy for specific error categories
        
        Args:
            category: Error category to handle
            strategy: Recovery function that returns success status
        """
        self._recovery_strategies[category] = strategy
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return self.error_detector.get_error_statistics()
    
    def _setup_socketio_handlers(self) -> None:
        """Setup SocketIO error handlers"""
        
        @self.socketio.on_error_default
        def default_error_handler(e):
            """Default error handler for all namespaces"""
            try:
                error_info = self.handle_error(e, {'source': 'socketio_default'})
                self.logger.error(f"SocketIO default error [{error_info.error_code}]: {e}")
            except Exception as handler_error:
                self.logger.error(f"Error in default error handler: {handler_error}")
        
        @self.socketio.on_error('/')
        def user_namespace_error_handler(e):
            """Error handler for user namespace"""
            try:
                error_info = self.handle_error(e, {'source': 'user_namespace'}, '/')
                self.logger.error(f"User namespace error [{error_info.error_code}]: {e}")
            except Exception as handler_error:
                self.logger.error(f"Error in user namespace error handler: {handler_error}")
        
        @self.socketio.on_error('/admin')
        def admin_namespace_error_handler(e):
            """Error handler for admin namespace"""
            try:
                error_info = self.handle_error(e, {'source': 'admin_namespace'}, '/admin')
                self.logger.error(f"Admin namespace error [{error_info.error_code}]: {e}")
            except Exception as handler_error:
                self.logger.error(f"Error in admin namespace error handler: {handler_error}")
        
        @self.socketio.on('connect_error')
        def handle_connect_error(data):
            """Handle connection errors"""
            try:
                connection_info = {
                    'host': request.host if request else 'unknown',
                    'user_agent': request.headers.get('User-Agent') if request else None,
                    'error_data': data
                }
                error_info = self.handle_connection_error(connection_info)
                self.logger.warning(f"Connection error [{error_info.error_code}]: {data}")
            except Exception as handler_error:
                self.logger.error(f"Error in connect error handler: {handler_error}")
    
    def _initialize_recovery_strategies(self) -> None:
        """Initialize default recovery strategies"""
        
        def cors_recovery(error_info: WebSocketErrorInfo, namespace: str) -> bool:
            """Recovery strategy for CORS errors"""
            try:
                # Suggest alternative origins or configuration
                suggestions = self.error_detector.get_debugging_suggestions(error_info)
                emit('cors_recovery_suggestions', {
                    'suggestions': suggestions,
                    'error_code': error_info.error_code
                }, namespace=namespace)
                return True
            except Exception:
                return False
        
        def auth_recovery(error_info: WebSocketErrorInfo, namespace: str) -> bool:
            """Recovery strategy for authentication errors"""
            try:
                # Redirect to login or refresh session
                emit('auth_recovery_required', {
                    'action': 'redirect_login',
                    'error_code': error_info.error_code,
                    'message': error_info.user_message
                }, namespace=namespace)
                return True
            except Exception:
                return False
        
        def transport_recovery(error_info: WebSocketErrorInfo, namespace: str) -> bool:
            """Recovery strategy for transport errors"""
            try:
                # Suggest transport fallback
                emit('transport_fallback_suggested', {
                    'fallback_transport': 'polling',
                    'error_code': error_info.error_code,
                    'instructions': 'Switching to polling transport for better compatibility'
                }, namespace=namespace)
                return True
            except Exception:
                return False
        
        def network_recovery(error_info: WebSocketErrorInfo, namespace: str) -> bool:
            """Recovery strategy for network errors"""
            try:
                # Suggest retry with backoff
                emit('network_recovery_suggested', {
                    'action': 'retry_with_backoff',
                    'error_code': error_info.error_code,
                    'retry_delay': 5000,  # 5 seconds
                    'max_retries': 3
                }, namespace=namespace)
                return True
            except Exception:
                return False
        
        # Register default strategies
        self._recovery_strategies[WebSocketErrorCategory.CORS] = cors_recovery
        self._recovery_strategies[WebSocketErrorCategory.AUTHENTICATION] = auth_recovery
        self._recovery_strategies[WebSocketErrorCategory.AUTHORIZATION] = auth_recovery
        self._recovery_strategies[WebSocketErrorCategory.TRANSPORT] = transport_recovery
        self._recovery_strategies[WebSocketErrorCategory.NETWORK] = network_recovery
    
    def _execute_error_callbacks(self, error_info: WebSocketErrorInfo) -> None:
        """Execute registered callbacks for error category"""
        callbacks = self._error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in callback for {error_info.category}: {e}")
    
    def _attempt_recovery(self, error_info: WebSocketErrorInfo, namespace: str) -> bool:
        """Attempt recovery using registered strategies"""
        strategy = self._recovery_strategies.get(error_info.category)
        if strategy:
            try:
                return strategy(error_info, namespace)
            except Exception as e:
                self.logger.error(f"Error in recovery strategy for {error_info.category}: {e}")
        return False
    
    def _notify_client(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Send error notification to client"""
        try:
            emit('websocket_error', {
                'error_code': error_info.error_code,
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'message': error_info.user_message,
                'timestamp': error_info.timestamp.isoformat(),
                'recovery_suggestions': self.error_detector.get_debugging_suggestions(error_info)[:3]  # Limit suggestions
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to notify client of error: {e}")
    
    def _handle_cors_recovery(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Handle CORS-specific recovery"""
        try:
            # Extract CORS analysis from debug info
            cors_analysis = error_info.debug_info.get('cors_analysis', {})
            
            emit('cors_error_details', {
                'error_code': error_info.error_code,
                'origin_provided': cors_analysis.get('origin_provided', False),
                'origin_allowed': cors_analysis.get('origin_in_allowed_list', False),
                'suggested_origins': cors_analysis.get('suggested_origins', []),
                'troubleshooting_steps': [
                    'Check if you\'re accessing from the correct URL',
                    'Verify CORS configuration on server',
                    'Try refreshing the page',
                    'Contact support if issue persists'
                ]
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to handle CORS recovery: {e}")
    
    def _notify_cors_error(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Send CORS-specific error notification"""
        try:
            emit('cors_error', {
                'error_code': error_info.error_code,
                'message': error_info.user_message,
                'debug_mode': self.logger.isEnabledFor(logging.DEBUG),
                'timestamp': error_info.timestamp.isoformat()
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to notify CORS error: {e}")
    
    def _handle_auth_recovery(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Handle authentication-specific recovery"""
        try:
            # Extract authentication analysis
            auth_analysis = error_info.debug_info.get('auth_analysis', {})
            
            emit('auth_error_details', {
                'error_code': error_info.error_code,
                'user_id_provided': auth_analysis.get('user_id_provided', False),
                'session_available': auth_analysis.get('session_data_available', False),
                'auth_method': auth_analysis.get('authentication_method', 'unknown'),
                'recovery_actions': [
                    'Please log in again',
                    'Clear browser cache if issue persists',
                    'Check if cookies are enabled',
                    'Contact support if problem continues'
                ]
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to handle auth recovery: {e}")
    
    def _notify_auth_error(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Send authentication-specific error notification"""
        try:
            emit('auth_error', {
                'error_code': error_info.error_code,
                'message': error_info.user_message,
                'action_required': 'login',
                'timestamp': error_info.timestamp.isoformat()
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to notify auth error: {e}")
    
    def _handle_connection_recovery(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Handle connection-specific recovery"""
        try:
            # Extract network analysis
            network_analysis = error_info.debug_info.get('network_analysis', {})
            
            emit('connection_error_details', {
                'error_code': error_info.error_code,
                'host': network_analysis.get('host'),
                'port': network_analysis.get('port'),
                'protocol': network_analysis.get('protocol'),
                'transport': network_analysis.get('transport'),
                'recovery_steps': [
                    'Check your internet connection',
                    'Try refreshing the page',
                    'Switch to a different network if available',
                    'Contact support if problem persists'
                ]
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to handle connection recovery: {e}")
    
    def _notify_connection_error(self, error_info: WebSocketErrorInfo, namespace: str) -> None:
        """Send connection-specific error notification"""
        try:
            emit('connection_error', {
                'error_code': error_info.error_code,
                'message': error_info.user_message,
                'retry_suggested': True,
                'timestamp': error_info.timestamp.isoformat()
            }, namespace=namespace)
        except Exception as e:
            self.logger.error(f"Failed to notify connection error: {e}")
    
    def _log_error_for_monitoring(self, error_info: WebSocketErrorInfo) -> None:
        """Log error information for monitoring systems"""
        monitoring_data = {
            'error_code': error_info.error_code,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'timestamp': error_info.timestamp.isoformat(),
            'context': error_info.context,
            'client_id': error_info.context.get('client_id'),
            'namespace': error_info.context.get('namespace'),
            'user_agent': error_info.context.get('user_agent')
        }
        
        # Log with structured data for monitoring
        self.logger.info(f"WebSocket error monitoring data", extra={
            'monitoring_data': monitoring_data,
            'error_category': error_info.category.value,
            'error_severity': error_info.severity.value
        })