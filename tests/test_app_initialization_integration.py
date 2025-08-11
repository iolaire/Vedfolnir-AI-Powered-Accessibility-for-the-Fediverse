#!/usr/bin/env python3

"""
Integration Tests for Web Application Initialization

This module tests the integration of the app initialization with the existing web application.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_initialization import (
    create_session_managed_app,
    validate_session_management_setup,
    get_session_management_info
)


class MockConfig:
    """Mock configuration for testing"""
    def __init__(self):
        self.webapp = Mock()
        self.webapp.secret_key = 'test-secret-key'
        self.webapp.host = '127.0.0.1'
        self.webapp.port = 5000
        self.webapp.debug = False
        
        self.storage = Mock()
        self.storage.database_url = 'sqlite:///:memory:'
        
        self.ollama = Mock()
        self.ollama.url = 'http://localhost:11434'
        self.ollama.model_name = 'llava:7b'
        self.ollama.timeout = 30


class TestAppInitializationIntegration(unittest.TestCase):
    """Integration test cases for app initialization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig()
    
    @patch('app_initialization.DatabaseManager')
    @patch('app_initialization.RequestScopedSessionManager')
    @patch('app_initialization.DatabaseContextMiddleware')
    @patch('app_initialization.LoginManager')
    @patch('app_initialization.create_global_detached_instance_handler')
    @patch('app_initialization.create_safe_template_context_processor')
    def test_create_session_managed_app_integration(self, mock_template_processor, 
                                                   mock_error_handler, mock_login_manager,
                                                   mock_middleware, mock_session_manager, 
                                                   mock_db_manager):
        """Test creating a session-managed app with all components"""
        # Create app using factory function
        app = create_session_managed_app(self.config)
        
        # Verify app was created
        self.assertIsNotNone(app)
        self.assertEqual(app.config['SECRET_KEY'], 'test-secret-key')
        
        # Verify all components were initialized
        mock_db_manager.assert_called_once_with(self.config)
        mock_session_manager.assert_called_once()
        mock_middleware.assert_called_once()
        mock_login_manager.assert_called_once()
        mock_error_handler.assert_called_once()
        mock_template_processor.assert_called_once()
        
        # Verify components are registered with app
        self.assertTrue(hasattr(app, 'request_session_manager'))
        self.assertTrue(hasattr(app, 'database_context_middleware'))
        self.assertTrue(hasattr(app, 'detached_instance_handler'))
        self.assertTrue(hasattr(app, 'db_manager'))
    
    @patch('app_initialization.DatabaseManager')
    @patch('app_initialization.RequestScopedSessionManager')
    @patch('app_initialization.DatabaseContextMiddleware')
    @patch('app_initialization.LoginManager')
    @patch('app_initialization.create_global_detached_instance_handler')
    @patch('app_initialization.create_safe_template_context_processor')
    def test_validate_session_management_integration(self, mock_template_processor, 
                                                    mock_error_handler, mock_login_manager,
                                                    mock_middleware, mock_session_manager, 
                                                    mock_db_manager):
        """Test validation of session management setup"""
        # Create app
        app = create_session_managed_app(self.config)
        
        # Validate session management setup
        validation_result = validate_session_management_setup(app)
        
        # Debug: print validation result if it fails
        if not validation_result['valid']:
            print(f"Validation errors: {validation_result['errors']}")
            print(f"Components found: {validation_result['components_found']}")
        
        # Should pass validation
        self.assertTrue(validation_result['valid'])
        self.assertEqual(len(validation_result['errors']), 0)
        
        # All components should be found
        self.assertTrue(validation_result['components_found']['request_session_manager'])
        self.assertTrue(validation_result['components_found']['database_context_middleware'])
        self.assertTrue(validation_result['components_found']['detached_instance_handler'])
        self.assertTrue(validation_result['components_found']['db_manager'])
        self.assertTrue(validation_result['components_found']['login_manager'])
        self.assertTrue(validation_result['components_found']['user_loader'])
    
    @patch('app_initialization.DatabaseManager')
    @patch('app_initialization.RequestScopedSessionManager')
    @patch('app_initialization.DatabaseContextMiddleware')
    @patch('app_initialization.LoginManager')
    @patch('app_initialization.create_global_detached_instance_handler')
    @patch('app_initialization.create_safe_template_context_processor')
    def test_get_session_management_info_integration(self, mock_template_processor, 
                                                    mock_error_handler, mock_login_manager,
                                                    mock_middleware, mock_session_manager, 
                                                    mock_db_manager):
        """Test getting session management info"""
        # Setup mocks to return status info
        mock_session_manager_instance = Mock()
        mock_session_manager_instance.get_session_info.return_value = {'active': True}
        mock_session_manager.return_value = mock_session_manager_instance
        
        mock_middleware_instance = Mock()
        mock_middleware_instance.get_middleware_status.return_value = {'status': 'active'}
        mock_middleware.return_value = mock_middleware_instance
        
        # Create app
        app = create_session_managed_app(self.config)
        
        # Get session management info
        info = get_session_management_info(app)
        
        # Should indicate session management is active
        self.assertTrue(info['session_management_active'])
        self.assertEqual(info['session_manager_status'], {'active': True})
        self.assertEqual(info['middleware_status'], {'status': 'active'})
        
        # All components should be present
        self.assertTrue(info['components']['request_session_manager']['present'])
        self.assertTrue(info['components']['database_context_middleware']['present'])
        self.assertTrue(info['components']['detached_instance_handler']['present'])
        self.assertTrue(info['components']['db_manager']['present'])
    
    def test_config_compatibility(self):
        """Test that the mock config is compatible with the app initialization"""
        # Verify config has all required attributes
        self.assertTrue(hasattr(self.config, 'webapp'))
        self.assertTrue(hasattr(self.config.webapp, 'secret_key'))
        self.assertTrue(hasattr(self.config, 'storage'))
        self.assertTrue(hasattr(self.config.storage, 'database_url'))
        
        # Verify config values are reasonable
        self.assertIsNotNone(self.config.webapp.secret_key)
        self.assertGreater(len(self.config.webapp.secret_key), 10)
        self.assertIn('sqlite', self.config.storage.database_url)


class TestAppInitializationErrorHandling(unittest.TestCase):
    """Test error handling in app initialization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MockConfig()
    
    @patch('app_initialization.DatabaseManager')
    def test_database_manager_initialization_error(self, mock_db_manager):
        """Test handling of database manager initialization error"""
        # Setup mock to raise exception
        mock_db_manager.side_effect = Exception("Database connection failed")
        
        # Should raise exception during app creation
        with self.assertRaises(Exception) as context:
            create_session_managed_app(self.config)
        
        self.assertIn("Database connection failed", str(context.exception))
    
    @patch('app_initialization.DatabaseManager')
    @patch('app_initialization.RequestScopedSessionManager')
    def test_session_manager_initialization_error(self, mock_session_manager, mock_db_manager):
        """Test handling of session manager initialization error"""
        # Setup mock to raise exception
        mock_session_manager.side_effect = Exception("Session manager failed")
        
        # Should raise exception during app creation
        with self.assertRaises(Exception) as context:
            create_session_managed_app(self.config)
        
        self.assertIn("Session manager failed", str(context.exception))
    
    @patch('app_initialization.DatabaseManager')
    @patch('app_initialization.RequestScopedSessionManager')
    @patch('app_initialization.DatabaseContextMiddleware')
    def test_middleware_initialization_error(self, mock_middleware, mock_session_manager, mock_db_manager):
        """Test handling of middleware initialization error"""
        # Setup mock to raise exception
        mock_middleware.side_effect = Exception("Middleware failed")
        
        # Should raise exception during app creation
        with self.assertRaises(Exception) as context:
            create_session_managed_app(self.config)
        
        self.assertIn("Middleware failed", str(context.exception))


if __name__ == '__main__':
    unittest.main()