# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Alert Configuration Adapter

Connects AlertManager with ConfigurationService to enable dynamic alert threshold
updates and notification channel configuration through the configuration system.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.alerts.components.alert_manager import AlertManager, AlertThresholds, NotificationChannel, NotificationConfig
from app.core.configuration.core.configuration_service import ConfigurationService, ConfigurationError
from app.core.configuration.events.configuration_event_bus import ConfigurationEventBus, ConfigurationChangeEvent, EventType
from app.services.alerts.components.alert_threshold_validator import AlertThresholdValidator, ValidationResult, ValidationSeverity

logger = logging.getLogger(__name__)


@dataclass
class AlertConfigurationMapping:
    """Mapping between configuration keys and alert settings"""
    config_key: str
    alert_attribute: str
    data_type: str
    validator: Optional[Callable[[Any], bool]] = None
    transformer: Optional[Callable[[Any], Any]] = None


class AlertConfigurationAdapter:
    """
    Adapter class connecting AlertManager with ConfigurationService
    
    Features:
    - Dynamic alert threshold updates from configuration
    - Notification channel configuration integration
    - Configuration change handlers for real-time updates
    - Threshold validation and safe update mechanisms
    - Comprehensive error handling and logging
    """
    
    # Configuration key mappings for alert thresholds
    THRESHOLD_MAPPINGS = [
        AlertConfigurationMapping(
            config_key="alert_job_failure_rate_threshold",
            alert_attribute="job_failure_rate",
            data_type="float",
            validator=lambda x: 0.0 <= x <= 1.0
        ),
        AlertConfigurationMapping(
            config_key="alert_repeated_failure_count_threshold",
            alert_attribute="repeated_failure_count",
            data_type="integer",
            validator=lambda x: x >= 1
        ),
        AlertConfigurationMapping(
            config_key="alert_resource_usage_threshold",
            alert_attribute="resource_usage_threshold",
            data_type="float",
            validator=lambda x: 0.0 <= x <= 1.0
        ),
        AlertConfigurationMapping(
            config_key="alert_queue_backup_threshold",
            alert_attribute="queue_backup_threshold",
            data_type="integer",
            validator=lambda x: x >= 1
        ),
        AlertConfigurationMapping(
            config_key="alert_ai_service_timeout_threshold",
            alert_attribute="ai_service_timeout",
            data_type="integer",
            validator=lambda x: x >= 1
        ),
        AlertConfigurationMapping(
            config_key="alert_performance_degradation_threshold",
            alert_attribute="performance_degradation_threshold",
            data_type="float",
            validator=lambda x: x >= 1.0
        )
    ]
    
    # Configuration key mappings for notification channels
    NOTIFICATION_MAPPINGS = [
        AlertConfigurationMapping(
            config_key="alert_email_enabled",
            alert_attribute="email_enabled",
            data_type="boolean"
        ),
        AlertConfigurationMapping(
            config_key="alert_webhook_enabled",
            alert_attribute="webhook_enabled",
            data_type="boolean"
        ),
        AlertConfigurationMapping(
            config_key="alert_in_app_enabled",
            alert_attribute="in_app_enabled",
            data_type="boolean"
        ),
        AlertConfigurationMapping(
            config_key="alert_notification_channels",
            alert_attribute="notification_channels",
            data_type="json",
            transformer=lambda x: x if isinstance(x, list) else []
        )
    ]
    
    def __init__(self, alert_manager: AlertManager, config_service: ConfigurationService, 
                 event_bus: Optional[ConfigurationEventBus] = None):
        """
        Initialize alert configuration adapter
        
        Args:
            alert_manager: AlertManager instance to configure
            config_service: ConfigurationService instance for reading configuration
            event_bus: Optional event bus for configuration change notifications
        """
        self.alert_manager = alert_manager
        self.config_service = config_service
        self.event_bus = event_bus
        
        # Track subscriptions for cleanup
        self._subscriptions: List[str] = []
        
        # Track last known good values for rollback
        self._last_good_thresholds: Optional[AlertThresholds] = None
        self._last_good_notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Threshold validator for safety
        self._validator = AlertThresholdValidator()
        
        # Statistics
        self._stats = {
            'threshold_updates': 0,
            'notification_updates': 0,
            'validation_failures': 0,
            'rollbacks': 0,
            'configuration_errors': 0,
            'validation_warnings': 0,
            'safe_fallbacks': 0
        }
        
        # Initialize with current configuration
        self._initialize_from_configuration()
        
        # Subscribe to configuration changes if event bus is available
        if self.event_bus:
            self._subscribe_to_changes()
        
        logger.info("AlertConfigurationAdapter initialized")
    
    def _initialize_from_configuration(self):
        """Initialize alert manager with current configuration values"""
        try:
            # Store current values as last known good
            self._last_good_thresholds = AlertThresholds(
                job_failure_rate=self.alert_manager.thresholds.job_failure_rate,
                repeated_failure_count=self.alert_manager.thresholds.repeated_failure_count,
                resource_usage_threshold=self.alert_manager.thresholds.resource_usage_threshold,
                queue_backup_threshold=self.alert_manager.thresholds.queue_backup_threshold,
                ai_service_timeout=self.alert_manager.thresholds.ai_service_timeout,
                performance_degradation_threshold=self.alert_manager.thresholds.performance_degradation_threshold
            )
            
            self._last_good_notification_configs = self.alert_manager.notification_configs.copy()
            
            # Update with configuration values
            self.update_alert_thresholds()
            self.update_notification_channels()
            
            logger.info("Alert manager initialized from configuration")
            
        except Exception as e:
            logger.error(f"Error initializing from configuration: {str(e)}")
            self._stats['configuration_errors'] += 1
    
    def _subscribe_to_changes(self):
        """Subscribe to configuration change events"""
        try:
            # Subscribe to threshold configuration changes
            for mapping in self.THRESHOLD_MAPPINGS:
                subscription_id = self.event_bus.subscribe(
                    EventType.CONFIGURATION_CHANGED,
                    mapping.config_key,
                    self._handle_threshold_change
                )
                self._subscriptions.append(subscription_id)
            
            # Subscribe to notification configuration changes
            for mapping in self.NOTIFICATION_MAPPINGS:
                subscription_id = self.event_bus.subscribe(
                    EventType.CONFIGURATION_CHANGED,
                    mapping.config_key,
                    self._handle_notification_change
                )
                self._subscriptions.append(subscription_id)
            
            logger.info(f"Subscribed to {len(self._subscriptions)} configuration changes")
            
        except Exception as e:
            logger.error(f"Error subscribing to configuration changes: {str(e)}")
    
    def update_alert_thresholds(self) -> bool:
        """
        Update alert thresholds from configuration
        
        Returns:
            True if update was successful
        """
        try:
            # Create new thresholds object
            new_thresholds = AlertThresholds()
            
            # Update each threshold from configuration
            for mapping in self.THRESHOLD_MAPPINGS:
                try:
                    config_value = self.config_service.get_config(mapping.config_key)
                    if config_value is not None:
                        # Validate value
                        if mapping.validator and not mapping.validator(config_value):
                            logger.warning(f"Invalid threshold value for {mapping.config_key}: {config_value}")
                            self._stats['validation_failures'] += 1
                            continue
                        
                        # Transform value if needed
                        if mapping.transformer:
                            config_value = mapping.transformer(config_value)
                        
                        # Set attribute on thresholds object
                        setattr(new_thresholds, mapping.alert_attribute, config_value)
                        logger.debug(f"Updated {mapping.alert_attribute} to {config_value}")
                
                except ConfigurationError as e:
                    logger.debug(f"Configuration not found for {mapping.config_key}: {str(e)}")
                    # Keep default value
                    continue
                except Exception as e:
                    logger.error(f"Error updating threshold {mapping.config_key}: {str(e)}")
                    self._stats['configuration_errors'] += 1
                    continue
            
            # Validate the complete threshold set using comprehensive validator
            validation_result = self._validator.validate_thresholds(new_thresholds)
            
            if validation_result.is_valid:
                # Log any warnings
                if validation_result.has_warnings():
                    warning_messages = validation_result.get_warning_messages()
                    for warning in warning_messages:
                        logger.warning(f"Threshold validation warning: {warning}")
                    self._stats['validation_warnings'] += len(warning_messages)
                
                # Update alert manager
                self.alert_manager.thresholds = new_thresholds
                self._last_good_thresholds = new_thresholds
                self._stats['threshold_updates'] += 1
                
                logger.info("Alert thresholds updated from configuration")
                
                # Log recommendations if any
                if validation_result.recommendations:
                    logger.info(f"Threshold recommendations: {'; '.join(validation_result.recommendations)}")
                
                return True
            else:
                # Log validation errors
                error_messages = validation_result.get_error_messages()
                for error in error_messages:
                    logger.error(f"Threshold validation error: {error}")
                
                logger.error("Threshold validation failed, keeping previous values")
                self._stats['validation_failures'] += 1
                
                # Consider safe fallback if current thresholds are also invalid
                if self._should_use_safe_fallback():
                    self._apply_safe_fallback_thresholds()
                
                return False
                
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {str(e)}")
            self._stats['configuration_errors'] += 1
            return False
    
    def update_notification_channels(self) -> bool:
        """
        Update notification channel configuration
        
        Returns:
            True if update was successful
        """
        try:
            updated_configs = {}
            
            # Update notification channel enablement
            for mapping in self.NOTIFICATION_MAPPINGS:
                try:
                    config_value = self.config_service.get_config(mapping.config_key)
                    if config_value is not None:
                        # Transform value if needed
                        if mapping.transformer:
                            config_value = mapping.transformer(config_value)
                        
                        # Handle different notification settings
                        if mapping.alert_attribute == "email_enabled":
                            if NotificationChannel.EMAIL in self.alert_manager.notification_configs:
                                config = self.alert_manager.notification_configs[NotificationChannel.EMAIL]
                                config.enabled = bool(config_value)
                                updated_configs[NotificationChannel.EMAIL] = config
                        
                        elif mapping.alert_attribute == "webhook_enabled":
                            if NotificationChannel.WEBHOOK in self.alert_manager.notification_configs:
                                config = self.alert_manager.notification_configs[NotificationChannel.WEBHOOK]
                                config.enabled = bool(config_value)
                                updated_configs[NotificationChannel.WEBHOOK] = config
                        
                        elif mapping.alert_attribute == "in_app_enabled":
                            if NotificationChannel.IN_APP in self.alert_manager.notification_configs:
                                config = self.alert_manager.notification_configs[NotificationChannel.IN_APP]
                                config.enabled = bool(config_value)
                                updated_configs[NotificationChannel.IN_APP] = config
                        
                        elif mapping.alert_attribute == "notification_channels":
                            # Handle list of enabled channels
                            if isinstance(config_value, list):
                                for channel_name in config_value:
                                    try:
                                        channel = NotificationChannel(channel_name)
                                        if channel in self.alert_manager.notification_configs:
                                            config = self.alert_manager.notification_configs[channel]
                                            config.enabled = True
                                            updated_configs[channel] = config
                                    except ValueError:
                                        logger.warning(f"Unknown notification channel: {channel_name}")
                
                except ConfigurationError as e:
                    logger.debug(f"Configuration not found for {mapping.config_key}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error updating notification config {mapping.config_key}: {str(e)}")
                    self._stats['configuration_errors'] += 1
                    continue
            
            # Update notification configurations
            if updated_configs:
                for channel, config in updated_configs.items():
                    self.alert_manager.notification_configs[channel] = config
                
                self._last_good_notification_configs.update(updated_configs)
                self._stats['notification_updates'] += 1
                
                logger.info(f"Updated {len(updated_configs)} notification channel configurations")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating notification channels: {str(e)}")
            self._stats['configuration_errors'] += 1
            return False
    
    def handle_threshold_change(self, threshold_type: str, new_value: Any) -> bool:
        """
        Handle individual threshold change
        
        Args:
            threshold_type: Type of threshold that changed
            new_value: New threshold value
            
        Returns:
            True if change was applied successfully
        """
        try:
            # Find the mapping for this threshold type
            mapping = None
            for m in self.THRESHOLD_MAPPINGS:
                if m.config_key == threshold_type or m.alert_attribute == threshold_type:
                    mapping = m
                    break
            
            if not mapping:
                logger.warning(f"Unknown threshold type: {threshold_type}")
                return False
            
            # Validate new value
            if mapping.validator and not mapping.validator(new_value):
                logger.error(f"Invalid threshold value for {threshold_type}: {new_value}")
                self._stats['validation_failures'] += 1
                return False
            
            # Transform value if needed
            if mapping.transformer:
                new_value = mapping.transformer(new_value)
            
            # Update the threshold
            old_value = getattr(self.alert_manager.thresholds, mapping.alert_attribute)
            setattr(self.alert_manager.thresholds, mapping.alert_attribute, new_value)
            
            # Validate the complete threshold set using comprehensive validator
            validation_result = self._validator.validate_thresholds(self.alert_manager.thresholds)
            
            if not validation_result.is_valid:
                # Rollback
                setattr(self.alert_manager.thresholds, mapping.alert_attribute, old_value)
                
                # Log validation errors
                error_messages = validation_result.get_error_messages()
                for error in error_messages:
                    logger.error(f"Threshold validation error: {error}")
                
                logger.error(f"Threshold validation failed for {threshold_type}, rolled back to {old_value}")
                self._stats['rollbacks'] += 1
                return False
            
            # Log any warnings
            if validation_result.has_warnings():
                warning_messages = validation_result.get_warning_messages()
                for warning in warning_messages:
                    logger.warning(f"Threshold validation warning: {warning}")
                self._stats['validation_warnings'] += len(warning_messages)
            
            logger.info(f"Updated alert threshold {threshold_type}: {old_value} -> {new_value}")
            self._stats['threshold_updates'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error handling threshold change for {threshold_type}: {str(e)}")
            self._stats['configuration_errors'] += 1
            return False
    
    def _handle_threshold_change(self, event: ConfigurationChangeEvent):
        """Handle threshold configuration change event"""
        try:
            self.handle_threshold_change(event.key, event.new_value)
        except Exception as e:
            logger.error(f"Error handling threshold change event: {str(e)}")
    
    def _handle_notification_change(self, event: ConfigurationChangeEvent):
        """Handle notification configuration change event"""
        try:
            self.update_notification_channels()
        except Exception as e:
            logger.error(f"Error handling notification change event: {str(e)}")
    
    def _should_use_safe_fallback(self) -> bool:
        """
        Determine if safe fallback thresholds should be used
        
        Returns:
            True if safe fallback should be applied
        """
        try:
            # Check if current thresholds are also invalid
            current_validation = self._validator.validate_thresholds(self.alert_manager.thresholds)
            
            # Use fallback if current thresholds have critical errors
            if current_validation.has_errors():
                logger.warning("Current thresholds also have validation errors, considering safe fallback")
                return True
            
            # Check if we've had multiple recent validation failures
            stats = self._validator.get_validation_statistics()
            recent_success_rate = stats.get('recent_validation_success_rate', 1.0)
            
            if recent_success_rate < 0.5:  # Less than 50% success rate
                logger.warning("Multiple recent validation failures, considering safe fallback")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error determining safe fallback need: {str(e)}")
            return True  # Err on the side of caution
    
    def _apply_safe_fallback_thresholds(self):
        """Apply safe fallback threshold values"""
        try:
            safe_thresholds = self._validator.get_safe_fallback_thresholds()
            
            # Validate safe thresholds (should always pass)
            validation_result = self._validator.validate_thresholds(safe_thresholds)
            
            if validation_result.is_valid:
                self.alert_manager.thresholds = safe_thresholds
                self._last_good_thresholds = safe_thresholds
                self._stats['safe_fallbacks'] += 1
                
                logger.warning("Applied safe fallback threshold values due to validation failures")
            else:
                logger.error("Safe fallback thresholds failed validation - this should not happen")
                
        except Exception as e:
            logger.error(f"Error applying safe fallback thresholds: {str(e)}")
    
    def validate_threshold_change(self, threshold_type: str, new_value: Any) -> ValidationResult:
        """
        Validate a proposed threshold change before applying it
        
        Args:
            threshold_type: Type of threshold to change
            new_value: Proposed new value
            
        Returns:
            ValidationResult with validation outcome
        """
        try:
            # Find the mapping for this threshold type
            mapping = None
            for m in self.THRESHOLD_MAPPINGS:
                if m.config_key == threshold_type or m.alert_attribute == threshold_type:
                    mapping = m
                    break
            
            if not mapping:
                return ValidationResult(
                    is_valid=False,
                    issues=[],
                    warnings=[],
                    recommendations=[f"Unknown threshold type: {threshold_type}"]
                )
            
            # Create a copy of current thresholds with the proposed change
            current_thresholds = AlertThresholds(
                job_failure_rate=self.alert_manager.thresholds.job_failure_rate,
                repeated_failure_count=self.alert_manager.thresholds.repeated_failure_count,
                resource_usage_threshold=self.alert_manager.thresholds.resource_usage_threshold,
                queue_backup_threshold=self.alert_manager.thresholds.queue_backup_threshold,
                ai_service_timeout=self.alert_manager.thresholds.ai_service_timeout,
                performance_degradation_threshold=self.alert_manager.thresholds.performance_degradation_threshold
            )
            
            # Apply the proposed change
            setattr(current_thresholds, mapping.alert_attribute, new_value)
            
            # Validate the modified thresholds
            return self._validator.validate_thresholds(current_thresholds)
            
        except Exception as e:
            logger.error(f"Error validating threshold change: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[],
                warnings=[],
                recommendations=[f"Validation error: {str(e)}"]
            )
    
    def get_threshold_recommendations(self) -> Dict[str, Any]:
        """
        Get recommendations for current threshold configuration
        
        Returns:
            Dictionary with recommendations and analysis
        """
        try:
            validation_result = self._validator.validate_thresholds(self.alert_manager.thresholds)
            
            return {
                'is_optimal': validation_result.is_valid and not validation_result.has_warnings(),
                'validation_result': {
                    'is_valid': validation_result.is_valid,
                    'has_warnings': validation_result.has_warnings(),
                    'error_count': len(validation_result.get_error_messages()),
                    'warning_count': len(validation_result.get_warning_messages())
                },
                'errors': validation_result.get_error_messages(),
                'warnings': validation_result.get_warning_messages(),
                'recommendations': validation_result.recommendations,
                'safe_fallback_available': True
            }
            
        except Exception as e:
            logger.error(f"Error getting threshold recommendations: {str(e)}")
            return {
                'is_optimal': False,
                'validation_result': {'is_valid': False},
                'errors': [f"Analysis error: {str(e)}"],
                'warnings': [],
                'recommendations': ["Unable to analyze current configuration"],
                'safe_fallback_available': True
            }
    
    def rollback_to_safe_values(self) -> bool:
        """
        Rollback to last known good configuration values
        
        Returns:
            True if rollback was successful
        """
        try:
            if self._last_good_thresholds:
                self.alert_manager.thresholds = self._last_good_thresholds
                logger.info("Rolled back alert thresholds to last known good values")
            
            if self._last_good_notification_configs:
                self.alert_manager.notification_configs.update(self._last_good_notification_configs)
                logger.info("Rolled back notification configs to last known good values")
            
            self._stats['rollbacks'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error during rollback: {str(e)}")
            return False
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current alert configuration values
        
        Returns:
            Dictionary with current configuration
        """
        try:
            config = {
                'thresholds': {
                    'job_failure_rate': self.alert_manager.thresholds.job_failure_rate,
                    'repeated_failure_count': self.alert_manager.thresholds.repeated_failure_count,
                    'resource_usage_threshold': self.alert_manager.thresholds.resource_usage_threshold,
                    'queue_backup_threshold': self.alert_manager.thresholds.queue_backup_threshold,
                    'ai_service_timeout': self.alert_manager.thresholds.ai_service_timeout,
                    'performance_degradation_threshold': self.alert_manager.thresholds.performance_degradation_threshold
                },
                'notification_channels': {}
            }
            
            for channel, notification_config in self.alert_manager.notification_configs.items():
                config['notification_channels'][channel.value] = {
                    'enabled': notification_config.enabled,
                    'config': notification_config.config
                }
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting current configuration: {str(e)}")
            return {}
    
    def get_adapter_statistics(self) -> Dict[str, Any]:
        """
        Get adapter statistics and metrics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'statistics': self._stats.copy(),
            'subscriptions': len(self._subscriptions),
            'last_good_thresholds_available': self._last_good_thresholds is not None,
            'last_good_notification_configs_count': len(self._last_good_notification_configs)
        }
    
    def cleanup(self):
        """Cleanup adapter resources"""
        try:
            # Unsubscribe from all configuration changes
            if self.event_bus:
                for subscription_id in self._subscriptions:
                    self.event_bus.unsubscribe(subscription_id)
                self._subscriptions.clear()
            
            logger.info("AlertConfigurationAdapter cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during adapter cleanup: {str(e)}")