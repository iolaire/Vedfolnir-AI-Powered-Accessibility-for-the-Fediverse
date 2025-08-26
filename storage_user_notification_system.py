# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage User Notification System for displaying storage limit notifications to users.

This service provides user-facing notifications when storage limits are reached,
reusing maintenance mode patterns for consistent UI/UX. It displays storage limit
banners on the caption generation page and hides the caption generation form when
storage limits are active.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
from flask import render_template_string

from storage_limit_enforcer import StorageLimitEnforcer, StorageBlockingState
from storage_monitor_service import StorageMonitorService
from storage_configuration_service import StorageConfigurationService

logger = logging.getLogger(__name__)


@dataclass
class StorageNotificationContext:
    """Context data for storage limit notifications"""
    is_blocked: bool
    reason: str
    storage_gb: float
    limit_gb: float
    usage_percentage: float
    blocked_at: Optional[datetime]
    banner_html: str
    should_hide_form: bool
    notification_type: str  # 'warning', 'error', 'info'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template context"""
        return {
            'is_blocked': self.is_blocked,
            'reason': self.reason,
            'storage_gb': self.storage_gb,
            'limit_gb': self.limit_gb,
            'usage_percentage': self.usage_percentage,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None,
            'banner_html': self.banner_html,
            'should_hide_form': self.should_hide_form,
            'notification_type': self.notification_type
        }


class StorageUserNotificationSystemError(Exception):
    """Base storage user notification system error"""
    pass


class StorageUserNotificationSystem:
    """
    User notification system for storage limits, reusing maintenance mode patterns.
    
    This service provides:
    - Storage limit banner display for caption generation page
    - Logic to hide caption generation form when storage limit is reached
    - Consistent styling with maintenance mode notifications
    - User-friendly messages explaining storage limit status
    
    Requirements addressed: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    
    def __init__(self, 
                 enforcer: Optional[StorageLimitEnforcer] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 config_service: Optional[StorageConfigurationService] = None):
        """
        Initialize the storage user notification system.
        
        Args:
            enforcer: Storage limit enforcer instance
            monitor_service: Storage monitor service instance
            config_service: Storage configuration service instance
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        self.enforcer = enforcer or StorageLimitEnforcer(self.config_service, self.monitor_service)
        
        logger.info("Storage user notification system initialized")
    
    def get_storage_notification_context(self) -> Optional[StorageNotificationContext]:
        """
        Get storage notification context for template rendering.
        
        This method provides the context data needed to display storage limit
        notifications to users, implementing requirements 4.1, 4.2, 4.3.
        
        Returns:
            StorageNotificationContext if storage notifications should be shown,
            None if no notifications are needed
        """
        try:
            # Get current blocking state
            blocking_state = self.enforcer.get_blocking_state()
            
            # Get current storage metrics
            metrics = self.monitor_service.get_storage_metrics()
            
            # Determine if we should show notifications
            should_show_notification = False
            notification_type = 'info'
            reason = ''
            is_blocked = False
            should_hide_form = False
            
            if blocking_state and blocking_state.is_blocked:
                # Storage is currently blocked
                should_show_notification = True
                notification_type = 'error'
                reason = blocking_state.reason
                is_blocked = True
                should_hide_form = True
                logger.debug(f"Storage blocked notification: {reason}")
                
            elif metrics.is_warning_exceeded:
                # Storage is approaching limit (warning threshold)
                should_show_notification = True
                notification_type = 'warning'
                reason = f"Storage usage is at {metrics.usage_percentage:.1f}% of limit"
                is_blocked = False
                should_hide_form = False
                logger.debug(f"Storage warning notification: {reason}")
            
            if not should_show_notification:
                return None
            
            # Create notification context
            context = StorageNotificationContext(
                is_blocked=is_blocked,
                reason=reason,
                storage_gb=metrics.total_gb,
                limit_gb=metrics.limit_gb,
                usage_percentage=metrics.usage_percentage,
                blocked_at=blocking_state.blocked_at if blocking_state else None,
                banner_html=self._create_storage_banner_html(
                    is_blocked, reason, metrics.total_gb, metrics.limit_gb, 
                    metrics.usage_percentage, notification_type
                ),
                should_hide_form=should_hide_form,
                notification_type=notification_type
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting storage notification context: {e}")
            # Return error notification context
            return StorageNotificationContext(
                is_blocked=True,
                reason="Error checking storage status",
                storage_gb=0.0,
                limit_gb=self.config_service.get_max_storage_gb(),
                usage_percentage=0.0,
                blocked_at=None,
                banner_html=self._create_error_banner_html(),
                should_hide_form=True,
                notification_type='error'
            )
    
    def render_storage_limit_banner(self) -> str:
        """
        Render storage limit banner HTML for display on web pages.
        
        This method generates the HTML banner for storage limit notifications,
        implementing requirement 4.2.
        
        Returns:
            HTML string for storage limit banner, empty string if no banner needed
        """
        try:
            context = self.get_storage_notification_context()
            if context:
                return context.banner_html
            return ""
        except Exception as e:
            logger.error(f"Error rendering storage limit banner: {e}")
            return self._create_error_banner_html()
    
    def should_hide_caption_form(self) -> bool:
        """
        Determine if caption generation form should be hidden due to storage limits.
        
        This method implements requirement 4.5 by determining when the caption
        generation form should be disabled and hidden.
        
        Returns:
            True if form should be hidden, False otherwise
        """
        try:
            context = self.get_storage_notification_context()
            return context.should_hide_form if context else False
        except Exception as e:
            logger.error(f"Error checking if caption form should be hidden: {e}")
            # Default to safe mode (hide form) on error
            return True
    
    def _create_storage_banner_html(self, 
                                   is_blocked: bool, 
                                   reason: str, 
                                   storage_gb: float, 
                                   limit_gb: float, 
                                   usage_percentage: float,
                                   notification_type: str) -> str:
        """
        Create HTML banner for storage limit notifications.
        
        This method creates the banner HTML using patterns similar to maintenance mode,
        implementing requirements 4.3 and 4.4.
        
        Args:
            is_blocked: Whether storage is currently blocked
            reason: Reason for the notification
            storage_gb: Current storage usage in GB
            limit_gb: Storage limit in GB
            usage_percentage: Storage usage percentage
            notification_type: Type of notification ('warning', 'error', 'info')
            
        Returns:
            HTML string for the banner
        """
        try:
            # Determine banner styling based on notification type
            if notification_type == 'error':
                banner_class = "alert alert-danger"
                icon = "🚫"
                title = "Caption Generation Unavailable"
            elif notification_type == 'warning':
                banner_class = "alert alert-warning"
                icon = "⚠️"
                title = "Storage Limit Warning"
            else:
                banner_class = "alert alert-info"
                icon = "ℹ️"
                title = "Storage Information"
            
            # Create user-friendly message
            if is_blocked:
                message = "Caption generation is temporarily unavailable due to storage limits."
                details = f"Current usage: {storage_gb:.1f}GB of {limit_gb:.1f}GB limit ({usage_percentage:.1f}%)"
                action_message = "Administrators have been notified and are working to resolve this issue."
            else:
                message = f"Storage usage is approaching the limit ({usage_percentage:.1f}%)."
                details = f"Current usage: {storage_gb:.1f}GB of {limit_gb:.1f}GB limit"
                action_message = "Caption generation will be temporarily disabled if the limit is reached."
            
            # Try to use Flask template rendering if available
            try:
                # HTML template (similar to maintenance mode banner)
                html_template = """
                <div class="{{ banner_class }}" role="alert" id="storage-limit-banner">
                    <div class="d-flex align-items-start">
                        <div class="flex-grow-1">
                            <h5 class="alert-heading">
                                {{ icon }} {{ title }}
                            </h5>
                            <p class="mb-2">{{ message }}</p>
                            <small class="text-muted">
                                {{ details }}<br>
                                {{ action_message }}
                            </small>
                            {% if reason %}
                            <hr>
                            <small><strong>Details:</strong> {{ reason }}</small>
                            {% endif %}
                        </div>
                        {% if not is_blocked %}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        {% endif %}
                    </div>
                </div>
                """
                
                # Render template
                return render_template_string(html_template,
                    banner_class=banner_class,
                    icon=icon,
                    title=title,
                    message=message,
                    details=details,
                    action_message=action_message,
                    reason=reason if reason != message else None,
                    is_blocked=is_blocked
                )
                
            except Exception:
                # Fallback to manual HTML construction when Flask context is not available
                close_button = '' if is_blocked else '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'
                reason_section = f'<hr><small><strong>Details:</strong> {reason}</small>' if reason and reason != message else ''
                
                return f'''
                <div class="{banner_class}" role="alert" id="storage-limit-banner">
                    <div class="d-flex align-items-start">
                        <div class="flex-grow-1">
                            <h5 class="alert-heading">
                                {icon} {title}
                            </h5>
                            <p class="mb-2">{message}</p>
                            <small class="text-muted">
                                {details}<br>
                                {action_message}
                            </small>
                            {reason_section}
                        </div>
                        {close_button}
                    </div>
                </div>
                '''
            
        except Exception as e:
            logger.error(f"Error creating storage banner HTML: {e}")
            return self._create_error_banner_html()
    
    def _create_error_banner_html(self) -> str:
        """
        Create fallback error banner HTML.
        
        Returns:
            HTML string for error banner
        """
        return '''
        <div class="alert alert-warning" role="alert" id="storage-error-banner">
            <div class="d-flex align-items-center">
                <div class="flex-grow-1">
                    <strong>⚠️ Storage Status Unavailable</strong><br>
                    <small>Unable to check storage status. Caption generation may be temporarily restricted.</small>
                </div>
            </div>
        </div>
        '''
    
    def get_storage_status_for_template(self) -> Dict[str, Any]:
        """
        Get storage status data for template context.
        
        This method provides a complete context dictionary that can be passed
        to templates for rendering storage-related information.
        
        Returns:
            Dictionary containing storage status information
        """
        try:
            context = self.get_storage_notification_context()
            
            if context:
                return {
                    'storage_notification': context.to_dict(),
                    'storage_limit_active': context.is_blocked,
                    'storage_banner_html': context.banner_html,
                    'hide_caption_form': context.should_hide_form
                }
            else:
                return {
                    'storage_notification': None,
                    'storage_limit_active': False,
                    'storage_banner_html': '',
                    'hide_caption_form': False
                }
                
        except Exception as e:
            logger.error(f"Error getting storage status for template: {e}")
            return {
                'storage_notification': None,
                'storage_limit_active': True,  # Safe default
                'storage_banner_html': self._create_error_banner_html(),
                'hide_caption_form': True  # Safe default
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the storage user notification system.
        
        Returns:
            Dictionary containing health check results
        """
        health = {
            'enforcer_healthy': False,
            'monitor_service_healthy': False,
            'config_service_healthy': False,
            'notification_context_accessible': False,
            'overall_healthy': False
        }
        
        try:
            # Check enforcer health
            enforcer_health = self.enforcer.health_check()
            health['enforcer_healthy'] = enforcer_health.get('overall_healthy', False)
            if not health['enforcer_healthy']:
                health['enforcer_error'] = 'Enforcer health check failed'
        except Exception as e:
            health['enforcer_error'] = str(e)
        
        try:
            # Check monitor service
            self.monitor_service.get_storage_metrics()
            health['monitor_service_healthy'] = True
        except Exception as e:
            health['monitor_error'] = str(e)
        
        try:
            # Check config service
            self.config_service.validate_storage_config()
            health['config_service_healthy'] = True
        except Exception as e:
            health['config_error'] = str(e)
        
        try:
            # Check notification context access
            self.get_storage_notification_context()
            health['notification_context_accessible'] = True
        except Exception as e:
            health['notification_context_error'] = str(e)
        
        # Overall health
        health['overall_healthy'] = all([
            health['enforcer_healthy'],
            health['monitor_service_healthy'],
            health['config_service_healthy'],
            health['notification_context_accessible']
        ])
        
        return health