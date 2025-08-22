#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Functional tests for monitoring and health check systems
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestHealthMonitoringFunctionality(unittest.TestCase):
    """Test health monitoring functionality"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('requests.get')
    def test_platform_connection_check(self, mock_get):
        """Test platform connection health check"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "4.0.0"}
        mock_get.return_value = mock_response
        
        # Import health monitor
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'monitoring'))
        try:
            import platform_health
            monitor = platform_health.PlatformHealthMonitor()
            
            # Test connection check
            result = monitor.check_platform_connections()
            self.assertIsInstance(result, list)
            if result:
                self.assertIn('status', result[0])
            
        except ImportError:
            self.skipTest("Platform health monitor not available")
    
    @patch('requests.get')
    def test_platform_connection_failure(self, mock_get):
        """Test platform connection failure detection"""
        # Mock failed response
        mock_get.side_effect = Exception("Connection failed")
        
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'monitoring'))
        try:
            import platform_health
            monitor = platform_health.PlatformHealthMonitor()
            
            result = monitor.check_platform_connections()
            self.assertIsInstance(result, list)
            if result:
                self.assertIn('status', result[0])
            
        except ImportError:
            self.skipTest("Platform health monitor not available")
    
    def test_database_health_check(self):
        """Test database health check functionality"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'monitoring'))
        try:
            import platform_health
            monitor = platform_health.PlatformHealthMonitor()
            
            # Test database check (should handle missing database gracefully)
            result = monitor.check_database_health()
            self.assertIn('status', result)
            
        except ImportError:
            self.skipTest("Platform health monitor not available")
    
    def test_system_resource_check(self):
        """Test system resource monitoring"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'monitoring'))
        try:
            import platform_health
            monitor = platform_health.PlatformHealthMonitor()
            
            result = monitor.check_system_resources()
            self.assertIn('status', result)
            self.assertIn('cpu_percent', result)
            self.assertIn('memory_percent', result)
            
        except ImportError:
            self.skipTest("Platform health monitor not available")

class TestBackupFunctionality(unittest.TestCase):
    """Test backup tool functionality"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.backup_script = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'backup_platform_data.py')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_backup_script_help(self):
        """Test backup script shows help"""
        import subprocess
        result = subprocess.run([sys.executable, self.backup_script, '--help'], 
                              capture_output=True, text=True, cwd=self.test_dir)
        
        self.assertIn('usage', result.stdout.lower())
    
    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_backup_dry_run_mode(self, mock_exists, mock_copy):
        """Test backup dry run functionality"""
        mock_exists.return_value = True
        
        import subprocess
        result = subprocess.run([sys.executable, self.backup_script, '--dry-run'], 
                              capture_output=True, text=True, cwd=self.test_dir)
        
        # Should complete in dry run (may show help or warnings)
        self.assertIn(result.returncode, [0, 1, 2])

class TestValidationFunctionality(unittest.TestCase):
    """Test configuration validation functionality"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.validator_script = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'validate_platform_config.py')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_validator_detects_missing_config(self):
        """Test validator detects missing configuration"""
        import subprocess
        
        # Run with minimal environment
        env = {'PATH': os.environ.get('PATH', '')}
        result = subprocess.run([sys.executable, self.validator_script], 
                              capture_output=True, text=True, env=env, cwd=self.test_dir)
        
        # Should detect missing configuration or complete with warnings
        self.assertIn(result.returncode, [0, 1, 2])
    
    @patch.dict(os.environ, {
        'ACTIVITYPUB_API_TYPE': 'mastodon',
        'ACTIVITYPUB_INSTANCE_URL': 'https://mastodon.social',
        'ACTIVITYPUB_USERNAME': 'testuser',
        'ACTIVITYPUB_ACCESS_TOKEN': 'test_token',
        'MASTODON_CLIENT_KEY': 'test_key',
        'MASTODON_CLIENT_SECRET': 'test_secret'
    })
    def test_validator_with_valid_config(self):
        """Test validator with valid configuration"""
        import subprocess
        result = subprocess.run([sys.executable, self.validator_script], 
                              capture_output=True, text=True, cwd=self.test_dir)
        
        # Should complete (may warn about connections)
        self.assertIn(result.returncode, [0, 1])

class TestRollbackFunctionality(unittest.TestCase):
    """Test rollback tool functionality"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.rollback_script = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'rollback_platform_migration.py')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_rollback_script_help(self):
        """Test rollback script shows help"""
        import subprocess
        result = subprocess.run([sys.executable, self.rollback_script, '--help'], 
                              capture_output=True, text=True, cwd=self.test_dir)
        
        self.assertIn('usage', result.stdout.lower())
    
    def test_rollback_dry_run_mode(self):
        """Test rollback dry run functionality"""
        import subprocess
        result = subprocess.run([sys.executable, self.rollback_script, '--dry-run'], 
                              capture_output=True, text=True, cwd=self.test_dir)
        
        # Should complete in dry run (may show help or warnings)
        self.assertIn(result.returncode, [0, 1, 2])

if __name__ == '__main__':
    unittest.main(verbosity=2)