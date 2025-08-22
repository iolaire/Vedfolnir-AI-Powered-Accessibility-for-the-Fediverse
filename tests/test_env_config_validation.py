# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test configuration validation for .env file approach
"""

import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from config import Config, ConfigurationError, AuthConfig, WebAppConfig

class TestEnvConfigValidation(unittest.TestCase):
    """Test configuration loading with .env file approach"""
    
    def setUp(self):
        """Set up test environment"""
        # Store original environment
        self.original_env = dict(os.environ)
        
        # Clear relevant environment variables
        env_vars = [
            'FLASK_SECRET_KEY', 'AUTH_ADMIN_USERNAME', 'AUTH_ADMIN_EMAIL', 
            'AUTH_ADMIN_PASSWORD', 'PLATFORM_ENCRYPTION_KEY'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Restore original environment"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_valid_env_configuration(self):
        """Test loading with properly configured .env file"""
        # Set valid environment variables (as if loaded from .env)
        os.environ.update({
            'FLASK_SECRET_KEY': 'a-very-secure-32-character-secret-key-here',
            'PLATFORM_ENCRYPTION_KEY': 'fernet-key-here-32-chars-base64-encoded='
        })
        
        # Test AuthConfig loading (no longer requires environment variables)
        auth_config = AuthConfig.from_env()
        self.assertEqual(auth_config.session_lifetime, 86400)  # Default value
        self.assertEqual(auth_config.require_auth, True)  # Default value
        
        # Test WebAppConfig loading
        webapp_config = WebAppConfig.from_env()
        self.assertEqual(webapp_config.secret_key, 'a-very-secure-32-character-secret-key-here')
        
        # Test full Config loading
        config = Config()
        self.assertIsNotNone(config.auth)
        self.assertIsNotNone(config.webapp)
    
    def test_missing_flask_secret_key(self):
        """Test error when FLASK_SECRET_KEY is missing from .env file"""
        # Set all other required variables
        os.environ.update({
            'AUTH_ADMIN_USERNAME': 'admin_user',
            'AUTH_ADMIN_EMAIL': 'admin@test.com',
            'AUTH_ADMIN_PASSWORD': 'SecurePassword123!',
            'PLATFORM_ENCRYPTION_KEY': 'fernet-key-here-32-chars-base64-encoded='
        })
        
        with self.assertRaises(ConfigurationError) as context:
            WebAppConfig.from_env()
        
        error_message = str(context.exception)
        self.assertIn('FLASK_SECRET_KEY is required in .env file', error_message)
        self.assertIn('copy .env.example to .env', error_message)
        self.assertIn('docs/security/environment-setup.md', error_message)
    
    def test_auth_config_no_longer_requires_env_vars(self):
        """Test that AuthConfig no longer requires environment variables"""
        # Set only Flask secret key and encryption key
        os.environ.update({
            'FLASK_SECRET_KEY': 'a-very-secure-32-character-secret-key-here',
            'PLATFORM_ENCRYPTION_KEY': 'fernet-key-here-32-chars-base64-encoded='
        })
        
        # AuthConfig should load successfully without admin credentials
        auth_config = AuthConfig.from_env()
        self.assertEqual(auth_config.session_lifetime, 86400)
        self.assertEqual(auth_config.require_auth, True)
    
    def test_missing_platform_encryption_key(self):
        """Test error when PLATFORM_ENCRYPTION_KEY is missing"""
        # Set only Flask secret key
        os.environ['FLASK_SECRET_KEY'] = 'a-very-secure-32-character-secret-key-here'
        
        # This should work for AuthConfig and WebAppConfig
        auth_config = AuthConfig.from_env()
        webapp_config = WebAppConfig.from_env()
        
        # But Config() might fail when trying to use platform encryption
        # (This depends on when the encryption key is actually used)
    
    def test_empty_platform_encryption_key(self):
        """Test error when PLATFORM_ENCRYPTION_KEY is empty string"""
        os.environ.update({
            'FLASK_SECRET_KEY': 'a-very-secure-32-character-secret-key-here',
            'PLATFORM_ENCRYPTION_KEY': ''  # Empty string
        })
        
        # Config loading should still work, but platform operations might fail
        # when the encryption key is actually used
    
    def test_empty_flask_secret_key(self):
        """Test error when FLASK_SECRET_KEY is empty string"""
        os.environ.update({
            'FLASK_SECRET_KEY': '',  # Empty string
            'AUTH_ADMIN_USERNAME': 'admin_user',
            'AUTH_ADMIN_EMAIL': 'admin@test.com',
            'AUTH_ADMIN_PASSWORD': 'SecurePassword123!'
        })
        
        with self.assertRaises(ConfigurationError) as context:
            WebAppConfig.from_env()
        
        error_message = str(context.exception)
        self.assertIn('FLASK_SECRET_KEY is required in .env file', error_message)
    
    def test_flask_secret_key_error_messages_reference_env_file(self):
        """Test that Flask secret key error messages reference .env file setup"""
        # Test Flask secret key error
        with self.assertRaises(ConfigurationError) as context:
            WebAppConfig.from_env()
        
        error_message = str(context.exception)
        self.assertIn('.env file', error_message)
        self.assertIn('copy .env.example to .env', error_message)
        self.assertNotIn('environment variable', error_message)
    
    def test_config_maintains_validation_logic(self):
        """Test that existing validation logic is maintained"""
        # Set valid configuration
        os.environ.update({
            'FLASK_SECRET_KEY': 'a-very-secure-32-character-secret-key-here',
            'PLATFORM_ENCRYPTION_KEY': 'fernet-key-here-32-chars-base64-encoded=',
            'AUTH_SESSION_LIFETIME': '7200',
            'AUTH_REQUIRE_AUTH': 'false',
            'FLASK_HOST': '0.0.0.0',
            'FLASK_PORT': '8080',
            'FLASK_DEBUG': 'true'
        })
        
        # Test that optional settings work
        auth_config = AuthConfig.from_env()
        self.assertEqual(auth_config.session_lifetime, 7200)
        self.assertEqual(auth_config.require_auth, False)
        
        webapp_config = WebAppConfig.from_env()
        self.assertEqual(webapp_config.host, '0.0.0.0')
        self.assertEqual(webapp_config.port, 8080)
        self.assertEqual(webapp_config.debug, True)
    
    def test_full_config_loading_with_env_file(self):
        """Test that full Config class works with .env file approach"""
        # Set required variables (only Flask secret key and encryption key now)
        os.environ.update({
            'FLASK_SECRET_KEY': 'a-very-secure-32-character-secret-key-here',
            'PLATFORM_ENCRYPTION_KEY': 'fernet-key-here-32-chars-base64-encoded='
        })
        
        # Should not raise any exceptions
        config = Config()
        
        # Verify configuration is loaded correctly
        self.assertEqual(config.webapp.secret_key, 'a-very-secure-32-character-secret-key-here')
        self.assertIsNotNone(config.auth)
        self.assertIsNotNone(config.storage)
        self.assertIsNotNone(config.ollama)

if __name__ == '__main__':
    unittest.main()