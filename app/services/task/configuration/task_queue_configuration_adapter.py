# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Task Queue Configuration Adapter

Connects TaskQueueManager with ConfigurationService to enable dynamic
configuration updates for concurrency limits, timeouts, and queue size limits.
"""

import logging
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone

from app.core.configuration.core.configuration_service import ConfigurationService, ConfigurationError
from app.services.task.core.task_queue_manager import TaskQueueManager

logger = logging.getLogger(__name__)


class TaskQueueConfigurationError(Exception):
    """Task queue configuration error"""
    pass


class TaskQueueConfigurationAdapter:
    """
    Adapter class that connects TaskQueueManager with ConfigurationService
    
    Provides dynamic configuration updates for:
    - max_concurrent_jobs: Maximum concurrent task execution
    - default_job_timeout: Default timeout for job execution
    - queue_size_limit: Maximum number of queued jobs
    """
    
    def __init__(self, task_queue_manager: TaskQueueManager, config_service: ConfigurationService):
        """
        Initialize the adapter
        
        Args:
            task_queue_manager: TaskQueueManager instance to configure
            config_service: ConfigurationService instance for reading configuration
        """
        self.task_queue_manager = task_queue_manager
        self.config_service = config_service
        self._lock = threading.RLock()
        self._subscriptions: Dict[str, str] = {}
        
        # Configuration keys
        self.MAX_CONCURRENT_JOBS_KEY = "max_concurrent_jobs"
        self.DEFAULT_JOB_TIMEOUT_KEY = "default_job_timeout"
        self.QUEUE_SIZE_LIMIT_KEY = "queue_size_limit"
        
        # Initialize with current configuration
        self._initialize_configuration()
        
        # Subscribe to configuration changes
        self._setup_configuration_subscriptions()
    
    def _initialize_configuration(self):
        """Initialize task queue with current configuration values"""
        try:
            # Update concurrency limits
            self.update_concurrency_limits()
            
            # Update timeout settings
            self.update_timeout_settings()
            
            # Update queue size limits
            self.update_queue_size_limits()
            
            logger.info("Task queue configuration adapter initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing task queue configuration: {str(e)}")
            raise TaskQueueConfigurationError(f"Failed to initialize configuration: {str(e)}")
    
    def _setup_configuration_subscriptions(self):
        """Set up subscriptions for configuration changes"""
        try:
            # Subscribe to max_concurrent_jobs changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.MAX_CONCURRENT_JOBS_KEY,
                self._handle_max_concurrent_jobs_change
            )
            self._subscriptions[self.MAX_CONCURRENT_JOBS_KEY] = subscription_id
            
            # Subscribe to default_job_timeout changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.DEFAULT_JOB_TIMEOUT_KEY,
                self._handle_default_job_timeout_change
            )
            self._subscriptions[self.DEFAULT_JOB_TIMEOUT_KEY] = subscription_id
            
            # Subscribe to queue_size_limit changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.QUEUE_SIZE_LIMIT_KEY,
                self._handle_queue_size_limit_change
            )
            self._subscriptions[self.QUEUE_SIZE_LIMIT_KEY] = subscription_id
            
            logger.info("Configuration change subscriptions established")
            
        except Exception as e:
            logger.error(f"Error setting up configuration subscriptions: {str(e)}")
            raise TaskQueueConfigurationError(f"Failed to setup subscriptions: {str(e)}")
    
    def update_concurrency_limits(self) -> bool:
        """
        Update task queue concurrency limits from configuration
        
        Returns:
            True if update was successful
        """
        try:
            with self._lock:
                # Get current configuration value
                max_concurrent = self.config_service.get_config(
                    self.MAX_CONCURRENT_JOBS_KEY, 
                    default=3  # Default from original TaskQueueManager
                )
                
                # Validate the value
                if not isinstance(max_concurrent, int) or max_concurrent < 1:
                    logger.error(f"Invalid max_concurrent_jobs value: {max_concurrent}. Must be positive integer.")
                    return False
                
                # Update the task queue manager
                old_value = getattr(self.task_queue_manager, 'max_concurrent_tasks', None)
                self.task_queue_manager.max_concurrent_tasks = max_concurrent
                
                logger.info(f"Updated max_concurrent_tasks from {old_value} to {max_concurrent}")
                return True
                
        except ConfigurationError as e:
            logger.error(f"Configuration error updating concurrency limits: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating concurrency limits: {str(e)}")
            return False
    
    def update_timeout_settings(self) -> bool:
        """
        Update job timeout settings from configuration
        
        Returns:
            True if update was successful
        """
        try:
            with self._lock:
                # Get current configuration value
                default_timeout = self.config_service.get_config(
                    self.DEFAULT_JOB_TIMEOUT_KEY,
                    default=3600  # Default 1 hour timeout
                )
                
                # Validate the value
                if not isinstance(default_timeout, (int, float)) or default_timeout <= 0:
                    logger.error(f"Invalid default_job_timeout value: {default_timeout}. Must be positive number.")
                    return False
                
                # Store timeout setting for use by task queue
                old_value = getattr(self.task_queue_manager, 'default_job_timeout', None)
                self.task_queue_manager.default_job_timeout = default_timeout
                
                logger.info(f"Updated default_job_timeout from {old_value} to {default_timeout}")
                return True
                
        except ConfigurationError as e:
            logger.error(f"Configuration error updating timeout settings: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating timeout settings: {str(e)}")
            return False
    
    def update_queue_size_limits(self) -> bool:
        """
        Update queue size limits from configuration
        
        Returns:
            True if update was successful
        """
        try:
            with self._lock:
                # Get current configuration value
                queue_size_limit = self.config_service.get_config(
                    self.QUEUE_SIZE_LIMIT_KEY,
                    default=100  # Default queue size limit
                )
                
                # Validate the value
                if not isinstance(queue_size_limit, int) or queue_size_limit < 1:
                    logger.error(f"Invalid queue_size_limit value: {queue_size_limit}. Must be positive integer.")
                    return False
                
                # Store queue size limit for use by task queue
                old_value = getattr(self.task_queue_manager, 'queue_size_limit', None)
                self.task_queue_manager.queue_size_limit = queue_size_limit
                
                logger.info(f"Updated queue_size_limit from {old_value} to {queue_size_limit}")
                return True
                
        except ConfigurationError as e:
            logger.error(f"Configuration error updating queue size limits: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating queue size limits: {str(e)}")
            return False
    
    def _handle_max_concurrent_jobs_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle max_concurrent_jobs configuration change
        
        Args:
            key: Configuration key
            old_value: Previous value
            new_value: New value
        """
        logger.info(f"Configuration change detected for {key}: {old_value} -> {new_value}")
        
        try:
            success = self.update_concurrency_limits()
            if success:
                logger.info(f"Successfully applied max_concurrent_jobs change: {new_value}")
            else:
                logger.error(f"Failed to apply max_concurrent_jobs change: {new_value}")
        except Exception as e:
            logger.error(f"Error handling max_concurrent_jobs change: {str(e)}")
    
    def _handle_default_job_timeout_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle default_job_timeout configuration change
        
        Args:
            key: Configuration key
            old_value: Previous value
            new_value: New value
        """
        logger.info(f"Configuration change detected for {key}: {old_value} -> {new_value}")
        
        try:
            success = self.update_timeout_settings()
            if success:
                logger.info(f"Successfully applied default_job_timeout change: {new_value}")
            else:
                logger.error(f"Failed to apply default_job_timeout change: {new_value}")
        except Exception as e:
            logger.error(f"Error handling default_job_timeout change: {str(e)}")
    
    def _handle_queue_size_limit_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle queue_size_limit configuration change
        
        Args:
            key: Configuration key
            old_value: Previous value
            new_value: New value
        """
        logger.info(f"Configuration change detected for {key}: {old_value} -> {new_value}")
        
        try:
            success = self.update_queue_size_limits()
            if success:
                logger.info(f"Successfully applied queue_size_limit change: {new_value}")
                
                # Check if current queue exceeds new limit
                self._enforce_queue_size_limit()
            else:
                logger.error(f"Failed to apply queue_size_limit change: {new_value}")
        except Exception as e:
            logger.error(f"Error handling queue_size_limit change: {str(e)}")
    
    def _enforce_queue_size_limit(self):
        """
        Enforce queue size limit by checking current queue size
        """
        try:
            # Get current queue statistics
            stats = self.task_queue_manager.get_queue_stats()
            queued_count = stats.get('queued', 0)
            queue_limit = getattr(self.task_queue_manager, 'queue_size_limit', 100)
            
            if queued_count > queue_limit:
                logger.warning(f"Current queue size ({queued_count}) exceeds new limit ({queue_limit})")
                # Note: We don't automatically cancel tasks here as that would be disruptive
                # Instead, we log the warning and let the enqueue_task method handle rejections
                
        except Exception as e:
            logger.error(f"Error enforcing queue size limit: {str(e)}")
    
    def handle_queue_limit_change(self, new_limit: int) -> bool:
        """
        Handle queue size limit change with proper error handling
        
        Args:
            new_limit: New queue size limit
            
        Returns:
            True if change was handled successfully
        """
        try:
            if new_limit < 1:
                raise ValueError(f"Queue size limit must be positive, got: {new_limit}")
            
            with self._lock:
                old_limit = getattr(self.task_queue_manager, 'queue_size_limit', 100)
                self.task_queue_manager.queue_size_limit = new_limit
                
                logger.info(f"Queue size limit changed from {old_limit} to {new_limit}")
                
                # Check current queue size against new limit
                self._enforce_queue_size_limit()
                
                return True
                
        except Exception as e:
            logger.error(f"Error handling queue limit change: {str(e)}")
            return False
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current task queue configuration values
        
        Returns:
            Dictionary with current configuration
        """
        try:
            return {
                'max_concurrent_jobs': self.config_service.get_config(self.MAX_CONCURRENT_JOBS_KEY, 3),
                'default_job_timeout': self.config_service.get_config(self.DEFAULT_JOB_TIMEOUT_KEY, 3600),
                'queue_size_limit': self.config_service.get_config(self.QUEUE_SIZE_LIMIT_KEY, 100),
                'current_max_concurrent_tasks': getattr(self.task_queue_manager, 'max_concurrent_tasks', 3),
                'current_default_job_timeout': getattr(self.task_queue_manager, 'default_job_timeout', 3600),
                'current_queue_size_limit': getattr(self.task_queue_manager, 'queue_size_limit', 100)
            }
        except Exception as e:
            logger.error(f"Error getting current configuration: {str(e)}")
            return {}
    
    def validate_queue_size_before_enqueue(self, user_id: int) -> bool:
        """
        Validate that queue size is within limits before allowing new task enqueue
        
        Args:
            user_id: User ID attempting to enqueue task
            
        Returns:
            True if enqueue is allowed, False if queue is full
        """
        try:
            # Get current queue statistics
            stats = self.task_queue_manager.get_queue_stats()
            queued_count = stats.get('queued', 0)
            queue_limit = getattr(self.task_queue_manager, 'queue_size_limit', 100)
            
            if queued_count >= queue_limit:
                logger.warning(f"Queue size limit reached ({queued_count}/{queue_limit}). Rejecting new task for user {user_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating queue size: {str(e)}")
            # On error, allow the enqueue to proceed (fail open)
            return True
    
    def cleanup(self):
        """Clean up subscriptions and resources"""
        try:
            # Unsubscribe from all configuration changes
            for key, subscription_id in self._subscriptions.items():
                self.config_service.unsubscribe(subscription_id)
                logger.debug(f"Unsubscribed from {key} configuration changes")
            
            self._subscriptions.clear()
            logger.info("Task queue configuration adapter cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during destruction