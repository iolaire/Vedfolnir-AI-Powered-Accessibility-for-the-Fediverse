from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

gdpr_bp = Blueprint('gdpr', __name__, url_prefix='/gdpr')

@gdpr_bp.route('/privacy_policy')
def privacy_policy():
    """Privacy policy page"""
    return render_template('gdpr/privacy_policy.html')

@gdpr_bp.route('/privacy_request')
@login_required
def privacy_request():
    """Privacy request form"""
    return render_template('gdpr/privacy_request.html')

@gdpr_bp.route('/consent_management')
@login_required
def consent_management():
    """Consent management page"""
    return render_template('gdpr/consent_management.html')

@gdpr_bp.route('/data_export')
@login_required
def data_export():
    """Data export page"""
    return render_template('gdpr/data_export.html')

@gdpr_bp.route('/data_erasure')
@login_required
def data_erasure():
    """Data erasure page"""
    return render_template('gdpr/data_erasure.html')

@gdpr_bp.route('/data_rectification')
@login_required
def data_rectification():
    """Data rectification page"""
    return render_template('gdpr/data_rectification.html')

@gdpr_bp.route('/data_portability')
@login_required
def data_portability():
    """Data portability page"""
    return redirect(url_for('gdpr.data_export'))

@gdpr_bp.route('/data_processing_info')
def data_processing_info():
    """Data processing information"""
    return redirect(url_for('gdpr.privacy_policy'))

@gdpr_bp.route('/compliance_report')
@login_required
def compliance_report():
    """GDPR compliance report"""
    return render_template('gdpr/rights_overview.html')
