# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for Maintenance Configuration Validator

Tests comprehensive validation of maintenance mode configuration parameters.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from maintenance_configuration_validator import (
    MaintenanceConfigurationValidator,
    ValidationSeverity,
    ValidationMessage,
    ValidationResult
)


class TestMaintenanceConfigurationValidator(unittest.TestCase):
    """Test maintenance configuration validator functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.validator = MaintenanceConfigurationValidator()
        
        # Create mock maintenance service
        self.mock_maintenance_service = Mock()
        self.validator_with_service = MaintenanceConfigurationValidator(
            maintenance_service=self.mock_maintenance_service
        )
    
    def test_valid_configuration(self):
        """Test validation of valid configuration"""
        config = {
            'reason': 'System maintenance for security updates',
            'duration': 60,
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors_count, 0)
        self.assertIsNotNone(result.validated_config)
        self.assertEqual(result.validated_config['reason'], config['reason'])
        self.assertEqual(result.validated_config['duration'], config['duration'])
        self.assertEqual(result.validated_config['mode'], config['mode'])
    
    def test_invalid_configuration_missing_reason(self):
        """Test validation with missing reason"""
        config = {
            'duration': 60,
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.errors_count, 0)
        
        # Check for specific error
        error_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.ERROR]
        self.assertTrue(any('required' in msg.lower() for msg in error_messages))
    
    def test_invalid_configuration_empty_reason(self):
        """Test validation with empty reason"""
        config = {
            'reason': '',
            'duration': 60,
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.errors_count, 0)
    
    def test_invalid_configuration_reason_too_long(self):
        """Test validation with reason too long"""
        config = {
            'reason': 'x' * 501,  # Exceeds max length
            'duration': 60,
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.errors_count, 0)
        
        # Check for specific error
        error_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.ERROR]
        self.assertTrue(any('too long' in msg.lower() for msg in error_messages))
    
    def test_warning_short_reason(self):
        """Test validation warning for short reason"""
        config = {
            'reason': 'Short',  # Less than 10 characters
            'duration': 60,
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(result.warnings_count, 0)
        
        # Check for specific warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        self.assertTrue(any('descriptive' in msg.lower() for msg in warning_messages))
    
    def test_invalid_duration_negative(self):
        """Test validation with negative duration"""
        config = {
            'reason': 'Valid maintenance reason',
            'duration': -10,
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.errors_count, 0)
        
        # Check for specific error
        error_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.ERROR]
        self.assertTrue(any('positive' in msg.lower() for msg in error_messages))
    
    def test_invalid_duration_too_long(self):
        """Test validation with duration too long"""
        config = {
            'reason': 'Valid maintenance reason',
            'duration': 1500,  # Exceeds 24 hours
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.errors_count, 0)
        
        # Check for specific error
        error_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.ERROR]
        self.assertTrue(any('exceed' in msg.lower() for msg in error_messages))
    
    def test_warning_long_duration(self):
        """Test validation warning for long duration"""
        config = {
            'reason': 'Valid maintenance reason',
            'duration': 500,  # More than 8 hours
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(result.warnings_count, 0)
        
        # Check for specific warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        self.assertTrue(any('long' in msg.lower() for msg in warning_messages))
    
    def test_warning_short_duration(self):
        """Test validation warning for very short duration"""
        config = {
            'reason': 'Valid maintenance reason',
            'duration': 3,  # Less than 5 minutes
            'mode': 'normal'
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(result.warnings_count, 0)
        
        # Check for specific warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        self.assertTrue(any('short' in msg.lower() for msg in warning_messages))
    
    def test_invalid_mode(self):
        """Test validation with invalid mode"""
        config = {
            'reason': 'Valid maintenance reason',
            'duration': 60,
            'mode': 'invalid_mode'
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.errors_count, 0)
        
        # Check for specific error
        error_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.ERROR]
        self.assertTrue(any('invalid' in msg.lower() for msg in error_messages))
    
    def test_emergency_mode_warning(self):
        """Test validation warning for emergency mode"""
        config = {
            'reason': 'Critical security issue detected',
            'duration': 30,
            'mode': 'emergency'
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid but with warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(result.warnings_count, 0)
        
        # Check for specific warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        self.assertTrue(any('emergency' in msg.lower() for msg in warning_messages))
    
    def test_test_mode_info(self):
        """Test validation info for test mode"""
        config = {
            'reason': 'Testing maintenance procedures',
            'duration': 15,
            'mode': 'test'
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid with info messages
        self.assertTrue(result.is_valid)
        self.assertGreater(result.info_count, 0)
        
        # Check for specific info
        info_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.INFO]
        self.assertTrue(any('simulate' in msg.lower() for msg in info_messages))
    
    def test_consistency_validation_emergency_mode(self):
        """Test consistency validation for emergency mode"""
        config = {
            'reason': 'Routine system maintenance',  # Doesn't match emergency
            'duration': 60,
            'mode': 'emergency'
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid but with consistency warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(result.warnings_count, 0)
        
        # Check for consistency warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        consistency_warnings = [msg for msg in warning_messages if 'emergency' in msg.lower() and 'reason' in msg.lower()]
        self.assertGreater(len(consistency_warnings), 0)
    
    def test_context_validation_with_service(self):
        """Test context validation with maintenance service"""
        # Mock active maintenance
        mock_status = Mock()
        mock_status.is_active = True
        mock_status.mode.value = 'normal'
        mock_status.reason = 'Existing maintenance'
        
        self.mock_maintenance_service.get_maintenance_status.return_value = mock_status
        self.mock_maintenance_service.get_service_stats.return_value = {'current_status': {}}
        
        config = {
            'reason': 'New maintenance reason',
            'duration': 60,
            'mode': 'normal'
        }
        
        result = self.validator_with_service.validate_configuration(config)
        
        # Should be valid but with context warnings
        self.assertTrue(result.is_valid)
        self.assertGreater(result.warnings_count, 0)
        
        # Check for context warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        context_warnings = [msg for msg in warning_messages if 'already active' in msg.lower()]
        self.assertGreater(len(context_warnings), 0)
    
    def test_performance_impact_assessment(self):
        """Test performance impact assessment"""
        # High impact configuration
        high_impact_config = {
            'reason': 'Emergency system repair',
            'duration': 300,  # 5 hours
            'mode': 'emergency'
        }
        
        result = self.validator.validate_configuration(high_impact_config)
        
        # Should have high impact warning
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        impact_warnings = [msg for msg in warning_messages if 'high impact' in msg.lower()]
        self.assertGreater(len(impact_warnings), 0)
        
        # Low impact configuration
        low_impact_config = {
            'reason': 'Testing maintenance procedures',
            'duration': 15,
            'mode': 'test'
        }
        
        result = self.validator.validate_configuration(low_impact_config)
        
        # Should have low impact info
        info_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.INFO]
        impact_info = [msg for msg in info_messages if 'low impact' in msg.lower()]
        self.assertGreater(len(impact_info), 0)
    
    def test_security_validation(self):
        """Test security validation"""
        config = {
            'reason': 'Security patch for critical vulnerability',
            'duration': 60,
            'mode': 'normal'  # Should suggest emergency mode
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid but with security suggestions
        self.assertTrue(result.is_valid)
        
        # Check for security-related warnings
        warning_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.WARNING]
        security_warnings = [msg for msg in warning_messages if 'security' in msg.lower() and 'emergency' in msg.lower()]
        self.assertGreater(len(security_warnings), 0)
    
    def test_optional_duration(self):
        """Test validation with optional duration"""
        config = {
            'reason': 'Valid maintenance reason',
            'mode': 'normal'
            # No duration specified
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should be valid with info about missing duration
        self.assertTrue(result.is_valid)
        self.assertGreater(result.info_count, 0)
        
        # Check for duration info
        info_messages = [msg.message for msg in result.messages if msg.severity == ValidationSeverity.INFO]
        duration_info = [msg for msg in info_messages if 'duration' in msg.lower()]
        self.assertGreater(len(duration_info), 0)
    
    def test_validation_statistics(self):
        """Test validation statistics tracking"""
        # Reset statistics
        self.validator.reset_statistics()
        
        # Perform some validations
        valid_config = {
            'reason': 'Valid maintenance reason',
            'duration': 60,
            'mode': 'normal'
        }
        
        invalid_config = {
            'reason': '',  # Invalid
            'duration': 60,
            'mode': 'normal'
        }
        
        # Valid validation
        result1 = self.validator.validate_configuration(valid_config)
        self.assertTrue(result1.is_valid)
        
        # Invalid validation
        result2 = self.validator.validate_configuration(invalid_config)
        self.assertFalse(result2.is_valid)
        
        # Check statistics
        stats = self.validator.get_validation_statistics()
        self.assertEqual(stats['total_validations'], 2)
        self.assertEqual(stats['successful_validations'], 1)
        self.assertEqual(stats['failed_validations'], 1)
        self.assertGreater(stats['errors_generated'], 0)
    
    def test_validation_rules_summary(self):
        """Test validation rules summary"""
        rules = self.validator.get_validation_rules_summary()
        
        # Check structure
        self.assertIn('reason_constraints', rules)
        self.assertIn('duration_constraints', rules)
        self.assertIn('mode_constraints', rules)
        self.assertIn('validation_features', rules)
        
        # Check reason constraints
        reason_constraints = rules['reason_constraints']
        self.assertIn('min_length', reason_constraints)
        self.assertIn('max_length', reason_constraints)
        self.assertIn('required', reason_constraints)
        self.assertTrue(reason_constraints['required'])
        
        # Check duration constraints
        duration_constraints = rules['duration_constraints']
        self.assertIn('min_minutes', duration_constraints)
        self.assertIn('max_minutes', duration_constraints)
        self.assertFalse(duration_constraints['required'])
        
        # Check mode constraints
        mode_constraints = rules['mode_constraints']
        self.assertIn('valid_modes', mode_constraints)
        self.assertIn('default', mode_constraints)
        self.assertEqual(mode_constraints['default'], 'normal')
    
    def test_error_handling(self):
        """Test error handling in validation"""
        # Test with invalid input type
        invalid_input = "not a dictionary"
        
        # Should not crash and return error result
        result = self.validator.validate_configuration(invalid_input)
        self.assertIsInstance(result, ValidationResult)
        # The validator should handle this gracefully
    
    def test_validated_config_structure(self):
        """Test validated configuration structure"""
        config = {
            'reason': '  Valid maintenance reason  ',  # With whitespace
            'duration': '60',  # String that should be converted
            'mode': 'NORMAL'  # Uppercase that should be normalized
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.validated_config)
        
        validated = result.validated_config
        
        # Check normalization
        self.assertEqual(validated['reason'], 'Valid maintenance reason')  # Trimmed
        self.assertEqual(validated['duration'], 60)  # Converted to int
        self.assertEqual(validated['mode'], 'normal')  # Lowercase
        
        # Check metadata
        self.assertIn('_validated_at', validated)
        self.assertIn('_validator_version', validated)


if __name__ == '__main__':
    unittest.main()