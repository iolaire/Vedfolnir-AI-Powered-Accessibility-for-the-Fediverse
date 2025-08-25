# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Performance Configuration Validator

Tests validation for performance-related configuration values with
safe fallback mechanisms and warning system for problematic configurations.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from performance_configuration_validator import (
    PerformanceConfigurationValidator,
    ValidationResult,
    ValidationSeverity,
    SystemResources
)


class TestPerformanceConfigurationValidator(unittest.TestCase):
    """Test PerformanceConfigurationValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock system resources to have consistent test results
        with patch.object(PerformanceConfigurationValidator, '_get_system_resources') as mock_get_resources:
            mock_get_resources.return_value = SystemResources(
                total_memory_mb=8192,  # 8GB
                available_memory_mb=6144,  # 6GB available
                cpu_count=4,
                cpu_usage_percent=25.0
            )
            self.validator = PerformanceConfigurationValidator()
    
    def test_initialization(self):
        """Test validator initialization"""
        self.assertIsNotNone(self.validator)
        self.assertEqual(self.validator._system_resources.total_memory_mb, 8192)
        self.assertEqual(self.validator._system_resources.available_memory_mb, 6144)
        self.assertIn('max_memory_usage_mb', self.validator.SAFE_FALLBACKS)
        self.assertIn('processing_priority_weights', self.validator.SAFE_FALLBACKS)
    
    def test_validate_memory_configuration_valid(self):
        """Test memory configuration validation with valid values"""
        results = self.validator.validate_memory_configuration(2048, 3)
        
        # Should have no errors for reasonable values
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertEqual(len(error_results), 0)
    
    def test_validate_memory_configuration_invalid_type(self):
        """Test memory configuration validation with invalid type"""
        results = self.validator.validate_memory_configuration("invalid", 3)
        
        # Should have error for invalid type
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertGreater(len(error_results), 0)
        self.assertIn("must be a number", error_results[0].message)
    
    def test_validate_memory_configuration_below_minimum(self):
        """Test memory configuration validation below minimum"""
        results = self.validator.validate_memory_configuration(256, 3)  # Below 512MB minimum
        
        # Should have error for value below minimum
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertGreater(len(error_results), 0)
        self.assertIn("below minimum", error_results[0].message)
        self.assertEqual(error_results[0].suggested_value, 512)
    
    def test_validate_memory_configuration_above_maximum(self):
        """Test memory configuration validation above maximum"""
        results = self.validator.validate_memory_configuration(20480, 3)  # Above 16GB maximum
        
        # Should have warning for very high value
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        self.assertGreater(len(warning_results), 0)
        self.assertIn("very high", warning_results[0].message)
    
    def test_validate_memory_configuration_exceeds_system_memory(self):
        """Test memory configuration that exceeds system memory"""
        # 4GB per job * 3 jobs = 12GB total, but system only has 8GB
        results = self.validator.validate_memory_configuration(4096, 3)
        
        # Should have critical error for exceeding available memory
        critical_results = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        self.assertGreater(len(critical_results), 0)
        self.assertIn("exceeds currently available memory", critical_results[0].message)
    
    def test_validate_memory_configuration_exceeds_safe_limit(self):
        """Test memory configuration that exceeds safe system limit"""
        # 3GB per job * 3 jobs = 9GB total, exceeds 80% of 8GB (6.4GB)
        results = self.validator.validate_memory_configuration(3072, 3)
        
        # Should have warning for exceeding safe limit
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        warning_messages = [r.message for r in warning_results]
        self.assertTrue(any("may exceed safe system limits" in msg for msg in warning_messages))
    
    def test_validate_priority_weights_valid(self):
        """Test priority weights validation with valid values"""
        valid_weights = {
            "urgent": 4.0,
            "high": 3.0,
            "normal": 2.0,
            "low": 1.0
        }
        
        results = self.validator.validate_priority_weights(valid_weights)
        
        # Should have no errors for valid weights
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertEqual(len(error_results), 0)
    
    def test_validate_priority_weights_invalid_type(self):
        """Test priority weights validation with invalid type"""
        results = self.validator.validate_priority_weights("invalid")
        
        # Should have error for invalid type
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertGreater(len(error_results), 0)
        self.assertIn("must be a dictionary", error_results[0].message)
    
    def test_validate_priority_weights_missing_keys(self):
        """Test priority weights validation with missing keys"""
        incomplete_weights = {
            "urgent": 4.0,
            "high": 3.0
            # Missing normal and low
        }
        
        results = self.validator.validate_priority_weights(incomplete_weights)
        
        # Should have error for missing keys
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertGreater(len(error_results), 0)
        self.assertIn("Missing required priority weight keys", error_results[0].message)
    
    def test_validate_priority_weights_invalid_values(self):
        """Test priority weights validation with invalid values"""
        invalid_weights = {
            "urgent": "not_a_number",
            "high": 3.0,
            "normal": 2.0,
            "low": 1.0
        }
        
        results = self.validator.validate_priority_weights(invalid_weights)
        
        # Should have error for invalid value
        error_results = [r for r in results if r.severity == ValidationSeverity.ERROR]
        self.assertGreater(len(error_results), 0)
        self.assertTrue(any("must be a number" in r.message for r in error_results))
    
    def test_validate_priority_weights_below_minimum(self):
        """Test priority weights validation with values below minimum"""
        low_weights = {
            "urgent": 4.0,
            "high": 3.0,
            "normal": 2.0,
            "low": 0.05  # Below minimum of 0.1
        }
        
        results = self.validator.validate_priority_weights(low_weights)
        
        # Should have warning for value below minimum
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        self.assertGreater(len(warning_results), 0)
        self.assertTrue(any("below minimum" in r.message for r in warning_results))
    
    def test_validate_priority_weights_above_maximum(self):
        """Test priority weights validation with values above maximum"""
        high_weights = {
            "urgent": 15.0,  # Above maximum of 10.0
            "high": 3.0,
            "normal": 2.0,
            "low": 1.0
        }
        
        results = self.validator.validate_priority_weights(high_weights)
        
        # Should have warning for value above maximum
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        self.assertGreater(len(warning_results), 0)
        self.assertTrue(any("above maximum" in r.message for r in warning_results))
    
    def test_validate_priority_weights_wrong_order(self):
        """Test priority weights validation with wrong ordering"""
        wrong_order_weights = {
            "urgent": 1.0,  # Should be highest
            "high": 4.0,    # Higher than urgent (wrong)
            "normal": 2.0,
            "low": 3.0      # Higher than normal (wrong)
        }
        
        results = self.validator.validate_priority_weights(wrong_order_weights)
        
        # Should have warning for wrong ordering
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        self.assertGreater(len(warning_results), 0)
        self.assertTrue(any("ordering issue" in r.message for r in warning_results))
    
    def test_validate_priority_weights_extreme_ratio(self):
        """Test priority weights validation with extreme ratios"""
        extreme_weights = {
            "urgent": 100.0,  # Very high
            "high": 3.0,
            "normal": 2.0,
            "low": 0.1       # Very low - ratio is 1000:1
        }
        
        results = self.validator.validate_priority_weights(extreme_weights)
        
        # Should have warning for extreme ratio
        warning_results = [r for r in results if r.severity == ValidationSeverity.WARNING]
        warning_messages = [r.message for r in warning_results]
        self.assertTrue(any("Large priority weight ratio" in msg for msg in warning_messages))
    
    def test_validate_performance_configuration_complete(self):
        """Test complete performance configuration validation"""
        config = {
            "max_memory_usage_mb": 2048,
            "max_concurrent_jobs": 3,
            "processing_priority_weights": {
                "urgent": 4.0,
                "high": 3.0,
                "normal": 2.0,
                "low": 1.0
            }
        }
        
        results = self.validator.validate_performance_configuration(config)
        
        # Should validate both memory and priority weights
        self.assertIsInstance(results, list)
        
        # Should not have critical errors for reasonable config
        critical_results = [r for r in results if r.severity == ValidationSeverity.CRITICAL]
        self.assertEqual(len(critical_results), 0)
    
    def test_validate_cross_configuration_impacts(self):
        """Test cross-configuration impact validation"""
        config = {
            "max_memory_usage_mb": 4096,  # 4GB per job
            "max_concurrent_jobs": 3,     # 3 jobs = 12GB total
            "queue_size_limit": 2         # Very small queue
        }
        
        results = self.validator._validate_cross_configuration_impacts(config)
        
        # Should detect memory impact and small queue issues
        self.assertGreater(len(results), 0)
        
        # Check for memory-related warnings
        memory_warnings = [r for r in results if "memory" in r.message.lower()]
        self.assertGreater(len(memory_warnings), 0)
    
    def test_get_safe_fallback_value(self):
        """Test getting safe fallback values"""
        memory_fallback = self.validator.get_safe_fallback_value("max_memory_usage_mb")
        self.assertEqual(memory_fallback, 2048)
        
        priority_fallback = self.validator.get_safe_fallback_value("processing_priority_weights")
        self.assertIsInstance(priority_fallback, dict)
        self.assertIn("urgent", priority_fallback)
        
        # Test non-existent key
        unknown_fallback = self.validator.get_safe_fallback_value("unknown_key")
        self.assertIsNone(unknown_fallback)
    
    def test_assess_configuration_impact(self):
        """Test configuration impact assessment"""
        config = {
            "max_memory_usage_mb": 2048,
            "max_concurrent_jobs": 3,
            "processing_priority_weights": {
                "urgent": 4.0,
                "high": 3.0,
                "normal": 2.0,
                "low": 1.0
            }
        }
        
        impact = self.validator.assess_configuration_impact(config)
        
        self.assertIn('system_resource_usage', impact)
        self.assertIn('performance_implications', impact)
        self.assertIn('stability_risks', impact)
        self.assertIn('recommendations', impact)
        
        # Check memory usage calculation
        if 'memory' in impact['system_resource_usage']:
            memory_info = impact['system_resource_usage']['memory']
            self.assertEqual(memory_info['total_allocation_mb'], 6144)  # 2048 * 3
    
    def test_assess_configuration_impact_high_memory(self):
        """Test configuration impact assessment with high memory usage"""
        config = {
            "max_memory_usage_mb": 3072,  # 3GB per job
            "max_concurrent_jobs": 3      # 9GB total (> 80% of 8GB system)
        }
        
        impact = self.validator.assess_configuration_impact(config)
        
        # Should detect high memory usage
        self.assertGreater(len(impact['performance_implications']), 0)
        
        # Check if stability risks are identified
        memory_usage_percent = (9216 / 8192) * 100  # Should be > 100%
        if memory_usage_percent > 80:
            self.assertGreater(len(impact['stability_risks']), 0)
    
    def test_get_system_resource_info(self):
        """Test getting system resource information"""
        # Mock the _get_system_resources method to return consistent values
        with patch.object(self.validator, '_get_system_resources') as mock_get_resources:
            mock_get_resources.return_value = SystemResources(
                total_memory_mb=8192,
                available_memory_mb=6144,
                cpu_count=4,
                cpu_usage_percent=25.0
            )
            
            info = self.validator.get_system_resource_info()
            
            self.assertIn('memory', info)
            self.assertIn('cpu', info)
            self.assertIn('recommendations', info)
            
            # Check memory info
            memory_info = info['memory']
            self.assertEqual(memory_info['total_mb'], 8192)
            self.assertEqual(memory_info['available_mb'], 6144)
            self.assertIn('usage_percent', memory_info)
            
            # Check CPU info
            cpu_info = info['cpu']
            self.assertEqual(cpu_info['count'], 4)
            self.assertEqual(cpu_info['usage_percent'], 25.0)
            
            # Check recommendations
            recommendations = info['recommendations']
            self.assertIn('safe_memory_limit_mb', recommendations)
            self.assertIn('max_concurrent_jobs_for_2gb_per_job', recommendations)


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult data class"""
    
    def test_validation_result_creation(self):
        """Test creating ValidationResult"""
        result = ValidationResult(
            key="test_key",
            severity=ValidationSeverity.WARNING,
            message="Test message",
            current_value=1024,
            suggested_value=2048,
            impact_description="Test impact"
        )
        
        self.assertEqual(result.key, "test_key")
        self.assertEqual(result.severity, ValidationSeverity.WARNING)
        self.assertEqual(result.message, "Test message")
        self.assertEqual(result.current_value, 1024)
        self.assertEqual(result.suggested_value, 2048)
        self.assertEqual(result.impact_description, "Test impact")
    
    def test_validation_result_minimal(self):
        """Test creating ValidationResult with minimal parameters"""
        result = ValidationResult(
            key="test_key",
            severity=ValidationSeverity.ERROR,
            message="Test error",
            current_value="invalid"
        )
        
        self.assertEqual(result.key, "test_key")
        self.assertEqual(result.severity, ValidationSeverity.ERROR)
        self.assertEqual(result.message, "Test error")
        self.assertEqual(result.current_value, "invalid")
        self.assertIsNone(result.suggested_value)
        self.assertIsNone(result.impact_description)


class TestSystemResources(unittest.TestCase):
    """Test SystemResources data class"""
    
    def test_system_resources_creation(self):
        """Test creating SystemResources"""
        resources = SystemResources(
            total_memory_mb=8192,
            available_memory_mb=6144,
            cpu_count=4,
            cpu_usage_percent=25.0
        )
        
        self.assertEqual(resources.total_memory_mb, 8192)
        self.assertEqual(resources.available_memory_mb, 6144)
        self.assertEqual(resources.cpu_count, 4)
        self.assertEqual(resources.cpu_usage_percent, 25.0)


if __name__ == '__main__':
    unittest.main()