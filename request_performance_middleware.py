# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Request Performance Middleware

This middleware automatically tracks request performance metrics for responsiveness monitoring.
It integrates with the SystemOptimizer to provide real-time request timing data.
"""

import time
import logging
from flask import request, g, current_app
from functools import wraps

logger = logging.getLogger(__name__)


class RequestPerformanceMiddleware:
    """Middleware for tracking request performance metrics"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)
        
        # Store reference to middleware in app
        app.request_performance_middleware = self
        
        logger.info("Request performance middleware initialized")
    
    def before_request(self):
        """Track request start time"""
        try:
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if system_optimizer and hasattr(system_optimizer, 'track_request_start'):
                # Generate request ID
                request_id = f"{request.method}_{request.endpoint}_{int(time.time() * 1000)}"
                
                # Track request start
                request_data = system_optimizer.track_request_start(request_id)
                
                # Store in Flask's g object for access in after_request
                g.request_performance_data = request_data
                g.request_start_time = time.time()
                
        except Exception as e:
            logger.error(f"Error in request performance before_request: {e}")
            # Don't let middleware errors break the request
            g.request_performance_data = None
            g.request_start_time = time.time()
    
    def after_request(self, response):
        """Track request completion and performance"""
        try:
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            request_data = getattr(g, 'request_performance_data', None)
            
            if system_optimizer and request_data and hasattr(system_optimizer, 'track_request_end'):
                # Track request end with details
                system_optimizer.track_request_end(
                    request_data,
                    endpoint=request.endpoint,
                    method=request.method,
                    status_code=response.status_code
                )
                
        except Exception as e:
            logger.error(f"Error in request performance after_request: {e}")
            # Don't let middleware errors break the response
        
        return response
    
    def teardown_request(self, exception):
        """Clean up request performance tracking data"""
        try:
            # Clean up any request-specific data
            if hasattr(g, 'request_performance_data'):
                delattr(g, 'request_performance_data')
            if hasattr(g, 'request_start_time'):
                delattr(g, 'request_start_time')
                
        except Exception as e:
            logger.error(f"Error in request performance teardown: {e}")


def track_slow_requests(threshold_seconds=5.0):
    """Decorator to track slow requests for specific endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                request_time = end_time - start_time
                
                if request_time > threshold_seconds:
                    logger.warning(
                        f"Slow request detected: {request.endpoint} "
                        f"({request.method}) took {request_time:.2f}s"
                    )
                    
                    # Track with system optimizer if available
                    system_optimizer = getattr(current_app, 'system_optimizer', None)
                    if system_optimizer and hasattr(system_optimizer, '_slow_requests'):
                        try:
                            slow_request = {
                                'id': f"slow_{int(end_time * 1000)}",
                                'time': request_time,
                                'timestamp': end_time,
                                'endpoint': request.endpoint,
                                'method': request.method,
                                'status_code': None  # Will be set by after_request
                            }
                            
                            if system_optimizer._request_lock:
                                with system_optimizer._request_lock:
                                    system_optimizer._slow_requests.append(slow_request)
                                    
                                    # Keep only recent slow requests
                                    if len(system_optimizer._slow_requests) > 100:
                                        system_optimizer._slow_requests = system_optimizer._slow_requests[-100:]
                        except Exception as e:
                            logger.error(f"Error tracking slow request: {e}")
        
        return decorated_function
    return decorator


def get_request_performance_summary():
    """Get a summary of current request performance"""
    try:
        system_optimizer = getattr(current_app, 'system_optimizer', None)
        if not system_optimizer:
            return {'error': 'System optimizer not available'}
        
        return system_optimizer._get_request_performance_metrics()
        
    except Exception as e:
        logger.error(f"Error getting request performance summary: {e}")
        return {'error': str(e)}


def initialize_request_performance_middleware(app):
    """Initialize request performance middleware with Flask app"""
    try:
        middleware = RequestPerformanceMiddleware(app)
        return middleware
    except Exception as e:
        logger.error(f"Failed to initialize request performance middleware: {e}")
        return None