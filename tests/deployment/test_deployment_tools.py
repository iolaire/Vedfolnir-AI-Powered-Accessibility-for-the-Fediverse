#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for deployment and monitoring tools (Task 6.2)
"""

import unittest
import os
import tempfile
import shutil
import subprocess
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestDeploymentScript(unittest.TestCase):
    """Test the deployment script functionality"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'deploy_platform_aware.sh')
        
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_deployment_script_exists(self):
        """Test that deployment script exists and is executable"""
        self.assertTrue(os.path.exists(self.script_path))
        self.assertTrue(os.access(self.script_path, os.X_OK))
    
    def test_deployment_script_syntax(self):
        """Test that deployment script has valid bash syntax"""
        result = subprocess.run(['bash', '-n', self.script_path], 
                              capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation tool"""
    
    def setUp(self):
        self.validator_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'validate_platform_config.py')
        
    def test_validator_exists(self):
        """Test that validator script exists"""
        self.assertTrue(os.path.exists(self.validator_path))
    
    def test_validator_syntax(self):
        """Test that validator has valid Python syntax"""
        result = subprocess.run([sys.executable, '-m', 'py_compile', self.validator_path], 
                              capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestPlatformHealth(unittest.TestCase):
    """Test platform health monitoring"""
    
    def setUp(self):
        self.health_path = os.path.join(os.path.dirname(__file__), '..', '..', 'monitoring', 'platform_health.py')
        
    def test_health_monitor_exists(self):
        """Test that health monitor exists"""
        self.assertTrue(os.path.exists(self.health_path))
    
    def test_health_monitor_syntax(self):
        """Test that health monitor has valid Python syntax"""
        result = subprocess.run([sys.executable, '-m', 'py_compile', self.health_path], 
                              capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestBackupTool(unittest.TestCase):
    """Test platform-aware backup tool"""
    
    def setUp(self):
        self.backup_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'backup_platform_data.py')
        
    def test_backup_tool_exists(self):
        """Test that backup tool exists"""
        self.assertTrue(os.path.exists(self.backup_path))
    
    def test_backup_tool_syntax(self):
        """Test that backup tool has valid Python syntax"""
        result = subprocess.run([sys.executable, '-m', 'py_compile', self.backup_path], 
                              capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestRollbackTool(unittest.TestCase):
    """Test migration rollback tool"""
    
    def setUp(self):
        self.rollback_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'rollback_platform_migration.py')
        
    def test_rollback_tool_exists(self):
        """Test that rollback tool exists"""
        self.assertTrue(os.path.exists(self.rollback_path))
    
    def test_rollback_tool_syntax(self):
        """Test that rollback tool has valid Python syntax"""
        result = subprocess.run([sys.executable, '-m', 'py_compile', self.rollback_path], 
                              capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")


class TestDeploymentIntegration(unittest.TestCase):
    """Integration tests for deployment tools"""
    
    def test_all_tools_exist(self):
        """Test that all required deployment tools exist"""
        tools = [
            'scripts/deploy_platform_aware.sh',
            'scripts/validate_platform_config.py',
            'monitoring/platform_health.py',
            'scripts/backup_platform_data.py',
            'scripts/rollback_platform_migration.py'
        ]
        
        for tool in tools:
            tool_path = os.path.join(os.path.dirname(__file__), '..', '..', tool)
            self.assertTrue(os.path.exists(tool_path), f"Missing tool: {tool}")


if __name__ == '__main__':
    unittest.main(verbosity=2)