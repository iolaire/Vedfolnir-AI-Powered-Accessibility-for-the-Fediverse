# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Alert Threshold Validator

Provides comprehensive validation for alert threshold values to prevent
invalid configurations and ensure system stability.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from .alert_manager import AlertThresholds

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of threshold validation"""
    is_valid: bool
    issues: List['ValidationIssue']
    warnings: List['ValidationIssue']
    recommendations: List[str]
    
    def has_errors(self) -> bool:
        """Check if validation has errors"""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if validation has warnings"""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues + self.warnings)
    
    def get_error_messages(self) -> List[str]:
        """Get all error messages"""
        return [issue.message for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    def get_warning_messages(self) -> List[str]:
        """Get all warning messages"""
        return [issue.message for issue in self.issues + self.warnings if issue.severity == ValidationSeverity.WARNING]


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    severity: ValidationSeverity
    field: str
    message: str
    current_value: Any
    suggested_value: Optional[Any] = None
    impact: Optional[str] = None


class AlertThresholdValidator:
    """
    Comprehensive validator for alert threshold configurations
    
    Features:
    - Range validation for all threshold types
    - Logical consistency checks between related thresholds
    - Performance impact assessment
    - Security and stability validation
    - Recommendation generation for optimal values
    """
    
    # Validation rules for individual thresholds
    VALIDATION_RULES = {
        'job_failure_rate': {
            'min': 0.0,
            'max': 1.0,
            'recommended_min': 0.01,
            'recommended_max': 0.5,
            'optimal': 0.1,
            'description': 'Job failure rate threshold (0.0-1.0)'
        },
        'repeated_failure_count': {
            'min': 1,
            'max': 100,
            'recommended_min': 2,
            'recommended_max': 10,
            'optimal': 3,
            'description': 'Repeated failure count threshold'
        },
        'resource_usage_threshold': {
            'min': 0.0,
            'max': 1.0,
            'recommended_min': 0.7,
            'recommended_max': 0.95,
            'optimal': 0.9,
            'description': 'Resource usage threshold (0.0-1.0)'
        },
        'queue_backup_threshold': {
            'min': 1,
            'max': 10000,
            'recommended_min': 10,
            'recommended_max': 1000,
            'optimal': 100,
            'description': 'Queue backup threshold (number of jobs)'
        },
        'ai_service_timeout': {
            'min': 1,
            'max': 3600,
            'recommended_min': 10,
            'recommended_max': 300,
            'optimal': 30,
            'description': 'AI service timeout threshold (seconds)'
        },
        'performance_degradation_threshold': {
            'min': 1.0,
            'max': 100.0,
            'recommended_min': 1.5,
            'recommended_max': 10.0,
            'optimal': 2.0,
            'description': 'Performance degradation threshold (multiplier)'
        }
    }
    
    def __init__(self):
        """Initialize threshold validator"""
        self._validation_history: List[ValidationResult] = []
        self._stats = {
            'validations_performed': 0,
            'validations_passed': 0,
            'validations_failed': 0,
            'warnings_generated': 0,
            'errors_detected': 0
        }
    
    def validate_thresholds(self, thresholds: AlertThresholds) -> ValidationResult:
        """
        Validate complete set of alert thresholds
        
        Args:
            thresholds: AlertThresholds object to validate
            
        Returns:
            ValidationResult with validation outcome and issues
        """
        try:
            issues = []
            warnings = []
            recommendations = []
            
            # Validate individual thresholds
            individual_issues = self._validate_individual_thresholds(thresholds)
            issues.extend(individual_issues)
            
            # Validate logical consistency
            consistency_issues = self._validate_threshold_consistency(thresholds)
            issues.extend(consistency_issues)
            
            # Generate performance warnings
            performance_warnings = self._check_performance_impact(thresholds)
            warnings.extend(performance_warnings)
            
            # Generate security warnings
            security_warnings = self._check_security_implications(thresholds)
            warnings.extend(security_warnings)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(thresholds, issues + warnings)
            
            # Determine overall validity
            is_valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)
            
            # Create validation result
            result = ValidationResult(
                is_valid=is_valid,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
            # Update statistics
            self._stats['validations_performed'] += 1
            if is_valid:
                self._stats['validations_passed'] += 1
            else:
                self._stats['validations_failed'] += 1
            
            self._stats['warnings_generated'] += len(warnings)
            self._stats['errors_detected'] += len([i for i in issues if i.severity == ValidationSeverity.ERROR])
            
            # Store in history
            self._validation_history.append(result)
            if len(self._validation_history) > 100:  # Keep last 100 validations
                self._validation_history.pop(0)
            
            logger.info(f"Threshold validation completed: valid={is_valid}, issues={len(issues)}, warnings={len(warnings)}")
            return result
            
        except Exception as e:
            logger.error(f"Error during threshold validation: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    field="validation",
                    message=f"Validation error: {str(e)}",
                    current_value=None
                )],
                warnings=[],
                recommendations=[]
            )
    
    def validate_individual_threshold(self, field: str, value: Any) -> List[ValidationIssue]:
        """
        Validate a single threshold value
        
        Args:
            field: Threshold field name
            value: Threshold value to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if field not in self.VALIDATION_RULES:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field=field,
                message=f"Unknown threshold field: {field}",
                current_value=value
            ))
            return issues
        
        rules = self.VALIDATION_RULES[field]
        
        # Type validation
        expected_type = type(rules['min'])
        if not isinstance(value, expected_type):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field=field,
                message=f"Invalid type for {field}: expected {expected_type.__name__}, got {type(value).__name__}",
                current_value=value,
                suggested_value=expected_type(rules['optimal'])
            ))
            return issues
        
        # Range validation
        if value < rules['min'] or value > rules['max']:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                field=field,
                message=f"Value {value} for {field} is outside valid range [{rules['min']}, {rules['max']}]",
                current_value=value,
                suggested_value=rules['optimal'],
                impact="May cause system instability or missed alerts"
            ))
        
        # Recommended range validation
        elif value < rules['recommended_min'] or value > rules['recommended_max']:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field=field,
                message=f"Value {value} for {field} is outside recommended range [{rules['recommended_min']}, {rules['recommended_max']}]",
                current_value=value,
                suggested_value=rules['optimal'],
                impact="May not provide optimal alerting performance"
            ))
        
        return issues
    
    def _validate_individual_thresholds(self, thresholds: AlertThresholds) -> List[ValidationIssue]:
        """Validate all individual threshold values"""
        issues = []
        
        threshold_values = {
            'job_failure_rate': thresholds.job_failure_rate,
            'repeated_failure_count': thresholds.repeated_failure_count,
            'resource_usage_threshold': thresholds.resource_usage_threshold,
            'queue_backup_threshold': thresholds.queue_backup_threshold,
            'ai_service_timeout': thresholds.ai_service_timeout,
            'performance_degradation_threshold': thresholds.performance_degradation_threshold
        }
        
        for field, value in threshold_values.items():
            field_issues = self.validate_individual_threshold(field, value)
            issues.extend(field_issues)
        
        return issues
    
    def _validate_threshold_consistency(self, thresholds: AlertThresholds) -> List[ValidationIssue]:
        """Validate logical consistency between thresholds"""
        issues = []
        
        # Check for conflicting threshold combinations
        
        # High resource threshold with low failure rate may miss alerts
        if (thresholds.resource_usage_threshold > 0.95 and 
            thresholds.job_failure_rate < 0.05):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="resource_usage_threshold",
                message="Very high resource threshold combined with very low failure rate may cause missed alerts",
                current_value=thresholds.resource_usage_threshold,
                suggested_value=0.9,
                impact="Critical resource issues may not trigger alerts in time"
            ))
        
        # Very high repeated failure count may delay critical alerts
        if thresholds.repeated_failure_count > 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="repeated_failure_count",
                message="High repeated failure count may delay critical alert notifications",
                current_value=thresholds.repeated_failure_count,
                suggested_value=5,
                impact="Critical issues may not be reported promptly"
            ))
        
        # Very short AI service timeout may cause false positives
        if thresholds.ai_service_timeout < 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="ai_service_timeout",
                message="Very short AI service timeout may cause false positive alerts",
                current_value=thresholds.ai_service_timeout,
                suggested_value=30,
                impact="May generate excessive timeout alerts during normal load"
            ))
        
        # Very large queue backup threshold may hide performance issues
        if thresholds.queue_backup_threshold > 1000:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="queue_backup_threshold",
                message="Very large queue backup threshold may hide performance degradation",
                current_value=thresholds.queue_backup_threshold,
                suggested_value=500,
                impact="Performance issues may not be detected until severely impacted"
            ))
        
        # Performance degradation threshold too high may miss issues
        if thresholds.performance_degradation_threshold > 5.0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="performance_degradation_threshold",
                message="High performance degradation threshold may miss performance issues",
                current_value=thresholds.performance_degradation_threshold,
                suggested_value=2.5,
                impact="Performance degradation may not be detected early enough"
            ))
        
        return issues
    
    def _check_performance_impact(self, thresholds: AlertThresholds) -> List[ValidationIssue]:
        """Check for potential performance impacts"""
        warnings = []
        
        # Very low thresholds may cause alert spam
        if thresholds.job_failure_rate < 0.01:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="job_failure_rate",
                message="Very low job failure rate threshold may generate excessive alerts",
                current_value=thresholds.job_failure_rate,
                impact="May cause alert fatigue and reduce effectiveness"
            ))
        
        if thresholds.resource_usage_threshold < 0.7:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="resource_usage_threshold",
                message="Low resource usage threshold may generate frequent alerts during normal operation",
                current_value=thresholds.resource_usage_threshold,
                impact="May cause unnecessary alert noise"
            ))
        
        if thresholds.queue_backup_threshold < 10:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="queue_backup_threshold",
                message="Very low queue backup threshold may trigger alerts during normal queue fluctuations",
                current_value=thresholds.queue_backup_threshold,
                impact="May generate false positive alerts"
            ))
        
        return warnings
    
    def _check_security_implications(self, thresholds: AlertThresholds) -> List[ValidationIssue]:
        """Check for security-related threshold issues"""
        warnings = []
        
        # High thresholds may allow security issues to go unnoticed
        if thresholds.job_failure_rate > 0.3:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="job_failure_rate",
                message="High job failure rate threshold may allow security-related failures to go unnoticed",
                current_value=thresholds.job_failure_rate,
                impact="Potential security incidents may not trigger alerts"
            ))
        
        if thresholds.repeated_failure_count > 20:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                field="repeated_failure_count",
                message="Very high repeated failure count may delay detection of security attacks",
                current_value=thresholds.repeated_failure_count,
                impact="Brute force or DoS attacks may not be detected promptly"
            ))
        
        return warnings
    
    def _generate_recommendations(self, thresholds: AlertThresholds, issues: List[ValidationIssue]) -> List[str]:
        """Generate recommendations for threshold optimization"""
        recommendations = []
        
        # General recommendations based on current values
        if thresholds.job_failure_rate != 0.1:
            recommendations.append("Consider using 0.1 (10%) as the job failure rate threshold for balanced alerting")
        
        if thresholds.resource_usage_threshold != 0.9:
            recommendations.append("Consider using 0.9 (90%) as the resource usage threshold for optimal performance monitoring")
        
        if thresholds.ai_service_timeout != 30:
            recommendations.append("Consider using 30 seconds as the AI service timeout for reliable service monitoring")
        
        # Recommendations based on detected issues
        error_fields = [issue.field for issue in issues if issue.severity == ValidationSeverity.ERROR]
        if error_fields:
            recommendations.append(f"Fix validation errors in fields: {', '.join(set(error_fields))}")
        
        warning_fields = [issue.field for issue in issues if issue.severity == ValidationSeverity.WARNING]
        if warning_fields:
            recommendations.append(f"Review warning conditions in fields: {', '.join(set(warning_fields))}")
        
        # Environment-specific recommendations
        recommendations.append("Test threshold changes in a staging environment before applying to production")
        recommendations.append("Monitor alert frequency after threshold changes to ensure optimal balance")
        recommendations.append("Consider implementing gradual threshold adjustments rather than large changes")
        
        return recommendations
    
    def get_safe_fallback_thresholds(self) -> AlertThresholds:
        """
        Get safe fallback threshold values
        
        Returns:
            AlertThresholds with conservative, safe values
        """
        return AlertThresholds(
            job_failure_rate=0.1,
            repeated_failure_count=3,
            resource_usage_threshold=0.9,
            queue_backup_threshold=100,
            ai_service_timeout=30,
            performance_degradation_threshold=2.0
        )
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics
        
        Returns:
            Dictionary with validation statistics
        """
        return {
            'statistics': self._stats.copy(),
            'validation_history_count': len(self._validation_history),
            'recent_validation_success_rate': self._calculate_recent_success_rate()
        }
    
    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate for recent validations"""
        if not self._validation_history:
            return 0.0
        
        recent_validations = self._validation_history[-10:]  # Last 10 validations
        successful = sum(1 for v in recent_validations if v.is_valid)
        return successful / len(recent_validations)
    
    def clear_validation_history(self):
        """Clear validation history"""
        self._validation_history.clear()
        logger.info("Validation history cleared")