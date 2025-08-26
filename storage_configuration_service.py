# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Configuration Service for managing storage limit settings.

This service handles configuration validation and management for storage limits,
including maximum storage size, warning thresholds, and monitoring settings.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StorageLimitConfig:
    """Configuration for storage limit management"""
    max_storage_gb: float
    warning_threshold_percentage: float
    monitoring_enabled: bool
    
    def get_warning_threshold_gb(self) -> float:
        """Calculate warning threshold in GB"""
        return self.max_storage_gb * (self.warning_threshold_percentage / 100.0)


class StorageConfigurationService:
    """
    Service for managing storage limit configuration and validation.
    
    This service handles:
    - Reading storage configuration from environment variables
    - Validating configuration values
    - Providing default values for missing configuration
    - Calculating derived values like warning thresholds
    """
    
    # Default configuration values
    DEFAULT_MAX_STORAGE_GB = 10.0
    DEFAULT_WARNING_THRESHOLD_PERCENTAGE = 80.0
    DEFAULT_MONITORING_ENABLED = True
    
    def __init__(self):
        """Initialize the storage configuration service"""
        self._config: Optional[StorageLimitConfig] = None
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load and validate configuration from environment variables"""
        try:
            # Read CAPTION_MAX_STORAGE_GB from environment
            max_storage_gb = self._get_max_storage_gb_from_env()
            
            # Read warning threshold percentage
            warning_threshold = self._get_warning_threshold_from_env()
            
            # Read monitoring enabled flag
            monitoring_enabled = self._get_monitoring_enabled_from_env()
            
            # Create configuration object
            self._config = StorageLimitConfig(
                max_storage_gb=max_storage_gb,
                warning_threshold_percentage=warning_threshold,
                monitoring_enabled=monitoring_enabled
            )
            
            logger.info(f"Storage configuration loaded: max_storage={max_storage_gb}GB, "
                       f"warning_threshold={warning_threshold}%, monitoring_enabled={monitoring_enabled}")
            
        except Exception as e:
            logger.error(f"Failed to load storage configuration: {e}")
            # Use default configuration on error
            self._config = StorageLimitConfig(
                max_storage_gb=self.DEFAULT_MAX_STORAGE_GB,
                warning_threshold_percentage=self.DEFAULT_WARNING_THRESHOLD_PERCENTAGE,
                monitoring_enabled=self.DEFAULT_MONITORING_ENABLED
            )
            logger.warning(f"Using default storage configuration: max_storage={self.DEFAULT_MAX_STORAGE_GB}GB")
    
    def _get_max_storage_gb_from_env(self) -> float:
        """
        Read and validate CAPTION_MAX_STORAGE_GB from environment variables.
        
        Returns:
            float: Maximum storage in GB
            
        Raises:
            ValueError: If the value is invalid
        """
        env_value = os.getenv("CAPTION_MAX_STORAGE_GB")
        
        if env_value is None:
            logger.info(f"CAPTION_MAX_STORAGE_GB not set, using default: {self.DEFAULT_MAX_STORAGE_GB}GB")
            return self.DEFAULT_MAX_STORAGE_GB
        
        try:
            max_storage_gb = float(env_value)
            
            # Validate that the value is positive
            if max_storage_gb <= 0:
                logger.error(f"CAPTION_MAX_STORAGE_GB must be positive, got: {max_storage_gb}")
                logger.warning(f"Using default value: {self.DEFAULT_MAX_STORAGE_GB}GB")
                return self.DEFAULT_MAX_STORAGE_GB
            
            return max_storage_gb
            
        except ValueError as e:
            logger.error(f"Invalid CAPTION_MAX_STORAGE_GB value '{env_value}': {e}")
            logger.warning(f"Using default value: {self.DEFAULT_MAX_STORAGE_GB}GB")
            return self.DEFAULT_MAX_STORAGE_GB
    
    def _get_warning_threshold_from_env(self) -> float:
        """
        Read and validate STORAGE_WARNING_THRESHOLD from environment variables.
        
        Returns:
            float: Warning threshold percentage (0-100)
        """
        env_value = os.getenv("STORAGE_WARNING_THRESHOLD")
        
        if env_value is None:
            return self.DEFAULT_WARNING_THRESHOLD_PERCENTAGE
        
        try:
            threshold = float(env_value)
            
            # Validate that the value is between 0 and 100
            if not (0 < threshold < 100):
                logger.error(f"STORAGE_WARNING_THRESHOLD must be between 0 and 100, got: {threshold}")
                logger.warning(f"Using default value: {self.DEFAULT_WARNING_THRESHOLD_PERCENTAGE}%")
                return self.DEFAULT_WARNING_THRESHOLD_PERCENTAGE
            
            return threshold
            
        except ValueError as e:
            logger.error(f"Invalid STORAGE_WARNING_THRESHOLD value '{env_value}': {e}")
            logger.warning(f"Using default value: {self.DEFAULT_WARNING_THRESHOLD_PERCENTAGE}%")
            return self.DEFAULT_WARNING_THRESHOLD_PERCENTAGE
    
    def _get_monitoring_enabled_from_env(self) -> bool:
        """
        Read and validate STORAGE_MONITORING_ENABLED from environment variables.
        
        Returns:
            bool: Whether storage monitoring is enabled
        """
        env_value = os.getenv("STORAGE_MONITORING_ENABLED")
        
        if env_value is None:
            return self.DEFAULT_MONITORING_ENABLED
        
        # Convert string to boolean
        return env_value.lower() in ("true", "1", "yes", "on", "enabled")
    
    def get_max_storage_gb(self) -> float:
        """
        Get the maximum storage limit in GB.
        
        Returns:
            float: Maximum storage in GB
        """
        return self._config.max_storage_gb
    
    def get_warning_threshold_gb(self) -> float:
        """
        Get the warning threshold in GB (80% of limit by default).
        
        Returns:
            float: Warning threshold in GB
        """
        return self._config.get_warning_threshold_gb()
    
    def is_storage_monitoring_enabled(self) -> bool:
        """
        Check if storage monitoring is enabled.
        
        Returns:
            bool: True if monitoring is enabled, False otherwise
        """
        return self._config.monitoring_enabled
    
    def validate_storage_config(self) -> bool:
        """
        Validate the current storage configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            # Check if configuration was loaded successfully
            if self._config is None:
                logger.error("Storage configuration not loaded")
                return False
            
            # Validate max storage is positive
            if self._config.max_storage_gb <= 0:
                logger.error(f"Invalid max storage: {self._config.max_storage_gb}GB")
                return False
            
            # Validate warning threshold is reasonable
            if not (0 < self._config.warning_threshold_percentage < 100):
                logger.error(f"Invalid warning threshold: {self._config.warning_threshold_percentage}%")
                return False
            
            # Validate that warning threshold GB is less than max storage
            warning_gb = self.get_warning_threshold_gb()
            if warning_gb >= self._config.max_storage_gb:
                logger.error(f"Warning threshold ({warning_gb}GB) must be less than max storage ({self._config.max_storage_gb}GB)")
                return False
            
            logger.debug("Storage configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Storage configuration validation failed: {e}")
            return False
    
    def get_configuration_summary(self) -> dict:
        """
        Get a summary of the current storage configuration.
        
        Returns:
            dict: Configuration summary
        """
        if self._config is None:
            return {"error": "Configuration not loaded"}
        
        return {
            "max_storage_gb": self._config.max_storage_gb,
            "warning_threshold_percentage": self._config.warning_threshold_percentage,
            "warning_threshold_gb": self.get_warning_threshold_gb(),
            "monitoring_enabled": self._config.monitoring_enabled,
            "is_valid": self.validate_storage_config()
        }
    
    def reload_configuration(self) -> None:
        """
        Reload configuration from environment variables.
        
        This can be used to pick up configuration changes without restarting the application.
        """
        logger.info("Reloading storage configuration")
        self._load_configuration()