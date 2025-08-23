# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for System Configuration Manager

Tests comprehensive system configuration management including:
- Configuration CRUD operations
- Validation and conflict detection
- Audit trail and rollback capabilities
- Export/import functionality
- Environment overrides
"""

import unittest
import json
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from config import Config
from database import DatabaseManager
from models import SystemConfiguration, User, UserRole, JobAuditLog
from system_configuration_manager import (
    SystemConfigurationManager, ConfigurationCategory, ConfigurationDataType,
    ConfigurationSchema, ConfigurationChange, ConfigurationValidationResult,
    ConfigurationExport
)


class TestSystemConfigurationManager(unittest.TestCase):
    """Test cases for SystemConfigurationManager"""
    
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
        
        # Create mock regular user
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.role = UserRole.REVIEWER
    
    def test_initialization(self):
        """Test configuration manager initialization"""
        self.assertIsInstance(self.config_manager, SystemConfigurationManager)
        self.assertIsNotNone(self.config_manager._configuration_schema)
        self.assertEqual(self.config_manager._environment_prefix, "VEDFOLNIR_CONFIG_")
        
        # Check that schema contains expected configurations
        schema = self.config_manager._configuration_schema
        self.assertIn("max_concurrent_jobs", schema)
        self.assertIn("maintenance_mode", schema)
        self.assertIn("rate_limit_per_user_per_hour", schema)
    
    def test_get_configuration_from_database(self):
        """Test getting configuration from database"""
        # Mock database configuration
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.key = "max_concurrent_jobs"
        mock_config.value = "10"
        mock_config.data_type = "integer"
        mock_config.is_sensitive = False
        mock_config.get_typed_value.return_value = 10
        
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        # Test getting configuration
        value = self.config_manager.get_configuration("max_concurrent_jobs")
        self.assertEqual(value, 10)
        
        # Verify database query
        self.session_mock.query.assert_called_with(SystemConfiguration)
        self.session_mock.query.return_value.filter_by.assert_called_with(key="max_concurrent_jobs")
    
    @patch.dict(os.environ, {'VEDFOLNIR_CONFIG_MAX_CONCURRENT_JOBS': '20'})
    def test_get_configuration_environment_override(self):
        """Test getting configuration with environment override"""
        # Mock database configuration
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.get_typed_value.return_value = 10
        
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        # Test getting configuration - should return environment value
        value = self.config_manager.get_configuration("max_concurrent_jobs")
        self.assertEqual(value, 20)  # Environment override
    
    def test_get_configuration_default_value(self):
        """Test getting configuration default value when not in database"""
        # Mock no configuration in database
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Test getting configuration - should return default
        value = self.config_manager.get_configuration("max_concurrent_jobs")
        self.assertEqual(value, 10)  # Default value from schema
    
    def test_get_configuration_sensitive_unauthorized(self):
        """Test getting sensitive configuration without admin authorization"""
        # Mock sensitive configuration
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.is_sensitive = True
        mock_config.get_typed_value.return_value = "secret_value"
        
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = mock_config
        
        # Test getting sensitive configuration without admin user ID
        value = self.config_manager.get_configuration("sensitive_key")
        self.assertEqual(value, "secret_value")  # Should still return value (no admin check without admin_user_id)
    
    def test_set_configuration_success(self):
        """Test setting configuration successfully"""
        # Mock existing configuration
        mock_config = Mock(spec=SystemConfiguration)
        mock_config.get_typed_value.return_value = 10
        mock_config.set_typed_value = Mock()
        
        # Mock query calls - first for admin user, second for existing config
        self.session_mock.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin authorization
            mock_config       # Existing configuration
        ]
        
        # Test setting configuration
        result = self.config_manager.set_configuration("max_concurrent_jobs", 15, 1, "Test update")
        
        self.assertTrue(result)
        mock_config.set_typed_value.assert_called_with(15)
        self.assertEqual(mock_config.updated_by, 1)
        self.session_mock.commit.assert_called_once()
    
    def test_set_configuration_unauthorized(self):
        """Test setting configuration without admin authorization"""
        # Mock regular user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Test setting configuration - should fail
        result = self.config_manager.set_configuration("max_concurrent_jobs", 15, 2, "Test update")
        
        self.assertFalse(result)
        self.session_mock.commit.assert_not_called()
    
    def test_set_configuration_validation_failure(self):
        """Test setting configuration with validation failure"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Test setting configuration with invalid value (below minimum)
        result = self.config_manager.set_configuration("max_concurrent_jobs", 0, 1, "Test update")
        
        self.assertFalse(result)
        self.session_mock.commit.assert_not_called()
    
    def test_set_configuration_new_config(self):
        """Test setting new configuration that doesn't exist"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.side_effect = [
            self.admin_user,  # Admin authorization
            None  # No existing configuration
        ]
        
        # Test setting new configuration
        result = self.config_manager.set_configuration("new_config", "test_value", 1, "New config")
        
        self.assertTrue(result)
        self.session_mock.add.assert_called_once()
        self.session_mock.commit.assert_called_once()
    
    def test_get_all_configurations(self):
        """Test getting all configurations"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock configurations
        mock_configs = [
            Mock(key="config1", get_typed_value=Mock(return_value="value1")),
            Mock(key="config2", get_typed_value=Mock(return_value="value2"))
        ]
        
        self.session_mock.query.return_value.filter_by.return_value.all.return_value = mock_configs
        
        # Test getting all configurations
        result = self.config_manager.get_all_configurations(1)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result["config1"], "value1")
        self.assertEqual(result["config2"], "value2")
    
    def test_get_all_configurations_with_category_filter(self):
        """Test getting configurations filtered by category"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock configurations
        mock_configs = [Mock(key="system_config", get_typed_value=Mock(return_value="value"))]
        self.session_mock.query.return_value.filter_by.return_value.all.return_value = mock_configs
        
        # Test getting configurations with category filter
        result = self.config_manager.get_all_configurations(1, ConfigurationCategory.SYSTEM)
        
        self.assertEqual(len(result), 1)
        # Verify category filter was applied
        calls = self.session_mock.query.return_value.filter_by.call_args_list
        self.assertTrue(any('category' in str(call) for call in calls))
    
    def test_validate_configuration_set_success(self):
        """Test validating a set of configurations successfully"""
        configurations = {
            "max_concurrent_jobs": 15,
            "maintenance_mode": False
        }
        
        result = self.config_manager.validate_configuration_set(configurations)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_configuration_set_with_errors(self):
        """Test validating configurations with errors"""
        configurations = {
            "max_concurrent_jobs": 0,  # Below minimum
            "invalid_key": "value"     # No schema
        }
        
        result = self.config_manager.validate_configuration_set(configurations)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertGreater(len(result.warnings), 0)
    
    def test_validate_configuration_set_with_conflicts(self):
        """Test validating configurations with conflicts"""
        configurations = {
            "max_concurrent_jobs": 50,
            "queue_size_limit": 10  # Conflict: max_jobs > queue_limit
        }
        
        result = self.config_manager.validate_configuration_set(configurations)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.conflicts), 0)
    
    def test_export_configurations(self):
        """Test exporting configurations"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock configurations
        mock_configs = [
            Mock(key="config1", get_typed_value=Mock(return_value="value1")),
            Mock(key="config2", get_typed_value=Mock(return_value="value2"))
        ]
        self.session_mock.query.return_value.filter_by.return_value.all.return_value = mock_configs
        
        # Test export
        export_data = self.config_manager.export_configurations(1)
        
        self.assertIsNotNone(export_data)
        self.assertIsInstance(export_data, ConfigurationExport)
        self.assertEqual(len(export_data.configurations), 2)
        self.assertEqual(export_data.exported_by, 1)
        self.assertIsNotNone(export_data.export_timestamp)
    
    def test_import_configurations_validate_only(self):
        """Test importing configurations in validate-only mode"""
        export_data = ConfigurationExport(
            configurations={"max_concurrent_jobs": 15},
            metadata={"version": "1.0"},
            export_timestamp=datetime.now(timezone.utc),
            exported_by=1
        )
        
        success, messages = self.config_manager.import_configurations(export_data, 1, validate_only=True)
        
        self.assertTrue(success)
        self.assertIn("Validation completed successfully", messages)
    
    def test_import_configurations_with_validation_errors(self):
        """Test importing configurations with validation errors"""
        export_data = ConfigurationExport(
            configurations={"max_concurrent_jobs": 0},  # Invalid value
            metadata={"version": "1.0"},
            export_timestamp=datetime.now(timezone.utc),
            exported_by=1
        )
        
        success, messages = self.config_manager.import_configurations(export_data, 1)
        
        self.assertFalse(success)
        self.assertTrue(any("Validation error" in msg for msg in messages))
    
    def test_get_configuration_history(self):
        """Test getting configuration history"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock audit logs
        mock_log = Mock(spec=JobAuditLog)
        mock_log.details = json.dumps({
            "key": "test_key",
            "old_value": "old",
            "new_value": "new",
            "reason": "test"
        })
        mock_log.admin_user_id = 1
        mock_log.user_id = None
        mock_log.timestamp = datetime.now(timezone.utc)
        
        self.session_mock.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_log]
        
        # Test getting history
        history = self.config_manager.get_configuration_history("test_key", 1)
        
        self.assertEqual(len(history), 1)
        self.assertIsInstance(history[0], ConfigurationChange)
        self.assertEqual(history[0].key, "test_key")
        self.assertEqual(history[0].old_value, "old")
        self.assertEqual(history[0].new_value, "new")
    
    def test_rollback_configuration(self):
        """Test rolling back configuration"""
        # Mock admin user query
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Mock configuration history
        target_timestamp = datetime.now(timezone.utc)
        
        # Mock the get_configuration_history method
        with patch.object(self.config_manager, 'get_configuration_history') as mock_history:
            mock_history.return_value = [
                ConfigurationChange(
                    key="test_key",
                    old_value="old",
                    new_value="target_value",
                    changed_by=1,
                    changed_at=target_timestamp,
                    reason="test"
                )
            ]
            
            # Mock the set_configuration method
            with patch.object(self.config_manager, 'set_configuration') as mock_set:
                mock_set.return_value = True
                
                # Test rollback
                result = self.config_manager.rollback_configuration("test_key", target_timestamp, 1, "rollback test")
                
                self.assertTrue(result)
                mock_set.assert_called_once_with("test_key", "target_value", 1, "Rollback to {}: rollback test".format(target_timestamp))
    
    def test_get_configuration_schema(self):
        """Test getting configuration schema"""
        # Test getting all schemas
        all_schemas = self.config_manager.get_configuration_schema()
        self.assertIsInstance(all_schemas, dict)
        self.assertIn("max_concurrent_jobs", all_schemas)
        
        # Test getting specific schema
        schema = self.config_manager.get_configuration_schema("max_concurrent_jobs")
        self.assertIsInstance(schema, ConfigurationSchema)
        self.assertEqual(schema.key, "max_concurrent_jobs")
        self.assertEqual(schema.data_type, ConfigurationDataType.INTEGER)
    
    def test_get_configuration_documentation(self):
        """Test getting configuration documentation"""
        documentation = self.config_manager.get_configuration_documentation()
        
        self.assertIsInstance(documentation, dict)
        
        # Check that all categories are present
        for category in ConfigurationCategory:
            self.assertIn(category.value, documentation)
            
        # Check structure of documentation
        system_docs = documentation[ConfigurationCategory.SYSTEM.value]
        self.assertIn("name", system_docs)
        self.assertIn("description", system_docs)
        self.assertIn("configurations", system_docs)
        self.assertIsInstance(system_docs["configurations"], list)
    
    def test_convert_value_types(self):
        """Test value type conversion"""
        # Test integer conversion
        self.assertEqual(self.config_manager._convert_value("10", ConfigurationDataType.INTEGER), 10)
        
        # Test float conversion
        self.assertEqual(self.config_manager._convert_value("10.5", ConfigurationDataType.FLOAT), 10.5)
        
        # Test boolean conversion
        self.assertTrue(self.config_manager._convert_value("true", ConfigurationDataType.BOOLEAN))
        self.assertFalse(self.config_manager._convert_value("false", ConfigurationDataType.BOOLEAN))
        
        # Test JSON conversion
        json_value = self.config_manager._convert_value('{"key": "value"}', ConfigurationDataType.JSON)
        self.assertEqual(json_value, {"key": "value"})
        
        # Test string conversion (default)
        self.assertEqual(self.config_manager._convert_value(123, ConfigurationDataType.STRING), "123")
    
    def test_validate_configuration_individual(self):
        """Test individual configuration validation"""
        # Test valid configuration
        result = self.config_manager._validate_configuration("max_concurrent_jobs", 15)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Test invalid configuration (below minimum)
        result = self.config_manager._validate_configuration("max_concurrent_jobs", 0)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        
        # Test invalid configuration (above maximum)
        result = self.config_manager._validate_configuration("max_concurrent_jobs", 200)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        
        # Test unknown configuration key
        result = self.config_manager._validate_configuration("unknown_key", "value")
        self.assertTrue(result.is_valid)  # Should be valid but with warnings
        self.assertGreater(len(result.warnings), 0)
    
    def test_check_configuration_conflicts(self):
        """Test configuration conflict detection"""
        # Test conflict: max_concurrent_jobs > queue_size_limit
        conflicts = self.config_manager._check_configuration_conflicts({
            "max_concurrent_jobs": 50,
            "queue_size_limit": 10
        })
        self.assertGreater(len(conflicts), 0)
        
        # Test no conflicts
        conflicts = self.config_manager._check_configuration_conflicts({
            "max_concurrent_jobs": 10,
            "queue_size_limit": 50
        })
        self.assertEqual(len(conflicts), 0)
    
    def test_create_configuration_audit(self):
        """Test creating configuration audit trail"""
        # Test audit creation
        self.config_manager._create_configuration_audit(
            self.session_mock, "test_key", "old_value", "new_value", 1, "test reason"
        )
        
        # Verify audit log was added
        self.session_mock.add.assert_called_once()
        
        # Get the audit log that was added
        audit_log = self.session_mock.add.call_args[0][0]
        self.assertIsInstance(audit_log, JobAuditLog)
        self.assertEqual(audit_log.action, "configuration_change")
        self.assertEqual(audit_log.admin_user_id, 1)
        
        # Verify audit details
        details = json.loads(audit_log.details)
        self.assertEqual(details["key"], "test_key")
        self.assertEqual(details["old_value"], "old_value")
        self.assertEqual(details["new_value"], "new_value")
        self.assertEqual(details["reason"], "test reason")
    
    def test_verify_admin_authorization_success(self):
        """Test admin authorization verification success"""
        # Mock admin user
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.admin_user
        
        # Should not raise exception
        try:
            self.config_manager._verify_admin_authorization(self.session_mock, 1)
        except ValueError:
            self.fail("Admin authorization should have succeeded")
    
    def test_verify_admin_authorization_failure(self):
        """Test admin authorization verification failure"""
        # Mock regular user
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = self.regular_user
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            self.config_manager._verify_admin_authorization(self.session_mock, 2)
    
    def test_verify_admin_authorization_user_not_found(self):
        """Test admin authorization when user not found"""
        # Mock no user found
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            self.config_manager._verify_admin_authorization(self.session_mock, 999)


if __name__ == '__main__':
    unittest.main()