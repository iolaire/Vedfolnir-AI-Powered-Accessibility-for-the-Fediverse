# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Detection Utility

This module provides utilities to detect previous user sessions based on various
session indicators including Flask-Login remember tokens, session data, and custom cookies.
"""

import logging
from typing import Optional, Dict, Any, List
from flask import request, session, current_app
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SessionDetectionResult:
    """Result object for session detection"""
    
    def __init__(self, has_previous_session: bool = False, 
                 detection_methods: Optional[List[str]] = None,
                 session_indicators: Optional[Dict[str, Any]] = None):
        self.has_previous_session = has_previous_session
        self.detection_methods = detection_methods or []
        self.session_indicators = session_indicators or {}
    
    def __bool__(self):
        """Allow boolean evaluation of the result"""
        return self.has_previous_session
    
    def __repr__(self):
        return f"SessionDetectionResult(has_previous_session={self.has_previous_session}, methods={self.detection_methods})"

def has_previous_session() -> bool:
    """
    Detect if user has previously logged in based on session indicators.
    
    This function checks for various session indicators to determine if a user
    has previously authenticated with the application:
    
    1. Flask-Login remember me tokens
    2. Flask session data indicating previous authentication
    3. Redis session data
    4. Custom session tracking cookies
    
    Returns:
        Boolean indicating if user has previous session indicators
    """
    result = detect_previous_session()
    return result.has_previous_session

def detect_previous_session() -> SessionDetectionResult:
    """
    Comprehensive session detection with detailed results.
    
    Performs detailed analysis of various session indicators and returns
    comprehensive information about detected session state.
    
    Returns:
        SessionDetectionResult object with detection details
    """
    detection_methods = []
    session_indicators = {}
    
    try:
        # Check for Flask-Login remember me token
        remember_token = _check_flask_login_remember_token()
        if remember_token:
            detection_methods.append("flask_login_remember_token")
            session_indicators["remember_token"] = remember_token
        
        # Check Flask session data
        flask_session_data = _check_flask_session_data()
        if flask_session_data:
            detection_methods.append("flask_session_data")
            session_indicators["flask_session"] = flask_session_data
        
        # Check Redis session data
        redis_session_data = _check_redis_session_data()
        if redis_session_data:
            detection_methods.append("redis_session_data")
            session_indicators["redis_session"] = redis_session_data
        
        # Check custom session tracking cookies
        custom_cookies = _check_custom_session_cookies()
        if custom_cookies:
            detection_methods.append("custom_session_cookies")
            session_indicators["custom_cookies"] = custom_cookies
        
        # Check for session ID in current Flask session
        session_id_data = _check_session_id_indicators()
        if session_id_data:
            detection_methods.append("session_id_indicators")
            session_indicators["session_id"] = session_id_data
        
        has_previous = len(detection_methods) > 0
        
        if has_previous:
            logger.debug(f"Previous session detected via methods: {detection_methods}")
        else:
            logger.debug("No previous session indicators found")
        
        return SessionDetectionResult(
            has_previous_session=has_previous,
            detection_methods=detection_methods,
            session_indicators=session_indicators
        )
        
    except Exception as e:
        logger.error(f"Error during session detection: {e}")
        # Return safe default - no previous session detected
        return SessionDetectionResult(has_previous_session=False)

def _check_flask_login_remember_token() -> Optional[Dict[str, Any]]:
    """
    Check for Flask-Login remember me token in cookies.
    
    Flask-Login stores remember me tokens in cookies with names like:
    - remember_token
    - session (with remember flag)
    
    Returns:
        Dictionary with token information if found, None otherwise
    """
    try:
        # Check for standard Flask-Login remember token cookie
        remember_token = request.cookies.get('remember_token')
        if remember_token:
            return {
                'token': remember_token[:10] + "..." if len(remember_token) > 10 else remember_token,
                'source': 'remember_token_cookie'
            }
        
        # Check for Flask session cookie with remember flag
        session_cookie = request.cookies.get('session')
        if session_cookie and len(session_cookie) > 20:  # Valid session cookies are typically longer
            return {
                'token': session_cookie[:10] + "...",
                'source': 'session_cookie'
            }
        
        return None
        
    except Exception as e:
        logger.debug(f"Error checking Flask-Login remember token: {e}")
        return None

def _check_flask_session_data() -> Optional[Dict[str, Any]]:
    """
    Check Flask session for previous authentication indicators.
    
    Looks for session data that indicates previous authentication:
    - user_id
    - _user_id (Flask-Login internal)
    - username
    - last_login timestamps
    
    Returns:
        Dictionary with session data if found, None otherwise
    """
    try:
        session_data = {}
        
        # Check for user ID indicators
        user_id = session.get('user_id')
        _user_id = session.get('_user_id')  # Flask-Login internal
        
        if user_id:
            session_data['user_id'] = user_id
        
        if _user_id:
            session_data['_user_id'] = _user_id
        
        # Check for username
        username = session.get('username')
        if username:
            session_data['username'] = username
        
        # Check for authentication timestamps
        last_activity = session.get('last_activity')
        if last_activity:
            session_data['last_activity'] = last_activity
        
        created_at = session.get('created_at')
        if created_at:
            session_data['created_at'] = created_at
        
        # Check for platform connection data (indicates active session)
        platform_connection_id = session.get('platform_connection_id')
        if platform_connection_id:
            session_data['platform_connection_id'] = platform_connection_id
        
        # Check for CSRF token (indicates active session)
        csrf_token = session.get('csrf_token')
        if csrf_token:
            session_data['has_csrf_token'] = True
        
        return session_data if session_data else None
        
    except Exception as e:
        logger.debug(f"Error checking Flask session data: {e}")
        return None

def _check_redis_session_data() -> Optional[Dict[str, Any]]:
    """
    Check Redis for active session data.
    
    Attempts to find active Redis sessions that might indicate
    previous authentication.
    
    Returns:
        Dictionary with Redis session info if found, None otherwise
    """
    try:
        # Get session manager from app
        session_manager = getattr(current_app, 'session_manager', None)
        if not session_manager:
            return None
        
        # Check if we have a session ID in Flask session
        session_id = getattr(session, 'sid', None) if hasattr(session, 'sid') else None
        
        if session_id and hasattr(session_manager, 'get_session_data'):
            # Try to get session data from Redis
            redis_data = session_manager.get_session_data(session_id)
            if redis_data:
                return {
                    'session_id': session_id,
                    'has_user_id': 'user_id' in redis_data,
                    'has_platform_data': 'platform_connection_id' in redis_data,
                    'last_updated': redis_data.get('_last_updated')
                }
        
        return None
        
    except Exception as e:
        logger.debug(f"Error checking Redis session data: {e}")
        return None

def _check_custom_session_cookies() -> Optional[Dict[str, Any]]:
    """
    Check for custom session tracking cookies.
    
    Looks for application-specific cookies that might indicate
    previous sessions:
    - vedfolnir_returning_user
    - vedfolnir_last_visit
    - platform_preference cookies
    
    Returns:
        Dictionary with custom cookie data if found, None otherwise
    """
    try:
        custom_cookies = {}
        
        # Check for returning user cookie
        returning_user = request.cookies.get('vedfolnir_returning_user')
        if returning_user:
            custom_cookies['returning_user'] = returning_user
        
        # Check for last visit timestamp
        last_visit = request.cookies.get('vedfolnir_last_visit')
        if last_visit:
            custom_cookies['last_visit'] = last_visit
        
        # Check for platform preference cookies
        platform_pref = request.cookies.get('vedfolnir_platform_preference')
        if platform_pref:
            custom_cookies['platform_preference'] = platform_pref
        
        # Check for any cookies with vedfolnir prefix
        for cookie_name, cookie_value in request.cookies.items():
            if cookie_name.startswith('vedfolnir_') and cookie_name not in ['vedfolnir_returning_user', 'vedfolnir_last_visit', 'vedfolnir_platform_preference']:
                custom_cookies[cookie_name] = cookie_value[:20] + "..." if len(cookie_value) > 20 else cookie_value
        
        return custom_cookies if custom_cookies else None
        
    except Exception as e:
        logger.debug(f"Error checking custom session cookies: {e}")
        return None

def _check_session_id_indicators() -> Optional[Dict[str, Any]]:
    """
    Check for session ID indicators in various locations.
    
    Looks for session identifiers that might indicate active or
    previous sessions.
    
    Returns:
        Dictionary with session ID data if found, None otherwise
    """
    try:
        session_id_data = {}
        
        # Check Flask session for session ID
        if hasattr(session, 'sid') and session.sid:
            session_id_data['flask_session_id'] = session.sid
        
        # Check for session ID in session data
        session_id_from_data = session.get('session_id')
        if session_id_from_data:
            session_id_data['session_data_id'] = session_id_from_data
        
        # Check if session is marked as permanent (indicates remember me)
        if hasattr(session, 'permanent') and session.permanent:
            session_id_data['is_permanent'] = True
        
        return session_id_data if session_id_data else None
        
    except Exception as e:
        logger.debug(f"Error checking session ID indicators: {e}")
        return None

def clear_session_indicators() -> bool:
    """
    Clear all session indicators for testing purposes.
    
    This function clears various session indicators to simulate
    a completely new user state. Useful for testing.
    
    Returns:
        True if clearing was successful, False otherwise
    """
    try:
        # Clear Flask session
        session.clear()
        
        # Note: We cannot clear cookies from server side, but we can
        # document what cookies should be cleared for testing
        logger.debug("Session indicators cleared (Flask session only)")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing session indicators: {e}")
        return False

def get_session_detection_summary() -> Dict[str, Any]:
    """
    Get a summary of current session detection state.
    
    Provides a comprehensive overview of all session indicators
    for debugging and monitoring purposes.
    
    Returns:
        Dictionary with session detection summary
    """
    try:
        result = detect_previous_session()
        
        return {
            'has_previous_session': result.has_previous_session,
            'detection_methods': result.detection_methods,
            'method_count': len(result.detection_methods),
            'session_indicators': result.session_indicators,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_info': {
                'has_cookies': len(request.cookies) > 0,
                'cookie_count': len(request.cookies),
                'has_flask_session': len(session) > 0,
                'flask_session_keys': list(session.keys()) if session else []
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating session detection summary: {e}")
        return {
            'has_previous_session': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }