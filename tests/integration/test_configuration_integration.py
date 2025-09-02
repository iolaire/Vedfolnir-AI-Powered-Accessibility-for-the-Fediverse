# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for System Configuration Management

Tests the complete configuration management system including
manager, validation, and basic functionality.
"""

import unittest
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from config import Config
from database import DatabaseManager
from models import SystemConfiguration, User, UserRole
from system_configuration_manager import (
    SystemConfigurationManager, ConfigurationCategory, 
    ConfigurationDataType, ConfigurationValidationResult
)


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for configuration management system"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = Mock(spec=DatabaseManager)
        self.session_mock = Mock()
        
        # Mock the context manager properly
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.session_mock)
        context_manager.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = context_manager
        
        self.config_manager = SystemConfigurationManager(self.db_manager)
        
        # Create mock admin user
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.role = UserRole.ADMIN
    
    def test_configuration_schema_completeness(self):
        """Test that configuration schema includes all expected categories"""
        schema = self.config_manager.get_configuration_schema()
        
        # Check that we have configurations for all categories
        categories_found = set()
        for config_schema in schema.values():
            categories_found.add(config_schema.category)
        
        # Should have at least these categories
        expected_categories = {
            ConfigurationCategory.SYSTEM,
            ConfigurationCategory.PERFORMANCE,
            ConfigurationCategory.SECURITY,
            ConfigurationCategory.ALERTS,
            ConfigurationCategory.FEATURES
        }
        
        self.assertTrue(expected_categories.issubset(categories_found))
    
    def test_configuration_validation_rules(self):
        """Test that configuration validation rules work correctly"""
        # Test valid configurations
        valid_configs = {
            "max_concurrent_jobs": 15,
            "maintenance_mode": False,
            "rate_limit_per_user_per_hour": 100
        }
        
        result = self.config_manager.validate_configuration_set(valid_configs)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Test invalid configurations
        invalid_configs = {
            "max_concurrent_jobs": 0,  # Below minimum
            "rate_limit_per_user_per_hour": -1  # Below minimum
        }
        
        result = self.config_manager.validate_configuration_set(invalid_configs)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_configuration_conflict_detection(self):
        """Test that configuration conflicts are detected"""
        # Test conflicting configurations
        conflicting_configs = {
            "max_concurrent_jobs": 100,
            "queue_size_limit": 10  # Conflict: max_jobs > queue_limit
        }
        
        result = self.config_manager.validate_configuration_set(conflicting_configs)
        self.assertGreater(len(result.conflicts), 0)
        
        # Test non-conflicting configurations
        valid_configs = {
            "max_concurrent_jobs": 10,
            "queue_size_limit": 50
        }
        
        result = self.config_manager.validate_configuration_set(valid_configs)
        self.assertEqual(len(result.conflicts), 0)
    
    def test_data_type_conversion(self):
        """Test that data type conversion works correctly"""
        # Test integer conversion
        result = self.config_manager._convert_value("42", ConfigurationDataType.INTEGER)
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)
        
        # Test float conversion
        result = self.config_manager._convert_value("3.14", ConfigurationDataType.FLOAT)
        self.assertEqual(result, 3.14)
        self.assertIsInstance(result, float)
        
        # Test boolean conversion
        result = self.config_manager._convert_value("true", ConfigurationDataType.BOOLEAN)
        self.assertTrue(result)
        self.assertIsInstance(result, bool)
        
        result = self.config_manager._convert_value("false", ConfigurationDataType.BOOLEAN)
        self.assertFalse(result)
        
        # Test JSON conversion
        result = self.config_manager._convert_value('{"key": "value"}', ConfigurationDataType.JSON)
        self.assertEqual(result, {"key": "value"})
        self.assertIsInstance(result, dict)
        
        # Test string conversion (default)
        result = self.config_manager._convert_value(123, ConfigurationDataType.STRING)
        self.assertEqual(result, "123")
        self.assertIsInstance(result, str)
    
    @patch.dict(os.environ, {'VEDFOLNIR_CONFIG_TEST_KEY': 'environment_value'})
    def test_environment_override(self):
        """Test that environment variables override database values"""
        # Mock database configuration
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.get_typed_value.return_value = "database_value"
        
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        # Test getting configuration - should return environment value
        value = self.config_manager.get_configuration("test_key")
        self.assertEqual(value, "environment_value")
    
    def test_configuration_documentation_structure(self):
        """Test that configuration documentation has proper structure"""
        documentation = self.config_manager.get_configuration_documentation()
        
        # Check that documentation is properly structured
        self.assertIsInstance(documentation, dict)
        
        for category_key, category_info in documentation.items():
            # Each category should have required fields
            self.assertIn("name", category_info)
            self.assertIn("description", category_info)
            self.assertIn("configurations", category_info)
            
            # Configurations should be a list
            self.assertIsInstance(category_info["configurations"], list)
            
            # Each configuration should have required fields
            for config in category_info["configurations"]:
                required_fields = ["key", "description", "data_type", "default_value"]
                for field in required_fields:
                    self.assertIn(field, config)
    
    def test_export_import_roundtrip(self):
        """Test that export/import works correctly"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock configurations for export
        mock_configs = [
            Mock(key="config1", get_typed_value=Mock(return_value="value1")),
            Mock(key="config2", get_typed_value=Mock(return_value=42))
        ]
        self.session_mock.query.return_value.filter_by.return_value.all.return_value = mock_configs
        
        # Test export
        export_data = self.config_manager.export_configurations(1)
        
        self.assertIsNotNone(export_data)
        self.assertEqual(len(export_data.configurations), 2)
        self.assertEqual(export_data.configurations["config1"], "value1")
        self.assertEqual(export_data.configurations["config2"], 42)
        
        # Test import validation (validate only)
        success, messages = self.config_manager.import_configurations(
            export_data, 1, validate_only=True
        )
        
        self.assertTrue(success)
        self.assertIn("Validation completed successfully", messages)
    
    def test_configuration_categories_enum(self):
        """Test that all configuration categories are properly defined"""
        # Test that all enum values are strings
        for category in ConfigurationCategory:
            self.assertIsInstance(category.value, str)
            self.assertTrue(len(category.value) > 0)
        
        # Test that category descriptions are available
        for category in ConfigurationCategory:
            description = self.config_manager._get_category_description(category)
            self.assertIsInstance(description, str)
            self.assertTrue(len(description) > 0)
    
    def test_configuration_data_types_enum(self):
        """Test that all configuration data types are properly defined"""
        # Test that all enum values are strings
        for data_type in ConfigurationDataType:
            self.assertIsInstance(data_type.value, str)
            self.assertTrue(len(data_type.value) > 0)
        
        # Test that conversion works for all data types
        test_values = {
            ConfigurationDataType.STRING: "test",
            ConfigurationDataType.INTEGER: "42",
            ConfigurationDataType.FLOAT: "3.14",
            ConfigurationDataType.BOOLEAN: "true",
            ConfigurationDataType.JSON: '{"key": "value"}'
        }
        
        for data_type, test_value in test_values.items():
            try:
                result = self.config_manager._convert_value(test_value, data_type)
                self.assertIsNotNone(result)
            except Exception as e:
                self.fail(f"Conversion failed for {data_type.value}: {e}")
    
    def test_validation_result_structure(self):
        """Test that validation results have proper structure"""
        # Test with valid configuration
        result = self.config_manager.validate_configuration_set({"max_concurrent_jobs": 10})
        
        self.assertIsInstance(result, ConfigurationValidationResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.errors, list)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.conflicts, list)
        
        # Test with invalid configuration
        result = self.config_manager.validate_configuration_set({"max_concurrent_jobs": 0})
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_admin_authorization_check(self):
        """Test that admin authorization is properly checked"""
        # Test with admin user
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        try:
            self.config_manager._verify_admin_authorization(self.session_mock, 1)
        except ValueError:
            self.fail("Admin authorization should have succeeded")
        
        # Test with non-admin user
        regular_user = Mock(spec=User)
        regular_user.id = 2
        regular_user.role = UserRole.REVIEWER
        
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = regular_user
        
        with self.assertRaises(ValueError):
            self.config_manager._verify_admin_authorization(self.session_mock, 2)
        
        # Test with non-existent user
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        with self.assertRaises(ValueError):
            self.config_manager._verify_admin_authorization(self.session_mock, 999)


if __name__ == '__main__':
    unittest.main()