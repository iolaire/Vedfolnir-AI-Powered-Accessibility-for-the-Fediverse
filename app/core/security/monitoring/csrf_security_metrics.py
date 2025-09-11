# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Security Metrics System

Comprehensive CSRF violation tracking, compliance metrics, and real-time alerting.
Integrates with the existing security monitoring infrastructure.
"""

import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

from app.core.security.core.security_monitoring import (
    SecurityEventType, SecurityEventSeverity, security_monitor
)

logger = logging.getLogger(__name__)

class CSRFViolationType(Enum):
    """Types of CSRF violations"""
    MISSING_TOKEN = "missing_token"
    INVALID_TOKEN = "invalid_token"
    EXPIRED_TOKEN = "expired_token"
    TOKEN_MISMATCH = "token_mismatch"
    MALFORMED_TOKEN = "malformed_token"
    REPLAY_ATTACK = "replay_attack"
    SESSION_MISMATCH = "session_mismatch"

class CSRFComplianceLevel(Enum):
    """CSRF compliance levels"""
    EXCELLENT = "excellent"  # 95%+ compliance
    GOOD = "good"           # 85-94% compliance
    FAIR = "fair"           # 70-84% compliance
    POOR = "poor"           # <70% compliance

@dataclass
class CSRFViolationEvent:
    """CSRF violation event data"""
    violation_type: CSRFViolationType
    timestamp: datetime
    source_ip: str
    user_id: Optional[str]
    endpoint: str
    user_agent: str
    session_id: str
    request_method: str
    error_details: Dict[str, Any]
    event_id: str

@dataclass
class CSRFComplianceMetrics:
    """CSRF compliance metrics"""
    total_requests: int
    protected_requests: int
    violation_count: int
    compliance_rate: float
    compliance_level: CSRFComplianceLevel
    violations_by_type: Dict[str, int]
    violations_by_endpoint: Dict[str, int]
    violations_by_ip: Dict[str, int]
    time_period: str
    last_updated: datetime

class CSRFSecurityMetrics:
    """CSRF security metrics and monitoring system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize CSRF security metrics"""
        self.config = config or {}
        self.violations = deque(maxlen=50000)
        self.violation_counts = defaultdict(int)
        self.endpoint_violations = defaultdict(int)
        self.ip_violations = defaultdict(int)
        self.user_violations = defaultdict(int)
        self.hourly_metrics = defaultdict(lambda: defaultdict(int))
        self.lock = threading.Lock()
        
        self.alert_thresholds = {
            'violations_per_ip_per_hour': 10,
            'violations_per_user_per_hour': 5,
            'violations_per_endpoint_per_hour': 20,
            'total_violations_per_hour': 100,
            'compliance_rate_threshold': 0.85,
            'critical_endpoints': ['login', 'admin', 'user_management', 'platform_management']
        }
        
        self.request_counts = defaultdict(int)
        self.protected_counts = defaultdict(int)
        
        self.metrics_thread = threading.Thread(target=self._background_metrics_collection, daemon=True)
        self.metrics_thread.start()
        
        logger.info("CSRF security metrics system initialized")
    
    def track_csrf_violation(self, violation_type: CSRFViolationType, source_ip: str,
                           endpoint: str, user_agent: str = "", user_id: str = None,
                           session_id: str = "", request_method: str = "POST",
                           error_details: Dict[str, Any] = None) -> str:
        """Track a CSRF violation"""
        import uuid
        event_id = str(uuid.uuid4())
        
        violation = CSRFViolationEvent(
            violation_type=violation_type,
            timestamp=datetime.utcnow(),
            source_ip=source_ip,
            user_id=user_id,
            endpoint=endpoint,
            user_agent=user_agent[:500],
            session_id=session_id,
            request_method=request_method,
            error_details=error_details or {},
            event_id=event_id
        )
        
        with self.lock:
            self.violations.append(violation)
            self.violation_counts[violation_type.value] += 1
            self.endpoint_violations[endpoint] += 1
            self.ip_violations[source_ip] += 1
            if user_id:
                self.user_violations[user_id] += 1
            
            hour_key = violation.timestamp.strftime('%Y-%m-%d-%H')
            self.hourly_metrics[hour_key]['total'] += 1
            self.hourly_metrics[hour_key][violation_type.value] += 1
        
        self._log_csrf_violation(violation)
        
        security_monitor.log_security_event(
            SecurityEventType.CSRF_ATTACK,
            SecurityEventSeverity.MEDIUM,
            source_ip,
            endpoint,
            user_agent,
            user_id,
            {
                'violation_type': violation_type.value,
                'session_id': session_id,
                'request_method': request_method,
                'error_details': error_details
            }
        )
        
        self._check_csrf_alert_conditions(violation)
        
        return event_id
    
    def track_csrf_protection(self, endpoint: str, protected: bool = True):
        """Track CSRF protection usage"""
        with self.lock:
            self.request_counts[endpoint] += 1
            if protected:
                self.protected_counts[endpoint] += 1
    
    def _log_csrf_violation(self, violation: CSRFViolationEvent):
        """Log CSRF violation to standard logging"""
        log_data = {
            'event_id': violation.event_id,
            'violation_type': violation.violation_type.value,
            'timestamp': violation.timestamp.isoformat(),
            'source_ip': violation.source_ip,
            'user_id': violation.user_id,
            'endpoint': violation.endpoint,
            'session_id': violation.session_id[:8] if violation.session_id else 'unknown',
            'request_method': violation.request_method,
            'user_agent': violation.user_agent[:100],
            'error_details': violation.error_details
        }
        
        logger.warning(f"CSRF_VIOLATION: {json.dumps(log_data)}")
    
    def _check_csrf_alert_conditions(self, violation: CSRFViolationEvent):
        """Check if violation triggers alert conditions"""
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        
        recent_violations = [
            v for v in self.violations
            if v.timestamp > one_hour_ago
        ]
        
        # Check violations per IP
        ip_violations = [v for v in recent_violations if v.source_ip == violation.source_ip]
        if len(ip_violations) >= self.alert_thresholds['violations_per_ip_per_hour']:
            self._trigger_csrf_alert(
                'high_violations_per_ip',
                f"High CSRF violations from IP {violation.source_ip}",
                {
                    'source_ip': violation.source_ip,
                    'violation_count': len(ip_violations),
                    'time_window': '1 hour'
                }
            )
        
        # Check critical endpoint violations
        if violation.endpoint in self.alert_thresholds['critical_endpoints']:
            self._trigger_csrf_alert(
                'critical_endpoint_violation',
                f"CSRF violation on critical endpoint {violation.endpoint}",
                {
                    'endpoint': violation.endpoint,
                    'violation_type': violation.violation_type.value,
                    'source_ip': violation.source_ip
                }
            )
    
    def _trigger_csrf_alert(self, alert_type: str, message: str, details: Dict[str, Any]):
        """Trigger CSRF security alert"""
        alert_data = {
            'alert_id': f"csrf_{alert_type}_{int(time.time())}",
            'alert_type': alert_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details,
            'severity': 'HIGH' if 'critical' in alert_type else 'MEDIUM'
        }
        
        logger.critical(f"CSRF_ALERT: {json.dumps(alert_data)}")
        
        severity = SecurityEventSeverity.HIGH if 'critical' in alert_type else SecurityEventSeverity.MEDIUM
        security_monitor.log_security_event(
            SecurityEventType.CSRF_ATTACK,
            severity,
            details.get('source_ip', 'unknown'),
            details.get('endpoint', 'unknown'),
            '',
            details.get('user_id'),
            {'alert_type': alert_type, 'alert_details': details}
        )
    
    def get_compliance_metrics(self, time_period: str = '24h') -> CSRFComplianceMetrics:
        """Get CSRF compliance metrics"""
        if time_period == '1h':
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
        elif time_period == '24h':
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
        elif time_period == '7d':
            cutoff_time = datetime.utcnow() - timedelta(days=7)
        elif time_period == '30d':
            cutoff_time = datetime.utcnow() - timedelta(days=30)
        else:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        with self.lock:
            recent_violations = [
                v for v in self.violations
                if v.timestamp > cutoff_time
            ]
            
            total_requests = sum(self.request_counts.values())
            protected_requests = sum(self.protected_counts.values())
            violation_count = len(recent_violations)
            
            if total_requests > 0:
                compliance_rate = max(0.0, (total_requests - violation_count) / total_requests)
            else:
                compliance_rate = 1.0
            
            if compliance_rate >= 0.95:
                compliance_level = CSRFComplianceLevel.EXCELLENT
            elif compliance_rate >= 0.85:
                compliance_level = CSRFComplianceLevel.GOOD
            elif compliance_rate >= 0.70:
                compliance_level = CSRFComplianceLevel.FAIR
            else:
                compliance_level = CSRFComplianceLevel.POOR
            
            violations_by_type = defaultdict(int)
            for violation in recent_violations:
                violations_by_type[violation.violation_type.value] += 1
            
            violations_by_endpoint = defaultdict(int)
            for violation in recent_violations:
                violations_by_endpoint[violation.endpoint] += 1
            
            violations_by_ip = defaultdict(int)
            for violation in recent_violations:
                violations_by_ip[violation.source_ip] += 1
        
        return CSRFComplianceMetrics(
            total_requests=total_requests,
            protected_requests=protected_requests,
            violation_count=violation_count,
            compliance_rate=compliance_rate,
            compliance_level=compliance_level,
            violations_by_type=dict(violations_by_type),
            violations_by_endpoint=dict(violations_by_endpoint),
            violations_by_ip=dict(violations_by_ip),
            time_period=time_period,
            last_updated=datetime.utcnow()
        )
    
    def get_csrf_dashboard_data(self) -> Dict[str, Any]:
        """Get CSRF dashboard data for monitoring interface"""
        current_time = datetime.utcnow()
        
        metrics_1h = self.get_compliance_metrics('1h')
        metrics_24h = self.get_compliance_metrics('24h')
        metrics_7d = self.get_compliance_metrics('7d')
        
        recent_violations = [
            {
                'event_id': v.event_id,
                'violation_type': v.violation_type.value,
                'timestamp': v.timestamp.isoformat(),
                'source_ip': v.source_ip,
                'endpoint': v.endpoint,
                'user_id': v.user_id
            }
            for v in list(self.violations)[-20:]
        ]
        
        # Create serializable versions of metrics
        def serialize_metrics(metrics):
            return {
                'compliance_rate': metrics.compliance_rate,
                'total_requests': metrics.total_requests,
                'violation_count': metrics.violation_count,
                'compliance_level': str(metrics.compliance_level),
                'violations_by_type': metrics.violations_by_type,
                'violations_by_endpoint': metrics.violations_by_endpoint,
                'violations_by_ip': metrics.violations_by_ip,
                'time_period': metrics.time_period
            }
        
        return {
            'compliance_metrics': {
                '1h': serialize_metrics(metrics_1h),
                '24h': serialize_metrics(metrics_24h),
                '7d': serialize_metrics(metrics_7d)
            },
            'recent_violations': recent_violations,
            'top_violation_types': sorted(self.violation_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'top_violation_endpoints': sorted(self.endpoint_violations.items(), key=lambda x: x[1], reverse=True)[:10],
            'top_violation_ips': sorted(self.ip_violations.items(), key=lambda x: x[1], reverse=True)[:10],
            'last_updated': current_time.isoformat()
        }
    
    def _background_metrics_collection(self):
        """Background thread for metrics collection and cleanup"""
        while True:
            try:
                self._cleanup_old_data()
                self._generate_periodic_reports()
                time.sleep(300)
            except Exception as e:
                logger.error(f"Error in CSRF metrics background thread: {e}")
                time.sleep(60)
    
    def _cleanup_old_data(self):
        """Clean up old metrics data"""
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        
        with self.lock:
            old_keys = [
                key for key in self.hourly_metrics.keys()
                if datetime.strptime(key, '%Y-%m-%d-%H') < cutoff_time
            ]
            for key in old_keys:
                del self.hourly_metrics[key]
    
    def _generate_periodic_reports(self):
        """Generate periodic CSRF security reports"""
        try:
            metrics = self.get_compliance_metrics('24h')
            logger.info(f"CSRF_DAILY_SUMMARY: {json.dumps(asdict(metrics), default=str)}")
        except Exception as e:
            logger.error(f"Error generating CSRF periodic reports: {e}")

# Global CSRF security metrics instance
_csrf_security_metrics: Optional[CSRFSecurityMetrics] = None

def get_csrf_security_metrics() -> CSRFSecurityMetrics:
    """Get the global CSRF security metrics instance"""
    global _csrf_security_metrics
    if _csrf_security_metrics is None:
        _csrf_security_metrics = CSRFSecurityMetrics()
    return _csrf_security_metrics

def track_csrf_violation(violation_type: str, source_ip: str, endpoint: str,
                        user_agent: str = "", user_id: str = None,
                        session_id: str = "", request_method: str = "POST",
                        error_details: Dict[str, Any] = None) -> str:
    """Convenience function to track CSRF violations"""
    metrics = get_csrf_security_metrics()
    violation_enum = CSRFViolationType(violation_type)
    return metrics.track_csrf_violation(
        violation_enum, source_ip, endpoint, user_agent,
        user_id, session_id, request_method, error_details
    )

def track_csrf_protection(endpoint: str, protected: bool = True):
    """Convenience function to track CSRF protection usage"""
    metrics = get_csrf_security_metrics()
    metrics.track_csrf_protection(endpoint, protected)