# Copyright (C) 2025 iolaire mcfadden.
# Consolidated WebSocket Production Factory

import logging
import os
from typing import Dict, Any, Optional
from flask import Flask
from flask_socketio import SocketIO

from ..core.factory import WebSocketFactory
from ..core.config_manager import ConsolidatedWebSocketConfigManager
from ..middleware.security_manager import ConsolidatedWebSocketSecurityManager
from ..services.performance_monitor import ConsolidatedWebSocketPerformanceMonitor
from ..services.error_handler import ConsolidatedWebSocketErrorHandler
from ..services.connection_optimizer import ConsolidatedWebSocketConnectionOptimizer

logger = logging.getLogger(__name__)

class ProductionWebSocketFactory:
    """Production-ready WebSocket factory with all optimizations and monitoring"""
    
    def __init__(self, app: Flask, config=None):
        self.app = app
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.config_manager = ConsolidatedWebSocketConfigManager(app.config)
        self.security_manager = ConsolidatedWebSocketSecurityManager(self.config)
        self.performance_monitor = ConsolidatedWebSocketPerformanceMonitor(self.config)
        self.error_handler = ConsolidatedWebSocketErrorHandler(self.config)
        self.connection_optimizer = ConsolidatedWebSocketConnectionOptimizer(self.config)
        
        # WebSocket instance
        self.socketio = None
    
    def create_production_websocket(self) -> SocketIO:
        """Create production-ready WebSocket instance"""
        try:
            # Get WebSocket configuration
            ws_config = self.config_manager.get_websocket_config()
            
            # Create SocketIO instance with production settings
            self.socketio = SocketIO(
                self.app,
                cors_allowed_origins=ws_config.cors_origins,
                async_mode=ws_config.async_mode,
                transports=ws_config.transports,
                ping_timeout=ws_config.ping_timeout,
                ping_interval=ws_config.ping_interval,
                max_http_buffer_size=ws_config.max_http_buffer_size,
                logger=self.config.get('enable_debug', False),
                engineio_logger=self.config.get('enable_debug', False)
            )
            
            # Setup event handlers
            self._setup_production_handlers()
            
            # Start optimization services
            self.performance_monitor.cleanup_old_metrics()
            self.connection_optimizer.start_optimization()
            
            self.logger.info("Production WebSocket instance created successfully")
            return self.socketio
            
        except Exception as e:
            self.logger.error(f"Error creating production WebSocket: {e}")
            raise
    
    def _setup_production_handlers(self):
        """Setup production event handlers with full monitoring and security"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            try:
                client_id = request.sid
                
                # Security validation
                is_valid, error_msg = self.security_manager.validate_connection(client_id, auth or {})
                if not is_valid:
                    self.error_handler.handle_error(
                        WebSocketErrorType.SECURITY_ERROR,
                        error_msg,
                        client_id=client_id
                    )
                    return False
                
                # Register connection
                self.performance_monitor.record_connection(client_id)
                self.connection_optimizer.register_connection(
                    client_id,
                    session_id=auth.get('session_id') if auth else None,
                    user_agent=request.headers.get('User-Agent'),
                    ip_address=request.environ.get('REMOTE_ADDR')
                )
                
                self.logger.info(f"WebSocket connection established: {client_id}")
                return True
                
            except Exception as e:
                self.error_handler.handle_error(
                    WebSocketErrorType.CONNECTION_ERROR,
                    str(e),
                    client_id=getattr(request, 'sid', None),
                    exception=e
                )
                return False
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            try:
                client_id = request.sid
                
                # Unregister connection
                self.performance_monitor.record_disconnection(client_id)
                self.connection_optimizer.unregister_connection(client_id)
                
                self.logger.info(f"WebSocket connection closed: {client_id}")
                
            except Exception as e:
                self.error_handler.handle_error(
                    WebSocketErrorType.CONNECTION_ERROR,
                    str(e),
                    client_id=getattr(request, 'sid', None),
                    exception=e
                )
        
        @self.socketio.on_error_default
        def default_error_handler(e):
            try:
                client_id = getattr(request, 'sid', None)
                self.error_handler.handle_error(
                    WebSocketErrorType.INTERNAL_ERROR,
                    str(e),
                    client_id=client_id,
                    exception=e
                )
            except Exception as handler_error:
                self.logger.critical(f"Error in error handler: {handler_error}")
    
    def get_production_status(self) -> Dict[str, Any]:
        """Get comprehensive production status"""
        try:
            return {
                'websocket_active': self.socketio is not None,
                'configuration_health': self.config_manager.get_health_status(),
                'security_metrics': self.security_manager.get_security_metrics(),
                'performance_summary': self.performance_monitor.get_performance_summary(),
                'connection_statistics': self.connection_optimizer.get_connection_statistics(),
                'error_statistics': self.error_handler.get_error_statistics(),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting production status: {e}")
            return {'error': str(e)}
    
    def shutdown_production_websocket(self):
        """Gracefully shutdown production WebSocket"""
        try:
            # Stop optimization services
            self.connection_optimizer.stop_optimization()
            
            # Clean up resources
            self.performance_monitor.cleanup_old_metrics()
            self.error_handler.cleanup_old_errors()
            self.security_manager.cleanup_expired_data()
            
            self.logger.info("Production WebSocket shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during WebSocket shutdown: {e}")
