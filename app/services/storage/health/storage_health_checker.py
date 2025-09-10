# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Health Checker for comprehensive storage system monitoring.

This service provides health checks for all storage system components including
configuration, monitoring, enforcement, and performance metrics.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService
from storage_limit_enforcer import StorageLimitEnforcer

logger = logging.getLogger(__name__)


class StorageHealthStatus(Enum):
    """Storage system health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


@dataclass
class StorageComponentHealth:
    """Health status for a storage system component"""
    component: str
    status: StorageHealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class StorageSystemHealth:
    """Overall storage system health status"""
    overall_status: StorageHealthStatus
    timestamp: datetime
    components: Dict[str, StorageComponentHealth]
    summary: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class StorageHealthChecker:
    """
    Comprehensive storage system health checker.
    
    This service provides:
    - Health checks for all storage system components
    - Performance monitoring and metrics collection
    - Alert generation for storage system issues
    - Integration with existing monitoring infrastructure
    """
    
    def __init__(self, 
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 enforcer_service: Optional[StorageLimitEnforcer] = None):
        """
        Initialize the storage health checker.
        
        Args:
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
            enforcer_service: Storage limit enforcer instance
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        self.enforcer_service = enforcer_service
        
        # Performance tracking
        self._performance_history = []
        self._max_history_entries = 100
        
        logger.info("Storage health checker initialized")
    
    def check_comprehensive_health(self) -> StorageSystemHealth:
        """
        Perform comprehensive health check of the entire storage system.
        
        Returns:
            StorageSystemHealth with complete system status
        """
        start_time = time.time()
        components = {}
        alerts = []
        
        try:
            # Check configuration service
            config_health = self._check_configuration_health()
            components['configuration'] = config_health
            
            # Check monitoring service
            monitor_health = self._check_monitoring_health()
            components['monitoring'] = monitor_health
            
            # Check enforcer service if available
            if self.enforcer_service:
                enforcer_health = self._check_enforcer_health()
                components['enforcement'] = enforcer_health
            
            # Check storage directory health
            directory_health = self._check_storage_directory_health()
            components['storage_directory'] = directory_health
            
            # Check performance metrics
            performance_health = self._check_performance_health()
            components['performance'] = performance_health
            
            # Determine overall status
            overall_status = self._determine_overall_status(components)
            
            # Generate alerts for unhealthy components
            alerts = self._generate_health_alerts(components)
            
            # Collect performance metrics
            performance_metrics = self._collect_performance_metrics(components)
            
            # Create summary
            summary = self._create_health_summary(components, performance_metrics)
            
            # Record performance
            total_time = (time.time() - start_time) * 1000
            self._record_performance_metric('health_check_duration_ms', total_time)
            
            return StorageSystemHealth(
                overall_status=overall_status,
                timestamp=datetime.now(timezone.utc),
                components=components,
                summary=summary,
                alerts=alerts,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            
            # Return error state
            error_component = StorageComponentHealth(
                component="health_checker",
                status=StorageHealthStatus.ERROR,
                message=f"Health check system error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
            
            return StorageSystemHealth(
                overall_status=StorageHealthStatus.ERROR,
                timestamp=datetime.now(timezone.utc),
                components={"health_checker": error_component},
                summary={"error": "Health check system failure"},
                alerts=[{
                    "type": "system_error",
                    "severity": "critical",
                    "message": f"Storage health check system failure: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }],
                performance_metrics={}
            )
    
    def _check_configuration_health(self) -> StorageComponentHealth:
        """Check storage configuration service health"""
        start_time = time.time()
        
        try:
            # Test configuration validation
            is_valid = self.config_service.validate_storage_config()
            config_summary = self.config_service.get_configuration_summary()
            
            response_time = (time.time() - start_time) * 1000
            
            if is_valid:
                status = StorageHealthStatus.HEALTHY
                message = "Storage configuration is valid and healthy"
            else:
                status = StorageHealthStatus.UNHEALTHY
                message = "Storage configuration validation failed"
            
            return StorageComponentHealth(
                component="configuration",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details=config_summary,
                metrics={
                    "max_storage_gb": config_summary.get("max_storage_gb", 0),
                    "warning_threshold_gb": config_summary.get("warning_threshold_gb", 0),
                    "monitoring_enabled": config_summary.get("monitoring_enabled", False)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Configuration health check failed: {e}")
            
            return StorageComponentHealth(
                component="configuration",
                status=StorageHealthStatus.ERROR,
                message=f"Configuration health check error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def _check_monitoring_health(self) -> StorageComponentHealth:
        """Check storage monitoring service health"""
        start_time = time.time()
        
        try:
            # Test storage metrics calculation
            metrics = self.monitor_service.get_storage_metrics()
            cache_info = self.monitor_service.get_cache_info()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on metrics and performance
            if response_time > 5000:  # 5 seconds
                status = StorageHealthStatus.DEGRADED
                message = f"Storage monitoring responding slowly ({response_time:.0f}ms)"
            elif metrics.is_limit_exceeded:
                status = StorageHealthStatus.DEGRADED
                message = f"Storage limit exceeded ({metrics.usage_percentage:.1f}%)"
            elif metrics.is_warning_exceeded:
                status = StorageHealthStatus.DEGRADED
                message = f"Storage warning threshold exceeded ({metrics.usage_percentage:.1f}%)"
            else:
                status = StorageHealthStatus.HEALTHY
                message = f"Storage monitoring healthy ({metrics.usage_percentage:.1f}% used)"
            
            return StorageComponentHealth(
                component="monitoring",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "storage_metrics": metrics.to_dict(),
                    "cache_info": cache_info
                },
                metrics={
                    "storage_usage_gb": metrics.total_gb,
                    "storage_limit_gb": metrics.limit_gb,
                    "usage_percentage": metrics.usage_percentage,
                    "cache_valid": cache_info.get("is_valid", False),
                    "cache_age_seconds": cache_info.get("cache_age_seconds", 0)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Monitoring health check failed: {e}")
            
            return StorageComponentHealth(
                component="monitoring",
                status=StorageHealthStatus.ERROR,
                message=f"Monitoring health check error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def _check_enforcer_health(self) -> StorageComponentHealth:
        """Check storage limit enforcer health"""
        start_time = time.time()
        
        try:
            # Test enforcer health check
            enforcer_health = self.enforcer_service.health_check()
            enforcement_stats = self.enforcer_service.get_enforcement_statistics()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on enforcer health
            if enforcer_health.get('overall_healthy', False):
                status = StorageHealthStatus.HEALTHY
                message = "Storage limit enforcement is healthy"
            else:
                status = StorageHealthStatus.UNHEALTHY
                message = "Storage limit enforcement has issues"
            
            return StorageComponentHealth(
                component="enforcement",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "enforcer_health": enforcer_health,
                    "enforcement_stats": enforcement_stats
                },
                metrics={
                    "currently_blocked": enforcement_stats.get("currently_blocked", False),
                    "total_checks": enforcement_stats.get("total_checks", 0),
                    "blocks_enforced": enforcement_stats.get("blocks_enforced", 0),
                    "automatic_unblocks": enforcement_stats.get("automatic_unblocks", 0)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Enforcer health check failed: {e}")
            
            return StorageComponentHealth(
                component="enforcement",
                status=StorageHealthStatus.ERROR,
                message=f"Enforcer health check error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def _check_storage_directory_health(self) -> StorageComponentHealth:
        """Check storage directory accessibility and permissions"""
        start_time = time.time()
        
        try:
            import os
            import shutil
            from pathlib import Path
            
            storage_dir = Path(self.monitor_service.STORAGE_IMAGES_DIR)
            issues = []
            
            # Check directory existence
            if not storage_dir.exists():
                issues.append("Storage directory does not exist")
            elif not storage_dir.is_dir():
                issues.append("Storage path is not a directory")
            
            # Check permissions
            if storage_dir.exists():
                if not os.access(storage_dir, os.R_OK):
                    issues.append("Storage directory not readable")
                if not os.access(storage_dir, os.W_OK):
                    issues.append("Storage directory not writable")
            
            # Check disk space
            if storage_dir.exists():
                disk_usage = shutil.disk_usage(storage_dir)
                free_gb = disk_usage.free / (1024**3)
                total_gb = disk_usage.total / (1024**3)
                used_gb = (disk_usage.total - disk_usage.free) / (1024**3)
                
                if free_gb < 1.0:  # Less than 1GB free
                    issues.append(f"Low disk space: {free_gb:.2f}GB free")
                elif free_gb < 5.0:  # Less than 5GB free
                    issues.append(f"Disk space warning: {free_gb:.2f}GB free")
            else:
                free_gb = total_gb = used_gb = 0
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if issues:
                critical_issues = [issue for issue in issues if 
                                 "does not exist" in issue or 
                                 "not readable" in issue or 
                                 "not writable" in issue]
                
                if critical_issues:
                    status = StorageHealthStatus.UNHEALTHY
                    message = "; ".join(critical_issues)
                else:
                    status = StorageHealthStatus.DEGRADED
                    message = "; ".join(issues)
            else:
                status = StorageHealthStatus.HEALTHY
                message = f"Storage directory healthy ({free_gb:.1f}GB free)"
            
            return StorageComponentHealth(
                component="storage_directory",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "directory_path": str(storage_dir),
                    "exists": storage_dir.exists(),
                    "is_directory": storage_dir.is_dir() if storage_dir.exists() else False,
                    "readable": os.access(storage_dir, os.R_OK) if storage_dir.exists() else False,
                    "writable": os.access(storage_dir, os.W_OK) if storage_dir.exists() else False,
                    "issues": issues
                },
                metrics={
                    "disk_free_gb": free_gb,
                    "disk_total_gb": total_gb,
                    "disk_used_gb": used_gb,
                    "disk_usage_percentage": (used_gb / total_gb * 100) if total_gb > 0 else 0
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Storage directory health check failed: {e}")
            
            return StorageComponentHealth(
                component="storage_directory",
                status=StorageHealthStatus.ERROR,
                message=f"Directory health check error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def _check_performance_health(self) -> StorageComponentHealth:
        """Check storage system performance metrics"""
        start_time = time.time()
        
        try:
            # Get recent performance history
            recent_metrics = self._get_recent_performance_metrics()
            
            # Calculate performance statistics
            if recent_metrics:
                avg_response_time = sum(recent_metrics) / len(recent_metrics)
                max_response_time = max(recent_metrics)
                min_response_time = min(recent_metrics)
            else:
                avg_response_time = max_response_time = min_response_time = 0
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on performance
            if avg_response_time > 2000:  # 2 seconds average
                status = StorageHealthStatus.DEGRADED
                message = f"Storage performance degraded (avg: {avg_response_time:.0f}ms)"
            elif max_response_time > 5000:  # 5 seconds max
                status = StorageHealthStatus.DEGRADED
                message = f"Storage performance spikes detected (max: {max_response_time:.0f}ms)"
            else:
                status = StorageHealthStatus.HEALTHY
                message = f"Storage performance healthy (avg: {avg_response_time:.0f}ms)"
            
            return StorageComponentHealth(
                component="performance",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "recent_metrics_count": len(recent_metrics),
                    "performance_history_size": len(self._performance_history)
                },
                metrics={
                    "avg_response_time_ms": avg_response_time,
                    "max_response_time_ms": max_response_time,
                    "min_response_time_ms": min_response_time,
                    "metrics_collected": len(recent_metrics)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Performance health check failed: {e}")
            
            return StorageComponentHealth(
                component="performance",
                status=StorageHealthStatus.ERROR,
                message=f"Performance health check error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def _determine_overall_status(self, components: Dict[str, StorageComponentHealth]) -> StorageHealthStatus:
        """Determine overall system status from component statuses"""
        statuses = [component.status for component in components.values()]
        
        if StorageHealthStatus.ERROR in statuses:
            return StorageHealthStatus.ERROR
        elif StorageHealthStatus.UNHEALTHY in statuses:
            return StorageHealthStatus.UNHEALTHY
        elif StorageHealthStatus.DEGRADED in statuses:
            return StorageHealthStatus.DEGRADED
        else:
            return StorageHealthStatus.HEALTHY
    
    def _generate_health_alerts(self, components: Dict[str, StorageComponentHealth]) -> List[Dict[str, Any]]:
        """Generate alerts for unhealthy components"""
        alerts = []
        
        for component_name, component in components.items():
            if component.status in [StorageHealthStatus.UNHEALTHY, StorageHealthStatus.ERROR]:
                severity = "critical" if component.status == StorageHealthStatus.ERROR else "warning"
                
                alerts.append({
                    "type": "storage_component_unhealthy",
                    "severity": severity,
                    "component": component_name,
                    "message": f"Storage {component_name} component is {component.status.value}: {component.message}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": component.details
                })
            elif component.status == StorageHealthStatus.DEGRADED:
                alerts.append({
                    "type": "storage_component_degraded",
                    "severity": "warning",
                    "component": component_name,
                    "message": f"Storage {component_name} component is degraded: {component.message}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": component.details
                })
        
        return alerts
    
    def _collect_performance_metrics(self, components: Dict[str, StorageComponentHealth]) -> Dict[str, Any]:
        """Collect performance metrics from all components"""
        metrics = {}
        
        for component_name, component in components.items():
            if component.response_time_ms is not None:
                metrics[f"{component_name}_response_time_ms"] = component.response_time_ms
            
            if component.metrics:
                for metric_name, metric_value in component.metrics.items():
                    metrics[f"{component_name}_{metric_name}"] = metric_value
        
        # Add overall metrics
        response_times = [c.response_time_ms for c in components.values() if c.response_time_ms is not None]
        if response_times:
            metrics["total_response_time_ms"] = sum(response_times)
            metrics["avg_component_response_time_ms"] = sum(response_times) / len(response_times)
            metrics["max_component_response_time_ms"] = max(response_times)
        
        return metrics
    
    def _create_health_summary(self, components: Dict[str, StorageComponentHealth], 
                              performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create health summary from components and metrics"""
        healthy_count = len([c for c in components.values() if c.status == StorageHealthStatus.HEALTHY])
        degraded_count = len([c for c in components.values() if c.status == StorageHealthStatus.DEGRADED])
        unhealthy_count = len([c for c in components.values() if c.status == StorageHealthStatus.UNHEALTHY])
        error_count = len([c for c in components.values() if c.status == StorageHealthStatus.ERROR])
        
        return {
            "total_components": len(components),
            "healthy_components": healthy_count,
            "degraded_components": degraded_count,
            "unhealthy_components": unhealthy_count,
            "error_components": error_count,
            "health_percentage": (healthy_count / len(components) * 100) if components else 0,
            "performance_metrics_count": len(performance_metrics),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }
    
    def _record_performance_metric(self, metric_name: str, value: float) -> None:
        """Record a performance metric for tracking"""
        metric_entry = {
            "metric": metric_name,
            "value": value,
            "timestamp": datetime.now(timezone.utc)
        }
        
        self._performance_history.append(metric_entry)
        
        # Limit history size
        if len(self._performance_history) > self._max_history_entries:
            self._performance_history = self._performance_history[-self._max_history_entries:]
    
    def _get_recent_performance_metrics(self, metric_name: str = "health_check_duration_ms", 
                                       limit: int = 10) -> List[float]:
        """Get recent performance metrics for analysis"""
        recent_metrics = [
            entry["value"] for entry in self._performance_history[-limit:]
            if entry["metric"] == metric_name
        ]
        return recent_metrics
    
    def get_storage_health_metrics(self) -> Dict[str, Any]:
        """Get storage health metrics for monitoring integration"""
        try:
            health = self.check_comprehensive_health()
            
            # Convert to monitoring-friendly format
            metrics = {
                "storage_system_healthy": 1 if health.overall_status == StorageHealthStatus.HEALTHY else 0,
                "storage_system_status": health.overall_status.value,
                "storage_components_total": health.summary["total_components"],
                "storage_components_healthy": health.summary["healthy_components"],
                "storage_components_degraded": health.summary["degraded_components"],
                "storage_components_unhealthy": health.summary["unhealthy_components"],
                "storage_components_error": health.summary["error_components"],
                "storage_health_percentage": health.summary["health_percentage"],
                "storage_alerts_count": len(health.alerts),
                "storage_last_check_timestamp": health.timestamp.timestamp()
            }
            
            # Add performance metrics
            metrics.update(health.performance_metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting storage health metrics: {e}")
            return {
                "storage_system_healthy": 0,
                "storage_system_status": "error",
                "storage_health_error": str(e)
            }
    
    def get_storage_alerts(self) -> List[Dict[str, Any]]:
        """Get current storage system alerts"""
        try:
            health = self.check_comprehensive_health()
            return health.alerts
        except Exception as e:
            logger.error(f"Error getting storage alerts: {e}")
            return [{
                "type": "storage_health_check_error",
                "severity": "critical",
                "message": f"Storage health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]