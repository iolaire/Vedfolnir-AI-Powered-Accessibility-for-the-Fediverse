#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import logging

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detached_instance_handler import DetachedInstanceHandler, create_global_detached_instance_handler, get_detached_instance_handler
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError
from models import User, PlatformConnection


class MockSessionManager:
    """Mock session manager for testing"""
    
    def __init__(self):
        self.mock_session = Mock()
        
    def get_request_session(self):
        return self.mock_session


class MockSQLAlchemyObject:
    """Mock SQLAlchemy object for testing"""
    
    def __init__(self, id=1, name="test_object"):
        self.id = id
        self.name = name
        self.test_relationship = []


class TestDetachedInstanceHandler(unittest.TestCase):
    """Test DetachedInstanceHandler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session_manager = MockSessionManager()
        self.handler = DetachedInstanceHandler(self.session_manager)
        self.mock_obj = MockSQLAlchemyObject()
        
        # Suppress logging during tests
        logging.getLogger('detached_instance_handler').setLevel(logging.CRITICAL)
    
    def test_handler_initialization(self):
        """Test DetachedInstanceHandler initialization"""
        self.assertEqual(self.handler.session_manager, self.session_manager)
        self.assertIsNotNone(self.handler.logger)
    
    def test_handle_detached_instance_merge_success(self):
        """Test successful object recovery using merge"""
        # Setup mock session to return merged object
        merged_obj = MockSQLAlchemyObject(id=1, name="merged_object")
        self.session_manager.mock_session.merge.return_value = merged_obj
        
        result = self.handler.handle_detached_instance(self.mock_obj)
        
        self.assertEqual(result, merged_obj)
        self.session_manager.mock_session.merge.assert_called_once_with(self.mock_obj)
    
    def test_handle_detached_instance_merge_fails_reload_success(self):
        """Test object recovery using reload when merge fails"""
        # Setup mock session: merge fails, query succeeds
        self.session_manager.mock_session.merge.side_effect = InvalidRequestError("Merge failed")
        
        reloaded_obj = MockSQLAlchemyObject(id=1, name="reloaded_object")
        mock_query = Mock()
        mock_query.get.return_value = reloaded_obj
        self.session_manager.mock_session.query.return_value = mock_query
        
        result = self.handler.handle_detached_instance(self.mock_obj)
        
        self.assertEqual(result, reloaded_obj)
        self.session_manager.mock_session.merge.assert_called_once_with(self.mock_obj)
        self.session_manager.mock_session.query.assert_called_once_with(MockSQLAlchemyObject)
        mock_query.get.assert_called_once_with(1)
    
    def test_handle_detached_instance_both_fail(self):
        """Test exception when both merge and reload fail"""
        # Setup mock session: both merge and query fail
        self.session_manager.mock_session.merge.side_effect = InvalidRequestError("Merge failed")
        
        mock_query = Mock()
        mock_query.get.return_value = None  # Object not found
        self.session_manager.mock_session.query.return_value = mock_query
        
        with self.assertRaises(InvalidRequestError):
            self.handler.handle_detached_instance(self.mock_obj)
    
    def test_handle_detached_instance_no_id(self):
        """Test exception when object has no id for reload"""
        # Create object without id
        obj_without_id = MockSQLAlchemyObject()
        obj_without_id.id = None
        
        # Setup mock session: merge fails
        self.session_manager.mock_session.merge.side_effect = InvalidRequestError("Merge failed")
        
        with self.assertRaises(InvalidRequestError):
            self.handler.handle_detached_instance(obj_without_id)
    
    def test_handle_detached_instance_custom_session(self):
        """Test using custom session instead of request session"""
        custom_session = Mock()
        merged_obj = MockSQLAlchemyObject(id=1, name="custom_merged")
        custom_session.merge.return_value = merged_obj
        
        result = self.handler.handle_detached_instance(self.mock_obj, custom_session)
        
        self.assertEqual(result, merged_obj)
        custom_session.merge.assert_called_once_with(self.mock_obj)
        # Request session should not be called
        self.session_manager.mock_session.merge.assert_not_called()
    
    def test_safe_access_success(self):
        """Test successful safe attribute access"""
        result = self.handler.safe_access(self.mock_obj, 'name')
        self.assertEqual(result, "test_object")
    
    def test_safe_access_detached_instance_error_recovery(self):
        """Test safe access with DetachedInstanceError recovery"""
        # Create mock object that raises DetachedInstanceError on attribute access
        mock_obj = Mock()
        mock_obj.id = 1
        
        # Configure __getattribute__ to raise DetachedInstanceError for 'name'
        def mock_getattribute(name):
            if name == 'name':
                raise DetachedInstanceError("Detached")
            elif name == 'id':
                return 1
            else:
                return Mock.return_value
        
        mock_obj.__getattribute__ = mock_getattribute
        
        # Setup recovery
        recovered_obj = Mock()
        recovered_obj.name = "recovered_name"
        self.session_manager.mock_session.merge.return_value = recovered_obj
        
        result = self.handler.safe_access(mock_obj, 'name')
        
        self.assertEqual(result, "recovered_name")
    
    def test_safe_access_attribute_error(self):
        """Test safe access with AttributeError returns default"""
        result = self.handler.safe_access(self.mock_obj, 'nonexistent_attr', 'default_value')
        self.assertEqual(result, 'default_value')
    
    def test_safe_access_recovery_fails(self):
        """Test safe access when recovery fails returns default"""
        # Create mock object that raises DetachedInstanceError
        mock_obj = Mock()
        mock_obj.id = 1
        
        # Configure __getattribute__ to raise DetachedInstanceError for 'name'
        def mock_getattribute(name):
            if name == 'name':
                raise DetachedInstanceError("Detached")
            elif name == 'id':
                return 1
            else:
                return Mock.return_value
        
        mock_obj.__getattribute__ = mock_getattribute
        
        # Setup recovery to fail
        self.session_manager.mock_session.merge.side_effect = Exception("Recovery failed")
        
        result = self.handler.safe_access(mock_obj, 'name', 'default_value')
        
        self.assertEqual(result, 'default_value')
    
    def test_safe_relationship_access_success(self):
        """Test successful safe relationship access"""
        self.mock_obj.test_relationship = ['item1', 'item2']
        
        result = self.handler.safe_relationship_access(self.mock_obj, 'test_relationship')
        self.assertEqual(result, ['item1', 'item2'])
    
    def test_safe_relationship_access_detached_instance_error(self):
        """Test safe relationship access with DetachedInstanceError recovery"""
        # Create mock object that raises DetachedInstanceError on relationship access
        mock_obj = Mock()
        mock_obj.id = 1
        
        # Configure __getattribute__ to raise DetachedInstanceError for 'test_relationship'
        def mock_getattribute(name):
            if name == 'test_relationship':
                raise DetachedInstanceError("Detached")
            elif name == 'id':
                return 1
            else:
                return Mock.return_value
        
        mock_obj.__getattribute__ = mock_getattribute
        
        # Setup recovery
        recovered_obj = Mock()
        recovered_obj.test_relationship = ['recovered_item']
        self.session_manager.mock_session.merge.return_value = recovered_obj
        
        result = self.handler.safe_relationship_access(mock_obj, 'test_relationship')
        
        self.assertEqual(result, ['recovered_item'])
    
    def test_safe_relationship_access_default_empty_list(self):
        """Test safe relationship access returns empty list by default"""
        result = self.handler.safe_relationship_access(self.mock_obj, 'nonexistent_relationship')
        self.assertEqual(result, [])
    
    def test_safe_relationship_access_custom_default(self):
        """Test safe relationship access with custom default"""
        custom_default = ['custom', 'default']
        result = self.handler.safe_relationship_access(self.mock_obj, 'nonexistent_relationship', custom_default)
        self.assertEqual(result, custom_default)
    
    def test_ensure_attached_already_in_session(self):
        """Test ensure_attached when object is already in session"""
        # Mock session to contain the object
        self.session_manager.mock_session.__contains__ = Mock(return_value=True)
        
        result = self.handler.ensure_attached(self.mock_obj)
        
        self.assertEqual(result, self.mock_obj)
        # Should not attempt recovery
        self.session_manager.mock_session.merge.assert_not_called()
    
    def test_ensure_attached_not_in_session(self):
        """Test ensure_attached when object is not in session"""
        # Mock session to not contain the object
        self.session_manager.mock_session.__contains__ = Mock(return_value=False)
        
        # Setup recovery
        recovered_obj = MockSQLAlchemyObject(id=1, name="recovered")
        self.session_manager.mock_session.merge.return_value = recovered_obj
        
        result = self.handler.ensure_attached(self.mock_obj)
        
        self.assertEqual(result, recovered_obj)
        self.session_manager.mock_session.merge.assert_called_once_with(self.mock_obj)
    
    def test_ensure_attached_recovery_fails(self):
        """Test ensure_attached when recovery fails returns original object"""
        # Mock session to not contain the object
        self.session_manager.mock_session.__contains__ = Mock(return_value=False)
        
        # Setup recovery to fail
        self.session_manager.mock_session.merge.side_effect = Exception("Recovery failed")
        
        result = self.handler.ensure_attached(self.mock_obj)
        
        self.assertEqual(result, self.mock_obj)  # Should return original object
    
    def test_ensure_attached_custom_session(self):
        """Test ensure_attached with custom session"""
        custom_session = Mock()
        custom_session.__contains__ = Mock(return_value=False)
        
        recovered_obj = MockSQLAlchemyObject(id=1, name="custom_recovered")
        custom_session.merge.return_value = recovered_obj
        
        result = self.handler.ensure_attached(self.mock_obj, custom_session)
        
        self.assertEqual(result, recovered_obj)
        custom_session.merge.assert_called_once_with(self.mock_obj)


class TestGlobalErrorHandlers(unittest.TestCase):
    """Test global error handler creation and functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Mock()
        self.app.view_functions = {'index': Mock(), 'login': Mock()}
        self.session_manager = MockSessionManager()
        
        # Mock Flask functions
        self.mock_request = Mock()
        self.mock_request.endpoint = 'dashboard'
        
        # Suppress logging during tests
        logging.getLogger('detached_instance_handler').setLevel(logging.CRITICAL)
    
    def test_create_global_detached_instance_handler(self):
        """Test creation of global error handlers"""
        # Create handler without Flask context dependencies
        handler = create_global_detached_instance_handler(self.app, self.session_manager)
        
        # Verify handler is created and stored
        self.assertIsInstance(handler, DetachedInstanceHandler)
        self.assertEqual(self.app.detached_instance_handler, handler)
        
        # Verify error handlers are registered
        self.app.errorhandler.assert_any_call(DetachedInstanceError)
        self.app.errorhandler.assert_any_call(SQLAlchemyError)
    
    def test_get_detached_instance_handler_success(self):
        """Test successful retrieval of handler"""
        mock_handler = Mock()
        
        with patch('detached_instance_handler.current_app') as mock_current_app:
            mock_current_app.detached_instance_handler = mock_handler
            
            result = get_detached_instance_handler()
            
            self.assertEqual(result, mock_handler)
    
    def test_get_detached_instance_handler_not_configured(self):
        """Test exception when handler is not configured"""
        with patch('detached_instance_handler.current_app') as mock_current_app:
            # Configure mock to not have the handler attribute
            type(mock_current_app).detached_instance_handler = Mock(side_effect=AttributeError)
            
            with self.assertRaises(RuntimeError) as context:
                get_detached_instance_handler()
            
            self.assertIn("DetachedInstanceHandler not configured", str(context.exception))


class TestIntegrationWithMockUsers(unittest.TestCase):
    """Test DetachedInstanceHandler integration with mock users"""
    
    def setUp(self):
        """Set up test fixtures with mock user management"""
        self.session_manager = MockSessionManager()
        self.handler = DetachedInstanceHandler(self.session_manager)
        
        # Create mock user and platform
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 1
        self.mock_user.username = "test_user"
        self.mock_user.email = "test@example.com"
        
        self.mock_platform = Mock(spec=PlatformConnection)
        self.mock_platform.id = 1
        self.mock_platform.name = "Test Platform"
        self.mock_platform.platform_type = "pixelfed"
        
        # Suppress logging during tests
        logging.getLogger('detached_instance_handler').setLevel(logging.CRITICAL)
    
    def test_handle_detached_user_object(self):
        """Test handling detached User object"""
        # Setup recovery
        recovered_user = Mock(spec=User)
        recovered_user.id = 1
        recovered_user.username = "recovered_user"
        self.session_manager.mock_session.merge.return_value = recovered_user
        
        result = self.handler.handle_detached_instance(self.mock_user)
        
        self.assertEqual(result, recovered_user)
        self.session_manager.mock_session.merge.assert_called_once_with(self.mock_user)
    
    def test_handle_detached_platform_object(self):
        """Test handling detached PlatformConnection object"""
        # Setup recovery
        recovered_platform = Mock(spec=PlatformConnection)
        recovered_platform.id = 1
        recovered_platform.name = "Recovered Platform"
        self.session_manager.mock_session.merge.return_value = recovered_platform
        
        result = self.handler.handle_detached_instance(self.mock_platform)
        
        self.assertEqual(result, recovered_platform)
        self.session_manager.mock_session.merge.assert_called_once_with(self.mock_platform)
    
    def test_safe_access_user_attributes(self):
        """Test safe access to user attributes"""
        # Test successful access
        result = self.handler.safe_access(self.mock_user, 'username')
        self.assertEqual(result, "test_user")
        
        # Test with default value
        result = self.handler.safe_access(self.mock_user, 'nonexistent', 'default')
        self.assertEqual(result, 'default')
    
    def test_safe_access_platform_attributes(self):
        """Test safe access to platform attributes"""
        # Test successful access
        result = self.handler.safe_access(self.mock_platform, 'name')
        self.assertEqual(result, "Test Platform")
        
        # Test platform type
        result = self.handler.safe_access(self.mock_platform, 'platform_type')
        self.assertEqual(result, "pixelfed")
    
    def test_safe_relationship_access_user_platforms(self):
        """Test safe access to user platform relationships"""
        # Setup user with platforms relationship
        self.mock_user.platform_connections = [self.mock_platform]
        
        result = self.handler.safe_relationship_access(self.mock_user, 'platform_connections')
        self.assertEqual(result, [self.mock_platform])
    
    def test_ensure_attached_with_mock_objects(self):
        """Test ensure_attached with mock user and platform objects"""
        # Test with user not in session
        self.session_manager.mock_session.__contains__ = Mock(return_value=False)
        
        recovered_user = Mock(spec=User)
        self.session_manager.mock_session.merge.return_value = recovered_user
        
        result = self.handler.ensure_attached(self.mock_user)
        
        self.assertEqual(result, recovered_user)
        self.session_manager.mock_session.merge.assert_called_once_with(self.mock_user)


if __name__ == '__main__':
    unittest.main()