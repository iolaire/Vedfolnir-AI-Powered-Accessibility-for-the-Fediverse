# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Configuration Adapter

Connects performance settings with application behavior, implementing dynamic
resource limit enforcement, memory monitoring, and job priority management.
"""

import logging
import threading
import psutil
import os
import json
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from configuration_service import ConfigurationService, ConfigurationError
from task_queue_manager import TaskQueueManager
from models import JobPriority

logger = logging.getLogger(__name__)


class MemoryLimitExceededError(Exception):
    """Memory limit exceeded error"""
    pass


class PerformanceConfigurationError(Exception):
    """Performance configuration error"""
    pass


@dataclass
class MemoryUsageInfo:
    """Memory usage information"""
    current_mb: float
    limit_mb: int
    percentage: float
    process_id: int
    timestamp: datetime


@dataclass
class PriorityWeights:
    """Job priority weights"""
    urgent: float
    high: float
    normal: float
    low: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriorityWeights':
        """Create from dictionary"""
        return cls(
            urgent=float(data.get('urgent', 4.0)),
            high=float(data.get('high', 3.0)),
            normal=float(data.get('normal', 2.0)),
            low=float(data.get('low', 1.0))
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'urgent': self.urgent,
            'high': self.high,
            'normal': self.normal,
            'low': self.low
        }


class PerformanceConfigurationAdapter:
    """
    Adapter class that connects performance settings with application behavior
    
    Provides:
    - Memory usage limit enforcement
    - Job priority weight system
    - Performance configuration validation
    - Memory monitoring and alerting
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
        self._memory_monitoring_enabled = True
        
        # Configuration keys
        self.MAX_MEMORY_USAGE_KEY = "max_memory_usage_mb"
        self.PRIORITY_WEIGHTS_KEY = "processing_priority_weights"
        
        # Current settings
        self._current_memory_limit_mb = 2048  # Default
        self._current_priority_weights = PriorityWeights(urgent=4.0, high=3.0, normal=2.0, low=1.0)
        
        # Memory monitoring
        self._memory_usage_history: List[MemoryUsageInfo] = []
        self._max_history_size = 100
        
        # Initialize with current configuration
        self._initialize_configuration()
        
        # Subscribe to configuration changes
        self._setup_configuration_subscriptions()
    
    def _initialize_configuration(self):
        """Initialize performance settings with current configuration values"""
        try:
            # Update memory limits
            self.update_memory_limits()
            
            # Update priority weights
            self.update_priority_weights()
            
            logger.info("Performance configuration adapter initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing performance configuration: {str(e)}")
            raise PerformanceConfigurationError(f"Failed to initialize configuration: {str(e)}")
    
    def _setup_configuration_subscriptions(self):
        """Set up subscriptions for configuration changes"""
        try:
            # Subscribe to max_memory_usage_mb changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.MAX_MEMORY_USAGE_KEY,
                self._handle_memory_limit_change
            )
            self._subscriptions[self.MAX_MEMORY_USAGE_KEY] = subscription_id
            
            # Subscribe to processing_priority_weights changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.PRIORITY_WEIGHTS_KEY,
                self._handle_priority_weights_change
            )
            self._subscriptions[self.PRIORITY_WEIGHTS_KEY] = subscription_id
            
            logger.info("Performance configuration change subscriptions established")
            
        except Exception as e:
            logger.error(f"Error setting up performance configuration subscriptions: {str(e)}")
            raise PerformanceConfigurationError(f"Failed to setup subscriptions: {str(e)}")
    
    def update_memory_limits(self) -> bool:
        """
        Update memory limits from configuration
        
        Returns:
            True if update was successful
        """
        try:
            with self._lock:
                # Get current configuration value
                memory_limit_mb = self.config_service.get_config(
                    self.MAX_MEMORY_USAGE_KEY,
                    default=2048  # Default 2GB
                )
                
                # Validate the value
                if not isinstance(memory_limit_mb, int) or memory_limit_mb < 512:
                    logger.error(f"Invalid max_memory_usage_mb value: {memory_limit_mb}. Must be integer >= 512.")
                    return False
                
                if memory_limit_mb > 16384:  # 16GB max
                    logger.warning(f"Memory limit {memory_limit_mb}MB is very high. Consider system capacity.")
                
                # Update current setting
                old_value = self._current_memory_limit_mb
                self._current_memory_limit_mb = memory_limit_mb
                
                logger.info(f"Updated memory limit from {old_value}MB to {memory_limit_mb}MB")
                return True
                
        except ConfigurationError as e:
            logger.error(f"Configuration error updating memory limits: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating memory limits: {str(e)}")
            return False
    
    def update_priority_weights(self) -> bool:
        """
        Update job priority weights from configuration
        
        Returns:
            True if update was successful
        """
        try:
            with self._lock:
                # Get current configuration value
                priority_weights_config = self.config_service.get_config(
                    self.PRIORITY_WEIGHTS_KEY,
                    default={"urgent": 4.0, "high": 3.0, "normal": 2.0, "low": 1.0}
                )
                
                # Validate and convert to PriorityWeights
                if not isinstance(priority_weights_config, dict):
                    logger.error(f"Invalid processing_priority_weights value: {priority_weights_config}. Must be dictionary.")
                    return False
                
                try:
                    new_weights = PriorityWeights.from_dict(priority_weights_config)
                    
                    # Validate weights are positive
                    if any(weight <= 0 for weight in [new_weights.urgent, new_weights.high, new_weights.normal, new_weights.low]):
                        logger.error("All priority weights must be positive numbers")
                        return False
                    
                    # Update current setting
                    old_weights = self._current_priority_weights
                    self._current_priority_weights = new_weights
                    
                    logger.info(f"Updated priority weights from {old_weights.to_dict()} to {new_weights.to_dict()}")
                    
                    # Trigger queue reordering if needed
                    self._reorder_queue_by_priority()
                    
                    return True
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing priority weights: {str(e)}")
                    return False
                
        except ConfigurationError as e:
            logger.error(f"Configuration error updating priority weights: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating priority weights: {str(e)}")
            return False
    
    def check_memory_usage(self, process_id: Optional[int] = None) -> MemoryUsageInfo:
        """
        Check current memory usage for a process
        
        Args:
            process_id: Process ID to check, or None for current process
            
        Returns:
            MemoryUsageInfo with current usage details
        """
        try:
            if process_id is None:
                process_id = os.getpid()
            
            process = psutil.Process(process_id)
            memory_info = process.memory_info()
            current_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            percentage = (current_mb / self._current_memory_limit_mb) * 100
            
            usage_info = MemoryUsageInfo(
                current_mb=current_mb,
                limit_mb=self._current_memory_limit_mb,
                percentage=percentage,
                process_id=process_id,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Add to history
            with self._lock:
                self._memory_usage_history.append(usage_info)
                if len(self._memory_usage_history) > self._max_history_size:
                    self._memory_usage_history.pop(0)
            
            return usage_info
            
        except psutil.NoSuchProcess:
            logger.error(f"Process {process_id} not found")
            raise PerformanceConfigurationError(f"Process {process_id} not found")
        except Exception as e:
            logger.error(f"Error checking memory usage: {str(e)}")
            raise PerformanceConfigurationError(f"Failed to check memory usage: {str(e)}")
    
    def enforce_memory_limit(self, process_id: Optional[int] = None, task_id: Optional[str] = None) -> bool:
        """
        Enforce memory limit for a process/task
        
        Args:
            process_id: Process ID to check, or None for current process
            task_id: Task ID for logging purposes
            
        Returns:
            True if within limits, False if limit exceeded
            
        Raises:
            MemoryLimitExceededError: If memory limit is exceeded
        """
        try:
            usage_info = self.check_memory_usage(process_id)
            
            if usage_info.current_mb > self._current_memory_limit_mb:
                error_msg = (f"Memory limit exceeded: {usage_info.current_mb:.1f}MB > "
                           f"{self._current_memory_limit_mb}MB ({usage_info.percentage:.1f}%)")
                
                if task_id:
                    error_msg += f" for task {task_id}"
                
                logger.error(error_msg)
                
                # Log memory usage details
                self._log_memory_usage_details(usage_info)
                
                raise MemoryLimitExceededError(error_msg)
            
            # Log warning if approaching limit (>80%)
            if usage_info.percentage > 80:
                logger.warning(f"Memory usage approaching limit: {usage_info.current_mb:.1f}MB "
                             f"({usage_info.percentage:.1f}% of {self._current_memory_limit_mb}MB)")
            
            return True
            
        except MemoryLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"Error enforcing memory limit: {str(e)}")
            # On error, allow execution to continue (fail open)
            return True
    
    def get_priority_score(self, priority: JobPriority) -> float:
        """
        Get priority score for a job priority level
        
        Args:
            priority: Job priority level
            
        Returns:
            Priority score (higher = more priority)
        """
        priority_map = {
            JobPriority.URGENT: self._current_priority_weights.urgent,
            JobPriority.HIGH: self._current_priority_weights.high,
            JobPriority.NORMAL: self._current_priority_weights.normal,
            JobPriority.LOW: self._current_priority_weights.low
        }
        
        return priority_map.get(priority, self._current_priority_weights.normal)
    
    def _reorder_queue_by_priority(self):
        """
        Trigger queue reordering based on new priority weights
        
        Note: This is a placeholder for queue reordering logic.
        In a real implementation, this would interact with the task queue
        to reorder pending tasks based on new priority calculations.
        """
        try:
            # Get current queue statistics
            stats = self.task_queue_manager.get_queue_stats()
            queued_count = stats.get('queued', 0)
            
            if queued_count > 0:
                logger.info(f"Priority weights updated. {queued_count} queued tasks will use new priority calculations.")
                # Note: Actual reordering would require additional task queue methods
                # This is logged for now as the task queue doesn't currently support reordering
            
        except Exception as e:
            logger.error(f"Error triggering queue reordering: {str(e)}")
    
    def _log_memory_usage_details(self, usage_info: MemoryUsageInfo):
        """
        Log detailed memory usage information
        
        Args:
            usage_info: Memory usage information to log
        """
        try:
            process = psutil.Process(usage_info.process_id)
            
            # Get additional memory details
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            logger.error(f"Memory usage details for PID {usage_info.process_id}:")
            logger.error(f"  RSS: {memory_info.rss / (1024*1024):.1f}MB")
            logger.error(f"  VMS: {memory_info.vms / (1024*1024):.1f}MB")
            logger.error(f"  System memory %: {memory_percent:.1f}%")
            logger.error(f"  Configured limit: {usage_info.limit_mb}MB")
            logger.error(f"  Limit usage: {usage_info.percentage:.1f}%")
            
        except Exception as e:
            logger.error(f"Error logging memory usage details: {str(e)}")
    
    def _handle_memory_limit_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle max_memory_usage_mb configuration change
        
        Args:
            key: Configuration key
            old_value: Previous value
            new_value: New value
        """
        logger.info(f"Configuration change detected for {key}: {old_value} -> {new_value}")
        
        try:
            success = self.update_memory_limits()
            if success:
                logger.info(f"Successfully applied memory limit change: {new_value}MB")
                
                # Check current memory usage against new limit
                try:
                    usage_info = self.check_memory_usage()
                    if usage_info.current_mb > new_value:
                        logger.warning(f"Current memory usage ({usage_info.current_mb:.1f}MB) "
                                     f"exceeds new limit ({new_value}MB)")
                except Exception as e:
                    logger.error(f"Error checking memory usage after limit change: {str(e)}")
            else:
                logger.error(f"Failed to apply memory limit change: {new_value}")
        except Exception as e:
            logger.error(f"Error handling memory limit change: {str(e)}")
    
    def _handle_priority_weights_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle processing_priority_weights configuration change
        
        Args:
            key: Configuration key
            old_value: Previous value
            new_value: New value
        """
        logger.info(f"Configuration change detected for {key}: {old_value} -> {new_value}")
        
        try:
            success = self.update_priority_weights()
            if success:
                logger.info(f"Successfully applied priority weights change: {new_value}")
            else:
                logger.error(f"Failed to apply priority weights change: {new_value}")
        except Exception as e:
            logger.error(f"Error handling priority weights change: {str(e)}")
    
    def validate_performance_configuration(self, config_values: Dict[str, Any]) -> List[str]:
        """
        Validate performance configuration values
        
        Args:
            config_values: Dictionary of configuration values to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Validate memory limit
            memory_limit = config_values.get(self.MAX_MEMORY_USAGE_KEY)
            if memory_limit is not None:
                if not isinstance(memory_limit, int):
                    errors.append(f"{self.MAX_MEMORY_USAGE_KEY} must be an integer")
                elif memory_limit < 512:
                    errors.append(f"{self.MAX_MEMORY_USAGE_KEY} must be at least 512MB")
                elif memory_limit > 16384:
                    errors.append(f"{self.MAX_MEMORY_USAGE_KEY} should not exceed 16384MB (16GB)")
            
            # Validate priority weights
            priority_weights = config_values.get(self.PRIORITY_WEIGHTS_KEY)
            if priority_weights is not None:
                if not isinstance(priority_weights, dict):
                    errors.append(f"{self.PRIORITY_WEIGHTS_KEY} must be a dictionary")
                else:
                    required_keys = ['urgent', 'high', 'normal', 'low']
                    for key in required_keys:
                        if key not in priority_weights:
                            errors.append(f"{self.PRIORITY_WEIGHTS_KEY} missing required key: {key}")
                        else:
                            try:
                                weight = float(priority_weights[key])
                                if weight <= 0:
                                    errors.append(f"{self.PRIORITY_WEIGHTS_KEY}.{key} must be positive")
                            except (ValueError, TypeError):
                                errors.append(f"{self.PRIORITY_WEIGHTS_KEY}.{key} must be a number")
            
            # Cross-validation: memory vs concurrent jobs
            memory_limit = config_values.get(self.MAX_MEMORY_USAGE_KEY, self._current_memory_limit_mb)
            max_jobs = config_values.get('max_concurrent_jobs', 3)
            
            if isinstance(memory_limit, int) and isinstance(max_jobs, int):
                total_memory = memory_limit * max_jobs
                if total_memory > 32768:  # 32GB warning threshold
                    errors.append(f"Total memory usage ({total_memory}MB) may exceed system capacity. "
                                f"Consider reducing memory limit or concurrent jobs.")
            
        except Exception as e:
            errors.append(f"Error validating performance configuration: {str(e)}")
        
        return errors
    
    def get_memory_usage_history(self, limit: int = 50) -> List[MemoryUsageInfo]:
        """
        Get recent memory usage history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of MemoryUsageInfo entries
        """
        with self._lock:
            return self._memory_usage_history[-limit:] if self._memory_usage_history else []
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current performance configuration values
        
        Returns:
            Dictionary with current configuration
        """
        try:
            return {
                'max_memory_usage_mb': self._current_memory_limit_mb,
                'processing_priority_weights': self._current_priority_weights.to_dict(),
                'memory_monitoring_enabled': self._memory_monitoring_enabled,
                'memory_usage_history_size': len(self._memory_usage_history)
            }
        except Exception as e:
            logger.error(f"Error getting current performance configuration: {str(e)}")
            return {}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics and metrics
        
        Returns:
            Dictionary with performance statistics
        """
        try:
            stats = {}
            
            # Current memory usage
            try:
                current_usage = self.check_memory_usage()
                stats['current_memory'] = {
                    'usage_mb': current_usage.current_mb,
                    'limit_mb': current_usage.limit_mb,
                    'percentage': current_usage.percentage,
                    'timestamp': current_usage.timestamp.isoformat()
                }
            except Exception as e:
                stats['current_memory'] = {'error': str(e)}
            
            # Memory usage history summary
            if self._memory_usage_history:
                recent_usage = self._memory_usage_history[-10:]  # Last 10 entries
                avg_usage = sum(entry.current_mb for entry in recent_usage) / len(recent_usage)
                max_usage = max(entry.current_mb for entry in recent_usage)
                
                stats['memory_history'] = {
                    'entries_count': len(self._memory_usage_history),
                    'recent_average_mb': avg_usage,
                    'recent_maximum_mb': max_usage
                }
            
            # Priority weights
            stats['priority_weights'] = self._current_priority_weights.to_dict()
            
            # Task queue stats
            try:
                queue_stats = self.task_queue_manager.get_queue_stats()
                stats['queue_stats'] = queue_stats
            except Exception as e:
                stats['queue_stats'] = {'error': str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting performance stats: {str(e)}")
            return {'error': str(e)}
    
    def cleanup(self):
        """Clean up subscriptions and resources"""
        try:
            # Unsubscribe from all configuration changes
            for key, subscription_id in self._subscriptions.items():
                self.config_service.unsubscribe(subscription_id)
                logger.debug(f"Unsubscribed from {key} configuration changes")
            
            self._subscriptions.clear()
            
            # Clear memory usage history
            with self._lock:
                self._memory_usage_history.clear()
            
            logger.info("Performance configuration adapter cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during destruction