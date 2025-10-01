# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Vault Client for Vedfolnir
Provides secure access to HashiCorp Vault for secrets management
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VaultClient:
    """HashiCorp Vault client for Vedfolnir secrets management"""
    
    def __init__(self, vault_addr: str = None, token: str = None):
        """
        Initialize Vault client
        
        Args:
            vault_addr: Vault server address (defaults to VAULT_ADDR env var)
            token: Vault token (defaults to VAULT_TOKEN env var or token file)
        """
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.token = token or self._get_token()
        self.session = requests.Session()
        self.session.headers.update({'X-Vault-Token': self.token})
        
        # Token renewal tracking
        self._token_info = None
        self._last_token_check = None
        
    def _get_token(self) -> str:
        """Get Vault token from environment or file"""
        # Try environment variable first
        token = os.getenv('VAULT_TOKEN')
        if token:
            return token
            
        # Try token file
        token_file = os.getenv('VAULT_TOKEN_FILE', '/vault/data/vedfolnir-token.txt')
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                return f.read().strip()
                
        raise ValueError("No Vault token found. Set VAULT_TOKEN or VAULT_TOKEN_FILE")
    
    def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request to Vault"""
        url = f"{self.vault_addr}/v1/{path}"
        
        # Check and renew token if needed
        self._check_token_renewal()
        
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code == 403:
            logger.error("Vault access denied. Token may be expired or invalid.")
            raise VaultAuthError("Access denied to Vault")
        elif response.status_code >= 400:
            logger.error(f"Vault request failed: {response.status_code} - {response.text}")
            response.raise_for_status()
            
        return response
    
    def _check_token_renewal(self):
        """Check if token needs renewal and renew if necessary"""
        now = datetime.now()
        
        # Check token info every 5 minutes
        if (self._last_token_check is None or 
            now - self._last_token_check > timedelta(minutes=5)):
            
            try:
                response = self._make_request('GET', 'auth/token/lookup-self')
                self._token_info = response.json()['data']
                self._last_token_check = now
                
                # Check if token expires soon (within 1 hour)
                ttl = self._token_info.get('ttl', 0)
                if ttl > 0 and ttl < 3600:  # Less than 1 hour
                    self._renew_token()
                    
            except Exception as e:
                logger.warning(f"Failed to check token status: {e}")
    
    def _renew_token(self):
        """Renew the current token"""
        try:
            response = self._make_request('POST', 'auth/token/renew-self')
            logger.info("Vault token renewed successfully")
        except Exception as e:
            logger.error(f"Failed to renew Vault token: {e}")
            raise VaultAuthError("Token renewal failed")
    
    def get_secret(self, path: str, version: int = None) -> Dict[str, Any]:
        """
        Get secret from KV v2 secrets engine
        
        Args:
            path: Secret path (without vedfolnir/ prefix)
            version: Specific version to retrieve (optional)
            
        Returns:
            Dictionary containing secret data
        """
        vault_path = f"vedfolnir/data/{path}"
        params = {}
        if version:
            params['version'] = version
            
        response = self._make_request('GET', vault_path, params=params)
        data = response.json()
        
        if 'data' not in data or 'data' not in data['data']:
            raise VaultSecretError(f"Secret not found: {path}")
            
        return data['data']['data']
    
    def put_secret(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store secret in KV v2 secrets engine
        
        Args:
            path: Secret path (without vedfolnir/ prefix)
            data: Secret data to store
            
        Returns:
            Response metadata
        """
        vault_path = f"vedfolnir/data/{path}"
        payload = {'data': data}
        
        response = self._make_request('POST', vault_path, json=payload)
        return response.json()
    
    def delete_secret(self, path: str, versions: list = None):
        """
        Delete secret versions
        
        Args:
            path: Secret path (without vedfolnir/ prefix)
            versions: List of versions to delete (optional, deletes latest if not specified)
        """
        if versions:
            vault_path = f"vedfolnir/delete/{path}"
            payload = {'versions': versions}
            self._make_request('POST', vault_path, json=payload)
        else:
            vault_path = f"vedfolnir/metadata/{path}"
            self._make_request('DELETE', vault_path)
    
    def get_database_credentials(self, role: str = 'vedfolnir-role') -> Dict[str, str]:
        """
        Get dynamic database credentials
        
        Args:
            role: Database role name
            
        Returns:
            Dictionary with username and password
        """
        response = self._make_request('GET', f'database/creds/{role}')
        data = response.json()
        
        if 'data' not in data:
            raise VaultSecretError(f"Failed to get database credentials for role: {role}")
            
        return {
            'username': data['data']['username'],
            'password': data['data']['password'],
            'lease_id': data['lease_id'],
            'lease_duration': data['lease_duration']
        }
    
    def encrypt_data(self, plaintext: str, key_name: str = 'vedfolnir-encryption') -> str:
        """
        Encrypt data using Transit secrets engine
        
        Args:
            plaintext: Data to encrypt
            key_name: Encryption key name
            
        Returns:
            Encrypted ciphertext
        """
        import base64
        
        # Encode plaintext to base64
        encoded_plaintext = base64.b64encode(plaintext.encode()).decode()
        
        payload = {'plaintext': encoded_plaintext}
        response = self._make_request('POST', f'transit/encrypt/{key_name}', json=payload)
        
        data = response.json()
        if 'data' not in data or 'ciphertext' not in data['data']:
            raise VaultEncryptionError("Encryption failed")
            
        return data['data']['ciphertext']
    
    def decrypt_data(self, ciphertext: str, key_name: str = 'vedfolnir-encryption') -> str:
        """
        Decrypt data using Transit secrets engine
        
        Args:
            ciphertext: Encrypted data
            key_name: Encryption key name
            
        Returns:
            Decrypted plaintext
        """
        import base64
        
        payload = {'ciphertext': ciphertext}
        response = self._make_request('POST', f'transit/decrypt/{key_name}', json=payload)
        
        data = response.json()
        if 'data' not in data or 'plaintext' not in data['data']:
            raise VaultEncryptionError("Decryption failed")
            
        # Decode from base64
        encoded_plaintext = data['data']['plaintext']
        return base64.b64decode(encoded_plaintext).decode()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Vault health status
        
        Returns:
            Health status information
        """
        try:
            response = requests.get(f"{self.vault_addr}/v1/sys/health", timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return {'healthy': False, 'error': str(e)}
    
    def list_secrets(self, path: str = '') -> list:
        """
        List secrets at given path
        
        Args:
            path: Path to list (optional)
            
        Returns:
            List of secret names
        """
        vault_path = f"vedfolnir/metadata/{path}" if path else "vedfolnir/metadata"
        params = {'list': 'true'}
        
        try:
            response = self._make_request('GET', vault_path, params=params)
            data = response.json()
            return data.get('data', {}).get('keys', [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise


class VaultAuthError(Exception):
    """Vault authentication error"""
    pass


class VaultSecretError(Exception):
    """Vault secret operation error"""
    pass


class VaultEncryptionError(Exception):
    """Vault encryption/decryption error"""
    pass


# Convenience functions for common operations
def get_flask_secret() -> str:
    """Get Flask secret key from Vault"""
    client = VaultClient()
    secret = client.get_secret('flask')
    return secret['secret_key']


def get_platform_encryption_key() -> str:
    """Get platform encryption key from Vault"""
    client = VaultClient()
    secret = client.get_secret('platform')
    return secret['encryption_key']


def get_database_url() -> str:
    """Get database URL with dynamic credentials"""
    client = VaultClient()
    creds = client.get_database_credentials()
    
    # Build database URL
    host = os.getenv('MYSQL_HOST', 'mysql')
    port = os.getenv('MYSQL_PORT', '3306')
    database = os.getenv('MYSQL_DATABASE', 'vedfolnir')
    
    return f"mysql+pymysql://{creds['username']}:{creds['password']}@{host}:{port}/{database}?charset=utf8mb4"


def get_redis_url() -> str:
    """Get Redis URL with password from Vault"""
    client = VaultClient()
    secret = client.get_secret('redis')
    
    host = os.getenv('REDIS_HOST', 'redis')
    port = os.getenv('REDIS_PORT', '6379')
    db = os.getenv('REDIS_DB', '0')
    
    return f"redis://:{secret['password']}@{host}:{port}/{db}"


if __name__ == '__main__':
    # Test Vault connectivity
    try:
        client = VaultClient()
        health = client.health_check()
        print(f"Vault health: {health}")
        
        # Test secret retrieval
        secrets = client.list_secrets()
        print(f"Available secrets: {secrets}")
        
    except Exception as e:
        print(f"Vault test failed: {e}")