# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Log Filter

Filters out cosmetic WebSocket errors that don't affect functionality.
These errors are internal to Flask-SocketIO and don't impact WebSocket operation.
"""

import logging
import re

class WebSocketErrorFilter(logging.Filter):
    """
    Filter to suppress cosmetic WebSocket errors that don't affect functionality
    
    This filter removes log entries for the "write() before start_response" error
    that occurs due to internal Flask-SocketIO WSGI handling, while preserving
    all other important log messages.
    """
    
    def __init__(self):
        super().__init__()
        self.filtered_count = 0
        
        # Patterns to filter out
        self.filter_patterns = [
            r'write\(\) before start_response',
            r'AssertionError.*write\(\) before start_response',
            # Only filter WebSocket-related 500 errors, not all 500 errors
            r'socket\.io.*transport=websocket.*500.*Error on request',
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.filter_patterns]
    
    def filter(self, record):
        """
        Filter log records
        
        Args:
            record: LogRecord to evaluate
            
        Returns:
            bool: True to keep the record, False to filter it out
        """
        try:
            # Get the log message
            message = record.getMessage() if hasattr(record, 'getMessage') else str(record.msg)
            
            # Check if this message should be filtered
            for pattern in self.compiled_patterns:
                if pattern.search(message):
                    self.filtered_count += 1
                    return False  # Filter out this message
            
            # Keep all other messages
            return True
            
        except Exception:
            # If there's any error in filtering, keep the message
            return True
    
    def get_filtered_count(self):
        """Get the number of messages filtered"""
        return self.filtered_count

def setup_websocket_log_filter():
    """
    Set up WebSocket error filtering for relevant loggers
    
    Returns:
        WebSocketErrorFilter: The filter instance for monitoring
    """
    # Create the filter
    websocket_filter = WebSocketErrorFilter()
    
    # Apply to werkzeug logger (handles WSGI errors)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(websocket_filter)
    
    # Apply to root logger to catch any other related errors
    root_logger = logging.getLogger()
    root_logger.addFilter(websocket_filter)
    
    logging.info("WebSocket error filter applied to suppress cosmetic Flask-SocketIO errors")
    
    return websocket_filter

def remove_websocket_log_filter(websocket_filter):
    """
    Remove WebSocket error filtering
    
    Args:
        websocket_filter: The filter instance to remove
    """
    if websocket_filter:
        # Remove from werkzeug logger
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.removeFilter(websocket_filter)
        
        # Remove from root logger
        root_logger = logging.getLogger()
        root_logger.removeFilter(websocket_filter)
        
        logging.info(f"WebSocket error filter removed (filtered {websocket_filter.get_filtered_count()} messages)")

# Global filter instance for monitoring
_websocket_filter = None

def get_websocket_filter_stats():
    """
    Get statistics about filtered WebSocket errors
    
    Returns:
        dict: Statistics about filtered messages
    """
    global _websocket_filter
    if _websocket_filter:
        return {
            'filtered_count': _websocket_filter.get_filtered_count(),
            'filter_active': True
        }
    else:
        return {
            'filtered_count': 0,
            'filter_active': False
        }