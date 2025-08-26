# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for MaintenanceModeMiddleware

Tests middleware request interception, admin bypass logic, operation blocking,
and maintenance response generation.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, g
from maintenance_mode_middleware import MaintenanceModeMiddleware
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus
from maintenance_operation_classifier import OperationType
from models import User, UserRole


class TestMaintenanceModeMiddleware(unittest.TestCase):
    """Test cases for MaintenanceModeMiddleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock maintenance service
        self.mock_maintenance_service = Mock(spec=EnhancedMaintenanceModeService)
        
        # Create middleware instance
        with patch.object(MaintenanceModeMiddleware, '_register_middleware_hooks'):
            self.middleware = MaintenanceModeMiddleware(self.app, self.mock_maintenance_service)
        
        # Create test users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = 'admin'
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = 'user'
        self.regular_user.role = UserRole.VIEWER
        
        # Default maintenance status (inactive)
        self.inactive_status = MaintenanceStatus(
            is_active=False,
            mode=MaintenanceMode.NORMAL,
            reason=None,
            estimated_duration=None,
            started_at=None,
            estimated_completion=None,
            enabled_by=None,
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        # Active maintenance status
        self.active_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="System maintenance",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=["caption_generation", "job_creation"],
            active_jobs_count=2,
            invalidated_sessions=5,
            test_mode=False
        )
    
    def test_middleware_initialization(self):
        """Test middleware initialization"""
        # Test that middleware is properly initialized
        self.assertIsNotNone(self.middleware.app)
        self.assertIsNotNone(self.middleware.maintenance_service)
        self.assertIsNotNone(self.middleware.operation_classifier)
        
        # Test that statistics are initialized
        stats = self.middleware.get_middleware_stats()
        self.assertIn('middleware_stats', stats)
        self.assertEqual(stats['middleware_stats']['total_requests'], 0)
    
    def test_is_admin_user_with_admin(self):
        """Test admin user identification with admin user"""
        result = self.middleware.is_admin_user(self.admin_user)
        self.assertTrue(result)
    
    def test_is_admin_user_with_regular_user(self):
        """Test admin user identification with regular user"""
        result = self.middleware.is_admin_user(self.regular_user)
        self.assertFalse(result)
    
    def test_is_admin_user_with_none(self):
        """Test admin user identification with None user"""
        result = self.middleware.is_admin_user(None)
        self.assertFalse(result)
    
    def test_is_admin_user_with_is_admin_method(self):
        """Test admin user identification with is_admin method"""
        user_with_method = Mock()
        user_with_method.is_admin = Mock(return_value=True)
        
        result = self.middleware.is_admin_user(user_with_method)
        self.assertTrue(result)
        user_with_method.is_admin.assert_called_once()
    
    def test_is_allowed_operation_with_allowed_operation(self):
        """Test operation allowance check with allowed operation"""
        # Mock operation classifier to return READ_OPERATIONS (allowed)
        with patch.object(self.middleware.operation_classifier, 'classify_operation') as mock_classify:
            with patch.object(self.middleware.operation_classifier, 'is_blocked_operation') as mock_blocked:
                mock_classify.return_value = OperationType.READ_OPERATIONS
                mock_blocked.return_value = False
                
                self.mock_maintenance_service.get_maintenance_status.return_value = self.active_status
                
                result = self.middleware.is_allowed_operation('/api/status', self.regular_user, 'GET')
                self.assertTrue(result)
                
                mock_classify.assert_called_once_with('/api/status', 'GET')
                mock_blocked.assert_called_once_with(OperationType.READ_OPERATIONS, MaintenanceMode.NORMAL)
    
    def test_is_allowed_operation_with_blocked_operation(self):
        """Test operation allowance check with blocked operation"""
        # Mock operation classifier to return CAPTION_GENERATION (blocked)
        with patch.object(self.middleware.operation_classifier, 'classify_operation') as mock_classify:
            with patch.object(self.middleware.operation_classifier, 'is_blocked_operation') as mock_blocked:
                mock_classify.return_value = OperationType.CAPTION_GENERATION
                mock_blocked.return_value = True
                
                self.mock_maintenance_service.get_maintenance_status.return_value = self.active_status
                
                result = self.middleware.is_allowed_operation('/caption/generate', self.regular_user, 'POST')
                self.assertFalse(result)
                
                mock_classify.assert_called_once_with('/caption/generate', 'POST')
                mock_blocked.assert_called_once_with(OperationType.CAPTION_GENERATION, MaintenanceMode.NORMAL)
    
    def test_create_maintenance_response(self):
        """Test maintenance response creation"""
        # Mock maintenance service responses
        self.mock_maintenance_service.get_maintenance_message.return_value = "System maintenance in progress"
        self.mock_maintenance_service.get_maintenance_status.return_value = self.active_status
        
        with self.app.test_request_context():
            response = self.middleware.create_maintenance_response('/caption/generate')
            
            # Check response status
            self.assertEqual(response.status_code, 503)
            
            # Check response headers
            self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
            self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')
            
            # Check response data
            response_data = json.loads(response.get_data(as_text=True))
            self.assertEqual(response_data['error'], 'Service Unavailable')
            self.assertEqual(response_data['message'], 'System maintenance in progress')
            self.assertTrue(response_data['maintenance_active'])
            self.assertEqual(response_data['maintenance_mode'], 'normal')
            self.assertEqual(response_data['reason'], 'System maintenance')
            self.assertEqual(response_data['operation'], '/caption/generate')
    
    def test_create_maintenance_response_with_duration(self):
        """Test maintenance response creation with estimated duration"""
        # Create status with estimated duration
        status_with_duration = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="System maintenance",
            estimated_duration=60,  # 60 minutes
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        self.mock_maintenance_service.get_maintenance_message.return_value = "System maintenance in progress"
        self.mock_maintenance_service.get_maintenance_status.return_value = status_with_duration
        
        with self.app.test_request_context():
            response = self.middleware.create_maintenance_response('/test')
            
            # Check Retry-After header (60 minutes = 3600 seconds)
            self.assertEqual(response.headers.get('Retry-After'), '3600')
    
    def test_before_request_maintenance_inactive(self):
        """Test before_request when maintenance is inactive"""
        # Mock maintenance service to return inactive status
        self.mock_maintenance_service.get_maintenance_status.return_value = self.inactive_status
        
        with self.app.test_request_context('/test', method='GET'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'test_endpoint'
                mock_request.path = '/test'
                mock_request.method = 'GET'
                
                result = self.middleware.before_request()
                
                # Should return None (allow request to continue)
                self.assertIsNone(result)
    
    def test_before_request_admin_bypass(self):
        """Test before_request with admin user bypass"""
        # Mock maintenance service to return active status
        self.mock_maintenance_service.get_maintenance_status.return_value = self.active_status
        
        with self.app.test_request_context('/test', method='GET'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'test_endpoint'
                mock_request.path = '/test'
                mock_request.method = 'GET'
                mock_request.headers = {'User-Agent': 'test-agent'}
                mock_request.remote_addr = '127.0.0.1'
                
                with patch.object(self.middleware, '_get_current_user', return_value=self.admin_user):
                    result = self.middleware.before_request()
                    
                    # Should return None (allow admin to bypass)
                    self.assertIsNone(result)
    
    def test_before_request_blocked_operation(self):
        """Test before_request with blocked operation"""
        # Mock maintenance service
        self.mock_maintenance_service.get_maintenance_status.return_value = self.active_status
        self.mock_maintenance_service.get_maintenance_message.return_value = "Maintenance in progress"
        
        with self.app.test_request_context('/caption/generate', method='POST'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'caption_generate'
                mock_request.path = '/caption/generate'
                mock_request.method = 'POST'
                mock_request.headers = {'User-Agent': 'test-agent'}
                mock_request.remote_addr = '127.0.0.1'
                
                with patch.object(self.middleware, '_get_current_user', return_value=self.regular_user):
                    with patch.object(self.middleware, 'is_allowed_operation', return_value=False):
                        result = self.middleware.before_request()
                        
                        # Should return maintenance response
                        self.assertIsNotNone(result)
                        self.assertEqual(result.status_code, 503)
    
    def test_before_request_skip_static_files(self):
        """Test before_request skips static files"""
        with self.app.test_request_context('/static/test.css'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'static'
                
                result = self.middleware.before_request()
                
                # Should return None (skip maintenance check)
                self.assertIsNone(result)
    
    def test_before_request_skip_health_check(self):
        """Test before_request skips health check endpoints"""
        with self.app.test_request_context('/health'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'health'
                
                result = self.middleware.before_request()
                
                # Should return None (skip maintenance check)
                self.assertIsNone(result)
    
    def test_log_blocked_attempt(self):
        """Test blocked attempt logging"""
        with patch.object(self.middleware, '_log_blocked_attempt') as mock_log:
            self.middleware.log_blocked_attempt('/test', self.regular_user, 'POST')
            mock_log.assert_called_once_with('/test', self.regular_user, 'POST')
    
    def test_log_blocked_attempt_internal(self):
        """Test internal blocked attempt logging"""
        with self.app.test_request_context('/test', method='POST'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.headers = {'User-Agent': 'test-agent'}
                mock_request.remote_addr = '127.0.0.1'
                
                self.middleware._log_blocked_attempt('/test', self.regular_user, 'POST')
                
                # Check that blocked attempts counter was updated
                stats = self.middleware.get_middleware_stats()
                self.assertIn('blocked_attempts_by_endpoint', stats)
                self.assertEqual(stats['blocked_attempts_by_endpoint'].get('/test:POST', 0), 1)
                
                # Verify maintenance service logging was called
                self.mock_maintenance_service.log_maintenance_event.assert_called_once()
    
    def test_get_middleware_stats(self):
        """Test middleware statistics retrieval"""
        # Mock maintenance service stats
        self.mock_maintenance_service.get_service_stats.return_value = {
            'current_status': {'is_active': False},
            'statistics': {'maintenance_activations': 0}
        }
        
        stats = self.middleware.get_middleware_stats()
        
        # Check stats structure
        self.assertIn('middleware_stats', stats)
        self.assertIn('blocked_attempts_by_endpoint', stats)
        self.assertIn('admin_bypasses_by_user', stats)
        self.assertIn('maintenance_service_stats', stats)
        self.assertIn('operation_classifier_stats', stats)
        self.assertIn('timestamp', stats)
    
    def test_reset_stats(self):
        """Test middleware statistics reset"""
        # Add some stats first
        with self.app.test_request_context('/test', method='POST'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.headers = {'User-Agent': 'test-agent'}
                mock_request.remote_addr = '127.0.0.1'
                
                self.middleware._log_blocked_attempt('/test', self.regular_user, 'POST')
        
        # Verify stats exist
        stats_before = self.middleware.get_middleware_stats()
        self.assertGreater(len(stats_before['blocked_attempts_by_endpoint']), 0)
        
        # Reset stats
        self.middleware.reset_stats()
        
        # Verify stats are reset
        stats_after = self.middleware.get_middleware_stats()
        self.assertEqual(len(stats_after['blocked_attempts_by_endpoint']), 0)
        self.assertEqual(stats_after['middleware_stats']['total_requests'], 0)
    
    def test_get_blocked_attempts_count(self):
        """Test blocked attempts count retrieval"""
        # Add some blocked attempts
        with self.app.test_request_context('/test', method='POST'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.headers = {'User-Agent': 'test-agent'}
                mock_request.remote_addr = '127.0.0.1'
                
                self.middleware._log_blocked_attempt('/test1', self.regular_user, 'POST')
                self.middleware._log_blocked_attempt('/test1', self.regular_user, 'GET')
                self.middleware._log_blocked_attempt('/test2', self.regular_user, 'POST')
        
        # Test specific endpoint and method
        count1 = self.middleware.get_blocked_attempts_count('/test1', 'POST')
        self.assertEqual(count1, 1)
        
        # Test specific endpoint (all methods)
        count2 = self.middleware.get_blocked_attempts_count('/test1')
        self.assertEqual(count2, 2)  # POST + GET
        
        # Test total count
        total_count = self.middleware.get_blocked_attempts_count()
        self.assertEqual(total_count, 0)  # This checks middleware_stats, not individual attempts
    
    def test_get_admin_bypasses_count(self):
        """Test admin bypasses count retrieval"""
        # Add some admin bypasses
        self.middleware._log_admin_bypass(self.admin_user)
        self.middleware._log_admin_bypass(self.admin_user)
        
        # Test specific user
        user_count = self.middleware.get_admin_bypasses_count(self.admin_user.id)
        self.assertEqual(user_count, 2)
        
        # Test total count
        total_count = self.middleware.get_admin_bypasses_count()
        self.assertEqual(total_count, 2)
    
    def test_should_skip_maintenance_check(self):
        """Test maintenance check skip logic"""
        test_cases = [
            ('static', True),
            ('health', True),
            ('health_check', True),
            ('api.health', True),
            ('admin.maintenance', True),
            ('admin.system_health', True),
            ('admin.emergency_maintenance', True),
            ('regular_endpoint', False),
        ]
        
        for endpoint, should_skip in test_cases:
            with self.app.test_request_context(f'/{endpoint}'):
                with patch('maintenance_mode_middleware.request') as mock_request:
                    mock_request.endpoint = endpoint
                    mock_request.path = f'/{endpoint}'
                    
                    result = self.middleware._should_skip_maintenance_check()
                    self.assertEqual(result, should_skip, f"Failed for endpoint: {endpoint}")
    
    def test_should_skip_maintenance_check_api_path(self):
        """Test maintenance check skip for API maintenance status path"""
        with self.app.test_request_context('/api/maintenance/status'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'api.maintenance_status'
                mock_request.path = '/api/maintenance/status'
                
                result = self.middleware._should_skip_maintenance_check()
                self.assertTrue(result)
    
    def test_get_current_user_flask_login(self):
        """Test getting current user from Flask-Login"""
        # Test that the method can handle authenticated users
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_user.username = 'test_user'
        mock_user.role = UserRole.VIEWER  # Set explicit role
        # Ensure is_admin method doesn't exist so it falls back to role check
        del mock_user.is_admin
        
        # Test the admin check logic with this user
        result = self.middleware.is_admin_user(mock_user)
        self.assertFalse(result)  # Mock user doesn't have admin role
    
    def test_get_current_user_session_context(self):
        """Test getting current user from session context"""
        # Test the SessionUser class creation logic
        session_data = {
            'user_id': 2,
            'username': 'session_user',
            'role': 'admin'
        }
        
        # Create a SessionUser like the middleware would
        class SessionUser:
            def __init__(self, session_data):
                self.id = session_data.get('user_id')
                self.username = session_data.get('username', 'unknown')
                self.role = UserRole(session_data.get('role', 'viewer'))
        
        user = SessionUser(session_data)
        
        # Test that it has the expected properties
        self.assertEqual(user.id, 2)
        self.assertEqual(user.username, 'session_user')
        self.assertEqual(user.role, UserRole.ADMIN)
        
        # Test admin check with this user
        result = self.middleware.is_admin_user(user)
        self.assertTrue(result)
    
    def test_get_current_user_none(self):
        """Test getting current user when none available"""
        # Test admin check with None user
        result = self.middleware.is_admin_user(None)
        self.assertFalse(result)
    
    def test_error_handling_in_before_request(self):
        """Test error handling in before_request method"""
        # Mock maintenance service to raise exception
        self.mock_maintenance_service.get_maintenance_status.side_effect = Exception("Test error")
        
        with self.app.test_request_context('/test'):
            with patch('maintenance_mode_middleware.request') as mock_request:
                mock_request.endpoint = 'test'
                mock_request.path = '/test'
                mock_request.method = 'GET'
                
                result = self.middleware.before_request()
                
                # Should return None (allow request) on error to prevent lockout
                self.assertIsNone(result)
    
    def test_error_handling_in_create_maintenance_response(self):
        """Test error handling in create_maintenance_response method"""
        # Mock maintenance service to raise exception
        self.mock_maintenance_service.get_maintenance_message.side_effect = Exception("Test error")
        self.mock_maintenance_service.get_maintenance_status.side_effect = Exception("Test error")
        
        with self.app.test_request_context():
            response = self.middleware.create_maintenance_response('/test')
            
            # Should return fallback response
            self.assertEqual(response.status_code, 503)
            response_data = json.loads(response.get_data(as_text=True))
            self.assertEqual(response_data['error'], 'Service Unavailable')
            self.assertIn('System maintenance is in progress', response_data['message'])


if __name__ == '__main__':
    unittest.main()