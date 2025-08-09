# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for multi-platform configuration support.

Tests configuration parsing, validation, and backward compatibility
for both Pixelfed and Mastodon platforms.
"""

import os
import unittest
from unittest.mock import patch
from config import ActivityPubConfig, Config, ConfigurationError


class TestActivityPubConfigMultiPlatform(unittest.TestCase):
    """Test ActivityPub configuration for multi-platform support"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear environment variables before each test
        env_vars_to_clear = [
            'ACTIVITYPUB_API_TYPE',
            'ACTIVITYPUB_INSTANCE_URL',
            'ACTIVITYPUB_ACCESS_TOKEN',
            'ACTIVITYPUB_USERNAME',
            'MASTODON_CLIENT_KEY',
            'MASTODON_CLIENT_SECRET',
            'PRIVATE_KEY_PATH',
            'PUBLIC_KEY_PATH',
            'ACTIVITYPUB_PLATFORM_TYPE',
            'PIXELFED_API'
        ]
        
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def test_pixelfed_configuration_valid(self):
        """Test valid Pixelfed configuration"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'ACTIVITYPUB_USERNAME': 'testuser'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'pixelfed')
            self.assertEqual(config.instance_url, 'https://pixelfed.example.com')
            self.assertEqual(config.access_token, 'test_token')
            self.assertEqual(config.username, 'testuser')
            self.assertIsNone(config.client_key)
            self.assertIsNone(config.client_secret)
    
    def test_mastodon_configuration_valid(self):
        """Test valid Mastodon configuration"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'mastodon')
            self.assertEqual(config.instance_url, 'https://mastodon.example.com')
            self.assertEqual(config.access_token, 'test_token')
            self.assertEqual(config.username, 'testuser')
            self.assertEqual(config.client_key, 'test_client_key')
            self.assertEqual(config.client_secret, 'test_client_secret')
    
    def test_default_behavior_no_api_type(self):
        """Test default behavior when ACTIVITYPUB_API_TYPE is not set (should default to pixelfed)"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'pixelfed')
    
    def test_mastodon_missing_client_key_error(self):
        """Test configuration validation error for missing Mastodon client key"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
            # Missing MASTODON_CLIENT_KEY
        }):
            with self.assertRaises(ConfigurationError) as context:
                ActivityPubConfig.from_env()
            
            self.assertIn("MASTODON_CLIENT_KEY is required", str(context.exception))
    
    def test_mastodon_missing_client_secret_error(self):
        """Test configuration validation error for missing Mastodon client secret"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_KEY': 'test_client_key'
            # Missing MASTODON_CLIENT_SECRET
        }):
            with self.assertRaises(ConfigurationError) as context:
                ActivityPubConfig.from_env()
            
            self.assertIn("MASTODON_CLIENT_SECRET is required", str(context.exception))
    
    def test_pixelfed_missing_credentials_error(self):
        """Test configuration validation error for missing Pixelfed credentials"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com'
            # Missing ACTIVITYPUB_ACCESS_TOKEN
        }):
            with self.assertRaises(ConfigurationError) as context:
                ActivityPubConfig.from_env()
            
            self.assertIn("ACTIVITYPUB_ACCESS_TOKEN is required", str(context.exception))
    
    def test_missing_instance_url_error(self):
        """Test configuration validation error for missing instance URL"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
            # Missing ACTIVITYPUB_INSTANCE_URL
        }):
            with self.assertRaises(ConfigurationError) as context:
                ActivityPubConfig.from_env()
            
            self.assertIn("ACTIVITYPUB_INSTANCE_URL is required", str(context.exception))
    
    def test_backward_compatibility_pixelfed_api_flag(self):
        """Test backward compatibility with existing PIXELFED_API flag"""
        with patch.dict(os.environ, {
            'PIXELFED_API': 'true',
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'pixelfed')
            self.assertTrue(config.is_pixelfed)
    
    def test_backward_compatibility_platform_type(self):
        """Test backward compatibility with ACTIVITYPUB_PLATFORM_TYPE"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_PLATFORM_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'mastodon')
            self.assertEqual(config.platform_type, 'mastodon')
    
    def test_environment_variable_precedence(self):
        """Test that ACTIVITYPUB_API_TYPE takes precedence over legacy variables"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_PLATFORM_TYPE': 'pixelfed',  # Should be ignored
            'PIXELFED_API': 'true',  # Should be ignored
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'mastodon')
    
    def test_configuration_object_creation_pixelfed(self):
        """Test configuration object creation for Pixelfed platform"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'PRIVATE_KEY_PATH': '/path/to/private.key',
            'PUBLIC_KEY_PATH': '/path/to/public.key'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'pixelfed')
            self.assertEqual(config.private_key_path, '/path/to/private.key')
            self.assertEqual(config.public_key_path, '/path/to/public.key')
            self.assertIsNone(config.client_key)
            self.assertIsNone(config.client_secret)
    
    def test_configuration_object_creation_mastodon(self):
        """Test configuration object creation for Mastodon platform"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'mastodon')
            self.assertEqual(config.client_key, 'test_client_key')
            self.assertEqual(config.client_secret, 'test_client_secret')
            self.assertIsNone(config.private_key_path)
            self.assertIsNone(config.public_key_path)
    
    def test_unsupported_api_type_fallback(self):
        """Test that unsupported API types fall back to pixelfed"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'unsupported_platform',
            'ACTIVITYPUB_INSTANCE_URL': 'https://example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'pixelfed')
    
    def test_case_insensitive_api_type(self):
        """Test that API type is case insensitive"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'MASTODON',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
        }):
            config = ActivityPubConfig.from_env()
            
            self.assertEqual(config.api_type, 'mastodon')


class TestConfigIntegration(unittest.TestCase):
    """Integration tests for configuration loading in different deployment scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear environment variables before each test
        env_vars_to_clear = [
            'ACTIVITYPUB_API_TYPE',
            'ACTIVITYPUB_INSTANCE_URL',
            'ACTIVITYPUB_ACCESS_TOKEN',
            'ACTIVITYPUB_USERNAME',
            'MASTODON_CLIENT_KEY',
            'MASTODON_CLIENT_SECRET',
            'PRIVATE_KEY_PATH',
            'PUBLIC_KEY_PATH',
            'ACTIVITYPUB_PLATFORM_TYPE',
            'PIXELFED_API'
        ]
        
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]
    
    def test_full_config_pixelfed_deployment(self):
        """Test complete configuration loading for Pixelfed deployment"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'PRIVATE_KEY_PATH': '/path/to/private.key',
            'PUBLIC_KEY_PATH': '/path/to/public.key',
            'MAX_POSTS_PER_RUN': '20',
            'LOG_LEVEL': 'DEBUG'
        }):
            config = Config()
            
            self.assertEqual(config.activitypub.api_type, 'pixelfed')
            self.assertEqual(config.activitypub.instance_url, 'https://pixelfed.example.com')
            self.assertEqual(config.activitypub.access_token, 'test_token')
            self.assertEqual(config.activitypub.username, 'testuser')
            self.assertEqual(config.max_posts_per_run, 20)
            self.assertEqual(config.log_level, 'DEBUG')
    
    def test_full_config_mastodon_deployment(self):
        """Test complete configuration loading for Mastodon deployment"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret',
            'MAX_POSTS_PER_RUN': '30',
            'LOG_LEVEL': 'INFO'
        }):
            config = Config()
            
            self.assertEqual(config.activitypub.api_type, 'mastodon')
            self.assertEqual(config.activitypub.instance_url, 'https://mastodon.example.com')
            self.assertEqual(config.activitypub.access_token, 'test_token')
            self.assertEqual(config.activitypub.username, 'testuser')
            self.assertEqual(config.activitypub.client_key, 'test_client_key')
            self.assertEqual(config.activitypub.client_secret, 'test_client_secret')
            self.assertEqual(config.max_posts_per_run, 30)
            self.assertEqual(config.log_level, 'INFO')
    
    def test_legacy_pixelfed_deployment_compatibility(self):
        """Test that legacy Pixelfed deployments continue to work"""
        with patch.dict(os.environ, {
            'PIXELFED_API': 'true',
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'ACTIVITYPUB_USERNAME': 'testuser'
        }):
            config = Config()
            
            self.assertEqual(config.activitypub.api_type, 'pixelfed')
            self.assertTrue(config.activitypub.is_pixelfed)
            self.assertEqual(config.activitypub.instance_url, 'https://pixelfed.example.com')
    
    def test_migration_from_platform_type_to_api_type(self):
        """Test migration from ACTIVITYPUB_PLATFORM_TYPE to ACTIVITYPUB_API_TYPE"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_PLATFORM_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
            'MASTODON_CLIENT_KEY': 'test_client_key',
            'MASTODON_CLIENT_SECRET': 'test_client_secret'
        }):
            config = Config()
            
            self.assertEqual(config.activitypub.api_type, 'mastodon')
            self.assertEqual(config.activitypub.platform_type, 'mastodon')
    
    def test_minimal_pixelfed_configuration(self):
        """Test minimal required configuration for Pixelfed"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_INSTANCE_URL': 'https://pixelfed.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
        }):
            config = Config()
            
            # Should default to pixelfed and work with minimal config
            self.assertEqual(config.activitypub.api_type, 'pixelfed')
            self.assertEqual(config.activitypub.instance_url, 'https://pixelfed.example.com')
            self.assertEqual(config.activitypub.access_token, 'test_token')
    
    def test_invalid_mastodon_configuration_raises_error(self):
        """Test that invalid Mastodon configuration raises appropriate error"""
        with patch.dict(os.environ, {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.example.com',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
            # Missing Mastodon client credentials
        }):
            with self.assertRaises(ConfigurationError):
                Config()


if __name__ == '__main__':
    unittest.main()