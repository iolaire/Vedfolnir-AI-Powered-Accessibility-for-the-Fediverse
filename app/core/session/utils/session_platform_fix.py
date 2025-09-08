#!/usr/bin/env python3
"""
Session Platform Fix

This module provides an improved implementation of platform session management
to fix the issue where platform data is lost between page transitions.

The main issues identified:
1. Flask session updates might not be immediately persisted
2. g.session_context updates don't persist across requests
3. Race conditions between Redis session manager and Flask session interface

Solution:
1. Ensure Flask session is marked as modified to trigger save
2. Force session save if needed
3. Add validation to ensure platform data is properly stored
4. Add debugging and logging
"""

from typing import Optional, Dict, Any
from flask import session, g, request, current_app
from datetime import datetime
from logging import getLogger

logger = getLogger(__name__)

def update_session_platform_fixed(platform_connection_id: int) -> bool:
    """
    Improved platform session update with better error handling and validation
    
    Args:
        platform_connection_id: New platform connection ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting platform update to {platform_connection_id}")
        
        # Get current session ID
        from session_middleware_v2 import get_current_session_id
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

def validate_platform_session(expected_platform_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Validate current platform session state
    
    Args:
        expected_platform_id: Expected platform connection ID (optional)
        
    Returns:
        Dictionary with validation results
    """
    result = {
        'valid': False,
        'flask_session_platform': None,
        'g_context_platform': None,
        'redis_session_platform': None,
        'errors': []
    }
    
    try:
        # Check Flask session
        flask_platform_id = session.get('platform_connection_id')
        result['flask_session_platform'] = flask_platform_id
        
        # Check g.session_context
        if hasattr(g, 'session_context') and g.session_context:
            g_platform_id = g.session_context.get('platform_connection_id')
            result['g_context_platform'] = g_platform_id
        else:
            result['errors'].append("g.session_context not available")
        
        # Check Redis session
        try:
            from session_middleware_v2 import get_current_session_id
            session_id = get_current_session_id()
            if session_id:
                session_manager = getattr(current_app, 'session_manager', None)
                if session_manager:
                    session_data = session_manager.get_session_data(session_id)
                    if session_data:
                        redis_platform_id = session_data.get('platform_connection_id')
                        result['redis_session_platform'] = redis_platform_id
                    else:
                        result['errors'].append("No Redis session data found")
                else:
                    result['errors'].append("No session manager found")
            else:
                result['errors'].append("No current session ID")
        except Exception as e:
            result['errors'].append(f"Redis session check failed: {e}")
        
        # Validate consistency
        platforms = [
            result['flask_session_platform'],
            result['g_context_platform'],
            result['redis_session_platform']
        ]
        
        # Remove None values for comparison
        non_none_platforms = [p for p in platforms if p is not None]
        
        if not non_none_platforms:
            result['errors'].append("No platform data found in any session store")
        elif len(set(non_none_platforms)) > 1:
            result['errors'].append(f"Platform data inconsistent across stores: {platforms}")
        elif expected_platform_id and non_none_platforms[0] != expected_platform_id:
            result['errors'].append(f"Platform data {non_none_platforms[0]} doesn't match expected {expected_platform_id}")
        else:
            result['valid'] = True
        
    except Exception as e:
        result['errors'].append(f"Validation error: {e}")
    
    return result

def debug_session_state() -> Dict[str, Any]:
    """
    Get detailed debug information about current session state
    
    Returns:
        Dictionary with debug information
    """
    debug_info = {
        'timestamp': str(datetime.now()),
        'flask_session_data': dict(session),
        'g_session_context': getattr(g, 'session_context', None),
        'session_id': None,
        'redis_session_data': None,
        'errors': []
    }
    
    try:
        from session_middleware_v2 import get_current_session_id
        session_id = get_current_session_id()
        debug_info['session_id'] = session_id
        
        if session_id:
            session_manager = getattr(current_app, 'session_manager', None)
            if session_manager:
                redis_data = session_manager.get_session_data(session_id)
                debug_info['redis_session_data'] = redis_data
            else:
                debug_info['errors'].append("No session manager found")
        else:
            debug_info['errors'].append("No current session ID")
            
    except Exception as e:
        debug_info['errors'].append(f"Debug error: {e}")
    
    return debug_info
