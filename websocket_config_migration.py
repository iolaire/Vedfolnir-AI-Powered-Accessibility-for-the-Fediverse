# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration Migration Tools

This module provides tools for migrating WebSocket configuration between
different versions, environments, and deployment scenarios.
"""

import os
import shutil
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from websocket_config_schema import WebSocketConfigSchema
from websocket_config_validator import WebSocketConfigValidator, ConfigurationReport


@dataclass
class MigrationStep:
    """Configuration migration step"""
    name: str
    description: str
    old_field: Optional[str] = None
    new_field: Optional[str] = None
    transformation: Optional[callable] = None
    validation: Optional[callable] = None
    required: bool = True


@dataclass
class MigrationPlan:
    """Configuration migration plan"""
    name: str
    description: str
    version_from: str
    version_to: str
    steps: List[MigrationStep] = field(default_factory=list)
    backup_required: bool = True
    rollback_supported: bool = True


@dataclass
class MigrationResult:
    """Migration execution result"""
    success: bool
    plan_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    steps_completed: int = 0
    steps_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    migrated_fields: Dict[str, Any] = field(default_factory=dict)


class WebSocketConfigMigration:
    """
    WebSocket configuration migration manager
    
    Handles migration of configuration between different versions,
    environments, and deployment scenarios with backup and rollback support.
    """
    
    def __init__(self):
        """Initialize migration manager"""
        self.schema = WebSocketConfigSchema()
        self.validator = WebSocketConfigValidator()
        self.logger = logging.getLogger(__name__)
        self._migration_plans = self._define_migration_plans()
    
    def _define_migration_plans(self) -> Dict[str, MigrationPlan]:
        """Define available migration plans"""
        return {
            "legacy_to_v1": MigrationPlan(
                name="legacy_to_v1",
                description="Migrate from legacy WebSocket configuration to v1.0",
                version_from="legacy",
                version_to="1.0",
                steps=[
                    MigrationStep(
                        name="migrate_cors_origins",
                        description="Migrate CORS_ALLOWED_ORIGINS to SOCKETIO_CORS_ORIGINS",
                        old_field="CORS_ALLOWED_ORIGINS",
                        new_field="SOCKETIO_CORS_ORIGINS",
                        transformation=lambda x: x  # Direct copy
                    ),
                    MigrationStep(
                        name="migrate_websocket_timeout",
                        description="Migrate WEBSOCKET_TIMEOUT to SOCKETIO_TIMEOUT",
                        old_field="WEBSOCKET_TIMEOUT",
                        new_field="SOCKETIO_TIMEOUT",
                        transformation=lambda x: str(int(x) * 1000)  # Convert seconds to milliseconds
                    ),
                    MigrationStep(
                        name="add_default_transports",
                        description="Add default transport configuration",
                        new_field="SOCKETIO_TRANSPORTS",
                        transformation=lambda: "websocket,polling"
                    ),
                    MigrationStep(
                        name="add_security_defaults",
                        description="Add default security configuration",
                        new_field="SOCKETIO_REQUIRE_AUTH",
                        transformation=lambda: "true"
                    )
                ]
            ),
            
            "development_to_production": MigrationPlan(
                name="development_to_production",
                description="Migrate configuration from development to production environment",
                version_from="development",
                version_to="production",
                steps=[
                    MigrationStep(
                        name="secure_cors_origins",
                        description="Replace wildcard CORS origins with specific domains",
                        old_field="SOCKETIO_CORS_ORIGINS",
                        new_field="SOCKETIO_CORS_ORIGINS",
                        transformation=self._transform_cors_for_production,
                        validation=self._validate_production_cors
                    ),
                    MigrationStep(
                        name="enable_security_features",
                        description="Enable all security features for production",
                        transformation=self._enable_production_security
                    ),
                    MigrationStep(
                        name="optimize_performance",
                        description="Apply production performance optimizations",
                        transformation=self._apply_production_performance
                    ),
                    MigrationStep(
                        name="configure_logging",
                        description="Configure production logging",
                        transformation=self._configure_production_logging
                    )
                ]
            ),
            
            "single_to_multi_instance": MigrationPlan(
                name="single_to_multi_instance",
                description="Migrate from single instance to multi-instance deployment",
                version_from="single",
                version_to="multi",
                steps=[
                    MigrationStep(
                        name="add_redis_session_backend",
                        description="Configure Redis session backend for multi-instance support",
                        transformation=self._configure_redis_backend
                    ),
                    MigrationStep(
                        name="configure_load_balancer_support",
                        description="Configure WebSocket for load balancer compatibility",
                        transformation=self._configure_load_balancer_support
                    ),
                    MigrationStep(
                        name="add_health_checks",
                        description="Add health check endpoints for load balancer",
                        transformation=self._add_health_checks
                    )
                ]
            )
        }
    
    def get_available_migrations(self) -> List[str]:
        """Get list of available migration plans"""
        return list(self._migration_plans.keys())
    
    def get_migration_plan(self, plan_name: str) -> Optional[MigrationPlan]:
        """Get migration plan by name"""
        return self._migration_plans.get(plan_name)
    
    def analyze_configuration_for_migration(self, env_file_path: str) -> Dict[str, Any]:
        """
        Analyze existing configuration for migration needs
        
        Args:
            env_file_path: Path to environment file
            
        Returns:
            Analysis results with migration recommendations
        """
        # Load existing configuration
        existing_config = self._load_env_file(env_file_path)
        
        # Validate current configuration
        report = self.validator.validate_configuration(existing_config)
        
        # Determine recommended migrations
        recommended_migrations = []
        
        # Check for legacy fields
        legacy_fields = ["CORS_ALLOWED_ORIGINS", "WEBSOCKET_TIMEOUT", "WS_PING_INTERVAL"]
        if any(field in existing_config for field in legacy_fields):
            recommended_migrations.append("legacy_to_v1")
        
        # Check for development patterns
        cors_origins = existing_config.get("SOCKETIO_CORS_ORIGINS", "")
        if cors_origins == "*" or "localhost" in cors_origins:
            env = existing_config.get("FLASK_ENV", "production")
            if env == "production":
                recommended_migrations.append("development_to_production")
        
        # Check for single instance patterns
        if "REDIS_URL" not in existing_config and "SOCKETIO_MAX_CONNECTIONS" not in existing_config:
            recommended_migrations.append("single_to_multi_instance")
        
        return {
            "current_configuration": existing_config,
            "validation_report": {
                "health_score": report.health_score,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "is_valid": report.is_valid
            },
            "recommended_migrations": recommended_migrations,
            "migration_urgency": self._assess_migration_urgency(report),
            "compatibility_issues": self._identify_compatibility_issues(existing_config)
        }
    
    def execute_migration(
        self,
        plan_name: str,
        env_file_path: str,
        backup_dir: Optional[str] = None,
        dry_run: bool = False
    ) -> MigrationResult:
        """
        Execute configuration migration
        
        Args:
            plan_name: Name of migration plan to execute
            env_file_path: Path to environment file
            backup_dir: Directory for backup files
            dry_run: If True, simulate migration without making changes
            
        Returns:
            Migration execution result
        """
        plan = self.get_migration_plan(plan_name)
        if not plan:
            return MigrationResult(
                success=False,
                plan_name=plan_name,
                errors=[f"Migration plan '{plan_name}' not found"]
            )
        
        result = MigrationResult(success=True, plan_name=plan_name)
        
        try:
            # Create backup if required
            if plan.backup_required and not dry_run:
                result.backup_path = self._create_backup(env_file_path, backup_dir)
                self.logger.info(f"Created backup at: {result.backup_path}")
            
            # Load existing configuration
            existing_config = self._load_env_file(env_file_path)
            migrated_config = existing_config.copy()
            
            # Execute migration steps
            for step in plan.steps:
                try:
                    self.logger.info(f"Executing migration step: {step.name}")
                    
                    if step.old_field and step.new_field:
                        # Field migration
                        if step.old_field in existing_config:
                            old_value = existing_config[step.old_field]
                            if step.transformation:
                                new_value = step.transformation(old_value)
                            else:
                                new_value = old_value
                            
                            migrated_config[step.new_field] = new_value
                            result.migrated_fields[step.new_field] = new_value
                            
                            # Remove old field
                            if step.old_field != step.new_field:
                                migrated_config.pop(step.old_field, None)
                    
                    elif step.new_field and step.transformation:
                        # New field addition
                        new_value = step.transformation()
                        migrated_config[step.new_field] = new_value
                        result.migrated_fields[step.new_field] = new_value
                    
                    elif step.transformation:
                        # Custom transformation
                        step.transformation(migrated_config)
                    
                    # Validate step if validation function provided
                    if step.validation:
                        if not step.validation(migrated_config):
                            raise ValueError(f"Step validation failed: {step.name}")
                    
                    result.steps_completed += 1
                    
                except Exception as e:
                    error_msg = f"Migration step '{step.name}' failed: {e}"
                    self.logger.error(error_msg)
                    result.errors.append(error_msg)
                    result.steps_failed += 1
                    
                    if step.required:
                        result.success = False
                        break
            
            # Validate final configuration
            if result.success:
                validation_report = self.validator.validate_configuration(migrated_config)
                if not validation_report.is_valid:
                    result.warnings.append("Migrated configuration has validation errors")
                    for error in validation_report.errors:
                        result.warnings.append(f"Validation error: {error.message}")
            
            # Write migrated configuration
            if result.success and not dry_run:
                self._write_env_file(env_file_path, migrated_config)
                self.logger.info(f"Migration completed successfully: {plan_name}")
            elif dry_run:
                self.logger.info(f"Dry run completed for migration: {plan_name}")
            
        except Exception as e:
            error_msg = f"Migration failed: {e}"
            self.logger.error(error_msg)
            result.success = False
            result.errors.append(error_msg)
        
        return result
    
    def rollback_migration(self, backup_path: str, env_file_path: str) -> bool:
        """
        Rollback migration using backup
        
        Args:
            backup_path: Path to backup file
            env_file_path: Path to environment file
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            shutil.copy2(backup_path, env_file_path)
            self.logger.info(f"Configuration rolled back from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def _load_env_file(self, file_path: str) -> Dict[str, str]:
        """Load environment variables from file"""
        config = {}
        
        if not os.path.exists(file_path):
            return config
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
        
        return config
    
    def _write_env_file(self, file_path: str, config: Dict[str, str]) -> None:
        """Write environment variables to file"""
        with open(file_path, 'w') as f:
            f.write("# WebSocket Configuration\n")
            f.write(f"# Migrated at: {datetime.now().isoformat()}\n\n")
            
            # Group by category for better organization
            categories = {}
            schema_fields = self.schema.get_schema_fields()
            
            for key, value in config.items():
                field_schema = schema_fields.get(key)
                category = field_schema.category if field_schema else "other"
                
                if category not in categories:
                    categories[category] = []
                categories[category].append((key, value))
            
            # Write configuration by category
            for category, fields in sorted(categories.items()):
                f.write(f"# {category.upper()} Configuration\n")
                for key, value in sorted(fields):
                    f.write(f"{key}={value}\n")
                f.write("\n")
    
    def _create_backup(self, env_file_path: str, backup_dir: Optional[str] = None) -> str:
        """Create backup of environment file"""
        if backup_dir is None:
            backup_dir = os.path.dirname(env_file_path)
        
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"websocket_config_backup_{timestamp}.env"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        shutil.copy2(env_file_path, backup_path)
        return backup_path
    
    def _assess_migration_urgency(self, report: ConfigurationReport) -> str:
        """Assess migration urgency based on validation report"""
        if report.health_score < 50:
            return "high"
        elif report.health_score < 75:
            return "medium"
        else:
            return "low"
    
    def _identify_compatibility_issues(self, config: Dict[str, str]) -> List[str]:
        """Identify compatibility issues in configuration"""
        issues = []
        
        # Check for deprecated fields
        deprecated_fields = ["CORS_ALLOWED_ORIGINS", "WEBSOCKET_TIMEOUT", "WS_PING_INTERVAL"]
        for field in deprecated_fields:
            if field in config:
                issues.append(f"Deprecated field '{field}' found")
        
        # Check for insecure configurations
        if config.get("SOCKETIO_CORS_ORIGINS") == "*":
            issues.append("Wildcard CORS origins pose security risk")
        
        # Check for missing required fields for production
        env = config.get("FLASK_ENV", "production")
        if env == "production":
            required_prod_fields = ["SOCKETIO_REQUIRE_AUTH", "SOCKETIO_CSRF_PROTECTION"]
            for field in required_prod_fields:
                if field not in config:
                    issues.append(f"Missing production field '{field}'")
        
        return issues
    
    # Migration transformation functions
    def _transform_cors_for_production(self, value: str) -> str:
        """Transform CORS origins for production environment"""
        if value == "*":
            # Replace wildcard with common production origins
            return "https://yourdomain.com,https://www.yourdomain.com"
        return value
    
    def _validate_production_cors(self, config: Dict[str, str]) -> bool:
        """Validate CORS configuration for production"""
        cors_origins = config.get("SOCKETIO_CORS_ORIGINS", "")
        return cors_origins != "*" and "localhost" not in cors_origins
    
    def _enable_production_security(self, config: Dict[str, str]) -> None:
        """Enable security features for production"""
        config.update({
            "SOCKETIO_REQUIRE_AUTH": "true",
            "SOCKETIO_SESSION_VALIDATION": "true",
            "SOCKETIO_RATE_LIMITING": "true",
            "SOCKETIO_CSRF_PROTECTION": "true"
        })
    
    def _apply_production_performance(self, config: Dict[str, str]) -> None:
        """Apply performance optimizations for production"""
        config.update({
            "SOCKETIO_MAX_CONNECTIONS": "5000",
            "SOCKETIO_CONNECTION_POOL_SIZE": "20",
            "SOCKETIO_PING_TIMEOUT": "120",
            "SOCKETIO_PING_INTERVAL": "30"
        })
    
    def _configure_production_logging(self, config: Dict[str, str]) -> None:
        """Configure logging for production"""
        config.update({
            "SOCKETIO_LOG_LEVEL": "WARNING",
            "SOCKETIO_LOG_CONNECTIONS": "false",
            "SOCKETIO_DEBUG": "false",
            "SOCKETIO_ENGINEIO_LOGGER": "false"
        })
    
    def _configure_redis_backend(self, config: Dict[str, str]) -> None:
        """Configure Redis backend for multi-instance support"""
        if "REDIS_URL" not in config:
            config["REDIS_URL"] = "redis://localhost:6379/0"
        
        config.update({
            "SESSION_STORAGE": "redis",
            "SOCKETIO_ASYNC_MODE": "eventlet"  # Better for multi-instance
        })
    
    def _configure_load_balancer_support(self, config: Dict[str, str]) -> None:
        """Configure WebSocket for load balancer compatibility"""
        config.update({
            "SOCKETIO_TRANSPORTS": "polling,websocket",  # Polling first for LB compatibility
            "SOCKETIO_PING_TIMEOUT": "60",
            "SOCKETIO_PING_INTERVAL": "25"
        })
    
    def _add_health_checks(self, config: Dict[str, str]) -> None:
        """Add health check configuration"""
        config.update({
            "HEALTH_CHECK_ENABLED": "true",
            "WEBSOCKET_HEALTH_CHECK_ENABLED": "true"
        })