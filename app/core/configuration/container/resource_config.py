# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Container Resource Configuration
Manages resource limits and scaling for containerized deployment
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResourceTier(Enum):
    """Resource tier definitions for different container sizes"""
    MICRO = "micro"      # < 1GB RAM, 1 CPU
    SMALL = "small"      # 1-2GB RAM, 1-2 CPU
    MEDIUM = "medium"    # 2-4GB RAM, 2-4 CPU
    LARGE = "large"      # 4-8GB RAM, 4-8 CPU
    XLARGE = "xlarge"    # > 8GB RAM, > 8 CPU


@dataclass
class ResourceLimits:
    """Resource limits configuration"""
    memory_mb: int
    cpu_cores: float
    disk_gb: int
    max_connections: int
    max_workers: int
    max_rq_workers: int


@dataclass
class ScalingConfig:
    """Auto-scaling configuration"""
    enabled: bool
    min_workers: int
    max_workers: int
    cpu_threshold: float
    memory_threshold: float
    scale_up_cooldown: int
    scale_down_cooldown: int


class ContainerResourceConfig:
    """Container resource configuration manager"""
    
    # Resource tier definitions
    RESOURCE_TIERS = {
        ResourceTier.MICRO: ResourceLimits(
            memory_mb=512,
            cpu_cores=0.5,
            disk_gb=10,
            max_connections=10,
            max_workers=1,
            max_rq_workers=1
        ),
        ResourceTier.SMALL: ResourceLimits(
            memory_mb=1024,
            cpu_cores=1.0,
            disk_gb=20,
            max_connections=20,
            max_workers=2,
            max_rq_workers=2
        ),
        ResourceTier.MEDIUM: ResourceLimits(
            memory_mb=2048,
            cpu_cores=2.0,
            disk_gb=40,
            max_connections=50,
            max_workers=4,
            max_rq_workers=3
        ),
        ResourceTier.LARGE: ResourceLimits(
            memory_mb=4096,
            cpu_cores=4.0,
            disk_gb=80,
            max_connections=100,
            max_workers=8,
            max_rq_workers=4
        ),
        ResourceTier.XLARGE: ResourceLimits(
            memory_mb=8192,
            cpu_cores=8.0,
            disk_gb=160,
            max_connections=200,
            max_workers=16,
            max_rq_workers=6
        )
    }
    
    def __init__(self):
        self.is_container = self._detect_container_environment()
        self.resource_tier = self._determine_resource_tier()
        self.limits = self._get_resource_limits()
        self.scaling_config = self._get_scaling_config()
        
        logger.info(f"Container resource config initialized - Tier: {self.resource_tier.value}")
    
    def _detect_container_environment(self) -> bool:
        """Detect if running in a container"""
        return (
            os.path.exists('/.dockerenv') or
            os.getenv('CONTAINER_ENV') == 'true' or
            os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup').read()
        )
    
    def _determine_resource_tier(self) -> ResourceTier:
        """Determine resource tier based on environment variables or auto-detection"""
        # Check explicit tier setting
        tier_env = os.getenv('RESOURCE_TIER', '').lower()
        if tier_env:
            try:
                return ResourceTier(tier_env)
            except ValueError:
                logger.warning(f"Invalid RESOURCE_TIER value: {tier_env}")
        
        # Auto-detect based on memory limit
        memory_limit = os.getenv('MEMORY_LIMIT', '2g')
        memory_mb = self._parse_memory_limit(memory_limit)
        
        if memory_mb < 1024:
            return ResourceTier.MICRO
        elif memory_mb < 2048:
            return ResourceTier.SMALL
        elif memory_mb < 4096:
            return ResourceTier.MEDIUM
        elif memory_mb < 8192:
            return ResourceTier.LARGE
        else:
            return ResourceTier.XLARGE
    
    def _parse_memory_limit(self, memory_limit: str) -> int:
        """Parse memory limit string to MB"""
        try:
            if memory_limit.endswith('g'):
                return int(memory_limit[:-1]) * 1024
            elif memory_limit.endswith('m'):
                return int(memory_limit[:-1])
            elif memory_limit.endswith('k'):
                return int(memory_limit[:-1]) // 1024
            else:
                # Assume MB if no unit
                return int(memory_limit)
        except (ValueError, IndexError):
            logger.warning(f"Could not parse memory limit: {memory_limit}, using default 2048MB")
            return 2048
    
    def _get_resource_limits(self) -> ResourceLimits:
        """Get resource limits for current tier"""
        base_limits = self.RESOURCE_TIERS[self.resource_tier]
        
        # Allow environment variable overrides
        return ResourceLimits(
            memory_mb=int(os.getenv('MAX_MEMORY_MB', base_limits.memory_mb)),
            cpu_cores=float(os.getenv('MAX_CPU_CORES', base_limits.cpu_cores)),
            disk_gb=int(os.getenv('MAX_DISK_GB', base_limits.disk_gb)),
            max_connections=int(os.getenv('MAX_DB_CONNECTIONS', base_limits.max_connections)),
            max_workers=int(os.getenv('MAX_GUNICORN_WORKERS', base_limits.max_workers)),
            max_rq_workers=int(os.getenv('MAX_RQ_WORKERS', base_limits.max_rq_workers))
        )
    
    def _get_scaling_config(self) -> ScalingConfig:
        """Get auto-scaling configuration"""
        return ScalingConfig(
            enabled=os.getenv('AUTO_SCALING_ENABLED', 'false').lower() == 'true',
            min_workers=int(os.getenv('MIN_WORKERS', '1')),
            max_workers=self.limits.max_workers,
            cpu_threshold=float(os.getenv('CPU_SCALE_THRESHOLD', '80.0')),
            memory_threshold=float(os.getenv('MEMORY_SCALE_THRESHOLD', '80.0')),
            scale_up_cooldown=int(os.getenv('SCALE_UP_COOLDOWN', '300')),    # 5 minutes
            scale_down_cooldown=int(os.getenv('SCALE_DOWN_COOLDOWN', '600'))  # 10 minutes
        )
    
    def get_gunicorn_config(self) -> Dict[str, Any]:
        """Get Gunicorn configuration based on resource limits"""
        return {
            'workers': self.limits.max_workers,
            'worker_connections': min(1000, self.limits.max_connections * 10),
            'max_requests': 1000 if self.limits.memory_mb >= 2048 else 500,
            'max_requests_jitter': 100 if self.limits.memory_mb >= 2048 else 50,
            'timeout': 60 if self.limits.memory_mb >= 2048 else 30,
            'keepalive': 2,
            'preload_app': True,
            'worker_tmp_dir': '/dev/shm' if self.is_container else None
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration based on resource limits"""
        return {
            'pool_size': min(20, self.limits.max_connections),
            'max_overflow': min(30, self.limits.max_connections // 2),
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        }
    
    def get_rq_config(self) -> Dict[str, Any]:
        """Get RQ worker configuration based on resource limits"""
        return {
            'max_workers': self.limits.max_rq_workers,
            'job_timeout': 300 if self.limits.memory_mb >= 2048 else 180,
            'result_ttl': 3600 if self.limits.memory_mb >= 2048 else 1800,
            'worker_ttl': 420,
            'maintenance_interval': 600
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration based on resource limits"""
        return {
            'max_connections': min(50, self.limits.max_connections),
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
    
    def should_enable_feature(self, feature: str) -> bool:
        """Determine if a feature should be enabled based on resource tier"""
        feature_requirements = {
            'performance_monitoring': ResourceTier.SMALL,
            'metrics_collection': ResourceTier.SMALL,
            'detailed_logging': ResourceTier.MEDIUM,
            'background_cleanup': ResourceTier.MEDIUM,
            'auto_scaling': ResourceTier.LARGE,
            'advanced_caching': ResourceTier.LARGE
        }
        
        required_tier = feature_requirements.get(feature)
        if not required_tier:
            return True  # Unknown features are enabled by default
        
        # Compare tier levels
        tier_order = [ResourceTier.MICRO, ResourceTier.SMALL, ResourceTier.MEDIUM, 
                     ResourceTier.LARGE, ResourceTier.XLARGE]
        
        current_index = tier_order.index(self.resource_tier)
        required_index = tier_order.index(required_tier)
        
        return current_index >= required_index
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration based on resource tier"""
        return {
            'metrics_enabled': self.should_enable_feature('metrics_collection'),
            'detailed_logging': self.should_enable_feature('detailed_logging'),
            'performance_monitoring': self.should_enable_feature('performance_monitoring'),
            'health_check_interval': 30 if self.resource_tier != ResourceTier.MICRO else 60,
            'log_retention_days': 7 if self.resource_tier in [ResourceTier.MICRO, ResourceTier.SMALL] else 30
        }
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of current resource configuration"""
        return {
            'is_container': self.is_container,
            'resource_tier': self.resource_tier.value,
            'limits': {
                'memory_mb': self.limits.memory_mb,
                'cpu_cores': self.limits.cpu_cores,
                'disk_gb': self.limits.disk_gb,
                'max_connections': self.limits.max_connections,
                'max_workers': self.limits.max_workers,
                'max_rq_workers': self.limits.max_rq_workers
            },
            'scaling': {
                'enabled': self.scaling_config.enabled,
                'min_workers': self.scaling_config.min_workers,
                'max_workers': self.scaling_config.max_workers
            },
            'features': {
                'performance_monitoring': self.should_enable_feature('performance_monitoring'),
                'metrics_collection': self.should_enable_feature('metrics_collection'),
                'auto_scaling': self.should_enable_feature('auto_scaling')
            }
        }


# Global resource config instance
_resource_config: Optional[ContainerResourceConfig] = None


def get_resource_config() -> ContainerResourceConfig:
    """Get or create the global resource configuration"""
    global _resource_config
    if _resource_config is None:
        _resource_config = ContainerResourceConfig()
    return _resource_config