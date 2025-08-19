# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Session Middleware Helper Functions

This module provides helper functions for Redis session management,
replacing the database_session_middleware functions with Redis-compatible versions.
"""

from typing import Optional, Dict, Any
from flask import g, current_app, request
from logging import getLogger

logger = getLogger(__name__)

def get_current_session_context() -> Optional[Dict[str, Any]]:
    """
    Get current session context with enriched user and platform information
    
    Returns:
        Session context dictionary with user_info and platform_info, or None if no session
    """
    # First try to get from g object (set by middleware)
    context = getattr(g, 'session_context', None)
    if context:
        return context
    
    # Fallback: get from Redis session manager and enrich it
    try:
        session_id = get_current_session_id()
        if session_id:
            unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            if unified_session_manager:
                context = unified_session_manager.get_session_context(session_id)
                if context:
                    # Enrich context with user and platform information
                    enriched_context = _enrich_session_context(context)
                    # Cache in g object for this request
                    g.session_context = enriched_context
                    return enriched_context
    except Exception as e:
        logger.debug(f"Error getting session context from Redis: {e}")
    
    return None

def _enrich_session_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich session context with user and platform information
    
    Args:
        context: Raw session context from Redis
        
    Returns:
        Enriched context with user_info and platform_info
    """
    enriched = context.copy()
    
    try:
        user_id = context.get('user_id')
        platform_connection_id = context.get('platform_connection_id')
        
        # Try to get database manager from current_app first
        db_manager = getattr(current_app, 'db_manager', None)
        
        # If not available, try to create one
        if not db_manager:
            try:
                from config import Config
                from database import DatabaseManager
                config = Config()
                db_manager = DatabaseManager(config)
            except Exception as e:
                logger.warning(f"Could not create database manager for session enrichment: {e}")
                return enriched
        
        # Get user information
        if user_id:
            session = db_manager.get_session()
            try:
                from models import User, PlatformConnection
                user = session.query(User).filter_by(id=user_id).first()
                if user:
                    enriched['user_info'] = {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role.value if hasattr(user.role, 'value') else str(user.role)
                    }
                
                # Get platform information
                if platform_connection_id:
                    platform = session.query(PlatformConnection).filter_by(
                        id=platform_connection_id,
                        user_id=user_id
                    ).first()
                    if platform:
                        enriched['platform_info'] = {
                            'id': platform.id,
                            'name': platform.name,
                            'platform_type': platform.platform_type,
                            'instance_url': platform.instance_url,
                            'username': platform.username,
                            'is_active': platform.is_active
                        }
                
            finally:
                db_manager.close_session(session)
                
    except Exception as e:
        logger.error(f"Error enriching session context: {e}")
    
    return enriched

def get_current_session_id() -> Optional[str]:
    """
    Get current Redis session ID from session cookie or g object
    
    Returns:
        Redis session ID or None if no session (never returns Flask session IDs)
    """
    # First try to get from g object (if already cached this request)
    session_id = getattr(g, 'session_id', None)
    if session_id:
        # Verify this is not a Flask session ID
        if session_id.startswith('.eJ') or session_id.startswith('eyJ'):
            logger.warning(f"Detected Flask session ID in g.session_id: {session_id[:20]}... - clearing it")
            g.session_id = None
            return None
        return session_id
    
    # Get from session cookie
    try:
        session_cookie_manager = getattr(current_app, 'session_cookie_manager', None)
        if session_cookie_manager:
            session_id = session_cookie_manager.get_session_id_from_cookie()
            if session_id:
                # Verify this is not a Flask session ID
                if session_id.startswith('.eJ') or session_id.startswith('eyJ'):
                    logger.warning(f"Detected Flask session ID in cookie: {session_id[:20]}... - ignoring it")
                    return None
                # Cache in g object for this request
                g.session_id = session_id
                return session_id
    except Exception as e:
        logger.debug(f"Error getting session ID from cookie: {e}")
    
    return None

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
    Update current session's platform context using Redis session manager
    
    Args:
        platform_id: New platform connection ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = get_current_session_id()
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        
        if session_id and unified_session_manager:
            # Update platform context in Redis
            success = unified_session_manager.update_platform_context(session_id, platform_id)
            if success:
                # Reload session context to reflect the change
                updated_context = unified_session_manager.get_session_context(session_id)
                if updated_context:
                    g.session_context = updated_context
                    logger.info(f"Updated session {session_id} platform context to {platform_id}")
                return True
            else:
                logger.warning(f"Failed to update session {session_id} platform context to {platform_id}")
                return False
        else:
            logger.warning("No session ID or session manager available for platform update")
            return False
            
    except Exception as e:
        logger.error(f"Error updating session platform context: {e}")
        return False

def create_user_session(user_id: int, platform_connection_id: Optional[int] = None) -> Optional[str]:
    """
    Create a new user session using Redis session manager
    
    Args:
        user_id: User ID
        platform_connection_id: Optional platform connection ID
        
    Returns:
        Session ID if successful, None otherwise
    """
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if unified_session_manager:
            session_id = unified_session_manager.create_session(user_id, platform_connection_id)
            if session_id:
                # Cache session ID in g object for this request
                g.session_id = session_id
                logger.info(f"Created new session {session_id} for user {user_id}")
                return session_id
        return None
    except Exception as e:
        logger.error(f"Error creating user session: {e}")
        return None

def destroy_current_session() -> bool:
    """
    Destroy the current session using Redis session manager
    
    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = get_current_session_id()
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        
        if session_id and unified_session_manager:
            success = unified_session_manager.destroy_session(session_id)
            if success:
                # Clear cached session data
                if hasattr(g, 'session_id'):
                    delattr(g, 'session_id')
                if hasattr(g, 'session_context'):
                    delattr(g, 'session_context')
                logger.info(f"Destroyed session {session_id}")
                return True
        return False
    except Exception as e:
        logger.error(f"Error destroying current session: {e}")
        return False

def validate_current_session() -> bool:
    """
    Validate the current session using Redis session manager
    
    Returns:
        True if session is valid, False otherwise
    """
    try:
        session_id = get_current_session_id()
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        
        if session_id and unified_session_manager:
            return unified_session_manager.validate_session(session_id)
        return False
    except Exception as e:
        logger.debug(f"Error validating current session: {e}")
        return False

def update_session_activity() -> bool:
    """
    Update current session activity timestamp using Redis session manager
    
    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = get_current_session_id()
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        
        if session_id and unified_session_manager:
            return unified_session_manager.update_session_activity(session_id)
        return False
    except Exception as e:
        logger.debug(f"Error updating session activity: {e}")
        return False

def clear_session_platform() -> bool:
    """
    Clear platform context from current session using Redis session manager
    
    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = get_current_session_id()
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        
        if session_id and unified_session_manager:
            # Update platform context to None/0 to clear it
            success = unified_session_manager.update_platform_context(session_id, None)
            if success:
                # Clear cached session data
                if hasattr(g, 'session_context'):
                    delattr(g, 'session_context')
                logger.info(f"Cleared platform context for session {session_id}")
                return True
        return False
    except Exception as e:
        logger.error(f"Error clearing session platform context: {e}")
        return False

def get_session_created_at() -> Optional[str]:
    """
    Get session creation timestamp from Redis session manager
    
    Returns:
        ISO timestamp string or None if not available
    """
    try:
        context = get_current_session_context()
        return context.get('created_at') if context else None
    except Exception as e:
        logger.debug(f"Error getting session created_at: {e}")
        return None

def get_session_last_activity() -> Optional[str]:
    """
    Get session last activity timestamp from Redis session manager
    
    Returns:
        ISO timestamp string or None if not available
    """
    try:
        context = get_current_session_context()
        return context.get('last_activity') if context else None
    except Exception as e:
        logger.debug(f"Error getting session last_activity: {e}")
        return None

# Compatibility class for tests
class DatabaseSessionMiddleware:
    """
    Compatibility class for tests that expect DatabaseSessionMiddleware
    This is deprecated - use Redis session middleware functions directly
    """
    def __init__(self, app, session_manager, cookie_manager):
        self.app = app
        self.session_manager = session_manager
        self.cookie_manager = cookie_manager
        logger.warning("DatabaseSessionMiddleware compatibility class is deprecated. Use Redis session middleware functions directly.")
    
    def init_app(self, app):
        """Initialize app - no-op for compatibility"""
        pass
