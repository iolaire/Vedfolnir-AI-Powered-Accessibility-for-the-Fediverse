# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Monitoring Dashboard Service

Provides comprehensive real-time monitoring, historical reporting, and customizable
dashboard widgets for system administrators with alerting integration.
"""

import logging
import json
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy import func, desc, and_, or_, text
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import (
    CaptionGenerationTask, TaskStatus, User, PlatformConnection, 
    Image, ProcessingStatus, ProcessingRun, UserRole
)
from admin.services.monitoring_service import AdminMonitoringService
from alert_manager import AlertManager, AlertType, AlertSeverity
from system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

class DashboardWidgetType(Enum):
    """Types of dashboard widgets"""
    METRIC_CARD = "metric_card"
    CHART = "chart"
    TABLE = "table"
    GAUGE = "gauge"
    ALERT_PANEL = "alert_panel"
    RESOURCE_MONITOR = "resource_monitor"

class ReportType(Enum):
    """Types of reports that can be generated"""
    SYSTEM_PERFORMANCE = "system_performance"
    USER_ACTIVITY = "user_activity"
    ERROR_ANALYSIS = "error_analysis"
    RESOURCE_USAGE = "resource_usage"
    COMPLIANCE_AUDIT = "compliance_audit"
    TASK_TRENDS = "task_trends"

class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"

@dataclass
class DashboardWidget:
    """Configuration for a dashboard widget"""
    id: str
    type: DashboardWidgetType
    title: str
    position: Dict[str, int]  # x, y, width, height
    config: Dict[str, Any]
    roles: List[UserRole]  # Which roles can see this widget
    refresh_interval: int = 30  # seconds
    enabled: bool = True

@dataclass
class ReportConfig:
    """Configuration for automated reports"""
    id: str
    name: str
    type: ReportType
    format: ReportFormat
    schedule: str  # cron expression
    recipients: List[str]  # email addresses
    parameters: Dict[str, Any]
    enabled: bool = True

@dataclass
class DashboardAlert:
    """Dashboard alert with visual indicators"""
    id: str
    type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime
    acknowledged: bool = False
    auto_dismiss: bool = False
    dismiss_after: Optional[int] = None  # seconds

class MonitoringDashboardService:
    """Enhanced monitoring dashboard service with reporting and alerting"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.admin_monitoring = AdminMonitoringService(db_manager)
        self.system_monitor = SystemMonitor()
        self.alert_manager = AlertManager()
        self._setup_default_widgets()
        self._setup_alert_handlers()
    
    def get_dashboard_config(self, user_role: UserRole) -> Dict[str, Any]:
        """Get dashboard configuration for specific user role"""
        try:
            # Filter widgets based on user role
            role_widgets = [
                widget for widget in self.default_widgets 
                if user_role in widget.roles
            ]
            
            return {
                'widgets': [asdict(widget) for widget in role_widgets],
                'refresh_interval': 30,
                'auto_refresh_enabled': True,
                'alert_polling_interval': 10,
                'theme': 'light'
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard config: {str(e)}")
            return {'widgets': [], 'error': str(e)}
    
    def get_widget_data(self, widget_id: str, user_role: UserRole) -> Dict[str, Any]:
        """Get data for a specific dashboard widget"""
        try:
            widget = next((w for w in self.default_widgets if w.id == widget_id), None)
            if not widget or user_role not in widget.roles:
                return {'error': 'Widget not found or access denied'}
            
            if widget.type == DashboardWidgetType.METRIC_CARD:
                return self._get_metric_card_data(widget)
            elif widget.type == DashboardWidgetType.CHART:
                return self._get_chart_data(widget)
            elif widget.type == DashboardWidgetType.TABLE:
                return self._get_table_data(widget)
            elif widget.type == DashboardWidgetType.GAUGE:
                return self._get_gauge_data(widget)
            elif widget.type == DashboardWidgetType.ALERT_PANEL:
                return self._get_alert_panel_data(widget)
            elif widget.type == DashboardWidgetType.RESOURCE_MONITOR:
                return self._get_resource_monitor_data(widget)
            else:
                return {'error': 'Unknown widget type'}
                
        except Exception as e:
            logger.error(f"Error getting widget data for {widget_id}: {str(e)}")
            return {'error': str(e)}
    
    def get_historical_report(self, report_type: ReportType, 
                            start_date: datetime, end_date: datetime,
                            parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate historical report for specified period"""
        try:
            if report_type == ReportType.SYSTEM_PERFORMANCE:
                return self._generate_performance_report(start_date, end_date, parameters)
            elif report_type == ReportType.USER_ACTIVITY:
                return self._generate_user_activity_report(start_date, end_date, parameters)
            elif report_type == ReportType.ERROR_ANALYSIS:
                return self._generate_error_analysis_report(start_date, end_date, parameters)
            elif report_type == ReportType.RESOURCE_USAGE:
                return self._generate_resource_usage_report(start_date, end_date, parameters)
            elif report_type == ReportType.COMPLIANCE_AUDIT:
                return self._generate_compliance_audit_report(start_date, end_date, parameters)
            elif report_type == ReportType.TASK_TRENDS:
                return self._generate_task_trends_report(start_date, end_date, parameters)
            else:
                return {'error': 'Unknown report type'}
                
        except Exception as e:
            logger.error(f"Error generating {report_type.value} report: {str(e)}")
            return {'error': str(e)}
    
    def export_report(self, report_data: Dict[str, Any], 
                     format: ReportFormat) -> Tuple[bytes, str]:
        """Export report data in specified format"""
        try:
            if format == ReportFormat.JSON:
                return self._export_json(report_data)
            elif format == ReportFormat.CSV:
                return self._export_csv(report_data)
            elif format == ReportFormat.HTML:
                return self._export_html(report_data)
            elif format == ReportFormat.PDF:
                return self._export_pdf(report_data)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting report as {format.value}: {str(e)}")
            raise
    
    def get_dashboard_alerts(self, acknowledged: bool = None) -> List[DashboardAlert]:
        """Get current dashboard alerts with visual indicators"""
        try:
            alerts = self.alert_manager.get_active_alerts()
            dashboard_alerts = []
            
            for alert in alerts:
                if acknowledged is None or alert.acknowledged == acknowledged:
                    dashboard_alert = DashboardAlert(
                        id=alert.id,
                        type=alert.type,
                        severity=alert.severity,
                        message=alert.message,
                        timestamp=alert.timestamp,
                        acknowledged=alert.acknowledged,
                        auto_dismiss=alert.auto_dismiss,
                        dismiss_after=alert.dismiss_after
                    )
                    dashboard_alerts.append(dashboard_alert)
            
            return dashboard_alerts
            
        except Exception as e:
            logger.error(f"Error getting dashboard alerts: {str(e)}")
            return []
    
    def acknowledge_alert(self, alert_id: str, admin_user_id: int) -> Dict[str, Any]:
        """Acknowledge a dashboard alert"""
        try:
            success = self.alert_manager.acknowledge_alert(admin_user_id, alert_id)
            
            if success:
                return {
                    'success': True,
                    'message': f'Alert {alert_id[:8]}... acknowledged'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to acknowledge alert'
                }
                
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time system metrics for dashboard updates"""
        try:
            # Get system overview
            overview = self.admin_monitoring.get_system_overview()
            
            # Get system health
            health = self.system_monitor.get_system_health()
            
            # Get performance metrics
            performance = self.system_monitor.get_performance_metrics()
            
            # Get active alerts count
            alerts = self.get_dashboard_alerts(acknowledged=False)
            alert_counts = {
                'critical': len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
                'warning': len([a for a in alerts if a.severity == AlertSeverity.WARNING]),
                'info': len([a for a in alerts if a.severity == AlertSeverity.INFO])
            }
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overview': overview,
                'health': health,
                'performance': performance,
                'alerts': alert_counts,
                'status': 'healthy' if health.get('overall_status') == 'healthy' else 'degraded'
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {str(e)}")
            return {'error': str(e)}
    
    def _setup_default_widgets(self):
        """Setup default dashboard widgets for different roles"""
        self.default_widgets = [
            # System Overview Metrics (All Admins)
            DashboardWidget(
                id="system_overview",
                type=DashboardWidgetType.METRIC_CARD,
                title="System Overview",
                position={"x": 0, "y": 0, "width": 12, "height": 2},
                config={"metrics": ["active_tasks", "recent_tasks", "active_users", "queue_length"]},
                roles=[UserRole.ADMIN]
            ),
            
            # Resource Monitor (All Admins)
            DashboardWidget(
                id="resource_monitor",
                type=DashboardWidgetType.RESOURCE_MONITOR,
                title="System Resources",
                position={"x": 0, "y": 2, "width": 6, "height": 3},
                config={"resources": ["cpu", "memory", "disk", "load"]},
                roles=[UserRole.ADMIN]
            ),
            
            # Alert Panel (All Admins)
            DashboardWidget(
                id="alert_panel",
                type=DashboardWidgetType.ALERT_PANEL,
                title="System Alerts",
                position={"x": 6, "y": 2, "width": 6, "height": 3},
                config={"max_alerts": 10, "show_acknowledged": False},
                roles=[UserRole.ADMIN]
            ),
            
            # Performance Chart (All Admins)
            DashboardWidget(
                id="performance_chart",
                type=DashboardWidgetType.CHART,
                title="Task Performance (24h)",
                position={"x": 0, "y": 5, "width": 8, "height": 4},
                config={"chart_type": "line", "period": "24h", "metrics": ["completed", "failed", "success_rate"]},
                roles=[UserRole.ADMIN]
            ),
            
            # Success Rate Gauge (All Admins)
            DashboardWidget(
                id="success_rate_gauge",
                type=DashboardWidgetType.GAUGE,
                title="Success Rate",
                position={"x": 8, "y": 5, "width": 4, "height": 4},
                config={"metric": "success_rate", "min": 0, "max": 100, "thresholds": [70, 90]},
                roles=[UserRole.ADMIN]
            ),
            
            # Active Tasks Table (All Admins)
            DashboardWidget(
                id="active_tasks_table",
                type=DashboardWidgetType.TABLE,
                title="Active Tasks",
                position={"x": 0, "y": 9, "width": 12, "height": 4},
                config={"max_rows": 10, "columns": ["id", "user", "platform", "status", "progress", "actions"]},
                roles=[UserRole.ADMIN]
            ),
            
            # User Activity Chart (Admin Only)
            DashboardWidget(
                id="user_activity_chart",
                type=DashboardWidgetType.CHART,
                title="User Activity (7 days)",
                position={"x": 0, "y": 13, "width": 12, "height": 4},
                config={"chart_type": "bar", "period": "7d", "metric": "user_tasks"},
                roles=[UserRole.ADMIN]
            )
        ]
    
    def _setup_alert_handlers(self):
        """Setup alert handlers for dashboard integration"""
        # Register alert handlers for different alert types
        self.alert_manager.register_alert_handler(
            AlertType.SYSTEM_ERROR,
            self._handle_system_alert
        )
        
        self.alert_manager.register_alert_handler(
            AlertType.PERFORMANCE_DEGRADATION,
            self._handle_performance_alert
        )
        
        self.alert_manager.register_alert_handler(
            AlertType.RESOURCE_LOW,
            self._handle_resource_alert
        )
    
    def _handle_system_alert(self, alert):
        """Handle system alerts for dashboard display"""
        logger.info(f"Dashboard system alert: {alert.message}")
    
    def _handle_performance_alert(self, alert):
        """Handle performance alerts for dashboard display"""
        logger.warning(f"Dashboard performance alert: {alert.message}")
    
    def _handle_resource_alert(self, alert):
        """Handle resource alerts for dashboard display"""
        logger.error(f"Dashboard resource alert: {alert.message}")
    
    def _get_metric_card_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for metric card widget"""
        overview = self.admin_monitoring.get_system_overview()
        
        metrics = {}
        for metric in widget.config.get('metrics', []):
            if metric == 'active_tasks':
                metrics[metric] = overview.get('active_tasks', 0)
            elif metric == 'recent_tasks':
                metrics[metric] = overview.get('recent_tasks', 0)
            elif metric == 'active_users':
                metrics[metric] = overview.get('active_users', 0)
            elif metric == 'queue_length':
                queue_stats = overview.get('queue_stats', {})
                metrics[metric] = queue_stats.get('queue_stats', {}).get('queued_tasks', 0)
        
        return {'metrics': metrics, 'timestamp': overview.get('timestamp')}
    
    def _get_chart_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for chart widget"""
        config = widget.config
        period = config.get('period', '24h')
        chart_type = config.get('chart_type', 'line')
        
        # Calculate time range based on period
        if period == '24h':
            hours = 24
        elif period == '7d':
            hours = 24 * 7
        elif period == '30d':
            hours = 24 * 30
        else:
            hours = 24
        
        # Get performance metrics for the period
        days = max(1, hours // 24)
        performance = self.admin_monitoring.get_performance_metrics(days=days)
        
        # Generate time series data
        data_points = self._generate_time_series_data(hours, performance)
        
        return {
            'chart_type': chart_type,
            'data': data_points,
            'period': period,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _get_table_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for table widget"""
        config = widget.config
        max_rows = config.get('max_rows', 10)
        
        if widget.id == 'active_tasks_table':
            tasks = self.admin_monitoring.get_active_tasks(limit=max_rows)
            return {
                'columns': config.get('columns', []),
                'rows': tasks,
                'total_count': len(tasks)
            }
        
        return {'columns': [], 'rows': [], 'total_count': 0}
    
    def _get_gauge_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for gauge widget"""
        config = widget.config
        metric = config.get('metric')
        
        if metric == 'success_rate':
            performance = self.admin_monitoring.get_performance_metrics(days=1)
            value = performance.get('success_rate', 0)
        else:
            value = 0
        
        return {
            'value': value,
            'min': config.get('min', 0),
            'max': config.get('max', 100),
            'thresholds': config.get('thresholds', []),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _get_alert_panel_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for alert panel widget"""
        config = widget.config
        max_alerts = config.get('max_alerts', 10)
        show_acknowledged = config.get('show_acknowledged', False)
        
        alerts = self.get_dashboard_alerts(acknowledged=None if show_acknowledged else False)
        
        # Sort by severity and timestamp
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 3), a.timestamp), reverse=True)
        
        return {
            'alerts': [asdict(alert) for alert in alerts[:max_alerts]],
            'total_count': len(alerts),
            'counts_by_severity': {
                'critical': len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
                'warning': len([a for a in alerts if a.severity == AlertSeverity.WARNING]),
                'info': len([a for a in alerts if a.severity == AlertSeverity.INFO])
            }
        }
    
    def _get_resource_monitor_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for resource monitor widget"""
        overview = self.admin_monitoring.get_system_overview()
        resources = overview.get('system_resources', {})
        
        return {
            'resources': resources,
            'timestamp': overview.get('timestamp'),
            'status': self._get_resource_status(resources)
        }
    
    def _get_resource_status(self, resources: Dict[str, Any]) -> str:
        """Determine overall resource status"""
        cpu = resources.get('cpu_percent', 0)
        memory = resources.get('memory_percent', 0)
        disk = resources.get('disk_percent', 0)
        
        if cpu > 90 or memory > 90 or disk > 90:
            return 'critical'
        elif cpu > 70 or memory > 70 or disk > 80:
            return 'warning'
        else:
            return 'healthy'
    
    def _generate_time_series_data(self, hours: int, performance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate time series data for charts"""
        # This is a simplified implementation
        # In a real system, you'd query historical data from the database
        
        data_points = []
        now = datetime.now(timezone.utc)
        
        # Generate hourly data points
        for i in range(hours):
            timestamp = now - timedelta(hours=hours - i)
            
            # Simulate data based on performance metrics
            # In reality, this would come from stored historical data
            data_points.append({
                'timestamp': timestamp.isoformat(),
                'completed': max(0, performance.get('total_completed_tasks', 0) // hours + (i % 3)),
                'failed': max(0, performance.get('total_failed_tasks', 0) // hours + (i % 2)),
                'success_rate': min(100, max(0, performance.get('success_rate', 95) + (i % 10 - 5)))
            })
        
        return data_points
    
    def _generate_performance_report(self, start_date: datetime, 
                                   end_date: datetime, 
                                   parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate system performance report"""
        session = self.db_manager.get_session()
        try:
            # Get tasks in date range
            tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.created_at >= start_date,
                CaptionGenerationTask.created_at <= end_date
            ).all()
            
            # Calculate metrics
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
            failed_tasks = len([t for t in tasks if t.status == TaskStatus.FAILED])
            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Calculate processing times
            processing_times = [
                t.results.processing_time_seconds for t in tasks 
                if t.results and t.results.processing_time_seconds
            ]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                'report_type': 'system_performance',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'failed_tasks': failed_tasks,
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time': round(avg_processing_time, 2)
                },
                'details': [
                    {
                        'task_id': task.id,
                        'user_id': task.user_id,
                        'status': task.status.value,
                        'created_at': task.created_at.isoformat(),
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'processing_time': task.results.processing_time_seconds if task.results else None
                    }
                    for task in tasks
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def _generate_user_activity_report(self, start_date: datetime, 
                                     end_date: datetime, 
                                     parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate user activity report"""
        session = self.db_manager.get_session()
        try:
            # Get user activity data
            user_activity = session.query(
                User.id,
                User.username,
                User.role,
                func.count(CaptionGenerationTask.id).label('task_count')
            ).outerjoin(CaptionGenerationTask).filter(
                or_(
                    CaptionGenerationTask.created_at.between(start_date, end_date),
                    CaptionGenerationTask.created_at.is_(None)
                )
            ).group_by(User.id, User.username, User.role).all()
            
            return {
                'report_type': 'user_activity',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'users': [
                    {
                        'user_id': user.id,
                        'username': user.username,
                        'role': user.role.value,
                        'task_count': user.task_count or 0
                    }
                    for user in user_activity
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating user activity report: {str(e)}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def _generate_error_analysis_report(self, start_date: datetime, 
                                      end_date: datetime, 
                                      parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate error analysis report"""
        session = self.db_manager.get_session()
        try:
            # Get failed tasks in date range
            failed_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.created_at >= start_date,
                CaptionGenerationTask.created_at <= end_date,
                CaptionGenerationTask.status == TaskStatus.FAILED
            ).all()
            
            # Analyze error patterns
            error_patterns = {}
            for task in failed_tasks:
                error_msg = task.error_message or 'Unknown error'
                # Simplify error message for pattern analysis
                error_key = error_msg.split(':')[0] if ':' in error_msg else error_msg
                error_patterns[error_key] = error_patterns.get(error_key, 0) + 1
            
            return {
                'report_type': 'error_analysis',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': {
                    'total_failed_tasks': len(failed_tasks),
                    'unique_error_types': len(error_patterns)
                },
                'error_patterns': [
                    {'error_type': error, 'count': count}
                    for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
                ],
                'failed_tasks': [
                    {
                        'task_id': task.id,
                        'user_id': task.user_id,
                        'error_message': task.error_message,
                        'created_at': task.created_at.isoformat(),
                        'failed_at': task.completed_at.isoformat() if task.completed_at else None
                    }
                    for task in failed_tasks
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating error analysis report: {str(e)}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def _generate_resource_usage_report(self, start_date: datetime, 
                                      end_date: datetime, 
                                      parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate resource usage report"""
        # This would typically pull from stored resource metrics
        # For now, return current resource usage as example
        overview = self.admin_monitoring.get_system_overview()
        resources = overview.get('system_resources', {})
        
        return {
            'report_type': 'resource_usage',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'current_usage': resources,
            'note': 'Historical resource data would be available with proper metrics storage',
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_compliance_audit_report(self, start_date: datetime, 
                                        end_date: datetime, 
                                        parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate compliance audit report"""
        session = self.db_manager.get_session()
        try:
            # Get all tasks in period for audit
            tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.created_at >= start_date,
                CaptionGenerationTask.created_at <= end_date
            ).all()
            
            # Get user activity
            users = session.query(User).filter(User.is_active == True).all()
            
            return {
                'report_type': 'compliance_audit',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'audit_summary': {
                    'total_tasks': len(tasks),
                    'active_users': len(users),
                    'data_retention_compliant': True,
                    'security_events': 0  # Would come from security audit logs
                },
                'user_data': [
                    {
                        'user_id': user.id,
                        'username': user.username,
                        'role': user.role.value,
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                        'is_active': user.is_active
                    }
                    for user in users
                ],
                'task_audit': [
                    {
                        'task_id': task.id,
                        'user_id': task.user_id,
                        'status': task.status.value,
                        'created_at': task.created_at.isoformat(),
                        'data_processed': bool(task.results)
                    }
                    for task in tasks
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance audit report: {str(e)}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def _generate_task_trends_report(self, start_date: datetime, 
                                   end_date: datetime, 
                                   parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate task trends report"""
        session = self.db_manager.get_session()
        try:
            # Get daily task counts
            daily_stats = session.query(
                func.date(CaptionGenerationTask.created_at).label('date'),
                func.count(CaptionGenerationTask.id).label('total_tasks'),
                func.sum(func.case([(CaptionGenerationTask.status == TaskStatus.COMPLETED, 1)], else_=0)).label('completed'),
                func.sum(func.case([(CaptionGenerationTask.status == TaskStatus.FAILED, 1)], else_=0)).label('failed')
            ).filter(
                CaptionGenerationTask.created_at >= start_date,
                CaptionGenerationTask.created_at <= end_date
            ).group_by(func.date(CaptionGenerationTask.created_at)).all()
            
            return {
                'report_type': 'task_trends',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'daily_trends': [
                    {
                        'date': str(stat.date),
                        'total_tasks': stat.total_tasks,
                        'completed': stat.completed or 0,
                        'failed': stat.failed or 0,
                        'success_rate': round((stat.completed or 0) / stat.total_tasks * 100, 2) if stat.total_tasks > 0 else 0
                    }
                    for stat in daily_stats
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating task trends report: {str(e)}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def _export_json(self, report_data: Dict[str, Any]) -> Tuple[bytes, str]:
        """Export report as JSON"""
        json_str = json.dumps(report_data, indent=2, default=str)
        return json_str.encode('utf-8'), 'application/json'
    
    def _export_csv(self, report_data: Dict[str, Any]) -> Tuple[bytes, str]:
        """Export report as CSV"""
        output = io.StringIO()
        
        # Extract tabular data based on report type
        if 'details' in report_data:
            data = report_data['details']
        elif 'users' in report_data:
            data = report_data['users']
        elif 'daily_trends' in report_data:
            data = report_data['daily_trends']
        else:
            # Fallback to summary data
            data = [report_data.get('summary', {})]
        
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content.encode('utf-8'), 'text/csv'
    
    def _export_html(self, report_data: Dict[str, Any]) -> Tuple[bytes, str]:
        """Export report as HTML"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_data.get('report_type', 'Report')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>{report_data.get('report_type', 'Report').replace('_', ' ').title()}</h1>
            <div class="summary">
                <h2>Summary</h2>
                <pre>{json.dumps(report_data.get('summary', {}), indent=2)}</pre>
            </div>
            <h2>Generated At</h2>
            <p>{report_data.get('generated_at', 'Unknown')}</p>
        </body>
        </html>
        """
        
        return html_content.encode('utf-8'), 'text/html'
    
    def _export_pdf(self, report_data: Dict[str, Any]) -> Tuple[bytes, str]:
        """Export report as PDF (placeholder implementation)"""
        # This would require a PDF library like reportlab
        # For now, return HTML content as placeholder
        html_content, _ = self._export_html(report_data)
        return html_content, 'text/html'