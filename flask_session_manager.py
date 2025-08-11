# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Flask-based Session Management System

This module provides Flask-native session management that replaces the database-based
session system. It uses Flask's built-in session handling with secure cookies.
"""

from logging import getLogger
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import session, g, request
from models import User, PlatformConnection
from database import DatabaseManager
from security.core.security_utils import sanitize_for_log

logger = getLogger(__name__)

class FlaskSessionManager:
    """Flask-based session manager using secure cookies"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_user_session(self, user_id: int, platform_connection_id: Optional[int] = None) -> bool:
        """
        Create a new user session using Flask's session
        
        Args:
            user_id: ID of the user
            platform_connection_id: Optional platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear any existing session data
            session.clear()
            
            # Set user session data
            session['user_id'] = user_id
            session['authenticated'] = True
            session['created_at'] = datetime.now(timezone.utc).isoformat()
            session['last_activity'] = datetime.now(timezone.utc).isoformat()
            
            # Set platform context if provided
            if platform_connection_id:
                session['platform_connection_id'] = platform_connection_id
            else:
                # Try to get user's default platform
                db_session = self.db_manager.get_session()
                try:
                    default_platform = db_session.query(PlatformConnection).filter_by(
                        user_id=user_id,
                        is_default=True,
                        is_active=True
                    ).first()
                    
                    if default_platform:
                        session['platform_connection_id'] = default_platform.id
                finally:
                    db_session.close()
            
            # Make session permanent for persistence
            session.permanent = True
            
            logger.info(f"Created Flask session for user {sanitize_for_log(str(user_id))} with platform {sanitize_for_log(str(platform_connection_id))}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Flask session: {e}")
            return False
    
    def get_session_context(self) -> Optional[Dict[str, Any]]:
        """
        Get current session context from Flask session
        
        Returns:
            Dictionary with session context or None if not authenticated
        """
        try:
            # Check if user is authenticated using Flask-Login current_user
            from flask_login import current_user
            if not current_user or not current_user.is_authenticated:
                return None
            
            # Ensure session has user_id set
            if not session.get('user_id'):
                session['user_id'] = current_user.id
                session['authenticated'] = True
            
            # Update last activity
            session['last_activity'] = datetime.now(timezone.utc).isoformat()
            
            # Get platform info if available
            platform_info = None
            platform_connection_id = session.get('platform_connection_id')
            
            if platform_connection_id:
                db_session = self.db_manager.get_session()
                try:
                    platform = db_session.query(PlatformConnection).filter_by(
                        id=platform_connection_id,
                        user_id=current_user.id,
                        is_active=True
                    ).first()
                    
                    if platform:
                        platform_info = {
                            'id': platform.id,
                            'name': platform.name,
                            'platform_type': platform.platform_type,
                            'instance_url': platform.instance_url,
                            'username': platform.username,
                            'is_default': platform.is_default
                        }
                finally:
                    db_session.close()
            
            return {
                'user_id': current_user.id,
                'platform_connection_id': platform_connection_id,
                'platform_info': platform_info,
                'created_at': session.get('created_at'),
                'last_activity': session.get('last_activity')
            }
            
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return None
    
    def update_platform_context(self, platform_connection_id: int) -> bool:
        """
        Update the active platform for current session
        
        Args:
            platform_connection_id: New platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if user is authenticated using Flask-Login current_user
            from flask_login import current_user
            if not current_user or not current_user.is_authenticated:
                logger.warning("Attempted to update platform context for unauthenticated user")
                return False
            
            # Ensure session has user_id set
            if not session.get('user_id'):
                session['user_id'] = current_user.id
                session['authenticated'] = True
            
            # Verify platform belongs to the user
            db_session = self.db_manager.get_session()
            try:
                platform = db_session.query(PlatformConnection).filter_by(
                    id=platform_connection_id,
                    user_id=current_user.id,
                    is_active=True
                ).first()
                
                if not platform:
                    logger.warning(f"Platform {sanitize_for_log(str(platform_connection_id))} not found or not accessible to user {sanitize_for_log(str(current_user.id))}")
                    return False
                
                # Update session
                session['platform_connection_id'] = platform_connection_id
                session['last_activity'] = datetime.now(timezone.utc).isoformat()
                
                # Update platform's last used timestamp
                platform.last_used = datetime.now(timezone.utc)
                db_session.commit()
                
                logger.info(f"Updated session platform to {sanitize_for_log(str(platform_connection_id))} for user {sanitize_for_log(str(current_user.id))}")
                return True
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error updating platform context: {e}")
            return False
    
    def validate_session(self, user_id: int) -> bool:
        """
        Validate that current session belongs to the specified user
        
        Args:
            user_id: Expected user ID
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            from flask_login import current_user
            if not current_user or not current_user.is_authenticated:
                return False
            
            if current_user.id != user_id:
                logger.warning(f"Session user ID mismatch: expected {sanitize_for_log(str(user_id))}, got {sanitize_for_log(str(current_user.id))}")
                return False
            
            # Update last activity
            session['last_activity'] = datetime.now(timezone.utc).isoformat()
            return True
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False
    
    def clear_session(self):
        """Clear the current session"""
        try:
            user_id = session.get('user_id')
            session.clear()
            if user_id:
                logger.info(f"Cleared session for user {sanitize_for_log(str(user_id))}")
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if current session is authenticated"""
        from flask_login import current_user
        return bool(current_user and current_user.is_authenticated)
    
    def get_current_user_id(self) -> Optional[int]:
        """Get current user ID from session"""
        from flask_login import current_user
        return current_user.id if (current_user and current_user.is_authenticated) else None
    
    def get_current_platform_id(self) -> Optional[int]:
        """Get current platform connection ID from session"""
        from flask_login import current_user
        return session.get('platform_connection_id') if (current_user and current_user.is_authenticated) else None


class FlaskPlatformContextMiddleware:
    """Flask middleware for managing platform context in requests"""
    
    def __init__(self, app, flask_session_manager: FlaskSessionManager):
        self.app = app
        self.flask_session_manager = flask_session_manager
        self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Set up platform context before each request"""
        # Initialize safe defaults
        g.platform_context = None
        g.flask_session_manager = self.flask_session_manager
        
        try:
            # Skip for static files and health checks
            if request.endpoint in ['static', 'health']:
                return
            
            # Get session context
            context = self.flask_session_manager.get_session_context()
            if context:
                g.platform_context = context
                
        except Exception as e:
            logger.error(f"Error in Flask middleware before_request: {e}")
            # Ensure g has safe defaults even if there's an error
            g.platform_context = None
            g.flask_session_manager = self.flask_session_manager
    
    def after_request(self, response):
        """Clean up after request"""
        # Clean up any temporary context
        if hasattr(g, 'platform_context'):
            g.platform_context = None
        
        return response


def get_current_platform_context() -> Optional[Dict[str, Any]]:
    """
    Get the current platform context from Flask's g object
    
    Returns:
        Platform context dictionary or None
    """
    # First try to get from g object (set by middleware)
    context = getattr(g, 'platform_context', None)
    if context:
        return context
    
    # Fallback: try to get from session manager directly
    try:
        flask_session_manager = getattr(g, 'flask_session_manager', None)
        if flask_session_manager:
            return flask_session_manager.get_session_context()
    except Exception as e:
        logger.debug(f"Error in platform context fallback: {e}")
    
    return None


def get_current_platform() -> Optional[PlatformConnection]:
    """
    Get the current platform connection from context
    
    Returns:
        PlatformConnection object or None
    """
    context = get_current_platform_context()
    if context and context.get('platform_connection_id'):
        # Import here to avoid circular imports
        from database import DatabaseManager
        from config import Config
        
        db_manager = DatabaseManager(Config())
        db_session = db_manager.get_session()
        try:
            return db_session.query(PlatformConnection).filter_by(
                id=context['platform_connection_id'],
                is_active=True
            ).first()
        finally:
            db_session.close()
    return None


def get_current_user_from_context() -> Optional[User]:
    """
    Get the current user from platform context
    
    Returns:
        User object or None
    """
    context = get_current_platform_context()
    if context and context.get('user_id'):
        # Import here to avoid circular imports
        from database import DatabaseManager
        from config import Config
        
        db_manager = DatabaseManager(Config())
        db_session = db_manager.get_session()
        try:
            return db_session.query(User).filter_by(
                id=context['user_id'],
                is_active=True
            ).first()
        finally:
            db_session.close()
    return None


def switch_platform_context(platform_connection_id: int) -> bool:
    """
    Switch the current session's platform context
    
    Args:
        platform_connection_id: ID of platform to switch to
        
    Returns:
        True if successful, False otherwise
    """
    flask_session_manager = getattr(g, 'flask_session_manager', None)
    if not flask_session_manager:
        return False
    
    return flask_session_manager.update_platform_context(platform_connection_id)