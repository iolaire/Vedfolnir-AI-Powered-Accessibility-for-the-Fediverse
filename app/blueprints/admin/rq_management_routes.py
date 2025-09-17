# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin RQ Management Routes

Provides administrative interface for RQ system management including
queue statistics, task migration, and system health monitoring.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.utils.web.response_helpers import success_response, error_response
from app.utils.decorators import admin_required
from app.core.security.core.security_utils import sanitize_for_log

rq_admin_bp = Blueprint('rq_admin', __name__, url_prefix='/admin/rq')


@rq_admin_bp.route('/dashboard')
@login_required
@admin_required
def rq_dashboard():
    """RQ system dashboard"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            current_app.logger.error("Database manager not found in app config")
            return error_response('Database manager not available', 500)
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        
        # Get system status
        system_status = caption_service.get_system_status()
        
        return render_template('admin/rq_dashboard.html', 
                             system_status=system_status,
                             user=current_user)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading RQ dashboard: {sanitize_for_log(str(e))}")
        return error_response('Failed to load RQ dashboard', 500)


@rq_admin_bp.route('/api/status')
@login_required
@admin_required
def get_rq_status():
    """Get RQ system status API"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            return error_response('Database manager not available', 500)
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        
        # Get system status
        system_status = caption_service.get_system_status()
        
        return success_response(system_status, 'RQ status retrieved successfully')
        
    except Exception as e:
        current_app.logger.error(f"Error getting RQ status: {sanitize_for_log(str(e))}")
        return error_response('Failed to get RQ status', 500)


@rq_admin_bp.route('/api/migrate-tasks', methods=['POST'])
@login_required
@admin_required
def migrate_tasks_to_rq():
    """Migrate database tasks to RQ"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            return error_response('Database manager not available', 500)
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        if not rq_queue_manager:
            return error_response('RQ system not available', 503)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        
        # Perform migration
        migration_result = caption_service.migrate_database_tasks_to_rq()
        
        if 'error' in migration_result:
            return error_response(migration_result['error'], 500)
        
        current_app.logger.info(f"Admin {current_user.id} initiated task migration to RQ")
        
        return success_response(migration_result, 'Task migration completed successfully')
        
    except Exception as e:
        current_app.logger.error(f"Error migrating tasks to RQ: {sanitize_for_log(str(e))}")
        return error_response('Failed to migrate tasks', 500)


@rq_admin_bp.route('/api/validate-migration', methods=['POST'])
@login_required
@admin_required
def validate_migration_integrity():
    """Validate migration integrity"""
    try:
        from app.services.task.web.rq_web_caption_service import RQWebCaptionService
        
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            return error_response('Database manager not available', 500)
        
        # Get RQ queue manager if available
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        if not rq_queue_manager:
            return error_response('RQ system not available', 503)
        
        # Create RQ-aware caption service
        caption_service = RQWebCaptionService(db_manager, rq_queue_manager)
        
        # Validate migration integrity
        validation_result = caption_service.validate_migration_integrity()
        
        if 'error' in validation_result:
            return error_response(validation_result['error'], 500)
        
        current_app.logger.info(f"Admin {current_user.id} validated migration integrity")
        
        return success_response(validation_result, 'Migration integrity validation completed')
        
    except Exception as e:
        current_app.logger.error(f"Error validating migration integrity: {sanitize_for_log(str(e))}")
        return error_response('Failed to validate migration integrity', 500)


@rq_admin_bp.route('/api/queue-stats')
@login_required
@admin_required
def get_queue_statistics():
    """Get detailed queue statistics"""
    try:
        db_manager = current_app.config.get('db_manager')
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        if not db_manager:
            return error_response('Database manager not available', 500)
        
        stats = {
            'rq_available': rq_queue_manager is not None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if rq_queue_manager:
            # Get RQ queue statistics
            rq_stats = rq_queue_manager.get_queue_stats()
            stats['rq_stats'] = rq_stats
            
            # Get health status
            health_status = rq_queue_manager.get_health_status()
            stats['health_status'] = health_status
        
        # Get database statistics
        from app.services.task.core.task_queue_manager import TaskQueueManager
        db_task_manager = TaskQueueManager(db_manager)
        db_stats = db_task_manager.get_queue_stats()
        stats['database_stats'] = db_stats
        
        return success_response(stats, 'Queue statistics retrieved successfully')
        
    except Exception as e:
        current_app.logger.error(f"Error getting queue statistics: {sanitize_for_log(str(e))}")
        return error_response('Failed to get queue statistics', 500)


@rq_admin_bp.route('/api/health-check', methods=['POST'])
@login_required
@admin_required
def force_health_check():
    """Force immediate health check"""
    try:
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        if not rq_queue_manager:
            return error_response('RQ system not available', 503)
        
        # Force health check
        health_result = rq_queue_manager.force_health_check()
        
        current_app.logger.info(f"Admin {current_user.id} forced RQ health check")
        
        return success_response(health_result, 'Health check completed')
        
    except Exception as e:
        current_app.logger.error(f"Error during forced health check: {sanitize_for_log(str(e))}")
        return error_response('Failed to perform health check', 500)


@rq_admin_bp.route('/api/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup_completed_jobs():
    """Cleanup completed RQ jobs"""
    try:
        rq_queue_manager = getattr(current_app, 'rq_queue_manager', None)
        
        if not rq_queue_manager:
            return error_response('RQ system not available', 503)
        
        # Cleanup completed jobs
        rq_queue_manager.cleanup_completed_jobs()
        
        current_app.logger.info(f"Admin {current_user.id} initiated RQ job cleanup")
        
        return success_response({}, 'Job cleanup completed successfully')
        
    except Exception as e:
        current_app.logger.error(f"Error during job cleanup: {sanitize_for_log(str(e))}")
        return error_response('Failed to cleanup jobs', 500)