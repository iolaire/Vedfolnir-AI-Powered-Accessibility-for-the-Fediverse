# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from session_performance_monitor import get_performance_monitor
from models import UserRole


def admin_required(f):
    """Decorator to require admin role for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if current_user.role != UserRole.ADMIN:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# Create blueprint for session monitoring routes
session_monitoring_bp = Blueprint('session_monitoring', __name__, url_prefix='/admin/session-monitoring')


@session_monitoring_bp.route('/status')
@login_required
@admin_required
def monitoring_status():
    """Get current session monitoring status."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        return jsonify({
            'status': 'success',
            'data': metrics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving session monitoring status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@session_monitoring_bp.route('/summary')
@login_required
@admin_required
def monitoring_summary():
    """Get performance summary."""
    try:
        monitor = get_performance_monitor()
        summary = monitor.get_performance_summary()
        
        return jsonify({
            'status': 'success',
            'data': {
                'summary': summary,
                'metrics': monitor.get_current_metrics()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving performance summary: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@session_monitoring_bp.route('/alerts')
@login_required
@admin_required
def monitoring_alerts():
    """Check for performance alerts."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        alerts = []
        
        # Performance thresholds
        slow_threshold = float(request.args.get('slow_threshold', 1.0))
        error_rate_threshold = float(request.args.get('error_rate_threshold', 0.05))
        recovery_rate_threshold = float(request.args.get('recovery_rate_threshold', 0.1))
        pool_utilization_threshold = float(request.args.get('pool_utilization_threshold', 0.8))
        
        # Check for slow operations
        perf_metrics = metrics['performance_metrics']
        
        if perf_metrics['avg_creation_time'] > slow_threshold:
            alerts.append({
                'type': 'slow_operation',
                'severity': 'warning',
                'message': f"Slow session creation: {perf_metrics['avg_creation_time']:.3f}s",
                'threshold': slow_threshold,
                'value': perf_metrics['avg_creation_time']
            })
        
        if perf_metrics['avg_cleanup_time'] > slow_threshold:
            alerts.append({
                'type': 'slow_operation',
                'severity': 'warning',
                'message': f"Slow session cleanup: {perf_metrics['avg_cleanup_time']:.3f}s",
                'threshold': slow_threshold,
                'value': perf_metrics['avg_cleanup_time']
            })
        
        if perf_metrics['avg_recovery_time'] > slow_threshold:
            alerts.append({
                'type': 'slow_operation',
                'severity': 'warning',
                'message': f"Slow recovery operations: {perf_metrics['avg_recovery_time']:.3f}s",
                'threshold': slow_threshold,
                'value': perf_metrics['avg_recovery_time']
            })
        
        # Check for high error rates
        session_metrics = metrics['session_metrics']
        total_operations = session_metrics['creations'] + session_metrics['closures']
        
        if total_operations > 0:
            error_rate = session_metrics['errors'] / total_operations
            if error_rate > error_rate_threshold:
                alerts.append({
                    'type': 'high_error_rate',
                    'severity': 'error',
                    'message': f"High error rate: {error_rate:.2%}",
                    'threshold': error_rate_threshold,
                    'value': error_rate,
                    'details': f"{session_metrics['errors']} errors out of {total_operations} operations"
                })
        
        # Check for high recovery rate
        recovery_rate = metrics['recovery_metrics']['recovery_rate']
        if recovery_rate > recovery_rate_threshold:
            alerts.append({
                'type': 'high_recovery_rate',
                'severity': 'warning',
                'message': f"High recovery rate: {recovery_rate:.2%}",
                'threshold': recovery_rate_threshold,
                'value': recovery_rate,
                'details': f"{metrics['recovery_metrics']['detached_instance_recoveries']} recoveries"
            })
        
        # Check pool utilization
        pool_metrics = metrics['pool_metrics']
        if pool_metrics['pool_size'] > 0:
            utilization = pool_metrics['checked_out'] / pool_metrics['pool_size']
            if utilization > pool_utilization_threshold:
                alerts.append({
                    'type': 'high_pool_utilization',
                    'severity': 'critical',
                    'message': f"High pool utilization: {utilization:.1%}",
                    'threshold': pool_utilization_threshold,
                    'value': utilization,
                    'details': f"{pool_metrics['checked_out']} out of {pool_metrics['pool_size']} connections"
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts,
                'alert_count': len(alerts),
                'has_critical': any(alert['severity'] == 'critical' for alert in alerts),
                'has_errors': any(alert['severity'] == 'error' for alert in alerts),
                'has_warnings': any(alert['severity'] == 'warning' for alert in alerts)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking performance alerts: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@session_monitoring_bp.route('/dashboard')
@login_required
@admin_required
def monitoring_dashboard():
    """Render session monitoring dashboard."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        return render_template('admin/session_monitoring_dashboard.html',
                             metrics=metrics,
                             title="Session Performance Monitoring")
        
    except Exception as e:
        current_app.logger.error(f"Error rendering monitoring dashboard: {e}")
        return render_template('errors/500.html'), 500


@session_monitoring_bp.route('/health')
def monitoring_health():
    """Health check endpoint for monitoring systems."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        # Basic health checks
        health_status = 'healthy'
        issues = []
        
        # Check for critical issues
        session_metrics = metrics['session_metrics']
        if session_metrics['errors'] > 0:
            total_ops = session_metrics['creations'] + session_metrics['closures']
            error_rate = session_metrics['errors'] / total_ops if total_ops > 0 else 0
            if error_rate > 0.1:  # 10% error rate is critical
                health_status = 'unhealthy'
                issues.append(f"High error rate: {error_rate:.2%}")
        
        # Check pool exhaustion
        pool_metrics = metrics['pool_metrics']
        if pool_metrics['pool_size'] > 0:
            utilization = pool_metrics['checked_out'] / pool_metrics['pool_size']
            if utilization > 0.95:  # 95% utilization is critical
                health_status = 'unhealthy'
                issues.append(f"Pool near exhaustion: {utilization:.1%}")
        
        # Check for excessive recovery operations
        recovery_rate = metrics['recovery_metrics']['recovery_rate']
        if recovery_rate > 0.2:  # 20% recovery rate is concerning
            health_status = 'degraded' if health_status == 'healthy' else health_status
            issues.append(f"High recovery rate: {recovery_rate:.2%}")
        
        return jsonify({
            'status': health_status,
            'timestamp': metrics['timestamp'],
            'issues': issues,
            'metrics_summary': {
                'active_sessions': session_metrics['active_sessions'],
                'error_rate': session_metrics['errors'] / max(session_metrics['creations'], 1),
                'recovery_rate': recovery_rate,
                'pool_utilization': pool_metrics['checked_out'] / max(pool_metrics['pool_size'], 1)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in monitoring health check: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': None
        }), 500


def register_session_monitoring_routes(app):
    """Register session monitoring routes with the Flask app."""
    app.register_blueprint(session_monitoring_bp)