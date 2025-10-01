# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Container Logging Configuration
Provides structured logging for containerized environments with JSON output
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in containers"""
    
    def __init__(self, service_name: str = "vedfolnir", include_extra: bool = True):
        super().__init__()
        self.service_name = service_name
        self.include_extra = include_extra
        self.container_id = self._get_container_id()
        self.container_name = os.getenv('CONTAINER_NAME', os.getenv('HOSTNAME', 'unknown'))
    
    def _get_container_id(self) -> str:
        """Get container ID if available"""
        try:
            if os.path.exists('/proc/self/cgroup'):
                with open('/proc/self/cgroup', 'r') as f:
                    for line in f:
                        if 'docker' in line:
                            return line.split('/')[-1].strip()[:12]
            return os.getenv('HOSTNAME', 'unknown')
        except Exception:
            return 'unknown'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        try:
            # Base log entry
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'service': self.service_name,
                'container_id': self.container_id,
                'container_name': self.container_name,
                'process_id': os.getpid(),
                'thread_id': record.thread,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            # Add exception information if present
            if record.exc_info:
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                    'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                    'traceback': self.formatException(record.exc_info)
                }
            
            # Add extra fields if enabled
            if self.include_extra:
                extra_fields = {}
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                                 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                                 'relativeCreated', 'thread', 'threadName', 'processName',
                                 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                        try:
                            # Ensure value is JSON serializable
                            json.dumps(value)
                            extra_fields[key] = value
                        except (TypeError, ValueError):
                            extra_fields[key] = str(value)
                
                if extra_fields:
                    log_entry['extra'] = extra_fields
            
            return json.dumps(log_entry, ensure_ascii=False)
            
        except Exception as e:
            # Fallback to simple format if JSON formatting fails
            return f"JSON_FORMAT_ERROR: {record.levelname} - {record.getMessage()} - Error: {e}"


class ContainerLoggerConfig:
    """Container logging configuration manager"""
    
    def __init__(self):
        self.is_container = self._detect_container_environment()
        self.json_logging_enabled = os.getenv('ENABLE_JSON_LOGGING', 'true').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.service_name = os.getenv('SERVICE_NAME', 'vedfolnir')
        
        # Container-specific settings
        if self.is_container:
            self.log_to_stdout = True
            self.log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
        else:
            self.log_to_stdout = False
            self.log_to_file = True
    
    def _detect_container_environment(self) -> bool:
        """Detect if running in a container"""
        return (
            os.path.exists('/.dockerenv') or
            os.getenv('CONTAINER_ENV') == 'true'
        )
    
    def setup_logging(self, logger_name: Optional[str] = None) -> logging.Logger:
        """Setup logging configuration for container environment"""
        # Get or create logger
        if logger_name:
            logger = logging.getLogger(logger_name)
        else:
            logger = logging.getLogger()
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Set log level
        logger.setLevel(getattr(logging, self.log_level, logging.INFO))
        
        # Choose formatter
        if self.json_logging_enabled and self.is_container:
            formatter = JSONFormatter(service_name=self.service_name)
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Add stdout handler for containers
        if self.log_to_stdout:
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setFormatter(formatter)
            stdout_handler.setLevel(logging.INFO)
            logger.addHandler(stdout_handler)
        
        # Add stderr handler for errors
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.setLevel(logging.ERROR)
        logger.addHandler(stderr_handler)
        
        # Add file handlers if enabled
        if self.log_to_file:
            self._add_file_handlers(logger, formatter)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    def _add_file_handlers(self, logger: logging.Logger, formatter: logging.Formatter) -> None:
        """Add file handlers for different log levels"""
        log_dir = '/app/logs/app' if self.is_container else 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # Main application log
        app_handler = RotatingFileHandler(
            os.path.join(log_dir, 'vedfolnir.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        app_handler.setFormatter(formatter)
        app_handler.setLevel(logging.INFO)
        logger.addHandler(app_handler)
        
        # Error log
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
        
        # Debug log (only in development)
        if os.getenv('FLASK_ENV') == 'development':
            debug_handler = RotatingFileHandler(
                os.path.join(log_dir, 'debug.log'),
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=2
            )
            debug_handler.setFormatter(formatter)
            debug_handler.setLevel(logging.DEBUG)
            logger.addHandler(debug_handler)
    
    def create_structured_logger(self, name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """Create a structured logger with additional context"""
        logger = logging.getLogger(name)
        
        if extra_context:
            # Create a custom adapter to add context to all log messages
            class ContextAdapter(logging.LoggerAdapter):
                def process(self, msg, kwargs):
                    # Add extra context to kwargs
                    if 'extra' not in kwargs:
                        kwargs['extra'] = {}
                    kwargs['extra'].update(extra_context)
                    return msg, kwargs
            
            return ContextAdapter(logger, extra_context)
        
        return logger
    
    def log_container_startup(self, logger: logging.Logger) -> None:
        """Log container startup information"""
        if not self.is_container:
            return
        
        startup_info = {
            'event': 'container_startup',
            'container_id': self._get_container_id(),
            'container_name': os.getenv('CONTAINER_NAME', 'unknown'),
            'image': os.getenv('CONTAINER_IMAGE', 'unknown'),
            'environment': {
                'flask_env': os.getenv('FLASK_ENV', 'production'),
                'flask_debug': os.getenv('FLASK_DEBUG', '0') == '1',
                'rq_workers': os.getenv('RQ_ENABLE_INTEGRATED_WORKERS', 'false'),
                'memory_limit': os.getenv('MEMORY_LIMIT', 'not_set'),
                'cpu_limit': os.getenv('CPU_LIMIT', 'not_set')
            }
        }
        
        logger.info("Container startup", extra=startup_info)
    
    def _get_container_id(self) -> str:
        """Get container ID if available"""
        try:
            if os.path.exists('/proc/self/cgroup'):
                with open('/proc/self/cgroup', 'r') as f:
                    for line in f:
                        if 'docker' in line:
                            return line.split('/')[-1].strip()[:12]
            return os.getenv('HOSTNAME', 'unknown')
        except Exception:
            return 'unknown'


# Global logger config instance
_logger_config: Optional[ContainerLoggerConfig] = None


def get_container_logger_config() -> ContainerLoggerConfig:
    """Get or create the global logger configuration"""
    global _logger_config
    if _logger_config is None:
        _logger_config = ContainerLoggerConfig()
    return _logger_config


def setup_container_logging(logger_name: Optional[str] = None) -> logging.Logger:
    """Setup container logging with appropriate configuration"""
    config = get_container_logger_config()
    logger = config.setup_logging(logger_name)
    
    # Log startup information
    config.log_container_startup(logger)
    
    return logger


def create_component_logger(component_name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """Create a logger for a specific component with context"""
    config = get_container_logger_config()
    
    # Add component context
    context = {'component': component_name}
    if extra_context:
        context.update(extra_context)
    
    return config.create_structured_logger(f"vedfolnir.{component_name}", context)