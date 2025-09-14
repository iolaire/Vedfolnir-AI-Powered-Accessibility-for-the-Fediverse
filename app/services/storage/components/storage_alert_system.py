# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Alert System for monitoring storage system failures and configuration issues.

This service integrates with the existing alert manager to provide storage-specific
alerts for system failures, configuration issues, and performance problems.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

from .storage_health_checker import StorageHealthChecker, StorageHealthStatus
from .storage_configuration_service import StorageConfigurationService
from .storage_monitor_service import StorageMonitorService
from .storage_limit_enforcer import StorageLimitEnforcer

logger = logging.getLogger(__name__)


class StorageAlertType(Enum):
    """Types of storage alerts"""
    CONFIGURATION_ERROR = "storage_configuration_error"
    MONITORING_FAILURE = "storage_monitoring_failure"
    ENFORCEMENT_ERROR = "storage_enforcement_error"
    DIRECTORY_ACCESS_ERROR = "storage_directory_access_error"
    PERFORMANCE_DEGRADATION = "storage_performance_degradation"
    LIMIT_EXCEEDED = "storage_limit_exceeded"
    WARNING_THRESHOLD_EXCEEDED = "storage_warning_threshold_exceeded"
    SYSTEM_HEALTH_DEGRADED = "storage_system_health_degraded"


class StorageAlertSeverity(Enum):
    """Severity levels for storage alerts"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class StorageAlertSystem:
    """
    Storage alert system for monitoring and alerting on storage issues.
    
    This service provides:
    - Integration with existing alert manager
    - Storage-specific alert types and severities
    - Automatic alert generation based on health checks
    - Alert suppression and rate limiting
    """
    
    def __init__(self, 
                 db_manager=None,
                 alert_manager=None):
        """
        Initialize the storage alert system.
        
        Args:
            db_manager: Database manager for enforcer integration
            alert_manager: Existing alert manager instance
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
                logger.warning(f"Could not initialize storage enforcer for alerts: {e}")
        
        self.health_checker = StorageHealthChecker(
            config_service=self.config_service,
            monitor_service=self.monitor_service,
            enforcer_service=self.enforcer_service
        )
        
        # Alert manager integration
        self.alert_manager = alert_manager
        
        # Alert suppression tracking
        self._suppressed_alerts = {}
        self._alert_counts = {}
        
        logger.info("Storage alert system initialized")
    
    def check_and_generate_alerts(self) -> List[Dict[str, Any]]:
        """
        Check storage system health and generate alerts for issues.
        
        Returns:
            List of generated alerts
        """
        alerts = []
        
        try:
            # Get comprehensive health check
            health_result = self.health_checker.check_comprehensive_health()
            
            # Generate alerts based on health status
            alerts.extend(self._generate_health_alerts(health_result))
            
            # Generate storage usage alerts
            alerts.extend(self._generate_usage_alerts())
            
            # Generate performance alerts
            alerts.extend(self._generate_performance_alerts(health_result))
            
            # Generate configuration alerts
            alerts.extend(self._generate_configuration_alerts())
            
            # Filter suppressed alerts
            alerts = self._filter_suppressed_alerts(alerts)
            
            # Send alerts to alert manager if available
            if self.alert_manager:
                for alert in alerts:
                    self._send_alert_to_manager(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking and generating storage alerts: {e}")
            
            # Generate error alert
            error_alert = self._create_alert(
                alert_type=StorageAlertType.MONITORING_FAILURE,
                severity=StorageAlertSeverity.CRITICAL,
                message=f"Storage alert system failure: {str(e)}",
                details={'error': str(e)}
            )
            
            return [error_alert]
    
    def _generate_health_alerts(self, health_result) -> List[Dict[str, Any]]:
        """Generate alerts based on health check results"""
        alerts = []
        
        # Overall system health alert
        if health_result.overall_status == StorageHealthStatus.ERROR:
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.SYSTEM_HEALTH_DEGRADED,
                severity=StorageAlertSeverity.CRITICAL,
                message="Storage system is in error state",
                details={
                    'overall_status': health_result.overall_status.value,
                    'healthy_components': health_result.summary['healthy_components'],
                    'total_components': health_result.summary['total_components']
                }
            ))
        elif health_result.overall_status == StorageHealthStatus.UNHEALTHY:
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.SYSTEM_HEALTH_DEGRADED,
                severity=StorageAlertSeverity.CRITICAL,
                message="Storage system is unhealthy",
                details={
                    'overall_status': health_result.overall_status.value,
                    'unhealthy_components': health_result.summary['unhealthy_components'],
                    'error_components': health_result.summary['error_components']
                }
            ))
        elif health_result.overall_status == StorageHealthStatus.DEGRADED:
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.SYSTEM_HEALTH_DEGRADED,
                severity=StorageAlertSeverity.WARNING,
                message="Storage system performance is degraded",
                details={
                    'overall_status': health_result.overall_status.value,
                    'degraded_components': health_result.summary['degraded_components']
                }
            ))
        
        # Component-specific alerts
        for component_name, component in health_result.components.items():
            if component.status == StorageHealthStatus.ERROR:
                alerts.append(self._create_alert(
                    alert_type=self._get_component_alert_type(component_name),
                    severity=StorageAlertSeverity.CRITICAL,
                    message=f"Storage {component_name} component error: {component.message}",
                    details={
                        'component': component_name,
                        'status': component.status.value,
                        'response_time_ms': component.response_time_ms,
                        'component_details': component.details
                    }
                ))
            elif component.status == StorageHealthStatus.UNHEALTHY:
                alerts.append(self._create_alert(
                    alert_type=self._get_component_alert_type(component_name),
                    severity=StorageAlertSeverity.CRITICAL,
                    message=f"Storage {component_name} component is unhealthy: {component.message}",
                    details={
                        'component': component_name,
                        'status': component.status.value,
                        'response_time_ms': component.response_time_ms
                    }
                ))
        
        return alerts
    
    def _generate_usage_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts based on storage usage"""
        alerts = []
        
        try:
            metrics = self.monitor_service.get_storage_metrics()
            
            # Storage limit exceeded alert
            if metrics.is_limit_exceeded:
                alerts.append(self._create_alert(
                    alert_type=StorageAlertType.LIMIT_EXCEEDED,
                    severity=StorageAlertSeverity.CRITICAL,
                    message=f"Storage limit exceeded: {metrics.total_gb:.2f}GB / {metrics.limit_gb:.2f}GB ({metrics.usage_percentage:.1f}%)",
                    details={
                        'current_usage_gb': metrics.total_gb,
                        'limit_gb': metrics.limit_gb,
                        'usage_percentage': metrics.usage_percentage,
                        'bytes_over_limit': metrics.total_bytes - (metrics.limit_gb * 1024**3)
                    }
                ))
            
            # Warning threshold exceeded alert
            elif metrics.is_warning_exceeded:
                alerts.append(self._create_alert(
                    alert_type=StorageAlertType.WARNING_THRESHOLD_EXCEEDED,
                    severity=StorageAlertSeverity.WARNING,
                    message=f"Storage warning threshold exceeded: {metrics.total_gb:.2f}GB / {metrics.limit_gb:.2f}GB ({metrics.usage_percentage:.1f}%)",
                    details={
                        'current_usage_gb': metrics.total_gb,
                        'limit_gb': metrics.limit_gb,
                        'warning_threshold_gb': self.config_service.get_warning_threshold_gb(),
                        'usage_percentage': metrics.usage_percentage
                    }
                ))
            
        except Exception as e:
            logger.error(f"Error generating usage alerts: {e}")
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.MONITORING_FAILURE,
                severity=StorageAlertSeverity.CRITICAL,
                message=f"Failed to check storage usage: {str(e)}",
                details={'error': str(e)}
            ))
        
        return alerts
    
    def _generate_performance_alerts(self, health_result) -> List[Dict[str, Any]]:
        """Generate alerts based on performance metrics"""
        alerts = []
        
        # Check overall performance
        avg_response_time = health_result.performance_metrics.get('avg_component_response_time_ms', 0)
        max_response_time = health_result.performance_metrics.get('max_component_response_time_ms', 0)
        
        if avg_response_time > 2000:  # 2 seconds average
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.PERFORMANCE_DEGRADATION,
                severity=StorageAlertSeverity.WARNING,
                message=f"Storage system performance degraded: average response time {avg_response_time:.0f}ms",
                details={
                    'avg_response_time_ms': avg_response_time,
                    'max_response_time_ms': max_response_time,
                    'performance_threshold_ms': 2000
                }
            ))
        
        if max_response_time > 5000:  # 5 seconds max
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.PERFORMANCE_DEGRADATION,
                severity=StorageAlertSeverity.CRITICAL,
                message=f"Storage system performance critical: maximum response time {max_response_time:.0f}ms",
                details={
                    'max_response_time_ms': max_response_time,
                    'critical_threshold_ms': 5000
                }
            ))
        
        return alerts
    
    def _generate_configuration_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts based on configuration issues"""
        alerts = []
        
        try:
            # Check configuration validity
            is_valid = self.config_service.validate_storage_config()
            
            if not is_valid:
                config_summary = self.config_service.get_configuration_summary()
                alerts.append(self._create_alert(
                    alert_type=StorageAlertType.CONFIGURATION_ERROR,
                    severity=StorageAlertSeverity.CRITICAL,
                    message="Storage configuration is invalid",
                    details={
                        'configuration_valid': is_valid,
                        'configuration_summary': config_summary
                    }
                ))
            
        except Exception as e:
            logger.error(f"Error checking configuration: {e}")
            alerts.append(self._create_alert(
                alert_type=StorageAlertType.CONFIGURATION_ERROR,
                severity=StorageAlertSeverity.CRITICAL,
                message=f"Failed to validate storage configuration: {str(e)}",
                details={'error': str(e)}
            ))
        
        return alerts
    
    def _get_component_alert_type(self, component_name: str) -> StorageAlertType:
        """Get appropriate alert type for component"""
        component_alert_map = {
            'configuration': StorageAlertType.CONFIGURATION_ERROR,
            'monitoring': StorageAlertType.MONITORING_FAILURE,
            'enforcement': StorageAlertType.ENFORCEMENT_ERROR,
            'storage_directory': StorageAlertType.DIRECTORY_ACCESS_ERROR,
            'performance': StorageAlertType.PERFORMANCE_DEGRADATION
        }
        
        return component_alert_map.get(component_name, StorageAlertType.SYSTEM_HEALTH_DEGRADED)
    
    def _create_alert(self, 
                     alert_type: StorageAlertType,
                     severity: StorageAlertSeverity,
                     message: str,
                     details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a standardized alert dictionary"""
        return {
            'id': f"storage_{alert_type.value}_{hash(message) % 10000}",
            'type': alert_type.value,
            'severity': severity.value,
            'category': 'storage',
            'title': f"Storage {alert_type.value.replace('_', ' ').title()}",
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': details or {},
            'source': 'storage_alert_system',
            'auto_dismiss': severity == StorageAlertSeverity.INFO,
            'dismiss_after': 300 if severity == StorageAlertSeverity.INFO else None
        }
    
    def _filter_suppressed_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out suppressed or rate-limited alerts"""
        filtered_alerts = []
        current_time = datetime.now(timezone.utc)
        
        for alert in alerts:
            alert_key = f"{alert['type']}_{alert['severity']}"
            
            # Check if alert is suppressed
            if alert_key in self._suppressed_alerts:
                suppressed_until = self._suppressed_alerts[alert_key]
                if current_time < suppressed_until:
                    continue  # Skip suppressed alert
                else:
                    # Remove expired suppression
                    del self._suppressed_alerts[alert_key]
            
            # Rate limiting: limit same alert type to once per 5 minutes
            if alert_key in self._alert_counts:
                last_sent, count = self._alert_counts[alert_key]
                time_diff = (current_time - last_sent).total_seconds()
                
                if time_diff < 300:  # 5 minutes
                    if count >= 3:  # Max 3 alerts per 5 minutes
                        continue  # Skip rate-limited alert
                    else:
                        self._alert_counts[alert_key] = (current_time, count + 1)
                else:
                    # Reset count after 5 minutes
                    self._alert_counts[alert_key] = (current_time, 1)
            else:
                self._alert_counts[alert_key] = (current_time, 1)
            
            filtered_alerts.append(alert)
        
        return filtered_alerts
    
    def _send_alert_to_manager(self, alert: Dict[str, Any]) -> None:
        """Send alert to the existing alert manager"""
        try:
            if hasattr(self.alert_manager, 'create_alert'):
                # Use existing alert manager interface
                self.alert_manager.create_alert(
                    alert_type=alert['type'],
                    severity=alert['severity'],
                    message=alert['message'],
                    details=alert['details']
                )
            else:
                logger.warning("Alert manager does not have create_alert method")
                
        except Exception as e:
            logger.error(f"Failed to send alert to manager: {e}")
    
    def suppress_alert_type(self, alert_type: str, duration_minutes: int = 60) -> None:
        """Suppress alerts of a specific type for a duration"""
        from datetime import timedelta
        
        suppress_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self._suppressed_alerts[alert_type] = suppress_until
        
        logger.info(f"Suppressed storage alert type '{alert_type}' for {duration_minutes} minutes")
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get statistics about storage alerts"""
        return {
            'suppressed_alerts': len(self._suppressed_alerts),
            'alert_counts': len(self._alert_counts),
            'total_alerts_sent': sum(count for _, count in self._alert_counts.values()),
            'suppressed_alert_types': list(self._suppressed_alerts.keys()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }