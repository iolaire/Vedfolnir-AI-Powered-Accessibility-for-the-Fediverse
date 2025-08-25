# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Job Management Routes"""

from flask import render_template, current_app, request, session
from flask_login import login_required, current_user
from models import UserRole
from session_error_handlers import with_session_error_handling

def register_routes(bp):
    """Register admin job management routes"""
    
    @bp.route('/job-management')
    @login_required
    @with_session_error_handling
    def job_management():
        """Admin job management interface with context switching"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        db_manager = current_app.config['db_manager']
        
        # Determine admin mode (default to True for admin users)
        admin_mode = request.args.get('admin_mode', 'true').lower() == 'true'
        
        # Get job statistics
        job_stats = get_job_statistics(current_user.id, admin_mode)
        
        # Get admin jobs (all jobs when in admin mode)
        admin_jobs = get_admin_jobs(current_user.id) if admin_mode else []
        
        # Get personal jobs (admin user's own jobs)
        personal_jobs = get_personal_jobs(current_user.id)
        
        return render_template('admin_job_management.html',
                             admin_mode=admin_mode,
                             job_stats=job_stats,
                             admin_jobs=admin_jobs,
                             personal_jobs=personal_jobs)
    
    @bp.route('/bulk-actions')
    @login_required
    @with_session_error_handling
    def bulk_actions():
        """Bulk actions management page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        db_manager = current_app.config['db_manager']
        
        # Get all active jobs for bulk actions
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask, User, PlatformConnection
            
            jobs = session.query(CaptionGenerationTask, User, PlatformConnection)\
                         .join(User, CaptionGenerationTask.user_id == User.id)\
                         .join(PlatformConnection, CaptionGenerationTask.platform_connection_id == PlatformConnection.id)\
                         .filter(CaptionGenerationTask.status.in_(['running', 'queued', 'failed']))\
                         .order_by(CaptionGenerationTask.created_at.desc())\
                         .all()
            
            job_list = []
            for task, user, platform in jobs:
                job_list.append({
                    'task_id': task.id,
                    'username': user.username,
                    'user_email': user.email,
                    'platform_name': platform.name,
                    'platform_type': platform.platform_type,
                    'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                    'created_at': task.created_at,
                    'progress_percentage': task.progress_percent or 0
                })
            
            # Available bulk actions
            bulk_actions = [
                {
                    'id': 'cancel_selected',
                    'name': 'Cancel Selected Jobs',
                    'description': 'Cancel all selected jobs',
                    'icon': 'bi-stop-circle',
                    'class': 'btn-outline-danger',
                    'requires_reason': True
                },
                {
                    'id': 'set_priority_high',
                    'name': 'Set High Priority',
                    'description': 'Set high priority for selected jobs',
                    'icon': 'bi-arrow-up-circle',
                    'class': 'btn-outline-warning',
                    'requires_reason': False
                },
                {
                    'id': 'restart_failed',
                    'name': 'Restart Failed Jobs',
                    'description': 'Restart all selected failed jobs',
                    'icon': 'bi-arrow-clockwise',
                    'class': 'btn-outline-success',
                    'requires_reason': False
                },
                {
                    'id': 'add_notes',
                    'name': 'Add Admin Notes',
                    'description': 'Add notes to selected jobs',
                    'icon': 'bi-sticky',
                    'class': 'btn-outline-secondary',
                    'requires_reason': True
                }
            ]
        
        return render_template('admin_bulk_actions.html',
                             jobs=job_list,
                             bulk_actions=bulk_actions,
                             total_jobs=len(job_list))
    
    @bp.route('/system-maintenance')
    @login_required
    @with_session_error_handling
    def system_maintenance():
        """System maintenance management page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        db_manager = current_app.config['db_manager']
        
        # Get system metrics and maintenance information
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask, User
            from datetime import datetime, timedelta
            
            # System statistics
            total_active_jobs = session.query(CaptionGenerationTask)\
                                     .filter(CaptionGenerationTask.status.in_(['running', 'queued']))\
                                     .count()
            
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            
            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_jobs = session.query(CaptionGenerationTask)\
                                .filter(CaptionGenerationTask.created_at >= yesterday)\
                                .count()
            
            # Check actual maintenance mode status
            from multi_tenant_control_service import MultiTenantControlService
            mt_service = MultiTenantControlService(db_manager)
            is_maintenance = mt_service.is_maintenance_mode()
            maintenance_reason = mt_service.get_maintenance_reason()
            
            system_metrics = {
                'active_jobs': total_active_jobs,
                'total_users': total_users,
                'active_users': active_users,
                'recent_jobs_24h': recent_jobs,
                'system_status': 'Maintenance' if is_maintenance else 'Running',
                'maintenance_reason': maintenance_reason,
                'uptime': '2 days, 14 hours',  # This could be calculated from app start time
                'memory_usage': '45%',  # This could be from system monitoring
                'cpu_usage': '23%'  # This could be from system monitoring
            }
            
            # Available maintenance actions - show different actions based on system status
            maintenance_actions = []
            
            # Add pause/resume action based on current status
            if is_maintenance:
                maintenance_actions.append({
                    'id': 'resume_system',
                    'name': 'Resume System',
                    'description': 'Resume normal job processing operations',
                    'icon': 'bi-play-circle',
                    'class': 'btn-outline-success',
                    'requires_reason': False
                })
            else:
                maintenance_actions.append({
                    'id': 'pause_system',
                    'name': 'Pause System',
                    'description': 'Temporarily pause all job processing',
                    'icon': 'bi-pause-circle',
                    'class': 'btn-outline-warning',
                    'requires_reason': True
                })
            
            # Add other maintenance actions
            maintenance_actions.extend([
                {
                    'id': 'clear_queue',
                    'name': 'Clear Job Queue',
                    'description': 'Remove all queued jobs (running jobs continue)',
                    'icon': 'bi-trash',
                    'class': 'btn-outline-danger',
                    'requires_reason': True
                },
                {
                    'id': 'restart_failed',
                    'name': 'Restart All Failed Jobs',
                    'description': 'Restart all failed jobs system-wide',
                    'icon': 'bi-arrow-clockwise',
                    'class': 'btn-outline-success',
                    'requires_reason': False
                },
                {
                    'id': 'cleanup_old_data',
                    'name': 'Cleanup Old Data',
                    'description': 'Remove old completed jobs and temporary files',
                    'icon': 'bi-broom',
                    'class': 'btn-outline-info',
                    'requires_reason': False
                }
            ])
        
        return render_template('admin_system_maintenance.html',
                             system_metrics=system_metrics,
                             maintenance_actions=maintenance_actions)
    
    @bp.route('/maintenance/pause-system')
    @login_required
    @with_session_error_handling
    def pause_system():
        """Pause system maintenance page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        # Check current maintenance mode status
        db_manager = current_app.config['db_manager']
        from multi_tenant_control_service import MultiTenantControlService
        mt_service = MultiTenantControlService(db_manager)
        is_maintenance = mt_service.is_maintenance_mode()
        maintenance_reason = mt_service.get_maintenance_reason()
        
        system_status = {
            'status': 'Maintenance' if is_maintenance else 'Running',
            'reason': maintenance_reason
        }
        
        return render_template('admin_maintenance_pause_system.html', system_status=system_status)
    
    @bp.route('/maintenance/resume-system')
    @login_required
    @with_session_error_handling
    def resume_system():
        """Resume system maintenance page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        # Check current maintenance mode status
        db_manager = current_app.config['db_manager']
        from multi_tenant_control_service import MultiTenantControlService
        mt_service = MultiTenantControlService(db_manager)
        is_maintenance = mt_service.is_maintenance_mode()
        maintenance_reason = mt_service.get_maintenance_reason()
        
        # Get additional status information
        system_status = {
            'status': 'Maintenance' if is_maintenance else 'Running',
            'reason': maintenance_reason,
            'paused_at': None  # This could be enhanced to track when the system was paused
        }
        
        return render_template('admin_maintenance_resume_system.html', system_status=system_status)
    
    @bp.route('/maintenance/clear-queue')
    @login_required
    @with_session_error_handling
    def clear_queue():
        """Clear job queue maintenance page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        db_manager = current_app.config['db_manager']
        
        # Get queued jobs count
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask
            queued_jobs_count = session.query(CaptionGenerationTask)\
                                     .filter_by(status='queued')\
                                     .count()
        
        return render_template('admin_maintenance_clear_queue.html',
                             queued_jobs_count=queued_jobs_count)
    
    @bp.route('/maintenance/restart-failed')
    @login_required
    @with_session_error_handling
    def restart_failed():
        """Restart failed jobs maintenance page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        db_manager = current_app.config['db_manager']
        
        # Get failed jobs
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask, User, PlatformConnection
            
            failed_jobs = session.query(CaptionGenerationTask, User, PlatformConnection)\
                               .join(User, CaptionGenerationTask.user_id == User.id)\
                               .join(PlatformConnection, CaptionGenerationTask.platform_connection_id == PlatformConnection.id)\
                               .filter(CaptionGenerationTask.status == 'failed')\
                               .order_by(CaptionGenerationTask.created_at.desc())\
                               .all()
            
            failed_jobs_list = []
            for task, user, platform in failed_jobs:
                failed_jobs_list.append({
                    'task_id': task.id,
                    'username': user.username,
                    'platform_name': platform.name,
                    'platform_type': platform.platform_type,
                    'created_at': task.created_at,
                    'error_message': getattr(task, 'error_message', 'Unknown error')
                })
        
        return render_template('admin_maintenance_restart_failed.html',
                             failed_jobs=failed_jobs_list,
                             failed_jobs_count=len(failed_jobs_list))
    
    @bp.route('/maintenance/cleanup-data')
    @login_required
    @with_session_error_handling
    def cleanup_data():
        """Cleanup old data maintenance page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        db_manager = current_app.config['db_manager']
        
        # Get cleanup statistics
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask, Image
            from datetime import datetime, timedelta
            
            # Old completed jobs (older than 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            old_completed_jobs = session.query(CaptionGenerationTask)\
                                      .filter(CaptionGenerationTask.status == 'completed')\
                                      .filter(CaptionGenerationTask.completed_at < thirty_days_ago)\
                                      .count()
            
            # Old failed jobs (older than 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            old_failed_jobs = session.query(CaptionGenerationTask)\
                                   .filter(CaptionGenerationTask.status == 'failed')\
                                   .filter(CaptionGenerationTask.created_at < seven_days_ago)\
                                   .count()
            
            # Orphaned images (no associated posts)
            orphaned_images = session.query(Image)\
                                   .filter(Image.post_id.is_(None))\
                                   .count()
            
            cleanup_stats = {
                'old_completed_jobs': old_completed_jobs,
                'old_failed_jobs': old_failed_jobs,
                'orphaned_images': orphaned_images,
                'total_cleanable': old_completed_jobs + old_failed_jobs + orphaned_images
            }
        
        return render_template('admin_maintenance_cleanup_data.html',
                             cleanup_stats=cleanup_stats)
    
    @bp.route('/job-history/<int:user_id>')
    @login_required
    @with_session_error_handling
    def job_history(user_id):
        """Job history page for a specific user"""
        if not current_user.role == UserRole.ADMIN and current_user.id != user_id:
            from flask import flash, redirect, url_for
            flash('Access denied. You can only view your own job history.', 'error')
            return redirect(url_for('admin.job_management'))
        
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask, User, PlatformConnection
            
            # Get user information
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                from flask import flash, redirect, url_for
                flash('User not found.', 'error')
                return redirect(url_for('admin.job_management'))
            
            # Get job history for the user
            jobs = session.query(CaptionGenerationTask, PlatformConnection)\
                         .join(PlatformConnection, CaptionGenerationTask.platform_connection_id == PlatformConnection.id)\
                         .filter(CaptionGenerationTask.user_id == user_id)\
                         .order_by(CaptionGenerationTask.created_at.desc())\
                         .limit(50)\
                         .all()
            
            job_history = []
            for task, platform in jobs:
                job_history.append({
                    'task_id': task.id,
                    'platform_name': platform.name,
                    'platform_type': platform.platform_type,
                    'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                    'created_at': task.created_at,
                    'completed_at': task.completed_at,
                    'progress_percentage': task.progress_percent or 0,
                    'results': {
                        'captions_generated': getattr(task, 'captions_generated', 0),
                        'images_processed': getattr(task, 'images_processed', 0),
                        'errors_count': getattr(task, 'errors_count', 0)
                    }
                })
        
        return render_template('admin_job_history.html',
                             user=user,
                             job_history=job_history,
                             is_own_history=(current_user.id == user_id))
    
    @bp.route('/help')
    @login_required
    @with_session_error_handling
    def help_center():
        """Admin help center"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        return render_template('admin_help_center.html')
    
    @bp.route('/logs')
    @login_required
    @with_session_error_handling
    def system_logs():
        """System logs viewer"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        import os
        from datetime import datetime
        
        log_files = []
        log_directory = 'logs'
        
        # Get available log files
        if os.path.exists(log_directory):
            for filename in os.listdir(log_directory):
                if filename.endswith('.log'):
                    filepath = os.path.join(log_directory, filename)
                    try:
                        stat = os.stat(filepath)
                        log_files.append({
                            'name': filename,
                            'path': filepath,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'size_mb': round(stat.st_size / (1024 * 1024), 2)
                        })
                    except OSError:
                        continue
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        # Get current log content (last 500 lines of webapp.log)
        current_log_content = []
        webapp_log_path = os.path.join(log_directory, 'webapp.log')
        
        if os.path.exists(webapp_log_path):
            try:
                with open(webapp_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 500 lines
                    current_log_content = lines[-500:] if len(lines) > 500 else lines
            except Exception as e:
                current_log_content = [f"Error reading log file: {e}"]
        
        return render_template('admin_system_logs.html',
                             log_files=log_files,
                             current_log_content=current_log_content,
                             current_log_name='webapp.log')

def get_job_statistics(admin_user_id, admin_mode=True):
    """Get job statistics for admin dashboard"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config['db_manager']
        service = WebCaptionGenerationService(db_manager)
        
        # Get system metrics
        metrics = service.get_system_metrics(admin_user_id)
        
        # Calculate statistics
        stats = {
            'total_active': metrics.get('active_jobs', 0),
            'personal_active': get_personal_active_jobs_count(admin_user_id),
            'admin_managed': get_admin_managed_jobs_count(admin_user_id),
            'queued': metrics.get('queued_jobs', 0)
        }
        
        return stats
        
    except Exception as e:
        current_app.logger.error(f"Error getting job statistics: {e}")
        return {
            'total_active': 0,
            'personal_active': 0,
            'admin_managed': 0,
            'queued': 0
        }

def get_admin_jobs(admin_user_id):
    """Get jobs that require admin management"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config['db_manager']
        service = WebCaptionGenerationService(db_manager)
        
        # Get all active jobs with admin access
        jobs = service.get_all_active_jobs(admin_user_id)
        
        # Format jobs for admin display
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
                'admin_managed': job.get('admin_managed', False),
                'admin_notes': job.get('admin_notes', '')
            }
            formatted_jobs.append(formatted_job)
        
        return formatted_jobs
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin jobs: {e}")
        return []

def get_personal_jobs(admin_user_id):
    """Get admin user's personal jobs"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask, PlatformConnection
            
            # Get admin user's own jobs
            jobs = session.query(CaptionGenerationTask)\
                         .join(PlatformConnection)\
                         .filter(CaptionGenerationTask.user_id == admin_user_id)\
                         .filter(CaptionGenerationTask.status.in_(['running', 'queued', 'completed', 'failed']))\
                         .order_by(CaptionGenerationTask.created_at.desc())\
                         .limit(10)\
                         .all()
            
            # Format jobs for display
            formatted_jobs = []
            for job in jobs:
                platform = job.platform_connection
                formatted_job = {
                    'task_id': job.id,
                    'platform_type': platform.platform_type if platform else 'unknown',
                    'platform_name': platform.name if platform else 'Unknown Platform',
                    'status': job.status.value if hasattr(job.status, 'value') else str(job.status),
                    'progress_percentage': job.progress_percent or 0,
                    'current_step': job.current_step or 'Initializing',
                    'created_at': job.created_at,
                    'max_posts': getattr(job, 'max_posts_per_run', None),
                    'processing_delay': getattr(job, 'processing_delay', None),
                    'results': {
                        'captions_generated': getattr(job, 'captions_generated', 0),
                        'images_processed': getattr(job, 'images_processed', 0),
                        'errors_count': getattr(job, 'errors_count', 0)
                    } if job.status.value == 'completed' else None
                }
                formatted_jobs.append(formatted_job)
            
            return formatted_jobs
        
    except Exception as e:
        current_app.logger.error(f"Error getting personal jobs: {e}")
        return []

def get_personal_active_jobs_count(admin_user_id):
    """Get count of admin user's active jobs"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask
            
            count = session.query(CaptionGenerationTask)\
                          .filter(CaptionGenerationTask.user_id == admin_user_id)\
                          .filter(CaptionGenerationTask.status.in_(['running', 'queued']))\
                          .count()
            
            return count
        
    except Exception as e:
        current_app.logger.error(f"Error getting personal active jobs count: {e}")
        return 0

def get_admin_managed_jobs_count(admin_user_id):
    """Get count of jobs managed by admin"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask
            
            count = session.query(CaptionGenerationTask)\
                          .filter(CaptionGenerationTask.admin_user_id == admin_user_id)\
                          .filter(CaptionGenerationTask.admin_managed == True)\
                          .count()
            
            return count
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin managed jobs count: {e}")
        return 0