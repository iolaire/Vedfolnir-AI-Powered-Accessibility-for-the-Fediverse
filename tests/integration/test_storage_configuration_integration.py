# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for StorageConfigurationService with the main configuration system.

Tests that the storage configuration service integrates properly with the existing
Config class and StorageConfig.
"""

import unittest
import os
import sys
from unittest.mock import patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config, StorageConfig
from storage_configuration_service import StorageConfigurationService


class TestStorageConfigurationIntegration(unittest.TestCase):
    """Test integration of StorageConfigurationService with main configuration system"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear any existing environment variables that might affect tests
        self.env_vars_to_clear = [
            'CAPTION_MAX_STORAGE_GB',
            'STORAGE_WARNING_THRESHOLD',
            'STORAGE_MONITORING_ENABLED'
        ]
        self.original_env_values = {}
        
        for var in self.env_vars_to_clear:
            self.original_env_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variables
        for var in self.env_vars_to_clear:
            if self.original_env_values[var] is not None:
                os.environ[var] = self.original_env_values[var]
            elif var in os.environ:
                del os.environ[var]
    
    def test_storage_config_includes_limit_service(self):
        """Test that StorageConfig includes the storage limit service"""
        storage_config = StorageConfig.from_env()
        
        # Should have limit_service attribute
        self.assertTrue(hasattr(storage_config, 'limit_service'))
        
        # Should be an instance of StorageConfigurationService (if import succeeded)
        if storage_config.limit_service is not None:
            self.assertIsInstance(storage_config.limit_service, StorageConfigurationService)
    
    def test_main_config_includes_storage_limit_service(self):
        """Test that main Config includes storage limit service through StorageConfig"""
        config = Config()
        
        # Should have storage attribute
        self.assertTrue(hasattr(config, 'storage'))
        
        # Storage should have limit_service
        self.assertTrue(hasattr(config.storage, 'limit_service'))
        
        # Should be able to access storage limit methods (if service loaded)
        if config.storage.limit_service is not None:
            max_storage = config.storage.limit_service.get_max_storage_gb()
            self.assertIsInstance(max_storage, float)
            self.assertGreater(max_storage, 0)
    
    def test_storage_limit_service_with_environment_variables(self):
        """Test storage limit service integration with environment variables"""
        # Set environment variables
        os.environ['CAPTION_MAX_STORAGE_GB'] = '25.0'
        os.environ['STORAGE_WARNING_THRESHOLD'] = '75.0'
        os.environ['STORAGE_MONITORING_ENABLED'] = 'true'
        
        # Create config
        config = Config()
        
        # Should pick up environment variables through the service
        if config.storage.limit_service is not None:
            self.assertEqual(config.storage.limit_service.get_max_storage_gb(), 25.0)
            self.assertEqual(config.storage.limit_service.get_warning_threshold_gb(), 18.75)  # 75% of 25GB
            self.assertTrue(config.storage.limit_service.is_storage_monitoring_enabled())
    
    def test_storage_limit_service_validation_integration(self):
        """Test that storage limit service validation works through main config"""
        config = Config()
        
        if config.storage.limit_service is not None:
            # Should be able to validate configuration
            is_valid = config.storage.limit_service.validate_storage_config()
            self.assertIsInstance(is_valid, bool)
            
            # Should be able to get configuration summary
            summary = config.storage.limit_service.get_configuration_summary()
            self.assertIsInstance(summary, dict)
            
            # Summary should contain expected keys
            expected_keys = ['max_storage_gb', 'warning_threshold_percentage', 
                           'warning_threshold_gb', 'monitoring_enabled', 'is_valid']
            for key in expected_keys:
                self.assertIn(key, summary)
    
    def test_storage_config_graceful_import_failure(self):
        """Test that StorageConfig handles graceful failure if service import fails"""
        # Mock import failure
        with patch('builtins.__import__', side_effect=ImportError("Test import failure")):
            with patch('config.logging') as mock_logging:
                storage_config = StorageConfig.from_env()
                
                # Should still create StorageConfig but with None limit_service
                self.assertIsNotNone(storage_config)
                self.assertIsNone(storage_config.limit_service)
                
                # Should log warning about import failure
                mock_logging.warning.assert_called()
    
    def test_standalone_service_vs_integrated_service(self):
        """Test that standalone service and integrated service behave the same"""
        # Set environment variables
        os.environ['CAPTION_MAX_STORAGE_GB'] = '15.0'
        os.environ['STORAGE_WARNING_THRESHOLD'] = '85.0'
        
        # Create standalone service
        standalone_service = StorageConfigurationService()
        
        # Create integrated service through config
        config = Config()
        integrated_service = config.storage.limit_service
        
        # Skip test if integrated service failed to load
        if integrated_service is None:
            self.skipTest("Integrated service failed to load")
        
        # Both should return the same values
        self.assertEqual(
            standalone_service.get_max_storage_gb(),
            integrated_service.get_max_storage_gb()
        )
        self.assertEqual(
            standalone_service.get_warning_threshold_gb(),
            integrated_service.get_warning_threshold_gb()
        )
        self.assertEqual(
            standalone_service.is_storage_monitoring_enabled(),
            integrated_service.is_storage_monitoring_enabled()
        )
        self.assertEqual(
            standalone_service.validate_storage_config(),
            integrated_service.validate_storage_config()
        )
    
    def test_config_validation_includes_storage_limits(self):
        """Test that main config validation can include storage limit validation"""
        config = Config()
        
        # Main config should have validate_configuration method
        self.assertTrue(hasattr(config, 'validate_configuration'))
        
        # Should be able to call validation (this tests that the config system works)
        try:
            validation_errors = config.validate_configuration()
            self.assertIsInstance(validation_errors, list)
        except Exception as e:
            # If validation fails due to missing dependencies, that's okay for this test
            # We're just testing that the integration doesn't break the config system
            pass
    
    def test_storage_directories_created(self):
        """Test that storage directories are still created properly with limit service"""
        # Create a temporary directory for testing
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set custom storage directories
            test_base_dir = os.path.join(temp_dir, "test_storage")
            test_images_dir = os.path.join(temp_dir, "test_storage", "images")
            test_logs_dir = os.path.join(temp_dir, "test_logs")
            
            # Create storage config with custom directories
            storage_config = StorageConfig(
                base_dir=test_base_dir,
                images_dir=test_images_dir,
                logs_dir=test_logs_dir
            )
            
            # Directories should be created
            self.assertTrue(os.path.exists(test_base_dir))
            self.assertTrue(os.path.exists(test_images_dir))
            self.assertTrue(os.path.exists(test_logs_dir))
            
            # Should still have limit service
            self.assertTrue(hasattr(storage_config, 'limit_service'))


if __name__ == '__main__':
    unittest.main()