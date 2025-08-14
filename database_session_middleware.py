# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Database Session Middleware

This middleware provides session context from database sessions, replacing Flask session
access with database session context. It loads session data before each request and
makes it available through the Flask g object.
"""

from logging import getLogger
from typing import Optional, Dict, Any
from flask import g, request, Flask
from unified_session_manager import UnifiedSessionManager, SessionValidationError, SessionExpiredError, SessionNotFoundError
from session_cookie_manager import SessionCookieManager

logger = getLogger(__name__)

class DatabaseSessionMiddleware:
    """Middleware to provide session context from database"""
    
    def __init__(self, app: Flask, session_manager: UnifiedSessionManager, cookie_manager: SessionCookieManager):
        """
        Initialize database session middleware
        
        Args:
            app: Flask application instance
            session_manager: Unified session manager
            cookie_manager: Session cookie manager
        """
        self.app = app
        self.session_manager = session_manager
        self.cookie_manager = cookie_manager
        self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize the middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self) -> None:
        """Load session context before each request"""
        # Initialize safe defaults
        g.session_context = None
        g.session_id = None
        g.session_manager = self.session_manager
        g.cookie_manager = self.cookie_manager
        
        try:
            # Skip session loading for static files and health checks
            if self._should_skip_session_loading():
                return
            
            # Get session ID from cookie
            session_id = self.cookie_manager.get_session_id_from_cookie()
            if not session_id:
                logger.debug("No session ID found in cookie")
                return
            
            # Load session context from database
            try:
                session_context = self.session_manager.get_session_context(session_id)
                if session_context:
                    g.session_context = session_context
                    g.session_id = session_id
                    logger.debug(f"Loaded session context for user {session_context.get('user_id')}")
                else:
                    logger.debug(f"No valid session context found for session ID {session_id[:8]}...")
                    # Session is invalid/expired, we'll let the cookie expire naturally
            except (SessionValidationError, SessionExpiredError, SessionNotFoundError) as e:
                logger.debug(f"Session validation failed: {e}")
                # Store the error for potential handling by routes
                g.session_error = e
                # Clear invalid session cookie
                g.clear_session_cookie = True
                
        except Exception as e:
            logger.error(f"Error in database session middleware before_request: {e}")
            # Ensure g has safe defaults even if there's an error
            g.session_context = None
            g.session_id = None
            g.session_manager = self.session_manager
            g.cookie_manager = self.cookie_manager
    
    def after_request(self, response) -> None:
        """Clean up after request"""
        try:
            # Clear session cookie if requested
            if getattr(g, 'clear_session_cookie', False):
                self.cookie_manager.clear_session_cookie(response)
            
            # Update session activity if we have an active session
            session_id = getattr(g, 'session_id', None)
            if session_id and hasattr(g, 'session_context') and g.session_context:
                # Update session activity (this is done automatically in get_session_context)
                # but we can refresh the cookie here if needed
                self.cookie_manager.refresh_session_cookie(response, session_id)
        except Exception as e:
            logger.debug(f"Error in database session middleware after_request: {e}")
        
        # Clean up g object
        if hasattr(g, 'session_context'):
            g.session_context = None
        if hasattr(g, 'session_id'):
            g.session_id = None
        if hasattr(g, 'session_error'):
            g.session_error = None
        if hasattr(g, 'clear_session_cookie'):
            g.clear_session_cookie = None
        
        return response
    
    def _should_skip_session_loading(self) -> bool:
        """
        Determine if session loading should be skipped for this request
        
        Returns:
            True if session loading should be skipped, False otherwise
        """
        # Skip for static files
        if request.endpoint == 'static':
            return True
        
        # Skip for health check endpoints
        if request.endpoint in ['health', 'health_check']:
            return True
        
        # Skip for API endpoints that don't need sessions
        if request.path.startswith('/api/health'):
            return True
        
        # Skip for favicon requests
        if request.path == '/favicon.ico':
            return True
        
        return False


# Session context access functions to replace Flask session usage
def get_current_session_context() -> Optional[Dict[str, Any]]:
    """
    Get current session context from g object
    
    Returns:
        Session context dictionary or None if no session
    """
    return getattr(g, 'session_context', None)

def get_current_session_id() -> Optional[str]:
    """
    Get current session ID from g object
    
    Returns:
        Session ID or None if no session
    """
    return getattr(g, 'session_id', None)

def get_current_user_id() -> Optional[int]:
    """
    Get current user ID from session context
    
    Returns:
        User ID or None if no session or user
    """
    context = get_current_session_context()
    return context.get('user_id') if context else None

def get_current_platform_id() -> Optional[int]:
    """
    Get current platform ID from session context
    
    Returns:
        Platform connection ID or None if no session or platform
    """
    context = get_current_session_context()
    return context.get('platform_connection_id') if context else None

def get_current_user_info() -> Optional[Dict[str, Any]]:
    """
    Get current user information from session context
    
    Returns:
        User info dictionary or None if no session or user
    """
    context = get_current_session_context()
    return context.get('user_info') if context else None

def get_current_platform_info() -> Optional[Dict[str, Any]]:
    """
    Get current platform information from session context
    
    Returns:
        Platform info dictionary or None if no session or platform
    """
    context = get_current_session_context()
    return context.get('platform_info') if context else None

def update_session_platform(platform_id: int) -> bool:
    """
    Update current session's platform context
    
    Args:
        platform_id: New platform connection ID
        
    Returns:
        True if successful, False otherwise
    """
    session_id = get_current_session_id()
    session_manager = getattr(g, 'session_manager', None)
    
    if session_id and session_manager:
        success = session_manager.update_platform_context(session_id, platform_id)
        if success:
            # Reload session context to reflect the change
            updated_context = session_manager.get_session_context(session_id)
            if updated_context:
                g.session_context = updated_context
        return success
    
    return False

def is_session_authenticated() -> bool:
    """
    Check if current session is authenticated
    
    Returns:
        True if session is authenticated, False otherwise
    """
    context = get_current_session_context()
    return context is not None and context.get('user_id') is not None

def get_session_created_at() -> Optional[str]:
    """
    Get session creation timestamp
    
    Returns:
        ISO format timestamp or None if no session
    """
    context = get_current_session_context()
    return context.get('created_at') if context else None

def get_session_last_activity() -> Optional[str]:
    """
    Get session last activity timestamp
    
    Returns:
        ISO format timestamp or None if no session
    """
    context = get_current_session_context()
    return context.get('last_activity') if context else None