# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for SessionConfigurationAdapter

Tests the integration between session management and configuration service.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import timedelta
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from session_configuration_adapter import SessionConfigurationAdapter, create_session_configuration_adapter


class TestSessionConfigurationAdapter(unittest.TestCase):
    """Test cases for SessionConfigurationAdapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.side_effect = self._mock_get_config
        self.mock_config_service.subscribe_to_changes.return_value = "subscription_id"
        self.mock_config_service.unsubscribe.return_value = True
        
        # Mock session managers
        self.mock_redis_session_manager = Mock()
        self.mock_redis_session_manager.session_timeout = timedelta(seconds=7200)
        
        self.mock_unified_session_manager = Mock()
        self.mock_unified_session_manager.config = Mock()
        self.mock_unified_session_manager.config.timeout = Mock()
        self.mock_unified_session_manager.config.timeout.session_lifetime = timedelta(seconds=7200)
        self.mock_unified_session_manager.config.security = Mock()
        self.mock_unified_session_manager.config.security.enabled = True
        self.mock_unified_session_manager.config.security.fingerprinting_enabled = True
        
        self.mock_flask_session_interface = Mock()
        self.mock_flask_session_interface.session_timeout = 7200
        
        # Default configuration values
        self.default_config = {
            'session_timeout_minutes': 120,
            'session_security_enabled': True,
            'rate_limit_per_user_per_hour': 1000,
            'max_concurrent_sessions_per_user': 5,
            'session_fingerprinting_enabled': True,
            'audit_log_retention_days': 90
        }
    
    def _mock_get_config(self, key, default=None):
        """Mock configuration service get_config method"""
        config_map = {
            'session_timeout_minutes': 120,
            'session_security_enabled': True,
            'rate_limit_per_user_per_hour': 1000,
            'max_concurrent_sessions_per_user': 5,
            'session_fingerprinting_enabled': True,
            'audit_log_retention_days': 90
        }
        return config_map.get(key, default)
    
    def test_initialization(self):
        """Test adapter initialization"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager,
            unified_session_manager=self.mock_unified_session_manager,
            flask_session_interface=self.mock_flask_session_interface
        )
        
        # Verify configuration service calls
        expected_calls = [
            call('session_timeout_minutes', 120),
            call('session_security_enabled', True),
            call('rate_limit_per_user_per_hour', 1000),
            call('max_concurrent_sessions_per_user', 5),
            call('session_fingerprinting_enabled', True),
            call('audit_log_retention_days', 90)
        ]
        self.mock_config_service.get_config.assert_has_calls(expected_calls, any_order=True)
        
        # Verify subscriptions were created
        self.assertEqual(self.mock_config_service.subscribe_to_changes.call_count, 6)
        
        # Verify configuration was applied
        self.assertEqual(adapter.get_current_session_timeout(), 120)
        self.assertTrue(adapter.is_session_security_enabled())
        self.assertEqual(adapter.get_current_rate_limit(), 1000)
    
    def test_initialization_with_config_service_failure(self):
        """Test adapter initialization when configuration service fails"""
        # Mock configuration service to raise exception
        self.mock_config_service.get_config.side_effect = Exception("Config service unavailable")
        
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager
        )
        
        # Should use default values when config service fails
        self.assertEqual(adapter.get_current_session_timeout(), 120)
        self.assertTrue(adapter.is_session_security_enabled())
        self.assertEqual(adapter.get_current_rate_limit(), 1000)
    
    def test_update_session_timeout(self):
        """Test updating session timeout"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager,
            unified_session_manager=self.mock_unified_session_manager,
            flask_session_interface=self.mock_flask_session_interface
        )
        
        # Update timeout configuration
        adapter._current_config['session_timeout_minutes'] = 180
        adapter.update_session_timeout()
        
        # Verify Redis session manager was updated
        self.assertEqual(self.mock_redis_session_manager.session_timeout, timedelta(seconds=10800))
        
        # Verify unified session manager was updated
        self.assertEqual(
            self.mock_unified_session_manager.config.timeout.session_lifetime,
            timedelta(seconds=10800)
        )
        
        # Verify Flask session interface was updated
        self.assertEqual(self.mock_flask_session_interface.session_timeout, 10800)
    
    def test_update_session_security_settings(self):
        """Test updating session security settings"""
        # Mock security manager
        mock_security_manager = Mock()
        mock_security_manager.set_security_enabled = Mock()
        mock_security_manager.set_fingerprinting_enabled = Mock()
        self.mock_redis_session_manager.security_manager = mock_security_manager
        
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager,
            unified_session_manager=self.mock_unified_session_manager
        )
        
        # Update security configuration
        adapter._current_config['session_security_enabled'] = False
        adapter._current_config['session_fingerprinting_enabled'] = False
        adapter.update_session_security_settings()
        
        # Verify Redis session manager security was updated
        mock_security_manager.set_security_enabled.assert_called_with(False)
        mock_security_manager.set_fingerprinting_enabled.assert_called_with(False)
        
        # Verify unified session manager security was updated
        self.assertFalse(self.mock_unified_session_manager.config.security.enabled)
        self.assertFalse(self.mock_unified_session_manager.config.security.fingerprinting_enabled)
    
    def test_configuration_change_handlers(self):
        """Test configuration change event handlers"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager,
            flask_session_interface=self.mock_flask_session_interface
        )
        
        # Test session timeout change
        adapter._handle_session_timeout_change('session_timeout_minutes', 120, 180)
        self.assertEqual(adapter._current_config['session_timeout_minutes'], 180)
        self.assertEqual(self.mock_redis_session_manager.session_timeout, timedelta(seconds=10800))
        
        # Test security change
        adapter._handle_session_security_change('session_security_enabled', True, False)
        self.assertEqual(adapter._current_config['session_security_enabled'], False)
        
        # Test rate limit change
        adapter._handle_rate_limit_change('rate_limit_per_user_per_hour', 1000, 2000)
        self.assertEqual(adapter._current_config['rate_limit_per_user_per_hour'], 2000)
        
        # Test max concurrent sessions change
        adapter._handle_max_concurrent_sessions_change('max_concurrent_sessions_per_user', 5, 10)
        self.assertEqual(adapter._current_config['max_concurrent_sessions_per_user'], 10)
        
        # Test fingerprinting change
        adapter._handle_session_fingerprinting_change('session_fingerprinting_enabled', True, False)
        self.assertEqual(adapter._current_config['session_fingerprinting_enabled'], False)
        
        # Test audit log retention change
        adapter._handle_audit_log_retention_change('audit_log_retention_days', 90, 180)
        self.assertEqual(adapter._current_config['audit_log_retention_days'], 180)
    
    def test_configuration_getters(self):
        """Test configuration getter methods"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager
        )
        
        # Test all getter methods
        self.assertEqual(adapter.get_current_session_timeout(), 120)
        self.assertEqual(adapter.get_current_rate_limit(), 1000)
        self.assertEqual(adapter.get_current_max_concurrent_sessions(), 5)
        self.assertTrue(adapter.is_session_security_enabled())
        self.assertTrue(adapter.is_session_fingerprinting_enabled())
        self.assertEqual(adapter.get_audit_log_retention_days(), 90)
        
        # Test configuration summary
        summary = adapter.get_configuration_summary()
        self.assertEqual(summary['session_timeout_minutes'], 120)
        self.assertEqual(summary['rate_limit_per_user_per_hour'], 1000)
        self.assertTrue(summary['session_security_enabled'])
    
    def test_refresh_configuration(self):
        """Test configuration refresh"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager
        )
        
        # Mock new configuration values
        def mock_get_config_refreshed(key, default=None):
            config_map = {
                'session_timeout_minutes': 240,  # Changed from 120
                'session_security_enabled': False,  # Changed from True
                'rate_limit_per_user_per_hour': 2000,  # Changed from 1000
                'max_concurrent_sessions_per_user': 10,  # Changed from 5
                'session_fingerprinting_enabled': False,  # Changed from True
                'audit_log_retention_days': 180  # Changed from 90
            }
            return config_map.get(key, default)
        
        # Update mock to return new values
        self.mock_config_service.get_config.side_effect = mock_get_config_refreshed
        
        # Refresh configuration
        adapter.refresh_configuration()
        
        # Verify configuration service was called
        self.mock_config_service.refresh_config.assert_called_once()
        
        # Verify new values were loaded
        self.assertEqual(adapter.get_current_session_timeout(), 240)
        self.assertFalse(adapter.is_session_security_enabled())
        self.assertEqual(adapter.get_current_rate_limit(), 2000)
    
    def test_cleanup(self):
        """Test adapter cleanup"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager
        )
        
        # Cleanup should unsubscribe from all configuration changes
        adapter.cleanup()
        
        # Verify all subscriptions were removed
        self.assertEqual(self.mock_config_service.unsubscribe.call_count, 6)
        self.assertEqual(len(adapter._subscriptions), 0)
    
    def test_error_handling_in_configuration_changes(self):
        """Test error handling in configuration change handlers"""
        # Create a mock that raises an exception during update_session_timeout
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager
        )
        
        # Mock the update_session_timeout method to raise an exception
        original_update = adapter.update_session_timeout
        def mock_update_with_error():
            raise Exception("Redis error")
        
        adapter.update_session_timeout = mock_update_with_error
        
        # Configuration change should not raise exception even if update fails
        try:
            adapter._handle_session_timeout_change('session_timeout_minutes', 120, 180)
            # Should not raise exception
        except Exception as e:
            self.fail(f"Configuration change handler raised exception: {e}")
        
        # Configuration should still be updated even if manager update fails
        self.assertEqual(adapter._current_config['session_timeout_minutes'], 180)
        
        # Restore original method
        adapter.update_session_timeout = original_update
    
    def test_minimal_initialization(self):
        """Test adapter initialization with minimal parameters"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service
        )
        
        # Should work with just configuration service
        self.assertEqual(adapter.get_current_session_timeout(), 120)
        self.assertTrue(adapter.is_session_security_enabled())
        
        # Updates should not fail even without session managers
        adapter.update_session_timeout()
        adapter.update_session_security_settings()
        adapter.update_rate_limiting()
    
    def test_factory_function(self):
        """Test factory function for creating adapter"""
        adapter = create_session_configuration_adapter(
            config_service=self.mock_config_service,
            redis_session_manager=self.mock_redis_session_manager,
            unified_session_manager=self.mock_unified_session_manager,
            flask_session_interface=self.mock_flask_session_interface
        )
        
        self.assertIsInstance(adapter, SessionConfigurationAdapter)
        self.assertEqual(adapter.config_service, self.mock_config_service)
        self.assertEqual(adapter.redis_session_manager, self.mock_redis_session_manager)
        self.assertEqual(adapter.unified_session_manager, self.mock_unified_session_manager)
        self.assertEqual(adapter.flask_session_interface, self.mock_flask_session_interface)
    
    def test_subscription_error_handling(self):
        """Test error handling during subscription setup"""
        # Mock subscription to raise exception
        self.mock_config_service.subscribe_to_changes.side_effect = Exception("Subscription failed")
        
        # Should not raise exception during initialization
        try:
            adapter = SessionConfigurationAdapter(
                config_service=self.mock_config_service,
                redis_session_manager=self.mock_redis_session_manager
            )
            # Should still work despite subscription failure
            self.assertEqual(adapter.get_current_session_timeout(), 120)
        except Exception as e:
            self.fail(f"Adapter initialization raised exception: {e}")
    
    def test_update_methods_with_missing_managers(self):
        """Test update methods when session managers are None"""
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=None,
            unified_session_manager=None,
            flask_session_interface=None
        )
        
        # Should not raise exceptions when managers are None
        try:
            adapter.update_session_timeout()
            adapter.update_session_security_settings()
            adapter.update_rate_limiting()
            adapter.update_max_concurrent_sessions()
        except Exception as e:
            self.fail(f"Update method raised exception with None managers: {e}")
    
    def test_security_manager_attribute_handling(self):
        """Test handling of security manager attributes that may not exist"""
        # Mock Redis session manager without security manager
        mock_redis_manager = Mock()
        mock_redis_manager.security_manager = None
        
        adapter = SessionConfigurationAdapter(
            config_service=self.mock_config_service,
            redis_session_manager=mock_redis_manager
        )
        
        # Should not raise exception when security manager is None
        try:
            adapter.update_session_security_settings()
        except Exception as e:
            self.fail(f"Security settings update raised exception: {e}")
        
        # Test with security manager that doesn't have expected methods
        mock_security_manager = Mock()
        del mock_security_manager.set_security_enabled
        del mock_security_manager.set_fingerprinting_enabled
        mock_redis_manager.security_manager = mock_security_manager
        
        try:
            adapter.update_session_security_settings()
        except Exception as e:
            self.fail(f"Security settings update raised exception with incomplete security manager: {e}")


if __name__ == '__main__':
    unittest.main()