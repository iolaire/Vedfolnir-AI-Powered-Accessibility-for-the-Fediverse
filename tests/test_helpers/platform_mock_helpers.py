# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Mock Helpers for Testing

This module provides specialized helpers for creating and configuring platform-specific mocks
to address common issues with platform integration testing.
"""

from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from models import PlatformConnection, User, UserRole

class PlatformMockHelper:
    """Helper class for creating platform-specific mocks"""
    
    @staticmethod
    def create_pixelfed_connection_mock(connection_id: int = 1,
                                      user_id: int = 1,
                                      is_active: bool = True,
                                      is_default: bool = True,
                                      instance_url: str = 'https://test-pixelfed.example.com') -> Mock:
        """
        Create a mock Pixelfed platform connection.
        
        Args:
            connection_id: ID of the connection
            user_id: ID of the user who owns the connection
            is_active: Whether the connection is active
            is_default: Whether this is the default connection
            instance_url: URL of the Pixelfed instance
            
        Returns:
            Mock configured as Pixelfed connection
        """
        connection_mock = Mock(spec=PlatformConnection)
        connection_mock.id = connection_id
        connection_mock.user_id = user_id
        connection_mock.name = 'Test Pixelfed'
        connection_mock.platform_type = 'pixelfed'
        connection_mock.instance_url = instance_url
        connection_mock.username = 'testuser'
        connection_mock.is_active = is_active
        connection_mock.is_default = is_default
        connection_mock.created_at = datetime.now(timezone.utc)
        
        # Mock encrypted credentials
        connection_mock.access_token = 'test_pixelfed_token'
        connection_mock.client_key = 'test_client_key'
        connection_mock.client_secret = 'test_client_secret'
        
        return connection_mock
    
    @staticmethod
    def create_mastodon_connection_mock(connection_id: int = 2,
                                      user_id: int = 1,
                                      is_active: bool = True,
                                      is_default: bool = False,
                                      instance_url: str = 'https://test-mastodon.example.com') -> Mock:
        """
        Create a mock Mastodon platform connection.
        
        Args:
            connection_id: ID of the connection
            user_id: ID of the user who owns the connection
            is_active: Whether the connection is active
            is_default: Whether this is the default connection
            instance_url: URL of the Mastodon instance
            
        Returns:
            Mock configured as Mastodon connection
        """
        connection_mock = Mock(spec=PlatformConnection)
        connection_mock.id = connection_id
        connection_mock.user_id = user_id
        connection_mock.name = 'Test Mastodon'
        connection_mock.platform_type = 'mastodon'
        connection_mock.instance_url = instance_url
        connection_mock.username = 'testuser'
        connection_mock.is_active = is_active
        connection_mock.is_default = is_default
        connection_mock.created_at = datetime.now(timezone.utc)
        
        # Mock encrypted credentials
        connection_mock.access_token = 'test_mastodon_token'
        connection_mock.client_key = 'test_client_key'
        connection_mock.client_secret = 'test_client_secret'
        
        return connection_mock
    
    @staticmethod
    def create_platform_context_mock(user_id: int = 1,
                                   platform_connection_id: int = 1,
                                   platform_type: str = 'pixelfed') -> Mock:
        """
        Create a mock platform context.
        
        Args:
            user_id: ID of the user
            platform_connection_id: ID of the platform connection
            platform_type: Type of platform
            
        Returns:
            Mock configured as platform context
        """
        context_mock = Mock()
        context_mock.user_id = user_id
        context_mock.platform_connection_id = platform_connection_id
        context_mock.platform_info = {
            'platform_type': platform_type,
            'instance_url': f'https://test-{platform_type}.example.com',
            'username': 'testuser'
        }
        context_mock.created_at = datetime.now(timezone.utc)
        
        return context_mock
    
    @staticmethod
    def create_activitypub_client_mock(platform_type: str = 'pixelfed',
                                     success: bool = True) -> AsyncMock:
        """
        Create a mock ActivityPub client.
        
        Args:
            platform_type: Type of platform (pixelfed, mastodon)
            success: Whether to simulate successful operations
            
        Returns:
            AsyncMock configured as ActivityPub client
        """
        client_mock = AsyncMock()
        
        if success:
            # Mock successful credential verification
            client_mock.verify_credentials = AsyncMock(return_value={
                'id': '123',
                'username': 'testuser',
                'display_name': 'Test User'
            })
            
            # Mock successful post fetching
            client_mock.get_posts = AsyncMock(return_value={
                'data': [
                    {
                        'id': '789',
                        'content': 'Test post',
                        'media_attachments': [
                            {
                                'id': '456',
                                'description': None,
                                'url': 'https://example.com/image.jpg'
                            }
                        ]
                    }
                ]
            })
            
            # Mock successful media description update
            if platform_type == 'pixelfed':
                client_mock.update_media_description = AsyncMock(return_value={
                    'success': True,
                    'media_id': '456'
                })
            elif platform_type == 'mastodon':
                client_mock.media_update = AsyncMock(return_value={
                    'id': '456',
                    'description': 'Updated description'
                })
        else:
            # Mock failed operations
            from app.services.activitypub.components.activitypub_client import ActivityPubError
            client_mock.verify_credentials.side_effect = ActivityPubError("Authentication failed")
            client_mock.get_posts.side_effect = ActivityPubError("Failed to fetch posts")
            
            if platform_type == 'pixelfed':
                client_mock.update_media_description.side_effect = ActivityPubError("Failed to update media")
            elif platform_type == 'mastodon':
                client_mock.media_update.side_effect = ActivityPubError("Failed to update media")
        
        return client_mock
    
    @staticmethod
    def create_platform_adapter_mock(platform_type: str = 'pixelfed',
                                   success: bool = True) -> Mock:
        """
        Create a mock platform adapter.
        
        Args:
            platform_type: Type of platform
            success: Whether to simulate successful operations
            
        Returns:
            Mock configured as platform adapter
        """
        adapter_mock = Mock()
        adapter_mock.platform_type = platform_type
        
        if success:
            # Mock successful operations
            adapter_mock.validate_connection = Mock(return_value=True)
            adapter_mock.get_posts_without_alt_text = Mock(return_value=[
                {
                    'id': '789',
                    'media_attachments': [
                        {'id': '456', 'description': None}
                    ]
                }
            ])
            adapter_mock.update_media_description = Mock(return_value=True)
            adapter_mock.get_user_info = Mock(return_value={
                'id': '123',
                'username': 'testuser'
            })
        else:
            # Mock failed operations
            adapter_mock.validate_connection = Mock(return_value=False)
            adapter_mock.get_posts_without_alt_text = Mock(side_effect=Exception("Connection failed"))
            adapter_mock.update_media_description = Mock(return_value=False)
            adapter_mock.get_user_info = Mock(side_effect=Exception("Authentication failed"))
        
        return adapter_mock

class PlatformTestDataFactory:
    """Factory for creating test data for platform testing"""
    
    @staticmethod
    def create_test_user_with_platforms(user_id: int = 1,
                                      username: str = 'testuser',
                                      include_pixelfed: bool = True,
                                      include_mastodon: bool = True) -> tuple[Mock, List[Mock]]:
        """
        Create a test user with platform connections.
        
        Args:
            user_id: ID of the user
            username: Username
            include_pixelfed: Whether to include Pixelfed connection
            include_mastodon: Whether to include Mastodon connection
            
        Returns:
            Tuple of (user_mock, list_of_platform_mocks)
        """
        user_mock = Mock(spec=User)
        user_mock.id = user_id
        user_mock.username = username
        user_mock.email = f'{username}@test.com'
        user_mock.role = UserRole.REVIEWER
        user_mock.is_active = True
        user_mock.created_at = datetime.now(timezone.utc)
        
        platforms = []
        
        if include_pixelfed:
            pixelfed_mock = PlatformMockHelper.create_pixelfed_connection_mock(
                connection_id=1,
                user_id=user_id,
                is_default=True
            )
            platforms.append(pixelfed_mock)
        
        if include_mastodon:
            mastodon_mock = PlatformMockHelper.create_mastodon_connection_mock(
                connection_id=2,
                user_id=user_id,
                is_default=not include_pixelfed  # Default if no Pixelfed
            )
            platforms.append(mastodon_mock)
        
        user_mock.platform_connections = platforms
        user_mock.get_active_platforms.return_value = [p for p in platforms if p.is_active]
        user_mock.get_default_platform.return_value = next(
            (p for p in platforms if p.is_default), 
            platforms[0] if platforms else None
        )
        
        return user_mock, platforms
    
    @staticmethod
    def create_test_posts_data(platform_type: str = 'pixelfed',
                             include_images_without_alt: bool = True,
                             post_count: int = 3) -> List[Dict[str, Any]]:
        """
        Create test posts data for platform testing.
        
        Args:
            platform_type: Type of platform
            include_images_without_alt: Whether to include images without alt text
            post_count: Number of posts to create
            
        Returns:
            List of post data dictionaries
        """
        posts = []
        
        for i in range(post_count):
            post_id = f'post_{i + 1}'
            media_id = f'media_{i + 1}'
            
            post_data = {
                'id': post_id,
                'content': f'Test post {i + 1}',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'media_attachments': []
            }
            
            if include_images_without_alt or i == 0:  # At least one post with image
                media_attachment = {
                    'id': media_id,
                    'type': 'image',
                    'url': f'https://example.com/image_{i + 1}.jpg',
                    'description': None if include_images_without_alt and i % 2 == 0 else f'Alt text for image {i + 1}'
                }
                post_data['media_attachments'].append(media_attachment)
            
            posts.append(post_data)
        
        return posts

# Convenience functions for common platform mock patterns
def create_pixelfed_test_setup(user_id: int = 1, success: bool = True) -> tuple[Mock, Mock, AsyncMock]:
    """Create a complete Pixelfed test setup with user, connection, and client"""
    user_mock, platforms = PlatformTestDataFactory.create_test_user_with_platforms(
        user_id=user_id,
        include_pixelfed=True,
        include_mastodon=False
    )
    
    connection_mock = platforms[0]
    client_mock = PlatformMockHelper.create_activitypub_client_mock(
        platform_type='pixelfed',
        success=success
    )
    
    return user_mock, connection_mock, client_mock

def create_mastodon_test_setup(user_id: int = 1, success: bool = True) -> tuple[Mock, Mock, AsyncMock]:
    """Create a complete Mastodon test setup with user, connection, and client"""
    user_mock, platforms = PlatformTestDataFactory.create_test_user_with_platforms(
        user_id=user_id,
        include_pixelfed=False,
        include_mastodon=True
    )
    
    connection_mock = platforms[0]
    client_mock = PlatformMockHelper.create_activitypub_client_mock(
        platform_type='mastodon',
        success=success
    )
    
    return user_mock, connection_mock, client_mock

def create_multi_platform_test_setup(user_id: int = 1, success: bool = True) -> tuple[Mock, List[Mock], List[AsyncMock]]:
    """Create a multi-platform test setup with user, connections, and clients"""
    user_mock, platforms = PlatformTestDataFactory.create_test_user_with_platforms(
        user_id=user_id,
        include_pixelfed=True,
        include_mastodon=True
    )
    
    clients = []
    for platform in platforms:
        client_mock = PlatformMockHelper.create_activitypub_client_mock(
            platform_type=platform.platform_type,
            success=success
        )
        clients.append(client_mock)
    
    return user_mock, platforms, clients

def patch_platform_context_manager(context_mock: Optional[Mock] = None) -> patch:
    """Create a patch for PlatformContextManager"""
    if context_mock is None:
        context_mock = PlatformMockHelper.create_platform_context_mock()
    
    manager_mock = Mock()
    manager_mock.set_context.return_value = context_mock
    manager_mock.get_context.return_value = context_mock
    manager_mock.require_context.return_value = context_mock
    manager_mock.clear_context.return_value = None
    
    return patch('platform_context.PlatformContextManager', return_value=manager_mock)

def patch_activitypub_client(platform_type: str = 'pixelfed', success: bool = True) -> patch:
    """Create a patch for ActivityPub client"""
    client_mock = PlatformMockHelper.create_activitypub_client_mock(
        platform_type=platform_type,
        success=success
    )
    
    return patch('activitypub_client.ActivityPubClient', return_value=client_mock)