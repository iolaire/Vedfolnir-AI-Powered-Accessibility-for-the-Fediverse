# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Transition Manager

Handles graceful transitions into and out of maintenance mode,
allowing running jobs to complete and providing status monitoring.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.services.maintenance.components.maintenance_mode_service import MaintenanceModeService, MaintenanceChangeEvent
from app.core.database.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class TransitionState(Enum):
    """Maintenance mode transition states"""
    NORMAL = "normal"
    ENTERING_MAINTENANCE = "entering_maintenance"
    IN_MAINTENANCE = "in_maintenance"
    EXITING_MAINTENANCE = "exiting_maintenance"


@dataclass
class RunningJobInfo:
    """Information about a running job"""
    job_id: str
    user_id: int
    started_at: datetime
    estimated_completion: Optional[datetime]
    job_type: str
    status: str


@dataclass
class TransitionStatus:
    """Status of maintenance mode transition"""
    state: TransitionState
    maintenance_enabled: bool
    running_jobs_count: int
    running_jobs: List[RunningJobInfo]
    transition_started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    can_complete_transition: bool
    blocking_jobs: List[str]


class MaintenanceModeTransitionManager:
    """
    Manages graceful transitions into and out of maintenance mode
    
    Features:
    - Allows running jobs to complete when entering maintenance
    - Immediate resumption when exiting maintenance
    - Status monitoring and reporting
    - Transition logging and audit trail
    - Configurable timeout for job completion
    """
    
    def __init__(self, maintenance_service: MaintenanceModeService, 
                 db_manager: DatabaseManager,
                 job_completion_timeout: int = 1800):  # 30 minutes default
        """
        Initialize transition manager
        
        Args:
            maintenance_service: Maintenance mode service instance
            db_manager: Database manager for job queries
            job_completion_timeout: Maximum time to wait for jobs to complete (seconds)
        """
        self.maintenance_service = maintenance_service
        self.db_manager = db_manager
        self.job_completion_timeout = job_completion_timeout
        
        # Transition state
        self._current_state = TransitionState.NORMAL
        self._transition_started_at: Optional[datetime] = None
        self._state_lock = threading.RLock()
        
        # Job monitoring
        self._running_jobs: Dict[str, RunningJobInfo] = {}
        self._jobs_lock = threading.RLock()
        
        # Transition callbacks
        self._transition_callbacks: Dict[str, Callable] = {}
        self._callbacks_lock = threading.RLock()
        
        # Subscribe to maintenance mode changes
        self.maintenance_service.subscribe_to_changes(self._handle_maintenance_change)
        
        # Start monitoring thread
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitor_transitions, daemon=True)
        self._monitoring_thread.start()
    
    def get_transition_status(self) -> TransitionStatus:
        """
        Get current transition status
        
        Returns:
            TransitionStatus object with current state
        """
        try:
            with self._state_lock:
                current_state = self._current_state
                transition_started = self._transition_started_at
            
            # Get current maintenance status
            maintenance_enabled = self.maintenance_service.is_maintenance_mode()
            
            # Get running jobs
            running_jobs = self._get_running_jobs()
            
            # Determine if transition can complete
            can_complete = self._can_complete_transition(current_state, running_jobs)
            
            # Get blocking jobs
            blocking_jobs = [job.job_id for job in running_jobs 
                           if current_state == TransitionState.ENTERING_MAINTENANCE]
            
            # Estimate completion time
            estimated_completion = None
            if current_state == TransitionState.ENTERING_MAINTENANCE and running_jobs:
                # Use the latest estimated completion from running jobs
                job_completions = [job.estimated_completion for job in running_jobs 
                                 if job.estimated_completion]
                if job_completions:
                    estimated_completion = max(job_completions)
            
            return TransitionStatus(
                state=current_state,
                maintenance_enabled=maintenance_enabled,
                running_jobs_count=len(running_jobs),
                running_jobs=running_jobs,
                transition_started_at=transition_started,
                estimated_completion=estimated_completion,
                can_complete_transition=can_complete,
                blocking_jobs=blocking_jobs
            )
            
        except Exception as e:
            logger.error(f"Error getting transition status: {str(e)}")
            return TransitionStatus(
                state=TransitionState.NORMAL,
                maintenance_enabled=False,
                running_jobs_count=0,
                running_jobs=[],
                transition_started_at=None,
                estimated_completion=None,
                can_complete_transition=True,
                blocking_jobs=[]
            )
    
    def force_transition_completion(self, reason: str = "Manual override") -> bool:
        """
        Force completion of maintenance mode transition
        
        Args:
            reason: Reason for forcing completion
            
        Returns:
            True if transition was forced successfully
        """
        try:
            with self._state_lock:
                current_state = self._current_state
                
                if current_state == TransitionState.ENTERING_MAINTENANCE:
                    # Force entry into maintenance mode
                    self._current_state = TransitionState.IN_MAINTENANCE
                    logger.warning(f"Forced maintenance mode entry: {reason}")
                    
                    # Notify callbacks
                    self._notify_transition_callbacks('forced_entry', {
                        'reason': reason,
                        'running_jobs': len(self._running_jobs)
                    })
                    
                    return True
                
                elif current_state == TransitionState.EXITING_MAINTENANCE:
                    # Force exit from maintenance mode
                    self._current_state = TransitionState.NORMAL
                    logger.warning(f"Forced maintenance mode exit: {reason}")
                    
                    # Notify callbacks
                    self._notify_transition_callbacks('forced_exit', {
                        'reason': reason
                    })
                    
                    return True
                
                else:
                    logger.info(f"No transition to force, current state: {current_state.value}")
                    return False
            
        except Exception as e:
            logger.error(f"Error forcing transition completion: {str(e)}")
            return False
    
    def subscribe_to_transitions(self, callback: Callable[[str, Dict[str, Any]], None]) -> str:
        """
        Subscribe to transition events
        
        Args:
            callback: Callback function (event_type, event_data)
            
        Returns:
            Subscription ID
        """
        import uuid
        subscription_id = str(uuid.uuid4())
        
        with self._callbacks_lock:
            self._transition_callbacks[subscription_id] = callback
        
        logger.debug(f"Added transition subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe_from_transitions(self, subscription_id: str) -> bool:
        """
        Remove transition subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._callbacks_lock:
            if subscription_id in self._transition_callbacks:
                del self._transition_callbacks[subscription_id]
                logger.debug(f"Removed transition subscription {subscription_id}")
                return True
        
        return False
    
    def shutdown(self):
        """Shutdown the transition manager"""
        self._monitoring_active = False
        if self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
    
    def _handle_maintenance_change(self, event: MaintenanceChangeEvent):
        """
        Handle maintenance mode change events
        
        Args:
            event: Maintenance change event
        """
        try:
            with self._state_lock:
                current_state = self._current_state
                
                if event.enabled and current_state == TransitionState.NORMAL:
                    # Entering maintenance mode
                    self._current_state = TransitionState.ENTERING_MAINTENANCE
                    self._transition_started_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Starting transition to maintenance mode: {event.reason}")
                    
                    # Check if we can complete immediately
                    running_jobs = self._get_running_jobs()
                    if not running_jobs:
                        self._current_state = TransitionState.IN_MAINTENANCE
                        logger.info("No running jobs, entering maintenance mode immediately")
                    
                    # Notify callbacks
                    self._notify_transition_callbacks('entering_maintenance', {
                        'reason': event.reason,
                        'running_jobs': len(running_jobs)
                    })
                
                elif not event.enabled and current_state in [TransitionState.IN_MAINTENANCE, TransitionState.ENTERING_MAINTENANCE]:
                    # Exiting maintenance mode
                    self._current_state = TransitionState.EXITING_MAINTENANCE
                    
                    logger.info("Starting transition out of maintenance mode")
                    
                    # Exit immediately (no jobs to wait for when exiting)
                    self._current_state = TransitionState.NORMAL
                    self._transition_started_at = None
                    
                    logger.info("Exited maintenance mode, normal operations resumed")
                    
                    # Notify callbacks
                    self._notify_transition_callbacks('exited_maintenance', {
                        'reason': 'Maintenance mode disabled'
                    })
            
        except Exception as e:
            logger.error(f"Error handling maintenance change: {str(e)}")
    
    def _monitor_transitions(self):
        """Monitor transition progress in background thread"""
        while self._monitoring_active:
            try:
                with self._state_lock:
                    current_state = self._current_state
                    transition_started = self._transition_started_at
                
                if current_state == TransitionState.ENTERING_MAINTENANCE:
                    # Check if jobs have completed
                    running_jobs = self._get_running_jobs()
                    
                    if not running_jobs:
                        # All jobs completed, enter maintenance mode
                        with self._state_lock:
                            self._current_state = TransitionState.IN_MAINTENANCE
                        
                        logger.info("All jobs completed, entered maintenance mode")
                        
                        # Notify callbacks
                        self._notify_transition_callbacks('entered_maintenance', {
                            'jobs_completed': True
                        })
                    
                    elif transition_started:
                        # Check for timeout
                        elapsed = (datetime.now(timezone.utc) - transition_started).total_seconds()
                        if elapsed > self.job_completion_timeout:
                            logger.warning(f"Maintenance transition timeout after {elapsed}s, forcing entry")
                            self.force_transition_completion("Timeout waiting for jobs to complete")
                
                # Sleep before next check
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in transition monitoring: {str(e)}")
                time.sleep(30)  # Longer sleep on error
    
    def _get_running_jobs(self) -> List[RunningJobInfo]:
        """
        Get list of currently running jobs
        
        Returns:
            List of RunningJobInfo objects
        """
        try:
            with self.db_manager.get_session() as session:
                # Query for running jobs (this would need to be adapted to your job model)
                # For now, return empty list as placeholder
                # In a real implementation, you would query your job/task table
                
                # Example query (adapt to your models):
                # from models import CaptionGenerationTask
                # running_tasks = session.query(CaptionGenerationTask).filter(
                #     CaptionGenerationTask.status.in_(['running', 'processing'])
                # ).all()
                
                # For now, return empty list
                return []
                
        except Exception as e:
            logger.error(f"Error getting running jobs: {str(e)}")
            return []
    
    def _can_complete_transition(self, state: TransitionState, running_jobs: List[RunningJobInfo]) -> bool:
        """
        Check if transition can be completed
        
        Args:
            state: Current transition state
            running_jobs: List of running jobs
            
        Returns:
            True if transition can complete
        """
        if state == TransitionState.ENTERING_MAINTENANCE:
            return len(running_jobs) == 0
        elif state == TransitionState.EXITING_MAINTENANCE:
            return True  # Exit can always complete immediately
        else:
            return True
    
    def _notify_transition_callbacks(self, event_type: str, event_data: Dict[str, Any]):
        """
        Notify transition callbacks
        
        Args:
            event_type: Type of transition event
            event_data: Event data
        """
        with self._callbacks_lock:
            for subscription_id, callback in self._transition_callbacks.items():
                try:
                    callback(event_type, event_data)
                except Exception as e:
                    logger.error(f"Error in transition callback {subscription_id}: {str(e)}")