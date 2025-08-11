#!/usr/bin/env python3

"""
Safe Template Context Processor

This module provides safe template context processing with error handling
for DetachedInstanceError and other database session issues. It ensures
templates never receive detached database objects.
"""

import logging
from typing import Dict, Any, Optional, List
from flask import current_app
from flask_login import current_user
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def safe_template_context() -> Dict[str, Any]:
    """
    Provide safe template context with error handling for database objects.
    
    This function ensures that templates receive safe, serialized data instead
    of potentially detached database objects. It handles DetachedInstanceError
    gracefully and provides fallback mechanisms.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 7.1, 7.2
    
    Returns:
        Dictionary containing safe template context variables
    """
    context = {
        'template_error': False,
        'current_user_safe': None,
        'user_platforms': [],
        'active_platform': None,
        'platform_count': 0
    }
    
    if not current_user.is_authenticated:
        return context
    
    try:
        # Get session manager and detached instance handler
        session_manager = getattr(current_app, 'request_session_manager', None)
        handler = getattr(current_app, 'detached_instance_handler', None)
        
        if not session_manager or not handler:
            logger.warning("Session manager or detached instance handler not available")
            context['template_error'] = True
            return context
        
        # Safely access current_user properties
        context['current_user_safe'] = _get_safe_user_data(current_user, handler)
        
        # Safely get user platforms
        platforms_data = _get_safe_platforms_data(current_user, handler, session_manager)
        context.update(platforms_data)
        
        logger.debug(f"Safe template context created for user {context['current_user_safe'].get('id')}")
        
    except DetachedInstanceError as e:
        logger.warning(f"DetachedInstanceError in template context: {e}")
        context['template_error'] = True
        _handle_detached_error_fallback(context, session_manager)
        
    except Exception as e:
        logger.error(f"Unexpected error in template context: {e}")
        context['template_error'] = True
    
    return context


def _get_safe_user_data(user, handler) -> Optional[Dict[str, Any]]:
    """
    Safely extract user data for template context.
    
    Args:
        user: Current user object
        handler: DetachedInstanceHandler instance
        
    Returns:
        Dictionary with safe user data or None
    """
    try:
        return {
            'id': handler.safe_access(user, 'id'),
            'username': handler.safe_access(user, 'username', 'Unknown'),
            'email': handler.safe_access(user, 'email', ''),
            'role': handler.safe_access(user, 'role', 'user'),
            'is_active': handler.safe_access(user, 'is_active', True)
        }
    except Exception as e:
        logger.error(f"Error getting safe user data: {e}")
        return {
            'id': None,
            'username': 'Unknown',
            'email': '',
            'role': 'user',
            'is_active': True
        }


def _get_safe_platforms_data(user, handler, session_manager) -> Dict[str, Any]:
    """
    Safely extract platform data for template context.
    
    Args:
        user: Current user object
        handler: DetachedInstanceHandler instance
        session_manager: RequestScopedSessionManager instance
        
    Returns:
        Dictionary with platform data
    """
    platforms_data = {
        'user_platforms': [],
        'active_platform': None,
        'platform_count': 0
    }
    
    try:
        # Try to get platforms through user object first
        platforms = handler.safe_relationship_access(user, 'platforms', [])
        
        if not platforms:
            # Fallback: query platforms directly from database
            platforms = _query_platforms_fallback(user, handler, session_manager)
        
        # Convert platforms to safe dictionaries
        safe_platforms = []
        active_platform = None
        
        for platform in platforms:
            try:
                platform_dict = _platform_to_safe_dict(platform, handler)
                if platform_dict:
                    safe_platforms.append(platform_dict)
                    
                    # Check if this is the active/default platform
                    if platform_dict.get('is_default') or (not active_platform and platform_dict.get('is_active')):
                        active_platform = platform_dict
                        
            except Exception as e:
                logger.warning(f"Error converting platform to dict: {e}")
                continue
        
        platforms_data.update({
            'user_platforms': safe_platforms,
            'active_platform': active_platform,
            'platform_count': len(safe_platforms)
        })
        
        logger.debug(f"Retrieved {len(safe_platforms)} platforms for template context")
        
    except Exception as e:
        logger.error(f"Error getting safe platforms data: {e}")
    
    return platforms_data


def _platform_to_safe_dict(platform, handler) -> Optional[Dict[str, Any]]:
    """
    Convert platform object to safe dictionary.
    
    Args:
        platform: PlatformConnection object
        handler: DetachedInstanceHandler instance
        
    Returns:
        Safe dictionary representation or None
    """
    try:
        # Try to use platform's to_dict method if available
        if hasattr(platform, 'to_dict') and callable(getattr(platform, 'to_dict')):
            try:
                return platform.to_dict()
            except DetachedInstanceError:
                # Fall through to manual extraction
                pass
        
        # Manual extraction using safe access
        return {
            'id': handler.safe_access(platform, 'id'),
            'name': handler.safe_access(platform, 'name', 'Unknown Platform'),
            'platform_type': handler.safe_access(platform, 'platform_type', 'unknown'),
            'instance_url': handler.safe_access(platform, 'instance_url', ''),
            'username': handler.safe_access(platform, 'username', ''),
            'is_active': handler.safe_access(platform, 'is_active', True),
            'is_default': handler.safe_access(platform, 'is_default', False),
            'created_at': handler.safe_access(platform, 'created_at'),
            'updated_at': handler.safe_access(platform, 'updated_at')
        }
        
    except Exception as e:
        logger.error(f"Error converting platform to safe dict: {e}")
        return None


def _query_platforms_fallback(user, handler, session_manager) -> List:
    """
    Fallback method to query platforms directly from database.
    
    Args:
        user: Current user object
        handler: DetachedInstanceHandler instance
        session_manager: RequestScopedSessionManager instance
        
    Returns:
        List of platform objects
    """
    try:
        # Import here to avoid circular imports
        from models import PlatformConnection
        
        session = session_manager.get_request_session()
        user_id = handler.safe_access(user, 'id')
        
        if user_id:
            platforms = session.query(PlatformConnection).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            logger.debug(f"Fallback query retrieved {len(platforms)} platforms")
            return platforms
            
    except Exception as e:
        logger.error(f"Error in platforms fallback query: {e}")
    
    return []


def _handle_detached_error_fallback(context: Dict[str, Any], session_manager) -> None:
    """
    Handle DetachedInstanceError by providing minimal fallback data.
    
    Args:
        context: Template context dictionary to update
        session_manager: RequestScopedSessionManager instance
    """
    try:
        # Try to get minimal user info from session or other sources
        if hasattr(current_user, 'get_id') and current_user.get_id():
            context['current_user_safe'] = {
                'id': current_user.get_id(),
                'username': 'User',
                'email': '',
                'role': 'user',
                'is_active': True
            }
        
        logger.info("Applied fallback template context due to DetachedInstanceError")
        
    except Exception as e:
        logger.error(f"Error in detached error fallback: {e}")
    
    # Always clear platform data since we can't safely access it during fallback
    context.update({
        'user_platforms': [],
        'active_platform': None,
        'platform_count': 0
    })


def create_safe_template_context_processor(app):
    """
    Register the safe template context processor with Flask app.
    
    Args:
        app: Flask application instance
    """
    @app.context_processor
    def inject_safe_context():
        """Inject safe template context into all templates"""
        return safe_template_context()
    
    logger.info("Safe template context processor registered")


def get_safe_user_context(user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get safe user context for a specific user (utility function).
    
    Args:
        user_id: Optional user ID, defaults to current_user
        
    Returns:
        Safe user context dictionary
    """
    if user_id is None and current_user.is_authenticated:
        return safe_template_context()
    
    if user_id is None:
        return {
            'template_error': False,
            'current_user_safe': None,
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }
    
    try:
        # Import here to avoid circular imports
        from models import User
        
        session_manager = getattr(current_app, 'request_session_manager', None)
        handler = getattr(current_app, 'detached_instance_handler', None)
        
        if not session_manager or not handler:
            raise RuntimeError("Session manager or handler not available")
        
        session = session_manager.get_request_session()
        user = session.query(User).get(user_id)
        
        if not user:
            return {
                'template_error': True,
                'current_user_safe': None,
                'user_platforms': [],
                'active_platform': None,
                'platform_count': 0
            }
        
        context = {
            'template_error': False,
            'current_user_safe': _get_safe_user_data(user, handler),
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }
        
        platforms_data = _get_safe_platforms_data(user, handler, session_manager)
        context.update(platforms_data)
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting safe user context for user {user_id}: {e}")
        return {
            'template_error': True,
            'current_user_safe': None,
            'user_platforms': [],
            'active_platform': None,
            'platform_count': 0
        }