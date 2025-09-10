# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Page Notification Integration

Comprehensive tests for the Page Notification Integration Manager and WebSocket
connection handling, including unit tests, integration tests, and functionality validation.
"""

import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, session
from dotenv import load_dotenv

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from page_notification_integrator import PageNotificationIntegrator, PageType, PageNotificationConfig
from app.blueprints.api.page_notification_routes import register_page_notification_routes


class TestPageNotificationIntegrator(unittest.TestCase):
    """Test cases for PageNotificationIntegrator"""
    
    def setUp(self):
        """Set up test environment"""
        load_dotenv()
        self.config = Config()
        
        # Create mock components
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        self.mock_notification_manager = Mock()
        
        # Create integrator instance
        self.integrator = PageNotificationIntegrator(
            self.mock_websocket_factory,
            self.mock_auth_handler,
            self.mock_namespace_manager,
            self.mock_notification_manager
        )
    
    def test_page_type_enum(self):
        """Test PageType enum values"""
        expected_types = [
            'user_dashboard', 'caption_processing', 'platform_management',
            'user_profile', 'admin_dashboard', 'user_management',
            'system_health', 'maintenance', 'security_audit'
        ]
        
        actual_types = [pt.value for pt in PageType]
        
        for expected_type in expected_types:
            self.assertIn(expected_type, actual_types)
    
    def test_page_notification_config_creation(self):
        """Test PageNotificationConfig creation"""
        config = PageNotificationConfig(
            page_type=PageType.USER_DASHBOARD,
            enabled_types={'system', 'caption'},
            auto_hide=True,
            max_notifications=5,
            position='top-right'
        )
        
        self.assertEqual(config.page_type, PageType.USER_DASHBOARD)
        self.assertEqual(config.enabled_types, {'system', 'caption'})
        self.assertTrue(config.auto_hide)
        self.assertEqual(config.max_notifications, 5)
        self.assertEqual(config.position, 'top-right')
    
    def test_default_page_configs_setup(self):
        """Test that default page configurations are set up correctly"""
        # Check that default configs exist for all page types
        for page_type in PageType:
            self.assertIn(page_type, self.integrator._page_configs)
            
            config = self.integrator._page_configs[page_type]
            self.assertIsInstance(config, PageNotificationConfig)
            self.assertEqual(config.page_type, page_type)
            self.assertIsInstance(config.enabled_types, set)
            self.assertIsInstance(config.websocket_events, set)
    
    def test_register_page_integration_success(self):
        """Test successful page integration registration"""
        # Mock the _get_current_user_info method to avoid session context issues
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'test_user',
                'role': 'admin',
                'permissions': {'system_management'}
            }
            
            # Register page integration
            result = self.integrator.register_page_integration(
                'test-page-1',
                PageType.USER_DASHBOARD
            )
            
            # Verify result
            self.assertIsInstance(result, dict)
            self.assertEqual(result['page_id'], 'test-page-1')
            self.assertEqual(result['page_type'], 'user_dashboard')
            self.assertIn('notification_config', result)
            self.assertIn('websocket_config', result)
            
            # Verify integration is stored
            self.assertIn('test-page-1', self.integrator._active_integrations)
    
    def test_register_page_integration_permission_denied(self):
        """Test page integration registration with insufficient permissions"""
        # Mock the _get_current_user_info method with insufficient permissions
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'test_user',
                'role': 'viewer',
                'permissions': set()
            }
            
            # Attempt to register admin page
            with self.assertRaises(RuntimeError) as context:
                self.integrator.register_page_integration(
                    'admin-page-1',
                    PageType.ADMIN_DASHBOARD
                )
            
            # Verify the error message contains permission information
            self.assertIn('User lacks permissions', str(context.exception))
    
    def test_initialize_page_notifications_unregistered(self):
        """Test initialization of unregistered page"""
        with self.assertRaises(RuntimeError) as context:
            self.integrator.initialize_page_notifications('unregistered-page')
        
        # Verify the error message contains the expected text
        self.assertIn('Page notification initialization failed', str(context.exception))
    
    def test_initialize_page_notifications_success(self):
        """Test successful page notification initialization"""
        # Mock the _get_current_user_info method
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'test_user',
                'role': 'admin',
                'permissions': {'system_management'}
            }
            
            # Register page first
            self.integrator.register_page_integration(
                'test-page-2',
                PageType.CAPTION_PROCESSING
            )
            
            # Initialize notifications
            result = self.integrator.initialize_page_notifications('test-page-2')
            
            # Verify result
            self.assertIsInstance(result, dict)
            self.assertEqual(result['page_id'], 'test-page-2')
            self.assertEqual(result['status'], 'initialized')
            self.assertIn('websocket_config', result)
            self.assertIn('event_handlers', result)
            self.assertIn('ui_config', result)
    
    def test_setup_websocket_connection(self):
        """Test WebSocket connection setup"""
        # Mock the _get_current_user_info method
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'test_user',
                'role': 'admin',
                'session_id': 'test-session-123'
            }
            
            # Register page first
            self.integrator.register_page_integration(
                'test-page-3',
                PageType.PLATFORM_MANAGEMENT
            )
            
            # Setup WebSocket connection
            result = self.integrator.setup_websocket_connection('test-page-3')
            
            # Verify result
            self.assertIsInstance(result, dict)
            self.assertIn('namespace', result)
            self.assertIn('auth_data', result)
            self.assertIn('transport_options', result)
            self.assertIn('reconnection_config', result)
            self.assertIn('timeout_config', result)
    
    def test_register_event_handlers(self):
        """Test event handler registration"""
        # Mock the _get_current_user_info method
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'test_user',
                'role': 'admin'
            }
            
            # Register page first
            self.integrator.register_page_integration(
                'test-page-4',
                PageType.USER_PROFILE
            )
            
            # Register event handlers
            custom_handlers = {
                'custom_event': 'handleCustomEvent'
            }
            result = self.integrator.register_event_handlers('test-page-4', custom_handlers)
            
            # Verify result
            self.assertIsInstance(result, dict)
            self.assertEqual(result['page_id'], 'test-page-4')
            self.assertIn('handlers', result)
            self.assertIn('middleware', result)
            self.assertIn('custom_event', result['handlers'])
    
    def test_cleanup_page_integration(self):
        """Test page integration cleanup"""
        # Add a mock integration
        self.integrator._active_integrations['test-cleanup'] = {
            'page_id': 'test-cleanup',
            'page_type': 'user_dashboard',
            'websocket_namespace': '/'
        }
        
        # Cleanup integration
        success = self.integrator.cleanup_page_integration('test-cleanup')
        
        # Verify cleanup
        self.assertTrue(success)
        self.assertNotIn('test-cleanup', self.integrator._active_integrations)
    
    def test_get_page_integration_status(self):
        """Test getting page integration status"""
        # Test unregistered page
        status = self.integrator.get_page_integration_status('unregistered')
        self.assertEqual(status['status'], 'not_registered')
        
        # Add a mock integration
        self.integrator._active_integrations['test-status'] = {
            'page_id': 'test-status',
            'page_type': 'admin_dashboard',
            'registered_at': '2025-01-01T00:00:00Z',
            'config': PageNotificationConfig(
                page_type=PageType.ADMIN_DASHBOARD,
                enabled_types={'admin', 'system'},
                auto_hide=False,
                max_notifications=10,
                position='top-center'
            )
        }
        
        # Get status
        status = self.integrator.get_page_integration_status('test-status')
        
        # Verify status
        self.assertEqual(status['status'], 'registered')
        self.assertEqual(status['page_id'], 'test-status')
        self.assertEqual(status['page_type'], 'admin_dashboard')
        self.assertIn('config', status)
    
    def test_get_integration_stats(self):
        """Test getting integration statistics"""
        # Add mock integrations
        self.integrator._active_integrations.update({
            'user-1': {
                'page_type': 'user_dashboard',
                'websocket_namespace': '/',
                'initialized': True,
                'websocket_configured': True,
                'websocket_connected': False
            },
            'admin-1': {
                'page_type': 'admin_dashboard',
                'websocket_namespace': '/admin',
                'initialized': True,
                'websocket_configured': True,
                'websocket_connected': True
            }
        })
        
        # Get stats
        stats = self.integrator.get_integration_stats()
        
        # Verify stats
        self.assertEqual(stats['total_integrations'], 2)
        self.assertEqual(stats['integrations_by_type']['user_dashboard'], 1)
        self.assertEqual(stats['integrations_by_type']['admin_dashboard'], 1)
        self.assertEqual(stats['integrations_by_namespace']['/'], 1)
        self.assertEqual(stats['integrations_by_namespace']['/admin'], 1)
        self.assertEqual(stats['initialized_integrations'], 2)
        self.assertEqual(stats['websocket_configured'], 2)
        self.assertEqual(stats['websocket_connected'], 1)


class TestPageNotificationRoutes(unittest.TestCase):
    """Test cases for page notification routes"""
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Create mock page integrator
        self.mock_integrator = Mock()
        self.app.page_notification_integrator = self.mock_integrator
        
        # Register routes
        register_page_notification_routes(self.app)
        
        # Create test client
        self.client = self.app.test_client()
        
        # Mock CSRF token
        self.csrf_token = 'test-csrf-token'
    
    def test_register_page_integration_success(self):
        """Test successful page registration via API"""
        # Mock integrator response
        self.mock_integrator.register_page_integration.return_value = {
            'page_id': 'api-test-1',
            'page_type': 'user_dashboard',
            'notification_config': {'enabled_types': ['system']},
            'websocket_config': {'namespace': '/'}
        }
        
        # Make request
        with self.app.test_request_context():
            response = self.client.post('/api/notifications/page/register',
                                      json={
                                          'page_id': 'api-test-1',
                                          'page_type': 'user_dashboard'
                                      },
                                      headers={'X-CSRFToken': self.csrf_token})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['page_id'], 'api-test-1')
    
    def test_register_page_integration_invalid_data(self):
        """Test page registration with invalid data"""
        # Make request with missing data
        with self.app.test_request_context():
            response = self.client.post('/api/notifications/page/register',
                                      json={},
                                      headers={'X-CSRFToken': self.csrf_token})
        
        # Verify error response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_initialize_page_notifications_success(self):
        """Test successful page initialization via API"""
        # Mock integrator response
        self.mock_integrator.initialize_page_notifications.return_value = {
            'page_id': 'api-test-2',
            'status': 'initialized',
            'websocket_config': {},
            'event_handlers': {},
            'ui_config': {}
        }
        
        # Make request
        with self.app.test_request_context():
            response = self.client.post('/api/notifications/page/initialize',
                                      json={'page_id': 'api-test-2'},
                                      headers={'X-CSRFToken': self.csrf_token})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'initialized')
    
    def test_get_websocket_config_success(self):
        """Test WebSocket configuration retrieval via API"""
        # Mock integrator response
        self.mock_integrator.setup_websocket_connection.return_value = {
            'namespace': '/',
            'auth_data': {'session_id': 'test-session'},
            'transport_options': {'transports': ['websocket']}
        }
        
        # Make request
        with self.app.test_request_context():
            response = self.client.post('/api/notifications/page/websocket-config',
                                      json={'page_id': 'api-test-3'},
                                      headers={'X-CSRFToken': self.csrf_token})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('websocket_config', data)
    
    def test_get_page_status_success(self):
        """Test page status retrieval via API"""
        # Mock integrator response
        self.mock_integrator.get_page_integration_status.return_value = {
            'page_id': 'api-test-4',
            'status': 'registered',
            'initialized': True,
            'websocket_connected': False
        }
        
        # Make request
        response = self.client.get('/api/notifications/page/status/api-test-4')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'registered')
    
    def test_cleanup_page_integration_success(self):
        """Test page cleanup via API"""
        # Mock integrator response
        self.mock_integrator.cleanup_page_integration.return_value = True
        
        # Make request
        with self.app.test_request_context():
            response = self.client.post('/api/notifications/page/cleanup',
                                      json={'page_id': 'api-test-5'},
                                      headers={'X-CSRFToken': self.csrf_token})
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_get_integration_stats_success(self):
        """Test integration statistics retrieval via API"""
        # Mock integrator response
        self.mock_integrator.get_integration_stats.return_value = {
            'total_integrations': 5,
            'integrations_by_type': {'user_dashboard': 3, 'admin_dashboard': 2},
            'websocket_connected': 4
        }
        
        # Make request
        response = self.client.get('/api/notifications/page/stats')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('stats', data)
        self.assertEqual(data['stats']['total_integrations'], 5)


class TestPageNotificationIntegration(unittest.TestCase):
    """Integration tests for the complete page notification system"""
    
    def setUp(self):
        """Set up integration test environment"""
        load_dotenv()
        self.config = Config()
        
        # Create Flask app
        self.app = Flask(__name__)
        self.app.config.from_object(self.config)
        self.app.config['TESTING'] = True
        
        # Create mock components for integration testing
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        self.mock_notification_manager = Mock()
        
        # Create integrator
        self.integrator = PageNotificationIntegrator(
            self.mock_websocket_factory,
            self.mock_auth_handler,
            self.mock_namespace_manager,
            self.mock_notification_manager
        )
        
        # Add to app context
        self.app.page_notification_integrator = self.integrator
        
        # Register routes
        register_page_notification_routes(self.app)
        
        # Create test client
        self.client = self.app.test_client()
    
    def test_complete_page_integration_workflow(self):
        """Test complete workflow from registration to cleanup"""
        # Mock the _get_current_user_info method
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'integration_test_user',
                'role': 'admin',
                'permissions': {'system_management'},
                'session_id': 'integration-test-session'
            }
            
            page_id = 'integration-test-page'
            page_type = PageType.USER_DASHBOARD
            
            # Step 1: Register page integration
            result = self.integrator.register_page_integration(page_id, page_type)
            self.assertIsInstance(result, dict)
            self.assertEqual(result['page_id'], page_id)
            
            # Step 2: Initialize notifications
            init_result = self.integrator.initialize_page_notifications(page_id)
            self.assertEqual(init_result['status'], 'initialized')
            
            # Step 3: Setup WebSocket connection
            ws_config = self.integrator.setup_websocket_connection(page_id)
            self.assertIn('namespace', ws_config)
            self.assertIn('auth_data', ws_config)
            
            # Step 4: Register event handlers
            handler_config = self.integrator.register_event_handlers(page_id)
            self.assertIn('handlers', handler_config)
            
            # Step 5: Check status
            status = self.integrator.get_page_integration_status(page_id)
            self.assertEqual(status['status'], 'registered')
            self.assertTrue(status['initialized'])
            self.assertTrue(status['websocket_configured'])
            
            # Step 6: Cleanup
            cleanup_success = self.integrator.cleanup_page_integration(page_id)
            self.assertTrue(cleanup_success)
            
            # Verify cleanup
            final_status = self.integrator.get_page_integration_status(page_id)
            self.assertEqual(final_status['status'], 'not_registered')
    
    def test_multiple_page_integrations(self):
        """Test handling multiple simultaneous page integrations"""
        # Mock the _get_current_user_info method
        with patch.object(self.integrator, '_get_current_user_info') as mock_user_info:
            mock_user_info.return_value = {
                'user_id': 1,
                'username': 'multi_test_user',
                'role': 'admin',
                'permissions': {'system_management', 'user_management'}
            }
            
            # Register multiple pages
            pages = [
                ('page-1', PageType.USER_DASHBOARD),
                ('page-2', PageType.CAPTION_PROCESSING),
                ('page-3', PageType.ADMIN_DASHBOARD)
            ]
            
            for page_id, page_type in pages:
                result = self.integrator.register_page_integration(page_id, page_type)
                self.assertEqual(result['page_id'], page_id)
                
                # Initialize each page
                init_result = self.integrator.initialize_page_notifications(page_id)
                self.assertEqual(init_result['status'], 'initialized')
            
            # Check statistics
            stats = self.integrator.get_integration_stats()
            self.assertEqual(stats['total_integrations'], 3)
            self.assertEqual(stats['initialized_integrations'], 3)
            
            # Cleanup all pages
            for page_id, _ in pages:
                success = self.integrator.cleanup_page_integration(page_id)
                self.assertTrue(success)
            
            # Verify final stats
            final_stats = self.integrator.get_integration_stats()
            self.assertEqual(final_stats['total_integrations'], 0)


def run_page_notification_tests():
    """
    Run all page notification integration tests
    
    Returns:
        Test results
    """
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases using TestLoader
    loader = unittest.TestLoader()
    test_suite.addTest(loader.loadTestsFromTestCase(TestPageNotificationIntegrator))
    test_suite.addTest(loader.loadTestsFromTestCase(TestPageNotificationRoutes))
    test_suite.addTest(loader.loadTestsFromTestCase(TestPageNotificationIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result


if __name__ == '__main__':
    print("=" * 80)
    print("Page Notification Integration Tests")
    print("=" * 80)
    
    # Run tests
    test_result = run_page_notification_tests()
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Tests run: {test_result.testsRun}")
    print(f"Failures: {len(test_result.failures)}")
    print(f"Errors: {len(test_result.errors)}")
    
    if test_result.failures:
        print("\nFailures:")
        for test, traceback in test_result.failures:
            print(f"  - {test}: {traceback}")
    
    if test_result.errors:
        print("\nErrors:")
        for test, traceback in test_result.errors:
            print(f"  - {test}: {traceback}")
    
    # Exit with appropriate code
    exit_code = 0 if test_result.wasSuccessful() else 1
    print(f"\nTests {'PASSED' if exit_code == 0 else 'FAILED'}")
    exit(exit_code)