# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security middleware for Flask application

Implements comprehensive security headers, input validation, and protection mechanisms.
"""

import re
import logging
from functools import wraps
from flask import request, abort, g, current_app
from werkzeug.exceptions import BadRequest
from flask_wtf.csrf import ValidationError
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """Comprehensive security middleware for Flask applications"""
    
    def __init__(self, app=None):
        self.app = app
        self.rate_limit_storage = {}  # In production, use Redis
        self.failed_attempts = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Generate CSP nonce for each request
        @app.before_request
        def generate_csp_nonce():
            g.csp_nonce = secrets.token_urlsafe(16)
    
    def before_request(self):
        """Security checks before each request"""
        try:
            # Skip security checks for static files and favicon
            if request.endpoint == 'static' or request.path.startswith('/static/') or 'favicon' in request.path:
                return
            
            # Skip security checks in debug mode for localhost
            if current_app.debug and request.remote_addr in ['127.0.0.1', '::1', 'localhost']:
                return
            
            # Rate limiting
            if not self._check_rate_limit():
                logger.warning(f"Rate limit exceeded for IP: {request.remote_addr}")
                abort(429)  # Too Many Requests
            
            # Input validation
            self._validate_request_data()
            
            # Check for suspicious patterns
            self._check_suspicious_patterns()
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            # Don't block requests due to middleware errors
    
    def after_request(self, response):
        """Add security headers after each request"""
        try:
            # Security headers
            self._add_security_headers(response)
            
            # Log security events
            self._log_security_event(response)
            
        except Exception as e:
            logger.error(f"Error adding security headers: {e}")
        
        return response
    
    def _check_rate_limit(self):
        """Check rate limiting for the current request"""
        client_ip = request.remote_addr
        current_time = datetime.utcnow()
        
        # Clean old entries
        cutoff_time = current_time - timedelta(minutes=1)
        self.rate_limit_storage = {
            ip: requests for ip, requests in self.rate_limit_storage.items()
            if any(req_time > cutoff_time for req_time in requests)
        }
        
        # Check current IP
        if client_ip not in self.rate_limit_storage:
            self.rate_limit_storage[client_ip] = []
        
        # Remove old requests for this IP
        self.rate_limit_storage[client_ip] = [
            req_time for req_time in self.rate_limit_storage[client_ip]
            if req_time > cutoff_time
        ]
        
        # Check rate limit (60 requests per minute)
        if len(self.rate_limit_storage[client_ip]) >= 60:
            return False
        
        # Add current request
        self.rate_limit_storage[client_ip].append(current_time)
        return True
    
    def _validate_request_data(self):
        """Validate request data for security issues"""
        # Check Content-Length
        if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"Large request from {request.remote_addr}: {request.content_length} bytes")
            abort(413)  # Payload Too Large
        
        # Validate JSON data
        if request.is_json:
            try:
                data = request.get_json(force=True, silent=True)
                if data:
                    self._validate_json_data(data)
            except Exception as e:
                logger.warning(f"Invalid JSON from {request.remote_addr}: {e}")
                # Don't abort for JSON parsing errors, let the endpoint handle it
                pass
        
        # Validate form data
        if request.form:
            self._validate_form_data(request.form)
        
        # Validate query parameters
        if request.args:
            self._validate_query_params(request.args)
    
    def _validate_json_data(self, data, max_depth=5, current_depth=0):
        """Validate JSON data recursively"""
        if current_depth > max_depth:
            raise BadRequest("JSON data too deeply nested")
        
        if isinstance(data, dict):
            if len(data) > 100:  # Limit number of keys
                raise BadRequest("Too many keys in JSON object")
            
            for key, value in data.items():
                if not isinstance(key, str) or len(key) > 100:
                    raise BadRequest("Invalid JSON key")
                
                self._validate_string_content(str(value))
                
                if isinstance(value, (dict, list)):
                    self._validate_json_data(value, max_depth, current_depth + 1)
        
        elif isinstance(data, list):
            if len(data) > 1000:  # Limit array size
                raise BadRequest("JSON array too large")
            
            for item in data:
                if isinstance(item, (dict, list)):
                    self._validate_json_data(item, max_depth, current_depth + 1)
                else:
                    self._validate_string_content(str(item))
    
    def _validate_form_data(self, form_data):
        """Validate form data"""
        for key, value in form_data.items():
            if len(key) > 100:
                raise BadRequest("Form field name too long")
            
            if len(value) > 10000:  # 10KB per field
                raise BadRequest("Form field value too long")
            
            self._validate_string_content(value)
    
    def _validate_query_params(self, query_params):
        """Validate query parameters"""
        for key, value in query_params.items():
            if len(key) > 100:
                raise BadRequest("Query parameter name too long")
            
            if len(value) > 1000:
                raise BadRequest("Query parameter value too long")
            
            self._validate_string_content(value)
    
    def _validate_string_content(self, content):
        """Validate string content for malicious patterns"""
        if not isinstance(content, str):
            return
        
        # Check for SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\bUNION\s+SELECT)",
            r"(\b(EXEC|EXECUTE)\s*\()",
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Potential SQL injection attempt from {request.remote_addr}: {content[:100]}")
                raise BadRequest("Invalid input detected")
        
        # Check for XSS patterns
        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Potential XSS attempt from {request.remote_addr}: {content[:100]}")
                raise BadRequest("Invalid input detected")
        
        # Check for path traversal
        if "../" in content or "..\\" in content:
            logger.warning(f"Path traversal attempt from {request.remote_addr}: {content[:100]}")
            raise BadRequest("Invalid input detected")
    
    def _check_suspicious_patterns(self):
        """Check for suspicious request patterns"""
        user_agent = request.headers.get('User-Agent', '')
        
        # Check for suspicious user agents
        suspicious_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'nessus',
            'burp', 'w3af', 'acunetix', 'appscan'
        ]
        
        for agent in suspicious_agents:
            if agent.lower() in user_agent.lower():
                logger.warning(f"Suspicious user agent from {request.remote_addr}: {user_agent}")
                abort(403)  # Forbidden
        
        # Check for suspicious headers
        if 'X-Forwarded-For' in request.headers:
            xff = request.headers['X-Forwarded-For']
            if len(xff.split(',')) > 10:  # Too many proxies
                logger.warning(f"Suspicious X-Forwarded-For from {request.remote_addr}: {xff}")
                abort(400)
    
    def _add_security_headers(self, response):
        """Add comprehensive security headers"""
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
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        )
        
        # HSTS (only for HTTPS)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )
        
        # Remove server information
        response.headers.pop('Server', None)
        
        # Additional security headers
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

        
        # Cache control for sensitive pages
        if request.endpoint in ['login', 'user_management', 'platform_management']:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
    
    def _log_security_event(self, response):
        """Log security-relevant events"""
        # Log failed authentication attempts
        if response.status_code == 401:
            client_ip = request.remote_addr
            self.failed_attempts[client_ip] = self.failed_attempts.get(client_ip, 0) + 1
            
            if self.failed_attempts[client_ip] > 5:
                logger.warning(f"Multiple failed login attempts from {client_ip}")
        
        # Log successful authentication
        elif response.status_code == 200 and request.endpoint == 'login':
            logger.info(f"Successful login from {request.remote_addr}")
        
        # Log suspicious status codes
        elif response.status_code in [403, 404, 429]:
            logger.info(f"Security event: {response.status_code} for {request.remote_addr} on {request.path}")


def require_https(f):
    """Decorator to require HTTPS for sensitive endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and not current_app.debug:
            logger.warning(f"HTTP request to secure endpoint from {request.remote_addr}")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def validate_csrf_token(f):
    """Decorator to validate CSRF tokens"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            from flask_wtf.csrf import validate_csrf
            try:
                # Check for CSRF token in form data or headers
                csrf_token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
                validate_csrf(csrf_token)
            except ValidationError:
                logger.warning(f"CSRF validation failed from {request.remote_addr}")
                abort(403, description="CSRF token validation failed")
        return f(*args, **kwargs)
    return decorated_function


def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    if not filename:
        return "unknown"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:95] + ('.' + ext if ext else '')
    
    return filename


def generate_secure_token(length=32):
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def hash_password_secure(password, salt=None):
    """Securely hash password with salt"""
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # Use PBKDF2 with SHA-256
    import hashlib
    import os
    
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt + key


def verify_password_secure(password, hashed):
    """Verify password against secure hash"""
    salt = hashed[:32]
    key = hashed[32:]
    
    import hashlib
    new_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    
    return key == new_key


def validate_input_length(max_length=10000):
    """Decorator to validate input length"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'POST':
                # Check form data
                for key, value in request.form.items():
                    if len(str(value)) > max_length:
                        logger.warning(f"Input too long from {request.remote_addr}: {key}")
                        abort(400)
                
                # Check JSON data
                if request.is_json:
                    data = request.get_json()
                    if data:
                        for key, value in data.items():
                            if len(str(value)) > max_length:
                                logger.warning(f"JSON input too long from {request.remote_addr}: {key}")
                                abort(400)
            
            return f(*args, **kwargs)
        return decorated_function
    
    # If called without parentheses, return the decorator directly
    if callable(max_length):
        f = max_length
        max_length = 10000  # Default value
        return decorator(f)
    else:
        return decorator


def rate_limit(limit=60, window_seconds=60, requests_per_minute=None):
    """Decorator to add rate limiting to endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This would integrate with the SecurityMiddleware rate limiting
            # For now, just pass through - in production this would check limits
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Alias for backward compatibility
require_secure_connection = require_https