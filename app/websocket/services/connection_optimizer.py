# Copyright (C) 2025 iolaire mcfadden.
# Consolidated WebSocket Connection Management

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECOVERING = "recovering"

class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    GEOGRAPHIC = "geographic"

@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    client_id: str
    session_id: Optional[str]
    connect_time: datetime
    last_activity: datetime
    state: ConnectionState
    server_instance: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    message_count: int = 0
    bytes_transferred: int = 0
    error_count: int = 0
    recovery_attempts: int = 0

@dataclass
class ServerInstance:
    """Server instance information for load balancing"""
    instance_id: str
    host: str
    port: int
    active_connections: int = 0
    max_connections: int = 1000
    weight: float = 1.0
    is_healthy: bool = True
    last_health_check: datetime = field(default_factory=datetime.utcnow)

class ConsolidatedWebSocketConnectionOptimizer:
    """Consolidated WebSocket connection optimization with backup/recovery and load balancing"""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Connection tracking
        self._connections = {}
        self._connection_pools = defaultdict(list)
        self._server_instances = {}
        
        # Load balancing
        self._load_balancing_strategy = LoadBalancingStrategy(
            self.config.get('load_balancing_strategy', 'round_robin')
        )
        self._current_server_index = 0
        
        # Connection optimization settings
        self._optimization_settings = {
            'max_connections_per_server': self.config.get('max_connections_per_server', 1000),
            'connection_timeout': self.config.get('connection_timeout', 30),
            'heartbeat_interval': self.config.get('heartbeat_interval', 30),
            'max_recovery_attempts': self.config.get('max_recovery_attempts', 3),
            'recovery_delay': self.config.get('recovery_delay', 5),
            'health_check_interval': self.config.get('health_check_interval', 60)
        }
        
        # Backup and recovery
        self._backup_servers = []
        self._recovery_queue = deque()
        
        # Threading
        self._lock = threading.Lock()
        self._optimization_thread = None
        self._running = False
    
    def start_optimization(self):
        """Start connection optimization background tasks"""
        try:
            self._running = True
            self._optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
            self._optimization_thread.start()
            self.logger.info("WebSocket connection optimization started")
        except Exception as e:
            self.logger.error(f"Error starting optimization: {e}")
    
    def stop_optimization(self):
        """Stop connection optimization"""
        try:
            self._running = False
            if self._optimization_thread:
                self._optimization_thread.join(timeout=5)
            self.logger.info("WebSocket connection optimization stopped")
        except Exception as e:
            self.logger.error(f"Error stopping optimization: {e}")
    
    def register_connection(self, client_id: str, session_id: Optional[str] = None, 
                          user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> bool:
        """Register new WebSocket connection"""
        try:
            with self._lock:
                # Select optimal server
                server_instance = self._select_optimal_server()
                if not server_instance:
                    self.logger.warning("No available server instances for new connection")
                    return False
                
                # Create connection info
                connection_info = ConnectionInfo(
                    client_id=client_id,
                    session_id=session_id,
                    connect_time=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    state=ConnectionState.CONNECTING,
                    server_instance=server_instance.instance_id,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
                
                # Register connection
                self._connections[client_id] = connection_info
                self._connection_pools[server_instance.instance_id].append(client_id)
                server_instance.active_connections += 1
                
                self.logger.debug(f"Registered connection {client_id} on server {server_instance.instance_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error registering connection: {e}")
            return False
    
    def update_connection_state(self, client_id: str, state: ConnectionState):
        """Update connection state"""
        try:
            with self._lock:
                if client_id in self._connections:
                    self._connections[client_id].state = state
                    self._connections[client_id].last_activity = datetime.utcnow()
                    
                    # Handle state-specific logic
                    if state == ConnectionState.ERROR:
                        self._handle_connection_error(client_id)
                    elif state == ConnectionState.CONNECTED:
                        self._handle_connection_success(client_id)
                        
        except Exception as e:
            self.logger.error(f"Error updating connection state: {e}")
    
    def unregister_connection(self, client_id: str):
        """Unregister WebSocket connection"""
        try:
            with self._lock:
                if client_id in self._connections:
                    connection_info = self._connections[client_id]
                    
                    # Update server instance
                    if connection_info.server_instance in self._server_instances:
                        server = self._server_instances[connection_info.server_instance]
                        server.active_connections = max(0, server.active_connections - 1)
                    
                    # Remove from connection pool
                    if connection_info.server_instance in self._connection_pools:
                        pool = self._connection_pools[connection_info.server_instance]
                        if client_id in pool:
                            pool.remove(client_id)
                    
                    # Remove connection
                    del self._connections[client_id]
                    
                    self.logger.debug(f"Unregistered connection {client_id}")
                    
        except Exception as e:
            self.logger.error(f"Error unregistering connection: {e}")
    
    def _select_optimal_server(self) -> Optional[ServerInstance]:
        """Select optimal server instance based on load balancing strategy"""
        try:
            available_servers = [
                server for server in self._server_instances.values()
                if server.is_healthy and server.active_connections < server.max_connections
            ]
            
            if not available_servers:
                return None
            
            if self._load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin_selection(available_servers)
            elif self._load_balancing_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return self._least_connections_selection(available_servers)
            elif self._load_balancing_strategy == LoadBalancingStrategy.WEIGHTED:
                return self._weighted_selection(available_servers)
            else:
                return available_servers[0]  # Default to first available
                
        except Exception as e:
            self.logger.error(f"Error selecting optimal server: {e}")
            return None
    
    def _round_robin_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Round-robin server selection"""
        server = servers[self._current_server_index % len(servers)]
        self._current_server_index += 1
        return server
    
    def _least_connections_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Least connections server selection"""
        return min(servers, key=lambda s: s.active_connections)
    
    def _weighted_selection(self, servers: List[ServerInstance]) -> ServerInstance:
        """Weighted server selection"""
        # Calculate weighted scores (lower is better)
        scored_servers = []
        for server in servers:
            load_ratio = server.active_connections / server.max_connections
            score = load_ratio / server.weight
            scored_servers.append((score, server))
        
        return min(scored_servers, key=lambda x: x[0])[1]
    
    def _handle_connection_error(self, client_id: str):
        """Handle connection error"""
        try:
            if client_id in self._connections:
                connection_info = self._connections[client_id]
                connection_info.error_count += 1
                
                # Add to recovery queue if under max attempts
                if connection_info.recovery_attempts < self._optimization_settings['max_recovery_attempts']:
                    self._recovery_queue.append(client_id)
                    self.logger.info(f"Added connection {client_id} to recovery queue")
                else:
                    self.logger.warning(f"Connection {client_id} exceeded max recovery attempts")
                    
        except Exception as e:
            self.logger.error(f"Error handling connection error: {e}")
    
    def _handle_connection_success(self, client_id: str):
        """Handle successful connection"""
        try:
            if client_id in self._connections:
                connection_info = self._connections[client_id]
                connection_info.recovery_attempts = 0  # Reset recovery attempts
                self.logger.debug(f"Connection {client_id} successfully established")
                
        except Exception as e:
            self.logger.error(f"Error handling connection success: {e}")
    
    def add_server_instance(self, instance_id: str, host: str, port: int, 
                           max_connections: int = 1000, weight: float = 1.0):
        """Add server instance for load balancing"""
        try:
            with self._lock:
                server_instance = ServerInstance(
                    instance_id=instance_id,
                    host=host,
                    port=port,
                    max_connections=max_connections,
                    weight=weight
                )
                
                self._server_instances[instance_id] = server_instance
                self.logger.info(f"Added server instance: {instance_id} ({host}:{port})")
                
        except Exception as e:
            self.logger.error(f"Error adding server instance: {e}")
    
    def remove_server_instance(self, instance_id: str):
        """Remove server instance"""
        try:
            with self._lock:
                if instance_id in self._server_instances:
                    # Move connections to other servers
                    self._migrate_connections_from_server(instance_id)
                    
                    # Remove server
                    del self._server_instances[instance_id]
                    if instance_id in self._connection_pools:
                        del self._connection_pools[instance_id]
                    
                    self.logger.info(f"Removed server instance: {instance_id}")
                    
        except Exception as e:
            self.logger.error(f"Error removing server instance: {e}")
    
    def _migrate_connections_from_server(self, instance_id: str):
        """Migrate connections from a server instance"""
        try:
            if instance_id not in self._connection_pools:
                return
            
            connections_to_migrate = self._connection_pools[instance_id].copy()
            
            for client_id in connections_to_migrate:
                if client_id in self._connections:
                    # Find new server
                    new_server = self._select_optimal_server()
                    if new_server:
                        # Update connection info
                        self._connections[client_id].server_instance = new_server.instance_id
                        self._connections[client_id].state = ConnectionState.RECOVERING
                        
                        # Move to new pool
                        self._connection_pools[new_server.instance_id].append(client_id)
                        new_server.active_connections += 1
                        
                        self.logger.info(f"Migrated connection {client_id} to server {new_server.instance_id}")
            
            # Clear old pool
            self._connection_pools[instance_id] = []
            
        except Exception as e:
            self.logger.error(f"Error migrating connections: {e}")
    
    def _optimization_loop(self):
        """Main optimization loop"""
        while self._running:
            try:
                # Process recovery queue
                self._process_recovery_queue()
                
                # Perform health checks
                self._perform_health_checks()
                
                # Optimize connections
                self._optimize_connections()
                
                # Clean up stale connections
                self._cleanup_stale_connections()
                
                time.sleep(10)  # Run every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                time.sleep(5)
    
    def _process_recovery_queue(self):
        """Process connection recovery queue"""
        try:
            while self._recovery_queue and self._running:
                client_id = self._recovery_queue.popleft()
                
                if client_id in self._connections:
                    connection_info = self._connections[client_id]
                    
                    # Attempt recovery
                    if self._attempt_connection_recovery(client_id):
                        connection_info.state = ConnectionState.RECOVERING
                        connection_info.recovery_attempts += 1
                    else:
                        # Recovery failed, remove connection
                        self.unregister_connection(client_id)
                
        except Exception as e:
            self.logger.error(f"Error processing recovery queue: {e}")
    
    def _attempt_connection_recovery(self, client_id: str) -> bool:
        """Attempt to recover a failed connection"""
        try:
            # This would implement actual connection recovery logic
            # For now, we'll simulate recovery attempt
            self.logger.info(f"Attempting recovery for connection {client_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error attempting connection recovery: {e}")
            return False
    
    def _perform_health_checks(self):
        """Perform health checks on server instances"""
        try:
            for server in self._server_instances.values():
                # Simple health check - in production, this would ping the server
                server.is_healthy = True  # Placeholder
                server.last_health_check = datetime.utcnow()
                
        except Exception as e:
            self.logger.error(f"Error performing health checks: {e}")
    
    def _optimize_connections(self):
        """Optimize connection distribution"""
        try:
            # Check for overloaded servers and rebalance if needed
            for server in self._server_instances.values():
                load_ratio = server.active_connections / server.max_connections
                
                if load_ratio > 0.9:  # 90% capacity
                    self.logger.warning(f"Server {server.instance_id} is at {load_ratio:.1%} capacity")
                    # Could implement connection migration here
                    
        except Exception as e:
            self.logger.error(f"Error optimizing connections: {e}")
    
    def _cleanup_stale_connections(self):
        """Clean up stale connections"""
        try:
            now = datetime.utcnow()
            timeout = timedelta(seconds=self._optimization_settings['connection_timeout'])
            
            stale_connections = []
            
            for client_id, connection_info in self._connections.items():
                if now - connection_info.last_activity > timeout:
                    stale_connections.append(client_id)
            
            for client_id in stale_connections:
                self.logger.info(f"Cleaning up stale connection: {client_id}")
                self.unregister_connection(client_id)
                
        except Exception as e:
            self.logger.error(f"Error cleaning up stale connections: {e}")
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        try:
            with self._lock:
                total_connections = len(self._connections)
                
                # Count by state
                state_counts = defaultdict(int)
                for connection in self._connections.values():
                    state_counts[connection.state.value] += 1
                
                # Server statistics
                server_stats = {}
                for server_id, server in self._server_instances.items():
                    server_stats[server_id] = {
                        'active_connections': server.active_connections,
                        'max_connections': server.max_connections,
                        'load_percentage': (server.active_connections / server.max_connections) * 100,
                        'is_healthy': server.is_healthy,
                        'weight': server.weight
                    }
                
                return {
                    'total_connections': total_connections,
                    'connections_by_state': dict(state_counts),
                    'server_instances': len(self._server_instances),
                    'server_statistics': server_stats,
                    'recovery_queue_size': len(self._recovery_queue),
                    'load_balancing_strategy': self._load_balancing_strategy.value,
                    'optimization_running': self._running
                }
                
        except Exception as e:
            self.logger.error(f"Error getting connection statistics: {e}")
            return {'error': str(e)}
