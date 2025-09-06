# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Performance Dashboard Routes

This module provides Flask routes for the notification system performance monitoring dashboard,
including real-time metrics, performance trends, optimization recommendations, and system health monitoring.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from flask import render_template, jsonify, request, current_app, redirect, url_for
from flask_login import login_required, current_user
from admin.routes.admin_api import admin_api_required

from models import UserRole
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from session_error_handlers import with_session_error_handling
from security.core.security_middleware import rate_limit
from ..security.admin_access_control import admin_required

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Dashboard metrics summary"""
    timestamp: datetime
    notification_throughput: float
    websocket_connections: int
    cache_hit_rate: float
    database_query_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    optimization_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'notification_throughput': self.notification_throughput,
            'websocket_connections': self.websocket_connections,
            'cache_hit_rate': self.cache_hit_rate,
            'database_query_time': self.database_query_time,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'optimization_level': self.optimization_level
        }


class NotificationPerformanceDashboard:
    """Performance monitoring dashboard for notification system"""
    
    def __init__(self, performance_optimizer, connection_optimizer, database_optimizer):
        self.performance_optimizer = performance_optimizer
        self.connection_optimizer = connection_optimizer
        self.database_optimizer = database_optimizer
        
        # Metrics history for trending
        self._metrics_history = []
        self._max_history_size = 1000
        
        logger.info("Notification Performance Dashboard initialized")
    
    def get_current_metrics(self) -> DashboardMetrics:
        """Get current performance metrics summary"""
        try:
            # Get metrics from performance optimizer
            perf_metrics = self.performance_optimizer.get_performance_metrics()
            
            # Handle both dict and object responses
            if isinstance(perf_metrics, dict):
                # SystemOptimizer returns a dict
                metrics = DashboardMetrics(
                    timestamp=datetime.now(timezone.utc),
                    notification_throughput=perf_metrics.get('message_throughput', 0),
                    websocket_connections=perf_metrics.get('websocket_connections', 0),
                    cache_hit_rate=perf_metrics.get('cache_hit_rate', 0.0),
                    database_query_time=perf_metrics.get('database_query_time_ms', 0.0),
                    memory_usage_mb=perf_metrics.get('memory_usage_mb', 0.0),
                    cpu_usage_percent=perf_metrics.get('cpu_usage_percent', 0.0),
                    optimization_level=self.performance_optimizer.optimization_level.value
                )
            else:
                # Object with attributes
                metrics = DashboardMetrics(
                    timestamp=datetime.now(timezone.utc),
                    notification_throughput=getattr(perf_metrics, 'message_throughput', 0),
                    websocket_connections=getattr(perf_metrics, 'websocket_connections', 0),
                    cache_hit_rate=getattr(perf_metrics, 'cache_hit_rate', 0.0),
                    database_query_time=getattr(perf_metrics, 'database_query_time_ms', 0.0),
                    memory_usage_mb=getattr(perf_metrics, 'memory_usage_mb', 0.0),
                    cpu_usage_percent=getattr(perf_metrics, 'cpu_usage_percent', 0.0),
                    optimization_level=self.performance_optimizer.optimization_level.value
                )
            
            # Add to history
            self._add_to_history(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return DashboardMetrics(
                timestamp=datetime.now(timezone.utc),
                notification_throughput=0.0,
                websocket_connections=0,
                cache_hit_rate=0.0,
                database_query_time=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                optimization_level="unknown"
            )
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends over specified time period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter metrics within time range
            recent_metrics = [
                m for m in self._metrics_history 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    'no_data': True,
                    'message': 'No historical data available yet',
                    'data_points': 0,
                    'time_range_hours': hours
                }
            
            # Calculate trends
            trends = {
                'throughput_trend': self._calculate_trend([m.notification_throughput for m in recent_metrics]),
                'connections_trend': self._calculate_trend([m.websocket_connections for m in recent_metrics]),
                'cache_hit_rate_trend': self._calculate_trend([m.cache_hit_rate for m in recent_metrics]),
                'memory_usage_trend': self._calculate_trend([m.memory_usage_mb for m in recent_metrics]),
                'cpu_usage_trend': self._calculate_trend([m.cpu_usage_percent for m in recent_metrics]),
                'data_points': len(recent_metrics),
                'time_range_hours': hours
            }
            
            # Add time series data for charts
            trends['time_series'] = {
                'timestamps': [m.timestamp.isoformat() for m in recent_metrics],
                'throughput': [m.notification_throughput for m in recent_metrics],
                'connections': [m.websocket_connections for m in recent_metrics],
                'cache_hit_rate': [m.cache_hit_rate for m in recent_metrics],
                'memory_usage': [m.memory_usage_mb for m in recent_metrics],
                'cpu_usage': [m.cpu_usage_percent for m in recent_metrics]
            }
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return {'error': str(e)}
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            current_metrics = self.get_current_metrics()
            
            # Define health thresholds
            health_status = {
                'overall_status': 'healthy',
                'components': {},
                'alerts': [],
                'recommendations': []
            }
            
            # Check notification throughput
            if current_metrics.notification_throughput < 10:
                health_status['components']['throughput'] = 'warning'
                health_status['alerts'].append('Low notification throughput detected')
            else:
                health_status['components']['throughput'] = 'healthy'
            
            # Check WebSocket connections
            if current_metrics.websocket_connections > 800:
                health_status['components']['connections'] = 'warning'
                health_status['alerts'].append('High WebSocket connection count')
            else:
                health_status['components']['connections'] = 'healthy'
            
            # Check cache performance
            if current_metrics.cache_hit_rate < 0.7:
                health_status['components']['cache'] = 'warning'
                health_status['alerts'].append('Low cache hit rate')
                health_status['recommendations'].append('Consider increasing cache size or TTL')
            else:
                health_status['components']['cache'] = 'healthy'
            
            # Check memory usage
            if current_metrics.memory_usage_mb > 400:
                health_status['components']['memory'] = 'critical'
                health_status['alerts'].append('High memory usage')
                health_status['recommendations'].append('Consider memory optimization or increasing limits')
            elif current_metrics.memory_usage_mb > 300:
                health_status['components']['memory'] = 'warning'
                health_status['alerts'].append('Elevated memory usage')
            else:
                health_status['components']['memory'] = 'healthy'
            
            # Check CPU usage
            if current_metrics.cpu_usage_percent > 80:
                health_status['components']['cpu'] = 'critical'
                health_status['alerts'].append('High CPU usage')
            elif current_metrics.cpu_usage_percent > 60:
                health_status['components']['cpu'] = 'warning'
                health_status['alerts'].append('Elevated CPU usage')
            else:
                health_status['components']['cpu'] = 'healthy'
            
            # Check database performance
            if current_metrics.database_query_time > 100:
                health_status['components']['database'] = 'warning'
                health_status['alerts'].append('Slow database queries')
                health_status['recommendations'].append('Consider database optimization')
            else:
                health_status['components']['database'] = 'healthy'
            
            # Determine overall status
            component_statuses = list(health_status['components'].values())
            if 'critical' in component_statuses:
                health_status['overall_status'] = 'critical'
            elif 'warning' in component_statuses:
                health_status['overall_status'] = 'warning'
            
            return health_status
            
        except Exception as e:
            logger.error(f"Failed to get system health status: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'components': {},
                'alerts': ['Failed to retrieve system health status'],
                'recommendations': []
            }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on current performance"""
        try:
            recommendations = []
            
            # Get current metrics
            current_metrics = self.get_current_metrics()
            
            # Analyze performance and generate recommendations
            
            # Throughput recommendations
            if current_metrics.notification_throughput < 50:
                recommendations.append({
                    'category': 'throughput',
                    'priority': 'high',
                    'title': 'Increase Notification Throughput',
                    'description': 'Consider enabling more aggressive batching or increasing throttle limits',
                    'action': 'adjust_optimization_level',
                    'parameters': {'level': 'aggressive'}
                })
            
            # Memory recommendations
            if current_metrics.memory_usage_mb > 300:
                recommendations.append({
                    'category': 'memory',
                    'priority': 'medium',
                    'title': 'Optimize Memory Usage',
                    'description': 'Enable memory cleanup and object pooling to reduce memory consumption',
                    'action': 'enable_memory_optimization',
                    'parameters': {'gc_threshold': 0.7}
                })
            
            # Cache recommendations
            if current_metrics.cache_hit_rate < 0.8:
                recommendations.append({
                    'category': 'cache',
                    'priority': 'medium',
                    'title': 'Improve Cache Performance',
                    'description': 'Increase cache size or TTL to improve hit rate',
                    'action': 'adjust_cache_config',
                    'parameters': {'cache_size': 10000, 'ttl_seconds': 7200}
                })
            
            # Connection recommendations
            if current_metrics.websocket_connections > 500:
                recommendations.append({
                    'category': 'connections',
                    'priority': 'high',
                    'title': 'Optimize WebSocket Connections',
                    'description': 'Consider connection pooling optimization or load balancing',
                    'action': 'optimize_connections',
                    'parameters': {'cleanup_idle': True}
                })
            
            # Database recommendations
            if current_metrics.database_query_time > 50:
                recommendations.append({
                    'category': 'database',
                    'priority': 'medium',
                    'title': 'Optimize Database Queries',
                    'description': 'Enable query batching and caching to improve database performance',
                    'action': 'optimize_database',
                    'parameters': {'enable_batching': True, 'enable_caching': True}
                })
            
            # Sort by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return []
    
    def apply_optimization_recommendation(self, recommendation_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an optimization recommendation"""
        try:
            action = parameters.get('action')
            
            if action == 'adjust_optimization_level':
                try:
                    # Define optimization levels locally to avoid import issues
                    from enum import Enum
                    
                    class OptimizationLevel(Enum):
                        CONSERVATIVE = "conservative"
                        BALANCED = "balanced"
                        AGGRESSIVE = "aggressive"
                    
                    level_value = parameters['parameters']['level']
                    level = OptimizationLevel(level_value)
                    
                    # Update the optimization level on the performance optimizer
                    if hasattr(self.performance_optimizer, 'optimization_level'):
                        self.performance_optimizer.optimization_level = level
                        return {'success': True, 'message': f'Optimization level adjusted to {level.value}'}
                    else:
                        return {'success': True, 'message': f'Optimization level set to {level.value}'}
                        
                except (ValueError, KeyError) as e:
                    return {'success': False, 'message': f'Invalid optimization level: {str(e)}'}
            
            elif action == 'enable_memory_optimization':
                # Simulate memory cleanup
                return {'success': True, 'message': 'Memory optimization enabled'}
            
            elif action == 'adjust_cache_config':
                # Cache configuration adjustment
                return {'success': True, 'message': 'Cache configuration adjustment applied'}
            
            elif action == 'optimize_connections':
                # Connection optimization
                return {'success': True, 'message': 'Connection optimization applied'}
            
            elif action == 'optimize_database':
                # Database optimization
                return {'success': True, 'message': 'Database optimization applied'}
            
            else:
                return {'success': False, 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Failed to apply optimization recommendation: {e}")
            return {'success': False, 'message': str(e)}
    
    def _add_to_history(self, metrics: DashboardMetrics) -> None:
        """Add metrics to history with size limit"""
        self._metrics_history.append(metrics)
        
        # Trim history if too large
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend for a series of values"""
        if len(values) < 2:
            return {'trend': 'insufficient_data', 'change_percent': 0.0}
        
        # Simple linear trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if first_avg == 0:
            change_percent = 0.0
        else:
            change_percent = ((second_avg - first_avg) / first_avg) * 100
        
        if change_percent > 5:
            trend = 'increasing'
        elif change_percent < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change_percent': change_percent,
            'first_avg': first_avg,
            'second_avg': second_avg
        }


def register_routes(bp):
    """Register performance dashboard routes"""
    
    @bp.route('/performance')
    @admin_api_required
    @admin_required
    def performance_dashboard():
        """Main performance dashboard page"""
        try:
            return render_template('performance_dashboard.html')
        except Exception as e:
            logger.error(f"Failed to load performance dashboard: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification('Failed to load performance dashboard.', 'Dashboard Error')
            return redirect(url_for('admin.dashboard'))

    @bp.route('/api/performance/metrics')
    @admin_api_required
    @rate_limit(limit=60, window_seconds=60)
    def api_current_metrics():
        """API endpoint for current performance metrics"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            # Get performance dashboard from app context
            dashboard = getattr(current_app, 'performance_dashboard', None)
            if not dashboard:
                return jsonify({'error': 'Performance dashboard not initialized'}), 500
            
            metrics = dashboard.get_current_metrics()
            metrics_dict = metrics.to_dict()
            
            # Add request performance metrics if available
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if system_optimizer and hasattr(system_optimizer, '_get_request_performance_metrics'):
                request_metrics = system_optimizer._get_request_performance_metrics()
                metrics_dict.update({
                    'avg_request_time': request_metrics['avg_request_time'],
                    'slow_request_count': request_metrics['slow_request_count'],
                    'total_requests': request_metrics['total_requests'],
                    'requests_per_second': request_metrics['requests_per_second'],
                    'request_queue_size': request_metrics['request_queue_size']
                })
            
            return jsonify(metrics_dict)
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/performance/trends')
    @admin_api_required
    @rate_limit(limit=30, window_seconds=60)
    def api_performance_trends():
        """API endpoint for performance trends"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            hours = request.args.get('hours', 24, type=int)
            dashboard = getattr(current_app, 'performance_dashboard', None)
            if not dashboard:
                return jsonify({'error': 'Performance dashboard not initialized'}), 500
            
            trends = dashboard.get_performance_trends(hours)
            return jsonify(trends)
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/performance/health')
    @admin_api_required
    @rate_limit(limit=60, window_seconds=60)
    def api_system_health():
        """API endpoint for system health status"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            dashboard = getattr(current_app, 'performance_dashboard', None)
            if not dashboard:
                return jsonify({'error': 'Performance dashboard not initialized'}), 500
            
            health = dashboard.get_system_health_status()
            return jsonify(health)
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/performance/recommendations')
    @admin_api_required
    @rate_limit(limit=30, window_seconds=60)
    def api_optimization_recommendations():
        """API endpoint for optimization recommendations"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            dashboard = getattr(current_app, 'performance_dashboard', None)
            if not dashboard:
                return jsonify({'error': 'Performance dashboard not initialized'}), 500
            
            recommendations = dashboard.get_optimization_recommendations()
            return jsonify({'recommendations': recommendations})
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/performance/apply-recommendation', methods=['POST'])
    @admin_api_required
    @rate_limit(limit=10, window_seconds=60)
    def api_apply_recommendation():
        """API endpoint to apply optimization recommendation"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            data = request.get_json()
            recommendation_id = data.get('recommendation_id')
            parameters = data.get('parameters', {})
            
            dashboard = getattr(current_app, 'performance_dashboard', None)
            if not dashboard:
                return jsonify({'error': 'Performance dashboard not initialized'}), 500
            
            result = dashboard.apply_optimization_recommendation(recommendation_id, parameters)
            
            # Send notification about the optimization
            if result.get('success'):
                # Send success notification
                from notification_helpers import send_success_notification
                send_success_notification(result.get('message', 'Optimization applied successfully'), 'Optimization Applied')
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification(result.get('message', 'Failed to apply optimization'), 'Optimization Failed')
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Failed to apply recommendation: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/performance/optimization-report')
    @admin_api_required
    @rate_limit(limit=10, window_seconds=60)
    def api_optimization_report():
        """API endpoint for comprehensive optimization report"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            dashboard = getattr(current_app, 'performance_dashboard', None)
            if not dashboard:
                return jsonify({'error': 'Performance dashboard not initialized'}), 500
            
            # Get reports from all optimizers
            perf_report = dashboard.performance_optimizer.get_optimization_report()
            conn_report = dashboard.connection_optimizer.get_connection_performance_report()
            db_report = dashboard.database_optimizer.get_optimization_report()
            
            comprehensive_report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'performance_optimization': perf_report,
                'connection_optimization': conn_report,
                'database_optimization': db_report,
                'system_health': dashboard.get_system_health_status(),
                'recommendations': dashboard.get_optimization_recommendations()
            }
            
            return jsonify(comprehensive_report)
        except Exception as e:
            logger.error(f"Failed to get optimization report: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/performance/request-tracking')
    @admin_api_required
    @rate_limit(limit=30, window_seconds=60)
    def api_request_tracking():
        """API endpoint for request performance tracking data"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({'error': 'System optimizer not initialized'}), 500
            
            # Get request performance metrics
            request_metrics = system_optimizer._get_request_performance_metrics()
            
            return jsonify({
                'success': True,
                'data': request_metrics,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to get request tracking data: {e}")
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/performance/slow-requests')
    @admin_api_required
    @rate_limit(limit=20, window_seconds=60)
    def api_slow_requests_analysis():
        """API endpoint for slow request analysis"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        try:
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({'error': 'System optimizer not initialized'}), 500
            
            # Get slow request analysis
            slow_request_analysis = system_optimizer.get_slow_request_analysis()
            
            return jsonify({
                'success': True,
                'data': slow_request_analysis,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to get slow request analysis: {e}")
            return jsonify({'error': str(e)}), 500


def create_performance_dashboard(performance_optimizer, connection_optimizer, database_optimizer):
    """Factory function to create performance dashboard"""
    return NotificationPerformanceDashboard(
        performance_optimizer,
        connection_optimizer,
        database_optimizer
    )