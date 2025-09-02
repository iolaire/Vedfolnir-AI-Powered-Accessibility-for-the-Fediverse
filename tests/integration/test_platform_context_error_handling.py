# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test error handling for PlatformContextManager

This module tests that the PlatformContextManager properly handles invalid operations
and provides appropriate error messages for various failure scenarios.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from platform_context import PlatformContextManager, PlatformContext, PlatformContextError
from models import User, PlatformConnection

class TestPlatformContextErrorHandling(unittest.TestCase):
    """Test error handling for PlatformContextManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session = Mock(spec=Session)
        self.context_manager = PlatformContextManager(self.session)
        
        # Create mock users
        self.active_user = Mock(spec=User)
        self.active_user.id = 1
        self.active_user.username = "testuser"
        self.active_user.is_active = True
        
        self.inactive_user = Mock(spec=User)
        self.inactive_user.id = 2
        self.inactive_user.username = "inactiveuser"
        self.inactive_user.is_active = False
        
        # Create mock platform connections
        self.active_platform = Mock(spec=PlatformConnection)
        self.active_platform.id = 1
        self.active_platform.name = "Test Platform"
        self.active_platform.platform_type = "pixelfed"
        self.active_platform.instance_url = "https://test.example.com"
        self.active_platform.username = "testuser"
        self.active_platform.is_active = True
        self.active_platform.is_default = True
        
        self.inactive_platform = Mock(spec=PlatformConnection)
        self.inactive_platform.id = 2
        self.inactive_platform.name = "Inactive Platform"
        self.inactive_platform.platform_type = "mastodon"
        self.inactive_platform.instance_url = "https://inactive.example.com"
        self.inactive_platform.username = "testuser"
        self.inactive_platform.is_active = False
        self.inactive_platform.is_default = False
        
        # Set up user platform relationships
        self.active_user.get_default_platform.return_value = self.active_platform
        self.active_user.get_active_platforms.return_value = [self.active_platform]
        
        self.inactive_user.get_default_platform.return_value = None
        self.inactive_user.get_active_platforms.return_value = []
    
    def test_set_context_with_nonexistent_user(self):
        """Test setting context with non-existent user ID"""
        # Mock query to return None (user not found)
        self.session.query.return_value.get.return_value = None
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_context(user_id=999)
        
        self.assertIn("User with ID 999 not found", str(cm.exception))
    
    def test_set_context_with_inactive_user(self):
        """Test setting context with inactive user"""
        # Mock query to return inactive user
        self.session.query.return_value.get.return_value = self.inactive_user
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_context(user_id=2)
        
        self.assertIn("User inactiveuser is not active", str(cm.exception))
    
    def test_set_context_with_nonexistent_platform(self):
        """Test setting context with non-existent platform connection ID"""
        # Mock user query to return active user
        user_query = Mock()
        user_query.get.return_value = self.active_user
        
        # Mock platform query to return None (platform not found)
        platform_query = Mock()
        platform_filter = Mock()
        platform_filter.first.return_value = None  # Platform not found
        platform_query.filter_by.return_value = platform_filter
        
        # Set up query mock to return different mocks for different calls
        self.session.query.side_effect = [user_query, platform_query]
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_context(user_id=1, platform_connection_id=999)
        
        self.assertIn("Platform connection 999 not found or not active for user testuser", str(cm.exception))
    
    def test_set_context_with_inactive_platform(self):
        """Test setting context with inactive platform connection"""
        # Mock user query to return active user
        user_query = Mock()
        user_query.get.return_value = self.active_user
        
        # Mock platform query to return None (inactive platform filtered out)
        platform_query = Mock()
        platform_filter = Mock()
        platform_filter.first.return_value = None  # Inactive platform filtered out
        platform_query.filter_by.return_value = platform_filter
        
        # Set up query mock to return different mocks for different calls
        self.session.query.side_effect = [user_query, platform_query]
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_context(user_id=1, platform_connection_id=2)
        
        self.assertIn("Platform connection 2 not found or not active for user testuser", str(cm.exception))
    
    def test_set_context_with_user_having_no_platforms(self):
        """Test setting context with user who has no active platforms"""
        # Create user with no platforms
        user_no_platforms = Mock(spec=User)
        user_no_platforms.id = 3
        user_no_platforms.username = "noplatforms"
        user_no_platforms.is_active = True
        user_no_platforms.get_default_platform.return_value = None
        user_no_platforms.get_active_platforms.return_value = []
        
        # Mock user query to return user with no platforms
        self.session.query.return_value.get.return_value = user_no_platforms
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_context(user_id=3)
        
        self.assertIn("No active platform connections found for user noplatforms", str(cm.exception))
    
    def test_set_context_with_database_error(self):
        """Test setting context when database error occurs"""
        # Mock database error
        self.session.query.side_effect = SQLAlchemyError("Database connection failed")
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_context(user_id=1)
        
        self.assertIn("Failed to set platform context", str(cm.exception))
    
    def test_require_context_without_context_set(self):
        """Test requiring context when no context is set"""
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.require_context()
        
        self.assertIn("No platform context set", str(cm.exception))
    
    def test_require_context_with_invalid_context(self):
        """Test requiring context when context is invalid"""
        # Set up invalid context (missing platform connection)
        invalid_context = PlatformContext(user_id=1)
        invalid_context.user = self.active_user
        # Don't set platform_connection_id or platform_connection
        
        self.context_manager._local.context = invalid_context
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.require_context()
        
        self.assertIn("Platform context is invalid or incomplete", str(cm.exception))
    
    def test_get_platform_filter_criteria_without_context(self):
        """Test getting platform filter criteria without context"""
        from models import Post
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.get_platform_filter_criteria(Post)
        
        self.assertIn("No platform context set", str(cm.exception))
    
    def test_inject_platform_data_without_context(self):
        """Test injecting platform data without context"""
        test_data = {'post_id': 'test123'}
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.inject_platform_data(test_data)
        
        self.assertIn("No platform context set", str(cm.exception))
    
    def test_create_activitypub_config_without_context(self):
        """Test creating ActivityPub config without context"""
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.create_activitypub_config()
        
        self.assertIn("No platform context set", str(cm.exception))
    
    def test_create_activitypub_config_with_invalid_platform(self):
        """Test creating ActivityPub config when platform connection fails"""
        # Set up valid context
        self.session.query.return_value.get.return_value = self.active_user
        self.session.query.return_value.filter_by.return_value.first.return_value = self.active_platform
        
        # Mock platform connection to_activitypub_config to fail
        self.active_platform.to_activitypub_config.side_effect = Exception("Invalid credentials")
        
        self.context_manager.set_context(user_id=1, platform_connection_id=1)
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.create_activitypub_config()
        
        self.assertIn("Failed to create ActivityPub config", str(cm.exception))
    
    def test_switch_platform_without_context(self):
        """Test switching platform without existing context"""
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.switch_platform(platform_connection_id=1)
        
        self.assertIn("No platform context set", str(cm.exception))
    
    def test_switch_platform_to_nonexistent_platform(self):
        """Test switching to non-existent platform"""
        # Set up initial context with proper mocking
        user_query = Mock()
        user_query.get.return_value = self.active_user
        
        platform_query = Mock()
        platform_filter = Mock()
        platform_filter.first.return_value = self.active_platform
        platform_query.filter_by.return_value = platform_filter
        
        # Mock platform query for switch to return None
        switch_query = Mock()
        switch_filter = Mock()
        switch_filter.first.return_value = None
        switch_query.filter_by.return_value = switch_filter
        
        self.session.query.side_effect = [user_query, platform_query, switch_query]
        
        self.context_manager.set_context(user_id=1, platform_connection_id=1)
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.switch_platform(platform_connection_id=999)
        
        self.assertIn("Platform connection 999 not found or not accessible", str(cm.exception))
    
    def test_switch_platform_to_other_users_platform(self):
        """Test switching to platform belonging to another user"""
        # Set up initial context with proper mocking
        user_query = Mock()
        user_query.get.return_value = self.active_user
        
        platform_query = Mock()
        platform_filter = Mock()
        platform_filter.first.return_value = self.active_platform
        platform_query.filter_by.return_value = platform_filter
        
        # Mock platform query for switch to return None (simulating access denied)
        switch_query = Mock()
        switch_filter = Mock()
        switch_filter.first.return_value = None
        switch_query.filter_by.return_value = switch_filter
        
        self.session.query.side_effect = [user_query, platform_query, switch_query]
        
        self.context_manager.set_context(user_id=1, platform_connection_id=1)
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.switch_platform(platform_connection_id=2)
        
        self.assertIn("Platform connection 2 not found or not accessible", str(cm.exception))
    
    def test_set_default_platform_without_context(self):
        """Test setting default platform without context"""
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_default_platform(platform_connection_id=1)
        
        self.assertIn("No platform context set", str(cm.exception))
    
    def test_set_default_platform_nonexistent(self):
        """Test setting non-existent platform as default"""
        # Set up initial context
        self.session.query.return_value.get.return_value = self.active_user
        self.session.query.return_value.filter_by.return_value.first.return_value = self.active_platform
        
        self.context_manager.set_context(user_id=1, platform_connection_id=1)
        
        # Mock platform query to return None for the platform to set as default
        self.session.query.return_value.filter_by.return_value.first.return_value = None
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_default_platform(platform_connection_id=999)
        
        self.assertIn("Platform connection 999 not found or not accessible", str(cm.exception))
    
    def test_set_default_platform_database_error(self):
        """Test setting default platform when database error occurs"""
        # Set up initial context
        self.session.query.return_value.get.return_value = self.active_user
        self.session.query.return_value.filter_by.return_value.first.return_value = self.active_platform
        
        self.context_manager.set_context(user_id=1, platform_connection_id=1)
        
        # Mock database error during update
        self.session.commit.side_effect = SQLAlchemyError("Database error")
        
        with self.assertRaises(PlatformContextError) as cm:
            self.context_manager.set_default_platform(platform_connection_id=1)
        
        self.assertIn("Failed to set default platform", str(cm.exception))
        # Verify rollback was called
        self.session.rollback.assert_called_once()
    
    def test_test_platform_connection_nonexistent(self):
        """Test testing non-existent platform connection"""
        # Mock query to return None
        self.session.query.return_value.get.return_value = None
        
        success, message = self.context_manager.test_platform_connection(platform_connection_id=999)
        
        self.assertFalse(success)
        self.assertIn("Platform connection 999 not found", message)
    
    def test_test_platform_connection_with_exception(self):
        """Test testing platform connection when test_connection raises exception"""
        # Set up platform mock
        platform = Mock(spec=PlatformConnection)
        platform.test_connection.side_effect = Exception("Connection failed")
        
        self.session.query.return_value.get.return_value = platform
        
        success, message = self.context_manager.test_platform_connection(platform_connection_id=1)
        
        self.assertFalse(success)
        self.assertEqual("Connection failed", message)
    
    def test_context_scope_exception_handling(self):
        """Test that context_scope properly handles exceptions and restores context"""
        # Set up initial context
        self.session.query.return_value.get.return_value = self.active_user
        self.session.query.return_value.filter_by.return_value.first.return_value = self.active_platform
        
        initial_context = self.context_manager.set_context(user_id=1, platform_connection_id=1)
        
        # Test that exception in context scope restores original context
        try:
            with self.context_manager.context_scope(user_id=1, platform_connection_id=1):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify original context is restored
        current_context = self.context_manager.current_context
        self.assertEqual(current_context.user_id, initial_context.user_id)
        self.assertEqual(current_context.platform_connection_id, initial_context.platform_connection_id)
    
    def test_validate_context_with_no_context(self):
        """Test context validation when no context is set"""
        errors = self.context_manager.validate_context()
        
        self.assertEqual(len(errors), 1)
        self.assertIn("No platform context set", errors[0])
    
    def test_validate_context_with_invalid_context(self):
        """Test context validation with invalid context"""
        # Create invalid context
        invalid_context = PlatformContext(user_id=1)
        # Don't set required fields
        
        self.context_manager._local.context = invalid_context
        
        errors = self.context_manager.validate_context()
        
        # Should have multiple validation errors
        self.assertGreater(len(errors), 1)
        self.assertTrue(any("User object not loaded" in error for error in errors))
        self.assertTrue(any("No platform connection ID" in error for error in errors))
    
    def test_validate_context_with_inactive_user(self):
        """Test context validation with inactive user"""
        # Create context with inactive user
        context = PlatformContext(user_id=2)
        context.user = self.inactive_user
        context.platform_connection_id = 1
        context.platform_connection = self.active_platform
        
        self.context_manager._local.context = context
        
        errors = self.context_manager.validate_context()
        
        self.assertTrue(any("User is not active" in error for error in errors))
    
    def test_validate_context_with_inactive_platform(self):
        """Test context validation with inactive platform"""
        # Create context with inactive platform
        context = PlatformContext(user_id=1)
        context.user = self.active_user
        context.platform_connection_id = 2
        context.platform_connection = self.inactive_platform
        
        self.context_manager._local.context = context
        
        errors = self.context_manager.validate_context()
        
        self.assertTrue(any("Platform connection is not active" in error for error in errors))
    
    def test_invalid_user_id_in_context_creation(self):
        """Test creating context with invalid user ID"""
        with self.assertRaises(ValueError) as cm:
            PlatformContext(user_id=None)
        
        self.assertIn("user_id is required", str(cm.exception))
        
        with self.assertRaises(ValueError) as cm:
            PlatformContext(user_id=0)
        
        self.assertIn("user_id is required", str(cm.exception))

if __name__ == '__main__':
    unittest.main()