# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
System Configuration Manager

Provides comprehensive system configuration management with validation,
audit trails, rollback capabilities, and environment-specific overrides.
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import DatabaseManager
from models import SystemConfiguration, User, UserRole, JobAuditLog
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class ConfigurationCategory(Enum):
    """Configuration categories for organization"""
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    LIMITS = "limits"
    ALERTS = "alerts"
    MAINTENANCE = "maintenance"
    FEATURES = "features"
    STORAGE = "storage"


class ConfigurationDataType(Enum):
    """Supported configuration data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


@dataclass
class ConfigurationSchema:
    """Schema definition for configuration keys"""
    key: str
    data_type: ConfigurationDataType
    category: ConfigurationCategory
    description: str
    default_value: Any = None
    is_sensitive: bool = False
    validation_rules: Dict[str, Any] = None
    environment_override: bool = True
    requires_restart: bool = False


@dataclass
class ConfigurationChange:
    """Represents a configuration change for audit trail"""
    key: str
    old_value: Any
    new_value: Any
    changed_by: int
    changed_at: datetime
    reason: str = ""


@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    conflicts: List[str]


@dataclass
class ConfigurationExport:
    """Configuration export data structure"""
    configurations: Dict[str, Any]
    metadata: Dict[str, Any]
    export_timestamp: datetime
    exported_by: int


class SystemConfigurationManager:
    """
    Comprehensive system configuration management service
    
    Provides:
    - Configuration CRUD operations with validation
    - Audit trail and rollback capabilities
    - Environment-specific overrides
    - Configuration export/import
    - Conflict detection and validation
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._configuration_schema = self._initialize_schema()
        self._environment_prefix = "VEDFOLNIR_CONFIG_"
    
    def _initialize_schema(self) -> Dict[str, ConfigurationSchema]:
        """Initialize the configuration schema with all supported settings"""
        schema = {}
        
        # System settings
        schema.update({
            "max_concurrent_jobs": ConfigurationSchema(
                key="max_concurrent_jobs",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.SYSTEM,
                description="Maximum number of concurrent caption generation jobs system-wide",
                default_value=10,
                validation_rules={"min": 1, "max": 100}
            ),
            "default_job_timeout": ConfigurationSchema(
                key="default_job_timeout",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.SYSTEM,
                description="Default timeout for caption generation jobs in seconds",
                default_value=3600,
                validation_rules={"min": 300, "max": 86400}
            ),
            "maintenance_mode": ConfigurationSchema(
                key="maintenance_mode",
                data_type=ConfigurationDataType.BOOLEAN,
                category=ConfigurationCategory.MAINTENANCE,
                description="Enable maintenance mode to prevent new job creation",
                default_value=False
            ),
            "maintenance_reason": ConfigurationSchema(
                key="maintenance_reason",
                data_type=ConfigurationDataType.STRING,
                category=ConfigurationCategory.MAINTENANCE,
                description="Reason for maintenance mode",
                default_value=""
            )
        })
        
        # Performance settings
        schema.update({
            "max_memory_usage_mb": ConfigurationSchema(
                key="max_memory_usage_mb",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.PERFORMANCE,
                description="Maximum memory usage per job in MB",
                default_value=2048,
                validation_rules={"min": 512, "max": 16384}
            ),
            "queue_size_limit": ConfigurationSchema(
                key="queue_size_limit",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.PERFORMANCE,
                description="Maximum number of jobs in queue",
                default_value=100,
                validation_rules={"min": 10, "max": 1000}
            ),
            "processing_priority_weights": ConfigurationSchema(
                key="processing_priority_weights",
                data_type=ConfigurationDataType.JSON,
                category=ConfigurationCategory.PERFORMANCE,
                description="Priority weights for job processing",
                default_value={"high": 3, "normal": 2, "low": 1}
            )
        })
        
        # Security settings
        schema.update({
            "rate_limit_per_user_per_hour": ConfigurationSchema(
                key="rate_limit_per_user_per_hour",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.SECURITY,
                description="Maximum jobs per user per hour",
                default_value=50,
                validation_rules={"min": 1, "max": 1000}
            ),
            "session_timeout_minutes": ConfigurationSchema(
                key="session_timeout_minutes",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.SECURITY,
                description="User session timeout in minutes",
                default_value=120,
                validation_rules={"min": 15, "max": 1440}
            ),
            "audit_log_retention_days": ConfigurationSchema(
                key="audit_log_retention_days",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.SECURITY,
                description="Number of days to retain audit logs",
                default_value=90,
                validation_rules={"min": 30, "max": 365}
            )
        })
        
        # Alert settings
        schema.update({
            "alert_queue_backup_threshold": ConfigurationSchema(
                key="alert_queue_backup_threshold",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.ALERTS,
                description="Queue size threshold for backup alerts",
                default_value=50,
                validation_rules={"min": 5, "max": 500}
            ),
            "alert_error_rate_threshold": ConfigurationSchema(
                key="alert_error_rate_threshold",
                data_type=ConfigurationDataType.FLOAT,
                category=ConfigurationCategory.ALERTS,
                description="Error rate threshold for alerts (0.0-1.0)",
                default_value=0.1,
                validation_rules={"min": 0.0, "max": 1.0}
            ),
            "alert_notification_channels": ConfigurationSchema(
                key="alert_notification_channels",
                data_type=ConfigurationDataType.JSON,
                category=ConfigurationCategory.ALERTS,
                description="Notification channels for alerts",
                default_value=["email", "dashboard"]
            )
        })
        
        # Feature flags
        schema.update({
            "enable_batch_processing": ConfigurationSchema(
                key="enable_batch_processing",
                data_type=ConfigurationDataType.BOOLEAN,
                category=ConfigurationCategory.FEATURES,
                description="Enable batch processing capabilities",
                default_value=True
            ),
            "enable_advanced_monitoring": ConfigurationSchema(
                key="enable_advanced_monitoring",
                data_type=ConfigurationDataType.BOOLEAN,
                category=ConfigurationCategory.FEATURES,
                description="Enable advanced system monitoring",
                default_value=True
            ),
            "enable_auto_retry": ConfigurationSchema(
                key="enable_auto_retry",
                data_type=ConfigurationDataType.BOOLEAN,
                category=ConfigurationCategory.FEATURES,
                description="Enable automatic retry for failed jobs",
                default_value=True
            )
        })
        
        # Storage management settings
        schema.update({
            "CAPTION_MAX_STORAGE_GB": ConfigurationSchema(
                key="CAPTION_MAX_STORAGE_GB",
                data_type=ConfigurationDataType.FLOAT,
                category=ConfigurationCategory.STORAGE,
                description="Maximum storage limit for image files in gigabytes",
                default_value=10.0,
                validation_rules={"min": 0.1, "max": 1000.0},
                environment_override=True,
                requires_restart=False
            ),
            "STORAGE_WARNING_THRESHOLD": ConfigurationSchema(
                key="STORAGE_WARNING_THRESHOLD",
                data_type=ConfigurationDataType.FLOAT,
                category=ConfigurationCategory.STORAGE,
                description="Warning threshold as percentage of maximum storage limit (1-100)",
                default_value=80.0,
                validation_rules={"min": 1.0, "max": 100.0},
                environment_override=True,
                requires_restart=False
            ),
            "STORAGE_MONITORING_ENABLED": ConfigurationSchema(
                key="STORAGE_MONITORING_ENABLED",
                data_type=ConfigurationDataType.BOOLEAN,
                category=ConfigurationCategory.STORAGE,
                description="Enable or disable storage monitoring and limit enforcement",
                default_value=True,
                environment_override=True,
                requires_restart=False
            ),
            "storage_cleanup_retention_days": ConfigurationSchema(
                key="storage_cleanup_retention_days",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.STORAGE,
                description="Number of days to retain storage event logs",
                default_value=30,
                validation_rules={"min": 1, "max": 365},
                requires_restart=False
            ),
            "storage_override_max_duration_hours": ConfigurationSchema(
                key="storage_override_max_duration_hours",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.STORAGE,
                description="Maximum duration for storage limit overrides in hours",
                default_value=24,
                validation_rules={"min": 1, "max": 168},
                requires_restart=False
            ),
            "storage_email_notification_enabled": ConfigurationSchema(
                key="storage_email_notification_enabled",
                data_type=ConfigurationDataType.BOOLEAN,
                category=ConfigurationCategory.STORAGE,
                description="Enable email notifications for storage limit events",
                default_value=True,
                requires_restart=False
            ),
            "storage_email_rate_limit_hours": ConfigurationSchema(
                key="storage_email_rate_limit_hours",
                data_type=ConfigurationDataType.INTEGER,
                category=ConfigurationCategory.STORAGE,
                description="Rate limit for storage email notifications in hours",
                default_value=24,
                validation_rules={"min": 1, "max": 168},
                requires_restart=False
            )
        })
        
        return schema
    
    def get_configuration(self, key: str, admin_user_id: int = None) -> Optional[Any]:
        """
        Get a configuration value with environment override support
        
        Args:
            key: Configuration key
            admin_user_id: Admin user ID (for sensitive configs)
            
        Returns:
            Configuration value or None if not found
        """
        try:
            # Check for environment override first
            env_key = f"{self._environment_prefix}{key.upper()}"
            env_value = os.getenv(env_key)
            
            if env_value is not None:
                schema = self._configuration_schema.get(key)
                if schema:
                    return self._convert_value(env_value, schema.data_type)
                return env_value
            
            # Get from database
            with self.db_manager.get_session() as session:
                config = session.query(SystemConfiguration).filter_by(key=key).first()
                
                if config:
                    # Check if sensitive and user is authorized
                    if config.is_sensitive and admin_user_id:
                        self._verify_admin_authorization(session, admin_user_id)
                    
                    return config.get_typed_value()
                
                # Return default value if available
                schema = self._configuration_schema.get(key)
                if schema:
                    return schema.default_value
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting configuration {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
            return None
    
    def set_configuration(self, key: str, value: Any, admin_user_id: int, 
                         reason: str = "") -> bool:
        """
        Set a configuration value with validation and audit trail
        
        Args:
            key: Configuration key
            value: Configuration value
            admin_user_id: Admin user ID performing the change
            reason: Reason for the change
            
        Returns:
            bool: True if successful
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                self._verify_admin_authorization(session, admin_user_id)
                
                # Validate configuration
                validation_result = self._validate_configuration(key, value)
                if not validation_result.is_valid:
                    logger.error(f"Configuration validation failed for {sanitize_for_log(key)}: {validation_result.errors}")
                    return False
                
                # Get existing configuration
                existing_config = session.query(SystemConfiguration).filter_by(key=key).first()
                old_value = existing_config.get_typed_value() if existing_config else None
                
                # Create or update configuration
                if existing_config:
                    existing_config.set_typed_value(value)
                    existing_config.updated_by = admin_user_id
                    existing_config.updated_at = datetime.now(timezone.utc)
                else:
                    schema = self._configuration_schema.get(key)
                    new_config = SystemConfiguration(
                        key=key,
                        data_type=schema.data_type.value if schema else ConfigurationDataType.STRING.value,
                        category=schema.category.value if schema else ConfigurationCategory.SYSTEM.value,
                        description=schema.description if schema else f"Configuration for {key}",
                        is_sensitive=schema.is_sensitive if schema else False,
                        updated_by=admin_user_id,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    new_config.set_typed_value(value)
                    session.add(new_config)
                
                # Create audit trail
                self._create_configuration_audit(session, key, old_value, value, 
                                               admin_user_id, reason)
                
                session.commit()
                logger.info(f"Configuration {sanitize_for_log(key)} updated by admin {sanitize_for_log(str(admin_user_id))}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting configuration {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
            return False
    
    def get_all_configurations(self, admin_user_id: int, 
                              category: Optional[ConfigurationCategory] = None,
                              include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Get all configurations, optionally filtered by category
        
        Args:
            admin_user_id: Admin user ID
            category: Optional category filter
            include_sensitive: Whether to include sensitive configurations
            
        Returns:
            Dictionary of configuration key-value pairs
        """
        try:
            with self.db_manager.get_session() as session:
                self._verify_admin_authorization(session, admin_user_id)
                
                query = session.query(SystemConfiguration)
                
                if category:
                    query = query.filter_by(category=category.value)
                
                if not include_sensitive:
                    query = query.filter_by(is_sensitive=False)
                
                configs = query.all()
                
                result = {}
                for config in configs:
                    # Check for environment override
                    env_key = f"{self._environment_prefix}{config.key.upper()}"
                    env_value = os.getenv(env_key)
                    
                    if env_value is not None:
                        schema = self._configuration_schema.get(config.key)
                        if schema:
                            result[config.key] = self._convert_value(env_value, schema.data_type)
                        else:
                            result[config.key] = env_value
                    else:
                        result[config.key] = config.get_typed_value()
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting all configurations: {sanitize_for_log(str(e))}")
            return {}
    
    def validate_configuration_set(self, configurations: Dict[str, Any]) -> ConfigurationValidationResult:
        """
        Validate a set of configurations for conflicts and consistency
        
        Args:
            configurations: Dictionary of configuration key-value pairs
            
        Returns:
            ConfigurationValidationResult with validation details
        """
        errors = []
        warnings = []
        conflicts = []
        
        try:
            # Validate individual configurations
            for key, value in configurations.items():
                validation = self._validate_configuration(key, value)
                if not validation.is_valid:
                    errors.extend([f"{key}: {error}" for error in validation.errors])
                warnings.extend([f"{key}: {warning}" for warning in validation.warnings])
            
            # Check for conflicts between configurations
            conflicts.extend(self._check_configuration_conflicts(configurations))
            
            return ConfigurationValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                conflicts=conflicts
            )
            
        except Exception as e:
            logger.error(f"Error validating configuration set: {sanitize_for_log(str(e))}")
            return ConfigurationValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                conflicts=[]
            )
    
    def export_configurations(self, admin_user_id: int, 
                             category: Optional[ConfigurationCategory] = None,
                             include_sensitive: bool = False) -> Optional[ConfigurationExport]:
        """
        Export configurations to a structured format
        
        Args:
            admin_user_id: Admin user ID performing export
            category: Optional category filter
            include_sensitive: Whether to include sensitive configurations
            
        Returns:
            ConfigurationExport object or None if failed
        """
        try:
            configurations = self.get_all_configurations(admin_user_id, category, include_sensitive)
            
            metadata = {
                "export_version": "1.0",
                "schema_version": "1.0",
                "category_filter": category.value if category else None,
                "includes_sensitive": include_sensitive,
                "total_configurations": len(configurations)
            }
            
            return ConfigurationExport(
                configurations=configurations,
                metadata=metadata,
                export_timestamp=datetime.now(timezone.utc),
                exported_by=admin_user_id
            )
            
        except Exception as e:
            logger.error(f"Error exporting configurations: {sanitize_for_log(str(e))}")
            return None
    
    def import_configurations(self, export_data: ConfigurationExport, 
                             admin_user_id: int, 
                             validate_only: bool = False,
                             overwrite_existing: bool = False) -> Tuple[bool, List[str]]:
        """
        Import configurations from export data
        
        Args:
            export_data: ConfigurationExport object
            admin_user_id: Admin user ID performing import
            validate_only: Only validate, don't actually import
            overwrite_existing: Whether to overwrite existing configurations
            
        Returns:
            Tuple of (success, list of messages)
        """
        messages = []
        
        try:
            # Validate the import data
            validation_result = self.validate_configuration_set(export_data.configurations)
            
            if not validation_result.is_valid:
                messages.extend([f"Validation error: {error}" for error in validation_result.errors])
                return False, messages
            
            if validation_result.warnings:
                messages.extend([f"Warning: {warning}" for warning in validation_result.warnings])
            
            if validation_result.conflicts:
                messages.extend([f"Conflict: {conflict}" for conflict in validation_result.conflicts])
            
            if validate_only:
                messages.append("Validation completed successfully")
                return True, messages
            
            # Import configurations
            imported_count = 0
            skipped_count = 0
            
            for key, value in export_data.configurations.items():
                # Check if configuration exists
                existing_value = self.get_configuration(key, admin_user_id)
                
                if existing_value is not None and not overwrite_existing:
                    messages.append(f"Skipped existing configuration: {key}")
                    skipped_count += 1
                    continue
                
                # Import the configuration
                if self.set_configuration(key, value, admin_user_id, 
                                        reason=f"Imported from export at {export_data.export_timestamp}"):
                    imported_count += 1
                    messages.append(f"Imported configuration: {key}")
                else:
                    messages.append(f"Failed to import configuration: {key}")
            
            messages.append(f"Import completed: {imported_count} imported, {skipped_count} skipped")
            return True, messages
            
        except Exception as e:
            logger.error(f"Error importing configurations: {sanitize_for_log(str(e))}")
            messages.append(f"Import error: {str(e)}")
            return False, messages
    
    def get_configuration_history(self, key: str, admin_user_id: int, 
                                 limit: int = 50) -> List[ConfigurationChange]:
        """
        Get configuration change history
        
        Args:
            key: Configuration key
            admin_user_id: Admin user ID
            limit: Maximum number of changes to return
            
        Returns:
            List of ConfigurationChange objects
        """
        try:
            with self.db_manager.get_session() as session:
                self._verify_admin_authorization(session, admin_user_id)
                
                audit_logs = session.query(JobAuditLog).filter(
                    JobAuditLog.action == "configuration_change",
                    JobAuditLog.details.contains(f'"key": "{key}"')
                ).order_by(JobAuditLog.timestamp.desc()).limit(limit).all()
                
                changes = []
                for log in audit_logs:
                    try:
                        details = json.loads(log.details)
                        if details.get("key") == key:
                            changes.append(ConfigurationChange(
                                key=key,
                                old_value=details.get("old_value"),
                                new_value=details.get("new_value"),
                                changed_by=log.admin_user_id or log.user_id,
                                changed_at=log.timestamp,
                                reason=details.get("reason", "")
                            ))
                    except json.JSONDecodeError:
                        continue
                
                return changes
                
        except Exception as e:
            logger.error(f"Error getting configuration history for {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
            return []
    
    def rollback_configuration(self, key: str, target_timestamp: datetime, 
                              admin_user_id: int, reason: str = "") -> bool:
        """
        Rollback a configuration to a previous value
        
        Args:
            key: Configuration key
            target_timestamp: Timestamp to rollback to
            admin_user_id: Admin user ID performing rollback
            reason: Reason for rollback
            
        Returns:
            bool: True if successful
        """
        try:
            # Get configuration history
            history = self.get_configuration_history(key, admin_user_id)
            
            # Find the configuration value at the target timestamp
            target_value = None
            for change in reversed(history):  # Reverse to go chronologically
                if change.changed_at <= target_timestamp:
                    target_value = change.new_value
                    break
            
            if target_value is None:
                logger.error(f"No configuration value found for {sanitize_for_log(key)} at {target_timestamp}")
                return False
            
            # Set the configuration to the target value
            rollback_reason = f"Rollback to {target_timestamp}: {reason}"
            return self.set_configuration(key, target_value, admin_user_id, rollback_reason)
            
        except Exception as e:
            logger.error(f"Error rolling back configuration {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
            return False
    
    def get_configuration_schema(self, key: Optional[str] = None) -> Union[Dict[str, ConfigurationSchema], ConfigurationSchema, None]:
        """
        Get configuration schema information
        
        Args:
            key: Optional specific configuration key
            
        Returns:
            Schema information for key or all schemas
        """
        if key:
            return self._configuration_schema.get(key)
        return self._configuration_schema
    
    def get_configuration_documentation(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive configuration documentation
        
        Returns:
            Dictionary with configuration documentation
        """
        documentation = {}
        
        for category in ConfigurationCategory:
            documentation[category.value] = {
                "name": category.value.title(),
                "description": self._get_category_description(category),
                "configurations": []
            }
        
        for key, schema in self._configuration_schema.items():
            config_doc = {
                "key": key,
                "description": schema.description,
                "data_type": schema.data_type.value,
                "default_value": schema.default_value,
                "is_sensitive": schema.is_sensitive,
                "validation_rules": schema.validation_rules or {},
                "environment_override": schema.environment_override,
                "requires_restart": schema.requires_restart
            }
            
            documentation[schema.category.value]["configurations"].append(config_doc)
        
        return documentation
    
    def _validate_configuration(self, key: str, value: Any) -> ConfigurationValidationResult:
        """Validate a single configuration"""
        errors = []
        warnings = []
        
        schema = self._configuration_schema.get(key)
        if not schema:
            warnings.append(f"No schema defined for configuration key: {key}")
            return ConfigurationValidationResult(True, errors, warnings, [])
        
        # Type validation
        try:
            converted_value = self._convert_value(value, schema.data_type)
        except (ValueError, TypeError) as e:
            errors.append(f"Invalid type for {key}: {str(e)}")
            return ConfigurationValidationResult(False, errors, warnings, [])
        
        # Validation rules
        if schema.validation_rules:
            rules = schema.validation_rules
            
            if "min" in rules and converted_value < rules["min"]:
                errors.append(f"Value {converted_value} is below minimum {rules['min']} for {key}")
            
            if "max" in rules and converted_value > rules["max"]:
                errors.append(f"Value {converted_value} is above maximum {rules['max']} for {key}")
            
            if "allowed_values" in rules and converted_value not in rules["allowed_values"]:
                errors.append(f"Value {converted_value} not in allowed values {rules['allowed_values']} for {key}")
        
        return ConfigurationValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _check_configuration_conflicts(self, configurations: Dict[str, Any]) -> List[str]:
        """Check for conflicts between configurations"""
        conflicts = []
        
        # Example conflict checks
        if "max_concurrent_jobs" in configurations and "queue_size_limit" in configurations:
            max_jobs = configurations["max_concurrent_jobs"]
            queue_limit = configurations["queue_size_limit"]
            if max_jobs > queue_limit:
                conflicts.append("max_concurrent_jobs cannot exceed queue_size_limit")
        
        if "rate_limit_per_user_per_hour" in configurations and "max_concurrent_jobs" in configurations:
            rate_limit = configurations["rate_limit_per_user_per_hour"]
            max_jobs = configurations["max_concurrent_jobs"]
            if rate_limit < max_jobs:
                conflicts.append("rate_limit_per_user_per_hour should be >= max_concurrent_jobs")
        
        return conflicts
    
    def _convert_value(self, value: Any, data_type: ConfigurationDataType) -> Any:
        """Convert value to the specified data type"""
        if value is None:
            return None
        
        if data_type == ConfigurationDataType.INTEGER:
            return int(value)
        elif data_type == ConfigurationDataType.FLOAT:
            return float(value)
        elif data_type == ConfigurationDataType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif data_type == ConfigurationDataType.JSON:
            if isinstance(value, str):
                return json.loads(value)
            return value
        else:  # STRING
            return str(value)
    
    def _create_configuration_audit(self, session: Session, key: str, old_value: Any, 
                                   new_value: Any, admin_user_id: int, reason: str):
        """Create audit trail for configuration change"""
        audit_details = {
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason
        }
        
        audit_log = JobAuditLog(
            task_id=None,  # Configuration changes don't have task IDs
            user_id=None,
            admin_user_id=admin_user_id,
            action="configuration_change",
            details=json.dumps(audit_details),
            timestamp=datetime.now(timezone.utc),
            ip_address="",  # Could be populated from request context
            user_agent=""   # Could be populated from request context
        )
        
        session.add(audit_log)
    
    def _verify_admin_authorization(self, session: Session, admin_user_id: int):
        """Verify that the user has admin authorization"""
        admin_user = session.query(User).filter_by(id=admin_user_id).first()
        if not admin_user or admin_user.role != UserRole.ADMIN:
            raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
    
    def _get_category_description(self, category: ConfigurationCategory) -> str:
        """Get description for configuration category"""
        descriptions = {
            ConfigurationCategory.SYSTEM: "Core system settings and operational parameters",
            ConfigurationCategory.PERFORMANCE: "Performance tuning and resource management settings",
            ConfigurationCategory.SECURITY: "Security policies and access control settings",
            ConfigurationCategory.LIMITS: "Resource limits and quotas",
            ConfigurationCategory.ALERTS: "Alert thresholds and notification settings",
            ConfigurationCategory.MAINTENANCE: "Maintenance mode and system status settings",
            ConfigurationCategory.FEATURES: "Feature flags and optional functionality",
            ConfigurationCategory.STORAGE: "Storage limit management and monitoring settings"
        }
        return descriptions.get(category, "Configuration settings")
    
    def initialize_default_configurations(self, admin_user_id: int) -> Tuple[int, List[str]]:
        """
        Initialize default configurations in the database
        
        Creates database records for all schema-defined configurations that don't already exist,
        using their default values from the schema.
        
        Args:
            admin_user_id: Admin user ID performing the initialization
            
        Returns:
            Tuple of (created_count, list of messages)
        """
        messages = []
        created_count = 0
        
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                self._verify_admin_authorization(session, admin_user_id)
                
                # Get existing configuration keys
                existing_configs = session.query(SystemConfiguration.key).all()
                existing_keys = {config.key for config in existing_configs}
                
                # Create configurations for schema entries that don't exist in database
                for key, schema in self._configuration_schema.items():
                    if key not in existing_keys:
                        # Create new configuration with default value
                        new_config = SystemConfiguration(
                            key=key,
                            data_type=schema.data_type.value,
                            category=schema.category.value,
                            description=schema.description,
                            is_sensitive=schema.is_sensitive,
                            updated_by=admin_user_id,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc)
                        )
                        
                        # Set the default value
                        if schema.default_value is not None:
                            new_config.set_typed_value(schema.default_value)
                        
                        session.add(new_config)
                        created_count += 1
                        messages.append(f"Created configuration: {key} = {schema.default_value}")
                        
                        # Create audit trail
                        self._create_configuration_audit(
                            session, key, None, schema.default_value, 
                            admin_user_id, "Initial configuration setup"
                        )
                
                session.commit()
                
                if created_count > 0:
                    messages.append(f"Successfully initialized {created_count} default configurations")
                    logger.info(f"Initialized {created_count} default configurations for admin {sanitize_for_log(str(admin_user_id))}")
                else:
                    messages.append("All configurations already exist in database")
                
                return created_count, messages
                
        except Exception as e:
            logger.error(f"Error initializing default configurations: {sanitize_for_log(str(e))}")
            messages.append(f"Error initializing configurations: {str(e)}")
            return 0, messages