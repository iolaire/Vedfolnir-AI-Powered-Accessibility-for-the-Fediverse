# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Error Notifier

Error notification system for administrators with configurable thresholds,
escalation policies, and multiple notification channels.
"""

import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import User, UserRole
from .rq_error_handler import ErrorCategory

logger = logging.getLogger(__name__)


class NotificationSeverity(Enum):
    """Notification severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels"""
    DATABASE = "database"
    EMAIL = "email"
    WEBHOOK = "webhook"
    ADMIN_DASHBOARD = "admin_dashboard"


class RQErrorNotifier:
    """Error notification system for RQ operations"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize RQ Error Notifier
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for notification state
            config: Optional configuration for notifications
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.config = config or {}
        
        # Notification configuration
        self.notification_thresholds = self._initialize_thresholds()
        self.escalation_policies = self._initialize_escalation_policies()
        self.notification_channels = self._initialize_channels()
        
        # Redis keys for notification state
        self.notification_state_key = "rq:notification_state"
        self.alert_history_key = "rq:alert_history"
        self.throttle_key_prefix = "rq:throttle"
        
        # Throttling configuration
        self.throttle_window = self.config.get('throttle_window', 300)  # 5 minutes
        self.max_notifications_per_window = self.config.get('max_notifications_per_window', 5)
        
        logger.info("RQ Error Notifier initialized with comprehensive notification system")
    
    def _initialize_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """Initialize notification thresholds"""
        return {
            'error_rate': {
                'low': {'threshold': 5, 'window': 300},      # 5 errors in 5 minutes
                'medium': {'threshold': 10, 'window': 300},   # 10 errors in 5 minutes
                'high': {'threshold': 20, 'window': 300},     # 20 errors in 5 minutes
                'critical': {'threshold': 50, 'window': 300}  # 50 errors in 5 minutes
            },
            'dead_letter_queue': {
                'low': {'threshold': 10},      # 10 items in DLQ
                'medium': {'threshold': 25},   # 25 items in DLQ
                'high': {'threshold': 50},     # 50 items in DLQ
                'critical': {'threshold': 100} # 100 items in DLQ
            },
            'worker_failures': {
                'low': {'threshold': 3, 'window': 600},      # 3 worker failures in 10 minutes
                'medium': {'threshold': 5, 'window': 600},   # 5 worker failures in 10 minutes
                'high': {'threshold': 10, 'window': 600},    # 10 worker failures in 10 minutes
                'critical': {'threshold': 20, 'window': 600} # 20 worker failures in 10 minutes
            },
            'redis_connection': {
                'medium': {'threshold': 1, 'window': 60},    # 1 Redis failure in 1 minute
                'high': {'threshold': 3, 'window': 300},     # 3 Redis failures in 5 minutes
                'critical': {'threshold': 5, 'window': 300}  # 5 Redis failures in 5 minutes
            }
        }
    
    def _initialize_escalation_policies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize escalation policies"""
        return {
            'low': {
                'channels': [NotificationChannel.ADMIN_DASHBOARD],
                'delay': 0,
                'repeat_interval': 3600  # 1 hour
            },
            'medium': {
                'channels': [NotificationChannel.ADMIN_DASHBOARD, NotificationChannel.DATABASE],
                'delay': 0,
                'repeat_interval': 1800  # 30 minutes
            },
            'high': {
                'channels': [NotificationChannel.ADMIN_DASHBOARD, NotificationChannel.DATABASE, NotificationChannel.EMAIL],
                'delay': 0,
                'repeat_interval': 600  # 10 minutes
            },
            'critical': {
                'channels': [NotificationChannel.ADMIN_DASHBOARD, NotificationChannel.DATABASE, 
                           NotificationChannel.EMAIL, NotificationChannel.WEBHOOK],
                'delay': 0,
                'repeat_interval': 300  # 5 minutes
            }
        }
    
    def _initialize_channels(self) -> Dict[NotificationChannel, Callable]:
        """Initialize notification channel handlers"""
        return {
            NotificationChannel.DATABASE: self._send_database_notification,
            NotificationChannel.EMAIL: self._send_email_notification,
            NotificationChannel.WEBHOOK: self._send_webhook_notification,
            NotificationChannel.ADMIN_DASHBOARD: self._send_dashboard_notification
        }
    
    def check_error_thresholds(self, error_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check error statistics against thresholds and generate notifications
        
        Args:
            error_stats: Error statistics from error handler
            
        Returns:
            List of notifications generated
        """
        notifications = []
        
        try:
            # Check error rate threshold
            error_rate_notifications = self._check_error_rate_threshold(error_stats)
            notifications.extend(error_rate_notifications)
            
            # Check dead letter queue threshold
            dlq_notifications = self._check_dlq_threshold(error_stats)
            notifications.extend(dlq_notifications)
            
            # Check worker failure threshold
            worker_notifications = self._check_worker_failure_threshold(error_stats)
            notifications.extend(worker_notifications)
            
            # Send notifications
            for notification in notifications:
                self._send_notification(notification)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to check error thresholds: {sanitize_for_log(str(e))}")
            return []
    
    def _check_error_rate_threshold(self, error_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check error rate against thresholds"""
        notifications = []
        
        try:
            total_failures = error_stats.get('total_failures', 0)
            
            # Check against each severity level
            for severity, config in self.notification_thresholds['error_rate'].items():
                threshold = config['threshold']
                
                if total_failures >= threshold:
                    # Check if we should throttle this notification
                    if self._should_throttle_notification('error_rate', severity):
                        continue
                    
                    notification = {
                        'type': 'error_rate_threshold',
                        'severity': severity,
                        'message': f"Error rate threshold exceeded: {total_failures} errors (threshold: {threshold})",
                        'details': {
                            'current_errors': total_failures,
                            'threshold': threshold,
                            'window': config.get('window', 300),
                            'error_categories': error_stats.get('error_categories', {})
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'recommendations': self._get_error_rate_recommendations(total_failures, error_stats)
                    }
                    
                    notifications.append(notification)
                    
                    # Record throttle state
                    self._record_notification_throttle('error_rate', severity)
                    
                    # Only send highest severity notification
                    break
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to check error rate threshold: {sanitize_for_log(str(e))}")
            return []
    
    def _check_dlq_threshold(self, error_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check dead letter queue size against thresholds"""
        notifications = []
        
        try:
            dlq_size = error_stats.get('dead_letter_queue_size', 0)
            
            # Check against each severity level
            for severity, config in self.notification_thresholds['dead_letter_queue'].items():
                threshold = config['threshold']
                
                if dlq_size >= threshold:
                    # Check if we should throttle this notification
                    if self._should_throttle_notification('dlq_size', severity):
                        continue
                    
                    notification = {
                        'type': 'dlq_threshold',
                        'severity': severity,
                        'message': f"Dead letter queue size threshold exceeded: {dlq_size} items (threshold: {threshold})",
                        'details': {
                            'current_size': dlq_size,
                            'threshold': threshold,
                            'error_categories': error_stats.get('error_categories', {})
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'recommendations': self._get_dlq_recommendations(dlq_size)
                    }
                    
                    notifications.append(notification)
                    
                    # Record throttle state
                    self._record_notification_throttle('dlq_size', severity)
                    
                    # Only send highest severity notification
                    break
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to check DLQ threshold: {sanitize_for_log(str(e))}")
            return []
    
    def _check_worker_failure_threshold(self, error_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check worker failure rate against thresholds"""
        notifications = []
        
        try:
            # This would be implemented with worker failure tracking
            # For now, we'll use a placeholder
            worker_failures = 0  # Would get from worker monitoring
            
            # Check against each severity level
            for severity, config in self.notification_thresholds['worker_failures'].items():
                threshold = config['threshold']
                
                if worker_failures >= threshold:
                    # Check if we should throttle this notification
                    if self._should_throttle_notification('worker_failures', severity):
                        continue
                    
                    notification = {
                        'type': 'worker_failure_threshold',
                        'severity': severity,
                        'message': f"Worker failure threshold exceeded: {worker_failures} failures (threshold: {threshold})",
                        'details': {
                            'current_failures': worker_failures,
                            'threshold': threshold,
                            'window': config.get('window', 600)
                        },
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'recommendations': self._get_worker_failure_recommendations(worker_failures)
                    }
                    
                    notifications.append(notification)
                    
                    # Record throttle state
                    self._record_notification_throttle('worker_failures', severity)
                    
                    # Only send highest severity notification
                    break
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to check worker failure threshold: {sanitize_for_log(str(e))}")
            return []
    
    def notify_redis_failure(self, failure_details: Dict[str, Any]) -> None:
        """Send immediate notification for Redis connection failure"""
        try:
            notification = {
                'type': 'redis_connection_failure',
                'severity': 'critical',
                'message': "Redis connection failure detected - RQ system may be degraded",
                'details': failure_details,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'recommendations': [
                    "Check Redis server status and connectivity",
                    "Verify Redis configuration and network settings",
                    "Monitor system for fallback to database queuing",
                    "Consider restarting Redis service if necessary"
                ]
            }
            
            self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to send Redis failure notification: {sanitize_for_log(str(e))}")
    
    def notify_system_recovery(self, recovery_details: Dict[str, Any]) -> None:
        """Send notification for system recovery"""
        try:
            notification = {
                'type': 'system_recovery',
                'severity': 'medium',
                'message': "RQ system recovery detected - normal operations resumed",
                'details': recovery_details,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'recommendations': [
                    "Monitor system stability over the next hour",
                    "Review error logs for any remaining issues",
                    "Verify all queues are processing normally"
                ]
            }
            
            self._send_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to send recovery notification: {sanitize_for_log(str(e))}")
    
    def _should_throttle_notification(self, notification_type: str, severity: str) -> bool:
        """Check if notification should be throttled"""
        try:
            throttle_key = f"{self.throttle_key_prefix}:{notification_type}:{severity}"
            
            # Get current throttle count
            current_count = self.redis_connection.get(throttle_key)
            
            if current_count is None:
                return False
            
            count = int(current_count)
            return count >= self.max_notifications_per_window
            
        except Exception as e:
            logger.warning(f"Failed to check notification throttle: {sanitize_for_log(str(e))}")
            return False
    
    def _record_notification_throttle(self, notification_type: str, severity: str) -> None:
        """Record notification for throttling"""
        try:
            throttle_key = f"{self.throttle_key_prefix}:{notification_type}:{severity}"
            
            # Increment counter with expiration
            pipe = self.redis_connection.pipeline()
            pipe.incr(throttle_key)
            pipe.expire(throttle_key, self.throttle_window)
            pipe.execute()
            
        except Exception as e:
            logger.warning(f"Failed to record notification throttle: {sanitize_for_log(str(e))}")
    
    def _send_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification through configured channels"""
        try:
            severity = notification.get('severity', 'medium')
            escalation_policy = self.escalation_policies.get(severity, self.escalation_policies['medium'])
            
            # Send through each configured channel
            for channel in escalation_policy['channels']:
                try:
                    handler = self.notification_channels.get(channel)
                    if handler:
                        handler(notification)
                    else:
                        logger.warning(f"No handler configured for notification channel: {channel}")
                        
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}: {sanitize_for_log(str(e))}")
            
            # Store notification in alert history
            self._store_alert_history(notification)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {sanitize_for_log(str(e))}")
    
    def _send_database_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification via database (admin notifications)"""
        try:
            from app.services.notification.helpers.notification_helpers import send_admin_notification
            from models import NotificationType, NotificationPriority, NotificationCategory
            
            # Map severity to notification priority
            severity_mapping = {
                'low': NotificationPriority.LOW,
                'medium': NotificationPriority.MEDIUM,
                'high': NotificationPriority.HIGH,
                'critical': NotificationPriority.URGENT
            }
            
            priority = severity_mapping.get(notification['severity'], NotificationPriority.MEDIUM)
            
            # Send to all admin users
            session = self.db_manager.get_session()
            try:
                admin_users = session.query(User).filter_by(role=UserRole.ADMIN).all()
                
                for admin_user in admin_users:
                    send_admin_notification(
                        message=notification['message'],
                        notification_type=NotificationType.ERROR,
                        title=f"RQ System Alert - {notification['type']}",
                        user_id=admin_user.id,
                        category=NotificationCategory.SYSTEM,
                        priority=priority,
                        data=notification['details']
                    )
                    
            finally:
                session.close()
            
            logger.info(f"Sent database notification: {notification['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send database notification: {sanitize_for_log(str(e))}")
    
    def _send_email_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification via email"""
        try:
            # This would integrate with the email service
            # For now, we'll log the notification
            logger.info(f"Email notification (placeholder): {notification['message']}")
            
            # In a full implementation, you would:
            # 1. Get admin email addresses from database
            # 2. Format email template with notification details
            # 3. Send via email service
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {sanitize_for_log(str(e))}")
    
    def _send_webhook_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification via webhook"""
        try:
            # This would send to configured webhook endpoints
            # For now, we'll log the notification
            logger.info(f"Webhook notification (placeholder): {notification['message']}")
            
            # In a full implementation, you would:
            # 1. Get webhook URLs from configuration
            # 2. Format webhook payload
            # 3. Send HTTP POST request to webhook endpoints
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {sanitize_for_log(str(e))}")
    
    def _send_dashboard_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification to admin dashboard"""
        try:
            # Store notification in Redis for dashboard display
            dashboard_key = "rq:dashboard_notifications"
            
            notification_data = {
                'id': f"rq_{int(time.time())}_{notification['type']}",
                'type': notification['type'],
                'severity': notification['severity'],
                'message': notification['message'],
                'timestamp': notification['timestamp'],
                'details': notification['details'],
                'acknowledged': False
            }
            
            # Store in Redis list
            pipe = self.redis_connection.pipeline()
            pipe.lpush(dashboard_key, json.dumps(notification_data, default=str))
            pipe.ltrim(dashboard_key, 0, 99)  # Keep last 100 notifications
            pipe.execute()
            
            logger.info(f"Sent dashboard notification: {notification['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send dashboard notification: {sanitize_for_log(str(e))}")
    
    def _store_alert_history(self, notification: Dict[str, Any]) -> None:
        """Store notification in alert history"""
        try:
            alert_entry = {
                'notification': notification,
                'sent_at': datetime.now(timezone.utc).isoformat(),
                'channels_used': [channel.value for channel in self.escalation_policies[notification['severity']]['channels']]
            }
            
            # Store in Redis
            pipe = self.redis_connection.pipeline()
            pipe.lpush(self.alert_history_key, json.dumps(alert_entry, default=str))
            pipe.ltrim(self.alert_history_key, 0, 999)  # Keep last 1000 alerts
            pipe.execute()
            
        except Exception as e:
            logger.warning(f"Failed to store alert history: {sanitize_for_log(str(e))}")
    
    def _get_error_rate_recommendations(self, error_count: int, error_stats: Dict[str, Any]) -> List[str]:
        """Get recommendations for high error rates"""
        recommendations = []
        
        if error_count > 50:
            recommendations.append("Consider pausing job processing to investigate root cause")
        
        if error_count > 20:
            recommendations.append("Review error logs for common patterns")
            recommendations.append("Check system resources (CPU, memory, disk)")
        
        # Check error categories
        error_categories = error_stats.get('error_categories', {})
        total_errors = sum(error_categories.values()) if error_categories else 1
        
        for category, count in error_categories.items():
            percentage = (count / total_errors) * 100
            
            if percentage > 50:
                if category == 'database_connection':
                    recommendations.append("High database errors - check database connectivity and pool settings")
                elif category == 'redis_connection':
                    recommendations.append("High Redis errors - verify Redis server health")
                elif category == 'resource_exhaustion':
                    recommendations.append("Resource exhaustion detected - consider scaling workers or reducing load")
        
        if not recommendations:
            recommendations.append("Monitor error patterns and check system health")
        
        return recommendations
    
    def _get_dlq_recommendations(self, dlq_size: int) -> List[str]:
        """Get recommendations for high DLQ size"""
        recommendations = []
        
        if dlq_size > 100:
            recommendations.append("Critical DLQ size - immediate investigation required")
            recommendations.append("Consider clearing DLQ after reviewing failed jobs")
        elif dlq_size > 50:
            recommendations.append("High DLQ size - review failed jobs for patterns")
            recommendations.append("Consider retrying recoverable jobs")
        else:
            recommendations.append("Monitor DLQ growth and review failed job patterns")
        
        recommendations.append("Analyze DLQ entries for common failure causes")
        recommendations.append("Update error handling based on failure patterns")
        
        return recommendations
    
    def _get_worker_failure_recommendations(self, failure_count: int) -> List[str]:
        """Get recommendations for worker failures"""
        recommendations = []
        
        if failure_count > 10:
            recommendations.append("High worker failure rate - check worker health and resources")
            recommendations.append("Consider restarting worker processes")
        
        recommendations.append("Review worker logs for failure patterns")
        recommendations.append("Check system resources and worker configuration")
        recommendations.append("Monitor worker process stability")
        
        return recommendations
    
    def get_dashboard_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notifications for admin dashboard"""
        try:
            dashboard_key = "rq:dashboard_notifications"
            notifications_json = self.redis_connection.lrange(dashboard_key, 0, limit - 1)
            
            notifications = []
            for notification_json in notifications_json:
                try:
                    notification = json.loads(notification_json)
                    notifications.append(notification)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse dashboard notification: {sanitize_for_log(str(e))}")
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get dashboard notifications: {sanitize_for_log(str(e))}")
            return []
    
    def acknowledge_notification(self, notification_id: str) -> bool:
        """Acknowledge a dashboard notification"""
        try:
            dashboard_key = "rq:dashboard_notifications"
            notifications_json = self.redis_connection.lrange(dashboard_key, 0, -1)
            
            updated_notifications = []
            acknowledged = False
            
            for notification_json in notifications_json:
                try:
                    notification = json.loads(notification_json)
                    
                    if notification.get('id') == notification_id:
                        notification['acknowledged'] = True
                        notification['acknowledged_at'] = datetime.now(timezone.utc).isoformat()
                        acknowledged = True
                    
                    updated_notifications.append(json.dumps(notification, default=str))
                    
                except json.JSONDecodeError:
                    # Keep original if parsing fails
                    updated_notifications.append(notification_json)
            
            # Replace notifications list
            if acknowledged and updated_notifications:
                pipe = self.redis_connection.pipeline()
                pipe.delete(dashboard_key)
                pipe.lpush(dashboard_key, *updated_notifications)
                pipe.execute()
            
            return acknowledged
            
        except Exception as e:
            logger.error(f"Failed to acknowledge notification: {sanitize_for_log(str(e))}")
            return False
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history"""
        try:
            alerts_json = self.redis_connection.lrange(self.alert_history_key, 0, limit - 1)
            
            alerts = []
            for alert_json in alerts_json:
                try:
                    alert = json.loads(alert_json)
                    alerts.append(alert)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse alert history: {sanitize_for_log(str(e))}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get alert history: {sanitize_for_log(str(e))}")
            return []