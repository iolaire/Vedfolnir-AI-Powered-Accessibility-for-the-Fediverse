# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Alerting System

Provides comprehensive alerting capabilities for session management issues including
threshold monitoring, alert escalation, notification delivery, and alert management.
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from logging import getLogger
from collections import defaultdict, deque
from threading import Lock

from session_health_checker import SessionHealthChecker, SessionHealthStatus
from session_config import get_session_config
from security.core.security_utils import sanitize_for_log

logger = getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

@dataclass
class Alert:
    """Session management alert"""
    id: str
    component: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    count: int = 1

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    component: str
    metric: str
    condition: str  # 'gt', 'lt', 'eq', 'ne'
    threshold: float
    severity: AlertSeverity
    duration_seconds: int = 0  # How long condition must persist
    cooldown_seconds: int = 300  # Minimum time between alerts
    enabled: bool = True

class SessionAlertingSystem:
    """Comprehensive alerting system for session management"""
    
    def __init__(self, health_checker: SessionHealthChecker):
        self.health_checker = health_checker
        self.config = get_session_config()
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_rules: List[AlertRule] = []
        self._lock = Lock()
        
        # Alert tracking
        self.condition_start_times: Dict[str, datetime] = {}
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Notification handlers
        self.notification_handlers: List[Callable[[Alert], None]] = []
        
        # Initialize default alert rules
        self._initialize_default_rules()
        
        # Start monitoring if enabled
        if self.config.monitoring.enable_alerting:
            self._start_monitoring()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            # Database session alerts
            AlertRule(
                name="High Database Response Time",
                component="database_sessions",
                metric="response_time_ms",
                condition="gt",
                threshold=5000,  # 5 seconds
                severity=AlertSeverity.CRITICAL,
                duration_seconds=30,
                cooldown_seconds=300
            ),
            AlertRule(
                name="High Session Count",
                component="database_sessions",
                metric="session_count",
                condition="gt",
                threshold=1000,
                severity=AlertSeverity.WARNING,
                duration_seconds=60,
                cooldown_seconds=600
            ),
            AlertRule(
                name="High Pool Utilization",
                component="database_sessions",
                metric="pool_utilization",
                condition="gt",
                threshold=0.9,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=30,
                cooldown_seconds=300
            ),
            
            # Platform switching alerts
            AlertRule(
                name="Orphaned Platform Sessions",
                component="platform_switching",
                metric="orphaned_sessions",
                condition="gt",
                threshold=0,
                severity=AlertSeverity.WARNING,
                duration_seconds=300,
                cooldown_seconds=1800
            ),
            
            # Session cleanup alerts
            AlertRule(
                name="Overdue Session Cleanup",
                component="session_cleanup",
                metric="overdue_cleanup",
                condition="gt",
                threshold=50,
                severity=AlertSeverity.WARNING,
                duration_seconds=600,
                cooldown_seconds=3600
            ),
            AlertRule(
                name="Ancient Sessions Detected",
                component="session_cleanup",
                metric="ancient_sessions",
                condition="gt",
                threshold=10,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=300,
                cooldown_seconds=1800
            ),
            
            # Security alerts
            AlertRule(
                name="Orphaned User Sessions",
                component="session_security",
                metric="orphaned_sessions",
                condition="gt",
                threshold=0,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=0,
                cooldown_seconds=300
            ),
            AlertRule(
                name="Inactive User Sessions",
                component="session_security",
                metric="inactive_user_sessions",
                condition="gt",
                threshold=5,
                severity=AlertSeverity.WARNING,
                duration_seconds=600,
                cooldown_seconds=3600
            )
        ]
        
        self.alert_rules.extend(default_rules)
        logger.info(f"Initialized {len(default_rules)} default alert rules")
    
    def _start_monitoring(self):
        """Start background monitoring for alerts"""
        logger.info("Session alerting system monitoring started")
        # Note: In a production system, this would start a background thread
        # For now, alerts are checked when health checks are performed
    
    def check_alerts(self) -> List[Alert]:
        """Check for new alerts based on current system health"""
        try:
            # Get current system health
            system_health = self.health_checker.check_comprehensive_session_health()
            
            new_alerts = []
            current_time = datetime.now(timezone.utc)
            
            # Check each alert rule
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # Get component health
                component_health = system_health.components.get(rule.component)
                if not component_health or not component_health.metrics:
                    continue
                
                # Get metric value
                metric_value = component_health.metrics.get(rule.metric)
                if metric_value is None:
                    continue
                
                # Check condition
                condition_met = self._evaluate_condition(metric_value, rule.condition, rule.threshold)
                rule_key = f"{rule.component}_{rule.metric}_{rule.condition}_{rule.threshold}"
                
                if condition_met:
                    # Track when condition started
                    if rule_key not in self.condition_start_times:
                        self.condition_start_times[rule_key] = current_time
                    
                    # Check if condition has persisted long enough
                    condition_duration = (current_time - self.condition_start_times[rule_key]).total_seconds()
                    
                    if condition_duration >= rule.duration_seconds:
                        # Check cooldown period
                        last_alert_time = self.last_alert_times.get(rule_key)
                        if not last_alert_time or (current_time - last_alert_time).total_seconds() >= rule.cooldown_seconds:
                            # Create alert
                            alert = self._create_alert(rule, metric_value, component_health)
                            new_alerts.append(alert)
                            self.last_alert_times[rule_key] = current_time
                else:
                    # Condition not met, reset tracking
                    if rule_key in self.condition_start_times:
                        del self.condition_start_times[rule_key]
            
            # Process new alerts
            with self._lock:
                for alert in new_alerts:
                    self._process_new_alert(alert)
            
            # Check for resolved alerts
            self._check_resolved_alerts(system_health)
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False
    
    def _create_alert(self, rule: AlertRule, metric_value: float, component_health) -> Alert:
        """Create a new alert"""
        alert_id = f"{rule.component}_{rule.metric}_{int(time.time())}"
        
        # Check if similar alert already exists
        existing_alert = self._find_similar_alert(rule.component, rule.name)
        if existing_alert:
            # Update existing alert
            existing_alert.count += 1
            existing_alert.updated_at = datetime.now(timezone.utc)
            existing_alert.metrics = component_health.metrics
            return existing_alert
        
        # Create new alert
        alert = Alert(
            id=alert_id,
            component=rule.component,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            title=rule.name,
            message=f"{rule.name}: {rule.metric} = {metric_value} (threshold: {rule.threshold})",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            details={
                "rule_name": rule.name,
                "metric": rule.metric,
                "value": metric_value,
                "threshold": rule.threshold,
                "condition": rule.condition,
                "component_status": component_health.status.value,
                "component_message": component_health.message
            },
            metrics=component_health.metrics
        )
        
        return alert
    
    def _find_similar_alert(self, component: str, title: str) -> Optional[Alert]:
        """Find similar active alert"""
        for alert in self.active_alerts.values():
            if alert.component == component and alert.title == title and alert.status == AlertStatus.ACTIVE:
                return alert
        return None
    
    def _process_new_alert(self, alert: Alert):
        """Process a new alert"""
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"New {alert.severity.value} alert: {alert.title} - {alert.message}")
        
        # Send notifications
        self._send_notifications(alert)
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error sending alert notification: {e}")
    
    def _check_resolved_alerts(self, system_health):
        """Check if any active alerts should be resolved"""
        resolved_alerts = []
        
        with self._lock:
            for alert_id, alert in list(self.active_alerts.items()):
                if alert.status != AlertStatus.ACTIVE:
                    continue
                
                # Check if the underlying condition is resolved
                component_health = system_health.components.get(alert.component)
                if component_health and component_health.status == SessionHealthStatus.HEALTHY:
                    # Mark as resolved
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now(timezone.utc)
                    alert.updated_at = datetime.now(timezone.utc)
                    resolved_alerts.append(alert)
                    
                    logger.info(f"Alert resolved: {alert.title}")
        
        # Remove resolved alerts from active list after some time
        current_time = datetime.now(timezone.utc)
        for alert_id, alert in list(self.active_alerts.items()):
            if (alert.status == AlertStatus.RESOLVED and 
                alert.resolved_at and 
                (current_time - alert.resolved_at).total_seconds() > 3600):  # 1 hour
                del self.active_alerts[alert_id]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            with self._lock:
                alert = self.active_alerts.get(alert_id)
                if not alert:
                    return False
                
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.now(timezone.utc)
                
                logger.info(f"Alert acknowledged by {sanitize_for_log(acknowledged_by)}: {alert.title}")
                return True
                
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Manually resolve an alert"""
        try:
            with self._lock:
                alert = self.active_alerts.get(alert_id)
                if not alert:
                    return False
                
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc)
                alert.updated_at = datetime.now(timezone.utc)
                
                logger.info(f"Alert manually resolved by {sanitize_for_log(resolved_by)}: {alert.title}")
                return True
                
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        with self._lock:
            alerts = [alert for alert in self.active_alerts.values() 
                     if alert.status == AlertStatus.ACTIVE]
            
            if severity:
                alerts = [alert for alert in alerts if alert.severity == severity]
            
            # Sort by severity and creation time
            severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
            alerts.sort(key=lambda a: (severity_order[a.severity], a.created_at))
            
            return alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics"""
        with self._lock:
            active_alerts = [alert for alert in self.active_alerts.values() 
                           if alert.status == AlertStatus.ACTIVE]
            
            summary = {
                "total_active": len(active_alerts),
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "warning": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in active_alerts if a.severity == AlertSeverity.INFO]),
                "acknowledged": len([a for a in active_alerts if a.status == AlertStatus.ACKNOWLEDGED]),
                "total_rules": len(self.alert_rules),
                "enabled_rules": len([r for r in self.alert_rules if r.enabled])
            }
            
            # Component breakdown
            component_counts = defaultdict(int)
            for alert in active_alerts:
                component_counts[alert.component] += 1
            
            summary["by_component"] = dict(component_counts)
            
            return summary
    
    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """Add a notification handler"""
        self.notification_handlers.append(handler)
        logger.info("Added alert notification handler")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add a custom alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    def update_alert_rule(self, rule_name: str, **kwargs) -> bool:
        """Update an existing alert rule"""
        for rule in self.alert_rules:
            if rule.name == rule_name:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                logger.info(f"Updated alert rule: {rule_name}")
                return True
        return False
    
    def disable_alert_rule(self, rule_name: str) -> bool:
        """Disable an alert rule"""
        return self.update_alert_rule(rule_name, enabled=False)
    
    def enable_alert_rule(self, rule_name: str) -> bool:
        """Enable an alert rule"""
        return self.update_alert_rule(rule_name, enabled=True)
    
    def export_alerts(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Export alerts for external analysis"""
        with self._lock:
            alerts = list(self.active_alerts.values())
            
            if include_resolved:
                alerts.extend([alert for alert in self.alert_history 
                             if alert.status == AlertStatus.RESOLVED])
            
            return [self._alert_to_dict(alert) for alert in alerts]
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        result = asdict(alert)
        
        # Convert enums and datetime objects
        result["severity"] = alert.severity.value
        result["status"] = alert.status.value
        result["created_at"] = alert.created_at.isoformat()
        result["updated_at"] = alert.updated_at.isoformat()
        
        if alert.acknowledged_at:
            result["acknowledged_at"] = alert.acknowledged_at.isoformat()
        if alert.resolved_at:
            result["resolved_at"] = alert.resolved_at.isoformat()
        
        return result

# Default notification handlers
def log_notification_handler(alert: Alert):
    """Log alert notifications"""
    log_level = logger.error if alert.severity == AlertSeverity.CRITICAL else logger.warning
    log_level(f"ALERT [{alert.severity.value.upper()}] {alert.component}: {alert.message}")

def console_notification_handler(alert: Alert):
    """Print alert to console"""
    timestamp = alert.created_at.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ALERT [{alert.severity.value.upper()}] {alert.component}: {alert.message}")

# Global alerting system instance
_alerting_system = None

def get_alerting_system(health_checker: SessionHealthChecker) -> SessionAlertingSystem:
    """Get or create global alerting system instance"""
    global _alerting_system
    if _alerting_system is None:
        _alerting_system = SessionAlertingSystem(health_checker)
        # Add default notification handlers
        _alerting_system.add_notification_handler(log_notification_handler)
        if get_session_config().monitoring.enable_console_alerts:
            _alerting_system.add_notification_handler(console_notification_handler)
    return _alerting_system