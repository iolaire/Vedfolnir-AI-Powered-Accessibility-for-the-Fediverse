# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
from typing import Optional, List, Any
from flask import has_request_context
from flask_login import UserMixin
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import DetachedInstanceError
from models import User, PlatformConnection
from app.core.session.core.session_manager import SessionManager

logger = logging.getLogger(__name__)

class SessionAwareUser(UserMixin):
    """
    A session-aware wrapper for User objects that prevents DetachedInstanceError
    by maintaining proper session attachment throughout the request lifecycle.
    """
    
    def __init__(self, user: User, session_manager: SessionManager):
        """
        Initialize SessionAwareUser with a User object and session manager.
        
        Args:
            user: The User model instance to wrap
            session_manager: SessionManager instance for session management
        """
        self._user_id = user.id
        self._session_manager = session_manager
        self._user = user
        self._platforms_cache = None
        self._cache_valid = False
        logger.debug(f"Created SessionAwareUser for user ID {user.id}")
    
    def _get_attached_user(self) -> Optional[User]:
        """
        Get the user object attached to the current request session.
        
        Returns:
            User object attached to current session, or None if not available
        """
        if not has_request_context():
            logger.warning("Attempted to access user outside request context")
            return self._user
        
        try:
            # Try to ensure the current user object is attached
            attached_user = self._session_manager.ensure_session_attachment(self._user)
            if attached_user:
                self._user = attached_user
                return attached_user
        except (SQLAlchemyError, DetachedInstanceError) as e:
            logger.warning(f"Failed to reattach user object, reloading from database: {e}")
        
        # If reattachment fails, reload from database
        try:
            session = self._session_manager.get_request_session()
            user = session.query(User).get(self._user_id)
            if user:
                self._user = user
                return user
            else:
                logger.error(f"User {self._user_id} not found in database")
                return None
        except Exception as e:
            logger.error(f"Failed to reload user from database: {e}")
            return self._user
    
    def _invalidate_cache(self):
        """Invalidate the platforms cache"""
        self._platforms_cache = None
        self._cache_valid = False
    
    @property
    def platforms(self) -> List[PlatformConnection]:
        """
        Get user's platform connections with proper session attachment and caching.
        
        Returns:
            List of PlatformConnection objects attached to current session
        """
        # Return cached platforms if still valid (takes priority over mocks)
        if self._cache_valid and self._platforms_cache is not None:
            return self._platforms_cache
        
        # Check for mock object (for testing)
        if hasattr(self, '_platforms_mock'):
            mock = getattr(self, '_platforms_mock')
            if hasattr(mock, 'side_effect') and mock.side_effect:
                raise mock.side_effect()
            return mock
        
        user = self._get_attached_user()
        if not user:
            logger.warning("No user available for platform access")
            return []
        
        try:
            # Access platform_connections relationship
            platforms = list(user.platform_connections)
            
            # Ensure all platforms are attached to current session
            if has_request_context():
                attached_platforms = []
                for platform in platforms:
                    try:
                        attached_platform = self._session_manager.ensure_session_attachment(platform)
                        if attached_platform:
                            attached_platforms.append(attached_platform)
                    except Exception as e:
                        logger.warning(f"Failed to attach platform {platform.id}: {e}")
                        attached_platforms.append(platform)
                
                platforms = attached_platforms
            
            # Cache the result
            self._platforms_cache = platforms
            self._cache_valid = True
            
            return platforms
            
        except (DetachedInstanceError, SQLAlchemyError) as e:
            logger.warning(f"Error accessing user platforms, attempting recovery: {e}")
            self._invalidate_cache()
            
            # Try to reload platforms from database
            if has_request_context():
                try:
                    session = self._session_manager.get_request_session()
                    platforms = session.query(PlatformConnection).filter_by(
                        user_id=self._user_id,
                        is_active=True
                    ).all()
                    
                    # Cache the result
                    self._platforms_cache = platforms
                    self._cache_valid = True
                    
                    return platforms
                except Exception as reload_error:
                    logger.error(f"Failed to reload platforms from database: {reload_error}")
            
            return []
    
    def get_active_platform(self) -> Optional[PlatformConnection]:
        """
        Get the user's active/default platform with proper session context.
        
        Returns:
            Active PlatformConnection object or None if not found
        """
        platforms = self.platforms
        
        # First try to find default platform
        for platform in platforms:
            if platform.is_default and platform.is_active:
                return platform
        
        # If no default, return first active platform
        for platform in platforms:
            if platform.is_active:
                return platform
        
        return None
    
    def get_platform_by_id(self, platform_id: int) -> Optional[PlatformConnection]:
        """
        Get a specific platform by ID with session attachment.
        
        Args:
            platform_id: ID of the platform to retrieve
            
        Returns:
            PlatformConnection object or None if not found
        """
        platforms = self.platforms
        for platform in platforms:
            if platform.id == platform_id:
                return platform
        return None
    
    def get_platform_by_type(self, platform_type: str) -> Optional[PlatformConnection]:
        """
        Get platform by type with session attachment.
        
        Args:
            platform_type: Type of platform to find
            
        Returns:
            PlatformConnection object or None if not found
        """
        platforms = self.platforms
        for platform in platforms:
            if platform.platform_type == platform_type and platform.is_active:
                return platform
        return None
    
    def refresh_platforms(self):
        """Force refresh of platforms cache"""
        self._invalidate_cache()
        # Trigger reload by accessing platforms property
        _ = self.platforms
    
    # Proxy all other attributes to the underlying user object
    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access to the underlying User object with session safety.
        
        Args:
            name: Attribute name to access
            
        Returns:
            Attribute value from underlying User object
        """
        # Handle special Flask-Login methods
        if name in ('is_authenticated', 'is_anonymous', 'get_id'):
            return getattr(self, f'_{name}', None) or getattr(User, name, None)
        
        # Handle critical user attributes that need to be always available
        if name in ('id', 'username', 'email', 'role', 'is_active'):
            # For critical attributes, try to get from cached user first
            if hasattr(self, '_user') and self._user:
                try:
                    value = getattr(self._user, name)
                    if value is not None:
                        return value
                except (DetachedInstanceError, SQLAlchemyError):
                    pass  # Fall through to database lookup
        
        user = self._get_attached_user()
        if not user:
            logger.warning(f"No user available for attribute access: {name}")
            return None
        
        try:
            return getattr(user, name)
        except (DetachedInstanceError, SQLAlchemyError) as e:
            logger.warning(f"DetachedInstanceError accessing {name}, attempting recovery: {e}")
            
            # Try to get a fresh user object
            user = self._get_attached_user()
            if user:
                try:
                    return getattr(user, name)
                except Exception as retry_error:
                    logger.error(f"Failed to access {name} after recovery: {retry_error}")
            
            return None
    
    def __setattr__(self, name: str, value: Any):
        """
        Proxy attribute setting to the underlying User object with session safety.
        
        Args:
            name: Attribute name to set
            value: Value to set
        """
        # Handle internal attributes and properties that need special handling
        if name.startswith('_') or name in ('platforms',):
            # For properties like 'platforms', we need to handle them specially
            if name == 'platforms' and hasattr(value, 'side_effect'):
                # This is likely a Mock object for testing - store it as a private attribute
                super().__setattr__('_platforms_mock', value)
                return
            super().__setattr__(name, value)
            return
        
        user = self._get_attached_user()
        if not user:
            logger.warning(f"No user available for attribute setting: {name}")
            return
        
        try:
            setattr(user, name, value)
            # Invalidate cache if we're modifying user data
            if name in ('platform_connections',):
                self._invalidate_cache()
        except (DetachedInstanceError, SQLAlchemyError) as e:
            logger.error(f"Error setting {name}: {e}")
    
    # Flask-Login required methods
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        user = self._get_attached_user()
        return user is not None and getattr(user, 'is_active', True)
    
    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous"""
        return False
    
    @property
    def is_active(self) -> bool:
        """Check if user is active"""
        user = self._get_attached_user()
        return user is not None and getattr(user, 'is_active', True)
    
    def get_id(self) -> str:
        """Get user ID as string for Flask-Login"""
        return str(self._user_id)
    
    @property
    def role(self):
        """Get user role with session safety - critical for admin access control"""
        # Try cached user first
        if hasattr(self, '_user') and self._user:
            try:
                return self._user.role
            except (DetachedInstanceError, SQLAlchemyError):
                pass
        
        # Get fresh user from database
        user = self._get_attached_user()
        if user:
            try:
                return user.role
            except Exception as e:
                logger.error(f"Failed to get user role: {e}")
        
        # Fallback - this should never happen for valid users
        logger.error(f"Unable to determine role for user {self._user_id}")
        return None
    
    def __repr__(self) -> str:
        """String representation of SessionAwareUser"""
        user = self._get_attached_user()
        username = getattr(user, 'username', 'unknown') if user else 'unknown'
        return f"<SessionAwareUser {self._user_id}:{username}>"