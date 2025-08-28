# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Production Logging System

This module provides production-grade logging for WebSocket connections,
including structured logging, log rotation, remote logging capabilities,
and comprehensive error tracking with alerting integration.
"""

import os
import json
import logging
import logging.handlers
import traceback
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import threading
from contextlib import contextmanager

from websocket_production_config import ProductionLoggingConfig

# Try to import optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


class WebSocketLogLevel(Enum):
    """WebSocket-specific log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class WebSocketLogCategory(Enum):
    """WebSocket log categories"""
    CONNECTION = "connection"
    MESSAGE = "message"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"
    SYSTEM = "system"
    MONITORING = "monitoring"


@dataclass
class WebSocketLogEntry:
    """Structured log entry for WebSocket events"""
    
    timestamp: str
    level: str
    category: str
    event_type: str
    message: str
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    connection_id: Optional[str] = None
    namespace: Optional[str] = None
    event_name: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[float] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class ProductionWebSocketLogger:
    """
    Production-grade WebSocket logger
    
    Provides structured logging, log rotation, remote logging,
    and comprehensive error tracking for WebSocket connections.
    """
    
    def __init__(self, config: ProductionLoggingConfig, logger_name: str = "websocket"):
        """
        Initialize production WebSocket logger
        
        Args:
            config: Production logging configuration
            logger_name: Name for the logger instance
        """
        self.config = config
        self.logger_name = logger_name
        self.logger = logging.getLogger(logger_name)
        self._setup_logging()
        self._remote_logging_session = None
        self._log_buffer = []
        self._buffer_lock = threading.Lock()
        
        # Initialize remote logging if configured
        if self.config.remote_logging_enabled and REQUESTS_AVAILABLE:
            self._setup_remote_logging()
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        log_level = getattr(logging, self.config.websocket_log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create formatters
        if self.config.json_logging and JSON_LOGGER_AVAILABLE:
            formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                fmt=self.config.log_format,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handlers
        self._setup_file_handlers(formatter)
        
        # Syslog handler
        if self.config.syslog_server:
            self._setup_syslog_handler(formatter)
        
        self.logger.info("Production WebSocket logging initialized")
    
    def _setup_file_handlers(self, formatter: logging.Formatter) -> None:
        """Setup file logging handlers with rotation"""
        log_files = {
            'websocket': self.config.websocket_log_file,
            'security': self.config.security_log_file,
            'performance': self.config.performance_log_file,
            'error': self.config.error_log_file
        }
        
        for log_type, log_file in log_files.items():
            if not log_file:
                continue
            
            try:
                # Create log directory if it doesn't exist
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                if self.config.log_rotation_enabled:
                    # Parse max log size
                    max_bytes = self._parse_log_size(self.config.max_log_size)
                    
                    handler = logging.handlers.RotatingFileHandler(
                        log_file,
                        maxBytes=max_bytes,
                        backupCount=self.config.backup_count,
                        encoding='utf-8'
                    )
                else:
                    handler = logging.FileHandler(log_file, encoding='utf-8')
                
                handler.setFormatter(formatter)
                
                # Set appropriate log level for each handler
                if log_type == 'security':
                    handler.setLevel(getattr(logging, self.config.security_log_level.upper(), logging.WARNING))
                elif log_type == 'performance':
                    handler.setLevel(getattr(logging, self.config.performance_log_level.upper(), logging.INFO))
                elif log_type == 'error':
                    handler.setLevel(getattr(logging, self.config.error_log_level.upper(), logging.ERROR))
                else:
                    handler.setLevel(getattr(logging, self.config.websocket_log_level.upper(), logging.INFO))
                
                self.logger.addHandler(handler)
                
            except Exception as e:
                print(f"Failed to setup file handler for {log_type}: {e}")
    
    def _setup_syslog_handler(self, formatter: logging.Formatter) -> None:
        """Setup syslog handler for remote logging"""
        try:
            if ':' in self.config.syslog_server:
                host, port = self.config.syslog_server.split(':')
                port = int(port)
            else:
                host = self.config.syslog_server
                port = 514
            
            handler = logging.handlers.SysLogHandler(
                address=(host, port),
                facility=logging.handlers.SysLogHandler.LOG_LOCAL0
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        except Exception as e:
            self.logger.error(f"Failed to setup syslog handler: {e}")
    
    def _setup_remote_logging(self) -> None:
        """Setup remote logging session"""
        try:
            self._remote_logging_session = requests.Session()
            self._remote_logging_session.timeout = 5
            
        except Exception as e:
            self.logger.error(f"Failed to setup remote logging: {e}")
    
    def _parse_log_size(self, size_str: str) -> int:
        """Parse log size string to bytes"""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def log_connection_event(self, event_type: str, message: str, 
                           session_id: Optional[str] = None,
                           user_id: Optional[int] = None,
                           connection_id: Optional[str] = None,
                           client_ip: Optional[str] = None,
                           user_agent: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None,
                           level: WebSocketLogLevel = WebSocketLogLevel.INFO) -> None:
        """Log WebSocket connection event"""
        
        log_entry = WebSocketLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=WebSocketLogCategory.CONNECTION.value,
            event_type=event_type,
            message=message,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            client_ip=client_ip,
            user_agent=user_agent,
            metadata=metadata
        )
        
        self._log_entry(log_entry)
    
    def log_message_event(self, event_type: str, message: str,
                         session_id: Optional[str] = None,
                         user_id: Optional[int] = None,
                         connection_id: Optional[str] = None,
                         namespace: Optional[str] = None,
                         event_name: Optional[str] = None,
                         duration_ms: Optional[float] = None,
                         metadata: Optional[Dict[str, Any]] = None,
                         level: WebSocketLogLevel = WebSocketLogLevel.INFO) -> None:
        """Log WebSocket message event"""
        
        log_entry = WebSocketLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=WebSocketLogCategory.MESSAGE.value,
            event_type=event_type,
            message=message,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            namespace=namespace,
            event_name=event_name,
            duration_ms=duration_ms,
            metadata=metadata
        )
        
        self._log_entry(log_entry)
    
    def log_security_event(self, event_type: str, message: str,
                          session_id: Optional[str] = None,
                          user_id: Optional[int] = None,
                          connection_id: Optional[str] = None,
                          client_ip: Optional[str] = None,
                          error_code: Optional[str] = None,
                          error_details: Optional[Dict[str, Any]] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          level: WebSocketLogLevel = WebSocketLogLevel.WARNING) -> None:
        """Log WebSocket security event"""
        
        log_entry = WebSocketLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=WebSocketLogCategory.SECURITY.value,
            event_type=event_type,
            message=message,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            client_ip=client_ip,
            error_code=error_code,
            error_details=error_details,
            metadata=metadata
        )
        
        self._log_entry(log_entry)
    
    def log_performance_event(self, event_type: str, message: str,
                             duration_ms: Optional[float] = None,
                             session_id: Optional[str] = None,
                             user_id: Optional[int] = None,
                             connection_id: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None,
                             level: WebSocketLogLevel = WebSocketLogLevel.INFO) -> None:
        """Log WebSocket performance event"""
        
        log_entry = WebSocketLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=WebSocketLogCategory.PERFORMANCE.value,
            event_type=event_type,
            message=message,
            duration_ms=duration_ms,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            metadata=metadata
        )
        
        self._log_entry(log_entry)
    
    def log_error_event(self, event_type: str, message: str,
                       error_code: Optional[str] = None,
                       error_details: Optional[Dict[str, Any]] = None,
                       session_id: Optional[str] = None,
                       user_id: Optional[int] = None,
                       connection_id: Optional[str] = None,
                       exception: Optional[Exception] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       level: WebSocketLogLevel = WebSocketLogLevel.ERROR) -> None:
        """Log WebSocket error event"""
        
        # Add exception details if provided
        if exception:
            if not error_details:
                error_details = {}
            error_details.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'traceback': traceback.format_exc()
            })
        
        log_entry = WebSocketLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=WebSocketLogCategory.ERROR.value,
            event_type=event_type,
            message=message,
            error_code=error_code,
            error_details=error_details,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            metadata=metadata
        )
        
        self._log_entry(log_entry)
    
    def log_system_event(self, event_type: str, message: str,
                        metadata: Optional[Dict[str, Any]] = None,
                        level: WebSocketLogLevel = WebSocketLogLevel.INFO) -> None:
        """Log WebSocket system event"""
        
        log_entry = WebSocketLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level.value,
            category=WebSocketLogCategory.SYSTEM.value,
            event_type=event_type,
            message=message,
            metadata=metadata
        )
        
        self._log_entry(log_entry)
    
    def _log_entry(self, log_entry: WebSocketLogEntry) -> None:
        """Process and output log entry"""
        # Log to standard logger
        log_level = getattr(logging, log_entry.level.upper(), logging.INFO)
        
        if self.config.structured_logging:
            # Log structured data
            extra_data = log_entry.to_dict()
            # Remove 'message' from extra to avoid conflict with LogRecord
            extra_data.pop('message', None)
            self.logger.log(log_level, log_entry.message, extra=extra_data)
        else:
            # Log formatted message
            formatted_message = self._format_log_message(log_entry)
            self.logger.log(log_level, formatted_message)
        
        # Send to remote logging if configured
        if self.config.remote_logging_enabled:
            self._send_remote_log(log_entry)
    
    def _format_log_message(self, log_entry: WebSocketLogEntry) -> str:
        """Format log entry as readable message"""
        parts = [
            f"[{log_entry.category.upper()}]",
            f"[{log_entry.event_type}]",
            log_entry.message
        ]
        
        if log_entry.session_id:
            parts.append(f"session={log_entry.session_id}")
        
        if log_entry.user_id:
            parts.append(f"user={log_entry.user_id}")
        
        if log_entry.connection_id:
            parts.append(f"conn={log_entry.connection_id}")
        
        if log_entry.duration_ms is not None:
            parts.append(f"duration={log_entry.duration_ms:.2f}ms")
        
        if log_entry.error_code:
            parts.append(f"error_code={log_entry.error_code}")
        
        return " ".join(parts)
    
    def _send_remote_log(self, log_entry: WebSocketLogEntry) -> None:
        """Send log entry to remote logging service"""
        if not self._remote_logging_session or not self.config.log_aggregation_service:
            return
        
        try:
            # Buffer logs for batch sending
            with self._buffer_lock:
                self._log_buffer.append(log_entry.to_dict())
                
                # Send buffer if it's full or for critical events
                if (len(self._log_buffer) >= 10 or 
                    log_entry.level in ['ERROR', 'CRITICAL']):
                    self._flush_log_buffer()
                    
        except Exception as e:
            # Don't let remote logging failures affect the application
            pass
    
    def _flush_log_buffer(self) -> None:
        """Flush log buffer to remote service"""
        if not self._log_buffer:
            return
        
        try:
            payload = {
                'logs': self._log_buffer.copy(),
                'source': 'websocket',
                'hostname': socket.gethostname(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            response = self._remote_logging_session.post(
                self.config.log_aggregation_service,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                self._log_buffer.clear()
                
        except Exception as e:
            # Don't let remote logging failures affect the application
            pass
    
    @contextmanager
    def log_performance_context(self, event_type: str, message: str,
                               session_id: Optional[str] = None,
                               user_id: Optional[int] = None,
                               connection_id: Optional[str] = None,
                               metadata: Optional[Dict[str, Any]] = None):
        """Context manager for logging performance events with timing"""
        start_time = datetime.now()
        
        try:
            yield
        finally:
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            self.log_performance_event(
                event_type=event_type,
                message=message,
                duration_ms=duration_ms,
                session_id=session_id,
                user_id=user_id,
                connection_id=connection_id,
                metadata=metadata
            )
    
    def flush_logs(self) -> None:
        """Flush all pending logs"""
        # Flush log buffer
        with self._buffer_lock:
            if self._log_buffer:
                self._flush_log_buffer()
        
        # Flush all handlers
        for handler in self.logger.handlers:
            handler.flush()
    
    def close(self) -> None:
        """Close logger and cleanup resources"""
        self.flush_logs()
        
        # Close remote logging session
        if self._remote_logging_session:
            self._remote_logging_session.close()
        
        # Close all handlers
        for handler in self.logger.handlers:
            handler.close()


class WebSocketProductionErrorHandler:
    """
    Production-grade error handler for WebSocket connections
    
    Provides comprehensive error handling, recovery mechanisms,
    and integration with monitoring and alerting systems.
    """
    
    def __init__(self, logger: ProductionWebSocketLogger):
        """
        Initialize production error handler
        
        Args:
            logger: Production WebSocket logger instance
        """
        self.logger = logger
        self.error_counts = {}
        self.error_lock = threading.Lock()
    
    def handle_connection_error(self, error: Exception, 
                              session_id: Optional[str] = None,
                              user_id: Optional[int] = None,
                              connection_id: Optional[str] = None,
                              client_ip: Optional[str] = None) -> None:
        """Handle WebSocket connection errors"""
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Track error frequency
        with self.error_lock:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log error event
        self.logger.log_error_event(
            event_type="connection_error",
            message=f"WebSocket connection error: {error_message}",
            error_code=error_type,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            exception=error,
            metadata={
                'client_ip': client_ip,
                'error_count': self.error_counts[error_type]
            }
        )
    
    def handle_message_error(self, error: Exception,
                           event_name: Optional[str] = None,
                           namespace: Optional[str] = None,
                           session_id: Optional[str] = None,
                           user_id: Optional[int] = None,
                           connection_id: Optional[str] = None) -> None:
        """Handle WebSocket message processing errors"""
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Track error frequency
        with self.error_lock:
            key = f"{error_type}_{event_name or 'unknown'}"
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Log error event
        self.logger.log_error_event(
            event_type="message_error",
            message=f"WebSocket message error in {event_name or 'unknown'}: {error_message}",
            error_code=error_type,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            exception=error,
            metadata={
                'event_name': event_name,
                'namespace': namespace,
                'error_count': self.error_counts.get(key, 0)
            }
        )
    
    def handle_security_error(self, error: Exception,
                            security_event_type: str,
                            session_id: Optional[str] = None,
                            user_id: Optional[int] = None,
                            connection_id: Optional[str] = None,
                            client_ip: Optional[str] = None) -> None:
        """Handle WebSocket security errors"""
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Track security error frequency
        with self.error_lock:
            key = f"security_{security_event_type}"
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Log security event
        self.logger.log_security_event(
            event_type=security_event_type,
            message=f"WebSocket security error: {error_message}",
            error_code=error_type,
            session_id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            client_ip=client_ip,
            exception=error,
            metadata={
                'security_event': security_event_type,
                'error_count': self.error_counts.get(key, 0)
            },
            level=WebSocketLogLevel.CRITICAL
        )
    
    def get_error_statistics(self) -> Dict[str, int]:
        """Get error statistics"""
        with self.error_lock:
            return self.error_counts.copy()
    
    def reset_error_statistics(self) -> None:
        """Reset error statistics"""
        with self.error_lock:
            self.error_counts.clear()


def create_production_logger(config: ProductionLoggingConfig, 
                           logger_name: str = "websocket") -> ProductionWebSocketLogger:
    """
    Factory function to create production WebSocket logger
    
    Args:
        config: Production logging configuration
        logger_name: Name for the logger instance
    
    Returns:
        Configured production WebSocket logger
    """
    return ProductionWebSocketLogger(config, logger_name)


def create_production_error_handler(logger: ProductionWebSocketLogger) -> WebSocketProductionErrorHandler:
    """
    Factory function to create production error handler
    
    Args:
        logger: Production WebSocket logger instance
    
    Returns:
        Configured production error handler
    """
    return WebSocketProductionErrorHandler(logger)