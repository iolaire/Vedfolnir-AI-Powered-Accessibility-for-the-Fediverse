#!/usr/bin/env python3
"""
MySQL Monitoring Dashboard and Analytics for Vedfolnir

This module provides comprehensive MySQL monitoring dashboard and analytics capabilities including:
- Real-time performance metrics visualization
- Historical trend analysis and reporting
- Interactive web dashboard with charts and graphs
- Automated alert dashboard and notification center
- Performance analytics and insights generation
- Custom metric collection and visualization
- Integration with existing monitoring systems
- Export capabilities for reports and data

Integrates with existing MySQL health monitoring, performance optimization, and security systems.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import sys
import threading
from collections import defaultdict, deque
import statistics

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from flask import Flask, render_template, jsonify, request, send_file
    from flask_socketio import SocketIO, emit
    import plotly.graph_objs as go
    import plotly.utils
    import pandas as pd
    import redis
    from config import Config
    from mysql_connection_validator import MySQLConnectionValidator
    from scripts.mysql_performance_optimizer import MySQLPerformanceOptimizer
    from scripts.mysql_performance_monitor import MySQLPerformanceMonitor
    from scripts.mysql_security_hardening import MySQLSecurityHardening
    from scripts.mysql_backup_recovery import MySQLBackupRecovery
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed")
    print("For dashboard: pip install flask flask-socketio plotly pandas")
    sys.exit(1)

logger = logging.getLogger(__name__)

@dataclass
class DashboardMetrics:
    """Container for dashboard metrics."""
    timestamp: datetime
    connection_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    security_metrics: Dict[str, float]
    backup_metrics: Dict[str, float]
    system_metrics: Dict[str, float]
    alert_counts: Dict[str, int]
    health_status: str

@dataclass
class AnalyticsReport:
    """Container for analytics report."""
    report_id: str
    report_type: str
    time_range: Dict[str, datetime]
    metrics_analyzed: List[str]
    insights: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]
    summary_statistics: Dict[str, Any]
    generated_at: datetime

class MySQLMonitoringDashboard:
    """
    Comprehensive MySQL monitoring dashboard and analytics system.
    
    Provides real-time monitoring, historical analysis, and interactive
    web dashboard for MySQL performance and health metrics.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the MySQL Monitoring Dashboard.
        
        Args:
            config: Optional Config instance, will create default if not provided
        """
        self.config = config or Config()
        
        # Initialize monitoring components
        self.validator = MySQLConnectionValidator()
        self.performance_optimizer = MySQLPerformanceOptimizer(config)
        self.performance_monitor = MySQLPerformanceMonitor(config)
        self.security_hardening = MySQLSecurityHardening(config)
        self.backup_recovery = MySQLBackupRecovery(config)
        
        # Flask app for dashboard
        self.app = Flask(__name__, template_folder='../templates', static_folder='../static')
        self.app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'mysql-dashboard-secret')
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Redis for metrics storage
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()
        
        # Dashboard configuration
        self.dashboard_config = {
            'update_interval': int(os.getenv('MYSQL_DASHBOARD_UPDATE_INTERVAL', '30')),  # seconds
            'metrics_retention_hours': int(os.getenv('MYSQL_DASHBOARD_RETENTION_HOURS', '168')),  # 7 days
            'max_chart_points': int(os.getenv('MYSQL_DASHBOARD_MAX_CHART_POINTS', '100')),
            'enable_real_time': os.getenv('MYSQL_DASHBOARD_REAL_TIME', 'true').lower() == 'true'
        }
        
        # Metrics collection
        self.metrics_history: deque = deque(maxlen=1000)
        self.current_metrics: Optional[DashboardMetrics] = None
        self.metrics_collector_running = False
        self.metrics_collector_thread: Optional[threading.Thread] = None
        
        # Analytics
        self.analytics_reports: Dict[str, AnalyticsReport] = {}
        
        # Setup Flask routes
        self._setup_routes()
        self._setup_socketio_events()
        
        logger.info("MySQL Monitoring Dashboard initialized")
    
    def _initialize_redis(self):
        """Initialize Redis connection for metrics storage."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/5')  # Use DB 5 for dashboard
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for dashboard metrics")
        except Exception as e:
            logger.warning(f"Redis not available for dashboard metrics: {e}")
            self.redis_client = None
    
    def _setup_routes(self):
        """Setup Flask routes for the dashboard."""
        
        @self.app.route('/')
        def dashboard_home():
            """Main dashboard page."""
            return render_template('mysql_dashboard.html', 
                                 config=self.dashboard_config,
                                 current_time=datetime.now().isoformat())
        
        @self.app.route('/api/metrics/current')
        def get_current_metrics():
            """Get current metrics."""
            try:
                if self.current_metrics:
                    return jsonify({
                        'success': True,
                        'metrics': asdict(self.current_metrics),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'No current metrics available',
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.app.route('/api/metrics/history')
        def get_metrics_history():
            """Get historical metrics."""
            try:
                hours = request.args.get('hours', 24, type=int)
                metric_type = request.args.get('type', 'all')
                
                history_data = self._get_metrics_history(hours, metric_type)
                
                return jsonify({
                    'success': True,
                    'history': history_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.app.route('/api/charts/<chart_type>')
        def get_chart_data(chart_type):
            """Get chart data for specific chart type."""
            try:
                hours = request.args.get('hours', 24, type=int)
                chart_data = self._generate_chart_data(chart_type, hours)
                
                return jsonify({
                    'success': True,
                    'chart_data': chart_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.app.route('/api/alerts')
        def get_alerts():
            """Get current alerts."""
            try:
                hours = request.args.get('hours', 24, type=int)
                alerts_data = self._get_alerts_data(hours)
                
                return jsonify({
                    'success': True,
                    'alerts': alerts_data,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.app.route('/api/analytics/generate', methods=['POST'])
        def generate_analytics_report():
            """Generate analytics report."""
            try:
                request_data = request.get_json()
                report_type = request_data.get('report_type', 'performance')
                time_range_hours = request_data.get('time_range_hours', 24)
                
                report = self._generate_analytics_report(report_type, time_range_hours)
                
                return jsonify({
                    'success': True,
                    'report': asdict(report),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.app.route('/api/export/<export_type>')
        def export_data(export_type):
            """Export dashboard data."""
            try:
                hours = request.args.get('hours', 24, type=int)
                format_type = request.args.get('format', 'json')
                
                export_result = self._export_data(export_type, hours, format_type)
                
                if export_result['success']:
                    return send_file(
                        export_result['file_path'],
                        as_attachment=True,
                        download_name=export_result['filename']
                    )
                else:
                    return jsonify(export_result)
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
    
    def _setup_socketio_events(self):
        """Setup SocketIO events for real-time updates."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info("Dashboard client connected")
            if self.current_metrics:
                emit('metrics_update', asdict(self.current_metrics))
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info("Dashboard client disconnected")
        
        @self.socketio.on('request_metrics')
        def handle_metrics_request():
            """Handle metrics request from client."""
            if self.current_metrics:
                emit('metrics_update', asdict(self.current_metrics))
    
    def start_metrics_collection(self) -> Dict[str, Any]:
        """Start metrics collection for the dashboard."""
        try:
            if self.metrics_collector_running:
                return {
                    'success': False,
                    'message': 'Metrics collection is already running',
                    'timestamp': datetime.now().isoformat()
                }
            
            self.metrics_collector_running = True
            self.metrics_collector_thread = threading.Thread(
                target=self._metrics_collection_loop,
                daemon=True
            )
            self.metrics_collector_thread.start()
            
            logger.info(f"Dashboard metrics collection started (interval: {self.dashboard_config['update_interval']}s)")
            return {
                'success': True,
                'message': f'Metrics collection started with {self.dashboard_config["update_interval"]}s interval',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start metrics collection: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def stop_metrics_collection(self) -> Dict[str, Any]:
        """Stop metrics collection."""
        try:
            if not self.metrics_collector_running:
                return {
                    'success': False,
                    'message': 'Metrics collection is not running',
                    'timestamp': datetime.now().isoformat()
                }
            
            self.metrics_collector_running = False
            if self.metrics_collector_thread and self.metrics_collector_thread.is_alive():
                self.metrics_collector_thread.join(timeout=10)
            
            logger.info("Dashboard metrics collection stopped")
            return {
                'success': True,
                'message': 'Metrics collection stopped',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop metrics collection: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _metrics_collection_loop(self):
        """Main metrics collection loop."""
        while self.metrics_collector_running:
            try:
                # Collect comprehensive metrics
                metrics = self._collect_dashboard_metrics()
                
                # Update current metrics
                self.current_metrics = metrics
                self.metrics_history.append(metrics)
                
                # Store in Redis if available
                if self.redis_client:
                    self._store_metrics_in_redis(metrics)
                
                # Emit real-time update if enabled
                if self.dashboard_config['enable_real_time']:
                    self.socketio.emit('metrics_update', asdict(metrics))
                
                # Sleep until next collection
                time.sleep(self.dashboard_config['update_interval'])
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.dashboard_config['update_interval'])
    
    def _collect_dashboard_metrics(self) -> DashboardMetrics:
        """Collect comprehensive metrics for the dashboard."""
        try:
            timestamp = datetime.now()
            
            # Connection metrics
            connection_metrics = {}
            try:
                health_result = self.validator.perform_health_check()
                if health_result.metrics:
                    connection_metrics = {
                        'connection_usage_percent': health_result.metrics.get('connection_usage_percent', 0),
                        'active_connections': health_result.metrics.get('active_connections', 0),
                        'response_time_ms': health_result.metrics.get('response_time_ms', 0)
                    }
            except Exception as e:
                logger.debug(f"Failed to collect connection metrics: {e}")
            
            # Performance metrics
            performance_metrics = {}
            try:
                if self.performance_optimizer.performance_history:
                    latest_perf = self.performance_optimizer.performance_history[-1]
                    performance_metrics = {
                        'avg_query_time_ms': latest_perf.avg_query_time_ms,
                        'slow_query_ratio_percent': latest_perf.slow_query_ratio_percent,
                        'innodb_buffer_pool_hit_ratio': latest_perf.innodb_buffer_pool_hit_ratio,
                        'disk_io_ops_per_sec': latest_perf.disk_io_ops_per_sec
                    }
            except Exception as e:
                logger.debug(f"Failed to collect performance metrics: {e}")
            
            # Security metrics
            security_metrics = {}
            try:
                security_status = self.security_hardening.get_security_status_summary()
                if security_status.get('success'):
                    summary = security_status['summary']
                    security_metrics = {
                        'overall_security_score': summary.get('overall_security_score', 0),
                        'critical_issues_count': summary.get('critical_issues_count', 0),
                        'ssl_enabled': 1 if summary.get('ssl_enabled') else 0
                    }
            except Exception as e:
                logger.debug(f"Failed to collect security metrics: {e}")
            
            # Backup metrics
            backup_metrics = {}
            try:
                backup_status = self.backup_recovery.get_backup_status_summary()
                if backup_status.get('success'):
                    summary = backup_status['summary']
                    backup_metrics = {
                        'total_backups': summary.get('total_backups', 0),
                        'total_size_gb': summary.get('total_size_gb', 0),
                        'scheduler_running': 1 if summary.get('scheduler_status', {}).get('running') else 0
                    }
            except Exception as e:
                logger.debug(f"Failed to collect backup metrics: {e}")
            
            # System metrics (simplified)
            system_metrics = {
                'uptime_hours': 0,  # Would implement system uptime collection
                'cpu_usage_percent': 0,  # Would implement CPU monitoring
                'memory_usage_percent': 0,  # Would implement memory monitoring
                'disk_usage_percent': 0  # Would implement disk monitoring
            }
            
            # Alert counts
            alert_counts = {}
            try:
                alerts_data = self.performance_monitor.get_recent_alerts(1)  # Last hour
                if alerts_data.get('success'):
                    alert_counts = alerts_data.get('alert_counts', {})
            except Exception as e:
                logger.debug(f"Failed to collect alert counts: {e}")
            
            # Overall health status
            health_status = 'unknown'
            try:
                health_result = self.validator.perform_health_check()
                health_status = 'healthy' if health_result.healthy else 'unhealthy'
            except Exception as e:
                logger.debug(f"Failed to determine health status: {e}")
            
            return DashboardMetrics(
                timestamp=timestamp,
                connection_metrics=connection_metrics,
                performance_metrics=performance_metrics,
                security_metrics=security_metrics,
                backup_metrics=backup_metrics,
                system_metrics=system_metrics,
                alert_counts=alert_counts,
                health_status=health_status
            )
            
        except Exception as e:
            logger.error(f"Failed to collect dashboard metrics: {e}")
            # Return minimal metrics
            return DashboardMetrics(
                timestamp=datetime.now(),
                connection_metrics={},
                performance_metrics={},
                security_metrics={},
                backup_metrics={},
                system_metrics={},
                alert_counts={},
                health_status='error'
            )
    
    def _store_metrics_in_redis(self, metrics: DashboardMetrics):
        """Store metrics in Redis for persistence."""
        try:
            if not self.redis_client:
                return
            
            # Store current metrics
            current_key = "mysql_dashboard:current_metrics"
            self.redis_client.setex(
                current_key,
                300,  # 5 minutes TTL
                json.dumps(asdict(metrics), default=str)
            )
            
            # Store historical metrics
            history_key = f"mysql_dashboard:history:{int(metrics.timestamp.timestamp())}"
            self.redis_client.setex(
                history_key,
                self.dashboard_config['metrics_retention_hours'] * 3600,  # TTL based on retention
                json.dumps(asdict(metrics), default=str)
            )
            
        except Exception as e:
            logger.debug(f"Failed to store metrics in Redis: {e}")
    
    def _get_metrics_history(self, hours: int, metric_type: str = 'all') -> List[Dict[str, Any]]:
        """Get historical metrics from Redis and memory."""
        try:
            history_data = []
            
            # Get from Redis if available
            if self.redis_client:
                cutoff_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
                pattern = "mysql_dashboard:history:*"
                keys = self.redis_client.keys(pattern)
                
                # Filter keys by timestamp
                recent_keys = [key for key in keys if int(key.split(':')[-1]) >= cutoff_timestamp]
                
                for key in recent_keys:
                    try:
                        metrics_data = self.redis_client.get(key)
                        if metrics_data:
                            metrics_dict = json.loads(metrics_data)
                            if metric_type == 'all' or metric_type in metrics_dict:
                                history_data.append(metrics_dict)
                    except Exception as e:
                        logger.debug(f"Could not parse metrics from {key}: {e}")
            
            # Get from memory
            cutoff_time = datetime.now() - timedelta(hours=hours)
            memory_data = [
                asdict(metrics) for metrics in self.metrics_history
                if metrics.timestamp >= cutoff_time
            ]
            
            # Combine and deduplicate
            all_data = history_data + memory_data
            seen_timestamps = set()
            unique_data = []
            
            for data in all_data:
                timestamp = data.get('timestamp')
                if timestamp and timestamp not in seen_timestamps:
                    seen_timestamps.add(timestamp)
                    unique_data.append(data)
            
            # Sort by timestamp
            unique_data.sort(key=lambda x: x.get('timestamp', ''))
            
            return unique_data
            
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    def _generate_chart_data(self, chart_type: str, hours: int) -> Dict[str, Any]:
        """Generate chart data for specific chart type."""
        try:
            history_data = self._get_metrics_history(hours)
            
            if not history_data:
                return {
                    'chart_type': chart_type,
                    'data': [],
                    'layout': {},
                    'error': 'No data available'
                }
            
            # Extract timestamps
            timestamps = [datetime.fromisoformat(d['timestamp']) for d in history_data]
            
            if chart_type == 'connection_usage':
                values = [d.get('connection_metrics', {}).get('connection_usage_percent', 0) for d in history_data]
                
                trace = go.Scatter(
                    x=timestamps,
                    y=values,
                    mode='lines+markers',
                    name='Connection Usage %',
                    line=dict(color='#1f77b4')
                )
                
                layout = go.Layout(
                    title='MySQL Connection Usage',
                    xaxis=dict(title='Time'),
                    yaxis=dict(title='Usage %', range=[0, 100]),
                    hovermode='x unified'
                )
                
            elif chart_type == 'query_performance':
                avg_times = [d.get('performance_metrics', {}).get('avg_query_time_ms', 0) for d in history_data]
                slow_ratios = [d.get('performance_metrics', {}).get('slow_query_ratio_percent', 0) for d in history_data]
                
                trace1 = go.Scatter(
                    x=timestamps,
                    y=avg_times,
                    mode='lines+markers',
                    name='Avg Query Time (ms)',
                    yaxis='y',
                    line=dict(color='#ff7f0e')
                )
                
                trace2 = go.Scatter(
                    x=timestamps,
                    y=slow_ratios,
                    mode='lines+markers',
                    name='Slow Query Ratio %',
                    yaxis='y2',
                    line=dict(color='#d62728')
                )
                
                layout = go.Layout(
                    title='MySQL Query Performance',
                    xaxis=dict(title='Time'),
                    yaxis=dict(title='Avg Query Time (ms)', side='left'),
                    yaxis2=dict(title='Slow Query Ratio %', side='right', overlaying='y'),
                    hovermode='x unified'
                )
                
                return {
                    'chart_type': chart_type,
                    'data': [trace1, trace2],
                    'layout': layout
                }
                
            elif chart_type == 'security_score':
                scores = [d.get('security_metrics', {}).get('overall_security_score', 0) for d in history_data]
                
                trace = go.Scatter(
                    x=timestamps,
                    y=scores,
                    mode='lines+markers',
                    name='Security Score',
                    line=dict(color='#2ca02c')
                )
                
                layout = go.Layout(
                    title='MySQL Security Score',
                    xaxis=dict(title='Time'),
                    yaxis=dict(title='Score', range=[0, 100]),
                    hovermode='x unified'
                )
                
            elif chart_type == 'backup_status':
                backup_counts = [d.get('backup_metrics', {}).get('total_backups', 0) for d in history_data]
                backup_sizes = [d.get('backup_metrics', {}).get('total_size_gb', 0) for d in history_data]
                
                trace1 = go.Scatter(
                    x=timestamps,
                    y=backup_counts,
                    mode='lines+markers',
                    name='Total Backups',
                    yaxis='y',
                    line=dict(color='#9467bd')
                )
                
                trace2 = go.Scatter(
                    x=timestamps,
                    y=backup_sizes,
                    mode='lines+markers',
                    name='Total Size (GB)',
                    yaxis='y2',
                    line=dict(color='#8c564b')
                )
                
                layout = go.Layout(
                    title='MySQL Backup Status',
                    xaxis=dict(title='Time'),
                    yaxis=dict(title='Backup Count', side='left'),
                    yaxis2=dict(title='Size (GB)', side='right', overlaying='y'),
                    hovermode='x unified'
                )
                
                return {
                    'chart_type': chart_type,
                    'data': [trace1, trace2],
                    'layout': layout
                }
            
            else:
                return {
                    'chart_type': chart_type,
                    'data': [],
                    'layout': {},
                    'error': f'Unknown chart type: {chart_type}'
                }
            
            return {
                'chart_type': chart_type,
                'data': [trace],
                'layout': layout
            }
            
        except Exception as e:
            logger.error(f"Failed to generate chart data for {chart_type}: {e}")
            return {
                'chart_type': chart_type,
                'data': [],
                'layout': {},
                'error': str(e)
            }
    
    def _get_alerts_data(self, hours: int) -> List[Dict[str, Any]]:
        """Get alerts data for the dashboard."""
        try:
            alerts_data = []
            
            # Get alerts from performance monitor
            try:
                perf_alerts = self.performance_monitor.get_recent_alerts(hours)
                if perf_alerts.get('success'):
                    for alert in perf_alerts.get('alerts', []):
                        alert['source'] = 'performance'
                        alerts_data.append(alert)
            except Exception as e:
                logger.debug(f"Failed to get performance alerts: {e}")
            
            # Get security events (treated as alerts)
            try:
                security_events = self.security_hardening._get_recent_security_events(hours)
                for event in security_events:
                    alerts_data.append({
                        'source': 'security',
                        'level': 'info',
                        'title': f"Security Event: {event.get('event_type', 'Unknown')}",
                        'message': json.dumps(event.get('data', {})),
                        'timestamp': event.get('timestamp')
                    })
            except Exception as e:
                logger.debug(f"Failed to get security events: {e}")
            
            # Sort by timestamp
            alerts_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return alerts_data
            
        except Exception as e:
            logger.error(f"Failed to get alerts data: {e}")
            return []
    
    def _generate_analytics_report(self, report_type: str, time_range_hours: int) -> AnalyticsReport:
        """Generate comprehensive analytics report."""
        try:
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{report_type}"
            
            # Get historical data
            history_data = self._get_metrics_history(time_range_hours)
            
            if not history_data:
                return AnalyticsReport(
                    report_id=report_id,
                    report_type=report_type,
                    time_range={'start': datetime.now() - timedelta(hours=time_range_hours), 'end': datetime.now()},
                    metrics_analyzed=[],
                    insights=[],
                    recommendations=[],
                    charts=[],
                    summary_statistics={},
                    generated_at=datetime.now()
                )
            
            # Analyze based on report type
            if report_type == 'performance':
                return self._generate_performance_analytics(report_id, history_data, time_range_hours)
            elif report_type == 'security':
                return self._generate_security_analytics(report_id, history_data, time_range_hours)
            elif report_type == 'backup':
                return self._generate_backup_analytics(report_id, history_data, time_range_hours)
            else:
                return self._generate_comprehensive_analytics(report_id, history_data, time_range_hours)
                
        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            return AnalyticsReport(
                report_id=report_id if 'report_id' in locals() else 'error',
                report_type=report_type,
                time_range={'start': datetime.now() - timedelta(hours=time_range_hours), 'end': datetime.now()},
                metrics_analyzed=[],
                insights=[{'type': 'error', 'message': str(e)}],
                recommendations=[],
                charts=[],
                summary_statistics={},
                generated_at=datetime.now()
            )
    
    def _generate_performance_analytics(self, report_id: str, history_data: List[Dict[str, Any]], 
                                      time_range_hours: int) -> AnalyticsReport:
        """Generate performance-focused analytics report."""
        insights = []
        recommendations = []
        charts = []
        summary_stats = {}
        
        # Extract performance metrics
        query_times = [d.get('performance_metrics', {}).get('avg_query_time_ms', 0) for d in history_data]
        connection_usage = [d.get('connection_metrics', {}).get('connection_usage_percent', 0) for d in history_data]
        slow_query_ratios = [d.get('performance_metrics', {}).get('slow_query_ratio_percent', 0) for d in history_data]
        
        # Calculate statistics
        if query_times:
            avg_query_time = statistics.mean(query_times)
            max_query_time = max(query_times)
            summary_stats['avg_query_time_ms'] = avg_query_time
            summary_stats['max_query_time_ms'] = max_query_time
            
            # Generate insights
            if avg_query_time > 1000:
                insights.append({
                    'type': 'warning',
                    'category': 'performance',
                    'message': f'Average query time is high: {avg_query_time:.1f}ms',
                    'impact': 'high'
                })
                recommendations.append({
                    'priority': 'high',
                    'category': 'query_optimization',
                    'title': 'Optimize slow queries',
                    'description': 'Review and optimize queries taking longer than 1 second'
                })
        
        if connection_usage:
            avg_connection_usage = statistics.mean(connection_usage)
            max_connection_usage = max(connection_usage)
            summary_stats['avg_connection_usage_percent'] = avg_connection_usage
            summary_stats['max_connection_usage_percent'] = max_connection_usage
            
            if max_connection_usage > 80:
                insights.append({
                    'type': 'warning',
                    'category': 'connections',
                    'message': f'Peak connection usage reached {max_connection_usage:.1f}%',
                    'impact': 'medium'
                })
        
        return AnalyticsReport(
            report_id=report_id,
            report_type='performance',
            time_range={'start': datetime.now() - timedelta(hours=time_range_hours), 'end': datetime.now()},
            metrics_analyzed=['query_times', 'connection_usage', 'slow_query_ratios'],
            insights=insights,
            recommendations=recommendations,
            charts=charts,
            summary_statistics=summary_stats,
            generated_at=datetime.now()
        )
    
    def _generate_security_analytics(self, report_id: str, history_data: List[Dict[str, Any]], 
                                   time_range_hours: int) -> AnalyticsReport:
        """Generate security-focused analytics report."""
        insights = []
        recommendations = []
        summary_stats = {}
        
        # Extract security metrics
        security_scores = [d.get('security_metrics', {}).get('overall_security_score', 0) for d in history_data]
        critical_issues = [d.get('security_metrics', {}).get('critical_issues_count', 0) for d in history_data]
        
        if security_scores:
            avg_security_score = statistics.mean(security_scores)
            min_security_score = min(security_scores)
            summary_stats['avg_security_score'] = avg_security_score
            summary_stats['min_security_score'] = min_security_score
            
            if avg_security_score < 75:
                insights.append({
                    'type': 'critical',
                    'category': 'security',
                    'message': f'Average security score is low: {avg_security_score:.1f}/100',
                    'impact': 'critical'
                })
                recommendations.append({
                    'priority': 'critical',
                    'category': 'security_hardening',
                    'title': 'Implement security hardening',
                    'description': 'Run security hardening procedures to improve security score'
                })
        
        return AnalyticsReport(
            report_id=report_id,
            report_type='security',
            time_range={'start': datetime.now() - timedelta(hours=time_range_hours), 'end': datetime.now()},
            metrics_analyzed=['security_scores', 'critical_issues'],
            insights=insights,
            recommendations=recommendations,
            charts=[],
            summary_statistics=summary_stats,
            generated_at=datetime.now()
        )
    
    def _generate_backup_analytics(self, report_id: str, history_data: List[Dict[str, Any]], 
                                 time_range_hours: int) -> AnalyticsReport:
        """Generate backup-focused analytics report."""
        insights = []
        recommendations = []
        summary_stats = {}
        
        # Extract backup metrics
        backup_counts = [d.get('backup_metrics', {}).get('total_backups', 0) for d in history_data]
        backup_sizes = [d.get('backup_metrics', {}).get('total_size_gb', 0) for d in history_data]
        
        if backup_counts:
            latest_backup_count = backup_counts[-1] if backup_counts else 0
            backup_growth = backup_counts[-1] - backup_counts[0] if len(backup_counts) > 1 else 0
            summary_stats['current_backup_count'] = latest_backup_count
            summary_stats['backup_growth'] = backup_growth
            
            if latest_backup_count == 0:
                insights.append({
                    'type': 'critical',
                    'category': 'backup',
                    'message': 'No backups found in the system',
                    'impact': 'critical'
                })
                recommendations.append({
                    'priority': 'critical',
                    'category': 'backup_setup',
                    'title': 'Set up automated backups',
                    'description': 'Configure and enable automated backup jobs'
                })
        
        return AnalyticsReport(
            report_id=report_id,
            report_type='backup',
            time_range={'start': datetime.now() - timedelta(hours=time_range_hours), 'end': datetime.now()},
            metrics_analyzed=['backup_counts', 'backup_sizes'],
            insights=insights,
            recommendations=recommendations,
            charts=[],
            summary_statistics=summary_stats,
            generated_at=datetime.now()
        )
    
    def _generate_comprehensive_analytics(self, report_id: str, history_data: List[Dict[str, Any]], 
                                        time_range_hours: int) -> AnalyticsReport:
        """Generate comprehensive analytics report covering all areas."""
        # Combine insights from all specialized reports
        perf_report = self._generate_performance_analytics(f"{report_id}_perf", history_data, time_range_hours)
        security_report = self._generate_security_analytics(f"{report_id}_sec", history_data, time_range_hours)
        backup_report = self._generate_backup_analytics(f"{report_id}_backup", history_data, time_range_hours)
        
        # Combine all insights and recommendations
        all_insights = perf_report.insights + security_report.insights + backup_report.insights
        all_recommendations = perf_report.recommendations + security_report.recommendations + backup_report.recommendations
        
        # Combine summary statistics
        combined_stats = {}
        combined_stats.update(perf_report.summary_statistics)
        combined_stats.update(security_report.summary_statistics)
        combined_stats.update(backup_report.summary_statistics)
        
        return AnalyticsReport(
            report_id=report_id,
            report_type='comprehensive',
            time_range={'start': datetime.now() - timedelta(hours=time_range_hours), 'end': datetime.now()},
            metrics_analyzed=['performance', 'security', 'backup', 'connections'],
            insights=all_insights,
            recommendations=all_recommendations,
            charts=[],
            summary_statistics=combined_stats,
            generated_at=datetime.now()
        )
    
    def _export_data(self, export_type: str, hours: int, format_type: str) -> Dict[str, Any]:
        """Export dashboard data in various formats."""
        try:
            export_dir = Path('./exports')
            export_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if export_type == 'metrics':
                # Export metrics data
                history_data = self._get_metrics_history(hours)
                
                if format_type == 'json':
                    filename = f'mysql_metrics_{timestamp}.json'
                    file_path = export_dir / filename
                    
                    with open(file_path, 'w') as f:
                        json.dump(history_data, f, indent=2, default=str)
                        
                elif format_type == 'csv':
                    filename = f'mysql_metrics_{timestamp}.csv'
                    file_path = export_dir / filename
                    
                    # Convert to DataFrame and export
                    df = pd.json_normalize(history_data)
                    df.to_csv(file_path, index=False)
                    
                else:
                    return {
                        'success': False,
                        'error': f'Unsupported format: {format_type}'
                    }
                    
            elif export_type == 'alerts':
                # Export alerts data
                alerts_data = self._get_alerts_data(hours)
                
                if format_type == 'json':
                    filename = f'mysql_alerts_{timestamp}.json'
                    file_path = export_dir / filename
                    
                    with open(file_path, 'w') as f:
                        json.dump(alerts_data, f, indent=2, default=str)
                        
                else:
                    return {
                        'success': False,
                        'error': f'Unsupported format: {format_type}'
                    }
                    
            else:
                return {
                    'success': False,
                    'error': f'Unsupported export type: {export_type}'
                }
            
            return {
                'success': True,
                'file_path': str(file_path),
                'filename': filename,
                'size_bytes': file_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_dashboard(self, host: str = '0.0.0.0', port: int = 5001, debug: bool = False):
        """Run the dashboard web application."""
        try:
            logger.info(f"Starting MySQL Monitoring Dashboard on {host}:{port}")
            
            # Start metrics collection
            self.start_metrics_collection()
            
            # Run Flask app with SocketIO
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )
            
        except Exception as e:
            logger.error(f"Failed to run dashboard: {e}")
            raise
        finally:
            # Cleanup
            self.stop_metrics_collection()
    
    def cleanup_resources(self):
        """Clean up dashboard resources."""
        try:
            # Stop metrics collection
            self.stop_metrics_collection()
            
            # Cleanup monitoring components
            self.performance_optimizer.cleanup_resources()
            self.performance_monitor.cleanup_resources()
            self.security_hardening.cleanup_resources()
            self.backup_recovery.cleanup_resources()
            
            # Close Redis connection
            if self.redis_client:
                try:
                    self.redis_client.close()
                except:
                    pass
            
            logger.info("MySQL Monitoring Dashboard resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during dashboard resource cleanup: {e}")


def main():
    """Command-line interface for MySQL Monitoring Dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQL Monitoring Dashboard for Vedfolnir')
    parser.add_argument('--action', choices=[
        'run', 'start-metrics', 'stop-metrics', 'generate-report', 'export'
    ], required=True, help='Action to perform')
    
    parser.add_argument('--host', default='0.0.0.0', help='Dashboard host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5001, help='Dashboard port (default: 5001)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    parser.add_argument('--report-type', choices=['performance', 'security', 'backup', 'comprehensive'],
                       default='comprehensive', help='Type of analytics report')
    parser.add_argument('--time-range-hours', type=int, default=24, help='Time range for analysis (hours)')
    
    parser.add_argument('--export-type', choices=['metrics', 'alerts'], help='Type of data to export')
    parser.add_argument('--export-format', choices=['json', 'csv'], default='json', help='Export format')
    parser.add_argument('--export-hours', type=int, default=24, help='Hours of data to export')
    
    parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                       help='Output format (default: table)')
    
    args = parser.parse_args()
    
    # Initialize dashboard
    try:
        dashboard = MySQLMonitoringDashboard()
        
        if args.action == 'run':
            dashboard.run_dashboard(args.host, args.port, args.debug)
            
        elif args.action == 'start-metrics':
            result = dashboard.start_metrics_collection()
            print_result(result, args.output_format)
            
        elif args.action == 'stop-metrics':
            result = dashboard.stop_metrics_collection()
            print_result(result, args.output_format)
            
        elif args.action == 'generate-report':
            report = dashboard._generate_analytics_report(args.report_type, args.time_range_hours)
            result = {
                'success': True,
                'report': asdict(report),
                'timestamp': datetime.now().isoformat()
            }
            print_result(result, args.output_format)
            
        elif args.action == 'export':
            if not args.export_type:
                print("Error: --export-type is required for export action")
                sys.exit(1)
            
            export_result = dashboard._export_data(args.export_type, args.export_hours, args.export_format)
            print_result(export_result, args.output_format)
        
        # Cleanup
        dashboard.cleanup_resources()
        
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")
        if 'dashboard' in locals():
            dashboard.cleanup_resources()
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        print_result(error_result, args.output_format)
        sys.exit(1)


def print_result(result: Dict[str, Any], output_format: str):
    """Print result in the specified format."""
    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*60}")
        print(f"MySQL Monitoring Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if result.get('success'):
            print("✅ Operation completed successfully")
            
            # Print specific result information
            if 'report' in result:
                report = result['report']
                print(f"\n📊 Analytics Report:")
                print(f"  Report ID: {report['report_id']}")
                print(f"  Type: {report['report_type']}")
                print(f"  Insights: {len(report['insights'])}")
                print(f"  Recommendations: {len(report['recommendations'])}")
                
                # Show top insights
                for insight in report['insights'][:3]:
                    level_emoji = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}
                    emoji = level_emoji.get(insight.get('type', 'info'), 'ℹ️')
                    print(f"  {emoji} {insight.get('message', 'No message')}")
            
            if 'file_path' in result:
                print(f"\n📁 Export Information:")
                print(f"  File: {result['filename']}")
                print(f"  Size: {result.get('size_bytes', 0)} bytes")
                print(f"  Path: {result['file_path']}")
        
        else:
            print("❌ Operation failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
        
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
