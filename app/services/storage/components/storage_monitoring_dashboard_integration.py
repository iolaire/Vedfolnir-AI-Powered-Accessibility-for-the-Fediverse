# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Monitoring Dashboard Integration

This service integrates storage system monitoring with the existing monitoring dashboard,
providing storage metrics, alerts, and performance data for the admin dashboard.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .storage_health_checker import StorageHealthChecker, StorageHealthStatus
from .storage_configuration_service import StorageConfigurationService
from .storage_monitor_service import StorageMonitorService
from .storage_limit_enforcer import StorageLimitEnforcer

logger = logging.getLogger(__name__)


class StorageMonitoringDashboardIntegration:
    """
    Integration service for storage monitoring with the admin dashboard.
    
    This service provides:
    - Storage metrics for dashboard widgets
    - Storage alerts for alert panels
    - Storage performance data for monitoring
    - Integration with existing monitoring infrastructure
    """
    
    def __init__(self, db_manager=None):
        """
        Initialize the storage monitoring dashboard integration.
        
        Args:
            db_manager: Database manager for enforcer integration
        """
        self.config_service = StorageConfigurationService()
        self.monitor_service = StorageMonitorService(self.config_service)
        
        # Initialize enforcer if database manager is available
        self.enforcer_service = None
        if db_manager:
            try:
                self.enforcer_service = StorageLimitEnforcer(
                    config_service=self.config_service,
                    monitor_service=self.monitor_service,
                    db_manager=db_manager
                )
            except Exception as e:
                logger.warning(f"Could not initialize storage enforcer: {e}")
        
        self.health_checker = StorageHealthChecker(
            config_service=self.config_service,
            monitor_service=self.monitor_service,
            enforcer_service=self.enforcer_service
        )
        
        logger.info("Storage monitoring dashboard integration initialized")
    
    def get_storage_dashboard_metrics(self) -> Dict[str, Any]:
        """Get storage metrics for dashboard display"""
        try:
            # Get storage metrics
            storage_metrics = self.monitor_service.get_storage_metrics()
            
            # Get health status
            health_result = self.health_checker.check_comprehensive_health()
            
            # Get enforcement statistics if available
            enforcement_stats = {}
            if self.enforcer_service:
                try:
                    enforcement_stats = self.enforcer_service.get_enforcement_statistics()
                except Exception as e:
                    logger.warning(f"Could not get enforcement statistics: {e}")
            
            return {
                'storage_usage': {
                    'current_gb': storage_metrics.total_gb,
                    'limit_gb': storage_metrics.limit_gb,
                    'usage_percentage': storage_metrics.usage_percentage,
                    'warning_threshold_gb': self.config_service.get_warning_threshold_gb(),
                    'is_limit_exceeded': storage_metrics.is_limit_exceeded,
                    'is_warning_exceeded': storage_metrics.is_warning_exceeded
                },
                'system_health': {
                    'overall_status': health_result.overall_status.value,
                    'healthy_components': health_result.summary['healthy_components'],
                    'total_components': health_result.summary['total_components'],
                    'health_percentage': health_result.summary['health_percentage']
                },
                'enforcement': {
                    'currently_blocked': enforcement_stats.get('currently_blocked', False),
                    'total_checks': enforcement_stats.get('total_checks', 0),
                    'blocks_enforced': enforcement_stats.get('blocks_enforced', 0),
                    'automatic_unblocks': enforcement_stats.get('automatic_unblocks', 0)
                },
                'performance': {
                    'last_check_time': health_result.timestamp.isoformat(),
                    'avg_response_time_ms': health_result.performance_metrics.get('avg_component_response_time_ms', 0),
                    'cache_valid': self.monitor_service.get_cache_info().get('is_valid', False)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage dashboard metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_storage_dashboard_alerts(self) -> List[Dict[str, Any]]:
        """Get storage alerts for dashboard alert panels"""
        try:
            alerts = self.health_checker.get_storage_alerts()
            
            # Format alerts for dashboard display
            dashboard_alerts = []
            for alert in alerts:
                dashboard_alerts.append({
                    'id': f"storage_{alert['type']}_{hash(alert['message']) % 10000}",
                    'type': 'storage',
                    'severity': alert['severity'],
                    'title': f"Storage {alert.get('component', 'System')} Alert",
                    'message': alert['message'],
                    'timestamp': alert['timestamp'],
                    'component': alert.get('component', 'storage'),
                    'details': alert.get('details', {}),
                    'auto_dismiss': alert['severity'] == 'info',
                    'dismiss_after': 300 if alert['severity'] == 'info' else None  # 5 minutes for info alerts
                })
            
            return dashboard_alerts
            
        except Exception as e:
            logger.error(f"Error getting storage dashboard alerts: {e}")
            return [{
                'id': 'storage_error_alert',
                'type': 'storage',
                'severity': 'critical',
                'title': 'Storage Monitoring Error',
                'message': f'Storage monitoring system error: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'component': 'storage_monitoring'
            }]
    
    def get_storage_widget_data(self, widget_type: str) -> Dict[str, Any]:
        """Get data for specific storage dashboard widgets"""
        try:
            if widget_type == 'storage_usage_gauge':
                return self._get_storage_usage_gauge_data()
            elif widget_type == 'storage_health_status':
                return self._get_storage_health_status_data()
            elif widget_type == 'storage_performance_chart':
                return self._get_storage_performance_chart_data()
            elif widget_type == 'storage_enforcement_status':
                return self._get_storage_enforcement_status_data()
            else:
                return {'error': f'Unknown storage widget type: {widget_type}'}
                
        except Exception as e:
            logger.error(f"Error getting storage widget data for {widget_type}: {e}")
            return {'error': str(e)}
    
    def _get_storage_usage_gauge_data(self) -> Dict[str, Any]:
        """Get data for storage usage gauge widget"""
        metrics = self.monitor_service.get_storage_metrics()
        
        # Determine gauge color based on usage
        if metrics.is_limit_exceeded:
            color = 'red'
            status = 'critical'
        elif metrics.is_warning_exceeded:
            color = 'orange'
            status = 'warning'
        else:
            color = 'green'
            status = 'healthy'
        
        return {
            'value': metrics.usage_percentage,
            'max': 100,
            'color': color,
            'status': status,
            'label': f'{metrics.total_gb:.1f}GB / {metrics.limit_gb:.1f}GB',
            'subtitle': f'{metrics.usage_percentage:.1f}% used',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _get_storage_health_status_data(self) -> Dict[str, Any]:
        """Get data for storage health status widget"""
        health_result = self.health_checker.check_comprehensive_health()
        
        # Map health status to display properties
        status_map = {
            StorageHealthStatus.HEALTHY: {'color': 'green', 'icon': 'check-circle'},
            StorageHealthStatus.DEGRADED: {'color': 'orange', 'icon': 'exclamation-triangle'},
            StorageHealthStatus.UNHEALTHY: {'color': 'red', 'icon': 'times-circle'},
            StorageHealthStatus.ERROR: {'color': 'red', 'icon': 'exclamation-circle'}
        }
        
        status_info = status_map.get(health_result.overall_status, {'color': 'gray', 'icon': 'question-circle'})
        
        return {
            'status': health_result.overall_status.value,
            'color': status_info['color'],
            'icon': status_info['icon'],
            'message': f'{health_result.summary["healthy_components"]}/{health_result.summary["total_components"]} components healthy',
            'details': {
                'healthy': health_result.summary['healthy_components'],
                'degraded': health_result.summary['degraded_components'],
                'unhealthy': health_result.summary['unhealthy_components'],
                'error': health_result.summary['error_components']
            },
            'timestamp': health_result.timestamp.isoformat()
        }
    
    def _get_storage_performance_chart_data(self) -> Dict[str, Any]:
        """Get data for storage performance chart widget"""
        # This would typically show historical performance data
        # For now, return current performance metrics
        health_result = self.health_checker.check_comprehensive_health()
        
        # Create simple time series data (would be expanded with real historical data)
        current_time = datetime.now(timezone.utc)
        
        return {
            'chart_type': 'line',
            'data': [{
                'timestamp': current_time.isoformat(),
                'response_time_ms': health_result.performance_metrics.get('avg_component_response_time_ms', 0),
                'health_percentage': health_result.summary['health_percentage']
            }],
            'metrics': {
                'avg_response_time': health_result.performance_metrics.get('avg_component_response_time_ms', 0),
                'max_response_time': health_result.performance_metrics.get('max_component_response_time_ms', 0)
            },
            'timestamp': current_time.isoformat()
        }
    
    def _get_storage_enforcement_status_data(self) -> Dict[str, Any]:
        """Get data for storage enforcement status widget"""
        if not self.enforcer_service:
            return {
                'status': 'unavailable',
                'message': 'Storage enforcement not available',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        try:
            stats = self.enforcer_service.get_enforcement_statistics()
            
            return {
                'currently_blocked': stats.get('currently_blocked', False),
                'block_reason': stats.get('current_block_reason'),
                'total_checks': stats.get('total_checks', 0),
                'blocks_enforced': stats.get('blocks_enforced', 0),
                'automatic_unblocks': stats.get('automatic_unblocks', 0),
                'success_rate': ((stats.get('total_checks', 1) - stats.get('blocks_enforced', 0)) / stats.get('total_checks', 1) * 100) if stats.get('total_checks', 0) > 0 else 100,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting enforcement status: {e}")
            return {
                'status': 'error',
                'message': f'Enforcement status error: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_storage_monitoring_summary(self) -> Dict[str, Any]:
        """Get storage monitoring summary for integration with existing monitoring"""
        try:
            dashboard_metrics = self.get_storage_dashboard_metrics()
            alerts = self.get_storage_dashboard_alerts()
            
            return {
                'storage_system': {
                    'status': dashboard_metrics['system_health']['overall_status'],
                    'usage_percentage': dashboard_metrics['storage_usage']['usage_percentage'],
                    'limit_exceeded': dashboard_metrics['storage_usage']['is_limit_exceeded'],
                    'warning_exceeded': dashboard_metrics['storage_usage']['is_warning_exceeded'],
                    'currently_blocked': dashboard_metrics['enforcement']['currently_blocked'],
                    'health_percentage': dashboard_metrics['system_health']['health_percentage'],
                    'alerts_count': len(alerts),
                    'critical_alerts': len([a for a in alerts if a['severity'] == 'critical']),
                    'warning_alerts': len([a for a in alerts if a['severity'] == 'warning'])
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage monitoring summary: {e}")
            return {
                'storage_system': {
                    'status': 'error',
                    'error': str(e)
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }