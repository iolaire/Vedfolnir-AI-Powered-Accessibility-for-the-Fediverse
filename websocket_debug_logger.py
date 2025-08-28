# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Debug Logger

Provides comprehensive debug logging capabilities for WebSocket connections
with configurable verbosity levels and structured logging output.
"""

import logging
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import IntEnum
import traceback
from contextlib import contextmanager


class DebugLevel(IntEnum):
    """Debug verbosity levels"""
    SILENT = 0      # No debug output
    ERROR = 1       # Errors only
    WARNING = 2     # Warnings and errors
    INFO = 3        # Info, warnings, and errors
    DEBUG = 4       # Debug, info, warnings, and errors
    VERBOSE = 5     # All messages including trace


class WebSocketDebugLogger:
    """Advanced debug logger for WebSocket operations"""
    
    def __init__(self, name: str = "websocket_debug", level: DebugLevel = DebugLevel.INFO):
        self.name = name
        self.level = level
        self.logger = logging.getLogger(name)
        self.session_id = None
        self.context_data = {}
        
        # Configure logger
        self._configure_logger()
        
        # Debug statistics
        self.stats = {
            'messages_logged': 0,
            'errors_logged': 0,
            'warnings_logged': 0,
            'session_start': datetime.now(timezone.utc),
            'events': []
        }
        
    def _configure_logger(self):
        """Configure the logger with appropriate handlers and formatters"""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set logging level based on debug level
        level_mapping = {
            DebugLevel.SILENT: logging.CRITICAL + 1,
            DebugLevel.ERROR: logging.ERROR,
            DebugLevel.WARNING: logging.WARNING,
            DebugLevel.INFO: logging.INFO,
            DebugLevel.DEBUG: logging.DEBUG,
            DebugLevel.VERBOSE: logging.DEBUG
        }
        
        self.logger.setLevel(level_mapping.get(self.level, logging.INFO))
        
        if self.level == DebugLevel.SILENT:
            return
            
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.logger.level)
        
        # Create formatter
        if self.level >= DebugLevel.VERBOSE:
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            )
            
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Create file handler if debug level is high enough
        if self.level >= DebugLevel.DEBUG:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            log_file = os.path.join(log_dir, f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            file_formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
    def set_session_id(self, session_id: str):
        """Set session ID for tracking"""
        self.session_id = session_id
        self.debug(f"Debug session started: {session_id}")
        
    def set_context(self, **kwargs):
        """Set context data for logging"""
        self.context_data.update(kwargs)
        if self.level >= DebugLevel.VERBOSE:
            self.debug(f"Context updated: {kwargs}")
            
    def clear_context(self):
        """Clear context data"""
        self.context_data.clear()
        if self.level >= DebugLevel.VERBOSE:
            self.debug("Context cleared")
            
    def _format_message(self, message: str, extra_data: Dict[str, Any] = None) -> str:
        """Format message with context and session information"""
        parts = []
        
        if self.session_id:
            parts.append(f"[{self.session_id}]")
            
        if self.context_data:
            context_str = " | ".join([f"{k}={v}" for k, v in self.context_data.items()])
            parts.append(f"({context_str})")
            
        parts.append(message)
        
        if extra_data and self.level >= DebugLevel.VERBOSE:
            parts.append(f"| Data: {json.dumps(extra_data, default=str)}")
            
        return " ".join(parts)
        
    def error(self, message: str, exception: Exception = None, extra_data: Dict[str, Any] = None):
        """Log error message"""
        if self.level < DebugLevel.ERROR:
            return
            
        formatted_message = self._format_message(message, extra_data)
        
        if exception:
            formatted_message += f" | Exception: {str(exception)}"
            if self.level >= DebugLevel.VERBOSE:
                formatted_message += f" | Traceback: {traceback.format_exc()}"
                
        self.logger.error(formatted_message)
        self.stats['errors_logged'] += 1
        self.stats['messages_logged'] += 1
        
        # Record event
        self._record_event('error', message, {'exception': str(exception) if exception else None})
        
    def warning(self, message: str, extra_data: Dict[str, Any] = None):
        """Log warning message"""
        if self.level < DebugLevel.WARNING:
            return
            
        formatted_message = self._format_message(message, extra_data)
        self.logger.warning(formatted_message)
        self.stats['warnings_logged'] += 1
        self.stats['messages_logged'] += 1
        
        self._record_event('warning', message)
        
    def info(self, message: str, extra_data: Dict[str, Any] = None):
        """Log info message"""
        if self.level < DebugLevel.INFO:
            return
            
        formatted_message = self._format_message(message, extra_data)
        self.logger.info(formatted_message)
        self.stats['messages_logged'] += 1
        
        self._record_event('info', message)
        
    def debug(self, message: str, extra_data: Dict[str, Any] = None):
        """Log debug message"""
        if self.level < DebugLevel.DEBUG:
            return
            
        formatted_message = self._format_message(message, extra_data)
        self.logger.debug(formatted_message)
        self.stats['messages_logged'] += 1
        
        self._record_event('debug', message)
        
    def verbose(self, message: str, extra_data: Dict[str, Any] = None):
        """Log verbose message"""
        if self.level < DebugLevel.VERBOSE:
            return
            
        formatted_message = self._format_message(message, extra_data)
        self.logger.debug(f"[VERBOSE] {formatted_message}")
        self.stats['messages_logged'] += 1
        
        self._record_event('verbose', message)
        
    def log_connection_attempt(self, server_url: str, transport: str = None, namespace: str = None):
        """Log WebSocket connection attempt"""
        data = {
            'server_url': server_url,
            'transport': transport,
            'namespace': namespace
        }
        self.info(f"Attempting WebSocket connection to {server_url}", data)
        
    def log_connection_success(self, server_url: str, transport: str = None, connect_time: float = None):
        """Log successful WebSocket connection"""
        data = {
            'server_url': server_url,
            'transport': transport,
            'connect_time': connect_time
        }
        self.info(f"WebSocket connection successful to {server_url}", data)
        
    def log_connection_failure(self, server_url: str, error: Exception, transport: str = None):
        """Log WebSocket connection failure"""
        data = {
            'server_url': server_url,
            'transport': transport
        }
        self.error(f"WebSocket connection failed to {server_url}", error, data)
        
    def log_message_sent(self, event: str, data: Any = None, namespace: str = None):
        """Log WebSocket message sent"""
        log_data = {
            'event': event,
            'namespace': namespace,
            'data_size': len(str(data)) if data else 0
        }
        
        if self.level >= DebugLevel.VERBOSE and data:
            log_data['data'] = data
            
        self.debug(f"WebSocket message sent: {event}", log_data)
        
    def log_message_received(self, event: str, data: Any = None, namespace: str = None):
        """Log WebSocket message received"""
        log_data = {
            'event': event,
            'namespace': namespace,
            'data_size': len(str(data)) if data else 0
        }
        
        if self.level >= DebugLevel.VERBOSE and data:
            log_data['data'] = data
            
        self.debug(f"WebSocket message received: {event}", log_data)
        
    def log_cors_check(self, origin: str, allowed: bool, reason: str = None):
        """Log CORS origin check"""
        data = {
            'origin': origin,
            'allowed': allowed,
            'reason': reason
        }
        
        if allowed:
            self.debug(f"CORS origin allowed: {origin}", data)
        else:
            self.warning(f"CORS origin rejected: {origin} - {reason}", data)
            
    def log_authentication_attempt(self, user_id: str = None, success: bool = None, reason: str = None):
        """Log authentication attempt"""
        data = {
            'user_id': user_id,
            'success': success,
            'reason': reason
        }
        
        if success:
            self.info(f"Authentication successful for user: {user_id}", data)
        else:
            self.warning(f"Authentication failed for user: {user_id} - {reason}", data)
            
    def log_transport_fallback(self, from_transport: str, to_transport: str, reason: str = None):
        """Log transport fallback"""
        data = {
            'from_transport': from_transport,
            'to_transport': to_transport,
            'reason': reason
        }
        self.info(f"Transport fallback: {from_transport} -> {to_transport}", data)
        
    def log_performance_metric(self, metric_name: str, value: float, unit: str = None):
        """Log performance metric"""
        data = {
            'metric': metric_name,
            'value': value,
            'unit': unit
        }
        self.debug(f"Performance metric - {metric_name}: {value} {unit or ''}", data)
        
    def _record_event(self, level: str, message: str, extra_data: Dict[str, Any] = None):
        """Record event for statistics"""
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': level,
            'message': message,
            'session_id': self.session_id,
            'context': self.context_data.copy()
        }
        
        if extra_data:
            event['extra_data'] = extra_data
            
        self.stats['events'].append(event)
        
        # Keep only last 1000 events to prevent memory issues
        if len(self.stats['events']) > 1000:
            self.stats['events'] = self.stats['events'][-1000:]
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get debug logging statistics"""
        runtime = datetime.now(timezone.utc) - self.stats['session_start']
        
        return {
            'session_id': self.session_id,
            'debug_level': self.level.name,
            'runtime_seconds': runtime.total_seconds(),
            'messages_logged': self.stats['messages_logged'],
            'errors_logged': self.stats['errors_logged'],
            'warnings_logged': self.stats['warnings_logged'],
            'events_count': len(self.stats['events']),
            'session_start': self.stats['session_start'].isoformat()
        }
        
    def export_debug_log(self, filename: str = None) -> str:
        """Export debug log to file"""
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"websocket_debug_log_{timestamp}.json"
            
        export_data = {
            'statistics': self.get_statistics(),
            'events': self.stats['events'],
            'context': self.context_data,
            'export_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
            
        self.info(f"Debug log exported to {filename}")
        return filename
        
    @contextmanager
    def debug_context(self, **context_data):
        """Context manager for temporary debug context"""
        old_context = self.context_data.copy()
        self.set_context(**context_data)
        
        try:
            yield self
        finally:
            self.context_data = old_context
            
    @contextmanager
    def timed_operation(self, operation_name: str):
        """Context manager for timing operations"""
        start_time = datetime.now(timezone.utc)
        self.debug(f"Starting operation: {operation_name}")
        
        try:
            yield self
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.error(f"Operation failed: {operation_name} (duration: {duration:.3f}s)", e)
            raise
        else:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.debug(f"Operation completed: {operation_name} (duration: {duration:.3f}s)")
            self.log_performance_metric(f"{operation_name}_duration", duration, "seconds")


class WebSocketDebugManager:
    """Manager for WebSocket debug loggers"""
    
    def __init__(self):
        self.loggers = {}
        self.global_level = DebugLevel.INFO
        
    def get_logger(self, name: str, level: DebugLevel = None) -> WebSocketDebugLogger:
        """Get or create a debug logger"""
        if name not in self.loggers:
            effective_level = level or self.global_level
            self.loggers[name] = WebSocketDebugLogger(name, effective_level)
            
        return self.loggers[name]
        
    def set_global_level(self, level: DebugLevel):
        """Set global debug level for all loggers"""
        self.global_level = level
        
        for logger in self.loggers.values():
            logger.level = level
            logger._configure_logger()
            
    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics from all loggers"""
        return {
            name: logger.get_statistics()
            for name, logger in self.loggers.items()
        }
        
    def export_all_logs(self, directory: str = "debug_logs") -> List[str]:
        """Export all debug logs to directory"""
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        exported_files = []
        
        for name, logger in self.loggers.items():
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(directory, f"{name}_debug_log_{timestamp}.json")
            logger.export_debug_log(filename)
            exported_files.append(filename)
            
        return exported_files


# Global debug manager instance
debug_manager = WebSocketDebugManager()


def get_debug_logger(name: str = "websocket", level: DebugLevel = None) -> WebSocketDebugLogger:
    """Get a WebSocket debug logger"""
    return debug_manager.get_logger(name, level)


def set_debug_level(level: DebugLevel):
    """Set global debug level"""
    debug_manager.set_global_level(level)


def configure_debug_from_env():
    """Configure debug logging from environment variables"""
    debug_level_str = os.getenv('WEBSOCKET_DEBUG_LEVEL', 'INFO').upper()
    
    level_mapping = {
        'SILENT': DebugLevel.SILENT,
        'ERROR': DebugLevel.ERROR,
        'WARNING': DebugLevel.WARNING,
        'INFO': DebugLevel.INFO,
        'DEBUG': DebugLevel.DEBUG,
        'VERBOSE': DebugLevel.VERBOSE
    }
    
    level = level_mapping.get(debug_level_str, DebugLevel.INFO)
    set_debug_level(level)
    
    return level