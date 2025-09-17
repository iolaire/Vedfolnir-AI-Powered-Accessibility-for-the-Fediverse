# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Health Monitor

Monitors Redis connectivity, memory usage, and performance for RQ operations.
Provides automatic failure detection and recovery mechanisms.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta, timezone
import redis
from .rq_config import RQConfig

logger = logging.getLogger(__name__)


class RedisHealthMonitor:
    """Monitors Redis health and triggers fallback mechanisms"""
    
    def __init__(self, redis_connection: redis.Redis, config: RQConfig):
        self.redis = redis_connection
        self.config = config
        self.is_healthy = True
        self.consecutive_failures = 0
        self.last_check_time = None
        self.last_failure_time = None
        self.last_recovery_time = None
        
        # Health check configuration
        self.health_check_interval = config.health_check_interval
        self.failure_threshold = config.failure_threshold
        self.memory_threshold = config.redis_memory_threshold
        
        # Monitoring thread
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Callbacks for health events
        self._failure_callbacks: list[Callable] = []
        self._recovery_callbacks: list[Callable] = []
        
        # Performance metrics
        self._metrics = {
            'total_checks': 0,
            'failed_checks': 0,
            'avg_response_time': 0.0,
            'last_response_time': 0.0,
            'memory_usage': {},
            'connection_info': {}
        }
    
    def start_monitoring(self) -> None:
        """Start background health monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Health monitoring already running")
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="RedisHealthMonitor",
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Redis health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background health monitoring"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=5)
            logger.info("Redis health monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                self.check_health()
                self._stop_monitoring.wait(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                self._stop_monitoring.wait(5)  # Short delay on error
    
    def check_health(self) -> bool:
        """Perform comprehensive health check"""
        start_time = time.time()
        
        try:
            # Basic connectivity test
            response_time = self._test_connectivity()
            
            # Memory usage check
            memory_info = self._check_memory_usage()
            
            # Connection info check
            connection_info = self._get_connection_info()
            
            # Update metrics
            self._update_metrics(response_time, memory_info, connection_info)
            
            # Check if Redis is healthy
            is_currently_healthy = (
                response_time is not None and
                response_time < 5.0 and  # Response time under 5 seconds
                len(memory_info) > 0 and  # Memory info was successfully retrieved
                memory_info.get('used_memory_percentage', 0) < self.memory_threshold * 100
            )
            
            if is_currently_healthy:
                self._handle_healthy_check()
                self.last_check_time = datetime.now(timezone.utc)
                return True
            else:
                self._handle_failed_check()
                self.last_check_time = datetime.now(timezone.utc)
                return False
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._handle_failed_check()
            return False
    
    def _test_connectivity(self) -> Optional[float]:
        """Test Redis connectivity and measure response time"""
        try:
            start_time = time.time()
            self.redis.ping()
            response_time = time.time() - start_time
            return response_time
        except Exception as e:
            logger.error(f"Redis connectivity test failed: {e}")
            return None
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check Redis memory usage"""
        try:
            info = self.redis.info('memory')
            
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            memory_info = {
                'used_memory': used_memory,
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'max_memory': max_memory,
                'max_memory_human': info.get('maxmemory_human', 'N/A'),
                'used_memory_percentage': 0,
                'memory_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
                'used_memory_rss': info.get('used_memory_rss', 0)
            }
            
            if max_memory > 0:
                memory_info['used_memory_percentage'] = (used_memory / max_memory) * 100
            
            return memory_info
            
        except Exception as e:
            logger.error(f"Memory usage check failed: {e}")
            return {}
    
    def _get_connection_info(self) -> Dict[str, Any]:
        """Get Redis connection information"""
        try:
            info = self.redis.info('clients')
            return {
                'connected_clients': info.get('connected_clients', 0),
                'client_recent_max_input_buffer': info.get('client_recent_max_input_buffer', 0),
                'client_recent_max_output_buffer': info.get('client_recent_max_output_buffer', 0),
                'blocked_clients': info.get('blocked_clients', 0)
            }
        except Exception as e:
            logger.error(f"Connection info check failed: {e}")
            return {}
    
    def _update_metrics(self, response_time: Optional[float], 
                       memory_info: Dict[str, Any], 
                       connection_info: Dict[str, Any]) -> None:
        """Update performance metrics"""
        self._metrics['total_checks'] += 1
        
        if response_time is not None:
            self._metrics['last_response_time'] = response_time
            # Update rolling average
            current_avg = self._metrics['avg_response_time']
            total_checks = self._metrics['total_checks']
            self._metrics['avg_response_time'] = (
                (current_avg * (total_checks - 1) + response_time) / total_checks
            )
        else:
            self._metrics['failed_checks'] += 1
        
        self._metrics['memory_usage'] = memory_info
        self._metrics['connection_info'] = connection_info
    
    def _handle_healthy_check(self) -> None:
        """Handle successful health check"""
        if not self.is_healthy:
            # Recovery detected
            self.is_healthy = True
            self.consecutive_failures = 0
            self.last_recovery_time = datetime.now(timezone.utc)
            
            logger.info("Redis health recovered")
            self._trigger_recovery_callbacks()
        else:
            # Reset failure counter on successful check
            self.consecutive_failures = 0
    
    def _handle_failed_check(self) -> None:
        """Handle failed health check"""
        self.consecutive_failures += 1
        
        if self.is_healthy and self.consecutive_failures >= self.failure_threshold:
            # Failure threshold reached
            self.is_healthy = False
            self.last_failure_time = datetime.now(timezone.utc)
            
            logger.error(f"Redis health failure detected after {self.consecutive_failures} consecutive failures")
            self._trigger_failure_callbacks()
    
    def _trigger_failure_callbacks(self) -> None:
        """Trigger registered failure callbacks"""
        for callback in self._failure_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in failure callback: {e}")
    
    def _trigger_recovery_callbacks(self) -> None:
        """Trigger registered recovery callbacks"""
        for callback in self._recovery_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in recovery callback: {e}")
    
    def register_failure_callback(self, callback: Callable) -> None:
        """Register callback for Redis failure events"""
        self._failure_callbacks.append(callback)
    
    def register_recovery_callback(self, callback: Callable) -> None:
        """Register callback for Redis recovery events"""
        self._recovery_callbacks.append(callback)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            'is_healthy': self.is_healthy,
            'consecutive_failures': self.consecutive_failures,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_recovery_time': self.last_recovery_time.isoformat() if self.last_recovery_time else None,
            'metrics': self._metrics.copy()
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information"""
        return self._metrics.get('memory_usage', {})
    
    def trigger_cleanup_if_needed(self) -> bool:
        """Trigger cleanup if memory usage is high"""
        memory_info = self.get_memory_usage()
        used_percentage = memory_info.get('used_memory_percentage', 0)
        
        if used_percentage > self.memory_threshold * 100:
            logger.warning(f"Redis memory usage high: {used_percentage:.1f}%")
            
            try:
                # Trigger Redis cleanup operations
                self._cleanup_expired_keys()
                return True
            except Exception as e:
                logger.error(f"Redis cleanup failed: {e}")
                return False
        
        return False
    
    def _cleanup_expired_keys(self) -> None:
        """Cleanup expired keys to free memory"""
        try:
            # Get keys with TTL that are close to expiring
            cursor = 0
            cleaned_count = 0
            
            while True:
                cursor, keys = self.redis.scan(cursor, match=f"{self.config.queue_prefix}*", count=100)
                
                for key in keys:
                    try:
                        ttl = self.redis.ttl(key)
                        if ttl == -1:  # No TTL set
                            # Set TTL for old keys (24 hours)
                            self.redis.expire(key, 86400)
                        elif 0 < ttl < 60:  # Expiring soon
                            # Let them expire naturally
                            pass
                    except Exception:
                        continue
                
                if cursor == 0:
                    break
            
            logger.info(f"Redis cleanup completed, processed keys")
            
        except Exception as e:
            logger.error(f"Redis cleanup error: {e}")
            raise
    
    def force_health_check(self) -> Dict[str, Any]:
        """Force immediate health check and return results"""
        self.check_health()
        return self.get_health_status()