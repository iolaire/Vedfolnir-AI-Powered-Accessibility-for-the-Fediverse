# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RateLimitingConfigurationAdapter

Tests the integration between rate limiting and configuration service.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from rate_limiting_configuration_adapter import RateLimitingConfigurationAdapter, create_rate_limiting_configuration_adapter


class TestRateLimitingConfigurationAdapter(unittest.TestCase):
    """Test cases for RateLimitingConfigurationAdapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.side_effect = self._mock_get_config
        self.mock_config_service.subscribe_to_changes.return_value = "subscription_id"
        self.mock_config_service.unsubscribe.return_value = True
        
        # Mock security middleware
        self.mock_security_middleware = Mock()
        self.mock_security_middleware._rate_limit_config = {}
        
        # Default configuration values
        self.default_config = {
            'rate_limit_per_user_per_hour': 1000,
            'rate_limit_per_ip_per_minute': 120,
            'rate_limiting_enabled': True,
            'rate_limit_window_minutes': 1,
            'rate_limit_burst_size': 10
        }
    
    def _mock_get_config(self, key, default=None):
        """Mock configuration service get_config method"""
        config_map = {
            'rate_limit_per_user_per_hour': 1000,
            'rate_limit_per_ip_per_minute': 120,
            'rate_limiting_enabled': True,
            'rate_limit_window_minutes': 1,
            'rate_limit_burst_size': 10
        }
        return config_map.get(key, default)
    
    def test_initialization(self):
        """Test adapter initialization"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Verify configuration service calls
        expected_calls = [
            call('rate_limit_per_user_per_hour', 1000),
            call('rate_limit_per_ip_per_minute', 120),
            call('rate_limiting_enabled', True),
            call('rate_limit_window_minutes', 1),
            call('rate_limit_burst_size', 10)
        ]
        self.mock_config_service.get_config.assert_has_calls(expected_calls, any_order=True)
        
        # Verify subscriptions were created
        self.assertEqual(self.mock_config_service.subscribe_to_changes.call_count, 5)
        
        # Verify configuration was applied
        self.assertEqual(adapter.get_current_rate_limit_per_user_per_hour(), 1000)
        self.assertEqual(adapter.get_current_rate_limit_per_ip_per_minute(), 120)
        self.assertTrue(adapter.is_rate_limiting_enabled())
    
    def test_initialization_with_config_service_failure(self):
        """Test adapter initialization when configuration service fails"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config.side_effect = Exception("Config service unavailable")
        
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Should use default values when config service fails
        self.assertEqual(adapter.get_current_rate_limit_per_user_per_hour(), 1000)
        self.assertEqual(adapter.get_current_rate_limit_per_ip_per_minute(), 120)
        self.assertTrue(adapter.is_rate_limiting_enabled())
    
    def test_configuration_change_handlers(self):
        """Test configuration change event handlers"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Test rate limit per user change
        adapter._handle_rate_limit_per_user_change('rate_limit_per_user_per_hour', 1000, 2000)
        self.assertEqual(adapter._current_config['rate_limit_per_user_per_hour'], 2000)
        
        # Test rate limit per IP change
        adapter._handle_rate_limit_per_ip_change('rate_limit_per_ip_per_minute', 120, 240)
        self.assertEqual(adapter._current_config['rate_limit_per_ip_per_minute'], 240)
        
        # Test rate limiting enabled change
        adapter._handle_rate_limiting_enabled_change('rate_limiting_enabled', True, False)
        self.assertEqual(adapter._current_config['rate_limiting_enabled'], False)
        
        # Test rate limit window change
        adapter._handle_rate_limit_window_change('rate_limit_window_minutes', 1, 5)
        self.assertEqual(adapter._current_config['rate_limit_window_minutes'], 5)
        
        # Test burst size change
        adapter._handle_rate_limit_burst_size_change('rate_limit_burst_size', 10, 20)
        self.assertEqual(adapter._current_config['rate_limit_burst_size'], 20)
    
    def test_configuration_getters(self):
        """Test configuration getter methods"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Test all getter methods
        self.assertEqual(adapter.get_current_rate_limit_per_user_per_hour(), 1000)
        self.assertEqual(adapter.get_current_rate_limit_per_ip_per_minute(), 120)
        self.assertTrue(adapter.is_rate_limiting_enabled())
        self.assertEqual(adapter.get_current_rate_limit_window_minutes(), 1)
        self.assertEqual(adapter.get_current_rate_limit_burst_size(), 10)
        
        # Test configuration summary
        summary = adapter.get_configuration_summary()
        self.assertEqual(summary['rate_limit_per_user_per_hour'], 1000)
        self.assertEqual(summary['rate_limit_per_ip_per_minute'], 120)
        self.assertTrue(summary['rate_limiting_enabled'])
    
    def test_rate_limit_checking_methods(self):
        """Test rate limit checking methods"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Test user rate limit checking
        self.assertTrue(adapter.check_rate_limit_for_user(1, 500))  # Within limit
        self.assertFalse(adapter.check_rate_limit_for_user(1, 1500))  # Over limit
        
        # Test IP rate limit checking
        self.assertTrue(adapter.check_rate_limit_for_ip('192.168.1.1', 60))  # Within limit
        self.assertFalse(adapter.check_rate_limit_for_ip('192.168.1.1', 150))  # Over limit
        
        # Test with rate limiting disabled
        adapter._current_config['rate_limiting_enabled'] = False
        self.assertTrue(adapter.check_rate_limit_for_user(1, 1500))  # Should pass when disabled
        self.assertTrue(adapter.check_rate_limit_for_ip('192.168.1.1', 150))  # Should pass when disabled
    
    def test_rate_limit_info_methods(self):
        """Test rate limit info methods"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Test user rate limit info
        user_info = adapter.get_rate_limit_info_for_user(1, 500)
        self.assertEqual(user_info['user_id'], 1)
        self.assertEqual(user_info['rate_limit'], 1000)
        self.assertEqual(user_info['current_requests'], 500)
        self.assertEqual(user_info['remaining_requests'], 500)
        self.assertEqual(user_info['window'], 'hour')
        self.assertTrue(user_info['enabled'])
        
        # Test IP rate limit info
        ip_info = adapter.get_rate_limit_info_for_ip('192.168.1.1', 60)
        self.assertEqual(ip_info['ip_address'], '192.168.1.1')
        self.assertEqual(ip_info['rate_limit'], 120)
        self.assertEqual(ip_info['current_requests'], 60)
        self.assertEqual(ip_info['remaining_requests'], 60)
        self.assertEqual(ip_info['window'], 'minute')
        self.assertEqual(ip_info['burst_size'], 10)
        self.assertTrue(ip_info['enabled'])
    
    def test_security_middleware_integration(self):
        """Test integration with security middleware"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Verify security middleware was updated
        expected_config = {
            'requests_per_minute': 120,
            'window_minutes': 1,
            'burst_size': 10,
            'enabled': True
        }
        
        # Check that security middleware config was updated
        for key, value in expected_config.items():
            self.assertEqual(self.mock_security_middleware._rate_limit_config[key], value)
    
    def test_refresh_configuration(self):
        """Test configuration refresh"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Mock new configuration values
        def mock_get_config_refreshed(key, default=None):
            config_map = {
                'rate_limit_per_user_per_hour': 2000,  # Changed from 1000
                'rate_limit_per_ip_per_minute': 240,   # Changed from 120
                'rate_limiting_enabled': False,        # Changed from True
                'rate_limit_window_minutes': 5,        # Changed from 1
                'rate_limit_burst_size': 20            # Changed from 10
            }
            return config_map.get(key, default)
        
        # Update mock to return new values
        self.mock_config_service.get_config.side_effect = mock_get_config_refreshed
        
        # Refresh configuration
        adapter.refresh_configuration()
        
        # Verify configuration service was called
        self.mock_config_service.refresh_config.assert_called_once()
        
        # Verify new values were loaded
        self.assertEqual(adapter.get_current_rate_limit_per_user_per_hour(), 2000)
        self.assertEqual(adapter.get_current_rate_limit_per_ip_per_minute(), 240)
        self.assertFalse(adapter.is_rate_limiting_enabled())
        self.assertEqual(adapter.get_current_rate_limit_window_minutes(), 5)
        self.assertEqual(adapter.get_current_rate_limit_burst_size(), 20)
    
    def test_cleanup(self):
        """Test adapter cleanup"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Cleanup should unsubscribe from all configuration changes
        adapter.cleanup()
        
        # Verify all subscriptions were removed
        self.assertEqual(self.mock_config_service.unsubscribe.call_count, 5)
        self.assertEqual(len(adapter._subscriptions), 0)
    
    def test_error_handling_in_configuration_changes(self):
        """Test error handling in configuration change handlers"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Mock the apply method to raise an exception
        original_apply = adapter._apply_rate_limiting_configuration
        def mock_apply_with_error():
            raise Exception("Apply error")
        
        adapter._apply_rate_limiting_configuration = mock_apply_with_error
        
        # Configuration change should not raise exception even if apply fails
        try:
            adapter._handle_rate_limit_per_user_change('rate_limit_per_user_per_hour', 1000, 2000)
            # Should not raise exception
        except Exception as e:
            self.fail(f"Configuration change handler raised exception: {e}")
        
        # Configuration should still be updated even if apply fails
        self.assertEqual(adapter._current_config['rate_limit_per_user_per_hour'], 2000)
        
        # Restore original method
        adapter._apply_rate_limiting_configuration = original_apply
    
    def test_minimal_initialization(self):
        """Test adapter initialization with minimal parameters"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service
        )
        
        # Should work with just configuration service
        self.assertEqual(adapter.get_current_rate_limit_per_user_per_hour(), 1000)
        self.assertTrue(adapter.is_rate_limiting_enabled())
        
        # Updates should not fail even without security middleware
        adapter._apply_rate_limiting_configuration()
    
    def test_factory_function(self):
        """Test factory function for creating adapter"""
        adapter = create_rate_limiting_configuration_adapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        self.assertIsInstance(adapter, RateLimitingConfigurationAdapter)
        self.assertEqual(adapter.config_service, self.mock_config_service)
        self.assertEqual(adapter.security_middleware, self.mock_security_middleware)
    
    def test_subscription_error_handling(self):
        """Test error handling during subscription setup"""
        # Mock subscription to raise exception
        self.mock_config_service.subscribe_to_changes.side_effect = Exception("Subscription failed")
        
        # Should not raise exception during initialization
        try:
            adapter = RateLimitingConfigurationAdapter(
                config_service=self.mock_config_service,
                security_middleware=self.mock_security_middleware
            )
            # Should still work despite subscription failure
            self.assertEqual(adapter.get_current_rate_limit_per_user_per_hour(), 1000)
        except Exception as e:
            self.fail(f"Adapter initialization raised exception: {e}")
    
    def test_security_middleware_without_rate_limit_config(self):
        """Test handling of security middleware without _rate_limit_config attribute"""
        # Create mock without _rate_limit_config attribute
        mock_middleware = Mock()
        del mock_middleware._rate_limit_config
        
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=mock_middleware
        )
        
        # Should create the attribute and not raise exception
        self.assertTrue(hasattr(mock_middleware, '_rate_limit_config'))
        self.assertIsInstance(mock_middleware._rate_limit_config, dict)
    
    def test_rate_limit_boundary_conditions(self):
        """Test rate limit checking at boundary conditions"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Test exactly at limit
        self.assertFalse(adapter.check_rate_limit_for_user(1, 1000))  # At limit
        self.assertTrue(adapter.check_rate_limit_for_user(1, 999))    # Just under limit
        
        self.assertFalse(adapter.check_rate_limit_for_ip('192.168.1.1', 120))  # At limit
        self.assertTrue(adapter.check_rate_limit_for_ip('192.168.1.1', 119))   # Just under limit
        
        # Test with zero requests
        self.assertTrue(adapter.check_rate_limit_for_user(1, 0))
        self.assertTrue(adapter.check_rate_limit_for_ip('192.168.1.1', 0))
    
    def test_rate_limit_info_with_over_limit_requests(self):
        """Test rate limit info when requests exceed limit"""
        adapter = RateLimitingConfigurationAdapter(
            config_service=self.mock_config_service,
            security_middleware=self.mock_security_middleware
        )
        
        # Test user over limit
        user_info = adapter.get_rate_limit_info_for_user(1, 1500)
        self.assertEqual(user_info['remaining_requests'], 0)  # Should be 0, not negative
        
        # Test IP over limit
        ip_info = adapter.get_rate_limit_info_for_ip('192.168.1.1', 200)
        self.assertEqual(ip_info['remaining_requests'], 0)  # Should be 0, not negative


if __name__ == '__main__':
    unittest.main()