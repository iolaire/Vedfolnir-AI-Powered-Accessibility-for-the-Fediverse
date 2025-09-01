# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
GDPR Routes

Routes for handling GDPR data subject rights and privacy management.
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, make_response, current_app
from flask_login import login_required, current_user
# from notification_flash_replacement import send_notification  # Removed - using unified notification system

from forms.gdpr_forms import (
    DataExportRequestForm, DataRectificationForm, DataErasureRequestForm,
    ConsentManagementForm, PrivacyRequestForm, GDPRComplianceReportForm,
    DataPortabilityForm
)

def validate_form_submission(form):
    """
    Manual form validation replacement for validate_on_submit()
    Since we're using regular WTForms instead of Flask-WTF
    """
    return request.method == 'POST' and form.validate()
from services.gdpr_service import GDPRDataSubjectService, GDPRPrivacyService
from services.user_management_service import UserProfileService
from request_scoped_session_manager import RequestScopedSessionManager
from models import UserAuditLog

logger = logging.getLogger(__name__)

# Create GDPR blueprint
gdpr_bp = Blueprint('gdpr', __name__, url_prefix='/gdpr')

def get_client_info():
    """Get client IP and user agent for audit logging"""
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
    user_agent = request.environ.get('HTTP_USER_AGENT', '')
    return ip_address, user_agent

@gdpr_bp.route('/data-export', methods=['GET', 'POST'])
@login_required
def data_export():
    """Handle personal data export requests (GDPR Article 20)"""
    form = DataExportRequestForm()
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                gdpr_service = GDPRDataSubjectService(db_session, current_app.config.get('BASE_URL', 'http://localhost:5000'))
                ip_address, user_agent = get_client_info()
            
            # Export personal data
            success, message, export_data = gdpr_service.export_personal_data(
                user_id=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success and export_data:
                # Filter data based on user preferences
                filtered_data = export_data.copy()
                
                if not form.include_activity_log.data:
                    filtered_data['personal_data'].pop('activity_log', None)
                
                if not form.include_content_data.data:
                    filtered_data['personal_data'].pop('content_data', None)
                
                if not form.include_platform_data.data:
                    filtered_data['personal_data'].pop('platform_connections', None)
                
                # Handle delivery method
                if form.delivery_method.data == 'download':
                    # Create downloadable response
                    if form.export_format.data == 'json':
                        response_data = json.dumps(filtered_data, indent=2, ensure_ascii=False)
                        mimetype = 'application/json'
                        filename = f'vedfolnir_data_export_{current_user.username}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
                    elif form.export_format.data == 'csv':
                        # Convert to CSV format (simplified)
                        response_data = gdpr_service._convert_to_csv(filtered_data)
                        mimetype = 'text/csv'
                        filename = f'vedfolnir_data_export_{current_user.username}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
                    else:  # XML
                        response_data = gdpr_service._convert_to_xml(filtered_data)
                        mimetype = 'application/xml'
                        filename = f'vedfolnir_data_export_{current_user.username}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.xml'
                    
                    response = make_response(response_data)
                    response.headers['Content-Type'] = mimetype
                    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    return response
                
                else:  # Email delivery
                    # Send email notification
                    email_success, email_message = gdpr_service.send_data_export_email(current_user, export_data)
                    
                    if email_success:
                        # Send success notification
                        from notification_helpers import send_success_notification
                        send_success_notification("Your data export has been completed. You will receive an email with instructions to access your data.", "Data Export Complete")
                        pass
                    else:
                        # Send warning notification
                        from notification_helpers import send_warning_notification
                        send_warning_notification("Data export completed, but we could not send the notification email. Please contact support.", "Email Notification Failed")
                
                # Store export data temporarily for download (if email delivery)
                        pass
                if form.delivery_method.data == 'email':
                    # In a real implementation, you might store this in a secure temporary location
                    # For now, we'll just show success message
                    pass
                
                # Send success notification
                from notification_helpers import send_success_notification
                send_success_notification("Your personal data export has been completed successfully.", "Data Export Complete")
                return redirect(url_for('gdpr.data_export'))
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification(f'Data export failed: {message}', 'Data Export Failed')
                
        except Exception as e:
            logger.error(f"Error processing data export request: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while processing your data export request.", "Processing Error")
    
    return render_template('gdpr/data_export.html', form=form)

@gdpr_bp.route('/data-rectification', methods=['GET', 'POST'])
@login_required
def data_rectification():
    """Handle data rectification requests (GDPR Article 16)"""
    form = DataRectificationForm()
    
    # Pre-populate form with current user data
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                gdpr_service = GDPRDataSubjectService(db_session)
                ip_address, user_agent = get_client_info()
                
                # Prepare rectification data
                rectification_data = {}
            
            if form.first_name.data != current_user.first_name:
                rectification_data['first_name'] = form.first_name.data
            
            if form.last_name.data != current_user.last_name:
                rectification_data['last_name'] = form.last_name.data
            
            if form.email.data != current_user.email:
                rectification_data['email'] = form.email.data
            
            if rectification_data:
                # Rectify personal data
                success, message, result = gdpr_service.rectify_personal_data(
                    user_id=current_user.id,
                    rectification_data=rectification_data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    # Send success notification
                    from notification_helpers import send_success_notification
                    send_success_notification("Your personal data has been rectified successfully.", "Data Updated")
                    if 'email' in rectification_data:
                        # Send info notification
                        from notification_helpers import send_info_notification
                        send_info_notification("Your email address has been updated and requires re-verification. Please check your new email for a verification link.", "Email Verification Required")
                        pass
                    return redirect(url_for('profile.profile'))
                else:
                    # Send error notification
                    from notification_helpers import send_error_notification
                    send_error_notification(f'Data rectification failed: {message}', 'Update Failed')
            else:
                # Send info notification
                from notification_helpers import send_info_notification
                send_info_notification("No changes were detected in your data.", "No Changes")
                pass
                
        except Exception as e:
            logger.error(f"Error processing data rectification request: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while processing your data rectification request.", "Processing Error")
    
    return render_template('gdpr/data_rectification.html', form=form)

@gdpr_bp.route('/data-erasure', methods=['GET', 'POST'])
@login_required
def data_erasure():
    """Handle data erasure requests (GDPR Article 17)"""
    form = DataErasureRequestForm()
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                gdpr_service = GDPRDataSubjectService(db_session)
                ip_address, user_agent = get_client_info()
                
                if form.erasure_type.data == 'complete':
                    # Complete data erasure
                    success, message, result = gdpr_service.erase_personal_data(
                        user_id=current_user.id,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                else:
                    # Data anonymization
                    success, message, result = gdpr_service.anonymize_personal_data(
                    user_id=current_user.id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            if success:
                # Send confirmation email before account deletion
                from services.email_service import email_service
                email_service.send_data_deletion_confirmation(
                    current_user.email, 
                    current_user.username,
                    form.erasure_type.data
                )
                
                # Send success notification
                from notification_helpers import send_success_notification
                send_success_notification("Your data erasure request has been processed successfully. You will receive a confirmation email.", "Account Deleted")
                
                # Log out user and redirect to home page
                from flask_login import logout_user
                logout_user()
                return redirect(url_for('main.index'))
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification(f'Data erasure failed: {message}', 'Deletion Failed')
                
        except Exception as e:
            logger.error(f"Error processing data erasure request: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while processing your data erasure request.", "Processing Error")
    
    return render_template('gdpr/data_erasure.html', form=form)

@gdpr_bp.route('/consent-management', methods=['GET', 'POST'])
@login_required
def consent_management():
    """Handle consent management (GDPR Article 7)"""
    form = ConsentManagementForm()
    
    # Pre-populate form with current consent status
    if request.method == 'GET':
        form.data_processing_consent.data = current_user.data_processing_consent
        # Add other consent fields as they are implemented
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                privacy_service = GDPRPrivacyService(db_session)
                ip_address, user_agent = get_client_info()
                
                # Update data processing consent
                if form.data_processing_consent.data != current_user.data_processing_consent:
                    success, message = privacy_service.record_consent(
                        user_id=current_user.id,
                        consent_type='data_processing',
                        consent_given=form.data_processing_consent.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if success:
                        # Send success notification
                        from notification_helpers import send_success_notification
                        send_success_notification(message, 'Consent Updated')
                        
                        # Send confirmation email for consent withdrawal
                        if not form.data_processing_consent.data:
                            from services.email_service import email_service
                            email_service.send_consent_withdrawal_confirmation(
                                current_user.email,
                                current_user.username,
                                current_app.config.get('BASE_URL', 'http://localhost:5000')
                            )
                    else:
                        from notification_helpers import send_error_notification
                        send_error_notification(f'Consent update failed: {message}', 'Update Failed')
            
            # Handle other consent types as they are implemented
            # (marketing, analytics, third-party sharing)
            
            return redirect(url_for('gdpr.consent_management'))
            
        except Exception as e:
            logger.error(f"Error processing consent management: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while updating your consent preferences.", "Processing Error")
    
    return render_template('gdpr/consent_management.html', form=form)

@gdpr_bp.route('/privacy-request', methods=['GET', 'POST'])
@login_required
def privacy_request():
    """Handle general privacy requests"""
    form = PrivacyRequestForm()
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                ip_address, user_agent = get_client_info()
            
            # Log the privacy request
            UserAuditLog.log_action(
                db_session,
                action="gdpr_privacy_request",
                user_id=current_user.id,
                details=f"Privacy request: {form.request_type.data} - {form.request_details.data[:100]}...",
                ip_address=ip_address,
                user_agent=user_agent
            )
            db_session.commit()
            
            # In a real implementation, this would create a support ticket
            # For now, we'll just log it and show a success message
            
            # Send success notification
            from notification_helpers import send_success_notification
            send_success_notification("Your privacy request has been submitted successfully. We will respond within 30 days as required by GDPR.", "Request Submitted")
            return redirect(url_for('gdpr.privacy_request'))
            
        except Exception as e:
            logger.error(f"Error processing privacy request: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while submitting your privacy request.", "Processing Error")
    
    return render_template('gdpr/privacy_request.html', form=form)

@gdpr_bp.route('/compliance-report', methods=['GET', 'POST'])
@login_required
def compliance_report():
    """Generate GDPR compliance report"""
    form = GDPRComplianceReportForm()
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                privacy_service = GDPRPrivacyService(db_session)
                
                if form.report_type.data == 'personal':
                    # Personal data report
                    gdpr_service = GDPRDataSubjectService(db_session)
                    success, message, report_data = gdpr_service.get_data_processing_info(current_user.id)
                elif form.report_type.data == 'consent':
                    # Consent history report
                    success, message, report_data = privacy_service.get_consent_history(current_user.id)
                elif form.report_type.data == 'compliance':
                    # Full compliance report
                    success, message, report_data = privacy_service.generate_privacy_report(current_user.id)
                else:
                    # Processing report
                    success, message, report_data = privacy_service.validate_gdpr_compliance(current_user.id)
                
                if success and report_data:
                    # Return JSON response for download
                    response_data = json.dumps(report_data, indent=2, ensure_ascii=False)
                    response = make_response(response_data)
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['Content-Disposition'] = f'attachment; filename="gdpr_report_{form.report_type.data}_{current_user.username}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json"'
                    
                    return response
                else:
                    from notification_helpers import send_error_notification
                    send_error_notification(f'Report generation failed: {message}', 'Report Generation Failed')
                
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while generating your compliance report.", "Processing Error")
    
    return render_template('gdpr/privacy_request.html', form=form)

@gdpr_bp.route('/data-portability', methods=['GET', 'POST'])
@login_required
def data_portability():
    """Handle data portability requests (GDPR Article 20)"""
    form = DataPortabilityForm()
    
    if validate_form_submission(form):
        try:
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                gdpr_service = GDPRDataSubjectService(db_session, current_app.config.get('BASE_URL', 'http://localhost:5000'))
                ip_address, user_agent = get_client_info()
                
                # Export data for portability
            success, message, export_data = gdpr_service.export_personal_data(
                user_id=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success and export_data:
                # Filter data based on categories
                if form.data_categories.data == 'profile':
                    filtered_data = {'personal_data': {'user_profile': export_data['personal_data']['user_profile']}}
                elif form.data_categories.data == 'content':
                    filtered_data = {'personal_data': {'content_data': export_data['personal_data'].get('content_data', {})}}
                elif form.data_categories.data == 'activity':
                    filtered_data = {'personal_data': {'activity_log': export_data['personal_data'].get('activity_log', [])}}
                else:
                    filtered_data = export_data
                
                # Add portability-specific metadata
                filtered_data['portability_info'] = {
                    'export_purpose': 'data_portability',
                    'gdpr_article': 'Article 20',
                    'destination_service': form.destination_service.data,
                    'export_format': form.export_format.data,
                    'structured_data': True,
                    'machine_readable': True
                }
                
                # Create response based on format
                if form.export_format.data == 'json':
                    response_data = json.dumps(filtered_data, indent=2, ensure_ascii=False)
                    mimetype = 'application/json'
                    extension = 'json'
                elif form.export_format.data == 'csv':
                    response_data = gdpr_service._convert_to_csv(filtered_data)
                    mimetype = 'text/csv'
                    extension = 'csv'
                elif form.export_format.data == 'xml':
                    response_data = gdpr_service._convert_to_xml(filtered_data)
                    mimetype = 'application/xml'
                    extension = 'xml'
                else:
                    # Send warning notification
                    from notification_helpers import send_warning_notification
                    send_warning_notification("API transfer not yet implemented. Please use download format.", "Feature Not Available")
                    return redirect(url_for('gdpr.data_portability'))
                
                filename = f'vedfolnir_portable_data_{current_user.username}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.{extension}'
                
                response = make_response(response_data)
                response.headers['Content-Type'] = mimetype
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                return response
            else:
                from notification_helpers import send_error_notification
                send_error_notification(f'Data portability export failed: {message}', 'Export Failed')
                
        except Exception as e:
            logger.error(f"Error processing data portability request: {e}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while processing your data portability request.", "Processing Error")
    
    return render_template('gdpr/data_export.html', form=form)

@gdpr_bp.route('/privacy-policy')
def privacy_policy():
    """Display privacy policy and data processing information"""
    return render_template('gdpr/privacy_policy.html')

@gdpr_bp.route('/data-processing-info')
@login_required
def data_processing_info():
    """Display data processing information for the user"""
    try:
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            gdpr_service = GDPRDataSubjectService(db_session)
            
            success, message, processing_info = gdpr_service.get_data_processing_info(current_user.id)
            
            if success:
                return render_template('gdpr/privacy_policy.html', processing_info=processing_info)
            else:
                from notification_helpers import send_error_notification
                send_error_notification(f'Could not retrieve data processing information: {message}', 'Information Retrieval Failed')
                return redirect(url_for('profile.profile'))
            
    except Exception as e:
        logger.error(f"Error retrieving data processing info: {e}")
        # Send error notification
        from notification_helpers import send_error_notification
        send_error_notification("An error occurred while retrieving data processing information.", "Processing Error")
        return redirect(url_for('profile.profile'))

@gdpr_bp.route('/rights-overview')
def rights_overview():
    """Display overview of GDPR rights"""
    return render_template('gdpr/rights_overview.html')