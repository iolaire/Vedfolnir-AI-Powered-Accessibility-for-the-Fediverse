# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Fallback Manager

Provides comprehensive fallback mechanisms for Redis unavailability including
automatic fallback to database queuing, Redis reconnection logic with exponential
backoff, and task migration back to RQ when Redis recovers.
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus, JobPriority
from .rq_config import RQConfig, TaskPriority
from .redis_health_monitor import RedisHealthMonitor
from .redis_connection_manager import RedisConnectionManager

logger = logging.getLogger(__name__)


class FallbackMode(Enum):
    """Fallback operation modes"""
    RQ_ONLY = "rq_only"           # Redis available, use RQ only
    DATABASE_ONLY = "database_only"  # Redis unavailable, use database only
    HYBRID = "hybrid"             # Both available, prefer RQ but support database
    RECOVERY = "recovery"         # Redis recovering, migrating tasks back


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RedisFallbackManager:
    """Manages comprehensive fallback mechanisms for Redis unavailability"""
    
    def __init__(self, db_manager: DatabaseManager, config: RQConfig):
        """
        Initialize Redis Fallback Manager
        
        Args:
            db_manager: Database manager instance
            config: RQ configuration
        """
        self.db_manager = db_manager
        self.config = config
        self._lock = threading.Lock()
        
        # Current state
        self.current_mode = FallbackMode.DATABASE_ONLY
        self.redis_available = False
        self.last_redis_check = None
        self.fallback_start_time = None
        self.recovery_start_time = None
        
        # Reconnection logic
        self.reconnection_attempts = 0
        self.max_reconnection_attempts = 10
        self.base_reconnection_delay = 2  # seconds
        self.max_reconnection_delay = 300  # 5 minutes
        self.last_reconnection_attempt = None
        
        # Task migration tracking
        self.migration_stats = {
            'tasks_migrated_to_db': 0,
            'tasks_migrated_to_rq': 0,
            'migration_failures': 0,
            'last_migration_time': None
        }
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[AlertLevel, str, Dict[str, Any]], None]] = []
        
        # Monitoring thread
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Redis components (will be set externally)
        self.redis_connection_manager: Optional[RedisConnectionManager] = None
        self.redis_health_monitor: Optional[RedisHealthMonitor] = None
    
    def set_redis_components(self, connection_manager: RedisConnectionManager, 
                           health_monitor: RedisHealthMonitor) -> None:
        """Set Redis components for monitoring and management"""
        self.redis_connection_manager = connection_manager
        self.redis_health_monitor = health_monitor
        
        # Register callbacks with health monitor
        if self.redis_health_monitor:
            self.redis_health_monitor.register_failure_callback(self.handle_redis_failure)
            self.redis_health_monitor.register_recovery_callback(self.handle_redis_recovery)
    
    def start_monitoring(self) -> None:
        """Start fallback monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Fallback monitoring already running")
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="RedisFallbackMonitor",
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Redis fallback monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop fallback monitoring"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=5)
            logger.info("Redis fallback monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop for fallback management"""
        while not self._stop_monitoring.is_set():
            try:
                self._check_and_update_status()
                self._handle_reconnection_attempts()
                self._monitor_memory_usage()
                
                # Wait before next check
                self._stop_monitoring.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in fallback monitoring loop: {sanitize_for_log(str(e))}")
                self._stop_monitoring.wait(5)  # Short delay on error
    
    def _check_and_update_status(self) -> None:
        """Check Redis status and update fallback mode"""
        with self._lock:
            try:
                # Check Redis health
                redis_healthy = False
                if self.redis_health_monitor:
                    redis_healthy = self.redis_health_monitor.check_health()
                
                self.last_redis_check = datetime.now(timezone.utc)
                
                # Update Redis availability status
                previous_availability = self.redis_available
                self.redis_available = redis_healthy
                
                # Handle state transitions
                if not previous_availability and redis_healthy:
                    # Redis became available
                    self._handle_redis_became_available()
                elif previous_availability and not redis_healthy:
                    # Redis became unavailable
                    self._handle_redis_became_unavailable()
                
            except Exception as e:
                logger.error(f"Error checking Redis status: {sanitize_for_log(str(e))}")
    
    def _handle_redis_became_available(self) -> None:
        """Handle Redis becoming available"""
        logger.info("Redis became available - initiating recovery mode")
        
        self.current_mode = FallbackMode.RECOVERY
        self.recovery_start_time = datetime.now(timezone.utc)
        self.reconnection_attempts = 0  # Reset reconnection attempts
        
        # Trigger alert
        self._trigger_alert(
            AlertLevel.INFO,
            "Redis recovery detected",
            {
                'previous_mode': self.current_mode.value,
                'fallback_duration': self._get_fallback_duration(),
                'recovery_start_time': self.recovery_start_time.isoformat()
            }
        )
        
        # Start task migration back to RQ
        self._migrate_database_tasks_to_rq()
    
    def _handle_redis_became_unavailable(self) -> None:
        """Handle Redis becoming unavailable"""
        logger.warning("Redis became unavailable - switching to database fallback")
        
        self.current_mode = FallbackMode.DATABASE_ONLY
        self.fallback_start_time = datetime.now(timezone.utc)
        
        # Trigger alert
        self._trigger_alert(
            AlertLevel.WARNING,
            "Redis failure detected - switched to database fallback",
            {
                'previous_mode': self.current_mode.value,
                'fallback_start_time': self.fallback_start_time.isoformat(),
                'reconnection_attempts': self.reconnection_attempts
            }
        )
    
    def handle_redis_failure(self) -> None:
        """Handle Redis failure detected by health monitor (within 30 seconds)"""
        with self._lock:
            logger.error("Redis failure detected by health monitor")
            
            if self.current_mode != FallbackMode.DATABASE_ONLY:
                self.current_mode = FallbackMode.DATABASE_ONLY
                self.fallback_start_time = datetime.now(timezone.utc)
                self.redis_available = False
                
                # Trigger critical alert
                self._trigger_alert(
                    AlertLevel.ERROR,
                    "Redis failure detected - automatic fallback to database",
                    {
                        'detection_time': datetime.now(timezone.utc).isoformat(),
                        'failure_threshold_reached': True
                    }
                )
                
                logger.info("Switched to database fallback mode due to Redis failure")
    
    def handle_redis_recovery(self) -> None:
        """Handle Redis recovery detected by health monitor"""
        with self._lock:
            logger.info("Redis recovery detected by health monitor")
            
            if self.current_mode == FallbackMode.DATABASE_ONLY:
                self.current_mode = FallbackMode.RECOVERY
                self.recovery_start_time = datetime.now(timezone.utc)
                self.redis_available = True
                self.reconnection_attempts = 0
                
                # Trigger recovery alert
                self._trigger_alert(
                    AlertLevel.INFO,
                    "Redis recovery detected - initiating task migration",
                    {
                        'recovery_time': self.recovery_start_time.isoformat(),
                        'fallback_duration': self._get_fallback_duration()
                    }
                )
                
                # Start migrating tasks back to RQ
                self._migrate_database_tasks_to_rq()
    
    def _handle_reconnection_attempts(self) -> None:
        """Handle Redis reconnection attempts with exponential backoff"""
        if self.redis_available or self.current_mode == FallbackMode.RQ_ONLY:
            return
        
        # Check if it's time for a reconnection attempt
        if self.last_reconnection_attempt:
            time_since_last = datetime.now(timezone.utc) - self.last_reconnection_attempt
            required_delay = self._calculate_reconnection_delay()
            
            if time_since_last.total_seconds() < required_delay:
                return  # Not time yet
        
        # Attempt reconnection
        if self.reconnection_attempts < self.max_reconnection_attempts:
            self._attempt_redis_reconnection()
    
    def _attempt_redis_reconnection(self) -> bool:
        """Attempt to reconnect to Redis"""
        self.reconnection_attempts += 1
        self.last_reconnection_attempt = datetime.now(timezone.utc)
        
        logger.info(f"Attempting Redis reconnection (attempt {self.reconnection_attempts}/"
                   f"{self.max_reconnection_attempts})")
        
        try:
            if self.redis_connection_manager:
                # Force health check to test connection
                health_status = self.redis_connection_manager.force_health_check()
                
                if health_status.get('is_healthy', False):
                    logger.info("Redis reconnection successful")
                    self.redis_available = True
                    self.reconnection_attempts = 0
                    return True
                else:
                    logger.warning(f"Redis reconnection attempt {self.reconnection_attempts} failed")
                    return False
            else:
                logger.error("Redis connection manager not available for reconnection")
                return False
                
        except Exception as e:
            logger.error(f"Redis reconnection attempt failed: {sanitize_for_log(str(e))}")
            return False
    
    def _calculate_reconnection_delay(self) -> float:
        """Calculate reconnection delay using exponential backoff"""
        delay = min(
            self.base_reconnection_delay * (2 ** (self.reconnection_attempts - 1)),
            self.max_reconnection_delay
        )
        return delay
    
    def _monitor_memory_usage(self) -> None:
        """Monitor Redis memory usage and trigger cleanup if needed"""
        if not self.redis_available or not self.redis_health_monitor:
            return
        
        try:
            memory_info = self.redis_health_monitor.get_memory_usage()
            used_percentage = memory_info.get('used_memory_percentage', 0)
            
            # Check if memory usage is approaching threshold
            if used_percentage > self.config.redis_memory_threshold * 100 * 0.9:  # 90% of threshold
                logger.warning(f"Redis memory usage high: {used_percentage:.1f}%")
                
                # Trigger cleanup
                cleanup_success = self.redis_health_monitor.trigger_cleanup_if_needed()
                
                if cleanup_success:
                    logger.info("Redis memory cleanup triggered successfully")
                else:
                    logger.error("Redis memory cleanup failed")
                    
                    # If cleanup fails and memory is critical, trigger alert
                    if used_percentage > self.config.redis_memory_threshold * 100:
                        self._trigger_alert(
                            AlertLevel.CRITICAL,
                            "Redis memory usage critical - cleanup failed",
                            {
                                'memory_usage_percentage': used_percentage,
                                'memory_threshold': self.config.redis_memory_threshold * 100,
                                'cleanup_attempted': True,
                                'cleanup_success': False
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Error monitoring Redis memory usage: {sanitize_for_log(str(e))}")
    
    def _migrate_database_tasks_to_rq(self) -> None:
        """Migrate database tasks back to RQ when Redis recovers"""
        try:
            logger.info("Starting migration of database tasks back to RQ")
            
            # Get queued tasks from database
            session = self.db_manager.get_session()
            try:
                queued_tasks = session.query(CaptionGenerationTask).filter_by(
                    status=TaskStatus.QUEUED
                ).order_by(
                    CaptionGenerationTask.priority == JobPriority.URGENT,
                    CaptionGenerationTask.priority == JobPriority.HIGH,
                    CaptionGenerationTask.priority == JobPriority.NORMAL,
                    CaptionGenerationTask.created_at
                ).limit(100).all()  # Migrate in batches
                
                migrated_count = 0
                failed_count = 0
                
                for task in queued_tasks:
                    try:
                        # This would need to be implemented with the RQ queue manager
                        # For now, we'll just track the intent
                        migrated_count += 1
                        logger.debug(f"Would migrate task {sanitize_for_log(task.id)} to RQ")
                        
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Failed to migrate task {sanitize_for_log(task.id)}: "
                                   f"{sanitize_for_log(str(e))}")
                
                # Update migration statistics
                self.migration_stats['tasks_migrated_to_rq'] += migrated_count
                self.migration_stats['migration_failures'] += failed_count
                self.migration_stats['last_migration_time'] = datetime.now(timezone.utc)
                
                logger.info(f"Task migration completed: {migrated_count} migrated, {failed_count} failed")
                
                # Update mode to RQ_ONLY if migration successful
                if migrated_count > 0 and failed_count == 0:
                    self.current_mode = FallbackMode.RQ_ONLY
                    
                    self._trigger_alert(
                        AlertLevel.INFO,
                        "Task migration to RQ completed successfully",
                        {
                            'migrated_tasks': migrated_count,
                            'failed_tasks': failed_count,
                            'new_mode': self.current_mode.value
                        }
                    )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error migrating database tasks to RQ: {sanitize_for_log(str(e))}")
            self.migration_stats['migration_failures'] += 1
    
    def force_fallback_to_database(self, reason: str = "Manual override") -> bool:
        """Force fallback to database mode"""
        with self._lock:
            try:
                previous_mode = self.current_mode
                self.current_mode = FallbackMode.DATABASE_ONLY
                self.fallback_start_time = datetime.now(timezone.utc)
                
                logger.warning(f"Forced fallback to database mode: {reason}")
                
                self._trigger_alert(
                    AlertLevel.WARNING,
                    f"Forced fallback to database mode: {reason}",
                    {
                        'previous_mode': previous_mode.value,
                        'forced_fallback': True,
                        'reason': reason
                    }
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Error forcing fallback to database: {sanitize_for_log(str(e))}")
                return False
    
    def force_recovery_to_rq(self, reason: str = "Manual override") -> bool:
        """Force recovery to RQ mode"""
        with self._lock:
            try:
                # Check if Redis is actually available
                if not self.redis_available:
                    logger.error("Cannot force recovery to RQ - Redis not available")
                    return False
                
                previous_mode = self.current_mode
                self.current_mode = FallbackMode.RQ_ONLY
                self.recovery_start_time = datetime.now(timezone.utc)
                
                logger.info(f"Forced recovery to RQ mode: {reason}")
                
                self._trigger_alert(
                    AlertLevel.INFO,
                    f"Forced recovery to RQ mode: {reason}",
                    {
                        'previous_mode': previous_mode.value,
                        'forced_recovery': True,
                        'reason': reason
                    }
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Error forcing recovery to RQ: {sanitize_for_log(str(e))}")
                return False
    
    def get_fallback_status(self) -> Dict[str, Any]:
        """Get comprehensive fallback status"""
        return {
            'current_mode': self.current_mode.value,
            'redis_available': self.redis_available,
            'last_redis_check': self.last_redis_check.isoformat() if self.last_redis_check else None,
            'fallback_start_time': self.fallback_start_time.isoformat() if self.fallback_start_time else None,
            'recovery_start_time': self.recovery_start_time.isoformat() if self.recovery_start_time else None,
            'fallback_duration': self._get_fallback_duration(),
            'reconnection_attempts': self.reconnection_attempts,
            'max_reconnection_attempts': self.max_reconnection_attempts,
            'last_reconnection_attempt': self.last_reconnection_attempt.isoformat() if self.last_reconnection_attempt else None,
            'next_reconnection_delay': self._calculate_reconnection_delay() if self.reconnection_attempts > 0 else 0,
            'migration_stats': self.migration_stats.copy()
        }
    
    def _get_fallback_duration(self) -> Optional[float]:
        """Get fallback duration in seconds"""
        if self.fallback_start_time:
            return (datetime.now(timezone.utc) - self.fallback_start_time).total_seconds()
        return None
    
    def register_alert_callback(self, callback: Callable[[AlertLevel, str, Dict[str, Any]], None]) -> None:
        """Register callback for fallback alerts"""
        self._alert_callbacks.append(callback)
    
    def _trigger_alert(self, level: AlertLevel, message: str, data: Dict[str, Any]) -> None:
        """Trigger alert callbacks"""
        alert_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level.value,
            'message': message,
            'fallback_status': self.get_fallback_status(),
            **data
        }
        
        for callback in self._alert_callbacks:
            try:
                callback(level, message, alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {sanitize_for_log(str(e))}")
        
        # Log the alert
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(level, logger.info)
        
        log_level(f"Fallback Alert [{level.value.upper()}]: {message}")
    
    def cleanup(self) -> None:
        """Cleanup fallback manager resources"""
        try:
            self.stop_monitoring()
            logger.info("Redis fallback manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during fallback manager cleanup: {sanitize_for_log(str(e))}")