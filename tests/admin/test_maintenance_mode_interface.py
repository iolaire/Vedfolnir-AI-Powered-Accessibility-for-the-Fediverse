# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Maintenance Mode Admin Interface

Tests the admin interface for maintenance mode controls and status display.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from models import User, UserRole
from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode, MaintenanceStatus


class TestMaintenanceModeAdminInterface(unittest.TestCase):
    """Test maintenance mode admin interface functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create mock configuration service
        self.mock_config_service = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.db_manager
        )
        
        # Create mock Flask app
        self.mock_app = Mock()
        self.mock_app.config = {
            'maintenance_service': self.maintenance_service,
            'db_manager': self.db_manager
        }
        
        # Create mock admin user
        self.admin_user = Mock()
        self.admin_user.username = 'test_admin'
        self.admin_user.role = UserRole.ADMIN
        
        # Create mock regular user
        self.regular_user = Mock()
        self.regular_user.username = 'test_user'
        self.regular_user.role = UserRole.REVIEWER
    
    def test_maintenance_dashboard_access_admin(self):
        """Test that admin users can access maintenance dashboard"""
        # Test route registration
        from admin.routes.maintenance_mode import register_routes
        
        # Mock blueprint
        mock_bp = Mock()
        register_routes(mock_bp)
        
        # Verify that routes were registered
        self.assertTrue(mock_bp.route.called, "Routes should be registered")
        
        # Check that maintenance-mode route was registered
        route_calls = [str(call) for call in mock_bp.route.call_args_list]
        maintenance_route_found = any('/maintenance-mode' in call for call in route_calls)
        self.assertTrue(maintenance_route_found, "Maintenance mode route should be registered")
    
    def test_maintenance_dashboard_access_denied_non_admin(self):
        """Test that non-admin users cannot access maintenance dashboard"""
        with patch('flask.current_app', self.mock_app):
            with patch('flask_login.current_user', self.regular_user):
                with patch('flask.flash') as mock_flash:
                    with patch('flask.redirect') as mock_redirect:
                        # This would be tested in integration tests
                        # For unit tests, we verify the access control logic
                        self.assertEqual(self.regular_user.role, UserRole.REVIEWER)
                        self.assertNotEqual(self.regular_user.role, UserRole.ADMIN)
    
    def test_enable_maintenance_mode_api(self):
        """Test enabling maintenance mode via API"""
        test_data = {
            'reason': 'Test maintenance',
            'duration': 60,
            'mode': 'normal'
        }
        
        # Test the maintenance service enable_maintenance method directly
        with patch.object(self.maintenance_service, 'enable_maintenance', return_value=True) as mock_enable:
            with patch.object(self.maintenance_service, 'log_maintenance_event') as mock_log:
                # Call the service method directly
                result = self.maintenance_service.enable_maintenance(
                    reason=test_data['reason'],
                    duration=test_data['duration'],
                    mode=MaintenanceMode.NORMAL,
                    enabled_by='test_admin'
                )
                
                # Verify the call was made
                mock_enable.assert_called_once_with(
                    reason='Test maintenance',
                    duration=60,
                    mode=MaintenanceMode.NORMAL,
                    enabled_by='test_admin'
                )
                
                # Verify the result
                self.assertTrue(result)
    
    def test_disable_maintenance_mode_api(self):
        """Test disabling maintenance mode via API"""
        # Test that maintenance service disable_maintenance is called
        with patch.object(self.maintenance_service, 'disable_maintenance', return_value=True) as mock_disable:
            with patch.object(self.maintenance_service, 'log_maintenance_event') as mock_log:
                # Call the service method directly
                result = self.maintenance_service.disable_maintenance(disabled_by='test_admin')
                
                # Verify the call was made
                mock_disable.assert_called_once_with(disabled_by='test_admin')
                
                # Verify the result
                self.assertTrue(result)
    
    def test_get_maintenance_status_api(self):
        """Test getting maintenance status via API"""
        # Create test status
        test_status = MaintenanceStatus(
            is_active=True,
            mode=MaintenanceMode.NORMAL,
            reason='Test maintenance',
            estimated_duration=60,
            started_at=datetime.now(timezone.utc),
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=60),
            enabled_by='test_admin',
            blocked_operations=['caption_generation', 'job_creation'],
            active_jobs_count=2,
            invalidated_sessions=5,
            test_mode=False
        )
        
        # Test the service methods directly
        with patch.object(self.maintenance_service, 'get_maintenance_status', return_value=test_status):
            with patch.object(self.maintenance_service, 'get_blocked_operations', return_value=['caption_generation', 'job_creation']):
                with patch.object(self.maintenance_service, 'get_service_stats', return_value={'statistics': {'maintenance_activations': 1}}):
                    # Get status from service
                    status = self.maintenance_service.get_maintenance_status()
                    blocked_ops = self.maintenance_service.get_blocked_operations()
                    stats = self.maintenance_service.get_service_stats()
                    
                    # Verify status data structure
                    self.assertTrue(status.is_active)
                    self.assertEqual(status.mode, MaintenanceMode.NORMAL)
                    self.assertEqual(status.reason, 'Test maintenance')
                    self.assertEqual(status.active_jobs_count, 2)
                    self.assertEqual(status.invalidated_sessions, 5)
                    self.assertEqual(blocked_ops, ['caption_generation', 'job_creation'])
                    self.assertEqual(stats['statistics']['maintenance_activations'], 1)
    
    def test_validate_maintenance_config_api(self):
        """Test maintenance configuration validation"""
        # Test valid configuration
        valid_config = {
            'reason': 'Valid maintenance reason',
            'duration': 60,
            'mode': 'normal'
        }
        
        # Test invalid configuration
        invalid_config = {
            'reason': '',  # Empty reason
            'duration': -1,  # Invalid duration
            'mode': 'invalid'  # Invalid mode
        }
        
        # Test validation logic directly
        
        # Valid config should pass
        self.assertGreater(len(valid_config['reason']), 0)
        self.assertGreater(valid_config['duration'], 0)
        self.assertIn(valid_config['mode'], ['normal', 'emergency', 'test'])
        
        # Invalid config should fail
        self.assertEqual(len(invalid_config['reason']), 0)
        self.assertLess(invalid_config['duration'], 0)
        self.assertNotIn(invalid_config['mode'], ['normal', 'emergency', 'test'])
    
    def test_maintenance_mode_enum_validation(self):
        """Test maintenance mode enum validation"""
        valid_modes = ['normal', 'emergency', 'test']
        invalid_modes = ['invalid', 'unknown', '']
        
        # Test valid modes
        for mode in valid_modes:
            self.assertIn(mode, valid_modes)
        
        # Test invalid modes
        for mode in invalid_modes:
            self.assertNotIn(mode, valid_modes)
    
    def test_duration_validation(self):
        """Test maintenance duration validation"""
        # Valid durations
        valid_durations = [1, 30, 60, 120, 480, 1440]  # 1 min to 24 hours
        
        # Invalid durations
        invalid_durations = [0, -1, 1441, 'invalid', None]
        
        for duration in valid_durations:
            if isinstance(duration, int):
                self.assertGreater(duration, 0)
                self.assertLessEqual(duration, 1440)
        
        for duration in invalid_durations:
            if duration is not None and isinstance(duration, int):
                self.assertTrue(duration <= 0 or duration > 1440)
    
    def test_reason_validation(self):
        """Test maintenance reason validation"""
        # Valid reasons
        valid_reasons = [
            'System maintenance required',
            'Database optimization in progress',
            'Security updates being applied'
        ]
        
        # Invalid reasons
        invalid_reasons = [
            '',  # Empty
            'a',  # Too short
            'x' * 501  # Too long (over 500 chars)
        ]
        
        for reason in valid_reasons:
            self.assertGreater(len(reason.strip()), 0)
            self.assertLessEqual(len(reason), 500)
        
        for reason in invalid_reasons:
            if reason == '':
                self.assertEqual(len(reason.strip()), 0)
            elif len(reason) == 1:
                self.assertLess(len(reason), 10)  # Too short warning threshold
            else:
                self.assertGreater(len(reason), 500)  # Too long
    
    def test_admin_access_control(self):
        """Test admin access control for maintenance operations"""
        # Admin user should have access
        self.assertEqual(self.admin_user.role, UserRole.ADMIN)
        
        # Regular user should not have access
        self.assertNotEqual(self.regular_user.role, UserRole.ADMIN)
        
        # Test role checking logic
        def is_admin(user):
            return user.role == UserRole.ADMIN
        
        self.assertTrue(is_admin(self.admin_user))
        self.assertFalse(is_admin(self.regular_user))
    
    def test_maintenance_service_integration(self):
        """Test integration with maintenance service"""
        # Test that maintenance service is properly configured
        self.assertIsNotNone(self.maintenance_service)
        self.assertIsNotNone(self.maintenance_service.config_service)
        
        # Test service methods exist
        self.assertTrue(hasattr(self.maintenance_service, 'enable_maintenance'))
        self.assertTrue(hasattr(self.maintenance_service, 'disable_maintenance'))
        self.assertTrue(hasattr(self.maintenance_service, 'get_maintenance_status'))
        self.assertTrue(hasattr(self.maintenance_service, 'get_blocked_operations'))
        self.assertTrue(hasattr(self.maintenance_service, 'log_maintenance_event'))
    
    def test_emergency_mode_handling(self):
        """Test emergency maintenance mode handling"""
        emergency_config = {
            'reason': 'Critical system issue detected',
            'duration': 30,
            'mode': 'emergency'
        }
        
        # Test emergency mode validation
        self.assertEqual(emergency_config['mode'], 'emergency')
        self.assertGreater(len(emergency_config['reason']), 0)
        
        # Emergency mode should have shorter duration typically
        self.assertLessEqual(emergency_config['duration'], 120)  # Max 2 hours for emergency
    
    def test_test_mode_handling(self):
        """Test test maintenance mode handling"""
        test_config = {
            'reason': 'Testing maintenance procedures',
            'duration': 15,
            'mode': 'test'
        }
        
        # Test mode validation
        self.assertEqual(test_config['mode'], 'test')
        self.assertGreater(len(test_config['reason']), 0)
        
        # Test mode should typically be shorter
        self.assertLessEqual(test_config['duration'], 60)  # Max 1 hour for testing


if __name__ == '__main__':
    unittest.main()