# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Secret Rotation Script for Vedfolnir Vault Integration
Handles automated rotation of secrets without container rebuilds
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the vault client to path
sys.path.append(os.path.dirname(__file__))
try:
    from vault_client import VaultClient, VaultSecretError
except ImportError:
    # Create a mock VaultClient for testing without Vault
    class VaultClient:
        def __init__(self, *args, **kwargs):
            pass
        def _make_request(self, *args, **kwargs):
            raise Exception("Vault not available")
    
    class VaultSecretError(Exception):
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecretRotationManager:
    """Manages automated secret rotation for Vedfolnir"""
    
    def __init__(self, vault_client: VaultClient = None):
        """
        Initialize secret rotation manager
        
        Args:
            vault_client: VaultClient instance (optional)
        """
        self.vault = vault_client or VaultClient()
        self.rotation_config = self._load_rotation_config()
        
    def _load_rotation_config(self) -> Dict[str, Any]:
        """Load rotation configuration"""
        config_file = os.getenv('ROTATION_CONFIG_FILE', '/vault/config/rotation-config.json')
        
        default_config = {
            "secrets": {
                "flask": {
                    "rotation_interval_days": 90,
                    "type": "flask_secret",
                    "notify_before_days": 7
                },
                "platform": {
                    "rotation_interval_days": 90,
                    "type": "encryption_key",
                    "notify_before_days": 7
                },
                "redis": {
                    "rotation_interval_days": 30,
                    "type": "password",
                    "notify_before_days": 3
                }
            },
            "database_credentials": {
                "rotation_interval_hours": 24,
                "notify_before_hours": 2
            },
            "notification": {
                "enabled": True,
                "webhook_url": os.getenv('ROTATION_WEBHOOK_URL'),
                "email_enabled": False
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.warning(f"Failed to load rotation config: {e}. Using defaults.")
        
        return default_config
    
    def check_secret_age(self, secret_path: str) -> Dict[str, Any]:
        """
        Check the age of a secret and determine if rotation is needed
        
        Args:
            secret_path: Path to the secret
            
        Returns:
            Dictionary with age information and rotation status
        """
        try:
            # Get secret metadata
            response = self.vault._make_request('GET', f'vedfolnir/metadata/{secret_path}')
            metadata = response.json()['data']
            
            # Get the latest version info
            versions = metadata.get('versions', {})
            if not versions:
                return {'error': 'No versions found'}
            
            latest_version = max(versions.keys(), key=int)
            version_info = versions[latest_version]
            
            created_time = datetime.fromisoformat(
                version_info['created_time'].replace('Z', '+00:00')
            )
            
            age_days = (datetime.now().astimezone() - created_time).days
            
            # Get rotation config for this secret
            secret_config = self.rotation_config['secrets'].get(secret_path, {})
            rotation_interval = secret_config.get('rotation_interval_days', 90)
            notify_before = secret_config.get('notify_before_days', 7)
            
            needs_rotation = age_days >= rotation_interval
            needs_notification = age_days >= (rotation_interval - notify_before)
            
            return {
                'secret_path': secret_path,
                'age_days': age_days,
                'created_time': created_time.isoformat(),
                'rotation_interval_days': rotation_interval,
                'needs_rotation': needs_rotation,
                'needs_notification': needs_notification,
                'days_until_rotation': max(0, rotation_interval - age_days)
            }
            
        except Exception as e:
            logger.error(f"Failed to check secret age for {secret_path}: {e}")
            return {'error': str(e)}
    
    def rotate_flask_secret(self) -> str:
        """
        Rotate Flask secret key
        
        Returns:
            New secret key
        """
        import secrets
        import string
        
        # Generate new Flask secret key
        alphabet = string.ascii_letters + string.digits + string.punctuation
        new_secret = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        # Store in Vault
        self.vault.put_secret('flask', {'secret_key': new_secret})
        
        logger.info("Flask secret key rotated successfully")
        return new_secret
    
    def rotate_platform_encryption_key(self) -> str:
        """
        Rotate platform encryption key
        
        Returns:
            New encryption key
        """
        from cryptography.fernet import Fernet
        
        # Generate new Fernet key
        new_key = Fernet.generate_key().decode()
        
        # Store in Vault
        self.vault.put_secret('platform', {'encryption_key': new_key})
        
        logger.info("Platform encryption key rotated successfully")
        return new_key
    
    def rotate_redis_password(self) -> str:
        """
        Rotate Redis password
        
        Returns:
            New password
        """
        import secrets
        import string
        
        # Generate new Redis password
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        # Store in Vault
        self.vault.put_secret('redis', {'password': new_password})
        
        logger.info("Redis password rotated successfully")
        return new_password
    
    def rotate_secret(self, secret_path: str) -> bool:
        """
        Rotate a specific secret based on its type
        
        Args:
            secret_path: Path to the secret to rotate
            
        Returns:
            True if rotation was successful
        """
        try:
            secret_config = self.rotation_config['secrets'].get(secret_path, {})
            secret_type = secret_config.get('type', 'unknown')
            
            if secret_type == 'flask_secret':
                self.rotate_flask_secret()
            elif secret_type == 'encryption_key':
                self.rotate_platform_encryption_key()
            elif secret_type == 'password':
                self.rotate_redis_password()
            else:
                logger.error(f"Unknown secret type: {secret_type}")
                return False
            
            # Send notification
            self._send_notification(f"Secret rotated: {secret_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {secret_path}: {e}")
            self._send_notification(f"Secret rotation failed: {secret_path} - {e}")
            return False
    
    def check_database_credentials(self) -> Dict[str, Any]:
        """
        Check database credential lease status
        
        Returns:
            Credential lease information
        """
        try:
            # Get current credentials to check lease
            creds = self.vault.get_database_credentials()
            
            lease_duration = creds.get('lease_duration', 0)
            rotation_interval = self.rotation_config['database_credentials']['rotation_interval_hours'] * 3600
            notify_before = self.rotation_config['database_credentials']['notify_before_hours'] * 3600
            
            needs_rotation = lease_duration <= rotation_interval
            needs_notification = lease_duration <= notify_before
            
            return {
                'lease_id': creds.get('lease_id'),
                'lease_duration': lease_duration,
                'username': creds.get('username'),
                'needs_rotation': needs_rotation,
                'needs_notification': needs_notification,
                'hours_until_expiry': lease_duration / 3600
            }
            
        except Exception as e:
            logger.error(f"Failed to check database credentials: {e}")
            return {'error': str(e)}
    
    def rotate_database_credentials(self) -> bool:
        """
        Rotate database credentials by getting new ones
        
        Returns:
            True if rotation was successful
        """
        try:
            # Get new credentials (this automatically rotates them)
            new_creds = self.vault.get_database_credentials()
            
            logger.info(f"Database credentials rotated. New username: {new_creds['username']}")
            self._send_notification(f"Database credentials rotated: {new_creds['username']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate database credentials: {e}")
            self._send_notification(f"Database credential rotation failed: {e}")
            return False
    
    def check_all_secrets(self) -> Dict[str, Any]:
        """
        Check all configured secrets for rotation needs
        
        Returns:
            Dictionary with status of all secrets
        """
        results = {
            'secrets': {},
            'database_credentials': {},
            'summary': {
                'needs_rotation': [],
                'needs_notification': [],
                'errors': []
            }
        }
        
        # Check application secrets
        for secret_path in self.rotation_config['secrets'].keys():
            secret_status = self.check_secret_age(secret_path)
            results['secrets'][secret_path] = secret_status
            
            if secret_status.get('error'):
                results['summary']['errors'].append(f"{secret_path}: {secret_status['error']}")
            elif secret_status.get('needs_rotation'):
                results['summary']['needs_rotation'].append(secret_path)
            elif secret_status.get('needs_notification'):
                results['summary']['needs_notification'].append(secret_path)
        
        # Check database credentials
        db_status = self.check_database_credentials()
        results['database_credentials'] = db_status
        
        if db_status.get('error'):
            results['summary']['errors'].append(f"database: {db_status['error']}")
        elif db_status.get('needs_rotation'):
            results['summary']['needs_rotation'].append('database_credentials')
        elif db_status.get('needs_notification'):
            results['summary']['needs_notification'].append('database_credentials')
        
        return results
    
    def rotate_all_needed(self) -> Dict[str, bool]:
        """
        Rotate all secrets that need rotation
        
        Returns:
            Dictionary with rotation results
        """
        status = self.check_all_secrets()
        results = {}
        
        # Rotate application secrets
        for secret_path in status['summary']['needs_rotation']:
            if secret_path == 'database_credentials':
                results[secret_path] = self.rotate_database_credentials()
            else:
                results[secret_path] = self.rotate_secret(secret_path)
        
        return results
    
    def _send_notification(self, message: str):
        """
        Send notification about secret rotation
        
        Args:
            message: Notification message
        """
        if not self.rotation_config['notification']['enabled']:
            return
        
        webhook_url = self.rotation_config['notification'].get('webhook_url')
        if webhook_url:
            try:
                import requests
                payload = {
                    'text': f"Vedfolnir Secret Rotation: {message}",
                    'timestamp': datetime.now().isoformat()
                }
                requests.post(webhook_url, json=payload, timeout=10)
                logger.info(f"Notification sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    def generate_rotation_report(self) -> str:
        """
        Generate a detailed rotation status report
        
        Returns:
            Formatted report string
        """
        status = self.check_all_secrets()
        
        report = []
        report.append("=== Vedfolnir Secret Rotation Report ===")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        report.append("SUMMARY:")
        report.append(f"  Secrets needing rotation: {len(status['summary']['needs_rotation'])}")
        report.append(f"  Secrets needing notification: {len(status['summary']['needs_notification'])}")
        report.append(f"  Errors: {len(status['summary']['errors'])}")
        report.append("")
        
        # Application secrets
        report.append("APPLICATION SECRETS:")
        for secret_path, secret_info in status['secrets'].items():
            if secret_info.get('error'):
                report.append(f"  {secret_path}: ERROR - {secret_info['error']}")
            else:
                age = secret_info['age_days']
                interval = secret_info['rotation_interval_days']
                status_text = "NEEDS ROTATION" if secret_info['needs_rotation'] else "OK"
                report.append(f"  {secret_path}: {status_text} (age: {age}d, interval: {interval}d)")
        
        report.append("")
        
        # Database credentials
        report.append("DATABASE CREDENTIALS:")
        db_info = status['database_credentials']
        if db_info.get('error'):
            report.append(f"  ERROR - {db_info['error']}")
        else:
            hours = db_info.get('hours_until_expiry', 0)
            status_text = "NEEDS ROTATION" if db_info['needs_rotation'] else "OK"
            report.append(f"  {status_text} (expires in: {hours:.1f}h)")
        
        if status['summary']['errors']:
            report.append("")
            report.append("ERRORS:")
            for error in status['summary']['errors']:
                report.append(f"  - {error}")
        
        return "\n".join(report)


def main():
    """Main CLI interface for secret rotation"""
    parser = argparse.ArgumentParser(description='Vedfolnir Secret Rotation Manager')
    parser.add_argument('--check', action='store_true', help='Check all secrets status')
    parser.add_argument('--rotate', metavar='SECRET', help='Rotate specific secret')
    parser.add_argument('--rotate-all', action='store_true', help='Rotate all secrets that need it')
    parser.add_argument('--report', action='store_true', help='Generate rotation report')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (check every hour)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        manager = SecretRotationManager()
        
        if args.check:
            status = manager.check_all_secrets()
            print(json.dumps(status, indent=2, default=str))
            
        elif args.rotate:
            success = manager.rotate_secret(args.rotate)
            print(f"Rotation {'successful' if success else 'failed'}")
            sys.exit(0 if success else 1)
            
        elif args.rotate_all:
            results = manager.rotate_all_needed()
            print("Rotation results:")
            for secret, success in results.items():
                print(f"  {secret}: {'SUCCESS' if success else 'FAILED'}")
            
            all_success = all(results.values())
            sys.exit(0 if all_success else 1)
            
        elif args.report:
            report = manager.generate_rotation_report()
            print(report)
            
        elif args.daemon:
            logger.info("Starting secret rotation daemon...")
            while True:
                try:
                    status = manager.check_all_secrets()
                    
                    # Send notifications for secrets needing attention
                    for secret in status['summary']['needs_notification']:
                        manager._send_notification(f"Secret {secret} needs rotation soon")
                    
                    # Auto-rotate if configured
                    if status['summary']['needs_rotation']:
                        logger.info(f"Auto-rotating secrets: {status['summary']['needs_rotation']}")
                        manager.rotate_all_needed()
                    
                except Exception as e:
                    logger.error(f"Daemon error: {e}")
                
                # Sleep for 1 hour
                time.sleep(3600)
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Secret rotation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()