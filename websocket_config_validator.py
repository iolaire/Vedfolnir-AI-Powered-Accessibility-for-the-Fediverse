# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration Validator

This module provides comprehensive validation for WebSocket configuration,
including detailed error messages, warnings, and configuration health checks.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from websocket_config_schema import (
    WebSocketConfigSchema,
    ConfigValidationLevel,
    ConfigDataType,
    ConfigSchemaField,
    ConfigValidationRule
)


@dataclass
class ValidationResult:
    """Configuration validation result"""
    field_name: str
    rule_name: str
    level: ConfigValidationLevel
    message: str
    current_value: Any
    suggested_value: Optional[Any] = None
    documentation_link: Optional[str] = None


@dataclass
class ConfigurationReport:
    """Comprehensive configuration validation report"""
    timestamp: datetime = field(default_factory=datetime.now)
    total_fields: int = 0
    validated_fields: int = 0
    errors: List[ValidationResult] = field(default_factory=list)
    warnings: List[ValidationResult] = field(default_factory=list)
    info: List[ValidationResult] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    deprecated_used: List[str] = field(default_factory=list)
    configuration_summary: Dict[str, Any] = field(default_factory=dict)
    health_score: float = 0.0
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid (no errors)"""
        return len(self.errors) == 0 and len(self.missing_required) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if configuration has warnings"""
        return len(self.warnings) > 0 or len(self.deprecated_used) > 0


class WebSocketConfigValidator:
    """
    Comprehensive WebSocket configuration validator
    
    Validates environment variables against schema, provides detailed
    error messages, and generates configuration health reports.
    """
    
    def __init__(self):
        """Initialize configuration validator"""
        self.schema = WebSocketConfigSchema()
        self.logger = logging.getLogger(__name__)
    
    def validate_configuration(self, env_vars: Optional[Dict[str, str]] = None) -> ConfigurationReport:
        """
        Validate WebSocket configuration
        
        Args:
            env_vars: Environment variables to validate (defaults to os.environ)
            
        Returns:
            Comprehensive validation report
        """
        if env_vars is None:
            env_vars = dict(os.environ)
        
        report = ConfigurationReport()
        schema_fields = self.schema.get_schema_fields()
        
        report.total_fields = len(schema_fields)
        
        # Validate each schema field
        for field_name, field_schema in schema_fields.items():
            self._validate_field(field_name, field_schema, env_vars, report)
        
        # Check for deprecated fields
        self._check_deprecated_fields(env_vars, report)
        
        # Generate configuration summary
        report.configuration_summary = self._generate_configuration_summary(env_vars)
        
        # Calculate health score
        report.health_score = self._calculate_health_score(report)
        
        self.logger.info(f"Configuration validation completed. Health score: {report.health_score:.2f}")
        
        return report
    
    def _validate_field(
        self,
        field_name: str,
        field_schema: ConfigSchemaField,
        env_vars: Dict[str, str],
        report: ConfigurationReport
    ) -> None:
        """Validate a single configuration field"""
        current_value = env_vars.get(field_name)
        
        # Check if required field is missing
        if field_schema.required and current_value is None:
            report.missing_required.append(field_name)
            return
        
        # Skip validation if field is not set and not required
        if current_value is None:
            return
        
        report.validated_fields += 1
        
        # Parse value according to data type
        try:
            parsed_value = self._parse_value(current_value, field_schema.data_type)
        except ValueError as e:
            report.errors.append(ValidationResult(
                field_name=field_name,
                rule_name="data_type",
                level=ConfigValidationLevel.ERROR,
                message=f"Invalid data type: {e}",
                current_value=current_value,
                suggested_value=str(field_schema.default_value)
            ))
            return
        
        # Apply validation rules
        validation_rules = self.schema.get_validation_rules(field_name)
        for rule in validation_rules:
            try:
                # Pass the original string value to validation rules that expect strings
                # and parsed value to rules that expect parsed types
                if rule.name in ["valid_origins", "production_wildcard", "valid_transports"]:
                    validation_input = current_value  # Use original string value
                else:
                    validation_input = parsed_value  # Use parsed value
                
                if not rule.validator(validation_input):
                    result = ValidationResult(
                        field_name=field_name,
                        rule_name=rule.name,
                        level=rule.level,
                        message=rule.message,
                        current_value=current_value,
                        suggested_value=self._get_suggested_value(field_name, field_schema)
                    )
                    
                    if rule.level == ConfigValidationLevel.ERROR:
                        report.errors.append(result)
                    elif rule.level == ConfigValidationLevel.WARNING:
                        report.warnings.append(result)
                    else:
                        report.info.append(result)
                        
            except Exception as e:
                self.logger.error(f"Validation rule '{rule.name}' failed for field '{field_name}': {e}")
                report.errors.append(ValidationResult(
                    field_name=field_name,
                    rule_name=rule.name,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Validation rule error: {e}",
                    current_value=current_value
                ))
    
    def _parse_value(self, value: str, data_type: ConfigDataType) -> Any:
        """Parse string value according to data type"""
        if data_type == ConfigDataType.STRING:
            return value
        elif data_type == ConfigDataType.INTEGER:
            return int(value)
        elif data_type == ConfigDataType.BOOLEAN:
            return value.lower() in ["true", "1", "yes", "on"]
        elif data_type == ConfigDataType.LIST:
            return [item.strip() for item in value.split(",") if item.strip()]
        elif data_type in [ConfigDataType.URL, ConfigDataType.HOST]:
            return value
        elif data_type == ConfigDataType.PORT:
            port = int(value)
            if not (1 <= port <= 65535):
                raise ValueError(f"Port must be between 1 and 65535, got {port}")
            return port
        else:
            return value
    
    def _get_suggested_value(self, field_name: str, field_schema: ConfigSchemaField) -> Optional[str]:
        """Get suggested value for a field"""
        if field_schema.examples:
            return field_schema.examples[0]
        return str(field_schema.default_value)
    
    def _check_deprecated_fields(self, env_vars: Dict[str, str], report: ConfigurationReport) -> None:
        """Check for usage of deprecated fields"""
        deprecated_fields = self.schema.get_deprecated_fields()
        
        for field_name in deprecated_fields:
            if field_name in env_vars:
                report.deprecated_used.append(field_name)
                
                field_schema = deprecated_fields[field_name]
                report.warnings.append(ValidationResult(
                    field_name=field_name,
                    rule_name="deprecated",
                    level=ConfigValidationLevel.WARNING,
                    message=f"Field is deprecated. {field_schema.migration_note or 'Please update your configuration.'}",
                    current_value=env_vars[field_name]
                ))
    
    def _generate_configuration_summary(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Generate configuration summary"""
        summary = {
            "environment": os.getenv("FLASK_ENV", "production"),
            "configured_fields": {},
            "categories": {}
        }
        
        # Summarize configured fields by category
        for category in self.schema.get_categories():
            category_fields = self.schema.get_fields_by_category(category)
            configured_count = sum(1 for field_name in category_fields if field_name in env_vars)
            
            summary["categories"][category] = {
                "total_fields": len(category_fields),
                "configured_fields": configured_count,
                "configuration_percentage": (configured_count / len(category_fields)) * 100
            }
        
        # Add specific configuration details
        summary["configured_fields"] = {
            field_name: env_vars[field_name]
            for field_name in env_vars
            if field_name in self.schema.get_schema_fields()
        }
        
        return summary
    
    def _calculate_health_score(self, report: ConfigurationReport) -> float:
        """Calculate configuration health score (0-100)"""
        if report.total_fields == 0:
            return 0.0
        
        # Base score from field coverage
        coverage_score = (report.validated_fields / report.total_fields) * 100
        
        # Penalties for issues
        error_penalty = len(report.errors) * 10
        missing_required_penalty = len(report.missing_required) * 15
        warning_penalty = len(report.warnings) * 2
        deprecated_penalty = len(report.deprecated_used) * 1
        
        # Calculate final score
        health_score = coverage_score - error_penalty - missing_required_penalty - warning_penalty - deprecated_penalty
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, health_score))
    
    def validate_runtime_configuration(self, config_dict: Dict[str, Any]) -> ConfigurationReport:
        """
        Validate runtime configuration dictionary
        
        Args:
            config_dict: Configuration dictionary to validate
            
        Returns:
            Validation report
        """
        # Convert config dict to environment variable format
        env_vars = {}
        for key, value in config_dict.items():
            if isinstance(value, (list, tuple)):
                env_vars[key] = ",".join(str(v) for v in value)
            else:
                env_vars[key] = str(value)
        
        return self.validate_configuration(env_vars)
    
    def get_field_documentation(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive documentation for a configuration field
        
        Args:
            field_name: Name of the configuration field
            
        Returns:
            Field documentation dictionary
        """
        field_schema = self.schema.get_field_by_name(field_name)
        if not field_schema:
            return None
        
        validation_rules = self.schema.get_validation_rules(field_name)
        
        return {
            "name": field_schema.name,
            "description": field_schema.description,
            "data_type": field_schema.data_type.value,
            "default_value": field_schema.default_value,
            "required": field_schema.required,
            "category": field_schema.category,
            "examples": field_schema.examples,
            "deprecated": field_schema.deprecated,
            "migration_note": field_schema.migration_note,
            "validation_rules": [
                {
                    "name": rule.name,
                    "message": rule.message,
                    "level": rule.level.value
                }
                for rule in validation_rules
            ]
        }
    
    def generate_configuration_template(self, include_optional: bool = True) -> str:
        """
        Generate configuration template with documentation
        
        Args:
            include_optional: Whether to include optional fields
            
        Returns:
            Configuration template as string
        """
        template_lines = [
            "# WebSocket Configuration Template",
            "# Generated by WebSocket Configuration Validator",
            f"# Generated at: {datetime.now().isoformat()}",
            "",
            "# This file contains all available WebSocket configuration options",
            "# with descriptions, examples, and default values.",
            ""
        ]
        
        # Group fields by category
        for category in sorted(self.schema.get_categories()):
            category_fields = self.schema.get_fields_by_category(category)
            
            template_lines.extend([
                f"# {category.upper()} CONFIGURATION",
                f"# {'-' * (len(category) + 15)}",
                ""
            ])
            
            for field_name, field_schema in sorted(category_fields.items()):
                # Skip optional fields if not requested
                if not include_optional and not field_schema.required:
                    continue
                
                # Add field documentation
                template_lines.extend([
                    f"# {field_schema.description}",
                    f"# Type: {field_schema.data_type.value}",
                    f"# Default: {field_schema.default_value}",
                    f"# Required: {'Yes' if field_schema.required else 'No'}"
                ])
                
                if field_schema.examples:
                    template_lines.append(f"# Examples: {', '.join(field_schema.examples)}")
                
                if field_schema.deprecated:
                    template_lines.append(f"# DEPRECATED: {field_schema.migration_note or 'Please update your configuration'}")
                
                # Add the actual configuration line (commented out)
                example_value = field_schema.examples[0] if field_schema.examples else str(field_schema.default_value)
                template_lines.extend([
                    f"# {field_name}={example_value}",
                    ""
                ])
        
        return "\n".join(template_lines)
    
    def check_configuration_health(self) -> Dict[str, Any]:
        """
        Perform runtime configuration health check
        
        Returns:
            Health check results
        """
        report = self.validate_configuration()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": report.health_score,
            "status": "healthy" if report.is_valid else "unhealthy",
            "summary": {
                "total_fields": report.total_fields,
                "validated_fields": report.validated_fields,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "missing_required": len(report.missing_required),
                "deprecated_used": len(report.deprecated_used)
            },
            "issues": {
                "errors": [
                    {
                        "field": result.field_name,
                        "message": result.message,
                        "current_value": result.current_value,
                        "suggested_value": result.suggested_value
                    }
                    for result in report.errors
                ],
                "warnings": [
                    {
                        "field": result.field_name,
                        "message": result.message,
                        "current_value": result.current_value
                    }
                    for result in report.warnings
                ],
                "missing_required": report.missing_required,
                "deprecated_used": report.deprecated_used
            },
            "configuration_summary": report.configuration_summary
        }