# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform Context Manager

This module provides the PlatformContextManager class for handling platform-specific
operations and context switching in the Vedfolnir platform-aware system.

The context manager tracks the current user and their active platform connection,
provides platform filtering for database queries, and handles platform-specific
configuration generation.
"""

import logging
import threading
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import User, PlatformConnection, Post, Image, ProcessingRun
from config import ActivityPubConfig, RetryConfig, RateLimitConfig


@dataclass
class PlatformContext:
    """Represents the current platform context for a user"""
    user_id: int
    user: Optional[User] = None
    platform_connection_id: Optional[int] = None
    platform_connection: Optional[PlatformConnection] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate context after initialization"""
        if not self.user_id:
            raise ValueError("user_id is required for platform context")
    
    @property
    def is_valid(self) -> bool:
        """Check if the context is valid and complete"""
        return (
            self.user_id is not None and
            self.user is not None and
            self.platform_connection_id is not None and
            self.platform_connection is not None and
            self.platform_connection.is_active
        )
    
    @property
    def platform_info(self) -> Dict[str, Any]:
        """Get platform information as a dictionary"""
        if not self.platform_connection:
            return {}
        
        return {
            'platform_type': self.platform_connection.platform_type,
            'instance_url': self.platform_connection.instance_url,
            'username': self.platform_connection.username,
            'name': self.platform_connection.name,
            'is_default': self.platform_connection.is_default
        }


class PlatformContextError(Exception):
    """Raised when there are issues with platform context operations"""
    pass


class PlatformContextManager:
    """
    Manages platform context for users and provides platform-aware operations.
    
    This class handles:
    - Setting and tracking user and platform context
    - Platform filtering for database queries
    - Data injection with platform information
    - ActivityPub configuration generation
    - Thread-safe context management
    """
    
    def __init__(self, session: Session):
        """
        Initialize the platform context manager.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.logger = logging.getLogger(__name__)
        
        # Thread-local storage for context
        self._local = threading.local()
        
        # Lock for thread-safe operations
        self._lock = threading.RLock()
    
    @property
    def current_context(self) -> Optional[PlatformContext]:
        """Get the current platform context for this thread"""
        return getattr(self._local, 'context', None)
    
    def set_context(self, user_id: int, platform_connection_id: Optional[int] = None, 
                   session_id: Optional[str] = None) -> PlatformContext:
        """
        Set the platform context for the current thread.
        
        Args:
            user_id: ID of the user
            platform_connection_id: ID of the platform connection (optional)
            session_id: Session ID for tracking (optional)
            
        Returns:
            The created platform context
            
        Raises:
            PlatformContextError: If context cannot be set
        """
        with self._lock:
            try:
                # Get user from database
                user = self.session.query(User).get(user_id)
                if not user:
                    raise PlatformContextError(f"User with ID {user_id} not found")
                
                if not user.is_active:
                    raise PlatformContextError(f"User {user.username} is not active")
                
                # Determine platform connection
                platform_connection = None
                if platform_connection_id:
                    # Use specified platform connection
                    platform_connection = self.session.query(PlatformConnection).filter_by(
                        id=platform_connection_id,
                        user_id=user_id,
                        is_active=True
                    ).first()
                    
                    if not platform_connection:
                        raise PlatformContextError(
                            f"Platform connection {platform_connection_id} not found or not active for user {user.username}"
                        )
                else:
                    # Use default platform connection
                    platform_connection = user.get_default_platform()
                    if not platform_connection:
                        # Fall back to any active platform
                        active_platforms = user.get_active_platforms()
                        if active_platforms:
                            platform_connection = active_platforms[0]
                            self.logger.warning(
                                f"No default platform for user {user.username}, using {platform_connection.name}"
                            )
                        else:
                            raise PlatformContextError(f"No active platform connections found for user {user.username}")
                
                # Create context
                context = PlatformContext(
                    user_id=user_id,
                    user=user,
                    platform_connection_id=platform_connection.id,
                    platform_connection=platform_connection,
                    session_id=session_id
                )
                
                # Store in thread-local storage
                self._local.context = context
                
                self.logger.debug(
                    f"Set platform context: user={user.username}, platform={platform_connection.name}"
                )
                
                return context
                
            except Exception as e:
                self.logger.error(f"Failed to set platform context: {e}")
                raise PlatformContextError(f"Failed to set platform context: {e}")
    
    def clear_context(self) -> None:
        """Clear the platform context for the current thread"""
        with self._lock:
            if hasattr(self._local, 'context'):
                context = self._local.context
                if context:
                    self.logger.debug(
                        f"Cleared platform context: user={context.user.username if context.user else 'unknown'}"
                    )
                delattr(self._local, 'context')
    
    def require_context(self) -> PlatformContext:
        """
        Get the current context, raising an error if not set.
        
        Returns:
            The current platform context
            
        Raises:
            PlatformContextError: If no context is set
        """
        context = self.current_context
        if not context:
            raise PlatformContextError("No platform context set. Call set_context() first.")
        
        if not context.is_valid:
            raise PlatformContextError("Platform context is invalid or incomplete")
        
        return context
    
    @contextmanager
    def context_scope(self, user_id: int, platform_connection_id: Optional[int] = None,
                     session_id: Optional[str] = None):
        """
        Context manager for temporary platform context.
        
        Args:
            user_id: ID of the user
            platform_connection_id: ID of the platform connection (optional)
            session_id: Session ID for tracking (optional)
            
        Yields:
            The platform context
        """
        old_context = self.current_context
        try:
            context = self.set_context(user_id, platform_connection_id, session_id)
            yield context
        finally:
            if old_context:
                self._local.context = old_context
            else:
                self.clear_context()
    
    def get_platform_filter_criteria(self, model_class) -> List:
        """
        Get SQLAlchemy filter criteria for platform-aware queries.
        
        Args:
            model_class: The SQLAlchemy model class to filter
            
        Returns:
            List of SQLAlchemy filter criteria
            
        Raises:
            PlatformContextError: If no context is set
        """
        context = self.require_context()
        
        # Build filter criteria based on model
        criteria = []
        
        if hasattr(model_class, 'platform_connection_id'):
            # Prefer platform_connection_id if available
            criteria.append(model_class.platform_connection_id == context.platform_connection_id)
        elif hasattr(model_class, 'platform_type') and hasattr(model_class, 'instance_url'):
            # Fall back to platform_type and instance_url for backward compatibility
            platform_info = context.platform_info
            criteria.extend([
                model_class.platform_type == platform_info['platform_type'],
                model_class.instance_url == platform_info['instance_url']
            ])
        else:
            self.logger.warning(f"Model {model_class.__name__} has no platform identification fields")
        
        return criteria
    
    def apply_platform_filter(self, query, model_class):
        """
        Apply platform filtering to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy query object
            model_class: The model class being queried
            
        Returns:
            Filtered query object
        """
        criteria = self.get_platform_filter_criteria(model_class)
        if criteria:
            return query.filter(and_(*criteria))
        return query
    
    def inject_platform_data(self, data: Dict[str, Any], model_class=None) -> Dict[str, Any]:
        """
        Inject platform identification data into a dictionary.
        
        Args:
            data: Dictionary to inject platform data into
            model_class: Optional model class to determine which fields to inject
            
        Returns:
            Dictionary with platform data injected
            
        Raises:
            PlatformContextError: If no context is set
        """
        context = self.require_context()
        platform_info = context.platform_info
        
        # Create a copy to avoid modifying the original
        injected_data = data.copy()
        
        # Always inject platform_connection_id if we have it
        if context.platform_connection_id:
            injected_data['platform_connection_id'] = context.platform_connection_id
        
        # Inject backward compatibility fields
        if 'platform_type' in platform_info:
            injected_data['platform_type'] = platform_info['platform_type']
        
        if 'instance_url' in platform_info:
            injected_data['instance_url'] = platform_info['instance_url']
        
        return injected_data
    
    def create_activitypub_config(self) -> ActivityPubConfig:
        """
        Create an ActivityPub configuration from the current platform context.
        
        Returns:
            ActivityPub configuration object
            
        Raises:
            PlatformContextError: If no context is set or config cannot be created
        """
        context = self.require_context()
        
        try:
            # Use the platform connection's built-in method
            config = context.platform_connection.to_activitypub_config()
            if not config:
                raise PlatformContextError("Failed to create ActivityPub configuration from platform connection")
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create ActivityPub config: {e}")
            raise PlatformContextError(f"Failed to create ActivityPub config: {e}")
    
    def switch_platform(self, platform_connection_id: int) -> PlatformContext:
        """
        Switch to a different platform connection for the current user.
        
        Args:
            platform_connection_id: ID of the platform connection to switch to
            
        Returns:
            Updated platform context
            
        Raises:
            PlatformContextError: If switch fails or platform not accessible
        """
        current_context = self.require_context()
        
        # Verify the new platform belongs to the current user
        platform_connection = self.session.query(PlatformConnection).filter_by(
            id=platform_connection_id,
            user_id=current_context.user_id,
            is_active=True
        ).first()
        
        if not platform_connection:
            raise PlatformContextError(
                f"Platform connection {platform_connection_id} not found or not accessible"
            )
        
        # Update context
        return self.set_context(
            user_id=current_context.user_id,
            platform_connection_id=platform_connection_id,
            session_id=current_context.session_id
        )
    
    def get_user_platforms(self, user_id: Optional[int] = None) -> List[PlatformConnection]:
        """
        Get all active platform connections for a user.
        
        Args:
            user_id: User ID (uses current context user if not provided)
            
        Returns:
            List of active platform connections
        """
        if user_id is None:
            context = self.require_context()
            user_id = context.user_id
        
        return self.session.query(PlatformConnection).filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
    
    def set_default_platform(self, platform_connection_id: int, user_id: Optional[int] = None) -> None:
        """
        Set a platform connection as the default for a user.
        
        Args:
            platform_connection_id: ID of the platform connection to set as default
            user_id: User ID (uses current context user if not provided)
            
        Raises:
            PlatformContextError: If operation fails
        """
        if user_id is None:
            context = self.require_context()
            user_id = context.user_id
        
        # Verify the platform belongs to the user
        platform_connection = self.session.query(PlatformConnection).filter_by(
            id=platform_connection_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not platform_connection:
            raise PlatformContextError(
                f"Platform connection {platform_connection_id} not found or not accessible"
            )
        
        try:
            # Clear existing default for this user
            self.session.query(PlatformConnection).filter_by(
                user_id=user_id
            ).update({'is_default': False})
            
            # Set new default
            platform_connection.is_default = True
            self.session.commit()
            
            self.logger.info(
                f"Set platform {platform_connection.name} as default for user {user_id}"
            )
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to set default platform: {e}")
            raise PlatformContextError(f"Failed to set default platform: {e}")
    
    def test_platform_connection(self, platform_connection_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Test a platform connection.
        
        Args:
            platform_connection_id: ID of platform to test (uses current context if not provided)
            
        Returns:
            Tuple of (success, message)
        """
        if platform_connection_id is None:
            context = self.require_context()
            platform_connection = context.platform_connection
        else:
            platform_connection = self.session.query(PlatformConnection).get(platform_connection_id)
            if not platform_connection:
                return False, f"Platform connection {platform_connection_id} not found"
        
        try:
            return platform_connection.test_connection()
        except Exception as e:
            self.logger.error(f"Platform connection test failed: {e}")
            return False, str(e)
    
    def get_context_info(self) -> Dict[str, Any]:
        """
        Get information about the current context.
        
        Returns:
            Dictionary with context information
        """
        context = self.current_context
        if not context:
            return {'has_context': False}
        
        return {
            'has_context': True,
            'is_valid': context.is_valid,
            'user_id': context.user_id,
            'username': context.user.username if context.user else None,
            'platform_connection_id': context.platform_connection_id,
            'platform_info': context.platform_info,
            'session_id': context.session_id
        }
    
    def validate_context(self) -> List[str]:
        """
        Validate the current context and return any issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        context = self.current_context
        errors = []
        
        if not context:
            errors.append("No platform context set")
            return errors
        
        if not context.user_id:
            errors.append("No user ID in context")
        
        if not context.user:
            errors.append("User object not loaded in context")
        elif not context.user.is_active:
            errors.append("User is not active")
        
        if not context.platform_connection_id:
            errors.append("No platform connection ID in context")
        
        if not context.platform_connection:
            errors.append("Platform connection object not loaded in context")
        elif not context.platform_connection.is_active:
            errors.append("Platform connection is not active")
        
        return errors