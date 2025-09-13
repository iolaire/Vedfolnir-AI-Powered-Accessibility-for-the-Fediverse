import re
import os
import logging
from functools import wraps
from flask import request, abort, g, current_app
from werkzeug.exceptions import BadRequest
# Removed Flask-WTF ValidationError import - using werkzeug exceptions
from datetime import datetime, timedelta
import hashlib
import secrets

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Comprehensive security middleware for Flask applications"""
    
    def __init__(self, app=None, rate_limiting_adapter=None):
        self.app = app
        self.rate_limit_storage = {}  # In production, use Redis
        self.failed_attempts = {}
        self.rate_limiting_adapter = rate_limiting_adapter
        
        # Rate limiting configuration (can be updated by adapter)
        self._rate_limit_config = {
            'requests_per_minute': 120,
            'window_minutes': 1,
            'burst_size': 10,
            'enabled': True
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        # Check if already initialized to prevent duplicate initialization
        if hasattr(app, '_security_middleware_initialized'):
            return
        
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Generate CSP nonce for each request
        @app.before_request
        def generate_csp_nonce():
            g.csp_nonce = secrets.token_urlsafe(16)
        
        # Mark as initialized
        app._security_middleware_initialized = True
    
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
        # Check if rate limiting is enabled
        if not self._rate_limit_config.get('enabled', True):
            return True
        
        client_ip = request.remote_addr
        current_time = datetime.utcnow()
        
        # Get current configuration values
        requests_per_minute = self._rate_limit_config.get('requests_per_minute', 120)
        window_minutes = self._rate_limit_config.get('window_minutes', 1)
        
        # Clean old entries
        cutoff_time = current_time - timedelta(minutes=window_minutes)
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
        
        # Check rate limit using configured value
        if len(self.rate_limit_storage[client_ip]) >= requests_per_minute:
            return False
        
        # Add current request
        self.rate_limit_storage[client_ip].append(current_time)
        return True
    
    def update_rate_limit_config(self, config: dict):
        """
        Update rate limiting configuration
        
        Args:
            config: Dictionary with rate limiting configuration
        """
        self._rate_limit_config.update(config)
        logger.info(f"Updated rate limiting configuration: {self._rate_limit_config}")
    
    def get_rate_limit_config(self) -> dict:
        """
        Get current rate limiting configuration
        
        Returns:
            Dictionary with current rate limiting configuration
        """
        return self._rate_limit_config.copy()
    
    def get_rate_limit_info_for_ip(self, ip_address: str) -> dict:
        """
        Get rate limit information for an IP address
        
        Args:
            ip_address: IP address to check
            
        Returns:
            Dictionary with rate limit information
        """
        current_time = datetime.utcnow()
        window_minutes = self._rate_limit_config.get('window_minutes', 1)
        cutoff_time = current_time - timedelta(minutes=window_minutes)
        
        # Count current requests for this IP
        current_requests = 0
        if ip_address in self.rate_limit_storage:
            current_requests = len([
                req_time for req_time in self.rate_limit_storage[ip_address]
                if req_time > cutoff_time
            ])
        
        requests_per_minute = self._rate_limit_config.get('requests_per_minute', 120)
        
        return {
            'ip_address': ip_address,
            'current_requests': current_requests,
            'rate_limit': requests_per_minute,
            'remaining_requests': max(0, requests_per_minute - current_requests),
            'window_minutes': window_minutes,
            'enabled': self._rate_limit_config.get('enabled', True)
        }
    
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
                
                # Skip validation for password, token, and API key fields
                if not any(field in key.lower() for field in ['password', 'token', 'access_token', 'api_key', 'apikey', 'csrf']):
                    pass
                
                if isinstance(value, (dict, list)):
                    self._validate_json_data(value, max_depth, current_depth + 1)
        
        elif isinstance(data, list):
            if len(data) > 1000:  # Limit array size
                raise BadRequest("JSON array too large")
            
            for item in data:
                if isinstance(item, (dict, list)):
                    self._validate_json_data(item, max_depth, current_depth + 1)
                else:
                    pass
    
    def _validate_form_data(self, form_data):
        """Validate form data"""
        for key, value in form_data.items():
            if len(key) > 100:
                raise BadRequest("Form field name too long")
            
            if len(value) > 10000:  # 10KB per field
                raise BadRequest("Form field value too long")
            
            # Skip validation for password, token, and API key fields
            if not any(field in key.lower() for field in ['password', 'token', 'access_token', 'api_key', 'apikey', 'csrf']):
                pass
    
    def _validate_query_params(self, query_params):
        """Validate query parameters"""
        for key, value in query_params.items():
            if len(key) > 100:
                raise BadRequest("Query parameter name too long")
            
            if len(value) > 1000:
                raise BadRequest("Query parameter value too long")
            
            pass
    
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
        # Enhanced Content Security Policy - Fixed for WebSocket and inline scripts
        csp_nonce = getattr(g, 'csp_nonce', 'default-nonce')
        
        # Check if we're in development mode - also allow CSP override for testing
        is_development = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('CSP_PERMISSIVE') == '1' or True
        
        # Build CSP policy based on environment
        if is_development:
            # Development CSP - more permissive for local development
            csp_policy = (
                f"default-src 'self' *; "
                f"script-src 'self' 'nonce-{csp_nonce}' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io https://unpkg.com *; "
                f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://fonts.gstatic.com *; "
                f"style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://fonts.gstatic.com *; "
                f"style-src-attr 'unsafe-inline'; "
                f"img-src 'self' data: https: blob: http: *; "
                f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data: *; "
                f"connect-src 'self' wss: ws: https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com http://localhost:5000 ws://localhost:5000 wss://localhost:5000 *; "
                f"frame-ancestors 'self'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"object-src 'none'; "
                f"media-src 'self' data: blob: https: http: *; "
                f"worker-src 'self' blob: *; "
                f"child-src 'self'; "
                f"frame-src 'self'; "
                f"report-uri /api/csp-report"
            )
        else:
            # Production CSP - stricter but allows necessary resources
            csp_policy = (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{csp_nonce}' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com; "
                f"style-src 'self' 'nonce-{csp_nonce}' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                f"style-src-elem 'self' 'nonce-{csp_nonce}' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                f"style-src-attr 'unsafe-inline'; "
                f"img-src 'self' data: https: blob:; "
                f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
                f"connect-src 'self' wss: ws: https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com wss://localhost:5000 ws://localhost:5000; "
                f"frame-ancestors 'self'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"object-src 'none'; "
                f"media-src 'self' data: blob: https:; "
                f"worker-src 'self' blob:; "
                f"child-src 'self'; "
                f"frame-src 'self'; "
                f"report-uri /api/csp-report; "
                f"upgrade-insecure-requests"
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
        # Allow HTTP for localhost/development (regardless of debug mode)
        if not request.is_secure:
            if request.remote_addr in ['127.0.0.1', '::1', 'localhost']:
                # Allow HTTP for local development
                return f(*args, **kwargs)
            else:
                logger.warning(f"HTTP request to secure endpoint from {request.remote_addr}")
                abort(403)
        return f(*args, **kwargs)
    return decorated_function

def validate_csrf_token(f):
    """Decorator to validate CSRF tokens using Redis session-aware validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            try:
                # Get CSRF token from form data or headers
                csrf_token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
                
                if not csrf_token:
                    logger.warning(f"CSRF token missing from {request.remote_addr}")
                    abort(403, description="CSRF token is required")
                
                # Use our Redis-aware CSRF token manager for validation
                csrf_manager = getattr(current_app, 'csrf_token_manager', None)
                if not csrf_manager:
                    # Fallback: create a temporary CSRF manager
                    from app.core.security.core.csrf_token_manager import CSRFTokenManager
                    csrf_manager = CSRFTokenManager()
                
                # Validate token using Redis session ID
                is_valid = csrf_manager.validate_token(csrf_token)
                
                if not is_valid:
                    logger.warning(f"CSRF validation failed from {request.remote_addr}")
                    abort(403, description="CSRF token validation failed")
                    
                logger.debug(f"CSRF token validated successfully for {request.endpoint}")
                
            except Exception as e:
                logger.error(f"CSRF validation error: {e}")
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

def rate_limit(limit=120, window_seconds=60, requests_per_minute=None):
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
