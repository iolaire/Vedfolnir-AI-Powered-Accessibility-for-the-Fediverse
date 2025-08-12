# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Session Configuration System

Tests the session management configuration system including timeout settings,
cleanup intervals, feature flags, and environment-specific configurations.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from session_config import (
    SessionConfig, SessionTimeoutConfig, SessionCleanupConfig, 
    SessionSyncConfig, SessionSecurityConfig, SessionMonitoringConfig,
    SessionFeatureFlags, SessionEnvironment, get_session_config, reload_session_config
)

class TestSessionTimeoutConfig(unittest.TestCase):
    """Test session timeout configuration"""
    
    def test_default_timeout_config(self):
        """Test default timeout configuration values"""
        config = SessionTimeoutConfig()
        
        self.assertEqual(config.session_lifetime, timedelta(hours=48))
        self.assertEqual(config.idle_timeout, timedelta(hours=24))
        self.assertEqual(config.absolute_timeout, timedelta(days=7))
        self.assertEqual(config.expiration_grace_period, timedelta(minutes=5))
        self.assertEqual(config.cleanup_grace_period, timedelta(minutes=10))
        self.assertEqual(config.expiration_warning_threshold, timedelta(minutes=15))
    
    @patch.dict(os.environ, {
        'SESSION_LIFETIME_SECONDS': '7200',  # 2 hours
        'SESSION_IDLE_TIMEOUT_SECONDS': '3600',  # 1 hour
        'SESSION_ABSOLUTE_TIMEOUT_SECONDS': '86400',  # 1 day
        'SESSION_EXPIRATION_GRACE_SECONDS': '600',  # 10 minutes
        'SESSION_CLEANUP_GRACE_SECONDS': '1200',  # 20 minutes
        'SESSION_WARNING_THRESHOLD_SECONDS': '1800'  # 30 minutes
    })
    def test_timeout_config_from_env(self):
        """Test timeout configuration from environment variables"""
        config = SessionTimeoutConfig.from_env()
        
        self.assertEqual(config.session_lifetime, timedelta(seconds=7200))
        self.assertEqual(config.idle_timeout, timedelta(seconds=3600))
        self.assertEqual(config.absolute_timeout, timedelta(seconds=86400))
        self.assertEqual(config.expiration_grace_period, timedelta(seconds=600))
        self.assertEqual(config.cleanup_grace_period, timedelta(seconds=1200))
        self.assertEqual(config.expiration_warning_threshold, timedelta(seconds=1800))

class TestSessionCleanupConfig(unittest.TestCase):
    """Test session cleanup configuration"""
    
    def test_default_cleanup_config(self):
        """Test default cleanup configuration values"""
        config = SessionCleanupConfig()
        
        self.assertEqual(config.cleanup_interval, timedelta(minutes=30))
        self.assertEqual(config.batch_cleanup_interval, timedelta(hours=6))
        self.assertEqual(config.deep_cleanup_interval, timedelta(days=1))
        self.assertEqual(config.cleanup_batch_size, 100)
        self.assertEqual(config.max_cleanup_batches_per_run, 10)
        self.assertEqual(config.max_expired_sessions_threshold, 1000)
        self.assertEqual(config.cleanup_trigger_threshold, 500)
        self.assertEqual(config.expired_session_retention_days, 7)
        self.assertEqual(config.audit_log_retention_days, 30)
    
    @patch.dict(os.environ, {
        'SESSION_CLEANUP_INTERVAL_SECONDS': '900',  # 15 minutes
        'SESSION_BATCH_CLEANUP_INTERVAL_SECONDS': '10800',  # 3 hours
        'SESSION_DEEP_CLEANUP_INTERVAL_SECONDS': '43200',  # 12 hours
        'SESSION_CLEANUP_BATCH_SIZE': '50',
        'SESSION_MAX_CLEANUP_BATCHES': '5',
        'SESSION_MAX_EXPIRED_THRESHOLD': '500',
        'SESSION_CLEANUP_TRIGGER_THRESHOLD': '250',
        'SESSION_EXPIRED_RETENTION_DAYS': '3',
        'SESSION_AUDIT_RETENTION_DAYS': '14'
    })
    def test_cleanup_config_from_env(self):
        """Test cleanup configuration from environment variables"""
        config = SessionCleanupConfig.from_env()
        
        self.assertEqual(config.cleanup_interval, timedelta(seconds=900))
        self.assertEqual(config.batch_cleanup_interval, timedelta(seconds=10800))
        self.assertEqual(config.deep_cleanup_interval, timedelta(seconds=43200))
        self.assertEqual(config.cleanup_batch_size, 50)
        self.assertEqual(config.max_cleanup_batches_per_run, 5)
        self.assertEqual(config.max_expired_sessions_threshold, 500)
        self.assertEqual(config.cleanup_trigger_threshold, 250)
        self.assertEqual(config.expired_session_retention_days, 3)
        self.assertEqual(config.audit_log_retention_days, 14)

class TestSessionSyncConfig(unittest.TestCase):
    """Test session synchronization configuration"""
    
    def test_default_sync_config(self):
        """Test default sync configuration values"""
        config = SessionSyncConfig()
        
        self.assertEqual(config.sync_check_interval, timedelta(seconds=2))
        self.assertEqual(config.heartbeat_interval, timedelta(seconds=30))
        self.assertEqual(config.sync_timeout, timedelta(seconds=5))
        self.assertEqual(config.tab_response_timeout, timedelta(seconds=3))
        self.assertEqual(config.localStorage_key_prefix, "vedfolnir_session_")
        self.assertEqual(config.max_sync_data_size, 1024)
    
    @patch.dict(os.environ, {
        'SESSION_SYNC_CHECK_INTERVAL_SECONDS': '1',
        'SESSION_HEARTBEAT_INTERVAL_SECONDS': '15',
        'SESSION_SYNC_TIMEOUT_SECONDS': '3',
        'SESSION_TAB_RESPONSE_TIMEOUT_SECONDS': '2',
        'SESSION_LOCALSTORAGE_PREFIX': 'test_session_',
        'SESSION_MAX_SYNC_DATA_SIZE': '512'
    })
    def test_sync_config_from_env(self):
        """Test sync configuration from environment variables"""
        config = SessionSyncConfig.from_env()
        
        self.assertEqual(config.sync_check_interval, timedelta(seconds=1))
        self.assertEqual(config.heartbeat_interval, timedelta(seconds=15))
        self.assertEqual(config.sync_timeout, timedelta(seconds=3))
        self.assertEqual(config.tab_response_timeout, timedelta(seconds=2))
        self.assertEqual(config.localStorage_key_prefix, "test_session_")
        self.assertEqual(config.max_sync_data_size, 512)

class TestSessionSecurityConfig(unittest.TestCase):
    """Test session security configuration"""
    
    def test_default_security_config(self):
        """Test default security configuration values"""
        config = SessionSecurityConfig()
        
        self.assertTrue(config.enable_fingerprinting)
        self.assertTrue(config.enable_suspicious_activity_detection)
        self.assertTrue(config.enable_audit_logging)
        self.assertEqual(config.max_concurrent_sessions_per_user, 5)
        self.assertEqual(config.suspicious_activity_threshold, 10)
        self.assertEqual(config.max_platform_switches_per_hour, 50)
        self.assertEqual(config.security_check_interval, timedelta(minutes=5))
    
    @patch.dict(os.environ, {
        'SESSION_ENABLE_FINGERPRINTING': 'false',
        'SESSION_ENABLE_SUSPICIOUS_DETECTION': 'false',
        'SESSION_ENABLE_AUDIT_LOGGING': 'false',
        'SESSION_MAX_CONCURRENT_PER_USER': '3',
        'SESSION_SUSPICIOUS_ACTIVITY_THRESHOLD': '5',
        'SESSION_MAX_PLATFORM_SWITCHES_PER_HOUR': '25',
        'SESSION_SECURITY_CHECK_INTERVAL_SECONDS': '600'
    })
    def test_security_config_from_env(self):
        """Test security configuration from environment variables"""
        config = SessionSecurityConfig.from_env()
        
        self.assertFalse(config.enable_fingerprinting)
        self.assertFalse(config.enable_suspicious_activity_detection)
        self.assertFalse(config.enable_audit_logging)
        self.assertEqual(config.max_concurrent_sessions_per_user, 3)
        self.assertEqual(config.suspicious_activity_threshold, 5)
        self.assertEqual(config.max_platform_switches_per_hour, 25)
        self.assertEqual(config.security_check_interval, timedelta(seconds=600))

class TestSessionMonitoringConfig(unittest.TestCase):
    """Test session monitoring configuration"""
    
    def test_default_monitoring_config(self):
        """Test default monitoring configuration values"""
        config = SessionMonitoringConfig()
        
        self.assertTrue(config.enable_performance_monitoring)
        self.assertTrue(config.enable_metrics_collection)
        self.assertTrue(config.enable_health_checks)
        self.assertEqual(config.metrics_collection_interval, timedelta(minutes=1))
        self.assertEqual(config.health_check_interval, timedelta(minutes=5))
        self.assertEqual(config.metrics_buffer_size, 1000)
        self.assertEqual(config.events_buffer_size, 500)
        
        # Check default alert thresholds
        expected_thresholds = {
            'session_creation_rate': 100.0,
            'session_failure_rate': 10.0,
            'avg_session_duration': 3600.0,
            'concurrent_sessions': 1000.0,
            'suspicious_activity_rate': 5.0
        }
        self.assertEqual(config.alert_thresholds, expected_thresholds)
    
    @patch.dict(os.environ, {
        'SESSION_ENABLE_PERFORMANCE_MONITORING': 'false',
        'SESSION_ENABLE_METRICS_COLLECTION': 'false',
        'SESSION_ENABLE_HEALTH_CHECKS': 'false',
        'SESSION_METRICS_INTERVAL_SECONDS': '30',
        'SESSION_HEALTH_CHECK_INTERVAL_SECONDS': '120',
        'SESSION_METRICS_BUFFER_SIZE': '500',
        'SESSION_EVENTS_BUFFER_SIZE': '250',
        'SESSION_ALERT_CREATION_RATE': '50.0',
        'SESSION_ALERT_FAILURE_RATE': '5.0'
    })
    def test_monitoring_config_from_env(self):
        """Test monitoring configuration from environment variables"""
        config = SessionMonitoringConfig.from_env()
        
        self.assertFalse(config.enable_performance_monitoring)
        self.assertFalse(config.enable_metrics_collection)
        self.assertFalse(config.enable_health_checks)
        self.assertEqual(config.metrics_collection_interval, timedelta(seconds=30))
        self.assertEqual(config.health_check_interval, timedelta(seconds=120))
        self.assertEqual(config.metrics_buffer_size, 500)
        self.assertEqual(config.events_buffer_size, 250)
        self.assertEqual(config.alert_thresholds['session_creation_rate'], 50.0)
        self.assertEqual(config.alert_thresholds['session_failure_rate'], 5.0)

class TestSessionFeatureFlags(unittest.TestCase):
    """Test session feature flags"""
    
    def test_default_feature_flags(self):
        """Test default feature flag values"""
        flags = SessionFeatureFlags()
        
        # Core features should be enabled by default
        self.assertTrue(flags.enable_cross_tab_sync)
        self.assertTrue(flags.enable_platform_switching)
        self.assertTrue(flags.enable_session_persistence)
        
        # Advanced features should be enabled by default
        self.assertTrue(flags.enable_optimistic_ui_updates)
        self.assertTrue(flags.enable_background_cleanup)
        self.assertTrue(flags.enable_session_analytics)
        
        # Experimental features should be disabled by default
        self.assertFalse(flags.enable_session_clustering)
        self.assertFalse(flags.enable_distributed_sessions)
        self.assertFalse(flags.enable_session_caching)
    
    @patch.dict(os.environ, {
        'SESSION_FEATURE_CROSS_TAB_SYNC': 'false',
        'SESSION_FEATURE_PLATFORM_SWITCHING': 'false',
        'SESSION_FEATURE_PERSISTENCE': 'false',
        'SESSION_FEATURE_OPTIMISTIC_UI': 'false',
        'SESSION_FEATURE_BACKGROUND_CLEANUP': 'false',
        'SESSION_FEATURE_ANALYTICS': 'false',
        'SESSION_FEATURE_CLUSTERING': 'true',
        'SESSION_FEATURE_DISTRIBUTED': 'true',
        'SESSION_FEATURE_CACHING': 'true'
    })
    def test_feature_flags_from_env(self):
        """Test feature flags from environment variables"""
        flags = SessionFeatureFlags.from_env()
        
        # Core features disabled
        self.assertFalse(flags.enable_cross_tab_sync)
        self.assertFalse(flags.enable_platform_switching)
        self.assertFalse(flags.enable_session_persistence)
        
        # Advanced features disabled
        self.assertFalse(flags.enable_optimistic_ui_updates)
        self.assertFalse(flags.enable_background_cleanup)
        self.assertFalse(flags.enable_session_analytics)
        
        # Experimental features enabled
        self.assertTrue(flags.enable_session_clustering)
        self.assertTrue(flags.enable_distributed_sessions)
        self.assertTrue(flags.enable_session_caching)

class TestSessionConfig(unittest.TestCase):
    """Test main session configuration"""
    
    def test_default_session_config(self):
        """Test default session configuration"""
        config = SessionConfig()
        
        self.assertEqual(config.environment, SessionEnvironment.DEVELOPMENT)
        self.assertFalse(config.debug_mode)
        self.assertIsInstance(config.timeout, SessionTimeoutConfig)
        self.assertIsInstance(config.cleanup, SessionCleanupConfig)
        self.assertIsInstance(config.sync, SessionSyncConfig)
        self.assertIsInstance(config.security, SessionSecurityConfig)
        self.assertIsInstance(config.monitoring, SessionMonitoringConfig)
        self.assertIsInstance(config.features, SessionFeatureFlags)
        self.assertEqual(config.custom_settings, {})
    
    @patch.dict(os.environ, {
        'SESSION_ENVIRONMENT': 'production',
        'SESSION_DEBUG_MODE': 'true',
        'SESSION_CUSTOM_TEST_SETTING': 'test_value',
        'SESSION_CUSTOM_ANOTHER_SETTING': 'another_value'
    })
    def test_session_config_from_env(self):
        """Test session configuration from environment variables"""
        config = SessionConfig.from_env()
        
        self.assertEqual(config.environment, SessionEnvironment.PRODUCTION)
        self.assertTrue(config.debug_mode)
        self.assertEqual(config.custom_settings['test_setting'], 'test_value')
        self.assertEqual(config.custom_settings['another_setting'], 'another_value')
    
    def test_environment_specific_config(self):
        """Test environment-specific configuration overrides"""
        config = SessionConfig()
        
        # Test development environment
        config.environment = SessionEnvironment.DEVELOPMENT
        dev_config = config.get_environment_specific_config()
        self.assertIn('timeout.session_lifetime', dev_config)
        self.assertTrue(dev_config['debug_mode'])
        
        # Test production environment
        config.environment = SessionEnvironment.PRODUCTION
        prod_config = config.get_environment_specific_config()
        self.assertIn('timeout.session_lifetime', prod_config)
        self.assertFalse(prod_config['debug_mode'])
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        config = SessionConfig()
        
        # Valid configuration should have no issues
        issues = config.validate_configuration()
        self.assertEqual(len(issues), 0)
        
        # Create invalid configuration
        config.timeout.idle_timeout = timedelta(hours=50)  # Greater than session lifetime
        config.timeout.session_lifetime = timedelta(hours=48)
        
        issues = config.validate_configuration()
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("Idle timeout should be less than session lifetime" in issue for issue in issues))
    
    def test_config_summary(self):
        """Test configuration summary generation"""
        config = SessionConfig()
        summary = config.get_config_summary()
        
        self.assertIn('environment', summary)
        self.assertIn('debug_mode', summary)
        self.assertIn('session_lifetime_hours', summary)
        self.assertIn('cleanup_interval_minutes', summary)
        self.assertIn('features_enabled', summary)
        self.assertIn('custom_settings_count', summary)
        
        # Check that features_enabled contains expected keys
        features = summary['features_enabled']
        self.assertIn('cross_tab_sync', features)
        self.assertIn('platform_switching', features)
        self.assertIn('monitoring', features)
        self.assertIn('security', features)

class TestSessionConfigGlobal(unittest.TestCase):
    """Test global session configuration functions"""
    
    def test_get_session_config(self):
        """Test getting global session configuration"""
        config = get_session_config()
        self.assertIsInstance(config, SessionConfig)
    
    def test_reload_session_config(self):
        """Test reloading session configuration"""
        # Get initial config
        config1 = get_session_config()
        
        # Reload config
        config2 = reload_session_config()
        
        # Should get a new instance
        self.assertIsInstance(config2, SessionConfig)
        # But with same values (since environment hasn't changed)
        self.assertEqual(config1.environment, config2.environment)

class TestSessionConfigIntegration(unittest.TestCase):
    """Test session configuration integration"""
    
    @patch.dict(os.environ, {
        'SESSION_ENVIRONMENT': 'testing',
        'SESSION_LIFETIME_SECONDS': '1800',  # 30 minutes
        'SESSION_CLEANUP_INTERVAL_SECONDS': '300',  # 5 minutes
        'SESSION_FEATURE_BACKGROUND_CLEANUP': 'false',
        'SESSION_ENABLE_PERFORMANCE_MONITORING': 'false'
    })
    def test_testing_environment_config(self):
        """Test configuration optimized for testing environment"""
        config = SessionConfig.from_env()
        config.apply_environment_overrides()
        
        self.assertEqual(config.environment, SessionEnvironment.TESTING)
        self.assertEqual(config.timeout.session_lifetime, timedelta(seconds=1800))
        self.assertEqual(config.cleanup.cleanup_interval, timedelta(seconds=300))
        self.assertFalse(config.features.enable_background_cleanup)
        self.assertFalse(config.monitoring.enable_performance_monitoring)
    
    def test_config_validation_comprehensive(self):
        """Test comprehensive configuration validation"""
        config = SessionConfig()
        
        # Test multiple validation issues
        config.timeout.idle_timeout = timedelta(hours=50)  # Invalid
        config.timeout.expiration_grace_period = timedelta(hours=25)  # Invalid
        config.cleanup.cleanup_batch_size = -1  # Invalid
        config.security.max_concurrent_sessions_per_user = 0  # Invalid
        config.monitoring.metrics_buffer_size = -1  # Invalid
        
        issues = config.validate_configuration()
        # Should have at least 4 issues (the ones we can detect)
        self.assertGreaterEqual(len(issues), 4)
        
        # Check specific issues are detected
        issue_text = ' '.join(issues)
        self.assertIn('Idle timeout should be less than session lifetime', issue_text)
        self.assertIn('Cleanup batch size must be positive', issue_text)
        self.assertIn('Max concurrent sessions per user must be positive', issue_text)
        self.assertIn('Metrics buffer size must be positive', issue_text)

if __name__ == '__main__':
    unittest.main()