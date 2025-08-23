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