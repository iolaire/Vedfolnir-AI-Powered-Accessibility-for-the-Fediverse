# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Monitoring Routes for Admin Dashboard

Provides admin interface for monitoring Redis Queue statistics,
managing queues, and viewing task performance metrics.
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import render_template, jsonify, request, current_app
from flask_login import login_required, current_user

from app.core.security.core.security_utils import sanitize_for_log
from app.utils.decorators import admin_required
from models import UserRole

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register RQ monitoring routes"""
    
    @bp.route('/rq-monitoring')
    @login_required
    @admin_required
    def rq_monitoring_dashboard():
        """RQ monitoring dashboard page"""
        try:
            # Get RQ queue manager if available
            rq_manager = getattr(current_app, 'rq_queue_manager', None)
            
            if not rq_manager:
                return render_template('admin/rq_monitoring_dashboard.html', 
                                     error="RQ system not initialized")
            
            # Get queue statistics
            queue_stats = rq_manager.get_queue_stats()
            health_status = rq_manager.get_health_status()
            
            # Get recent task performance metrics
            performance_metrics = _get_performance_metrics()
            
            return render_template('admin/rq_monitoring_dashboard.html',
                                 queue_stats=queue_stats,
                                 health_status=health_status,
                                 performance_metrics=performance_metrics)
                                 
        except Exception as e:
            logger.error(f"Error loading RQ monitoring dashboard: {sanitize_for_log(str(e))}")
            return render_template('admin/rq_monitoring_dashboard.html', 
                                 error=f"Failed to load RQ monitoring data: {str(e)}")
    
    @bp.route('/rq-task-management')
    @login_required
    @admin_required
    def rq_task_management():
        """RQ task management page"""
        return render_template('admin/rq_task_management.html')
    
    @bp.route('/api/rq/queue-stats')
    @login_required
    @admin_required
    def api_queue_stats():
        """API endpoint for real-time queue statistics"""
        try:
            rq_manager = getattr(current_app, 'rq_queue_manager', None)
            
            if not rq_manager:
                return jsonify({
                    'success': False,
                    'error': 'RQ system not initialized'
                })
            
            # Get comprehensive queue statistics
            stats = rq_manager.get_queue_stats()
            health = rq_manager.get_health_status()
            
            # Add timestamp
            stats['timestamp'] = datetime.now(timezone.utc).isoformat()
            stats['health'] = health
            
            return jsonify({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/performance-metrics')
    @login_required
    @admin_required
    def api_performance_metrics():
        """API endpoint for RQ performance metrics"""
        try:
            metrics = _get_performance_metrics()
            
            return jsonify({
                'success': True,
                'data': metrics
            })
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/queue-management', methods=['POST'])
    @login_required
    @admin_required
    def api_queue_management():
        """API endpoint for queue management operations"""
        try:
            rq_manager = getattr(current_app, 'rq_queue_manager', None)
            
            if not rq_manager:
                return jsonify({
                    'success': False,
                    'error': 'RQ system not initialized'
                })
            
            action = request.json.get('action')
            queue_name = request.json.get('queue_name')
            
            if action == 'pause_queue':
                result = _pause_queue(rq_manager, queue_name)
            elif action == 'resume_queue':
                result = _resume_queue(rq_manager, queue_name)
            elif action == 'clear_queue':
                result = _clear_queue(rq_manager, queue_name)
            elif action == 'cleanup_completed':
                result = _cleanup_completed_jobs(rq_manager)
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unknown action: {action}'
                })
            
            # Log admin action
            logger.info(f"Admin {sanitize_for_log(str(current_user.id))} performed RQ action: {sanitize_for_log(action)} on queue: {sanitize_for_log(queue_name or 'all')}")
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in queue management: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/health-check')
    @login_required
    @admin_required
    def api_health_check():
        """API endpoint for RQ health check"""
        try:
            rq_manager = getattr(current_app, 'rq_queue_manager', None)
            
            if not rq_manager:
                return jsonify({
                    'success': False,
                    'error': 'RQ system not initialized'
                })
            
            # Force health check
            health_status = rq_manager.force_health_check()
            
            return jsonify({
                'success': True,
                'data': health_status
            })
            
        except Exception as e:
            logger.error(f"Error in health check: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/monitoring/metrics')
    @login_required
    @admin_required
    def api_monitoring_metrics():
        """API endpoint for RQ monitoring metrics"""
        try:
            monitoring_service = getattr(current_app, 'rq_monitoring_service', None)
            
            if not monitoring_service:
                return jsonify({
                    'success': False,
                    'error': 'RQ monitoring service not initialized'
                })
            
            # Get current metrics
            current_metrics = monitoring_service.get_current_metrics()
            
            # Get metrics history
            hours = request.args.get('hours', 24, type=int)
            metrics_history = monitoring_service.get_metrics_history(hours)
            
            return jsonify({
                'success': True,
                'data': {
                    'current': current_metrics.__dict__ if current_metrics else None,
                    'history': [m.__dict__ for m in metrics_history],
                    'monitoring_active': monitoring_service._monitoring_active
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting monitoring metrics: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/monitoring/alerts')
    @login_required
    @admin_required
    def api_monitoring_alerts():
        """API endpoint for RQ monitoring alerts"""
        try:
            monitoring_service = getattr(current_app, 'rq_monitoring_service', None)
            
            if not monitoring_service:
                return jsonify({
                    'success': False,
                    'error': 'RQ monitoring service not initialized'
                })
            
            # Get active alerts
            active_alerts = monitoring_service.get_active_alerts()
            
            return jsonify({
                'success': True,
                'data': {
                    'alerts': [alert.__dict__ for alert in active_alerts],
                    'count': len(active_alerts)
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting monitoring alerts: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/monitoring/alerts/<alert_id>/acknowledge', methods=['POST'])
    @login_required
    @admin_required
    def api_acknowledge_alert(alert_id):
        """API endpoint to acknowledge an alert"""
        try:
            monitoring_service = getattr(current_app, 'rq_monitoring_service', None)
            
            if not monitoring_service:
                return jsonify({
                    'success': False,
                    'error': 'RQ monitoring service not initialized'
                })
            
            # Acknowledge the alert
            success = monitoring_service.acknowledge_alert(alert_id)
            
            if success:
                logger.info(f"Admin {sanitize_for_log(str(current_user.id))} acknowledged RQ alert: {sanitize_for_log(alert_id)}")
                return jsonify({
                    'success': True,
                    'message': 'Alert acknowledged successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Alert not found'
                })
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/monitoring/health-summary')
    @login_required
    @admin_required
    def api_health_summary():
        """API endpoint for RQ health summary"""
        try:
            monitoring_service = getattr(current_app, 'rq_monitoring_service', None)
            
            if not monitoring_service:
                return jsonify({
                    'success': False,
                    'error': 'RQ monitoring service not initialized'
                })
            
            # Get health summary
            health_summary = monitoring_service.get_health_summary()
            
            return jsonify({
                'success': True,
                'data': health_summary
            })
            
        except Exception as e:
            logger.error(f"Error getting health summary: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/monitoring/thresholds', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def api_monitoring_thresholds():
        """API endpoint for managing monitoring thresholds"""
        try:
            monitoring_service = getattr(current_app, 'rq_monitoring_service', None)
            
            if not monitoring_service:
                return jsonify({
                    'success': False,
                    'error': 'RQ monitoring service not initialized'
                })
            
            if request.method == 'GET':
                # Get current thresholds
                thresholds = monitoring_service.get_thresholds()
                return jsonify({
                    'success': True,
                    'data': thresholds
                })
            
            elif request.method == 'POST':
                # Update thresholds
                new_thresholds = request.json
                if not new_thresholds:
                    return jsonify({
                        'success': False,
                        'error': 'No threshold data provided'
                    })
                
                monitoring_service.update_thresholds(new_thresholds)
                
                logger.info(f"Admin {sanitize_for_log(str(current_user.id))} updated RQ monitoring thresholds")
                
                return jsonify({
                    'success': True,
                    'message': 'Thresholds updated successfully'
                })
            
        except Exception as e:
            logger.error(f"Error managing thresholds: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/health/comprehensive')
    @login_required
    @admin_required
    def api_comprehensive_health_check():
        """API endpoint for comprehensive RQ health check"""
        try:
            # Import here to avoid circular imports
            from app.services.task.rq.rq_health_checker import RQHealthChecker
            
            # Get database manager from current app
            db_manager = current_app.config['db_manager']
            rq_manager = getattr(current_app, 'rq_queue_manager', None)
            
            # Create health checker
            health_checker = RQHealthChecker(db_manager, rq_manager)
            
            # Perform comprehensive health check
            health_result = health_checker.check_overall_health()
            
            return jsonify({
                'success': True,
                'data': health_result
            })
            
        except Exception as e:
            logger.error(f"Error in comprehensive health check: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/tasks')
    @login_required
    @admin_required
    def api_list_tasks():
        """API endpoint for listing RQ tasks with filtering"""
        try:
            # Get query parameters
            status_filter = request.args.get('status')
            priority_filter = request.args.get('priority')
            user_id_filter = request.args.get('user_id', type=int)
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            session = db_manager.get_session()
            try:
                from models import CaptionGenerationTask, TaskStatus, JobPriority, User
                
                # Build query
                query = session.query(CaptionGenerationTask).join(User)
                
                # Apply filters
                if status_filter:
                    try:
                        status_enum = TaskStatus(status_filter)
                        query = query.filter(CaptionGenerationTask.status == status_enum)
                    except ValueError:
                        pass  # Invalid status, ignore filter
                
                if priority_filter:
                    try:
                        priority_enum = JobPriority(priority_filter)
                        query = query.filter(CaptionGenerationTask.priority == priority_enum)
                    except ValueError:
                        pass  # Invalid priority, ignore filter
                
                if user_id_filter:
                    query = query.filter(CaptionGenerationTask.user_id == user_id_filter)
                
                # Get total count
                total_count = query.count()
                
                # Apply pagination and ordering
                tasks = query.order_by(
                    CaptionGenerationTask.created_at.desc()
                ).offset(offset).limit(limit).all()
                
                # Format task data
                task_data = []
                for task in tasks:
                    user = session.query(User).filter_by(id=task.user_id).first()
                    
                    task_info = {
                        'task_id': task.id,
                        'user_id': task.user_id,
                        'username': user.username if user else 'Unknown',
                        'user_email': user.email if user else 'Unknown',
                        'status': task.status.value,
                        'priority': task.priority.value if task.priority else 'normal',
                        'created_at': task.created_at.isoformat() if task.created_at else None,
                        'started_at': task.started_at.isoformat() if task.started_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'progress_percentage': getattr(task, 'progress_percentage', 0),
                        'current_step': getattr(task, 'current_step', 'Initializing'),
                        'error_message': task.error_message,
                        'platform_connection_id': task.platform_connection_id,
                        'settings': task.settings or {}
                    }
                    
                    # Calculate duration if applicable
                    if task.started_at and task.completed_at:
                        duration = (task.completed_at - task.started_at).total_seconds()
                        task_info['duration_seconds'] = duration
                    
                    task_data.append(task_info)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'tasks': task_data,
                        'pagination': {
                            'total': total_count,
                            'limit': limit,
                            'offset': offset,
                            'has_more': offset + limit < total_count
                        }
                    }
                })
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error listing RQ tasks: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/tasks/<task_id>')
    @login_required
    @admin_required
    def api_get_task_details(task_id):
        """API endpoint for getting detailed task information"""
        try:
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            session = db_manager.get_session()
            try:
                from models import CaptionGenerationTask, User, PlatformConnection
                
                # Get task with related data
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    return jsonify({
                        'success': False,
                        'error': 'Task not found'
                    })
                
                # Get user information
                user = session.query(User).filter_by(id=task.user_id).first()
                
                # Get platform connection information
                platform_conn = None
                if task.platform_connection_id:
                    platform_conn = session.query(PlatformConnection).filter_by(
                        id=task.platform_connection_id
                    ).first()
                
                # Build detailed task information
                task_details = {
                    'task_id': task.id,
                    'user': {
                        'id': task.user_id,
                        'username': user.username if user else 'Unknown',
                        'email': user.email if user else 'Unknown',
                        'role': user.role.value if user and user.role else 'unknown'
                    },
                    'platform': {
                        'connection_id': task.platform_connection_id,
                        'name': platform_conn.platform_name if platform_conn else 'Unknown',
                        'type': platform_conn.platform_type if platform_conn else 'Unknown'
                    } if platform_conn else None,
                    'status': task.status.value,
                    'priority': task.priority.value if task.priority else 'normal',
                    'timestamps': {
                        'created_at': task.created_at.isoformat() if task.created_at else None,
                        'started_at': task.started_at.isoformat() if task.started_at else None,
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None
                    },
                    'progress': {
                        'percentage': getattr(task, 'progress_percentage', 0),
                        'current_step': getattr(task, 'current_step', 'Initializing'),
                        'images_processed': getattr(task, 'images_processed', 0),
                        'total_images': getattr(task, 'total_images', 0)
                    },
                    'settings': task.settings or {},
                    'error_info': {
                        'message': task.error_message,
                        'details': getattr(task, 'error_details', None)
                    } if task.error_message else None,
                    'admin_info': {
                        'cancelled_by_admin': getattr(task, 'cancelled_by_admin', False),
                        'admin_user_id': getattr(task, 'admin_user_id', None),
                        'cancellation_reason': getattr(task, 'cancellation_reason', None),
                        'admin_notes': getattr(task, 'admin_notes', None)
                    }
                }
                
                # Calculate duration if applicable
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    task_details['duration_seconds'] = duration
                elif task.started_at:
                    # Task is still running
                    from datetime import datetime, timezone
                    duration = (datetime.now(timezone.utc) - task.started_at).total_seconds()
                    task_details['current_duration_seconds'] = duration
                
                # Get RQ job information if available
                rq_manager = getattr(current_app, 'rq_queue_manager', None)
                if rq_manager and hasattr(rq_manager, 'queues'):
                    rq_job_info = _get_rq_job_info(rq_manager, task_id)
                    if rq_job_info:
                        task_details['rq_job'] = rq_job_info
                
                return jsonify({
                    'success': True,
                    'data': task_details
                })
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting task details: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/tasks/<task_id>/cancel', methods=['POST'])
    @login_required
    @admin_required
    def api_cancel_task(task_id):
        """API endpoint for cancelling a task"""
        try:
            data = request.get_json() or {}
            reason = data.get('reason', 'Cancelled by administrator')
            
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            # Try to cancel via RQ first, then fallback to database
            rq_manager = getattr(current_app, 'rq_queue_manager', None)
            success = False
            
            if rq_manager:
                # Try RQ cancellation (if implemented)
                try:
                    # This would use the task queue manager's cancel method
                    from app.services.task.core.task_queue_manager import TaskQueueManager
                    task_manager = TaskQueueManager(db_manager)
                    success = task_manager.cancel_task_as_admin(
                        task_id, 
                        current_user.id, 
                        reason
                    )
                except Exception as e:
                    logger.warning(f"RQ cancellation failed, trying database: {e}")
            
            if not success:
                # Fallback to direct database cancellation
                session = db_manager.get_session()
                try:
                    from models import CaptionGenerationTask, TaskStatus
                    from datetime import datetime, timezone
                    
                    task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                    
                    if not task:
                        return jsonify({
                            'success': False,
                            'error': 'Task not found'
                        })
                    
                    if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
                        return jsonify({
                            'success': False,
                            'error': f'Cannot cancel task with status: {task.status.value}'
                        })
                    
                    # Cancel the task
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now(timezone.utc)
                    task.cancelled_by_admin = True
                    task.admin_user_id = current_user.id
                    task.cancellation_reason = reason
                    
                    session.commit()
                    success = True
                    
                finally:
                    session.close()
            
            if success:
                logger.info(f"Admin {sanitize_for_log(str(current_user.id))} cancelled task {sanitize_for_log(task_id)}: {sanitize_for_log(reason)}")
                return jsonify({
                    'success': True,
                    'message': 'Task cancelled successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to cancel task'
                })
                
        except Exception as e:
            logger.error(f"Error cancelling task: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/tasks/<task_id>/retry', methods=['POST'])
    @login_required
    @admin_required
    def api_retry_task(task_id):
        """API endpoint for retrying a failed task"""
        try:
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            session = db_manager.get_session()
            try:
                from models import CaptionGenerationTask, TaskStatus
                from datetime import datetime, timezone
                
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    return jsonify({
                        'success': False,
                        'error': 'Task not found'
                    })
                
                if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    return jsonify({
                        'success': False,
                        'error': f'Cannot retry task with status: {task.status.value}'
                    })
                
                # Reset task for retry
                task.status = TaskStatus.QUEUED
                task.started_at = None
                task.completed_at = None
                task.error_message = None
                task.progress_percentage = 0
                task.current_step = None
                
                # Clear admin cancellation info
                task.cancelled_by_admin = False
                task.admin_user_id = None
                task.cancellation_reason = None
                
                # Add admin note about retry
                task.admin_notes = f"Retried by admin {current_user.id} at {datetime.now(timezone.utc).isoformat()}"
                
                session.commit()
                
                # Try to enqueue to RQ if available
                rq_manager = getattr(current_app, 'rq_queue_manager', None)
                if rq_manager:
                    try:
                        # This would re-enqueue the task to RQ
                        # Implementation depends on RQ queue manager interface
                        pass
                    except Exception as e:
                        logger.warning(f"Failed to enqueue retried task to RQ: {e}")
                
                logger.info(f"Admin {sanitize_for_log(str(current_user.id))} retried task {sanitize_for_log(task_id)}")
                
                return jsonify({
                    'success': True,
                    'message': 'Task queued for retry successfully'
                })
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error retrying task: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/tasks/<task_id>/priority', methods=['PUT'])
    @login_required
    @admin_required
    def api_update_task_priority(task_id):
        """API endpoint for updating task priority"""
        try:
            data = request.get_json()
            if not data or 'priority' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Priority is required'
                })
            
            new_priority = data['priority']
            
            # Validate priority
            from models import JobPriority
            try:
                priority_enum = JobPriority(new_priority)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid priority: {new_priority}'
                })
            
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            session = db_manager.get_session()
            try:
                from models import CaptionGenerationTask, TaskStatus
                
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    return jsonify({
                        'success': False,
                        'error': 'Task not found'
                    })
                
                if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
                    return jsonify({
                        'success': False,
                        'error': f'Cannot change priority of task with status: {task.status.value}'
                    })
                
                old_priority = task.priority.value if task.priority else 'normal'
                task.priority = priority_enum
                
                session.commit()
                
                logger.info(f"Admin {sanitize_for_log(str(current_user.id))} changed task {sanitize_for_log(task_id)} priority from {old_priority} to {new_priority}")
                
                return jsonify({
                    'success': True,
                    'message': f'Task priority updated to {new_priority}'
                })
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error updating task priority: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
    
    @bp.route('/api/rq/tasks/<task_id>/notes', methods=['PUT'])
    @login_required
    @admin_required
    def api_update_task_notes(task_id):
        """API endpoint for updating task admin notes"""
        try:
            data = request.get_json()
            if not data or 'notes' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Notes are required'
                })
            
            notes = data['notes']
            
            # Get database manager
            db_manager = current_app.config['db_manager']
            
            session = db_manager.get_session()
            try:
                from models import CaptionGenerationTask
                
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    return jsonify({
                        'success': False,
                        'error': 'Task not found'
                    })
                
                task.admin_notes = notes
                session.commit()
                
                logger.info(f"Admin {sanitize_for_log(str(current_user.id))} updated notes for task {sanitize_for_log(task_id)}")
                
                return jsonify({
                    'success': True,
                    'message': 'Task notes updated successfully'
                })
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error updating task notes: {sanitize_for_log(str(e))}")
            return jsonify({
                'success': False,
                'error': str(e)
            })


def _get_rq_job_info(rq_manager, task_id):
    """Get RQ job information for a task"""
    try:
        # This would query RQ for job information
        # Implementation depends on RQ queue manager interface
        
        for queue_name, queue in rq_manager.queues.items():
            try:
                job = queue.fetch_job(task_id)
                if job:
                    return {
                        'queue': queue_name,
                        'status': job.get_status(),
                        'created_at': job.created_at.isoformat() if job.created_at else None,
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                        'result': str(job.result) if job.result else None,
                        'exc_info': job.exc_info if hasattr(job, 'exc_info') else None
                    }
            except Exception:
                continue  # Job not in this queue
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting RQ job info: {sanitize_for_log(str(e))}")
        return None


def _get_performance_metrics():
    """Get RQ performance metrics from database"""
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from models import CaptionGenerationTask, TaskStatus
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        session = db_manager.get_session()
        try:
            # Calculate metrics for the last 24 hours
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Task completion metrics
            completed_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.COMPLETED,
                CaptionGenerationTask.completed_at >= since
            ).all()
            
            failed_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status == TaskStatus.FAILED,
                CaptionGenerationTask.completed_at >= since
            ).all()
            
            # Calculate processing times
            processing_times = []
            for task in completed_tasks:
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    processing_times.append(duration)
            
            # Calculate success rate
            total_completed = len(completed_tasks) + len(failed_tasks)
            success_rate = (len(completed_tasks) / total_completed * 100) if total_completed > 0 else 0
            
            # Calculate average processing time
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                'completed_tasks_24h': len(completed_tasks),
                'failed_tasks_24h': len(failed_tasks),
                'success_rate': round(success_rate, 2),
                'avg_processing_time': round(avg_processing_time, 2),
                'min_processing_time': min(processing_times) if processing_times else 0,
                'max_processing_time': max(processing_times) if processing_times else 0,
                'total_tasks_24h': total_completed,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {sanitize_for_log(str(e))}")
        return {
            'completed_tasks_24h': 0,
            'failed_tasks_24h': 0,
            'success_rate': 0,
            'avg_processing_time': 0,
            'min_processing_time': 0,
            'max_processing_time': 0,
            'total_tasks_24h': 0,
            'error': str(e)
        }


def _pause_queue(rq_manager, queue_name):
    """Pause a specific queue or all queues"""
    try:
        # Note: RQ doesn't have built-in pause functionality
        # This would need to be implemented by stopping workers
        # For now, return a placeholder response
        return {
            'success': True,
            'message': f'Queue pause requested for: {queue_name or "all queues"}',
            'note': 'Queue pausing requires worker management implementation'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _resume_queue(rq_manager, queue_name):
    """Resume a specific queue or all queues"""
    try:
        # Note: RQ doesn't have built-in resume functionality
        # This would need to be implemented by starting workers
        # For now, return a placeholder response
        return {
            'success': True,
            'message': f'Queue resume requested for: {queue_name or "all queues"}',
            'note': 'Queue resuming requires worker management implementation'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _clear_queue(rq_manager, queue_name):
    """Clear a specific queue"""
    try:
        if not hasattr(rq_manager, 'queues') or not rq_manager.queues:
            return {
                'success': False,
                'error': 'No queues available'
            }
        
        if queue_name and queue_name in rq_manager.queues:
            queue = rq_manager.queues[queue_name]
            cleared_count = len(queue)
            queue.empty()
            
            return {
                'success': True,
                'message': f'Cleared {cleared_count} jobs from {queue_name} queue'
            }
        else:
            # Clear all queues
            total_cleared = 0
            for name, queue in rq_manager.queues.items():
                count = len(queue)
                queue.empty()
                total_cleared += count
            
            return {
                'success': True,
                'message': f'Cleared {total_cleared} jobs from all queues'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _cleanup_completed_jobs(rq_manager):
    """Clean up completed jobs from all queues"""
    try:
        rq_manager.cleanup_completed_jobs()
        
        return {
            'success': True,
            'message': 'Completed job cleanup initiated'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }