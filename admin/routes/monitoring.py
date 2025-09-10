# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Monitoring Routes"""

from flask import render_template, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole
from app.utils.helpers.response_helpers import success_response, error_response
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from app.core.session.error_handling.session_error_handlers import with_session_error_handling
from app.core.security.core.security_middleware import rate_limit

def register_routes(bp):
    """Register monitoring routes"""
    
    @bp.route('/monitoring')
    @login_required
    def monitoring_dashboard():
        """Administrative monitoring dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
            
        try:
            from ..services.monitoring_service import AdminMonitoringService
            monitoring_service = AdminMonitoringService(current_app.config['db_manager'])
            
            system_overview = monitoring_service.get_system_overview()
            active_tasks = monitoring_service.get_active_tasks(limit=20)
            performance_metrics = monitoring_service.get_performance_metrics(days=7)
            
            return render_template('admin_monitoring.html',
                                 system_overview=system_overview,
                                 active_tasks=active_tasks,
                                 performance_metrics=performance_metrics)
                                 
        except Exception as e:
            current_app.logger.error(f"Error loading monitoring dashboard: {str(e)}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Error loading monitoring dashboard.", "Error")
            return redirect(url_for('admin.dashboard'))

    @bp.route('/api/system_overview')
    @login_required
    @rate_limit(limit=30, window_seconds=60)
    def api_system_overview():
        """Get real-time system overview"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            from ..services.monitoring_service import AdminMonitoringService
            monitoring_service = AdminMonitoringService(current_app.config['db_manager'])
            overview = monitoring_service.get_system_overview()
            return success_response({'overview': overview})
        except Exception as e:
            return error_response(str(e), 500)

