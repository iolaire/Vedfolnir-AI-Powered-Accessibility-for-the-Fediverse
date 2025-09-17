# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Configuration Management

Provides configuration classes for Redis Queue integration with support for
integrated and external worker modes.
"""

import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerMode(Enum):
    """Worker deployment modes"""
    INTEGRATED = "integrated"  # Workers run as threads within Gunicorn
    EXTERNAL = "external"      # Workers run as separate processes
    HYBRID = "hybrid"          # Combination of both modes


class TaskPriority(Enum):
    """Task priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class RetryPolicy:
    """Retry policy configuration"""
    max_retries: int = 3
    backoff_strategy: str = 'exponential'  # linear, exponential, fixed
    base_delay: int = 60  # seconds
    max_delay: int = 3600  # seconds


@dataclass
class QueueConfig:
    """Configuration for individual queues"""
    name: str
    priority_level: int
    max_workers: int
    timeout: int
    retry_policy: RetryPolicy
    
    def __post_init__(self):
        if isinstance(self.retry_policy, dict):
            self.retry_policy = RetryPolicy(**self.retry_policy)


@dataclass
class WorkerConfig:
    """Configuration for RQ workers"""
    worker_id: str
    queues: List[str]  # Priority order
    worker_type: str  # integrated, external
    concurrency: int
    memory_limit: int  # MB
    timeout: int  # seconds
    health_check_interval: int  # seconds


class RQConfig:
    """Main RQ configuration class"""
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_db = self._parse_redis_db()
        self.redis_password = os.getenv('REDIS_PASSWORD')
        
        # Worker configuration
        self.worker_mode = WorkerMode(os.getenv('WORKER_MODE', 'integrated'))
        self.worker_count = int(os.getenv('RQ_WORKER_COUNT', '2'))
        self.worker_timeout = int(os.getenv('RQ_WORKER_TIMEOUT', '300'))
        self.worker_memory_limit = int(os.getenv('RQ_WORKER_MEMORY_LIMIT', '500'))
        
        # Queue configuration
        self.queue_prefix = os.getenv('RQ_QUEUE_PREFIX', 'vedfolnir:rq:')
        self.default_timeout = int(os.getenv('RQ_DEFAULT_TIMEOUT', '300'))
        self.result_ttl = int(os.getenv('RQ_RESULT_TTL', '86400'))  # 24 hours
        self.job_ttl = int(os.getenv('RQ_JOB_TTL', '7200'))  # 2 hours
        
        # Health monitoring
        self.health_check_interval = int(os.getenv('RQ_HEALTH_CHECK_INTERVAL', '30'))
        self.redis_memory_threshold = float(os.getenv('REDIS_MEMORY_THRESHOLD', '0.8'))
        self.failure_threshold = int(os.getenv('RQ_FAILURE_THRESHOLD', '3'))
        
        # Initialize queue configurations
        self.queue_configs = self._initialize_queue_configs()
        
        # Initialize worker configurations
        self.worker_configs = self._initialize_worker_configs()
    
    def _initialize_queue_configs(self) -> Dict[str, QueueConfig]:
        """Initialize queue configurations for different priorities"""
        retry_policy = RetryPolicy(
            max_retries=3,
            backoff_strategy='exponential',
            base_delay=60,
            max_delay=3600
        )
        
        return {
            TaskPriority.URGENT.value: QueueConfig(
                name=f"{self.queue_prefix}urgent",
                priority_level=1,
                max_workers=2,
                timeout=600,  # 10 minutes
                retry_policy=retry_policy
            ),
            TaskPriority.HIGH.value: QueueConfig(
                name=f"{self.queue_prefix}high",
                priority_level=2,
                max_workers=3,
                timeout=self.default_timeout,
                retry_policy=retry_policy
            ),
            TaskPriority.NORMAL.value: QueueConfig(
                name=f"{self.queue_prefix}normal",
                priority_level=3,
                max_workers=4,
                timeout=self.default_timeout,
                retry_policy=retry_policy
            ),
            TaskPriority.LOW.value: QueueConfig(
                name=f"{self.queue_prefix}low",
                priority_level=4,
                max_workers=2,
                timeout=900,  # 15 minutes
                retry_policy=retry_policy
            )
        }
    
    def _initialize_worker_configs(self) -> Dict[str, WorkerConfig]:
        """Initialize worker configurations based on mode"""
        configs = {}
        
        if self.worker_mode in [WorkerMode.INTEGRATED, WorkerMode.HYBRID]:
            # Integrated workers configuration
            configs['integrated_urgent_high'] = WorkerConfig(
                worker_id='integrated_urgent_high',
                queues=['urgent', 'high'],
                worker_type='integrated',
                concurrency=2,
                memory_limit=self.worker_memory_limit,
                timeout=self.worker_timeout,
                health_check_interval=self.health_check_interval
            )
            
            configs['integrated_normal'] = WorkerConfig(
                worker_id='integrated_normal',
                queues=['normal'],
                worker_type='integrated',
                concurrency=2,
                memory_limit=self.worker_memory_limit,
                timeout=self.worker_timeout,
                health_check_interval=self.health_check_interval
            )
        
        if self.worker_mode in [WorkerMode.EXTERNAL, WorkerMode.HYBRID]:
            # External workers configuration
            configs['external_low'] = WorkerConfig(
                worker_id='external_low',
                queues=['low'],
                worker_type='external',
                concurrency=3,
                memory_limit=self.worker_memory_limit * 2,
                timeout=self.worker_timeout * 2,
                health_check_interval=self.health_check_interval
            )
        
        return configs
    
    def get_queue_names(self) -> List[str]:
        """Get list of queue names in priority order"""
        return [
            TaskPriority.URGENT.value,
            TaskPriority.HIGH.value,
            TaskPriority.NORMAL.value,
            TaskPriority.LOW.value
        ]
    
    def get_redis_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters"""
        params = {
            'host': self._parse_redis_host(),
            'port': self._parse_redis_port(),
            'db': self.redis_db,
            'decode_responses': True,
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
        
        if self.redis_password:
            params['password'] = self.redis_password
        
        return params
    
    def _parse_redis_host(self) -> str:
        """Parse Redis host from URL"""
        if '://' in self.redis_url:
            # Parse from URL format
            url_parts = self.redis_url.split('://')[-1]
            if '@' in url_parts:
                url_parts = url_parts.split('@')[-1]
            host_port = url_parts.split('/')[0]
            return host_port.split(':')[0]
        return 'localhost'
    
    def _parse_redis_port(self) -> int:
        """Parse Redis port from URL"""
        if '://' in self.redis_url:
            url_parts = self.redis_url.split('://')[-1]
            if '@' in url_parts:
                url_parts = url_parts.split('@')[-1]
            host_port = url_parts.split('/')[0]
            if ':' in host_port:
                return int(host_port.split(':')[1])
        return 6379
    
    def _parse_redis_db(self) -> int:
        """Parse Redis database number from URL"""
        if '://' in self.redis_url and '/' in self.redis_url:
            # Extract database number from URL
            url_parts = self.redis_url.split('/')
            if len(url_parts) > 3:  # redis://host:port/db
                try:
                    return int(url_parts[-1])
                except ValueError:
                    pass
        return int(os.getenv('REDIS_DB', '0'))
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        try:
            # Validate worker mode
            if self.worker_mode not in WorkerMode:
                logger.error(f"Invalid worker mode: {self.worker_mode}")
                return False
            
            # Validate worker count
            if self.worker_count < 1:
                logger.error(f"Invalid worker count: {self.worker_count}")
                return False
            
            # Validate timeouts
            if self.worker_timeout < 60:
                logger.error(f"Worker timeout too low: {self.worker_timeout}")
                return False
            
            # Validate memory limits
            if self.worker_memory_limit < 100:
                logger.error(f"Worker memory limit too low: {self.worker_memory_limit}")
                return False
            
            logger.info("RQ configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'redis_url': self.redis_url,
            'redis_db': self.redis_db,
            'worker_mode': self.worker_mode.value,
            'worker_count': self.worker_count,
            'worker_timeout': self.worker_timeout,
            'worker_memory_limit': self.worker_memory_limit,
            'queue_prefix': self.queue_prefix,
            'default_timeout': self.default_timeout,
            'result_ttl': self.result_ttl,
            'job_ttl': self.job_ttl,
            'health_check_interval': self.health_check_interval,
            'redis_memory_threshold': self.redis_memory_threshold,
            'failure_threshold': self.failure_threshold,
            'queue_configs': {k: v.__dict__ for k, v in self.queue_configs.items()},
            'worker_configs': {k: v.__dict__ for k, v in self.worker_configs.items()}
        }


# Global configuration instance
rq_config = RQConfig()