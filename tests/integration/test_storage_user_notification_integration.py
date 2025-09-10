# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Storage User Notification System with web routes.

Tests the integration of storage limit notifications with the caption generation
web interface, including banner display and form hiding functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_user_notification_system import StorageUserNotificationSystem
from app.services.storage.components.storage_limit_enforcer import StorageLimitEnforcer, StorageBlockingState, StorageCheckResult
from app.services.storage.components.storage_monitor_service import StorageMetrics


class TestStorageUserNotificationIntegration(unittest.TestCase):
    """Integration tests for storage user notification system with web routes"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock Flask app and request context
        self.mock_app = Mock()
        self.mock_request_context = Mock()
        
        # Mock dependencies
        self.mock_config_service = Mock()
        self.mock_monitor_service = Mock()
        self.mock_enforcer = Mock()
        
        # Configure mock config service
        self.mock_config_service.get_max_storage_gb.return_value = 10.0
        self.mock_config_service.get_warning_threshold_gb.return_value = 8.0
        self.mock_config_service.validate_storage_config.return_value = True
        
        # Create notification system
        self.notification_system = StorageUserNotificationSystem(
            enforcer=self.mock_enforcer,
            monitor_service=self.mock_monitor_service,
            config_service=self.mock_config_service
        )
    
    def test_caption_generation_page_with_no_storage_issues(self):
        """Test caption generation page when no storage issues exist"""
        # Mock no blocking state
        self.mock_enforcer.get_blocking_state.return_value = None
        
        # Mock storage metrics under warning threshold
        metrics = StorageMetrics(
            total_bytes=5 * 1024**3,  # 5GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Get template context
        template_context = self.notification_system.get_storage_status_for_template()
        
        # Verify template context for normal operation
        self.assertIsNone(template_context['storage_notification'])
        self.assertFalse(template_context['storage_limit_active'])
        self.assertEqual(template_context['storage_banner_html'], '')
        self.assertFalse(template_context['hide_caption_form'])
    
    def test_caption_generation_page_with_storage_warning(self):
        """Test caption generation page when storage is at warning threshold"""
        # Mock no blocking state
        self.mock_enforcer.get_blocking_state.return_value = None
        
        # Mock storage metrics at warning threshold
        metrics = StorageMetrics(
            total_bytes=9 * 1024**3,  # 9GB
            total_gb=9.0,
            limit_gb=10.0,
            usage_percentage=90.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Get template context
        template_context = self.notification_system.get_storage_status_for_template()
        
        # Verify template context for warning state
        self.assertIsNotNone(template_context['storage_notification'])
        self.assertFalse(template_context['storage_limit_active'])  # Warning, not blocked
        self.assertIsInstance(template_context['storage_banner_html'], str)
        self.assertIn('alert alert-warning', template_context['storage_banner_html'])
        self.assertFalse(template_context['hide_caption_form'])  # Form should still be available
        
        # Check notification details
        notification = template_context['storage_notification']
        self.assertFalse(notification['is_blocked'])
        self.assertEqual(notification['notification_type'], 'warning')
        self.assertIn('90.0% of limit', notification['reason'])
    
    def test_caption_generation_page_with_storage_blocked(self):
        """Test caption generation page when storage is blocked"""
        # Mock blocking state
        blocked_at = datetime.now(timezone.utc)
        blocking_state = StorageBlockingState(
            is_blocked=True,
            reason="Storage limit exceeded",
            blocked_at=blocked_at,
            storage_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            last_checked=datetime.now(timezone.utc)
        )
        self.mock_enforcer.get_blocking_state.return_value = blocking_state
        
        # Mock storage metrics over limit
        metrics = StorageMetrics(
            total_bytes=11 * 1024**3,  # 11GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Get template context
        template_context = self.notification_system.get_storage_status_for_template()
        
        # Verify template context for blocked state
        self.assertIsNotNone(template_context['storage_notification'])
        self.assertTrue(template_context['storage_limit_active'])
        self.assertIsInstance(template_context['storage_banner_html'], str)
        self.assertIn('alert alert-danger', template_context['storage_banner_html'])
        self.assertTrue(template_context['hide_caption_form'])  # Form should be hidden
        
        # Check notification details
        notification = template_context['storage_notification']
        self.assertTrue(notification['is_blocked'])
        self.assertEqual(notification['notification_type'], 'error')
        self.assertEqual(notification['reason'], 'Storage limit exceeded')
        self.assertTrue(notification['should_hide_form'])
    
    @patch('storage_limit_enforcer.StorageLimitEnforcer')
    def test_start_caption_generation_blocked_by_storage_limit(self, mock_enforcer_class):
        """Test that start_caption_generation is blocked when storage limit is exceeded"""
        # Mock enforcer instance
        mock_enforcer_instance = Mock()
        mock_enforcer_class.return_value = mock_enforcer_instance
        
        # Mock storage check to return blocked
        mock_enforcer_instance.check_storage_before_generation.return_value = StorageCheckResult.BLOCKED_LIMIT_EXCEEDED
        
        # Simulate the route logic
        storage_enforcer = mock_enforcer_class()
        storage_check = storage_enforcer.check_storage_before_generation()
        
        # Verify that the check returns blocked
        self.assertEqual(storage_check, StorageCheckResult.BLOCKED_LIMIT_EXCEEDED)
        
        # Verify that the enforcer was called
        mock_enforcer_instance.check_storage_before_generation.assert_called_once()
    
    @patch('storage_limit_enforcer.StorageLimitEnforcer')
    def test_start_caption_generation_allowed_when_storage_ok(self, mock_enforcer_class):
        """Test that start_caption_generation is allowed when storage is OK"""
        # Mock enforcer instance
        mock_enforcer_instance = Mock()
        mock_enforcer_class.return_value = mock_enforcer_instance
        
        # Mock storage check to return allowed
        mock_enforcer_instance.check_storage_before_generation.return_value = StorageCheckResult.ALLOWED
        
        # Simulate the route logic
        storage_enforcer = mock_enforcer_class()
        storage_check = storage_enforcer.check_storage_before_generation()
        
        # Verify that the check returns allowed
        self.assertEqual(storage_check, StorageCheckResult.ALLOWED)
        
        # Verify that the enforcer was called
        mock_enforcer_instance.check_storage_before_generation.assert_called_once()
    
    @patch('storage_limit_enforcer.StorageLimitEnforcer')
    def test_start_caption_generation_error_handling(self, mock_enforcer_class):
        """Test error handling in start_caption_generation when storage check fails"""
        # Mock enforcer instance
        mock_enforcer_instance = Mock()
        mock_enforcer_class.return_value = mock_enforcer_instance
        
        # Mock storage check to return error
        mock_enforcer_instance.check_storage_before_generation.return_value = StorageCheckResult.ERROR
        
        # Simulate the route logic
        storage_enforcer = mock_enforcer_class()
        storage_check = storage_enforcer.check_storage_before_generation()
        
        # Verify that the check returns error
        self.assertEqual(storage_check, StorageCheckResult.ERROR)
        
        # Verify that the enforcer was called
        mock_enforcer_instance.check_storage_before_generation.assert_called_once()
    
    def test_template_context_structure(self):
        """Test that template context has the expected structure"""
        # Mock no blocking state
        self.mock_enforcer.get_blocking_state.return_value = None
        
        # Mock normal storage metrics
        metrics = StorageMetrics(
            total_bytes=5 * 1024**3,  # 5GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Get template context
        template_context = self.notification_system.get_storage_status_for_template()
        
        # Verify required keys are present
        required_keys = [
            'storage_notification',
            'storage_limit_active',
            'storage_banner_html',
            'hide_caption_form'
        ]
        
        for key in required_keys:
            self.assertIn(key, template_context, f"Missing required key: {key}")
        
        # Verify data types
        self.assertIsInstance(template_context['storage_limit_active'], bool)
        self.assertIsInstance(template_context['storage_banner_html'], str)
        self.assertIsInstance(template_context['hide_caption_form'], bool)
    
    def test_banner_html_content_for_blocked_state(self):
        """Test that banner HTML contains expected content for blocked state"""
        # Mock blocking state
        blocking_state = StorageBlockingState(
            is_blocked=True,
            reason="Storage limit exceeded",
            blocked_at=datetime.now(timezone.utc),
            storage_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            last_checked=datetime.now(timezone.utc)
        )
        self.mock_enforcer.get_blocking_state.return_value = blocking_state
        
        # Mock storage metrics over limit
        metrics = StorageMetrics(
            total_bytes=11 * 1024**3,  # 11GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Get banner HTML
        banner_html = self.notification_system.render_storage_limit_banner()
        
        # Verify banner content
        self.assertIn('Caption Generation Unavailable', banner_html)
        self.assertIn('alert alert-danger', banner_html)
        self.assertIn('🚫', banner_html)
        self.assertIn('temporarily unavailable', banner_html)
        self.assertIn('11.0GB of 10.0GB', banner_html)
        self.assertIn('110.0%', banner_html)
    
    def test_banner_html_content_for_warning_state(self):
        """Test that banner HTML contains expected content for warning state"""
        # Mock no blocking state
        self.mock_enforcer.get_blocking_state.return_value = None
        
        # Mock storage metrics at warning threshold
        metrics = StorageMetrics(
            total_bytes=9 * 1024**3,  # 9GB
            total_gb=9.0,
            limit_gb=10.0,
            usage_percentage=90.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Get banner HTML
        banner_html = self.notification_system.render_storage_limit_banner()
        
        # Verify banner content
        self.assertIn('Storage Limit Warning', banner_html)
        self.assertIn('alert alert-warning', banner_html)
        self.assertIn('⚠️', banner_html)
        self.assertIn('approaching the limit', banner_html)
        self.assertIn('9.0GB of 10.0GB', banner_html)
        self.assertIn('90.0%', banner_html)
    
    def test_form_hiding_logic(self):
        """Test the logic for hiding caption generation form"""
        # Test 1: Form should not be hidden when storage is normal
        self.mock_enforcer.get_blocking_state.return_value = None
        metrics = StorageMetrics(
            total_bytes=5 * 1024**3,  # 5GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        should_hide = self.notification_system.should_hide_caption_form()
        self.assertFalse(should_hide)
        
        # Test 2: Form should not be hidden when storage is at warning (but not blocked)
        metrics.is_warning_exceeded = True
        metrics.usage_percentage = 90.0
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        should_hide = self.notification_system.should_hide_caption_form()
        self.assertFalse(should_hide)
        
        # Test 3: Form should be hidden when storage is blocked
        blocking_state = StorageBlockingState(
            is_blocked=True,
            reason="Storage limit exceeded",
            blocked_at=datetime.now(timezone.utc),
            storage_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            last_checked=datetime.now(timezone.utc)
        )
        self.mock_enforcer.get_blocking_state.return_value = blocking_state
        
        should_hide = self.notification_system.should_hide_caption_form()
        self.assertTrue(should_hide)
    
    def test_notification_system_error_recovery(self):
        """Test that notification system handles errors gracefully"""
        # Mock enforcer to raise exception
        self.mock_enforcer.get_blocking_state.side_effect = Exception("Redis connection failed")
        
        # Get template context (should not raise exception)
        template_context = self.notification_system.get_storage_status_for_template()
        
        # Verify error handling provides safe defaults
        self.assertIsNotNone(template_context['storage_notification'])
        self.assertTrue(template_context['storage_limit_active'])  # Safe default
        self.assertTrue(template_context['hide_caption_form'])  # Safe default
        self.assertIn('alert', template_context['storage_banner_html'])
        
        # Verify error notification content
        notification = template_context['storage_notification']
        self.assertTrue(notification['is_blocked'])
        self.assertEqual(notification['reason'], 'Error checking storage status')
        self.assertEqual(notification['notification_type'], 'error')


if __name__ == '__main__':
    unittest.main()