# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Secrets Integration for Vedfolnir Vault
Manages integration between HashiCorp Vault and Docker secrets
"""

import os
import sys
import json
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Add the vault client to path
sys.path.append(os.path.dirname(__file__))
try:
    from vault_client import VaultClient
except ImportError:
    # Create a mock VaultClient for testing without Vault
    class VaultClient:
        def __init__(self, *args, **kwargs):
            pass
        def get_secret(self, *args, **kwargs):
            raise Exception("Vault not available")
        def health_check(self, *args, **kwargs):
            return {'healthy': False, 'error': 'Vault not available'}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DockerSecretsManager:
    """Manages Docker secrets integration with HashiCorp Vault"""
    
    def __init__(self, vault_client: VaultClient = None, secrets_dir: str = None):
        """
        Initialize Docker secrets manager
        
        Args:
            vault_client: VaultClient instance (optional)
            secrets_dir: Directory for Docker secrets files (optional)
        """
        self.vault = vault_client or VaultClient()
        self.secrets_dir = Path(secrets_dir or '/run/secrets')
        self.vault_secrets_dir = Path('/vault/secrets')
        
        # Ensure directories exist
        self.vault_secrets_dir.mkdir(parents=True, exist_ok=True)
        
        # Secret mappings from Vault to Docker secrets
        self.secret_mappings = {
            'flask_secret_key': {
                'vault_path': 'flask',
                'vault_key': 'secret_key',
                'docker_secret': 'flask_secret_key',
                'file_path': self.vault_secrets_dir / 'flask_secret_key.txt'
            },
            'platform_encryption_key': {
                'vault_path': 'platform',
                'vault_key': 'encryption_key',
                'docker_secret': 'platform_encryption_key',
                'file_path': self.vault_secrets_dir / 'platform_encryption_key.txt'
            },
            'redis_password': {
                'vault_path': 'redis',
                'vault_key': 'password',
                'docker_secret': 'redis_password',
                'file_path': self.vault_secrets_dir / 'redis_password.txt'
            },
            'mysql_password': {
                'vault_path': 'database',
                'vault_key': 'password',
                'docker_secret': 'mysql_password',
                'file_path': self.vault_secrets_dir / 'mysql_password.txt'
            },
            'vault_token': {
                'vault_path': None,  # Special case - read from file
                'vault_key': None,
                'docker_secret': 'vault_token',
                'file_path': self.vault_secrets_dir / 'vault_token.txt'
            }
        }
    
    def sync_secret_from_vault(self, secret_name: str) -> bool:
        """
        Sync a secret from Vault to Docker secrets file
        
        Args:
            secret_name: Name of the secret to sync
            
        Returns:
            True if sync was successful
        """
        if secret_name not in self.secret_mappings:
            logger.error(f"Unknown secret: {secret_name}")
            return False
        
        mapping = self.secret_mappings[secret_name]
        
        try:
            # Special handling for vault_token
            if secret_name == 'vault_token':
                # Copy existing vault token
                vault_token_file = Path('/vault/data/vedfolnir-token.txt')
                if vault_token_file.exists():
                    secret_value = vault_token_file.read_text().strip()
                else:
                    logger.error("Vault token file not found")
                    return False
            else:
                # Get secret from Vault
                vault_secret = self.vault.get_secret(mapping['vault_path'])
                secret_value = vault_secret[mapping['vault_key']]
            
            # Write to Docker secrets file
            mapping['file_path'].write_text(secret_value)
            mapping['file_path'].chmod(0o600)  # Secure permissions
            
            logger.info(f"Synced secret: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync secret {secret_name}: {e}")
            return False
    
    def sync_all_secrets(self) -> Dict[str, bool]:
        """
        Sync all configured secrets from Vault to Docker secrets files
        
        Returns:
            Dictionary with sync results for each secret
        """
        results = {}
        
        for secret_name in self.secret_mappings.keys():
            results[secret_name] = self.sync_secret_from_vault(secret_name)
        
        return results
    
    def create_database_secret_from_dynamic_creds(self) -> bool:
        """
        Create database secret file from Vault dynamic credentials
        
        Returns:
            True if successful
        """
        try:
            # Get dynamic database credentials
            creds = self.vault.get_database_credentials()
            
            # Create database URL
            host = os.getenv('MYSQL_HOST', 'mysql')
            port = os.getenv('MYSQL_PORT', '3306')
            database = os.getenv('MYSQL_DATABASE', 'vedfolnir')
            
            db_url = f"mysql+pymysql://{creds['username']}:{creds['password']}@{host}:{port}/{database}?charset=utf8mb4"
            
            # Write database URL to secret file
            db_url_file = self.vault_secrets_dir / 'database_url.txt'
            db_url_file.write_text(db_url)
            db_url_file.chmod(0o600)
            
            # Also write individual components
            db_user_file = self.vault_secrets_dir / 'mysql_user.txt'
            db_user_file.write_text(creds['username'])
            db_user_file.chmod(0o600)
            
            db_pass_file = self.vault_secrets_dir / 'mysql_password.txt'
            db_pass_file.write_text(creds['password'])
            db_pass_file.chmod(0o600)
            
            logger.info(f"Created database secrets for user: {creds['username']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database secret: {e}")
            return False
    
    def read_docker_secret(self, secret_name: str) -> Optional[str]:
        """
        Read a Docker secret from the secrets directory
        
        Args:
            secret_name: Name of the secret to read
            
        Returns:
            Secret value or None if not found
        """
        secret_file = self.secrets_dir / secret_name
        
        if not secret_file.exists():
            # Try vault secrets directory as fallback
            secret_file = self.vault_secrets_dir / f"{secret_name}.txt"
        
        if secret_file.exists():
            try:
                return secret_file.read_text().strip()
            except Exception as e:
                logger.error(f"Failed to read secret {secret_name}: {e}")
        
        return None
    
    def validate_secrets(self) -> Dict[str, bool]:
        """
        Validate that all required secrets are available
        
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        for secret_name, mapping in self.secret_mappings.items():
            # Check if secret file exists and is readable
            secret_value = self.read_docker_secret(mapping['docker_secret'])
            results[secret_name] = secret_value is not None and len(secret_value) > 0
        
        # Check database URL
        db_url_file = self.vault_secrets_dir / 'database_url.txt'
        results['database_url'] = db_url_file.exists() and len(db_url_file.read_text().strip()) > 0
        
        return results
    
    def rotate_secret_files(self, secret_name: str) -> bool:
        """
        Rotate secret files after Vault rotation
        
        Args:
            secret_name: Name of the secret that was rotated
            
        Returns:
            True if file rotation was successful
        """
        logger.info(f"Rotating secret file for: {secret_name}")
        
        # Re-sync the secret from Vault
        success = self.sync_secret_from_vault(secret_name)
        
        if success:
            # Signal applications to reload (if needed)
            self._signal_application_reload()
        
        return success
    
    def _signal_application_reload(self):
        """
        Signal applications to reload configuration
        This could be implemented as:
        - Writing to a reload trigger file
        - Sending a signal to application containers
        - Using a message queue
        """
        try:
            # Create a reload trigger file
            reload_file = Path('/vault/signals/reload_secrets')
            reload_file.parent.mkdir(parents=True, exist_ok=True)
            reload_file.write_text(str(int(time.time())))
            
            logger.info("Created secret reload signal")
            
        except Exception as e:
            logger.error(f"Failed to signal application reload: {e}")
    
    def cleanup_old_secrets(self, max_age_hours: int = 24):
        """
        Clean up old secret files
        
        Args:
            max_age_hours: Maximum age of secret files to keep
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for secret_file in self.vault_secrets_dir.glob('*.txt.old.*'):
                file_age = current_time - secret_file.stat().st_mtime
                
                if file_age > max_age_seconds:
                    secret_file.unlink()
                    logger.info(f"Cleaned up old secret file: {secret_file}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old secrets: {e}")
    
    def backup_current_secrets(self) -> str:
        """
        Create a backup of current secret files
        
        Returns:
            Backup directory path
        """
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path(f'/vault/backups/secrets_{timestamp}')
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy all secret files
            for secret_file in self.vault_secrets_dir.glob('*.txt'):
                shutil.copy2(secret_file, backup_dir)
            
            logger.info(f"Created secrets backup: {backup_dir}")
            return str(backup_dir)
            
        except Exception as e:
            logger.error(f"Failed to backup secrets: {e}")
            raise
    
    def generate_docker_compose_secrets(self) -> Dict[str, Any]:
        """
        Generate Docker Compose secrets configuration
        
        Returns:
            Dictionary with Docker Compose secrets configuration
        """
        secrets_config = {}
        
        for secret_name, mapping in self.secret_mappings.items():
            secrets_config[mapping['docker_secret']] = {
                'file': str(mapping['file_path'])
            }
        
        # Add database URL secret
        secrets_config['database_url'] = {
            'file': str(self.vault_secrets_dir / 'database_url.txt')
        }
        
        return secrets_config
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on secrets integration
        
        Returns:
            Health check results
        """
        health = {
            'vault_connectivity': False,
            'secrets_validation': {},
            'file_permissions': {},
            'overall_status': 'unhealthy'
        }
        
        try:
            # Check Vault connectivity
            vault_health = self.vault.health_check()
            health['vault_connectivity'] = vault_health.get('sealed', True) == False
            
            # Validate secrets
            health['secrets_validation'] = self.validate_secrets()
            
            # Check file permissions
            for secret_name, mapping in self.secret_mappings.items():
                if mapping['file_path'].exists():
                    stat = mapping['file_path'].stat()
                    health['file_permissions'][secret_name] = {
                        'exists': True,
                        'mode': oct(stat.st_mode)[-3:],
                        'secure': (stat.st_mode & 0o077) == 0  # Only owner can read
                    }
                else:
                    health['file_permissions'][secret_name] = {'exists': False}
            
            # Overall status
            vault_ok = health['vault_connectivity']
            secrets_ok = all(health['secrets_validation'].values())
            permissions_ok = all(
                perm.get('secure', False) for perm in health['file_permissions'].values()
                if perm.get('exists', False)
            )
            
            if vault_ok and secrets_ok and permissions_ok:
                health['overall_status'] = 'healthy'
            elif vault_ok and secrets_ok:
                health['overall_status'] = 'degraded'
            
        except Exception as e:
            health['error'] = str(e)
        
        return health


def main():
    """Main CLI interface for Docker secrets integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Vedfolnir Docker Secrets Integration')
    parser.add_argument('--sync', action='store_true', help='Sync all secrets from Vault')
    parser.add_argument('--sync-secret', metavar='SECRET', help='Sync specific secret')
    parser.add_argument('--validate', action='store_true', help='Validate all secrets')
    parser.add_argument('--health', action='store_true', help='Perform health check')
    parser.add_argument('--generate-compose', action='store_true', help='Generate Docker Compose secrets config')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup old secret files')
    parser.add_argument('--backup', action='store_true', help='Backup current secrets')
    
    args = parser.parse_args()
    
    try:
        manager = DockerSecretsManager()
        
        if args.sync:
            results = manager.sync_all_secrets()
            print("Sync results:")
            for secret, success in results.items():
                print(f"  {secret}: {'SUCCESS' if success else 'FAILED'}")
            
            # Also create database secret
            db_success = manager.create_database_secret_from_dynamic_creds()
            print(f"  database_credentials: {'SUCCESS' if db_success else 'FAILED'}")
            
        elif args.sync_secret:
            success = manager.sync_secret_from_vault(args.sync_secret)
            print(f"Sync {args.sync_secret}: {'SUCCESS' if success else 'FAILED'}")
            
        elif args.validate:
            results = manager.validate_secrets()
            print("Validation results:")
            for secret, valid in results.items():
                print(f"  {secret}: {'VALID' if valid else 'INVALID'}")
            
        elif args.health:
            health = manager.health_check()
            print(json.dumps(health, indent=2))
            
        elif args.generate_compose:
            config = manager.generate_docker_compose_secrets()
            print("Docker Compose secrets configuration:")
            print(json.dumps({'secrets': config}, indent=2))
            
        elif args.cleanup:
            manager.cleanup_old_secrets()
            print("Cleanup completed")
            
        elif args.backup:
            backup_dir = manager.backup_current_secrets()
            print(f"Backup created: {backup_dir}")
            
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Docker secrets integration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()