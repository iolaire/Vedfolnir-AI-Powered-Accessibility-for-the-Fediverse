# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration Health Checker

This module provides runtime health checking and monitoring for WebSocket
configuration, including performance metrics and automated issue detection.
"""

import os
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

from websocket_config_validator import WebSocketConfigValidator, ConfigurationReport


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Health check metric"""
    name: str
    value: Any
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@dataclass
class HealthCheckResult:
    """Health check result"""
    timestamp: datetime = field(default_factory=datetime.now)
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    metrics: List[HealthMetric] = field(default_factory=list)
    configuration_health: Optional[ConfigurationReport] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def is_healthy(self) -> bool:
        """Check if overall status is healthy"""
        return self.overall_status == HealthStatus.HEALTHY
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return (
            self.overall_status == HealthStatus.WARNING or
            any(metric.status == HealthStatus.WARNING for metric in self.metrics)
        )
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues"""
        return (
            self.overall_status == HealthStatus.CRITICAL or
            any(metric.status == HealthStatus.CRITICAL for metric in self.metrics)
        )


class WebSocketConfigHealthChecker:
    """
    WebSocket configuration health checker
    
    Provides runtime health monitoring, performance metrics collection,
    and automated issue detection for WebSocket configuration.
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize health checker
        
        Args:
            check_interval: Health check interval in seconds
        """
        self.validator = WebSocketConfigValidator()
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval
        
        # Health check history
        self._health_history = deque(maxlen=100)
        self._performance_history = deque(maxlen=1000)
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._last_check_time = None
        
        # Health check callbacks
        self._health_callbacks: List[Callable[[HealthCheckResult], None]] = []
        
        # Performance metrics
        self._performance_metrics = {
            "config_validation_time": deque(maxlen=100),
            "health_check_time": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
            "cpu_usage": deque(maxlen=100)
        }
    
    def perform_health_check(self) -> HealthCheckResult:
        """
        Perform comprehensive health check
        
        Returns:
            Health check result with metrics and recommendations
        """
        start_time = time.time()
        result = HealthCheckResult()
        
        try:
            # Validate configuration
            config_start = time.time()
            result.configuration_health = self.validator.validate_configuration()
            config_time = time.time() - config_start
            
            self._performance_metrics["config_validation_time"].append(config_time)
            
            # Check configuration health
            self._check_configuration_health(result)
            
            # Check environment variables
            self._check_environment_variables(result)
            
            # Check performance metrics
            self._check_performance_metrics(result)
            
            # Check system resources
            self._check_system_resources(result)
            
            # Check connectivity
            self._check_connectivity(result)
            
            # Generate recommendations
            self._generate_recommendations(result)
            
            # Determine overall status
            result.overall_status = self._determine_overall_status(result)
            
            # Record performance metrics
            health_check_time = time.time() - start_time
            self._performance_metrics["health_check_time"].append(health_check_time)
            
            result.performance_metrics = {
                "health_check_duration": health_check_time,
                "config_validation_duration": config_time,
                "total_metrics": len(result.metrics),
                "timestamp": result.timestamp.isoformat()
            }
            
            # Store in history
            self._health_history.append(result)
            self._last_check_time = result.timestamp
            
            self.logger.info(f"Health check completed: {result.overall_status.value}")
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            result.overall_status = HealthStatus.CRITICAL
            result.metrics.append(HealthMetric(
                name="health_check_error",
                value=str(e),
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}"
            ))
        
        # Notify callbacks
        for callback in self._health_callbacks:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Health check callback failed: {e}")
        
        return result
    
    def _check_configuration_health(self, result: HealthCheckResult) -> None:
        """Check configuration validation health"""
        if not result.configuration_health:
            result.metrics.append(HealthMetric(
                name="configuration_validation",
                value="failed",
                status=HealthStatus.CRITICAL,
                message="Configuration validation failed"
            ))
            return
        
        config_health = result.configuration_health
        
        # Check validation errors
        if config_health.errors:
            result.metrics.append(HealthMetric(
                name="configuration_errors",
                value=len(config_health.errors),
                status=HealthStatus.CRITICAL,
                message=f"Configuration has {len(config_health.errors)} errors",
                threshold_critical=1
            ))
        
        # Check validation warnings
        if config_health.warnings:
            result.metrics.append(HealthMetric(
                name="configuration_warnings",
                value=len(config_health.warnings),
                status=HealthStatus.WARNING,
                message=f"Configuration has {len(config_health.warnings)} warnings",
                threshold_warning=1
            ))
        
        # Check missing required fields
        if config_health.missing_required:
            result.metrics.append(HealthMetric(
                name="missing_required_fields",
                value=len(config_health.missing_required),
                status=HealthStatus.CRITICAL,
                message=f"Missing {len(config_health.missing_required)} required fields",
                threshold_critical=1
            ))
        
        # Check health score
        health_score = config_health.health_score
        if health_score < 50:
            status = HealthStatus.CRITICAL
        elif health_score < 75:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY
        
        result.metrics.append(HealthMetric(
            name="configuration_health_score",
            value=health_score,
            status=status,
            message=f"Configuration health score: {health_score:.1f}%",
            threshold_warning=75,
            threshold_critical=50
        ))
    
    def _check_environment_variables(self, result: HealthCheckResult) -> None:
        """Check environment variable availability and format"""
        schema_fields = self.validator.schema.get_schema_fields()
        required_fields = self.validator.schema.get_required_fields()
        
        # Check required environment variables
        missing_required = []
        for field_name in required_fields:
            if not os.getenv(field_name):
                missing_required.append(field_name)
        
        if missing_required:
            result.metrics.append(HealthMetric(
                name="missing_env_vars",
                value=missing_required,
                status=HealthStatus.CRITICAL,
                message=f"Missing required environment variables: {', '.join(missing_required)}"
            ))
        
        # Check environment variable format
        invalid_formats = []
        for field_name, field_schema in schema_fields.items():
            env_value = os.getenv(field_name)
            if env_value:
                try:
                    # Basic format validation
                    if field_schema.data_type.value == "integer":
                        int(env_value)
                    elif field_schema.data_type.value == "boolean":
                        if env_value.lower() not in ["true", "false", "1", "0", "yes", "no", "on", "off"]:
                            invalid_formats.append(field_name)
                except ValueError:
                    invalid_formats.append(field_name)
        
        if invalid_formats:
            result.metrics.append(HealthMetric(
                name="invalid_env_format",
                value=invalid_formats,
                status=HealthStatus.WARNING,
                message=f"Environment variables with invalid format: {', '.join(invalid_formats)}"
            ))
    
    def _check_performance_metrics(self, result: HealthCheckResult) -> None:
        """Check performance metrics"""
        # Check configuration validation time
        if self._performance_metrics["config_validation_time"]:
            avg_validation_time = sum(self._performance_metrics["config_validation_time"]) / len(self._performance_metrics["config_validation_time"])
            
            if avg_validation_time > 1.0:
                status = HealthStatus.CRITICAL
            elif avg_validation_time > 0.5:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            result.metrics.append(HealthMetric(
                name="config_validation_performance",
                value=avg_validation_time,
                status=status,
                message=f"Average config validation time: {avg_validation_time:.3f}s",
                threshold_warning=0.5,
                threshold_critical=1.0
            ))
        
        # Check health check time
        if self._performance_metrics["health_check_time"]:
            avg_health_check_time = sum(self._performance_metrics["health_check_time"]) / len(self._performance_metrics["health_check_time"])
            
            if avg_health_check_time > 5.0:
                status = HealthStatus.CRITICAL
            elif avg_health_check_time > 2.0:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            result.metrics.append(HealthMetric(
                name="health_check_performance",
                value=avg_health_check_time,
                status=status,
                message=f"Average health check time: {avg_health_check_time:.3f}s",
                threshold_warning=2.0,
                threshold_critical=5.0
            ))
    
    def _check_system_resources(self, result: HealthCheckResult) -> None:
        """Check system resource usage"""
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > 90:
                status = HealthStatus.CRITICAL
            elif memory_percent > 80:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            result.metrics.append(HealthMetric(
                name="memory_usage",
                value=memory_percent,
                status=status,
                message=f"Memory usage: {memory_percent:.1f}%",
                threshold_warning=80,
                threshold_critical=90
            ))
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 90:
                status = HealthStatus.CRITICAL
            elif cpu_percent > 80:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.HEALTHY
            
            result.metrics.append(HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                status=status,
                message=f"CPU usage: {cpu_percent:.1f}%",
                threshold_warning=80,
                threshold_critical=90
            ))
            
        except ImportError:
            result.metrics.append(HealthMetric(
                name="system_monitoring",
                value="unavailable",
                status=HealthStatus.WARNING,
                message="System monitoring unavailable (psutil not installed)"
            ))
    
    def _check_connectivity(self, result: HealthCheckResult) -> None:
        """Check connectivity to external services"""
        # Check Redis connectivity if configured
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
                
                result.metrics.append(HealthMetric(
                    name="redis_connectivity",
                    value="connected",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection successful"
                ))
            except Exception as e:
                result.metrics.append(HealthMetric(
                    name="redis_connectivity",
                    value="failed",
                    status=HealthStatus.CRITICAL,
                    message=f"Redis connection failed: {e}"
                ))
    
    def _generate_recommendations(self, result: HealthCheckResult) -> None:
        """Generate health improvement recommendations"""
        recommendations = []
        
        # Configuration recommendations
        if result.configuration_health:
            if result.configuration_health.errors:
                recommendations.append("Fix configuration errors to improve system stability")
            
            if result.configuration_health.warnings:
                recommendations.append("Address configuration warnings to optimize performance")
            
            if result.configuration_health.health_score < 75:
                recommendations.append("Review and update configuration to improve health score")
        
        # Performance recommendations
        for metric in result.metrics:
            if metric.name == "config_validation_performance" and metric.status != HealthStatus.HEALTHY:
                recommendations.append("Consider optimizing configuration validation performance")
            
            elif metric.name == "memory_usage" and metric.status == HealthStatus.CRITICAL:
                recommendations.append("High memory usage detected - consider scaling or optimization")
            
            elif metric.name == "cpu_usage" and metric.status == HealthStatus.CRITICAL:
                recommendations.append("High CPU usage detected - consider load balancing or optimization")
        
        # Security recommendations
        cors_origins = os.getenv("SOCKETIO_CORS_ORIGINS", "")
        if cors_origins == "*":
            recommendations.append("Replace wildcard CORS origins with specific domains for better security")
        
        if os.getenv("SOCKETIO_DEBUG", "false").lower() == "true":
            env = os.getenv("FLASK_ENV", "production")
            if env == "production":
                recommendations.append("Disable debug mode in production environment")
        
        result.recommendations = recommendations
    
    def _determine_overall_status(self, result: HealthCheckResult) -> HealthStatus:
        """Determine overall health status"""
        if any(metric.status == HealthStatus.CRITICAL for metric in result.metrics):
            return HealthStatus.CRITICAL
        elif any(metric.status == HealthStatus.WARNING for metric in result.metrics):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        if self._monitoring_active:
            self.logger.warning("Health monitoring is already active")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        self.logger.info(f"Started health monitoring with {self.check_interval}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        
        self.logger.info("Stopped health monitoring")
    
    def _monitoring_loop(self) -> None:
        """Health monitoring loop"""
        while self._monitoring_active:
            try:
                self.perform_health_check()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def add_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """Add health check callback"""
        self._health_callbacks.append(callback)
    
    def remove_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """Remove health check callback"""
        if callback in self._health_callbacks:
            self._health_callbacks.remove(callback)
    
    def get_health_history(self, limit: Optional[int] = None) -> List[HealthCheckResult]:
        """Get health check history"""
        history = list(self._health_history)
        if limit:
            history = history[-limit:]
        return history
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary statistics"""
        if not self._health_history:
            return {"status": "no_data", "message": "No health check data available"}
        
        recent_results = list(self._health_history)[-10:]  # Last 10 checks
        
        # Calculate status distribution
        status_counts = {}
        for result in recent_results:
            status = result.overall_status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate average health score
        health_scores = []
        for result in recent_results:
            if result.configuration_health:
                health_scores.append(result.configuration_health.health_score)
        
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 0
        
        # Get latest result
        latest_result = recent_results[-1]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "latest_status": latest_result.overall_status.value,
            "average_health_score": avg_health_score,
            "status_distribution": status_counts,
            "total_checks": len(self._health_history),
            "monitoring_active": self._monitoring_active,
            "last_check": self._last_check_time.isoformat() if self._last_check_time else None,
            "recommendations_count": len(latest_result.recommendations),
            "critical_issues": latest_result.has_critical_issues,
            "warnings": latest_result.has_warnings
        }