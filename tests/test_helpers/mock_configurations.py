# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Standardized Mock Configurations for Testing

This module provides standardized mock object configurations to ensure consistent
behavior across all test suites. It addresses common mock configuration issues
including async operations, tuple unpacking, database query chains, and platform
behavior simulation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Callable
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from dataclasses import dataclass

from models import User, PlatformConnection, TaskStatus, UserRole

@dataclass
class MockConfiguration:
    """Configuration for standardized mock objects"""
    mock_type: str  # 'sync', 'async', 'database_query', 'platform_api'
    return_value: Any = None
    side_effect: Optional[Union[Exception, Callable, List[Any]]] = None
    supports_unpacking: bool = False
    async_support: bool = False
    spec: Optional[type] = None
    attributes: Optional[Dict[str, Any]] = None

class StandardizedMockFactory:
    """Factory for creating standardized mock objects"""
    
    @staticmethod
    def create_async_mock(return_value: Any = None, 
                         side_effect: Optional[Union[Exception, Callable, List[Any]]] = None,
                         spec: Optional[type] = None) -> AsyncMock:
        """
        Create a properly configured AsyncMock for async operations.
        
        Args:
            return_value: Value to return when called
            side_effect: Exception or callable to use as side effect
            spec: Class to use as spec for the mock
            
        Returns:
            Configured AsyncMock object
        """
        mock = AsyncMock(spec=spec)
        
        if return_value is not None:
            mock.return_value = return_value
        
        if side_effect is not None:
            mock.side_effect = side_effect
            
        # Ensure async methods are properly configured
        if hasattr(mock, '__aenter__'):
            mock.__aenter__.return_value = mock
        if hasattr(mock, '__aexit__'):
            mock.__aexit__.return_value = None
            
        return mock
    
    @staticmethod
    def create_database_query_mock(return_value: Any = None,
                                  supports_chaining: bool = True,
                                  supports_unpacking: bool = False) -> Mock:
        """
        Create a mock for database query operations with proper chaining support.
        
        Args:
            return_value: Final return value of the query chain
            supports_chaining: Whether to support method chaining
            supports_unpacking: Whether to support tuple unpacking
            
        Returns:
            Configured Mock object for database queries
        """
        if supports_chaining:
            # Create a chain of mocks for query operations
            query_mock = Mock()
            filter_mock = Mock()
            filter_by_mock = Mock()
            join_mock = Mock()
            order_by_mock = Mock()
            limit_mock = Mock()
            offset_mock = Mock()
            first_mock = Mock()
            all_mock = Mock()
            count_mock = Mock()
            
            # Set up the chain
            query_mock.filter.return_value = filter_mock
            query_mock.filter_by.return_value = filter_by_mock
            query_mock.join.return_value = join_mock
            query_mock.order_by.return_value = order_by_mock
            query_mock.limit.return_value = limit_mock
            query_mock.offset.return_value = offset_mock
            
            # Each intermediate mock should also support chaining
            for intermediate_mock in [filter_mock, filter_by_mock, join_mock, 
                                    order_by_mock, limit_mock, offset_mock]:
                intermediate_mock.filter.return_value = filter_mock
                intermediate_mock.filter_by.return_value = filter_by_mock
                intermediate_mock.join.return_value = join_mock
                intermediate_mock.order_by.return_value = order_by_mock
                intermediate_mock.limit.return_value = limit_mock
                intermediate_mock.offset.return_value = offset_mock
                intermediate_mock.first.return_value = return_value
                intermediate_mock.all.return_value = return_value if isinstance(return_value, list) else [return_value] if return_value else []
                intermediate_mock.count.return_value = len(return_value) if isinstance(return_value, list) else (1 if return_value else 0)
            
            # Set final return values
            query_mock.first.return_value = return_value
            query_mock.all.return_value = return_value if isinstance(return_value, list) else [return_value] if return_value else []
            query_mock.count.return_value = len(return_value) if isinstance(return_value, list) else (1 if return_value else 0)
            
            if supports_unpacking:
                # Configure for tuple unpacking
                if isinstance(return_value, (list, tuple)):
                    query_mock.__iter__ = Mock(return_value=iter(return_value))
                    query_mock.__getitem__ = Mock(side_effect=lambda i: return_value[i])
                    query_mock.__len__ = Mock(return_value=len(return_value))
            
            return query_mock
        else:
            # Simple mock without chaining
            mock = Mock()
            mock.return_value = return_value
            
            if supports_unpacking and isinstance(return_value, (list, tuple)):
                mock.__iter__ = Mock(return_value=iter(return_value))
                mock.__getitem__ = Mock(side_effect=lambda i: return_value[i])
                mock.__len__ = Mock(return_value=len(return_value))
            
            return mock
    
    @staticmethod
    def create_session_mock(autocommit: bool = True,
                           rollback_on_error: bool = True) -> Mock:
        """
        Create a mock database session with proper context manager support.
        
        Args:
            autocommit: Whether to automatically handle commits
            rollback_on_error: Whether to handle rollbacks on errors
            
        Returns:
            Configured Mock session object
        """
        session_mock = Mock()
        
        # Configure context manager support
        session_mock.__enter__ = Mock(return_value=session_mock)
        session_mock.__exit__ = Mock(return_value=None)
        
        # Configure basic session methods
        session_mock.add = Mock()
        session_mock.delete = Mock()
        session_mock.commit = Mock()
        session_mock.rollback = Mock()
        session_mock.flush = Mock()
        session_mock.refresh = Mock()
        session_mock.expunge = Mock()
        session_mock.close = Mock()
        
        # Configure query method to return a database query mock
        session_mock.query = Mock(side_effect=lambda model: 
            StandardizedMockFactory.create_database_query_mock())
        
        return session_mock
    
    @staticmethod
    def create_platform_api_mock(platform_type: str = 'pixelfed',
                                success_responses: bool = True,
                                async_support: bool = True) -> Union[Mock, AsyncMock]:
        """
        Create a mock for platform API operations.
        
        Args:
            platform_type: Type of platform (pixelfed, mastodon)
            success_responses: Whether to return successful responses
            async_support: Whether to use AsyncMock
            
        Returns:
            Configured Mock or AsyncMock for platform API
        """
        if async_support:
            api_mock = AsyncMock()
        else:
            api_mock = Mock()
        
        # Configure common API methods
        if platform_type == 'pixelfed':
            # Pixelfed-specific API methods
            api_mock.get_posts = StandardizedMockFactory.create_async_mock(
                return_value={'data': []} if success_responses else None
            )
            api_mock.update_media_description = StandardizedMockFactory.create_async_mock(
                return_value={'success': True} if success_responses else None
            )
            api_mock.verify_credentials = StandardizedMockFactory.create_async_mock(
                return_value={'id': '123', 'username': 'testuser'} if success_responses else None
            )
        elif platform_type == 'mastodon':
            # Mastodon-specific API methods
            api_mock.timeline_home = StandardizedMockFactory.create_async_mock(
                return_value=[] if success_responses else None
            )
            api_mock.media_update = StandardizedMockFactory.create_async_mock(
                return_value={'id': '123'} if success_responses else None
            )
            api_mock.account_verify_credentials = StandardizedMockFactory.create_async_mock(
                return_value={'id': '123', 'username': 'testuser'} if success_responses else None
            )
        
        # Configure HTTP response attributes for async mocks
        if async_support:
            api_mock.status_code = 200 if success_responses else 500
            api_mock.raise_for_status = StandardizedMockFactory.create_async_mock()
            api_mock.json = StandardizedMockFactory.create_async_mock(
                return_value={'success': True} if success_responses else {'error': 'API Error'}
            )
        
        return api_mock
    
    @staticmethod
    def create_task_mock(task_id: str = 'test-task-id',
                        user_id: int = 1,
                        status: TaskStatus = TaskStatus.QUEUED,
                        can_be_cancelled: bool = True) -> Mock:
        """
        Create a mock task object for task queue testing.
        
        Args:
            task_id: ID of the task
            user_id: ID of the user who owns the task
            status: Current status of the task
            can_be_cancelled: Whether the task can be cancelled
            
        Returns:
            Configured Mock task object
        """
        task_mock = Mock()
        task_mock.id = task_id
        task_mock.user_id = user_id
        task_mock.status = status
        task_mock.created_at = datetime.now(timezone.utc)
        task_mock.started_at = None
        task_mock.completed_at = None
        task_mock.error_message = None
        task_mock.can_be_cancelled.return_value = can_be_cancelled
        
        return task_mock
    
    @staticmethod
    def create_user_mock(user_id: int = 1,
                        username: str = 'testuser',
                        role: UserRole = UserRole.REVIEWER,
                        is_active: bool = True,
                        with_platforms: bool = True) -> Mock:
        """
        Create a mock user object for testing.
        
        Args:
            user_id: ID of the user
            username: Username
            role: User role
            is_active: Whether user is active
            with_platforms: Whether to include platform connections
            
        Returns:
            Configured Mock user object
        """
        user_mock = Mock(spec=User)
        user_mock.id = user_id
        user_mock.username = username
        user_mock.role = role
        user_mock.is_active = is_active
        user_mock.created_at = datetime.now(timezone.utc)
        
        if with_platforms:
            platform_mock = StandardizedMockFactory.create_platform_connection_mock(
                user_id=user_id
            )
            user_mock.platform_connections = [platform_mock]
            user_mock.get_active_platforms.return_value = [platform_mock]
            user_mock.get_default_platform.return_value = platform_mock
        else:
            user_mock.platform_connections = []
            user_mock.get_active_platforms.return_value = []
            user_mock.get_default_platform.return_value = None
        
        return user_mock
    
    @staticmethod
    def create_platform_connection_mock(connection_id: int = 1,
                                      user_id: int = 1,
                                      platform_type: str = 'pixelfed',
                                      is_active: bool = True,
                                      is_default: bool = True) -> Mock:
        """
        Create a mock platform connection object for testing.
        
        Args:
            connection_id: ID of the platform connection
            user_id: ID of the user who owns the connection
            platform_type: Type of platform
            is_active: Whether connection is active
            is_default: Whether this is the default connection
            
        Returns:
            Configured Mock platform connection object
        """
        platform_mock = Mock(spec=PlatformConnection)
        platform_mock.id = connection_id
        platform_mock.user_id = user_id
        platform_mock.name = f'Test {platform_type.title()}'
        platform_mock.platform_type = platform_type
        platform_mock.instance_url = f'https://test-{platform_type}.example.com'
        platform_mock.username = 'testuser'
        platform_mock.is_active = is_active
        platform_mock.is_default = is_default
        platform_mock.created_at = datetime.now(timezone.utc)
        
        # Mock encrypted credential access
        platform_mock.access_token = 'test_access_token'
        platform_mock.client_key = 'test_client_key'
        platform_mock.client_secret = 'test_client_secret'
        
        return platform_mock

class MockConfigurationPresets:
    """Predefined mock configurations for common testing scenarios"""
    
    @staticmethod
    def get_database_session_config() -> MockConfiguration:
        """Get configuration for database session mocks"""
        return MockConfiguration(
            mock_type='database_session',
            spec=None,
            attributes={
                'autocommit': True,
                'rollback_on_error': True
            }
        )
    
    @staticmethod
    def get_async_http_client_config(success: bool = True) -> MockConfiguration:
        """Get configuration for async HTTP client mocks"""
        return MockConfiguration(
            mock_type='async',
            async_support=True,
            return_value={
                'status_code': 200 if success else 500,
                'json': {'success': True} if success else {'error': 'HTTP Error'}
            }
        )
    
    @staticmethod
    def get_platform_api_config(platform_type: str = 'pixelfed') -> MockConfiguration:
        """Get configuration for platform API mocks"""
        return MockConfiguration(
            mock_type='platform_api',
            async_support=True,
            attributes={
                'platform_type': platform_type,
                'success_responses': True
            }
        )
    
    @staticmethod
    def get_task_queue_config() -> MockConfiguration:
        """Get configuration for task queue mocks"""
        return MockConfiguration(
            mock_type='sync',
            supports_unpacking=True,
            attributes={
                'max_concurrent_tasks': 2,
                'cleanup_interval': 3600
            }
        )

# Convenience functions for common mock patterns
def create_mock_with_unpacking(items: List[Any]) -> Mock:
    """
    Create a mock that supports tuple/list unpacking operations.
    
    Args:
        items: List of items to support unpacking for
        
    Returns:
        Mock object configured for unpacking
    """
    mock = Mock()
    mock.__iter__ = Mock(return_value=iter(items))
    mock.__getitem__ = Mock(side_effect=lambda i: items[i])
    mock.__len__ = Mock(return_value=len(items))
    mock.return_value = items
    return mock

def create_async_context_manager_mock(return_value: Any = None) -> AsyncMock:
    """
    Create an async context manager mock.
    
    Args:
        return_value: Value to return from the context manager
        
    Returns:
        AsyncMock configured as context manager
    """
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=return_value or mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock

def patch_database_session(session_mock: Optional[Mock] = None) -> Mock:
    """
    Create a patch for database session with standardized configuration.
    
    Args:
        session_mock: Optional existing session mock to use
        
    Returns:
        Configured session mock
    """
    if session_mock is None:
        session_mock = StandardizedMockFactory.create_session_mock()
    
    return patch('database.DatabaseManager.get_session', return_value=session_mock)

def patch_async_http_client(success: bool = True) -> AsyncMock:
    """
    Create a patch for async HTTP client with standardized configuration.
    
    Args:
        success: Whether to simulate successful responses
        
    Returns:
        Configured AsyncMock for HTTP client
    """
    client_mock = StandardizedMockFactory.create_platform_api_mock(
        success_responses=success,
        async_support=True
    )
    
    return patch('httpx.AsyncClient', return_value=client_mock)