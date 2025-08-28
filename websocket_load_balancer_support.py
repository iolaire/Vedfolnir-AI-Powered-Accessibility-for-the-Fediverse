# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Load Balancer Support

This module provides load balancer compatibility and session affinity support
for WebSocket connections in production environments, including sticky sessions,
health checks, proxy header handling, and multi-instance coordination.
"""

import os
import json
import time
import uuid
import socket
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from flask import Flask, request, session, jsonify, make_response
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

from websocket_production_config import LoadBalancerConfig
from websocket_production_logging import ProductionWebSocketLogger, WebSocketLogLevel

# Try to import optional dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ServerStatus(Enum):
    """Server status for load balancing"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


class AffinityStrategy(Enum):
    """Session affinity strategies"""
    COOKIE_BASED = "cookie"
    IP_BASED = "ip"
    SESSION_BASED = "session"
    HYBRID = "hybrid"


@dataclass
class ServerInstance:
    """Server instance information"""
    server_id: str
    hostname: str
    port: int
    status: ServerStatus
    last_heartbeat: str
    connection_count: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    response_time_ms: float = 0.0
    error_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionAffinity:
    """Session affinity information"""
    session_id: str
    server_id: str
    user_id: Optional[int]
    client_ip: str
    created_at: str
    last_access: str
    connection_count: int = 0
    sticky_until: Optional[str] = None


class WebSocketLoadBalancerSupport:
    """
    Load balancer support for WebSocket connections
    
    Provides session affinity, health checks, proxy header handling,
    and multi-instance coordination for production deployments.
    """
    
    def __init__(self, config: LoadBalancerConfig,
                 logger: ProductionWebSocketLogger,
                 app: Optional[Flask] = None,
                 socketio: Optional[SocketIO] = None,
                 redis_client: Optional[Any] = None):
        """
        Initialize load balancer support
        
        Args:
            config: Load balancer configuration
            logger: Production WebSocket logger
            app: Flask application instance (optional)
            socketio: SocketIO instance (optional)
            redis_client: Redis client for coordination (optional)
        """
        self.config = config
        self.logger = logger
        self.app = app
        self.socketio = socketio
        self.redis_client = redis_client
        
        # Server identification
        self.server_id = self._generate_server_id()
        self.server_instance = self._create_server_instance()
        
        # Session affinity tracking
        self.session_affinities: Dict[str, SessionAffinity] = {}
        self.affinity_lock = threading.Lock()
        
        # Health check state
        self.health_status = ServerStatus.HEALTHY
        self.health_details = {}
        self.health_lock = threading.Lock()
        
        # Load balancer integration
        self.proxy_headers_configured = False
        
        # Setup components
        if self.app:
            self._setup_proxy_headers()
            self._setup_health_endpoints()
            self._setup_session_affinity()
        
        # Start background tasks
        self._start_heartbeat()
        self._start_affinity_cleanup()
    
    def _generate_server_id(self) -> str:
        """Generate unique server ID"""
        hostname = socket.gethostname()
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"{hostname}_{timestamp}_{unique_id}"
    
    def _create_server_instance(self) -> ServerInstance:
        """Create server instance information"""
        return ServerInstance(
            server_id=self.server_id,
            hostname=socket.gethostname(),
            port=int(os.getenv('FLASK_PORT', 5000)),
            status=ServerStatus.HEALTHY,
            last_heartbeat=datetime.now(timezone.utc).isoformat()
        )
    
    def _setup_proxy_headers(self) -> None:
        """Setup proxy header handling"""
        if not self.config.trust_proxy_headers or self.proxy_headers_configured:
            return
        
        try:
            # Configure ProxyFix middleware
            self.app.wsgi_app = ProxyFix(
                self.app.wsgi_app,
                x_for=1,  # Trust X-Forwarded-For
                x_proto=1,  # Trust X-Forwarded-Proto
                x_host=1,  # Trust X-Forwarded-Host
                x_prefix=1  # Trust X-Forwarded-Prefix
            )
            
            self.proxy_headers_configured = True
            
            self.logger.log_system_event(
                event_type="proxy_headers_configured",
                message="Proxy headers configured for load balancer support",
                metadata={'trusted_headers': self.config.proxy_headers}
            )
            
        except Exception as e:
            self.logger.log_error_event(
                event_type="proxy_headers_setup_failed",
                message=f"Failed to setup proxy headers: {str(e)}",
                exception=e
            )
    
    def _setup_health_endpoints(self) -> None:
        """Setup health check endpoints"""
        
        @self.app.route(self.config.health_check_path, methods=['GET'])
        def health_check():
            """Health check endpoint for load balancers"""
            health_result = self.get_health_status()
            
            response_data = {
                'status': health_result['status'],
                'server_id': self.server_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'connections': health_result.get('connection_count', 0),
                'uptime': health_result.get('uptime_seconds', 0)
            }
            
            # Add detailed health info if requested
            if request.args.get('detailed') == 'true':
                response_data.update(health_result)
            
            status_code = 200 if health_result['status'] == 'healthy' else 503
            return jsonify(response_data), status_code
        
        @self.app.route(f"{self.config.health_check_path}/ready", methods=['GET'])
        def readiness_check():
            """Readiness check for Kubernetes/container orchestration"""
            ready = (self.health_status in [ServerStatus.HEALTHY, ServerStatus.DEGRADED] and
                    self.socketio is not None)
            
            response_data = {
                'ready': ready,
                'server_id': self.server_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            status_code = 200 if ready else 503
            return jsonify(response_data), status_code
        
        @self.app.route(f"{self.config.health_check_path}/live", methods=['GET'])
        def liveness_check():
            """Liveness check for Kubernetes/container orchestration"""
            alive = self.health_status != ServerStatus.UNHEALTHY
            
            response_data = {
                'alive': alive,
                'server_id': self.server_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            status_code = 200 if alive else 503
            return jsonify(response_data), status_code
    
    def _setup_session_affinity(self) -> None:
        """Setup session affinity handling"""
        
        @self.app.before_request
        def handle_session_affinity():
            """Handle session affinity before each request"""
            if not self.config.session_affinity_enabled:
                return
            
            try:
                # Get client information
                client_ip = self._get_client_ip()
                session_id = session.get('session_id') or str(uuid.uuid4())
                user_id = session.get('user_id')
                
                # Check existing affinity
                affinity = self._get_session_affinity(session_id)
                
                if affinity:
                    # Update existing affinity
                    affinity.last_access = datetime.now(timezone.utc).isoformat()
                    affinity.connection_count += 1
                else:
                    # Create new affinity
                    affinity = SessionAffinity(
                        session_id=session_id,
                        server_id=self.server_id,
                        user_id=user_id,
                        client_ip=client_ip,
                        created_at=datetime.now(timezone.utc).isoformat(),
                        last_access=datetime.now(timezone.utc).isoformat(),
                        connection_count=1,
                        sticky_until=(datetime.now(timezone.utc) + 
                                    timedelta(seconds=self.config.session_affinity_timeout)).isoformat()
                    )
                    
                    with self.affinity_lock:
                        self.session_affinities[session_id] = affinity
                
                # Set affinity cookie
                if not request.cookies.get(self.config.session_affinity_cookie):
                    @self.app.after_request
                    def set_affinity_cookie(response):
                        response.set_cookie(
                            self.config.session_affinity_cookie,
                            self.server_id,
                            max_age=self.config.session_affinity_timeout,
                            httponly=True,
                            secure=request.is_secure,
                            samesite='Lax'
                        )
                        return response
                
            except Exception as e:
                self.logger.log_error_event(
                    event_type="session_affinity_error",
                    message=f"Session affinity handling failed: {str(e)}",
                    exception=e
                )
    
    def _get_client_ip(self) -> str:
        """Get client IP address considering proxy headers"""
        if self.config.trust_proxy_headers:
            # Check proxy headers in order of preference
            for header in self.config.proxy_headers:
                if header in request.headers:
                    ip = request.headers[header].split(',')[0].strip()
                    if ip:
                        return ip
        
        return request.remote_addr or 'unknown'
    
    def _get_session_affinity(self, session_id: str) -> Optional[SessionAffinity]:
        """Get session affinity information"""
        with self.affinity_lock:
            return self.session_affinities.get(session_id)
    
    def register_websocket_connection(self, session_id: str, connection_id: str,
                                    user_id: Optional[int] = None,
                                    namespace: Optional[str] = None) -> None:
        """Register WebSocket connection for load balancing"""
        
        # Update server instance connection count
        self.server_instance.connection_count += 1
        
        # Update session affinity
        affinity = self._get_session_affinity(session_id)
        if affinity:
            affinity.connection_count += 1
            affinity.last_access = datetime.now(timezone.utc).isoformat()
        
        # Register with Redis if available
        if self.redis_client and REDIS_AVAILABLE:
            try:
                connection_data = {
                    'server_id': self.server_id,
                    'session_id': session_id,
                    'connection_id': connection_id,
                    'user_id': user_id,
                    'namespace': namespace,
                    'connected_at': datetime.now(timezone.utc).isoformat()
                }
                
                self.redis_client.hset(
                    f"websocket:connections:{connection_id}",
                    mapping=connection_data
                )
                self.redis_client.expire(
                    f"websocket:connections:{connection_id}",
                    self.config.connection_timeout * 2
                )
                
            except Exception as e:
                self.logger.log_error_event(
                    event_type="redis_connection_registration_failed",
                    message=f"Failed to register connection in Redis: {str(e)}",
                    exception=e
                )
        
        self.logger.log_connection_event(
            event_type="connection_registered",
            message=f"WebSocket connection registered for load balancing",
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            metadata={
                'server_id': self.server_id,
                'namespace': namespace,
                'total_connections': self.server_instance.connection_count
            }
        )
    
    def unregister_websocket_connection(self, session_id: str, connection_id: str) -> None:
        """Unregister WebSocket connection from load balancing"""
        
        # Update server instance connection count
        self.server_instance.connection_count = max(0, self.server_instance.connection_count - 1)
        
        # Update session affinity
        affinity = self._get_session_affinity(session_id)
        if affinity:
            affinity.connection_count = max(0, affinity.connection_count - 1)
        
        # Unregister from Redis if available
        if self.redis_client and REDIS_AVAILABLE:
            try:
                self.redis_client.delete(f"websocket:connections:{connection_id}")
                
            except Exception as e:
                self.logger.log_error_event(
                    event_type="redis_connection_unregistration_failed",
                    message=f"Failed to unregister connection from Redis: {str(e)}",
                    exception=e
                )
        
        self.logger.log_connection_event(
            event_type="connection_unregistered",
            message=f"WebSocket connection unregistered from load balancing",
            session_id=session_id,
            connection_id=connection_id,
            metadata={
                'server_id': self.server_id,
                'remaining_connections': self.server_instance.connection_count
            }
        )
    
    def update_server_metrics(self, cpu_usage: float, memory_usage: float,
                            response_time_ms: float, error_rate: float) -> None:
        """Update server metrics for load balancing decisions"""
        
        self.server_instance.cpu_usage = cpu_usage
        self.server_instance.memory_usage = memory_usage
        self.server_instance.response_time_ms = response_time_ms
        self.server_instance.error_rate = error_rate
        self.server_instance.last_heartbeat = datetime.now(timezone.utc).isoformat()
        
        # Update health status based on metrics
        self._update_health_status()
        
        # Send heartbeat to Redis if available
        if self.redis_client and REDIS_AVAILABLE:
            try:
                server_data = {
                    'server_id': self.server_id,
                    'hostname': self.server_instance.hostname,
                    'port': self.server_instance.port,
                    'status': self.server_instance.status.value,
                    'connection_count': self.server_instance.connection_count,
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'response_time_ms': response_time_ms,
                    'error_rate': error_rate,
                    'last_heartbeat': self.server_instance.last_heartbeat
                }
                
                self.redis_client.hset(
                    f"websocket:servers:{self.server_id}",
                    mapping=server_data
                )
                self.redis_client.expire(
                    f"websocket:servers:{self.server_id}",
                    self.config.health_check_interval * 3
                )
                
            except Exception as e:
                self.logger.log_error_event(
                    event_type="redis_heartbeat_failed",
                    message=f"Failed to send heartbeat to Redis: {str(e)}",
                    exception=e
                )
    
    def _update_health_status(self) -> None:
        """Update health status based on current metrics"""
        
        with self.health_lock:
            # Determine status based on metrics
            if (self.server_instance.cpu_usage > 90 or 
                self.server_instance.memory_usage > 2000 or  # 2GB
                self.server_instance.error_rate > 10):
                self.health_status = ServerStatus.UNHEALTHY
            elif (self.server_instance.cpu_usage > 70 or 
                  self.server_instance.memory_usage > 1000 or  # 1GB
                  self.server_instance.error_rate > 1):
                self.health_status = ServerStatus.DEGRADED
            else:
                self.health_status = ServerStatus.HEALTHY
            
            self.server_instance.status = self.health_status
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        
        with self.health_lock:
            return {
                'status': self.health_status.value,
                'server_id': self.server_id,
                'hostname': self.server_instance.hostname,
                'port': self.server_instance.port,
                'connection_count': self.server_instance.connection_count,
                'cpu_usage': self.server_instance.cpu_usage,
                'memory_usage': self.server_instance.memory_usage,
                'response_time_ms': self.server_instance.response_time_ms,
                'error_rate': self.server_instance.error_rate,
                'last_heartbeat': self.server_instance.last_heartbeat,
                'uptime_seconds': int(time.time() - self._start_time) if hasattr(self, '_start_time') else 0
            }
    
    def get_server_list(self) -> List[Dict[str, Any]]:
        """Get list of all servers (from Redis if available)"""
        
        servers = []
        
        if self.redis_client and REDIS_AVAILABLE:
            try:
                server_keys = self.redis_client.keys("websocket:servers:*")
                
                for key in server_keys:
                    server_data = self.redis_client.hgetall(key)
                    if server_data:
                        # Convert bytes to strings
                        server_info = {k.decode(): v.decode() for k, v in server_data.items()}
                        servers.append(server_info)
                        
            except Exception as e:
                self.logger.log_error_event(
                    event_type="redis_server_list_failed",
                    message=f"Failed to get server list from Redis: {str(e)}",
                    exception=e
                )
        
        # Always include current server
        servers.append({
            'server_id': self.server_id,
            'hostname': self.server_instance.hostname,
            'port': str(self.server_instance.port),
            'status': self.server_instance.status.value,
            'connection_count': str(self.server_instance.connection_count),
            'cpu_usage': str(self.server_instance.cpu_usage),
            'memory_usage': str(self.server_instance.memory_usage),
            'response_time_ms': str(self.server_instance.response_time_ms),
            'error_rate': str(self.server_instance.error_rate),
            'last_heartbeat': self.server_instance.last_heartbeat
        })
        
        return servers
    
    def _start_heartbeat(self) -> None:
        """Start heartbeat thread"""
        self._start_time = time.time()
        
        def heartbeat_loop():
            while True:
                try:
                    # Update heartbeat timestamp
                    self.server_instance.last_heartbeat = datetime.now(timezone.utc).isoformat()
                    
                    # Send heartbeat if Redis is available
                    if self.redis_client and REDIS_AVAILABLE:
                        try:
                            heartbeat_data = {
                                'server_id': self.server_id,
                                'timestamp': self.server_instance.last_heartbeat,
                                'status': self.server_instance.status.value
                            }
                            
                            self.redis_client.hset(
                                f"websocket:heartbeat:{self.server_id}",
                                mapping=heartbeat_data
                            )
                            self.redis_client.expire(
                                f"websocket:heartbeat:{self.server_id}",
                                self.config.health_check_interval * 2
                            )
                            
                        except Exception as e:
                            self.logger.log_error_event(
                                event_type="heartbeat_redis_failed",
                                message=f"Failed to send heartbeat to Redis: {str(e)}",
                                exception=e
                            )
                    
                    time.sleep(self.config.health_check_interval)
                    
                except Exception as e:
                    self.logger.log_error_event(
                        event_type="heartbeat_error",
                        message=f"Heartbeat error: {str(e)}",
                        exception=e
                    )
                    time.sleep(30)  # Wait longer on error
        
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
    
    def _start_affinity_cleanup(self) -> None:
        """Start session affinity cleanup thread"""
        
        def cleanup_loop():
            while True:
                try:
                    current_time = datetime.now(timezone.utc)
                    expired_sessions = []
                    
                    with self.affinity_lock:
                        for session_id, affinity in self.session_affinities.items():
                            if affinity.sticky_until:
                                sticky_until = datetime.fromisoformat(affinity.sticky_until.replace('Z', '+00:00'))
                                if current_time > sticky_until:
                                    expired_sessions.append(session_id)
                        
                        # Remove expired sessions
                        for session_id in expired_sessions:
                            del self.session_affinities[session_id]
                    
                    if expired_sessions:
                        self.logger.log_system_event(
                            event_type="affinity_cleanup",
                            message=f"Cleaned up {len(expired_sessions)} expired session affinities"
                        )
                    
                    time.sleep(300)  # Clean up every 5 minutes
                    
                except Exception as e:
                    self.logger.log_error_event(
                        event_type="affinity_cleanup_error",
                        message=f"Session affinity cleanup error: {str(e)}",
                        exception=e
                    )
                    time.sleep(600)  # Wait longer on error
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def set_maintenance_mode(self, enabled: bool) -> None:
        """Set server maintenance mode"""
        
        with self.health_lock:
            if enabled:
                self.health_status = ServerStatus.MAINTENANCE
            else:
                self._update_health_status()  # Recalculate based on metrics
            
            self.server_instance.status = self.health_status
        
        self.logger.log_system_event(
            event_type="maintenance_mode_changed",
            message=f"Maintenance mode {'enabled' if enabled else 'disabled'}",
            metadata={'server_id': self.server_id}
        )
    
    def get_session_affinity_info(self) -> Dict[str, Any]:
        """Get session affinity information"""
        
        with self.affinity_lock:
            return {
                'total_affinities': len(self.session_affinities),
                'server_id': self.server_id,
                'affinity_timeout': self.config.session_affinity_timeout,
                'sticky_sessions_enabled': self.config.sticky_sessions,
                'affinities': [
                    {
                        'session_id': affinity.session_id,
                        'user_id': affinity.user_id,
                        'client_ip': affinity.client_ip,
                        'created_at': affinity.created_at,
                        'last_access': affinity.last_access,
                        'connection_count': affinity.connection_count
                    }
                    for affinity in self.session_affinities.values()
                ]
            }


def create_load_balancer_support(config: LoadBalancerConfig,
                               logger: ProductionWebSocketLogger,
                               app: Optional[Flask] = None,
                               socketio: Optional[SocketIO] = None,
                               redis_client: Optional[Any] = None) -> WebSocketLoadBalancerSupport:
    """
    Factory function to create WebSocket load balancer support
    
    Args:
        config: Load balancer configuration
        logger: Production WebSocket logger
        app: Flask application instance (optional)
        socketio: SocketIO instance (optional)
        redis_client: Redis client (optional)
    
    Returns:
        Configured WebSocket load balancer support
    """
    return WebSocketLoadBalancerSupport(config, logger, app, socketio, redis_client)