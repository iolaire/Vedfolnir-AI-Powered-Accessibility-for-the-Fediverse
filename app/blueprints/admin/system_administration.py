# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin System Administration Routes"""

from flask import render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from models import UserRole
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.monitoring.system.system_monitor import SystemMonitor
from app.services.monitoring.performance.monitors.performance_monitor import get_performance_monitor
# Rate limiting will be handled by the security middleware
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def register_routes(bp):
    """Register system administration routes"""
    
    @bp.route('/system')
    @login_required
    def system_administration():
        """System Administration Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get consolidated monitoring framework components
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            performance_monitor = get_performance_monitor()
            
            # Get system health from consolidated monitoring framework
            system_health = system_monitor.get_system_health()
            
            # Get performance metrics from consolidated monitoring framework
            performance_metrics = system_monitor.get_performance_metrics()
            
            # Get resource usage from consolidated monitoring framework
            resource_usage = system_monitor.check_resource_usage()
            
            # Get error trends from consolidated monitoring framework
            error_trends = system_monitor.get_error_trends(hours=24)
            
            # Get performance summary from performance monitor
            performance_summary = performance_monitor.get_performance_summary()
            
            # Get recent performance metrics
            recent_metrics = performance_monitor.get_recent_metrics(limit=20)
            
            # Get stuck jobs detection
            stuck_jobs = system_monitor.detect_stuck_jobs()
            
            # Get queue wait time prediction
            predicted_wait_time = system_monitor.predict_queue_wait_time()
            
            # Prepare dashboard data
            dashboard_data = {
                'system_health': system_health.to_dict(),
                'performance_metrics': performance_metrics.to_dict(),
                'resource_usage': resource_usage.to_dict(),
                'error_trends': error_trends.to_dict(),
                'performance_summary': performance_summary,
                'recent_metrics': recent_metrics,
                'stuck_jobs': stuck_jobs,
                'predicted_wait_time': predicted_wait_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send success notification
            from app.services.notification.helpers.notification_helpers import send_success_notification
            send_success_notification("System administration dashboard loaded successfully", "Dashboard Loaded")
            
            return render_template('admin_system_administration.html', 
                                 dashboard_data=dashboard_data,
                                 current_user=current_user)
            
        except Exception as e:
            logger.error(f"Error loading system administration dashboard: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(f'Error loading system administration dashboard: {str(e)}', 'Dashboard Error')
            return jsonify({'error': 'Failed to load system administration dashboard'}), 500

    @bp.route('/system/api/health')
    @login_required
    def system_health_api():
        """System Health API Endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get system health from consolidated monitoring framework
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            system_health = system_monitor.get_system_health()
            
            return jsonify(system_health.to_dict())
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return jsonify({'error': 'Failed to get system health'}), 500

    @bp.route('/system/api/performance')
    @login_required
    def system_performance_api():
        """System Performance API Endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get performance metrics from consolidated monitoring framework
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            performance_metrics = system_monitor.get_performance_metrics()
            
            return jsonify(performance_metrics.to_dict())
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return jsonify({'error': 'Failed to get performance metrics'}), 500

    @bp.route('/system/api/resources')
    @login_required
    def system_resources_api():
        """System Resources API Endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get resource usage from consolidated monitoring framework
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            resource_usage = system_monitor.check_resource_usage()
            
            return jsonify(resource_usage.to_dict())
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return jsonify({'error': 'Failed to get resource usage'}), 500

    @bp.route('/system/api/errors')
    @login_required
    def system_errors_api():
        """System Error Trends API Endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get error trends from consolidated monitoring framework
            hours = request.args.get('hours', 24, type=int)
            if hours > 168:  # Limit to 7 days
                hours = 168
                
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            error_trends = system_monitor.get_error_trends(hours=hours)
            
            return jsonify(error_trends.to_dict())
            
        except Exception as e:
            logger.error(f"Error getting error trends: {e}")
            return jsonify({'error': 'Failed to get error trends'}), 500

    @bp.route('/system/api/stuck-jobs')
    @login_required
    def stuck_jobs_api():
        """Stuck Jobs Detection API Endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get stuck jobs from consolidated monitoring framework
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            stuck_jobs = system_monitor.detect_stuck_jobs()
            
            return jsonify({
                'stuck_jobs': stuck_jobs,
                'count': len(stuck_jobs),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error detecting stuck jobs: {e}")
            return jsonify({'error': 'Failed to detect stuck jobs'}), 500

    @bp.route('/system/api/queue-prediction')
    @login_required
    def queue_prediction_api():
        """Queue Wait Time Prediction API Endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get queue prediction from consolidated monitoring framework
            db_manager = current_app.config['db_manager']
            system_monitor = SystemMonitor(db_manager)
            predicted_wait_time = system_monitor.predict_queue_wait_time()
            
            return jsonify({
                'predicted_wait_time_seconds': predicted_wait_time,
                'predicted_wait_time_minutes': round(predicted_wait_time / 60, 1),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error predicting queue wait time: {e}")
            return jsonify({'error': 'Failed to predict queue wait time'}), 500