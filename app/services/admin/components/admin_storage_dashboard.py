# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Storage Dashboard for displaying storage metrics and status in the admin interface.

This service provides storage monitoring integration for the admin dashboard,
including storage usage gauges, status indicators, and color-coded status display
based on storage usage levels.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics
from app.services.storage.components.storage_limit_enforcer import StorageLimitEnforcer

logger = logging.getLogger(__name__)


@dataclass
class StorageDashboardData:
    """Storage dashboard data structure for admin interface"""
    current_usage_gb: float
    limit_gb: float
    usage_percentage: float
    status_color: str
    status_text: str
    is_blocked: bool
    block_reason: Optional[str]
    warning_threshold_gb: float
    is_warning_exceeded: bool
    is_limit_exceeded: bool
    last_calculated: datetime
    cache_info: Dict[str, Any]
    enforcement_stats: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'current_usage_gb': self.current_usage_gb,
            'limit_gb': self.limit_gb,
            'usage_percentage': self.usage_percentage,
            'status_color': self.status_color,
            'status_text': self.status_text,
            'is_blocked': self.is_blocked,
            'block_reason': self.block_reason,
            'warning_threshold_gb': self.warning_threshold_gb,
            'is_warning_exceeded': self.is_warning_exceeded,
            'is_limit_exceeded': self.is_limit_exceeded,
            'last_calculated': self.last_calculated.isoformat() if self.last_calculated else None,
            'cache_info': self.cache_info,
            'enforcement_stats': self.enforcement_stats,
            'formatted_usage': f"{self.current_usage_gb:.2f} GB",
            'formatted_limit': f"{self.limit_gb:.2f} GB",
            'formatted_percentage': f"{self.usage_percentage:.1f}%",
            'available_space_gb': max(0, self.limit_gb - self.current_usage_gb),
            'formatted_available': f"{max(0, self.limit_gb - self.current_usage_gb):.2f} GB"
        }


class AdminStorageDashboard:
    """
    Admin dashboard integration for storage monitoring and management.
    
    This service provides:
    - Storage usage gauge and status indicators for admin dashboard
    - Color-coded storage status (green/yellow/red) based on usage levels
    - Storage metrics display with formatted values
    - Integration with storage limit enforcement system
    - Quick access to cleanup tools and override controls
    """
    
    # Status color thresholds
    GREEN_THRESHOLD = 70.0  # Below 70% usage
    YELLOW_THRESHOLD = 80.0  # 70-80% usage (warning threshold)
    RED_THRESHOLD = 100.0   # Above 80% usage or limit exceeded
    
    # Status text mappings
    STATUS_TEXTS = {
        'green': 'Normal',
        'yellow': 'Warning',
        'red': 'Critical'
    }
    
    def __init__(self, 
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 enforcer_service: Optional[StorageLimitEnforcer] = None):
        """
        Initialize the admin storage dashboard.
        
        Args:
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
            enforcer_service: Storage limit enforcer service instance
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        self.enforcer_service = enforcer_service or StorageLimitEnforcer(
            self.config_service, 
            self.monitor_service
        )
        
        logger.info("Admin storage dashboard initialized")
    
    def get_storage_status_color(self, usage_percentage: float, is_limit_exceeded: bool = False) -> str:
        """
        Get color-coded storage status based on usage percentage.
        
        Implements color-coded storage status (green/yellow/red) as specified
        in requirements 6.4 and 6.5.
        
        Args:
            usage_percentage: Current storage usage percentage
            is_limit_exceeded: Whether storage limit is exceeded
            
        Returns:
            str: Status color ('green', 'yellow', or 'red')
        """
        # Red status for limit exceeded or critical usage
        if is_limit_exceeded or usage_percentage >= self.YELLOW_THRESHOLD:
            return 'red'
        
        # Yellow status for warning threshold
        elif usage_percentage >= self.GREEN_THRESHOLD:
            return 'yellow'
        
        # Green status for normal usage
        else:
            return 'green'
    
    def format_storage_display(self, usage_gb: float, limit_gb: float) -> str:
        """
        Format storage usage for display in admin dashboard.
        
        Args:
            usage_gb: Current usage in GB
            limit_gb: Storage limit in GB
            
        Returns:
            str: Formatted storage display string
        """
        return f"{usage_gb:.2f} GB / {limit_gb:.2f} GB"
    
    def get_storage_dashboard_data(self) -> StorageDashboardData:
        """
        Get comprehensive storage dashboard data for admin interface.
        
        This method implements the core dashboard data collection as specified
        in requirements 6.1, 6.2, 6.3, 6.4, and 6.5.
        
        Returns:
            StorageDashboardData: Complete dashboard data structure
            
        Raises:
            Exception: If storage data collection fails
        """
        try:
            # Get current storage metrics
            metrics = self.monitor_service.get_storage_metrics()
            
            # Get storage status color
            status_color = self.get_storage_status_color(
                metrics.usage_percentage, 
                metrics.is_limit_exceeded
            )
            
            # Get status text
            status_text = self.STATUS_TEXTS.get(status_color, 'Unknown')
            
            # Get blocking state from enforcer
            blocking_state = self.enforcer_service.get_blocking_state()
            is_blocked = blocking_state.is_blocked if blocking_state else False
            block_reason = blocking_state.reason if blocking_state and blocking_state.is_blocked else None
            
            # Get cache information
            cache_info = self.monitor_service.get_cache_info()
            
            # Get enforcement statistics
            enforcement_stats = self.enforcer_service.get_enforcement_statistics()
            
            # Create dashboard data
            dashboard_data = StorageDashboardData(
                current_usage_gb=metrics.total_gb,
                limit_gb=metrics.limit_gb,
                usage_percentage=metrics.usage_percentage,
                status_color=status_color,
                status_text=status_text,
                is_blocked=is_blocked,
                block_reason=block_reason,
                warning_threshold_gb=self.config_service.get_warning_threshold_gb(),
                is_warning_exceeded=metrics.is_warning_exceeded,
                is_limit_exceeded=metrics.is_limit_exceeded,
                last_calculated=metrics.last_calculated,
                cache_info=cache_info,
                enforcement_stats=enforcement_stats
            )
            
            logger.debug(f"Storage dashboard data collected: {metrics.total_gb:.2f}GB / {metrics.limit_gb:.2f}GB ({metrics.usage_percentage:.1f}%) - {status_color}")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get storage dashboard data: {e}")
            
            # Return safe default data on error
            return self._get_error_dashboard_data(str(e))
    
    def _get_error_dashboard_data(self, error_message: str) -> StorageDashboardData:
        """
        Get safe default dashboard data when storage data collection fails.
        
        Args:
            error_message: Error message to include
            
        Returns:
            StorageDashboardData: Safe default dashboard data
        """
        try:
            limit_gb = self.config_service.get_max_storage_gb()
            warning_threshold_gb = self.config_service.get_warning_threshold_gb()
        except Exception:
            limit_gb = 10.0  # Default fallback
            warning_threshold_gb = 8.0  # Default fallback
        
        return StorageDashboardData(
            current_usage_gb=0.0,
            limit_gb=limit_gb,
            usage_percentage=0.0,
            status_color='red',
            status_text='Error',
            is_blocked=True,  # Safe mode - assume blocked on error
            block_reason=f"Storage monitoring error: {error_message}",
            warning_threshold_gb=warning_threshold_gb,
            is_warning_exceeded=False,
            is_limit_exceeded=False,
            last_calculated=datetime.now(),
            cache_info={'has_cache': False, 'error': error_message},
            enforcement_stats={'error': error_message}
        )
    
    def get_storage_gauge_data(self) -> Dict[str, Any]:
        """
        Get data specifically formatted for storage usage gauge display.
        
        Returns:
            dict: Gauge-specific data for frontend visualization
        """
        try:
            dashboard_data = self.get_storage_dashboard_data()
            dashboard_dict = dashboard_data.to_dict()
            
            # Calculate gauge segments for visual display
            usage_percentage = min(dashboard_data.usage_percentage, 100.0)  # Cap at 100% for display
            warning_percentage = (dashboard_data.warning_threshold_gb / dashboard_data.limit_gb) * 100.0
            
            return {
                'current_percentage': usage_percentage,
                'warning_percentage': warning_percentage,
                'status_color': dashboard_data.status_color,
                'status_text': dashboard_data.status_text,
                'current_usage': dashboard_dict['formatted_usage'],
                'limit': dashboard_dict['formatted_limit'],
                'available': dashboard_dict['formatted_available'],
                'is_over_limit': dashboard_data.usage_percentage > 100.0,
                'gauge_color_class': f'storage-gauge-{dashboard_data.status_color}',
                'progress_bar_class': f'bg-{self._get_bootstrap_color(dashboard_data.status_color)}'
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage gauge data: {e}")
            return {
                'current_percentage': 0.0,
                'warning_percentage': 80.0,
                'status_color': 'red',
                'status_text': 'Error',
                'current_usage': '0.00 GB',
                'limit': '10.00 GB',
                'available': '10.00 GB',
                'is_over_limit': False,
                'gauge_color_class': 'storage-gauge-red',
                'progress_bar_class': 'bg-danger',
                'error': str(e)
            }
    
    def _get_bootstrap_color(self, status_color: str) -> str:
        """
        Convert status color to Bootstrap color class.
        
        Args:
            status_color: Status color ('green', 'yellow', 'red')
            
        Returns:
            str: Bootstrap color class
        """
        color_mapping = {
            'green': 'success',
            'yellow': 'warning',
            'red': 'danger'
        }
        return color_mapping.get(status_color, 'secondary')
    
    def get_storage_summary_card_data(self) -> Dict[str, Any]:
        """
        Get data for storage summary card display in admin dashboard.
        
        Returns:
            dict: Summary card data for dashboard display
        """
        try:
            dashboard_data = self.get_storage_dashboard_data()
            dashboard_dict = dashboard_data.to_dict()
            
            # Determine card styling based on status
            card_class = f"border-{self._get_bootstrap_color(dashboard_data.status_color)}"
            header_class = f"bg-{self._get_bootstrap_color(dashboard_data.status_color)} text-white"
            
            # Create status icon
            status_icons = {
                'green': 'bi-check-circle-fill',
                'yellow': 'bi-exclamation-triangle-fill',
                'red': 'bi-x-circle-fill'
            }
            status_icon = status_icons.get(dashboard_data.status_color, 'bi-question-circle-fill')
            
            return {
                'title': 'Storage Usage',
                'current_usage': dashboard_dict['formatted_usage'],
                'limit': dashboard_dict['formatted_limit'],
                'percentage': dashboard_dict['formatted_percentage'],
                'available': dashboard_dict['formatted_available'],
                'status_text': dashboard_data.status_text,
                'status_color': dashboard_data.status_color,
                'status_icon': status_icon,
                'card_class': card_class,
                'header_class': header_class,
                'is_blocked': dashboard_data.is_blocked,
                'block_reason': dashboard_data.block_reason,
                'is_warning': dashboard_data.is_warning_exceeded,
                'is_critical': dashboard_data.is_limit_exceeded,
                'last_updated': dashboard_data.last_calculated.strftime('%Y-%m-%d %H:%M:%S') if dashboard_data.last_calculated else 'Unknown'
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage summary card data: {e}")
            return {
                'title': 'Storage Usage',
                'current_usage': '0.00 GB',
                'limit': '10.00 GB',
                'percentage': '0.0%',
                'available': '10.00 GB',
                'status_text': 'Error',
                'status_color': 'red',
                'status_icon': 'bi-x-circle-fill',
                'card_class': 'border-danger',
                'header_class': 'bg-danger text-white',
                'is_blocked': True,
                'block_reason': f'Storage monitoring error: {e}',
                'is_warning': False,
                'is_critical': False,
                'last_updated': 'Error',
                'error': str(e)
            }
    
    def get_quick_actions_data(self) -> Dict[str, Any]:
        """
        Get data for storage-related quick actions in admin dashboard.
        
        Returns:
            dict: Quick actions data for dashboard display
        """
        try:
            dashboard_data = self.get_storage_dashboard_data()
            
            # Determine available actions based on current state
            actions = []
            
            # Cleanup action (always available)
            actions.append({
                'title': 'Data Cleanup',
                'description': 'Free up storage space',
                'url': 'admin.cleanup',  # Flask route name
                'icon': 'bi-trash',
                'class': 'btn-outline-warning',
                'priority': 1 if dashboard_data.is_warning_exceeded else 3
            })
            
            # Override action (if blocked)
            if dashboard_data.is_blocked:
                actions.append({
                    'title': 'Override Limits',
                    'description': 'Temporarily bypass storage limits',
                    'url': 'admin.storage_override',  # Flask route name (to be implemented)
                    'icon': 'bi-unlock',
                    'class': 'btn-outline-danger',
                    'priority': 1
                })
            
            # Refresh action
            actions.append({
                'title': 'Refresh Storage',
                'description': 'Recalculate storage usage',
                'url': 'admin.storage_refresh',  # Flask route name (to be implemented)
                'icon': 'bi-arrow-clockwise',
                'class': 'btn-outline-primary',
                'priority': 2
            })
            
            # Sort actions by priority
            actions.sort(key=lambda x: x['priority'])
            
            return {
                'actions': actions,
                'has_critical_actions': any(action['priority'] == 1 for action in actions),
                'total_actions': len(actions)
            }
            
        except Exception as e:
            logger.error(f"Failed to get quick actions data: {e}")
            return {
                'actions': [{
                    'title': 'Storage Error',
                    'description': 'Storage monitoring unavailable',
                    'url': '#',
                    'icon': 'bi-exclamation-triangle',
                    'class': 'btn-outline-danger disabled',
                    'priority': 1
                }],
                'has_critical_actions': True,
                'total_actions': 1,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the storage dashboard system.
        
        Returns:
            dict: Health check results
        """
        health = {
            'config_service_healthy': False,
            'monitor_service_healthy': False,
            'enforcer_service_healthy': False,
            'dashboard_data_accessible': False,
            'overall_healthy': False
        }
        
        try:
            # Check config service
            self.config_service.validate_storage_config()
            health['config_service_healthy'] = True
        except Exception as e:
            health['config_error'] = str(e)
        
        try:
            # Check monitor service
            self.monitor_service.get_storage_metrics()
            health['monitor_service_healthy'] = True
        except Exception as e:
            health['monitor_error'] = str(e)
        
        try:
            # Check enforcer service
            enforcer_health = self.enforcer_service.health_check()
            health['enforcer_service_healthy'] = enforcer_health.get('overall_healthy', False)
            if not health['enforcer_service_healthy']:
                health['enforcer_error'] = enforcer_health
        except Exception as e:
            health['enforcer_error'] = str(e)
        
        try:
            # Check dashboard data access
            self.get_storage_dashboard_data()
            health['dashboard_data_accessible'] = True
        except Exception as e:
            health['dashboard_error'] = str(e)
        
        # Overall health
        health['overall_healthy'] = all([
            health['config_service_healthy'],
            health['monitor_service_healthy'],
            health['enforcer_service_healthy'],
            health['dashboard_data_accessible']
        ])
        
        return health