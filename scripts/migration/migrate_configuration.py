# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Migration Script for macOS to Docker Migration
Migrates environment configuration from macOS .env to Docker container .env
"""

import os
import sys
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
import argparse
import re

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class ConfigurationMigrator:
    def __init__(self, source_env=None, target_env=None):
        """Initialize configuration migrator"""
        self.source_env = Path(source_env) if source_env else Path('.env')
        self.target_env = Path(target_env) if target_env else Path('.env.docker')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'config_migration_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Configuration mappings for Docker environment
        self.docker_mappings = {
            # Database connections - use container networking
            'DATABASE_URL': self._convert_database_url,
            'REDIS_URL': self._convert_redis_url,
            
            # Ollama API - use host.docker.internal for external service
            'OLLAMA_URL': self._convert_ollama_url,
            'OLLAMA_BASE_URL': self._convert_ollama_url,
            
            # File paths - use container paths
            'STORAGE_PATH': self._convert_storage_path,
            'LOG_PATH': self._convert_log_path,
            'BACKUP_PATH': self._convert_backup_path,
            
            # Security - use Docker secrets
            'FLASK_SECRET_KEY': self._convert_to_secret_file,
            'PLATFORM_ENCRYPTION_KEY': self._convert_to_secret_file,
            'MYSQL_PASSWORD': self._convert_to_secret_file,
            'REDIS_PASSWORD': self._convert_to_secret_file,
        }
        
        # Docker-specific additions
        self.docker_additions = {
            'DOCKER_DEPLOYMENT': 'true',
            'CONTAINER_NAME': 'vedfolnir',
            'NETWORK_NAME': 'vedfolnir_internal',
            'VOLUME_PREFIX': './data',
            'CONFIG_MOUNT': './config:/app/config',
            'STORAGE_MOUNT': './storage:/app/storage',
            'LOGS_MOUNT': './logs:/app/logs',
        }
        
    def _convert_database_url(self, value):
        """Convert database URL to use container networking"""
        if not value:
            return value
            
        # Replace localhost with mysql container name
        converted = value.replace('localhost', 'mysql')
        converted = converted.replace('127.0.0.1', 'mysql')
        
        # Ensure charset is set for container
        if 'charset=' not in converted:
            if '?' in converted:
                converted += '&charset=utf8mb4'
            else:
                converted += '?charset=utf8mb4'
        
        self.logger.info(f"Database URL converted for container networking")
        return converted
    
    def _convert_redis_url(self, value):
        """Convert Redis URL to use container networking"""
        if not value:
            return value
            
        # Replace localhost with redis container name
        converted = value.replace('localhost', 'redis')
        converted = converted.replace('127.0.0.1', 'redis')
        
        self.logger.info(f"Redis URL converted for container networking")
        return converted
    
    def _convert_ollama_url(self, value):
        """Convert Ollama URL to use host.docker.internal"""
        if not value:
            return 'http://host.docker.internal:11434'
            
        # Replace localhost with host.docker.internal for external service
        converted = value.replace('localhost', 'host.docker.internal')
        converted = converted.replace('127.0.0.1', 'host.docker.internal')
        
        self.logger.info(f"Ollama URL converted for external host access")
        return converted
    
    def _convert_storage_path(self, value):
        """Convert storage path to container mount point"""
        return '/app/storage'
    
    def _convert_log_path(self, value):
        """Convert log path to container mount point"""
        return '/app/logs'
    
    def _convert_backup_path(self, value):
        """Convert backup path to container mount point"""
        return '/app/storage/backups'
    
    def _convert_to_secret_file(self, value):
        """Convert sensitive values to Docker secret file references"""
        if not value:
            return value
            
        # Map to Docker secret file path
        secret_mappings = {
            'FLASK_SECRET_KEY': '/run/secrets/flask_secret_key',
            'PLATFORM_ENCRYPTION_KEY': '/run/secrets/platform_encryption_key',
            'MYSQL_PASSWORD': '/run/secrets/mysql_password',
            'REDIS_PASSWORD': '/run/secrets/redis_password',
        }
        
        # Return the file path, actual secret will be managed by Docker
        return secret_mappings.get(value, value)
    
    def load_source_config(self):
        """Load source environment configuration"""
        try:
            if not self.source_env.exists():
                self.logger.error(f"Source environment file not found: {self.source_env}")
                return None
            
            config = {}
            with open(self.source_env, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        config[key] = value
                    else:
                        self.logger.warning(f"Invalid line format at line {line_num}: {line}")
            
            self.logger.info(f"Loaded {len(config)} configuration items from {self.source_env}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load source configuration: {e}")
            return None
    
    def convert_config_for_docker(self, source_config):
        """Convert configuration for Docker environment"""
        try:
            docker_config = {}
            conversion_log = []
            
            # Process existing configuration
            for key, value in source_config.items():
                if key in self.docker_mappings:
                    # Apply specific conversion
                    converter = self.docker_mappings[key]
                    if callable(converter):
                        new_value = converter(value)
                    else:
                        new_value = converter
                    
                    docker_config[key] = new_value
                    conversion_log.append({
                        'key': key,
                        'original': value,
                        'converted': new_value,
                        'action': 'converted'
                    })
                else:
                    # Keep as-is for most values
                    docker_config[key] = value
                    conversion_log.append({
                        'key': key,
                        'original': value,
                        'converted': value,
                        'action': 'preserved'
                    })
            
            # Add Docker-specific configuration
            for key, value in self.docker_additions.items():
                docker_config[key] = value
                conversion_log.append({
                    'key': key,
                    'original': None,
                    'converted': value,
                    'action': 'added'
                })
            
            # Save conversion log
            log_file = Path(f"config_conversion_log_{self.timestamp}.json")
            with open(log_file, 'w') as f:
                json.dump(conversion_log, f, indent=2)
            
            self.logger.info(f"Configuration converted for Docker: {len(docker_config)} items")
            self.logger.info(f"Conversion log saved: {log_file}")
            
            return docker_config
            
        except Exception as e:
            self.logger.error(f"Failed to convert configuration: {e}")
            return None
    
    def create_docker_secrets(self, source_config):
        """Create Docker secret files from sensitive configuration"""
        try:
            secrets_dir = Path('./secrets')
            secrets_dir.mkdir(exist_ok=True)
            
            secret_mappings = {
                'FLASK_SECRET_KEY': 'flask_secret_key.txt',
                'PLATFORM_ENCRYPTION_KEY': 'platform_encryption_key.txt',
                'MYSQL_PASSWORD': 'mysql_password.txt',
                'REDIS_PASSWORD': 'redis_password.txt'
            }
            
            created_secrets = []
            
            for env_key, secret_file in secret_mappings.items():
                if env_key in source_config:
                    secret_path = secrets_dir / secret_file
                    
                    # Only create if doesn't exist
                    if not secret_path.exists():
                        with open(secret_path, 'w') as f:
                            f.write(source_config[env_key])
                        
                        # Set restrictive permissions
                        secret_path.chmod(0o600)
                        
                        created_secrets.append(str(secret_path))
                        self.logger.info(f"Created secret file: {secret_path}")
                    else:
                        self.logger.info(f"Secret file already exists: {secret_path}")
            
            return created_secrets
            
        except Exception as e:
            self.logger.error(f"Failed to create Docker secrets: {e}")
            return []
    
    def write_docker_config(self, docker_config):
        """Write Docker environment configuration"""
        try:
            # Backup existing target file if it exists
            if self.target_env.exists():
                backup_path = Path(f"{self.target_env}.backup_{self.timestamp}")
                shutil.copy2(self.target_env, backup_path)
                self.logger.info(f"Backed up existing config: {backup_path}")
            
            # Write new configuration
            with open(self.target_env, 'w') as f:
                f.write(f"# Docker Environment Configuration\n")
                f.write(f"# Generated on {datetime.now().isoformat()}\n")
                f.write(f"# Migrated from {self.source_env}\n\n")
                
                # Group related configurations
                groups = {
                    'Docker Configuration': ['DOCKER_DEPLOYMENT', 'CONTAINER_NAME', 'NETWORK_NAME'],
                    'Database Configuration': ['DATABASE_URL', 'DB_POOL_SIZE', 'DB_MAX_OVERFLOW'],
                    'Redis Configuration': ['REDIS_URL', 'REDIS_SESSION_PREFIX', 'REDIS_SESSION_TIMEOUT'],
                    'AI/ML Configuration': ['OLLAMA_URL', 'OLLAMA_MODEL', 'CAPTION_MAX_LENGTH'],
                    'Security Configuration': ['FLASK_SECRET_KEY', 'PLATFORM_ENCRYPTION_KEY', 'SECURITY_CSRF_ENABLED'],
                    'Volume Mounts': ['VOLUME_PREFIX', 'CONFIG_MOUNT', 'STORAGE_MOUNT', 'LOGS_MOUNT'],
                    'Application Configuration': []  # Catch-all for remaining items
                }
                
                written_keys = set()
                
                for group_name, group_keys in groups.items():
                    if group_keys:
                        # Write specific group keys
                        group_items = [(k, v) for k, v in docker_config.items() if k in group_keys]
                    else:
                        # Write remaining keys
                        group_items = [(k, v) for k, v in docker_config.items() if k not in written_keys]
                    
                    if group_items:
                        f.write(f"# {group_name}\n")
                        for key, value in sorted(group_items):
                            f.write(f"{key}={value}\n")
                            written_keys.add(key)
                        f.write("\n")
            
            self.logger.info(f"Docker configuration written: {self.target_env}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Docker configuration: {e}")
            return False
    
    def create_docker_compose_env_template(self, docker_config):
        """Create docker-compose environment template"""
        try:
            template_path = Path('.env.docker-compose')
            
            with open(template_path, 'w') as f:
                f.write("# Docker Compose Environment Variables\n")
                f.write("# This file contains variables used by docker-compose.yml\n\n")
                
                # Extract Docker Compose specific variables
                compose_vars = {
                    'MYSQL_ROOT_PASSWORD': docker_config.get('MYSQL_ROOT_PASSWORD', 'secure_root_password'),
                    'MYSQL_DATABASE': 'vedfolnir',
                    'MYSQL_USER': 'vedfolnir',
                    'MYSQL_PASSWORD': docker_config.get('MYSQL_PASSWORD', 'secure_password'),
                    'REDIS_PASSWORD': docker_config.get('REDIS_PASSWORD', ''),
                    'COMPOSE_PROJECT_NAME': 'vedfolnir',
                    'NETWORK_NAME': 'vedfolnir_internal',
                    'VOLUME_PREFIX': './data'
                }
                
                for key, value in compose_vars.items():
                    f.write(f"{key}={value}\n")
            
            self.logger.info(f"Docker Compose template created: {template_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Docker Compose template: {e}")
            return False
    
    def validate_migration(self, source_config, docker_config):
        """Validate configuration migration"""
        try:
            validation_results = {
                'source_keys': len(source_config),
                'docker_keys': len(docker_config),
                'missing_keys': [],
                'converted_keys': [],
                'added_keys': [],
                'validation_passed': True
            }
            
            # Check for missing critical keys
            critical_keys = [
                'DATABASE_URL', 'REDIS_URL', 'FLASK_SECRET_KEY',
                'PLATFORM_ENCRYPTION_KEY', 'OLLAMA_URL'
            ]
            
            for key in critical_keys:
                if key not in docker_config:
                    validation_results['missing_keys'].append(key)
                    validation_results['validation_passed'] = False
            
            # Identify converted keys
            for key in source_config:
                if key in docker_config and docker_config[key] != source_config[key]:
                    validation_results['converted_keys'].append(key)
            
            # Identify added keys
            for key in docker_config:
                if key not in source_config:
                    validation_results['added_keys'].append(key)
            
            # Save validation results
            validation_file = Path(f"config_validation_{self.timestamp}.json")
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            if validation_results['validation_passed']:
                self.logger.info("Configuration migration validation passed")
            else:
                self.logger.warning("Configuration migration validation found issues")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return None
    
    def run_migration(self):
        """Run complete configuration migration"""
        self.logger.info("Starting configuration migration for Docker deployment")
        
        # Load source configuration
        source_config = self.load_source_config()
        if not source_config:
            return False
        
        # Convert configuration for Docker
        docker_config = self.convert_config_for_docker(source_config)
        if not docker_config:
            return False
        
        # Create Docker secrets
        created_secrets = self.create_docker_secrets(source_config)
        
        # Write Docker configuration
        if not self.write_docker_config(docker_config):
            return False
        
        # Create Docker Compose template
        if not self.create_docker_compose_env_template(docker_config):
            return False
        
        # Validate migration
        validation_results = self.validate_migration(source_config, docker_config)
        if not validation_results:
            return False
        
        self.logger.info("Configuration migration completed successfully")
        self.logger.info(f"Source config: {self.source_env}")
        self.logger.info(f"Docker config: {self.target_env}")
        self.logger.info(f"Created secrets: {len(created_secrets)}")
        
        if not validation_results['validation_passed']:
            self.logger.warning("Migration completed with validation warnings")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Migrate configuration from macOS to Docker')
    parser.add_argument('--source', help='Source .env file path', default='.env')
    parser.add_argument('--target', help='Target .env file path', default='.env.docker')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    migrator = ConfigurationMigrator(args.source, args.target)
    success = migrator.run_migration()
    
    if success:
        print(f"\n✅ Configuration migration completed successfully")
        print(f"📁 Source: {migrator.source_env}")
        print(f"📁 Target: {migrator.target_env}")
        print(f"📋 Check log file: config_migration_{migrator.timestamp}.log")
    else:
        print(f"\n❌ Configuration migration failed")
        print(f"📋 Check log file: config_migration_{migrator.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()