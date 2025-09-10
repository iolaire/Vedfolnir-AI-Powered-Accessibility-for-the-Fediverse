# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Alerting System

Real-time security alerting for CSRF violations and security incidents.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityAlert:
    """Security alert data structure"""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    source: str

class SecurityAlertManager:
    """Manages security alerts and notifications"""
    
    def __init__(self):
        """Initialize security alert manager"""
        self.alert_handlers = []
        self.alert_history = []
        self.alert_thresholds = {
            'csrf_violations_per_hour': 10,
            'failed_logins_per_hour': 20,
            'suspicious_requests_per_hour': 50
        }
    
    def trigger_csrf_violation_alert(self, violation_count: int, source_ip: str, 
                                   time_window: str = "1 hour") -> str:
        """Trigger CSRF violation alert"""
        severity = AlertSeverity.HIGH if violation_count > 20 else AlertSeverity.MEDIUM
        
        alert = SecurityAlert(
            alert_id=f"csrf_violation_{int(datetime.now().timestamp())}",
            alert_type="csrf_violation",
            severity=severity,
            message=f"High CSRF violation rate detected: {violation_count} violations in {time_window}",
            details={
                'violation_count': violation_count,
                'source_ip': source_ip,
                'time_window': time_window,
                'threshold': self.alert_thresholds['csrf_violations_per_hour']
            },
            timestamp=datetime.now(),
            source="csrf_monitoring"
        )
        
        return self._process_alert(alert)
    
    def trigger_security_compliance_alert(self, compliance_rate: float, 
                                        component: str) -> str:
        """Trigger security compliance alert"""
        severity = AlertSeverity.CRITICAL if compliance_rate < 0.7 else AlertSeverity.HIGH
        
        alert = SecurityAlert(
            alert_id=f"compliance_{component}_{int(datetime.now().timestamp())}",
            alert_type="compliance_degradation",
            severity=severity,
            message=f"Security compliance degraded for {component}: {compliance_rate:.1%}",
            details={
                'compliance_rate': compliance_rate,
                'component': component,
                'threshold': 0.8
            },
            timestamp=datetime.now(),
            source="compliance_monitoring"
        )
        
        return self._process_alert(alert)
    
    def _process_alert(self, alert: SecurityAlert) -> str:
        """Process and distribute security alert"""
        # Log the alert
        log_level = {
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(alert.severity, logging.WARNING)
        
        logger.log(log_level, f"SECURITY_ALERT: {alert.message}")
        
        # Store alert in history
        self.alert_history.append(alert)
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Send notifications
        self._send_alert_notifications(alert)
        
        return alert.alert_id
    
    def _send_alert_notifications(self, alert: SecurityAlert) -> None:
        """Send alert notifications"""
        try:
            # Log-based notification (always available)
            alert_data = {
                'alert_id': alert.alert_id,
                'type': alert.alert_type,
                'severity': alert.severity.value,
                'message': alert.message,
                'details': alert.details,
                'timestamp': alert.timestamp.isoformat()
            }
            
            logger.critical(f"SECURITY_NOTIFICATION: {json.dumps(alert_data)}")
            
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[SecurityAlert]:
        """Get recent security alerts"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        return [
            alert for alert in self.alert_history
            if alert.timestamp.timestamp() > cutoff_time
        ]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary for dashboard"""
        recent_alerts = self.get_recent_alerts(24)
        
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([
                a for a in recent_alerts if a.severity == severity
            ])
        
        alert_types = {}
        for alert in recent_alerts:
            alert_types[alert.alert_type] = alert_types.get(alert.alert_type, 0) + 1
        
        return {
            'total_alerts_24h': len(recent_alerts),
            'severity_distribution': severity_counts,
            'alert_types': alert_types,
            'latest_alert': recent_alerts[-1].timestamp.isoformat() if recent_alerts else None,
            'critical_alerts': severity_counts.get('critical', 0),
            'high_alerts': severity_counts.get('high', 0)
        }

# Global alert manager instance
_security_alert_manager = None

def get_security_alert_manager() -> SecurityAlertManager:
    """Get global security alert manager instance"""
    global _security_alert_manager
    if _security_alert_manager is None:
        _security_alert_manager = SecurityAlertManager()
    return _security_alert_manager

def trigger_csrf_violation_alert(violation_count: int, source_ip: str) -> str:
    """Convenience function to trigger CSRF violation alert"""
    manager = get_security_alert_manager()
    return manager.trigger_csrf_violation_alert(violation_count, source_ip)