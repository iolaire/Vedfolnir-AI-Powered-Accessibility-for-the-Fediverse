# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification WebSocket Recovery System

Provides automatic recovery mechanisms for WebSocket connections in the notification system,
including connection monitoring, failure detection, and automatic reconnection strategies.
"""

import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque

from websocket_factory import WebSocketFactory
from websocket_namespace_manager import WebSocketNamespaceManager
from websocket_auth_handler import WebSocketAuthHandler
from notification_system_monitor import NotificationSystemMonitor

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    SUSPENDED = "suspended"


class RecoveryStrategy(Enum):
    """Recovery strategy types"""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class ConnectionHealth:
    """Connection health information"""
    connection_id: str
    user_id: int
    namespace: str
    state: ConnectionState
    last_activity: datetime
    failure_count: int
    recovery_attempts: int
    last_recovery_attempt: Optional[datetime]
    latency: float
    error_rate: float
    timestamp: datetime


@dataclass
class RecoveryAction:
    """Recovery action information"""
    action_id: str
    connection_id: str
    strategy: RecoveryStrategy
    attempt_count: int
    scheduled_time: datetime
    max_attempts: int
    backoff_multiplier: float
    success: Optional[bool] = None
    error_message: Optional[str] = None


class NotificationWebSocketRecovery:
    """
    WebSocket connection recovery system for notifications
    
    Monitors WebSocket connections, detects failures, and implements
    automatic recovery strategies to maintain reliable notification delivery.
    """
    
    def __init__(self, websocket_factory: WebSocketFactory,
                 namespace_manager: WebSocketNamespaceManager,
                 auth_handler: WebSocketAuthHandler,
                 monitor: NotificationSystemMonitor,
                 recovery_interval: int = 30,
                 max_recovery_attempts: int = 5):
        """
        Initialize WebSocket recovery system
        
        Args:
            websocket_factory: WebSocket factory instance
            namespace_manager: WebSocket namespace manager
            auth_handler: WebSocket authentication handler
            monitor: Notification system monitor
            recovery_interval: Recovery check interval in seconds
            max_recovery_attempts: Maximum recovery attempts per connection
        """
        self.websocket_factory = websocket_factory
        self.namespace_manager = namespace_manager
        self.auth_handler = auth_handler
        self.monitor = monitor
        self.recovery_interval = recovery_interval
        self.max_recovery_attempts = max_recovery_attempts
        
        # Recovery state
        self._recovery_active = False
        self._recovery_thread = None
        
        # Connection tracking
        self._connection_health = {}  # connection_id -> ConnectionHealth
        self._recovery_queue = deque()  # Queue of RecoveryAction objects
        self._failed_connections = set()  # Set of failed connection IDs
        self._suspended_connections = set()  # Set of suspended connection IDs
        
        # Recovery strategies configuration
        self._recovery_strategies = {
            RecoveryStrategy.IMMEDIATE: {
                'initial_delay': 0,
                'max_delay': 0,
                'backoff_multiplier': 1.0,
                'max_attempts': 3
            },
            RecoveryStrategy.EXPONENTIAL_BACKOFF: {
                'initial_delay': 1,
                'max_delay': 300,  # 5 minutes
                'backoff_multiplier': 2.0,
                'max_attempts': 5
            },
            RecoveryStrategy.LINEAR_BACKOFF: {
                'initial_delay': 5,
                'max_delay': 60,   # 1 minute
                'backoff_multiplier': 1.0,
                'max_attempts': 10
            },
            RecoveryStrategy.CIRCUIT_BREAKER: {
                'initial_delay': 30,
                'max_delay': 600,  # 10 minutes
                'backoff_multiplier': 1.5,
                'max_attempts': 3
            }
        }
        
        # Health check thresholds
        self.health_thresholds = {
            'max_latency': 5000,        # 5 seconds
            'max_error_rate': 0.1,      # 10% error rate
            'max_inactivity': 300,      # 5 minutes
            'max_failure_count': 3,     # 3 consecutive failures
            'recovery_timeout': 30      # 30 seconds for recovery
        }
        
        # Statistics
        self._recovery_stats = {
            'total_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'connections_monitored': 0,
            'average_recovery_time': 0
        }
        
        # Recovery callbacks
        self._recovery_callbacks = []
        
        logger.info("WebSocket recovery system initialized")
    
    def start_recovery_monitoring(self) -> None:
        """Start continuous recovery monitoring"""
        if self._recovery_active:
            logger.warning("Recovery monitoring already active")
            return
        
        self._recovery_active = True
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True,
            name="WebSocketRecovery"
        )
        self._recovery_thread.start()
        logger.info("Started WebSocket recovery monitoring")
    
    def stop_recovery_monitoring(self) -> None:
        """Stop recovery monitoring"""
        self._recovery_active = False
        if self._recovery_thread:
            self._recovery_thread.join(timeout=5)
        logger.info("Stopped WebSocket recovery monitoring")
    
    def register_recovery_callback(self, callback: Callable[[str, bool, str], None]) -> None:
        """
        Register callback for recovery events
        
        Args:
            callback: Function called with (connection_id, success, message)
        """
        self._recovery_callbacks.append(callback)
    
    def check_connection_health(self, connection_id: str) -> Optional[ConnectionHealth]:
        """
        Check health of a specific connection
        
        Args:
            connection_id: Connection ID to check
            
        Returns:
            ConnectionHealth object or None if not found
        """
        try:
            # Get connection from namespace manager
            connection = self.namespace_manager._connections.get(connection_id)
            if not connection:
                return None
            
            # Calculate health metrics
            current_time = datetime.now(timezone.utc)
            last_activity = getattr(connection, 'last_activity', current_time)
            failure_count = getattr(connection, 'failure_count', 0)
            
            # Determine connection state
            if connection.connected:
                if connection_id in self._suspended_connections:
                    state = ConnectionState.SUSPENDED
                elif connection_id in self._failed_connections:
                    state = ConnectionState.FAILED
                else:
                    state = ConnectionState.CONNECTED
            else:
                if connection_id in self._recovery_queue:
                    state = ConnectionState.RECONNECTING
                else:
                    state = ConnectionState.DISCONNECTED
            
            # Calculate latency and error rate (simplified)
            latency = getattr(connection, 'latency', 0)
            error_rate = getattr(connection, 'error_rate', 0)
            
            health = ConnectionHealth(
                connection_id=connection_id,
                user_id=getattr(connection, 'user_id', 0),
                namespace=connection.namespace,
                state=state,
                last_activity=last_activity,
                failure_count=failure_count,
                recovery_attempts=getattr(connection, 'recovery_attempts', 0),
                last_recovery_attempt=getattr(connection, 'last_recovery_attempt', None),
                latency=latency,
                error_rate=error_rate,
                timestamp=current_time
            )
            
            self._connection_health[connection_id] = health
            return health
            
        except Exception as e:
            logger.error(f"Failed to check connection health for {connection_id}: {e}")
            return None
    
    def trigger_connection_recovery(self, connection_id: str, 
                                  strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF) -> bool:
        """
        Trigger recovery for a specific connection
        
        Args:
            connection_id: Connection ID to recover
            strategy: Recovery strategy to use
            
        Returns:
            True if recovery was initiated
        """
        try:
            # Check if connection exists
            connection = self.namespace_manager._connections.get(connection_id)
            if not connection:
                logger.warning(f"Connection {connection_id} not found for recovery")
                return False
            
            # Check if already in recovery
            existing_recovery = next(
                (action for action in self._recovery_queue if action.connection_id == connection_id),
                None
            )
            
            if existing_recovery:
                logger.info(f"Connection {connection_id} already in recovery queue")
                return True
            
            # Create recovery action
            strategy_config = self._recovery_strategies[strategy]
            current_time = datetime.now(timezone.utc)
            
            recovery_action = RecoveryAction(
                action_id=f"recovery_{connection_id}_{int(time.time())}",
                connection_id=connection_id,
                strategy=strategy,
                attempt_count=0,
                scheduled_time=current_time,
                max_attempts=strategy_config['max_attempts'],
                backoff_multiplier=strategy_config['backoff_multiplier']
            )
            
            self._recovery_queue.append(recovery_action)
            logger.info(f"Scheduled recovery for connection {connection_id} using {strategy.value} strategy")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger recovery for connection {connection_id}: {e}")
            return False
    
    def suspend_connection(self, connection_id: str, reason: str = "Health check failure") -> bool:
        """
        Suspend a connection temporarily
        
        Args:
            connection_id: Connection ID to suspend
            reason: Reason for suspension
            
        Returns:
            True if connection was suspended
        """
        try:
            connection = self.namespace_manager._connections.get(connection_id)
            if not connection:
                return False
            
            self._suspended_connections.add(connection_id)
            
            # Notify callbacks
            for callback in self._recovery_callbacks:
                try:
                    callback(connection_id, False, f"Connection suspended: {reason}")
                except Exception as e:
                    logger.error(f"Recovery callback failed: {e}")
            
            logger.warning(f"Suspended connection {connection_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to suspend connection {connection_id}: {e}")
            return False
    
    def resume_connection(self, connection_id: str) -> bool:
        """
        Resume a suspended connection
        
        Args:
            connection_id: Connection ID to resume
            
        Returns:
            True if connection was resumed
        """
        try:
            if connection_id in self._suspended_connections:
                self._suspended_connections.remove(connection_id)
                
                # Trigger recovery to re-establish connection
                self.trigger_connection_recovery(connection_id, RecoveryStrategy.IMMEDIATE)
                
                logger.info(f"Resumed connection {connection_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to resume connection {connection_id}: {e}")
            return False
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get recovery system statistics
        
        Returns:
            Dictionary containing recovery statistics
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Count connections by state
            state_counts = defaultdict(int)
            for health in self._connection_health.values():
                state_counts[health.state.value] += 1
            
            # Get recovery queue status
            pending_recoveries = len(self._recovery_queue)
            active_recoveries = len([
                action for action in self._recovery_queue
                if action.scheduled_time <= current_time
            ])
            
            return {
                'recovery_active': self._recovery_active,
                'connections_monitored': len(self._connection_health),
                'connection_states': dict(state_counts),
                'failed_connections': len(self._failed_connections),
                'suspended_connections': len(self._suspended_connections),
                'pending_recoveries': pending_recoveries,
                'active_recoveries': active_recoveries,
                'recovery_stats': self._recovery_stats.copy(),
                'health_thresholds': self.health_thresholds.copy(),
                'timestamp': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get recovery statistics: {e}")
            return {'error': str(e)}
    
    def get_connection_health_report(self) -> Dict[str, Any]:
        """
        Get detailed connection health report
        
        Returns:
            Dictionary containing connection health information
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Update health for all connections
            for connection_id in list(self.namespace_manager._connections.keys()):
                self.check_connection_health(connection_id)
            
            # Categorize connections by health
            healthy_connections = []
            unhealthy_connections = []
            critical_connections = []
            
            for health in self._connection_health.values():
                if health.state == ConnectionState.CONNECTED and health.error_rate < 0.05:
                    healthy_connections.append(health)
                elif health.state in [ConnectionState.FAILED, ConnectionState.SUSPENDED]:
                    critical_connections.append(health)
                else:
                    unhealthy_connections.append(health)
            
            return {
                'total_connections': len(self._connection_health),
                'healthy_connections': len(healthy_connections),
                'unhealthy_connections': len(unhealthy_connections),
                'critical_connections': len(critical_connections),
                'health_details': {
                    'healthy': [
                        {
                            'connection_id': h.connection_id,
                            'user_id': h.user_id,
                            'namespace': h.namespace,
                            'latency': h.latency,
                            'last_activity': h.last_activity.isoformat()
                        }
                        for h in healthy_connections[:10]  # Limit to 10 for brevity
                    ],
                    'unhealthy': [
                        {
                            'connection_id': h.connection_id,
                            'user_id': h.user_id,
                            'namespace': h.namespace,
                            'state': h.state.value,
                            'failure_count': h.failure_count,
                            'error_rate': h.error_rate,
                            'last_activity': h.last_activity.isoformat()
                        }
                        for h in unhealthy_connections
                    ],
                    'critical': [
                        {
                            'connection_id': h.connection_id,
                            'user_id': h.user_id,
                            'namespace': h.namespace,
                            'state': h.state.value,
                            'failure_count': h.failure_count,
                            'recovery_attempts': h.recovery_attempts,
                            'last_recovery_attempt': h.last_recovery_attempt.isoformat() if h.last_recovery_attempt else None
                        }
                        for h in critical_connections
                    ]
                },
                'timestamp': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection health report: {e}")
            return {'error': str(e)}
    
    def _recovery_loop(self) -> None:
        """Main recovery monitoring loop"""
        logger.info("Started WebSocket recovery monitoring loop")
        
        while self._recovery_active:
            try:
                start_time = time.time()
                
                # Check health of all connections
                self._check_all_connections_health()
                
                # Process recovery queue
                self._process_recovery_queue()
                
                # Clean up old health records
                self._cleanup_old_health_records()
                
                # Update statistics
                self._update_recovery_statistics()
                
                # Calculate sleep time
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.recovery_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in recovery monitoring loop: {e}")
                time.sleep(self.recovery_interval)
    
    def _check_all_connections_health(self) -> None:
        """Check health of all active connections"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for connection_id in list(self.namespace_manager._connections.keys()):
                health = self.check_connection_health(connection_id)
                
                if not health:
                    continue
                
                # Check for health issues
                needs_recovery = False
                recovery_strategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
                
                # Check latency threshold
                if health.latency > self.health_thresholds['max_latency']:
                    logger.warning(f"Connection {connection_id} has high latency: {health.latency}ms")
                    needs_recovery = True
                    recovery_strategy = RecoveryStrategy.LINEAR_BACKOFF
                
                # Check error rate threshold
                if health.error_rate > self.health_thresholds['max_error_rate']:
                    logger.warning(f"Connection {connection_id} has high error rate: {health.error_rate:.2%}")
                    needs_recovery = True
                    recovery_strategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
                
                # Check inactivity threshold
                inactivity_duration = (current_time - health.last_activity).total_seconds()
                if inactivity_duration > self.health_thresholds['max_inactivity']:
                    logger.warning(f"Connection {connection_id} inactive for {inactivity_duration}s")
                    needs_recovery = True
                    recovery_strategy = RecoveryStrategy.IMMEDIATE
                
                # Check failure count threshold
                if health.failure_count >= self.health_thresholds['max_failure_count']:
                    logger.error(f"Connection {connection_id} has {health.failure_count} failures")
                    self._failed_connections.add(connection_id)
                    needs_recovery = True
                    recovery_strategy = RecoveryStrategy.CIRCUIT_BREAKER
                
                # Trigger recovery if needed
                if needs_recovery and connection_id not in self._suspended_connections:
                    self.trigger_connection_recovery(connection_id, recovery_strategy)
                    
        except Exception as e:
            logger.error(f"Failed to check all connections health: {e}")
    
    def _process_recovery_queue(self) -> None:
        """Process pending recovery actions"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Process actions that are ready
            while self._recovery_queue:
                action = self._recovery_queue[0]
                
                if action.scheduled_time > current_time:
                    break  # Not ready yet
                
                # Remove from queue
                self._recovery_queue.popleft()
                
                # Execute recovery action
                success = self._execute_recovery_action(action)
                
                # Update statistics
                self._recovery_stats['total_recoveries'] += 1
                if success:
                    self._recovery_stats['successful_recoveries'] += 1
                else:
                    self._recovery_stats['failed_recoveries'] += 1
                
                # Schedule retry if failed and attempts remaining
                if not success and action.attempt_count < action.max_attempts:
                    self._schedule_retry(action)
                
        except Exception as e:
            logger.error(f"Failed to process recovery queue: {e}")
    
    def _execute_recovery_action(self, action: RecoveryAction) -> bool:
        """
        Execute a recovery action
        
        Args:
            action: RecoveryAction to execute
            
        Returns:
            True if recovery was successful
        """
        try:
            action.attempt_count += 1
            recovery_start_time = time.time()
            
            logger.info(f"Executing recovery action {action.action_id} (attempt {action.attempt_count})")
            
            # Get connection
            connection = self.namespace_manager._connections.get(action.connection_id)
            if not connection:
                action.success = False
                action.error_message = "Connection not found"
                return False
            
            # Attempt to recover connection based on strategy
            if action.strategy == RecoveryStrategy.IMMEDIATE:
                success = self._immediate_recovery(connection)
            elif action.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                success = self._exponential_backoff_recovery(connection, action)
            elif action.strategy == RecoveryStrategy.LINEAR_BACKOFF:
                success = self._linear_backoff_recovery(connection, action)
            elif action.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                success = self._circuit_breaker_recovery(connection, action)
            else:
                success = False
                action.error_message = f"Unknown recovery strategy: {action.strategy}"
            
            # Update action result
            action.success = success
            recovery_time = (time.time() - recovery_start_time) * 1000  # Convert to ms
            
            # Update average recovery time
            current_avg = self._recovery_stats['average_recovery_time']
            total_recoveries = self._recovery_stats['total_recoveries']
            self._recovery_stats['average_recovery_time'] = (
                (current_avg * total_recoveries + recovery_time) / (total_recoveries + 1)
            )
            
            # Notify callbacks
            for callback in self._recovery_callbacks:
                try:
                    callback(
                        action.connection_id,
                        success,
                        f"Recovery {'successful' if success else 'failed'} using {action.strategy.value}"
                    )
                except Exception as e:
                    logger.error(f"Recovery callback failed: {e}")
            
            if success:
                logger.info(f"Recovery successful for connection {action.connection_id}")
                # Remove from failed connections if successful
                self._failed_connections.discard(action.connection_id)
            else:
                logger.warning(f"Recovery failed for connection {action.connection_id}: {action.error_message}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute recovery action {action.action_id}: {e}")
            action.success = False
            action.error_message = str(e)
            return False
    
    def _immediate_recovery(self, connection) -> bool:
        """Immediate recovery strategy"""
        try:
            # Simply try to reconnect immediately
            if hasattr(connection, 'reconnect'):
                return connection.reconnect()
            else:
                # Fallback: mark as needing reconnection
                connection.connected = False
                return True
                
        except Exception as e:
            logger.error(f"Immediate recovery failed: {e}")
            return False
    
    def _exponential_backoff_recovery(self, connection, action: RecoveryAction) -> bool:
        """Exponential backoff recovery strategy"""
        try:
            # Calculate delay for next attempt
            strategy_config = self._recovery_strategies[RecoveryStrategy.EXPONENTIAL_BACKOFF]
            delay = min(
                strategy_config['initial_delay'] * (strategy_config['backoff_multiplier'] ** (action.attempt_count - 1)),
                strategy_config['max_delay']
            )
            
            # For this attempt, just try to reconnect
            if hasattr(connection, 'reconnect'):
                return connection.reconnect()
            else:
                connection.connected = False
                return True
                
        except Exception as e:
            logger.error(f"Exponential backoff recovery failed: {e}")
            return False
    
    def _linear_backoff_recovery(self, connection, action: RecoveryAction) -> bool:
        """Linear backoff recovery strategy"""
        try:
            # Linear backoff - same delay each time
            if hasattr(connection, 'reconnect'):
                return connection.reconnect()
            else:
                connection.connected = False
                return True
                
        except Exception as e:
            logger.error(f"Linear backoff recovery failed: {e}")
            return False
    
    def _circuit_breaker_recovery(self, connection, action: RecoveryAction) -> bool:
        """Circuit breaker recovery strategy"""
        try:
            # Circuit breaker - longer delays, fewer attempts
            if hasattr(connection, 'reconnect'):
                success = connection.reconnect()
                if not success:
                    # Suspend connection if circuit breaker recovery fails
                    self.suspend_connection(action.connection_id, "Circuit breaker recovery failed")
                return success
            else:
                connection.connected = False
                return True
                
        except Exception as e:
            logger.error(f"Circuit breaker recovery failed: {e}")
            return False
    
    def _schedule_retry(self, action: RecoveryAction) -> None:
        """Schedule a retry for a failed recovery action"""
        try:
            strategy_config = self._recovery_strategies[action.strategy]
            
            # Calculate delay based on strategy
            if action.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                delay = min(
                    strategy_config['initial_delay'] * (strategy_config['backoff_multiplier'] ** action.attempt_count),
                    strategy_config['max_delay']
                )
            elif action.strategy == RecoveryStrategy.LINEAR_BACKOFF:
                delay = strategy_config['initial_delay'] * action.attempt_count
            else:
                delay = strategy_config['initial_delay']
            
            # Schedule next attempt
            action.scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=delay)
            self._recovery_queue.append(action)
            
            logger.info(f"Scheduled retry for {action.connection_id} in {delay} seconds")
            
        except Exception as e:
            logger.error(f"Failed to schedule retry: {e}")
    
    def _cleanup_old_health_records(self) -> None:
        """Clean up old health records"""
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(hours=1)  # Keep 1 hour of history
            
            # Remove old health records
            old_connections = [
                conn_id for conn_id, health in self._connection_health.items()
                if health.timestamp < cutoff_time
            ]
            
            for conn_id in old_connections:
                del self._connection_health[conn_id]
                
            if old_connections:
                logger.debug(f"Cleaned up {len(old_connections)} old health records")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old health records: {e}")
    
    def _update_recovery_statistics(self) -> None:
        """Update recovery statistics"""
        try:
            self._recovery_stats['connections_monitored'] = len(self._connection_health)
            
        except Exception as e:
            logger.error(f"Failed to update recovery statistics: {e}")


def create_websocket_recovery_system(websocket_factory: WebSocketFactory,
                                   namespace_manager: WebSocketNamespaceManager,
                                   auth_handler: WebSocketAuthHandler,
                                   monitor: NotificationSystemMonitor) -> NotificationWebSocketRecovery:
    """
    Create WebSocket recovery system
    
    Args:
        websocket_factory: WebSocket factory instance
        namespace_manager: WebSocket namespace manager
        auth_handler: WebSocket authentication handler
        monitor: Notification system monitor
        
    Returns:
        NotificationWebSocketRecovery instance
    """
    return NotificationWebSocketRecovery(
        websocket_factory=websocket_factory,
        namespace_manager=namespace_manager,
        auth_handler=auth_handler,
        monitor=monitor
    )