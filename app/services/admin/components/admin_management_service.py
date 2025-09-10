# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Management Service for Multi-Tenant Caption Management

This service provides centralized administrative oversight capabilities for
caption generation jobs across all users in the system.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.core.database.core.database_manager import DatabaseManager
from models import (
    CaptionGenerationTask, TaskStatus, User, UserRole, PlatformConnection,
    JobPriority, SystemConfiguration, JobAuditLog
)
from app.services.task.core.task_queue_manager import TaskQueueManager
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

@dataclass
class SystemOverview:
    """System overview data for admin dashboard"""
    total_users: int
    active_users: int
    total_tasks: int
    active_tasks: int
    queued_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    system_health_score: float
    resource_usage: Dict[str, Any]
    recent_errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]

@dataclass
class JobDetails:
    """Detailed job information for admin inspection"""
    task_id: str
    user_id: int
    username: str
    platform_name: str
    status: str
    priority: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress_percent: int
    current_step: Optional[str]
    error_message: Optional[str]
    admin_notes: Optional[str]
    cancelled_by_admin: bool
    cancellation_reason: Optional[str]
    retry_count: int
    max_retries: int
    resource_usage: Optional[Dict[str, Any]]

@dataclass
class ErrorDiagnostics:
    """Error diagnostic information for troubleshooting"""
    task_id: str
    error_message: str
    error_category: str
    suggested_solutions: List[str]
    system_state: Dict[str, Any]
    related_logs: List[Dict[str, Any]]
    recovery_options: List[str]

@dataclass
class SystemSettings:
    """System configuration settings"""
    max_concurrent_tasks: int
    default_task_timeout: int
    cleanup_interval_hours: int
    max_retry_attempts: int
    enable_auto_recovery: bool
    maintenance_mode: bool
    rate_limit_per_user: int
    resource_limits: Dict[str, Any]

class AdminManagementService:
    """Centralized administrative oversight service for caption generation"""
    
    def __init__(self, db_manager: DatabaseManager, task_queue_manager: TaskQueueManager):
        self.db_manager = db_manager
        self.task_queue_manager = task_queue_manager
        
    def _verify_admin_authorization(self, session: Session, admin_user_id: int) -> User:
        """
        Verify that the user has admin authorization
        
        Args:
            session: Database session
            admin_user_id: User ID to verify
            
        Returns:
            User object if authorized
            
        Raises:
            ValueError: If user is not authorized
        """
        admin_user = session.query(User).filter_by(id=admin_user_id).first()
        if not admin_user:
            raise ValueError(f"User {admin_user_id} not found")
        
        if admin_user.role != UserRole.ADMIN:
            raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
        
        return admin_user
    
    def _log_admin_action(self, session: Session, admin_user_id: int, action: str, 
                         task_id: Optional[str] = None, details: Optional[str] = None):
        """Log administrative action for audit trail"""
        try:
            audit_log = JobAuditLog(
                task_id=task_id,
                user_id=None,  # Admin actions don't have a target user in this context
                admin_user_id=admin_user_id,
                action=action,
                details=details,
                timestamp=datetime.now(timezone.utc),
                ip_address=None,  # Could be passed from request context
                user_agent=None   # Could be passed from request context
            )
            session.add(audit_log)
            logger.info(f"Admin action logged: {sanitize_for_log(action)} by user {sanitize_for_log(str(admin_user_id))}")
        except Exception as e:
            logger.error(f"Failed to log admin action: {sanitize_for_log(str(e))}")
    
    def get_system_overview(self, admin_user_id: int) -> SystemOverview:
        """
        Get comprehensive system overview for admin dashboard
        
        Args:
            admin_user_id: Admin user ID requesting the overview
            
        Returns:
            SystemOverview object with dashboard data
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Get user statistics
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            
            # Get task statistics
            total_tasks = session.query(CaptionGenerationTask).count()
            active_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
            ).count()
            queued_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.QUEUED).count()
            running_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.RUNNING).count()
            completed_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.COMPLETED).count()
            failed_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.FAILED).count()
            cancelled_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.CANCELLED).count()
            
            # Calculate system health score (0-100)
            health_score = self._calculate_system_health_score(session)
            
            # Get resource usage
            resource_usage = self._get_resource_usage()
            
            # Get recent errors (last 24 hours)
            recent_errors = self._get_recent_errors(session, hours=24)
            
            # Get performance metrics
            performance_metrics = self._get_performance_metrics(session)
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "get_system_overview")
            session.commit()
            
            return SystemOverview(
                total_users=total_users,
                active_users=active_users,
                total_tasks=total_tasks,
                active_tasks=active_tasks,
                queued_tasks=queued_tasks,
                running_tasks=running_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                cancelled_tasks=cancelled_tasks,
                system_health_score=health_score,
                resource_usage=resource_usage,
                recent_errors=recent_errors,
                performance_metrics=performance_metrics
            )
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error getting system overview: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def get_user_job_details(self, admin_user_id: int, target_user_id: int, 
                           limit: int = 50) -> List[JobDetails]:
        """
        Get detailed job information for a specific user
        
        Args:
            admin_user_id: Admin user ID requesting the details
            target_user_id: User ID whose jobs to inspect
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobDetails objects
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Get user jobs with related data
            jobs_query = session.query(CaptionGenerationTask).join(User).join(PlatformConnection).filter(
                CaptionGenerationTask.user_id == target_user_id
            ).order_by(desc(CaptionGenerationTask.created_at)).limit(limit)
            
            job_details = []
            for task in jobs_query:
                # Parse resource usage if available
                resource_usage = None
                if task.resource_usage:
                    try:
                        import json
                        resource_usage = json.loads(task.resource_usage)
                    except (json.JSONDecodeError, TypeError):
                        resource_usage = None
                
                job_details.append(JobDetails(
                    task_id=task.id,
                    user_id=task.user_id,
                    username=task.user.username,
                    platform_name=task.platform_connection.name,
                    status=task.status.value,
                    priority=task.priority.value,
                    created_at=task.created_at,
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                    progress_percent=task.progress_percent,
                    current_step=task.current_step,
                    error_message=task.error_message,
                    admin_notes=task.admin_notes,
                    cancelled_by_admin=task.cancelled_by_admin,
                    cancellation_reason=task.cancellation_reason,
                    retry_count=task.retry_count,
                    max_retries=task.max_retries,
                    resource_usage=resource_usage
                ))
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "get_user_job_details", 
                                 details=f"target_user_id={target_user_id}")
            session.commit()
            
            return job_details
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error getting user job details: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def cancel_job_as_admin(self, admin_user_id: int, task_id: str, reason: str) -> bool:
        """
        Cancel a job as administrator with proper authorization and audit logging
        
        Args:
            admin_user_id: Admin user ID performing the cancellation
            task_id: Task ID to cancel
            reason: Reason for cancellation
            
        Returns:
            bool: True if job was cancelled successfully
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Use the task queue manager's admin cancellation method
            success = self.task_queue_manager.cancel_task_as_admin(task_id, admin_user_id, reason)
            
            # Log admin action regardless of success/failure
            action_details = f"reason={reason}, success={success}"
            self._log_admin_action(session, admin_user_id, "cancel_job_as_admin", 
                                 task_id=task_id, details=action_details)
            session.commit()
            
            if success:
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} cancelled job {sanitize_for_log(task_id)}")
            else:
                logger.warning(f"Admin {sanitize_for_log(str(admin_user_id))} failed to cancel job {sanitize_for_log(task_id)}")
            
            return success
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error cancelling job as admin: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def update_system_settings(self, admin_user_id: int, settings: SystemSettings) -> bool:
        """
        Update system-wide configuration settings
        
        Args:
            admin_user_id: Admin user ID performing the update
            settings: SystemSettings object with new configuration
            
        Returns:
            bool: True if settings were updated successfully
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Update system configuration settings
            settings_dict = asdict(settings)
            
            for key, value in settings_dict.items():
                # Handle nested dictionaries (like resource_limits)
                if isinstance(value, dict):
                    import json
                    value_str = json.dumps(value)
                    data_type = 'json'
                else:
                    value_str = str(value)
                    data_type = type(value).__name__
                
                # Get or create configuration entry
                config_entry = session.query(SystemConfiguration).filter_by(key=key).first()
                
                if config_entry:
                    config_entry.value = value_str
                    config_entry.updated_by = admin_user_id
                    config_entry.updated_at = datetime.now(timezone.utc)
                else:
                    config_entry = SystemConfiguration(
                        key=key,
                        value=value_str,
                        data_type=data_type,
                        category='system',
                        updated_by=admin_user_id,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(config_entry)
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "update_system_settings", 
                                 details=f"updated {len(settings_dict)} settings")
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} updated system settings")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating system settings: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def get_error_diagnostics(self, admin_user_id: int, task_id: str) -> ErrorDiagnostics:
        """
        Get comprehensive error diagnostics for a failed job
        
        Args:
            admin_user_id: Admin user ID requesting diagnostics
            task_id: Task ID to diagnose
            
        Returns:
            ErrorDiagnostics object with troubleshooting information
            
        Raises:
            ValueError: If user is not authorized or task not found
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Get the task
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            if not task.error_message:
                raise ValueError(f"Task {task_id} has no error message")
            
            # Categorize the error
            error_category = self._categorize_error(task.error_message)
            
            # Generate suggested solutions
            suggested_solutions = self._generate_error_solutions(error_category, task.error_message)
            
            # Get system state at time of error
            system_state = self._get_system_state_snapshot()
            
            # Get related audit logs
            related_logs = self._get_related_audit_logs(session, task_id)
            
            # Generate recovery options
            recovery_options = self._generate_recovery_options(task, error_category)
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "get_error_diagnostics", 
                                 task_id=task_id)
            session.commit()
            
            return ErrorDiagnostics(
                task_id=task_id,
                error_message=task.error_message,
                error_category=error_category,
                suggested_solutions=suggested_solutions,
                system_state=system_state,
                related_logs=related_logs,
                recovery_options=recovery_options
            )
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error getting error diagnostics: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def restart_failed_job(self, admin_user_id: int, task_id: str) -> str:
        """
        Restart a failed job for admin job recovery
        
        Args:
            admin_user_id: Admin user ID performing the restart
            task_id: Task ID to restart
            
        Returns:
            str: New task ID for the restarted job
            
        Raises:
            ValueError: If user is not authorized or task cannot be restarted
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Get the failed task
            failed_task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            if not failed_task:
                raise ValueError(f"Task {task_id} not found")
            
            if failed_task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                raise ValueError(f"Task {task_id} is not in a failed or cancelled state")
            
            # Create a new task based on the failed one
            new_task = CaptionGenerationTask(
                user_id=failed_task.user_id,
                platform_connection_id=failed_task.platform_connection_id,
                settings_json=failed_task.settings_json,
                priority=JobPriority.HIGH,  # Give restarted tasks higher priority
                admin_notes=f"Restarted by admin {admin_user_id} from failed task {task_id}",
                max_retries=failed_task.max_retries
            )
            
            # Enqueue the new task
            new_task_id = self.task_queue_manager.enqueue_task(new_task)
            
            # Update the original task to indicate it was restarted
            failed_task.admin_notes = (failed_task.admin_notes or "") + f"\nRestarted as task {new_task_id} by admin {admin_user_id}"
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "restart_failed_job", 
                                 task_id=task_id, details=f"new_task_id={new_task_id}")
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} restarted failed job {sanitize_for_log(task_id)} as {sanitize_for_log(new_task_id)}")
            return new_task_id
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error restarting failed job: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    # Helper methods for system overview and diagnostics
    
    def _calculate_system_health_score(self, session: Session) -> float:
        """Calculate overall system health score (0-100)"""
        try:
            # Get task statistics for the last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            recent_tasks = session.query(CaptionGenerationTask).filter(
                CaptionGenerationTask.created_at >= cutoff_time
            ).count()
            
            if recent_tasks == 0:
                return 100.0  # No recent activity, assume healthy
            
            successful_tasks = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.created_at >= cutoff_time,
                    CaptionGenerationTask.status == TaskStatus.COMPLETED
                )
            ).count()
            
            failed_tasks = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.created_at >= cutoff_time,
                    CaptionGenerationTask.status == TaskStatus.FAILED
                )
            ).count()
            
            # Calculate success rate
            success_rate = (successful_tasks / recent_tasks) * 100 if recent_tasks > 0 else 100
            
            # Adjust for system load (penalize if too many queued tasks)
            queued_tasks = session.query(CaptionGenerationTask).filter_by(status=TaskStatus.QUEUED).count()
            load_penalty = min(queued_tasks * 2, 20)  # Max 20 point penalty
            
            health_score = max(0, success_rate - load_penalty)
            return round(health_score, 1)
            
        except Exception as e:
            logger.error(f"Error calculating system health score: {sanitize_for_log(str(e))}")
            return 50.0  # Default to neutral score on error
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'active_connections': len(psutil.net_connections()),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except ImportError:
            # psutil not available, return basic info
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'active_connections': 0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'note': 'psutil not available for detailed metrics'
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
    
    def _get_recent_errors(self, session: Session, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent error information"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            failed_tasks = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at >= cutoff_time
                )
            ).order_by(desc(CaptionGenerationTask.completed_at)).limit(10).all()
            
            errors = []
            for task in failed_tasks:
                errors.append({
                    'task_id': task.id,
                    'user_id': task.user_id,
                    'error_message': task.error_message,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'retry_count': task.retry_count
                })
            
            return errors
            
        except Exception as e:
            logger.error(f"Error getting recent errors: {sanitize_for_log(str(e))}")
            return []
    
    def _get_performance_metrics(self, session: Session) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            # Calculate average task completion time for the last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            completed_tasks = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at >= cutoff_time,
                    CaptionGenerationTask.started_at.isnot(None)
                )
            ).all()
            
            if completed_tasks:
                completion_times = []
                for task in completed_tasks:
                    if task.started_at and task.completed_at:
                        duration = (task.completed_at - task.started_at).total_seconds()
                        completion_times.append(duration)
                
                avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            else:
                avg_completion_time = 0
            
            # Get queue statistics
            queue_stats = self.task_queue_manager.get_queue_stats()
            
            return {
                'avg_completion_time_seconds': round(avg_completion_time, 2),
                'completed_tasks_24h': len(completed_tasks),
                'queue_statistics': queue_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {sanitize_for_log(str(e))}")
            return {'error': str(e)}
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message for better diagnostics"""
        error_lower = error_message.lower()
        
        if 'connection' in error_lower or 'network' in error_lower:
            return 'network'
        elif 'timeout' in error_lower:
            return 'timeout'
        elif 'permission' in error_lower or 'unauthorized' in error_lower:
            return 'authorization'
        elif 'rate limit' in error_lower or 'too many requests' in error_lower:
            return 'rate_limit'
        elif 'database' in error_lower or 'sql' in error_lower:
            return 'database'
        elif 'ollama' in error_lower or 'ai' in error_lower or 'model' in error_lower:
            return 'ai_service'
        elif 'memory' in error_lower or 'resource' in error_lower:
            return 'resource'
        else:
            return 'unknown'
    
    def _generate_error_solutions(self, error_category: str, error_message: str) -> List[str]:
        """Generate suggested solutions based on error category"""
        solutions = {
            'network': [
                'Check network connectivity to the platform',
                'Verify platform instance URL is correct',
                'Check firewall settings',
                'Retry the operation after a brief delay'
            ],
            'timeout': [
                'Increase timeout settings',
                'Check system load and reduce concurrent tasks',
                'Verify AI service is responding',
                'Consider breaking large jobs into smaller batches'
            ],
            'authorization': [
                'Verify platform credentials are valid',
                'Check if access token has expired',
                'Ensure user has necessary permissions',
                'Re-authenticate with the platform'
            ],
            'rate_limit': [
                'Reduce request frequency',
                'Implement exponential backoff',
                'Check platform rate limit policies',
                'Consider upgrading platform account if applicable'
            ],
            'database': [
                'Check database connectivity',
                'Verify database schema is up to date',
                'Check for database locks or deadlocks',
                'Review database logs for additional details'
            ],
            'ai_service': [
                'Check if Ollama service is running',
                'Verify AI model is available',
                'Check AI service logs',
                'Restart AI service if necessary'
            ],
            'resource': [
                'Check system memory usage',
                'Reduce concurrent task limit',
                'Clear temporary files',
                'Consider upgrading system resources'
            ],
            'unknown': [
                'Review full error logs',
                'Check system status',
                'Try restarting the failed operation',
                'Contact system administrator if issue persists'
            ]
        }
        
        return solutions.get(error_category, solutions['unknown'])
    
    def _get_system_state_snapshot(self) -> Dict[str, Any]:
        """Get current system state for diagnostics"""
        try:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'database_status': 'connected',  # Could check actual connection
                'queue_stats': self.task_queue_manager.get_queue_stats(),
                'resource_usage': self._get_resource_usage()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_related_audit_logs(self, session: Session, task_id: str) -> List[Dict[str, Any]]:
        """Get audit logs related to a specific task"""
        try:
            logs = session.query(JobAuditLog).filter_by(task_id=task_id).order_by(
                desc(JobAuditLog.timestamp)
            ).limit(10).all()
            
            return [
                {
                    'action': log.action,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'admin_user_id': log.admin_user_id,
                    'details': log.details
                }
                for log in logs
            ]
        except Exception as e:
            logger.error(f"Error getting related audit logs: {sanitize_for_log(str(e))}")
            return []
    
    def _generate_recovery_options(self, task: CaptionGenerationTask, error_category: str) -> List[str]:
        """Generate recovery options for a failed task"""
        options = ['Restart the task with same settings']
        
        if task.retry_count < task.max_retries:
            options.append('Retry with automatic retry logic')
        
        if error_category == 'timeout':
            options.append('Restart with increased timeout settings')
        elif error_category == 'rate_limit':
            options.append('Restart with reduced processing speed')
        elif error_category == 'resource':
            options.append('Restart when system resources are available')
        
        options.extend([
            'Cancel the task permanently',
            'Modify task settings and restart',
            'Contact user for manual intervention'
        ])
        
        return options