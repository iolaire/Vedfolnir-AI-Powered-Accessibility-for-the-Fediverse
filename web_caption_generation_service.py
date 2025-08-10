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
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from database import DatabaseManager
from models import (
    CaptionGenerationTask, CaptionGenerationSettings, CaptionGenerationUserSettings,
    GenerationResults, TaskStatus, PlatformConnection, User
)
from task_queue_manager import TaskQueueManager
from progress_tracker import ProgressTracker
from platform_aware_caption_adapter import PlatformAwareCaptionAdapter
from security.core.security_utils import sanitize_for_log
from error_recovery_manager import error_recovery_manager, handle_caption_error

logger = logging.getLogger(__name__)

class WebCaptionGenerationService:
    """Main orchestration service for web-based caption generation"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.task_queue_manager = TaskQueueManager(db_manager)
        self.progress_tracker = ProgressTracker(db_manager)
        
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
    
    def get_generation_status(self, task_id: str, user_id: int = None) -> Optional[Dict[str, Any]]:
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
            
            # Authorization check
            if user_id is not None and task.user_id != user_id:
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
            
            # Complete progress tracking
            self.progress_tracker.complete_progress(task_id, results)
            
            logger.info(f"Completed caption generation task {sanitize_for_log(task_id)}: {results.captions_generated} captions generated")
            
        except Exception as e:
            logger.error(f"Error processing task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
            
            # Handle error with recovery manager
            try:
                error_info = error_recovery_manager.create_error_info(e, {
                    'task_id': task_id,
                    'operation': 'caption_generation',
                    'user_id': task.user_id,
                    'platform_id': task.platform_connection_id
                })
                
                user_message = error_recovery_manager._get_user_friendly_message(error_info)
                
                # Mark task as failed with user-friendly message
                self.task_queue_manager.complete_task(task_id, success=False, error_message=user_message)
                
                # Update progress with error
                self.progress_tracker.update_progress(
                    task_id,
                    "Failed",
                    100,
                    {'error': user_message, 'error_category': error_info.category.value}
                )
                
            except Exception as recovery_error:
                logger.error(f"Error in recovery handling: {sanitize_for_log(str(recovery_error))}")
                # Fallback to original error handling
                self.task_queue_manager.complete_task(task_id, success=False, error_message=str(e))
                self.progress_tracker.update_progress(task_id, "Failed", 100, {'error': str(e)})
    
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