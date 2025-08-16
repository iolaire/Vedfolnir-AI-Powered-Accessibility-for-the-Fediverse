# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Management Monitoring and Alerting System

This module provides comprehensive monitoring and alerting for user management operations,
including user activity tracking, security event monitoring, performance metrics, and
automated alerting for critical issues.
"""

import os
import sys
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from database import DatabaseManager
from models import User, UserSession, UserAuditLog, UserRole


@dataclass
class AlertThreshold:
    """Configuration for monitoring alert thresholds"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    time_window_minutes: int
    enabled: bool = True


@dataclass
class MonitoringMetric:
    """Container for monitoring metric data"""
    name: str
    value: float
    timestamp: datetime
    status: str  # 'ok', 'warning', 'critical'
    details: Dict[str, Any]


@dataclass
class Alert:
    """Container for alert information"""
    alert_id: str
    severity: str  # 'warning', 'critical'
    metric_name: str
    message: str
    timestamp: datetime
    details: Dict[str, Any]
    resolved: bool = False


class UserManagementMonitor:
    """
    Comprehensive monitoring system for user management operations.
    
    Monitors:
    - User registration rates and patterns
    - Authentication success/failure rates
    - Account security events
    - Email system performance
    - Database performance metrics
    - System resource usage
    """
    
    def __init__(self, config: Config):
        """
        Initialize monitoring system.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.db_manager = DatabaseManager(config)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize alert thresholds
        self.alert_thresholds = self._load_alert_thresholds()
        
        # Alert history for deduplication
        self.alert_history: List[Alert] = []
        
        # Metrics storage
        self.metrics_history: List[MonitoringMetric] = []
        
        # Email configuration for alerts
        self.smtp_config = {
            'server': os.getenv('ALERT_SMTP_SERVER', os.getenv('MAIL_SERVER')),
            'port': int(os.getenv('ALERT_SMTP_PORT', os.getenv('MAIL_PORT', 587))),
            'username': os.getenv('ALERT_SMTP_USERNAME', os.getenv('MAIL_USERNAME')),
            'password': os.getenv('ALERT_SMTP_PASSWORD', os.getenv('MAIL_PASSWORD')),
            'use_tls': os.getenv('ALERT_SMTP_USE_TLS', 'true').lower() == 'true',
            'from_address': os.getenv('ALERT_FROM_ADDRESS', os.getenv('MAIL_DEFAULT_SENDER')),
            'to_addresses': os.getenv('ALERT_TO_ADDRESSES', '').split(',')
        }
    
    def _load_alert_thresholds(self) -> List[AlertThreshold]:
        """Load alert threshold configuration"""
        return [
            # User registration monitoring
            AlertThreshold(
                metric_name='registration_rate',
                warning_threshold=50,  # registrations per hour
                critical_threshold=100,
                time_window_minutes=60
            ),
            
            # Authentication monitoring
            AlertThreshold(
                metric_name='failed_login_rate',
                warning_threshold=10,  # failed logins per minute
                critical_threshold=25,
                time_window_minutes=5
            ),
            
            # Account security monitoring
            AlertThreshold(
                metric_name='account_lockout_rate',
                warning_threshold=5,  # lockouts per hour
                critical_threshold=15,
                time_window_minutes=60
            ),
            
            # Email system monitoring
            AlertThreshold(
                metric_name='email_failure_rate',
                warning_threshold=5,  # percent failure rate
                critical_threshold=15,
                time_window_minutes=30
            ),
            
            # Database performance monitoring
            AlertThreshold(
                metric_name='db_response_time',
                warning_threshold=1000,  # milliseconds
                critical_threshold=3000,
                time_window_minutes=10
            ),
            
            # System resource monitoring
            AlertThreshold(
                metric_name='memory_usage_percent',
                warning_threshold=80,  # percent
                critical_threshold=95,
                time_window_minutes=5
            ),
            
            # Session monitoring
            AlertThreshold(
                metric_name='active_sessions',
                warning_threshold=1000,  # concurrent sessions
                critical_threshold=2000,
                time_window_minutes=5
            )
        ]
    
    def collect_user_metrics(self) -> List[MonitoringMetric]:
        """
        Collect user management metrics.
        
        Returns:
            List of monitoring metrics
        """
        metrics = []
        current_time = datetime.utcnow()
        
        try:
            session = self.db_manager.get_session()
            
            # User registration metrics
            registration_metrics = self._collect_registration_metrics(session, current_time)
            metrics.extend(registration_metrics)
            
            # Authentication metrics
            auth_metrics = self._collect_authentication_metrics(session, current_time)
            metrics.extend(auth_metrics)
            
            # Account security metrics
            security_metrics = self._collect_security_metrics(session, current_time)
            metrics.extend(security_metrics)
            
            # Email system metrics
            email_metrics = self._collect_email_metrics(session, current_time)
            metrics.extend(email_metrics)
            
            # Database performance metrics
            db_metrics = self._collect_database_metrics(session, current_time)
            metrics.extend(db_metrics)
            
            # Session metrics
            session_metrics = self._collect_session_metrics(session, current_time)
            metrics.extend(session_metrics)
            
            session.close()
            
        except Exception as e:
            self.logger.error(f"Error collecting user metrics: {e}")
            metrics.append(MonitoringMetric(
                name='metric_collection_error',
                value=1,
                timestamp=current_time,
                status='critical',
                details={'error': str(e)}
            ))
        
        return metrics
    
    def _collect_registration_metrics(self, session, current_time: datetime) -> List[MonitoringMetric]:
        """Collect user registration metrics"""
        metrics = []
        
        try:
            # Registration rate (last hour)
            hour_ago = current_time - timedelta(hours=1)
            recent_registrations = session.query(User).filter(
                User.created_at > hour_ago
            ).count()
            
            metrics.append(MonitoringMetric(
                name='registration_rate',
                value=recent_registrations,
                timestamp=current_time,
                status='ok',
                details={'time_window': '1_hour', 'count': recent_registrations}
            ))
            
            # Email verification rate
            unverified_users = session.query(User).filter(
                User.email_verified == False,
                User.created_at > hour_ago
            ).count()
            
            verification_rate = 0 if recent_registrations == 0 else (
                (recent_registrations - unverified_users) / recent_registrations * 100
            )
            
            metrics.append(MonitoringMetric(
                name='email_verification_rate',
                value=verification_rate,
                timestamp=current_time,
                status='ok',
                details={
                    'verified_count': recent_registrations - unverified_users,
                    'total_registrations': recent_registrations,
                    'rate_percent': verification_rate
                }
            ))
            
            # Total user count
            total_users = session.query(User).count()
            metrics.append(MonitoringMetric(
                name='total_users',
                value=total_users,
                timestamp=current_time,
                status='ok',
                details={'count': total_users}
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting registration metrics: {e}")
        
        return metrics
    
    def _collect_authentication_metrics(self, session, current_time: datetime) -> List[MonitoringMetric]:
        """Collect authentication metrics"""
        metrics = []
        
        try:
            # Failed login rate (last 5 minutes)
            five_min_ago = current_time - timedelta(minutes=5)
            failed_logins = session.query(UserAuditLog).filter(
                UserAuditLog.action == 'login_failed',
                UserAuditLog.created_at > five_min_ago
            ).count()
            
            metrics.append(MonitoringMetric(
                name='failed_login_rate',
                value=failed_logins,
                timestamp=current_time,
                status='ok',
                details={'time_window': '5_minutes', 'count': failed_logins}
            ))
            
            # Successful login rate
            successful_logins = session.query(UserAuditLog).filter(
                UserAuditLog.action == 'login_success',
                UserAuditLog.created_at > five_min_ago
            ).count()
            
            metrics.append(MonitoringMetric(
                name='successful_login_rate',
                value=successful_logins,
                timestamp=current_time,
                status='ok',
                details={'time_window': '5_minutes', 'count': successful_logins}
            ))
            
            # Login success rate percentage
            total_logins = failed_logins + successful_logins
            success_rate = 100 if total_logins == 0 else (successful_logins / total_logins * 100)
            
            metrics.append(MonitoringMetric(
                name='login_success_rate',
                value=success_rate,
                timestamp=current_time,
                status='ok',
                details={
                    'successful': successful_logins,
                    'failed': failed_logins,
                    'total': total_logins,
                    'rate_percent': success_rate
                }
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting authentication metrics: {e}")
        
        return metrics
    
    def _collect_security_metrics(self, session, current_time: datetime) -> List[MonitoringMetric]:
        """Collect security metrics"""
        metrics = []
        
        try:
            # Account lockout rate (last hour)
            hour_ago = current_time - timedelta(hours=1)
            lockout_events = session.query(UserAuditLog).filter(
                UserAuditLog.action == 'account_locked',
                UserAuditLog.created_at > hour_ago
            ).count()
            
            metrics.append(MonitoringMetric(
                name='account_lockout_rate',
                value=lockout_events,
                timestamp=current_time,
                status='ok',
                details={'time_window': '1_hour', 'count': lockout_events}
            ))
            
            # Currently locked accounts
            locked_accounts = session.query(User).filter(
                User.account_locked == True
            ).count()
            
            metrics.append(MonitoringMetric(
                name='locked_accounts_count',
                value=locked_accounts,
                timestamp=current_time,
                status='ok',
                details={'count': locked_accounts}
            ))
            
            # Password reset requests (last hour)
            password_resets = session.query(UserAuditLog).filter(
                UserAuditLog.action == 'password_reset_requested',
                UserAuditLog.created_at > hour_ago
            ).count()
            
            metrics.append(MonitoringMetric(
                name='password_reset_rate',
                value=password_resets,
                timestamp=current_time,
                status='ok',
                details={'time_window': '1_hour', 'count': password_resets}
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting security metrics: {e}")
        
        return metrics
    
    def _collect_email_metrics(self, session, current_time: datetime) -> List[MonitoringMetric]:
        """Collect email system metrics"""
        metrics = []
        
        try:
            # Email sending attempts (last 30 minutes)
            thirty_min_ago = current_time - timedelta(minutes=30)
            
            email_sent = session.query(UserAuditLog).filter(
                UserAuditLog.action.in_(['email_sent', 'verification_email_sent', 'reset_email_sent']),
                UserAuditLog.created_at > thirty_min_ago
            ).count()
            
            email_failed = session.query(UserAuditLog).filter(
                UserAuditLog.action.in_(['email_failed', 'email_delivery_failed']),
                UserAuditLog.created_at > thirty_min_ago
            ).count()
            
            total_email_attempts = email_sent + email_failed
            failure_rate = 0 if total_email_attempts == 0 else (email_failed / total_email_attempts * 100)
            
            metrics.append(MonitoringMetric(
                name='email_failure_rate',
                value=failure_rate,
                timestamp=current_time,
                status='ok',
                details={
                    'sent': email_sent,
                    'failed': email_failed,
                    'total': total_email_attempts,
                    'failure_rate_percent': failure_rate
                }
            ))
            
            # Pending email verifications
            pending_verifications = session.query(User).filter(
                User.email_verified == False,
                User.email_verification_token.isnot(None)
            ).count()
            
            metrics.append(MonitoringMetric(
                name='pending_email_verifications',
                value=pending_verifications,
                timestamp=current_time,
                status='ok',
                details={'count': pending_verifications}
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting email metrics: {e}")
        
        return metrics
    
    def _collect_database_metrics(self, session, current_time: datetime) -> List[MonitoringMetric]:
        """Collect database performance metrics"""
        metrics = []
        
        try:
            # Database response time test
            start_time = time.time()
            session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            response_time_ms = (time.time() - start_time) * 1000
            
            metrics.append(MonitoringMetric(
                name='db_response_time',
                value=response_time_ms,
                timestamp=current_time,
                status='ok',
                details={'response_time_ms': response_time_ms}
            ))
            
            # Database size metrics
            db_path = self.config.storage.database_path
            if os.path.exists(db_path):
                db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
                metrics.append(MonitoringMetric(
                    name='database_size_mb',
                    value=db_size_mb,
                    timestamp=current_time,
                    status='ok',
                    details={'size_mb': db_size_mb}
                ))
            
        except Exception as e:
            self.logger.error(f"Error collecting database metrics: {e}")
        
        return metrics
    
    def _collect_session_metrics(self, session, current_time: datetime) -> List[MonitoringMetric]:
        """Collect session metrics"""
        metrics = []
        
        try:
            # Active sessions count
            active_sessions = session.query(UserSession).filter(
                UserSession.is_active == True
            ).count()
            
            metrics.append(MonitoringMetric(
                name='active_sessions',
                value=active_sessions,
                timestamp=current_time,
                status='ok',
                details={'count': active_sessions}
            ))
            
            # Session creation rate (last hour)
            hour_ago = current_time - timedelta(hours=1)
            new_sessions = session.query(UserSession).filter(
                UserSession.created_at > hour_ago
            ).count()
            
            metrics.append(MonitoringMetric(
                name='session_creation_rate',
                value=new_sessions,
                timestamp=current_time,
                status='ok',
                details={'time_window': '1_hour', 'count': new_sessions}
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting session metrics: {e}")
        
        return metrics
    
    def collect_system_metrics(self) -> List[MonitoringMetric]:
        """
        Collect system resource metrics.
        
        Returns:
            List of system monitoring metrics
        """
        metrics = []
        current_time = datetime.utcnow()
        
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.append(MonitoringMetric(
                name='memory_usage_percent',
                value=memory.percent,
                timestamp=current_time,
                status='ok',
                details={
                    'used_mb': memory.used / (1024 * 1024),
                    'total_mb': memory.total / (1024 * 1024),
                    'percent': memory.percent
                }
            ))
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(MonitoringMetric(
                name='cpu_usage_percent',
                value=cpu_percent,
                timestamp=current_time,
                status='ok',
                details={'percent': cpu_percent}
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            metrics.append(MonitoringMetric(
                name='disk_usage_percent',
                value=disk.percent,
                timestamp=current_time,
                status='ok',
                details={
                    'used_gb': disk.used / (1024 * 1024 * 1024),
                    'total_gb': disk.total / (1024 * 1024 * 1024),
                    'percent': disk.percent
                }
            ))
            
        except ImportError:
            self.logger.warning("psutil not available for system metrics")
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
        
        return metrics
    
    def evaluate_alerts(self, metrics: List[MonitoringMetric]) -> List[Alert]:
        """
        Evaluate metrics against alert thresholds.
        
        Args:
            metrics: List of monitoring metrics
        
        Returns:
            List of alerts to be sent
        """
        alerts = []
        current_time = datetime.utcnow()
        
        for metric in metrics:
            # Find matching threshold configuration
            threshold = next(
                (t for t in self.alert_thresholds if t.metric_name == metric.name),
                None
            )
            
            if not threshold or not threshold.enabled:
                continue
            
            # Determine alert severity
            severity = None
            if metric.value >= threshold.critical_threshold:
                severity = 'critical'
            elif metric.value >= threshold.warning_threshold:
                severity = 'warning'
            
            if severity:
                alert_id = f"{metric.name}_{severity}_{int(current_time.timestamp())}"
                
                # Check for duplicate alerts (within last hour)
                if not self._is_duplicate_alert(metric.name, severity):
                    alert = Alert(
                        alert_id=alert_id,
                        severity=severity,
                        metric_name=metric.name,
                        message=self._generate_alert_message(metric, threshold, severity),
                        timestamp=current_time,
                        details={
                            'metric_value': metric.value,
                            'threshold': threshold.critical_threshold if severity == 'critical' else threshold.warning_threshold,
                            'metric_details': metric.details
                        }
                    )
                    alerts.append(alert)
                    self.alert_history.append(alert)
        
        return alerts
    
    def _is_duplicate_alert(self, metric_name: str, severity: str) -> bool:
        """Check if alert is duplicate within last hour"""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        return any(
            alert.metric_name == metric_name and
            alert.severity == severity and
            alert.timestamp > hour_ago and
            not alert.resolved
            for alert in self.alert_history
        )
    
    def _generate_alert_message(self, metric: MonitoringMetric, threshold: AlertThreshold, severity: str) -> str:
        """Generate human-readable alert message"""
        threshold_value = threshold.critical_threshold if severity == 'critical' else threshold.warning_threshold
        
        messages = {
            'registration_rate': f"High user registration rate: {metric.value} registrations in {threshold.time_window_minutes} minutes (threshold: {threshold_value})",
            'failed_login_rate': f"High failed login rate: {metric.value} failed attempts in {threshold.time_window_minutes} minutes (threshold: {threshold_value})",
            'account_lockout_rate': f"High account lockout rate: {metric.value} lockouts in {threshold.time_window_minutes} minutes (threshold: {threshold_value})",
            'email_failure_rate': f"High email failure rate: {metric.value}% failures (threshold: {threshold_value}%)",
            'db_response_time': f"Slow database response: {metric.value}ms (threshold: {threshold_value}ms)",
            'memory_usage_percent': f"High memory usage: {metric.value}% (threshold: {threshold_value}%)",
            'active_sessions': f"High concurrent sessions: {metric.value} active sessions (threshold: {threshold_value})"
        }
        
        return messages.get(
            metric.name,
            f"{severity.upper()}: {metric.name} = {metric.value} (threshold: {threshold_value})"
        )
    
    def send_alerts(self, alerts: List[Alert]) -> None:
        """
        Send alerts via email.
        
        Args:
            alerts: List of alerts to send
        """
        if not alerts or not self.smtp_config['server']:
            return
        
        try:
            # Group alerts by severity
            critical_alerts = [a for a in alerts if a.severity == 'critical']
            warning_alerts = [a for a in alerts if a.severity == 'warning']
            
            if critical_alerts:
                self._send_alert_email(critical_alerts, 'CRITICAL')
            
            if warning_alerts:
                self._send_alert_email(warning_alerts, 'WARNING')
            
        except Exception as e:
            self.logger.error(f"Error sending alerts: {e}")
    
    def _send_alert_email(self, alerts: List[Alert], severity: str) -> None:
        """Send alert email for specific severity level"""
        if not self.smtp_config['to_addresses'] or not self.smtp_config['to_addresses'][0]:
            self.logger.warning("No alert email addresses configured")
            return
        
        try:
            # Create email message
            msg = MimeMultipart()
            msg['From'] = self.smtp_config['from_address']
            msg['To'] = ', '.join(self.smtp_config['to_addresses'])
            msg['Subject'] = f"Vedfolnir User Management Alert - {severity}"
            
            # Create email body
            body = self._create_alert_email_body(alerts, severity)
            msg.attach(MimeText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                if self.smtp_config['use_tls']:
                    server.starttls()
                
                if self.smtp_config['username'] and self.smtp_config['password']:
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                
                server.send_message(msg)
            
            self.logger.info(f"Sent {severity} alert email with {len(alerts)} alerts")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
    
    def _create_alert_email_body(self, alerts: List[Alert], severity: str) -> str:
        """Create HTML email body for alerts"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {'#d32f2f' if severity == 'CRITICAL' else '#f57c00'}; color: white; padding: 10px; }}
                .alert {{ margin: 10px 0; padding: 10px; border-left: 4px solid {'#d32f2f' if severity == 'CRITICAL' else '#f57c00'}; background-color: #f5f5f5; }}
                .details {{ margin-top: 10px; font-size: 0.9em; color: #666; }}
                .timestamp {{ font-size: 0.8em; color: #999; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Vedfolnir User Management - {severity} Alerts</h2>
                <p>Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            </div>
        """
        
        for alert in alerts:
            html += f"""
            <div class="alert">
                <h3>{alert.message}</h3>
                <div class="timestamp">Alert Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</div>
                <div class="details">
                    <strong>Metric:</strong> {alert.metric_name}<br>
                    <strong>Value:</strong> {alert.details.get('metric_value', 'N/A')}<br>
                    <strong>Threshold:</strong> {alert.details.get('threshold', 'N/A')}<br>
                    <strong>Details:</strong> {json.dumps(alert.details.get('metric_details', {}), indent=2)}
                </div>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def generate_monitoring_report(self, metrics: List[MonitoringMetric]) -> Dict[str, Any]:
        """
        Generate comprehensive monitoring report.
        
        Args:
            metrics: List of monitoring metrics
        
        Returns:
            Dictionary containing monitoring report
        """
        current_time = datetime.utcnow()
        
        # Group metrics by category
        user_metrics = [m for m in metrics if m.name.startswith(('registration', 'total_users', 'email_verification'))]
        auth_metrics = [m for m in metrics if m.name.startswith(('login', 'failed_login'))]
        security_metrics = [m for m in metrics if m.name.startswith(('account_lockout', 'locked_accounts', 'password_reset'))]
        email_metrics = [m for m in metrics if m.name.startswith(('email_', 'pending_email'))]
        system_metrics = [m for m in metrics if m.name.startswith(('db_', 'memory_', 'cpu_', 'disk_'))]
        session_metrics = [m for m in metrics if m.name.startswith('session') or m.name == 'active_sessions']
        
        report = {
            'report_timestamp': current_time.isoformat(),
            'summary': {
                'total_metrics': len(metrics),
                'healthy_metrics': len([m for m in metrics if m.status == 'ok']),
                'warning_metrics': len([m for m in metrics if m.status == 'warning']),
                'critical_metrics': len([m for m in metrics if m.status == 'critical'])
            },
            'categories': {
                'user_management': self._summarize_metrics(user_metrics),
                'authentication': self._summarize_metrics(auth_metrics),
                'security': self._summarize_metrics(security_metrics),
                'email_system': self._summarize_metrics(email_metrics),
                'system_performance': self._summarize_metrics(system_metrics),
                'session_management': self._summarize_metrics(session_metrics)
            },
            'detailed_metrics': [asdict(m) for m in metrics]
        }
        
        return report
    
    def _summarize_metrics(self, metrics: List[MonitoringMetric]) -> Dict[str, Any]:
        """Summarize metrics for a category"""
        if not metrics:
            return {'count': 0, 'status': 'no_data'}
        
        return {
            'count': len(metrics),
            'status': 'critical' if any(m.status == 'critical' for m in metrics) else
                     'warning' if any(m.status == 'warning' for m in metrics) else 'ok',
            'metrics': {m.name: m.value for m in metrics}
        }
    
    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """
        Run complete monitoring cycle.
        
        Returns:
            Dictionary containing monitoring results
        """
        self.logger.info("Starting user management monitoring cycle")
        
        try:
            # Collect all metrics
            user_metrics = self.collect_user_metrics()
            system_metrics = self.collect_system_metrics()
            all_metrics = user_metrics + system_metrics
            
            # Store metrics in history
            self.metrics_history.extend(all_metrics)
            
            # Keep only last 24 hours of metrics
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_time]
            
            # Evaluate alerts
            alerts = self.evaluate_alerts(all_metrics)
            
            # Send alerts
            if alerts:
                self.send_alerts(alerts)
            
            # Generate report
            report = self.generate_monitoring_report(all_metrics)
            report['alerts_generated'] = len(alerts)
            report['alerts'] = [asdict(a) for a in alerts]
            
            self.logger.info(f"Monitoring cycle completed: {len(all_metrics)} metrics, {len(alerts)} alerts")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


def main():
    """Main monitoring script entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='User Management Monitoring')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--output', help='Output file for monitoring report')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize configuration
        config = Config()
        
        # Initialize monitoring
        monitor = UserManagementMonitor(config)
        
        if args.continuous:
            # Run continuous monitoring
            print(f"Starting continuous monitoring with {args.interval}s interval...")
            while True:
                try:
                    report = monitor.run_monitoring_cycle()
                    
                    if args.output:
                        with open(args.output, 'w') as f:
                            json.dump(report, f, indent=2, default=str)
                    
                    print(f"Monitoring cycle completed at {datetime.utcnow()}")
                    time.sleep(args.interval)
                    
                except KeyboardInterrupt:
                    print("Monitoring stopped by user")
                    break
                except Exception as e:
                    print(f"Error in monitoring cycle: {e}")
                    time.sleep(args.interval)
        else:
            # Run single monitoring cycle
            report = monitor.run_monitoring_cycle()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"Monitoring report saved to {args.output}")
            else:
                print(json.dumps(report, indent=2, default=str))
        
        return 0
        
    except Exception as e:
        print(f"Monitoring error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())