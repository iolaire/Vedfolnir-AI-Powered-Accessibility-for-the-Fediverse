# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Dashboard Routes"""

from flask import render_template, current_app
from flask_login import login_required, current_user
from models import UserRole
from session_error_handlers import with_session_error_handling

def register_routes(bp):
    """Register dashboard routes"""
    
    @bp.route('/')
    @bp.route('/dashboard')
    @login_required
    @with_session_error_handling
    def dashboard():
        """Enhanced admin dashboard with multi-tenant caption management"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        db_manager = current_app.config['db_manager']
        
        # Get system overview stats
        with db_manager.get_session() as session:
            from models import User, PlatformConnection, Image, Post
            
            stats = {
                'total_users': session.query(User).count(),
                'active_users': session.query(User).filter_by(is_active=True).count(),
                'total_platforms': session.query(PlatformConnection).count(),
                'total_images': session.query(Image).count(),
                'total_posts': session.query(Post).count(),
            }
        
        # Get system metrics for multi-tenant management
        system_metrics = get_system_metrics(current_user.id)
        
        # Get active jobs for admin oversight
        active_jobs = get_active_jobs_for_admin(current_user.id)
        
        # Get system alerts
        system_alerts = get_system_alerts()
        
        # Get system configuration
        system_config = get_system_configuration()
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             system_metrics=system_metrics,
                             active_jobs=active_jobs,
                             system_alerts=system_alerts,
                             system_config=system_config)
    
    @bp.route('/configuration')
    @login_required
    @with_session_error_handling
    def configuration_management():
        """System configuration management page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('admin.dashboard'))
            
        return render_template('admin/configuration_management.html')
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             system_metrics=system_metrics,
                             active_jobs=active_jobs,
                             system_alerts=system_alerts,
                             system_config=system_config)

def get_system_metrics(admin_user_id):
    """Get system metrics for multi-tenant caption management"""
    try:
        # Import services
        from web_caption_generation_service import WebCaptionGenerationService
        from system_monitor import SystemMonitor
        
        # Get web caption generation service
        db_manager = current_app.config['db_manager']
        service = WebCaptionGenerationService(db_manager)
        
        # Get system metrics from the service
        metrics = service.get_system_metrics(admin_user_id)
        
        # Get additional metrics from system monitor
        monitor = SystemMonitor(db_manager)
        system_health = monitor.get_system_health()
        performance_metrics = monitor.get_performance_metrics()
        
        # Combine metrics
        combined_metrics = {
            'active_jobs': metrics.get('active_jobs', 0),
            'queued_jobs': metrics.get('queued_jobs', 0),
            'completed_today': metrics.get('completed_today', 0),
            'failed_jobs': metrics.get('failed_jobs', 0),
            'success_rate': metrics.get('success_rate', 0),
            'error_rate': metrics.get('error_rate', 0),
            'system_load': performance_metrics.get('cpu_usage_percent', 0),
            'avg_processing_time': metrics.get('avg_processing_time', 0)
        }
        
        return combined_metrics
        
    except Exception as e:
        current_app.logger.error(f"Error getting system metrics: {e}")
        return {
            'active_jobs': 0,
            'queued_jobs': 0,
            'completed_today': 0,
            'failed_jobs': 0,
            'success_rate': 0,
            'error_rate': 0,
            'system_load': 0,
            'avg_processing_time': 0
        }

def get_active_jobs_for_admin(admin_user_id):
    """Get active jobs for admin dashboard"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config['db_manager']
        service = WebCaptionGenerationService(db_manager)
        
        # Get all active jobs with admin access
        jobs = service.get_all_active_jobs(admin_user_id)
        
        # Format jobs for display
        formatted_jobs = []
        for job in jobs:
            formatted_job = {
                'task_id': job.get('task_id', ''),
                'username': job.get('username', 'Unknown'),
                'user_email': job.get('user_email', ''),
                'platform_type': job.get('platform_type', 'unknown'),
                'platform_name': job.get('platform_name', 'Unknown Platform'),
                'status': job.get('status', 'unknown'),
                'progress_percentage': job.get('progress_percentage', 0),
                'current_step': job.get('current_step', 'Initializing'),
                'created_at': job.get('created_at'),
                'estimated_completion': job.get('estimated_completion', 'Calculating...')
            }
            formatted_jobs.append(formatted_job)
        
        return formatted_jobs
        
    except Exception as e:
        current_app.logger.error(f"Error getting active jobs: {e}")
        return []

def get_system_alerts():
    """Get system alerts for admin dashboard"""
    try:
        from alert_manager import AlertManager
        
        db_manager = current_app.config['db_manager']
        alert_manager = AlertManager(db_manager)
        
        # Get active alerts
        alerts = alert_manager.get_active_alerts()
        
        # Format alerts for display
        formatted_alerts = []
        for alert in alerts:
            formatted_alert = {
                'id': alert.get('id', ''),
                'title': alert.get('title', 'System Alert'),
                'message': alert.get('message', ''),
                'severity': alert.get('severity', 'info'),
                'created_at': alert.get('created_at')
            }
            formatted_alerts.append(formatted_alert)
        
        return formatted_alerts
        
    except Exception as e:
        current_app.logger.error(f"Error getting system alerts: {e}")
        return []

def get_system_configuration():
    """Get system configuration for admin dashboard"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import SystemConfiguration
            
            # Get configuration values
            config = {}
            config_items = session.query(SystemConfiguration).all()
            
            for item in config_items:
                config[item.key] = item.value
            
            # Set defaults if not configured
            return {
                'max_concurrent_jobs': int(config.get('max_concurrent_jobs', 5)),
                'job_timeout_minutes': int(config.get('job_timeout_minutes', 30)),
                'max_retries': int(config.get('max_retries', 3)),
                'alert_threshold': int(config.get('alert_threshold', 80))
            }
        
    except Exception as e:
        current_app.logger.error(f"Error getting system configuration: {e}")
        return {
            'max_concurrent_jobs': 5,
            'job_timeout_minutes': 30,
            'max_retries': 3,
            'alert_threshold': 80
        }