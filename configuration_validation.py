# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Validation and Safety Mechanisms

Provides comprehensive validation, conflict detection, restart requirement
tracking, and configuration change impact assessment.
"""

import re
import json
import logging
import threading
from typing import Any, Dict, List, Optional, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import ipaddress
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ImpactLevel(Enum):
    """Configuration change impact levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictType(Enum):
    """Configuration conflict types"""
    VALUE_CONFLICT = "value_conflict"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    RANGE_CONFLICT = "range_conflict"
    TYPE_CONFLICT = "type_conflict"
    LOGICAL_CONFLICT = "logical_conflict"


@dataclass
class ValidationRule:
    """Configuration validation rule"""
    rule_type: str
    description: str
    validator: Callable[[Any], bool]
    error_message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of configuration validation"""
    key: str
    value: Any
    is_valid: bool
    issues: List['ValidationIssue'] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    """Configuration validation issue"""
    rule_type: str
    severity: ValidationSeverity
    message: str
    suggested_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictDetection:
    """Configuration conflict detection result"""
    conflict_type: ConflictType
    keys: List[str]
    description: str
    severity: ValidationSeverity
    resolution_suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactAssessment:
    """Configuration change impact assessment"""
    key: str
    old_value: Any
    new_value: Any
    impact_level: ImpactLevel
    affected_components: List[str]
    requires_restart: bool
    estimated_downtime: Optional[str] = None
    rollback_complexity: str = "low"
    risk_factors: List[str] = field(default_factory=list)
    mitigation_steps: List[str] = field(default_factory=list)


@dataclass
class RestartRequirement:
    """Restart requirement tracking"""
    key: str
    reason: str
    component: str
    priority: str = "normal"  # low, normal, high, critical
    estimated_restart_time: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConfigurationValidator:
    """
    Comprehensive configuration validation and safety system
    
    Features:
    - Schema-based validation with custom rules
    - Conflict detection between related configurations
    - Impact assessment for configuration changes
    - Restart requirement tracking and notification
    - Safety mechanisms and rollback support
    """
    
    def __init__(self):
        """Initialize configuration validator"""
        # Validation rules registry
        self._validation_rules: Dict[str, List[ValidationRule]] = {}
        self._rules_lock = threading.RLock()
        
        # Conflict detection rules
        self._conflict_rules: List[Callable[[Dict[str, Any]], List[ConflictDetection]]] = []
        self._conflict_lock = threading.RLock()
        
        # Restart requirements tracking
        self._restart_requirements: Dict[str, RestartRequirement] = {}
        self._restart_lock = threading.RLock()
        
        # Impact assessment rules
        self._impact_rules: Dict[str, Callable[[str, Any, Any], ImpactAssessment]] = {}
        self._impact_lock = threading.RLock()
        
        # Component dependencies
        self._component_dependencies: Dict[str, List[str]] = {}
        self._dependencies_lock = threading.RLock()
        
        # Initialize built-in validation rules
        self._initialize_builtin_rules()
        self._initialize_builtin_conflicts()
        self._initialize_builtin_impacts()
    
    def add_validation_rule(self, key: str, rule: ValidationRule):
        """
        Add validation rule for a configuration key
        
        Args:
            key: Configuration key
            rule: Validation rule to add
        """
        with self._rules_lock:
            if key not in self._validation_rules:
                self._validation_rules[key] = []
            self._validation_rules[key].append(rule)
        
        logger.debug(f"Added validation rule for key {key}: {rule.rule_type}")
    
    def add_conflict_rule(self, conflict_detector: Callable[[Dict[str, Any]], List[ConflictDetection]]):
        """
        Add conflict detection rule
        
        Args:
            conflict_detector: Function that detects conflicts in configuration set
        """
        with self._conflict_lock:
            self._conflict_rules.append(conflict_detector)
        
        logger.debug("Added conflict detection rule")
    
    def add_impact_rule(self, key: str, impact_assessor: Callable[[str, Any, Any], ImpactAssessment]):
        """
        Add impact assessment rule for a configuration key
        
        Args:
            key: Configuration key
            impact_assessor: Function that assesses impact of changes
        """
        with self._impact_lock:
            self._impact_rules[key] = impact_assessor
        
        logger.debug(f"Added impact assessment rule for key {key}")
    
    def validate_value(self, key: str, value: Any) -> ValidationResult:
        """
        Validate a single configuration value
        
        Args:
            key: Configuration key
            value: Value to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(key=key, value=value, is_valid=True)
        
        with self._rules_lock:
            rules = self._validation_rules.get(key, [])
        
        for rule in rules:
            try:
                if not rule.validator(value):
                    issue = ValidationIssue(
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        message=rule.error_message,
                        metadata=rule.metadata.copy()
                    )
                    result.issues.append(issue)
                    
                    if rule.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
                        result.is_valid = False
                    elif rule.severity == ValidationSeverity.WARNING:
                        result.warnings.append(rule.error_message)
                
            except Exception as e:
                logger.error(f"Error in validation rule {rule.rule_type} for key {key}: {str(e)}")
                issue = ValidationIssue(
                    rule_type="validation_error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation rule failed: {str(e)}"
                )
                result.issues.append(issue)
                result.is_valid = False
        
        return result
    
    def validate_configuration_set(self, configurations: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """
        Validate a set of configurations
        
        Args:
            configurations: Dictionary of configuration key-value pairs
            
        Returns:
            Dictionary of validation results by key
        """
        results = {}
        
        # Validate individual values
        for key, value in configurations.items():
            results[key] = self.validate_value(key, value)
        
        return results
    
    def detect_conflicts(self, configurations: Dict[str, Any]) -> List[ConflictDetection]:
        """
        Detect conflicts in configuration set
        
        Args:
            configurations: Dictionary of configuration key-value pairs
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        with self._conflict_lock:
            for conflict_detector in self._conflict_rules:
                try:
                    detected_conflicts = conflict_detector(configurations)
                    conflicts.extend(detected_conflicts)
                except Exception as e:
                    logger.error(f"Error in conflict detection: {str(e)}")
        
        return conflicts
    
    def assess_change_impact(self, key: str, old_value: Any, new_value: Any) -> ImpactAssessment:
        """
        Assess impact of configuration change
        
        Args:
            key: Configuration key
            old_value: Current value
            new_value: Proposed new value
            
        Returns:
            ImpactAssessment with change impact details
        """
        with self._impact_lock:
            impact_assessor = self._impact_rules.get(key)
        
        if impact_assessor:
            try:
                return impact_assessor(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Error in impact assessment for key {key}: {str(e)}")
        
        # Default impact assessment
        return self._default_impact_assessment(key, old_value, new_value)
    
    def add_restart_requirement(self, key: str, reason: str, component: str,
                               priority: str = "normal", estimated_time: str = None,
                               dependencies: List[str] = None):
        """
        Add restart requirement for configuration change
        
        Args:
            key: Configuration key
            reason: Reason for restart requirement
            component: Component that requires restart
            priority: Priority level (low, normal, high, critical)
            estimated_time: Estimated restart time
            dependencies: List of dependent components
        """
        requirement = RestartRequirement(
            key=key,
            reason=reason,
            component=component,
            priority=priority,
            estimated_restart_time=estimated_time,
            dependencies=dependencies or []
        )
        
        with self._restart_lock:
            self._restart_requirements[key] = requirement
        
        logger.info(f"Added restart requirement for key {key}: {reason}")
    
    def remove_restart_requirement(self, key: str) -> bool:
        """
        Remove restart requirement for configuration key
        
        Args:
            key: Configuration key
            
        Returns:
            True if requirement was removed
        """
        with self._restart_lock:
            if key in self._restart_requirements:
                del self._restart_requirements[key]
                logger.info(f"Removed restart requirement for key {key}")
                return True
            return False
    
    def get_restart_requirements(self) -> List[RestartRequirement]:
        """
        Get all pending restart requirements
        
        Returns:
            List of restart requirements
        """
        with self._restart_lock:
            return list(self._restart_requirements.values())
    
    def get_restart_requirements_by_priority(self, priority: str) -> List[RestartRequirement]:
        """
        Get restart requirements by priority level
        
        Args:
            priority: Priority level to filter by
            
        Returns:
            List of restart requirements with specified priority
        """
        with self._restart_lock:
            return [req for req in self._restart_requirements.values() if req.priority == priority]
    
    def clear_restart_requirements(self):
        """Clear all restart requirements"""
        with self._restart_lock:
            count = len(self._restart_requirements)
            self._restart_requirements.clear()
            logger.info(f"Cleared {count} restart requirements")
    
    def add_component_dependency(self, component: str, dependencies: List[str]):
        """
        Add component dependencies for impact assessment
        
        Args:
            component: Component name
            dependencies: List of dependent components
        """
        with self._dependencies_lock:
            self._component_dependencies[component] = dependencies
        
        logger.debug(f"Added dependencies for component {component}: {dependencies}")
    
    def get_affected_components(self, component: str) -> List[str]:
        """
        Get components affected by changes to a component
        
        Args:
            component: Component name
            
        Returns:
            List of affected components
        """
        affected = set()
        
        with self._dependencies_lock:
            # Direct dependencies
            affected.update(self._component_dependencies.get(component, []))
            
            # Reverse dependencies (components that depend on this one)
            for comp, deps in self._component_dependencies.items():
                if component in deps:
                    affected.add(comp)
        
        return list(affected)
    
    def _initialize_builtin_rules(self):
        """Initialize built-in validation rules"""
        # Integer range validation
        def integer_range_validator(min_val: int, max_val: int):
            def validator(value):
                try:
                    int_val = int(value)
                    return min_val <= int_val <= max_val
                except (ValueError, TypeError):
                    return False
            return validator
        
        # Float range validation
        def float_range_validator(min_val: float, max_val: float):
            def validator(value):
                try:
                    float_val = float(value)
                    return min_val <= float_val <= max_val
                except (ValueError, TypeError):
                    return False
            return validator
        
        # String length validation
        def string_length_validator(min_len: int, max_len: int):
            def validator(value):
                try:
                    str_val = str(value)
                    return min_len <= len(str_val) <= max_len
                except:
                    return False
            return validator
        
        # URL validation
        def url_validator(value):
            try:
                result = urlparse(str(value))
                return all([result.scheme, result.netloc])
            except:
                return False
        
        # Email validation
        def email_validator(value):
            try:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return re.match(email_pattern, str(value)) is not None
            except:
                return False
        
        # IP address validation
        def ip_validator(value):
            try:
                ipaddress.ip_address(str(value))
                return True
            except:
                return False
        
        # JSON validation
        def json_validator(value):
            try:
                if isinstance(value, (dict, list)):
                    return True
                json.loads(str(value))
                return True
            except:
                return False
        
        # Add common validation rules
        common_rules = {
            'max_concurrent_jobs': [
                ValidationRule(
                    rule_type="integer_range",
                    description="Must be between 1 and 100",
                    validator=integer_range_validator(1, 100),
                    error_message="max_concurrent_jobs must be between 1 and 100"
                )
            ],
            'session_timeout_minutes': [
                ValidationRule(
                    rule_type="integer_range",
                    description="Must be between 15 and 1440 minutes",
                    validator=integer_range_validator(15, 1440),
                    error_message="session_timeout_minutes must be between 15 and 1440"
                )
            ],
            'alert_error_rate_threshold': [
                ValidationRule(
                    rule_type="float_range",
                    description="Must be between 0.0 and 1.0",
                    validator=float_range_validator(0.0, 1.0),
                    error_message="alert_error_rate_threshold must be between 0.0 and 1.0"
                )
            ]
        }
        
        for key, rules in common_rules.items():
            for rule in rules:
                self.add_validation_rule(key, rule)
    
    def _initialize_builtin_conflicts(self):
        """Initialize built-in conflict detection rules"""
        def max_jobs_vs_queue_limit(configs: Dict[str, Any]) -> List[ConflictDetection]:
            conflicts = []
            max_jobs = configs.get('max_concurrent_jobs')
            queue_limit = configs.get('queue_size_limit')
            
            if max_jobs is not None and queue_limit is not None:
                try:
                    if int(max_jobs) > int(queue_limit):
                        conflicts.append(ConflictDetection(
                            conflict_type=ConflictType.LOGICAL_CONFLICT,
                            keys=['max_concurrent_jobs', 'queue_size_limit'],
                            description="max_concurrent_jobs cannot exceed queue_size_limit",
                            severity=ValidationSeverity.ERROR,
                            resolution_suggestions=[
                                "Increase queue_size_limit",
                                "Decrease max_concurrent_jobs"
                            ]
                        ))
                except (ValueError, TypeError):
                    pass
            
            return conflicts
        
        def memory_vs_job_limits(configs: Dict[str, Any]) -> List[ConflictDetection]:
            conflicts = []
            max_memory = configs.get('max_memory_usage_mb')
            max_jobs = configs.get('max_concurrent_jobs')
            
            if max_memory is not None and max_jobs is not None:
                try:
                    total_memory = int(max_memory) * int(max_jobs)
                    if total_memory > 16384:  # 16GB limit
                        conflicts.append(ConflictDetection(
                            conflict_type=ConflictType.RANGE_CONFLICT,
                            keys=['max_memory_usage_mb', 'max_concurrent_jobs'],
                            description=f"Total memory usage ({total_memory}MB) may exceed system limits",
                            severity=ValidationSeverity.WARNING,
                            resolution_suggestions=[
                                "Reduce max_memory_usage_mb",
                                "Reduce max_concurrent_jobs",
                                "Ensure system has sufficient memory"
                            ]
                        ))
                except (ValueError, TypeError):
                    pass
            
            return conflicts
        
        self.add_conflict_rule(max_jobs_vs_queue_limit)
        self.add_conflict_rule(memory_vs_job_limits)
    
    def _initialize_builtin_impacts(self):
        """Initialize built-in impact assessment rules"""
        def assess_max_concurrent_jobs(key: str, old_value: Any, new_value: Any) -> ImpactAssessment:
            try:
                old_val = int(old_value) if old_value is not None else 0
                new_val = int(new_value)
                
                if new_val < old_val:
                    impact_level = ImpactLevel.MEDIUM
                    risk_factors = ["May cause job queuing", "Reduced processing capacity"]
                elif new_val > old_val * 2:
                    impact_level = ImpactLevel.HIGH
                    risk_factors = ["Increased memory usage", "Potential system overload"]
                else:
                    impact_level = ImpactLevel.LOW
                    risk_factors = []
                
                return ImpactAssessment(
                    key=key,
                    old_value=old_value,
                    new_value=new_value,
                    impact_level=impact_level,
                    affected_components=["task_queue", "job_processor"],
                    requires_restart=False,
                    risk_factors=risk_factors,
                    mitigation_steps=["Monitor system resources", "Adjust gradually"]
                )
            except (ValueError, TypeError):
                return self._default_impact_assessment(key, old_value, new_value)
        
        def assess_session_timeout(key: str, old_value: Any, new_value: Any) -> ImpactAssessment:
            try:
                old_val = int(old_value) if old_value is not None else 120
                new_val = int(new_value)
                
                if new_val < old_val:
                    impact_level = ImpactLevel.MEDIUM
                    risk_factors = ["Users may be logged out more frequently"]
                    affected_components = ["session_manager", "web_interface"]
                else:
                    impact_level = ImpactLevel.LOW
                    risk_factors = []
                    affected_components = ["session_manager"]
                
                return ImpactAssessment(
                    key=key,
                    old_value=old_value,
                    new_value=new_value,
                    impact_level=impact_level,
                    affected_components=affected_components,
                    requires_restart=True,
                    risk_factors=risk_factors,
                    mitigation_steps=["Notify users of change", "Monitor session activity"]
                )
            except (ValueError, TypeError):
                return self._default_impact_assessment(key, old_value, new_value)
        
        self.add_impact_rule('max_concurrent_jobs', assess_max_concurrent_jobs)
        self.add_impact_rule('session_timeout_minutes', assess_session_timeout)
    
    def _default_impact_assessment(self, key: str, old_value: Any, new_value: Any) -> ImpactAssessment:
        """Default impact assessment for unknown configuration keys"""
        return ImpactAssessment(
            key=key,
            old_value=old_value,
            new_value=new_value,
            impact_level=ImpactLevel.LOW,
            affected_components=["unknown"],
            requires_restart=False,
            risk_factors=["Unknown impact"],
            mitigation_steps=["Monitor system after change", "Be prepared to rollback"]
        )
    
    def get_related_configurations(self, key: str) -> List[str]:
        """Get configurations related to the given key"""
        # Define configuration relationships
        relationships = {
            'max_concurrent_jobs': ['queue_size_limit', 'default_job_timeout'],
            'session_timeout_minutes': ['rate_limit_per_user_per_hour', 'audit_log_retention_days'],
            'queue_size_limit': ['max_concurrent_jobs', 'alert_queue_backup_threshold'],
            'default_job_timeout': ['max_concurrent_jobs', 'alert_error_rate_threshold'],
            'maintenance_mode': ['maintenance_reason'],
            'maintenance_reason': ['maintenance_mode'],
            'enable_batch_processing': ['max_concurrent_jobs', 'queue_size_limit'],
            'enable_advanced_monitoring': ['alert_queue_backup_threshold', 'alert_error_rate_threshold'],
            'max_memory_usage_mb': ['max_concurrent_jobs', 'processing_priority_weights'],
            'processing_priority_weights': ['max_memory_usage_mb', 'max_concurrent_jobs']
        }
        
        return relationships.get(key, [])
    
    def validate_single_value(self, key: str, value: Any, schema) -> 'ValidationResult':
        """Validate a single configuration value against its schema"""
        from system_configuration_manager import ConfigurationDataType
        
        errors = []
        warnings = []
        
        try:
            # Type validation
            if schema.data_type == ConfigurationDataType.INTEGER:
                try:
                    int_value = int(value)
                    value = int_value
                except (ValueError, TypeError):
                    errors.append(f"Value must be an integer, got: {type(value).__name__}")
                    return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            elif schema.data_type == ConfigurationDataType.FLOAT:
                try:
                    float_value = float(value)
                    value = float_value
                except (ValueError, TypeError):
                    errors.append(f"Value must be a number, got: {type(value).__name__}")
                    return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            elif schema.data_type == ConfigurationDataType.BOOLEAN:
                if isinstance(value, str):
                    if value.lower() in ('true', '1', 'yes', 'on'):
                        value = True
                    elif value.lower() in ('false', '0', 'no', 'off'):
                        value = False
                    else:
                        errors.append(f"Boolean value must be true/false, got: {value}")
                        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
                elif not isinstance(value, bool):
                    errors.append(f"Value must be boolean, got: {type(value).__name__}")
                    return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            elif schema.data_type == ConfigurationDataType.JSON:
                if isinstance(value, str):
                    try:
                        import json
                        json.loads(value)
                    except json.JSONDecodeError as e:
                        errors.append(f"Invalid JSON format: {str(e)}")
                        return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Validation rules
            if schema.validation_rules:
                rules = schema.validation_rules
                
                # Min/Max validation for numeric types
                if schema.data_type in [ConfigurationDataType.INTEGER, ConfigurationDataType.FLOAT]:
                    if 'min' in rules and value < rules['min']:
                        errors.append(f"Value {value} is below minimum {rules['min']}")
                    if 'max' in rules and value > rules['max']:
                        errors.append(f"Value {value} is above maximum {rules['max']}")
                
                # Length validation for strings
                if schema.data_type == ConfigurationDataType.STRING:
                    if 'min_length' in rules and len(str(value)) < rules['min_length']:
                        errors.append(f"Value length {len(str(value))} is below minimum {rules['min_length']}")
                    if 'max_length' in rules and len(str(value)) > rules['max_length']:
                        errors.append(f"Value length {len(str(value))} is above maximum {rules['max_length']}")
                
                # Pattern validation
                if 'pattern' in rules:
                    import re
                    if not re.match(rules['pattern'], str(value)):
                        errors.append(f"Value does not match required pattern: {rules['pattern']}")
                
                # Allowed values validation
                if 'allowed_values' in rules:
                    if value not in rules['allowed_values']:
                        errors.append(f"Value must be one of: {rules['allowed_values']}")
            
            # Custom validation rules
            with self._rules_lock:
                if key in self._validation_rules:
                    for rule in self._validation_rules[key]:
                        try:
                            rule_result = rule.validate(value)
                            if not rule_result.is_valid:
                                errors.extend(rule_result.errors)
                                warnings.extend(rule_result.warnings)
                        except Exception as e:
                            errors.append(f"Validation rule error: {str(e)}")
            
            # Add warnings for potentially problematic values
            if schema.data_type in [ConfigurationDataType.INTEGER, ConfigurationDataType.FLOAT]:
                if key == 'session_timeout_minutes' and value < 5:
                    warnings.append("Very short session timeout may cause frequent logouts")
                elif key == 'max_concurrent_jobs' and value > 100:
                    warnings.append("High concurrent job limit may impact system performance")
                elif key == 'queue_size_limit' and value > 10000:
                    warnings.append("Large queue size limit may consume significant memory")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)


# Global validator instance
_global_validator: Optional[ConfigurationValidator] = None
_validator_lock = threading.Lock()


def get_validator() -> ConfigurationValidator:
    """Get global configuration validator instance"""
    global _global_validator
    
    with _validator_lock:
        if _global_validator is None:
            _global_validator = ConfigurationValidator()
        return _global_validator


def set_validator(validator: ConfigurationValidator):
    """Set global configuration validator instance"""
    global _global_validator
    
    with _validator_lock:
        _global_validator = validator