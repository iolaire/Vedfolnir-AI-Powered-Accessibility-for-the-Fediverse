# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Audit Dashboard

Web interface for security audit reporting, vulnerability tracking,
and compliance monitoring.
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user

from security.reporting.security_audit_system import get_security_audit_system, VulnerabilityStatus
from security.core.security_utils import admin_required

logger = logging.getLogger(__name__)

audit_dashboard_bp = Blueprint('audit_dashboard', __name__, url_prefix='/admin/security/audit')

@audit_dashboard_bp.route('/dashboard')
@login_required
@admin_required
def audit_dashboard():
    """Security audit dashboard page"""
    try:
        audit_system = get_security_audit_system()
        
        # Get dashboard data
        vulnerability_data = audit_system.get_vulnerability_dashboard_data()
        compliance_data = audit_system.get_compliance_dashboard_data()
        remediation_data = audit_system.generate_remediation_report()
        
        return render_template('admin/templates/security_audit_dashboard.html',
                             vulnerability_data=vulnerability_data,
                             compliance_data=compliance_data,
                             remediation_data=remediation_data,
                             page_title="Security Audit Dashboard")
    
    except Exception as e:
        logger.error(f"Error loading audit dashboard: {e}")
        # Send error notification
        from notification_helpers import send_error_notification
        send_error_notification('Error loading security audit dashboard', 'Dashboard Error')
        return redirect(url_for('main.index'))

@audit_dashboard_bp.route('/api/generate-report')
@login_required
@admin_required
def generate_audit_report():
    """Generate new comprehensive audit report"""
    try:
        scope = request.args.get('scope', 'full')
        audit_system = get_security_audit_system()
        
        report = audit_system.generate_comprehensive_audit_report(scope)
        
        return jsonify({
            'success': True,
            'report_id': report.report_id,
            'overall_score': report.overall_score,
            'risk_level': report.risk_level,
            'vulnerabilities_found': report.vulnerabilities_found,
            'compliance_rate': report.compliance_rate,
            'recommendations': report.recommendations,
            'generated_at': report.generated_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error generating audit report: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate audit report',
            'message': str(e)
        }), 500

@audit_dashboard_bp.route('/api/vulnerabilities')
@login_required
@admin_required
def get_vulnerabilities():
    """Get vulnerability data"""
    try:
        audit_system = get_security_audit_system()
        data = audit_system.get_vulnerability_dashboard_data()
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error fetching vulnerabilities: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch vulnerabilities',
            'message': str(e)
        }), 500

@audit_dashboard_bp.route('/api/compliance')
@login_required
@admin_required
def get_compliance_data():
    """Get compliance data"""
    try:
        audit_system = get_security_audit_system()
        data = audit_system.get_compliance_dashboard_data()
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error fetching compliance data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch compliance data',
            'message': str(e)
        }), 500

@audit_dashboard_bp.route('/api/remediation')
@login_required
@admin_required
def get_remediation_data():
    """Get remediation progress data"""
    try:
        audit_system = get_security_audit_system()
        data = audit_system.generate_remediation_report()
        
        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error fetching remediation data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch remediation data',
            'message': str(e)
        }), 500

@audit_dashboard_bp.route('/api/vulnerability/<vulnerability_id>/update', methods=['POST'])
@login_required
@admin_required
def update_vulnerability(vulnerability_id):
    """Update vulnerability status"""
    try:
        data = request.get_json()
        status = VulnerabilityStatus(data.get('status'))
        resolution_notes = data.get('resolution_notes')
        assigned_to = data.get('assigned_to')
        
        audit_system = get_security_audit_system()
        success = audit_system.update_vulnerability_status(
            vulnerability_id, status, resolution_notes, assigned_to
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Vulnerability updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Vulnerability not found'
            }), 404
    
    except Exception as e:
        logger.error(f"Error updating vulnerability: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update vulnerability',
            'message': str(e)
        }), 500

@audit_dashboard_bp.route('/api/vulnerability/track', methods=['POST'])
@login_required
@admin_required
def track_new_vulnerability():
    """Track a new vulnerability"""
    try:
        data = request.get_json()
        
        vulnerability_id = get_security_audit_system().track_vulnerability(
            vulnerability_type=data.get('type'),
            severity=data.get('severity'),
            description=data.get('description'),
            affected_component=data.get('component'),
            assigned_to=data.get('assigned_to')
        )
        
        return jsonify({
            'success': True,
            'vulnerability_id': vulnerability_id,
            'message': 'Vulnerability tracked successfully'
        })
    
    except Exception as e:
        logger.error(f"Error tracking vulnerability: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to track vulnerability',
            'message': str(e)
        }), 500

def register_audit_dashboard(app):
    """Register audit dashboard with Flask app"""
    app.register_blueprint(audit_dashboard_bp)
    logger.info("Security audit dashboard registered")