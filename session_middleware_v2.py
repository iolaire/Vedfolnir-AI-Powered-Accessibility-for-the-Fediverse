# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Middleware V2

Simplified session middleware that works with Flask sessions and Redis backend.
Provides session context and helper functions for the application.
"""

from typing import Optional, Dict, Any
from flask import session, g, request, current_app
from logging import getLogger

logger = getLogger(__name__)

class SessionMiddleware:
    """
    Simplified session middleware for Flask Redis sessions
    
    This middleware:
    - Extracts session context from Flask session
    - Provides helper functions for session access
    - Handles session ID management
    - Integrates with the session manager
    """
    
    def __init__(self, app, session_manager):
        """
        Initialize session middleware
        
        Args:
            app: Flask application instance
            session_manager: Session manager instance
        """
        self.app = app
        self.session_manager = session_manager
        
        # Register middleware hooks
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """
        Process request before route handler
        
        Sets up session context in g object for easy access
        """
        try:
            # Get session ID from Flask session (managed by Redis session interface)
            session_id = getattr(session, 'sid', None) if hasattr(session, 'sid') else None
            
            if session_id:
                # Store session ID in g for easy access
                g.session_id = session_id
                
                # Get fresh session data from Redis to ensure consistency
                fresh_session_data = None
                if self.session_manager and hasattr(self.session_manager, 'get_session_data'):
                    try:
                        fresh_session_data = self.session_manager.get_session_data(session_id)
                        if fresh_session_data:
                            logger.debug(f"Retrieved fresh session data from Redis: {fresh_session_data}")
                            
                            # Update Flask session with fresh data if there are discrepancies
                            platform_keys = ['platform_connection_id', 'platform_name', 'platform_type', 'platform_instance_url']
                            session_updated = False
                            
                            for key in platform_keys:
                                if key in fresh_session_data:
                                    flask_value = session.get(key)
                                    redis_value = fresh_session_data[key]
                                    if flask_value != redis_value:
                                        logger.info(f"Syncing Flask session {key}: {flask_value} -> {redis_value}")
                                        session[key] = redis_value
                                        session_updated = True
                            
                            if session_updated:
                                session.modified = True
                                logger.info("Flask session updated with fresh Redis data")
                    except Exception as e:
                        logger.debug(f"Could not get fresh session data from Redis: {e}")
                
                # Create session context from Flask session data (with Redis sync)
                g.session_context = {
                    'session_id': session_id,
                    'user_id': session.get('user_id'),
                    'username': session.get('username'),
                    'email': session.get('email'),
                    'role': session.get('role'),
                    'platform_connection_id': session.get('platform_connection_id'),
                    'platform_name': session.get('platform_name'),
                    'platform_type': session.get('platform_type'),
                    'platform_instance_url': session.get('platform_instance_url'),
                    'csrf_token': session.get('csrf_token'),
                    'created_at': session.get('created_at'),
                    'last_activity': session.get('last_activity')
                }
                
                # Remove None values
                g.session_context = {k: v for k, v in g.session_context.items() if v is not None}
                
                logger.debug(f"Session context created: {g.session_context}")
                
            else:
                g.session_id = None
                g.session_context = None
                logger.debug("No session ID found, cleared session context")
                
        except Exception as e:
            logger.debug(f"Error in session middleware before_request: {e}")
            g.session_id = None
            g.session_context = None
    
    def after_request(self, response):
        """
        Process response after route handler
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response object
        """
        try:
            # Update session activity if session exists
            if hasattr(g, 'session_id') and g.session_id:
                # Flask session interface handles TTL updates automatically
                pass
                
        except Exception as e:
            logger.debug(f"Error in session middleware after_request: {e}")
        
        return response

# Helper functions for session access

def get_current_session_id() -> Optional[str]:
    """
    Get current session ID
    
    Returns:
        Session ID or None if no session
    """
    return getattr(g, 'session_id', None)

def get_current_session_context() -> Optional[Dict[str, Any]]:
    """
    Get current session context
    
    Returns:
        Session context dictionary or None if no session
    """
    return getattr(g, 'session_context', None)

def get_current_user_id() -> Optional[int]:
    """
    Get current user ID from session
    
    Returns:
        User ID or None if not logged in
    """
    context = get_current_session_context()
    return context.get('user_id') if context else None

def get_current_platform_id() -> Optional[int]:
    """
    Get current platform connection ID from session
    
    Returns:
        Platform connection ID or None if no platform selected
    """
    context = get_current_session_context()
    return context.get('platform_connection_id') if context else None

def get_current_platform_info() -> Optional[Dict[str, Any]]:
    """
    Get current platform information from session
    
    Returns:
        Platform info dictionary or None if no platform selected
    """
    context = get_current_session_context()
    if not context:
        return None
    
    platform_info = {}
    for key in ['platform_connection_id', 'platform_name', 'platform_type', 'platform_instance_url']:
        if key in context:
            platform_info[key] = context[key]
    
    return platform_info if platform_info else None

def update_session_platform(platform_connection_id: int) -> bool:
    """
    Update current session's platform context with improved error handling
    
    Args:
        platform_connection_id: New platform connection ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting platform update to {platform_connection_id}")
        
        session_id = get_current_session_id()
        if not session_id:
            logger.error("No current session ID found")
            return False
        
        logger.info(f"Current session ID: {session_id}")
        
        # Get session manager from app
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            logger.error("No session manager found in app")
            return False
        
        # First, update the Redis session manager
        logger.info("Updating Redis session manager...")
        success = session_manager.switch_platform(session_id, platform_connection_id)
        
        if not success:
            logger.error("Failed to update Redis session manager")
            return False
        
        logger.info("Redis session manager updated successfully")
        
        # Get updated session data from Redis
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            logger.error("Failed to get updated session data from Redis")
            return False
        
        logger.info(f"Retrieved session data: {session_data}")
        
        # Update Flask session with new platform data
        platform_keys = ['platform_connection_id', 'platform_name', 'platform_type', 'platform_instance_url']
        updated_keys = []
        
        for key in platform_keys:
            if key in session_data:
                old_value = session.get(key)
                new_value = session_data[key]
                session[key] = new_value
                updated_keys.append(key)
                logger.info(f"Updated Flask session {key}: {old_value} -> {new_value}")
        
        if not updated_keys:
            logger.error("No platform keys found in session data")
            return False
        
        # CRITICAL: Mark Flask session as modified to ensure it gets saved
        session.modified = True
        logger.info("Marked Flask session as modified")
        
        # Update g.session_context for current request (if it exists)
        if hasattr(g, 'session_context') and g.session_context:
            platform_updates = {
                k: v for k, v in session_data.items() 
                if k.startswith('platform_')
            }
            g.session_context.update(platform_updates)
            logger.info(f"Updated g.session_context with: {platform_updates}")
        else:
            logger.warning("g.session_context not available for update")
        
        # Validation: Verify the update was successful
        if session.get('platform_connection_id') != platform_connection_id:
            logger.error(f"Validation failed: Flask session platform_connection_id is {session.get('platform_connection_id')}, expected {platform_connection_id}")
            return False
        
        logger.info(f"Platform update successful: {platform_connection_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating session platform: {e}", exc_info=True)
        return False

def create_user_session(user_id: int, platform_connection_id: Optional[int] = None) -> Optional[str]:
    """
    Create a new session for a user
    
    Args:
        user_id: User ID
        platform_connection_id: Optional platform connection ID
        
    Returns:
        Session ID or None if creation failed
    """
    try:
        # Get session manager from app
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return None
        
        # Create session
        session_id = session_manager.create_session(user_id, platform_connection_id)
        
        if session_id:
            # Get session data and populate Flask session
            session_data = session_manager.get_session_data(session_id)
            if session_data:
                # Clear existing session data
                session.clear()
                
                # Populate Flask session with new data
                for key, value in session_data.items():
                    if not key.startswith('_'):  # Skip internal keys
                        session[key] = value
                
                # Set session as permanent for timeout control
                session.permanent = True
                
                logger.info(f"Created Flask session for user {user_id}")
        
        return session_id
        
    except Exception as e:
        logger.error(f"Error creating user session: {e}")
        return None

def destroy_current_session() -> bool:
    """
    Destroy the current session
    
    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = get_current_session_id()
        if not session_id:
            return False
        
        # Get session manager from app
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return False
        
        # Destroy session in manager
        success = session_manager.destroy_session(session_id)
        
        if success:
            # Clear Flask session
            session.clear()
            
            # Clear g context
            g.session_id = None
            g.session_context = None
        
        return success
        
    except Exception as e:
        logger.error(f"Error destroying current session: {e}")
        return False

def extend_current_session(additional_seconds: int = None) -> bool:
    """
    Extend the current session timeout
    
    Args:
        additional_seconds: Additional seconds to add (default: reset to full timeout)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = get_current_session_id()
        if not session_id:
            return False
        
        # Get session manager from app
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return False
        
        return session_manager.extend_session(session_id, additional_seconds)
        
    except Exception as e:
        logger.error(f"Error extending current session: {e}")
        return False

def is_user_authenticated() -> bool:
    """
    Check if current user is authenticated
    
    Returns:
        True if user is authenticated, False otherwise
    """
    context = get_current_session_context()
    return context is not None and context.get('user_id') is not None

def has_platform_context() -> bool:
    """
    Check if current session has platform context
    
    Returns:
        True if platform context exists, False otherwise
    """
    context = get_current_session_context()
    return context is not None and context.get('platform_connection_id') is not None

def get_csrf_token() -> Optional[str]:
    """
    Get CSRF token from current session
    
    Returns:
        CSRF token or None if no session
    """
    context = get_current_session_context()
    return context.get('csrf_token') if context else None
