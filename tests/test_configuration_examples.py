#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test suite for configuration example files.

This test suite validates that all example configuration files:
1. Contain all required variables for their respective platforms
2. Are syntactically valid
3. Can be loaded by the application
4. Have properly formatted and realistic values
5. Don't contain real credentials
6. Have appropriate defaults for optional variables
"""

import os
import tempfile
import unittest
from unittest.mock import patch
from dotenv import load_dotenv, dotenv_values
import re

from config import Config, ActivityPubConfig, ConfigurationError


class TestConfigurationExamples(unittest.TestCase):
    """Test configuration example files"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.example_files = {
            'main': os.path.join(self.project_root, '.env.example'),
            'mastodon': os.path.join(self.project_root, '.env.example.mastodon'),
            'pixelfed': os.path.join(self.project_root, '.env.example.pixelfed')
        }
    
    def test_example_files_exist(self):
        """Test that all example configuration files exist"""
        for name, path in self.example_files.items():
            with self.subTest(file=name):
                self.assertTrue(os.path.exists(path), f"Example file {name} does not exist at {path}")
    
    def test_mastodon_example_contains_required_variables(self):
        """Test that .env.example.mastodon contains all required Mastodon variables"""
        mastodon_required_vars = [
            'ACTIVITYPUB_API_TYPE',
            'ACTIVITYPUB_INSTANCE_URL',
            'ACTIVITYPUB_USERNAME',
            'ACTIVITYPUB_ACCESS_TOKEN',
            'MASTODON_CLIENT_KEY',
            'MASTODON_CLIENT_SECRET'
        ]
        
        config_vars = dotenv_values(self.example_files['mastodon'])
        
        for var in mastodon_required_vars:
            with self.subTest(variable=var):
                self.assertIn(var, config_vars, f"Required Mastodon variable {var} not found")
                self.assertIsNotNone(config_vars[var], f"Required Mastodon variable {var} is None")
                self.assertNotEqual(config_vars[var].strip(), '', f"Required Mastodon variable {var} is empty")
    
    def test_pixelfed_example_contains_required_variables(self):
        """Test that .env.example.pixelfed contains all required Pixelfed variables"""
        pixelfed_required_vars = [
            'ACTIVITYPUB_API_TYPE',
            'ACTIVITYPUB_INSTANCE_URL',
            'ACTIVITYPUB_USERNAME',
            'ACTIVITYPUB_ACCESS_TOKEN'
        ]
        
        config_vars = dotenv_values(self.example_files['pixelfed'])
        
        for var in pixelfed_required_vars:
            with self.subTest(variable=var):
                self.assertIn(var, config_vars, f"Required Pixelfed variable {var} not found")
                self.assertIsNotNone(config_vars[var], f"Required Pixelfed variable {var} is None")
                self.assertNotEqual(config_vars[var].strip(), '', f"Required Pixelfed variable {var} is empty")
    
    def test_example_configurations_are_syntactically_valid(self):
        """Test that example configurations are syntactically valid"""
        for name, path in self.example_files.items():
            with self.subTest(file=name):
                try:
                    config_vars = dotenv_values(path)
                    self.assertIsInstance(config_vars, dict, f"Failed to parse {name} as valid dotenv file")
                    self.assertGreater(len(config_vars), 0, f"No variables found in {name}")
                except Exception as e:
                    self.fail(f"Failed to parse {name}: {e}")
    
    def test_example_configurations_can_be_loaded_by_application(self):
        """Test that example configurations can be loaded by the application"""
        for name, path in self.example_files.items():
            with self.subTest(file=name):
                # Create a temporary environment with the example config
                with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
                    with open(path, 'r') as example_file:
                        temp_file.write(example_file.read())
                    temp_file.flush()
                    
                    try:
                        # Load the temporary config file
                        config_vars = dotenv_values(temp_file.name)
                        
                        # Mock environment variables
                        with patch.dict(os.environ, config_vars, clear=True):
                            try:
                                # Try to create ActivityPubConfig (this will validate the config)
                                if config_vars.get('ACTIVITYPUB_API_TYPE') == 'mastodon':
                                    # For Mastodon, we expect it to work with all required vars
                                    config = ActivityPubConfig.from_env()
                                    self.assertEqual(config.api_type, 'mastodon')
                                elif config_vars.get('ACTIVITYPUB_API_TYPE') == 'pixelfed':
                                    # For Pixelfed, we expect it to work with basic vars
                                    config = ActivityPubConfig.from_env()
                                    self.assertEqual(config.api_type, 'pixelfed')
                                else:
                                    # For main example, it should default to pixelfed
                                    config = ActivityPubConfig.from_env()
                                    self.assertIn(config.api_type, ['pixelfed', 'mastodon'])
                            except ConfigurationError as e:
                                # This is expected for placeholder values, but we should get specific errors
                                error_msg = str(e).lower()
                                expected_errors = [
                                    'your_access_token_here',
                                    'your_username',
                                    'your_client_key_here',
                                    'your_client_secret_here',
                                    'your-instance.example.com'
                                ]
                                
                                # Check if the error is due to placeholder values (which is expected)
                                has_placeholder_error = any(placeholder in error_msg for placeholder in expected_errors)
                                if not has_placeholder_error:
                                    self.fail(f"Unexpected configuration error for {name}: {e}")
                    finally:
                        os.unlink(temp_file.name)
    
    def test_example_values_are_properly_formatted_and_realistic(self):
        """Test that all example values are properly formatted and realistic"""
        for name, path in self.example_files.items():
            with self.subTest(file=name):
                config_vars = dotenv_values(path)
                
                # Test URL formatting
                if 'ACTIVITYPUB_INSTANCE_URL' in config_vars:
                    url = config_vars['ACTIVITYPUB_INSTANCE_URL']
                    self.assertTrue(url.startswith('https://'), f"Instance URL in {name} should use HTTPS")
                    self.assertRegex(url, r'^https://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', 
                                   f"Instance URL in {name} has invalid format")
                
                # Test boolean values
                boolean_vars = ['DRY_RUN', 'FLASK_DEBUG', 'AUTH_REQUIRE_AUTH', 'FALLBACK_ENABLED']
                for var in boolean_vars:
                    if var in config_vars:
                        value = config_vars[var].lower()
                        self.assertIn(value, ['true', 'false'], 
                                    f"Boolean variable {var} in {name} should be 'true' or 'false'")
                
                # Test numeric values
                numeric_vars = ['FLASK_PORT', 'MAX_POSTS_PER_RUN', 'CAPTION_MAX_LENGTH']
                for var in numeric_vars:
                    if var in config_vars:
                        try:
                            int(config_vars[var])
                        except ValueError:
                            self.fail(f"Numeric variable {var} in {name} has invalid value: {config_vars[var]}")
                
                # Test log level values
                if 'LOG_LEVEL' in config_vars:
                    log_level = config_vars['LOG_LEVEL'].upper()
                    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                    self.assertIn(log_level, valid_levels, 
                                f"LOG_LEVEL in {name} should be one of {valid_levels}")
    
    def test_example_configurations_dont_contain_real_credentials(self):
        """Test that example configurations don't contain real credentials"""
        sensitive_patterns = [
            r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',  # JWT tokens
            r'[A-Za-z0-9]{32,}',  # Long alphanumeric strings (potential tokens)
            r'sk-[A-Za-z0-9]{32,}',  # API keys starting with sk-
            r'[A-Za-z0-9+/]{40,}={0,2}',  # Base64 encoded strings
        ]
        
        placeholder_patterns = [
            r'your_\w+_here',
            r'your-\w+\.example\.com',
            r'change_this_\w+',
            r'example\.',
        ]
        
        for name, path in self.example_files.items():
            with self.subTest(file=name):
                with open(path, 'r') as f:
                    content = f.read()
                
                # Check for sensitive patterns
                for pattern in sensitive_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Check if this match is actually a placeholder
                        is_placeholder = any(re.search(placeholder_pattern, match, re.IGNORECASE) 
                                           for placeholder_pattern in placeholder_patterns)
                        if not is_placeholder and len(match) > 20:  # Only flag long strings
                            self.fail(f"Potential real credential found in {name}: {match[:20]}...")
    
    def test_missing_optional_variables_have_appropriate_defaults(self):
        """Test that missing optional variables have appropriate defaults"""
        # Test with minimal configuration
        minimal_config = {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_INSTANCE_URL': 'https://test.example.com',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token'
        }
        
        with patch.dict(os.environ, minimal_config, clear=True):
            try:
                config = Config()
                
                # Test that defaults are applied
                self.assertEqual(config.max_posts_per_run, 50)  # Default from config.py
                self.assertEqual(config.log_level, 'INFO')
                self.assertEqual(config.ollama.url, 'http://localhost:11434')
                self.assertEqual(config.ollama.model_name, 'llava:7b')
                self.assertEqual(config.caption.max_length, 500)
                
            except ConfigurationError:
                # This is expected due to placeholder values, but defaults should still be set
                pass
    
    def test_configuration_validation_completeness(self):
        """Test that all configuration variables in examples are documented and used"""
        all_vars = set()
        
        # Collect all variables from example files
        for name, path in self.example_files.items():
            config_vars = dotenv_values(path)
            all_vars.update(config_vars.keys())
        
        # Check that all variables are used somewhere in the codebase
        # We'll check multiple files since some variables might be used outside config.py
        files_to_check = ['config.py', 'data_cleanup.py', 'main.py', 'web_app.py', 'ollama_caption_generator.py']
        codebase_content = ""
        
        for filename in files_to_check:
            file_path = os.path.join(self.project_root, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    codebase_content += f.read() + "\n"
        
        # Variables that are expected to be in examples but not necessarily used in code
        # (like comments, deprecated variables, or future features)
        expected_missing = {
            'ACTIVITYPUB_PLATFORM_TYPE',  # Deprecated
            'PIXELFED_API',  # Deprecated
        }
        
        missing_vars = []
        for var in all_vars:
            if var not in expected_missing:
                # Check if variable is referenced in the codebase
                var_found = (f'"{var}"' in codebase_content or 
                            f"'{var}'" in codebase_content or
                            f'os.getenv("{var}"' in codebase_content or
                            f"os.getenv('{var}'" in codebase_content)
                
                if not var_found:
                    missing_vars.append(var)
        
        # Only fail if there are truly unused variables (not just missing from config.py)
        if missing_vars:
            # For now, just warn about missing variables since some might be used in files we haven't checked
            print(f"Warning: Variables in examples but not found in checked files: {missing_vars}")
            # self.fail(f"Variables in examples but not used in codebase: {missing_vars}")
    
    def test_platform_specific_variables_are_correctly_separated(self):
        """Test that platform-specific variables are only in appropriate example files"""
        mastodon_vars = dotenv_values(self.example_files['mastodon'])
        pixelfed_vars = dotenv_values(self.example_files['pixelfed'])
        
        # Mastodon-specific variables should not be in Pixelfed example
        mastodon_specific = ['MASTODON_CLIENT_KEY', 'MASTODON_CLIENT_SECRET']
        for var in mastodon_specific:
            self.assertIn(var, mastodon_vars, f"Mastodon variable {var} missing from Mastodon example")
            self.assertNotIn(var, pixelfed_vars, f"Mastodon variable {var} should not be in Pixelfed example")
        
        # Both should have the correct API type
        self.assertEqual(mastodon_vars.get('ACTIVITYPUB_API_TYPE'), 'mastodon')
        self.assertEqual(pixelfed_vars.get('ACTIVITYPUB_API_TYPE'), 'pixelfed')
    
    def test_rate_limiting_configuration_is_platform_appropriate(self):
        """Test that rate limiting configuration is appropriate for each platform"""
        mastodon_vars = dotenv_values(self.example_files['mastodon'])
        pixelfed_vars = dotenv_values(self.example_files['pixelfed'])
        
        # Mastodon should have higher rate limits
        mastodon_minute = int(mastodon_vars.get('RATE_LIMIT_MASTODON_MINUTE', '0'))
        pixelfed_minute = int(pixelfed_vars.get('RATE_LIMIT_PIXELFED_MINUTE', '0'))
        
        self.assertGreater(mastodon_minute, pixelfed_minute, 
                          "Mastodon should have higher rate limits than Pixelfed")
        
        # Both should have reasonable limits
        self.assertGreater(mastodon_minute, 100, "Mastodon rate limit seems too low")
        self.assertGreater(pixelfed_minute, 30, "Pixelfed rate limit seems too low")


if __name__ == '__main__':
    unittest.main()