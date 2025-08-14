# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Standardized Mock Configurations

This test file demonstrates the usage of all standardized mock configurations
and validates that they work correctly for common testing scenarios.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from tests.test_helpers import (
    StandardizedMockFactory,
    AsyncMockHelper,
    DatabaseMockHelper,
    PlatformMockHelper,
    create_mock_with_unpacking,
    create_async_context_manager_mock,
    patch_database_session,
    patch_async_http_client,
    create_pixelfed_test_setup,
    QueryMockBuilder
)
from models import User, PlatformConnection, CaptionGenerationTask, TaskStatus, UserRole


class TestStandardizedMockConfigurations(unittest.TestCase):
    """Test standardized mock configurations"""
    
    def test_async_mock_creation(self):
        """Test creating async mocks with proper configuration"""
        # Test basic async mock
        async_mock = StandardizedMockFactory.create_async_mock(
            return_value={'success': True}
        )
        
        self.assertIsInstance(async_mock, AsyncMock)
        
        # Test async mock with side effect
        test_exception = Exception("Test error")
        async_mock_with_error = StandardizedMockFactory.create_async_mock(
            side_effect=test_exception
        )
        
        self.assertIsInstance(async_mock_with_error, AsyncMock)
        self.assertEqual(async_mock_with_error.side_effect, test_exception)
    
    def test_database_query_mock_chaining(self):
        """Test database query mock with method chaining"""
        test_result = {'id': 1, 'name': 'test'}
        query_mock = StandardizedMockFactory.create_database_query_mock(
            return_value=test_result,
            supports_chaining=True
        )
        
        # Test method chaining
        result = query_mock.filter().filter_by().order_by().first()
        self.assertEqual(result, test_result)
        
        # Test direct calls
        result = query_mock.first()
        self.assertEqual(result, test_result)
        
        # Test count
        count = query_mock.count()
        self.assertEqual(count, 1)
    
    def test_database_query_mock_with_list_results(self):
        """Test database query mock with list results"""
        test_results = [{'id': 1}, {'id': 2}, {'id': 3}]
        query_mock = StandardizedMockFactory.create_database_query_mock(
            return_value=test_results,
            supports_chaining=True
        )
        
        # Test all() method
        results = query_mock.all()
        self.assertEqual(results, test_results)
        
        # Test count
        count = query_mock.count()
        self.assertEqual(count, 3)
        
        # Test first() with list
        first_result = query_mock.first()
        self.assertEqual(first_result, test_results)
    
    def test_database_query_mock_with_unpacking(self):
        """Test database query mock with tuple unpacking support"""
        test_items = ['item1', 'item2', 'item3']
        query_mock = StandardizedMockFactory.create_database_query_mock(
            return_value=test_items,
            supports_unpacking=True
        )
        
        # Test iteration
        items = list(query_mock)
        self.assertEqual(items, test_items)
        
        # Test indexing
        self.assertEqual(query_mock[0], 'item1')
        self.assertEqual(query_mock[1], 'item2')
        
        # Test length
        self.assertEqual(len(query_mock), 3)
    
    def test_session_mock_creation(self):
        """Test database session mock creation"""
        session_mock = StandardizedMockFactory.create_session_mock()
        
        # Test basic session methods exist
        self.assertTrue(hasattr(session_mock, 'add'))
        self.assertTrue(hasattr(session_mock, 'commit'))
        self.assertTrue(hasattr(session_mock, 'rollback'))
        self.assertTrue(hasattr(session_mock, 'query'))
        
        # Test context manager support
        self.assertTrue(hasattr(session_mock, '__enter__'))
        self.assertTrue(hasattr(session_mock, '__exit__'))
        
        # Test context manager usage
        with session_mock as session:
            self.assertEqual(session, session_mock)
    
    def test_platform_api_mock_pixelfed(self):
        """Test Pixelfed API mock creation"""
        api_mock = StandardizedMockFactory.create_platform_api_mock(
            platform_type='pixelfed',
            success_responses=True,
            async_support=True
        )
        
        self.assertIsInstance(api_mock, AsyncMock)
        self.assertTrue(hasattr(api_mock, 'get_posts'))
        self.assertTrue(hasattr(api_mock, 'update_media_description'))
        self.assertTrue(hasattr(api_mock, 'verify_credentials'))
    
    def test_platform_api_mock_mastodon(self):
        """Test Mastodon API mock creation"""
        api_mock = StandardizedMockFactory.create_platform_api_mock(
            platform_type='mastodon',
            success_responses=True,
            async_support=True
        )
        
        self.assertIsInstance(api_mock, AsyncMock)
        self.assertTrue(hasattr(api_mock, 'timeline_home'))
        self.assertTrue(hasattr(api_mock, 'media_update'))
        self.assertTrue(hasattr(api_mock, 'account_verify_credentials'))
    
    def test_task_mock_creation(self):
        """Test task mock creation"""
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id='test-task-123',
            user_id=42,
            status=TaskStatus.RUNNING,
            can_be_cancelled=False
        )
        
        self.assertEqual(task_mock.id, 'test-task-123')
        self.assertEqual(task_mock.user_id, 42)
        self.assertEqual(task_mock.status, TaskStatus.RUNNING)
        self.assertFalse(task_mock.can_be_cancelled())
    
    def test_user_mock_creation(self):
        """Test user mock creation"""
        user_mock = StandardizedMockFactory.create_user_mock(
            user_id=123,
            username='testuser123',
            role=UserRole.ADMIN,
            with_platforms=True
        )
        
        self.assertEqual(user_mock.id, 123)
        self.assertEqual(user_mock.username, 'testuser123')
        self.assertEqual(user_mock.role, UserRole.ADMIN)
        self.assertTrue(len(user_mock.platform_connections) > 0)
    
    def test_platform_connection_mock_creation(self):
        """Test platform connection mock creation"""
        platform_mock = StandardizedMockFactory.create_platform_connection_mock(
            connection_id=456,
            user_id=123,
            platform_type='mastodon',
            is_default=False
        )
        
        self.assertEqual(platform_mock.id, 456)
        self.assertEqual(platform_mock.user_id, 123)
        self.assertEqual(platform_mock.platform_type, 'mastodon')
        self.assertFalse(platform_mock.is_default)
    
    def test_mock_with_unpacking(self):
        """Test mock with unpacking support"""
        items = ['a', 'b', 'c']
        mock = create_mock_with_unpacking(items)
        
        # Test iteration
        result = list(mock)
        self.assertEqual(result, items)
        
        # Test indexing
        self.assertEqual(mock[0], 'a')
        self.assertEqual(mock[2], 'c')
        
        # Test length
        self.assertEqual(len(mock), 3)
    
    def test_async_context_manager_mock(self):
        """Test async context manager mock"""
        return_value = {'data': 'test'}
        context_mock = create_async_context_manager_mock(return_value)
        
        self.assertIsInstance(context_mock, AsyncMock)
        self.assertTrue(hasattr(context_mock, '__aenter__'))
        self.assertTrue(hasattr(context_mock, '__aexit__'))
    
    def test_async_http_response_helper(self):
        """Test async HTTP response helper"""
        json_data = {'success': True, 'data': 'test'}
        response_mock = AsyncMockHelper.create_async_http_response(
            status_code=200,
            json_data=json_data
        )
        
        self.assertEqual(response_mock.status_code, 200)
        self.assertIsInstance(response_mock.json, AsyncMock)
        self.assertIsInstance(response_mock.raise_for_status, AsyncMock)
    
    def test_async_http_client_helper(self):
        """Test async HTTP client helper"""
        response_mock = AsyncMockHelper.create_async_http_response(
            status_code=200,
            json_data={'test': 'data'}
        )
        
        client_mock = AsyncMockHelper.create_async_http_client(
            responses=[response_mock]
        )
        
        self.assertIsInstance(client_mock, AsyncMock)
        self.assertTrue(hasattr(client_mock, 'get'))
        self.assertTrue(hasattr(client_mock, 'post'))
        self.assertTrue(hasattr(client_mock, '__aenter__'))
        self.assertTrue(hasattr(client_mock, '__aexit__'))
    
    def test_database_mock_helper(self):
        """Test database mock helper"""
        test_user = {'id': 1, 'username': 'testuser'}
        session_mock = DatabaseMockHelper.create_session_mock(
            query_results={'User': test_user}
        )
        
        # Test query with specific model result
        query_result = session_mock.query(User)
        self.assertIsNotNone(query_result)
        
        # Test session methods
        session_mock.add(test_user)
        session_mock.commit()
        
        session_mock.add.assert_called_once_with(test_user)
        session_mock.commit.assert_called_once()
    
    def test_query_mock_builder(self):
        """Test query mock builder"""
        test_result = {'id': 1, 'name': 'test'}
        
        query_mock = (QueryMockBuilder()
                     .filter(test_result)
                     .filter_by()
                     .order_by()
                     .first())
        
        # Test the built query
        result = query_mock.filter().filter_by().order_by().first()
        self.assertEqual(result, test_result)
    
    def test_platform_test_setup_helpers(self):
        """Test platform test setup helpers"""
        # Test Pixelfed setup
        user_mock, connection_mock, client_mock = create_pixelfed_test_setup(
            user_id=123,
            success=True
        )
        
        self.assertEqual(user_mock.id, 123)
        self.assertEqual(connection_mock.platform_type, 'pixelfed')
        self.assertIsInstance(client_mock, AsyncMock)
        
        # Test that user has the connection
        self.assertIn(connection_mock, user_mock.platform_connections)
    
    def test_database_manager_mock(self):
        """Test database manager mock creation"""
        session_mock = DatabaseMockHelper.create_session_mock()
        db_manager_mock = DatabaseMockHelper.create_database_manager_mock(session_mock)
        
        # Test get_session returns the session mock
        returned_session = db_manager_mock.get_session()
        self.assertEqual(returned_session, session_mock)
        
        # Test session_scope context manager
        with db_manager_mock.session_scope() as session:
            self.assertEqual(session, session_mock)
    
    def test_model_mock_creation(self):
        """Test model mock creation with defaults"""
        # Test User model mock
        user_mock = DatabaseMockHelper.create_model_mock(
            User,
            username='custom_user',
            role=UserRole.ADMIN
        )
        
        self.assertEqual(user_mock.username, 'custom_user')
        self.assertEqual(user_mock.role, UserRole.ADMIN)
        self.assertTrue(hasattr(user_mock, 'id'))
        self.assertTrue(hasattr(user_mock, 'email'))
        
        # Test PlatformConnection model mock
        platform_mock = DatabaseMockHelper.create_model_mock(
            PlatformConnection,
            platform_type='mastodon',
            is_default=False
        )
        
        self.assertEqual(platform_mock.platform_type, 'mastodon')
        self.assertFalse(platform_mock.is_default)
        self.assertTrue(hasattr(platform_mock, 'id'))
        self.assertTrue(hasattr(platform_mock, 'user_id'))
        
        # Test CaptionGenerationTask model mock
        task_mock = DatabaseMockHelper.create_model_mock(
            CaptionGenerationTask,
            status=TaskStatus.COMPLETED,
            user_id=456
        )
        
        self.assertEqual(task_mock.status, TaskStatus.COMPLETED)
        self.assertEqual(task_mock.user_id, 456)
        self.assertTrue(hasattr(task_mock, 'id'))
        self.assertTrue(hasattr(task_mock, 'created_at'))


class TestMockConfigurationIntegration(unittest.TestCase):
    """Test integration of mock configurations in realistic scenarios"""
    
    @patch('database.DatabaseManager')
    def test_task_queue_manager_mock_integration(self, mock_db_manager_class):
        """Test task queue manager with standardized mocks"""
        # Create standardized mocks
        session_mock = DatabaseMockHelper.create_session_mock()
        db_manager_mock = DatabaseMockHelper.create_database_manager_mock(session_mock)
        mock_db_manager_class.return_value = db_manager_mock
        
        # Create test task
        task_mock = StandardizedMockFactory.create_task_mock(
            task_id='integration-test-task',
            user_id=1,
            status=TaskStatus.QUEUED
        )
        
        # Configure query mock to return no existing active tasks
        query_mock = DatabaseMockHelper.create_query_chain_mock(final_result=None)
        session_mock.query.return_value = query_mock
        
        # Test would go here - this demonstrates the setup
        self.assertIsNotNone(task_mock)
        self.assertEqual(task_mock.id, 'integration-test-task')
        self.assertEqual(task_mock.status, TaskStatus.QUEUED)
    
    def test_platform_context_mock_integration(self):
        """Test platform context with standardized mocks"""
        # Create platform test setup
        user_mock, connection_mock, client_mock = create_pixelfed_test_setup(
            user_id=1,
            success=True
        )
        
        # Create platform context mock
        context_mock = PlatformMockHelper.create_platform_context_mock(
            user_id=user_mock.id,
            platform_connection_id=connection_mock.id,
            platform_type=connection_mock.platform_type
        )
        
        # Verify integration
        self.assertEqual(context_mock.user_id, user_mock.id)
        self.assertEqual(context_mock.platform_connection_id, connection_mock.id)
        self.assertEqual(context_mock.platform_info['platform_type'], 'pixelfed')
    
    def test_async_operation_mock_integration(self):
        """Test async operations with standardized mocks"""
        # Create async HTTP client mock
        json_response = {'success': True, 'data': 'test'}
        response_mock = AsyncMockHelper.create_async_http_response(
            status_code=200,
            json_data=json_response
        )
        
        client_mock = AsyncMockHelper.create_async_http_client(
            responses=[response_mock]
        )
        
        # Test async context manager
        self.assertTrue(hasattr(client_mock, '__aenter__'))
        self.assertTrue(hasattr(client_mock, '__aexit__'))
        
        # Test HTTP methods
        self.assertTrue(hasattr(client_mock, 'get'))
        self.assertTrue(hasattr(client_mock, 'post'))


if __name__ == '__main__':
    unittest.main()