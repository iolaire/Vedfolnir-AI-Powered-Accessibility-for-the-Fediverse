# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Security Dashboard

Web interface for monitoring CSRF security metrics, violations, and compliance.
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user

from app.core.security.monitoring.csrf_security_metrics import get_csrf_security_metrics
from admin.security.admin_access_control import admin_required

logger = logging.getLogger(__name__)

# Create blueprint for CSRF dashboard
csrf_dashboard_bp = Blueprint('csrf_dashboard', __name__, url_prefix='/admin/security/csrf')

@csrf_dashboard_bp.route('/dashboard')
@login_required
@admin_required
def csrf_dashboard():
    """CSRF security dashboard page"""
    try:
        csrf_metrics = get_csrf_security_metrics()
        dashboard_data = csrf_metrics.get_csrf_dashboard_data()
        
        return render_template('csrf_security_dashboard.html', 
                             dashboard_data=dashboard_data,
                             page_title="CSRF Security Dashboard")
    
    except Exception as e:
        logger.error(f"Error loading CSRF dashboard: {e}")
        return render_template('errors/500.html'), 500

@csrf_dashboard_bp.route('/api/metrics')
@login_required
@admin_required
def csrf_metrics_api():
    """API endpoint for CSRF metrics data"""
    try:
        time_period = request.args.get('period', '24h')
        csrf_metrics = get_csrf_security_metrics()
        
        if time_period == 'dashboard':
            data = csrf_metrics.get_csrf_dashboard_data()
        else:
            compliance_metrics = csrf_metrics.get_compliance_metrics(time_period)
            data = {
                'compliance_metrics': {
                    'total_requests': compliance_metrics.total_requests,
                    'protected_requests': compliance_metrics.protected_requests,
                    'violation_count': compliance_metrics.violation_count,
                    'compliance_rate': compliance_metrics.compliance_rate,
                    'compliance_level': compliance_metrics.compliance_level.value,
                    'violations_by_type': compliance_metrics.violations_by_type,
                    'violations_by_endpoint': compliance_metrics.violations_by_endpoint,
                    'violations_by_ip': compliance_metrics.violations_by_ip,
                    'time_period': compliance_metrics.time_period,
                    'last_updated': compliance_metrics.last_updated.isoformat()
                }
            }
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error fetching CSRF metrics: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch CSRF metrics',
            'message': str(e)
        }), 500

@csrf_dashboard_bp.route('/api/violations')
@login_required
@admin_required
def csrf_violations_api():
    """API endpoint for recent CSRF violations"""
    try:
        limit = min(int(request.args.get('limit', 50)), 200)  # Max 200 violations
        csrf_metrics = get_csrf_security_metrics()
        
        # Get recent violations
        recent_violations = list(csrf_metrics.violations)[-limit:]
        
        violations_data = [
            {
                'event_id': v.event_id,
                'violation_type': v.violation_type.value,
                'timestamp': v.timestamp.isoformat(),
                'source_ip': v.source_ip,
                'user_id': v.user_id,
                'endpoint': v.endpoint,
                'user_agent': v.user_agent[:100],
                'session_id': v.session_id[:8] if v.session_id else 'unknown',
                'request_method': v.request_method,
                'error_details': v.error_details
            }
            for v in reversed(recent_violations)  # Most recent first
        ]
        
        return jsonify({
            'success': True,
            'violations': violations_data,
            'total_count': len(violations_data),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error fetching CSRF violations: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch CSRF violations',
            'message': str(e)
        }), 500

@csrf_dashboard_bp.route('/api/alerts')
@login_required
@admin_required
def csrf_alerts_api():
    """API endpoint for CSRF security alerts"""
    try:
        csrf_metrics = get_csrf_security_metrics()
        dashboard_data = csrf_metrics.get_csrf_dashboard_data()
        
        # Extract alert information
        alert_data = {
            'active_alerts': [],
            'alert_level': 'GREEN',
            'compliance_status': dashboard_data['compliance_metrics']['24h']['compliance_level'],
            'recent_violation_count': len(dashboard_data['recent_violations']),
            'top_violation_sources': dashboard_data['top_violation_ips'][:5]
        }
        
        # Check for alert conditions
        compliance_24h = dashboard_data['compliance_metrics']['24h']
        if compliance_24h['compliance_rate'] < 0.85:
            alert_data['active_alerts'].append({
                'type': 'low_compliance',
                'message': f"CSRF compliance rate is {compliance_24h['compliance_rate']:.1%}",
                'severity': 'MEDIUM'
            })
            alert_data['alert_level'] = 'YELLOW'
        
        if compliance_24h['violation_count'] > 50:
            alert_data['active_alerts'].append({
                'type': 'high_violations',
                'message': f"{compliance_24h['violation_count']} CSRF violations in last 24h",
                'severity': 'HIGH'
            })
            alert_data['alert_level'] = 'RED'
        
        return jsonify({
            'success': True,
            'alerts': alert_data,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error fetching CSRF alerts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch CSRF alerts',
            'message': str(e)
        }), 500

def register_csrf_dashboard(app):
    """Register CSRF dashboard with Flask app
    
    Args:
        app: Flask application instance
    """
    # Check if already registered to prevent duplicate registration
    if hasattr(app, '_csrf_dashboard_registered'):
        return
    
    app.register_blueprint(csrf_dashboard_bp)
    app._csrf_dashboard_registered = True
    logger.info("CSRF security dashboard registered")