# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Rate Limiting Configuration Adapter

Integrates rate limiting with the configuration service to enable dynamic
rate limit updates without service restart.
"""

import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta

from app.core.configuration.core.configuration_service import ConfigurationService

logger = logging.getLogger(__name__)


class RateLimitingConfigurationAdapter:
    """
    Adapter class connecting rate limiting systems with ConfigurationService
    
    Provides dynamic rate limit configuration with real-time updates.
    """
    
    def __init__(self, config_service: ConfigurationService, 
                 security_middleware=None):
        """
        Initialize rate limiting configuration adapter
        
        Args:
            config_service: Configuration service instance
            security_middleware: Security middleware instance (optional)
        """
        self.config_service = config_service
        self.security_middleware = security_middleware
        
        # Configuration keys
        self.rate_limit_per_user_per_hour_key = 'rate_limit_per_user_per_hour'
        self.rate_limit_per_ip_per_minute_key = 'rate_limit_per_ip_per_minute'
        self.rate_limit_enabled_key = 'rate_limiting_enabled'
        self.rate_limit_window_minutes_key = 'rate_limit_window_minutes'
        self.rate_limit_burst_size_key = 'rate_limit_burst_size'
        
        # Current configuration cache
        self._current_config = {}
        
        # Subscription IDs for configuration changes
        self._subscriptions = {}
        
        # Initialize configuration and subscribe to changes
        self._initialize_configuration()
        self._subscribe_to_configuration_changes()
        
        logger.info("RateLimitingConfigurationAdapter initialized")
    
    def _initialize_configuration(self):
        """Initialize current configuration values"""
        try:
            # Load current configuration values
            self._current_config = {
                'rate_limit_per_user_per_hour': self.config_service.get_config(
                    self.rate_limit_per_user_per_hour_key, 1000  # Default: 1000 requests per hour per user
                ),
                'rate_limit_per_ip_per_minute': self.config_service.get_config(
                    self.rate_limit_per_ip_per_minute_key, 120  # Default: 120 requests per minute per IP
                ),
                'rate_limiting_enabled': self.config_service.get_config(
                    self.rate_limit_enabled_key, True  # Default: enabled
                ),
                'rate_limit_window_minutes': self.config_service.get_config(
                    self.rate_limit_window_minutes_key, 1  # Default: 1 minute window
                ),
                'rate_limit_burst_size': self.config_service.get_config(
                    self.rate_limit_burst_size_key, 10  # Default: 10 requests burst
                )
            }
            
            # Apply initial configuration
            self._apply_rate_limiting_configuration()
            
            logger.info(f"Initialized rate limiting configuration: {self._current_config}")
            
        except Exception as e:
            logger.error(f"Error initializing rate limiting configuration: {e}")
            # Use default values if configuration service fails
            self._current_config = {
                'rate_limit_per_user_per_hour': 1000,
                'rate_limit_per_ip_per_minute': 120,
                'rate_limiting_enabled': True,
                'rate_limit_window_minutes': 1,
                'rate_limit_burst_size': 10
            }
    
    def _subscribe_to_configuration_changes(self):
        """Subscribe to configuration change notifications"""
        try:
            # Subscribe to rate limit per user per hour changes
            self._subscriptions['rate_limit_per_user_per_hour'] = self.config_service.subscribe_to_changes(
                self.rate_limit_per_user_per_hour_key, self._handle_rate_limit_per_user_change
            )
            
            # Subscribe to rate limit per IP per minute changes
            self._subscriptions['rate_limit_per_ip_per_minute'] = self.config_service.subscribe_to_changes(
                self.rate_limit_per_ip_per_minute_key, self._handle_rate_limit_per_ip_change
            )
            
            # Subscribe to rate limiting enabled/disabled changes
            self._subscriptions['rate_limiting_enabled'] = self.config_service.subscribe_to_changes(
                self.rate_limit_enabled_key, self._handle_rate_limiting_enabled_change
            )
            
            # Subscribe to rate limit window changes
            self._subscriptions['rate_limit_window_minutes'] = self.config_service.subscribe_to_changes(
                self.rate_limit_window_minutes_key, self._handle_rate_limit_window_change
            )
            
            # Subscribe to burst size changes
            self._subscriptions['rate_limit_burst_size'] = self.config_service.subscribe_to_changes(
                self.rate_limit_burst_size_key, self._handle_rate_limit_burst_size_change
            )
            
            logger.info("Subscribed to rate limiting configuration changes")
            
        except Exception as e:
            logger.error(f"Error subscribing to rate limiting configuration changes: {e}")
    
    def _apply_rate_limiting_configuration(self):
        """Apply current configuration to rate limiting systems"""
        try:
            # Update security middleware if available
            if self.security_middleware:
                self._update_security_middleware_rate_limits()
            
            logger.info("Applied rate limiting configuration to all systems")
            
        except Exception as e:
            logger.error(f"Error applying rate limiting configuration: {e}")
    
    def _update_security_middleware_rate_limits(self):
        """Update security middleware rate limiting settings"""
        try:
            if not hasattr(self.security_middleware, '_rate_limit_config'):
                # Initialize rate limit config if it doesn't exist
                self.security_middleware._rate_limit_config = {}
            
            # Update rate limiting configuration
            self.security_middleware._rate_limit_config.update({
                'requests_per_minute': self._current_config.get('rate_limit_per_ip_per_minute', 120),
                'window_minutes': self._current_config.get('rate_limit_window_minutes', 1),
                'burst_size': self._current_config.get('rate_limit_burst_size', 10),
                'enabled': self._current_config.get('rate_limiting_enabled', True)
            })
            
            logger.info(f"Updated security middleware rate limits: {self.security_middleware._rate_limit_config}")
            
        except Exception as e:
            logger.error(f"Error updating security middleware rate limits: {e}")
    
    def _handle_rate_limit_per_user_change(self, key: str, old_value: Any, new_value: Any):
        """Handle rate limit per user per hour configuration change"""
        try:
            logger.info(f"Rate limit per user per hour changed from {old_value} to {new_value}")
            self._current_config['rate_limit_per_user_per_hour'] = new_value
            self._apply_rate_limiting_configuration()
            
        except Exception as e:
            logger.error(f"Error handling rate limit per user change: {e}")
    
    def _handle_rate_limit_per_ip_change(self, key: str, old_value: Any, new_value: Any):
        """Handle rate limit per IP per minute configuration change"""
        try:
            logger.info(f"Rate limit per IP per minute changed from {old_value} to {new_value}")
            self._current_config['rate_limit_per_ip_per_minute'] = new_value
            self._apply_rate_limiting_configuration()
            
        except Exception as e:
            logger.error(f"Error handling rate limit per IP change: {e}")
    
    def _handle_rate_limiting_enabled_change(self, key: str, old_value: Any, new_value: Any):
        """Handle rate limiting enabled/disabled configuration change"""
        try:
            logger.info(f"Rate limiting enabled changed from {old_value} to {new_value}")
            self._current_config['rate_limiting_enabled'] = new_value
            self._apply_rate_limiting_configuration()
            
        except Exception as e:
            logger.error(f"Error handling rate limiting enabled change: {e}")
    
    def _handle_rate_limit_window_change(self, key: str, old_value: Any, new_value: Any):
        """Handle rate limit window configuration change"""
        try:
            logger.info(f"Rate limit window changed from {old_value} to {new_value} minutes")
            self._current_config['rate_limit_window_minutes'] = new_value
            self._apply_rate_limiting_configuration()
            
        except Exception as e:
            logger.error(f"Error handling rate limit window change: {e}")
    
    def _handle_rate_limit_burst_size_change(self, key: str, old_value: Any, new_value: Any):
        """Handle rate limit burst size configuration change"""
        try:
            logger.info(f"Rate limit burst size changed from {old_value} to {new_value}")
            self._current_config['rate_limit_burst_size'] = new_value
            self._apply_rate_limiting_configuration()
            
        except Exception as e:
            logger.error(f"Error handling rate limit burst size change: {e}")
    
    def get_current_rate_limit_per_user_per_hour(self) -> int:
        """
        Get current rate limit per user per hour
        
        Returns:
            Rate limit per user per hour
        """
        return self._current_config.get('rate_limit_per_user_per_hour', 1000)
    
    def get_current_rate_limit_per_ip_per_minute(self) -> int:
        """
        Get current rate limit per IP per minute
        
        Returns:
            Rate limit per IP per minute
        """
        return self._current_config.get('rate_limit_per_ip_per_minute', 120)
    
    def is_rate_limiting_enabled(self) -> bool:
        """
        Check if rate limiting is enabled
        
        Returns:
            True if rate limiting is enabled
        """
        return self._current_config.get('rate_limiting_enabled', True)
    
    def get_current_rate_limit_window_minutes(self) -> int:
        """
        Get current rate limit window in minutes
        
        Returns:
            Rate limit window in minutes
        """
        return self._current_config.get('rate_limit_window_minutes', 1)
    
    def get_current_rate_limit_burst_size(self) -> int:
        """
        Get current rate limit burst size
        
        Returns:
            Rate limit burst size
        """
        return self._current_config.get('rate_limit_burst_size', 10)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get summary of current rate limiting configuration
        
        Returns:
            Dictionary with current configuration values
        """
        return self._current_config.copy()
    
    def check_rate_limit_for_user(self, user_id: int, current_requests: int) -> bool:
        """
        Check if user is within rate limits
        
        Args:
            user_id: User ID to check
            current_requests: Current number of requests in the time window
            
        Returns:
            True if within limits, False if rate limited
        """
        if not self.is_rate_limiting_enabled():
            return True
        
        rate_limit = self.get_current_rate_limit_per_user_per_hour()
        return current_requests < rate_limit
    
    def check_rate_limit_for_ip(self, ip_address: str, current_requests: int) -> bool:
        """
        Check if IP address is within rate limits
        
        Args:
            ip_address: IP address to check
            current_requests: Current number of requests in the time window
            
        Returns:
            True if within limits, False if rate limited
        """
        if not self.is_rate_limiting_enabled():
            return True
        
        rate_limit = self.get_current_rate_limit_per_ip_per_minute()
        return current_requests < rate_limit
    
    def get_rate_limit_info_for_user(self, user_id: int, current_requests: int) -> Dict[str, Any]:
        """
        Get rate limit information for a user
        
        Args:
            user_id: User ID
            current_requests: Current number of requests
            
        Returns:
            Dictionary with rate limit information
        """
        rate_limit = self.get_current_rate_limit_per_user_per_hour()
        return {
            'user_id': user_id,
            'rate_limit': rate_limit,
            'current_requests': current_requests,
            'remaining_requests': max(0, rate_limit - current_requests),
            'window': 'hour',
            'enabled': self.is_rate_limiting_enabled()
        }
    
    def get_rate_limit_info_for_ip(self, ip_address: str, current_requests: int) -> Dict[str, Any]:
        """
        Get rate limit information for an IP address
        
        Args:
            ip_address: IP address
            current_requests: Current number of requests
            
        Returns:
            Dictionary with rate limit information
        """
        rate_limit = self.get_current_rate_limit_per_ip_per_minute()
        return {
            'ip_address': ip_address,
            'rate_limit': rate_limit,
            'current_requests': current_requests,
            'remaining_requests': max(0, rate_limit - current_requests),
            'window': 'minute',
            'burst_size': self.get_current_rate_limit_burst_size(),
            'enabled': self.is_rate_limiting_enabled()
        }
    
    def refresh_configuration(self):
        """Refresh configuration from configuration service"""
        try:
            # Refresh configuration cache
            self.config_service.refresh_config()
            
            # Reload configuration values
            self._initialize_configuration()
            
            logger.info("Refreshed rate limiting configuration")
            
        except Exception as e:
            logger.error(f"Error refreshing rate limiting configuration: {e}")
    
    def cleanup(self):
        """Clean up subscriptions and resources"""
        try:
            # Unsubscribe from configuration changes
            for subscription_id in self._subscriptions.values():
                self.config_service.unsubscribe(subscription_id)
            
            self._subscriptions.clear()
            logger.info("Cleaned up rate limiting configuration adapter")
            
        except Exception as e:
            logger.error(f"Error cleaning up rate limiting configuration adapter: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction


def create_rate_limiting_configuration_adapter(config_service: ConfigurationService,
                                             security_middleware=None) -> RateLimitingConfigurationAdapter:
    """
    Factory function to create a rate limiting configuration adapter
    
    Args:
        config_service: Configuration service instance
        security_middleware: Security middleware instance (optional)
        
    Returns:
        RateLimitingConfigurationAdapter instance
    """
    return RateLimitingConfigurationAdapter(
        config_service=config_service,
        security_middleware=security_middleware
    )