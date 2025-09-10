# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test error handling for DatabaseManager platform operations

This module tests that the DatabaseManager properly handles invalid operations
and provides appropriate error messages for various failure scenarios.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.database.core.database_manager import DatabaseManager, DatabaseOperationError, PlatformValidationError
from app.services.platform.core.platform_context import PlatformContextError
from models import User, PlatformConnection, Post, Image
from config import Config

class TestDatabaseErrorHandling(unittest.TestCase):
    """Test error handling for DatabaseManager platform operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock config with proper nested structure
        self.config = Mock(spec=Config)
        
        # Mock storage config
        storage_config = Mock()
        storage_config.database_url = "mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db"
        
        # Mock db_config
        db_config = Mock()
        db_config.pool_size = 4
        db_config.max_overflow = 14
        db_config.pool_timeout = 34
        db_config.pool_recycle = 3600
        db_config.query_logging = False
        
        storage_config.db_config = db_config
        self.config.storage = storage_config
        
        # Mock database manager with mocked session
        with patch('database.create_engine'), \
             patch('database.scoped_session'), \
             patch.object(DatabaseManager, 'create_tables'):
            self.db_manager = DatabaseManager(self.config)
            self.db_manager.Session = Mock()
            self.db_manager._context_manager = Mock()
        
        # Mock session
        self.session = Mock(spec=Session)
        self.db_manager.get_session = Mock(return_value=self.session)
    
    def test_get_or_create_post_empty_post_id(self):
        """Test creating post with empty post ID"""
        with self.assertRaises(PlatformValidationError) as cm:
            self.db_manager.get_or_create_post(
                post_id="", 
                user_id="testuser", 
                post_url="https://example.com/post/123"
            )
        
        self.assertIn("Post ID cannot be empty", str(cm.exception))
    
    def test_get_or_create_post_whitespace_post_id(self):
        """Test creating post with whitespace-only post ID"""
        with self.assertRaises(PlatformValidationError) as cm:
            self.db_manager.get_or_create_post(
                post_id="   ", 
                user_id="testuser", 
                post_url="https://example.com/post/123"
            )
        
        self.assertIn("Post ID cannot be empty", str(cm.exception))
    
    def test_get_or_create_post_empty_user_id(self):
        """Test creating post with empty user ID"""
        with self.assertRaises(PlatformValidationError) as cm:
            self.db_manager.get_or_create_post(
                post_id="123", 
                user_id="", 
                post_url="https://example.com/post/123"
            )
        
        self.assertIn("User ID cannot be empty", str(cm.exception))
    
    def test_get_or_create_post_empty_post_url(self):
        """Test creating post with empty post URL"""
        with self.assertRaises(PlatformValidationError) as cm:
            self.db_manager.get_or_create_post(
                post_id="123", 
                user_id="testuser", 
                post_url=""
            )
        
        self.assertIn("Post URL cannot be empty", str(cm.exception))
    
    def test_get_or_create_post_invalid_url_format(self):
        """Test creating post with invalid URL format"""
        with self.assertRaises(PlatformValidationError) as cm:
            self.db_manager.get_or_create_post(
                post_id="123", 
                user_id="testuser", 
                post_url="not-a-url"
            )
        
        self.assertIn("Post URL must start with http:// or https://", str(cm.exception))
    
    def test_get_or_create_post_no_platform_context(self):
        """Test creating post without platform context"""
        # Mock context manager to raise error
        self.db_manager._context_manager.require_context.side_effect = PlatformContextError("No context")
        
        with self.assertRaises(PlatformValidationError) as cm:
            self.db_manager.get_or_create_post(
                post_id="123", 
                user_id="testuser", 
                post_url="https://example.com/post/123"
            )
        
        self.assertIn("Platform context required for post operations", str(cm.exception))
    
    def test_get_or_create_post_successful_creation(self):
        """Test successful post creation with platform context"""
        # Mock context manager
        mock_context = Mock()
        mock_context.platform_info = {'name': 'Test Platform'}
        self.db_manager._context_manager.require_context.return_value = mock_context
        self.db_manager._context_manager.apply_platform_filter.return_value = self.session.query.return_value
        self.db_manager._context_manager.inject_platform_data.return_value = {
            'post_id': '123',
            'user_id': 'testuser',
            'post_url': 'https://example.com/post/123',
            'platform_connection_id': 1
        }
        
        # Mock query to return None first (post doesn't exist), then return created post
        mock_post = Mock()
        self.session.query.return_value.filter_by.return_value.first.side_effect = [None, mock_post]
        
        result = self.db_manager.get_or_create_post(
            post_id="123", 
            user_id="testuser", 
            post_url="https://example.com/post/123"
        )
        
        # Should return the created post
        self.assertEqual(result, mock_post)
    
    def test_get_or_create_post_existing_post(self):
        """Test retrieving existing post"""
        # Mock context manager
        mock_context = Mock()
        self.db_manager._context_manager.require_context.return_value = mock_context
        self.db_manager._context_manager.apply_platform_filter.return_value = self.session.query.return_value
        
        # Mock query to return existing post
        mock_post = Mock()
        self.session.query.return_value.filter_by.return_value.first.return_value = mock_post
        
        result = self.db_manager.get_or_create_post(
            post_id="123", 
            user_id="testuser", 
            post_url="https://example.com/post/123"
        )
        
        # Should return the existing post
        self.assertEqual(result, mock_post)
    
    def test_platform_connection_validation_errors(self):
        """Test platform connection validation errors"""
        # Test empty name
        with self.assertRaises(PlatformValidationError):
            self.db_manager.create_platform_connection(
                user_id=1,
                name="",  # Empty name
                platform_type="pixelfed",
                instance_url="https://example.com",
                username="testuser",
                access_token="token123"
            )
        
        # Test invalid platform type
        with self.assertRaises(PlatformValidationError):
            self.db_manager.create_platform_connection(
                user_id=1,
                name="Test Platform",
                platform_type="invalid",  # Invalid platform type
                instance_url="https://example.com",
                username="testuser",
                access_token="token123"
            )
    
    def test_update_platform_connection_validation(self):
        """Test platform connection update validation"""
        # Mock existing connection
        mock_connection = Mock()
        mock_connection.user_id = 1
        self.session.query.return_value.get.return_value = mock_connection
        
        # Test updating with invalid data should raise validation error
        with self.assertRaises(PlatformValidationError):
            self.db_manager.update_platform_connection(
                connection_id=1,
                user_id=1,
                platform_type="invalid_type"  # Invalid platform type
            )
    
    def test_set_platform_context_invalid_user(self):
        """Test setting platform context with invalid user"""
        self.db_manager._context_manager.set_context.side_effect = PlatformContextError("User not found")
        
        with self.assertRaises(PlatformContextError):
            self.db_manager.set_platform_context(user_id=999)
    
    def test_require_platform_context_no_context(self):
        """Test requiring platform context when none is set"""
        self.db_manager._context_manager.require_context.side_effect = PlatformContextError("No context")
        
        with self.assertRaises(PlatformContextError):
            self.db_manager.require_platform_context()
    
    def test_apply_platform_filter_no_context(self):
        """Test applying platform filter when no context is set"""
        # Mock context manager to raise error
        self.db_manager._context_manager.apply_platform_filter.side_effect = PlatformContextError("No context")
        
        # This should not raise an error but return unfiltered query
        query = Mock()
        result = self.db_manager._apply_platform_filter(query, Post)
        
        # Should return the original query
        self.assertEqual(result, query)
    
    def test_inject_platform_data_no_context(self):
        """Test injecting platform data when no context is set"""
        # Mock context manager to raise error
        self.db_manager._context_manager.inject_platform_data.side_effect = PlatformContextError("No context")
        
        test_data = {'post_id': '123'}
        result = self.db_manager._inject_platform_data(test_data)
        
        # Should return original data unchanged
        self.assertEqual(result, test_data)
    
    def test_create_platform_connection_invalid_user_id(self):
        """Test creating platform connection with invalid user ID"""
        with self.assertRaises(PlatformValidationError):
            self.db_manager.create_platform_connection(
                user_id=0,  # Invalid user ID
                name="Test Platform",
                platform_type="pixelfed",
                instance_url="https://example.com",
                username="testuser",
                access_token="token123"
            )
    
    def test_switch_platform_context_invalid_user(self):
        """Test switching platform context with invalid user"""
        with self.assertRaises(PlatformValidationError):
            self.db_manager.switch_platform_context(
                user_id=999,  # Non-existent user
                platform_connection_id=1
            )

if __name__ == '__main__':
    unittest.main()