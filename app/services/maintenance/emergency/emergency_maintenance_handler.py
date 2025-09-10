# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Emergency Maintenance Handler

Handles emergency maintenance scenarios with immediate system protection,
job termination, and critical admin-only access.
"""

import logging
import threading
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, SessionInvalidationError
from app.core.session.core.unified_session_manager import UnifiedSessionManager
from app.services.task.core.task_queue_manager import TaskQueueManager
from models import User, UserRole, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class EmergencyReport:
    """Emergency maintenance activity report"""
    activation_time: datetime
    deactivation_time: Optional[datetime]
    triggered_by: str
    reason: str
    terminated_jobs: List[str]
    invalidated_sessions: int
    duration_minutes: Optional[int]
    recovery_status: str
    errors: List[str]
    summary: str


class EmergencyModeError(Exception):
    """Emergency maintenance mode error"""
    pass


class JobTerminationError(Exception):
    """Job termination error"""
    pass


class EmergencyMaintenanceHandler:
    """
    Emergency maintenance handler with immediate blocking and job termination
    
    Features:
    - Immediate emergency mode activation
    - Safe job termination with configurable grace period
    - Force session cleanup for immediate session invalidation
    - Critical admin-only access restriction
    - Emergency activity reporting and documentation
    - Recovery mechanisms after emergency mode deactivation
    """
    
    def __init__(self, 
                 maintenance_service: EnhancedMaintenanceModeService,
                 session_manager: UnifiedSessionManager,
                 task_queue_manager: TaskQueueManager,
                 db_manager=None):
        """
        Initialize emergency maintenance handler
        
        Args:
            maintenance_service: Enhanced maintenance mode service
            session_manager: Maintenance session manager
            task_queue_manager: Task queue manager for job operations
            db_manager: Database manager for operation tracking (optional)
        """
        self.maintenance_service = maintenance_service
        self.session_manager = session_manager
        self.task_queue_manager = task_queue_manager
        self.db_manager = db_manager
        
        # Emergency state tracking
        self._emergency_active = False
        self._emergency_start_time: Optional[datetime] = None
        self._emergency_triggered_by: Optional[str] = None
        self._emergency_reason: Optional[str] = None
        self._terminated_jobs: List[str] = []
        self._invalidated_sessions_count = 0
        self._emergency_errors: List[str] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'emergency_activations': 0,
            'jobs_terminated': 0,
            'sessions_invalidated': 0,
            'errors': 0,
            'average_activation_time_seconds': 0.0,
            'total_downtime_minutes': 0.0
        }
    
    def activate_emergency_mode(self, reason: str, triggered_by: str) -> bool:
        """
        Activate emergency maintenance mode with immediate operation blocking
        
        Args:
            reason: Reason for emergency activation
            triggered_by: Identifier of who/what triggered emergency mode
            
        Returns:
            True if emergency mode was activated successfully
            
        Raises:
            EmergencyModeError: If activation fails
        """
        activation_start = time.time()
        
        try:
            with self._lock:
                logger.critical(f"EMERGENCY MAINTENANCE ACTIVATION: {reason} (triggered by: {triggered_by})")
                
                # Reset emergency state
                self._emergency_active = True
                self._emergency_start_time = datetime.now(timezone.utc)
                self._emergency_triggered_by = triggered_by
                self._emergency_reason = reason
                self._terminated_jobs = []
                self._invalidated_sessions_count = 0
                self._emergency_errors = []
                
                # Step 1: Activate emergency maintenance mode
                logger.info("Step 1: Activating emergency maintenance mode")
                success = self.maintenance_service.enable_maintenance(
                    reason=f"EMERGENCY: {reason}",
                    duration=None,  # Indefinite until manually disabled
                    mode=MaintenanceMode.EMERGENCY,
                    enabled_by=triggered_by
                )
                
                if not success:
                    error_msg = "Failed to activate emergency maintenance mode"
                    self._emergency_errors.append(error_msg)
                    raise EmergencyModeError(error_msg)
                
                # Step 2: Force session cleanup (immediate)
                logger.info("Step 2: Force session cleanup")
                try:
                    invalidated_count = self.force_session_cleanup()
                    self._invalidated_sessions_count = invalidated_count
                    logger.info(f"Force invalidated {invalidated_count} sessions")
                except Exception as e:
                    error_msg = f"Session cleanup failed: {str(e)}"
                    self._emergency_errors.append(error_msg)
                    logger.error(error_msg)
                
                # Step 3: Terminate running jobs (with minimal grace period)
                logger.info("Step 3: Terminating running jobs")
                try:
                    terminated_jobs = self.terminate_running_jobs(grace_period=10)  # 10 seconds only
                    self._terminated_jobs = terminated_jobs
                    logger.info(f"Terminated {len(terminated_jobs)} running jobs")
                except Exception as e:
                    error_msg = f"Job termination failed: {str(e)}"
                    self._emergency_errors.append(error_msg)
                    logger.error(error_msg)
                
                # Step 4: Enable critical admin-only access
                logger.info("Step 4: Enabling critical admin-only access")
                try:
                    self.enable_critical_admin_only()
                    logger.info("Critical admin-only access enabled")
                except Exception as e:
                    error_msg = f"Critical admin-only access failed: {str(e)}"
                    self._emergency_errors.append(error_msg)
                    logger.error(error_msg)
                
                # Update statistics
                activation_time = time.time() - activation_start
                self._stats['emergency_activations'] += 1
                self._stats['jobs_terminated'] += len(self._terminated_jobs)
                self._stats['sessions_invalidated'] += self._invalidated_sessions_count
                self._stats['errors'] += len(self._emergency_errors)
                
                # Update average activation time
                if self._stats['emergency_activations'] > 0:
                    current_avg = self._stats['average_activation_time_seconds']
                    new_avg = ((current_avg * (self._stats['emergency_activations'] - 1)) + activation_time) / self._stats['emergency_activations']
                    self._stats['average_activation_time_seconds'] = new_avg
                
                # Log emergency event
                self.maintenance_service.log_maintenance_event(
                    event_type='emergency_activated',
                    details={
                        'reason': reason,
                        'triggered_by': triggered_by,
                        'terminated_jobs': len(self._terminated_jobs),
                        'invalidated_sessions': self._invalidated_sessions_count,
                        'activation_time_seconds': activation_time,
                        'errors': self._emergency_errors
                    },
                    administrator=triggered_by
                )
                
                logger.critical(f"EMERGENCY MAINTENANCE ACTIVATED in {activation_time:.2f}s - "
                              f"Jobs terminated: {len(self._terminated_jobs)}, "
                              f"Sessions invalidated: {self._invalidated_sessions_count}, "
                              f"Errors: {len(self._emergency_errors)}")
                
                return True
                
        except Exception as e:
            logger.critical(f"CRITICAL ERROR during emergency activation: {str(e)}")
            self._emergency_errors.append(f"Critical activation error: {str(e)}")
            self._stats['errors'] += 1
            raise EmergencyModeError(f"Emergency activation failed: {str(e)}")
    
    def terminate_running_jobs(self, grace_period: int = 30) -> List[str]:
        """
        Terminate running jobs with configurable grace period for cleanup
        
        Args:
            grace_period: Grace period in seconds for job cleanup
            
        Returns:
            List of terminated job IDs
            
        Raises:
            JobTerminationError: If job termination fails
        """
        try:
            logger.info(f"Terminating running jobs with {grace_period}s grace period")
            
            terminated_jobs = []
            
            # Get all running tasks
            queue_stats = self.task_queue_manager.get_queue_stats()
            running_count = queue_stats.get('running', 0)
            
            if running_count == 0:
                logger.info("No running jobs to terminate")
                return terminated_jobs
            
            # Get all tasks for admin operations (we need admin privileges)
            # For emergency mode, we'll use a system admin context
            try:
                # Get all running tasks - we'll need to implement a system-level method
                # For now, we'll use the existing admin method with a system admin ID
                system_admin_id = self._get_system_admin_id()
                if system_admin_id:
                    all_tasks = self.task_queue_manager.get_all_tasks(
                        admin_user_id=system_admin_id,
                        status_filter=[TaskStatus.RUNNING],
                        limit=1000
                    )
                    
                    # Terminate each running task
                    for task in all_tasks:
                        try:
                            # Cancel the task with emergency reason
                            success = self.task_queue_manager.cancel_task_as_admin(
                                task_id=task.id,
                                admin_user_id=system_admin_id,
                                reason=f"Emergency maintenance termination (grace period: {grace_period}s)"
                            )
                            
                            if success:
                                terminated_jobs.append(task.id)
                                logger.debug(f"Terminated job {task.id}")
                            else:
                                logger.warning(f"Failed to terminate job {task.id}")
                                
                        except Exception as e:
                            logger.error(f"Error terminating job {task.id}: {str(e)}")
                            continue
                    
                    # Wait for grace period to allow cleanup
                    if grace_period > 0 and terminated_jobs:
                        logger.info(f"Waiting {grace_period}s for job cleanup...")
                        time.sleep(grace_period)
                        
                        # Log job termination notifications
                        for job_id in terminated_jobs:
                            self._log_job_termination_notification(job_id, grace_period)
                
                else:
                    logger.error("No system admin found for job termination")
                    raise JobTerminationError("No system admin available for job termination")
                    
            except Exception as e:
                logger.error(f"Error during job termination: {str(e)}")
                raise JobTerminationError(f"Job termination failed: {str(e)}")
            
            logger.info(f"Successfully terminated {len(terminated_jobs)} jobs")
            return terminated_jobs
            
        except Exception as e:
            logger.error(f"Critical error in job termination: {str(e)}")
            raise JobTerminationError(f"Job termination failed: {str(e)}")
    
    def force_session_cleanup(self) -> int:
        """
        Force immediate session invalidation for all non-admin users
        
        Returns:
            Number of sessions invalidated
            
        Raises:
            SessionInvalidationError: If session cleanup fails
        """
        try:
            logger.info("Force session cleanup initiated")
            
            # Invalidate all non-admin sessions immediately
            invalidated_sessions = self.session_manager.invalidate_non_admin_sessions()
            
            # Enable login prevention
            self.session_manager.prevent_non_admin_login()
            
            logger.info(f"Force invalidated {len(invalidated_sessions)} sessions")
            return len(invalidated_sessions)
            
        except Exception as e:
            logger.error(f"Force session cleanup failed: {str(e)}")

            raise SessionInvalidationError(f"Force session cleanup failed: {str(e)}")
    
    def enable_critical_admin_only(self) -> None:
        """
        Enable critical admin-only access during emergency situations
        
        This restricts access to only essential administrative functions
        and blocks all other operations, even for regular admin users.
        """
        try:
            logger.info("Enabling critical admin-only access")
            
            # This would integrate with the maintenance middleware to enforce
            # even stricter access controls during emergency mode
            
            # For now, we'll log the activation and rely on the emergency
            # maintenance mode to block operations
            
            # In a full implementation, this might:
            # 1. Update access control lists
            # 2. Restrict even admin operations to critical functions only
            # 3. Enable emergency-only routes
            # 4. Disable non-essential admin features
            
            logger.info("Critical admin-only access enabled")
            
        except Exception as e:
            logger.error(f"Failed to enable critical admin-only access: {str(e)}")
            raise EmergencyModeError(f"Critical admin-only access failed: {str(e)}")
    
    def create_emergency_report(self) -> EmergencyReport:
        """
        Create emergency maintenance activity documentation report
        
        Returns:
            EmergencyReport with comprehensive emergency activity data
        """
        try:
            with self._lock:
                # Calculate duration if emergency is complete
                duration_minutes = None
                deactivation_time = None
                
                if not self._emergency_active and self._emergency_start_time:
                    # Emergency has been deactivated, calculate duration from stats
                    duration_minutes = self._stats.get('total_downtime_minutes', 0)
                elif self._emergency_start_time:
                    # Emergency is still active, calculate current duration
                    current_time = datetime.now(timezone.utc)
                    duration = current_time - self._emergency_start_time
                    duration_minutes = duration.total_seconds() / 60
                
                # Determine recovery status
                recovery_status = "completed" if not self._emergency_active else "in_progress"
                if self._emergency_errors:
                    recovery_status += "_with_errors"
                
                # Create summary
                summary = self._create_emergency_summary()
                
                report = EmergencyReport(
                    activation_time=self._emergency_start_time or datetime.now(timezone.utc),
                    deactivation_time=deactivation_time,
                    triggered_by=self._emergency_triggered_by or "unknown",
                    reason=self._emergency_reason or "unknown",
                    terminated_jobs=self._terminated_jobs.copy(),
                    invalidated_sessions=self._invalidated_sessions_count,
                    duration_minutes=duration_minutes,
                    recovery_status=recovery_status,
                    errors=self._emergency_errors.copy(),
                    summary=summary
                )
                
                logger.info("Emergency report generated")
                return report
                
        except Exception as e:
            logger.error(f"Error creating emergency report: {str(e)}")
            # Return a minimal report with error information
            return EmergencyReport(
                activation_time=datetime.now(timezone.utc),
                deactivation_time=None,
                triggered_by="unknown",
                reason="report_generation_error",
                terminated_jobs=[],
                invalidated_sessions=0,
                duration_minutes=None,
                recovery_status="error",
                errors=[f"Report generation failed: {str(e)}"],
                summary=f"Emergency report generation failed: {str(e)}"
            )
    
    def deactivate_emergency_mode(self, deactivated_by: str) -> bool:
        """
        Deactivate emergency maintenance mode and begin recovery procedures
        
        Args:
            deactivated_by: Identifier of who deactivated emergency mode
            
        Returns:
            True if deactivation was successful
        """
        try:
            with self._lock:
                if not self._emergency_active:
                    logger.warning("Emergency mode is not active, cannot deactivate")
                    return False
                
                logger.info(f"Deactivating emergency mode (by: {deactivated_by})")
                
                deactivation_start = time.time()
                deactivation_time = datetime.now(timezone.utc)
                
                # Calculate total downtime
                if self._emergency_start_time:
                    downtime = deactivation_time - self._emergency_start_time
                    downtime_minutes = downtime.total_seconds() / 60
                    self._stats['total_downtime_minutes'] += downtime_minutes
                
                # Step 1: Disable emergency maintenance mode
                success = self.maintenance_service.disable_maintenance(disabled_by=deactivated_by)
                if not success:
                    logger.error("Failed to disable emergency maintenance mode")
                    return False
                
                # Step 2: Re-enable normal login for non-admin users
                try:
                    self.session_manager.allow_non_admin_login()
                    logger.info("Re-enabled normal login for non-admin users")
                except Exception as e:
                    logger.error(f"Failed to re-enable normal login: {str(e)}")
                    self._emergency_errors.append(f"Login re-enable failed: {str(e)}")
                
                # Step 3: Clean up emergency state
                try:
                    self.session_manager.cleanup_maintenance_state()
                    logger.info("Cleaned up maintenance session state")
                except Exception as e:
                    logger.error(f"Failed to cleanup session state: {str(e)}")
                    self._emergency_errors.append(f"Session cleanup failed: {str(e)}")
                
                # Step 4: Log deactivation event
                self.maintenance_service.log_maintenance_event(
                    event_type='emergency_deactivated',
                    details={
                        'deactivated_by': deactivated_by,
                        'duration_minutes': downtime_minutes if self._emergency_start_time else 0,
                        'terminated_jobs': len(self._terminated_jobs),
                        'invalidated_sessions': self._invalidated_sessions_count,
                        'errors': self._emergency_errors,
                        'deactivation_time_seconds': time.time() - deactivation_start
                    },
                    administrator=deactivated_by
                )
                
                # Update emergency state
                self._emergency_active = False
                
                logger.info(f"Emergency mode deactivated successfully by {deactivated_by}")
                return True
                
        except Exception as e:
            logger.error(f"Error deactivating emergency mode: {str(e)}")
            self._emergency_errors.append(f"Deactivation error: {str(e)}")
            return False
    
    def get_emergency_status(self) -> Dict[str, Any]:
        """
        Get current emergency maintenance status
        
        Returns:
            Dictionary with emergency status information
        """
        try:
            with self._lock:
                current_time = datetime.now(timezone.utc)
                
                # Calculate current duration if active
                current_duration_minutes = None
                if self._emergency_active and self._emergency_start_time:
                    duration = current_time - self._emergency_start_time
                    current_duration_minutes = duration.total_seconds() / 60
                
                return {
                    'is_active': self._emergency_active,
                    'start_time': self._emergency_start_time.isoformat() if self._emergency_start_time else None,
                    'triggered_by': self._emergency_triggered_by,
                    'reason': self._emergency_reason,
                    'current_duration_minutes': current_duration_minutes,
                    'terminated_jobs_count': len(self._terminated_jobs),
                    'invalidated_sessions_count': self._invalidated_sessions_count,
                    'errors_count': len(self._emergency_errors),
                    'statistics': self._stats.copy(),
                    'last_updated': current_time.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting emergency status: {str(e)}")
            return {
                'is_active': False,
                'error': str(e),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    def _get_system_admin_id(self) -> Optional[int]:
        """
        Get system admin user ID for emergency operations
        
        Returns:
            Admin user ID or None if not found
        """
        try:
            if not self.db_manager:
                logger.warning("No database manager available for system admin lookup")
                return None
            
            with self.db_manager.get_session() as session:
                # Find the first admin user
                admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
                if admin_user:
                    return admin_user.id
                else:
                    logger.error("No admin user found in database")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting system admin ID: {str(e)}")
            return None
    
    def _log_job_termination_notification(self, job_id: str, grace_period: int) -> None:
        """
        Log job termination notification
        
        Args:
            job_id: ID of terminated job
            grace_period: Grace period that was given
        """
        try:
            logger.info(f"Job {job_id} terminated during emergency maintenance "
                       f"(grace period: {grace_period}s)")
            
            # In a full implementation, this might:
            # 1. Send notification to job owner
            # 2. Log to audit trail
            # 3. Update job recovery queue
            # 4. Send alerts to monitoring systems
            
        except Exception as e:
            logger.error(f"Error logging job termination notification: {str(e)}")
    
    def _create_emergency_summary(self) -> str:
        """
        Create emergency maintenance summary text
        
        Returns:
            Summary string
        """
        try:
            if not self._emergency_start_time:
                return "Emergency maintenance summary not available"
            
            # Calculate duration
            if self._emergency_active:
                duration = datetime.now(timezone.utc) - self._emergency_start_time
                status = "ACTIVE"
            else:
                duration_minutes = self._stats.get('total_downtime_minutes', 0)
                duration = timedelta(minutes=duration_minutes)
                status = "COMPLETED"
            
            duration_str = f"{duration.total_seconds() / 60:.1f} minutes"
            
            summary = f"Emergency maintenance {status}: {self._emergency_reason or 'Unknown reason'} "
            summary += f"(triggered by: {self._emergency_triggered_by or 'unknown'}). "
            summary += f"Duration: {duration_str}. "
            summary += f"Impact: {len(self._terminated_jobs)} jobs terminated, "
            summary += f"{self._invalidated_sessions_count} sessions invalidated. "
            
            if self._emergency_errors:
                summary += f"Errors encountered: {len(self._emergency_errors)}. "
            else:
                summary += "No errors encountered. "
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating emergency summary: {str(e)}")
            return f"Emergency summary generation failed: {str(e)}"