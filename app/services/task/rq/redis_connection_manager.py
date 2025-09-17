# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Connection Manager for RQ

Manages Redis connections for RQ operations with connection pooling,
health monitoring, and automatic reconnection capabilities.
"""

import logging
import time
from typing import Optional, Dict, Any
import redis
from redis.connection import ConnectionPool
from .rq_config import RQConfig
from .redis_health_monitor import RedisHealthMonitor

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Manages Redis connections for RQ operations"""
    
    def __init__(self, config: RQConfig):
        self.config = config
        self._connection_pool: Optional[ConnectionPool] = None
        self._redis_connection: Optional[redis.Redis] = None
        self._health_monitor: Optional[RedisHealthMonitor] = None
        self._connection_attempts = 0
        self._max_connection_attempts = 5
        self._reconnection_delay = 1  # seconds
    
    def initialize(self) -> bool:
        """Initialize Redis connection and health monitoring"""
        try:
            # Create connection pool
            self._create_connection_pool()
            
            # Create Redis connection
            self._redis_connection = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            if not self._test_connection():
                logger.error("Failed to establish Redis connection")
                return False
            
            # Initialize health monitor
            self._health_monitor = RedisHealthMonitor(self._redis_connection, self.config)
            
            # Register health callbacks
            self._health_monitor.register_failure_callback(self._handle_redis_failure)
            self._health_monitor.register_recovery_callback(self._handle_redis_recovery)
            
            # Start health monitoring
            self._health_monitor.start_monitoring()
            
            logger.info("Redis connection manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection manager: {e}")
            return False
    
    def _create_connection_pool(self) -> None:
        """Create Redis connection pool"""
        connection_params = self.config.get_redis_connection_params()
        
        # Add connection pool specific parameters
        pool_params = {
            **connection_params,
            'max_connections': 20,
            'retry_on_timeout': True,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
        }
        
        self._connection_pool = ConnectionPool(**pool_params)
        logger.info(f"Created Redis connection pool with params: {connection_params}")
    
    def _test_connection(self) -> bool:
        """Test Redis connection"""
        try:
            start_time = time.time()
            response = self._redis_connection.ping()
            response_time = time.time() - start_time
            
            if response:
                logger.info(f"Redis connection test successful (response time: {response_time:.3f}s)")
                return True
            else:
                logger.error("Redis ping returned False")
                return False
                
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            return False
    
    def get_connection(self) -> Optional[redis.Redis]:
        """Get Redis connection with automatic reconnection"""
        if not self._redis_connection:
            if not self._reconnect():
                return None
        
        # Test connection health
        try:
            self._redis_connection.ping()
            return self._redis_connection
        except Exception as e:
            logger.warning(f"Redis connection unhealthy: {e}")
            if self._reconnect():
                return self._redis_connection
            return None
    
    def _reconnect(self) -> bool:
        """Attempt to reconnect to Redis"""
        self._connection_attempts += 1
        
        if self._connection_attempts > self._max_connection_attempts:
            logger.error(f"Max reconnection attempts ({self._max_connection_attempts}) exceeded")
            return False
        
        try:
            logger.info(f"Attempting Redis reconnection (attempt {self._connection_attempts})")
            
            # Wait before reconnection attempt
            if self._connection_attempts > 1:
                delay = min(self._reconnection_delay * (2 ** (self._connection_attempts - 1)), 30)
                time.sleep(delay)
            
            # Recreate connection pool and connection
            self._create_connection_pool()
            self._redis_connection = redis.Redis(connection_pool=self._connection_pool)
            
            # Test new connection
            if self._test_connection():
                self._connection_attempts = 0  # Reset on successful connection
                logger.info("Redis reconnection successful")
                return True
            else:
                logger.error("Redis reconnection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Redis reconnection failed: {e}")
            return False
    
    def _handle_redis_failure(self) -> None:
        """Handle Redis failure event"""
        logger.warning("Redis failure detected by health monitor")
        # Additional failure handling can be added here
        # For example, triggering database fallback mode
    
    def _handle_redis_recovery(self) -> None:
        """Handle Redis recovery event"""
        logger.info("Redis recovery detected by health monitor")
        self._connection_attempts = 0  # Reset connection attempts on recovery
        # Additional recovery handling can be added here
        # For example, migrating tasks back from database to RQ
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get connection and health status"""
        status = {
            'connection_established': self._redis_connection is not None,
            'connection_attempts': self._connection_attempts,
            'max_attempts_reached': self._connection_attempts >= self._max_connection_attempts,
            'health_monitor_active': self._health_monitor is not None
        }
        
        if self._health_monitor:
            status.update(self._health_monitor.get_health_status())
        
        return status
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed connection information"""
        if not self._redis_connection:
            return {'status': 'not_connected'}
        
        try:
            info = self._redis_connection.info()
            return {
                'status': 'connected',
                'redis_version': info.get('redis_version'),
                'connected_clients': info.get('connected_clients'),
                'used_memory_human': info.get('used_memory_human'),
                'total_commands_processed': info.get('total_commands_processed'),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses')
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def cleanup(self) -> None:
        """Cleanup connections and stop monitoring"""
        try:
            if self._health_monitor:
                self._health_monitor.stop_monitoring()
            
            if self._connection_pool:
                self._connection_pool.disconnect()
            
            logger.info("Redis connection manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during Redis connection cleanup: {e}")
    
    def force_health_check(self) -> Dict[str, Any]:
        """Force immediate health check"""
        if self._health_monitor:
            return self._health_monitor.force_health_check()
        return {'error': 'Health monitor not initialized'}
    
    def trigger_cleanup(self) -> bool:
        """Trigger Redis cleanup operations"""
        if self._health_monitor:
            return self._health_monitor.trigger_cleanup_if_needed()
        return False