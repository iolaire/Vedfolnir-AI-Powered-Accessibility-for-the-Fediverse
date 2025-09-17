# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Retention Configuration

Provides configuration management for RQ data retention policies,
including environment-based policy selection and custom policy definitions.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from .retention_policy import RetentionPolicy

logger = logging.getLogger(__name__)


@dataclass
class RQRetentionConfig:
    """Configuration for RQ data retention system"""
    
    # Active policy selection
    active_policy_name: str = "default"
    
    # Monitoring configuration
    monitoring_enabled: bool = True
    monitoring_interval: int = 300  # 5 minutes
    
    # Memory thresholds (overrides for policy defaults)
    memory_warning_threshold_mb: Optional[int] = None
    memory_critical_threshold_mb: Optional[int] = None
    
    # Cleanup configuration
    auto_cleanup_enabled: bool = True
    emergency_cleanup_enabled: bool = True
    cleanup_batch_size: Optional[int] = None
    
    # TTL overrides (in seconds)
    completed_tasks_ttl_override: Optional[int] = None
    failed_tasks_ttl_override: Optional[int] = None
    cancelled_tasks_ttl_override: Optional[int] = None
    progress_data_ttl_override: Optional[int] = None
    security_logs_ttl_override: Optional[int] = None
    
    # Custom policies
    custom_policies: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize custom policies if not provided"""
        if self.custom_policies is None:
            self.custom_policies = {}


class RQRetentionConfigManager:
    """Manages RQ retention configuration from environment and custom settings"""
    
    def __init__(self):
        """Initialize retention configuration manager"""
        self.config = self._load_configuration()
        self._validate_configuration()
        
        logger.info(f"RQ Retention Configuration loaded with policy: {self.config.active_policy_name}")
    
    def _load_configuration(self) -> RQRetentionConfig:
        """Load configuration from environment variables and defaults"""
        try:
            config = RQRetentionConfig()
            
            # Load from environment variables
            config.active_policy_name = os.getenv('RQ_RETENTION_POLICY', 'default')
            
            # Monitoring configuration
            config.monitoring_enabled = os.getenv('RQ_RETENTION_MONITORING_ENABLED', 'true').lower() == 'true'
            config.monitoring_interval = int(os.getenv('RQ_RETENTION_MONITORING_INTERVAL', '300'))
            
            # Memory thresholds
            if os.getenv('RQ_MEMORY_WARNING_THRESHOLD_MB'):
                config.memory_warning_threshold_mb = int(os.getenv('RQ_MEMORY_WARNING_THRESHOLD_MB'))
            
            if os.getenv('RQ_MEMORY_CRITICAL_THRESHOLD_MB'):
                config.memory_critical_threshold_mb = int(os.getenv('RQ_MEMORY_CRITICAL_THRESHOLD_MB'))
            
            # Cleanup configuration
            config.auto_cleanup_enabled = os.getenv('RQ_AUTO_CLEANUP_ENABLED', 'true').lower() == 'true'
            config.emergency_cleanup_enabled = os.getenv('RQ_EMERGENCY_CLEANUP_ENABLED', 'true').lower() == 'true'
            
            if os.getenv('RQ_CLEANUP_BATCH_SIZE'):
                config.cleanup_batch_size = int(os.getenv('RQ_CLEANUP_BATCH_SIZE'))
            
            # TTL overrides
            if os.getenv('RQ_COMPLETED_TASKS_TTL'):
                config.completed_tasks_ttl_override = int(os.getenv('RQ_COMPLETED_TASKS_TTL'))
            
            if os.getenv('RQ_FAILED_TASKS_TTL'):
                config.failed_tasks_ttl_override = int(os.getenv('RQ_FAILED_TASKS_TTL'))
            
            if os.getenv('RQ_CANCELLED_TASKS_TTL'):
                config.cancelled_tasks_ttl_override = int(os.getenv('RQ_CANCELLED_TASKS_TTL'))
            
            if os.getenv('RQ_PROGRESS_DATA_TTL'):
                config.progress_data_ttl_override = int(os.getenv('RQ_PROGRESS_DATA_TTL'))
            
            if os.getenv('RQ_SECURITY_LOGS_TTL'):
                config.security_logs_ttl_override = int(os.getenv('RQ_SECURITY_LOGS_TTL'))
            
            # Load custom policies from environment (JSON format)
            custom_policies_json = os.getenv('RQ_CUSTOM_POLICIES')
            if custom_policies_json:
                import json
                config.custom_policies = json.loads(custom_policies_json)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load RQ retention configuration: {e}")
            # Return default configuration on error
            return RQRetentionConfig()
    
    def _validate_configuration(self) -> None:
        """Validate configuration values"""
        try:
            # Validate monitoring interval
            if self.config.monitoring_interval < 60:
                logger.warning("Monitoring interval less than 60 seconds, setting to 60")
                self.config.monitoring_interval = 60
            
            # Validate memory thresholds
            if (self.config.memory_warning_threshold_mb and 
                self.config.memory_critical_threshold_mb and
                self.config.memory_warning_threshold_mb >= self.config.memory_critical_threshold_mb):
                logger.warning("Memory warning threshold >= critical threshold, adjusting")
                self.config.memory_warning_threshold_mb = int(self.config.memory_critical_threshold_mb * 0.8)
            
            # Validate TTL values
            ttl_fields = [
                'completed_tasks_ttl_override',
                'failed_tasks_ttl_override', 
                'cancelled_tasks_ttl_override',
                'progress_data_ttl_override',
                'security_logs_ttl_override'
            ]
            
            for field in ttl_fields:
                value = getattr(self.config, field)
                if value is not None and value < 60:
                    logger.warning(f"{field} less than 60 seconds, setting to 60")
                    setattr(self.config, field, 60)
            
            # Validate batch size
            if self.config.cleanup_batch_size and self.config.cleanup_batch_size < 10:
                logger.warning("Cleanup batch size less than 10, setting to 10")
                self.config.cleanup_batch_size = 10
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
    
    def get_config(self) -> RQRetentionConfig:
        """Get current retention configuration"""
        return self.config
    
    def create_retention_policy(self, policy_name: str) -> RetentionPolicy:
        """
        Create a retention policy based on configuration
        
        Args:
            policy_name: Name of the policy to create
            
        Returns:
            RetentionPolicy instance
        """
        try:
            # Check if it's a custom policy
            if policy_name in self.config.custom_policies:
                return self._create_custom_policy(policy_name)
            
            # Get base policy from predefined policies
            base_policies = self._get_predefined_policies()
            
            if policy_name not in base_policies:
                logger.warning(f"Unknown policy {policy_name}, using default")
                policy_name = 'default'
            
            policy = base_policies[policy_name]
            
            # Apply configuration overrides
            policy = self._apply_config_overrides(policy)
            
            return policy
            
        except Exception as e:
            logger.error(f"Failed to create retention policy {policy_name}: {e}")
            # Return default policy on error
            return self._get_predefined_policies()['default']
    
    def _create_custom_policy(self, policy_name: str) -> RetentionPolicy:
        """Create a custom retention policy from configuration"""
        try:
            custom_config = self.config.custom_policies[policy_name]
            
            policy = RetentionPolicy(
                name=policy_name,
                description=custom_config.get('description', f'Custom policy: {policy_name}'),
                completed_tasks_ttl=custom_config.get('completed_tasks_ttl', 86400),
                failed_tasks_ttl=custom_config.get('failed_tasks_ttl', 259200),
                cancelled_tasks_ttl=custom_config.get('cancelled_tasks_ttl', 43200),
                progress_data_ttl=custom_config.get('progress_data_ttl', 3600),
                security_logs_ttl=custom_config.get('security_logs_ttl', 604800),
                max_memory_usage_mb=custom_config.get('max_memory_usage_mb', 512),
                cleanup_threshold_mb=custom_config.get('cleanup_threshold_mb', 400),
                cleanup_batch_size=custom_config.get('cleanup_batch_size', 100),
                enabled=custom_config.get('enabled', True)
            )
            
            # Apply configuration overrides
            policy = self._apply_config_overrides(policy)
            
            return policy
            
        except Exception as e:
            logger.error(f"Failed to create custom policy {policy_name}: {e}")
            raise
    
    def _apply_config_overrides(self, policy: RetentionPolicy) -> RetentionPolicy:
        """Apply configuration overrides to a policy"""
        try:
            # Apply TTL overrides
            if self.config.completed_tasks_ttl_override is not None:
                policy.completed_tasks_ttl = self.config.completed_tasks_ttl_override
            
            if self.config.failed_tasks_ttl_override is not None:
                policy.failed_tasks_ttl = self.config.failed_tasks_ttl_override
            
            if self.config.cancelled_tasks_ttl_override is not None:
                policy.cancelled_tasks_ttl = self.config.cancelled_tasks_ttl_override
            
            if self.config.progress_data_ttl_override is not None:
                policy.progress_data_ttl = self.config.progress_data_ttl_override
            
            if self.config.security_logs_ttl_override is not None:
                policy.security_logs_ttl = self.config.security_logs_ttl_override
            
            # Apply memory threshold overrides
            if self.config.memory_critical_threshold_mb is not None:
                policy.max_memory_usage_mb = self.config.memory_critical_threshold_mb
            
            if self.config.memory_warning_threshold_mb is not None:
                policy.cleanup_threshold_mb = self.config.memory_warning_threshold_mb
            
            # Apply batch size override
            if self.config.cleanup_batch_size is not None:
                policy.cleanup_batch_size = self.config.cleanup_batch_size
            
            return policy
            
        except Exception as e:
            logger.error(f"Failed to apply configuration overrides: {e}")
            return policy
    
    def _get_predefined_policies(self) -> Dict[str, RetentionPolicy]:
        """Get predefined retention policies"""
        return {
            'default': RetentionPolicy(
                name='default',
                description='Default retention policy for production use',
                completed_tasks_ttl=86400,      # 24 hours
                failed_tasks_ttl=259200,        # 72 hours
                cancelled_tasks_ttl=43200,      # 12 hours
                progress_data_ttl=3600,         # 1 hour
                security_logs_ttl=604800,       # 7 days
                max_memory_usage_mb=512,        # 512 MB
                cleanup_threshold_mb=400,       # 400 MB
                cleanup_batch_size=100
            ),
            'development': RetentionPolicy(
                name='development',
                description='Development retention policy with shorter TTLs',
                completed_tasks_ttl=3600,       # 1 hour
                failed_tasks_ttl=7200,          # 2 hours
                cancelled_tasks_ttl=1800,       # 30 minutes
                progress_data_ttl=900,          # 15 minutes
                security_logs_ttl=86400,        # 1 day
                max_memory_usage_mb=128,        # 128 MB
                cleanup_threshold_mb=100,       # 100 MB
                cleanup_batch_size=50
            ),
            'high_volume': RetentionPolicy(
                name='high_volume',
                description='High volume retention policy with aggressive cleanup',
                completed_tasks_ttl=43200,      # 12 hours
                failed_tasks_ttl=86400,         # 24 hours
                cancelled_tasks_ttl=3600,       # 1 hour
                progress_data_ttl=1800,         # 30 minutes
                security_logs_ttl=259200,       # 3 days
                max_memory_usage_mb=1024,       # 1 GB
                cleanup_threshold_mb=800,       # 800 MB
                cleanup_batch_size=200
            ),
            'conservative': RetentionPolicy(
                name='conservative',
                description='Conservative retention policy with longer TTLs',
                completed_tasks_ttl=604800,     # 7 days
                failed_tasks_ttl=1209600,       # 14 days
                cancelled_tasks_ttl=259200,     # 3 days
                progress_data_ttl=86400,        # 1 day
                security_logs_ttl=2592000,      # 30 days
                max_memory_usage_mb=2048,       # 2 GB
                cleanup_threshold_mb=1600,      # 1.6 GB
                cleanup_batch_size=50
            )
        }
    
    def update_policy(self, policy_name: str, **kwargs) -> bool:
        """
        Update a custom policy or create a new one
        
        Args:
            policy_name: Name of the policy to update/create
            **kwargs: Policy parameters to update
            
        Returns:
            True if successful
        """
        try:
            if policy_name not in self.config.custom_policies:
                self.config.custom_policies[policy_name] = {}
            
            # Update policy parameters
            self.config.custom_policies[policy_name].update(kwargs)
            
            logger.info(f"Updated custom policy: {policy_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update policy {policy_name}: {e}")
            return False
    
    def delete_custom_policy(self, policy_name: str) -> bool:
        """
        Delete a custom policy
        
        Args:
            policy_name: Name of the policy to delete
            
        Returns:
            True if successful
        """
        try:
            if policy_name in self.config.custom_policies:
                del self.config.custom_policies[policy_name]
                logger.info(f"Deleted custom policy: {policy_name}")
                return True
            else:
                logger.warning(f"Custom policy not found: {policy_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete policy {policy_name}: {e}")
            return False
    
    def get_available_policies(self) -> Dict[str, str]:
        """
        Get list of available policies with descriptions
        
        Returns:
            Dictionary mapping policy names to descriptions
        """
        try:
            policies = {}
            
            # Add predefined policies
            predefined = self._get_predefined_policies()
            for name, policy in predefined.items():
                policies[name] = policy.description
            
            # Add custom policies
            for name, config in self.config.custom_policies.items():
                policies[name] = config.get('description', f'Custom policy: {name}')
            
            return policies
            
        except Exception as e:
            logger.error(f"Failed to get available policies: {e}")
            return {'default': 'Default retention policy'}
    
    def export_configuration(self) -> Dict[str, Any]:
        """
        Export current configuration as dictionary
        
        Returns:
            Configuration dictionary
        """
        try:
            return asdict(self.config)
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return {}
    
    def import_configuration(self, config_dict: Dict[str, Any]) -> bool:
        """
        Import configuration from dictionary
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            True if successful
        """
        try:
            # Validate required fields
            required_fields = ['active_policy_name']
            for field in required_fields:
                if field not in config_dict:
                    raise ValueError(f"Missing required field: {field}")
            
            # Update configuration
            for key, value in config_dict.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Re-validate configuration
            self._validate_configuration()
            
            logger.info("Configuration imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False


# Global configuration manager instance
_config_manager: Optional[RQRetentionConfigManager] = None


def get_retention_config_manager() -> RQRetentionConfigManager:
    """Get global retention configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = RQRetentionConfigManager()
    return _config_manager


def get_retention_config() -> RQRetentionConfig:
    """Get current retention configuration"""
    return get_retention_config_manager().get_config()


def create_retention_policy(policy_name: str = None) -> RetentionPolicy:
    """
    Create retention policy from configuration
    
    Args:
        policy_name: Optional policy name, uses active policy if not specified
        
    Returns:
        RetentionPolicy instance
    """
    config_manager = get_retention_config_manager()
    if policy_name is None:
        policy_name = config_manager.get_config().active_policy_name
    
    return config_manager.create_retention_policy(policy_name)