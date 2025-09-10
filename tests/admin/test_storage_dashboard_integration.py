# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for storage dashboard admin routes.

Tests the integration between AdminStorageDashboard and admin routes,
including template rendering and data flow.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.admin.components.admin_storage_dashboard import AdminStorageDashboard
from app.services.storage.components.storage_monitor_service import StorageMetrics


class TestStorageDashboardIntegration(unittest.TestCase):
    """Test cases for storage dashboard integration"""
    
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
        
        # Mock storage metrics
        self.mock_metrics = StorageMetrics(
            total_bytes=5368709120,  # 5 GB
            total_gb=5.0,
            limit_gb=10.0,
            usage_percentage=50.0,
            is_limit_exceeded=False,
            is_warning_exceeded=False,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = self.mock_metrics
        self.mock_monitor_service.get_cache_info.return_value = {
            'has_cache': True,
            'is_valid': True,
            'cache_age_seconds': 60
        }
        
        # Mock enforcer state
        self.mock_enforcer_service.get_blocking_state.return_value = None
        self.mock_enforcer_service.get_enforcement_statistics.return_value = {
            'total_checks': 100,
            'blocks_enforced': 0,
            'automatic_unblocks': 0,
            'limit_exceeded_count': 0
        }
        self.mock_enforcer_service.health_check.return_value = {'overall_healthy': True}
        
        # Create dashboard instance
        self.dashboard = AdminStorageDashboard(
            config_service=self.mock_config_service,
            monitor_service=self.mock_monitor_service,
            enforcer_service=self.mock_enforcer_service
        )
    
    def test_dashboard_data_for_template_rendering(self):
        """Test that dashboard data is properly formatted for template rendering"""
        # Get dashboard data
        dashboard_data = self.dashboard.get_storage_dashboard_data()
        gauge_data = self.dashboard.get_storage_gauge_data()
        summary_data = self.dashboard.get_storage_summary_card_data()
        actions_data = self.dashboard.get_quick_actions_data()
        
        # Verify dashboard data structure
        self.assertIsNotNone(dashboard_data)
        dashboard_dict = dashboard_data.to_dict()
        
        # Check required template fields
        required_fields = [
            'current_usage_gb', 'limit_gb', 'usage_percentage',
            'status_color', 'status_text', 'is_blocked',
            'formatted_usage', 'formatted_limit', 'formatted_percentage'
        ]
        
        for field in required_fields:
            self.assertIn(field, dashboard_dict, f"Missing required field: {field}")
        
        # Verify gauge data structure
        self.assertIsNotNone(gauge_data)
        gauge_required_fields = [
            'current_percentage', 'warning_percentage', 'status_color',
            'current_usage', 'limit', 'available'
        ]
        
        for field in gauge_required_fields:
            self.assertIn(field, gauge_data, f"Missing required gauge field: {field}")
        
        # Verify summary data structure
        self.assertIsNotNone(summary_data)
        summary_required_fields = [
            'title', 'current_usage', 'limit', 'percentage',
            'status_text', 'status_color', 'is_blocked'
        ]
        
        for field in summary_required_fields:
            self.assertIn(field, summary_data, f"Missing required summary field: {field}")
        
        # Verify actions data structure
        self.assertIsNotNone(actions_data)
        self.assertIn('actions', actions_data)
        self.assertIn('has_critical_actions', actions_data)
        self.assertIsInstance(actions_data['actions'], list)
    
    def test_template_data_values(self):
        """Test that template data contains expected values"""
        # Get all dashboard data
        dashboard_data = self.dashboard.get_storage_dashboard_data()
        gauge_data = self.dashboard.get_storage_gauge_data()
        summary_data = self.dashboard.get_storage_summary_card_data()
        
        # Verify values match expected metrics
        self.assertEqual(gauge_data['current_percentage'], 50.0)
        self.assertEqual(gauge_data['status_color'], 'green')
        self.assertEqual(gauge_data['current_usage'], '5.00 GB')
        self.assertEqual(gauge_data['limit'], '10.00 GB')
        self.assertEqual(gauge_data['available'], '5.00 GB')
        
        # Verify summary data values
        self.assertEqual(summary_data['current_usage'], '5.00 GB')
        self.assertEqual(summary_data['limit'], '10.00 GB')
        self.assertEqual(summary_data['percentage'], '50.0%')
        self.assertEqual(summary_data['status_text'], 'Normal')
        self.assertEqual(summary_data['status_color'], 'green')
        self.assertFalse(summary_data['is_blocked'])
    
    def test_template_data_warning_state(self):
        """Test template data for warning storage state"""
        # Update mock metrics for warning state
        warning_metrics = StorageMetrics(
            total_bytes=8589934592,  # 8 GB
            total_gb=8.0,
            limit_gb=10.0,
            usage_percentage=80.0,
            is_limit_exceeded=False,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = warning_metrics
        
        # Get dashboard data
        gauge_data = self.dashboard.get_storage_gauge_data()
        summary_data = self.dashboard.get_storage_summary_card_data()
        
        # Verify warning state values
        self.assertEqual(gauge_data['current_percentage'], 80.0)
        self.assertEqual(gauge_data['status_color'], 'red')  # 80% is red threshold
        self.assertEqual(gauge_data['current_usage'], '8.00 GB')
        
        # Verify summary reflects warning state
        self.assertEqual(summary_data['status_color'], 'red')
        self.assertEqual(summary_data['status_text'], 'Critical')
        self.assertTrue(summary_data['is_warning'])
    
    def test_template_data_blocked_state(self):
        """Test template data for blocked storage state"""
        # Update mock metrics for blocked state
        blocked_metrics = StorageMetrics(
            total_bytes=11811160064,  # 11 GB
            total_gb=11.0,
            limit_gb=10.0,
            usage_percentage=110.0,
            is_limit_exceeded=True,
            is_warning_exceeded=True,
            last_calculated=datetime.now()
        )
        
        self.mock_monitor_service.get_storage_metrics.return_value = blocked_metrics
        
        # Mock blocking state
        mock_blocking_state = Mock()
        mock_blocking_state.is_blocked = True
        mock_blocking_state.reason = "Storage limit exceeded"
        self.mock_enforcer_service.get_blocking_state.return_value = mock_blocking_state
        
        # Get dashboard data
        gauge_data = self.dashboard.get_storage_gauge_data()
        summary_data = self.dashboard.get_storage_summary_card_data()
        actions_data = self.dashboard.get_quick_actions_data()
        
        # Verify blocked state values
        self.assertEqual(gauge_data['current_percentage'], 100.0)  # Capped at 100% for display
        self.assertTrue(gauge_data['is_over_limit'])
        self.assertEqual(gauge_data['status_color'], 'red')
        
        # Verify summary reflects blocked state
        self.assertTrue(summary_data['is_blocked'])
        self.assertTrue(summary_data['is_critical'])
        self.assertEqual(summary_data['block_reason'], "Storage limit exceeded")
        
        # Verify actions include override option
        self.assertTrue(actions_data['has_critical_actions'])
        override_action = next((a for a in actions_data['actions'] if 'Override' in a['title']), None)
        self.assertIsNotNone(override_action)
    
    def test_error_handling_for_templates(self):
        """Test that error states provide safe template data"""
        # Mock service to raise exception
        self.mock_monitor_service.get_storage_metrics.side_effect = Exception("Storage error")
        
        # Get dashboard data (should handle error gracefully)
        gauge_data = self.dashboard.get_storage_gauge_data()
        summary_data = self.dashboard.get_storage_summary_card_data()
        actions_data = self.dashboard.get_quick_actions_data()
        
        # Verify error handling provides safe defaults
        self.assertEqual(gauge_data['current_percentage'], 0.0)
        self.assertEqual(gauge_data['status_color'], 'red')
        self.assertEqual(gauge_data['status_text'], 'Error')
        # Note: error key may not be present if the error occurs in dashboard data collection
        
        # Verify summary data has error state
        self.assertEqual(summary_data['status_color'], 'red')
        self.assertEqual(summary_data['status_text'], 'Error')
        self.assertTrue(summary_data['is_blocked'])  # Safe mode
        self.assertIn('Storage monitoring error', summary_data['block_reason'])
        
        # Verify actions data handles error
        self.assertIn('actions', actions_data)
        self.assertIsInstance(actions_data['actions'], list)
    
    def test_bootstrap_color_mapping(self):
        """Test Bootstrap color class mapping for templates"""
        # Test color mappings
        self.assertEqual(self.dashboard._get_bootstrap_color('green'), 'success')
        self.assertEqual(self.dashboard._get_bootstrap_color('yellow'), 'warning')
        self.assertEqual(self.dashboard._get_bootstrap_color('red'), 'danger')
        self.assertEqual(self.dashboard._get_bootstrap_color('unknown'), 'secondary')
        
        # Verify summary data uses correct Bootstrap classes
        summary_data = self.dashboard.get_storage_summary_card_data()
        self.assertEqual(summary_data['card_class'], 'border-success')
        self.assertEqual(summary_data['header_class'], 'bg-success text-white')
    
    def test_health_check_integration(self):
        """Test health check integration for admin monitoring"""
        # Perform health check
        health = self.dashboard.health_check()
        
        # Verify health check structure for admin display
        required_health_fields = [
            'config_service_healthy',
            'monitor_service_healthy', 
            'enforcer_service_healthy',
            'dashboard_data_accessible',
            'overall_healthy'
        ]
        
        for field in required_health_fields:
            self.assertIn(field, health, f"Missing health field: {field}")
        
        # Verify healthy state
        self.assertTrue(health['overall_healthy'])
        
        # Test unhealthy state
        self.mock_config_service.validate_storage_config.side_effect = Exception("Config error")
        health_unhealthy = self.dashboard.health_check()
        
        self.assertFalse(health_unhealthy['overall_healthy'])
        self.assertIn('config_error', health_unhealthy)


if __name__ == '__main__':
    unittest.main()