# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH the SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Retention Configuration

Tests the configuration management system for RQ data retention policies,
including environment variable loading, custom policies, and policy overrides.
"""

import unittest
from unittest.mock import patch, Mock
import os
import json

from app.services.task.rq.rq_retention_config import (
    RQRetentionConfig, 
    RQRetentionConfigManager,
    get_retention_config_manager,
    create_retention_policy
)
from app.services.task.rq.retention_policy import RetentionPolicy


class TestRQRetentionConfig(unittest.TestCase):
    """Test RQ retention configuration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Clear any existing environment variables
        self.env_vars_to_clear = [
            'RQ_RETENTION_POLICY',
            'RQ_RETENTION_MONITORING_ENABLED',
            'RQ_RETENTION_MONITORING_INTERVAL',
            'RQ_MEMORY_WARNING_THRESHOLD_MB',
            'RQ_MEMORY_CRITICAL_THRESHOLD_MB',
            'RQ_AUTO_CLEANUP_ENABLED',
            'RQ_EMERGENCY_CLEANUP_ENABLED',
            'RQ_CLEANUP_BATCH_SIZE',
            'RQ_COMPLETED_TASKS_TTL',
            'RQ_FAILED_TASKS_TTL',
            'RQ_CANCELLED_TASKS_TTL',
            'RQ_PROGRESS_DATA_TTL',
            'RQ_SECURITY_LOGS_TTL',
            'RQ_CUSTOM_POLICIES'
        ]
        
        for var in self.env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clear environment variables
        for var in self.env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def test_default_configuration(self):
        """Test default configuration loading"""
        config = RQRetentionConfig()
        
        # Verify defaults
        self.assertEqual(config.active_policy_name, "default")
        self.assertTrue(config.monitoring_enabled)
        self.assertEqual(config.monitoring_interval, 300)
        self.assertTrue(config.auto_cleanup_enabled)
        self.assertTrue(config.emergency_cleanup_enabled)
        self.assertIsNone(config.memory_warning_threshold_mb)
        self.assertIsNone(config.memory_critical_threshold_mb)
        self.assertEqual(config.custom_policies, {})
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables"""
        # Set environment variables
        os.environ['RQ_RETENTION_POLICY'] = 'high_volume'
        os.environ['RQ_RETENTION_MONITORING_ENABLED'] = 'false'
        os.environ['RQ_RETENTION_MONITORING_INTERVAL'] = '600'
        os.environ['RQ_MEMORY_WARNING_THRESHOLD_MB'] = '800'
        os.environ['RQ_MEMORY_CRITICAL_THRESHOLD_MB'] = '1000'
        os.environ['RQ_AUTO_CLEANUP_ENABLED'] = 'false'
        os.environ['RQ_EMERGENCY_CLEANUP_ENABLED'] = 'false'
        os.environ['RQ_CLEANUP_BATCH_SIZE'] = '200'
        os.environ['RQ_COMPLETED_TASKS_TTL'] = '7200'
        os.environ['RQ_FAILED_TASKS_TTL'] = '14400'
        
        # Create configuration manager
        config_manager = RQRetentionConfigManager()
        config = config_manager.get_config()
        
        # Verify environment variables were loaded
        self.assertEqual(config.active_policy_name, 'high_volume')
        self.assertFalse(config.monitoring_enabled)
        self.assertEqual(config.monitoring_interval, 600)
        self.assertEqual(config.memory_warning_threshold_mb, 800)
        self.assertEqual(config.memory_critical_threshold_mb, 1000)
        self.assertFalse(config.auto_cleanup_enabled)
        self.assertFalse(config.emergency_cleanup_enabled)
        self.assertEqual(config.cleanup_batch_size, 200)
        self.assertEqual(config.completed_tasks_ttl_override, 7200)
        self.assertEqual(config.failed_tasks_ttl_override, 14400)
    
    def test_custom_policies_loading(self):
        """Test loading custom policies from environment"""
        custom_policies = {
            'test_policy': {
                'description': 'Test policy for unit tests',
                'completed_tasks_ttl': 1800,
                'failed_tasks_ttl': 3600,
                'max_memory_usage_mb': 256,
                'cleanup_threshold_mb': 200
            }
        }
        
        os.environ['RQ_CUSTOM_POLICIES'] = json.dumps(custom_policies)
        
        config_manager = RQRetentionConfigManager()
        config = config_manager.get_config()
        
        # Verify custom policy was loaded
        self.assertIn('test_policy', config.custom_policies)
        self.assertEqual(config.custom_policies['test_policy']['description'], 'Test policy for unit tests')
        self.assertEqual(config.custom_policies['test_policy']['completed_tasks_ttl'], 1800)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Set invalid values
        os.environ['RQ_RETENTION_MONITORING_INTERVAL'] = '30'  # Too low
        os.environ['RQ_MEMORY_WARNING_THRESHOLD_MB'] = '1000'
        os.environ['RQ_MEMORY_CRITICAL_THRESHOLD_MB'] = '800'  # Lower than warning
        os.environ['RQ_CLEANUP_BATCH_SIZE'] = '5'  # Too low
        os.environ['RQ_COMPLETED_TASKS_TTL'] = '30'  # Too low
        
        config_manager = RQRetentionConfigManager()
        config = config_manager.get_config()
        
        # Verify validation corrections
        self.assertEqual(config.monitoring_interval, 60)  # Corrected to minimum
        self.assertEqual(config.memory_warning_threshold_mb, 640)  # Adjusted to 80% of critical
        self.assertEqual(config.cleanup_batch_size, 10)  # Corrected to minimum
        self.assertEqual(config.completed_tasks_ttl_override, 60)  # Corrected to minimum
    
    def test_predefined_policy_creation(self):
        """Test creating predefined retention policies"""
        config_manager = RQRetentionConfigManager()
        
        # Test default policy
        default_policy = config_manager.create_retention_policy('default')
        self.assertEqual(default_policy.name, 'default')
        self.assertEqual(default_policy.completed_tasks_ttl, 86400)
        self.assertEqual(default_policy.max_memory_usage_mb, 512)
        
        # Test development policy
        dev_policy = config_manager.create_retention_policy('development')
        self.assertEqual(dev_policy.name, 'development')
        self.assertEqual(dev_policy.completed_tasks_ttl, 3600)
        self.assertEqual(dev_policy.max_memory_usage_mb, 128)
        
        # Test high volume policy
        hv_policy = config_manager.create_retention_policy('high_volume')
        self.assertEqual(hv_policy.name, 'high_volume')
        self.assertEqual(hv_policy.completed_tasks_ttl, 43200)
        self.assertEqual(hv_policy.max_memory_usage_mb, 1024)
    
    def test_custom_policy_creation(self):
        """Test creating custom retention policies"""
        custom_policies = {
            'custom_test': {
                'description': 'Custom test policy',
                'completed_tasks_ttl': 1800,
                'failed_tasks_ttl': 3600,
                'cancelled_tasks_ttl': 900,
                'progress_data_ttl': 300,
                'security_logs_ttl': 86400,
                'max_memory_usage_mb': 256,
                'cleanup_threshold_mb': 200,
                'cleanup_batch_size': 75,
                'enabled': True
            }
        }
        
        os.environ['RQ_CUSTOM_POLICIES'] = json.dumps(custom_policies)
        
        config_manager = RQRetentionConfigManager()
        custom_policy = config_manager.create_retention_policy('custom_test')
        
        # Verify custom policy properties
        self.assertEqual(custom_policy.name, 'custom_test')
        self.assertEqual(custom_policy.description, 'Custom test policy')
        self.assertEqual(custom_policy.completed_tasks_ttl, 1800)
        self.assertEqual(custom_policy.failed_tasks_ttl, 3600)
        self.assertEqual(custom_policy.cancelled_tasks_ttl, 900)
        self.assertEqual(custom_policy.progress_data_ttl, 300)
        self.assertEqual(custom_policy.security_logs_ttl, 86400)
        self.assertEqual(custom_policy.max_memory_usage_mb, 256)
        self.assertEqual(custom_policy.cleanup_threshold_mb, 200)
        self.assertEqual(custom_policy.cleanup_batch_size, 75)
        self.assertTrue(custom_policy.enabled)
    
    def test_configuration_overrides(self):
        """Test configuration overrides on policies"""
        # Set override values
        os.environ['RQ_COMPLETED_TASKS_TTL'] = '1800'
        os.environ['RQ_FAILED_TASKS_TTL'] = '3600'
        os.environ['RQ_MEMORY_CRITICAL_THRESHOLD_MB'] = '1024'
        os.environ['RQ_MEMORY_WARNING_THRESHOLD_MB'] = '800'
        os.environ['RQ_CLEANUP_BATCH_SIZE'] = '150'
        
        config_manager = RQRetentionConfigManager()
        
        # Create default policy with overrides
        policy = config_manager.create_retention_policy('default')
        
        # Verify overrides were applied
        self.assertEqual(policy.completed_tasks_ttl, 1800)  # Override applied
        self.assertEqual(policy.failed_tasks_ttl, 3600)     # Override applied
        self.assertEqual(policy.max_memory_usage_mb, 1024)  # Override applied
        self.assertEqual(policy.cleanup_threshold_mb, 800)  # Override applied
        self.assertEqual(policy.cleanup_batch_size, 150)    # Override applied
    
    def test_policy_management(self):
        """Test policy management operations"""
        config_manager = RQRetentionConfigManager()
        
        # Test updating custom policy
        result = config_manager.update_policy('test_policy', 
                                            description='Updated test policy',
                                            completed_tasks_ttl=2400,
                                            max_memory_usage_mb=512)
        self.assertTrue(result)
        
        # Verify policy was updated
        config = config_manager.get_config()
        self.assertIn('test_policy', config.custom_policies)
        self.assertEqual(config.custom_policies['test_policy']['description'], 'Updated test policy')
        self.assertEqual(config.custom_policies['test_policy']['completed_tasks_ttl'], 2400)
        
        # Test deleting custom policy
        result = config_manager.delete_custom_policy('test_policy')
        self.assertTrue(result)
        
        # Verify policy was deleted
        config = config_manager.get_config()
        self.assertNotIn('test_policy', config.custom_policies)
        
        # Test deleting non-existent policy
        result = config_manager.delete_custom_policy('non_existent')
        self.assertFalse(result)
    
    def test_available_policies(self):
        """Test getting available policies"""
        custom_policies = {
            'custom1': {'description': 'Custom policy 1'},
            'custom2': {'description': 'Custom policy 2'}
        }
        
        os.environ['RQ_CUSTOM_POLICIES'] = json.dumps(custom_policies)
        
        config_manager = RQRetentionConfigManager()
        available = config_manager.get_available_policies()
        
        # Verify predefined policies are included
        self.assertIn('default', available)
        self.assertIn('development', available)
        self.assertIn('high_volume', available)
        self.assertIn('conservative', available)
        
        # Verify custom policies are included
        self.assertIn('custom1', available)
        self.assertIn('custom2', available)
        
        # Verify descriptions
        self.assertEqual(available['custom1'], 'Custom policy 1')
        self.assertEqual(available['custom2'], 'Custom policy 2')
    
    def test_configuration_export_import(self):
        """Test configuration export and import"""
        # Set up initial configuration
        os.environ['RQ_RETENTION_POLICY'] = 'high_volume'
        os.environ['RQ_COMPLETED_TASKS_TTL'] = '3600'
        
        config_manager = RQRetentionConfigManager()
        
        # Export configuration
        exported = config_manager.export_configuration()
        
        # Verify export structure
        self.assertIn('active_policy_name', exported)
        self.assertIn('monitoring_enabled', exported)
        self.assertIn('completed_tasks_ttl_override', exported)
        self.assertEqual(exported['active_policy_name'], 'high_volume')
        self.assertEqual(exported['completed_tasks_ttl_override'], 3600)
        
        # Test import
        new_config = {
            'active_policy_name': 'development',
            'monitoring_enabled': False,
            'completed_tasks_ttl_override': 7200
        }
        
        result = config_manager.import_configuration(new_config)
        self.assertTrue(result)
        
        # Verify import was successful
        config = config_manager.get_config()
        self.assertEqual(config.active_policy_name, 'development')
        self.assertFalse(config.monitoring_enabled)
        self.assertEqual(config.completed_tasks_ttl_override, 7200)
    
    def test_global_functions(self):
        """Test global configuration functions"""
        # Test get_retention_config_manager
        manager1 = get_retention_config_manager()
        manager2 = get_retention_config_manager()
        
        # Should return same instance (singleton pattern)
        self.assertIs(manager1, manager2)
        
        # Test create_retention_policy with default
        policy = create_retention_policy()
        self.assertEqual(policy.name, 'default')
        
        # Test create_retention_policy with specific policy
        policy = create_retention_policy('development')
        self.assertEqual(policy.name, 'development')
    
    def test_error_handling(self):
        """Test error handling in configuration management"""
        # Test invalid JSON in custom policies
        os.environ['RQ_CUSTOM_POLICIES'] = 'invalid json'
        
        # Should not raise exception, should use default config
        config_manager = RQRetentionConfigManager()
        config = config_manager.get_config()
        self.assertEqual(config.custom_policies, {})
        
        # Test creating unknown policy
        policy = config_manager.create_retention_policy('unknown_policy')
        self.assertEqual(policy.name, 'default')  # Should fallback to default
        
        # Test import with missing required fields
        result = config_manager.import_configuration({'invalid': 'config'})
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()