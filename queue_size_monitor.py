# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Queue Size Monitor

Monitors task queue size and provides alerting when limits are approached or exceeded.
Integrates with ConfigurationService for dynamic threshold management.
"""

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class QueueAlert:
    """Queue size alert"""
    level: AlertLevel
    message: str
    current_size: int
    limit: int
    threshold_percentage: float
    timestamp: datetime
    alert_id: str


class QueueSizeMonitor:
    """
    Monitors task queue size and provides alerting functionality
    
    Features:
    - Real-time queue size monitoring
    - Configurable alert thresholds
    - Alert suppression to prevent spam
    - Integration with configuration service
    - Queue size statistics and trends
    """
    
    def __init__(self, task_queue_manager: 'TaskQueueManager', 
                 config_service: Optional['ConfigurationService'] = None,
                 alert_callback: Optional[Callable[[QueueAlert], None]] = None):
        """
        Initialize queue size monitor
        
        Args:
            task_queue_manager: TaskQueueManager instance to monitor
            config_service: Optional configuration service for dynamic thresholds
            alert_callback: Optional callback function for alert notifications
        """
        self.task_queue_manager = task_queue_manager
        self.config_service = config_service
        self.alert_callback = alert_callback
        
        # Monitoring configuration
        self.warning_threshold = 0.8  # 80% of limit
        self.critical_threshold = 0.95  # 95% of limit
        self.check_interval = 30  # seconds
        self.alert_suppression_time = 300  # 5 minutes
        
        # State tracking
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._last_alerts: Dict[str, datetime] = {}
        self._alert_history: List[QueueAlert] = []
        self._statistics: Dict[str, Any] = {}
        
        # Load configuration if available
        if self.config_service:
            self._load_configuration()
    
    def _load_configuration(self):
        """Load monitoring configuration from configuration service"""
        try:
            self.warning_threshold = self.config_service.get_config(
                'queue_monitor_warning_threshold', self.warning_threshold
            )
            self.critical_threshold = self.config_service.get_config(
                'queue_monitor_critical_threshold', self.critical_threshold
            )
            self.check_interval = self.config_service.get_config(
                'queue_monitor_check_interval', self.check_interval
            )
            self.alert_suppression_time = self.config_service.get_config(
                'queue_monitor_alert_suppression_time', self.alert_suppression_time
            )
            
            logger.info(f"Queue monitor configuration loaded: warning={self.warning_threshold}, "
                       f"critical={self.critical_threshold}, interval={self.check_interval}s")
            
        except Exception as e:
            logger.error(f"Error loading queue monitor configuration: {str(e)}")
    
    def start_monitoring(self) -> bool:
        """
        Start queue size monitoring
        
        Returns:
            True if monitoring started successfully
        """
        with self._lock:
            if self._monitoring:
                logger.warning("Queue size monitoring is already running")
                return False
            
            try:
                self._monitoring = True
                self._monitor_thread = threading.Thread(
                    target=self._monitor_loop,
                    name="QueueSizeMonitor",
                    daemon=True
                )
                self._monitor_thread.start()
                
                logger.info("Queue size monitoring started")
                return True
                
            except Exception as e:
                logger.error(f"Error starting queue size monitoring: {str(e)}")
                self._monitoring = False
                return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop queue size monitoring
        
        Returns:
            True if monitoring stopped successfully
        """
        with self._lock:
            if not self._monitoring:
                logger.warning("Queue size monitoring is not running")
                return False
            
            try:
                self._monitoring = False
                
                if self._monitor_thread and self._monitor_thread.is_alive():
                    self._monitor_thread.join(timeout=5.0)
                
                logger.info("Queue size monitoring stopped")
                return True
                
            except Exception as e:
                logger.error(f"Error stopping queue size monitoring: {str(e)}")
                return False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Queue size monitor loop started")
        
        while self._monitoring:
            try:
                self._check_queue_size()
                self._update_statistics()
                
                # Sleep with monitoring check
                for _ in range(int(self.check_interval)):
                    if not self._monitoring:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in queue size monitor loop: {str(e)}")
                time.sleep(5)  # Brief pause before retrying
        
        logger.info("Queue size monitor loop stopped")
    
    def _check_queue_size(self):
        """Check current queue size and generate alerts if needed"""
        try:
            # Get current queue statistics
            stats = self.task_queue_manager.get_queue_stats()
            current_size = stats.get('queued', 0)
            
            # Get current queue size limit
            queue_limit = getattr(self.task_queue_manager, 'queue_size_limit', 100)
            
            if queue_limit <= 0:
                return  # No limit configured
            
            # Calculate percentage
            percentage = current_size / queue_limit
            
            # Check thresholds
            if percentage >= self.critical_threshold:
                self._generate_alert(
                    AlertLevel.CRITICAL,
                    f"Queue size critical: {current_size}/{queue_limit} ({percentage:.1%})",
                    current_size,
                    queue_limit,
                    percentage
                )
            elif percentage >= self.warning_threshold:
                self._generate_alert(
                    AlertLevel.WARNING,
                    f"Queue size warning: {current_size}/{queue_limit} ({percentage:.1%})",
                    current_size,
                    queue_limit,
                    percentage
                )
            elif current_size == 0 and self._has_recent_alerts():
                # Queue cleared - send info alert
                self._generate_alert(
                    AlertLevel.INFO,
                    f"Queue size normalized: {current_size}/{queue_limit} ({percentage:.1%})",
                    current_size,
                    queue_limit,
                    percentage
                )
            
        except Exception as e:
            logger.error(f"Error checking queue size: {str(e)}")
    
    def _generate_alert(self, level: AlertLevel, message: str, current_size: int, 
                       limit: int, percentage: float):
        """Generate and process an alert"""
        try:
            # Check alert suppression
            alert_key = f"{level.value}_{current_size}_{limit}"
            now = datetime.now(timezone.utc)
            
            if alert_key in self._last_alerts:
                time_since_last = (now - self._last_alerts[alert_key]).total_seconds()
                if time_since_last < self.alert_suppression_time:
                    return  # Suppress duplicate alert
            
            # Create alert
            alert = QueueAlert(
                level=level,
                message=message,
                current_size=current_size,
                limit=limit,
                threshold_percentage=percentage,
                timestamp=now,
                alert_id=f"queue_alert_{now.timestamp()}"
            )
            
            # Record alert
            self._last_alerts[alert_key] = now
            self._alert_history.append(alert)
            
            # Keep alert history manageable
            if len(self._alert_history) > 100:
                self._alert_history = self._alert_history[-50:]
            
            # Log alert
            log_method = {
                AlertLevel.INFO: logger.info,
                AlertLevel.WARNING: logger.warning,
                AlertLevel.CRITICAL: logger.critical
            }.get(level, logger.info)
            
            log_method(f"Queue size alert: {message}")
            
            # Call alert callback if provided
            if self.alert_callback:
                try:
                    self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error generating alert: {str(e)}")
    
    def _has_recent_alerts(self) -> bool:
        """Check if there have been recent warning or critical alerts"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        for alert in reversed(self._alert_history):
            if alert.timestamp < cutoff_time:
                break
            if alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
                return True
        
        return False
    
    def _update_statistics(self):
        """Update queue size statistics"""
        try:
            stats = self.task_queue_manager.get_queue_stats()
            current_size = stats.get('queued', 0)
            queue_limit = getattr(self.task_queue_manager, 'queue_size_limit', 100)
            
            now = datetime.now(timezone.utc)
            
            # Initialize statistics if needed
            if not self._statistics:
                self._statistics = {
                    'max_size_observed': current_size,
                    'min_size_observed': current_size,
                    'total_checks': 0,
                    'alert_counts': {level.value: 0 for level in AlertLevel},
                    'last_updated': now,
                    'average_size': current_size,
                    'size_history': []
                }
            
            # Update statistics
            self._statistics['total_checks'] += 1
            self._statistics['max_size_observed'] = max(self._statistics['max_size_observed'], current_size)
            self._statistics['min_size_observed'] = min(self._statistics['min_size_observed'], current_size)
            self._statistics['last_updated'] = now
            
            # Update size history (keep last 100 entries)
            self._statistics['size_history'].append({
                'size': current_size,
                'limit': queue_limit,
                'timestamp': now
            })
            if len(self._statistics['size_history']) > 100:
                self._statistics['size_history'] = self._statistics['size_history'][-50:]
            
            # Calculate average size
            if self._statistics['size_history']:
                total_size = sum(entry['size'] for entry in self._statistics['size_history'])
                self._statistics['average_size'] = total_size / len(self._statistics['size_history'])
            
            # Count alerts
            for alert in self._alert_history:
                if alert.timestamp >= now - timedelta(hours=24):  # Last 24 hours
                    self._statistics['alert_counts'][alert.level.value] += 1
            
        except Exception as e:
            logger.error(f"Error updating queue statistics: {str(e)}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        Get current queue monitoring status
        
        Returns:
            Dictionary with current status information
        """
        try:
            stats = self.task_queue_manager.get_queue_stats()
            current_size = stats.get('queued', 0)
            queue_limit = getattr(self.task_queue_manager, 'queue_size_limit', 100)
            
            percentage = current_size / queue_limit if queue_limit > 0 else 0
            
            return {
                'monitoring_active': self._monitoring,
                'current_queue_size': current_size,
                'queue_size_limit': queue_limit,
                'utilization_percentage': percentage,
                'warning_threshold': self.warning_threshold,
                'critical_threshold': self.critical_threshold,
                'check_interval': self.check_interval,
                'recent_alerts': len([a for a in self._alert_history 
                                    if a.timestamp >= datetime.now(timezone.utc) - timedelta(hours=1)]),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting current status: {str(e)}")
            return {'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue size monitoring statistics
        
        Returns:
            Dictionary with monitoring statistics
        """
        with self._lock:
            return self._statistics.copy() if self._statistics else {}
    
    def get_alert_history(self, hours: int = 24) -> List[QueueAlert]:
        """
        Get alert history for specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of alerts within the time period
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [alert for alert in self._alert_history if alert.timestamp >= cutoff_time]
    
    def update_thresholds(self, warning_threshold: Optional[float] = None,
                         critical_threshold: Optional[float] = None) -> bool:
        """
        Update alert thresholds
        
        Args:
            warning_threshold: Warning threshold (0.0 to 1.0)
            critical_threshold: Critical threshold (0.0 to 1.0)
            
        Returns:
            True if thresholds were updated successfully
        """
        try:
            with self._lock:
                if warning_threshold is not None:
                    if 0.0 <= warning_threshold <= 1.0:
                        self.warning_threshold = warning_threshold
                        logger.info(f"Updated warning threshold to {warning_threshold}")
                    else:
                        logger.error(f"Invalid warning threshold: {warning_threshold}")
                        return False
                
                if critical_threshold is not None:
                    if 0.0 <= critical_threshold <= 1.0:
                        self.critical_threshold = critical_threshold
                        logger.info(f"Updated critical threshold to {critical_threshold}")
                    else:
                        logger.error(f"Invalid critical threshold: {critical_threshold}")
                        return False
                
                # Validate threshold relationship
                if self.warning_threshold >= self.critical_threshold:
                    logger.error("Warning threshold must be less than critical threshold")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating thresholds: {str(e)}")
            return False
    
    def force_check(self) -> Dict[str, Any]:
        """
        Force an immediate queue size check
        
        Returns:
            Dictionary with check results
        """
        try:
            self._check_queue_size()
            return self.get_current_status()
        except Exception as e:
            logger.error(f"Error in forced check: {str(e)}")
            return {'error': str(e)}
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is currently active"""
        return self._monitoring
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop_monitoring()
            logger.info("Queue size monitor cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during destruction