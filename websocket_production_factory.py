# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Production Factory

This module provides a comprehensive production-ready WebSocket factory that integrates
SSL/TLS support, production logging, monitoring, backup/recovery, load balancer support,
and all production readiness features into a unified system.
"""

import os
import ssl
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from flask import Flask
from flask_socketio import SocketIO

from config import Config
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager

# Production components
from websocket_production_config import (
    ProductionWebSocketConfigManager, 
    ProductionWebSocketConfig,
    SSLConfig,
    LoadBalancerConfig,
    ProductionLoggingConfig,
    ProductionMonitoringConfig,
    BackupRecoveryConfig
)
from websocket_production_logging import (
    ProductionWebSocketLogger,
    WebSocketProductionErrorHandler,
    create_production_logger,
    create_production_error_handler
)
from websocket_production_monitoring import (
    WebSocketProductionMonitor,
    create_production_monitor
)
from websocket_backup_recovery import (
    WebSocketBackupManager,
    create_backup_manager
)
from websocket_load_balancer_support import (
    WebSocketLoadBalancerSupport,
    create_load_balancer_support
)

# Try to import optional dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProductionWebSocketFactory(WebSocketFactory):
    """
    Production-ready WebSocket factory
    
    Extends the base WebSocket factory with comprehensive production features
    including SSL/TLS support, advanced logging, monitoring, backup/recovery,
    load balancer compatibility, and enterprise-grade error handling.
    """
    
    def __init__(self, config: Config, 
                 db_manager=None, 
                 session_manager=None,
                 redis_client=None):
        """
        Initialize production WebSocket factory
        
        Args:
            config: Application configuration
            db_manager: Database manager instance (optional)
            session_manager: Session manager instance (optional)
            redis_client: Redis client for coordination (optional)
        """
        # Initialize production configuration manager
        self.production_config_manager = ProductionWebSocketConfigManager(config)
        
        # Initialize base components
        cors_manager = CORSManager(self.production_config_manager)
        
        # Initialize production components
        self.production_config = self.production_config_manager.get_production_config()
        
        # Setup production logging
        if self.production_config:
            self.production_logger = create_production_logger(
                self.production_config.logging_config,
                "websocket_production"
            )
            self.error_handler = create_production_error_handler(self.production_logger)
        else:
            # Fallback to standard logging
            self.production_logger = None
            self.error_handler = None
        
        # Initialize base factory
        super().__init__(
            config_manager=self.production_config_manager,
            cors_manager=cors_manager,
            db_manager=db_manager,
            session_manager=session_manager
        )
        
        # Production-specific components
        self.redis_client = redis_client
        self.monitor = None
        self.backup_manager = None
        self.load_balancer_support = None
        
        # SSL context
        self.ssl_context = self.production_config_manager.get_ssl_context()
        
        logger.info("Production WebSocket factory initialized")
    
    def create_production_socketio_instance(self, app: Flask) -> SocketIO:
        """
        Create production-ready SocketIO instance with all features
        
        Args:
            app: Flask application instance
        
        Returns:
            Configured SocketIO instance with production features
        """
        try:
            # Get production configuration
            if self.production_config:
                socketio_config = self.production_config_manager.get_socketio_production_config()
            else:
                socketio_config = self.config_manager.get_socketio_config()
            
            # Create SocketIO instance
            socketio = SocketIO(app, **socketio_config)
            
            # Setup production components
            self._setup_production_components(app, socketio)
            
            # Configure namespaces with production features
            self._configure_production_namespaces(socketio)
            
            # Setup production error handlers
            self._setup_production_error_handlers(socketio)
            
            # Setup production event handlers
            self._setup_production_event_handlers(socketio)
            
            if self.production_logger:
                self.production_logger.log_system_event(
                    event_type="socketio_created",
                    message="Production SocketIO instance created successfully",
                    metadata={
                        'ssl_enabled': self.ssl_context is not None,
                        'monitoring_enabled': self.monitor is not None,
                        'backup_enabled': self.backup_manager is not None,
                        'load_balancer_support': self.load_balancer_support is not None
                    }
                )
            
            return socketio
            
        except Exception as e:
            if self.production_logger:
                self.production_logger.log_error_event(
                    event_type="socketio_creation_failed",
                    message=f"Failed to create production SocketIO instance: {str(e)}",
                    exception=e
                )
            raise
    
    def _setup_production_components(self, app: Flask, socketio: SocketIO) -> None:
        """Setup production components"""
        
        if not self.production_config:
            return
        
        try:
            # Setup monitoring
            if self.production_config.monitoring_config.metrics_enabled:
                self.monitor = create_production_monitor(
                    self.production_config.monitoring_config,
                    self.production_logger,
                    app,
                    socketio
                )
            
            # Setup backup manager
            if self.production_config.backup_config.state_backup_enabled:
                self.backup_manager = create_backup_manager(
                    self.production_config.backup_config,
                    self.production_logger,
                    socketio,
                    self.redis_client
                )
            
            # Setup load balancer support
            if self.production_config.load_balancer_config.session_affinity_enabled:
                self.load_balancer_support = create_load_balancer_support(
                    self.production_config.load_balancer_config,
                    self.production_logger,
                    app,
                    socketio,
                    self.redis_client
                )
            
            if self.production_logger:
                self.production_logger.log_system_event(
                    event_type="production_components_setup",
                    message="Production components setup completed",
                    metadata={
                        'monitoring': self.monitor is not None,
                        'backup': self.backup_manager is not None,
                        'load_balancer': self.load_balancer_support is not None
                    }
                )
                
        except Exception as e:
            if self.production_logger:
                self.production_logger.log_error_event(
                    event_type="production_components_setup_failed",
                    message=f"Failed to setup production components: {str(e)}",
                    exception=e
                )
            raise
    
    def _configure_production_namespaces(self, socketio: SocketIO) -> None:
        """Configure namespaces with production features"""
        
        try:
            # Create namespace manager with production features
            auth_handler = WebSocketAuthHandler(self.db_manager, self.session_manager)
            namespace_manager = WebSocketNamespaceManager(socketio, auth_handler)
            
            # Setup user namespace with production monitoring
            @socketio.on('connect', namespace='/user')
            def handle_user_connect(auth):
                return self._handle_production_connect(auth, '/user')
            
            @socketio.on('disconnect', namespace='/user')
            def handle_user_disconnect():
                return self._handle_production_disconnect('/user')
            
            # Setup admin namespace with production monitoring
            @socketio.on('connect', namespace='/admin')
            def handle_admin_connect(auth):
                return self._handle_production_connect(auth, '/admin')
            
            @socketio.on('disconnect', namespace='/admin')
            def handle_admin_disconnect():
                return self._handle_production_disconnect('/admin')
            
            # Setup namespace-specific event handlers
            namespace_manager.setup_user_namespace()
            namespace_manager.setup_admin_namespace()
            
            if self.production_logger:
                self.production_logger.log_system_event(
                    event_type="production_namespaces_configured",
                    message="Production namespaces configured successfully"
                )
                
        except Exception as e:
            if self.production_logger:
                self.production_logger.log_error_event(
                    event_type="production_namespaces_setup_failed",
                    message=f"Failed to configure production namespaces: {str(e)}",
                    exception=e
                )
            raise
    
    def _handle_production_connect(self, auth: Dict[str, Any], namespace: str) -> bool:
        """Handle WebSocket connection with production features"""
        
        try:
            from flask import request, session
            from flask_socketio import disconnect
            
            # Get connection information
            session_id = session.get('session_id', 'unknown')
            user_id = session.get('user_id')
            connection_id = request.sid
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            user_agent = request.headers.get('User-Agent', 'unknown')
            
            # Log connection attempt
            if self.production_logger:
                self.production_logger.log_connection_event(
                    event_type="connection_attempt",
                    message=f"WebSocket connection attempt to {namespace}",
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id,
                    client_ip=client_ip,
                    user_agent=user_agent
                )
            
            # Authenticate connection
            auth_handler = WebSocketAuthHandler(self.db_manager, self.session_manager)
            user = auth_handler.authenticate_connection(session)
            
            if not user:
                if self.production_logger:
                    self.production_logger.log_security_event(
                        event_type="authentication_failed",
                        message="WebSocket authentication failed",
                        session_id=session_id,
                        connection_id=connection_id,
                        client_ip=client_ip
                    )
                disconnect()
                return False
            
            # Check admin access for admin namespace
            if namespace == '/admin' and not auth_handler.authorize_admin_access(user):
                if self.production_logger:
                    self.production_logger.log_security_event(
                        event_type="admin_access_denied",
                        message="Admin access denied for WebSocket connection",
                        session_id=session_id,
                        user_id=user.id,
                        connection_id=connection_id,
                        client_ip=client_ip
                    )
                disconnect()
                return False
            
            # Record metrics
            if self.monitor:
                self.monitor.record_connection_event(
                    event_type="connect",
                    session_id=session_id,
                    user_id=user.id,
                    namespace=namespace,
                    success=True
                )
            
            # Track connection for backup
            if self.backup_manager:
                self.backup_manager.track_connection(
                    session_id=session_id,
                    user_id=user.id,
                    connection_id=connection_id,
                    namespace=namespace,
                    client_info={
                        'ip': client_ip,
                        'user_agent': user_agent
                    }
                )
            
            # Register with load balancer
            if self.load_balancer_support:
                self.load_balancer_support.register_websocket_connection(
                    session_id=session_id,
                    connection_id=connection_id,
                    user_id=user.id,
                    namespace=namespace
                )
            
            # Log successful connection
            if self.production_logger:
                self.production_logger.log_connection_event(
                    event_type="connection_established",
                    message=f"WebSocket connection established to {namespace}",
                    session_id=session_id,
                    user_id=user.id,
                    connection_id=connection_id,
                    client_ip=client_ip
                )
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_connection_error(
                    error=e,
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id,
                    client_ip=client_ip
                )
            
            # Record failed connection
            if self.monitor:
                self.monitor.record_connection_event(
                    event_type="connect",
                    session_id=session_id,
                    user_id=user_id,
                    namespace=namespace,
                    success=False
                )
            
            disconnect()
            return False
    
    def _handle_production_disconnect(self, namespace: str) -> None:
        """Handle WebSocket disconnection with production features"""
        
        try:
            from flask import request, session
            
            # Get connection information
            session_id = session.get('session_id', 'unknown')
            user_id = session.get('user_id')
            connection_id = request.sid
            
            # Record metrics
            if self.monitor:
                self.monitor.record_connection_event(
                    event_type="disconnect",
                    session_id=session_id,
                    user_id=user_id,
                    namespace=namespace,
                    success=True
                )
            
            # Untrack connection from backup
            if self.backup_manager:
                self.backup_manager.untrack_connection(connection_id)
            
            # Unregister from load balancer
            if self.load_balancer_support:
                self.load_balancer_support.unregister_websocket_connection(
                    session_id=session_id,
                    connection_id=connection_id
                )
            
            # Log disconnection
            if self.production_logger:
                self.production_logger.log_connection_event(
                    event_type="connection_closed",
                    message=f"WebSocket connection closed from {namespace}",
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id
                )
                
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_connection_error(
                    error=e,
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id
                )
    
    def _setup_production_error_handlers(self, socketio: SocketIO) -> None:
        """Setup production error handlers"""
        
        @socketio.on_error_default
        def default_error_handler(e):
            if self.error_handler:
                from flask import request, session
                
                session_id = session.get('session_id', 'unknown')
                user_id = session.get('user_id')
                connection_id = request.sid
                
                self.error_handler.handle_message_error(
                    error=e,
                    event_name='unknown',
                    namespace=request.namespace,
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id
                )
        
        @socketio.on_error('/user')
        def user_error_handler(e):
            if self.error_handler:
                from flask import request, session
                
                session_id = session.get('session_id', 'unknown')
                user_id = session.get('user_id')
                connection_id = request.sid
                
                self.error_handler.handle_message_error(
                    error=e,
                    event_name='user_event',
                    namespace='/user',
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id
                )
        
        @socketio.on_error('/admin')
        def admin_error_handler(e):
            if self.error_handler:
                from flask import request, session
                
                session_id = session.get('session_id', 'unknown')
                user_id = session.get('user_id')
                connection_id = request.sid
                
                self.error_handler.handle_message_error(
                    error=e,
                    event_name='admin_event',
                    namespace='/admin',
                    session_id=session_id,
                    user_id=user_id,
                    connection_id=connection_id
                )
    
    def _setup_production_event_handlers(self, socketio: SocketIO) -> None:
        """Setup production event handlers with monitoring"""
        
        # Wrap existing event handlers with production monitoring
        original_on = socketio.on
        
        def monitored_on(event, handler=None, namespace=None):
            """Wrapper for event handlers with production monitoring"""
            
            def wrapper(f):
                def monitored_handler(*args, **kwargs):
                    start_time = time.time()
                    
                    try:
                        from flask import request, session
                        
                        session_id = session.get('session_id', 'unknown')
                        user_id = session.get('user_id')
                        connection_id = request.sid
                        
                        # Log message event
                        if self.production_logger:
                            self.production_logger.log_message_event(
                                event_type="message_received",
                                message=f"WebSocket event received: {event}",
                                session_id=session_id,
                                user_id=user_id,
                                connection_id=connection_id,
                                namespace=namespace,
                                event_name=event
                            )
                        
                        # Execute handler
                        result = f(*args, **kwargs)
                        
                        # Record metrics
                        duration_ms = (time.time() - start_time) * 1000
                        
                        if self.monitor:
                            self.monitor.record_message_event(
                                event_name=event,
                                namespace=namespace,
                                processing_time_ms=duration_ms,
                                success=True
                            )
                        
                        # Log successful processing
                        if self.production_logger:
                            self.production_logger.log_message_event(
                                event_type="message_processed",
                                message=f"WebSocket event processed successfully: {event}",
                                session_id=session_id,
                                user_id=user_id,
                                connection_id=connection_id,
                                namespace=namespace,
                                event_name=event,
                                duration_ms=duration_ms
                            )
                        
                        return result
                        
                    except Exception as e:
                        duration_ms = (time.time() - start_time) * 1000
                        
                        # Handle error
                        if self.error_handler:
                            self.error_handler.handle_message_error(
                                error=e,
                                event_name=event,
                                namespace=namespace,
                                session_id=session_id,
                                user_id=user_id,
                                connection_id=connection_id
                            )
                        
                        # Record failed message
                        if self.monitor:
                            self.monitor.record_message_event(
                                event_name=event,
                                namespace=namespace,
                                processing_time_ms=duration_ms,
                                success=False
                            )
                        
                        raise
                
                return original_on(event, monitored_handler, namespace)
            
            if handler is None:
                return wrapper
            else:
                return wrapper(handler)
        
        # Replace socketio.on with monitored version
        socketio.on = monitored_on
    
    def get_production_status(self) -> Dict[str, Any]:
        """Get comprehensive production status"""
        
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'production_mode': self.production_config_manager.is_production_mode(),
            'ssl_enabled': self.production_config_manager.is_ssl_enabled(),
            'components': {
                'monitoring': self.monitor is not None,
                'backup': self.backup_manager is not None,
                'load_balancer': self.load_balancer_support is not None,
                'error_handling': self.error_handler is not None,
                'logging': self.production_logger is not None
            }
        }
        
        # Add component-specific status
        if self.monitor:
            status['monitoring'] = self.monitor.get_all_metrics()
        
        if self.load_balancer_support:
            status['load_balancer'] = self.load_balancer_support.get_health_status()
        
        if self.backup_manager:
            status['backup'] = {
                'enabled': True,
                'backups_available': len(self.backup_manager.list_backups())
            }
        
        return status
    
    def shutdown_production_components(self) -> None:
        """Shutdown production components gracefully"""
        
        try:
            # Stop backup manager
            if self.backup_manager:
                self.backup_manager.stop_automatic_backup()
            
            # Flush logs
            if self.production_logger:
                self.production_logger.flush_logs()
                self.production_logger.close()
            
            if self.production_logger:
                self.production_logger.log_system_event(
                    event_type="production_shutdown",
                    message="Production WebSocket components shutdown completed"
                )
                
        except Exception as e:
            logger.error(f"Error during production components shutdown: {e}")


def create_production_websocket_factory(config: Config,
                                      db_manager=None,
                                      session_manager=None,
                                      redis_client=None) -> ProductionWebSocketFactory:
    """
    Factory function to create production WebSocket factory
    
    Args:
        config: Application configuration
        db_manager: Database manager instance (optional)
        session_manager: Session manager instance (optional)
        redis_client: Redis client (optional)
    
    Returns:
        Configured production WebSocket factory
    """
    return ProductionWebSocketFactory(config, db_manager, session_manager, redis_client)