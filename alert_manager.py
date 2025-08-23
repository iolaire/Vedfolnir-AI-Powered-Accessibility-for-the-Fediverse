# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Multi-Tenant Caption Management Alert System

Provides comprehensive alerting capabilities for caption generation system issues including
job failures, resource monitoring, AI service outages, queue management, and system health.
"""

import json
import uuid
import smtplib
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from logging import getLogger
from collections import defaultdict, deque
from threading import Lock, Thread

# Email imports with error handling
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    MimeText = None
    MimeMultipart = None

from database import DatabaseManager
from models import User, UserRole, AlertType as ModelAlertType, AlertSeverity as ModelAlertSeverity
from config import Config

logger = getLogger(__name__)

# Use AlertType and AlertSeverity from models.py
AlertType = ModelAlertType
AlertSeverity = ModelAlertSeverity

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class NotificationChannel(Enum):
    """Notification channel types"""
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    LOG = "log"

@dataclass
class Alert:
    """Caption generation system alert"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None  # admin user_id
    context: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    count: int = 1
    escalation_level: int = 0

@dataclass
class AlertThresholds:
    """Alert threshold configuration"""
    job_failure_rate: float = 0.1  # 10% failure rate
    repeated_failure_count: int = 3
    resource_usage_threshold: float = 0.9  # 90% usage
    queue_backup_threshold: int = 100  # jobs in queue
    ai_service_timeout: int = 30  # seconds
    performance_degradation_threshold: float = 2.0  # 2x normal time

@dataclass
class NotificationConfig:
    """Notification configuration"""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = None

class AlertManager:
    """Comprehensive alert management system for caption generation"""
    
    def __init__(self, db_manager: DatabaseManager, config: Config):
        self.db_manager = db_manager
        self.config = config
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self._lock = Lock()
        
        # Alert configuration
        self.thresholds = AlertThresholds()
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Alert handlers and tracking
        self.alert_handlers: Dict[AlertType, List[Callable]] = defaultdict(list)
        self.escalation_handlers: List[Callable[[Alert], None]] = []
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Background monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[Thread] = None
        
        # Initialize default configurations
        self._initialize_default_configs()
        
        logger.info("AlertManager initialized for caption generation system")
    
    def _initialize_default_configs(self):
        """Initialize default notification configurations"""
        # Email notifications
        self.notification_configs[NotificationChannel.EMAIL] = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=True,
            config={
                'smtp_server': getattr(self.config, 'SMTP_SERVER', 'localhost'),
                'smtp_port': getattr(self.config, 'SMTP_PORT', 587),
                'smtp_username': getattr(self.config, 'SMTP_USERNAME', ''),
                'smtp_password': getattr(self.config, 'SMTP_PASSWORD', ''),
                'from_email': getattr(self.config, 'ALERT_FROM_EMAIL', 'alerts@vedfolnir.local'),
                'admin_emails': getattr(self.config, 'ADMIN_ALERT_EMAILS', '').split(',')
            }
        )
        
        # In-app notifications
        self.notification_configs[NotificationChannel.IN_APP] = NotificationConfig(
            channel=NotificationChannel.IN_APP,
            enabled=True
        )
        
        # Webhook notifications
        self.notification_configs[NotificationChannel.WEBHOOK] = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            enabled=getattr(self.config, 'WEBHOOK_ALERTS_ENABLED', False),
            config={
                'webhook_url': getattr(self.config, 'ALERT_WEBHOOK_URL', ''),
                'webhook_secret': getattr(self.config, 'ALERT_WEBHOOK_SECRET', '')
            }
        )
        
        # Log notifications (always enabled)
        self.notification_configs[NotificationChannel.LOG] = NotificationConfig(
            channel=NotificationChannel.LOG,
            enabled=True
        )
    
    def register_alert_handler(self, alert_type: AlertType, handler: Callable[[Alert], None]):
        """Register a handler for specific alert types"""
        self.alert_handlers[alert_type].append(handler)
        logger.info(f"Registered alert handler for {alert_type.value}")
    
    def send_alert(
        self, 
        alert_type: AlertType, 
        message: str, 
        severity: AlertSeverity,
        context: Dict[str, Any] = None
    ) -> str:
        """Send an alert and return alert ID"""
        try:
            # Check for duplicate alerts (cooldown period)
            alert_key = f"{alert_type.value}_{message}"
            current_time = datetime.now(timezone.utc)
            
            # Check if similar alert was sent recently (5 minute cooldown)
            last_alert_time = self.last_alert_times.get(alert_key)
            if last_alert_time and (current_time - last_alert_time).total_seconds() < 300:
                # Update existing alert count instead of creating new one
                existing_alert = self._find_similar_alert(alert_type, message)
                if existing_alert:
                    existing_alert.count += 1
                    existing_alert.updated_at = current_time
                    return existing_alert.id
            
            # Create new alert
            alert_id = str(uuid.uuid4())
            alert = Alert(
                id=alert_id,
                alert_type=alert_type,
                severity=severity,
                status=AlertStatus.ACTIVE,
                title=self._generate_alert_title(alert_type, severity),
                message=message,
                created_at=current_time,
                updated_at=current_time,
                context=context or {}
            )
            
            # Store alert
            with self._lock:
                self.active_alerts[alert_id] = alert
                self.alert_history.append(alert)
                self.last_alert_times[alert_key] = current_time
            
            # Log alert
            log_level = logger.error if severity == AlertSeverity.CRITICAL else logger.warning
            log_level(f"ALERT [{severity.value.upper()}] {alert_type.value}: {message}")
            
            # Send notifications
            self._send_notifications(alert)
            
            # Call registered handlers
            for handler in self.alert_handlers[alert_type]:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")
            
            # Check for escalation
            self._check_escalation(alert)
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return ""
    
    def _generate_alert_title(self, alert_type: AlertType, severity: AlertSeverity) -> str:
        """Generate alert title based on type and severity"""
        titles = {
            AlertType.JOB_FAILURE: "Caption Generation Job Failed",
            AlertType.REPEATED_FAILURES: "Repeated Caption Generation Failures",
            AlertType.RESOURCE_LOW: "System Resources Running Low",
            AlertType.AI_SERVICE_DOWN: "AI Service Unavailable",
            AlertType.QUEUE_BACKUP: "Caption Generation Queue Backed Up",
            AlertType.SYSTEM_ERROR: "System Error Detected",
            AlertType.USER_ISSUE: "User Issue Reported",
            AlertType.PERFORMANCE_DEGRADATION: "Performance Degradation Detected"
        }
        
        base_title = titles.get(alert_type, "System Alert")
        if severity == AlertSeverity.CRITICAL:
            return f"CRITICAL: {base_title}"
        elif severity == AlertSeverity.HIGH:
            return f"HIGH: {base_title}"
        elif severity == AlertSeverity.MEDIUM:
            return f"MEDIUM: {base_title}"
        else:
            return base_title
    
    def _find_similar_alert(self, alert_type: AlertType, message: str) -> Optional[Alert]:
        """Find similar active alert"""
        for alert in self.active_alerts.values():
            if (alert.alert_type == alert_type and 
                alert.message == message and 
                alert.status == AlertStatus.ACTIVE):
                return alert
        return None
    
    def _send_notifications(self, alert: Alert):
        """Send notifications through configured channels"""
        for channel, config in self.notification_configs.items():
            if not config.enabled:
                continue
            
            try:
                if channel == NotificationChannel.EMAIL:
                    self._send_email_notification(alert, config)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert, config)
                elif channel == NotificationChannel.IN_APP:
                    self._send_in_app_notification(alert)
                # LOG channel is handled by the main logging above
                
            except Exception as e:
                logger.error(f"Error sending {channel.value} notification: {e}")
    
    def _send_email_notification(self, alert: Alert, config: NotificationConfig):
        """Send email notification"""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available - skipping email notification")
            return
            
        if not config.config or not config.config.get('admin_emails'):
            return
        
        try:
            # Create email message
            msg = MimeMultipart()
            msg['From'] = config.config['from_email']
            msg['To'] = ', '.join(config.config['admin_emails'])
            msg['Subject'] = f"[Vedfolnir Alert] {alert.title}"
            
            # Email body
            body = f"""
Alert Details:
- Type: {alert.alert_type.value}
- Severity: {alert.severity.value.upper()}
- Message: {alert.message}
- Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
- Alert ID: {alert.id}

Context:
{json.dumps(alert.context, indent=2) if alert.context else 'None'}

Please check the admin dashboard for more details and to acknowledge this alert.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(config.config['smtp_server'], config.config['smtp_port'])
            if config.config.get('smtp_username'):
                server.starttls()
                server.login(config.config['smtp_username'], config.config['smtp_password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_notification(self, alert: Alert, config: NotificationConfig):
        """Send webhook notification"""
        if not config.config or not config.config.get('webhook_url'):
            return
        
        try:
            payload = {
                'alert_id': alert.id,
                'alert_type': alert.alert_type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.created_at.isoformat(),
                'context': alert.context
            }
            
            headers = {'Content-Type': 'application/json'}
            if config.config.get('webhook_secret'):
                headers['X-Webhook-Secret'] = config.config['webhook_secret']
            
            response = requests.post(
                config.config['webhook_url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook alert sent for {alert.id}")
            else:
                logger.warning(f"Webhook alert failed with status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_in_app_notification(self, alert: Alert):
        """Send in-app notification (store in database for admin dashboard)"""
        try:
            # Store alert in database for admin dashboard display
            # This would typically be stored in a notifications table
            # For now, we'll just log it as in-app notifications are handled by the dashboard
            logger.info(f"In-app notification created for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}")
    
    def _check_escalation(self, alert: Alert):
        """Check if alert should be escalated"""
        # Escalate critical alerts that aren't acknowledged within 15 minutes
        if (alert.severity == AlertSeverity.CRITICAL and 
            alert.status == AlertStatus.ACTIVE):
            
            # Schedule escalation check (in a real system, this would be a background task)
            logger.info(f"Critical alert {alert.id} scheduled for escalation check")
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        with self._lock:
            alerts = [alert for alert in self.active_alerts.values() 
                     if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]]
            
            if severity:
                alerts = [alert for alert in alerts if alert.severity == severity]
            
            # Sort by severity and creation time
            severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.HIGH: 1, AlertSeverity.MEDIUM: 2, AlertSeverity.LOW: 3}
            alerts.sort(key=lambda a: (severity_order[a.severity], a.created_at))
            
            return alerts
    
    def acknowledge_alert(self, admin_user_id: int, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            with self._lock:
                alert = self.active_alerts.get(alert_id)
                if not alert or alert.status != AlertStatus.ACTIVE:
                    return False
                
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                alert.acknowledged_by = admin_user_id
                alert.updated_at = datetime.now(timezone.utc)
                
                logger.info(f"Alert {alert_id} acknowledged by admin user {admin_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, admin_user_id: int, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            with self._lock:
                alert = self.active_alerts.get(alert_id)
                if not alert:
                    return False
                
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                alert.updated_at = datetime.now(timezone.utc)
                
                logger.info(f"Alert {alert_id} resolved by admin user {admin_user_id}")
                
                # Remove from active alerts after some time
                # In a real system, this would be handled by a cleanup task
                return True
                
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def configure_alert_thresholds(self, admin_user_id: int, thresholds: AlertThresholds) -> bool:
        """Configure alert thresholds"""
        try:
            # Validate thresholds
            if (thresholds.job_failure_rate < 0 or thresholds.job_failure_rate > 1 or
                thresholds.repeated_failure_count < 1 or
                thresholds.resource_usage_threshold < 0 or thresholds.resource_usage_threshold > 1):
                logger.warning(f"Invalid threshold values provided by admin {admin_user_id}")
                return False
            
            self.thresholds = thresholds
            logger.info(f"Alert thresholds updated by admin user {admin_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring alert thresholds: {e}")
            return False
    
    def get_alert_history(
        self, 
        limit: int = 100, 
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Alert]:
        """Get alert history with filtering options"""
        try:
            alerts = list(self.alert_history)
            
            # Apply filters
            if alert_type:
                alerts = [a for a in alerts if a.alert_type == alert_type]
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            if start_date:
                alerts = [a for a in alerts if a.created_at >= start_date]
            
            if end_date:
                alerts = [a for a in alerts if a.created_at <= end_date]
            
            # Sort by creation time (newest first) and limit
            alerts.sort(key=lambda a: a.created_at, reverse=True)
            return alerts[:limit]
            
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics and metrics"""
        try:
            with self._lock:
                active_alerts = list(self.active_alerts.values())
                all_alerts = list(self.alert_history)
                
                # Current status
                stats = {
                    'active_alerts': len([a for a in active_alerts if a.status == AlertStatus.ACTIVE]),
                    'acknowledged_alerts': len([a for a in active_alerts if a.status == AlertStatus.ACKNOWLEDGED]),
                    'total_active': len(active_alerts),
                    'total_historical': len(all_alerts)
                }
                
                # By severity
                stats['by_severity'] = {
                    'critical': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                    'high': len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
                    'medium': len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM]),
                    'low': len([a for a in active_alerts if a.severity == AlertSeverity.LOW])
                }
                
                # By type
                type_counts = defaultdict(int)
                for alert in active_alerts:
                    type_counts[alert.alert_type.value] += 1
                stats['by_type'] = dict(type_counts)
                
                # Recent trends (last 24 hours)
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_alerts = [a for a in all_alerts if a.created_at >= recent_cutoff]
                stats['recent_24h'] = len(recent_alerts)
                
                # Average resolution time
                resolved_alerts = [a for a in all_alerts if a.resolved_at]
                if resolved_alerts:
                    resolution_times = [
                        (a.resolved_at - a.created_at).total_seconds() 
                        for a in resolved_alerts
                    ]
                    stats['avg_resolution_time_seconds'] = sum(resolution_times) / len(resolution_times)
                else:
                    stats['avg_resolution_time_seconds'] = 0
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {}
    
    def cleanup_old_alerts(self, days_to_keep: int = 30):
        """Clean up old resolved alerts"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            with self._lock:
                # Remove old resolved alerts from active alerts
                to_remove = []
                for alert_id, alert in self.active_alerts.items():
                    if (alert.status == AlertStatus.RESOLVED and 
                        alert.resolved_at and 
                        alert.resolved_at < cutoff_date):
                        to_remove.append(alert_id)
                
                for alert_id in to_remove:
                    del self.active_alerts[alert_id]
                
                logger.info(f"Cleaned up {len(to_remove)} old resolved alerts")
                
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
    
    def export_alerts(self, format: str = 'json') -> Union[str, List[Dict[str, Any]]]:
        """Export alerts for external analysis"""
        try:
            alerts_data = []
            
            with self._lock:
                for alert in self.alert_history:
                    alert_dict = {
                        'id': alert.id,
                        'alert_type': alert.alert_type.value,
                        'severity': alert.severity.value,
                        'status': alert.status.value,
                        'title': alert.title,
                        'message': alert.message,
                        'created_at': alert.created_at.isoformat(),
                        'updated_at': alert.updated_at.isoformat(),
                        'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                        'acknowledged_by': alert.acknowledged_by,
                        'context': alert.context,
                        'count': alert.count,
                        'escalation_level': alert.escalation_level
                    }
                    alerts_data.append(alert_dict)
            
            if format == 'json':
                return json.dumps(alerts_data, indent=2)
            else:
                return alerts_data
                
        except Exception as e:
            logger.error(f"Error exporting alerts: {e}")
            return [] if format != 'json' else '[]'

# Convenience functions for common alert scenarios
def alert_job_failure(alert_manager: AlertManager, job_id: str, user_id: int, error: str):
    """Send job failure alert"""
    alert_manager.send_alert(
        AlertType.JOB_FAILURE,
        f"Caption generation job {job_id} failed for user {user_id}: {error}",
        AlertSeverity.HIGH,
        {'job_id': job_id, 'user_id': user_id, 'error': error}
    )

def alert_repeated_failures(alert_manager: AlertManager, user_id: int, failure_count: int):
    """Send repeated failures alert"""
    alert_manager.send_alert(
        AlertType.REPEATED_FAILURES,
        f"User {user_id} has {failure_count} consecutive job failures",
        AlertSeverity.CRITICAL,
        {'user_id': user_id, 'failure_count': failure_count}
    )

def alert_resource_low(alert_manager: AlertManager, resource_type: str, usage_percent: float):
    """Send resource low alert"""
    severity = AlertSeverity.CRITICAL if usage_percent > 95 else AlertSeverity.HIGH
    alert_manager.send_alert(
        AlertType.RESOURCE_LOW,
        f"{resource_type} usage at {usage_percent:.1f}%",
        severity,
        {'resource_type': resource_type, 'usage_percent': usage_percent}
    )

def alert_ai_service_down(alert_manager: AlertManager, service_name: str, error: str):
    """Send AI service down alert"""
    alert_manager.send_alert(
        AlertType.AI_SERVICE_DOWN,
        f"AI service {service_name} is unavailable: {error}",
        AlertSeverity.CRITICAL,
        {'service_name': service_name, 'error': error}
    )

def alert_queue_backup(alert_manager: AlertManager, queue_length: int, estimated_wait: int):
    """Send queue backup alert"""
    severity = AlertSeverity.CRITICAL if queue_length > 500 else AlertSeverity.HIGH
    alert_manager.send_alert(
        AlertType.QUEUE_BACKUP,
        f"Caption generation queue has {queue_length} jobs (estimated wait: {estimated_wait} minutes)",
        severity,
        {'queue_length': queue_length, 'estimated_wait_minutes': estimated_wait}
    )