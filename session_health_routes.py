# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Health Check Routes

Provides HTTP endpoints for session management health monitoring, alerting, and dashboard functionality.
"""

from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from models import UserRole
from session_health_checker import get_session_health_checker, SessionHealthStatus
from security.core.security_utils import sanitize_for_log

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

# Create blueprint for session health routes
session_health_bp = Blueprint('session_health', __name__, url_prefix='/admin/session-health')

@session_health_bp.route('/status')
@login_required
@admin_required
def health_status():
    """Get current session management health status."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return jsonify({
                'status': 'error',
                'message': 'Session management components not available'
            }), 500
        
        health_checker = get_session_health_checker(db_manager, session_manager)
        system_health = health_checker.check_comprehensive_session_health()
        
        return jsonify({
            'status': 'success',
            'data': health_checker.to_dict(system_health)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving session health status: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_health_bp.route('/component/<component_name>')
@login_required
@admin_required
def component_health(component_name):
    """Get health status for a specific session component."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return jsonify({
                'status': 'error',
                'message': 'Session management components not available'
            }), 500
        
        health_checker = get_session_health_checker(db_manager, session_manager)
        
        # Map component names to health check methods
        component_checks = {
            'database_sessions': health_checker.check_database_session_health,
            'session_monitoring': health_checker.check_session_monitoring_health,
            'platform_switching': health_checker.check_platform_switching_health,
            'session_cleanup': health_checker.check_session_cleanup_health,
            'session_security': health_checker.check_session_security_health
        }
        
        if component_name not in component_checks:
            return jsonify({
                'status': 'error',
                'message': f'Unknown component: {component_name}',
                'available_components': list(component_checks.keys())
            }), 404
        
        # Run specific component health check
        component_health = component_checks[component_name]()
        
        # Convert to dictionary
        health_dict = {
            'name': component_health.name,
            'status': component_health.status.value,
            'message': component_health.message,
            'response_time_ms': component_health.response_time_ms,
            'last_check': component_health.last_check.isoformat() if component_health.last_check else None,
            'details': component_health.details,
            'metrics': component_health.metrics
        }
        
        return jsonify({
            'status': 'success',
            'data': health_dict
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking component health for {sanitize_for_log(component_name)}: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_health_bp.route('/alerts')
@login_required
@admin_required
def health_alerts():
    """Get session management health alerts."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return jsonify({
                'status': 'error',
                'message': 'Session management components not available'
            }), 500
        
        health_checker = get_session_health_checker(db_manager, session_manager)
        system_health = health_checker.check_comprehensive_session_health()
        
        # Filter alerts by severity if requested
        severity_filter = request.args.get('severity')
        alerts = system_health.alerts
        
        if severity_filter:
            alerts = [alert for alert in alerts if alert['severity'] == severity_filter]
        
        # Sort alerts by severity (critical first)
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts,
                'summary': {
                    'total_alerts': len(system_health.alerts),
                    'critical_alerts': system_health.summary['critical_alerts'],
                    'warning_alerts': system_health.summary['warning_alerts'],
                    'filtered_count': len(alerts)
                },
                'overall_status': system_health.status.value,
                'timestamp': system_health.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving session health alerts: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_health_bp.route('/metrics')
@login_required
@admin_required
def health_metrics():
    """Get session management performance metrics."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return jsonify({
                'status': 'error',
                'message': 'Session management components not available'
            }), 500
        
        health_checker = get_session_health_checker(db_manager, session_manager)
        system_health = health_checker.check_comprehensive_session_health()
        
        # Extract metrics from all components
        metrics = {}
        for component_name, component in system_health.components.items():
            if component.metrics:
                metrics[component_name] = component.metrics
        
        # Add summary metrics
        metrics['summary'] = {
            'overall_status': system_health.status.value,
            'avg_response_time_ms': system_health.summary.get('avg_response_time_ms', 0),
            'healthy_components': system_health.summary['healthy_components'],
            'total_components': system_health.summary['total_components'],
            'health_percentage': (system_health.summary['healthy_components'] / system_health.summary['total_components']) * 100
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'metrics': metrics,
                'timestamp': system_health.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving session health metrics: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_health_bp.route('/dashboard')
@login_required
@admin_required
def health_dashboard():
    """Render session management health dashboard."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return render_template('errors/500.html', 
                                 error_message="Session management components not available"), 500
        
        health_checker = get_session_health_checker(db_manager, session_manager)
        system_health = health_checker.check_comprehensive_session_health()
        
        # Prepare data for template
        dashboard_data = {
            'system_health': health_checker.to_dict(system_health),
            'refresh_interval': 30,  # seconds
            'component_order': [
                'database_sessions',
                'session_monitoring', 
                'platform_switching',
                'session_cleanup',
                'session_security'
            ]
        }
        
        return render_template('admin/templates/session_health_dashboard.html',
                             dashboard_data=dashboard_data,
                             title="Session Management Health Dashboard")
        
    except Exception as e:
        current_app.logger.error(f"Error rendering session health dashboard: {sanitize_for_log(str(e))}")
        return render_template('errors/500.html', 
                             error_message=f"Dashboard error: {str(e)}"), 500

@session_health_bp.route('/health')
@login_required
@admin_required
def admin_health():
    """Admin-only health check endpoint for session management monitoring."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Session management components not available',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 503
        
        health_checker = get_session_health_checker(db_manager, session_manager)
        system_health = health_checker.check_comprehensive_session_health()
        
        # Determine HTTP status code
        if system_health.status == SessionHealthStatus.HEALTHY:
            status_code = 200
        elif system_health.status == SessionHealthStatus.DEGRADED:
            status_code = 200  # Still operational
        else:
            status_code = 503  # Service unavailable
        
        # Return minimal health information for public endpoint
        response_data = {
            'status': system_health.status.value,
            'timestamp': system_health.timestamp.isoformat(),
            'summary': {
                'total_components': system_health.summary['total_components'],
                'healthy_components': system_health.summary['healthy_components'],
                'total_alerts': system_health.summary['total_alerts'],
                'critical_alerts': system_health.summary['critical_alerts']
            }
        }
        
        # Add basic issues for degraded/unhealthy status
        if system_health.status != SessionHealthStatus.HEALTHY:
            response_data['issues'] = [
                alert['message'] for alert in system_health.alerts[:3]  # Top 3 issues
            ]
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in session health check: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': 'Health check failed',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@session_health_bp.route('/history')
@login_required
@admin_required
def health_history():
    """Get session health history (if available from monitoring)."""
    try:
        # Get health checker from app context
        db_manager = current_app.config.get('db_manager')
        session_manager = current_app.config.get('session_manager')
        
        if not db_manager or not session_manager:
            return jsonify({
                'status': 'error',
                'message': 'Session management components not available'
            }), 500
        
        # Get query parameters
        hours = request.args.get('hours', 24, type=int)
        component = request.args.get('component')
        
        # For now, return current status as history is not implemented
        # This could be extended to store historical health data
        health_checker = get_session_health_checker(db_manager, session_manager)
        current_health = health_checker.check_comprehensive_session_health()
        
        # Simulate historical data with current status
        history_data = {
            'period_hours': hours,
            'component_filter': component,
            'current_status': health_checker.to_dict(current_health),
            'historical_data': {
                'note': 'Historical health data not yet implemented',
                'suggestion': 'Consider implementing health data persistence for trending analysis'
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': history_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving session health history: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def register_session_health_routes(app):
    """Register session health routes with the Flask app."""
    # Store required components in app config for route access
    if hasattr(app, 'request_session_manager'):
        app.config['session_manager'] = getattr(app, 'session_manager', None)
        app.config['db_manager'] = getattr(app, 'db_manager', None)
    
    app.register_blueprint(session_health_bp)
    app.logger.info("Session health monitoring routes registered")