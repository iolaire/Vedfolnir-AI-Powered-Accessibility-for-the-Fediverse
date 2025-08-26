# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for StorageUserNotificationSystem.

Tests the user notification system for storage limits, including banner generation,
form hiding logic, and template context creation.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_user_notification_system import (
    StorageUserNotificationSystem, 
    StorageNotificationContext,
    StorageUserNotificationSystemError
)
from storage_limit_enforcer import StorageBlockingState
from storage_monitor_service import StorageMetrics


class TestStorageUserNotificationSystem(unittest.TestCase):
    """Test cases for StorageUserNotificationSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
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
    
    def test_initialization(self):
        """Test notification system initialization"""
        self.assertIsNotNone(self.notification_system)
        self.assertEqual(self.notification_system.config_service, self.mock_config_service)
        self.assertEqual(self.notification_system.monitor_service, self.mock_monitor_service)
        self.assertEqual(self.notification_system.enforcer, self.mock_enforcer)
    
    def test_get_storage_notification_context_no_issues(self):
        """Test getting notification context when no storage issues exist"""
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
        
        # Get notification context
        context = self.notification_system.get_storage_notification_context()
        
        # Should return None (no notifications needed)
        self.assertIsNone(context)
    
    def test_get_storage_notification_context_blocked_state(self):
        """Test getting notification context when storage is blocked"""
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
        
        # Get notification context
        context = self.notification_system.get_storage_notification_context()
        
        # Should return blocked context
        self.assertIsNotNone(context)
        self.assertTrue(context.is_blocked)
        self.assertEqual(context.reason, "Storage limit exceeded")
        self.assertEqual(context.storage_gb, 11.0)
        self.assertEqual(context.limit_gb, 10.0)
        self.assertEqual(context.usage_percentage, 110.0)
        self.assertEqual(context.blocked_at, blocked_at)
        self.assertTrue(context.should_hide_form)
        self.assertEqual(context.notification_type, 'error')
        self.assertIn('alert alert-danger', context.banner_html)
    
    def test_get_storage_notification_context_warning_state(self):
        """Test getting notification context when storage is at warning threshold"""
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
        
        # Get notification context
        context = self.notification_system.get_storage_notification_context()
        
        # Should return warning context
        self.assertIsNotNone(context)
        self.assertFalse(context.is_blocked)
        self.assertIn("90.0% of limit", context.reason)
        self.assertEqual(context.storage_gb, 9.0)
        self.assertEqual(context.limit_gb, 10.0)
        self.assertEqual(context.usage_percentage, 90.0)
        self.assertIsNone(context.blocked_at)
        self.assertFalse(context.should_hide_form)
        self.assertEqual(context.notification_type, 'warning')
        self.assertIn('alert alert-warning', context.banner_html)
    
    def test_get_storage_notification_context_error_handling(self):
        """Test error handling in get_storage_notification_context"""
        # Mock enforcer to raise exception
        self.mock_enforcer.get_blocking_state.side_effect = Exception("Redis connection failed")
        
        # Get notification context
        context = self.notification_system.get_storage_notification_context()
        
        # Should return error context
        self.assertIsNotNone(context)
        self.assertTrue(context.is_blocked)
        self.assertEqual(context.reason, "Error checking storage status")
        self.assertTrue(context.should_hide_form)
        self.assertEqual(context.notification_type, 'error')
        self.assertIn('alert', context.banner_html)
    
    def test_render_storage_limit_banner_no_notification(self):
        """Test rendering banner when no notification is needed"""
        # Mock no blocking state and no warning
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
        
        # Render banner
        banner_html = self.notification_system.render_storage_limit_banner()
        
        # Should return empty string
        self.assertEqual(banner_html, "")
    
    def test_render_storage_limit_banner_with_notification(self):
        """Test rendering banner when notification is needed"""
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
        
        # Render banner
        banner_html = self.notification_system.render_storage_limit_banner()
        
        # Should return HTML banner
        self.assertIsInstance(banner_html, str)
        self.assertIn('alert', banner_html)
        self.assertIn('Caption Generation Unavailable', banner_html)
    
    def test_render_storage_limit_banner_error_handling(self):
        """Test error handling in render_storage_limit_banner"""
        # Mock enforcer to raise exception
        self.mock_enforcer.get_blocking_state.side_effect = Exception("Redis connection failed")
        
        # Render banner
        banner_html = self.notification_system.render_storage_limit_banner()
        
        # Should return error banner
        self.assertIsInstance(banner_html, str)
        self.assertIn('alert', banner_html)
        self.assertIn('Storage Status Unavailable', banner_html)
    
    def test_should_hide_caption_form_not_blocked(self):
        """Test should_hide_caption_form when not blocked"""
        # Mock no blocking state
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
        
        # Check if form should be hidden
        should_hide = self.notification_system.should_hide_caption_form()
        
        # Should not hide form
        self.assertFalse(should_hide)
    
    def test_should_hide_caption_form_blocked(self):
        """Test should_hide_caption_form when blocked"""
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
        
        # Check if form should be hidden
        should_hide = self.notification_system.should_hide_caption_form()
        
        # Should hide form
        self.assertTrue(should_hide)
    
    def test_should_hide_caption_form_error_handling(self):
        """Test error handling in should_hide_caption_form"""
        # Mock enforcer to raise exception
        self.mock_enforcer.get_blocking_state.side_effect = Exception("Redis connection failed")
        
        # Check if form should be hidden
        should_hide = self.notification_system.should_hide_caption_form()
        
        # Should hide form (safe default)
        self.assertTrue(should_hide)
    
    def test_get_storage_status_for_template_normal(self):
        """Test getting storage status for template context (normal state)"""
        # Mock no blocking state
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
        
        # Get template status
        status = self.notification_system.get_storage_status_for_template()
        
        # Check status structure
        self.assertIsInstance(status, dict)
        self.assertIsNone(status['storage_notification'])
        self.assertFalse(status['storage_limit_active'])
        self.assertEqual(status['storage_banner_html'], '')
        self.assertFalse(status['hide_caption_form'])
    
    def test_get_storage_status_for_template_blocked(self):
        """Test getting storage status for template context (blocked state)"""
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
        
        # Get template status
        status = self.notification_system.get_storage_status_for_template()
        
        # Check status structure
        self.assertIsInstance(status, dict)
        self.assertIsNotNone(status['storage_notification'])
        self.assertTrue(status['storage_limit_active'])
        self.assertIsInstance(status['storage_banner_html'], str)
        self.assertIn('alert', status['storage_banner_html'])
        self.assertTrue(status['hide_caption_form'])
    
    def test_get_storage_status_for_template_error_handling(self):
        """Test error handling in get_storage_status_for_template"""
        # Mock enforcer to raise exception
        self.mock_enforcer.get_blocking_state.side_effect = Exception("Redis connection failed")
        
        # Get template status
        status = self.notification_system.get_storage_status_for_template()
        
        # Check error handling (safe defaults)
        self.assertIsInstance(status, dict)
        self.assertIsNotNone(status['storage_notification'])  # Error context is returned
        self.assertTrue(status['storage_limit_active'])  # Safe default
        self.assertIsInstance(status['storage_banner_html'], str)
        self.assertIn('alert', status['storage_banner_html'])
        self.assertTrue(status['hide_caption_form'])  # Safe default
        
        # Check that error notification context is properly structured
        notification = status['storage_notification']
        self.assertTrue(notification['is_blocked'])
        self.assertEqual(notification['reason'], 'Error checking storage status')
        self.assertTrue(notification['should_hide_form'])
        self.assertEqual(notification['notification_type'], 'error')
    
    def test_storage_notification_context_to_dict(self):
        """Test StorageNotificationContext to_dict method"""
        blocked_at = datetime.now(timezone.utc)
        context = StorageNotificationContext(
            is_blocked=True,
            reason="Test reason",
            storage_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            blocked_at=blocked_at,
            banner_html="<div>Test banner</div>",
            should_hide_form=True,
            notification_type='error'
        )
        
        # Convert to dict
        context_dict = context.to_dict()
        
        # Check dict structure
        self.assertIsInstance(context_dict, dict)
        self.assertTrue(context_dict['is_blocked'])
        self.assertEqual(context_dict['reason'], "Test reason")
        self.assertEqual(context_dict['storage_gb'], 11.0)
        self.assertEqual(context_dict['limit_gb'], 10.0)
        self.assertEqual(context_dict['usage_percentage'], 110.0)
        self.assertEqual(context_dict['blocked_at'], blocked_at.isoformat())
        self.assertEqual(context_dict['banner_html'], "<div>Test banner</div>")
        self.assertTrue(context_dict['should_hide_form'])
        self.assertEqual(context_dict['notification_type'], 'error')
    
    def test_health_check_all_healthy(self):
        """Test health check when all components are healthy"""
        # Mock healthy enforcer
        self.mock_enforcer.health_check.return_value = {'overall_healthy': True}
        
        # Mock healthy monitor service
        metrics = StorageMetrics(
            total_bytes=5 * 1024**3,
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now(timezone.utc)
        )
        self.mock_monitor_service.get_storage_metrics.return_value = metrics
        
        # Perform health check
        health = self.notification_system.health_check()
        
        # Check health results
        self.assertIsInstance(health, dict)
        self.assertTrue(health['enforcer_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['notification_context_accessible'])
        self.assertTrue(health['overall_healthy'])
    
    def test_health_check_with_failures(self):
        """Test health check when components have failures"""
        # Mock unhealthy enforcer
        self.mock_enforcer.health_check.return_value = {'overall_healthy': False}
        
        # Mock monitor service failure
        self.mock_monitor_service.get_storage_metrics.side_effect = Exception("Monitor failed")
        
        # Mock config service failure
        self.mock_config_service.validate_storage_config.side_effect = Exception("Config failed")
        
        # Perform health check
        health = self.notification_system.health_check()
        
        # Check health results
        self.assertIsInstance(health, dict)
        self.assertFalse(health['enforcer_healthy'])
        self.assertFalse(health['monitor_service_healthy'])
        self.assertFalse(health['config_service_healthy'])
        self.assertFalse(health['overall_healthy'])
        self.assertIn('enforcer_error', health)
        self.assertIn('monitor_error', health)
        self.assertIn('config_error', health)


if __name__ == '__main__':
    unittest.main()