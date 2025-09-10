# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Service

Provides centralized maintenance mode control with immediate effect,
configuration service integration, and change notifications.
"""

import logging
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import uuid

from configuration_service import ConfigurationService
from configuration_event_bus import ConfigurationEventBus, EventType, ConfigurationChangeEvent

logger = logging.getLogger(__name__)


class MaintenanceStatus(Enum):
    """Maintenance mode status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSITIONING = "transitioning"


@dataclass
class MaintenanceInfo:
    """Maintenance mode information with metadata"""
    enabled: bool
    reason: Optional[str]
    status: MaintenanceStatus
    enabled_at: Optional[datetime]
    disabled_at: Optional[datetime]
    last_updated: datetime
    source: str


@dataclass
class MaintenanceChangeEvent:
    """Maintenance mode change event"""
    enabled: bool
    reason: Optional[str]
    changed_at: datetime
    changed_by: Optional[str] = None


class MaintenanceModeError(Exception):
    """Base maintenance mode error"""
    pass


class MaintenanceModeService:
    """
    Centralized maintenance mode control service
    
    Features:
    - Real-time maintenance mode status checking
    - Configuration service integration
    - Change notifications and subscriptions
    - Status tracking and reporting
    - Immediate maintenance mode effects
    """
    
    # Configuration keys
    MAINTENANCE_MODE_KEY = "maintenance_mode"
    MAINTENANCE_REASON_KEY = "maintenance_reason"
    
    def __init__(self, config_service: ConfigurationService, event_bus: ConfigurationEventBus = None):
        """
        Initialize maintenance mode service
        
        Args:
            config_service: Configuration service instance
            event_bus: Optional event bus for change notifications
        """
        self.config_service = config_service
        self.event_bus = event_bus
        
        # Change subscribers
        self._change_subscribers: Dict[str, Callable] = {}
        self._subscribers_lock = threading.RLock()
        
        # Status tracking
        self._last_status: Optional[MaintenanceInfo] = None
        self._status_lock = threading.RLock()
        
        # Subscribe to configuration changes if event bus is available
        if self.event_bus:
            self._setup_change_subscriptions()
    
    def is_maintenance_mode(self) -> bool:
        """
        Check if maintenance mode is currently enabled
        
        Returns:
            True if maintenance mode is enabled, False otherwise
        """
        try:
            maintenance_info = self.get_maintenance_status()
            return maintenance_info.enabled
            
        except Exception as e:
            logger.error(f"Error checking maintenance mode: {str(e)}")
            # Default to False (not in maintenance) on error
            return False
    
    def get_maintenance_reason(self) -> Optional[str]:
        """
        Get the current maintenance reason
        
        Returns:
            Maintenance reason string or None if not set
        """
        try:
            maintenance_info = self.get_maintenance_status()
            return maintenance_info.reason
            
        except Exception as e:
            logger.error(f"Error getting maintenance reason: {str(e)}")
            return None
    
    def get_maintenance_status(self) -> MaintenanceInfo:
        """
        Get comprehensive maintenance mode status
        
        Returns:
            MaintenanceInfo object with current status
        """
        try:
            # Get maintenance mode flag
            mode_config = self.config_service.get_config_with_metadata(self.MAINTENANCE_MODE_KEY)
            enabled = False
            mode_source = "default"
            mode_updated = datetime.now(timezone.utc)
            
            if mode_config:
                enabled = self._convert_to_boolean(mode_config.value)
                mode_source = mode_config.source.value
                mode_updated = mode_config.last_updated
            
            # Get maintenance reason
            reason_config = self.config_service.get_config_with_metadata(self.MAINTENANCE_REASON_KEY)
            reason = None
            
            if reason_config and reason_config.value:
                reason = str(reason_config.value).strip()
                if not reason:  # Empty string
                    reason = None
            
            # Determine status
            status = MaintenanceStatus.ACTIVE if enabled else MaintenanceStatus.INACTIVE
            
            # Create maintenance info
            maintenance_info = MaintenanceInfo(
                enabled=enabled,
                reason=reason,
                status=status,
                enabled_at=mode_updated if enabled else None,
                disabled_at=mode_updated if not enabled else None,
                last_updated=mode_updated,
                source=mode_source
            )
            
            # Update cached status
            with self._status_lock:
                self._last_status = maintenance_info
            
            return maintenance_info
            
        except Exception as e:
            logger.error(f"Error getting maintenance status: {str(e)}")
            # Return safe default status
            return MaintenanceInfo(
                enabled=False,
                reason=None,
                status=MaintenanceStatus.INACTIVE,
                enabled_at=None,
                disabled_at=None,
                last_updated=datetime.now(timezone.utc),
                source="error_fallback"
            )
    
    def enable_maintenance(self, reason: str, changed_by: Optional[str] = None) -> bool:
        """
        Enable maintenance mode with reason
        
        Args:
            reason: Reason for enabling maintenance mode
            changed_by: Optional identifier of who made the change
            
        Returns:
            True if maintenance mode was enabled successfully
        """
        try:
            # This would typically be handled by the configuration management system
            # For now, we'll log the request and notify subscribers
            logger.info(f"Maintenance mode enable requested: {reason} (by: {changed_by})")
            
            # Create change event
            change_event = MaintenanceChangeEvent(
                enabled=True,
                reason=reason,
                changed_at=datetime.now(timezone.utc),
                changed_by=changed_by
            )
            
            # Notify subscribers
            self._notify_change_subscribers(change_event)
            
            return True
            
        except Exception as e:
            logger.error(f"Error enabling maintenance mode: {str(e)}")
            return False
    
    def disable_maintenance(self, changed_by: Optional[str] = None) -> bool:
        """
        Disable maintenance mode
        
        Args:
            changed_by: Optional identifier of who made the change
            
        Returns:
            True if maintenance mode was disabled successfully
        """
        try:
            # This would typically be handled by the configuration management system
            # For now, we'll log the request and notify subscribers
            logger.info(f"Maintenance mode disable requested (by: {changed_by})")
            
            # Create change event
            change_event = MaintenanceChangeEvent(
                enabled=False,
                reason=None,
                changed_at=datetime.now(timezone.utc),
                changed_by=changed_by
            )
            
            # Notify subscribers
            self._notify_change_subscribers(change_event)
            
            return True
            
        except Exception as e:
            logger.error(f"Error disabling maintenance mode: {str(e)}")
            return False
    
    def subscribe_to_changes(self, callback: Callable[[MaintenanceChangeEvent], None]) -> str:
        """
        Subscribe to maintenance mode changes
        
        Args:
            callback: Callback function to receive change events
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        with self._subscribers_lock:
            self._change_subscribers[subscription_id] = callback
        
        logger.debug(f"Added maintenance mode subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe_from_changes(self, subscription_id: str) -> bool:
        """
        Remove maintenance mode change subscription
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscribers_lock:
            if subscription_id in self._change_subscribers:
                del self._change_subscribers[subscription_id]
                logger.debug(f"Removed maintenance mode subscription {subscription_id}")
                return True
        
        return False
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get maintenance mode status summary for monitoring
        
        Returns:
            Dictionary with status summary
        """
        try:
            maintenance_info = self.get_maintenance_status()
            
            return {
                'maintenance_mode': {
                    'enabled': maintenance_info.enabled,
                    'reason': maintenance_info.reason,
                    'status': maintenance_info.status.value,
                    'enabled_at': maintenance_info.enabled_at.isoformat() if maintenance_info.enabled_at else None,
                    'disabled_at': maintenance_info.disabled_at.isoformat() if maintenance_info.disabled_at else None,
                    'last_updated': maintenance_info.last_updated.isoformat(),
                    'source': maintenance_info.source
                },
                'subscribers': len(self._change_subscribers),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting status summary: {str(e)}")
            return {
                'maintenance_mode': {
                    'enabled': False,
                    'reason': None,
                    'status': 'error',
                    'error': str(e)
                },
                'subscribers': 0,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
    
    def refresh_status(self) -> bool:
        """
        Refresh maintenance mode status from configuration service
        
        Returns:
            True if refresh was successful
        """
        try:
            # Refresh configuration cache
            self.config_service.refresh_config(self.MAINTENANCE_MODE_KEY)
            self.config_service.refresh_config(self.MAINTENANCE_REASON_KEY)
            
            # Clear cached status to force refresh
            with self._status_lock:
                self._last_status = None
            
            # Get fresh status
            self.get_maintenance_status()
            
            logger.debug("Maintenance mode status refreshed")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing maintenance mode status: {str(e)}")
            return False
    
    def _convert_to_boolean(self, value: Any) -> bool:
        """
        Convert configuration value to boolean
        
        Args:
            value: Value to convert
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            return bool(value)
    
    def _setup_change_subscriptions(self):
        """Setup subscriptions to configuration changes"""
        try:
            # Subscribe to maintenance mode configuration changes
            self.config_service.subscribe_to_changes(
                self.MAINTENANCE_MODE_KEY,
                self._handle_maintenance_mode_change
            )
            
            self.config_service.subscribe_to_changes(
                self.MAINTENANCE_REASON_KEY,
                self._handle_maintenance_reason_change
            )
            
            logger.debug("Setup maintenance mode change subscriptions")
            
        except Exception as e:
            logger.error(f"Error setting up change subscriptions: {str(e)}")
    
    def _handle_maintenance_mode_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle maintenance mode configuration changes
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
        """
        try:
            old_enabled = self._convert_to_boolean(old_value) if old_value is not None else False
            new_enabled = self._convert_to_boolean(new_value) if new_value is not None else False
            
            if old_enabled != new_enabled:
                # Get current reason
                reason = self.get_maintenance_reason()
                
                # Create change event
                change_event = MaintenanceChangeEvent(
                    enabled=new_enabled,
                    reason=reason,
                    changed_at=datetime.now(timezone.utc)
                )
                
                # Notify subscribers
                self._notify_change_subscribers(change_event)
                
                logger.info(f"Maintenance mode changed from {old_enabled} to {new_enabled}")
            
        except Exception as e:
            logger.error(f"Error handling maintenance mode change: {str(e)}")
    
    def _handle_maintenance_reason_change(self, key: str, old_value: Any, new_value: Any):
        """
        Handle maintenance reason configuration changes
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
        """
        try:
            old_reason = str(old_value).strip() if old_value else None
            new_reason = str(new_value).strip() if new_value else None
            
            # Only notify if maintenance mode is currently enabled
            if self.is_maintenance_mode() and old_reason != new_reason:
                # Create change event
                change_event = MaintenanceChangeEvent(
                    enabled=True,  # Still enabled, just reason changed
                    reason=new_reason,
                    changed_at=datetime.now(timezone.utc)
                )
                
                # Notify subscribers
                self._notify_change_subscribers(change_event)
                
                logger.info(f"Maintenance reason changed from '{old_reason}' to '{new_reason}'")
            
        except Exception as e:
            logger.error(f"Error handling maintenance reason change: {str(e)}")
    
    def _notify_change_subscribers(self, change_event: MaintenanceChangeEvent):
        """
        Notify subscribers of maintenance mode changes
        
        Args:
            change_event: Maintenance change event
        """
        with self._subscribers_lock:
            for subscription_id, callback in self._change_subscribers.items():
                try:
                    callback(change_event)
                except Exception as e:
                    logger.error(f"Error in maintenance mode change callback {subscription_id}: {str(e)}")