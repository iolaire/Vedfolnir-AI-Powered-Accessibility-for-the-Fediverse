# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Mock User Helper for Testing

This module provides utilities for creating and managing mock users and platform connections
for testing purposes. It ensures consistent test data setup and cleanup across all tests
that involve user sessions and platforms.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models import User, PlatformConnection, UserRole
from database import DatabaseManager
from config import Config

logger = logging.getLogger(__name__)


class MockUserHelper:
    """Helper class for creating and managing mock users in tests"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the mock user helper.
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
        self.created_users = []  # Track created users for cleanup
        self.created_platforms = []  # Track created platforms for cleanup
    
    def create_mock_user(self, 
                        username: Optional[str] = None,
                        email: Optional[str] = None,
                        password: str = "test_password_123",
                        role: UserRole = UserRole.REVIEWER,
                        is_active: bool = True,
                        with_platforms: bool = True,
                        platform_configs: Optional[List[Dict[str, Any]]] = None) -> User:
        """
        Create a mock user for testing.
        
        Args:
            username: Username (auto-generated if None)
            email: Email address (auto-generated if None)
            password: Password for the user
            role: User role
            is_active: Whether user is active
            with_platforms: Whether to create platform connections
            platform_configs: List of platform configuration dicts
            
        Returns:
            Created User object
        """
        # Generate unique identifiers if not provided
        unique_id = str(uuid.uuid4())[:8]
        if username is None:
            username = f"test_user_{unique_id}"
        if email is None:
            email = f"test_{unique_id}@example.com"
        
        session = self.db_manager.get_session()
        try:
            # Create user
            user = User(
                username=username,
                email=email,
                role=role,
                is_active=is_active
            )
            user.set_password(password)
            
            session.add(user)
            session.commit()
            session.refresh(user)  # Get the ID
            
            # Track for cleanup
            self.created_users.append(user.id)
            
            logger.info(f"Created mock user: {username} (ID: {user.id})")
            
            # Create platform connections if requested
            if with_platforms:
                if platform_configs is None:
                    # Create default platform configurations
                    platform_configs = [
                        {
                            'name': f'Test Pixelfed {unique_id}',
                            'platform_type': 'pixelfed',
                            'instance_url': f'https://test-pixelfed-{unique_id}.example.com',
                            'username': f'testuser_{unique_id}',
                            'access_token': f'test_token_{unique_id}',
                            'is_default': True
                        },
                        {
                            'name': f'Test Mastodon {unique_id}',
                            'platform_type': 'mastodon',
                            'instance_url': f'https://test-mastodon-{unique_id}.example.com',
                            'username': f'testuser_{unique_id}',
                            'access_token': f'test_token_mastodon_{unique_id}',
                            'is_default': False
                        }
                    ]
                
                # Create platforms using the same session to avoid DetachedInstanceError
                for i, config in enumerate(platform_configs):
                    platform = self.create_mock_platform(user.id, session=session, **config)
                    # Don't append to user.platform_connections here - let SQLAlchemy handle the relationship
            
            session.commit()
            
            # Return a fresh user object with eager loading to avoid DetachedInstanceError
            from sqlalchemy.orm import joinedload
            fresh_user = session.query(User).options(
                joinedload(User.platform_connections),
                joinedload(User.sessions)
            ).filter(User.id == user.id).first()
            return fresh_user
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating mock user: {e}")
            raise
        finally:
            session.close()
    
    def create_mock_platform(self,
                           user_id: int,
                           name: str,
                           platform_type: str,
                           instance_url: str,
                           username: str,
                           access_token: str,
                           client_key: Optional[str] = None,
                           client_secret: Optional[str] = None,
                           is_default: bool = False,
                           is_active: bool = True,
                           session: Optional[Session] = None) -> PlatformConnection:
        """
        Create a mock platform connection for testing.
        
        Args:
            user_id: ID of the user to associate with
            name: Platform connection name
            platform_type: Type of platform (pixelfed, mastodon)
            instance_url: URL of the platform instance
            username: Username on the platform
            access_token: Access token for API access
            client_key: Optional client key
            client_secret: Optional client secret
            is_default: Whether this is the default platform
            is_active: Whether platform is active
            session: Optional existing session to use
            
        Returns:
            Created PlatformConnection object
        """
        # Use provided session or create new one
        if session is None:
            session = self.db_manager.get_session()
            should_close_session = True
        else:
            should_close_session = False
        
        try:
            platform = PlatformConnection(
                user_id=user_id,
                name=name,
                platform_type=platform_type,
                instance_url=instance_url,
                username=username,
                is_default=is_default,
                is_active=is_active
            )
            
            # Set encrypted credentials
            platform.access_token = access_token
            if client_key:
                platform.client_key = client_key
            if client_secret:
                platform.client_secret = client_secret
            
            session.add(platform)
            
            # Only commit if we created the session
            if should_close_session:
                session.commit()
                session.refresh(platform)
            else:
                # Let the caller handle commit
                session.flush()  # Get the ID without committing
            
            # Track for cleanup
            self.created_platforms.append(platform.id)
            
            logger.info(f"Created mock platform: {name} (ID: {platform.id}) for user {user_id}")
            return platform
            
        except Exception as e:
            if should_close_session:
                session.rollback()
            logger.error(f"Error creating mock platform: {e}")
            raise
        finally:
            if should_close_session:
                session.close()
    
    def get_mock_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a mock user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User object if found, None otherwise
        """
        session = self.db_manager.get_session()
        try:
            from sqlalchemy.orm import joinedload
            user = session.query(User).options(
                joinedload(User.platform_connections),
                joinedload(User.sessions)
            ).filter_by(username=username).first()
            return user
        finally:
            session.close()
    
    def cleanup_mock_users(self):
        """Clean up all created mock users and their associated data"""
        session = self.db_manager.get_session()
        try:
            # Clean up platforms first (due to foreign key constraints)
            for platform_id in self.created_platforms:
                platform = session.query(PlatformConnection).get(platform_id)
                if platform:
                    session.delete(platform)
                    logger.debug(f"Deleted mock platform: {platform_id}")
            
            # Clean up users
            for user_id in self.created_users:
                user = session.query(User).get(user_id)
                if user:
                    # Delete associated sessions and other related data
                    for session_obj in user.sessions:
                        session.delete(session_obj)
                    
                    session.delete(user)
                    logger.debug(f"Deleted mock user: {user_id}")
            
            session.commit()
            
            # Clear tracking lists
            self.created_users.clear()
            self.created_platforms.clear()
            
            logger.info("Cleaned up all mock users and platforms")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up mock users: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_specific_user(self, user_id: int):
        """
        Clean up a specific user and their associated data.
        
        Args:
            user_id: ID of the user to clean up
        """
        session = self.db_manager.get_session()
        try:
            user = session.query(User).get(user_id)
            if user:
                # Delete associated platforms
                for platform in user.platform_connections:
                    session.delete(platform)
                    if platform.id in self.created_platforms:
                        self.created_platforms.remove(platform.id)
                
                # Delete associated sessions
                for session_obj in user.sessions:
                    session.delete(session_obj)
                
                # Delete user
                session.delete(user)
                if user_id in self.created_users:
                    self.created_users.remove(user_id)
                
                session.commit()
                logger.info(f"Cleaned up specific user: {user_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up user {user_id}: {e}")
            raise
        finally:
            session.close()
    
    def get_created_user_count(self) -> int:
        """Get the number of users created by this helper"""
        return len(self.created_users)
    
    def get_created_platform_count(self) -> int:
        """Get the number of platforms created by this helper"""
        return len(self.created_platforms)


# Convenience functions for easy use in tests
def create_test_user_with_platforms(db_manager: DatabaseManager, 
                                   username: Optional[str] = None,
                                   role: UserRole = UserRole.REVIEWER) -> tuple[User, MockUserHelper]:
    """
    Convenience function to create a test user with default platforms.
    
    Args:
        db_manager: DatabaseManager instance
        username: Optional username (auto-generated if None)
        role: User role
        
    Returns:
        Tuple of (User object, MockUserHelper instance for cleanup)
    """
    helper = MockUserHelper(db_manager)
    user = helper.create_mock_user(username=username, role=role, with_platforms=True)
    return user, helper


def cleanup_test_user(helper: MockUserHelper):
    """
    Convenience function to clean up test users.
    
    Args:
        helper: MockUserHelper instance to clean up
    """
    helper.cleanup_mock_users()


# Test configuration constants
TEST_USER_DEFAULTS = {
    'password': 'test_password_123',
    'role': UserRole.REVIEWER,
    'is_active': True
}

TEST_PLATFORM_DEFAULTS = {
    'pixelfed': {
        'platform_type': 'pixelfed',
        'instance_url': 'https://test-pixelfed.example.com',
        'is_default': True
    },
    'mastodon': {
        'platform_type': 'mastodon', 
        'instance_url': 'https://test-mastodon.example.com',
        'is_default': False
    }
}