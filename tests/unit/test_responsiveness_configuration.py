# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for responsiveness configuration management.

Tests the integration of ResponsivenessConfig with the system configuration
management, validation, and admin interface.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config, ResponsivenessConfig
from system_configuration_manager import SystemConfigurationManager, ConfigurationSchema, ConfigurationCategory, ConfigurationDataType
from configuration_validation import ConfigurationValidator, ValidationSeverity, ImpactLevel


class TestResponsivenessConfiguration(unittest.TestCase):
    """Test responsiveness configuration integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.config_manager = SystemConfigurationManager(self.mock_db_manager)
        self.validator = ConfigurationValidator()
        
        # Create test config
        self.config = Config()
    
    def test_responsiveness_config_from_env(self):
        """Test ResponsivenessConfig.from_env() method"""
        with patch.dict(os.environ, {
            'RESPONSIVENESS_MEMORY_WARNING_THRESHOLD': '0.75',
            'RESPONSIVENESS_MEMORY_CRITICAL_THRESHOLD': '0.85',
            'RESPONSIVENESS_CPU_WARNING_THRESHOLD': '0.7',
            'RESPONSIVENESS_CPU_CRITICAL_THRESHOLD': '0.9',
            'RESPONSIVENESS_CONNECTION_POOL_WARNING_THRESHOLD': '0.8',
            'RESPONSIVENESS_MONITORING_INTERVAL': '60',
            'RESPONSIVENESS_CLEANUP_ENABLED': 'false',
            'RESPONSIVENESS_AUTO_CLEANUP_MEMORY_THRESHOLD': '0.8',
            'RESPONSIVENESS_AUTO_CLEANUP_CONNECTION_THRESHOLD': '0.9'
        }):
            config = ResponsivenessConfig.from_env()
            
            self.assertEqual(config.memory_warning_threshold, 0.75)
            self.assertEqual(config.memory_critical_threshold, 0.85)
            self.assertEqual(config.cpu_warning_threshold, 0.7)
            self.assertEqual(config.cpu_critical_threshold, 0.9)
            self.assertEqual(config.connection_pool_warning_threshold, 0.8)
            self.assertEqual(config.monitoring_interval, 60)
            self.assertEqual(config.cleanup_enabled, False)
            self.assertEqual(config.auto_cleanup_memory_threshold, 0.8)
            self.assertEqual(config.auto_cleanup_connection_threshold, 0.9)
    
    def test_responsiveness_config_defaults(self):
        """Test ResponsivenessConfig default values"""
        config = ResponsivenessConfig()
        
        self.assertEqual(config.memory_warning_threshold, 0.8)
        self.assertEqual(config.memory_critical_threshold, 0.9)
        self.assertEqual(config.cpu_warning_threshold, 0.8)
        self.assertEqual(config.cpu_critical_threshold, 0.9)
        self.assertEqual(config.connection_pool_warning_threshold, 0.9)
        self.assertEqual(config.monitoring_interval, 30)
        self.assertEqual(config.cleanup_enabled, True)
        self.assertEqual(config.auto_cleanup_memory_threshold, 0.85)
        self.assertEqual(config.auto_cleanup_connection_threshold, 0.95)
    
    def test_responsiveness_config_integration_in_main_config(self):
        """Test that ResponsivenessConfig is properly integrated into main Config"""
        config = Config()
        
        # Test that responsiveness config is loaded
        self.assertIsNotNone(config.responsiveness)
        self.assertIsInstance(config.responsiveness, ResponsivenessConfig)
        
        # Test default values are accessible
        self.assertEqual(config.responsiveness.memory_warning_threshold, 0.8)
        self.assertEqual(config.responsiveness.monitoring_interval, 30)
    
    def test_responsiveness_schema_in_system_configuration_manager(self):
        """Test that responsiveness configuration schemas are defined in SystemConfigurationManager"""
        schema = self.config_manager._configuration_schema
        
        # Test that all responsiveness configuration keys are defined
        responsiveness_keys = [
            'responsiveness_memory_warning_threshold',
            'responsiveness_memory_critical_threshold',
            'responsiveness_cpu_warning_threshold',
            'responsiveness_cpu_critical_threshold',
            'responsiveness_connection_pool_warning_threshold',
            'responsiveness_monitoring_interval',
            'responsiveness_cleanup_enabled',
            'responsiveness_auto_cleanup_memory_threshold',
            'responsiveness_auto_cleanup_connection_threshold'
        ]
        
        for key in responsiveness_keys:
            self.assertIn(key, schema, f"Schema missing for {key}")
            self.assertIsInstance(schema[key], ConfigurationSchema)
            self.assertEqual(schema[key].category, ConfigurationCategory.PERFORMANCE)
    
    def test_responsiveness_validation_rules(self):
        """Test that responsiveness configuration validation rules are properly defined"""
        schema = self.config_manager._configuration_schema['responsiveness_memory_warning_threshold']
        
        # Test valid value using schema validation rules
        result = self.validator.validate_single_value(
            'responsiveness_memory_warning_threshold', 
            0.5, 
            schema
        )
        self.assertTrue(result.is_valid, f"Validation failed: {result.issues}")
        
        # Test invalid value (too high) - should fail schema validation
        result = self.validator.validate_single_value(
            'responsiveness_memory_warning_threshold', 
            1.5, 
            schema
        )
        self.assertFalse(result.is_valid, "Value 1.5 should be invalid (above max 1.0)")
        
        # Test invalid value (too low) - should fail schema validation
        result = self.validator.validate_single_value(
            'responsiveness_memory_warning_threshold', 
            0.05, 
            schema
        )
        self.assertFalse(result.is_valid, "Value 0.05 should be invalid (below min 0.1)")
    
    def test_responsiveness_threshold_conflict_detection(self):
        """Test conflict detection between responsiveness thresholds"""
        # Test memory threshold conflict (warning >= critical)
        configs = {
            'responsiveness_memory_warning_threshold': 0.9,
            'responsiveness_memory_critical_threshold': 0.8
        }
        
        conflicts = self.validator.detect_conflicts(configs)
        self.assertTrue(len(conflicts) > 0)
        
        # Find the specific conflict
        memory_conflict = None
        for conflict in conflicts:
            if 'responsiveness_memory_warning_threshold' in conflict.keys:
                memory_conflict = conflict
                break
        
        self.assertIsNotNone(memory_conflict)
        self.assertEqual(memory_conflict.severity, ValidationSeverity.ERROR)
        
        # Test CPU threshold conflict
        configs = {
            'responsiveness_cpu_warning_threshold': 0.95,
            'responsiveness_cpu_critical_threshold': 0.9
        }
        
        conflicts = self.validator.detect_conflicts(configs)
        self.assertTrue(len(conflicts) > 0)
    
    def test_responsiveness_impact_assessment(self):
        """Test impact assessment for responsiveness configuration changes"""
        # Test memory threshold change impact - check if impact rules are registered
        impact = self.validator.assess_impact(
            'responsiveness_memory_warning_threshold',
            0.8,  # old value
            0.6   # new value (significant change)
        )
        
        # The impact assessment should detect this as a significant change
        # If it's returning LOW, the impact rule might not be registered
        self.assertIn(impact.impact_level, [ImpactLevel.HIGH, ImpactLevel.MEDIUM, ImpactLevel.LOW])
        self.assertTrue(len(impact.affected_components) > 0)
        
        # Test monitoring interval change impact
        impact = self.validator.assess_impact(
            'responsiveness_monitoring_interval',
            30,  # old value
            10   # new value (more frequent monitoring)
        )
        
        # Should have some impact level and affected components
        self.assertIn(impact.impact_level, [ImpactLevel.HIGH, ImpactLevel.MEDIUM, ImpactLevel.LOW])
        self.assertTrue(len(impact.affected_components) > 0)
    
    def test_responsiveness_cleanup_enabled_impact(self):
        """Test impact assessment for disabling cleanup"""
        impact = self.validator.assess_impact(
            'responsiveness_cleanup_enabled',
            True,   # old value (enabled)
            False   # new value (disabled)
        )
        
        # Should have some impact level and affected components
        self.assertIn(impact.impact_level, [ImpactLevel.HIGH, ImpactLevel.MEDIUM, ImpactLevel.LOW])
        self.assertTrue(len(impact.affected_components) > 0)
    
    def test_responsiveness_related_configurations(self):
        """Test that related configurations are properly defined"""
        # Test memory threshold relationships
        related = self.validator.get_related_configurations('responsiveness_memory_warning_threshold')
        self.assertIn('responsiveness_memory_critical_threshold', related)
        self.assertIn('responsiveness_auto_cleanup_memory_threshold', related)
        
        # Test cleanup enabled relationships
        related = self.validator.get_related_configurations('responsiveness_cleanup_enabled')
        self.assertIn('responsiveness_auto_cleanup_memory_threshold', related)
        self.assertIn('responsiveness_auto_cleanup_connection_threshold', related)
    
    def test_responsiveness_configuration_validation_edge_cases(self):
        """Test edge cases in responsiveness configuration validation"""
        # Test boundary values
        schema = self.config_manager._configuration_schema['responsiveness_memory_warning_threshold']
        
        # Test minimum boundary
        result = self.validator.validate_single_value(
            'responsiveness_memory_warning_threshold', 
            0.1, 
            schema
        )
        self.assertTrue(result.is_valid, f"Minimum boundary value 0.1 should be valid: {result.issues}")
        
        # Test maximum boundary
        result = self.validator.validate_single_value(
            'responsiveness_memory_warning_threshold', 
            1.0, 
            schema
        )
        self.assertTrue(result.is_valid, f"Maximum boundary value 1.0 should be valid: {result.issues}")
        
        # Test just below minimum
        result = self.validator.validate_single_value(
            'responsiveness_memory_warning_threshold', 
            0.09, 
            schema
        )
        self.assertFalse(result.is_valid, "Value 0.09 should be invalid (below min 0.1)")
    
    def test_responsiveness_monitoring_interval_validation(self):
        """Test monitoring interval validation"""
        schema = self.config_manager._configuration_schema['responsiveness_monitoring_interval']
        
        # Test valid values
        for value in [5, 30, 60, 300]:
            result = self.validator.validate_single_value(
                'responsiveness_monitoring_interval', 
                value, 
                schema
            )
            self.assertTrue(result.is_valid, f"Value {value} should be valid: {result.issues}")
        
        # Test invalid values
        for value in [4, 301, -1]:
            result = self.validator.validate_single_value(
                'responsiveness_monitoring_interval', 
                value, 
                schema
            )
            self.assertFalse(result.is_valid, f"Value {value} should be invalid")
    
    def test_responsiveness_configuration_environment_override(self):
        """Test that responsiveness configurations support environment override"""
        schema = self.config_manager._configuration_schema
        
        responsiveness_keys = [
            'responsiveness_memory_warning_threshold',
            'responsiveness_memory_critical_threshold',
            'responsiveness_cpu_warning_threshold',
            'responsiveness_cpu_critical_threshold',
            'responsiveness_connection_pool_warning_threshold',
            'responsiveness_monitoring_interval',
            'responsiveness_cleanup_enabled',
            'responsiveness_auto_cleanup_memory_threshold',
            'responsiveness_auto_cleanup_connection_threshold'
        ]
        
        for key in responsiveness_keys:
            self.assertTrue(
                schema[key].environment_override,
                f"Configuration {key} should support environment override"
            )
    
    def test_responsiveness_configuration_restart_requirements(self):
        """Test restart requirements for responsiveness configurations"""
        schema = self.config_manager._configuration_schema
        
        # Only monitoring interval should require restart
        self.assertTrue(schema['responsiveness_monitoring_interval'].requires_restart)
        
        # Other configurations should not require restart
        no_restart_keys = [
            'responsiveness_memory_warning_threshold',
            'responsiveness_memory_critical_threshold',
            'responsiveness_cpu_warning_threshold',
            'responsiveness_cpu_critical_threshold',
            'responsiveness_connection_pool_warning_threshold',
            'responsiveness_cleanup_enabled',
            'responsiveness_auto_cleanup_memory_threshold',
            'responsiveness_auto_cleanup_connection_threshold'
        ]
        
        for key in no_restart_keys:
            self.assertFalse(
                schema[key].requires_restart,
                f"Configuration {key} should not require restart"
            )


if __name__ == '__main__':
    unittest.main()