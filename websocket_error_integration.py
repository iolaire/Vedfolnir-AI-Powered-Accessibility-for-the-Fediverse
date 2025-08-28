# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Error Integration Module

This module integrates the comprehensive error detection and handling system
with the existing WebSocket infrastructure, providing seamless error management
across all WebSocket components.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from flask_socketio import SocketIO
from flask import Flask

from websocket_error_detector import WebSocketErrorDetector, WebSocketErrorCategory
from websocket_error_handler import WebSocketErrorHandler
from websocket_error_logger import WebSocketErrorLogger


class WebSocketErrorIntegration:
    """
    Integration layer for comprehensive WebSocket error management
    
    This class provides:
    - Seamless integration with existing WebSocket components
    - Centralized error management configuration
    - Error monitoring and reporting
    - Integration with WebSocket factory and managers
    """
    
    def __init__(self, app: Optional[Flask] = None, socketio: Optional[SocketIO] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the error integration system
        
        Args:
            app: Flask application instance
            socketio: SocketIO instance
            config: Configuration dictionary
        """
        self.app = app
        self.socketio = socketio
        self.config = config or {}
        
        # Initialize components
        self.logger = logging.getLogger(__name__)
        self.error_detector = WebSocketErrorDetector(self.logger)
        self.error_logger = WebSocketErrorLogger(
            log_dir=self.config.get('error_log_dir', 'logs'),
            max_log_size=self.config.get('max_log_size', 10 * 1024 * 1024),
            max_recent_errors=self.config.get('max_recent_errors', 1000)
        )
        
        # Error handler will be initialized when SocketIO is available
        self.error_handler: Optional[WebSocketErrorHandler] = None
        
        # Integration state
        self._integrated = False
        self._error_callbacks: Dict[str, List[Callable]] = {}
        
        # Initialize if components are available
        if self.socketio:
            self._initialize_error_handler()
    
    def integrate_with_factory(self, websocket_factory) -> None:
        """
        Integrate with WebSocket factory
        
        Args:
            websocket_factory: WebSocketFactory instance
        """
        try:
            # Register error detection with factory
            if hasattr(websocket_factory, 'register_error_detector'):
                websocket_factory.register_error_detector(self.error_detector)
            
            # Register error handler with factory
            if hasattr(websocket_factory, 'register_error_handler') and self.error_handler:
                websocket_factory.register_error_handler(self.error_handler)
            
            # Setup factory error callbacks
            self._setup_factory_callbacks(websocket_factory)
            
            self.logger.info("Successfully integrated with WebSocket factory")
            
        except Exception as e:
            self.logger.error(f"Failed to integrate with WebSocket factory: {e}")
    
    def integrate_with_cors_manager(self, cors_manager) -> None:
        """
        Integrate with CORS manager
        
        Args:
            cors_manager: WebSocketCORSManager instance
        """
        try:
            # Register CORS error callback
            def cors_error_callback(origin: str, allowed_origins: List[str], error_details: Optional[Dict] = None):
                """Handle CORS errors from CORS manager"""
                error_info = self.error_detector.detect_cors_error(origin, allowed_origins, error_details)
                self.error_logger.log_cors_error(error_info, origin, allowed_origins)
                
                if self.error_handler:
                    self.error_handler.handle_cors_error(origin, allowed_origins)
                
                return error_info
            
            # Register callback with CORS manager
            if hasattr(cors_manager, 'register_error_callback'):
                cors_manager.register_error_callback(cors_error_callback)
            
            self.logger.info("Successfully integrated with CORS manager")
            
        except Exception as e:
            self.logger.error(f"Failed to integrate with CORS manager: {e}")
    
    def integrate_with_auth_handler(self, auth_handler) -> None:
        """
        Integrate with authentication handler
        
        Args:
            auth_handler: WebSocketAuthHandler instance
        """
        try:
            # Register authentication error callback
            def auth_error_callback(user_id: Optional[int], session_data: Optional[Dict], error_details: Optional[Dict] = None):
                """Handle authentication errors from auth handler"""
                error_info = self.error_detector.detect_authentication_error(user_id, session_data, error_details)
                self.error_logger.log_authentication_error(error_info, user_id, session_data)
                
                if self.error_handler:
                    self.error_handler.handle_authentication_error(user_id, session_data)
                
                return error_info
            
            # Register callback with auth handler
            if hasattr(auth_handler, 'register_error_callback'):
                auth_handler.register_error_callback(auth_error_callback)
            
            self.logger.info("Successfully integrated with authentication handler")
            
        except Exception as e:
            self.logger.error(f"Failed to integrate with authentication handler: {e}")
    
    def integrate_with_config_manager(self, config_manager) -> None:
        """
        Integrate with configuration manager
        
        Args:
            config_manager: WebSocketConfigManager instance
        """
        try:
            # Register configuration error callback
            def config_error_callback(config_error: str, config_details: Optional[Dict] = None):
                """Handle configuration errors from config manager"""
                error_info = self.error_detector.detect_error(
                    f"WebSocket configuration error: {config_error}",
                    {'config_details': config_details or {}}
                )
                self.error_logger.log_error(error_info)
                
                if self.error_handler:
                    self.error_handler.handle_error(Exception(config_error), {'source': 'config_manager'})
                
                return error_info
            
            # Register callback with config manager
            if hasattr(config_manager, 'register_error_callback'):
                config_manager.register_error_callback(config_error_callback)
            
            self.logger.info("Successfully integrated with configuration manager")
            
        except Exception as e:
            self.logger.error(f"Failed to integrate with configuration manager: {e}")
    
    def setup_socketio_integration(self, socketio: SocketIO) -> None:
        """
        Setup integration with SocketIO instance
        
        Args:
            socketio: SocketIO instance to integrate with
        """
        self.socketio = socketio
        self._initialize_error_handler()
        self._setup_socketio_error_handlers()
        self._integrated = True
        
        self.logger.info("WebSocket error integration setup complete")
    
    def register_error_callback(self, category: str, callback: Callable) -> None:
        """
        Register custom error callback
        
        Args:
            category: Error category or 'all' for all errors
            callback: Callback function to execute
        """
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        stats = {
            'detector_stats': self.error_detector.get_error_statistics(),
            'logger_stats': self.error_logger.get_error_summary(),
            'integration_status': {
                'integrated': self._integrated,
                'socketio_available': self.socketio is not None,
                'error_handler_available': self.error_handler is not None
            }
        }
        
        if self.error_handler:
            stats['handler_stats'] = self.error_handler.get_error_statistics()
        
        return stats
    
    def get_debugging_report(self, error_code: str) -> Optional[Dict[str, Any]]:
        """Get debugging report for specific error"""
        return self.error_logger.get_debugging_report(error_code)
    
    def export_error_logs(self, output_file: str, hours: int = 24, format: str = 'json') -> bool:
        """Export error logs to file"""
        return self.error_logger.export_error_logs(output_file, hours, format)
    
    def _initialize_error_handler(self) -> None:
        """Initialize error handler with SocketIO"""
        if self.socketio:
            self.error_handler = WebSocketErrorHandler(
                self.socketio,
                self.error_detector,
                self.logger
            )
            
            # Register error categories with handler
            self._register_error_categories()
    
    def _register_error_categories(self) -> None:
        """Register error category handlers"""
        if not self.error_handler:
            return
        
        # CORS error callback
        def cors_callback(error_info):
            self.error_logger.log_error(error_info)
            self._execute_custom_callbacks('cors', error_info)
        
        # Authentication error callback
        def auth_callback(error_info):
            self.error_logger.log_error(error_info)
            self._execute_custom_callbacks('authentication', error_info)
        
        # Network error callback
        def network_callback(error_info):
            self.error_logger.log_error(error_info)
            self._execute_custom_callbacks('network', error_info)
        
        # Register callbacks
        self.error_handler.register_error_callback(WebSocketErrorCategory.CORS, cors_callback)
        self.error_handler.register_error_callback(WebSocketErrorCategory.AUTHENTICATION, auth_callback)
        self.error_handler.register_error_callback(WebSocketErrorCategory.AUTHORIZATION, auth_callback)
        self.error_handler.register_error_callback(WebSocketErrorCategory.NETWORK, network_callback)
    
    def _setup_socketio_error_handlers(self) -> None:
        """Setup SocketIO-specific error handlers"""
        if not self.socketio:
            return
        
        # Connection error handler
        @self.socketio.on('connect_error')
        def handle_connect_error(data):
            """Handle SocketIO connection errors"""
            try:
                connection_info = {
                    'error_data': data,
                    'source': 'socketio_connect'
                }
                
                if self.error_handler:
                    self.error_handler.handle_connection_error(connection_info)
                else:
                    # Fallback logging
                    error_info = self.error_detector.detect_error(f"SocketIO connection error: {data}")
                    self.error_logger.log_error(error_info)
                    
            except Exception as e:
                self.logger.error(f"Error in SocketIO connect error handler: {e}")
        
        # Disconnect error handler
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle SocketIO disconnections"""
            try:
                # Log disconnection for monitoring
                self.logger.debug("SocketIO client disconnected")
                
            except Exception as e:
                self.logger.error(f"Error in SocketIO disconnect handler: {e}")
    
    def _setup_factory_callbacks(self, websocket_factory) -> None:
        """Setup callbacks with WebSocket factory"""
        try:
            # Error detection callback
            def factory_error_callback(error, context=None):
                """Handle errors from WebSocket factory"""
                error_info = self.error_detector.detect_error(error, context)
                self.error_logger.log_error(error_info)
                
                if self.error_handler:
                    self.error_handler.handle_error(error, context)
                
                return error_info
            
            # Register with factory if method exists
            if hasattr(websocket_factory, 'set_error_callback'):
                websocket_factory.set_error_callback(factory_error_callback)
            
        except Exception as e:
            self.logger.error(f"Failed to setup factory callbacks: {e}")
    
    def _execute_custom_callbacks(self, category: str, error_info) -> None:
        """Execute custom error callbacks"""
        # Execute category-specific callbacks
        for callback in self._error_callbacks.get(category, []):
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in custom callback for {category}: {e}")
        
        # Execute 'all' callbacks
        for callback in self._error_callbacks.get('all', []):
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in custom 'all' callback: {e}")


def create_error_integration(app: Flask, socketio: SocketIO, config: Optional[Dict[str, Any]] = None) -> WebSocketErrorIntegration:
    """
    Factory function to create and configure error integration
    
    Args:
        app: Flask application
        socketio: SocketIO instance
        config: Configuration dictionary
        
    Returns:
        Configured WebSocketErrorIntegration instance
    """
    # Default configuration
    default_config = {
        'error_log_dir': 'logs',
        'max_log_size': 10 * 1024 * 1024,  # 10MB
        'max_recent_errors': 1000,
        'enable_debug_logging': app.debug if app else False
    }
    
    # Merge with provided config
    if config:
        default_config.update(config)
    
    # Create integration instance
    integration = WebSocketErrorIntegration(app, socketio, default_config)
    
    # Setup SocketIO integration
    integration.setup_socketio_integration(socketio)
    
    return integration


def integrate_with_existing_components(integration: WebSocketErrorIntegration, **components) -> None:
    """
    Integrate error system with existing WebSocket components
    
    Args:
        integration: WebSocketErrorIntegration instance
        **components: Named components to integrate with
    """
    # Integrate with factory
    if 'factory' in components:
        integration.integrate_with_factory(components['factory'])
    
    # Integrate with CORS manager
    if 'cors_manager' in components:
        integration.integrate_with_cors_manager(components['cors_manager'])
    
    # Integrate with auth handler
    if 'auth_handler' in components:
        integration.integrate_with_auth_handler(components['auth_handler'])
    
    # Integrate with config manager
    if 'config_manager' in components:
        integration.integrate_with_config_manager(components['config_manager'])


# Convenience functions for common integration patterns

def setup_comprehensive_error_handling(app: Flask, socketio: SocketIO, **components) -> WebSocketErrorIntegration:
    """
    Setup comprehensive error handling for WebSocket system
    
    Args:
        app: Flask application
        socketio: SocketIO instance
        **components: WebSocket components to integrate with
        
    Returns:
        Configured error integration system
    """
    # Create integration
    integration = create_error_integration(app, socketio)
    
    # Integrate with existing components
    integrate_with_existing_components(integration, **components)
    
    return integration


def add_error_monitoring_to_factory(factory, integration: WebSocketErrorIntegration) -> None:
    """
    Add error monitoring to existing WebSocket factory
    
    Args:
        factory: WebSocketFactory instance
        integration: Error integration system
    """
    integration.integrate_with_factory(factory)