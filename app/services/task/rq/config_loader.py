# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Configuration Loader

Loads environment-specific RQ configuration from files and environment variables.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .production_config import ProductionRQConfig, DeploymentEnvironment, create_production_config

logger = logging.getLogger(__name__)


class RQConfigLoader:
    """Loads RQ configuration from environment-specific files and variables"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            config_dir: Directory containing configuration files (defaults to config/rq)
        """
        self.config_dir = Path(config_dir or 'config/rq')
        self.loaded_config: Optional[ProductionRQConfig] = None
    
    def load_config(self, environment: Optional[str] = None) -> ProductionRQConfig:
        """
        Load configuration for specified environment
        
        Args:
            environment: Environment name (development, staging, production)
            
        Returns:
            ProductionRQConfig instance
        """
        # Determine environment
        env_name = environment or self._detect_environment()
        
        logger.info(f"Loading RQ configuration for {env_name} environment")
        
        # Load environment file if it exists
        self._load_environment_file(env_name)
        
        # Create production configuration
        config = create_production_config(env_name)
        
        # Validate configuration
        if not config.validate_production_config():
            raise ValueError(f"Invalid configuration for {env_name} environment")
        
        # Setup logging
        config.setup_production_logging()
        
        self.loaded_config = config
        logger.info(f"RQ configuration loaded successfully for {env_name} environment")
        
        return config
    
    def _detect_environment(self) -> str:
        """Detect current environment"""
        # Check various environment variables
        env_vars = [
            'DEPLOYMENT_ENV',
            'FLASK_ENV',
            'ENVIRONMENT',
            'ENV'
        ]
        
        for var in env_vars:
            env_value = os.getenv(var)
            if env_value:
                env_name = env_value.lower()
                if env_name in ['prod', 'production']:
                    return 'production'
                elif env_name in ['stage', 'staging']:
                    return 'staging'
                elif env_name in ['dev', 'development']:
                    return 'development'
        
        # Default to development
        return 'development'
    
    def _load_environment_file(self, environment: str) -> None:
        """Load environment-specific configuration file"""
        env_file = self.config_dir / f"{environment}.env"
        
        if not env_file.exists():
            logger.warning(f"Environment file not found: {env_file}")
            return
        
        try:
            logger.info(f"Loading environment file: {env_file}")
            
            with open(env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Set environment variable if not already set
                        if key not in os.environ:
                            os.environ[key] = value
                            logger.debug(f"Set {key}={value}")
                        else:
                            logger.debug(f"Environment variable {key} already set, skipping")
                    else:
                        logger.warning(f"Invalid line in {env_file}:{line_num}: {line}")
            
            logger.info(f"Environment file loaded successfully: {env_file}")
            
        except Exception as e:
            logger.error(f"Failed to load environment file {env_file}: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of loaded configuration"""
        if not self.loaded_config:
            return {'error': 'No configuration loaded'}
        
        return {
            'environment': self.loaded_config.environment.value,
            'worker_mode': self.loaded_config.worker_mode.value,
            'worker_count': self.loaded_config.worker_count,
            'worker_timeout': self.loaded_config.worker_timeout,
            'memory_limit': self.loaded_config.worker_memory_limit,
            'redis_url': self.loaded_config.redis_url,
            'logging_level': self.loaded_config.logging_config.level.value,
            'monitoring_enabled': self.loaded_config.monitoring_config.enable_metrics,
            'auto_scaling_enabled': self.loaded_config.scaling_config.enable_auto_scaling,
            'worker_configs': len(self.loaded_config.worker_configs),
            'queue_configs': len(self.loaded_config.queue_configs)
        }
    
    def export_environment_variables(self, output_file: Optional[str] = None) -> Dict[str, str]:
        """
        Export configuration as environment variables
        
        Args:
            output_file: Optional file to write environment variables to
            
        Returns:
            Dictionary of environment variables
        """
        if not self.loaded_config:
            raise ValueError("No configuration loaded")
        
        env_vars = self.loaded_config.get_environment_variables()
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write("# RQ Configuration Environment Variables\n")
                    f.write(f"# Generated for {self.loaded_config.environment.value} environment\n\n")
                    
                    for key, value in sorted(env_vars.items()):
                        f.write(f"export {key}={value}\n")
                
                logger.info(f"Environment variables exported to {output_file}")
                
            except Exception as e:
                logger.error(f"Failed to export environment variables to {output_file}: {e}")
                raise
        
        return env_vars
    
    def validate_current_environment(self) -> bool:
        """Validate current environment configuration"""
        try:
            # Try to load configuration for current environment
            config = self.load_config()
            
            # Perform additional validation checks
            validation_results = []
            
            # Check Redis connectivity
            try:
                import redis
                redis_conn = redis.from_url(config.redis_url)
                redis_conn.ping()
                validation_results.append(("Redis connectivity", True, "OK"))
            except Exception as e:
                validation_results.append(("Redis connectivity", False, str(e)))
            
            # Check log directory
            if config.logging_config.file_path:
                log_dir = os.path.dirname(config.logging_config.file_path)
                if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
                    validation_results.append(("Log directory", True, f"Writable: {log_dir}"))
                else:
                    validation_results.append(("Log directory", False, f"Not writable: {log_dir}"))
            
            # Check worker configuration
            if len(config.worker_configs) > 0:
                validation_results.append(("Worker configuration", True, f"{len(config.worker_configs)} workers configured"))
            else:
                validation_results.append(("Worker configuration", False, "No workers configured"))
            
            # Report validation results
            all_passed = True
            for check_name, passed, message in validation_results:
                if passed:
                    logger.info(f"✅ {check_name}: {message}")
                else:
                    logger.error(f"❌ {check_name}: {message}")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            return False


# Global configuration loader instance
_config_loader: Optional[RQConfigLoader] = None


def get_config_loader(config_dir: Optional[str] = None) -> RQConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    
    if _config_loader is None:
        _config_loader = RQConfigLoader(config_dir)
    
    return _config_loader


def load_rq_config(environment: Optional[str] = None, config_dir: Optional[str] = None) -> ProductionRQConfig:
    """
    Load RQ configuration for specified environment
    
    Args:
        environment: Environment name (development, staging, production)
        config_dir: Directory containing configuration files
        
    Returns:
        ProductionRQConfig instance
    """
    loader = get_config_loader(config_dir)
    return loader.load_config(environment)