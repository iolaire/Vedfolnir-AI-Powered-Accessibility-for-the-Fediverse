# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Configuration Management Routes

Provides REST API endpoints for comprehensive system configuration management
including validation, audit trails, export/import, and rollback capabilities.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.exceptions import BadRequest

from system_configuration_manager import (
    SystemConfigurationManager, ConfigurationCategory, 
    ConfigurationExport, ConfigurationValidationResult
)
from security.core.security_utils import sanitize_for_log
from security.core.role_based_access import require_admin

logger = logging.getLogger(__name__)

# Create blueprint
configuration_bp = Blueprint('admin_configuration', __name__, url_prefix='/admin/api/configuration')


@configuration_bp.route('/schema', methods=['GET'])
@require_admin
def get_configuration_schema():
    """Get configuration schema information"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        key = request.args.get('key')
        schema = config_manager.get_configuration_schema(key)
        
        if key and not schema:
            return jsonify({"error": f"Schema not found for key: {key}"}), 404
        
        # Convert schema objects to dictionaries for JSON serialization
        if key:
            schema_dict = {
                "key": schema.key,
                "data_type": schema.data_type.value,
                "category": schema.category.value,
                "description": schema.description,
                "default_value": schema.default_value,
                "is_sensitive": schema.is_sensitive,
                "validation_rules": schema.validation_rules or {},
                "environment_override": schema.environment_override,
                "requires_restart": schema.requires_restart
            }
            return jsonify({"schema": schema_dict})
        else:
            schemas_dict = {}
            for k, s in schema.items():
                schemas_dict[k] = {
                    "key": s.key,
                    "data_type": s.data_type.value,
                    "category": s.category.value,
                    "description": s.description,
                    "default_value": s.default_value,
                    "is_sensitive": s.is_sensitive,
                    "validation_rules": s.validation_rules or {},
                    "environment_override": s.environment_override,
                    "requires_restart": s.requires_restart
                }
            return jsonify({"schemas": schemas_dict})
        
    except Exception as e:
        logger.error(f"Error getting configuration schema: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to get configuration schema"}), 500


@configuration_bp.route('/documentation', methods=['GET'])
@require_admin
def get_configuration_documentation():
    """Get comprehensive configuration documentation"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        documentation = config_manager.get_configuration_documentation()
        return jsonify({"documentation": documentation})
        
    except Exception as e:
        logger.error(f"Error getting configuration documentation: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to get configuration documentation"}), 500


@configuration_bp.route('/', methods=['GET'])
@require_admin
def get_configurations():
    """Get all configurations, optionally filtered by category"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        # Parse query parameters
        category_str = request.args.get('category')
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        
        category = None
        if category_str:
            try:
                category = ConfigurationCategory(category_str)
            except ValueError:
                return jsonify({"error": f"Invalid category: {category_str}"}), 400
        
        configurations = config_manager.get_all_configurations(
            admin_user_id, category, include_sensitive
        )
        
        return jsonify({
            "configurations": configurations,
            "category": category.value if category else None,
            "include_sensitive": include_sensitive,
            "total_count": len(configurations)
        })
        
    except Exception as e:
        logger.error(f"Error getting configurations: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to get configurations"}), 500


@configuration_bp.route('/<key>', methods=['GET'])
@require_admin
def get_configuration(key: str):
    """Get a specific configuration value"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        value = config_manager.get_configuration(key, admin_user_id)
        
        if value is None:
            return jsonify({"error": f"Configuration not found: {key}"}), 404
        
        return jsonify({
            "key": key,
            "value": value
        })
        
    except Exception as e:
        logger.error(f"Error getting configuration {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
        return jsonify({"error": f"Failed to get configuration: {key}"}), 500


@configuration_bp.route('/<key>', methods=['PUT'])
@require_admin
def set_configuration(key: str):
    """Set a configuration value"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({"error": "Request must contain 'value' field"}), 400
        
        value = data['value']
        reason = data.get('reason', '')
        
        success = config_manager.set_configuration(key, value, admin_user_id, reason)
        
        if success:
            return jsonify({
                "message": f"Configuration {key} updated successfully",
                "key": key,
                "value": value
            })
        else:
            return jsonify({"error": f"Failed to update configuration: {key}"}), 500
        
    except Exception as e:
        logger.error(f"Error setting configuration {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
        return jsonify({"error": f"Failed to set configuration: {key}"}), 500


@configuration_bp.route('/batch', methods=['PUT'])
@require_admin
def set_configurations_batch():
    """Set multiple configurations in a batch"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        data = request.get_json()
        if not data or 'configurations' not in data:
            return jsonify({"error": "Request must contain 'configurations' field"}), 400
        
        configurations = data['configurations']
        reason = data.get('reason', 'Batch configuration update')
        validate_only = data.get('validate_only', False)
        
        # Validate configurations first
        validation_result = config_manager.validate_configuration_set(configurations)
        
        if not validation_result.is_valid:
            return jsonify({
                "error": "Configuration validation failed",
                "validation_errors": validation_result.errors,
                "validation_warnings": validation_result.warnings,
                "conflicts": validation_result.conflicts
            }), 400
        
        if validate_only:
            return jsonify({
                "message": "Configuration validation successful",
                "validation_warnings": validation_result.warnings,
                "conflicts": validation_result.conflicts
            })
        
        # Apply configurations
        success_count = 0
        failed_configs = []
        
        for key, value in configurations.items():
            if config_manager.set_configuration(key, value, admin_user_id, reason):
                success_count += 1
            else:
                failed_configs.append(key)
        
        return jsonify({
            "message": f"Batch update completed: {success_count} successful, {len(failed_configs)} failed",
            "success_count": success_count,
            "failed_configurations": failed_configs,
            "validation_warnings": validation_result.warnings,
            "conflicts": validation_result.conflicts
        })
        
    except Exception as e:
        logger.error(f"Error in batch configuration update: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to update configurations"}), 500


@configuration_bp.route('/validate', methods=['POST'])
@require_admin
def validate_configurations():
    """Validate a set of configurations"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        data = request.get_json()
        if not data or 'configurations' not in data:
            return jsonify({"error": "Request must contain 'configurations' field"}), 400
        
        configurations = data['configurations']
        validation_result = config_manager.validate_configuration_set(configurations)
        
        return jsonify({
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "conflicts": validation_result.conflicts
        })
        
    except Exception as e:
        logger.error(f"Error validating configurations: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to validate configurations"}), 500


@configuration_bp.route('/<key>/history', methods=['GET'])
@require_admin
def get_configuration_history(key: str):
    """Get configuration change history"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        limit = int(request.args.get('limit', 50))
        history = config_manager.get_configuration_history(key, admin_user_id, limit)
        
        # Convert history to JSON-serializable format
        history_data = []
        for change in history:
            history_data.append({
                "key": change.key,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "changed_by": change.changed_by,
                "changed_at": change.changed_at.isoformat(),
                "reason": change.reason
            })
        
        return jsonify({
            "key": key,
            "history": history_data,
            "total_changes": len(history_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting configuration history for {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
        return jsonify({"error": f"Failed to get configuration history: {key}"}), 500


@configuration_bp.route('/<key>/rollback', methods=['POST'])
@require_admin
def rollback_configuration(key: str):
    """Rollback a configuration to a previous value"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        data = request.get_json()
        if not data or 'target_timestamp' not in data:
            return jsonify({"error": "Request must contain 'target_timestamp' field"}), 400
        
        target_timestamp = datetime.fromisoformat(data['target_timestamp'].replace('Z', '+00:00'))
        reason = data.get('reason', 'Configuration rollback')
        
        success = config_manager.rollback_configuration(key, target_timestamp, admin_user_id, reason)
        
        if success:
            return jsonify({
                "message": f"Configuration {key} rolled back successfully",
                "key": key,
                "target_timestamp": target_timestamp.isoformat()
            })
        else:
            return jsonify({"error": f"Failed to rollback configuration: {key}"}), 500
        
    except Exception as e:
        logger.error(f"Error rolling back configuration {sanitize_for_log(key)}: {sanitize_for_log(str(e))}")
        return jsonify({"error": f"Failed to rollback configuration: {key}"}), 500


@configuration_bp.route('/export', methods=['GET'])
@require_admin
def export_configurations():
    """Export configurations to a structured format"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        # Parse query parameters
        category_str = request.args.get('category')
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        
        category = None
        if category_str:
            try:
                category = ConfigurationCategory(category_str)
            except ValueError:
                return jsonify({"error": f"Invalid category: {category_str}"}), 400
        
        export_data = config_manager.export_configurations(admin_user_id, category, include_sensitive)
        
        if not export_data:
            return jsonify({"error": "Failed to export configurations"}), 500
        
        return jsonify({
            "configurations": export_data.configurations,
            "metadata": export_data.metadata,
            "export_timestamp": export_data.export_timestamp.isoformat(),
            "exported_by": export_data.exported_by
        })
        
    except Exception as e:
        logger.error(f"Error exporting configurations: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to export configurations"}), 500


@configuration_bp.route('/import', methods=['POST'])
@require_admin
def import_configurations():
    """Import configurations from export data"""
    try:
        config_manager: SystemConfigurationManager = current_app.config.get('system_configuration_manager')
        if not config_manager:
            return jsonify({"error": "Configuration manager not available"}), 500
        
        admin_user_id = session.get('user_id')
        if not admin_user_id:
            return jsonify({"error": "Admin user ID not found in session"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request must contain import data"}), 400
        
        # Validate required fields
        required_fields = ['configurations', 'metadata', 'export_timestamp', 'exported_by']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create ConfigurationExport object
        export_data = ConfigurationExport(
            configurations=data['configurations'],
            metadata=data['metadata'],
            export_timestamp=datetime.fromisoformat(data['export_timestamp'].replace('Z', '+00:00')),
            exported_by=data['exported_by']
        )
        
        validate_only = data.get('validate_only', False)
        overwrite_existing = data.get('overwrite_existing', False)
        
        success, messages = config_manager.import_configurations(
            export_data, admin_user_id, validate_only, overwrite_existing
        )
        
        return jsonify({
            "success": success,
            "messages": messages,
            "validate_only": validate_only,
            "overwrite_existing": overwrite_existing
        })
        
    except Exception as e:
        logger.error(f"Error importing configurations: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to import configurations"}), 500


@configuration_bp.route('/categories', methods=['GET'])
@require_admin
def get_configuration_categories():
    """Get available configuration categories"""
    try:
        categories = []
        for category in ConfigurationCategory:
            categories.append({
                "value": category.value,
                "name": category.value.title(),
                "description": _get_category_description(category)
            })
        
        return jsonify({"categories": categories})
        
    except Exception as e:
        logger.error(f"Error getting configuration categories: {sanitize_for_log(str(e))}")
        return jsonify({"error": "Failed to get configuration categories"}), 500


def _get_category_description(category: ConfigurationCategory) -> str:
    """Get description for configuration category"""
    descriptions = {
        ConfigurationCategory.SYSTEM: "Core system settings and operational parameters",
        ConfigurationCategory.PERFORMANCE: "Performance tuning and resource management settings",
        ConfigurationCategory.SECURITY: "Security policies and access control settings",
        ConfigurationCategory.LIMITS: "Resource limits and quotas",
        ConfigurationCategory.ALERTS: "Alert thresholds and notification settings",
        ConfigurationCategory.MAINTENANCE: "Maintenance mode and system status settings",
        ConfigurationCategory.FEATURES: "Feature flags and optional functionality"
    }
    return descriptions.get(category, "Configuration settings")