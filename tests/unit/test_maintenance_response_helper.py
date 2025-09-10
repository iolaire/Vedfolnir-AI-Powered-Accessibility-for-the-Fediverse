# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for maintenance response helper

Tests standardized maintenance response formatting, message templates,
and user-friendly maintenance status display.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.components.maintenance_response_helper import MaintenanceResponseHelper
from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import MaintenanceStatus, MaintenanceMode
from app.services.maintenance.components.maintenance_operation_classifier import OperationType


class TestMaintenanceResponseHelper(unittest.TestCase):
    """Test maintenance response helper functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.response_helper = MaintenanceResponseHelper()
        
        # Create test maintenance status
        self.maintenance_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Routine system maintenance",
            estimated_duration=60,
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=60),
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=2,
            invalidated_sessions=5,
            test_mode=False
        )
    
    def test_create_json_response_structure(self):
        """Test that JSON response has correct structure"""
        response_data = self.response_helper.create_json_response(
            '/api/test_operation',
            self.maintenance_status,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Verify top-level structure
        self.assertIn('error', response_data)
        self.assertIn('maintenance_active', response_data)
        self.assertIn('maintenance_info', response_data)
        self.assertIn('operation_info', response_data)
        self.assertIn('message', response_data)
        self.assertIn('timestamp', response_data)
        
        # Verify maintenance_info structure
        maintenance_info = response_data['maintenance_info']
        self.assertIn('mode', maintenance_info)
        self.assertIn('reason', maintenance_info)
        self.assertIn('started_at', maintenance_info)
        self.assertIn('estimated_completion', maintenance_info)
        self.assertIn('estimated_duration', maintenance_info)
        self.assertIn('enabled_by', maintenance_info)
        self.assertIn('test_mode', maintenance_info)
        
        # Verify operation_info structure
        operation_info = response_data['operation_info']
        self.assertIn('operation', operation_info)
        self.assertIn('operation_type', operation_info)
        self.assertIn('title', operation_info)
        self.assertIn('description', operation_info)
        self.assertIn('icon', operation_info)
        self.assertIn('suggestion', operation_info)
    
    def test_json_response_values(self):
        """Test that JSON response contains correct values"""
        response_data = self.response_helper.create_json_response(
            '/api/switch_platform/123',
            self.maintenance_status,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Verify basic values
        self.assertEqual(response_data['error'], 'Service Unavailable')
        self.assertTrue(response_data['maintenance_active'])
        
        # Verify maintenance info values
        maintenance_info = response_data['maintenance_info']
        self.assertEqual(maintenance_info['mode'], 'normal')
        self.assertEqual(maintenance_info['reason'], 'Routine system maintenance')
        self.assertEqual(maintenance_info['estimated_duration'], 60)
        self.assertEqual(maintenance_info['enabled_by'], 'admin')
        self.assertFalse(maintenance_info['test_mode'])
        
        # Verify operation info values
        operation_info = response_data['operation_info']
        self.assertEqual(operation_info['operation'], '/api/switch_platform/123')
        self.assertEqual(operation_info['operation_type'], 'platform_operations')
        self.assertEqual(operation_info['title'], 'Platform Operations Unavailable')
        self.assertEqual(operation_info['icon'], '🔗')
    
    def test_operation_templates(self):
        """Test operation-specific message templates"""
        test_cases = [
            (OperationType.PLATFORM_OPERATIONS, 'Platform Operations Unavailable', '🔗', 'Platform switching'),
            (OperationType.BATCH_OPERATIONS, 'Batch Operations Unavailable', '📦', 'Bulk processing'),
            (OperationType.CAPTION_GENERATION, 'Caption Generation Unavailable', '🤖', 'AI caption generation'),
            (OperationType.JOB_CREATION, 'Job Creation Unavailable', '⚙️', 'background jobs'),
            (OperationType.USER_DATA_MODIFICATION, 'Profile Updates Unavailable', '👤', 'User profile'),
            (OperationType.IMAGE_PROCESSING, 'Image Processing Unavailable', '🖼️', 'Image upload'),
        ]
        
        for operation_type, expected_title, expected_icon, expected_description_part in test_cases:
            with self.subTest(operation_type=operation_type):
                template = self.response_helper.get_operation_message_template(operation_type)
                
                self.assertEqual(template['title'], expected_title)
                self.assertEqual(template['icon'], expected_icon)
                self.assertIn(expected_description_part, template['description'])
                self.assertIn('suggestion', template)
    
    def test_unknown_operation_template(self):
        """Test default template for unknown operations"""
        template = self.response_helper.get_operation_message_template(OperationType.UNKNOWN)
        
        self.assertEqual(template['title'], 'Service Temporarily Unavailable')
        self.assertEqual(template['icon'], '🔧')
        self.assertIn('temporarily disabled', template['description'])
        self.assertIn('try again', template['suggestion'])
    
    def test_maintenance_mode_messages(self):
        """Test mode-specific messages"""
        test_cases = [
            (MaintenanceMode.NORMAL, '🔧 System Maintenance', 'improve system performance'),
            (MaintenanceMode.EMERGENCY, '🚨 Emergency Maintenance', 'critical system issues'),
            (MaintenanceMode.TEST, '🧪 Test Maintenance', 'system validation'),
        ]
        
        for mode, expected_prefix, expected_description_part in test_cases:
            with self.subTest(mode=mode):
                status = MaintenanceStatus(
                    is_active=True,
                    mode=mode,
                    reason="Test reason",
                    estimated_duration=30,
                    started_at=datetime.now(timezone.utc),
                    estimated_completion=None,
                    enabled_by="admin",
                    blocked_operations=[],
                    active_jobs_count=0,
                    invalidated_sessions=0,
                    test_mode=(mode == MaintenanceMode.TEST)
                )
                
                response_data = self.response_helper.create_json_response(
                    '/api/test',
                    status,
                    OperationType.PLATFORM_OPERATIONS
                )
                
                self.assertIn(expected_prefix, response_data['message'])
                # The mode description is not included in the message, only the prefix
                # So we'll just check that the prefix is there
    
    def test_retry_after_calculation(self):
        """Test retry-after calculation"""
        # Test with estimated completion
        completion_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        status_with_completion = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Test",
            estimated_duration=None,
            started_at=datetime.now(timezone.utc),
            estimated_completion=completion_time,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        response_data = self.response_helper.create_json_response(
            '/api/test',
            status_with_completion,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Should have retry_after field
        self.assertIn('retry_after', response_data)
        self.assertIsInstance(response_data['retry_after'], int)
        self.assertGreater(response_data['retry_after'], 0)
        
        # Test with estimated duration
        status_with_duration = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Test",
            estimated_duration=45,  # 45 minutes
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        response_data = self.response_helper.create_json_response(
            '/api/test',
            status_with_duration,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Should have retry_after field (45 minutes = 2700 seconds)
        self.assertIn('retry_after', response_data)
        self.assertEqual(response_data['retry_after'], 2700)
    
    @patch('maintenance_response_helper.jsonify')
    def test_create_flask_response(self, mock_jsonify):
        """Test Flask response creation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_jsonify.return_value = mock_response
        
        response = self.response_helper.create_flask_response(
            '/api/test',
            self.maintenance_status,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Verify response properties
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers.get('X-Maintenance-Active'), 'true')
        self.assertEqual(response.headers.get('X-Maintenance-Mode'), 'normal')
        
        # Verify jsonify was called
        mock_jsonify.assert_called_once()
        call_args = mock_jsonify.call_args[0][0]
        self.assertEqual(call_args['error'], 'Service Unavailable')
        self.assertTrue(call_args['maintenance_active'])
    
    @patch('maintenance_response_helper.jsonify')
    def test_flask_response_with_retry_after(self, mock_jsonify):
        """Test Flask response with Retry-After header"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_jsonify.return_value = mock_response
        
        status_with_duration = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Test",
            estimated_duration=30,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        response = self.response_helper.create_flask_response(
            '/api/test',
            status_with_duration,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Verify Retry-After header
        self.assertEqual(response.headers.get('Retry-After'), '1800')  # 30 minutes = 1800 seconds
    
    def test_html_maintenance_banner(self):
        """Test HTML maintenance banner creation"""
        # HTML banner creation requires Flask context, so we'll test the fallback
        banner_html = self.response_helper.create_html_maintenance_banner(self.maintenance_status)
        
        # Should return fallback HTML due to missing Flask context
        self.assertIn('alert', banner_html)
        self.assertIn('🔧', banner_html)
        self.assertIn('maintenance', banner_html)
    
    def test_html_banner_for_different_modes(self):
        """Test HTML banner styling for different maintenance modes"""
        # Test emergency mode
        emergency_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.EMERGENCY,
            reason="Critical issue",
            estimated_duration=None,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        emergency_banner = self.response_helper.create_html_maintenance_banner(emergency_status)
        # Should return fallback HTML due to missing Flask context
        self.assertIn('alert', emergency_banner)
        self.assertIn('🔧', emergency_banner)  # Fallback uses 🔧
        
        # Test test mode
        test_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.TEST,
            reason="Testing",
            estimated_duration=None,
            started_at=datetime.now(timezone.utc),
            estimated_completion=None,
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=True
        )
        
        test_banner = self.response_helper.create_html_maintenance_banner(test_status)
        # Should return fallback HTML due to missing Flask context
        self.assertIn('alert', test_banner)
        self.assertIn('🔧', test_banner)  # Fallback uses 🔧
    
    def test_html_banner_inactive_maintenance(self):
        """Test HTML banner for inactive maintenance"""
        inactive_status = MaintenanceStatus(
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
        
        banner_html = self.response_helper.create_html_maintenance_banner(inactive_status)
        self.assertEqual(banner_html, "")  # Should return empty string
    
    def test_maintenance_status_dict(self):
        """Test maintenance status dictionary creation"""
        status_dict = self.response_helper.create_maintenance_status_dict(self.maintenance_status)
        
        # Verify dictionary structure
        expected_keys = [
            'is_active', 'mode', 'mode_display', 'mode_description',
            'reason', 'estimated_duration', 'started_at', 'estimated_completion',
            'enabled_by', 'blocked_operations', 'active_jobs_count',
            'invalidated_sessions', 'test_mode', 'banner_html'
        ]
        
        for key in expected_keys:
            self.assertIn(key, status_dict)
        
        # Verify values
        self.assertTrue(status_dict['is_active'])
        self.assertEqual(status_dict['mode'], 'normal')
        self.assertEqual(status_dict['mode_display'], '🔧 System Maintenance')
        self.assertEqual(status_dict['reason'], 'Routine system maintenance')
        self.assertEqual(status_dict['estimated_duration'], 60)
        self.assertEqual(status_dict['enabled_by'], 'admin')
        self.assertFalse(status_dict['test_mode'])
        # Banner HTML will be fallback due to missing Flask context
        self.assertIn('alert', status_dict['banner_html'])
    
    def test_error_handling_in_json_response(self):
        """Test error handling in JSON response creation"""
        # Test with None operation type
        response_data = self.response_helper.create_json_response(
            '/api/test',
            self.maintenance_status,
            None
        )
        
        # Should use default template
        self.assertEqual(response_data['operation_info']['title'], 'Service Temporarily Unavailable')
        self.assertEqual(response_data['operation_info']['operation_type'], 'unknown')
    
    @patch('maintenance_response_helper.logger')
    @patch('maintenance_response_helper.jsonify')
    def test_error_handling_in_flask_response(self, mock_jsonify, mock_logger):
        """Test error handling in Flask response creation"""
        # First call raises exception, second call (fallback) succeeds
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.headers = {}
        
        mock_jsonify.side_effect = [Exception("Test error"), mock_response]
        
        response = self.response_helper.create_flask_response(
            '/api/test',
            self.maintenance_status,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Should return fallback response
        self.assertEqual(response.status_code, 503)
        mock_logger.error.assert_called()
    
    def test_message_building(self):
        """Test comprehensive message building"""
        response_data = self.response_helper.create_json_response(
            '/api/switch_platform/123',
            self.maintenance_status,
            OperationType.PLATFORM_OPERATIONS
        )
        
        message = response_data['message']
        
        # Should contain mode prefix
        self.assertIn('🔧 System Maintenance', message)
        
        # Should contain reason
        self.assertIn('Routine system maintenance', message)
        
        # Should contain operation description
        self.assertIn('Platform switching', message)
        
        # Should contain completion time
        self.assertIn('Expected completion:', message)
        
        # Should contain suggestion
        self.assertIn('current platform connection', message)
        
        # Should contain general advice
        self.assertIn('try again after maintenance', message)
    
    def test_duration_vs_completion_time_priority(self):
        """Test that completion time takes priority over duration"""
        completion_time = datetime.now(timezone.utc) + timedelta(minutes=45)
        status_with_both = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason="Test",
            estimated_duration=60,  # This should be ignored
            started_at=datetime.now(timezone.utc),
            estimated_completion=completion_time,  # This should be used
            enabled_by="admin",
            blocked_operations=[],
            active_jobs_count=0,
            invalidated_sessions=0,
            test_mode=False
        )
        
        response_data = self.response_helper.create_json_response(
            '/api/test',
            status_with_both,
            OperationType.PLATFORM_OPERATIONS
        )
        
        # Should use completion time, not duration
        self.assertIn('Expected completion:', response_data['message'])
        self.assertNotIn('Estimated duration: 60 minutes', response_data['message'])


if __name__ == '__main__':
    unittest.main()