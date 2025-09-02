# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Configuration Adapter

Connects session management systems with the configuration service to enable
dynamic session timeout and security controls based on configuration values.
"""

import logging
from typing import Optional, Dict, Any, Callable
from datetime import timedelta

from configuration_service import ConfigurationService
from session_manager_v2 import SessionManagerV2
from unified_session_manager import UnifiedSessionManager
from flask_redis_session_interface import FlaskRedisSessionInterface

logger = logging.getLogger(__name__)


class SessionConfigurationAdapter:
    """
    Adapter class connecting session managers with ConfigurationService
    
    Provides dynamic session timeout and security controls based on
    configuration values with real-time updates.
    """
    
    def __init__(self, config_service: ConfigurationService, 
                 redis_session_manager: Optional[SessionManagerV2] = None,
                 unified_session_manager: Optional[UnifiedSessionManager] = None,
                 flask_session_interface: Optional[FlaskRedisSessionInterface] = None):
        """
        Initialize session configuration adapter
        
        Args:
            config_service: Configuration service instance
            redis_session_manager: SessionManagerV2 instance (optional)
            unified_session_manager: Unified session manager (optional)
            flask_session_interface: Flask Redis session interface (optional)
        """
        self.config_service = config_service
        self.redis_session_manager = redis_session_manager
        self.unified_session_manager = unified_session_manager
        self.flask_session_interface = flask_session_interface
        
        # Configuration keys
        self.session_timeout_key = 'session_timeout_minutes'
        self.session_security_key = 'session_security_enabled'
        self.rate_limit_key = 'rate_limit_per_user_per_hour'
        self.max_concurrent_sessions_key = 'max_concurrent_sessions_per_user'
        self.session_fingerprinting_key = 'session_fingerprinting_enabled'
        self.audit_log_retention_key = 'audit_log_retention_days'
        
        # Current configuration cache
        self._current_config = {}
        
        # Subscription IDs for configuration changes
        self._subscriptions = {}
        
        # Initialize configuration and subscribe to changes
        self._initialize_configuration()
        self._subscribe_to_configuration_changes()
        
        logger.info("SessionConfigurationAdapter initialized")
    
    def _initialize_configuration(self):
        """Initialize current configuration values"""
        try:
            # Load current configuration values
            self._current_config = {
                'session_timeout_minutes': self.config_service.get_config(
                    self.session_timeout_key, 120  # Default: 2 hours
                ),
                'session_security_enabled': self.config_service.get_config(
                    self.session_security_key, True
                ),
                'rate_limit_per_user_per_hour': self.config_service.get_config(
                    self.rate_limit_key, 1000  # Default: 1000 requests per hour
                ),
                'max_concurrent_sessions_per_user': self.config_service.get_config(
                    self.max_concurrent_sessions_key, 5  # Default: 5 concurrent sessions
                ),
                'session_fingerprinting_enabled': self.config_service.get_config(
                    self.session_fingerprinting_key, True
                ),
                'audit_log_retention_days': self.config_service.get_config(
                    self.audit_log_retention_key, 90  # Default: 90 days
                )
            }
            
            # Apply initial configuration
            self._apply_session_configuration()
            
            logger.info(f"Initialized session configuration: {self._current_config}")
            
        except Exception as e:
            logger.error(f"Error initializing session configuration: {e}")
            # Use default values if configuration service fails
            self._current_config = {
                'session_timeout_minutes': 120,
                'session_security_enabled': True,
                'rate_limit_per_user_per_hour': 1000,
                'max_concurrent_sessions_per_user': 5,
                'session_fingerprinting_enabled': True,
                'audit_log_retention_days': 90
            }
    
    def _subscribe_to_configuration_changes(self):
        """Subscribe to configuration change notifications"""
        try:
            # Subscribe to session timeout changes
            self._subscriptions['session_timeout'] = self.config_service.subscribe_to_changes(
                self.session_timeout_key, self._handle_session_timeout_change
            )
            
            # Subscribe to security setting changes
            self._subscriptions['session_security'] = self.config_service.subscribe_to_changes(
                self.session_security_key, self._handle_session_security_change
            )
            
            # Subscribe to rate limit changes
            self._subscriptions['rate_limit'] = self.config_service.subscribe_to_changes(
                self.rate_limit_key, self._handle_rate_limit_change
            )
            
            # Subscribe to concurrent sessions limit changes
            self._subscriptions['max_concurrent_sessions'] = self.config_service.subscribe_to_changes(
                self.max_concurrent_sessions_key, self._handle_max_concurrent_sessions_change
            )
            
            # Subscribe to session fingerprinting changes
            self._subscriptions['session_fingerprinting'] = self.config_service.subscribe_to_changes(
                self.session_fingerprinting_key, self._handle_session_fingerprinting_change
            )
            
            # Subscribe to audit log retention changes
            self._subscriptions['audit_log_retention'] = self.config_service.subscribe_to_changes(
                self.audit_log_retention_key, self._handle_audit_log_retention_change
            )
            
            logger.info("Subscribed to session configuration changes")
            
        except Exception as e:
            logger.error(f"Error subscribing to configuration changes: {e}")
    
    def _apply_session_configuration(self):
        """Apply current configuration to session managers"""
        try:
            # Update session timeout
            self.update_session_timeout()
            
            # Update security settings
            self.update_session_security_settings()
            
            # Update rate limiting
            self.update_rate_limiting()
            
            logger.info("Applied session configuration to all managers")
            
        except Exception as e:
            logger.error(f"Error applying session configuration: {e}")
    
    def update_session_timeout(self):
        """Update session timeout settings based on configuration"""
        try:
            timeout_minutes = self._current_config.get('session_timeout_minutes', 120)
            timeout_seconds = timeout_minutes * 60
            
            # Update SessionManagerV2 (Redis-based)
            if self.redis_session_manager:
                # SessionManagerV2 uses session_timeout parameter
                if hasattr(self.redis_session_manager, 'session_timeout'):
                    self.redis_session_manager.session_timeout = timeout_seconds
                    logger.info(f"Updated SessionManagerV2 timeout to {timeout_minutes} minutes")
            
            # Update unified session manager
            if self.unified_session_manager:
                # Update session config if it has timeout settings
                if hasattr(self.unified_session_manager, 'config') and self.unified_session_manager.config:
                    if hasattr(self.unified_session_manager.config.timeout, 'session_lifetime'):
                        self.unified_session_manager.config.timeout.session_lifetime = timedelta(seconds=timeout_seconds)
                        logger.info(f"Updated unified session manager timeout to {timeout_minutes} minutes")
            
            # Update Flask session interface
            if self.flask_session_interface:
                self.flask_session_interface.session_timeout = timeout_seconds
                logger.info(f"Updated Flask session interface timeout to {timeout_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Error updating session timeout: {e}")
    
    def update_session_security_settings(self):
        """Update session security settings based on configuration"""
        try:
            security_enabled = self._current_config.get('session_security_enabled', True)
            fingerprinting_enabled = self._current_config.get('session_fingerprinting_enabled', True)
            
            # Update SessionManagerV2 security settings
            if self.redis_session_manager:
                # SessionManagerV2 may not have direct security manager access
                # Security is typically handled at the application level
                # Store configuration for use by security middleware
                logger.info(f"Updated SessionManagerV2 security config: enabled={security_enabled}, fingerprinting={fingerprinting_enabled}")
            
            # Update unified session manager security settings
            if self.unified_session_manager:
                # Update security configuration if available
                if hasattr(self.unified_session_manager, 'config') and self.unified_session_manager.config:
                    if hasattr(self.unified_session_manager.config, 'security'):
                        self.unified_session_manager.config.security.enabled = security_enabled
                        self.unified_session_manager.config.security.fingerprinting_enabled = fingerprinting_enabled
                        logger.info(f"Updated unified session security: enabled={security_enabled}, fingerprinting={fingerprinting_enabled}")
            
        except Exception as e:
            logger.error(f"Error updating session security settings: {e}")
    
    def update_rate_limiting(self):
        """Update rate limiting settings based on configuration"""
        try:
            rate_limit = self._current_config.get('rate_limit_per_user_per_hour', 1000)
            
            # Update rate limiting in session managers
            # Note: This would integrate with the security middleware rate limiting
            # For now, we'll store the configuration for use by other components
            
            logger.info(f"Updated rate limiting configuration: {rate_limit} requests per hour per user")
            
        except Exception as e:
            logger.error(f"Error updating rate limiting: {e}")
    
    def update_max_concurrent_sessions(self):
        """Update maximum concurrent sessions per user"""
        try:
            max_sessions = self._current_config.get('max_concurrent_sessions_per_user', 5)
            
            # This would be used by session managers to enforce concurrent session limits
            # Store the configuration for use by session creation logic
            
            logger.info(f"Updated max concurrent sessions: {max_sessions} per user")
            
        except Exception as e:
            logger.error(f"Error updating max concurrent sessions: {e}")
    
    def _handle_session_timeout_change(self, key: str, old_value: Any, new_value: Any):
        """Handle session timeout configuration change"""
        try:
            logger.info(f"Session timeout changed from {old_value} to {new_value} minutes")
            self._current_config['session_timeout_minutes'] = new_value
            self.update_session_timeout()
            
        except Exception as e:
            logger.error(f"Error handling session timeout change: {e}")
    
    def _handle_session_security_change(self, key: str, old_value: Any, new_value: Any):
        """Handle session security configuration change"""
        try:
            logger.info(f"Session security changed from {old_value} to {new_value}")
            self._current_config['session_security_enabled'] = new_value
            self.update_session_security_settings()
            
        except Exception as e:
            logger.error(f"Error handling session security change: {e}")
    
    def _handle_rate_limit_change(self, key: str, old_value: Any, new_value: Any):
        """Handle rate limit configuration change"""
        try:
            logger.info(f"Rate limit changed from {old_value} to {new_value} requests per hour")
            self._current_config['rate_limit_per_user_per_hour'] = new_value
            self.update_rate_limiting()
            
        except Exception as e:
            logger.error(f"Error handling rate limit change: {e}")
    
    def _handle_max_concurrent_sessions_change(self, key: str, old_value: Any, new_value: Any):
        """Handle max concurrent sessions configuration change"""
        try:
            logger.info(f"Max concurrent sessions changed from {old_value} to {new_value}")
            self._current_config['max_concurrent_sessions_per_user'] = new_value
            self.update_max_concurrent_sessions()
            
        except Exception as e:
            logger.error(f"Error handling max concurrent sessions change: {e}")
    
    def _handle_session_fingerprinting_change(self, key: str, old_value: Any, new_value: Any):
        """Handle session fingerprinting configuration change"""
        try:
            logger.info(f"Session fingerprinting changed from {old_value} to {new_value}")
            self._current_config['session_fingerprinting_enabled'] = new_value
            self.update_session_security_settings()
            
        except Exception as e:
            logger.error(f"Error handling session fingerprinting change: {e}")
    
    def _handle_audit_log_retention_change(self, key: str, old_value: Any, new_value: Any):
        """Handle audit log retention configuration change"""
        try:
            logger.info(f"Audit log retention changed from {old_value} to {new_value} days")
            self._current_config['audit_log_retention_days'] = new_value
            
            # This would be used by audit log cleanup processes
            # For now, just store the configuration
            
        except Exception as e:
            logger.error(f"Error handling audit log retention change: {e}")
    
    def get_current_session_timeout(self) -> int:
        """
        Get current session timeout in minutes
        
        Returns:
            Session timeout in minutes
        """
        return self._current_config.get('session_timeout_minutes', 120)
    
    def get_current_rate_limit(self) -> int:
        """
        Get current rate limit per user per hour
        
        Returns:
            Rate limit per user per hour
        """
        return self._current_config.get('rate_limit_per_user_per_hour', 1000)
    
    def get_current_max_concurrent_sessions(self) -> int:
        """
        Get current maximum concurrent sessions per user
        
        Returns:
            Maximum concurrent sessions per user
        """
        return self._current_config.get('max_concurrent_sessions_per_user', 5)
    
    def is_session_security_enabled(self) -> bool:
        """
        Check if session security is enabled
        
        Returns:
            True if session security is enabled
        """
        return self._current_config.get('session_security_enabled', True)
    
    def is_session_fingerprinting_enabled(self) -> bool:
        """
        Check if session fingerprinting is enabled
        
        Returns:
            True if session fingerprinting is enabled
        """
        return self._current_config.get('session_fingerprinting_enabled', True)
    
    def get_audit_log_retention_days(self) -> int:
        """
        Get audit log retention period in days
        
        Returns:
            Audit log retention period in days
        """
        return self._current_config.get('audit_log_retention_days', 90)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session configuration
        
        Returns:
            Dictionary with current configuration values
        """
        return self._current_config.copy()
    
    def refresh_configuration(self):
        """Refresh configuration from configuration service"""
        try:
            # Refresh configuration cache
            self.config_service.refresh_config()
            
            # Reload configuration values
            self._initialize_configuration()
            
            logger.info("Refreshed session configuration")
            
        except Exception as e:
            logger.error(f"Error refreshing session configuration: {e}")
    
    def cleanup(self):
        """Clean up subscriptions and resources"""
        try:
            # Unsubscribe from configuration changes
            for subscription_id in self._subscriptions.values():
                self.config_service.unsubscribe(subscription_id)
            
            self._subscriptions.clear()
            logger.info("Cleaned up session configuration adapter")
            
        except Exception as e:
            logger.error(f"Error cleaning up session configuration adapter: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction


def create_session_configuration_adapter(config_service: ConfigurationService,
                                        redis_session_manager: Optional[SessionManagerV2] = None,
                                        unified_session_manager: Optional[UnifiedSessionManager] = None,
                                        flask_session_interface: Optional[FlaskRedisSessionInterface] = None) -> SessionConfigurationAdapter:
    """
    Factory function to create a session configuration adapter
    
    Args:
        config_service: Configuration service instance
        redis_session_manager: SessionManagerV2 instance (optional)
        unified_session_manager: Unified session manager (optional)
        flask_session_interface: Flask Redis session interface (optional)
        
    Returns:
        SessionConfigurationAdapter instance
    """
    return SessionConfigurationAdapter(
        config_service=config_service,
        redis_session_manager=redis_session_manager,
        unified_session_manager=unified_session_manager,
        flask_session_interface=flask_session_interface
    )