#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch
import sys
import os
import logging

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detached_instance_handler import DetachedInstanceHandler, create_global_detached_instance_handler
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError

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

class TestDetachedInstanceHandlerSimple(unittest.TestCase):
    """Test DetachedInstanceHandler core functionality (simplified)"""
    
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
    
    def test_safe_access_attribute_error(self):
        """Test safe access with AttributeError returns default"""
        result = self.handler.safe_access(self.mock_obj, 'nonexistent_attr', 'default_value')
        self.assertEqual(result, 'default_value')
    
    def test_safe_access_no_default(self):
        """Test safe access without default returns None"""
        result = self.handler.safe_access(self.mock_obj, 'nonexistent_attr')
        self.assertIsNone(result)
    
    def test_safe_relationship_access_success(self):
        """Test successful safe relationship access"""
        self.mock_obj.test_relationship = ['item1', 'item2']
        
        result = self.handler.safe_relationship_access(self.mock_obj, 'test_relationship')
        self.assertEqual(result, ['item1', 'item2'])
    
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

class TestGlobalErrorHandlersSimple(unittest.TestCase):
    """Test global error handler creation (simplified)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Mock()
        self.app.view_functions = {'index': Mock(), 'login': Mock()}
        self.session_manager = MockSessionManager()
        
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
    
    def test_handler_methods_exist(self):
        """Test that all required handler methods exist"""
        handler = DetachedInstanceHandler(self.session_manager)
        
        # Check that all required methods exist
        required_methods = [
            'handle_detached_instance',
            'safe_access',
            'safe_relationship_access',
            'ensure_attached'
        ]
        
        for method_name in required_methods:
            self.assertTrue(hasattr(handler, method_name))
            self.assertTrue(callable(getattr(handler, method_name)))
    
    def test_handler_with_different_object_types(self):
        """Test handler works with different mock object types"""
        handler = DetachedInstanceHandler(self.session_manager)
        
        # Test with different mock objects
        user_obj = Mock()
        user_obj.id = 1
        user_obj.username = "test_user"
        
        platform_obj = Mock()
        platform_obj.id = 2
        platform_obj.name = "test_platform"
        
        # Setup recovery
        self.session_manager.mock_session.merge.side_effect = [user_obj, platform_obj]
        
        # Test recovery for both objects
        result1 = handler.handle_detached_instance(user_obj)
        result2 = handler.handle_detached_instance(platform_obj)
        
        self.assertEqual(result1, user_obj)
        self.assertEqual(result2, platform_obj)
    
    def test_safe_access_with_various_attributes(self):
        """Test safe access with various attribute types"""
        handler = DetachedInstanceHandler(self.session_manager)
        
        # Create object with different attribute types
        test_obj = Mock()
        test_obj.string_attr = "test_string"
        test_obj.int_attr = 42
        test_obj.bool_attr = True
        test_obj.list_attr = [1, 2, 3]
        test_obj.dict_attr = {'key': 'value'}
        
        # Test accessing different attribute types
        self.assertEqual(handler.safe_access(test_obj, 'string_attr'), "test_string")
        self.assertEqual(handler.safe_access(test_obj, 'int_attr'), 42)
        self.assertEqual(handler.safe_access(test_obj, 'bool_attr'), True)
        self.assertEqual(handler.safe_access(test_obj, 'list_attr'), [1, 2, 3])
        self.assertEqual(handler.safe_access(test_obj, 'dict_attr'), {'key': 'value'})
    
    def test_error_handling_robustness(self):
        """Test that handler is robust against various error conditions"""
        handler = DetachedInstanceHandler(self.session_manager)
        
        # Test with None object
        result = handler.safe_access(None, 'any_attr', 'default')
        self.assertEqual(result, 'default')
        
        # Test with object without id
        obj_no_id = Mock()
        del obj_no_id.id  # Remove id attribute
        
        # Should handle gracefully
        result = handler.safe_access(obj_no_id, 'name', 'default')
        # Should return the actual attribute or default
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()