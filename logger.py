# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import logging
import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# Define custom log levels for structured logging
ERROR_SUMMARY = 25  # Between WARNING (30) and INFO (20)
logging.addLevelName(ERROR_SUMMARY, "ERROR_SUMMARY")

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in a structured format (JSON or text)
    """
    
    def __init__(self, use_json: bool = False, include_traceback: bool = True):
        """
        Initialize the formatter
        
        Args:
            use_json: Whether to output logs as JSON
            include_traceback: Whether to include traceback in error logs
        """
        super().__init__()
        self.use_json = use_json
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string
        """
        # Extract basic log information
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if available
        if record.exc_info and self.include_traceback:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)
        
        # Add any custom fields that were passed via extra parameter
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno", 
                          "lineno", "module", "msecs", "message", "msg", 
                          "name", "pathname", "process", "processName", 
                          "relativeCreated", "stack_info", "thread", "threadName",
                          "extra"]:
                log_data[key] = value
        
        # Format as JSON or text
        if self.use_json:
            return json.dumps(log_data)
        else:
            # Format as structured text
            base = f"[{log_data['timestamp']}] {log_data['level']} {log_data['logger']} - {log_data['message']}"
            
            # Add context information
            context = []
            for key, value in log_data.items():
                if key not in ["timestamp", "level", "logger", "message", "exception", "module", "function", "line"]:
                    context.append(f"{key}={value}")
            
            if context:
                base += f" ({', '.join(context)})"
            
            # Add exception information
            if "exception" in log_data:
                base += f"\nException: {log_data['exception']['type']}: {log_data['exception']['message']}"
                if self.include_traceback:
                    base += f"\nTraceback:\n{''.join(log_data['exception']['traceback'])}"
            
            return base


class ErrorCollector:
    """
    Collects error information during processing for summary reporting
    """
    
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        self.component_errors: Dict[str, int] = {}
        self.error_types: Dict[str, int] = {}
    
    def add_error(self, error_type: str, message: str, component: str, 
                 details: Optional[Dict[str, Any]] = None, 
                 exception: Optional[Exception] = None) -> None:
        """
        Add an error to the collector
        
        Args:
            error_type: Type of error (e.g., "API", "Database", "Processing")
            message: Error message
            component: Component where the error occurred
            details: Additional error details
            exception: Exception object if available
        """
        error_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "message": message,
            "component": component,
            "details": details or {}
        }
        
        # Add exception information if available
        if exception:
            error_info["exception"] = {
                "type": exception.__class__.__name__,
                "message": str(exception),
                "traceback": traceback.format_exception(type(exception), exception, exception.__traceback__)
            }
        
        self.errors.append(error_info)
        
        # Update error counts
        self.error_counts[message] = self.error_counts.get(message, 0) + 1
        self.component_errors[component] = self.component_errors.get(component, 0) + 1
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    def get_summary(self) -> str:
        """
        Get a summary of collected errors
        
        Returns:
            Formatted error summary
        """
        if not self.errors:
            return "No errors recorded"
        
        summary = [
            "=== Error Summary ===",
            f"Total errors: {len(self.errors)}",
            "",
            "=== Errors by Type ==="
        ]
        
        for error_type, count in sorted(self.error_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.errors)) * 100
            summary.append(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        summary.append("")
        summary.append("=== Errors by Component ===")
        
        for component, count in sorted(self.component_errors.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.errors)) * 100
            summary.append(f"  {component}: {count} ({percentage:.1f}%)")
        
        summary.append("")
        summary.append("=== Most Common Errors ===")
        
        for message, count in sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(self.errors)) * 100
            summary.append(f"  {message}: {count} ({percentage:.1f}%)")
        
        summary.append("")
        summary.append("=== Recent Errors ===")
        
        for error in self.errors[-5:]:
            summary.append(f"  [{error['timestamp']}] {error['type']} in {error['component']}: {error['message']}")
        
        return "\n".join(summary)
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        Get a detailed report of collected errors
        
        Returns:
            Dictionary with error information
        """
        return {
            "total_errors": len(self.errors),
            "errors_by_type": self.error_types,
            "errors_by_component": self.component_errors,
            "common_errors": self.error_counts,
            "errors": self.errors
        }
    
    def reset(self) -> None:
        """Reset the error collector"""
        self.__init__()


# Global error collector
error_collector = ErrorCollector()


def setup_logging(log_level: str = "INFO", 
                 log_file: Optional[str] = "logs/vedfolnir.log",
                 use_json: bool = False,
                 include_traceback: bool = True) -> None:
    """
    Set up logging with structured formatter
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file, or None to disable file logging
        use_json: Whether to output logs as JSON
        include_traceback: Whether to include traceback in error logs
    """
    from security_utils import is_safe_path, sanitize_filename
    
    # Create formatter
    formatter = StructuredFormatter(use_json=use_json, include_traceback=include_traceback)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        # Validate and sanitize the log file path to prevent path traversal
        base_dir = os.path.abspath("logs")
        
        # Sanitize the filename component
        log_filename = os.path.basename(log_file)
        log_filename = sanitize_filename(log_filename)
        
        # Construct safe path within logs directory
        safe_log_file = os.path.join(base_dir, log_filename)
        
        # Verify the path is safe (within base directory)
        if not is_safe_path(safe_log_file, base_dir):
            # Fallback to default safe path
            safe_log_file = os.path.join(base_dir, "vedfolnir.log")
        
        # Create logs directory if it doesn't exist
        os.makedirs(base_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(safe_log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def log_with_context(logger: logging.Logger, level: int, msg: str, 
                    extra: Optional[Dict[str, Any]] = None, **kwargs) -> None:
    """
    Log a message with additional context
    
    Args:
        logger: Logger to use
        level: Log level
        msg: Log message
        extra: Additional context to include in the log
        **kwargs: Additional keyword arguments to pass to the logger
    """
    if extra is None:
        extra = {}
    
    # Create LogRecord with extra context
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=kwargs.get("exc_info"),
    )
    
    # Add extra context
    for key, value in extra.items():
        setattr(record, key, value)
    
    # Log the record
    logger.handle(record)


def log_error(logger: logging.Logger, error_type: str, message: str, 
             component: str, details: Optional[Dict[str, Any]] = None,
             exception: Optional[Exception] = None) -> None:
    """
    Log an error and add it to the error collector
    
    Args:
        logger: Logger to use
        error_type: Type of error (e.g., "API", "Database", "Processing")
        message: Error message
        component: Component where the error occurred
        details: Additional error details
        exception: Exception object if available
    """
    # Add error to collector
    error_collector.add_error(
        error_type=error_type,
        message=message,
        component=component,
        details=details,
        exception=exception
    )
    
    # Log the error
    extra = {
        "error_type": error_type,
        "component": component
    }
    
    if details:
        extra.update(details)
    
    logger.error(message, extra=extra, exc_info=exception)


def log_error_summary(logger: logging.Logger) -> None:
    """
    Log a summary of collected errors
    
    Args:
        logger: Logger to use
    """
    summary = error_collector.get_summary()
    logger.log(ERROR_SUMMARY, "Error Summary Report")
    for line in summary.split("\n"):
        logger.log(ERROR_SUMMARY, line)


def get_error_summary() -> str:
    """
    Get a summary of collected errors
    
    Returns:
        Formatted error summary
    """
    return error_collector.get_summary()


def get_error_report() -> Dict[str, Any]:
    """
    Get a detailed report of collected errors
    
    Returns:
        Dictionary with error information
    """
    return error_collector.get_detailed_report()


def reset_error_collector() -> None:
    """Reset the error collector"""
    error_collector.reset()