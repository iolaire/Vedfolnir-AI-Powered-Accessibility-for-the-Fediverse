# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Production Configuration for RQ Workers

Provides production-specific configuration settings, environment-based worker scaling,
and logging integration for production deployment.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .rq_config import RQConfig, WorkerConfig, QueueConfig, TaskPriority

logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Logging levels for production"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ProductionLoggingConfig:
    """Production logging configuration"""
    level: LogLevel = LogLevel.INFO
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_syslog: bool = False
    syslog_address: str = '/dev/log'
    enable_json_logging: bool = False
    
    def __post_init__(self):
        # Set default log file path if not specified
        if self.file_path is None:
            log_dir = os.getenv('LOG_DIR', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            self.file_path = os.path.join(log_dir, 'rq_workers.log')


@dataclass
class ProductionMonitoringConfig:
    """Production monitoring configuration"""
    enable_metrics: bool = True
    metrics_port: int = 9090
    metrics_path: str = '/metrics'
    enable_health_checks: bool = True
    health_check_port: int = 8080
    health_check_path: str = '/health'
    enable_alerting: bool = False
    alert_webhook_url: Optional[str] = None
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'memory_usage_percent': 85.0,
        'cpu_usage_percent': 80.0,
        'queue_backlog_size': 1000,
        'worker_failure_rate': 0.1
    })


@dataclass
class ProductionScalingConfig:
    """Production scaling configuration"""
    enable_auto_scaling: bool = False
    min_workers_per_queue: Dict[str, int] = field(default_factory=lambda: {
        'urgent': 1,
        'high': 2,
        'normal': 2,
        'low': 1
    })
    max_workers_per_queue: Dict[str, int] = field(default_factory=lambda: {
        'urgent': 4,
        'high': 6,
        'normal': 8,
        'low': 4
    })
    scaling_threshold_up: float = 0.8  # Scale up when queue utilization > 80%
    scaling_threshold_down: float = 0.3  # Scale down when queue utilization < 30%
    scaling_cooldown_seconds: int = 300  # 5 minutes between scaling operations
    
    def __post_init__(self):
        # Validate scaling configuration
        for queue in self.min_workers_per_queue:
            if queue in self.max_workers_per_queue:
                if self.min_workers_per_queue[queue] > self.max_workers_per_queue[queue]:
                    raise ValueError(f"Min workers ({self.min_workers_per_queue[queue]}) > max workers ({self.max_workers_per_queue[queue]}) for queue {queue}")


class ProductionRQConfig(RQConfig):
    """Production-specific RQ configuration"""
    
    def __init__(self, environment: Optional[DeploymentEnvironment] = None):
        """
        Initialize production RQ configuration
        
        Args:
            environment: Deployment environment (auto-detected if not provided)
        """
        super().__init__()
        
        # Determine environment
        self.environment = environment or self._detect_environment()
        
        # Initialize production-specific configurations
        self.logging_config = self._initialize_logging_config()
        self.monitoring_config = self._initialize_monitoring_config()
        self.scaling_config = self._initialize_scaling_config()
        
        # Override base configuration with production settings
        self._apply_production_overrides()
        
        # Initialize environment-specific worker configurations
        self.worker_configs = self._initialize_production_worker_configs()
        
        logger.info(f"Production RQ configuration initialized for {self.environment.value} environment")
    
    def _detect_environment(self) -> DeploymentEnvironment:
        """Auto-detect deployment environment"""
        env_name = os.getenv('DEPLOYMENT_ENV', os.getenv('FLASK_ENV', 'development')).lower()
        
        if env_name in ['prod', 'production']:
            return DeploymentEnvironment.PRODUCTION
        elif env_name in ['stage', 'staging']:
            return DeploymentEnvironment.STAGING
        else:
            return DeploymentEnvironment.DEVELOPMENT
    
    def _initialize_logging_config(self) -> ProductionLoggingConfig:
        """Initialize production logging configuration"""
        # Environment-specific log levels
        log_level_map = {
            DeploymentEnvironment.DEVELOPMENT: LogLevel.DEBUG,
            DeploymentEnvironment.STAGING: LogLevel.INFO,
            DeploymentEnvironment.PRODUCTION: LogLevel.WARNING
        }
        
        return ProductionLoggingConfig(
            level=LogLevel(os.getenv('RQ_LOG_LEVEL', log_level_map[self.environment].value)),
            file_path=os.getenv('RQ_LOG_FILE'),
            max_file_size=int(os.getenv('RQ_LOG_MAX_SIZE', '10485760')),  # 10MB
            backup_count=int(os.getenv('RQ_LOG_BACKUP_COUNT', '5')),
            enable_syslog=os.getenv('RQ_ENABLE_SYSLOG', 'false').lower() == 'true',
            syslog_address=os.getenv('RQ_SYSLOG_ADDRESS', '/dev/log'),
            enable_json_logging=os.getenv('RQ_ENABLE_JSON_LOGGING', 'false').lower() == 'true'
        )
    
    def _initialize_monitoring_config(self) -> ProductionMonitoringConfig:
        """Initialize production monitoring configuration"""
        return ProductionMonitoringConfig(
            enable_metrics=os.getenv('RQ_ENABLE_METRICS', 'true').lower() == 'true',
            metrics_port=int(os.getenv('RQ_METRICS_PORT', '9090')),
            metrics_path=os.getenv('RQ_METRICS_PATH', '/metrics'),
            enable_health_checks=os.getenv('RQ_ENABLE_HEALTH_CHECKS', 'true').lower() == 'true',
            health_check_port=int(os.getenv('RQ_HEALTH_CHECK_PORT', '8080')),
            health_check_path=os.getenv('RQ_HEALTH_CHECK_PATH', '/health'),
            enable_alerting=os.getenv('RQ_ENABLE_ALERTING', 'false').lower() == 'true',
            alert_webhook_url=os.getenv('RQ_ALERT_WEBHOOK_URL'),
            alert_thresholds={
                'memory_usage_percent': float(os.getenv('RQ_ALERT_MEMORY_THRESHOLD', '85.0')),
                'cpu_usage_percent': float(os.getenv('RQ_ALERT_CPU_THRESHOLD', '80.0')),
                'queue_backlog_size': float(os.getenv('RQ_ALERT_QUEUE_THRESHOLD', '1000')),
                'worker_failure_rate': float(os.getenv('RQ_ALERT_FAILURE_RATE_THRESHOLD', '0.1'))
            }
        )
    
    def _initialize_scaling_config(self) -> ProductionScalingConfig:
        """Initialize production scaling configuration"""
        return ProductionScalingConfig(
            enable_auto_scaling=os.getenv('RQ_ENABLE_AUTO_SCALING', 'false').lower() == 'true',
            min_workers_per_queue={
                'urgent': int(os.getenv('RQ_MIN_URGENT_WORKERS', '1')),
                'high': int(os.getenv('RQ_MIN_HIGH_WORKERS', '2')),
                'normal': int(os.getenv('RQ_MIN_NORMAL_WORKERS', '2')),
                'low': int(os.getenv('RQ_MIN_LOW_WORKERS', '1'))
            },
            max_workers_per_queue={
                'urgent': int(os.getenv('RQ_MAX_URGENT_WORKERS', '4')),
                'high': int(os.getenv('RQ_MAX_HIGH_WORKERS', '6')),
                'normal': int(os.getenv('RQ_MAX_NORMAL_WORKERS', '8')),
                'low': int(os.getenv('RQ_MAX_LOW_WORKERS', '4'))
            },
            scaling_threshold_up=float(os.getenv('RQ_SCALING_THRESHOLD_UP', '0.8')),
            scaling_threshold_down=float(os.getenv('RQ_SCALING_THRESHOLD_DOWN', '0.3')),
            scaling_cooldown_seconds=int(os.getenv('RQ_SCALING_COOLDOWN', '300'))
        )
    
    def _apply_production_overrides(self) -> None:
        """Apply production-specific overrides to base configuration"""
        # Environment-specific timeouts
        timeout_multipliers = {
            DeploymentEnvironment.DEVELOPMENT: 1.0,
            DeploymentEnvironment.STAGING: 1.5,
            DeploymentEnvironment.PRODUCTION: 2.0
        }
        
        multiplier = timeout_multipliers[self.environment]
        self.worker_timeout = int(self.worker_timeout * multiplier)
        self.default_timeout = int(self.default_timeout * multiplier)
        
        # Environment-specific memory limits
        memory_multipliers = {
            DeploymentEnvironment.DEVELOPMENT: 1.0,
            DeploymentEnvironment.STAGING: 1.5,
            DeploymentEnvironment.PRODUCTION: 2.0
        }
        
        memory_multiplier = memory_multipliers[self.environment]
        self.worker_memory_limit = int(self.worker_memory_limit * memory_multiplier)
        
        # Production-specific Redis settings
        if self.environment == DeploymentEnvironment.PRODUCTION:
            # Longer TTLs for production
            self.result_ttl = int(os.getenv('RQ_PROD_RESULT_TTL', str(self.result_ttl * 2)))
            self.job_ttl = int(os.getenv('RQ_PROD_JOB_TTL', str(self.job_ttl * 2)))
            
            # More conservative health check intervals
            self.health_check_interval = int(os.getenv('RQ_PROD_HEALTH_CHECK_INTERVAL', '60'))
    
    def _initialize_production_worker_configs(self) -> Dict[str, WorkerConfig]:
        """Initialize production worker configurations based on environment"""
        configs = {}
        
        # Environment-specific worker counts
        worker_counts = {
            DeploymentEnvironment.DEVELOPMENT: {
                'integrated_urgent_high': 1,
                'integrated_normal': 1,
                'external_low': 1
            },
            DeploymentEnvironment.STAGING: {
                'integrated_urgent_high': 2,
                'integrated_normal': 2,
                'external_low': 2
            },
            DeploymentEnvironment.PRODUCTION: {
                'integrated_urgent_high': 3,
                'integrated_normal': 4,
                'external_low': 3
            }
        }
        
        counts = worker_counts[self.environment]
        
        # Integrated workers for urgent/high priority
        for i in range(counts['integrated_urgent_high']):
            worker_id = f'integrated_urgent_high_{i}'
            configs[worker_id] = WorkerConfig(
                worker_id=worker_id,
                queues=['urgent', 'high'],
                worker_type='integrated',
                concurrency=1,
                memory_limit=self.worker_memory_limit,
                timeout=self.worker_timeout,
                health_check_interval=self.health_check_interval
            )
        
        # Integrated workers for normal priority
        for i in range(counts['integrated_normal']):
            worker_id = f'integrated_normal_{i}'
            configs[worker_id] = WorkerConfig(
                worker_id=worker_id,
                queues=['normal'],
                worker_type='integrated',
                concurrency=1,
                memory_limit=self.worker_memory_limit,
                timeout=self.worker_timeout,
                health_check_interval=self.health_check_interval
            )
        
        # External workers for low priority (if enabled)
        if self.worker_mode.value in ['external', 'hybrid']:
            for i in range(counts['external_low']):
                worker_id = f'external_low_{i}'
                configs[worker_id] = WorkerConfig(
                    worker_id=worker_id,
                    queues=['low'],
                    worker_type='external',
                    concurrency=1,
                    memory_limit=self.worker_memory_limit * 2,  # External workers get more memory
                    timeout=self.worker_timeout * 2,  # External workers get more time
                    health_check_interval=self.health_check_interval
                )
        
        return configs
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for production deployment"""
        env_vars = {
            'DEPLOYMENT_ENV': self.environment.value,
            'WORKER_MODE': self.worker_mode.value,
            'RQ_WORKER_COUNT': str(self.worker_count),
            'RQ_WORKER_TIMEOUT': str(self.worker_timeout),
            'RQ_WORKER_MEMORY_LIMIT': str(self.worker_memory_limit),
            'RQ_DEFAULT_TIMEOUT': str(self.default_timeout),
            'RQ_RESULT_TTL': str(self.result_ttl),
            'RQ_JOB_TTL': str(self.job_ttl),
            'RQ_HEALTH_CHECK_INTERVAL': str(self.health_check_interval),
            'REDIS_MEMORY_THRESHOLD': str(self.redis_memory_threshold),
            'RQ_FAILURE_THRESHOLD': str(self.failure_threshold),
            
            # Logging configuration
            'RQ_LOG_LEVEL': self.logging_config.level.value,
            'RQ_LOG_FILE': self.logging_config.file_path or '',
            'RQ_LOG_MAX_SIZE': str(self.logging_config.max_file_size),
            'RQ_LOG_BACKUP_COUNT': str(self.logging_config.backup_count),
            'RQ_ENABLE_SYSLOG': str(self.logging_config.enable_syslog).lower(),
            'RQ_ENABLE_JSON_LOGGING': str(self.logging_config.enable_json_logging).lower(),
            
            # Monitoring configuration
            'RQ_ENABLE_METRICS': str(self.monitoring_config.enable_metrics).lower(),
            'RQ_METRICS_PORT': str(self.monitoring_config.metrics_port),
            'RQ_ENABLE_HEALTH_CHECKS': str(self.monitoring_config.enable_health_checks).lower(),
            'RQ_HEALTH_CHECK_PORT': str(self.monitoring_config.health_check_port),
            'RQ_ENABLE_ALERTING': str(self.monitoring_config.enable_alerting).lower(),
            
            # Scaling configuration
            'RQ_ENABLE_AUTO_SCALING': str(self.scaling_config.enable_auto_scaling).lower(),
            'RQ_SCALING_THRESHOLD_UP': str(self.scaling_config.scaling_threshold_up),
            'RQ_SCALING_THRESHOLD_DOWN': str(self.scaling_config.scaling_threshold_down),
            'RQ_SCALING_COOLDOWN': str(self.scaling_config.scaling_cooldown_seconds)
        }
        
        # Add worker count environment variables
        for queue, min_count in self.scaling_config.min_workers_per_queue.items():
            env_vars[f'RQ_MIN_{queue.upper()}_WORKERS'] = str(min_count)
        
        for queue, max_count in self.scaling_config.max_workers_per_queue.items():
            env_vars[f'RQ_MAX_{queue.upper()}_WORKERS'] = str(max_count)
        
        # Add alert thresholds
        for metric, threshold in self.monitoring_config.alert_thresholds.items():
            env_var_name = f'RQ_ALERT_{metric.upper()}_THRESHOLD'
            env_vars[env_var_name] = str(threshold)
        
        return env_vars
    
    def setup_production_logging(self) -> None:
        """Setup production logging configuration"""
        try:
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, self.logging_config.level.value))
            
            # Clear existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Create formatter
            if self.logging_config.enable_json_logging:
                # JSON formatter for structured logging
                import json
                from datetime import datetime
                
                class JSONFormatter(logging.Formatter):
                    def format(self, record):
                        log_entry = {
                            'timestamp': datetime.utcnow().isoformat(),
                            'level': record.levelname,
                            'logger': record.name,
                            'message': record.getMessage(),
                            'module': record.module,
                            'function': record.funcName,
                            'line': record.lineno
                        }
                        
                        if record.exc_info:
                            log_entry['exception'] = self.formatException(record.exc_info)
                        
                        return json.dumps(log_entry)
                
                formatter = JSONFormatter()
            else:
                formatter = logging.Formatter(self.logging_config.format)
            
            # File handler
            if self.logging_config.file_path:
                from logging.handlers import RotatingFileHandler
                
                file_handler = RotatingFileHandler(
                    self.logging_config.file_path,
                    maxBytes=self.logging_config.max_file_size,
                    backupCount=self.logging_config.backup_count
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            
            # Console handler for development
            if self.environment == DeploymentEnvironment.DEVELOPMENT:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            # Syslog handler for production
            if self.logging_config.enable_syslog:
                from logging.handlers import SysLogHandler
                
                syslog_handler = SysLogHandler(address=self.logging_config.syslog_address)
                syslog_handler.setFormatter(formatter)
                root_logger.addHandler(syslog_handler)
            
            logger.info(f"Production logging configured for {self.environment.value} environment")
            
        except Exception as e:
            logger.error(f"Failed to setup production logging: {e}")
            raise
    
    def validate_production_config(self) -> bool:
        """Validate production configuration"""
        try:
            # Validate base configuration
            if not super().validate_config():
                return False
            
            # Validate scaling configuration
            if self.scaling_config.enable_auto_scaling:
                if self.scaling_config.scaling_threshold_up <= self.scaling_config.scaling_threshold_down:
                    logger.error("Scaling threshold up must be greater than scaling threshold down")
                    return False
                
                if self.scaling_config.scaling_cooldown_seconds < 60:
                    logger.error("Scaling cooldown must be at least 60 seconds")
                    return False
            
            # Validate monitoring configuration
            if self.monitoring_config.enable_alerting and not self.monitoring_config.alert_webhook_url:
                logger.error("Alert webhook URL required when alerting is enabled")
                return False
            
            # Validate logging configuration
            if self.logging_config.file_path:
                log_dir = os.path.dirname(self.logging_config.file_path)
                if not os.path.exists(log_dir):
                    try:
                        os.makedirs(log_dir, exist_ok=True)
                    except Exception as e:
                        logger.error(f"Cannot create log directory {log_dir}: {e}")
                        return False
            
            logger.info("Production configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Production configuration validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert production configuration to dictionary"""
        config_dict = super().to_dict()
        
        config_dict.update({
            'environment': self.environment.value,
            'logging_config': {
                'level': self.logging_config.level.value,
                'file_path': self.logging_config.file_path,
                'max_file_size': self.logging_config.max_file_size,
                'backup_count': self.logging_config.backup_count,
                'enable_syslog': self.logging_config.enable_syslog,
                'enable_json_logging': self.logging_config.enable_json_logging
            },
            'monitoring_config': {
                'enable_metrics': self.monitoring_config.enable_metrics,
                'metrics_port': self.monitoring_config.metrics_port,
                'enable_health_checks': self.monitoring_config.enable_health_checks,
                'health_check_port': self.monitoring_config.health_check_port,
                'enable_alerting': self.monitoring_config.enable_alerting,
                'alert_thresholds': self.monitoring_config.alert_thresholds
            },
            'scaling_config': {
                'enable_auto_scaling': self.scaling_config.enable_auto_scaling,
                'min_workers_per_queue': self.scaling_config.min_workers_per_queue,
                'max_workers_per_queue': self.scaling_config.max_workers_per_queue,
                'scaling_threshold_up': self.scaling_config.scaling_threshold_up,
                'scaling_threshold_down': self.scaling_config.scaling_threshold_down,
                'scaling_cooldown_seconds': self.scaling_config.scaling_cooldown_seconds
            }
        })
        
        return config_dict


# Factory function for creating production configuration
def create_production_config(environment: Optional[str] = None) -> ProductionRQConfig:
    """
    Create production RQ configuration
    
    Args:
        environment: Environment name (development, staging, production)
        
    Returns:
        ProductionRQConfig instance
    """
    env = None
    if environment:
        try:
            env = DeploymentEnvironment(environment.lower())
        except ValueError:
            logger.warning(f"Unknown environment '{environment}', using auto-detection")
    
    return ProductionRQConfig(environment=env)