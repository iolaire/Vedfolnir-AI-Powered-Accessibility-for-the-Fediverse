# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Memory Monitor

Provides memory monitoring and enforcement during job execution with
graceful termination when memory limits are exceeded.
"""

import logging
import threading
import time
import psutil
import os
import signal
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from performance_configuration_adapter import PerformanceConfigurationAdapter, MemoryLimitExceededError

logger = logging.getLogger(__name__)


class MemoryMonitorStatus(Enum):
    """Memory monitor status"""
    STOPPED = "stopped"
    RUNNING = "running"
    WARNING = "warning"
    LIMIT_EXCEEDED = "limit_exceeded"
    ERROR = "error"


@dataclass
class MemoryMonitorConfig:
    """Memory monitor configuration"""
    check_interval_seconds: float = 5.0
    warning_threshold_percent: float = 80.0
    critical_threshold_percent: float = 95.0
    grace_period_seconds: float = 10.0
    enable_graceful_termination: bool = True


class MemoryMonitor:
    """
    Memory monitor for job execution
    
    Monitors memory usage during job execution and provides:
    - Continuous memory usage monitoring
    - Warning notifications when approaching limits
    - Graceful job termination when limits are exceeded
    - Memory usage reporting and alerting
    """
    
    def __init__(self, performance_adapter: PerformanceConfigurationAdapter, 
                 config: Optional[MemoryMonitorConfig] = None):
        """
        Initialize memory monitor
        
        Args:
            performance_adapter: Performance configuration adapter
            config: Monitor configuration (uses defaults if None)
        """
        self.performance_adapter = performance_adapter
        self.config = config or MemoryMonitorConfig()
        
        # Monitor state
        self._status = MemoryMonitorStatus.STOPPED
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Monitored process info
        self._process_id: Optional[int] = None
        self._task_id: Optional[str] = None
        
        # Callbacks
        self._warning_callback: Optional[Callable[[float, float], None]] = None
        self._limit_exceeded_callback: Optional[Callable[[str], None]] = None
        self._termination_callback: Optional[Callable[[str], None]] = None
        
        # Statistics
        self._start_time: Optional[datetime] = None
        self._warning_count = 0
        self._limit_exceeded_count = 0
        self._max_memory_usage = 0.0
    
    def start_monitoring(self, process_id: Optional[int] = None, task_id: Optional[str] = None) -> bool:
        """
        Start memory monitoring for a process
        
        Args:
            process_id: Process ID to monitor (current process if None)
            task_id: Task ID for logging purposes
            
        Returns:
            True if monitoring started successfully
        """
        try:
            with self._lock:
                if self._status == MemoryMonitorStatus.RUNNING:
                    logger.warning("Memory monitor is already running")
                    return False
                
                # Set process info
                self._process_id = process_id or os.getpid()
                self._task_id = task_id
                
                # Verify process exists
                try:
                    psutil.Process(self._process_id)
                except psutil.NoSuchProcess:
                    logger.error(f"Process {self._process_id} not found")
                    return False
                
                # Reset state
                self._stop_event.clear()
                self._status = MemoryMonitorStatus.RUNNING
                self._start_time = datetime.now(timezone.utc)
                self._warning_count = 0
                self._limit_exceeded_count = 0
                self._max_memory_usage = 0.0
                
                # Start monitoring thread
                self._monitoring_thread = threading.Thread(
                    target=self._monitoring_loop,
                    name=f"MemoryMonitor-{self._process_id}",
                    daemon=True
                )
                self._monitoring_thread.start()
                
                logger.info(f"Started memory monitoring for process {self._process_id}"
                          f"{f' (task {task_id})' if task_id else ''}")
                return True
                
        except Exception as e:
            logger.error(f"Error starting memory monitoring: {str(e)}")
            self._status = MemoryMonitorStatus.ERROR
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop memory monitoring
        
        Returns:
            True if monitoring stopped successfully
        """
        try:
            with self._lock:
                if self._status == MemoryMonitorStatus.STOPPED:
                    return True
                
                # Signal stop
                self._stop_event.set()
                
                # Wait for thread to finish
                if self._monitoring_thread and self._monitoring_thread.is_alive():
                    self._monitoring_thread.join(timeout=5.0)
                    
                    if self._monitoring_thread.is_alive():
                        logger.warning("Memory monitoring thread did not stop gracefully")
                
                self._status = MemoryMonitorStatus.STOPPED
                self._monitoring_thread = None
                
                logger.info(f"Stopped memory monitoring for process {self._process_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error stopping memory monitoring: {str(e)}")
            return False
    
    def set_warning_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback for memory usage warnings
        
        Args:
            callback: Function called with (current_mb, limit_mb) when warning threshold exceeded
        """
        self._warning_callback = callback
    
    def set_limit_exceeded_callback(self, callback: Callable[[str], None]):
        """
        Set callback for memory limit exceeded
        
        Args:
            callback: Function called with error message when limit exceeded
        """
        self._limit_exceeded_callback = callback
    
    def set_termination_callback(self, callback: Callable[[str], None]):
        """
        Set callback for process termination
        
        Args:
            callback: Function called with reason when process is terminated
        """
        self._termination_callback = callback
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while not self._stop_event.is_set():
                try:
                    # Check memory usage
                    self._check_memory_usage()
                    
                    # Wait for next check
                    if self._stop_event.wait(self.config.check_interval_seconds):
                        break  # Stop event was set
                        
                except Exception as e:
                    logger.error(f"Error in memory monitoring loop: {str(e)}")
                    self._status = MemoryMonitorStatus.ERROR
                    time.sleep(self.config.check_interval_seconds)
                    
        except Exception as e:
            logger.error(f"Fatal error in memory monitoring loop: {str(e)}")
            self._status = MemoryMonitorStatus.ERROR
        finally:
            logger.debug("Memory monitoring loop ended")
    
    def _check_memory_usage(self):
        """Check current memory usage and take action if needed"""
        try:
            # Get current memory usage
            usage_info = self.performance_adapter.check_memory_usage(self._process_id)
            
            # Update max usage
            if usage_info.current_mb > self._max_memory_usage:
                self._max_memory_usage = usage_info.current_mb
            
            # Check warning threshold
            if usage_info.percentage >= self.config.warning_threshold_percent:
                self._handle_warning_threshold(usage_info)
            
            # Check critical threshold
            if usage_info.percentage >= self.config.critical_threshold_percent:
                self._handle_critical_threshold(usage_info)
            
            # Check absolute limit
            if usage_info.current_mb > usage_info.limit_mb:
                self._handle_limit_exceeded(usage_info)
                
        except psutil.NoSuchProcess:
            logger.info(f"Monitored process {self._process_id} no longer exists")
            self._status = MemoryMonitorStatus.STOPPED
            self._stop_event.set()
        except Exception as e:
            logger.error(f"Error checking memory usage: {str(e)}")
            self._status = MemoryMonitorStatus.ERROR
    
    def _handle_warning_threshold(self, usage_info):
        """Handle warning threshold exceeded"""
        try:
            if self._status != MemoryMonitorStatus.WARNING:
                self._status = MemoryMonitorStatus.WARNING
                self._warning_count += 1
                
                warning_msg = (f"Memory usage warning: {usage_info.current_mb:.1f}MB "
                             f"({usage_info.percentage:.1f}% of {usage_info.limit_mb}MB)")
                
                if self._task_id:
                    warning_msg += f" for task {self._task_id}"
                
                logger.warning(warning_msg)
                
                # Call warning callback
                if self._warning_callback:
                    try:
                        self._warning_callback(usage_info.current_mb, usage_info.limit_mb)
                    except Exception as e:
                        logger.error(f"Error in warning callback: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error handling warning threshold: {str(e)}")
    
    def _handle_critical_threshold(self, usage_info):
        """Handle critical threshold exceeded"""
        try:
            critical_msg = (f"Memory usage critical: {usage_info.current_mb:.1f}MB "
                          f"({usage_info.percentage:.1f}% of {usage_info.limit_mb}MB)")
            
            if self._task_id:
                critical_msg += f" for task {self._task_id}"
            
            logger.error(critical_msg)
            
            # Start grace period for graceful shutdown
            if self.config.enable_graceful_termination:
                logger.warning(f"Starting {self.config.grace_period_seconds}s grace period for graceful shutdown")
                
        except Exception as e:
            logger.error(f"Error handling critical threshold: {str(e)}")
    
    def _handle_limit_exceeded(self, usage_info):
        """Handle memory limit exceeded"""
        try:
            self._status = MemoryMonitorStatus.LIMIT_EXCEEDED
            self._limit_exceeded_count += 1
            
            error_msg = (f"Memory limit exceeded: {usage_info.current_mb:.1f}MB > "
                        f"{usage_info.limit_mb}MB ({usage_info.percentage:.1f}%)")
            
            if self._task_id:
                error_msg += f" for task {self._task_id}"
            
            logger.error(error_msg)
            
            # Call limit exceeded callback
            if self._limit_exceeded_callback:
                try:
                    self._limit_exceeded_callback(error_msg)
                except Exception as e:
                    logger.error(f"Error in limit exceeded callback: {str(e)}")
            
            # Terminate process if enabled
            if self.config.enable_graceful_termination:
                self._terminate_process_gracefully(error_msg)
            
        except Exception as e:
            logger.error(f"Error handling limit exceeded: {str(e)}")
    
    def _terminate_process_gracefully(self, reason: str):
        """
        Terminate process gracefully
        
        Args:
            reason: Reason for termination
        """
        try:
            logger.error(f"Terminating process {self._process_id} due to memory limit exceeded")
            
            # Call termination callback
            if self._termination_callback:
                try:
                    self._termination_callback(reason)
                except Exception as e:
                    logger.error(f"Error in termination callback: {str(e)}")
            
            # Get process
            process = psutil.Process(self._process_id)
            
            # Try graceful termination first (SIGTERM)
            if self._process_id != os.getpid():  # Don't terminate ourselves
                logger.info(f"Sending SIGTERM to process {self._process_id}")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=self.config.grace_period_seconds)
                    logger.info(f"Process {self._process_id} terminated gracefully")
                except psutil.TimeoutExpired:
                    # Force kill if graceful termination failed
                    logger.warning(f"Process {self._process_id} did not terminate gracefully, forcing kill")
                    process.kill()
                    logger.info(f"Process {self._process_id} force killed")
            else:
                # If monitoring our own process, just log and let the application handle it
                logger.error("Memory limit exceeded in current process - application should handle graceful shutdown")
                
        except psutil.NoSuchProcess:
            logger.info(f"Process {self._process_id} already terminated")
        except Exception as e:
            logger.error(f"Error terminating process: {str(e)}")
    
    def get_status(self) -> MemoryMonitorStatus:
        """Get current monitor status"""
        return self._status
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get monitoring statistics
        
        Returns:
            Dictionary with monitoring statistics
        """
        try:
            with self._lock:
                stats = {
                    'status': self._status.value,
                    'process_id': self._process_id,
                    'task_id': self._task_id,
                    'warning_count': self._warning_count,
                    'limit_exceeded_count': self._limit_exceeded_count,
                    'max_memory_usage_mb': self._max_memory_usage,
                    'config': {
                        'check_interval_seconds': self.config.check_interval_seconds,
                        'warning_threshold_percent': self.config.warning_threshold_percent,
                        'critical_threshold_percent': self.config.critical_threshold_percent,
                        'grace_period_seconds': self.config.grace_period_seconds,
                        'enable_graceful_termination': self.config.enable_graceful_termination
                    }
                }
                
                if self._start_time:
                    stats['start_time'] = self._start_time.isoformat()
                    stats['monitoring_duration_seconds'] = (
                        datetime.now(timezone.utc) - self._start_time
                    ).total_seconds()
                
                # Add current memory usage if monitoring
                if self._status == MemoryMonitorStatus.RUNNING:
                    try:
                        current_usage = self.performance_adapter.check_memory_usage(self._process_id)
                        stats['current_memory'] = {
                            'usage_mb': current_usage.current_mb,
                            'limit_mb': current_usage.limit_mb,
                            'percentage': current_usage.percentage
                        }
                    except Exception as e:
                        stats['current_memory'] = {'error': str(e)}
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting monitor statistics: {str(e)}")
            return {'error': str(e)}
    
    def is_monitoring(self) -> bool:
        """Check if currently monitoring"""
        return self._status == MemoryMonitorStatus.RUNNING
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()