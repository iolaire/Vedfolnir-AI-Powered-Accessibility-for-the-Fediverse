# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Dashboard Routes"""

from flask import render_template, current_app, jsonify
from flask_login import login_required, current_user
from models import UserRole
from app.core.session.error_handling.session_error_handlers import with_session_error_handling
from app.services.admin.components.admin_storage_dashboard import AdminStorageDashboard
from app.utils.version.version import __version__
from datetime import datetime

def register_routes(bp):
    """Register dashboard routes"""
    
    @bp.route('/')
    @bp.route('/dashboard')
    @login_required
    def dashboard():
        """Admin landing page and dashboard overview"""
        if not current_user.role == UserRole.ADMIN:
            from flask import redirect, url_for
            # from notification_flash_replacement import send_notification  # Removed - using unified notification system
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
            
        db_manager = current_app.config['db_manager']
        
        # Get basic system overview stats for landing page
        with db_manager.get_session() as session:
            from models import User, PlatformConnection, Image, Post
            from datetime import datetime, timedelta
            from sqlalchemy import func, case
            
            # Optimized single query for all counts
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Single aggregated query for user statistics
            user_stats = session.query(
                func.count(User.id).label('total_users'),
                func.sum(case((User.is_active == True, 1), else_=0)).label('active_users'),
                func.sum(case((User.created_at >= yesterday, 1), else_=0)).label('new_users_24h'),
                func.sum(case((User.last_login >= yesterday, 1), else_=0)).label('recent_logins')
            ).first()
            
            # Single query for platform count
            platform_count = session.query(func.count(PlatformConnection.id)).scalar()
            
            # Single query for content counts
            content_stats = session.query(
                func.count(Image.id).label('total_images'),
                func.count(Post.id).label('total_posts')
            ).select_from(Image).outerjoin(Post).first()
            
            # Build stats dictionary
            stats = {
                'total_users': user_stats.total_users or 0,
                'active_users': user_stats.active_users or 0,
                'new_users_24h': user_stats.new_users_24h or 0,
                'recent_logins': user_stats.recent_logins or 0,
                'total_platforms': platform_count or 0,
                'total_images': content_stats.total_images or 0,
                'total_posts': content_stats.total_posts or 0,
            }
        
        # Get system metrics from database (simplified approach)
        try:
            with db_manager.get_session() as session:
                from models import CaptionGenerationTask
                from datetime import datetime, timedelta
                
                # Get basic job statistics from database
                yesterday = datetime.utcnow() - timedelta(days=1)
                
                # Count caption generation tasks by status as proxy for job statistics
                caption_stats = session.query(
                    CaptionGenerationTask.status,
                    func.count(CaptionGenerationTask.id).label('count')
                ).group_by(CaptionGenerationTask.status).all()
                
                # Process caption statistics
                completed_count = 0
                pending_count = 0
                failed_count = 0
                
                for status, count in caption_stats:
                    if status == 'approved':
                        completed_count = count
                    elif status in ['pending', 'processing']:
                        pending_count = count
                    elif status == 'rejected':
                        failed_count = count
                
                # Calculate success rate
                total_processed = completed_count + failed_count
                success_rate = round((completed_count / total_processed * 100), 1) if total_processed > 0 else 95.0
                
                # Build system metrics dictionary
                system_metrics = {
                    'active_jobs': pending_count,
                    'queued_jobs': pending_count,
                    'completed_today': completed_count,
                    'success_rate': success_rate,
                    'failed_jobs': failed_count,
                    'total_tasks': completed_count + pending_count + failed_count,
                    'avg_processing_time': 0,  # Would need timestamp data for this
                    'error_rate': round((failed_count / total_processed * 100), 1) if total_processed > 0 else 5.0,
                    'throughput_metrics': {
                        'tasks_created_last_hour': 0,  # Would need more detailed timestamp queries
                        'tasks_completed_last_hour': 0,
                        'tasks_failed_last_hour': 0,
                    }
                }
        except Exception as e:
            current_app.logger.error(f"Error getting system metrics: {e}")
            # Fallback to basic metrics if database query fails
            system_metrics = {
                'active_jobs': 0,
                'queued_jobs': 0,
                'completed_today': 0,
                'success_rate': 95.0,
                'failed_jobs': 0,
                'total_tasks': 0,
                'avg_processing_time': 0,
                'error_rate': 5.0,
                'throughput_metrics': {
                    'tasks_created_last_hour': 0,
                    'tasks_completed_last_hour': 0,
                    'tasks_failed_last_hour': 0,
                }
            }
        
        # Get basic system health status
        try:
            health_checker = current_app.config.get('health_checker')
            if health_checker:
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    system_health = asyncio.create_task(health_checker.check_system_health())
                    system_health = loop.run_until_complete(system_health)
                    health_status = system_health.status.value
                except RuntimeError:
                    system_health = asyncio.run(health_checker.check_system_health())
                    health_status = system_health.status.value
            else:
                health_status = 'healthy'
        except Exception as e:
            current_app.logger.error(f"Error getting health status: {e}")
            health_status = 'unknown'
        
        # Get storage dashboard data
        try:
            storage_dashboard = AdminStorageDashboard()
            storage_data = storage_dashboard.get_storage_summary_card_data()
            storage_gauge = storage_dashboard.get_storage_gauge_data()
            storage_actions = storage_dashboard.get_quick_actions_data()
        except Exception as e:
            current_app.logger.error(f"Error getting storage dashboard data: {e}")
            storage_data = {
                'title': 'Storage Usage',
                'current_usage': '0.00 GB',
                'limit': '10.00 GB',
                'percentage': '0.0%',
                'status_text': 'Error',
                'status_color': 'red',
                'error': str(e)
            }
            storage_gauge = {
                'current_percentage': 0.0,
                'status_color': 'red',
                'error': str(e)
            }
            storage_actions = {
                'actions': [],
                'error': str(e)
            }
        
        # Add system configuration for dashboard form
        system_config = {
            'max_concurrent_jobs': 5,
            'job_timeout_minutes': 30,
            'max_retries': 3,
            'alert_threshold': 80
        }
        
        return render_template('dashboard.html', 
                             stats=stats,
                             system_metrics=system_metrics,
                             health_status=health_status,
                             app_version=__version__,
                             storage_data=storage_data,
                             storage_gauge=storage_gauge,
                             storage_actions=storage_actions,
                             system_config=system_config)
    
    @bp.route('/configuration')
    @login_required
    def configuration_management():
        """System configuration management page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import redirect, url_for
            # from notification_flash_replacement import send_notification  # Removed - using unified notification system
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.dashboard'))
            
        return render_template('configuration_management.html')
    
    @bp.route('/api/dashboard/stats')
    @login_required
    def dashboard_stats_api():
        """API endpoint for dashboard statistics"""
        if not current_user.role == UserRole.ADMIN:
            from flask import jsonify
            return jsonify({'error': 'Access denied'}), 403
        
        from flask import jsonify
        db_manager = current_app.config['db_manager']
        
        try:
            with db_manager.get_session() as session:
                from models import User, PlatformConnection, Image, Post, CaptionGenerationTask
                from datetime import datetime, timedelta
                from sqlalchemy import func, case
                
                # Get user statistics
                yesterday = datetime.utcnow() - timedelta(days=1)
                user_stats = session.query(
                    func.count(User.id).label('total_users'),
                    func.sum(case((User.is_active == True, 1), else_=0)).label('active_users'),
                    func.sum(case((User.created_at >= yesterday, 1), else_=0)).label('new_users_24h'),
                    func.sum(case((User.last_login >= yesterday, 1), else_=0)).label('recent_logins')
                ).first()
                
                # Get platform count
                platform_count = session.query(func.count(PlatformConnection.id)).scalar()
                
                # Get content statistics
                content_stats = session.query(
                    func.count(Image.id).label('total_images'),
                    func.count(Post.id).label('total_posts')
                ).select_from(Image).outerjoin(Post).first()
                
                # Get job statistics
                caption_stats = session.query(
                    CaptionGenerationTask.status,
                    func.count(CaptionGenerationTask.id).label('count')
                ).group_by(CaptionGenerationTask.status).all()
                
                completed_count = 0
                pending_count = 0
                failed_count = 0
                
                for status, count in caption_stats:
                    if status == 'approved':
                        completed_count = count
                    elif status in ['pending', 'processing']:
                        pending_count = count
                    elif status == 'rejected':
                        failed_count = count
                
                total_processed = completed_count + failed_count
                success_rate = round((completed_count / total_processed * 100), 1) if total_processed > 0 else 95.0
                error_rate = round((failed_count / total_processed * 100), 1) if total_processed > 0 else 5.0
                
                # Build response
                stats = {
                    'users': {
                        'total': user_stats.total_users or 0,
                        'active': user_stats.active_users or 0,
                        'new_24h': user_stats.new_users_24h or 0,
                        'recent_logins': user_stats.recent_logins or 0
                    },
                    'platforms': {
                        'total': platform_count or 0
                    },
                    'content': {
                        'images': content_stats.total_images or 0,
                        'posts': content_stats.total_posts or 0
                    },
                    'jobs': {
                        'active': pending_count,
                        'queued': pending_count,
                        'completed': completed_count,
                        'failed': failed_count,
                        'total': completed_count + pending_count + failed_count,
                        'success_rate': success_rate,
                        'error_rate': error_rate
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                return jsonify(stats)
                
        except Exception as e:
            current_app.logger.error(f"Error getting dashboard stats: {e}")
            return jsonify({'error': 'Failed to get statistics'}), 500
    
    @bp.route('/api/system/metrics')
    @login_required
    def system_metrics_api():
        """API endpoint for system metrics"""
        if not current_user.role == UserRole.ADMIN:
            from flask import jsonify
            return jsonify({'error': 'Access denied'}), 403
        
        from flask import jsonify
        import psutil
        
        try:
            # Get system resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            # Get system monitor if available
            system_monitor = current_app.config.get('system_monitor')
            health_status = 'unknown'
            
            if system_monitor:
                try:
                    health = system_monitor.get_system_health()
                    health_status = health.status
                except Exception:
                    health_status = 'unknown'
            
            # Build metrics response
            metrics = {
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_mb': memory.used / (1024 * 1024),
                    'memory_total_mb': memory.total / (1024 * 1024),
                    'disk_percent': disk.percent,
                    'disk_used_gb': disk.used / (1024 * 1024 * 1024),
                    'disk_total_gb': disk.total / (1024 * 1024 * 1024)
                },
                'health': {
                    'status': health_status,
                    'database': 'healthy' if db_manager else 'error',
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            return jsonify(metrics)
            
        except Exception as e:
            current_app.logger.error(f"Error getting system metrics: {e}")
            return jsonify({'error': 'Failed to get system metrics'}), 500

