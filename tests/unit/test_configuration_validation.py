# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for ConfigurationValidator
"""

import unittest
import os
import sys
import threading
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from configuration_validation import (
    ConfigurationValidator, ValidationRule, ValidationResult, ValidationIssue,
    ConflictDetection, ImpactAssessment, RestartRequirement,
    ValidationSeverity, ImpactLevel, ConflictType,
    get_validator, set_validator
)


class TestConfigurationValidator(unittest.TestCase):
    """Test cases for ConfigurationValidator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ConfigurationValidator()
    
    def tearDown(self):
        """Clean up after tests"""
        pass
    
    def test_validation_rule_creation(self):
        """Test validation rule creation and addition"""
        def test_validator(value):
            return isinstance(value, int) and value > 0
        
        rule = ValidationRule(
            rule_type="positive_integer",
            description="Must be a positive integer",
            validator=test_validator,
            error_message="Value must be a positive integer",
            severity=ValidationSeverity.ERROR
        )
        
        # Add rule to validator
        self.validator.add_validation_rule("test_key", rule)
        
        # Test valid value
        result = self.validator.validate_value("test_key", 5)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
        
        # Test invalid value
        result = self.validator.validate_value("test_key", -1)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].rule_type, "positive_integer")
        self.assertEqual(result.issues[0].severity, ValidationSeverity.ERROR)
    
    def test_builtin_validation_rules(self):
        """Test built-in validation rules"""
        # Test max_concurrent_jobs validation
        result = self.validator.validate_value("max_concurrent_jobs", 50)
        self.assertTrue(result.is_valid)
        
        result = self.validator.validate_value("max_concurrent_jobs", 0)
        self.assertFalse(result.is_valid)
        
        result = self.validator.validate_value("max_concurrent_jobs", 150)
        self.assertFalse(result.is_valid)
        
        # Test session_timeout_minutes validation
        result = self.validator.validate_value("session_timeout_minutes", 60)
        self.assertTrue(result.is_valid)
        
        result = self.validator.validate_value("session_timeout_minutes", 5)
        self.assertFalse(result.is_valid)
        
        result = self.validator.validate_value("session_timeout_minutes", 2000)
        self.assertFalse(result.is_valid)
        
        # Test alert_error_rate_threshold validation
        result = self.validator.validate_value("alert_error_rate_threshold", 0.5)
        self.assertTrue(result.is_valid)
        
        result = self.validator.validate_value("alert_error_rate_threshold", -0.1)
        self.assertFalse(result.is_valid)
        
        result = self.validator.validate_value("alert_error_rate_threshold", 1.5)
        self.assertFalse(result.is_valid)
    
    def test_configuration_set_validation(self):
        """Test validation of configuration sets"""
        configs = {
            "max_concurrent_jobs": 10,
            "session_timeout_minutes": 120,
            "alert_error_rate_threshold": 0.1,
            "unknown_key": "some_value"
        }
        
        results = self.validator.validate_configuration_set(configs)
        
        # Verify results for each key
        self.assertTrue(results["max_concurrent_jobs"].is_valid)
        self.assertTrue(results["session_timeout_minutes"].is_valid)
        self.assertTrue(results["alert_error_rate_threshold"].is_valid)
        self.assertTrue(results["unknown_key"].is_valid)  # No rules for unknown key
        
        # Test with invalid values
        invalid_configs = {
            "max_concurrent_jobs": 0,
            "session_timeout_minutes": 5,
            "alert_error_rate_threshold": 2.0
        }
        
        results = self.validator.validate_configuration_set(invalid_configs)
        
        self.assertFalse(results["max_concurrent_jobs"].is_valid)
        self.assertFalse(results["session_timeout_minutes"].is_valid)
        self.assertFalse(results["alert_error_rate_threshold"].is_valid)
    
    def test_conflict_detection(self):
        """Test configuration conflict detection"""
        # Test max_concurrent_jobs vs queue_size_limit conflict
        configs = {
            "max_concurrent_jobs": 20,
            "queue_size_limit": 10
        }
        
        conflicts = self.validator.detect_conflicts(configs)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_type, ConflictType.LOGICAL_CONFLICT)
        self.assertIn("max_concurrent_jobs", conflicts[0].keys)
        self.assertIn("queue_size_limit", conflicts[0].keys)
        self.assertEqual(conflicts[0].severity, ValidationSeverity.ERROR)
        
        # Test memory vs job limits warning
        configs = {
            "max_memory_usage_mb": 2048,
            "max_concurrent_jobs": 10
        }
        
        conflicts = self.validator.detect_conflicts(configs)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_type, ConflictType.RANGE_CONFLICT)
        self.assertEqual(conflicts[0].severity, ValidationSeverity.WARNING)
        
        # Test no conflicts
        configs = {
            "max_concurrent_jobs": 10,
            "queue_size_limit": 50
        }
        
        conflicts = self.validator.detect_conflicts(configs)
        self.assertEqual(len(conflicts), 0)
    
    def test_custom_conflict_detection(self):
        """Test custom conflict detection rules"""
        def custom_conflict_detector(configs):
            conflicts = []
            if configs.get("key1") == "value1" and configs.get("key2") == "value2":
                conflicts.append(ConflictDetection(
                    conflict_type=ConflictType.VALUE_CONFLICT,
                    keys=["key1", "key2"],
                    description="key1 and key2 cannot both have these values",
                    severity=ValidationSeverity.ERROR
                ))
            return conflicts
        
        self.validator.add_conflict_rule(custom_conflict_detector)
        
        # Test conflict
        configs = {"key1": "value1", "key2": "value2"}
        conflicts = self.validator.detect_conflicts(configs)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].conflict_type, ConflictType.VALUE_CONFLICT)
        
        # Test no conflict
        configs = {"key1": "value1", "key2": "other_value"}
        conflicts = self.validator.detect_conflicts(configs)
        
        # Should only have the custom conflict, not the built-in ones
        custom_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.VALUE_CONFLICT]
        self.assertEqual(len(custom_conflicts), 0)
    
    def test_impact_assessment(self):
        """Test configuration change impact assessment"""
        # Test max_concurrent_jobs impact
        impact = self.validator.assess_change_impact("max_concurrent_jobs", 10, 5)
        
        self.assertEqual(impact.key, "max_concurrent_jobs")
        self.assertEqual(impact.old_value, 10)
        self.assertEqual(impact.new_value, 5)
        self.assertEqual(impact.impact_level, ImpactLevel.MEDIUM)
        self.assertIn("task_queue", impact.affected_components)
        self.assertFalse(impact.requires_restart)
        
        # Test session_timeout_minutes impact
        impact = self.validator.assess_change_impact("session_timeout_minutes", 120, 60)
        
        self.assertEqual(impact.impact_level, ImpactLevel.MEDIUM)
        self.assertIn("session_manager", impact.affected_components)
        self.assertTrue(impact.requires_restart)
        
        # Test unknown key impact (default assessment)
        impact = self.validator.assess_change_impact("unknown_key", "old", "new")
        
        self.assertEqual(impact.impact_level, ImpactLevel.LOW)
        self.assertIn("unknown", impact.affected_components)
        self.assertFalse(impact.requires_restart)
    
    def test_custom_impact_assessment(self):
        """Test custom impact assessment rules"""
        def custom_impact_assessor(key, old_value, new_value):
            return ImpactAssessment(
                key=key,
                old_value=old_value,
                new_value=new_value,
                impact_level=ImpactLevel.CRITICAL,
                affected_components=["custom_component"],
                requires_restart=True,
                risk_factors=["Custom risk"],
                mitigation_steps=["Custom mitigation"]
            )
        
        self.validator.add_impact_rule("custom_key", custom_impact_assessor)
        
        impact = self.validator.assess_change_impact("custom_key", "old", "new")
        
        self.assertEqual(impact.impact_level, ImpactLevel.CRITICAL)
        self.assertIn("custom_component", impact.affected_components)
        self.assertTrue(impact.requires_restart)
        self.assertIn("Custom risk", impact.risk_factors)
        self.assertIn("Custom mitigation", impact.mitigation_steps)
    
    def test_restart_requirement_tracking(self):
        """Test restart requirement tracking"""
        # Initially no restart requirements
        requirements = self.validator.get_restart_requirements()
        self.assertEqual(len(requirements), 0)
        
        # Add restart requirement
        self.validator.add_restart_requirement(
            key="test_key",
            reason="Configuration change requires restart",
            component="test_component",
            priority="high",
            estimated_time="30 seconds",
            dependencies=["dependency1", "dependency2"]
        )
        
        # Verify requirement was added
        requirements = self.validator.get_restart_requirements()
        self.assertEqual(len(requirements), 1)
        
        req = requirements[0]
        self.assertEqual(req.key, "test_key")
        self.assertEqual(req.reason, "Configuration change requires restart")
        self.assertEqual(req.component, "test_component")
        self.assertEqual(req.priority, "high")
        self.assertEqual(req.estimated_restart_time, "30 seconds")
        self.assertEqual(req.dependencies, ["dependency1", "dependency2"])
        self.assertIsInstance(req.added_at, datetime)
        
        # Test filtering by priority
        high_priority = self.validator.get_restart_requirements_by_priority("high")
        self.assertEqual(len(high_priority), 1)
        
        normal_priority = self.validator.get_restart_requirements_by_priority("normal")
        self.assertEqual(len(normal_priority), 0)
        
        # Remove restart requirement
        success = self.validator.remove_restart_requirement("test_key")
        self.assertTrue(success)
        
        requirements = self.validator.get_restart_requirements()
        self.assertEqual(len(requirements), 0)
        
        # Try to remove non-existent requirement
        success = self.validator.remove_restart_requirement("nonexistent_key")
        self.assertFalse(success)
    
    def test_restart_requirement_clearing(self):
        """Test clearing all restart requirements"""
        # Add multiple requirements
        for i in range(3):
            self.validator.add_restart_requirement(
                key=f"key_{i}",
                reason=f"Reason {i}",
                component=f"component_{i}"
            )
        
        # Verify they were added
        requirements = self.validator.get_restart_requirements()
        self.assertEqual(len(requirements), 3)
        
        # Clear all requirements
        self.validator.clear_restart_requirements()
        
        # Verify they were cleared
        requirements = self.validator.get_restart_requirements()
        self.assertEqual(len(requirements), 0)
    
    def test_component_dependencies(self):
        """Test component dependency management"""
        # Add component dependencies
        self.validator.add_component_dependency("component_a", ["component_b", "component_c"])
        self.validator.add_component_dependency("component_b", ["component_d"])
        
        # Test getting affected components
        affected = self.validator.get_affected_components("component_a")
        self.assertIn("component_b", affected)
        self.assertIn("component_c", affected)
        
        # Test reverse dependencies
        affected = self.validator.get_affected_components("component_b")
        self.assertIn("component_a", affected)  # component_a depends on component_b
        self.assertIn("component_d", affected)  # component_b depends on component_d
    
    def test_validation_with_warnings(self):
        """Test validation with warning-level issues"""
        def warning_validator(value):
            return int(value) < 100  # Warning if value >= 100
        
        rule = ValidationRule(
            rule_type="warning_test",
            description="Should be less than 100",
            validator=warning_validator,
            error_message="Value should be less than 100 for optimal performance",
            severity=ValidationSeverity.WARNING
        )
        
        self.validator.add_validation_rule("test_key", rule)
        
        # Test value that triggers warning
        result = self.validator.validate_value("test_key", 150)
        
        self.assertTrue(result.is_valid)  # Still valid despite warning
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("optimal performance", result.warnings[0])
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        def failing_validator(value):
            raise Exception("Validator error")
        
        rule = ValidationRule(
            rule_type="failing_test",
            description="This validator will fail",
            validator=failing_validator,
            error_message="This should not be seen",
            severity=ValidationSeverity.ERROR
        )
        
        self.validator.add_validation_rule("test_key", rule)
        
        # Test validation with failing validator
        result = self.validator.validate_value("test_key", "any_value")
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].rule_type, "validation_error")
        self.assertIn("Validation rule failed", result.issues[0].message)
    
    def test_thread_safety(self):
        """Test thread safety of validator operations"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Add validation rules
                def test_validator(value):
                    return isinstance(value, int) and value > worker_id
                
                rule = ValidationRule(
                    rule_type=f"worker_{worker_id}_test",
                    description=f"Worker {worker_id} test",
                    validator=test_validator,
                    error_message=f"Worker {worker_id} validation failed"
                )
                
                self.validator.add_validation_rule(f"worker_{worker_id}_key", rule)
                
                # Validate values
                for i in range(5):
                    result = self.validator.validate_value(f"worker_{worker_id}_key", i)
                    results.append((worker_id, i, result.is_valid))
                
                # Add restart requirements
                self.validator.add_restart_requirement(
                    key=f"worker_{worker_id}_key",
                    reason=f"Worker {worker_id} restart",
                    component=f"worker_{worker_id}_component"
                )
                
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify results
        self.assertEqual(len(results), 15)  # 3 workers * 5 validations each
        
        # Verify restart requirements were added
        requirements = self.validator.get_restart_requirements()
        self.assertEqual(len(requirements), 3)
    
    def test_global_validator(self):
        """Test global validator singleton"""
        # Get global validator
        validator1 = get_validator()
        validator2 = get_validator()
        
        # Should be the same instance
        self.assertIs(validator1, validator2)
        
        # Set custom validator
        custom_validator = ConfigurationValidator()
        set_validator(custom_validator)
        
        validator3 = get_validator()
        self.assertIs(validator3, custom_validator)
        self.assertIsNot(validator3, validator1)
    
    def test_validation_issue_metadata(self):
        """Test validation issue metadata handling"""
        def test_validator(value):
            return False  # Always fail
        
        rule = ValidationRule(
            rule_type="metadata_test",
            description="Test with metadata",
            validator=test_validator,
            error_message="Test error",
            severity=ValidationSeverity.ERROR,
            metadata={"custom_field": "custom_value", "number": 42}
        )
        
        self.validator.add_validation_rule("test_key", rule)
        
        result = self.validator.validate_value("test_key", "any_value")
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        
        issue = result.issues[0]
        self.assertEqual(issue.metadata["custom_field"], "custom_value")
        self.assertEqual(issue.metadata["number"], 42)


if __name__ == '__main__':
    unittest.main()