# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for StorageConfigurationService.

Tests configuration validation, default value handling, and environment variable processing
for storage limit management.
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
import logging

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.storage.components.storage_configuration_service import StorageConfigurationService, StorageLimitConfig


class TestStorageLimitConfig(unittest.TestCase):
    """Test cases for StorageLimitConfig dataclass"""
    
    def test_storage_limit_config_creation(self):
        """Test creating StorageLimitConfig with valid values"""
        config = StorageLimitConfig(
            max_storage_gb=15.0,
            warning_threshold_percentage=75.0,
            monitoring_enabled=True
        )
        
        self.assertEqual(config.max_storage_gb, 15.0)
        self.assertEqual(config.warning_threshold_percentage, 75.0)
        self.assertTrue(config.monitoring_enabled)
    
    def test_get_warning_threshold_gb(self):
        """Test calculation of warning threshold in GB"""
        config = StorageLimitConfig(
            max_storage_gb=20.0,
            warning_threshold_percentage=80.0,
            monitoring_enabled=True
        )
        
        # 80% of 20GB = 16GB
        self.assertEqual(config.get_warning_threshold_gb(), 16.0)
    
    def test_get_warning_threshold_gb_different_values(self):
        """Test warning threshold calculation with different values"""
        test_cases = [
            (10.0, 80.0, 8.0),   # 80% of 10GB = 8GB
            (5.0, 90.0, 4.5),    # 90% of 5GB = 4.5GB
            (100.0, 75.0, 75.0), # 75% of 100GB = 75GB
            (1.5, 60.0, 0.9),    # 60% of 1.5GB = 0.9GB
        ]
        
        for max_storage, threshold_pct, expected_gb in test_cases:
            with self.subTest(max_storage=max_storage, threshold_pct=threshold_pct):
                config = StorageLimitConfig(
                    max_storage_gb=max_storage,
                    warning_threshold_percentage=threshold_pct,
                    monitoring_enabled=True
                )
                self.assertAlmostEqual(config.get_warning_threshold_gb(), expected_gb, places=2)


class TestStorageConfigurationService(unittest.TestCase):
    """Test cases for StorageConfigurationService"""
    
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
    
    def test_default_configuration(self):
        """Test service initialization with default values"""
        service = StorageConfigurationService()
        
        # Should use default values when no environment variables are set
        self.assertEqual(service.get_max_storage_gb(), 10.0)
        self.assertEqual(service.get_warning_threshold_gb(), 8.0)  # 80% of 10GB
        self.assertTrue(service.is_storage_monitoring_enabled())
        self.assertTrue(service.validate_storage_config())
    
    def test_valid_environment_configuration(self):
        """Test service initialization with valid environment variables"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '25.5'
        os.environ['STORAGE_WARNING_THRESHOLD'] = '85.0'
        os.environ['STORAGE_MONITORING_ENABLED'] = 'true'
        
        service = StorageConfigurationService()
        
        self.assertEqual(service.get_max_storage_gb(), 25.5)
        self.assertEqual(service.get_warning_threshold_gb(), 21.675)  # 85% of 25.5GB
        self.assertTrue(service.is_storage_monitoring_enabled())
        self.assertTrue(service.validate_storage_config())
    
    def test_invalid_max_storage_gb_negative(self):
        """Test handling of negative CAPTION_MAX_STORAGE_GB"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '-5.0'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default value
            self.assertEqual(service.get_max_storage_gb(), 10.0)
            
            # Should log error and warning
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
    
    def test_invalid_max_storage_gb_zero(self):
        """Test handling of zero CAPTION_MAX_STORAGE_GB"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '0'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default value
            self.assertEqual(service.get_max_storage_gb(), 10.0)
            
            # Should log error and warning
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
    
    def test_invalid_max_storage_gb_non_numeric(self):
        """Test handling of non-numeric CAPTION_MAX_STORAGE_GB"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = 'not_a_number'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default value
            self.assertEqual(service.get_max_storage_gb(), 10.0)
            
            # Should log error and warning
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
    
    def test_invalid_warning_threshold_too_high(self):
        """Test handling of warning threshold > 100%"""
        os.environ['STORAGE_WARNING_THRESHOLD'] = '150.0'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default warning threshold (80%)
            self.assertEqual(service.get_warning_threshold_gb(), 8.0)  # 80% of 10GB
            
            # Should log error and warning
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
    
    def test_invalid_warning_threshold_zero(self):
        """Test handling of warning threshold = 0%"""
        os.environ['STORAGE_WARNING_THRESHOLD'] = '0'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default warning threshold (80%)
            self.assertEqual(service.get_warning_threshold_gb(), 8.0)  # 80% of 10GB
            
            # Should log error and warning
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
    
    def test_invalid_warning_threshold_non_numeric(self):
        """Test handling of non-numeric warning threshold"""
        os.environ['STORAGE_WARNING_THRESHOLD'] = 'invalid'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default warning threshold (80%)
            self.assertEqual(service.get_warning_threshold_gb(), 8.0)  # 80% of 10GB
            
            # Should log error and warning
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
    
    def test_monitoring_enabled_various_values(self):
        """Test various values for STORAGE_MONITORING_ENABLED"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('YES', True),
            ('on', True),
            ('ON', True),
            ('enabled', True),
            ('ENABLED', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('NO', False),
            ('off', False),
            ('OFF', False),
            ('disabled', False),
            ('DISABLED', False),
            ('invalid_value', False),
            ('', False),
        ]
        
        for env_value, expected in test_cases:
            with self.subTest(env_value=env_value):
                # Clear environment first
                if 'STORAGE_MONITORING_ENABLED' in os.environ:
                    del os.environ['STORAGE_MONITORING_ENABLED']
                
                os.environ['STORAGE_MONITORING_ENABLED'] = env_value
                service = StorageConfigurationService()
                self.assertEqual(service.is_storage_monitoring_enabled(), expected)
    
    def test_configuration_validation_success(self):
        """Test successful configuration validation"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '20.0'
        os.environ['STORAGE_WARNING_THRESHOLD'] = '75.0'
        
        service = StorageConfigurationService()
        self.assertTrue(service.validate_storage_config())
    
    def test_configuration_validation_with_edge_values(self):
        """Test configuration validation with edge case values"""
        # Test minimum valid values
        os.environ['CAPTION_MAX_STORAGE_GB'] = '0.1'  # Very small but positive
        os.environ['STORAGE_WARNING_THRESHOLD'] = '1.0'  # Very small but positive
        
        service = StorageConfigurationService()
        self.assertTrue(service.validate_storage_config())
        
        # Test maximum valid values
        os.environ['CAPTION_MAX_STORAGE_GB'] = '1000.0'  # Very large
        os.environ['STORAGE_WARNING_THRESHOLD'] = '99.9'  # Almost 100%
        
        service = StorageConfigurationService()
        self.assertTrue(service.validate_storage_config())
    
    def test_get_configuration_summary(self):
        """Test getting configuration summary"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '15.0'
        os.environ['STORAGE_WARNING_THRESHOLD'] = '70.0'
        os.environ['STORAGE_MONITORING_ENABLED'] = 'true'
        
        service = StorageConfigurationService()
        summary = service.get_configuration_summary()
        
        expected_summary = {
            'max_storage_gb': 15.0,
            'warning_threshold_percentage': 70.0,
            'warning_threshold_gb': 10.5,  # 70% of 15GB
            'monitoring_enabled': True,
            'is_valid': True
        }
        
        self.assertEqual(summary, expected_summary)
    
    def test_get_configuration_summary_with_invalid_config(self):
        """Test configuration summary when config is invalid"""
        # Create a service and then manually break its config for testing
        service = StorageConfigurationService()
        service._config = None  # Simulate failed configuration loading
        
        summary = service.get_configuration_summary()
        self.assertEqual(summary, {"error": "Configuration not loaded"})
    
    @patch('app.services.storage.components.storage_configuration_service.logger')
    def test_reload_configuration(self, mock_logger):
        """Test reloading configuration"""
        # Start with default configuration
        service = StorageConfigurationService()
        self.assertEqual(service.get_max_storage_gb(), 10.0)
        
        # Clear previous log calls
        mock_logger.reset_mock()
        
        # Change environment variable
        os.environ['CAPTION_MAX_STORAGE_GB'] = '30.0'
        
        # Reload configuration
        service.reload_configuration()
        
        # Should pick up new value
        self.assertEqual(service.get_max_storage_gb(), 30.0)
        
        # Should log reload message (check that it was called with this message)
        reload_calls = [call for call in mock_logger.info.call_args_list 
                       if "Reloading storage configuration" in str(call)]
        self.assertTrue(len(reload_calls) > 0, "Should log reload message")
    
    @patch('app.services.storage.components.storage_configuration_service.logger')
    def test_logging_on_successful_load(self, mock_logger):
        """Test that successful configuration loading is logged"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '12.0'
        
        service = StorageConfigurationService()
        
        # Should log successful configuration load
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        self.assertIn("Storage configuration loaded", call_args)
        self.assertIn("max_storage=12.0GB", call_args)
    
    @patch('app.services.storage.components.storage_configuration_service.logger')
    def test_logging_on_configuration_error(self, mock_logger):
        """Test logging when configuration loading fails"""
        # Mock an exception during configuration loading
        with patch.object(StorageConfigurationService, '_get_max_storage_gb_from_env', 
                         side_effect=Exception("Test exception")):
            service = StorageConfigurationService()
            
            # Should log error and use defaults
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()
            
            # Should still work with defaults
            self.assertEqual(service.get_max_storage_gb(), 10.0)
    
    def test_requirements_1_1_read_caption_max_storage_gb(self):
        """Test Requirement 1.1: System SHALL read CAPTION_MAX_STORAGE_GB from environment"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = '15.0'
        
        service = StorageConfigurationService()
        
        # Should read the value from environment
        self.assertEqual(service.get_max_storage_gb(), 15.0)
    
    def test_requirements_1_2_default_value_10gb(self):
        """Test Requirement 1.2: System SHALL use default value of 10 GB when not set"""
        # Ensure environment variable is not set
        if 'CAPTION_MAX_STORAGE_GB' in os.environ:
            del os.environ['CAPTION_MAX_STORAGE_GB']
        
        service = StorageConfigurationService()
        
        # Should use default value of 10 GB
        self.assertEqual(service.get_max_storage_gb(), 10.0)
    
    def test_requirements_1_3_validate_positive_number(self):
        """Test Requirement 1.3: System SHALL validate CAPTION_MAX_STORAGE_GB as positive"""
        test_cases = [
            ('15.5', 15.5, True),    # Valid positive number
            ('0.1', 0.1, True),      # Valid small positive number
            ('1000', 1000.0, True),  # Valid large positive number
            ('-5.0', 10.0, False),   # Invalid negative number -> default
            ('0', 10.0, False),      # Invalid zero -> default
            ('-0.1', 10.0, False),   # Invalid negative -> default
        ]
        
        for env_value, expected_value, should_be_valid in test_cases:
            with self.subTest(env_value=env_value):
                # Clear environment first
                if 'CAPTION_MAX_STORAGE_GB' in os.environ:
                    del os.environ['CAPTION_MAX_STORAGE_GB']
                
                os.environ['CAPTION_MAX_STORAGE_GB'] = env_value
                
                with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
                    service = StorageConfigurationService()
                    
                    self.assertEqual(service.get_max_storage_gb(), expected_value)
                    
                    if not should_be_valid:
                        # Should log error for invalid values
                        mock_logger.error.assert_called()
    
    def test_requirements_1_4_log_error_use_default_on_invalid(self):
        """Test Requirement 1.4: System SHALL log error and use default on invalid value"""
        os.environ['CAPTION_MAX_STORAGE_GB'] = 'invalid_value'
        
        with patch('app.services.storage.components.storage_configuration_service.logger') as mock_logger:
            service = StorageConfigurationService()
            
            # Should use default value
            self.assertEqual(service.get_max_storage_gb(), 10.0)
            
            # Should log error
            mock_logger.error.assert_called()
            error_call_args = mock_logger.error.call_args[0][0]
            self.assertIn("Invalid CAPTION_MAX_STORAGE_GB", error_call_args)
            
            # Should log warning about using default
            mock_logger.warning.assert_called()
            warning_call_args = mock_logger.warning.call_args[0][0]
            self.assertIn("Using default value", warning_call_args)


if __name__ == '__main__':
    # Set up logging for tests
    logging.basicConfig(level=logging.DEBUG)
    
    unittest.main()