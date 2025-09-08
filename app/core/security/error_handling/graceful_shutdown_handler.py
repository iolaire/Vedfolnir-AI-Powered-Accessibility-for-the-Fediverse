# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Graceful Shutdown Handler

Provides graceful shutdown capabilities for the Flask web application,
ensuring that running caption generation jobs are completed or safely cancelled
before the application terminates.
"""

import logging
import signal
import threading
import time
import atexit
from typing import Dict, Any, Optional, List
from flask import Flask

from system_recovery_manager import SystemRecoveryManager
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class GracefulShutdownHandler:
    """Handles graceful shutdown for Flask applications"""
    
    def __init__(self, app: Flask, recovery_manager: SystemRecoveryManager, 
                 shutdown_timeout: int = 30):
        self.app = app
        self.recovery_manager = recovery_manager
        self.shutdown_timeout = shutdown_timeout
        self._shutdown_initiated = False
        self._shutdown_lock = threading.Lock()
        
        # Register shutdown handlers
        self._register_signal_handlers()
        self._register_atexit_handler()
        
        # Store reference in app for access from other components
        app.graceful_shutdown_handler = self
        
        logger.info(f"Graceful shutdown handler initialized with {shutdown_timeout}s timeout")
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = {
                signal.SIGTERM: 'SIGTERM',
                signal.SIGINT: 'SIGINT'
            }.get(signum, f'Signal {signum}')
            
            logger.info(f"Received {signal_name}, initiating graceful shutdown")
            self.initiate_shutdown(f"Received {signal_name}")
        
        # Register handlers for common shutdown signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # On Windows, also handle SIGBREAK
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    def _register_atexit_handler(self):
        """Register atexit handler for cleanup"""
        def atexit_handler():
            if not self._shutdown_initiated:
                logger.info("Application exiting, performing cleanup")
                self.initiate_shutdown("Application exit")
        
        atexit.register(atexit_handler)
    
    def initiate_shutdown(self, reason: str = "Manual shutdown") -> Dict[str, Any]:
        """
        Initiate graceful shutdown process
        
        Args:
            reason: Reason for shutdown
            
        Returns:
            Dict with shutdown statistics
        """
        with self._shutdown_lock:
            if self._shutdown_initiated:
                logger.info("Shutdown already initiated, skipping")
                return {"status": "already_initiated"}
            
            self._shutdown_initiated = True
        
        logger.info(f"Initiating graceful shutdown: {sanitize_for_log(reason)}")
        
        try:
            # Perform graceful shutdown using recovery manager
            import asyncio
            
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run shutdown process
            shutdown_stats = loop.run_until_complete(
                self.recovery_manager.graceful_shutdown(self.shutdown_timeout)
            )
            
            logger.info(f"Graceful shutdown completed: {shutdown_stats}")
            return shutdown_stats
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {sanitize_for_log(str(e))}")
            return {"status": "error", "error": str(e)}
    
    def is_shutdown_initiated(self) -> bool:
        """Check if shutdown has been initiated"""
        return self._shutdown_initiated
    
    def get_shutdown_status(self) -> Dict[str, Any]:
        """Get current shutdown status"""
        return {
            "shutdown_initiated": self._shutdown_initiated,
            "shutdown_timeout": self.shutdown_timeout
        }

class FlaskShutdownMiddleware:
    """Middleware to handle shutdown requests during Flask request processing"""
    
    def __init__(self, app: Flask, shutdown_handler: GracefulShutdownHandler):
        self.app = app
        self.shutdown_handler = shutdown_handler
        
        # Register before_request handler
        app.before_request(self._before_request)
        
        # Register after_request handler
        app.after_request(self._after_request)
    
    def _before_request(self):
        """Check if shutdown is initiated before processing requests"""
        if self.shutdown_handler.is_shutdown_initiated():
            from flask import jsonify, request
            
            # Return appropriate response based on request type
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    "error": "Service is shutting down",
                    "message": "The service is currently shutting down. Please try again later."
                }), 503
            else:
                from flask import render_template
                try:
                    return render_template('errors/503.html', 
                                         message="Service is shutting down"), 503
                except:
                    return "Service is shutting down. Please try again later.", 503
    
    def _after_request(self, response):
        """Add shutdown headers if shutdown is initiated"""
        if self.shutdown_handler.is_shutdown_initiated():
            response.headers['X-Service-Status'] = 'shutting-down'
            response.headers['Retry-After'] = '60'  # Suggest retry after 60 seconds
        
        return response

def initialize_graceful_shutdown(app: Flask, recovery_manager: SystemRecoveryManager, 
                               shutdown_timeout: int = 30) -> GracefulShutdownHandler:
    """
    Initialize graceful shutdown handling for a Flask application
    
    Args:
        app: Flask application instance
        recovery_manager: System recovery manager instance
        shutdown_timeout: Timeout in seconds for graceful shutdown
        
    Returns:
        GracefulShutdownHandler instance
    """
    # Create shutdown handler
    shutdown_handler = GracefulShutdownHandler(app, recovery_manager, shutdown_timeout)
    
    # Create and register middleware
    shutdown_middleware = FlaskShutdownMiddleware(app, shutdown_handler)
    
    # Add shutdown route for manual shutdown (admin only)
    @app.route('/admin/api/shutdown', methods=['POST'])
    def admin_shutdown():
        from flask import request, jsonify
        from flask_login import current_user
        from models import UserRole
        
        # Check admin authorization
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Get shutdown reason from request
        data = request.get_json() or {}
        reason = data.get('reason', 'Manual admin shutdown')
        
        # Initiate shutdown
        shutdown_stats = shutdown_handler.initiate_shutdown(reason)
        
        return jsonify({
            "message": "Graceful shutdown initiated",
            "stats": shutdown_stats
        })
    
    # Add shutdown status route
    @app.route('/api/shutdown-status')
    def shutdown_status():
        from flask import jsonify
        
        status = shutdown_handler.get_shutdown_status()
        return jsonify(status)
    
    logger.info("Graceful shutdown handling initialized")
    return shutdown_handler

# Context manager for graceful operations
class GracefulOperationContext:
    """Context manager for operations that should complete before shutdown"""
    
    def __init__(self, operation_name: str, shutdown_handler: GracefulShutdownHandler):
        self.operation_name = operation_name
        self.shutdown_handler = shutdown_handler
        self._operation_started = False
    
    def __enter__(self):
        if self.shutdown_handler.is_shutdown_initiated():
            raise RuntimeError(f"Cannot start {self.operation_name}: shutdown in progress")
        
        self._operation_started = True
        logger.debug(f"Started graceful operation: {sanitize_for_log(self.operation_name)}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._operation_started:
            logger.debug(f"Completed graceful operation: {sanitize_for_log(self.operation_name)}")
        
        # Don't suppress exceptions
        return False

def graceful_operation(operation_name: str, app: Flask):
    """
    Decorator for operations that should complete before shutdown
    
    Args:
        operation_name: Name of the operation for logging
        app: Flask application instance
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            shutdown_handler = getattr(app, 'graceful_shutdown_handler', None)
            if not shutdown_handler:
                # No shutdown handler, proceed normally
                return func(*args, **kwargs)
            
            with GracefulOperationContext(operation_name, shutdown_handler):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator