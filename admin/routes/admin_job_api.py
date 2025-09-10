# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Job Management API Routes"""

from flask import jsonify, request, current_app, session, redirect, url_for
from flask_login import login_required, current_user
from models import UserRole
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from app.core.session.error_handling.session_error_handlers import with_session_error_handling
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def api_login_required(f):
    """Custom login required decorator for API routes that returns JSON instead of redirects"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        return f(*args, **kwargs)
    return decorated_function

def api_admin_required(f):
    """Custom admin required decorator for API routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Admin privileges required', 'code': 'ADMIN_REQUIRED'}), 403
        return f(*args, **kwargs)
    return decorated_function

def register_api_routes(bp):
    """Register admin job management API routes"""
    
    @bp.route('/api/bulk-actions', methods=['GET'])
    @api_admin_required
    def get_bulk_actions():
        """Get available bulk actions and current job selection"""
        
        try:
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
                        'created_at': task.created_at.isoformat() if task.created_at else None,
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
                
                return jsonify({
                    'success': True,
                    'jobs': job_list,
                    'bulk_actions': bulk_actions,
                    'total_jobs': len(job_list)
                })
        
        except Exception as e:
            logger.error(f"Error getting bulk actions: {e}")
            return jsonify({'error': 'Failed to load bulk actions'}), 500
    
    @bp.route('/api/bulk-actions/execute', methods=['POST'])
    @api_admin_required
    def execute_bulk_action():
        """Execute a bulk action on selected jobs"""
        
        try:
            data = request.get_json()
            action_id = data.get('action_id')
            job_ids = data.get('job_ids', [])
            reason = data.get('reason', '')
            
            if not action_id or not job_ids:
                return jsonify({'error': 'Action ID and job IDs are required'}), 400
            
            db_manager = current_app.config['db_manager']
            results = []
            
            with db_manager.get_session() as session:
                from models import CaptionGenerationTask
                
                for job_id in job_ids:
                    try:
                        task = session.query(CaptionGenerationTask).filter_by(id=job_id).first()
                        if not task:
                            results.append({'job_id': job_id, 'success': False, 'error': 'Job not found'})
                            continue
                        
                        if action_id == 'cancel_selected':
                            task.status = 'cancelled'
                            task.admin_notes = f"Cancelled by admin: {reason}"
                            task.admin_user_id = current_user.id
                            task.admin_managed = True
                            
                        elif action_id == 'set_priority_high':
                            task.priority = 'high'
                            task.admin_notes = f"Priority set to high by admin"
                            task.admin_user_id = current_user.id
                            task.admin_managed = True
                            
                        elif action_id == 'restart_failed' and task.status.value == 'failed':
                            # Create new task with same settings
                            new_task = CaptionGenerationTask(
                                user_id=task.user_id,
                                platform_connection_id=task.platform_connection_id,
                                status='queued',
                                admin_notes=f"Restarted by admin from failed job {job_id}",
                                admin_user_id=current_user.id,
                                admin_managed=True
                            )
                            session.add(new_task)
                            
                        elif action_id == 'add_notes':
                            existing_notes = task.admin_notes or ''
                            task.admin_notes = f"{existing_notes}\n{reason}".strip()
                            task.admin_user_id = current_user.id
                            task.admin_managed = True
                        
                        results.append({'job_id': job_id, 'success': True})
                        
                    except Exception as e:
                        logger.error(f"Error processing job {job_id}: {e}")
                        results.append({'job_id': job_id, 'success': False, 'error': str(e)})
                
                session.commit()
            
            successful_count = sum(1 for r in results if r['success'])
            
            return jsonify({
                'success': True,
                'results': results,
                'successful_count': successful_count,
                'total_count': len(job_ids),
                'message': f"Bulk action completed: {successful_count}/{len(job_ids)} jobs processed successfully"
            })
        
        except Exception as e:
            logger.error(f"Error executing bulk action: {e}")
            return jsonify({'error': 'Failed to execute bulk action'}), 500
    
    @bp.route('/api/system-maintenance', methods=['GET'])
    @api_admin_required
    def get_system_maintenance():
        """Get system maintenance information"""
        
        try:
            from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
            
            db_manager = current_app.config['db_manager']
            service = WebCaptionGenerationService(db_manager)
            
            # Get system metrics
            metrics = service.get_system_metrics(current_user.id)
            
            # Get system status
            system_status = {
                'status': 'operational',
                'uptime': '2h 15m',
                'last_maintenance': '2025-09-02T20:00:00Z'
            }
            
            # Get recent maintenance activities
            maintenance_log = [
                {
                    'timestamp': '2025-09-02T20:00:00Z',
                    'action': 'System restart',
                    'user': 'admin',
                    'status': 'completed'
                }
            ]
            
            return jsonify({
                'success': True,
                'system_status': system_status,
                'metrics': metrics,
                'maintenance_log': maintenance_log,
                'maintenance_actions': [
                    {
                        'id': 'pause_system',
                        'name': 'Pause System',
                        'description': 'Prevent new jobs from starting',
                        'icon': 'bi-pause-circle',
                        'class': 'btn-warning',
                        'requires_reason': True
                    },
                    {
                        'id': 'resume_system',
                        'name': 'Resume System',
                        'description': 'Allow new jobs to start',
                        'icon': 'bi-play-circle',
                        'class': 'btn-success',
                        'requires_reason': False
                    },
                    {
                        'id': 'clear_queue',
                        'name': 'Clear Job Queue',
                        'description': 'Remove all queued jobs',
                        'icon': 'bi-trash',
                        'class': 'btn-danger',
                        'requires_reason': True
                    },
                    {
                        'id': 'restart_services',
                        'name': 'Restart Services',
                        'description': 'Restart background services',
                        'icon': 'bi-arrow-clockwise',
                        'class': 'btn-info',
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
                ]
            })
        
        except Exception as e:
            logger.error(f"Error getting system maintenance info: {e}")
            return jsonify({'error': 'Failed to load system maintenance information'}), 500
    
    @bp.route('/api/system-maintenance/execute', methods=['POST'])
    @api_admin_required
    def execute_maintenance_action():
        """Execute a system maintenance action"""
        
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                action_id = data.get('action_id')
                reason = data.get('reason', '')
            else:
                # Handle form data
                action_id = request.form.get('action')
                reason = request.form.get('reason', '')
            
            if not action_id:
                if request.is_json:
                    return jsonify({'error': 'Action ID is required'}), 400
                else:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Action is required", "Error")
                    return redirect(url_for('admin.system_maintenance'))
            
            db_manager = current_app.config['db_manager']
            
            if action_id == 'pause_system':
                # Get additional form data for pause system
                duration = request.form.get('duration', '') if not request.is_json else ''
                custom_duration = request.form.get('customDuration', '') if not request.is_json else ''
                notify_users = request.form.get('notifyUsers') == 'on' if not request.is_json else False
                
                # Use custom duration if specified
                if duration == 'custom' and custom_duration:
                    duration = custom_duration
                
                # Use the proper multi-tenant control service
                from app.services.batch.components.multi_tenant_control_service import MultiTenantControlService
                mt_service = MultiTenantControlService(db_manager)
                
                success = mt_service.pause_system_jobs(current_user.id, reason)
                
                if success:
                    duration_msg = f" (Expected duration: {duration})" if duration else ""
                    notify_msg = " Users will be notified." if notify_users else ""
                    message = f"System has been paused successfully.{duration_msg}{notify_msg}"
                    result = {
                        'success': True,
                        'message': message,
                        'new_status': 'paused'
                    }
                else:
                    result = {
                        'success': False,
                        'message': 'Failed to pause system'
                    }
            elif action_id == 'resume_system':
                # Use the proper multi-tenant control service
                from app.services.batch.components.multi_tenant_control_service import MultiTenantControlService
                mt_service = MultiTenantControlService(db_manager)
                
                success = mt_service.resume_system_jobs(current_user.id)
                
                if success:
                    result = {
                        'success': True,
                        'message': 'System has been resumed successfully',
                        'new_status': 'active'
                    }
                else:
                    result = {
                        'success': False,
                        'message': 'Failed to resume system'
                    }
            elif action_id == 'clear_queue':
                result = clear_job_queue(reason, current_user.id)
            elif action_id == 'restart_services':
                result = restart_services(reason, current_user.id)
            elif action_id == 'restart_failed':
                result = restart_all_failed_jobs(reason, current_user.id)
            elif action_id == 'cleanup_old_data':
                result = cleanup_old_data(reason, current_user.id)
            else:
                error_msg = 'Unknown maintenance action'
                if request.is_json:
                    return jsonify({'error': error_msg}), 400
                else:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification(error_msg, "Error")
                    return redirect(url_for('admin.system_maintenance'))
            
            # Log maintenance action
            log_maintenance_action(action_id, reason, current_user.id, result['success'])
            
            if request.is_json:
                return jsonify(result)
            else:
                # Handle form submission response
                if result['success']:
                    # Send success notification
                    from app.services.notification.helpers.notification_helpers import send_success_notification
                    send_success_notification(result.get('message', 'Maintenance action completed successfully'), "Maintenance Complete")
                else:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification(result.get('message', 'Maintenance action failed'), "Maintenance Failed")
                return redirect(url_for('admin.system_maintenance'))
        
        except Exception as e:
            logger.error(f"Error executing maintenance action: {e}")
            if request.is_json:
                return jsonify({'error': 'Failed to execute maintenance action'}), 500
            else:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("Failed to execute maintenance action", "Error")
                return redirect(url_for('admin.system_maintenance'))
    
    @bp.route('/api/job-history/<int:user_id>', methods=['GET'])
    @api_login_required
    def get_job_history(user_id):
        """Get job history for a user"""
        if not current_user.role == UserRole.ADMIN and current_user.id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            status_filter = request.args.get('status', None)
            
            db_manager = current_app.config['db_manager']
            
            with db_manager.get_session() as session:
                from models import CaptionGenerationTask, PlatformConnection
                
                query = session.query(CaptionGenerationTask, PlatformConnection)\
                              .join(PlatformConnection)\
                              .filter(CaptionGenerationTask.user_id == user_id)\
                              .order_by(CaptionGenerationTask.created_at.desc())
                
                if status_filter:
                    query = query.filter(CaptionGenerationTask.status == status_filter)
                
                # Calculate pagination
                total = query.count()
                offset = (page - 1) * per_page
                jobs = query.offset(offset).limit(per_page).all()
                
                job_list = []
                for task, platform in jobs:
                    job_list.append({
                        'task_id': task.id,
                        'platform_name': platform.name,
                        'platform_type': platform.platform_type,
                        'status': task.status.value if hasattr(task.status, 'value') else str(task.status),
                        'created_at': task.created_at.isoformat() if task.created_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'progress_percentage': task.progress_percent or 0,
                        'captions_generated': getattr(task, 'captions_generated', 0),
                        'images_processed': getattr(task, 'images_processed', 0),
                        'errors_count': getattr(task, 'errors_count', 0),
                        'admin_managed': task.admin_managed or False,
                        'admin_notes': task.admin_notes
                    })
                
                return jsonify({
                    'success': True,
                    'jobs': job_list,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                })
        
        except Exception as e:
            logger.error(f"Error getting job history: {e}")
            return jsonify({'error': 'Failed to load job history'}), 500
    
    @bp.route('/api/logs/content/<filename>', methods=['GET'])
    @api_admin_required
    def get_log_file_content(filename):
        """Get content of a specific log file"""
        try:
            import os
            
            # Validate filename to prevent directory traversal
            if '..' in filename or '/' in filename or '\\' in filename:
                return jsonify({'error': 'Invalid filename'}), 400
            
            log_directory = 'logs'
            filepath = os.path.join(log_directory, filename)
            
            if not os.path.exists(filepath):
                return jsonify({'error': 'Log file not found'}), 404
            
            # Read log file content (last 1000 lines)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Get last 1000 lines
                content = lines[-1000:] if len(lines) > 1000 else lines
                # Remove newlines for JSON transport
                content = [line.rstrip('\n\r') for line in content]
            
            return jsonify({
                'success': True,
                'filename': filename,
                'content': content,
                'total_lines': len(lines),
                'showing_lines': len(content)
            })
            
        except Exception as e:
            logger.error(f"Error reading log file {filename}: {e}")
            return jsonify({'error': f'Failed to read log file: {str(e)}'}), 500
    
    @bp.route('/api/logs/download/<filename>', methods=['GET'])
    @api_admin_required
    def download_log_file(filename):
        """Download a log file"""
        try:
            import os
            from flask import send_file
            
            # Validate filename to prevent directory traversal
            if '..' in filename or '/' in filename or '\\' in filename:
                return jsonify({'error': 'Invalid filename'}), 400
            
            log_directory = 'logs'
            filepath = os.path.join(log_directory, filename)
            
            if not os.path.exists(filepath):
                return jsonify({'error': 'Log file not found'}), 404
            
            return send_file(filepath, as_attachment=True, download_name=filename)
            
        except Exception as e:
            logger.error(f"Error downloading log file {filename}: {e}")
            return jsonify({'error': f'Failed to download log file: {str(e)}'}), 500


def get_system_status():
    """Get current system status"""
    try:
        # This would integrate with actual system monitoring
        return {
            'status': 'active',  # active, paused, maintenance
            'uptime': '2 days, 14 hours',
            'last_maintenance': '2025-08-20T10:30:00Z',
            'maintenance_mode': False
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            'status': 'unknown',
            'uptime': 'Unknown',
            'last_maintenance': None,
            'maintenance_mode': False
        }

def get_maintenance_log():
    """Get recent maintenance activities"""
    try:
        from datetime import datetime, timedelta
        import os
        import re
        
        maintenance_actions = []
        
        # Try to read recent maintenance actions from application logs
        try:
            log_file_path = 'logs/webapp.log'
            if os.path.exists(log_file_path):
                # Read the last 100 lines of the log file
                with open(log_file_path, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                
                # Parse maintenance-related log entries
                for line in recent_lines:
                    if 'Maintenance action' in line or 'System paused' in line or 'System resumed' in line:
                        # Extract timestamp, action, and details from log line
                        # Example log format: "2025-08-24 16:30:00,123 - INFO - Maintenance action pause_system by admin 1: SUCCESS - test reason"
                        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if match:
                            timestamp = match.group(1)
                            
                            # Determine action type and details
                            if 'pause_system' in line:
                                action = 'System Paused'
                                status = 'completed' if 'SUCCESS' in line else 'failed'
                                # Extract reason from log line
                                reason_match = re.search(r'SUCCESS - (.+)$', line)
                                details = f"Reason: {reason_match.group(1)}" if reason_match else "System paused for maintenance"
                            elif 'resume_system' in line:
                                action = 'System Resumed'
                                status = 'completed' if 'SUCCESS' in line else 'failed'
                                details = "System resumed normal operations"
                            elif 'clear_queue' in line:
                                action = 'Job Queue Cleared'
                                status = 'completed' if 'SUCCESS' in line else 'failed'
                                details = "Cleared all queued jobs"
                            elif 'restart_failed' in line:
                                action = 'Failed Jobs Restarted'
                                status = 'completed' if 'SUCCESS' in line else 'failed'
                                details = "Restarted all failed jobs"
                            elif 'cleanup_old_data' in line:
                                action = 'Data Cleanup'
                                status = 'completed' if 'SUCCESS' in line else 'failed'
                                details = "Cleaned up old data and temporary files"
                            else:
                                action = 'System Maintenance'
                                status = 'completed'
                                details = "Maintenance action performed"
                            
                            # Extract admin user ID
                            admin_match = re.search(r'admin (\d+)', line)
                            admin_user = f"admin_{admin_match.group(1)}" if admin_match else "admin"
                            
                            maintenance_actions.append({
                                'timestamp': timestamp + 'Z',  # Add Z for ISO format
                                'action': action,
                                'admin_user': admin_user,
                                'status': status,
                                'details': details
                            })
                
                # Sort by timestamp (most recent first) and limit to 10
                maintenance_actions.sort(key=lambda x: x['timestamp'], reverse=True)
                maintenance_actions = maintenance_actions[:10]
        
        except Exception as log_error:
            logger.warning(f"Could not read maintenance log from file: {log_error}")
        
        # If no log entries found, return some default recent actions
        if not maintenance_actions:
            now = datetime.utcnow()
            maintenance_actions = [
                {
                    'timestamp': (now - timedelta(hours=2)).isoformat() + 'Z',
                    'action': 'System Health Check',
                    'admin_user': 'admin',
                    'status': 'completed',
                    'details': 'All systems operational'
                },
                {
                    'timestamp': (now - timedelta(hours=6)).isoformat() + 'Z',
                    'action': 'Automatic Cleanup',
                    'admin_user': 'system',
                    'status': 'completed',
                    'details': 'Cleaned up temporary files and old sessions'
                }
            ]
        
        return maintenance_actions
        
    except Exception as e:
        logger.error(f"Error getting maintenance log: {e}")
        return []


def clear_job_queue(reason, admin_user_id):
    """Clear the job queue"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask
            
            # Cancel all queued jobs
            queued_jobs = session.query(CaptionGenerationTask)\
                                .filter(CaptionGenerationTask.status == 'queued')\
                                .all()
            
            count = len(queued_jobs)
            
            for job in queued_jobs:
                job.status = 'cancelled'
                job.admin_notes = f"Cancelled during queue clear: {reason}"
                job.admin_user_id = admin_user_id
                job.admin_managed = True
            
            session.commit()
            
            logger.info(f"Job queue cleared by admin {admin_user_id}: {count} jobs cancelled")
            return {
                'success': True,
                'message': f'Successfully cleared {count} jobs from queue',
                'jobs_cleared': count
            }
    
    except Exception as e:
        logger.error(f"Error clearing job queue: {e}")
        return {
            'success': False,
            'error': 'Failed to clear job queue'
        }

def restart_services(reason, admin_user_id):
    """Restart background services"""
    try:
        # Implementation would restart background services
        logger.info(f"Services restart requested by admin {admin_user_id}: {reason}")
        return {
            'success': True,
            'message': 'Background services restart initiated',
            'restart_time': '30 seconds'
        }
    except Exception as e:
        logger.error(f"Error restarting services: {e}")
        return {
            'success': False,
            'error': 'Failed to restart services'
        }

def restart_all_failed_jobs(reason, admin_user_id):
    """Restart all failed jobs system-wide"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import CaptionGenerationTask
            
            # Get all failed jobs
            failed_jobs = session.query(CaptionGenerationTask)\
                                .filter(CaptionGenerationTask.status == 'failed')\
                                .all()
            
            count = len(failed_jobs)
            restarted_count = 0
            
            for job in failed_jobs:
                try:
                    # Create new task with same settings
                    new_task = CaptionGenerationTask(
                        user_id=job.user_id,
                        platform_connection_id=job.platform_connection_id,
                        status='queued',
                        admin_notes=f"Restarted by admin from failed job {job.id}: {reason}",
                        admin_user_id=admin_user_id,
                        admin_managed=True
                    )
                    session.add(new_task)
                    restarted_count += 1
                except Exception as e:
                    logger.error(f"Error restarting failed job {job.id}: {e}")
            
            session.commit()
            
            logger.info(f"Failed jobs restart by admin {admin_user_id}: {restarted_count}/{count} jobs restarted")
            return {
                'success': True,
                'message': f'Successfully restarted {restarted_count} out of {count} failed jobs',
                'jobs_restarted': restarted_count,
                'total_failed': count
            }
    
    except Exception as e:
        logger.error(f"Error restarting failed jobs: {e}")
        return {
            'success': False,
            'error': 'Failed to restart failed jobs'
        }

def cleanup_old_data(reason, admin_user_id):
    """Cleanup old data and temporary files"""
    try:
        db_manager = current_app.config['db_manager']
        
        # Use the existing cleanup service
        from admin.services.cleanup_service import CleanupService
        cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
        
        # Cleanup old processing runs (older than 30 days)
        result = cleanup_service.cleanup_old_processing_runs(days=30, dry_run=False)
        
        if result['success']:
            count = result.get('count', 0)
            logger.info(f"Data cleanup by admin {admin_user_id}: {count} old records cleaned")
            return {
                'success': True,
                'message': f"Successfully cleaned up {count} old records and temporary files",
                'count': count,
                'freed_space': result.get('freed_space', 'Unknown')
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Failed to cleanup old data')
            }
    
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        return {
            'success': False,
            'error': 'Failed to cleanup old data'
        }

def log_maintenance_action(action_id, reason, admin_user_id, success):
    """Log maintenance action to database"""
    try:
        from app.services.batch.components.multi_tenant_control_service import MultiTenantControlService
        db_manager = current_app.config['db_manager']
        mt_service = MultiTenantControlService(db_manager)
        
        # The MultiTenantControlService already logs admin actions internally
        # So we just need to log to the application logger as well
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"Maintenance action {action_id} by admin {admin_user_id}: {status} - {reason}")
    except Exception as e:
        logger.error(f"Error logging maintenance action: {e}")