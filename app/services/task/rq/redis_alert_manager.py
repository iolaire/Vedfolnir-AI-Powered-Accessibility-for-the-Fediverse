# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Alert Manager

Provides alerting mechanisms for Redis failures and recovery events with
notification integration and administrative alerts.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import User, UserRole, NotificationType, NotificationPriority, NotificationCategory

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of Redis alerts"""
    REDIS_FAILURE = "redis_failure"
    REDIS_RECOVERY = "redis_recovery"
    MEMORY_WARNING = "memory_warning"
    MEMORY_CRITICAL = "memory_critical"
    FALLBACK_ACTIVATED = "fallback_activated"
    MIGRATION_COMPLETED = "migration_completed"
    RECONNECTION_FAILED = "reconnection_failed"
    CLEANUP_FAILED = "cleanup_failed"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RedisAlertManager:
    """Manages alerting for Redis failures and recovery events"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize Redis Alert Manager
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        
        # Alert configuration
        self.alert_config = {
            AlertType.REDIS_FAILURE: {
                'severity': AlertSeverity.CRITICAL,
                'notify_admins': True,
                'log_level': 'error',
                'title': 'Redis Service Failure'
            },
            AlertType.REDIS_RECOVERY: {
                'severity': AlertSeverity.MEDIUM,
                'notify_admins': True,
                'log_level': 'info',
                'title': 'Redis Service Recovery'
            },
            AlertType.MEMORY_WARNING: {
                'severity': AlertSeverity.MEDIUM,
                'notify_admins': True,
                'log_level': 'warning',
                'title': 'Redis Memory Usage Warning'
            },
            AlertType.MEMORY_CRITICAL: {
                'severity': AlertSeverity.CRITICAL,
                'notify_admins': True,
                'log_level': 'error',
                'title': 'Redis Memory Usage Critical'
            },
            AlertType.FALLBACK_ACTIVATED: {
                'severity': AlertSeverity.HIGH,
                'notify_admins': True,
                'log_level': 'warning',
                'title': 'Database Fallback Activated'
            },
            AlertType.MIGRATION_COMPLETED: {
                'severity': AlertSeverity.LOW,
                'notify_admins': True,
                'log_level': 'info',
                'title': 'Task Migration Completed'
            },
            AlertType.RECONNECTION_FAILED: {
                'severity': AlertSeverity.HIGH,
                'notify_admins': True,
                'log_level': 'error',
                'title': 'Redis Reconnection Failed'
            },
            AlertType.CLEANUP_FAILED: {
                'severity': AlertSeverity.MEDIUM,
                'notify_admins': True,
                'log_level': 'warning',
                'title': 'Redis Cleanup Failed'
            }
        }
        
        # Alert history
        self.alert_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
    
    def send_redis_failure_alert(self, failure_data: Dict[str, Any]) -> None:
        """Send alert for Redis failure"""
        alert_data = {
            'failure_time': failure_data.get('detection_time', datetime.now(timezone.utc).isoformat()),
            'consecutive_failures': failure_data.get('consecutive_failures', 0),
            'failure_threshold_reached': failure_data.get('failure_threshold_reached', False),
            'fallback_activated': True,
            'impact': 'Task processing switched to database fallback mode'
        }
        
        message = (
            f"Redis service failure detected at {alert_data['failure_time']}. "
            f"System has automatically switched to database fallback mode. "
            f"Task processing will continue but may experience reduced performance."
        )
        
        if alert_data['consecutive_failures'] > 0:
            message += f" Consecutive failures: {alert_data['consecutive_failures']}"
        
        self._send_alert(AlertType.REDIS_FAILURE, message, alert_data)
    
    def send_redis_recovery_alert(self, recovery_data: Dict[str, Any]) -> None:
        """Send alert for Redis recovery"""
        alert_data = {
            'recovery_time': recovery_data.get('recovery_time', datetime.now(timezone.utc).isoformat()),
            'fallback_duration': recovery_data.get('fallback_duration', 0),
            'migration_initiated': True,
            'impact': 'Task processing restored to Redis Queue system'
        }
        
        fallback_duration_str = self._format_duration(alert_data['fallback_duration'])
        
        message = (
            f"Redis service has recovered at {alert_data['recovery_time']}. "
            f"Fallback mode was active for {fallback_duration_str}. "
            f"Task migration back to Redis Queue system has been initiated."
        )
        
        self._send_alert(AlertType.REDIS_RECOVERY, message, alert_data)
    
    def send_memory_warning_alert(self, memory_data: Dict[str, Any]) -> None:
        """Send alert for Redis memory usage warning"""
        alert_data = {
            'memory_usage_percentage': memory_data.get('memory_usage_percentage', 0),
            'memory_threshold': memory_data.get('memory_threshold', 80),
            'used_memory_human': memory_data.get('used_memory_human', 'Unknown'),
            'max_memory_human': memory_data.get('max_memory_human', 'Unknown'),
            'cleanup_recommended': True
        }
        
        message = (
            f"Redis memory usage is high: {alert_data['memory_usage_percentage']:.1f}% "
            f"(threshold: {alert_data['memory_threshold']}%). "
            f"Used memory: {alert_data['used_memory_human']}. "
            f"Automatic cleanup will be attempted."
        )
        
        self._send_alert(AlertType.MEMORY_WARNING, message, alert_data)
    
    def send_memory_critical_alert(self, memory_data: Dict[str, Any]) -> None:
        """Send alert for critical Redis memory usage"""
        alert_data = {
            'memory_usage_percentage': memory_data.get('memory_usage_percentage', 0),
            'memory_threshold': memory_data.get('memory_threshold', 80),
            'used_memory_human': memory_data.get('used_memory_human', 'Unknown'),
            'cleanup_attempted': memory_data.get('cleanup_attempted', False),
            'cleanup_success': memory_data.get('cleanup_success', False),
            'impact': 'Redis performance may be severely degraded'
        }
        
        message = (
            f"CRITICAL: Redis memory usage is at {alert_data['memory_usage_percentage']:.1f}%. "
            f"Used memory: {alert_data['used_memory_human']}. "
        )
        
        if alert_data['cleanup_attempted']:
            if alert_data['cleanup_success']:
                message += "Automatic cleanup was successful."
            else:
                message += "Automatic cleanup FAILED. Manual intervention may be required."
        else:
            message += "Automatic cleanup will be attempted."
        
        self._send_alert(AlertType.MEMORY_CRITICAL, message, alert_data)
    
    def send_fallback_activated_alert(self, fallback_data: Dict[str, Any]) -> None:
        """Send alert for database fallback activation"""
        alert_data = {
            'activation_time': fallback_data.get('fallback_start_time', datetime.now(timezone.utc).isoformat()),
            'reason': fallback_data.get('reason', 'Redis unavailable'),
            'previous_mode': fallback_data.get('previous_mode', 'unknown'),
            'impact': 'Task processing switched to database mode with potential performance impact'
        }
        
        message = (
            f"Database fallback mode activated at {alert_data['activation_time']}. "
            f"Reason: {alert_data['reason']}. "
            f"Task processing will continue using database queuing with potential performance impact."
        )
        
        self._send_alert(AlertType.FALLBACK_ACTIVATED, message, alert_data)
    
    def send_migration_completed_alert(self, migration_data: Dict[str, Any]) -> None:
        """Send alert for completed task migration"""
        alert_data = {
            'completion_time': migration_data.get('completion_time', datetime.now(timezone.utc).isoformat()),
            'migrated_tasks': migration_data.get('migrated_tasks', 0),
            'failed_tasks': migration_data.get('failed_tasks', 0),
            'migration_direction': migration_data.get('direction', 'to_rq'),
            'new_mode': migration_data.get('new_mode', 'unknown')
        }
        
        direction_str = "to Redis Queue" if alert_data['migration_direction'] == 'to_rq' else "to database"
        
        message = (
            f"Task migration {direction_str} completed at {alert_data['completion_time']}. "
            f"Successfully migrated: {alert_data['migrated_tasks']} tasks. "
        )
        
        if alert_data['failed_tasks'] > 0:
            message += f"Failed migrations: {alert_data['failed_tasks']} tasks. "
        
        message += f"System is now in {alert_data['new_mode']} mode."
        
        self._send_alert(AlertType.MIGRATION_COMPLETED, message, alert_data)
    
    def send_reconnection_failed_alert(self, reconnection_data: Dict[str, Any]) -> None:
        """Send alert for failed Redis reconnection attempts"""
        alert_data = {
            'failure_time': reconnection_data.get('failure_time', datetime.now(timezone.utc).isoformat()),
            'attempt_number': reconnection_data.get('attempt_number', 0),
            'max_attempts': reconnection_data.get('max_attempts', 10),
            'next_attempt_delay': reconnection_data.get('next_attempt_delay', 0),
            'total_downtime': reconnection_data.get('total_downtime', 0)
        }
        
        message = (
            f"Redis reconnection attempt {alert_data['attempt_number']}/{alert_data['max_attempts']} "
            f"failed at {alert_data['failure_time']}. "
        )
        
        if alert_data['attempt_number'] >= alert_data['max_attempts']:
            message += "Maximum reconnection attempts reached. Manual intervention may be required."
        else:
            next_delay_str = self._format_duration(alert_data['next_attempt_delay'])
            message += f"Next attempt in {next_delay_str}."
        
        if alert_data['total_downtime'] > 0:
            downtime_str = self._format_duration(alert_data['total_downtime'])
            message += f" Total downtime: {downtime_str}."
        
        self._send_alert(AlertType.RECONNECTION_FAILED, message, alert_data)
    
    def send_cleanup_failed_alert(self, cleanup_data: Dict[str, Any]) -> None:
        """Send alert for failed Redis cleanup operations"""
        alert_data = {
            'failure_time': cleanup_data.get('failure_time', datetime.now(timezone.utc).isoformat()),
            'memory_usage': cleanup_data.get('memory_usage_percentage', 0),
            'error_message': cleanup_data.get('error_message', 'Unknown error'),
            'impact': 'Redis memory usage remains high'
        }
        
        message = (
            f"Redis cleanup operation failed at {alert_data['failure_time']}. "
            f"Current memory usage: {alert_data['memory_usage']:.1f}%. "
            f"Error: {alert_data['error_message']}. "
            f"Manual cleanup may be required."
        )
        
        self._send_alert(AlertType.CLEANUP_FAILED, message, alert_data)
    
    def _send_alert(self, alert_type: AlertType, message: str, data: Dict[str, Any]) -> None:
        """Send alert with appropriate notifications"""
        try:
            config = self.alert_config.get(alert_type, {})
            
            # Create alert record
            alert_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': alert_type.value,
                'severity': config.get('severity', AlertSeverity.MEDIUM).value,
                'title': config.get('title', 'Redis Alert'),
                'message': message,
                'data': data
            }
            
            # Add to history
            self._add_to_history(alert_record)
            
            # Log the alert
            self._log_alert(alert_record, config.get('log_level', 'info'))
            
            # Send notifications to admins if configured
            if config.get('notify_admins', False):
                self._notify_administrators(alert_record)
            
        except Exception as e:
            logger.error(f"Error sending alert: {sanitize_for_log(str(e))}")
    
    def _add_to_history(self, alert_record: Dict[str, Any]) -> None:
        """Add alert to history"""
        self.alert_history.append(alert_record)
        
        # Trim history if it exceeds max size
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
    
    def _log_alert(self, alert_record: Dict[str, Any], log_level: str) -> None:
        """Log alert with appropriate level"""
        log_message = f"[{alert_record['severity'].upper()}] {alert_record['title']}: {alert_record['message']}"
        
        log_func = {
            'debug': logger.debug,
            'info': logger.info,
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }.get(log_level, logger.info)
        
        log_func(log_message)
    
    def _notify_administrators(self, alert_record: Dict[str, Any]) -> None:
        """Send notifications to administrators"""
        try:
            # Get admin users
            admin_users = self._get_admin_users()
            
            if not admin_users:
                logger.warning("No admin users found for Redis alert notifications")
                return
            
            # Determine notification priority and type
            notification_priority = self._get_notification_priority(alert_record['severity'])
            notification_type = self._get_notification_type(alert_record['type'])
            
            # Send notification to each admin
            for admin_user in admin_users:
                try:
                    self._send_user_notification(
                        user_id=admin_user.id,
                        title=alert_record['title'],
                        message=alert_record['message'],
                        notification_type=notification_type,
                        priority=notification_priority,
                        data={
                            'alert_type': alert_record['type'],
                            'alert_severity': alert_record['severity'],
                            'alert_timestamp': alert_record['timestamp'],
                            **alert_record['data']
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {admin_user.id}: "
                               f"{sanitize_for_log(str(e))}")
            
        except Exception as e:
            logger.error(f"Error notifying administrators: {sanitize_for_log(str(e))}")
    
    def _get_admin_users(self) -> List[User]:
        """Get list of admin users"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).filter_by(role=UserRole.ADMIN).all()
        finally:
            session.close()
    
    def _get_notification_priority(self, severity: str) -> NotificationPriority:
        """Get notification priority based on alert severity"""
        mapping = {
            AlertSeverity.LOW.value: NotificationPriority.LOW,
            AlertSeverity.MEDIUM.value: NotificationPriority.MEDIUM,
            AlertSeverity.HIGH.value: NotificationPriority.HIGH,
            AlertSeverity.CRITICAL.value: NotificationPriority.URGENT
        }
        return mapping.get(severity, NotificationPriority.MEDIUM)
    
    def _get_notification_type(self, alert_type: str) -> NotificationType:
        """Get notification type based on alert type"""
        if 'failure' in alert_type or 'critical' in alert_type or 'failed' in alert_type:
            return NotificationType.ERROR
        elif 'warning' in alert_type:
            return NotificationType.WARNING
        elif 'recovery' in alert_type or 'completed' in alert_type:
            return NotificationType.SUCCESS
        else:
            return NotificationType.INFO
    
    def _send_user_notification(self, user_id: int, title: str, message: str,
                              notification_type: NotificationType,
                              priority: NotificationPriority,
                              data: Dict[str, Any]) -> None:
        """Send notification to a specific user"""
        try:
            from app.services.notification.helpers.notification_helpers import send_user_notification
            
            send_user_notification(
                message=message,
                notification_type=notification_type,
                title=title,
                user_id=user_id,
                category=NotificationCategory.SYSTEM,
                priority=priority,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Failed to send user notification: {sanitize_for_log(str(e))}")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{seconds:.0f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    def get_alert_history(self, limit: Optional[int] = None,
                         alert_type: Optional[AlertType] = None,
                         severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get alert history with optional filtering"""
        history = self.alert_history.copy()
        
        # Filter by alert type
        if alert_type:
            history = [alert for alert in history if alert['type'] == alert_type.value]
        
        # Filter by severity
        if severity:
            history = [alert for alert in history if alert['severity'] == severity.value]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply limit
        if limit:
            history = history[:limit]
        
        return history
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        
        if total_alerts == 0:
            return {
                'total_alerts': 0,
                'by_type': {},
                'by_severity': {},
                'recent_alerts': 0
            }
        
        # Count by type
        by_type = {}
        for alert in self.alert_history:
            alert_type = alert['type']
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
        
        # Count by severity
        by_severity = {}
        for alert in self.alert_history:
            severity = alert['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Count recent alerts (last 24 hours)
        recent_cutoff = datetime.now(timezone.utc).timestamp() - 86400  # 24 hours ago
        recent_alerts = sum(
            1 for alert in self.alert_history
            if datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')).timestamp() > recent_cutoff
        )
        
        return {
            'total_alerts': total_alerts,
            'by_type': by_type,
            'by_severity': by_severity,
            'recent_alerts': recent_alerts
        }
    
    def clear_alert_history(self) -> int:
        """Clear alert history and return number of cleared alerts"""
        cleared_count = len(self.alert_history)
        self.alert_history.clear()
        logger.info(f"Cleared {cleared_count} alerts from history")
        return cleared_count