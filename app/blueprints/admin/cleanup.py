# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MIGRATION NOTE: Flash messages in this file have been commented out as part of
# the notification system migration. The application now uses the unified
# WebSocket-based notification system. These comments should be replaced with
# appropriate unified notification calls in a future update.


from app.services.notification.manager.unified_manager import UnifiedNotificationManager
"""Admin Data Cleanup Routes"""

import logging
from flask import render_template, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole, ProcessingStatus
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from app.core.session.error_handling.session_error_handlers import with_session_error_handling
from app.services.admin.components.cleanup_service import CleanupService

logger = logging.getLogger(__name__)

def register_routes(bp):
    """Register cleanup routes"""
    
    @bp.route('/cleanup')
    @login_required
    def cleanup():
        """Admin interface for data cleanup"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
            
        db_manager = current_app.config['db_manager']
        cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
        
        stats = cleanup_service.get_cleanup_statistics()
        retention = {'processing_runs': 30, 'rejected_images': 7, 'posted_images': 30, 'error_images': 7}
        
        return render_template('admin_cleanup.html', stats=stats, users=stats.get('users', []), retention=retention)

    @bp.route('/cleanup/runs', methods=['POST'])
    @login_required
    def cleanup_runs():
        """Handle various cleanup operations"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied.", "Access Denied")
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
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Invalid number of days.", "Invalid Input")
                    return redirect(url_for('admin.cleanup'))
                
                result = cleanup_service.cleanup_old_processing_runs(days=days, dry_run=dry_run)
                
            elif operation == 'cleanup_images':
                status_str = request.form.get('status', 'rejected')
                days = request.form.get('days', type=int)
                
                if not days or days < 1:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Invalid number of days.", "Invalid Input")
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
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Please select a user.", "Invalid Input")
                    return redirect(url_for('admin.cleanup'))
                
                result = cleanup_service.cleanup_user_data(user_id=user_id, dry_run=dry_run)
                
            elif operation == 'cleanup_storage_images':
                result = cleanup_service.cleanup_storage_images_with_monitoring(dry_run=dry_run)
                
            elif operation == 'full_cleanup':
                result = cleanup_service.run_full_cleanup(dry_run=dry_run)
                
            else:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("Unknown cleanup operation.", "Invalid Operation")
                return redirect(url_for('admin.cleanup'))
            
            # Handle result
            if result['success']:
                message = result['message']
                
                # Add storage information if available
                if 'storage_freed_gb' in result and result['storage_freed_gb'] > 0:
                    message += f" (Storage freed: {result['storage_freed_gb']:.2f}GB)"
                
                if 'limit_lifted' in result and result['limit_lifted']:
                    message += " - Storage limits automatically lifted!"
                    # Send success notification
                    from app.services.notification.helpers.notification_helpers import send_success_notification
                    send_success_notification(message, "Cleanup Complete")
                else:
                    # Send notification based on dry run status
                    from app.services.notification.helpers.notification_helpers import send_info_notification, send_success_notification
                    if dry_run:
                        send_info_notification(message, "Cleanup Preview")
                    else:
                        send_success_notification(message, "Cleanup Complete")
            else:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification(f'Error: {result["error"]}', "Cleanup Failed")
                
                pass
        except Exception as e:
            logger.error(f"Error in cleanup operation {operation}: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(f'Cleanup operation failed: {str(e)}', "Operation Failed")
        
        return redirect(url_for('admin.cleanup'))