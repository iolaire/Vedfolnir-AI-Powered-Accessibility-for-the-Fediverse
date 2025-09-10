# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Monitoring Dashboard

Provides web-based dashboard endpoints for real-time monitoring of the notification system,
including delivery status, WebSocket connections, performance metrics, and alerting.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_required, current_user

from app.services.monitoring.system.notification_monitor import NotificationSystemMonitor, AlertSeverity
from models import UserRole
from app.core.security.core.role_based_access import require_admin

logger = logging.getLogger(__name__)

# Create blueprint for monitoring dashboard
monitoring_bp = Blueprint('notification_monitoring', __name__, url_prefix='/admin/monitoring/notifications')


@monitoring_bp.route('/dashboard')
@login_required
@require_admin
def monitoring_dashboard():
    """
    Main monitoring dashboard page
    
    Returns:
        Rendered dashboard template
    """
    try:
        return render_template('admin/notification_monitoring_dashboard.html',
                             title='Notification System Monitoring')
    except Exception as e:
        logger.error(f"Failed to render monitoring dashboard: {e}")
        return render_template('admin/error.html', 
                             error="Failed to load monitoring dashboard"), 500


@monitoring_bp.route('/api/health')
@login_required
@require_admin
def get_system_health():
    """
    Get comprehensive system health status
    
    Returns:
        JSON response with system health data
    """
    try:
        monitor = current_app.notification_system_monitor
        health_data = monitor.get_system_health()
        
        return jsonify({
            'success': True,
            'data': health_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/delivery')
@login_required
@require_admin
def get_delivery_metrics():
    """
    Get notification delivery dashboard data
    
    Returns:
        JSON response with delivery metrics
    """
    try:
        monitor = current_app.notification_system_monitor
        delivery_data = monitor.get_delivery_dashboard_data()
        
        return jsonify({
            'success': True,
            'data': delivery_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get delivery metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/websocket')
@login_required
@require_admin
def get_websocket_metrics():
    """
    Get WebSocket connection dashboard data
    
    Returns:
        JSON response with WebSocket metrics
    """
    try:
        monitor = current_app.notification_system_monitor
        websocket_data = monitor.get_websocket_dashboard_data()
        
        return jsonify({
            'success': True,
            'data': websocket_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get WebSocket metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/performance')
@login_required
@require_admin
def get_performance_metrics():
    """
    Get system performance metrics
    
    Returns:
        JSON response with performance metrics
    """
    try:
        monitor = current_app.notification_system_monitor
        performance_data = monitor.get_performance_metrics()
        
        return jsonify({
            'success': True,
            'data': performance_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/alerts')
@login_required
@require_admin
def get_alerts():
    """
    Get current alerts and alert history
    
    Returns:
        JSON response with alert data
    """
    try:
        monitor = current_app.notification_system_monitor
        health_data = monitor.get_system_health()
        
        # Extract alert information
        active_alerts = health_data.get('active_alerts', [])
        
        # Get alert history (last 50 alerts)
        alert_history = list(monitor._alert_history)[-50:]
        
        return jsonify({
            'success': True,
            'data': {
                'active_alerts': active_alerts,
                'alert_history': [
                    {
                        'id': alert.id,
                        'severity': alert.severity.value,
                        'title': alert.title,
                        'message': alert.message,
                        'component': alert.component,
                        'timestamp': alert.timestamp.isoformat(),
                        'resolved': alert.resolved,
                        'resolution_time': alert.resolution_time.isoformat() if alert.resolution_time else None
                    }
                    for alert in alert_history
                ],
                'alert_count': len(active_alerts)
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/recovery', methods=['POST'])
@login_required
@require_admin
def trigger_recovery():
    """
    Manually trigger a recovery action
    
    Returns:
        JSON response with recovery result
    """
    try:
        data = request.get_json()
        action_type = data.get('action_type')
        
        if not action_type:
            return jsonify({
                'success': False,
                'error': 'Missing action_type parameter'
            }), 400
        
        monitor = current_app.notification_system_monitor
        success = monitor.trigger_recovery_action(action_type)
        
        return jsonify({
            'success': success,
            'message': f'Recovery action "{action_type}" {"completed successfully" if success else "failed"}',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to trigger recovery: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/config')
@login_required
@require_admin
def get_monitoring_config():
    """
    Get monitoring configuration and thresholds
    
    Returns:
        JSON response with monitoring configuration
    """
    try:
        monitor = current_app.notification_system_monitor
        
        config_data = {
            'monitoring_interval': monitor.monitoring_interval,
            'alert_thresholds': monitor.alert_thresholds,
            'monitoring_active': monitor._monitoring_active,
            'recovery_actions': list(monitor._recovery_actions.keys()),
            'metrics_history_size': {
                'delivery_metrics': len(monitor._delivery_metrics_history),
                'connection_metrics': len(monitor._connection_metrics_history),
                'performance_metrics': len(monitor._performance_metrics_history)
            }
        }
        
        return jsonify({
            'success': True,
            'data': config_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get monitoring config: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/start', methods=['POST'])
@login_required
@require_admin
def start_monitoring():
    """
    Start monitoring system
    
    Returns:
        JSON response with start result
    """
    try:
        monitor = current_app.notification_system_monitor
        
        if monitor._monitoring_active:
            return jsonify({
                'success': True,
                'message': 'Monitoring is already active',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        monitor.start_monitoring()
        
        return jsonify({
            'success': True,
            'message': 'Monitoring started successfully',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/stop', methods=['POST'])
@login_required
@require_admin
def stop_monitoring():
    """
    Stop monitoring system
    
    Returns:
        JSON response with stop result
    """
    try:
        monitor = current_app.notification_system_monitor
        
        if not monitor._monitoring_active:
            return jsonify({
                'success': True,
                'message': 'Monitoring is already stopped',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        monitor.stop_monitoring()
        
        return jsonify({
            'success': True,
            'message': 'Monitoring stopped successfully',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@monitoring_bp.route('/api/realtime')
@login_required
@require_admin
def get_realtime_data():
    """
    Get real-time monitoring data for live updates
    
    Returns:
        JSON response with real-time data
    """
    try:
        monitor = current_app.notification_system_monitor
        
        # Get current metrics
        health_data = monitor.get_system_health()
        delivery_data = monitor.get_delivery_dashboard_data()
        websocket_data = monitor.get_websocket_dashboard_data()
        performance_data = monitor.get_performance_metrics()
        
        # Combine into real-time update
        realtime_data = {
            'health': {
                'status': health_data.get('overall_health'),
                'alert_count': health_data.get('alert_count', 0)
            },
            'delivery': {
                'rate': delivery_data.get('trends', {}).get('delivery_rate', {}).get('current', 0),
                'queue_depth': delivery_data.get('trends', {}).get('queue_depth', {}).get('current', 0),
                'messages_per_second': delivery_data.get('current_metrics', {}).get('messages_per_second', 0) if delivery_data.get('current_metrics') else 0
            },
            'websocket': {
                'active_connections': websocket_data.get('current_metrics', {}).get('active_connections', 0) if websocket_data.get('current_metrics') else 0,
                'success_rate': websocket_data.get('trends', {}).get('success_rate', {}).get('current', 0)
            },
            'performance': {
                'cpu_usage': performance_data.get('trends', {}).get('cpu_usage', {}).get('current', 0),
                'memory_usage': performance_data.get('trends', {}).get('memory_usage', {}).get('current', 0),
                'notification_latency': performance_data.get('trends', {}).get('notification_latency', {}).get('current', 0)
            }
        }
        
        return jsonify({
            'success': True,
            'data': realtime_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get real-time data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


# WebSocket events for real-time updates
def setup_monitoring_websocket_events(socketio, monitor: NotificationSystemMonitor):
    """
    Set up WebSocket events for real-time monitoring updates
    
    Args:
        socketio: Flask-SocketIO instance
        monitor: NotificationSystemMonitor instance
    """
    
    @socketio.on('join_monitoring', namespace='/admin')
    def on_join_monitoring():
        """Handle client joining monitoring room"""
        try:
            if current_user.is_authenticated and current_user.role == UserRole.ADMIN:
                from flask_socketio import join_room
                join_room('monitoring')
                logger.info(f"Admin user {current_user.username} joined monitoring room")
            else:
                logger.warning("Non-admin user attempted to join monitoring room")
        except Exception as e:
            logger.error(f"Failed to join monitoring room: {e}")
    
    @socketio.on('leave_monitoring', namespace='/admin')
    def on_leave_monitoring():
        """Handle client leaving monitoring room"""
        try:
            if current_user.is_authenticated:
                from flask_socketio import leave_room
                leave_room('monitoring')
                logger.info(f"User {current_user.username} left monitoring room")
        except Exception as e:
            logger.error(f"Failed to leave monitoring room: {e}")
    
    # Register alert callback to send real-time alerts
    def alert_callback(alert):
        """Send real-time alert to monitoring clients"""
        try:
            from flask_socketio import emit
            emit('monitoring_alert', {
                'id': alert.id,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'component': alert.component,
                'timestamp': alert.timestamp.isoformat()
            }, room='monitoring', namespace='/admin')
        except Exception as e:
            logger.error(f"Failed to send real-time alert: {e}")
    
    monitor.register_alert_callback(alert_callback)


class NotificationMonitoringDashboard:
    """
    Notification monitoring dashboard service
    
    Provides integration between the monitoring system and web interface
    """
    
    def __init__(self, monitor: NotificationSystemMonitor):
        """
        Initialize monitoring dashboard
        
        Args:
            monitor: NotificationSystemMonitor instance
        """
        self.monitor = monitor
        self.logger = logging.getLogger(__name__)
    
    def register_with_app(self, app, socketio=None):
        """
        Register monitoring dashboard with Flask app
        
        Args:
            app: Flask application instance
            socketio: Flask-SocketIO instance (optional)
        """
        try:
            # Register blueprint
            app.register_blueprint(monitoring_bp)
            
            # Store monitor in app context
            app.notification_system_monitor = self.monitor
            
            # Set up WebSocket events if socketio is provided
            if socketio:
                setup_monitoring_websocket_events(socketio, self.monitor)
            
            self.logger.info("Notification monitoring dashboard registered with app")
            
        except Exception as e:
            self.logger.error(f"Failed to register monitoring dashboard: {e}")
            raise
    
    def start_monitoring(self):
        """Start the monitoring system"""
        try:
            self.monitor.start_monitoring()
            self.logger.info("Monitoring system started")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring system: {e}")
            raise
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        try:
            self.monitor.stop_monitoring()
            self.logger.info("Monitoring system stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring system: {e}")
            raise
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get dashboard summary data
        
        Returns:
            Dictionary containing dashboard summary
        """
        try:
            health_data = self.monitor.get_system_health()
            
            return {
                'overall_health': health_data.get('overall_health'),
                'active_alerts': len(health_data.get('active_alerts', [])),
                'monitoring_active': self.monitor._monitoring_active,
                'last_check': health_data.get('last_check'),
                'summary': {
                    'delivery_rate': health_data.get('delivery_metrics', {}).get('delivery_rate', 0),
                    'active_connections': health_data.get('connection_metrics', {}).get('active_connections', 0),
                    'cpu_usage': health_data.get('performance_metrics', {}).get('cpu_usage', 0),
                    'memory_usage': health_data.get('performance_metrics', {}).get('memory_usage', 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard summary: {e}")
            return {'error': str(e)}


def create_monitoring_dashboard(monitor: NotificationSystemMonitor) -> NotificationMonitoringDashboard:
    """
    Create notification monitoring dashboard
    
    Args:
        monitor: NotificationSystemMonitor instance
        
    Returns:
        NotificationMonitoringDashboard instance
    """
    return NotificationMonitoringDashboard(monitor)