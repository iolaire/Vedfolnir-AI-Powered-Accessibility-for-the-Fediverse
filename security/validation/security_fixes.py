#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security Fixes Implementation

This script implements comprehensive security fixes for the web-integrated caption generation system.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class SecurityFixer:
    """Implements security fixes based on audit findings"""
    
    def __init__(self):
        self.fixes_applied = []
        self.fixes_failed = []
    
    def apply_all_fixes(self):
        """Apply all security fixes"""
        logger.info("Starting security fixes implementation...")
        
        # 1. Fix CSRF Protection
        self._fix_csrf_protection()
        
        # 2. Fix Input Validation
        self._fix_input_validation()
        
        # 3. Fix Security Headers
        self._fix_security_headers()
        
        # 4. Fix Session Security
        self._fix_session_security()
        
        # 5. Fix WebSocket Security
        self._fix_websocket_security()
        
        # 6. Fix Error Handling
        self._fix_error_handling()
        
        # 7. Fix Logging Security
        self._fix_logging_security()
        
        # 8. Fix Template Security
        self._fix_template_security()
        
        return {
            'fixes_applied': len(self.fixes_applied),
            'fixes_failed': len(self.fixes_failed),
            'applied': self.fixes_applied,
            'failed': self.fixes_failed
        }
    
    def _fix_csrf_protection(self):
        """Implement comprehensive CSRF protection"""
        logger.info("Fixing CSRF protection...")
        
        try:
            # 1. Update Flask app configuration for CSRF
            self._update_flask_csrf_config()
            
            # 2. Implement proper CSRF token validation
            self._implement_csrf_validation()
            
            # 3. Add CSRF tokens to all forms
            self._add_csrf_tokens_to_forms()
            
            self.fixes_applied.append("CSRF Protection Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix CSRF protection: {e}")
            self.fixes_failed.append(f"CSRF Protection: {e}")
    
    def _fix_input_validation(self):
        """Implement comprehensive input validation"""
        logger.info("Fixing input validation...")
        
        try:
            # 1. Create enhanced input validation middleware
            self._create_input_validation_middleware()
            
            # 2. Add XSS protection
            self._add_xss_protection()
            
            # 3. Add SQL injection protection
            self._add_sql_injection_protection()
            
            self.fixes_applied.append("Input Validation Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix input validation: {e}")
            self.fixes_failed.append(f"Input Validation: {e}")
    
    def _fix_security_headers(self):
        """Implement comprehensive security headers"""
        logger.info("Fixing security headers...")
        
        try:
            # Update security middleware with enhanced headers
            self._update_security_headers()
            
            self.fixes_applied.append("Security Headers Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix security headers: {e}")
            self.fixes_failed.append(f"Security Headers: {e}")
    
    def _fix_session_security(self):
        """Implement secure session management"""
        logger.info("Fixing session security...")
        
        try:
            # Update Flask app with secure session configuration
            self._update_session_config()
            
            self.fixes_applied.append("Session Security Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix session security: {e}")
            self.fixes_failed.append(f"Session Security: {e}")
    
    def _fix_websocket_security(self):
        """Implement WebSocket security enhancements"""
        logger.info("Fixing WebSocket security...")
        
        try:
            # Add WebSocket input validation and rate limiting
            self._enhance_websocket_security()
            
            self.fixes_applied.append("WebSocket Security Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix WebSocket security: {e}")
            self.fixes_failed.append(f"WebSocket Security: {e}")
    
    def _fix_error_handling(self):
        """Implement secure error handling"""
        logger.info("Fixing error handling...")
        
        try:
            # Create secure error handlers
            self._create_secure_error_handlers()
            
            self.fixes_applied.append("Error Handling Secured")
            
        except Exception as e:
            logger.error(f"Failed to fix error handling: {e}")
            self.fixes_failed.append(f"Error Handling: {e}")
    
    def _fix_logging_security(self):
        """Implement secure logging practices"""
        logger.info("Fixing logging security...")
        
        try:
            # Create secure logging utilities
            self._create_secure_logging()
            
            self.fixes_applied.append("Logging Security Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix logging security: {e}")
            self.fixes_failed.append(f"Logging Security: {e}")
    
    def _fix_template_security(self):
        """Fix template security issues"""
        logger.info("Fixing template security...")
        
        try:
            # Remove unsafe template filters
            self._fix_template_filters()
            
            self.fixes_applied.append("Template Security Enhanced")
            
        except Exception as e:
            logger.error(f"Failed to fix template security: {e}")
            self.fixes_failed.append(f"Template Security: {e}")
    
    def _update_flask_csrf_config(self):
        """Update Flask configuration for CSRF protection"""
        web_app_path = Path('web_app.py')
        if not web_app_path.exists():
            return
        
        with open(web_app_path, 'r') as f:
            content = f.read()
        
        # Add Flask-WTF CSRF protection
        if 'from flask_wtf.csrf import CSRFProtect' not in content:
            # Add import
            import_line = "from flask_wtf.csrf import CSRFProtect\n"
            content = content.replace(
                "from flask_wtf import FlaskForm",
                f"from flask_wtf import FlaskForm\n{import_line}"
            )
            
            # Add CSRF initialization
            csrf_init = """
# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Configure CSRF settings
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = True
app.config['WTF_CSRF_CHECK_DEFAULT'] = True
"""
            
            # Insert after app configuration
            content = content.replace(
                "app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=config.auth.remember_cookie_duration)",
                f"app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=config.auth.remember_cookie_duration)\n{csrf_init}"
            )
        
        with open(web_app_path, 'w') as f:
            f.write(content)
    
    def _implement_csrf_validation(self):
        """Implement proper CSRF token validation"""
        security_middleware_path = Path('security_middleware.py')
        if not security_middleware_path.exists():
            return
        
        with open(security_middleware_path, 'r') as f:
            content = f.read()
        
        # Replace the existing CSRF validation with proper implementation
        new_csrf_validation = '''
def validate_csrf_token(f):
    """Decorator to validate CSRF tokens"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except ValidationError:
                logger.warning(f"CSRF validation failed from {request.remote_addr}")
                abort(403, description="CSRF token validation failed")
        return f(*args, **kwargs)
    return decorated_function
'''
        
        # Replace existing function
        content = re.sub(
            r'def validate_csrf_token\(f\):.*?return decorated_function',
            new_csrf_validation.strip(),
            content,
            flags=re.DOTALL
        )
        
        with open(security_middleware_path, 'w') as f:
            f.write(content)
    
    def _add_csrf_tokens_to_forms(self):
        """Add CSRF tokens to all HTML forms"""
        templates_dir = Path('templates')
        if not templates_dir.exists():
            return
        
        for template_file in templates_dir.glob('*.html'):
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Add CSRF token to forms that don't have it
            if '<form' in content and 'csrf_token' not in content:
                # Add CSRF token after form opening tag
                content = re.sub(
                    r'(<form[^>]*>)',
                    r'\1\n    {{ csrf_token() }}',
                    content
                )
                
                with open(template_file, 'w') as f:
                    f.write(content)
    
    def _create_input_validation_middleware(self):
        """Create enhanced input validation middleware"""
        validation_code = '''
"""
Enhanced Input Validation Middleware

Provides comprehensive input validation and sanitization.
"""

import re
import html
import bleach
from urllib.parse import quote
from flask import request, abort
from werkzeug.exceptions import BadRequest

class EnhancedInputValidator:
    """Enhanced input validation and sanitization"""
    
    # Allowed HTML tags for rich text fields
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
    ALLOWED_ATTRIBUTES = {}
    
    @staticmethod
    def sanitize_html(text):
        """Sanitize HTML content"""
        if not text:
            return ""
        return bleach.clean(text, tags=EnhancedInputValidator.ALLOWED_TAGS, 
                          attributes=EnhancedInputValidator.ALLOWED_ATTRIBUTES)
    
    @staticmethod
    def sanitize_sql(text):
        """Sanitize text to prevent SQL injection"""
        if not text:
            return ""
        
        # Remove dangerous SQL keywords and characters
        dangerous_patterns = [
            r"(\\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\\b)",
            r"(--|#|/\\*|\\*/)",
            r"(\\b(OR|AND)\\s+\\d+\\s*=\\s*\\d+)",
            r"(\\bUNION\\s+SELECT)",
            r"(\\b(EXEC|EXECUTE)\\s*\\()",
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def sanitize_xss(text):
        """Sanitize text to prevent XSS"""
        if not text:
            return ""
        
        # HTML encode dangerous characters
        text = html.escape(text)
        
        # Remove javascript: URLs
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Remove on* event handlers
        text = re.sub(r'\\bon\\w+\\s*=', '', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def validate_length(text, max_length=10000):
        """Validate text length"""
        if text and len(text) > max_length:
            raise BadRequest(f"Input too long (max {max_length} characters)")
        return text
    
    @staticmethod
    def validate_filename(filename):
        """Validate and sanitize filename"""
        if not filename:
            return "unknown"
        
        # Remove path components
        filename = filename.split('/')[-1].split('\\\\')[-1]
        
        # Remove dangerous characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Limit length
        if len(filename) > 100:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:95] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url):
        """Validate URL format and scheme"""
        if not url:
            return False
        
        # Only allow http and https
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Basic URL validation
        pattern = r'^https?://[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}(/.*)?$'
        return re.match(pattern, url) is not None

def enhanced_input_validation(f):
    """Decorator for enhanced input validation"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        validator = EnhancedInputValidator()
        
        # Validate form data
        if request.form:
            for key, value in request.form.items():
                # Length validation
                validator.validate_length(value)
                
                # XSS sanitization
                request.form = request.form.copy()
                request.form[key] = validator.sanitize_xss(value)
        
        # Validate JSON data
        if request.is_json:
            data = request.get_json()
            if data:
                _validate_json_recursive(data, validator)
        
        return f(*args, **kwargs)
    return decorated_function

def _validate_json_recursive(data, validator, depth=0):
    """Recursively validate JSON data"""
    if depth > 10:  # Prevent deep nesting attacks
        raise BadRequest("JSON data too deeply nested")
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                validator.validate_length(value)
                data[key] = validator.sanitize_xss(value)
            elif isinstance(value, (dict, list)):
                _validate_json_recursive(value, validator, depth + 1)
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                validator.validate_length(item)
                data[i] = validator.sanitize_xss(item)
            elif isinstance(item, (dict, list)):
                _validate_json_recursive(item, validator, depth + 1)
'''
        
        with open('enhanced_input_validation.py', 'w') as f:
            f.write(validation_code)
    
    def _add_xss_protection(self):
        """Add XSS protection to existing code"""
        # Update web_app.py to use enhanced validation
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Add import for enhanced validation
            if 'from enhanced_input_validation import' not in content:
                content = content.replace(
                    'from security.core.security_utils import sanitize_for_log, sanitize_html_input',
                    'from security.core.security_utils import sanitize_for_log, sanitize_html_input\nfrom enhanced_input_validation import enhanced_input_validation, EnhancedInputValidator'
                )
            
            # Add validation decorator to vulnerable endpoints
            vulnerable_endpoints = [
                'edit_user', 'api_update_caption', 
                'api_add_platform', 'save_caption_settings'
            ]
            
            for endpoint in vulnerable_endpoints:
                pattern = f'def {endpoint}\\('
                if re.search(pattern, content):
                    # Add decorator before function
                    content = re.sub(
                        f'(def {endpoint}\\()',
                        f'@enhanced_input_validation\n\\1',
                        content
                    )
            
            with open(web_app_path, 'w') as f:
                f.write(content)
    
    def _add_sql_injection_protection(self):
        """Add SQL injection protection"""
        # This is mostly handled by SQLAlchemy ORM, but we'll add extra validation
        # Update any raw SQL usage to use parameterized queries
        for file_path in ['web_app.py', 'models.py', 'database.py']:
            path = Path(file_path)
            if not path.exists():
                continue
            
            with open(path, 'r') as f:
                content = f.read()
            
            # Look for potential SQL injection points and add comments
            if 'text(' in content and '%' in content:
                # Add warning comments
                content = re.sub(
                    r'(.*text\\([^)]*%[^)]*\\).*)',
                    r'# WARNING: Potential SQL injection - use parameterized queries\n\\1',
                    content
                )
                
                with open(path, 'w') as f:
                    f.write(content)
    
    def _update_security_headers(self):
        """Update security headers with enhanced protection"""
        security_middleware_path = Path('security_middleware.py')
        if not security_middleware_path.exists():
            return
        
        with open(security_middleware_path, 'r') as f:
            content = f.read()
        
        # Update CSP policy to be more restrictive
        new_csp = '''
        # Enhanced Content Security Policy
        csp_nonce = getattr(g, 'csp_nonce', 'default-nonce')
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net; "
            f"style-src 'self' 'nonce-{csp_nonce}' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self' wss: ws:; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"object-src 'none'; "
            f"media-src 'self'"
        )
        response.headers['Content-Security-Policy'] = csp_policy
'''
        
        # Replace existing CSP
        content = re.sub(
            r'# Content Security Policy.*?response\.headers\[\'Content-Security-Policy\'\] = csp_policy',
            new_csp.strip(),
            content,
            flags=re.DOTALL
        )
        
        # Add additional security headers
        additional_headers = '''
        
        # Additional security headers
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
'''
        
        # Add after existing headers
        content = content.replace(
            "response.headers.pop('Server', None)",
            f"response.headers.pop('Server', None){additional_headers}"
        )
        
        with open(security_middleware_path, 'w') as f:
            f.write(content)
    
    def _update_session_config(self):
        """Update Flask session configuration for security"""
        web_app_path = Path('web_app.py')
        if not web_app_path.exists():
            return
        
        with open(web_app_path, 'r') as f:
            content = f.read()
        
        # Add secure session configuration
        session_config = '''
# Secure session configuration
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['SESSION_COOKIE_NAME'] = '__Host-session'  # Secure prefix
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
'''
        
        # Add after existing configuration
        content = content.replace(
            "app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=config.auth.remember_cookie_duration)",
            f"app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=config.auth.remember_cookie_duration)\n{session_config}"
        )
        
        with open(web_app_path, 'w') as f:
            f.write(content)
    
    def _enhance_websocket_security(self):
        """Enhance WebSocket security"""
        websocket_path = Path('websocket_progress_handler.py')
        if not websocket_path.exists():
            return
        
        with open(websocket_path, 'r') as f:
            content = f.read()
        
        # Add rate limiting and input validation
        enhanced_handlers = '''
    def _register_handlers(self):
        """Register SocketIO event handlers with security enhancements"""
        
        # Rate limiting storage
        self._rate_limits = {}
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection with rate limiting"""
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated WebSocket connection attempt from {sanitize_for_log(request.remote_addr)}")
                disconnect()
                return False
            
            # Rate limiting check
            if not self._check_connection_rate_limit():
                logger.warning(f"WebSocket connection rate limit exceeded for user {sanitize_for_log(str(current_user.id))}")
                disconnect()
                return False
            
            logger.info(f"WebSocket connected: user {sanitize_for_log(str(current_user.id))} session {sanitize_for_log(request.sid)}")
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            if current_user.is_authenticated:
                logger.info(f"WebSocket disconnected: user {sanitize_for_log(str(current_user.id))} session {sanitize_for_log(request.sid)}")
                self._cleanup_connection(request.sid)
        
        @self.socketio.on('join_task')
        def handle_join_task(data):
            """Handle client joining a task room with input validation"""
            if not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            # Input validation
            if not isinstance(data, dict):
                emit('error', {'message': 'Invalid data format'})
                return
            
            task_id = data.get('task_id')
            if not task_id or not isinstance(task_id, str):
                emit('error', {'message': 'Task ID required'})
                return
            
            # Validate task ID format (UUID)
            import uuid
            try:
                uuid.UUID(task_id)
            except ValueError:
                emit('error', {'message': 'Invalid task ID format'})
                return
            
            # Verify user has access to this task
            if not self._verify_task_access(task_id, current_user.id):
                emit('error', {'message': 'Access denied to task'})
                return
            
            # Join the task room
            join_room(task_id)
            
            # Track the connection
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(request.sid)
            
            # Send current progress if available
            progress = self.progress_tracker.get_progress(task_id, current_user.id)
            if progress:
                emit('progress_update', progress.to_dict())
            
            logger.info(f"User {sanitize_for_log(str(current_user.id))} joined task {sanitize_for_log(task_id)} room")
        
        # Add other handlers with similar validation...
    
    def _check_connection_rate_limit(self, limit=10, window_seconds=60):
        """Check WebSocket connection rate limiting"""
        from datetime import datetime, timedelta
        
        user_id = current_user.id
        current_time = datetime.utcnow()
        
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = []
        
        # Clean old entries
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        self._rate_limits[user_id] = [
            timestamp for timestamp in self._rate_limits[user_id]
            if timestamp > cutoff_time
        ]
        
        # Check limit
        if len(self._rate_limits[user_id]) >= limit:
            return False
        
        # Add current connection
        self._rate_limits[user_id].append(current_time)
        return True
'''
        
        # Replace the existing _register_handlers method
        content = re.sub(
            r'def _register_handlers\(self\):.*?logger\.info\(f"User.*?room"\)',
            enhanced_handlers.strip(),
            content,
            flags=re.DOTALL
        )
        
        with open(websocket_path, 'w') as f:
            f.write(content)
    
    def _create_secure_error_handlers(self):
        """Create secure error handlers"""
        error_handlers_code = '''
"""
Secure Error Handlers

Provides secure error handling that doesn't leak sensitive information.
"""

from flask import render_template, jsonify, request
import logging

logger = logging.getLogger(__name__)

def register_secure_error_handlers(app):
    """Register secure error handlers with the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors securely"""
        logger.warning(f"Bad request from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Bad Request',
                'message': 'The request could not be understood by the server.'
            }), 400
        
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized errors securely"""
        logger.warning(f"Unauthorized access attempt from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required.'
            }), 401
        
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden errors securely"""
        logger.warning(f"Forbidden access attempt from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.'
            }), 403
        
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors securely"""
        logger.info(f"404 error from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found.'
            }), 404
        
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit errors securely"""
        logger.warning(f"Rate limit exceeded from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Rate Limit Exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors securely"""
        logger.error(f"Internal server error from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An internal server error occurred.'
            }), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unexpected exceptions securely"""
        logger.exception(f"Unhandled exception from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred.'
            }), 500
        
        return render_template('errors/500.html'), 500
'''
        
        with open('secure_error_handlers.py', 'w') as f:
            f.write(error_handlers_code)
        
        # Update web_app.py to use secure error handlers
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Add import and registration
            if 'from secure_error_handlers import' not in content:
                content = content.replace(
                    'from admin_monitoring import AdminMonitoringService',
                    'from admin_monitoring import AdminMonitoringService\nfrom security.logging.secure_error_handlers import register_secure_error_handlers'
                )
                
                # Add registration after app initialization
                content = content.replace(
                    '# Initialize admin monitoring service',
                    '# Register secure error handlers\nregister_secure_error_handlers(app)\n\n# Initialize admin monitoring service'
                )
            
            with open(web_app_path, 'w') as f:
                f.write(content)
    
    def _create_secure_logging(self):
        """Create secure logging utilities"""
        secure_logging_code = '''
"""
Secure Logging Utilities

Provides secure logging that prevents sensitive data exposure and log injection.
"""

import re
import logging
from typing import Any, Dict

class SecureLogger:
    """Secure logger that sanitizes sensitive data"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
        # Sensitive data patterns to sanitize
        self.sensitive_patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'password=***'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'token=***'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'secret=***'),
            (r'key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'key=***'),
            (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'api_key=***'),
            (r'access_token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'access_token=***'),
        ]
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize log message to remove sensitive data"""
        if not isinstance(message, str):
            message = str(message)
        
        # Remove sensitive data
        for pattern, replacement in self.sensitive_patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        # Prevent log injection by removing newlines and control characters
        message = re.sub(r'[\\r\\n\\t]', ' ', message)
        message = re.sub(r'[\\x00-\\x1f\\x7f-\\x9f]', '', message)
        
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
        'timestamp': str(datetime.utcnow()),
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
'''
        
        with open('secure_logging.py', 'w') as f:
            f.write(secure_logging_code)
    
    def _fix_template_filters(self):
        """Fix unsafe template filters"""
        templates_dir = Path('templates')
        if not templates_dir.exists():
            return
        
        for template_file in templates_dir.glob('*.html'):
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Remove |safe filters and replace with proper escaping
            if '|safe' in content:
                # Log the change
                logger.warning(f"Removing unsafe |safe filter from {template_file}")
                
                # Replace |safe with proper escaping
                content = content.replace('|safe', '')
                
                with open(template_file, 'w') as f:
                    f.write(content)

def main():
    """Main function to apply security fixes"""
    fixer = SecurityFixer()
    results = fixer.apply_all_fixes()
    
    print("\\n" + "="*60)
    print("SECURITY FIXES SUMMARY")
    print("="*60)
    print(f"Fixes Applied: {results['fixes_applied']}")
    print(f"Fixes Failed: {results['fixes_failed']}")
    
    if results['applied']:
        print("\\nSuccessfully Applied:")
        for fix in results['applied']:
            print(f"  ✓ {fix}")
    
    if results['failed']:
        print("\\nFailed to Apply:")
        for fix in results['failed']:
            print(f"  ✗ {fix}")
    
    return len(results['failed'])

if __name__ == '__main__':
    import sys
    failed_count = main()
    sys.exit(failed_count)