#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test suite for the configuration validation script.
"""

import os
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch


class TestConfigValidationScript(unittest.TestCase):
    """Test the validate_config.py script"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.script_path = os.path.join(self.project_root, 'validate_config.py')
    
    def test_validation_script_exists(self):
        """Test that the validation script exists and is executable"""
        self.assertTrue(os.path.exists(self.script_path), "validate_config.py script does not exist")
    
    def test_validation_script_runs_with_valid_config(self):
        """Test that the validation script runs successfully with valid configuration"""
        # Create a temporary valid configuration
        valid_config = {
            'ACTIVITYPUB_API_TYPE': 'pixelfed',
            'ACTIVITYPUB_INSTANCE_URL': 'https://test.example.com',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token_123',
            'OLLAMA_URL': 'http://localhost:11434',
            'OLLAMA_MODEL': 'llava:7b'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            for key, value in valid_config.items():
                temp_file.write(f"{key}={value}\n")
            temp_file.flush()
            
            try:
                # Run the validation script with the temporary config
                env = os.environ.copy()
                env.update(valid_config)
                
                result = subprocess.run(
                    [sys.executable, self.script_path],
                    env=env,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                # The script should run successfully
                self.assertEqual(result.returncode, 0, f"Script failed with output: {result.stderr}")
                self.assertIn("Configuration validation successful", result.stdout)
                
            finally:
                os.unlink(temp_file.name)
    
    def test_validation_script_fails_with_invalid_config(self):
        """Test that the validation script fails appropriately with invalid configuration"""
        # Create a temporary invalid configuration (missing required fields)
        invalid_config = {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://test.example.com',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token_123',
            # Missing MASTODON_CLIENT_KEY and MASTODON_CLIENT_SECRET
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            for key, value in invalid_config.items():
                temp_file.write(f"{key}={value}\n")
            temp_file.flush()
            
            try:
                # Run the validation script with the temporary config
                env = os.environ.copy()
                env.clear()  # Clear environment to ensure only our config is used
                env.update(invalid_config)
                
                result = subprocess.run(
                    [sys.executable, self.script_path],
                    env=env,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                # The script should fail with a configuration error
                self.assertNotEqual(result.returncode, 0, "Script should have failed with invalid config")
                self.assertIn("Configuration Error", result.stdout)
                
            finally:
                os.unlink(temp_file.name)
    
    def test_validation_script_provides_helpful_error_messages(self):
        """Test that the validation script provides helpful error messages"""
        # Test with missing Mastodon credentials
        invalid_config = {
            'ACTIVITYPUB_API_TYPE': 'mastodon',
            'ACTIVITYPUB_INSTANCE_URL': 'https://test.example.com',
            'ACTIVITYPUB_USERNAME': 'testuser',
            'ACTIVITYPUB_ACCESS_TOKEN': 'test_token_123',
        }
        
        env = os.environ.copy()
        env.clear()
        env.update(invalid_config)
        
        result = subprocess.run(
            [sys.executable, self.script_path],
            env=env,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        # Should provide helpful error message about Mastodon credentials
        self.assertIn("Create a Mastodon application", result.stdout)
        self.assertIn("client key and secret", result.stdout)


if __name__ == '__main__':
    unittest.main()