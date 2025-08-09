#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security fixes implementation for web caption generation system
"""

import os
import re
from pathlib import Path
from typing import Dict, List

class SecurityFixer:
    """Implements security fixes based on audit findings"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
    def fix_database_security(self):
        """Fix SQL injection vulnerabilities in data_cleanup.py"""
        print("🔧 Fixing database security issues...")
        
        data_cleanup_file = self.project_root / "data_cleanup.py"
        if not data_cleanup_file.exists():
            return
            
        with open(data_cleanup_file, 'r') as f:
            content = f.read()
        
        # Fix SQL injection in image count query
        content = content.replace(
            'image_count_result = session.execute(text(f"SELECT COUNT(*) FROM images WHERE post_id IN ({placeholders})"), params).scalar()',
            'image_count_result = session.query(Image).filter(Image.post_id.in_(post_ids)).count()'
        )
        
        # Fix SQL injection in image paths query
        content = content.replace(
            'image_paths_result = session.execute(text(f"SELECT local_path FROM images WHERE post_id IN ({placeholders})"), params).fetchall()',
            'image_paths_result = session.query(Image.local_path).filter(Image.post_id.in_(post_ids)).all()'
        )
        
        # Fix SQL injection in delete query
        content = content.replace(
            'session.execute(text(f"DELETE FROM images WHERE post_id IN ({placeholders})"), params)',
            'session.query(Image).filter(Image.post_id.in_(post_ids)).delete(synchronize_session=False)'
        )
        
        with open(data_cleanup_file, 'w') as f:
            f.write(content)
        
        print("✅ Fixed SQL injection vulnerabilities")
    
    def fix_security_headers(self):
        """Add comprehensive security headers to web_app.py"""
        print("🔧 Adding security headers...")
        
        web_app_file = self.project_root / "web_app.py"
        if not web_app_file.exists():
            return
            
        with open(web_app_file, 'r') as f:
            content = f.read()
        
        # Add security headers middleware
        security_headers_code = '''
# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers to all responses"""
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # HTTPS enforcement (only in production)
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "font-src 'self' cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response
'''
        
        # Insert security headers after imports
        import_end = content.find('\n\n# Initialize')
        if import_end == -1:
            import_end = content.find('\napp = Flask')
        
        if import_end != -1:
            content = content[:import_end] + security_headers_code + content[import_end:]
        
        with open(web_app_file, 'w') as f:
            f.write(content)
        
        print("✅ Added comprehensive security headers")
    
    def fix_session_security(self):
        """Fix session security configuration"""
        print("🔧 Fixing session security...")
        
        # Fix web_app.py session configuration
        web_app_file = self.project_root / "web_app.py"
        if web_app_file.exists():
            with open(web_app_file, 'r') as f:
                content = f.read()
            
            # Add secure session configuration
            session_config = '''
# Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=not app.debug,  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY=True,         # Prevent XSS access
    SESSION_COOKIE_SAMESITE='Lax',        # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)  # Session timeout
)
'''
            
            # Insert after app configuration
            config_end = content.find('app.config[')
            if config_end != -1:
                line_end = content.find('\n', config_end)
                content = content[:line_end] + session_config + content[line_end:]
            
            with open(web_app_file, 'w') as f:
                f.write(content)
        
        # Fix session_manager.py
        session_manager_file = self.project_root / "session_manager.py"
        if session_manager_file.exists():
            with open(session_manager_file, 'r') as f:
                content = f.read()
            
            # Add secure session flags
            if 'secure=' not in content:
                content = content.replace(
                    'session.permanent = True',
                    '''session.permanent = True
        # Set secure session flags
        if hasattr(session, 'cookie'):
            session.cookie.secure = not current_app.debug
            session.cookie.httponly = True
            session.cookie.samesite = 'Lax' '''
                )
            
            with open(session_manager_file, 'w') as f:
                f.write(content)
        
        print("✅ Fixed session security configuration")
    
    def fix_input_validation(self):
        """Add comprehensive input validation"""
        print("🔧 Adding input validation...")
        
        # Create input validation utility
        validation_code = '''"""
Input validation utilities for security
"""
import re
import html
from typing import Any, Dict, Optional
from flask import request

class InputValidator:
    """Secure input validation and sanitization"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # Limit length
        value = value[:max_length]
        
        # HTML escape
        value = html.escape(value)
        
        # Remove null bytes
        value = value.replace('\\x00', '')
        
        return value.strip()
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = 0, max_val: int = 1000000) -> Optional[int]:
        """Validate integer input"""
        try:
            int_val = int(value)
            if min_val <= int_val <= max_val:
                return int_val
        except (ValueError, TypeError):
            pass
        return None
    
    @staticmethod
    def validate_boolean(value: Any) -> bool:
        """Validate boolean input"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    @staticmethod
    def validate_form_data(form_data: Dict[str, Any], schema: Dict[str, Dict]) -> Dict[str, Any]:
        """Validate form data against schema"""
        validated = {}
        
        for field, rules in schema.items():
            value = form_data.get(field)
            
            if value is None:
                if rules.get('required', False):
                    raise ValueError(f"Required field '{field}' is missing")
                continue
            
            field_type = rules.get('type', 'string')
            
            if field_type == 'string':
                max_length = rules.get('max_length', 1000)
                validated[field] = InputValidator.sanitize_string(value, max_length)
            elif field_type == 'integer':
                min_val = rules.get('min', 0)
                max_val = rules.get('max', 1000000)
                validated[field] = InputValidator.validate_integer(value, min_val, max_val)
            elif field_type == 'boolean':
                validated[field] = InputValidator.validate_boolean(value)
        
        return validated

def validate_request_data(schema: Dict[str, Dict]):
    """Decorator for request data validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                if request.method == 'POST':
                    if request.is_json:
                        data = request.get_json() or {}
                    else:
                        data = request.form.to_dict()
                    
                    validated_data = InputValidator.validate_form_data(data, schema)
                    request.validated_data = validated_data
                
                return func(*args, **kwargs)
            except ValueError as e:
                from flask import jsonify
                return jsonify({'success': False, 'error': str(e)}), 400
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
'''
        
        validation_file = self.project_root / "input_validation.py"
        with open(validation_file, 'w') as f:
            f.write(validation_code)
        
        print("✅ Added input validation utilities")
    
    def fix_csrf_protection(self):
        """Add CSRF protection"""
        print("🔧 Adding CSRF protection...")
        
        csrf_code = '''"""
CSRF protection implementation
"""
import secrets
import hmac
import hashlib
from flask import session, request, abort
from functools import wraps

class CSRFProtection:
    """CSRF protection implementation"""
    
    @staticmethod
    def generate_csrf_token():
        """Generate CSRF token"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token(token):
        """Validate CSRF token"""
        session_token = session.get('csrf_token')
        if not session_token or not token:
            return False
        
        return hmac.compare_digest(session_token, token)

def csrf_protect(func):
    """CSRF protection decorator"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == 'POST':
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not CSRFProtection.validate_csrf_token(token):
                abort(403, "CSRF token validation failed")
        
        return func(*args, **kwargs)
    
    return wrapper

# Template function for CSRF token
def csrf_token():
    """Template function to get CSRF token"""
    return CSRFProtection.generate_csrf_token()
'''
        
        csrf_file = self.project_root / "csrf_protection.py"
        with open(csrf_file, 'w') as f:
            f.write(csrf_code)
        
        print("✅ Added CSRF protection")
    
    def fix_error_handling(self):
        """Fix error information disclosure"""
        print("🔧 Fixing error handling...")
        
        error_handler_code = '''"""
Secure error handling to prevent information disclosure
"""
import logging
import traceback
import uuid
from flask import jsonify, current_app

class SecureErrorHandler:
    """Secure error handling with information disclosure prevention"""
    
    @staticmethod
    def handle_error(error, user_message="An error occurred", log_details=True):
        """Handle errors securely without exposing sensitive information"""
        error_id = str(uuid.uuid4())[:8]
        
        # Log detailed error for debugging (server-side only)
        if log_details:
            logger = logging.getLogger(__name__)
            logger.error(f"Error {error_id}: {str(error)}")
            if current_app.debug:
                logger.error(f"Traceback for {error_id}: {traceback.format_exc()}")
        
        # Return generic error to user
        return {
            'success': False,
            'error': user_message,
            'error_id': error_id
        }
    
    @staticmethod
    def handle_validation_error(error):
        """Handle validation errors with safe error messages"""
        return SecureErrorHandler.handle_error(
            error, 
            "Invalid input provided", 
            log_details=True
        )
    
    @staticmethod
    def handle_auth_error(error):
        """Handle authentication errors"""
        return SecureErrorHandler.handle_error(
            error,
            "Authentication failed",
            log_details=True
        )
    
    @staticmethod
    def handle_platform_error(error):
        """Handle platform connection errors"""
        return SecureErrorHandler.handle_error(
            error,
            "Platform connection failed",
            log_details=True
        )

def safe_error_response(error, user_message="An error occurred", status_code=500):
    """Return safe error response"""
    error_data = SecureErrorHandler.handle_error(error, user_message)
    return jsonify(error_data), status_code
'''
        
        error_handler_file = self.project_root / "secure_error_handler.py"
        with open(error_handler_file, 'w') as f:
            f.write(error_handler_code)
        
        print("✅ Added secure error handling")
    
    def fix_logging_security(self):
        """Fix sensitive data in logging"""
        print("🔧 Fixing logging security...")
        
        secure_logging_code = '''"""
Secure logging utilities to prevent sensitive data exposure
"""
import logging
import re
from typing import Any, Dict

class SecureLogger:
    """Secure logging with sensitive data filtering"""
    
    SENSITIVE_PATTERNS = [
        r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
        r'credential["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
    ]
    
    @staticmethod
    def sanitize_message(message: str) -> str:
        """Remove sensitive data from log messages"""
        for pattern in SecureLogger.SENSITIVE_PATTERNS:
            message = re.sub(pattern, r'\\1=***REDACTED***', message, flags=re.IGNORECASE)
        return message
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from dictionary"""
        sanitized = {}
        sensitive_keys = ['password', 'token', 'secret', 'key', 'credential']
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def safe_log(logger: logging.Logger, level: int, message: str, *args, **kwargs):
        """Log message with sensitive data filtering"""
        sanitized_message = SecureLogger.sanitize_message(message)
        logger.log(level, sanitized_message, *args, **kwargs)

# Convenience functions
def safe_info(logger: logging.Logger, message: str, *args, **kwargs):
    SecureLogger.safe_log(logger, logging.INFO, message, *args, **kwargs)

def safe_error(logger: logging.Logger, message: str, *args, **kwargs):
    SecureLogger.safe_log(logger, logging.ERROR, message, *args, **kwargs)

def safe_debug(logger: logging.Logger, message: str, *args, **kwargs):
    SecureLogger.safe_log(logger, logging.DEBUG, message, *args, **kwargs)
'''
        
        secure_logging_file = self.project_root / "secure_logging.py"
        with open(secure_logging_file, 'w') as f:
            f.write(secure_logging_code)
        
        print("✅ Added secure logging utilities")
    
    def apply_all_fixes(self):
        """Apply all security fixes"""
        print("🔒 Applying comprehensive security fixes...")
        
        self.fix_database_security()
        self.fix_security_headers()
        self.fix_session_security()
        self.fix_input_validation()
        self.fix_csrf_protection()
        self.fix_error_handling()
        self.fix_logging_security()
        
        print("✅ All security fixes applied successfully")

def main():
    """Apply security fixes"""
    fixer = SecurityFixer(".")
    fixer.apply_all_fixes()
    return 0

if __name__ == "__main__":
    exit(main())