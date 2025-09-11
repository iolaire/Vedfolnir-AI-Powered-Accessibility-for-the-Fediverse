# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Web Caption Generation Service

This is the main orchestration service for web-based caption generation.
It coordinates between the task queue, progress tracking, and caption generation components.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

from app.core.database.core.database_manager import DatabaseManager
from models import (
    CaptionGenerationTask, CaptionGenerationSettings, CaptionGenerationUserSettings,
    GenerationResults, TaskStatus, PlatformConnection, User, UserRole, JobPriority,
    JobAuditLog
)
from app.services.task.core.task_queue_manager import TaskQueueManager
from app.services.monitoring.progress.progress_tracker import ProgressTracker
from app.services.platform.adapters.platform_aware_caption_adapter import PlatformAwareCaptionAdapter
from app.core.security.core.security_utils import sanitize_for_log
from app.core.security.error_handling.error_recovery_manager import error_recovery_manager, handle_caption_error
from app.core.security.error_handling.enhanced_error_recovery_manager import EnhancedErrorRecoveryManager

logger = logging.getLogger(__name__)

class WebCaptionGenerationService:
    """Main orchestration service for web-based caption generation"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.task_queue_manager = TaskQueueManager(db_manager)
        self.progress_tracker = ProgressTracker(db_manager)
        self.enhanced_error_recovery = EnhancedErrorRecoveryManager()
        
        # Background task management
        self._background_tasks = set()
        self._shutdown_event = asyncio.Event()
        
    async def start_caption_generation(
        self, 
        user_id: int, 
        platform_connection_id: int,
        settings: Optional[CaptionGenerationSettings] = None
    ) -> str:
        """
        Start caption generation for a user and platform
        
        Args:
            user_id: The user ID
            platform_connection_id: The platform connection ID
            settings: Optional custom settings (uses user defaults if not provided)
            
        Returns:
            str: The task ID
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If task creation fails
        """
        try:
            # Check storage limits before starting caption generation
            await self._check_storage_limits_before_generation()
            
            # Check if user already has an active task first
            active_task = self.task_queue_manager.get_user_active_task(user_id)
            if active_task:
                raise ValueError(f"User {user_id} already has an active caption generation task: {active_task.id}")
            
            # Validate user and platform access
            await self._validate_user_platform_access(user_id, platform_connection_id)
            
            # Get or create settings
            if settings is None:
                settings = await self._get_user_settings(user_id, platform_connection_id)
            
            # Create task
            task = CaptionGenerationTask(
                user_id=user_id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.QUEUED
            )
            task.settings = settings
            
            # Enqueue the task
            task_id = self.task_queue_manager.enqueue_task(task)
            
            # Start background processing if not already running
            self._ensure_background_processor()
            
            # Trigger immediate processing of the task in a separate thread
            import threading
            def process_in_thread():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._process_next_task_immediately())
                finally:
                    loop.close()
            
            thread = threading.Thread(target=process_in_thread, daemon=True)
            thread.start()
            
            logger.info(f"Started caption generation task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start caption generation: {sanitize_for_log(str(e))}")
            raise
    
    def start_caption_generation_sync(
        self, 
        user_id: int, 
        platform_connection_id: int,
        settings: Optional[CaptionGenerationSettings] = None
    ) -> str:
        """Synchronous wrapper for start_caption_generation"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.start_caption_generation(user_id, platform_connection_id, settings)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync caption generation: {e}")
            raise
    
    async def _check_storage_limits_before_generation(self) -> None:
        """
        Check storage limits before caption generation and handle automatic re-enabling.
        
        This method implements requirements 5.3 and 5.4 by checking storage limits
        before each caption generation operation and automatically re-enabling when
        storage drops below the limit.
        
        Raises:
            ValueError: If storage limit is exceeded and generation should be blocked
        """
        try:
            from app.services.storage.components.storage_limit_enforcer import StorageLimitEnforcer, StorageCheckResult
            storage_enforcer = StorageLimitEnforcer()
            
            # Perform storage check which includes automatic re-enabling logic
            storage_check = storage_enforcer.check_storage_before_generation()
            
            if storage_check == StorageCheckResult.BLOCKED_LIMIT_EXCEEDED:
                logger.warning("Caption generation blocked due to storage limit exceeded")
                raise ValueError("Caption generation is temporarily unavailable due to storage limits. Storage limit has been reached.")
            elif storage_check == StorageCheckResult.BLOCKED_OVERRIDE_EXPIRED:
                logger.warning("Caption generation blocked due to expired storage override")
                raise ValueError("Caption generation is temporarily unavailable. Storage override has expired.")
            elif storage_check == StorageCheckResult.ERROR:
                logger.error("Storage check failed during caption generation")
                raise ValueError("Unable to verify storage availability. Please try again in a few moments.")
            elif storage_check == StorageCheckResult.ALLOWED:
                logger.debug("Storage check passed, caption generation allowed")
            
        except ImportError as e:
            logger.error(f"Storage limit enforcer not available: {e}")
            # Continue without storage checks if the module is not available
        except Exception as e:
            logger.error(f"Storage check error during caption generation: {sanitize_for_log(str(e))}")
            # Re-raise ValueError exceptions (these are expected blocking conditions)
            if isinstance(e, ValueError):
                raise
            # For other exceptions, log but don't block caption generation
            logger.warning("Continuing with caption generation despite storage check error")
    
    def get_generation_status(self, task_id: str, user_id: int = None, admin_access: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get the status of a caption generation task
        
        Args:
            task_id: The task ID
            user_id: Optional user ID for authorization
            
        Returns:
            Dict with task status information or None if not found
        """
        try:
            # Get task from queue manager
            task = self.task_queue_manager.get_task(task_id)
            
            if not task:
                return None
            
            # Authorization check (skip for admin access)
            if not admin_access and user_id is not None and task.user_id != user_id:
                logger.warning(f"User {sanitize_for_log(str(user_id))} attempted to access task {sanitize_for_log(task_id)} owned by user {sanitize_for_log(str(task.user_id))}")
                return None
            
            # Get progress information
            progress = self.progress_tracker.get_progress(task_id, user_id)
            
            # Build status response
            status = {
                'task_id': task.id,
                'status': task.status.value,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'progress_percent': task.progress_percent or 0,
                'current_step': task.current_step or 'Queued',
                'error_message': task.error_message
            }
            
            # Add progress details if available
            if progress:
                status['progress_details'] = progress.details
            
            # Add results if completed
            if task.results:
                status['results'] = task.results.to_dict()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting task status: {sanitize_for_log(str(e))}")
            return None
    
    def get_task_status(self, task_id: str, user_id: int = None, admin_access: bool = False) -> Optional[Dict[str, Any]]:
        """
        Wrapper method for get_generation_status to maintain API compatibility
        """
        return self.get_generation_status(task_id, user_id, admin_access)
    
    def cancel_generation(self, task_id: str, user_id: int) -> bool:
        """
        Cancel a caption generation task
        
        Args:
            task_id: The task ID to cancel
            user_id: The user ID for authorization
            
        Returns:
            bool: True if cancellation was successful
        """
        try:
            success = self.task_queue_manager.cancel_task(task_id, user_id)
            
            if success:
                logger.info(f"Cancelled task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling task: {sanitize_for_log(str(e))}")
            return False
    
    async def get_generation_results(self, task_id: str, user_id: int = None) -> Optional[GenerationResults]:
        """
        Get the results of a completed caption generation task
        
        Args:
            task_id: The task ID
            user_id: Optional user ID for authorization
            
        Returns:
            GenerationResults or None if not found or not completed
        """
        try:
            # Get task
            task = self.task_queue_manager.get_task(task_id)
            
            if not task:
                return None
            
            # Authorization check
            if user_id is not None and task.user_id != user_id:
                return None
            
            # Check if task is completed
            if not task.is_completed():
                return None
            
            return task.results
            
        except Exception as e:
            logger.error(f"Error getting task results: {sanitize_for_log(str(e))}")
            return None
    
    async def _validate_user_platform_access(self, user_id: int, platform_connection_id: int):
        """
        Validate that a user has access to a platform connection
        
        Args:
            user_id: The user ID
            platform_connection_id: The platform connection ID
            
        Raises:
            ValueError: If validation fails
        """
        session = self.db_manager.get_session()
        try:
            # Check if user exists and is active
            user = session.query(User).filter_by(id=user_id, is_active=True).first()
            if not user:
                raise ValueError(f"User {user_id} not found or inactive")
            
            # Check if platform connection exists and belongs to user
            platform_connection = session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not platform_connection:
                raise ValueError(f"Platform connection {platform_connection_id} not found or not accessible to user {user_id}")
            
            # Active task check is now done earlier in start_caption_generation
            
        finally:
            session.close()
    
    async def _get_user_settings(self, user_id: int, platform_connection_id: int) -> CaptionGenerationSettings:
        """
        Get user's caption generation settings for a platform
        
        Args:
            user_id: The user ID
            platform_connection_id: The platform connection ID
            
        Returns:
            CaptionGenerationSettings: User settings or defaults
        """
        session = self.db_manager.get_session()
        try:
            # Try to get user's custom settings
            user_settings = session.query(CaptionGenerationUserSettings).filter_by(
                user_id=user_id,
                platform_connection_id=platform_connection_id
            ).first()
            
            if user_settings:
                return user_settings.to_settings_dataclass()
            else:
                # Return default settings
                return CaptionGenerationSettings()
                
        finally:
            session.close()
    
    def _ensure_background_processor(self):
        """Ensure background task processor is running"""
        # Check if we already have a background processor running
        if not any(not task.done() for task in self._background_tasks):
            try:
                # Start new background processor
                task = asyncio.create_task(self._background_processor())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
                
                logger.info("Started background caption generation processor")
            except RuntimeError:
                # No event loop running, skip background processor
                logger.info("No event loop available, skipping background processor")
    
    async def _background_processor(self):
        """Background task processor that handles queued caption generation tasks"""
        logger.info("Background caption generation processor started")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Get next task from queue
                    task = self.task_queue_manager.get_next_task()
                    
                    if task:
                        # Process the task
                        await self._process_task(task)
                    else:
                        # No tasks available, wait a bit
                        await asyncio.sleep(1.0)
                        
                except Exception as e:
                    logger.error(f"Error in background processor: {sanitize_for_log(str(e))}")
                    await asyncio.sleep(5.0)  # Wait longer on error
                    
        except asyncio.CancelledError:
            logger.info("Background processor cancelled")
        except Exception as e:
            logger.error(f"Fatal error in background processor: {sanitize_for_log(str(e))}")
        finally:
            logger.info("Background caption generation processor stopped")
    
    @handle_caption_error(context={'operation': 'process_task'})
    async def _process_task(self, task: CaptionGenerationTask):
        """
        Process a single caption generation task
        
        Args:
            task: The task to process
        """
        task_id = task.id
        
        try:
            logger.info(f"Processing caption generation task {sanitize_for_log(task_id)}")
            
            # Check storage limits before processing task
            try:
                await self._check_storage_limits_before_generation()
            except ValueError as e:
                # Storage limit exceeded, fail the task
                logger.warning(f"Task {task_id} failed due to storage limits: {e}")
                self.task_queue_manager.fail_task(task_id, str(e))
                return
            
            # Get platform connection
            session = self.db_manager.get_session()
            try:
                platform_connection = session.query(PlatformConnection).filter_by(
                    id=task.platform_connection_id,
                    is_active=True
                ).first()
                
                if not platform_connection:
                    raise RuntimeError(f"Platform connection {task.platform_connection_id} not found or inactive")
                
                # Detach from session to avoid issues
                session.expunge(platform_connection)
                
            finally:
                session.close()
            
            # Create progress callback
            progress_callback = self.progress_tracker.create_progress_callback(task_id)
            
            # Create caption adapter
            adapter = PlatformAwareCaptionAdapter(platform_connection)
            
            # Generate captions
            results = await adapter.generate_captions_for_user(task.settings, progress_callback)
            results.task_id = task_id
            
            # Complete the task
            self.task_queue_manager.complete_task(task_id, success=True)
            
            # Complete progress tracking with enhanced notification
            self.progress_tracker.complete_progress(task_id, results)
            
            # Send completion notification with action buttons
            self.progress_tracker.send_caption_complete_notification(
                task.user_id, 
                task_id, 
                {
                    'captions_generated': results.captions_generated,
                    'images_processed': results.images_processed,
                    'processing_time': results.processing_time_seconds,
                    'success_rate': results.success_rate
                }
            )
            
            # Trigger review workflow integration
            self._trigger_review_workflow_integration(task_id, task.user_id, results)
            
            logger.info(f"Completed caption generation task {sanitize_for_log(task_id)}: {results.captions_generated} captions generated")
            
        except Exception as e:
            logger.error(f"Error processing task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
            
            # Handle error with enhanced recovery manager
            try:
                # Create enhanced error info with additional context
                enhanced_error_info = self.enhanced_error_recovery.create_enhanced_error_info(e, {
                    'task_id': task_id,
                    'operation': 'caption_generation',
                    'user_id': task.user_id,
                    'platform_connection_id': task.platform_connection_id
                })
                
                # Get user-friendly message and recovery suggestions
                user_message = self.enhanced_error_recovery._get_user_friendly_message(enhanced_error_info)
                recovery_suggestions = enhanced_error_info.recovery_suggestions
                
                # Mark task as failed with enhanced error information
                self.task_queue_manager.complete_task(task_id, success=False, error_message=user_message)
                
                # Update progress with enhanced error details
                error_details = {
                    'error': user_message,
                    'error_category': enhanced_error_info.category.value,
                    'escalation_level': enhanced_error_info.escalation_level.value,
                    'recovery_suggestions': recovery_suggestions,
                    'pattern_matched': enhanced_error_info.pattern_matched
                }
                
                # Use fail_progress method for proper error notification
                self.progress_tracker.fail_progress(task_id, user_message, error_details)
                
                # Send enhanced error notification with retry options
                self.progress_tracker.send_caption_error_notification(
                    task.user_id,
                    task_id,
                    user_message,
                    error_category=error_details.get('error_category'),
                    recovery_suggestions=error_details.get('recovery_suggestions', [])
                )
                
                # Check if admin escalation is needed
                if enhanced_error_info.escalation_level.value in ['high', 'critical']:
                    logger.warning(f"Task {sanitize_for_log(task_id)} failed with {enhanced_error_info.escalation_level.value} escalation level")
                
            except Exception as recovery_error:
                logger.error(f"Error in enhanced recovery handling: {sanitize_for_log(str(recovery_error))}")
                # Fallback to original error handling
                self.task_queue_manager.complete_task(task_id, success=False, error_message=str(e))
                self.progress_tracker.fail_progress(task_id, str(e), {'error': str(e)})
    
    async def shutdown(self):
        """Shutdown the service and clean up background tasks"""
        logger.info("Shutting down caption generation service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Caption generation service shutdown complete")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics
        
        Returns:
            Dict with service statistics
        """
        try:
            # Get queue stats
            queue_stats = self.task_queue_manager.get_queue_stats()
            
            # Get active progress sessions
            active_sessions = self.progress_tracker.get_active_progress_sessions()
            
            # Background task stats
            background_tasks_count = len([t for t in self._background_tasks if not t.done()])
            
            return {
                'queue_stats': queue_stats,
                'active_progress_sessions': len(active_sessions),
                'background_processors': background_tasks_count,
                'service_status': 'running' if not self._shutdown_event.is_set() else 'shutting_down'
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {sanitize_for_log(str(e))}")
            return {
                'error': 'Failed to get service statistics'
            }
    
    async def save_user_settings(
        self, 
        user_id: int, 
        platform_connection_id: int, 
        settings: CaptionGenerationSettings
    ) -> bool:
        """
        Save user's caption generation settings for a platform
        
        Args:
            user_id: The user ID
            platform_connection_id: The platform connection ID
            settings: The settings to save
            
        Returns:
            bool: True if settings were saved successfully
        """
        session = self.db_manager.get_session()
        try:
            # Get or create user settings record
            user_settings = session.query(CaptionGenerationUserSettings).filter_by(
                user_id=user_id,
                platform_connection_id=platform_connection_id
            ).first()
            
            if user_settings:
                # Update existing settings
                user_settings.update_from_dataclass(settings)
            else:
                # Create new settings record
                user_settings = CaptionGenerationUserSettings(
                    user_id=user_id,
                    platform_connection_id=platform_connection_id
                )
                user_settings.update_from_dataclass(settings)
                session.add(user_settings)
            
            session.commit()
            
            logger.info(f"Saved caption generation settings for user {sanitize_for_log(str(user_id))} platform {sanitize_for_log(str(platform_connection_id))}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error saving user settings: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    async def get_user_settings(
        self, 
        user_id: int, 
        platform_connection_id: int
    ) -> CaptionGenerationSettings:
        """
        Get user's caption generation settings for a platform
        
        Args:
            user_id: The user ID
            platform_connection_id: The platform connection ID
            
        Returns:
            CaptionGenerationSettings: User settings or defaults
        """
        return await self._get_user_settings(user_id, platform_connection_id)
    
    async def _process_next_task_immediately(self):
        """Process the next available task immediately"""
        try:
            task = self.task_queue_manager.get_next_task()
            if task:
                await self._process_task(task)
        except Exception as e:
            logger.error(f"Error in immediate task processing: {sanitize_for_log(str(e))}")
    
    def get_active_task_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the active task for a user (if any)
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict with active task information or None if no active task
        """
        try:
            # Get active task from task queue manager
            active_task = self.task_queue_manager.get_user_active_task(user_id)
            
            if not active_task:
                return None
            
            # Convert to dictionary for template compatibility
            task_info = {
                'task_id': active_task.id,
                'status': active_task.status.value,
                'created_at': active_task.created_at.isoformat() if active_task.created_at else None,
                'started_at': active_task.started_at.isoformat() if active_task.started_at else None,
                'progress_percent': active_task.progress_percent or 0,
                'current_step': active_task.current_step or 'Queued',
                'error_message': active_task.error_message
            }
            
            return task_info
            
        except Exception as e:
            logger.error(f"Error getting active task for user {sanitize_for_log(str(user_id))}: {sanitize_for_log(str(e))}")
            return None
    
    async def get_user_task_history(self, user_id: int, limit: int = 10) -> list:
        """
        Get task history for a user
        
        Args:
            user_id: The user ID
            limit: Maximum number of tasks to return
            
        Returns:
            List of task information dictionaries
        """
        try:
            tasks = self.task_queue_manager.get_user_task_history(user_id, limit)
            
            # Convert to dictionaries for JSON serialization
            task_history = []
            for task in tasks:
                task_info = {
                    'task_id': task.id,
                    'status': task.status.value,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'progress_percent': task.progress_percent or 0,
                    'current_step': task.current_step,
                    'error_message': task.error_message
                }
                
                # Add results if available
                if task.results:
                    task_info['results'] = task.results.to_dict()
                
                task_history.append(task_info)
            
            return task_history
            
        except Exception as e:
            logger.error(f"Error getting user task history: {sanitize_for_log(str(e))}")
            return []
    
    async def retry_failed_task(self, user_id: int, original_task_id: str, platform_connection_id: int) -> str:
        """
        Retry a failed task with the same settings
        
        Args:
            user_id: The user ID
            original_task_id: The original task ID to retry
            platform_connection_id: The platform connection ID
            
        Returns:
            str: The new task ID
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If task creation fails
        """
        try:
            # Check if user already has an active task
            active_task = self.task_queue_manager.get_user_active_task(user_id)
            if active_task:
                raise ValueError(f"User {user_id} already has an active caption generation task: {active_task.id}")
            
            # Get the original task
            original_task = self.task_queue_manager.get_task(original_task_id)
            if not original_task:
                raise ValueError(f"Original task {original_task_id} not found")
            
            # Verify task belongs to user
            if original_task.user_id != user_id:
                raise ValueError(f"Task {original_task_id} does not belong to user {user_id}")
            
            # Verify task is in a retryable state
            if original_task.status.value not in ['failed', 'cancelled']:
                raise ValueError(f"Task {original_task_id} is not in a retryable state (current status: {original_task.status.value})")
            
            # Validate user and platform access
            await self._validate_user_platform_access(user_id, platform_connection_id)
            
            # Use the original task's settings
            settings = original_task.settings
            if not settings:
                # Fallback to default settings if original task doesn't have settings
                settings = await self._get_user_settings(user_id, platform_connection_id)
            
            # Create new task with same settings
            task = CaptionGenerationTask(
                user_id=user_id,
                platform_connection_id=platform_connection_id,
                status=TaskStatus.QUEUED
            )
            task.settings = settings
            
            # Enqueue the task
            task_id = self.task_queue_manager.enqueue_task(task)
            
            # Start background processing if not already running
            self._ensure_background_processor()
            
            # Trigger immediate processing of the task in a separate thread
            import threading
            def process_in_thread():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._process_next_task_immediately())
                finally:
                    loop.close()
            
            thread = threading.Thread(target=process_in_thread, daemon=True)
            thread.start()
            
            logger.info(f"Retried task {sanitize_for_log(original_task_id)} as new task {sanitize_for_log(task_id)} for user {sanitize_for_log(str(user_id))}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to retry task: {sanitize_for_log(str(e))}")
            raise
    
    # Admin Methods
    
    def _verify_admin_authorization(self, session, admin_user_id: int) -> User:
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
    
    def _log_admin_action(self, session, admin_user_id: int, action: str, 
                         task_id: Optional[str] = None, details: Optional[str] = None):
        """Log administrative action for audit trail"""
        try:
            # Only log to JobAuditLog if we have a task_id and user_id
            # For general admin actions without a specific task, we'll just log to the application log
            if task_id:
                # Get the task to find the user_id
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                if task:
                    audit_log = JobAuditLog(
                        task_id=task_id,
                        user_id=task.user_id,
                        admin_user_id=admin_user_id,
                        action=action,
                        details=details,
                        timestamp=datetime.now(timezone.utc),
                        ip_address=None,  # Could be passed from request context
                        user_agent=None   # Could be passed from request context
                    )
                    session.add(audit_log)
            
            # Always log to application log
            logger.info(f"Admin action logged: {sanitize_for_log(action)} by user {sanitize_for_log(str(admin_user_id))}")
        except Exception as e:
            logger.error(f"Failed to log admin action: {sanitize_for_log(str(e))}")
    
    def get_all_active_jobs(self, admin_user_id: int) -> List[Dict[str, Any]]:
        """
        Get all active caption generation jobs for admin dashboard visibility
        
        Args:
            admin_user_id: Admin user ID requesting the jobs
            
        Returns:
            List of job information dictionaries
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Get all active tasks using the task queue manager
            active_tasks = self.task_queue_manager.get_all_tasks(
                admin_user_id, 
                status_filter=[TaskStatus.QUEUED, TaskStatus.RUNNING],
                limit=200
            )
            
            # Convert to dictionaries with additional information
            jobs = []
            for task in active_tasks:
                # Get progress information
                progress = self.progress_tracker.get_progress(task.id, admin_user_id)
                
                # Get user information
                user = session.query(User).filter_by(id=task.user_id).first()
                platform_connection = session.query(PlatformConnection).filter_by(id=task.platform_connection_id).first()
                
                job_info = {
                    'task_id': task.id,
                    'user_id': task.user_id,
                    'username': user.username if user else 'Unknown',
                    'platform_name': platform_connection.name if platform_connection else 'Unknown',
                    'platform_type': platform_connection.platform_type if platform_connection else 'Unknown',
                    'status': task.status.value,
                    'priority': task.priority.value if task.priority else 'normal',
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'progress_percent': task.progress_percent or 0,
                    'current_step': task.current_step or 'Queued',
                    'error_message': task.error_message,
                    'admin_notes': task.admin_notes,
                    'retry_count': task.retry_count or 0,
                    'max_retries': task.max_retries or 3
                }
                
                # Add progress details if available
                if progress:
                    job_info['progress_details'] = progress.details
                
                jobs.append(job_info)
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "get_all_active_jobs", 
                                 details=f"returned {len(jobs)} active jobs")
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} retrieved {len(jobs)} active jobs")
            return jobs
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error getting all active jobs: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def cancel_user_job(self, admin_user_id: int, task_id: str, reason: str) -> bool:
        """
        Cancel a user's job with admin authorization and audit logging
        
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
            self._log_admin_action(session, admin_user_id, "cancel_user_job", 
                                 task_id=task_id, details=action_details)
            session.commit()
            
            if success:
                logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} cancelled job {sanitize_for_log(task_id)}")
            else:
                logger.warning(f"Admin {sanitize_for_log(str(admin_user_id))} failed to cancel job {sanitize_for_log(task_id)}")
            
            return success
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error cancelling user job: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def get_system_metrics(self, admin_user_id: int) -> Dict[str, Any]:
        """
        Get system performance metrics for admin monitoring
        
        Args:
            admin_user_id: Admin user ID requesting the metrics
            
        Returns:
            Dict with system metrics and performance data
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Get queue statistics
            queue_stats = self.task_queue_manager.get_queue_statistics(admin_user_id)
            
            # Get service statistics
            service_stats = self.get_service_stats()
            
            # Get task completion metrics for the last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Use string comparison for datetime to avoid timezone issues
            completed_tasks_24h = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at.isnot(None),
                    CaptionGenerationTask.completed_at >= cutoff_time.replace(tzinfo=None)
                )
            ).count()
            
            failed_tasks_24h = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at.isnot(None),
                    CaptionGenerationTask.completed_at >= cutoff_time.replace(tzinfo=None)
                )
            ).count()
            
            # Calculate success rate
            total_completed_24h = completed_tasks_24h + failed_tasks_24h
            success_rate = (completed_tasks_24h / total_completed_24h * 100) if total_completed_24h > 0 else 100
            
            # Get average completion time
            completed_tasks = session.query(CaptionGenerationTask).filter(
                and_(
                    CaptionGenerationTask.status == TaskStatus.COMPLETED,
                    CaptionGenerationTask.completed_at.isnot(None),
                    CaptionGenerationTask.completed_at >= cutoff_time.replace(tzinfo=None),
                    CaptionGenerationTask.started_at.isnot(None)
                )
            ).all()
            
            completion_times = []
            for task in completed_tasks:
                if task.started_at and task.completed_at:
                    # Ensure both datetimes are timezone-aware for consistent comparison
                    started_at = task.started_at
                    completed_at = task.completed_at
                    
                    # Convert naive datetimes to timezone-aware
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                    if completed_at.tzinfo is None:
                        completed_at = completed_at.replace(tzinfo=timezone.utc)
                    
                    duration = (completed_at - started_at).total_seconds()
                    completion_times.append(duration)
            
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            # Get resource usage
            try:
                import psutil
                resource_usage = {
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                }
                
                # Try to get network connections, but handle permission errors
                try:
                    resource_usage['active_connections'] = len(psutil.net_connections())
                except (psutil.AccessDenied, PermissionError):
                    resource_usage['active_connections'] = 0
                    resource_usage['connections_note'] = 'Permission denied for network connections'
                    
            except ImportError:
                resource_usage = {
                    'cpu_percent': 0,
                    'memory_percent': 0,
                    'disk_percent': 0,
                    'active_connections': 0,
                    'note': 'psutil not available for detailed metrics'
                }
            
            metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'queue_statistics': queue_stats,
                'service_statistics': service_stats,
                'performance_metrics': {
                    'completed_tasks_24h': completed_tasks_24h,
                    'failed_tasks_24h': failed_tasks_24h,
                    'success_rate_percent': round(success_rate, 2),
                    'avg_completion_time_seconds': round(avg_completion_time, 2),
                    'total_tasks_processed_24h': total_completed_24h
                },
                'resource_usage': resource_usage
            }
            
            # Log admin action
            self._log_admin_action(session, admin_user_id, "get_system_metrics")
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} retrieved system metrics")
            return metrics
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error getting system metrics: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def get_job_history(self, admin_user_id: int, filters: Optional[Dict[str, Any]] = None, 
                       limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get job history with filtering and search capabilities for admin use
        
        Args:
            admin_user_id: Admin user ID requesting the history
            filters: Optional filters (user_id, status, date_range, platform_id)
            limit: Maximum number of jobs to return
            
        Returns:
            List of job history dictionaries
            
        Raises:
            ValueError: If user is not authorized
        """
        session = self.db_manager.get_session()
        try:
            # Verify admin authorization
            self._verify_admin_authorization(session, admin_user_id)
            
            # Build query with filters and explicit join conditions
            query = session.query(CaptionGenerationTask).join(
                User, CaptionGenerationTask.user_id == User.id
            ).join(PlatformConnection)
            
            if filters:
                # Filter by user ID
                if 'user_id' in filters and filters['user_id']:
                    query = query.filter(CaptionGenerationTask.user_id == filters['user_id'])
                
                # Filter by status
                if 'status' in filters and filters['status']:
                    if isinstance(filters['status'], list):
                        status_enums = [TaskStatus(s) for s in filters['status']]
                        query = query.filter(CaptionGenerationTask.status.in_(status_enums))
                    else:
                        query = query.filter(CaptionGenerationTask.status == TaskStatus(filters['status']))
                
                # Filter by platform connection ID
                if 'platform_connection_id' in filters and filters['platform_connection_id']:
                    query = query.filter(CaptionGenerationTask.platform_connection_id == filters['platform_connection_id'])
                
                # Filter by date range
                if 'date_from' in filters and filters['date_from']:
                    date_from = datetime.fromisoformat(filters['date_from'].replace('Z', '+00:00'))
                    query = query.filter(CaptionGenerationTask.created_at >= date_from)
                
                if 'date_to' in filters and filters['date_to']:
                    date_to = datetime.fromisoformat(filters['date_to'].replace('Z', '+00:00'))
                    query = query.filter(CaptionGenerationTask.created_at <= date_to)
                
                # Search by username
                if 'username' in filters and filters['username']:
                    query = query.filter(User.username.ilike(f"%{filters['username']}%"))
            
            # Order by creation date (newest first) and limit
            tasks = query.order_by(CaptionGenerationTask.created_at.desc()).limit(limit).all()
            
            # Convert to dictionaries
            job_history = []
            for task in tasks:
                # Parse resource usage if available
                resource_usage = None
                if task.resource_usage:
                    try:
                        import json
                        resource_usage = json.loads(task.resource_usage)
                    except (json.JSONDecodeError, TypeError):
                        resource_usage = None
                
                job_info = {
                    'task_id': task.id,
                    'user_id': task.user_id,
                    'username': task.user.username,
                    'platform_name': task.platform_connection.name,
                    'platform_type': task.platform_connection.platform_type,
                    'status': task.status.value,
                    'priority': task.priority.value if task.priority else 'normal',
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'progress_percent': task.progress_percent or 0,
                    'current_step': task.current_step,
                    'error_message': task.error_message,
                    'admin_notes': task.admin_notes,
                    'cancelled_by_admin': task.cancelled_by_admin or False,
                    'cancellation_reason': task.cancellation_reason,
                    'retry_count': task.retry_count or 0,
                    'max_retries': task.max_retries or 3,
                    'resource_usage': resource_usage
                }
                
                # Add results if available
                if task.results:
                    job_info['results'] = task.results.to_dict()
                
                job_history.append(job_info)
            
            # Log admin action
            filter_details = f"filters={filters}, returned {len(job_history)} jobs"
            self._log_admin_action(session, admin_user_id, "get_job_history", 
                                 details=filter_details)
            session.commit()
            
            logger.info(f"Admin {sanitize_for_log(str(admin_user_id))} retrieved job history with {len(job_history)} results")
            return job_history
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error getting job history: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def _trigger_review_workflow_integration(self, task_id: str, user_id: int, results: GenerationResults):
        """
        Trigger review workflow integration after job completion
        
        Args:
            task_id: The completed task ID
            user_id: The user ID
            results: The generation results
        """
        try:
            # Import here to avoid circular imports
            from caption_review_integration import CaptionReviewIntegration
            
            # Create review integration instance
            review_integration = CaptionReviewIntegration(self.db_manager)
            
            # Create review batch from completed task
            batch_info = review_integration.create_review_batch_from_task(task_id, user_id)
            
            if batch_info:
                logger.info(f"Created review batch for completed task {sanitize_for_log(task_id)} with {batch_info['total_images']} images")
                
                # Store review redirect information for the user
                self._store_review_redirect_info(user_id, task_id, batch_info)
            else:
                logger.warning(f"Failed to create review batch for task {sanitize_for_log(task_id)}")
                
        except Exception as e:
            logger.error(f"Error triggering review workflow integration: {sanitize_for_log(str(e))}")
    
    def _store_review_redirect_info(self, user_id: int, task_id: str, batch_info: Dict[str, Any]):
        """
        Store review redirect information for automatic redirection
        
        Args:
            user_id: The user ID
            task_id: The task ID
            batch_info: The batch information
        """
        try:
            # Store in Redis for quick access (if available)
            try:
                import redis
                import json
                from config import Config
                
                config = Config()
                if hasattr(config, 'REDIS_URL') and config.REDIS_URL:
                    r = redis.from_url(config.REDIS_URL)
                    
                    redirect_info = {
                        'task_id': task_id,
                        'batch_id': batch_info['batch_id'],
                        'total_images': batch_info['total_images'],
                        'redirect_url': f"/review/batch/{batch_info['batch_id']}",
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Store with 1 hour expiration
                    r.setex(f"review_redirect:{user_id}:{task_id}", 3600, json.dumps(redirect_info))
                    
                    logger.debug(f"Stored review redirect info in Redis for user {sanitize_for_log(str(user_id))}")
                    
            except Exception as redis_error:
                logger.debug(f"Redis not available for review redirect storage: {sanitize_for_log(str(redis_error))}")
                
        except Exception as e:
            logger.error(f"Error storing review redirect info: {sanitize_for_log(str(e))}")
    
    def get_review_redirect_info(self, user_id: int, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get review redirect information for a completed task
        
        Args:
            user_id: The user ID
            task_id: The task ID
            
        Returns:
            Dict with redirect information or None if not found
        """
        try:
            # Try to get from Redis first
            try:
                import redis
                import json
                from config import Config
                
                config = Config()
                if hasattr(config, 'REDIS_URL') and config.REDIS_URL:
                    r = redis.from_url(config.REDIS_URL)
                    
                    redirect_data = r.get(f"review_redirect:{user_id}:{task_id}")
                    if redirect_data:
                        redirect_info = json.loads(redirect_data)
                        logger.debug(f"Retrieved review redirect info from Redis for user {sanitize_for_log(str(user_id))}")
                        return redirect_info
                        
            except Exception as redis_error:
                logger.debug(f"Redis not available for review redirect retrieval: {sanitize_for_log(str(redis_error))}")
            
            # Fallback: create redirect info from task data
            task = self.task_queue_manager.get_task(task_id)
            if task and task.user_id == user_id and task.is_completed() and task.results:
                redirect_info = {
                    'task_id': task_id,
                    'batch_id': task_id,  # Use task_id as batch_id
                    'total_images': len(task.results.generated_image_ids or []),
                    'redirect_url': f"/review/batch/{task_id}",
                    'created_at': task.completed_at.isoformat() if task.completed_at else None
                }
                return redirect_info
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting review redirect info: {sanitize_for_log(str(e))}")
            return None