# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Data Cleanup Routes"""

import logging
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import UserRole, ProcessingStatus
from session_error_handlers import with_session_error_handling
from ..services.cleanup_service import CleanupService

logger = logging.getLogger(__name__)

def register_routes(bp):
    """Register cleanup routes"""
    
    @bp.route('/cleanup')
    @login_required
    @with_session_error_handling
    def cleanup():
        """Admin interface for data cleanup"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        db_manager = current_app.config['db_manager']
        cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
        
        stats = cleanup_service.get_cleanup_statistics()
        retention = {'processing_runs': 30, 'rejected_images': 7, 'posted_images': 30, 'error_images': 7}
        
        return render_template('admin_cleanup.html', stats=stats, users=stats.get('users', []), retention=retention)

    @bp.route('/cleanup/runs', methods=['POST'])
    @login_required
    @with_session_error_handling
    def cleanup_runs():
        """Handle various cleanup operations"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied', 'error')
            return redirect(url_for('admin.cleanup'))
        
        db_manager = current_app.config['db_manager']
        cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
        
        # Determine the type of cleanup operation
        operation = request.form.get('operation', 'archive_runs')
        dry_run = 'dry_run' in request.form
        
        try:
            if operation == 'archive_runs':
                days = request.form.get('days', type=int)
                if not days or days < 1:
                    flash('Invalid number of days', 'error')
                    return redirect(url_for('admin.cleanup'))
                
                result = cleanup_service.cleanup_old_processing_runs(days=days, dry_run=dry_run)
                
            elif operation == 'cleanup_images':
                status_str = request.form.get('status', 'rejected')
                days = request.form.get('days', type=int)
                
                if not days or days < 1:
                    flash('Invalid number of days', 'error')
                    return redirect(url_for('admin.cleanup'))
                
                # Convert status string to enum
                status_map = {
                    'rejected': ProcessingStatus.REJECTED,
                    'posted': ProcessingStatus.POSTED,
                    'error': ProcessingStatus.ERROR
                }
                status = status_map.get(status_str, ProcessingStatus.REJECTED)
                
                # Use storage-aware cleanup if available
                result = cleanup_service.cleanup_old_images_with_storage_monitoring(
                    status=status, days=days, dry_run=dry_run
                )
                
            elif operation == 'cleanup_orphaned_posts':
                result = cleanup_service.cleanup_orphaned_posts(dry_run=dry_run)
                
            elif operation == 'cleanup_user_data':
                user_id = request.form.get('user_id')
                if not user_id:
                    flash('Please select a user', 'error')
                    return redirect(url_for('admin.cleanup'))
                
                result = cleanup_service.cleanup_user_data(user_id=user_id, dry_run=dry_run)
                
            elif operation == 'cleanup_storage_images':
                result = cleanup_service.cleanup_storage_images_with_monitoring(dry_run=dry_run)
                
            elif operation == 'full_cleanup':
                result = cleanup_service.run_full_cleanup(dry_run=dry_run)
                
            else:
                flash('Unknown cleanup operation', 'error')
                return redirect(url_for('admin.cleanup'))
            
            # Handle result
            if result['success']:
                message = result['message']
                
                # Add storage information if available
                if 'storage_freed_gb' in result and result['storage_freed_gb'] > 0:
                    message += f" (Storage freed: {result['storage_freed_gb']:.2f}GB)"
                
                if 'limit_lifted' in result and result['limit_lifted']:
                    message += " - Storage limits automatically lifted!"
                    flash(message, 'success')
                else:
                    flash(message, 'info' if dry_run else 'success')
            else:
                flash(f'Error: {result["error"]}', 'error')
                
        except Exception as e:
            logger.error(f"Error in cleanup operation {operation}: {e}")
            flash(f'Cleanup operation failed: {str(e)}', 'error')
        
        return redirect(url_for('admin.cleanup'))