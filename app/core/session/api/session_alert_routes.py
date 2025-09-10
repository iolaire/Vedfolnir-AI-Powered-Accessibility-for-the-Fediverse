# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Alert Routes

Provides HTTP endpoints for managing session management alerts including
acknowledgment, resolution, and alert rule configuration.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timezone

from models import UserRole
from session_alerting_system import AlertSeverity, AlertStatus
from app.core.security.core.security_utils import sanitize_for_log

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

# Create blueprint for session alert routes
session_alert_bp = Blueprint('session_alerts', __name__, url_prefix='/admin/session-alerts')

@session_alert_bp.route('/active')
@login_required
@admin_required
def get_active_alerts():
    """Get active session management alerts."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Get query parameters
        severity_filter = request.args.get('severity')
        severity = None
        if severity_filter:
            try:
                severity = AlertSeverity(severity_filter.lower())
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid severity: {severity_filter}'
                }), 400
        
        # Check for new alerts first
        new_alerts = alerting_system.check_alerts()
        
        # Get active alerts
        active_alerts = alerting_system.get_active_alerts(severity)
        
        # Convert to dictionaries
        alerts_data = []
        for alert in active_alerts:
            alert_dict = alerting_system._alert_to_dict(alert)
            alerts_data.append(alert_dict)
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts_data,
                'new_alerts_count': len(new_alerts),
                'total_count': len(alerts_data),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting active alerts: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/summary')
@login_required
@admin_required
def get_alert_summary():
    """Get alert summary statistics."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Check for new alerts first
        alerting_system.check_alerts()
        
        # Get summary
        summary = alerting_system.get_alert_summary()
        
        return jsonify({
            'status': 'success',
            'data': {
                'summary': summary,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting alert summary: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/<alert_id>/acknowledge', methods=['POST'])
@login_required
@admin_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Acknowledge the alert
        success = alerting_system.acknowledge_alert(alert_id, current_user.username)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Alert acknowledged successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Alert not found or could not be acknowledged'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error acknowledging alert {sanitize_for_log(alert_id)}: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/<alert_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_alert(alert_id):
    """Manually resolve an alert."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Resolve the alert
        success = alerting_system.resolve_alert(alert_id, current_user.username)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Alert resolved successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Alert not found or could not be resolved'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error resolving alert {sanitize_for_log(alert_id)}: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/rules')
@login_required
@admin_required
def get_alert_rules():
    """Get alert rules configuration."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Get alert rules
        rules_data = []
        for rule in alerting_system.alert_rules:
            rule_dict = {
                'name': rule.name,
                'component': rule.component,
                'metric': rule.metric,
                'condition': rule.condition,
                'threshold': rule.threshold,
                'severity': rule.severity.value,
                'duration_seconds': rule.duration_seconds,
                'cooldown_seconds': rule.cooldown_seconds,
                'enabled': rule.enabled
            }
            rules_data.append(rule_dict)
        
        return jsonify({
            'status': 'success',
            'data': {
                'rules': rules_data,
                'total_rules': len(rules_data),
                'enabled_rules': len([r for r in alerting_system.alert_rules if r.enabled])
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting alert rules: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/rules/<rule_name>/enable', methods=['POST'])
@login_required
@admin_required
def enable_alert_rule(rule_name):
    """Enable an alert rule."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        success = alerting_system.enable_alert_rule(rule_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Alert rule "{rule_name}" enabled successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Alert rule "{rule_name}" not found'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error enabling alert rule {sanitize_for_log(rule_name)}: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/rules/<rule_name>/disable', methods=['POST'])
@login_required
@admin_required
def disable_alert_rule(rule_name):
    """Disable an alert rule."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        success = alerting_system.disable_alert_rule(rule_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Alert rule "{rule_name}" disabled successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Alert rule "{rule_name}" not found'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error disabling alert rule {sanitize_for_log(rule_name)}: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/rules/<rule_name>/update', methods=['PUT'])
@login_required
@admin_required
def update_alert_rule(rule_name):
    """Update an alert rule configuration."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Validate and sanitize update data
        allowed_fields = ['threshold', 'duration_seconds', 'cooldown_seconds', 'enabled']
        update_data = {}
        
        for field in allowed_fields:
            if field in data:
                value = data[field]
                
                # Type validation
                if field in ['threshold'] and not isinstance(value, (int, float)):
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid type for {field}: must be numeric'
                    }), 400
                
                if field in ['duration_seconds', 'cooldown_seconds'] and not isinstance(value, int):
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid type for {field}: must be integer'
                    }), 400
                
                if field == 'enabled' and not isinstance(value, bool):
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid type for {field}: must be boolean'
                    }), 400
                
                # Range validation
                if field in ['duration_seconds', 'cooldown_seconds'] and value < 0:
                    return jsonify({
                        'status': 'error',
                        'message': f'{field} must be non-negative'
                    }), 400
                
                update_data[field] = value
        
        if not update_data:
            return jsonify({
                'status': 'error',
                'message': 'No valid fields to update'
            }), 400
        
        success = alerting_system.update_alert_rule(rule_name, **update_data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Alert rule "{rule_name}" updated successfully',
                'updated_fields': list(update_data.keys())
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Alert rule "{rule_name}" not found'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Error updating alert rule {sanitize_for_log(rule_name)}: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/export')
@login_required
@admin_required
def export_alerts():
    """Export alerts for external analysis."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Get query parameters
        include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
        
        # Export alerts
        alerts_data = alerting_system.export_alerts(include_resolved=include_resolved)
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts_data,
                'export_timestamp': datetime.now(timezone.utc).isoformat(),
                'include_resolved': include_resolved,
                'total_count': len(alerts_data)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error exporting alerts: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@session_alert_bp.route('/test')
@login_required
@admin_required
def test_alerting():
    """Test the alerting system by checking for alerts."""
    try:
        alerting_system = current_app.config.get('session_alerting_system')
        if not alerting_system:
            return jsonify({
                'status': 'error',
                'message': 'Alerting system not available'
            }), 500
        
        # Force alert check
        new_alerts = alerting_system.check_alerts()
        
        # Get current status
        summary = alerting_system.get_alert_summary()
        
        return jsonify({
            'status': 'success',
            'data': {
                'test_completed': True,
                'new_alerts_found': len(new_alerts),
                'current_summary': summary,
                'test_timestamp': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error testing alerting system: {sanitize_for_log(str(e))}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def register_session_alert_routes(app):
    """Register session alert routes with the Flask app."""
    app.register_blueprint(session_alert_bp)
    app.logger.info("Session alert management routes registered")