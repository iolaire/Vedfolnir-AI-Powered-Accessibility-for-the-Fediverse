# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket WSGI Middleware

This middleware intercepts WebSocket requests at the WSGI level to prevent
session handling that causes "write() before start_response" errors.
"""

import logging
from typing import Callable, Any, List, Tuple

logger = logging.getLogger(__name__)

class WebSocketWSGIMiddleware:
    """
    WSGI middleware that intercepts WebSocket requests to prevent session handling issues
    """
    
    def __init__(self, app: Callable):
        """
        Initialize the WebSocket WSGI middleware
        
        Args:
            app: The WSGI application to wrap
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    def __call__(self, environ: dict, start_response: Callable) -> Any:
        """
        WSGI application callable
        
        Args:
            environ: WSGI environment dictionary
            start_response: WSGI start_response callable
            
        Returns:
            WSGI response
        """
        # Check if this is a WebSocket request
        if self._is_websocket_request(environ):
            self.logger.info(f"WebSocket request intercepted: {environ.get('PATH_INFO', 'unknown')}")
            
            # For WebSocket requests, we need to be very careful about session handling
            # Remove any session-related middleware from the environ if possible
            self._prepare_websocket_environ(environ)
        
        # Call the wrapped application
        return self.app(environ, start_response)
    
    def _is_websocket_request(self, environ: dict) -> bool:
        """
        Check if the request is a WebSocket request
        
        Args:
            environ: WSGI environment dictionary
            
        Returns:
            True if this is a WebSocket request
        """
        # Check for WebSocket upgrade headers
        upgrade = environ.get('HTTP_UPGRADE', '').lower()
        connection = environ.get('HTTP_CONNECTION', '').lower()
        
        # Check for SocketIO path
        path = environ.get('PATH_INFO', '')
        
        # Check query string for WebSocket transport
        query_string = environ.get('QUERY_STRING', '')
        
        is_websocket = (
            upgrade == 'websocket' or
            'upgrade' in connection or
            'websocket' in connection or
            path.startswith('/socket.io/') or
            'transport=websocket' in query_string or
            'EIO=' in query_string
        )
        
        if is_websocket:
            self.logger.debug(f"WebSocket detected - Path: {path}, Upgrade: {upgrade}, Connection: {connection}, Query: {query_string}")
        
        return is_websocket
    
    def _prepare_websocket_environ(self, environ: dict) -> None:
        """
        Prepare the WSGI environ for WebSocket handling
        
        Args:
            environ: WSGI environment dictionary to modify
        """
        # Add a flag to indicate this is a WebSocket request
        environ['vedfolnir.websocket_request'] = True
        
        # Log the preparation
        self.logger.debug(f"Prepared WebSocket environ for {environ.get('PATH_INFO', 'unknown')}")

def create_websocket_wsgi_middleware(app: Callable) -> WebSocketWSGIMiddleware:
    """
    Create and configure WebSocket WSGI middleware
    
    Args:
        app: The Flask application to wrap
        
    Returns:
        Configured WebSocket WSGI middleware
    """
    middleware = WebSocketWSGIMiddleware(app)
    logger.info("WebSocket WSGI middleware created")
    return middleware