# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Event Logger for comprehensive logging of all storage events and state changes.

This module provides specialized logging functionality for storage management events,
including structured logging, log rotation, and integration with the storage warning
monitoring system as specified in requirement 2.4.
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from storage_warning_monitor import StorageEventType, StorageEvent
from storage_monitor_service import StorageMetrics

# Configure storage-specific logger
storage_logger = logging.getLogger('storage_events')


class LogLevel(Enum):
    """Log levels for storage events"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class StorageLogEntry:
    """Structured log entry for storage events"""
    timestamp: datetime
    level: LogLevel
    event_type: str
    message: str
    storage_gb: float
    limit_gb: float
    warning_threshold_gb: float
    usage_percentage: float
    is_warning_exceeded: bool
    is_limit_exceeded: bool
    component: str
    additional_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class StorageEventLogger:
    """
    Comprehensive logger for storage events and state changes.
    
    This logger provides:
    - Structured logging for all storage events
    - Automatic log rotation and retention
    - JSON-formatted logs for analysis
    - Integration with standard Python logging
    - File-based and console logging options
    """
    
    # Default log configuration
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_LOG_FILE = "storage_events.log"
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    DEFAULT_BACKUP_COUNT = 5
    DEFAULT_LOG_LEVEL = logging.INFO
    
    def __init__(self,
                 log_dir: Optional[str] = None,
                 log_file: Optional[str] = None,
                 max_bytes: Optional[int] = None,
                 backup_count: Optional[int] = None,
                 log_level: Optional[int] = None,
                 enable_console: bool = True,
                 enable_json_format: bool = True):
        """
        Initialize the storage event logger.
        
        Args:
            log_dir: Directory for log files (default: logs)
            log_file: Log file name (default: storage_events.log)
            max_bytes: Maximum log file size before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
            log_level: Logging level (default: INFO)
            enable_console: Enable console logging (default: True)
            enable_json_format: Enable JSON formatting (default: True)
        """
        self.log_dir = log_dir or self.DEFAULT_LOG_DIR
        self.log_file = log_file or self.DEFAULT_LOG_FILE
        self.max_bytes = max_bytes or self.DEFAULT_MAX_BYTES
        self.backup_count = backup_count or self.DEFAULT_BACKUP_COUNT
        self.log_level = log_level or self.DEFAULT_LOG_LEVEL
        self.enable_console = enable_console
        self.enable_json_format = enable_json_format
        
        # Create log directory if it doesn't exist
        self._ensure_log_directory()
        
        # Initialize logger
        self._setup_logger()
        
        # Log initialization
        self.log_info("storage_logger_initialized", "Storage event logger initialized", 
                     additional_data={
                         'log_dir': self.log_dir,
                         'log_file': self.log_file,
                         'max_bytes': self.max_bytes,
                         'backup_count': self.backup_count,
                         'log_level': logging.getLevelName(self.log_level),
                         'enable_console': self.enable_console,
                         'enable_json_format': self.enable_json_format
                     })
    
    def _ensure_log_directory(self) -> None:
        """Ensure the log directory exists"""
        try:
            log_path = Path(self.log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create log directory {self.log_dir}: {e}")
    
    def _setup_logger(self) -> None:
        """Set up the storage event logger with handlers and formatters"""
        # Configure the storage logger
        storage_logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in storage_logger.handlers[:]:
            storage_logger.removeHandler(handler)
        
        # File handler with rotation
        log_file_path = os.path.join(self.log_dir, self.log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        file_handler.setLevel(self.log_level)
        
        # Console handler (optional)
        console_handler = None
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
        
        # Set up formatters
        if self.enable_json_format:
            # JSON formatter for structured logging
            json_formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": %(message)s}'
            )
            file_handler.setFormatter(json_formatter)
            
            if console_handler:
                # Use regular formatter for console for readability
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
        else:
            # Regular formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            if console_handler:
                console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        storage_logger.addHandler(file_handler)
        if console_handler:
            storage_logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        storage_logger.propagate = False
    
    def _create_log_entry(self, level: LogLevel, event_type: str, message: str,
                         metrics: Optional[StorageMetrics] = None,
                         component: str = "storage_system",
                         additional_data: Optional[Dict[str, Any]] = None) -> StorageLogEntry:
        """
        Create a structured log entry.
        
        Args:
            level: Log level
            event_type: Type of storage event
            message: Log message
            metrics: Optional storage metrics
            component: Component generating the log
            additional_data: Optional additional data
            
        Returns:
            StorageLogEntry object
        """
        # Use default metrics if not provided
        if metrics is None:
            metrics = StorageMetrics(
                total_bytes=0,
                total_gb=0.0,
                limit_gb=10.0,
                usage_percentage=0.0,
                is_limit_exceeded=False,
                is_warning_exceeded=False,
                last_calculated=datetime.now()
            )
        
        return StorageLogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            event_type=event_type,
            message=message,
            storage_gb=metrics.total_gb,
            limit_gb=metrics.limit_gb,
            warning_threshold_gb=metrics.limit_gb * 0.8,  # Assume 80% threshold
            usage_percentage=metrics.usage_percentage,
            is_warning_exceeded=metrics.is_warning_exceeded,
            is_limit_exceeded=metrics.is_limit_exceeded,
            component=component,
            additional_data=additional_data
        )
    
    def _log_entry(self, log_entry: StorageLogEntry) -> None:
        """
        Log a structured log entry.
        
        Args:
            log_entry: StorageLogEntry to log
        """
        try:
            if self.enable_json_format:
                # Log as JSON for structured logging
                log_message = log_entry.to_json()
            else:
                # Log as formatted string
                log_message = (f"[{log_entry.event_type}] {log_entry.message} "
                             f"(Storage: {log_entry.storage_gb:.2f}GB/{log_entry.limit_gb:.2f}GB, "
                             f"{log_entry.usage_percentage:.1f}%)")
            
            # Log at appropriate level
            if log_entry.level == LogLevel.DEBUG:
                storage_logger.debug(log_message)
            elif log_entry.level == LogLevel.INFO:
                storage_logger.info(log_message)
            elif log_entry.level == LogLevel.WARNING:
                storage_logger.warning(log_message)
            elif log_entry.level == LogLevel.ERROR:
                storage_logger.error(log_message)
            elif log_entry.level == LogLevel.CRITICAL:
                storage_logger.critical(log_message)
                
        except Exception as e:
            # Fallback logging to prevent log failures from breaking the system
            print(f"Storage logger error: {e}")
            storage_logger.error(f"Failed to log storage event: {e}")
    
    def log_debug(self, event_type: str, message: str, 
                  metrics: Optional[StorageMetrics] = None,
                  component: str = "storage_system",
                  additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug-level storage event"""
        log_entry = self._create_log_entry(LogLevel.DEBUG, event_type, message, metrics, component, additional_data)
        self._log_entry(log_entry)
    
    def log_info(self, event_type: str, message: str,
                 metrics: Optional[StorageMetrics] = None,
                 component: str = "storage_system",
                 additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an info-level storage event"""
        log_entry = self._create_log_entry(LogLevel.INFO, event_type, message, metrics, component, additional_data)
        self._log_entry(log_entry)
    
    def log_warning(self, event_type: str, message: str,
                    metrics: Optional[StorageMetrics] = None,
                    component: str = "storage_system",
                    additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning-level storage event"""
        log_entry = self._create_log_entry(LogLevel.WARNING, event_type, message, metrics, component, additional_data)
        self._log_entry(log_entry)
    
    def log_error(self, event_type: str, message: str,
                  metrics: Optional[StorageMetrics] = None,
                  component: str = "storage_system",
                  additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error-level storage event"""
        log_entry = self._create_log_entry(LogLevel.ERROR, event_type, message, metrics, component, additional_data)
        self._log_entry(log_entry)
    
    def log_critical(self, event_type: str, message: str,
                     metrics: Optional[StorageMetrics] = None,
                     component: str = "storage_system",
                     additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a critical-level storage event"""
        log_entry = self._create_log_entry(LogLevel.CRITICAL, event_type, message, metrics, component, additional_data)
        self._log_entry(log_entry)
    
    def log_storage_event(self, storage_event: StorageEvent, component: str = "storage_monitor") -> None:
        """
        Log a StorageEvent from the warning monitor.
        
        Args:
            storage_event: StorageEvent to log
            component: Component that generated the event
        """
        try:
            # Convert StorageEvent to metrics for logging
            metrics = StorageMetrics(
                total_bytes=int(storage_event.storage_gb * 1024**3),
                total_gb=storage_event.storage_gb,
                limit_gb=storage_event.limit_gb,
                usage_percentage=storage_event.usage_percentage,
                is_limit_exceeded=storage_event.is_limit_exceeded,
                is_warning_exceeded=storage_event.is_warning_exceeded,
                last_calculated=storage_event.timestamp
            )
            
            # Determine log level based on event type
            if storage_event.event_type in [StorageEventType.LIMIT_EXCEEDED, StorageEventType.MONITORING_ERROR]:
                level = LogLevel.CRITICAL
            elif storage_event.event_type in [StorageEventType.WARNING_THRESHOLD_EXCEEDED]:
                level = LogLevel.WARNING
            elif storage_event.event_type in [StorageEventType.WARNING_THRESHOLD_CLEARED, StorageEventType.LIMIT_CLEARED]:
                level = LogLevel.INFO
            else:
                level = LogLevel.DEBUG
            
            # Create and log entry
            log_entry = self._create_log_entry(
                level=level,
                event_type=storage_event.event_type.value,
                message=storage_event.message,
                metrics=metrics,
                component=component,
                additional_data=storage_event.additional_data
            )
            
            self._log_entry(log_entry)
            
        except Exception as e:
            storage_logger.error(f"Failed to log storage event: {e}")
    
    def log_threshold_exceeded(self, metrics: StorageMetrics, threshold_type: str = "warning") -> None:
        """
        Log threshold exceeded events with appropriate severity.
        
        Args:
            metrics: Current storage metrics
            threshold_type: Type of threshold ('warning' or 'limit')
        """
        if threshold_type == "limit":
            self.log_critical(
                event_type="storage_limit_exceeded",
                message=f"Storage limit exceeded: {metrics.total_gb:.2f}GB >= {metrics.limit_gb:.2f}GB",
                metrics=metrics,
                component="storage_enforcer",
                additional_data={
                    'threshold_type': threshold_type,
                    'exceeded_by_gb': metrics.total_gb - metrics.limit_gb,
                    'exceeded_by_percentage': metrics.usage_percentage - 100.0
                }
            )
        else:
            warning_threshold_gb = metrics.limit_gb * 0.8  # Assume 80% threshold
            self.log_warning(
                event_type="storage_warning_threshold_exceeded",
                message=f"Storage warning threshold exceeded: {metrics.total_gb:.2f}GB >= {warning_threshold_gb:.2f}GB",
                metrics=metrics,
                component="storage_monitor",
                additional_data={
                    'threshold_type': threshold_type,
                    'warning_threshold_gb': warning_threshold_gb,
                    'exceeded_by_gb': metrics.total_gb - warning_threshold_gb,
                    'exceeded_by_percentage': metrics.usage_percentage - 80.0
                }
            )
    
    def log_threshold_cleared(self, metrics: StorageMetrics, threshold_type: str = "warning") -> None:
        """
        Log threshold cleared events.
        
        Args:
            metrics: Current storage metrics
            threshold_type: Type of threshold ('warning' or 'limit')
        """
        if threshold_type == "limit":
            self.log_info(
                event_type="storage_limit_cleared",
                message=f"Storage usage dropped below limit: {metrics.total_gb:.2f}GB < {metrics.limit_gb:.2f}GB",
                metrics=metrics,
                component="storage_enforcer",
                additional_data={
                    'threshold_type': threshold_type,
                    'below_by_gb': metrics.limit_gb - metrics.total_gb,
                    'below_by_percentage': 100.0 - metrics.usage_percentage
                }
            )
        else:
            warning_threshold_gb = metrics.limit_gb * 0.8  # Assume 80% threshold
            self.log_info(
                event_type="storage_warning_threshold_cleared",
                message=f"Storage usage dropped below warning threshold: {metrics.total_gb:.2f}GB < {warning_threshold_gb:.2f}GB",
                metrics=metrics,
                component="storage_monitor",
                additional_data={
                    'threshold_type': threshold_type,
                    'warning_threshold_gb': warning_threshold_gb,
                    'below_by_gb': warning_threshold_gb - metrics.total_gb,
                    'below_by_percentage': 80.0 - metrics.usage_percentage
                }
            )
    
    def log_monitoring_event(self, event_type: str, message: str, 
                           metrics: Optional[StorageMetrics] = None,
                           additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log monitoring-related events.
        
        Args:
            event_type: Type of monitoring event
            message: Event message
            metrics: Optional storage metrics
            additional_data: Optional additional data
        """
        self.log_info(
            event_type=event_type,
            message=message,
            metrics=metrics,
            component="storage_warning_monitor",
            additional_data=additional_data
        )
    
    def log_configuration_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """
        Log configuration changes.
        
        Args:
            old_config: Previous configuration
            new_config: New configuration
        """
        self.log_info(
            event_type="storage_configuration_changed",
            message="Storage configuration updated",
            component="storage_configuration",
            additional_data={
                'old_config': old_config,
                'new_config': new_config,
                'changes': {k: {'old': old_config.get(k), 'new': v} 
                           for k, v in new_config.items() 
                           if old_config.get(k) != v}
            }
        )
    
    def log_cleanup_event(self, files_removed: int, space_freed_gb: float, 
                         metrics_before: StorageMetrics, metrics_after: StorageMetrics) -> None:
        """
        Log cleanup operations.
        
        Args:
            files_removed: Number of files removed
            space_freed_gb: Amount of space freed in GB
            metrics_before: Storage metrics before cleanup
            metrics_after: Storage metrics after cleanup
        """
        self.log_info(
            event_type="storage_cleanup_completed",
            message=f"Storage cleanup completed: {files_removed} files removed, {space_freed_gb:.2f}GB freed",
            metrics=metrics_after,
            component="storage_cleanup",
            additional_data={
                'files_removed': files_removed,
                'space_freed_gb': space_freed_gb,
                'usage_before_gb': metrics_before.total_gb,
                'usage_after_gb': metrics_after.total_gb,
                'usage_reduction_percentage': metrics_before.usage_percentage - metrics_after.usage_percentage
            }
        )
    
    def get_log_file_path(self) -> str:
        """Get the full path to the current log file"""
        return os.path.join(self.log_dir, self.log_file)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the log files.
        
        Returns:
            Dictionary containing log file statistics
        """
        try:
            log_file_path = self.get_log_file_path()
            
            stats = {
                'log_file_path': log_file_path,
                'log_file_exists': os.path.exists(log_file_path),
                'log_file_size_bytes': 0,
                'log_file_size_mb': 0.0,
                'backup_files': [],
                'total_log_size_mb': 0.0
            }
            
            if os.path.exists(log_file_path):
                file_size = os.path.getsize(log_file_path)
                stats['log_file_size_bytes'] = file_size
                stats['log_file_size_mb'] = file_size / (1024 * 1024)
                stats['total_log_size_mb'] = stats['log_file_size_mb']
                
                # Check for backup files
                log_dir_path = Path(self.log_dir)
                backup_pattern = f"{self.log_file}.*"
                backup_files = list(log_dir_path.glob(backup_pattern))
                
                for backup_file in backup_files:
                    backup_size = backup_file.stat().st_size
                    stats['backup_files'].append({
                        'name': backup_file.name,
                        'size_bytes': backup_size,
                        'size_mb': backup_size / (1024 * 1024)
                    })
                    stats['total_log_size_mb'] += backup_size / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            return {
                'error': str(e),
                'log_file_path': self.get_log_file_path(),
                'log_file_exists': False
            }


# Global storage event logger instance
_global_storage_logger: Optional[StorageEventLogger] = None


def get_storage_logger() -> StorageEventLogger:
    """
    Get the global storage event logger instance.
    
    Returns:
        StorageEventLogger instance
    """
    global _global_storage_logger
    
    if _global_storage_logger is None:
        _global_storage_logger = StorageEventLogger()
    
    return _global_storage_logger


def configure_storage_logging(log_dir: Optional[str] = None,
                            log_file: Optional[str] = None,
                            max_bytes: Optional[int] = None,
                            backup_count: Optional[int] = None,
                            log_level: Optional[int] = None,
                            enable_console: bool = True,
                            enable_json_format: bool = True) -> StorageEventLogger:
    """
    Configure the global storage event logger.
    
    Args:
        log_dir: Directory for log files
        log_file: Log file name
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        log_level: Logging level
        enable_console: Enable console logging
        enable_json_format: Enable JSON formatting
        
    Returns:
        Configured StorageEventLogger instance
    """
    global _global_storage_logger
    
    _global_storage_logger = StorageEventLogger(
        log_dir=log_dir,
        log_file=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
        log_level=log_level,
        enable_console=enable_console,
        enable_json_format=enable_json_format
    )
    
    return _global_storage_logger