# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for AdminStorageDashboard class.

Tests the admin dashboard integration for storage monitoring,
including metrics display, status indicators, and color-coded status.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.admin.components.admin_storage_dashboard import AdminStorageDashboard, StorageDashboardData
from app.services.storage.components.storage_monitor_service import StorageMetrics


class TestAdminStorageDashboard(unittest.TestCase):
    """Test cases for AdminStorageDashboard class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock services
        self.mock_config_service = Mock()
        self.mock_monitor_service = Mock()
        self.mock_enforcer_service = Mock()
        
        # Configure mock defaults
        self.mock_config_service.get_max_storage_gb.return_value = 10.0
        self.mock_config_service.get_warning_threshold_gb.return_value = 8.0
        self.mock_config_service.validate_storage_config.return_value = True
        
        # Create dashboard instance
        self.dashboard = AdminStorageDashboard(
            config_service=self.mock_config_service,
            monitor_service=self.mock_monitor_service,
            enforcer_service=self.mock_enforcer_service
        )
    
    def test_initialization(self):
        """Test AdminStorageDashboard initialization"""
        self.assertIsNotNone(self.dashboard.config_service)
        self.assertIsNotNone(self.dashboard.monitor_service)
        self.assertIsNotNone(self.dashboard.enforcer_service)
    
    def test_get_storage_status_color_green(self):
        """Test storage status color for normal usage (green)"""
        # Test normal usage (below 70%)
        color = self.dashboard.get_storage_status_color(50.0, False)
        self.assertEqual(color, 'green')
        
        color = self.dashboard.get_storage_status_color(69.9, False)
        self.assertEqual(color, 'green')
    
    def test_get_storage_status_color_yellow(self):
        """Test storage status color for warning usage (yellow)"""
        # Test warning usage (70-80%)
        color = self.dashboard.get_storage_status_color(70.0, False)
        self.assertEqual(color, 'yellow')
        
        color = self.dashboard.get_storage_status_color(79.9, False)
        self.assertEqual(color, 'yellow')
    
    def test_get_storage_status_color_red(self):
        """Test storage status color for critical usage (red)"""
        # Test critical usage (above 80%)
        color = self.dashboard.get_storage_status_color(80.0, False)
        self.assertEqual(color, 'red')
        
        color = self.dashboard.get_storage_status_color(95.0, False)
        self.assertEqual(color, 'red')
        
        # Test limit exceeded (always red)
        color = self.dashboard.get_storage_status_color(50.0, True)
        self.assertEqual(color, 'red')
    
    def test_format_storage_display(self):
        """Test storage display formatting"""
        display = self.dashboard.format_storage_display(5.25, 10.0)
        self.assertEqual(display, "5.25 GB / 10.00 GB")
        
        display = self.dashboard.format_storage_display(0.0, 10.0)
        self.assertEqual(display, "0.00 GB / 10.00 GB")
    
    def test_get_storage_dashboard_data_normal(self):
        """Test getting dashboard data for normal storage usage"""
        # Mock storage metrics
        mock_metrics = StorageMetrics(
            total_bytes=5368709120,  # 5 GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {
            'has_cache': True,
            'is_valid': True,
            'cache_age_seconds': 60
        }
        
        # Mock enforcer state
        self.mock_enforcer_service.get_blocking_state.return_value = None
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {
            'total_checks': 100,
            'blocks_enforced': 0
        }
        
        # Get dashboard data
        data = self.dashboard.get_storage_dashboard_data()
        
        # Verify data
        self.assertIsInstance(data, StorageDashboardData)
        self.assertEqual(data.current_usage_gb, 5.0)
        self.assertEqual(data.limit_gb, 10.0)
        self.assertEqual(data.usage_percentage, 50.0)
        self.assertEqual(data.status_color, 'green')
        self.assertEqual(data.status_text, 'Normal')
        self.assertFalse(data.is_blocked)
        self.assertFalse(data.is_warning_exceeded)
        self.assertFalse(data.is_limit_exceeded)
    
    def test_get_storage_dashboard_data_warning(self):
        """Test getting dashboard data for warning storage usage"""
        # Mock storage metrics for warning level
        mock_metrics = StorageMetrics(
            total_bytes=8589934592,  # 8 GB
            total_gb=8.0,
            limit_gb=10.0,
            usage_percentage=80.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {'has_cache': False}
        self.mock_enforcer_service.get_blocking_state.return_value = None
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {}
        
        # Get dashboard data
        data = self.dashboard.get_storage_dashboard_data()
        
        # Verify warning status
        self.assertEqual(data.status_color, 'red')  # 80% is red threshold
        self.assertEqual(data.status_text, 'Critical')
        self.assertTrue(data.is_warning_exceeded)
        self.assertFalse(data.is_limit_exceeded)
    
    def test_get_storage_dashboard_data_blocked(self):
        """Test getting dashboard data when storage is blocked"""
        # Mock storage metrics for limit exceeded
        mock_metrics = StorageMetrics(
            total_bytes=11811160064,  # 11 GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {'has_cache': True}
        
        # Mock blocking state
        mock_blocking_state = Mock()
        mock_blocking_state.is_blocked = True
        mock_blocking_state.reason = "Storage limit exceeded"
        self.mock_enforcer_service.get_blocking_state.return_value = mock_blocking_state
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {
            'blocks_enforced': 1
        }
        
        # Get dashboard data
        data = self.dashboard.get_storage_dashboard_data()
        
        # Verify blocked status
        self.assertEqual(data.status_color, 'red')
        self.assertEqual(data.status_text, 'Critical')
        self.assertTrue(data.is_blocked)
        self.assertEqual(data.block_reason, "Storage limit exceeded")
        self.assertTrue(data.is_limit_exceeded)
    
    def test_get_storage_dashboard_data_error_handling(self):
        """Test error handling in dashboard data collection"""
        # Mock service to raise exception
        self.mock_monitor_service.get_storage_metrics.side_effect = Exception("Storage error")
        
        # Get dashboard data (should return error data)
        data = self.dashboard.get_storage_dashboard_data()
        
        # Verify error handling
        self.assertEqual(data.status_color, 'red')
        self.assertEqual(data.status_text, 'Error')
        self.assertTrue(data.is_blocked)  # Safe mode
        self.assertIn("Storage monitoring error", data.block_reason)
    
    def test_get_storage_gauge_data(self):
        """Test storage gauge data for frontend visualization"""
        # Mock storage metrics
        mock_metrics = StorageMetrics(
            total_bytes=7516192768,  # 7 GB
            total_gb=7.0,
            limit_gb=10.0,
            usage_percentage=70.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {'has_cache': True}
        self.mock_enforcer_service.get_blocking_state.return_value = None
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {}
        
        # Get gauge data
        gauge_data = self.dashboard.get_storage_gauge_data()
        
        # Verify gauge data
        self.assertEqual(gauge_data['current_percentage'], 70.0)
        self.assertEqual(gauge_data['warning_percentage'], 80.0)  # 8GB / 10GB * 100
        self.assertEqual(gauge_data['status_color'], 'yellow')  # 70% is yellow
        self.assertEqual(gauge_data['current_usage'], '7.00 GB')
        self.assertEqual(gauge_data['limit'], '10.00 GB')
        self.assertEqual(gauge_data['available'], '3.00 GB')
        self.assertFalse(gauge_data['is_over_limit'])
    
    def test_get_storage_summary_card_data(self):
        """Test storage summary card data for dashboard display"""
        # Mock storage metrics
        mock_metrics = StorageMetrics(
            total_bytes=5368709120,  # 5 GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {'has_cache': True}
        self.mock_enforcer_service.get_blocking_state.return_value = None
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {}
        
        # Get summary card data
        card_data = self.dashboard.get_storage_summary_card_data()
        
        # Verify card data
        self.assertEqual(card_data['title'], 'Storage Usage')
        self.assertEqual(card_data['current_usage'], '5.00 GB')
        self.assertEqual(card_data['limit'], '10.00 GB')
        self.assertEqual(card_data['percentage'], '50.0%')
        self.assertEqual(card_data['available'], '5.00 GB')
        self.assertEqual(card_data['status_text'], 'Normal')
        self.assertEqual(card_data['status_color'], 'green')
        self.assertEqual(card_data['status_icon'], 'bi-check-circle-fill')
        self.assertEqual(card_data['card_class'], 'border-success')
        self.assertEqual(card_data['header_class'], 'bg-success text-white')
        self.assertFalse(card_data['is_blocked'])
        self.assertFalse(card_data['is_warning'])
        self.assertFalse(card_data['is_critical'])
    
    def test_get_quick_actions_data(self):
        """Test quick actions data for dashboard display"""
        # Mock normal storage state
        mock_metrics = StorageMetrics(
            total_bytes=5368709120,  # 5 GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {'has_cache': True}
        self.mock_enforcer_service.get_blocking_state.return_value = None
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {}
        
        # Get actions data
        actions_data = self.dashboard.get_quick_actions_data()
        
        # Verify actions data
        self.assertIn('actions', actions_data)
        self.assertIn('has_critical_actions', actions_data)
        self.assertIn('total_actions', actions_data)
        
        # Should have cleanup and refresh actions
        actions = actions_data['actions']
        self.assertGreaterEqual(len(actions), 2)
        
        # Find cleanup action
        cleanup_action = next((a for a in actions if 'Cleanup' in a['title']), None)
        self.assertIsNotNone(cleanup_action)
        self.assertEqual(cleanup_action['url'], 'admin.cleanup')
        self.assertEqual(cleanup_action['icon'], 'bi-trash')
    
    def test_get_quick_actions_data_blocked(self):
        """Test quick actions data when storage is blocked"""
        # Mock blocked storage state
        mock_metrics = StorageMetrics(
            total_bytes=11811160064,  # 11 GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {'has_cache': True}
        
        # Mock blocking state
        mock_blocking_state = Mock()
        mock_blocking_state.is_blocked = True
        mock_blocking_state.reason = "Storage limit exceeded"
        self.mock_enforcer_service.get_blocking_state.return_value = mock_blocking_state
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {}
        
        # Get actions data
        actions_data = self.dashboard.get_quick_actions_data()
        
        # Should have critical actions when blocked
        self.assertTrue(actions_data['has_critical_actions'])
        
        # Should have override action
        actions = actions_data['actions']
        override_action = next((a for a in actions if 'Override' in a['title']), None)
        self.assertIsNotNone(override_action)
        self.assertEqual(override_action['priority'], 1)  # High priority
    
    def test_health_check(self):
        """Test storage dashboard health check"""
        # Mock healthy services
        self.mock_config_service.validate_storage_config.return_value = True
        self.mock_monitor_service.get_storage_metrics.return_value = Mock()
        self.mock_enforcer_service.health_check.return_value = {'overall_healthy': True}
        
        # Perform health check
        health = self.dashboard.health_check()
        
        # Verify health check results
        self.assertIn('config_service_healthy', health)
        self.assertIn('monitor_service_healthy', health)
        self.assertIn('enforcer_service_healthy', health)
        self.assertIn('dashboard_data_accessible', health)
        self.assertIn('overall_healthy', health)
        
        # Should be healthy
        self.assertTrue(health['config_service_healthy'])
        self.assertTrue(health['monitor_service_healthy'])
        self.assertTrue(health['enforcer_service_healthy'])
        self.assertTrue(health['dashboard_data_accessible'])
        self.assertTrue(health['overall_healthy'])
    
    def test_health_check_unhealthy(self):
        """Test storage dashboard health check with unhealthy services"""
        # Mock unhealthy services
        self.mock_config_service.validate_storage_config.side_effect = Exception("Config error")
        self.mock_monitor_service.get_storage_metrics.side_effect = Exception("Monitor error")
        self.mock_enforcer_service.health_check.return_value = {'overall_healthy': False}
        
        # Perform health check
        health = self.dashboard.health_check()
        
        # Should be unhealthy
        self.assertFalse(health['config_service_healthy'])
        self.assertFalse(health['monitor_service_healthy'])
        self.assertFalse(health['enforcer_service_healthy'])
        self.assertFalse(health['overall_healthy'])
        
        # Should have error details
        self.assertIn('config_error', health)
        self.assertIn('monitor_error', health)


if __name__ == '__main__':
    unittest.main()