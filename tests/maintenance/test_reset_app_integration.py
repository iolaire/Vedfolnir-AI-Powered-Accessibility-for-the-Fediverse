# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration test for reset_app.py functionality

This test verifies that the reset_app.py script works correctly by running
the actual command-line interface.
"""

import unittest
import subprocess
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestResetAppIntegration(unittest.TestCase):
    """Integration test for reset_app.py script"""
    
    def setUp(self):
        """Set up test environment"""
        self.script_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            'scripts', 'maintenance', 'reset_app.py'
        )
    
    def test_help_command(self):
        """Test that help command works"""
        result = subprocess.run([
            'python', self.script_path, '--help'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Vedfolnir Application Reset Tool', result.stdout)
        self.assertIn('--delete-all-user-data', result.stdout)
        self.assertIn('--reset-complete', result.stdout)
    
    def test_status_command(self):
        """Test that status command works"""
        result = subprocess.run([
            'python', self.script_path, '--status'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        # Output goes to stderr (logging)
        combined_output = result.stdout + result.stderr
        self.assertIn('Application Status', combined_output)
    
    def test_delete_all_user_data_dry_run(self):
        """Test that delete all user data dry run works"""
        result = subprocess.run([
            'python', self.script_path, '--delete-all-user-data', '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        # Output goes to stderr (logging)
        combined_output = result.stdout + result.stderr
        self.assertIn('DRY RUN SUMMARY', combined_output)
        self.assertIn('Users Processed:', combined_output)
    
    def test_reset_complete_dry_run(self):
        """Test that reset complete dry run works"""
        result = subprocess.run([
            'python', self.script_path, '--reset-complete', '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        # Output goes to stderr (logging)
        combined_output = result.stdout + result.stderr
        self.assertIn('DRY RUN - Complete reset would be successful', combined_output)
    
    def test_clear_redis_dry_run(self):
        """Test that clear Redis dry run works"""
        result = subprocess.run([
            'python', self.script_path, '--clear-redis', '--dry-run'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        # Output goes to stderr (logging)
        combined_output = result.stdout + result.stderr
        # Should either succeed or warn about Redis not being available
        self.assertTrue(
            'DRY RUN - Would clear' in combined_output or 
            'Redis connection failed' in combined_output
        )


if __name__ == '__main__':
    unittest.main()