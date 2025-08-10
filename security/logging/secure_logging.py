# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Secure Logging Utilities

Provides secure logging that prevents sensitive data exposure and log injection.
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict

class SecureLogger:
    """Secure logger that sanitizes sensitive data"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
        # Sensitive data patterns to sanitize
        self.sensitive_patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'password=***'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'token=***'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'secret=***'),
            (r'key["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'key=***'),
            (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'api_key=***'),
            (r'access_token["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'access_token=***'),
        ]
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize log message to remove sensitive data"""
        if not isinstance(message, str):
            message = str(message)
        
        # Remove sensitive data
        for pattern, replacement in self.sensitive_patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        # Prevent log injection by removing newlines and control characters
        message = re.sub(r'[\r\n\t]', ' ', message)
        message = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', message)
        
        # Limit message length
        if len(message) > 1000:
            message = message[:997] + "..."
        
        return message
    
    def debug(self, message: Any, *args, **kwargs):
        """Log debug message securely"""
        self.logger.debug(self._sanitize_message(str(message)), *args, **kwargs)
    
    def info(self, message: Any, *args, **kwargs):
        """Log info message securely"""
        self.logger.info(self._sanitize_message(str(message)), *args, **kwargs)
    
    def warning(self, message: Any, *args, **kwargs):
        """Log warning message securely"""
        self.logger.warning(self._sanitize_message(str(message)), *args, **kwargs)
    
    def error(self, message: Any, *args, **kwargs):
        """Log error message securely"""
        self.logger.error(self._sanitize_message(str(message)), *args, **kwargs)
    
    def critical(self, message: Any, *args, **kwargs):
        """Log critical message securely"""
        self.logger.critical(self._sanitize_message(str(message)), *args, **kwargs)
    
    def exception(self, message: Any, *args, **kwargs):
        """Log exception message securely"""
        self.logger.exception(self._sanitize_message(str(message)), *args, **kwargs)

def get_secure_logger(name: str) -> SecureLogger:
    """Get a secure logger instance"""
    return SecureLogger(name)

def log_security_event(event_type: str, details: Dict[str, Any] = None):
    """Log security events with proper sanitization"""
    security_logger = get_secure_logger('security')
    
    event_data = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    if details:
        # Sanitize details
        sanitized_details = {}
        for key, value in details.items():
            if key.lower() in ['password', 'token', 'secret', 'key']:
                sanitized_details[key] = '***'
            else:
                sanitized_details[key] = str(value)[:100]  # Limit length
        
        event_data.update(sanitized_details)
    
    security_logger.info(f"Security event: {event_data}")
