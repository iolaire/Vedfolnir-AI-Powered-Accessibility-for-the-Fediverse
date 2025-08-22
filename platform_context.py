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
    
    def __init__(self, message: str, **kwargs):
        """
        Initialize PlatformContextError with message and optional context.
        
        Args:
            message: Error message
            **kwargs: Additional context information (e.g., user_id, platform_id)
        """
        super().__init__(message)
        self.context = kwargs

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
                # Validate user_id to prevent SQL injection
                if not isinstance(user_id, int) or user_id <= 0:
                    raise PlatformContextError(f"Invalid user ID: {user_id}. Must be a positive integer.")
                
                # Validate platform_connection_id if provided
                if platform_connection_id is not None:
                    if not isinstance(platform_connection_id, int) or platform_connection_id <= 0:
                        raise PlatformContextError(f"Invalid platform connection ID: {platform_connection_id}. Must be a positive integer.")
                
                # Get user from database using parameterized query
                user = self.session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise PlatformContextError(f"User with ID {user_id} not found")
                
                if not user.is_active:
                    raise PlatformContextError(f"User {user.username} is not active")
                
                # Determine platform connection with comprehensive validation
                platform_connection = None
                if platform_connection_id:
                    # Use specified platform connection with strict validation
                    platform_connection = self.session.query(PlatformConnection).filter(
                        PlatformConnection.id == platform_connection_id,
                        PlatformConnection.user_id == user_id,
                        PlatformConnection.is_active == True
                    ).first()
                    
                    if not platform_connection:
                        # Check if platform connection exists but is inactive
                        inactive_platform = self.session.query(PlatformConnection).filter(
                            PlatformConnection.id == platform_connection_id,
                            PlatformConnection.user_id == user_id
                        ).first()
                        
                        if inactive_platform:
                            raise PlatformContextError(
                                f"Platform connection {platform_connection_id} exists but is inactive for user {user.username}"
                            )
                        
                        # Check if platform connection exists but belongs to different user
                        other_user_platform = self.session.query(PlatformConnection).filter(
                            PlatformConnection.id == platform_connection_id
                        ).first()
                        
                        if other_user_platform:
                            raise PlatformContextError(
                                f"Platform connection {platform_connection_id} belongs to a different user"
                            )
                        
                        # Platform connection doesn't exist at all
                        raise PlatformContextError(
                            f"Platform connection {platform_connection_id} not found"
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
                
                # Additional validation for platform connection
                if not platform_connection.is_active:
                    raise PlatformContextError(f"Platform connection {platform_connection.name} is not active")
                
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
                
            except PlatformContextError:
                # Re-raise PlatformContextError as-is
                raise
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
        try:
            current_context = self.require_context()
            
            # Validate platform_connection_id to prevent SQL injection
            if not isinstance(platform_connection_id, int) or platform_connection_id <= 0:
                raise PlatformContextError(f"Invalid platform connection ID: {platform_connection_id}. Must be a positive integer.")
            
            # Verify the new platform belongs to the current user with comprehensive checks
            platform_connection = self.session.query(PlatformConnection).filter(
                PlatformConnection.id == platform_connection_id,
                PlatformConnection.user_id == current_context.user_id,
                PlatformConnection.is_active == True
            ).first()
            
            if not platform_connection:
                # Provide detailed error information
                # Check if platform exists but is inactive
                inactive_platform = self.session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_connection_id,
                    PlatformConnection.user_id == current_context.user_id
                ).first()
                
                if inactive_platform:
                    raise PlatformContextError(
                        f"Cannot switch to platform connection {platform_connection_id}: platform is inactive"
                    )
                
                # Check if platform exists but belongs to different user
                other_user_platform = self.session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_connection_id
                ).first()
                
                if other_user_platform:
                    raise PlatformContextError(
                        f"Platform connection {platform_connection_id} not found or not accessible"
                    )
                
                # Platform doesn't exist
                raise PlatformContextError(
                    f"Platform connection {platform_connection_id} not found or not accessible"
                )
            
            # Store previous context for rollback if needed
            previous_context = current_context
            
            try:
                # Update context
                new_context = self.set_context(
                    user_id=current_context.user_id,
                    platform_connection_id=platform_connection_id,
                    session_id=current_context.session_id
                )
                
                self.logger.info(
                    f"Successfully switched platform context from {previous_context.platform_connection.name} "
                    f"to {new_context.platform_connection.name} for user {current_context.user.username}"
                )
                
                return new_context
                
            except Exception as switch_error:
                # Attempt to restore previous context on failure
                try:
                    self._local.context = previous_context
                    self.logger.warning(
                        f"Platform switch failed, restored previous context: {switch_error}"
                    )
                except Exception as restore_error:
                    self.logger.error(
                        f"Failed to restore previous context after switch failure: {restore_error}"
                    )
                raise PlatformContextError(f"Platform switch failed: {switch_error}")
                
        except PlatformContextError:
            # Re-raise PlatformContextError as-is
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during platform switch: {e}")
            raise PlatformContextError(f"Platform switch failed due to unexpected error: {e}")
    
    def get_user_platforms(self, user_id: Optional[int] = None) -> List[PlatformConnection]:
        """
        Get all active platform connections for a user.
        
        Args:
            user_id: User ID (uses current context user if not provided)
            
        Returns:
            List of active platform connections
            
        Raises:
            PlatformContextError: If user_id is invalid
        """
        try:
            if user_id is None:
                context = self.require_context()
                user_id = context.user_id
            else:
                # Validate user_id to prevent SQL injection
                if not isinstance(user_id, int) or user_id <= 0:
                    raise PlatformContextError(f"Invalid user ID: {user_id}. Must be a positive integer.")
            
            return self.session.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id,
                PlatformConnection.is_active == True
            ).order_by(PlatformConnection.is_default.desc(), PlatformConnection.name).all()
            
        except PlatformContextError:
            # Re-raise PlatformContextError as-is
            raise
        except Exception as e:
            self.logger.error(f"Failed to get user platforms: {e}")
            raise PlatformContextError(f"Failed to get user platforms: {e}")
    
    def set_default_platform(self, platform_connection_id: int, user_id: Optional[int] = None) -> None:
        """
        Set a platform connection as the default for a user.
        
        Args:
            platform_connection_id: ID of the platform connection to set as default
            user_id: User ID (uses current context user if not provided)
            
        Raises:
            PlatformContextError: If operation fails
        """
        try:
            # Validate platform_connection_id to prevent SQL injection
            if not isinstance(platform_connection_id, int) or platform_connection_id <= 0:
                raise PlatformContextError(f"Invalid platform connection ID: {platform_connection_id}. Must be a positive integer.")
            
            if user_id is None:
                context = self.require_context()
                user_id = context.user_id
            else:
                # Validate user_id to prevent SQL injection
                if not isinstance(user_id, int) or user_id <= 0:
                    raise PlatformContextError(f"Invalid user ID: {user_id}. Must be a positive integer.")
            
            # Verify the platform belongs to the user with comprehensive validation
            platform_connection = self.session.query(PlatformConnection).filter(
                PlatformConnection.id == platform_connection_id,
                PlatformConnection.user_id == user_id,
                PlatformConnection.is_active == True
            ).first()
            
            if not platform_connection:
                # Provide detailed error information
                # Check if platform exists but is inactive
                inactive_platform = self.session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_connection_id,
                    PlatformConnection.user_id == user_id
                ).first()
                
                if inactive_platform:
                    raise PlatformContextError(
                        f"Cannot set inactive platform connection {platform_connection_id} as default"
                    )
                
                # Check if platform exists but belongs to different user
                other_user_platform = self.session.query(PlatformConnection).filter(
                    PlatformConnection.id == platform_connection_id
                ).first()
                
                if other_user_platform:
                    raise PlatformContextError(
                        f"Cannot set platform connection {platform_connection_id} as default: access denied"
                    )
                
                # Platform doesn't exist
                raise PlatformContextError(
                    f"Platform connection {platform_connection_id} not found"
                )
            
            # Clear existing default for this user using parameterized query
            self.session.query(PlatformConnection).filter(
                PlatformConnection.user_id == user_id
            ).update({'is_default': False})
            
            # Set new default
            platform_connection.is_default = True
            self.session.commit()
            
            self.logger.info(
                f"Set platform {platform_connection.name} as default for user {user_id}"
            )
            
        except PlatformContextError:
            # Re-raise PlatformContextError as-is
            raise
        except Exception as e:
            try:
                self.session.rollback()
            except Exception as rollback_error:
                self.logger.error(f"Failed to rollback transaction: {rollback_error}")
            
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
    
    def validate_platform_access(self, platform_type: str, instance_url: str) -> bool:
        """
        Validate if the current context has access to a specific platform.
        
        Args:
            platform_type: Type of platform (e.g., 'pixelfed', 'mastodon')
            instance_url: URL of the platform instance
            
        Returns:
            True if access is valid, False otherwise
        """
        try:
            context = self.require_context()
            platform_info = context.platform_info
            
            return (
                platform_info.get('platform_type') == platform_type and
                platform_info.get('instance_url') == instance_url
            )
        except PlatformContextError:
            return False
    
    def get_platform_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for the current platform context.
        
        Returns:
            Dictionary with platform statistics
            
        Raises:
            PlatformContextError: If no context is set
        """
        context = self.require_context()
        
        try:
            # Get platform-specific statistics
            from models import Post, Image
            
            # Count posts for this platform
            total_posts = self.session.query(Post).filter(
                Post.platform_connection_id == context.platform_connection_id
            ).count()
            
            # Count images for this platform
            total_images = self.session.query(Image).filter(
                Image.platform_connection_id == context.platform_connection_id
            ).count()
            
            # Count processed images
            processed_images = self.session.query(Image).filter(
                Image.platform_connection_id == context.platform_connection_id,
                Image.final_caption.isnot(None)
            ).count()
            
            return {
                'total_posts': total_posts,
                'total_images': total_images,
                'processed_images': processed_images,
                'platform_type': context.platform_info.get('platform_type'),
                'instance_url': context.platform_info.get('instance_url'),
                'platform_name': context.platform_connection.name
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get platform statistics: {e}")
            raise PlatformContextError(f"Failed to get platform statistics: {e}")
    
    def get_activitypub_config(self) -> ActivityPubConfig:
        """
        Get ActivityPub configuration from the current platform context.
        This is an alias for create_activitypub_config for backward compatibility.
        
        Returns:
            ActivityPub configuration object
            
        Raises:
            PlatformContextError: If no context is set or config cannot be created
        """
        return self.create_activitypub_config()