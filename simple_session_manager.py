# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simplified Session Management

This module provides simplified session management functions that work with
the Flask-Redis session system for user authentication and platform context.
"""

import redis
from flask import session, current_app, g
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """Simplified session manager for user authentication and platform context"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or self._get_redis_client()
    
    def _get_redis_client(self):
        """Get Redis client from app or create new one"""
        if hasattr(current_app, 'redis_client'):
            return current_app.redis_client
        
        import os
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)
    
    def login_user(self, user_id: int, platform_id: Optional[int] = None) -> bool:
        """Log in a user and optionally set platform context"""
        try:
            session['user_id'] = user_id
            session['logged_in'] = True
            session['login_time'] = datetime.now(timezone.utc).isoformat()
            
            if platform_id:
                session['platform_connection_id'] = platform_id
            
            session.permanent = True
            
            logger.info(f"User {user_id} logged in successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to login user {user_id}: {e}")
            return False
    
    def logout_user(self) -> bool:
        """Log out the current user"""
        try:
            user_id = session.get('user_id')
            
            # Clear all session data
            session.clear()
            
            logger.info(f"User {user_id} logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to logout user: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return session.get('logged_in', False) and session.get('user_id') is not None
    
    def get_user_id(self) -> Optional[int]:
        """Get current user ID"""
        return session.get('user_id')
    
    def set_platform_context(self, platform_id: int) -> bool:
        """Set the current platform context"""
        try:
            session['platform_connection_id'] = platform_id
            session['platform_switch_time'] = datetime.now(timezone.utc).isoformat()
            
            logger.debug(f"Platform context set to {platform_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set platform context: {e}")
            return False
    
    def get_platform_context(self) -> Optional[int]:
        """Get current platform context"""
        return session.get('platform_connection_id')
    
    def clear_platform_context(self) -> bool:
        """Clear platform context"""
        try:
            session.pop('platform_connection_id', None)
            session.pop('platform_switch_time', None)
            
            logger.debug("Platform context cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear platform context: {e}")
            return False
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get all session data"""
        return dict(session)
    
    def set_session_data(self, key: str, value: Any) -> bool:
        """Set session data"""
        try:
            session[key] = value
            return True
        except Exception as e:
            logger.error(f"Failed to set session data {key}: {e}")
            return False
    
    def get_session_data_item(self, key: str, default=None) -> Any:
        """Get session data item"""
        return session.get(key, default)
    
    def remove_session_data_item(self, key: str) -> bool:
        """Remove session data item"""
        try:
            session.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Failed to remove session data {key}: {e}")
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        return {
            'user_id': self.get_user_id(),
            'logged_in': self.is_logged_in(),
            'platform_id': self.get_platform_context(),
            'login_time': session.get('login_time'),
            'platform_switch_time': session.get('platform_switch_time'),
            'session_keys': list(session.keys())
        }

# Global session manager instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

# Convenience functions
def login_user(user_id: int, platform_id: Optional[int] = None) -> bool:
    """Log in a user"""
    return get_session_manager().login_user(user_id, platform_id)

def logout_user() -> bool:
    """Log out current user"""
    return get_session_manager().logout_user()

def is_logged_in() -> bool:
    """Check if user is logged in"""
    return get_session_manager().is_logged_in()

def get_current_user_id() -> Optional[int]:
    """Get current user ID"""
    return get_session_manager().get_user_id()

def set_platform_context(platform_id: int) -> bool:
    """Set platform context"""
    return get_session_manager().set_platform_context(platform_id)

def get_platform_context() -> Optional[int]:
    """Get platform context"""
    return get_session_manager().get_platform_context()

def clear_platform_context() -> bool:
    """Clear platform context"""
    return get_session_manager().clear_platform_context()

def get_session_info() -> Dict[str, Any]:
    """Get session information"""
    return get_session_manager().get_session_info()

# Flask-Login integration helpers
def get_current_user_from_session(db_manager):
    """Get current user object from session using database"""
    user_id = get_current_user_id()
    if not user_id:
        return None
    
    try:
        session = db_manager.get_session()
        try:
            from models import User
            from sqlalchemy.orm import joinedload
            
            user = session.query(User).options(
                joinedload(User.platform_connections),
            ).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            return user
            
        finally:
            db_manager.close_session(session)
            
    except Exception as e:
        logger.error(f"Failed to get user from session: {e}")
        return None

def get_current_platform_from_session(db_manager):
    """Get current platform object from session using database"""
    platform_id = get_platform_context()
    if not platform_id:
        return None
    
    try:
        session = db_manager.get_session()
        try:
            from models import PlatformConnection
            
            platform = session.query(PlatformConnection).filter(
                PlatformConnection.id == platform_id,
                PlatformConnection.is_active == True
            ).first()
            
            return platform
            
        finally:
            db_manager.close_session(session)
            
    except Exception as e:
        logger.error(f"Failed to get platform from session: {e}")
        return None
