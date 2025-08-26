# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin API Routes"""

from flask import jsonify, request
from flask_login import current_user
from models import UserRole
from ..security.admin_access_control import admin_api_required
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

def register_api_routes(bp):
    """Register admin API routes"""
    
    @bp.route('/api/clear_platform_context', methods=['POST'])
    @admin_api_required
    def clear_platform_context():
        """Clear platform context for admin users"""
        try:
            # Clear platform context from Redis session
            from redis_session_middleware import clear_session_platform
            success = clear_session_platform()
            
            if success:
                logger.info(f"Admin user {current_user.id} cleared platform context")
            else:
                logger.warning(f"Failed to clear platform context for admin user {current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Platform context cleared successfully'
            })
            
        except Exception as e:
            logger.error(f"Error clearing platform context for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to clear platform context'
            }), 500
    
    @bp.route('/api/system_stats', methods=['GET'])
    @admin_api_required
    def get_system_stats():
        """Get comprehensive system statistics for admin dashboard"""
        try:
            from .admin_access_control import get_admin_system_stats
            stats = get_admin_system_stats()
            
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting system stats for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve system statistics'
            }), 500
    
    @bp.route('/api/user_stats', methods=['GET'])
    @admin_api_required
    def get_user_stats():
        """Get user statistics for admin dashboard"""
        try:
            from flask import current_app
            session_manager = current_app.request_session_manager
            
            with session_manager.session_scope() as db_session:
                from models import User, UserRole
                from datetime import datetime, timedelta
                
                # Basic user counts
                total_users = db_session.query(User).count()
                active_users = db_session.query(User).filter_by(is_active=True).count()
                admin_users = db_session.query(User).filter_by(role=UserRole.ADMIN).count()
                viewer_users = db_session.query(User).filter_by(role=UserRole.VIEWER).count()
                
                # Status counts
                unverified_users = db_session.query(User).filter_by(email_verified=False).count()
                locked_users = db_session.query(User).filter_by(account_locked=True).count()
                
                # Recent activity
                yesterday = datetime.utcnow() - timedelta(days=1)
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                new_users_24h = db_session.query(User).filter(User.created_at >= yesterday).count()
                new_users_7d = db_session.query(User).filter(User.created_at >= week_ago).count()
                
                recent_logins = db_session.query(User).filter(
                    User.last_login >= yesterday
                ).count()
                
                stats = {
                    'total_users': total_users,
                    'active_users': active_users,
                    'admin_users': admin_users,
                    'viewer_users': viewer_users,
                    'unverified_users': unverified_users,
                    'locked_users': locked_users,
                    'new_users_24h': new_users_24h,
                    'new_users_7d': new_users_7d,
                    'recent_logins': recent_logins
                }
                
                return jsonify({
                    'success': True,
                    'stats': stats
                })
                
        except Exception as e:
            logger.error(f"Error getting user stats for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve user statistics'
            }), 500
    
    @bp.route('/api/platform_stats', methods=['GET'])
    @admin_api_required
    def get_platform_stats():
        """Get platform statistics for admin dashboard"""
        try:
            from flask import current_app
            session_manager = current_app.request_session_manager
            
            with session_manager.session_scope() as db_session:
                from models import PlatformConnection
                from sqlalchemy import func
                
                # Platform counts
                total_platforms = db_session.query(PlatformConnection).filter_by(is_active=True).count()
                
                # Platform types
                platform_types = db_session.query(
                    PlatformConnection.platform_type,
                    func.count(PlatformConnection.id).label('count')
                ).filter_by(is_active=True).group_by(PlatformConnection.platform_type).all()
                
                # Platforms by user
                platforms_per_user = db_session.query(
                    PlatformConnection.user_id,
                    func.count(PlatformConnection.id).label('count')
                ).filter_by(is_active=True).group_by(PlatformConnection.user_id).all()
                
                avg_platforms_per_user = sum(p.count for p in platforms_per_user) / len(platforms_per_user) if platforms_per_user else 0
                
                stats = {
                    'total_platforms': total_platforms,
                    'platform_types': {pt.platform_type: pt.count for pt in platform_types},
                    'avg_platforms_per_user': round(avg_platforms_per_user, 2)
                }
                
                return jsonify({
                    'success': True,
                    'stats': stats
                })
                
        except Exception as e:
            logger.error(f"Error getting platform stats for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve platform statistics'
            }), 500
    
    @bp.route('/api/alerts', methods=['GET'])
    @admin_api_required
    def get_alerts():
        """Get system alerts for admin dashboard"""
        try:
            from flask import current_app
            
            # Get alerts from error recovery manager if available
            alerts = []
            
            # Try to get alerts from error recovery manager
            try:
                from error_recovery_manager import ErrorRecoveryManager
                error_manager = getattr(current_app, 'error_recovery_manager', None)
                if error_manager:
                    notifications = error_manager.get_admin_notifications(unread_only=True)
                    for i, notification in enumerate(notifications):
                        alerts.append({
                            'id': f"error_{i}",
                            'title': f"{notification.get('category', 'System')} Alert",
                            'message': notification.get('message', 'System alert'),
                            'severity': notification.get('severity', 'warning').lower(),
                            'created_at': notification.get('timestamp', datetime.utcnow().isoformat()),
                            'component': notification.get('component', 'system')
                        })
            except Exception as e:
                logger.debug(f"Could not get error manager alerts: {e}")
            
            # Try to get alerts from session alerting system
            try:
                from session_alerting_system import SessionAlertingSystem
                session_alerting = getattr(current_app, 'session_alerting_system', None)
                if session_alerting:
                    session_alerts = session_alerting.get_recent_alerts(limit=10)
                    for alert in session_alerts:
                        alerts.append({
                            'id': f"session_{alert.id}",
                            'title': alert.title,
                            'message': alert.message,
                            'severity': alert.severity.value.lower(),
                            'created_at': alert.created_at.isoformat(),
                            'component': alert.component
                        })
            except Exception as e:
                logger.debug(f"Could not get session alerts: {e}")
            
            # If no alerts from managers, create some sample system status alerts
            if not alerts:
                from flask import current_app
                session_manager = current_app.request_session_manager
                
                with session_manager.session_scope() as db_session:
                    from models import User
                    from datetime import datetime, timedelta
                    
                    # Check for system health indicators
                    recent_time = datetime.utcnow() - timedelta(hours=1)
                    
                    # Check for recent user activity
                    recent_users = db_session.query(User).filter(
                        User.last_login >= recent_time
                    ).count()
                    
                    if recent_users == 0:
                        alerts.append({
                            'id': 'no_recent_activity',
                            'title': 'Low User Activity',
                            'message': 'No users have logged in within the last hour',
                            'severity': 'info',
                            'created_at': datetime.utcnow().isoformat(),
                            'component': 'user_activity'
                        })
            
            return jsonify({
                'success': True,
                'alerts': alerts
            })
            
        except Exception as e:
            logger.error(f"Error getting alerts for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve alerts'
            }), 500
    
    @bp.route('/api/notifications', methods=['GET'])
    @admin_api_required
    def get_notifications():
        """Get admin notifications (alias for alerts)"""
        # This is an alias for the alerts endpoint to handle the 404 error
        return get_alerts()
    
    @bp.route('/alerts/<alert_id>/acknowledge', methods=['POST'])
    @admin_api_required
    def acknowledge_alert(alert_id):
        """Acknowledge a system alert"""
        try:
            # For now, just return success since alerts are generated dynamically
            # In a real implementation, this would update an alerts database table
            logger.info(f"Alert {alert_id} acknowledged by admin {current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Alert acknowledged successfully'
            })
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id} for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to acknowledge alert'
            }), 500
    
    # Multi-Tenant Caption Management API Routes
    
    @bp.route('/api/system-metrics', methods=['GET'])
    @admin_api_required
    def get_system_metrics():
        """Get system metrics for multi-tenant caption management dashboard"""
        try:
            from web_caption_generation_service import WebCaptionGenerationService
            from system_monitor import SystemMonitor
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = WebCaptionGenerationService(db_manager)
            monitor = SystemMonitor(db_manager)
            
            # Get metrics from service
            metrics = service.get_system_metrics(current_user.id)
            
            # Get additional system health metrics
            system_health = monitor.get_system_health()
            performance_metrics = monitor.get_performance_metrics()
            
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
            
            return jsonify({
                'success': True,
                'metrics': combined_metrics
            })
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve system metrics'
            }), 500
    
    @bp.route('/api/jobs/active', methods=['GET'])
    @admin_api_required
    def get_active_jobs():
        """Get active caption generation jobs for admin dashboard"""
        try:
            from web_caption_generation_service import WebCaptionGenerationService
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = WebCaptionGenerationService(db_manager)
            
            jobs = service.get_all_active_jobs(current_user.id)
            
            return jsonify({
                'success': True,
                'jobs': jobs
            })
            
        except Exception as e:
            logger.error(f"Error getting active jobs: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve active jobs'
            }), 500
    

    
    @bp.route('/api/jobs/<task_id>/priority', methods=['PUT'])
    @admin_api_required
    def set_job_priority(task_id):
        """Set caption generation job priority as admin"""
        try:
            data = request.get_json()
            priority = data.get('priority', 'normal')
            
            from multi_tenant_control_service import MultiTenantControlService
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = MultiTenantControlService(db_manager)
            
            success = service.set_job_priority(current_user.id, task_id, priority)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Job priority set to {priority}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to set job priority'
                }), 400
                
        except Exception as e:
            logger.error(f"Error setting job priority for {task_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to set job priority'
            }), 500
    
    @bp.route('/api/jobs/<task_id>/restart', methods=['POST'])
    @admin_api_required
    def restart_job(task_id):
        """Restart a failed caption generation job as admin"""
        try:
            from admin_management_service import AdminManagementService
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = AdminManagementService(db_manager)
            
            new_task_id = service.restart_failed_job(current_user.id, task_id)
            
            if new_task_id:
                return jsonify({
                    'success': True,
                    'message': 'Job restarted successfully',
                    'new_task_id': new_task_id
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to restart job'
                }), 400
                
        except Exception as e:
            logger.error(f"Error restarting job {task_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to restart job'
            }), 500
    
    @bp.route('/api/jobs/<task_id>/details', methods=['GET'])
    @admin_api_required
    def get_job_details(task_id):
        """Get detailed caption generation job information"""
        try:
            from admin_management_service import AdminManagementService
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = AdminManagementService(db_manager)
            
            job_details = service.get_error_diagnostics(current_user.id, task_id)
            
            return jsonify({
                'success': True,
                'job': job_details
            })
            
        except Exception as e:
            logger.error(f"Error getting job details for {task_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve job details'
            }), 500
    

    
    # Job Management API Endpoints
    
    @bp.route('/api/jobs', methods=['GET'])
    @admin_api_required
    def get_all_jobs():
        """Get all caption generation jobs for admin management"""
        try:
            from web_caption_generation_service import WebCaptionGenerationService
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = WebCaptionGenerationService(db_manager)
            
            # Get query parameters for filtering
            status = request.args.get('status')
            user_id = request.args.get('user_id')
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            jobs = service.get_all_active_jobs(current_user.id)
            
            # Apply filters if provided
            if status:
                jobs = [job for job in jobs if job.get('status') == status]
            if user_id:
                jobs = [job for job in jobs if job.get('user_id') == int(user_id)]
            
            # Apply pagination
            total_jobs = len(jobs)
            jobs = jobs[offset:offset + limit]
            
            return jsonify({
                'success': True,
                'jobs': jobs,
                'total': total_jobs,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            logger.error(f"Error getting all jobs: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve jobs'
            }), 500
    
    @bp.route('/api/jobs/<task_id>/cancel', methods=['POST'])
    @admin_api_required
    def cancel_job_admin(task_id):
        """Cancel a caption generation job as admin"""
        try:
            # Validate input
            if not task_id:
                return jsonify({
                    'success': False,
                    'error': 'Task ID is required'
                }), 400
            
            data = request.get_json() or {}
            reason = data.get('reason', 'Cancelled by administrator')
            
            # Validate reason
            if not reason or len(reason.strip()) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Cancellation reason is required'
                }), 400
            
            if len(reason) > 500:
                return jsonify({
                    'success': False,
                    'error': 'Cancellation reason too long (max 500 characters)'
                }), 400
            
            from admin_management_service import AdminManagementService
            from task_queue_manager import TaskQueueManager
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            task_queue_manager = TaskQueueManager(db_manager)
            service = AdminManagementService(db_manager, task_queue_manager)
            
            success = service.cancel_job_as_admin(current_user.id, task_id, reason)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Job cancelled successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to cancel job'
                }), 400
                
        except ValueError as e:
            logger.warning(f"Invalid request to cancel job {task_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error cancelling job {task_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to cancel job'
            }), 500
    
    # System Metrics API Endpoints
    
    @bp.route('/api/metrics', methods=['GET'])
    @admin_api_required
    def get_system_metrics_detailed():
        """Get detailed system metrics for multi-tenant caption management dashboard"""
        try:
            from web_caption_generation_service import WebCaptionGenerationService
            from system_monitor import SystemMonitor
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            service = WebCaptionGenerationService(db_manager)
            monitor = SystemMonitor(db_manager)
            
            # Get metrics from service
            metrics = service.get_system_metrics(current_user.id)
            
            # Get additional system health metrics
            system_health = monitor.get_system_health()
            performance_metrics = monitor.get_performance_metrics()
            resource_usage = monitor.check_resource_usage()
            
            combined_metrics = {
                'job_metrics': {
                    'active_jobs': metrics.get('active_jobs', 0),
                    'queued_jobs': metrics.get('queued_jobs', 0),
                    'completed_today': metrics.get('completed_today', 0),
                    'failed_jobs': metrics.get('failed_jobs', 0),
                    'success_rate': metrics.get('success_rate', 0),
                    'error_rate': metrics.get('error_rate', 0),
                    'avg_processing_time': metrics.get('avg_processing_time', 0)
                },
                'system_health': {
                    'overall_score': system_health.overall_health_score,
                    'database_status': system_health.database_status,
                    'redis_status': system_health.redis_status,
                    'ai_service_status': system_health.ai_service_status,
                    'queue_health': system_health.queue_health
                },
                'performance': {
                    'cpu_usage_percent': performance_metrics.cpu_usage_percent,
                    'memory_usage_percent': performance_metrics.memory_usage_percent,
                    'disk_usage_percent': performance_metrics.disk_usage_percent,
                    'response_time_ms': performance_metrics.avg_response_time_ms,
                    'throughput_per_minute': performance_metrics.throughput_per_minute
                },
                'resource_usage': {
                    'cpu_percent': resource_usage.cpu_percent,
                    'memory_percent': resource_usage.memory_percent,
                    'memory_used_mb': resource_usage.memory_used_mb,
                    'memory_total_mb': resource_usage.memory_total_mb,
                    'disk_percent': resource_usage.disk_percent,
                    'disk_used_gb': resource_usage.disk_used_gb,
                    'disk_total_gb': resource_usage.disk_total_gb,
                    'database_connections': resource_usage.database_connections,
                    'redis_memory_mb': resource_usage.redis_memory_mb
                },
                'timestamp': performance_metrics.timestamp.isoformat()
            }
            
            return jsonify({
                'success': True,
                'metrics': combined_metrics
            })
            
        except Exception as e:
            logger.error(f"Error getting detailed system metrics: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve system metrics'
            }), 500
    
    @bp.route('/api/system-health', methods=['GET'])
    @admin_api_required
    def get_system_health():
        """Get system health status for monitoring dashboard"""
        try:
            from system_monitor import SystemMonitor
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            monitor = SystemMonitor(db_manager)
            
            health = monitor.get_system_health()
            
            return jsonify({
                'success': True,
                'health': {
                    'overall_score': health.overall_health_score,
                    'status': 'healthy' if health.overall_health_score >= 80 else 'degraded' if health.overall_health_score >= 60 else 'unhealthy',
                    'components': {
                        'database': {
                            'status': health.database_status,
                            'healthy': health.database_status == 'connected'
                        },
                        'redis': {
                            'status': health.redis_status,
                            'healthy': health.redis_status == 'connected'
                        },
                        'ai_service': {
                            'status': health.ai_service_status,
                            'healthy': health.ai_service_status == 'available'
                        },
                        'queue': {
                            'status': health.queue_health,
                            'healthy': health.queue_health == 'normal'
                        }
                    },
                    'timestamp': health.timestamp.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve system health'
            }), 500
    
    # Missing API Endpoints for Monitoring Dashboard
    
    @bp.route('/api/cleanup_tasks', methods=['POST'])
    @admin_api_required
    def cleanup_tasks():
        """Cleanup old tasks API endpoint"""
        try:
            data = request.get_json() or {}
            days = data.get('days', 30)
            dry_run = data.get('dry_run', True)
            
            from ..services.cleanup_service import CleanupService
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
            
            # Perform cleanup operation
            result = cleanup_service.cleanup_old_processing_runs(days=days, dry_run=dry_run)
            
            if result['success']:
                message = result['message']
                if dry_run:
                    message = f"DRY RUN: {message}"
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'details': result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Cleanup operation failed')
                }), 400
                
        except Exception as e:
            logger.error(f"Error in cleanup tasks API: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to perform cleanup operation'
            }), 500
    
    @bp.route('/api/user_activity', methods=['GET'])
    @admin_api_required
    def user_activity():
        """Get user activity data API endpoint"""
        try:
            days = int(request.args.get('days', 7))
            
            from flask import current_app
            session_manager = current_app.request_session_manager
            
            with session_manager.session_scope() as db_session:
                from models import User, UserSession, CaptionGenerationTask
                from datetime import datetime, timedelta
                from sqlalchemy import func, desc
                
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Get user activity statistics
                user_stats = db_session.query(
                    User.id,
                    User.username,
                    User.email,
                    User.last_login,
                    func.count(CaptionGenerationTask.id).label('task_count')
                ).outerjoin(
                    CaptionGenerationTask,
                    (CaptionGenerationTask.user_id == User.id) &
                    (CaptionGenerationTask.created_at >= start_date)
                ).group_by(User.id).order_by(desc(User.last_login)).limit(50).all()
                
                # Format activity data
                activity_data = []
                for stat in user_stats:
                    activity_data.append({
                        'user_id': stat.id,
                        'username': stat.username,
                        'email': stat.email,
                        'last_login': stat.last_login.isoformat() if stat.last_login else None,
                        'task_count': stat.task_count or 0,
                        'active_in_period': stat.task_count > 0 or (
                            stat.last_login and stat.last_login >= start_date
                        )
                    })
                
                return jsonify({
                    'success': True,
                    'activity': activity_data,
                    'period_days': days,
                    'total_users': len(activity_data)
                })
                
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve user activity data'
            }), 500
    
    @bp.route('/api/active_tasks', methods=['GET'])
    @admin_api_required
    def active_tasks():
        """Get active tasks for monitoring dashboard"""
        try:
            from ..services.monitoring_service import AdminMonitoringService
            from flask import current_app
            
            monitoring_service = AdminMonitoringService(current_app.config['db_manager'])
            tasks = monitoring_service.get_active_tasks(limit=20)
            
            return jsonify({
                'success': True,
                'tasks': tasks
            })
            
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve active tasks'
            }), 500
    
    @bp.route('/api/cancel_task/<task_id>', methods=['POST'])
    @admin_api_required
    def cancel_task(task_id):
        """Cancel a specific task"""
        try:
            data = request.get_json() or {}
            reason = data.get('reason', 'Cancelled by administrator')
            
            from admin_management_service import AdminManagementService
            from task_queue_manager import TaskQueueManager
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            task_queue_manager = TaskQueueManager(db_manager)
            service = AdminManagementService(db_manager, task_queue_manager)
            
            success = service.cancel_job_as_admin(current_user.id, task_id, reason)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Task {task_id[:8]}... cancelled successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to cancel task'
                }), 400
                
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to cancel task'
            }), 500

    # User Management API Endpoints
    
    @bp.route('/api/users/<int:user_id>/jobs', methods=['GET'])
    @admin_api_required
    def get_user_jobs(user_id):
        """Get caption generation jobs for a specific user"""
        try:
            # Validate user_id
            if user_id <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Invalid user ID'
                }), 400
            
            from admin_management_service import AdminManagementService
            from task_queue_manager import TaskQueueManager
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            task_queue_manager = TaskQueueManager(db_manager)
            service = AdminManagementService(db_manager, task_queue_manager)
            
            # Get query parameters
            limit = int(request.args.get('limit', 50))
            if limit > 200:  # Prevent excessive data retrieval
                limit = 200
            
            job_details = service.get_user_job_details(current_user.id, user_id, limit)
            
            # Convert job details to JSON-serializable format
            jobs = []
            for job in job_details:
                job_dict = {
                    'task_id': job.task_id,
                    'user_id': job.user_id,
                    'username': job.username,
                    'platform_name': job.platform_name,
                    'status': job.status,
                    'priority': job.priority,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'progress_percent': job.progress_percent,
                    'current_step': job.current_step,
                    'error_message': job.error_message,
                    'admin_notes': job.admin_notes,
                    'cancelled_by_admin': job.cancelled_by_admin,
                    'cancellation_reason': job.cancellation_reason,
                    'retry_count': job.retry_count,
                    'max_retries': job.max_retries,
                    'resource_usage': job.resource_usage
                }
                jobs.append(job_dict)
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'jobs': jobs,
                'total': len(jobs)
            })
            
        except ValueError as e:
            logger.warning(f"Invalid request to get user jobs for user {user_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error getting user jobs for user {user_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve user jobs'
            }), 500
    
    @bp.route('/api/users/<int:user_id>/limits', methods=['GET', 'PUT'])
    @admin_api_required
    def manage_user_limits(user_id):
        """Get or update job limits for a specific user"""
        if request.method == 'GET':
            try:
                # Validate user_id
                if user_id <= 0:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid user ID'
                    }), 400
                
                from multi_tenant_control_service import MultiTenantControlService
                from flask import current_app
                
                db_manager = current_app.config['db_manager']
                service = MultiTenantControlService(db_manager)
                
                limits = service.get_user_job_limits(user_id)
                
                return jsonify({
                    'success': True,
                    'user_id': user_id,
                    'limits': limits.to_dict()
                })
                
            except Exception as e:
                logger.error(f"Error getting user limits for user {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to retrieve user limits'
                }), 500
        
        elif request.method == 'PUT':
            try:
                # Validate user_id
                if user_id <= 0:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid user ID'
                    }), 400
                
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Request data is required'
                    }), 400
                
                # Validate limits data
                required_fields = ['max_concurrent_jobs', 'max_jobs_per_hour', 'max_jobs_per_day']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                    
                    if not isinstance(data[field], int) or data[field] < 0:
                        return jsonify({
                            'success': False,
                            'error': f'Invalid value for {field}: must be a non-negative integer'
                        }), 400
                
                # Validate optional fields
                if 'max_processing_time_minutes' in data:
                    if not isinstance(data['max_processing_time_minutes'], int) or data['max_processing_time_minutes'] <= 0:
                        return jsonify({
                            'success': False,
                            'error': 'max_processing_time_minutes must be a positive integer'
                        }), 400
                
                if 'enabled' in data:
                    if not isinstance(data['enabled'], bool):
                        return jsonify({
                            'success': False,
                            'error': 'enabled must be a boolean value'
                        }), 400
                
                from multi_tenant_control_service import MultiTenantControlService, UserJobLimits
                from flask import current_app
                
                db_manager = current_app.config['db_manager']
                service = MultiTenantControlService(db_manager)
                
                # Create UserJobLimits object from data
                limits = UserJobLimits.from_dict(data)
                
                success = service.set_user_job_limits(current_user.id, user_id, limits)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'User limits updated successfully',
                        'user_id': user_id,
                        'limits': limits.to_dict()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update user limits'
                    }), 400
                    
            except ValueError as e:
                logger.warning(f"Invalid request to update user limits for user {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            except Exception as e:
                logger.error(f"Error updating user limits for user {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to update user limits'
                }), 500
    
    # Configuration Management API Endpoints
    
    @bp.route('/api/config', methods=['GET', 'PUT'])
    @admin_api_required
    def system_config():
        """Get or update system configuration for multi-tenant caption management"""
        if request.method == 'GET':
            try:
                from admin_management_service import AdminManagementService
                from task_queue_manager import TaskQueueManager
                from flask import current_app
                
                db_manager = current_app.config['db_manager']
                task_queue_manager = TaskQueueManager(db_manager)
                service = AdminManagementService(db_manager, task_queue_manager)
                
                overview = service.get_system_overview(current_user.id)
                
                # Get additional configuration from multi-tenant service
                from multi_tenant_control_service import MultiTenantControlService
                mt_service = MultiTenantControlService(db_manager)
                
                rate_limits = mt_service.get_system_rate_limits()
                maintenance_mode = mt_service.is_maintenance_mode()
                maintenance_reason = mt_service.get_maintenance_reason()
                
                config = {
                    'system_overview': {
                        'total_users': overview.total_users,
                        'active_users': overview.active_users,
                        'total_tasks': overview.total_tasks,
                        'active_tasks': overview.active_tasks,
                        'system_health_score': overview.system_health_score
                    },
                    'rate_limits': rate_limits.to_dict(),
                    'maintenance': {
                        'enabled': maintenance_mode,
                        'reason': maintenance_reason
                    },
                    'performance_metrics': overview.performance_metrics,
                    'resource_usage': overview.resource_usage
                }
                
                return jsonify({
                    'success': True,
                    'config': config
                })
                
            except Exception as e:
                logger.error(f"Error getting system config: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to retrieve system configuration'
                }), 500
        
        elif request.method == 'PUT':
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'Configuration data is required'
                    }), 400
                
                from admin_management_service import AdminManagementService, SystemSettings
                from multi_tenant_control_service import MultiTenantControlService, RateLimits
                from task_queue_manager import TaskQueueManager
                from flask import current_app
                
                db_manager = current_app.config['db_manager']
                task_queue_manager = TaskQueueManager(db_manager)
                admin_service = AdminManagementService(db_manager, task_queue_manager)
                mt_service = MultiTenantControlService(db_manager)
                
                success_count = 0
                errors = []
                
                # Update rate limits if provided
                if 'rate_limits' in data:
                    try:
                        rate_limits = RateLimits.from_dict(data['rate_limits'])
                        if mt_service.configure_rate_limits(current_user.id, rate_limits):
                            success_count += 1
                        else:
                            errors.append('Failed to update rate limits')
                    except Exception as e:
                        errors.append(f'Invalid rate limits configuration: {str(e)}')
                
                # Update maintenance mode if provided
                if 'maintenance' in data:
                    maintenance_data = data['maintenance']
                    if 'enabled' in maintenance_data:
                        try:
                            if maintenance_data['enabled']:
                                reason = maintenance_data.get('reason', 'Maintenance mode enabled by administrator')
                                if mt_service.pause_system_jobs(current_user.id, reason):
                                    success_count += 1
                                else:
                                    errors.append('Failed to enable maintenance mode')
                            else:
                                if mt_service.resume_system_jobs(current_user.id):
                                    success_count += 1
                                else:
                                    errors.append('Failed to disable maintenance mode')
                        except Exception as e:
                            errors.append(f'Failed to update maintenance mode: {str(e)}')
                
                # Update system settings if provided
                if 'system_settings' in data:
                    try:
                        settings = SystemSettings(**data['system_settings'])
                        if admin_service.update_system_settings(current_user.id, settings):
                            success_count += 1
                        else:
                            errors.append('Failed to update system settings')
                    except Exception as e:
                        errors.append(f'Invalid system settings: {str(e)}')
                
                if success_count > 0 and len(errors) == 0:
                    return jsonify({
                        'success': True,
                        'message': f'Successfully updated {success_count} configuration sections'
                    })
                elif success_count > 0:
                    return jsonify({
                        'success': True,
                        'message': f'Partially updated {success_count} configuration sections',
                        'warnings': errors
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update configuration',
                        'details': errors
                    }), 400
                    
            except Exception as e:
                logger.error(f"Error updating system config: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to update system configuration'
                }), 500
    
    # Alert Management API Endpoints
    
    @bp.route('/api/alerts', methods=['GET'])
    @admin_api_required
    def get_system_alerts():
        """Get system alerts for multi-tenant caption management"""
        try:
            from alert_manager import AlertManager
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            config = current_app.config.get('config')
            alert_manager = AlertManager(db_manager, config)
            
            alerts = alert_manager.get_active_alerts()
            
            # Convert alerts to JSON-serializable format
            alert_list = []
            for alert in alerts:
                alert_dict = {
                    'id': alert.id,
                    'alert_type': alert.alert_type.value,
                    'severity': alert.severity.value,
                    'status': alert.status.value,
                    'title': alert.title,
                    'message': alert.message,
                    'created_at': alert.created_at.isoformat(),
                    'updated_at': alert.updated_at.isoformat(),
                    'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'escalated_at': alert.escalated_at.isoformat() if alert.escalated_at else None,
                    'acknowledged_by': alert.acknowledged_by,
                    'context': alert.context,
                    'metrics': alert.metrics,
                    'count': alert.count,
                    'escalation_level': alert.escalation_level
                }
                alert_list.append(alert_dict)
            
            return jsonify({
                'success': True,
                'alerts': alert_list,
                'total': len(alert_list)
            })
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve alerts'
            }), 500
    
    @bp.route('/api/alerts/<alert_id>/acknowledge', methods=['POST'])
    @admin_api_required
    def acknowledge_alert_detailed(alert_id):
        """Acknowledge a system alert with detailed logging"""
        try:
            # Validate alert_id
            if not alert_id:
                return jsonify({
                    'success': False,
                    'error': 'Alert ID is required'
                }), 400
            
            from alert_manager import AlertManager
            from flask import current_app
            
            db_manager = current_app.config['db_manager']
            config = current_app.config.get('config')
            alert_manager = AlertManager(db_manager, config)
            
            success = alert_manager.acknowledge_alert(current_user.id, alert_id)
            
            if success:
                logger.info(f"Alert {alert_id} acknowledged by admin {current_user.id}")
                return jsonify({
                    'success': True,
                    'message': 'Alert acknowledged successfully',
                    'alert_id': alert_id,
                    'acknowledged_by': current_user.id,
                    'acknowledged_at': datetime.now(timezone.utc).isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to acknowledge alert'
                }), 400
                
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id} for admin {current_user.id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to acknowledge alert'
            }), 500