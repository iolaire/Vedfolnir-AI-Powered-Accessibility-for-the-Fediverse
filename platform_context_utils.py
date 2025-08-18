# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Context Utilities

Provides utilities to ensure platform context is consistently available throughout the application.
"""

from typing import Optional, Dict, Any, Tuple
from flask import g
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def ensure_platform_context(db_manager, session_manager) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Ensure platform context is available, creating it if necessary.
    
    Args:
        db_manager: Database manager instance
        session_manager: Session manager instance
        
    Returns:
        Tuple of (platform_context, was_created)
        - platform_context: Dictionary with platform context or None
        - was_created: Boolean indicating if context was newly created
    """
    from models import PlatformConnection
    from security.core.security_utils import sanitize_for_log
    
    # First try to get existing context
    context = getattr(g, 'platform_context', None)
    if context and context.get('platform_connection_id'):
        return context, False
    
    # Check if user is authenticated
    if not current_user or not current_user.is_authenticated:
        return None, False
    
    try:
        # Get session ID from database session context
        from database_session_middleware import get_current_session_id
        session_id = get_current_session_id()
        
        # Get user's platforms
        db_session = db_manager.get_session()
        try:
            user_id = getattr(current_user, 'id', None)
            if not user_id:
                return []
                
            user_platforms = db_session.query(PlatformConnection).filter_by(
                user_id=user_id,
                is_active=True
            ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
            
            if not user_platforms:
                logger.warning(f"No active platforms found for user {sanitize_for_log(current_user.username)}")
                return None, False
            
            # Get default platform
            default_platform = next((p for p in user_platforms if p.is_default), user_platforms[0])
            
            # Create or update session context
            if flask_session_id:
                # Update existing session
                success = session_manager.update_platform_context(flask_session_id, default_platform.id)
                if not success:
                    logger.error(f"Failed to update session context for user {sanitize_for_log(current_user.username)}")
                    return None, False
            else:
                # Create new session using unified session manager from app context
                from flask import current_app
                unified_session_manager = getattr(current_app, 'unified_session_manager', None)
                if not unified_session_manager:
                    # Fallback: create new instance
                    from unified_session_manager import UnifiedSessionManager
                    unified_session_manager = UnifiedSessionManager(db_manager)
                
                session_id = unified_session_manager.create_session(user_id, default_platform.id)
                
                if session_id:
                    # Set session cookie
                    from flask import make_response, request
                    from session_cookie_manager import create_session_cookie_manager
                    cookie_manager = create_session_cookie_manager({})
                    # Note: This would need to be handled in a response context
            
            # Get the updated context
            context = session_manager.get_session_context(flask_session_id)
            if context:
                # Set in g for current request
                g.platform_context = context
                logger.info(f"Created platform context for user {sanitize_for_log(current_user.username)} with platform {sanitize_for_log(default_platform.name)}")
                return context, True
            else:
                logger.error(f"Failed to retrieve created session context for user {sanitize_for_log(current_user.username)}")
                return None, False
                
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error ensuring platform context: {e}")
        return None, False

def get_platform_context_with_fallback(db_manager, session_manager) -> Optional[Dict[str, Any]]:
    """
    Get platform context with automatic fallback and creation if needed.
    
    Args:
        db_manager: Database manager instance
        session_manager: Session manager instance
        
    Returns:
        Platform context dictionary or None
    """
    context, was_created = ensure_platform_context(db_manager, session_manager)
    return context

def validate_platform_context(context: Optional[Dict[str, Any]], db_manager) -> bool:
    """
    Validate that a platform context is still valid.
    
    Args:
        context: Platform context dictionary
        db_manager: Database manager instance
        
    Returns:
        True if context is valid, False otherwise
    """
    if not context or not context.get('platform_connection_id'):
        return False
    
    if not current_user or not current_user.is_authenticated:
        return False
    
    try:
        from models import PlatformConnection
        
        db_session = db_manager.get_session()
        try:
            user_id = getattr(current_user, 'id', None)
            if not user_id:
                return None
                
            platform = db_session.query(PlatformConnection).filter_by(
                id=context['platform_connection_id'],
                user_id=user_id,
                is_active=True
            ).first()
            
            return platform is not None
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error validating platform context: {e}")
        return False

def refresh_platform_context(db_manager, session_manager) -> Optional[Dict[str, Any]]:
    """
    Force refresh of platform context from database.
    
    Args:
        db_manager: Database manager instance
        session_manager: Session manager instance
        
    Returns:
        Refreshed platform context or None
    """
    try:
        from database_session_middleware import get_current_session_id
        session_id = get_current_session_id()
        if not session_id:
            return ensure_platform_context(db_manager, session_manager)[0]
        
        # Get fresh context from session manager
        context = session_manager.get_session_context(flask_session_id)
        if context:
            # Validate the context
            if validate_platform_context(context, db_manager):
                g.platform_context = context
                return context
            else:
                # Context is invalid, recreate it
                return ensure_platform_context(db_manager, session_manager)[0]
        else:
            # No context found, create it
            return ensure_platform_context(db_manager, session_manager)[0]
            
    except Exception as e:
        logger.error(f"Error refreshing platform context: {e}")
        return None

def get_current_platform_dict(context: Optional[Dict[str, Any]], db_manager) -> Optional[Dict[str, Any]]:
    """
    Get current platform as a dictionary from context.
    
    Args:
        context: Platform context dictionary
        db_manager: Database manager instance
        
    Returns:
        Platform dictionary or None
    """
    if not context or not context.get('platform_connection_id'):
        return None
    
    try:
        from models import PlatformConnection
        
        db_session = db_manager.get_session()
        try:
            platform = db_session.query(PlatformConnection).filter_by(
                id=context['platform_connection_id'],
                is_active=True
            ).first()
            
            if platform:
                return {
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type,
                    'instance_url': platform.instance_url,
                    'username': platform.username,
                    'is_default': platform.is_default,
                    'is_active': platform.is_active
                }
            
            return None
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error getting current platform dict: {e}")
        return None