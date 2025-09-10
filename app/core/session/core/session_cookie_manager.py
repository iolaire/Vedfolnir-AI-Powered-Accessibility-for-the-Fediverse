# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Cookie Management System

This module manages secure session cookies containing only session IDs.
It replaces Flask session cookies with minimal, secure cookies that reference
database sessions as the single source of truth.
"""

from logging import getLogger
from typing import Optional
from flask import request, Response
from datetime import timedelta

logger = getLogger(__name__)

class SessionCookieManager:
    """Manages secure session cookies containing only session ID"""
    
    def __init__(self, cookie_name: str = 'session_id', max_age: int = 86400, secure: bool = True):
        """
        Initialize session cookie manager
        
        Args:
            cookie_name: Name of the session cookie
            max_age: Cookie max age in seconds (default: 24 hours)
            secure: Whether to set secure flag (default: True)
        """
        self.cookie_name = cookie_name
        self.max_age = max_age
        self.secure = secure
    
    def set_session_cookie(self, response: Response, session_id: str) -> None:
        """
        Set secure session cookie with just the session ID
        
        Args:
            response: Flask response object
            session_id: Session ID to store in cookie
        """
        try:
            response.set_cookie(
                self.cookie_name,
                session_id,
                max_age=self.max_age,
                secure=self.secure,
                httponly=True,  # Prevent XSS access
                samesite='Lax',  # CSRF protection while allowing normal navigation
                path='/'  # Available for entire application
            )
            logger.debug(f"Set session cookie for session {session_id[:8]}...")
        except (ValueError, TypeError) as e:
            logger.error(f"Error setting session cookie: {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting session cookie: {e}")
            raise
    
    def get_session_id_from_cookie(self) -> Optional[str]:
        """
        Extract session ID from secure cookie
        
        Returns:
            Session ID if found, None otherwise
        """
        try:
            session_id = request.cookies.get(self.cookie_name)
            if session_id:
                logger.debug(f"Retrieved session ID from cookie: {session_id[:8]}...")
                return session_id
            else:
                logger.debug("No session cookie found")
                return None
        except Exception as e:
            logger.error(f"Error getting session ID from cookie: {e}")
            return None
    
    def clear_session_cookie(self, response: Response) -> None:
        """
        Clear session cookie
        
        Args:
            response: Flask response object
        """
        try:
            response.set_cookie(
                self.cookie_name,
                '',
                expires=0,
                secure=self.secure,
                httponly=True,
                samesite='Lax',
                path='/'
            )
            logger.debug("Cleared session cookie")
        except Exception as e:
            logger.error(f"Error clearing session cookie: {e}")
    
    def validate_cookie_security(self) -> bool:
        """
        Validate that cookie security settings are appropriate
        
        Returns:
            True if security settings are valid, False otherwise
        """
        # Check if secure flag is set appropriately
        if not self.secure:
            logger.warning("Session cookie secure flag is disabled - this should only be used in development")
        
        # Check max age is reasonable (not too long or too short)
        if self.max_age < 300:  # 5 minutes
            logger.warning("Session cookie max age is very short, may cause frequent re-authentication")
            return False
        
        if self.max_age > 604800:  # 7 days
            logger.warning("Session cookie max age is very long, may pose security risk")
            return False
        
        return True
    
    def refresh_session_cookie(self, response: Response, session_id: str) -> None:
        """
        Refresh session cookie with updated expiration
        
        Args:
            response: Flask response object
            session_id: Session ID to refresh
        """
        # Simply set the cookie again with new expiration
        self.set_session_cookie(response, session_id)
        logger.debug(f"Refreshed session cookie for session {session_id[:8]}...")

def create_session_cookie_manager(app_config: dict) -> SessionCookieManager:
    """
    Create session cookie manager from Flask app configuration
    
    Args:
        app_config: Flask app configuration dictionary
        
    Returns:
        Configured SessionCookieManager instance
    """
    # Extract configuration with defaults
    cookie_name = app_config.get('SESSION_COOKIE_NAME', 'session_id')
    max_age = int(app_config.get('PERMANENT_SESSION_LIFETIME', timedelta(days=1)).total_seconds())
    secure = app_config.get('SESSION_COOKIE_SECURE', True)
    
    # Create and validate cookie manager
    cookie_manager = SessionCookieManager(
        cookie_name=cookie_name,
        max_age=max_age,
        secure=secure
    )
    
    # Validate security settings
    # amazonq-ignore-next-line
    if not cookie_manager.validate_cookie_security():
        logger.warning("Session cookie security validation failed")
    
    from app.core.security.core.security_utils import sanitize_for_log
    logger.info(f"Created session cookie manager: {sanitize_for_log(cookie_name)}, max_age={sanitize_for_log(str(max_age))}, secure={sanitize_for_log(str(secure))}")
    return cookie_manager