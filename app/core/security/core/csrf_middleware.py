# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Validation Middleware

Flask middleware for consistent CSRF validation across all routes
with automatic token generation and exemption handling.
"""

import logging
from typing import Set, List, Optional, Callable
from functools import wraps
from flask import request, g, current_app
# Removed Flask-WTF validate_csrf import - using custom CSRF system only
from werkzeug.exceptions import Forbidden
from app.core.security.core.csrf_token_manager import get_csrf_token_manager, CSRFValidationContext
from app.core.security.core.csrf_error_handler import get_csrf_error_handler
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class CSRFMiddleware:
    """CSRF validation middleware for Flask applications"""
    
    def __init__(self, app=None):
        """Initialize CSRF middleware
        
        Args:
            app: Flask application instance (optional)
        """
        self.app = app
        self.exempt_endpoints: Set[str] = set()
        self.exempt_methods: Set[str] = {'GET', 'HEAD', 'OPTIONS'}
        self.exempt_paths: Set[str] = set()
        self.validation_callbacks: List[Callable] = []
        
        # Default exempt endpoints
        self.default_exempt_endpoints = {
            'static',
            'api_get_csrf_token',
            'health_check',
            'favicon'
        }
        
        # Default exempt paths
        self.default_exempt_paths = {
            '/static/',
            '/favicon.ico',
            '/robots.txt',
            '/health',
            '/api/health'
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Add default exemptions
        self.exempt_endpoints.update(self.default_exempt_endpoints)
        self.exempt_paths.update(self.default_exempt_paths)
        
        # Register middleware
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Store middleware in app
        app.csrf_middleware = self
        
        logger.info("CSRF middleware initialized")
    
    def before_request(self):
        """Process request before route handler"""
        try:
            # Skip CSRF validation for exempt requests
            if self._is_request_exempt():
                g.csrf_exempt = True
                return None
            
            # Validate CSRF token for state-changing requests
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self._validate_csrf_token()
            
            g.csrf_exempt = False
            return None
            
        except Exception as e:
            logger.error(f"CSRF middleware error: {sanitize_for_log(str(e))}")
            # Let the error handler deal with it
            raise
    
    def after_request(self, response):
        """Process response after route handler
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response object
        """
        try:
            # Add CSRF token to response headers for AJAX requests
            if (request.method == 'GET' and 
                request.headers.get('X-Requested-With') == 'XMLHttpRequest'):
                
                try:
                    csrf_manager = get_csrf_token_manager()
                    token = csrf_manager.generate_token()
                    response.headers['X-CSRF-Token'] = token
                except Exception as e:
                    logger.warning(f"Failed to add CSRF token to response: {e}")
            
            return response
            
        except Exception as e:
            logger.error(f"CSRF middleware after_request error: {sanitize_for_log(str(e))}")
            return response
    
    def _is_request_exempt(self) -> bool:
        """Check if current request is exempt from CSRF validation
        
        Returns:
            True if request is exempt, False otherwise
        """
        # Check method exemption
        if request.method in self.exempt_methods:
            return True
        
        # Check endpoint exemption
        if request.endpoint in self.exempt_endpoints:
            return True
        
        # Check path exemption
        for exempt_path in self.exempt_paths:
            if request.path.startswith(exempt_path):
                return True
        
        # Check custom validation callbacks
        for callback in self.validation_callbacks:
            try:
                if callback(request):
                    return True
            except Exception as e:
                logger.warning(f"CSRF exemption callback error: {e}")
        
        return False
    
    def _validate_csrf_token(self):
        """Validate CSRF token for current request using our custom Redis session-aware validation"""
        try:
            # Get CSRF token from headers or form
            csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            
            if not csrf_token:
                logger.warning(f"CSRF token missing for {request.endpoint}")
                # Use werkzeug Forbidden instead of Flask-WTF CSRFError
                raise Forbidden("CSRF token is required")
            
            # Use our Redis-aware CSRF token manager for validation
            csrf_manager = get_csrf_token_manager()
            is_valid = csrf_manager.validate_token(csrf_token)
            
            if not is_valid:
                logger.warning(f"CSRF token validation failed for {request.endpoint}")
                # Use werkzeug Forbidden instead of Flask-WTF CSRFError
                raise Forbidden("CSRF token validation failed")
            
            logger.debug(f"CSRF validation successful for {request.endpoint}")
            
        except Exception as e:
            # Create validation context
            context = CSRFValidationContext(
                request_method=request.method,
                endpoint=request.endpoint or 'unknown',
                user_id=getattr(g, 'user_id', None)
            )
            
            # Handle CSRF error
            csrf_error_handler = get_csrf_error_handler()
            response, status_code = csrf_error_handler.handle_csrf_failure(e, context)
            
            # Raise Forbidden exception with custom response
            error = Forbidden()
            error.response = response
            raise error
    
    def exempt_endpoint(self, endpoint: str):
        """Add endpoint to CSRF exemption list
        
        Args:
            endpoint: Endpoint name to exempt
        """
        self.exempt_endpoints.add(endpoint)
        logger.debug(f"Added CSRF exemption for endpoint: {endpoint}")
    
    def exempt_path(self, path: str):
        """Add path to CSRF exemption list
        
        Args:
            path: Path pattern to exempt
        """
        self.exempt_paths.add(path)
        logger.debug(f"Added CSRF exemption for path: {path}")
    
    def exempt_method(self, method: str):
        """Add HTTP method to CSRF exemption list
        
        Args:
            method: HTTP method to exempt
        """
        self.exempt_methods.add(method.upper())
        logger.debug(f"Added CSRF exemption for method: {method}")
    
    def add_validation_callback(self, callback: Callable[[any], bool]):
        """Add custom validation callback
        
        Args:
            callback: Function that takes request and returns bool (True = exempt)
        """
        self.validation_callbacks.append(callback)
        logger.debug("Added custom CSRF validation callback")
    
    def remove_exemption(self, endpoint: Optional[str] = None, 
                        path: Optional[str] = None, 
                        method: Optional[str] = None):
        """Remove exemption from CSRF validation
        
        Args:
            endpoint: Endpoint to remove from exemption
            path: Path to remove from exemption
            method: Method to remove from exemption
        """
        if endpoint and endpoint in self.exempt_endpoints:
            self.exempt_endpoints.remove(endpoint)
            logger.debug(f"Removed CSRF exemption for endpoint: {endpoint}")
        
        if path and path in self.exempt_paths:
            self.exempt_paths.remove(path)
            logger.debug(f"Removed CSRF exemption for path: {path}")
        
        if method and method.upper() in self.exempt_methods:
            self.exempt_methods.remove(method.upper())
            logger.debug(f"Removed CSRF exemption for method: {method}")
    
    def get_exemptions(self) -> dict:
        """Get current exemption configuration
        
        Returns:
            Dictionary of current exemptions
        """
        return {
            'endpoints': list(self.exempt_endpoints),
            'paths': list(self.exempt_paths),
            'methods': list(self.exempt_methods),
            'callbacks': len(self.validation_callbacks)
        }

def csrf_exempt(f):
    """Decorator to exempt a route from CSRF validation
    
    Args:
        f: Route function to exempt
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.csrf_exempt = True
        return f(*args, **kwargs)
    
    return decorated_function

def require_csrf(f):
    """Decorator to explicitly require CSRF validation for a route
    
    Args:
        f: Route function that requires CSRF validation
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Force CSRF validation even for GET requests
        if not getattr(g, 'csrf_exempt', False):
            try:
                # Use our custom CSRF validation instead of Flask-WTF
                csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
                if not csrf_token:
                    raise Exception("CSRF token is required")
                
                # Use our Redis-aware CSRF token manager for validation
                csrf_manager = get_csrf_token_manager()
                is_valid = csrf_manager.validate_token(csrf_token)
                
                if not is_valid:
                    raise Exception("CSRF token validation failed")
                    
            except Exception as e:
                context = CSRFValidationContext(
                    request_method=request.method,
                    endpoint=request.endpoint or 'unknown'
                )
                
                csrf_error_handler = get_csrf_error_handler()
                response, status_code = csrf_error_handler.handle_csrf_failure(e, context)
                
                error = Forbidden()
                error.response = response
                raise error
        
        return f(*args, **kwargs)
    
    return decorated_function

def initialize_csrf_middleware(app) -> CSRFMiddleware:
    """Initialize CSRF middleware for Flask app
    
    Args:
        app: Flask application instance
        
    Returns:
        Initialized CSRFMiddleware instance
    """
    middleware = CSRFMiddleware(app)
    
    # Add application-specific exemptions
    if hasattr(app, 'config'):
        # Exempt health check endpoints
        middleware.exempt_endpoint('health_check')
        middleware.exempt_endpoint('api_health_check')
        
        # Exempt static file serving
        middleware.exempt_path('/static/')
        middleware.exempt_path('/favicon.ico')
        
        # Add custom exemptions from config
        custom_exempt_endpoints = app.config.get('CSRF_EXEMPT_ENDPOINTS', [])
        for endpoint in custom_exempt_endpoints:
            middleware.exempt_endpoint(endpoint)
        
        custom_exempt_paths = app.config.get('CSRF_EXEMPT_PATHS', [])
        for path in custom_exempt_paths:
            middleware.exempt_path(path)
    
    logger.info("CSRF middleware initialized with application-specific configuration")
    return middleware

# Global middleware instance
_csrf_middleware: Optional[CSRFMiddleware] = None

def get_csrf_middleware() -> Optional[CSRFMiddleware]:
    """Get the global CSRF middleware instance
    
    Returns:
        CSRFMiddleware instance or None
    """
    global _csrf_middleware
    return _csrf_middleware

def set_csrf_middleware(middleware: CSRFMiddleware):
    """Set the global CSRF middleware instance
    
    Args:
        middleware: CSRFMiddleware instance
    """
    global _csrf_middleware
    _csrf_middleware = middleware