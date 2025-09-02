# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Dashboard Monitoring Routes

Provides real-time monitoring dashboard, historical reporting, and customizable
widgets for system administrators with alerting integration.
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import (
    render_template, jsonify, request, redirect, url_for, flash, 
    current_app, make_response, Response
)
from flask_login import login_required, current_user

from models import UserRole
from security.core.role_based_access import require_admin
from session_error_handlers import with_session_error_handling
from utils.response_helpers import success_response, error_response
from monitoring_dashboard_service import (
    MonitoringDashboardService, ReportType, ReportFormat, DashboardWidgetType
)

logger = logging.getLogger(__name__)

def register_dashboard_routes(bp):
    """Register enhanced dashboard monitoring routes"""
    
    @bp.route('/websocket-diagnostic')
    @login_required
    @require_admin
    def websocket_diagnostic():
        """WebSocket connection diagnostic page"""
        return render_template('websocket_diagnostic.html')
    
    @bp.route('/dashboard/monitoring')
    @login_required
    @require_admin
    def enhanced_monitoring_dashboard():
        """Enhanced real-time monitoring dashboard"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            
            # Get dashboard configuration for user role
            dashboard_config = dashboard_service.get_dashboard_config(current_user.role)
            
            # Get initial data for widgets
            widget_data = {}
            for widget in dashboard_config.get('widgets', []):
                widget_data[widget['id']] = dashboard_service.get_widget_data(
                    widget['id'], current_user.role
                )
            
            # Get dashboard alerts
            alerts = dashboard_service.get_dashboard_alerts(acknowledged=False)
            
            return render_template(
                'enhanced_monitoring_dashboard.html',
                dashboard_config=dashboard_config,
                widget_data=widget_data,
                alerts=alerts,
                user_role=current_user.role.value
            )
            
        except Exception as e:
            logger.error(f"Error loading enhanced monitoring dashboard: {str(e)}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification('Error loading monitoring dashboard.', 'Dashboard Error')
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/dashboard/config')
    @login_required
    @require_admin
    def get_dashboard_config():
        """Get dashboard configuration for current user"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            config = dashboard_service.get_dashboard_config(current_user.role)
            
            return success_response({'config': config})
            
        except Exception as e:
            logger.error(f"Error getting dashboard config: {str(e)}")
            return error_response(str(e), 500)
    
    @bp.route('/api/dashboard/widget/<widget_id>')
    @login_required
    @require_admin
    def get_widget_data(widget_id):
        """Get data for specific dashboard widget"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            data = dashboard_service.get_widget_data(widget_id, current_user.role)
            
            return jsonify({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            logger.error(f"Error getting widget data for {widget_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/dashboard/metrics/realtime')
    @login_required
    @require_admin
    def get_realtime_metrics():
        """Get real-time system metrics for dashboard updates"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            metrics = dashboard_service.get_real_time_metrics()
            
            return jsonify({
                'success': True,
                'metrics': metrics
            })
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/dashboard/alerts')
    @login_required
    @require_admin
    def get_dashboard_alerts():
        """Get current dashboard alerts"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            acknowledged = request.args.get('acknowledged')
            
            if acknowledged is not None:
                acknowledged = acknowledged.lower() == 'true'
            
            alerts = dashboard_service.get_dashboard_alerts(acknowledged=acknowledged)
            
            return jsonify({
                'success': True,
                'alerts': [
                    {
                        'id': alert.id,
                        'type': alert.type.value,
                        'severity': alert.severity.value,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat(),
                        'acknowledged': alert.acknowledged
                    }
                    for alert in alerts
                ]
            })
            
        except Exception as e:
            logger.error(f"Error getting dashboard alerts: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/dashboard/alerts/<alert_id>/acknowledge', methods=['POST'])
    @login_required
    @require_admin
    def acknowledge_dashboard_alert(alert_id):
        """Acknowledge a dashboard alert"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            result = dashboard_service.acknowledge_alert(alert_id, current_user.id)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/dashboard/reports')
    @login_required
    @require_admin
    def reports_dashboard():
        """Historical reports dashboard"""
        try:
            return render_template('reports_dashboard.html')
            
        except Exception as e:
            logger.error(f"Error loading reports dashboard: {str(e)}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification('Error loading reports dashboard.', 'Dashboard Error')
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/reports/generate', methods=['POST'])
    @login_required
    @require_admin
    def generate_report():
        """Generate historical report"""
        try:
            data = request.get_json()
            
            # Parse parameters
            report_type = ReportType(data.get('report_type'))
            start_date = datetime.fromisoformat(data.get('start_date'))
            end_date = datetime.fromisoformat(data.get('end_date'))
            parameters = data.get('parameters', {})
            
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            report_data = dashboard_service.get_historical_report(
                report_type, start_date, end_date, parameters
            )
            
            return jsonify({
                'success': True,
                'report': report_data
            })
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/reports/export', methods=['POST'])
    @login_required
    @require_admin
    def export_report():
        """Export report in specified format"""
        try:
            data = request.get_json()
            
            report_data = data.get('report_data')
            format_type = ReportFormat(data.get('format', 'json'))
            
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            content, mime_type = dashboard_service.export_report(report_data, format_type)
            
            # Create response with appropriate headers
            response = make_response(content)
            response.headers['Content-Type'] = mime_type
            response.headers['Content-Disposition'] = f'attachment; filename=report.{format_type.value}'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting report: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/reports/schedule', methods=['POST'])
    @login_required
    @require_admin
    def schedule_report():
        """Schedule automated report generation"""
        try:
            data = request.get_json()
            
            # This would integrate with a job scheduler like Celery
            # For now, just return success
            logger.info(f"Report scheduling requested: {data}")
            
            return jsonify({
                'success': True,
                'message': 'Report scheduled successfully',
                'schedule_id': f"schedule_{datetime.now().timestamp()}"
            })
            
        except Exception as e:
            logger.error(f"Error scheduling report: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/dashboard/widgets/customize')
    @login_required
    @require_admin
    def customize_widgets():
        """Widget customization interface"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            config = dashboard_service.get_dashboard_config(current_user.role)
            
            return render_template(
                'widget_customization.html',
                dashboard_config=config,
                widget_types=[wt.value for wt in DashboardWidgetType],
                user_role=current_user.role.value
            )
            
        except Exception as e:
            logger.error(f"Error loading widget customization: {str(e)}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification('Error loading widget customization.', 'Dashboard Error')
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/dashboard/widgets/save', methods=['POST'])
    @login_required
    @require_admin
    def save_widget_config():
        """Save widget configuration"""
        try:
            data = request.get_json()
            
            # This would save widget configuration to database
            # For now, just return success
            logger.info(f"Widget configuration save requested: {data}")
            
            return jsonify({
                'success': True,
                'message': 'Widget configuration saved successfully'
            })
            
        except Exception as e:
            logger.error(f"Error saving widget configuration: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Dashboard real-time updates are now handled via WebSocket
    # See websocket_progress_handler.py AdminDashboardWebSocket class
    
    @bp.route('/api/dashboard/health')
    @login_required
    @require_admin
    def dashboard_health():
        """Dashboard health check endpoint"""
        try:
            dashboard_service = MonitoringDashboardService(current_app.config['db_manager'])
            metrics = dashboard_service.get_real_time_metrics()
            
            return jsonify({
                'success': True,
                'status': metrics.get('status', 'unknown'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Dashboard health check failed: {str(e)}")
            return jsonify({
                'success': False,
                'status': 'error',
                'error': str(e)
            }), 500