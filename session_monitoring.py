# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Monitoring and Logging Infrastructure
Provides comprehensive monitoring, metrics collection, and diagnostic capabilities for session management
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from logging import getLogger
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from threading import Lock

from models import UserSession, User
from database import DatabaseManager
from security.core.security_utils import sanitize_for_log
from session_config import get_session_config, SessionConfig

logger = getLogger(__name__)

@dataclass
class SessionMetric:
    """Data class for session metrics"""
    timestamp: datetime
    metric_type: str
    session_id: str
    user_id: int
    value: float
    metadata: Dict[str, Any]

@dataclass
class SessionEvent:
    """Data class for session events"""
    timestamp: datetime
    event_type: str
    session_id: str
    user_id: int
    details: Dict[str, Any]
    severity: str = 'info'

class SessionMonitor:
    """Comprehensive session monitoring and metrics collection"""
    
    def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig] = None):
        self.db_manager = db_manager
        self.config = config or get_session_config()
        
        # Use configuration for buffer sizes and thresholds
        self.metrics_buffer = deque(maxlen=self.config.monitoring.metrics_buffer_size)
        self.events_buffer = deque(maxlen=self.config.monitoring.events_buffer_size)
        self.performance_stats = defaultdict(list)
        self.alert_thresholds = self.config.monitoring.alert_thresholds
        self._lock = Lock()
        
        # Initialize monitoring if enabled
        if self.config.monitoring.enable_performance_monitoring:
            self._initialize_monitoring()
    
    def _initialize_monitoring(self):
        """Initialize monitoring system"""
        logger.info("Initializing session monitoring system")
        
        # Log initial system state
        self.log_system_startup()
    
    def log_system_startup(self):
        """Log system startup information"""
        try:
            with self.db_manager.get_session() as db_session:
                active_sessions = db_session.query(UserSession).count()
                
            startup_event = SessionEvent(
                timestamp=datetime.now(timezone.utc),
                event_type='system_startup',
                session_id='system',
                user_id=0,
                details={
                    'active_sessions_at_startup': active_sessions,
                    'monitoring_initialized': True
                },
                severity='info'
            )
            
            self.record_event(startup_event)
            logger.info(f"Session monitoring initialized - {active_sessions} active sessions")
            
        except Exception as e:
            logger.error(f"Error logging system startup: {e}")
    
    def record_metric(self, metric_type: str, session_id: str, user_id: int, 
                     value: float, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a session metric
        
        Args:
            metric_type: Type of metric (e.g., 'session_duration', 'sync_time')
            session_id: Session ID
            user_id: User ID
            value: Metric value
            metadata: Additional metadata
        """
        try:
            metric = SessionMetric(
                timestamp=datetime.now(timezone.utc),
                metric_type=metric_type,
                session_id=session_id,
                user_id=user_id,
                value=value,
                metadata=metadata or {}
            )
            
            with self._lock:
                self.metrics_buffer.append(metric)
                self.performance_stats[metric_type].append(value)
                
                # Keep only recent performance stats
                if len(self.performance_stats[metric_type]) > 100:
                    self.performance_stats[metric_type] = self.performance_stats[metric_type][-100:]
            
            # Check for alerts
            self._check_metric_alerts(metric)
            
            logger.debug(f"Recorded metric: {metric_type} = {value} for session {sanitize_for_log(session_id)}")
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def record_event(self, event: SessionEvent):
        """
        Record a session event
        
        Args:
            event: SessionEvent object
        """
        try:
            with self._lock:
                self.events_buffer.append(event)
            
            # Log event based on severity
            log_message = f"Session event: {event.event_type} for session {sanitize_for_log(event.session_id)}"
            
            if event.severity == 'error':
                logger.error(log_message)
            elif event.severity == 'warning':
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # Check for alerts
            self._check_event_alerts(event)
            
        except Exception as e:
            logger.error(f"Error recording event: {e}")
    
    def log_session_created(self, session_id: str, user_id: int, platform_id: Optional[int] = None):
        """Log session creation"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_created',
            session_id=session_id,
            user_id=user_id,
            details={
                'platform_id': platform_id,
                'creation_method': 'standard'
            }
        )
        self.record_event(event)
        
        # Record creation rate metric
        self.record_metric('session_creation_rate', session_id, user_id, 1.0)
    
    def log_session_expired(self, session_id: str, user_id: int, reason: str = 'timeout'):
        """Log session expiration"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_expired',
            session_id=session_id,
            user_id=user_id,
            details={
                'expiration_reason': reason,
                'cleanup_performed': True
            },
            severity='info'
        )
        self.record_event(event)
    
    def log_session_error(self, session_id: str, user_id: int, error_type: str, error_details: str):
        """Log session error"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_error',
            session_id=session_id,
            user_id=user_id,
            details={
                'error_type': error_type,
                'error_details': sanitize_for_log(error_details)
            },
            severity='error'
        )
        self.record_event(event)
        
        # Record error rate metric
        self.record_metric('session_error_rate', session_id, user_id, 1.0)
    
    def log_platform_switch(self, session_id: str, user_id: int, old_platform_id: Optional[int], 
                           new_platform_id: int, switch_duration: float):
        """Log platform switch"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='platform_switch',
            session_id=session_id,
            user_id=user_id,
            details={
                'old_platform_id': old_platform_id,
                'new_platform_id': new_platform_id,
                'switch_duration_ms': switch_duration
            }
        )
        self.record_event(event)
        
        # Record switch performance metric
        self.record_metric('platform_switch_duration', session_id, user_id, switch_duration)
    
    def log_suspicious_activity(self, session_id: str, user_id: int, activity_type: str, details: Dict[str, Any]):
        """Log suspicious session activity"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='suspicious_activity',
            session_id=session_id,
            user_id=user_id,
            details={
                'activity_type': activity_type,
                **details
            },
            severity='warning'
        )
        self.record_event(event)
        
        # Record suspicious activity metric
        self.record_metric('suspicious_activity_rate', session_id, user_id, 1.0)
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive session statistics
        
        Returns:
            Dictionary with session statistics
        """
        try:
            with self.db_manager.get_session() as db_session:
                # Get basic session counts
                total_sessions = db_session.query(UserSession).count()
                
                # Get active sessions (not expired)
                now = datetime.now(timezone.utc)
                cutoff_time = now - timedelta(hours=48)  # Default session timeout
                
                active_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at >= cutoff_time
                ).count()
                
                # Get user statistics
                unique_users = db_session.query(UserSession.user_id).distinct().count()
            
            # Calculate performance statistics
            with self._lock:
                performance_stats = {}
                for metric_type, values in self.performance_stats.items():
                    if values:
                        performance_stats[metric_type] = {
                            'count': len(values),
                            'avg': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values),
                            'recent': values[-10:] if len(values) >= 10 else values
                        }
                
                # Get recent events summary
                recent_events = list(self.events_buffer)[-50:]  # Last 50 events
                event_summary = defaultdict(int)
                for event in recent_events:
                    event_summary[event.event_type] += 1
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_counts': {
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'unique_users': unique_users
                },
                'performance_stats': performance_stats,
                'recent_events': dict(event_summary),
                'monitoring_health': {
                    'metrics_buffer_size': len(self.metrics_buffer),
                    'events_buffer_size': len(self.events_buffer),
                    'monitoring_active': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {'error': str(e)}
    
    def get_session_health_report(self) -> Dict[str, Any]:
        """
        Generate session health report
        
        Returns:
            Dictionary with health report
        """
        try:
            stats = self.get_session_statistics()
            
            # Analyze health indicators
            health_indicators = {
                'overall_health': 'good',
                'issues': [],
                'recommendations': []
            }
            
            # Check session creation rate
            if 'session_creation_rate' in stats.get('performance_stats', {}):
                creation_stats = stats['performance_stats']['session_creation_rate']
                if creation_stats['avg'] > self.alert_thresholds['session_creation_rate']:
                    health_indicators['issues'].append('High session creation rate detected')
                    health_indicators['overall_health'] = 'warning'
            
            # Check error rates
            if 'session_error_rate' in stats.get('performance_stats', {}):
                error_stats = stats['performance_stats']['session_error_rate']
                if error_stats['avg'] > self.alert_thresholds['session_failure_rate']:
                    health_indicators['issues'].append('High session error rate detected')
                    health_indicators['overall_health'] = 'critical'
            
            # Check concurrent sessions
            active_sessions = stats.get('session_counts', {}).get('active_sessions', 0)
            if active_sessions > self.alert_thresholds['concurrent_sessions']:
                health_indicators['issues'].append('High number of concurrent sessions')
                health_indicators['overall_health'] = 'warning'
            
            # Generate recommendations
            if not health_indicators['issues']:
                health_indicators['recommendations'].append('Session system is operating normally')
            else:
                health_indicators['recommendations'].append('Review session management configuration')
                health_indicators['recommendations'].append('Consider implementing session cleanup policies')
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'health_status': health_indicators,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {'error': str(e)}
    
    def _check_metric_alerts(self, metric: SessionMetric):
        """Check if metric triggers any alerts"""
        try:
            # Implement alert logic based on thresholds
            if metric.metric_type in self.alert_thresholds:
                threshold = self.alert_thresholds[metric.metric_type]
                
                if metric.value > threshold:
                    logger.warning(f"Alert: {metric.metric_type} value {metric.value} exceeds threshold {threshold}")
                    
                    # Record alert event
                    alert_event = SessionEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type='metric_alert',
                        session_id=metric.session_id,
                        user_id=metric.user_id,
                        details={
                            'metric_type': metric.metric_type,
                            'value': metric.value,
                            'threshold': threshold
                        },
                        severity='warning'
                    )
                    self.record_event(alert_event)
                    
        except Exception as e:
            logger.error(f"Error checking metric alerts: {e}")
    
    def _check_event_alerts(self, event: SessionEvent):
        """Check if event triggers any alerts"""
        try:
            # Count recent events of the same type
            recent_events = [e for e in self.events_buffer 
                           if e.event_type == event.event_type 
                           and (datetime.now(timezone.utc) - e.timestamp).total_seconds() < 60]
            
            # Alert on high frequency of certain events
            if event.event_type in ['session_error', 'suspicious_activity'] and len(recent_events) > 5:
                logger.warning(f"Alert: High frequency of {event.event_type} events: {len(recent_events)} in last minute")
                
        except Exception as e:
            logger.error(f"Error checking event alerts: {e}")
    
    def export_metrics(self, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Export metrics for external analysis
        
        Args:
            start_time: Start time for export (optional)
            end_time: End time for export (optional)
            
        Returns:
            List of metric dictionaries
        """
        try:
            with self._lock:
                metrics = list(self.metrics_buffer)
            
            # Filter by time range if specified
            if start_time or end_time:
                filtered_metrics = []
                for metric in metrics:
                    if start_time and metric.timestamp < start_time:
                        continue
                    if end_time and metric.timestamp > end_time:
                        continue
                    filtered_metrics.append(metric)
                metrics = filtered_metrics
            
            # Convert to dictionaries
            return [asdict(metric) for metric in metrics]
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int = 7):
        """
        Clean up old monitoring data
        
        Args:
            retention_days: Number of days to retain data
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            with self._lock:
                # Clean up old metrics
                self.metrics_buffer = deque(
                    [m for m in self.metrics_buffer if m.timestamp >= cutoff_time],
                    maxlen=1000
                )
                
                # Clean up old events
                self.events_buffer = deque(
                    [e for e in self.events_buffer if e.timestamp >= cutoff_time],
                    maxlen=500
                )
            
            logger.info(f"Cleaned up monitoring data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old monitoring data: {e}")

# Global session monitor instance
session_monitor = None

def get_session_monitor(db_manager: DatabaseManager, config: Optional[SessionConfig] = None) -> Optional[SessionMonitor]:
    """Get or create global session monitor instance"""
    global session_monitor
    if session_monitor is None:
        session_config = config or get_session_config()
        if session_config.monitoring.enable_performance_monitoring:
            session_monitor = SessionMonitor(db_manager, session_config)
        else:
            return None
    return session_monitor