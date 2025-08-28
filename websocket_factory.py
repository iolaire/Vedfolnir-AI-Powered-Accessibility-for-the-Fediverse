# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Factory

This module provides a factory for creating and configuring Flask-SocketIO instances
with standardized settings, unified configuration, transport management, timeout
configuration, and comprehensive error handling.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from flask import Flask
from flask_socketio import SocketIO, emit
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_security_middleware import WebSocketSecurityMiddleware, WebSocketSecurityConfig

logger = logging.getLogger(__name__)


class WebSocketFactory:
    """
    Factory for creating and configuring Flask-SocketIO instances with standardized settings
    
    Provides unified SocketIO configuration, transport management, timeout configuration,
    namespace setup, comprehensive error handling registration, and integrated security.
    """
    
    def __init__(self, config_manager: WebSocketConfigManager, cors_manager: CORSManager,
                 db_manager=None, session_manager=None, security_config: Optional[WebSocketSecurityConfig] = None):
        """
        Initialize WebSocket factory
        
        Args:
            config_manager: WebSocket configuration manager instance
            cors_manager: CORS manager instance
            db_manager: Database manager for security features (optional)
            session_manager: Session manager for security features (optional)
            security_config: Security configuration (optional)
        """
        self.config_manager = config_manager
        self.cors_manager = cors_manager
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.security_config = security_config
        self.logger = logging.getLogger(__name__)
        self._error_handlers = {}
        self._namespace_handlers = {}
        self._middleware_functions = []
        self._security_middleware = None
    
    def create_socketio_instance(self, app: Flask) -> SocketIO:
        """
        Create and configure a Flask-SocketIO instance with standardized settings
        
        Args:
            app: Flask application instance
            
        Returns:
            Configured SocketIO instance
        """
        try:
            # Get SocketIO configuration
            socketio_config = self._get_unified_socketio_config()
            
            self.logger.info("Creating SocketIO instance with configuration:")
            self.logger.info(f"  - CORS Origins: {len(socketio_config.get('cors_allowed_origins', []))} origins")
            self.logger.info(f"  - Async Mode: {socketio_config.get('async_mode', 'threading')}")
            self.logger.info(f"  - Transports: {socketio_config.get('transports', ['websocket', 'polling'])}")
            self.logger.info(f"  - Ping Timeout: {socketio_config.get('ping_timeout', 60)}s")
            self.logger.info(f"  - Ping Interval: {socketio_config.get('ping_interval', 25)}s")
            
            # Create SocketIO instance
            socketio = SocketIO(app, **socketio_config)
            
            # Configure CORS headers for the Flask app
            self.cors_manager.setup_cors_headers(app)
            self.cors_manager.handle_preflight_requests(app)
            
            # Setup error handlers
            self._setup_error_handlers(socketio)
            
            # Setup middleware
            self._setup_middleware(socketio)
            
            # Setup security middleware if components are available
            if self.db_manager and self.session_manager:
                self._setup_security_middleware(socketio)
            
            # Configure namespaces
            self._configure_default_namespaces(socketio)
            
            self.logger.info("SocketIO instance created and configured successfully")
            return socketio
            
        except Exception as e:
            self.logger.error(f"Failed to create SocketIO instance: {e}")
            raise RuntimeError(f"WebSocket factory failed to create SocketIO instance: {e}")
    
    def _get_unified_socketio_config(self) -> Dict[str, Any]:
        """
        Get unified SocketIO configuration combining config manager and CORS manager
        
        Returns:
            Unified configuration dictionary for SocketIO initialization
        """
        # Get base configuration from config manager
        base_config = self.config_manager.get_socketio_config()
        
        # Get CORS configuration from CORS manager
        cors_config = self.cors_manager.get_cors_config_for_socketio()
        
        # Merge configurations
        unified_config = {**base_config, **cors_config}
        
        # Add factory-specific configurations
        unified_config.update({
            'logger': True,  # Enable SocketIO logging
            'engineio_logger': False,  # Disable engine.io logging (too verbose)
        })
        
        self.logger.debug(f"Unified SocketIO config: {unified_config}")
        return unified_config
    
    def _setup_security_middleware(self, socketio: SocketIO) -> None:
        """
        Setup security middleware for WebSocket connections
        
        Args:
            socketio: SocketIO instance to secure
        """
        try:
            from websocket_security_middleware import setup_websocket_security
            
            self._security_middleware = setup_websocket_security(
                socketio, self.db_manager, self.session_manager, self.security_config
            )
            
            self.logger.info("WebSocket security middleware configured")
            
        except Exception as e:
            self.logger.error(f"Failed to setup WebSocket security middleware: {e}")
            # Continue without security middleware
    
    def configure_namespaces(self, socketio: SocketIO, namespace_configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Configure WebSocket namespaces with specific settings
        
        Args:
            socketio: SocketIO instance to configure
            namespace_configs: Dictionary mapping namespace names to their configurations
        """
        for namespace, config in namespace_configs.items():
            try:
                self.logger.info(f"Configuring namespace: {namespace}")
                
                # Register namespace handlers if provided
                if 'handlers' in config:
                    self._register_namespace_handlers(socketio, namespace, config['handlers'])
                
                # Setup namespace-specific middleware
                if 'middleware' in config:
                    self._setup_namespace_middleware(socketio, namespace, config['middleware'])
                
                # Configure namespace authentication
                if 'auth_required' in config and config['auth_required']:
                    self._setup_namespace_authentication(socketio, namespace)
                
                self.logger.info(f"Namespace {namespace} configured successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to configure namespace {namespace}: {e}")
                raise RuntimeError(f"Namespace configuration failed for {namespace}: {e}")
    
    def _configure_default_namespaces(self, socketio: SocketIO) -> None:
        """
        Configure default namespaces for the application
        
        Args:
            socketio: SocketIO instance to configure
        """
        default_namespaces = {
            '/': {
                'description': 'Default namespace for user connections',
                'auth_required': True,
            },
            '/admin': {
                'description': 'Admin namespace for administrative functions',
                'auth_required': True,
                'admin_only': True,
            }
        }
        
        for namespace, config in default_namespaces.items():
            self.logger.debug(f"Setting up default namespace: {namespace}")
            
            # Setup basic connection handlers
            self._setup_default_connection_handlers(socketio, namespace)
            
            # Setup authentication if required
            if config.get('auth_required', False):
                self._setup_namespace_authentication(socketio, namespace)
    
    def _setup_default_connection_handlers(self, socketio: SocketIO, namespace: str) -> None:
        """
        Setup default connection handlers for a namespace
        
        Args:
            socketio: SocketIO instance
            namespace: Namespace to setup handlers for
        """
        @socketio.on('connect', namespace=namespace)
        def handle_connect(auth=None):
            """Handle client connection"""
            try:
                self.logger.info(f"Client connecting to namespace {namespace}")
                
                # Validate origin
                from flask import request
                origin = request.headers.get('Origin')
                if origin:
                    is_valid, error_msg = self.cors_manager.validate_websocket_origin(origin, namespace)
                    if not is_valid:
                        self.logger.warning(f"Connection rejected for namespace {namespace}: {error_msg}")
                        return False
                
                self.logger.info(f"Client connected successfully to namespace {namespace}")
                return True
                
            except Exception as e:
                self.logger.error(f"Connection error in namespace {namespace}: {e}")
                return False
        
        @socketio.on('disconnect', namespace=namespace)
        def handle_disconnect():
            """Handle client disconnection"""
            try:
                self.logger.info(f"Client disconnected from namespace {namespace}")
            except Exception as e:
                self.logger.error(f"Disconnect error in namespace {namespace}: {e}")
    
    def _setup_namespace_authentication(self, socketio: SocketIO, namespace: str) -> None:
        """
        Setup authentication for a specific namespace
        
        Args:
            socketio: SocketIO instance
            namespace: Namespace to setup authentication for
        """
        # This will be implemented when the authentication handler is available
        # For now, we'll set up the framework
        self.logger.debug(f"Authentication framework setup for namespace: {namespace}")
    
    def _register_namespace_handlers(self, socketio: SocketIO, namespace: str, handlers: Dict[str, Callable]) -> None:
        """
        Register event handlers for a namespace
        
        Args:
            socketio: SocketIO instance
            namespace: Namespace to register handlers for
            handlers: Dictionary mapping event names to handler functions
        """
        for event_name, handler in handlers.items():
            try:
                socketio.on(event_name, namespace=namespace)(handler)
                self.logger.debug(f"Registered handler for event '{event_name}' in namespace '{namespace}'")
            except Exception as e:
                self.logger.error(f"Failed to register handler for event '{event_name}' in namespace '{namespace}': {e}")
    
    def _setup_namespace_middleware(self, socketio: SocketIO, namespace: str, middleware: List[Callable]) -> None:
        """
        Setup middleware for a specific namespace
        
        Args:
            socketio: SocketIO instance
            namespace: Namespace to setup middleware for
            middleware: List of middleware functions
        """
        for middleware_func in middleware:
            try:
                # Apply middleware to namespace
                # This is a placeholder for namespace-specific middleware
                self.logger.debug(f"Applied middleware to namespace: {namespace}")
            except Exception as e:
                self.logger.error(f"Failed to apply middleware to namespace {namespace}: {e}")
    
    def setup_error_handlers(self, socketio: SocketIO) -> None:
        """
        Setup comprehensive error handlers for the SocketIO instance
        
        Args:
            socketio: SocketIO instance to setup error handlers for
        """
        self._setup_error_handlers(socketio)
    
    def _setup_error_handlers(self, socketio: SocketIO) -> None:
        """
        Setup comprehensive error handling for SocketIO
        
        Args:
            socketio: SocketIO instance to setup error handlers for
        """
        @socketio.on_error_default
        def default_error_handler(e):
            """Default error handler for all namespaces"""
            try:
                self.logger.error(f"SocketIO error: {e}")
                
                # Emit error to client if possible
                try:
                    emit('error', {
                        'message': 'An error occurred',
                        'type': 'server_error',
                        'timestamp': self._get_current_timestamp()
                    })
                except Exception as emit_error:
                    self.logger.error(f"Failed to emit error to client: {emit_error}")
                
            except Exception as handler_error:
                self.logger.error(f"Error in default error handler: {handler_error}")
        
        @socketio.on_error('/')
        def user_namespace_error_handler(e):
            """Error handler for user namespace"""
            try:
                self.logger.error(f"User namespace error: {e}")
                
                emit('error', {
                    'message': 'Connection error occurred',
                    'type': 'user_error',
                    'namespace': '/',
                    'timestamp': self._get_current_timestamp()
                })
                
            except Exception as handler_error:
                self.logger.error(f"Error in user namespace error handler: {handler_error}")
        
        @socketio.on_error('/admin')
        def admin_namespace_error_handler(e):
            """Error handler for admin namespace"""
            try:
                self.logger.error(f"Admin namespace error: {e}")
                
                emit('error', {
                    'message': 'Admin connection error occurred',
                    'type': 'admin_error',
                    'namespace': '/admin',
                    'timestamp': self._get_current_timestamp()
                })
                
            except Exception as handler_error:
                self.logger.error(f"Error in admin namespace error handler: {handler_error}")
        
        # Setup connection error handlers
        self._setup_connection_error_handlers(socketio)
        
        # Setup transport error handlers
        self._setup_transport_error_handlers(socketio)
        
        self.logger.info("Error handlers configured for SocketIO instance")
    
    def _setup_connection_error_handlers(self, socketio: SocketIO) -> None:
        """
        Setup connection-specific error handlers
        
        Args:
            socketio: SocketIO instance
        """
        # Connection timeout handler
        @socketio.on('connect_error')
        def handle_connect_error(data):
            """Handle connection errors"""
            try:
                self.logger.warning(f"Connection error: {data}")
                
                # Analyze error type
                error_type = self._analyze_connection_error(data)
                
                emit('connection_error', {
                    'message': 'Connection failed',
                    'error_type': error_type,
                    'data': str(data),
                    'timestamp': self._get_current_timestamp()
                })
                
            except Exception as e:
                self.logger.error(f"Error in connection error handler: {e}")
    
    def _setup_transport_error_handlers(self, socketio: SocketIO) -> None:
        """
        Setup transport-specific error handlers
        
        Args:
            socketio: SocketIO instance
        """
        # This will handle WebSocket and polling transport errors
        # Implementation depends on specific transport error patterns
        self.logger.debug("Transport error handlers configured")
    
    def _setup_middleware(self, socketio: SocketIO) -> None:
        """
        Setup middleware functions for SocketIO
        
        Args:
            socketio: SocketIO instance
        """
        # Apply registered middleware functions
        for middleware_func in self._middleware_functions:
            try:
                middleware_func(socketio)
                self.logger.debug("Applied middleware function to SocketIO")
            except Exception as e:
                self.logger.error(f"Failed to apply middleware: {e}")
    
    def register_middleware(self, middleware_func: Callable) -> None:
        """
        Register a middleware function to be applied to SocketIO instances
        
        Args:
            middleware_func: Middleware function that takes a SocketIO instance
        """
        self._middleware_functions.append(middleware_func)
        self.logger.debug("Middleware function registered")
    
    def register_error_handler(self, error_type: str, handler: Callable) -> None:
        """
        Register a custom error handler
        
        Args:
            error_type: Type of error to handle
            handler: Error handler function
        """
        self._error_handlers[error_type] = handler
        self.logger.debug(f"Error handler registered for type: {error_type}")
    
    def _analyze_connection_error(self, error_data: Any) -> str:
        """
        Analyze connection error to determine error type
        
        Args:
            error_data: Error data from connection
            
        Returns:
            Error type string
        """
        error_str = str(error_data).lower()
        
        if 'cors' in error_str or 'origin' in error_str:
            return 'cors_error'
        elif 'timeout' in error_str:
            return 'timeout_error'
        elif 'transport' in error_str:
            return 'transport_error'
        elif 'auth' in error_str or 'unauthorized' in error_str:
            return 'auth_error'
        else:
            return 'unknown_error'
    
    def _get_current_timestamp(self) -> str:
        """
        Get current timestamp for error messages
        
        Returns:
            ISO format timestamp string
        """
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def get_factory_status(self) -> Dict[str, Any]:
        """
        Get factory status and configuration information
        
        Returns:
            Dictionary containing factory status information
        """
        status = {
            'config_manager_status': self.config_manager.get_configuration_summary(),
            'cors_debug_info': self.cors_manager.get_cors_debug_info(),
            'registered_middleware': len(self._middleware_functions),
            'registered_error_handlers': list(self._error_handlers.keys()),
            'namespace_handlers': list(self._namespace_handlers.keys()),
            'security_enabled': self._security_middleware is not None,
        }
        
        # Add security stats if available
        if self._security_middleware:
            try:
                status['security_stats'] = self._security_middleware.get_security_stats()
            except Exception as e:
                status['security_error'] = str(e)
        
        return status
    
    def validate_factory_configuration(self) -> bool:
        """
        Validate factory configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate config manager
            if not self.config_manager.validate_configuration():
                self.logger.error("Config manager validation failed")
                return False
            
            # Validate CORS manager
            cors_origins = self.cors_manager.get_allowed_origins()
            if not cors_origins:
                self.logger.error("No CORS origins configured")
                return False
            
            self.logger.info("Factory configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Factory configuration validation failed: {e}")
            return False
    
    def create_test_socketio_instance(self, app: Flask, test_config: Optional[Dict[str, Any]] = None) -> SocketIO:
        """
        Create a SocketIO instance for testing with optional test configuration
        
        Args:
            app: Flask application instance
            test_config: Optional test-specific configuration overrides
            
        Returns:
            SocketIO instance configured for testing
        """
        try:
            # Get base configuration
            socketio_config = self._get_unified_socketio_config()
            
            # Apply test configuration overrides
            if test_config:
                socketio_config.update(test_config)
                self.logger.debug(f"Applied test configuration overrides: {test_config}")
            
            # Create SocketIO instance
            socketio = SocketIO(app, **socketio_config)
            
            # Setup minimal error handlers for testing
            @socketio.on_error_default
            def test_error_handler(e):
                self.logger.error(f"Test SocketIO error: {e}")
            
            self.logger.info("Test SocketIO instance created successfully")
            return socketio
            
        except Exception as e:
            self.logger.error(f"Failed to create test SocketIO instance: {e}")
            raise RuntimeError(f"Test WebSocket factory failed: {e}")