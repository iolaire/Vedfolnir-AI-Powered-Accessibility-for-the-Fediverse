# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for AlertThresholdValidator

Tests the comprehensive validation system for alert threshold configurations
including range validation, consistency checks, and safety mechanisms.
"""

import unittest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.alerts.components.alert_threshold_validator import (
    AlertThresholdValidator, ValidationResult, ValidationIssue, ValidationSeverity
)
from app.services.alerts.components.alert_manager import AlertThresholds


class TestAlertThresholdValidator(unittest.TestCase):
    """Test cases for AlertThresholdValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = AlertThresholdValidator()
    
    def test_validator_initialization(self):
        """Test validator initialization"""
        self.assertIsNotNone(self.validator)
        self.assertEqual(len(self.validator._validation_history), 0)
        self.assertEqual(self.validator._stats['validations_performed'], 0)
    
    def test_validation_rules_configuration(self):
        """Test validation rules are properly configured"""
        rules = AlertThresholdValidator.VALIDATION_RULES
        
        # Verify all expected threshold fields have rules
        expected_fields = [
            'job_failure_rate',
            'repeated_failure_count',
            'resource_usage_threshold',
            'queue_backup_threshold',
            'ai_service_timeout',
            'performance_degradation_threshold'
        ]
        
        for field in expected_fields:
            self.assertIn(field, rules)
            rule = rules[field]
            
            # Verify required rule properties
            self.assertIn('min', rule)
            self.assertIn('max', rule)
            self.assertIn('recommended_min', rule)
            self.assertIn('recommended_max', rule)
            self.assertIn('optimal', rule)
            self.assertIn('description', rule)
            
            # Verify logical rule consistency
            self.assertLessEqual(rule['min'], rule['recommended_min'])
            self.assertLessEqual(rule['recommended_min'], rule['optimal'])
            self.assertLessEqual(rule['optimal'], rule['recommended_max'])
            self.assertLessEqual(rule['recommended_max'], rule['max'])
    
    def test_validate_valid_thresholds(self):
        """Test validation of valid threshold configuration"""
        # Create valid thresholds
        thresholds = AlertThresholds(
            job_failure_rate=0.1,
            repeated_failure_count=3,
            resource_usage_threshold=0.9,
            queue_backup_threshold=100,
            ai_service_timeout=30,
            performance_degradation_threshold=2.0
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Verify validation passed
        self.assertTrue(result.is_valid)
        self.assertFalse(result.has_errors())
        self.assertEqual(len(result.get_error_messages()), 0)
        
        # Verify statistics updated
        self.assertEqual(self.validator._stats['validations_performed'], 1)
        self.assertEqual(self.validator._stats['validations_passed'], 1)
        self.assertEqual(self.validator._stats['validations_failed'], 0)
    
    def test_validate_invalid_thresholds(self):
        """Test validation of invalid threshold configuration"""
        # Create invalid thresholds
        thresholds = AlertThresholds(
            job_failure_rate=1.5,  # Invalid: > 1.0
            repeated_failure_count=0,  # Invalid: < 1
            resource_usage_threshold=-0.1,  # Invalid: < 0.0
            queue_backup_threshold=0,  # Invalid: < 1
            ai_service_timeout=0,  # Invalid: < 1
            performance_degradation_threshold=0.5  # Invalid: < 1.0
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Verify validation failed
        self.assertFalse(result.is_valid)
        self.assertTrue(result.has_errors())
        self.assertGreater(len(result.get_error_messages()), 0)
        
        # Verify all invalid fields are reported
        error_messages = result.get_error_messages()
        self.assertTrue(any('job_failure_rate' in msg for msg in error_messages))
        self.assertTrue(any('repeated_failure_count' in msg for msg in error_messages))
        self.assertTrue(any('resource_usage_threshold' in msg for msg in error_messages))
        self.assertTrue(any('queue_backup_threshold' in msg for msg in error_messages))
        self.assertTrue(any('ai_service_timeout' in msg for msg in error_messages))
        self.assertTrue(any('performance_degradation_threshold' in msg for msg in error_messages))
        
        # Verify statistics updated
        self.assertEqual(self.validator._stats['validations_performed'], 1)
        self.assertEqual(self.validator._stats['validations_passed'], 0)
        self.assertEqual(self.validator._stats['validations_failed'], 1)
        self.assertGreater(self.validator._stats['errors_detected'], 0)
    
    def test_validate_thresholds_with_warnings(self):
        """Test validation with warning conditions"""
        # Create thresholds that trigger warnings
        thresholds = AlertThresholds(
            job_failure_rate=0.005,  # Very low - may cause alert spam
            repeated_failure_count=25,  # Very high - may delay alerts
            resource_usage_threshold=0.98,  # Very high with low failure rate
            queue_backup_threshold=5,  # Very low - may cause false positives
            ai_service_timeout=300,  # High but valid
            performance_degradation_threshold=8.0  # High but valid
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Verify validation passed but has warnings
        self.assertTrue(result.is_valid)
        self.assertTrue(result.has_warnings())
        self.assertGreater(len(result.get_warning_messages()), 0)
        
        # Verify recommendations are provided
        self.assertGreater(len(result.recommendations), 0)
    
    def test_validate_individual_threshold_valid(self):
        """Test validation of individual valid threshold"""
        # Test valid job failure rate
        issues = self.validator.validate_individual_threshold('job_failure_rate', 0.1)
        
        # Should have no issues
        self.assertEqual(len(issues), 0)
    
    def test_validate_individual_threshold_invalid_range(self):
        """Test validation of individual threshold with invalid range"""
        # Test invalid job failure rate (too high)
        issues = self.validator.validate_individual_threshold('job_failure_rate', 1.5)
        
        # Should have error
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.ERROR)
        self.assertIn('outside valid range', issues[0].message)
    
    def test_validate_individual_threshold_invalid_type(self):
        """Test validation of individual threshold with invalid type"""
        # Test invalid type for job failure rate
        issues = self.validator.validate_individual_threshold('job_failure_rate', "invalid")
        
        # Should have error
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.ERROR)
        self.assertIn('Invalid type', issues[0].message)
    
    def test_validate_individual_threshold_outside_recommended(self):
        """Test validation of individual threshold outside recommended range"""
        # Test job failure rate outside recommended range but within valid range
        issues = self.validator.validate_individual_threshold('job_failure_rate', 0.6)
        
        # Should have warning
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.WARNING)
        self.assertIn('outside recommended range', issues[0].message)
    
    def test_validate_individual_threshold_unknown_field(self):
        """Test validation of unknown threshold field"""
        # Test unknown field
        issues = self.validator.validate_individual_threshold('unknown_field', 0.5)
        
        # Should have error
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.ERROR)
        self.assertIn('Unknown threshold field', issues[0].message)
    
    def test_threshold_consistency_validation(self):
        """Test logical consistency validation between thresholds"""
        # Create thresholds with consistency issues
        thresholds = AlertThresholds(
            job_failure_rate=0.01,  # Very low
            repeated_failure_count=15,  # High
            resource_usage_threshold=0.98,  # Very high
            queue_backup_threshold=2000,  # Very large
            ai_service_timeout=5,  # Very short
            performance_degradation_threshold=8.0  # High
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Should be valid but have warnings about consistency
        self.assertTrue(result.is_valid)
        self.assertTrue(result.has_warnings())
        
        warning_messages = result.get_warning_messages()
        
        # Check for specific consistency warnings
        self.assertTrue(any('missed alerts' in msg for msg in warning_messages))
        self.assertTrue(any('delay critical alert' in msg for msg in warning_messages))
    
    def test_performance_impact_warnings(self):
        """Test performance impact warning generation"""
        # Create thresholds that may impact performance
        thresholds = AlertThresholds(
            job_failure_rate=0.005,  # Very low - may cause spam
            repeated_failure_count=3,
            resource_usage_threshold=0.6,  # Low - may cause frequent alerts
            queue_backup_threshold=5,  # Very low - may cause false positives
            ai_service_timeout=30,
            performance_degradation_threshold=2.0
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Should have performance-related warnings
        self.assertTrue(result.has_warnings())
        
        warning_messages = result.get_warning_messages()
        self.assertTrue(any('excessive alerts' in msg or 'frequent alerts' in msg or 'false positive' in msg 
                          for msg in warning_messages))
    
    def test_security_implications_warnings(self):
        """Test security implications warning generation"""
        # Create thresholds with potential security implications
        thresholds = AlertThresholds(
            job_failure_rate=0.4,  # High - may miss security issues
            repeated_failure_count=25,  # Very high - may delay attack detection
            resource_usage_threshold=0.9,
            queue_backup_threshold=100,
            ai_service_timeout=30,
            performance_degradation_threshold=2.0
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Should have security-related warnings
        self.assertTrue(result.has_warnings())
        
        warning_messages = result.get_warning_messages()
        self.assertTrue(any('security' in msg.lower() or 'attack' in msg.lower() 
                          for msg in warning_messages))
    
    def test_recommendation_generation(self):
        """Test recommendation generation"""
        # Create thresholds that need recommendations
        thresholds = AlertThresholds(
            job_failure_rate=0.2,  # Not optimal
            repeated_failure_count=5,  # Not optimal
            resource_usage_threshold=0.8,  # Not optimal
            queue_backup_threshold=200,  # Not optimal
            ai_service_timeout=60,  # Not optimal
            performance_degradation_threshold=3.0  # Not optimal
        )
        
        # Validate thresholds
        result = self.validator.validate_thresholds(thresholds)
        
        # Should have recommendations
        self.assertGreater(len(result.recommendations), 0)
        
        # Check for specific recommendations
        recommendations = result.recommendations
        self.assertTrue(any('0.1' in rec and 'job failure rate' in rec for rec in recommendations))
        self.assertTrue(any('0.9' in rec and 'resource usage' in rec for rec in recommendations))
        self.assertTrue(any('30 seconds' in rec and 'AI service timeout' in rec for rec in recommendations))
    
    def test_get_safe_fallback_thresholds(self):
        """Test safe fallback threshold generation"""
        # Get safe fallback thresholds
        safe_thresholds = self.validator.get_safe_fallback_thresholds()
        
        # Verify they are valid
        result = self.validator.validate_thresholds(safe_thresholds)
        self.assertTrue(result.is_valid)
        
        # Verify they match expected safe values
        self.assertEqual(safe_thresholds.job_failure_rate, 0.1)
        self.assertEqual(safe_thresholds.repeated_failure_count, 3)
        self.assertEqual(safe_thresholds.resource_usage_threshold, 0.9)
        self.assertEqual(safe_thresholds.queue_backup_threshold, 100)
        self.assertEqual(safe_thresholds.ai_service_timeout, 30)
        self.assertEqual(safe_thresholds.performance_degradation_threshold, 2.0)
    
    def test_validation_statistics(self):
        """Test validation statistics tracking"""
        # Perform multiple validations
        valid_thresholds = AlertThresholds()
        invalid_thresholds = AlertThresholds(job_failure_rate=2.0)
        
        # Validate multiple times
        self.validator.validate_thresholds(valid_thresholds)
        self.validator.validate_thresholds(invalid_thresholds)
        self.validator.validate_thresholds(valid_thresholds)
        
        # Get statistics
        stats = self.validator.get_validation_statistics()
        
        # Verify statistics
        self.assertEqual(stats['statistics']['validations_performed'], 3)
        self.assertEqual(stats['statistics']['validations_passed'], 2)
        self.assertEqual(stats['statistics']['validations_failed'], 1)
        self.assertGreater(stats['statistics']['errors_detected'], 0)
        self.assertEqual(stats['validation_history_count'], 3)
        self.assertGreater(stats['recent_validation_success_rate'], 0.5)
    
    def test_validation_history_management(self):
        """Test validation history management"""
        # Perform validation
        thresholds = AlertThresholds()
        result = self.validator.validate_thresholds(thresholds)
        
        # Verify history is stored
        self.assertEqual(len(self.validator._validation_history), 1)
        self.assertEqual(self.validator._validation_history[0], result)
        
        # Clear history
        self.validator.clear_validation_history()
        self.assertEqual(len(self.validator._validation_history), 0)
    
    def test_validation_result_methods(self):
        """Test ValidationResult helper methods"""
        # Create validation result with errors and warnings
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, 'field1', 'Error message', 1.0),
            ValidationIssue(ValidationSeverity.WARNING, 'field2', 'Warning message', 2.0)
        ]
        warnings = [
            ValidationIssue(ValidationSeverity.WARNING, 'field3', 'Another warning', 3.0)
        ]
        
        result = ValidationResult(
            is_valid=False,
            issues=issues,
            warnings=warnings,
            recommendations=['Recommendation 1']
        )
        
        # Test helper methods
        self.assertTrue(result.has_errors())
        self.assertTrue(result.has_warnings())
        
        error_messages = result.get_error_messages()
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(error_messages[0], 'Error message')
        
        warning_messages = result.get_warning_messages()
        self.assertEqual(len(warning_messages), 2)
        self.assertIn('Warning message', warning_messages)
        self.assertIn('Another warning', warning_messages)
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        # Create invalid thresholds object that might cause exceptions
        class InvalidThresholds:
            def __getattribute__(self, name):
                if name in ['job_failure_rate', 'repeated_failure_count']:
                    raise AttributeError(f"No attribute {name}")
                return super().__getattribute__(name)
        
        invalid_thresholds = InvalidThresholds()
        
        # Validate should handle errors gracefully
        result = self.validator.validate_thresholds(invalid_thresholds)
        
        # Should return invalid result with error message
        self.assertFalse(result.is_valid)
        self.assertTrue(result.has_errors())
        error_messages = result.get_error_messages()
        self.assertTrue(any('Validation error' in msg for msg in error_messages))


if __name__ == '__main__':
    unittest.main()