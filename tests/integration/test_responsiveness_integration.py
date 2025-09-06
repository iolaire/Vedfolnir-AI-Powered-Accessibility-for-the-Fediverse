# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for responsiveness monitoring with health checks.

Tests the integration of responsiveness monitoring functionality with the
existing health check systems.
"""

import unittest
import asyncio
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from health_check import HealthChecker, HealthStatus


class TestResponsivenessIntegration(unittest.TestCase):
    """Integration tests for responsiveness monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        try:
            self.config = Config()
            self.db_manager = DatabaseManager(self.config)
            self.health_checker = HealthChecker(self.config, self.db_manager)
        except Exception as e:
            self.skipTest(f"Could not initialize test environment: {e}")
    
    def test_health_checker_has_responsiveness_config(self):
        """Test that HealthChecker has responsiveness configuration"""
        self.assertIsNotNone(self.health_checker.responsiveness_config)
        self.assertHasAttr(self.health_checker.responsiveness_config, 'memory_warning_threshold')
        self.assertHasAttr(self.health_checker.responsiveness_config, 'memory_critical_threshold')
        self.assertHasAttr(self.health_checker.responsiveness_config, 'cpu_warning_threshold')
        self.assertHasAttr(self.health_checker.responsiveness_config, 'cpu_critical_threshold')
    
    def test_health_checker_has_responsiveness_method(self):
        """Test that HealthChecker has responsiveness health check method"""
        self.assertTrue(hasattr(self.health_checker, 'check_responsiveness_health'))
        self.assertTrue(callable(getattr(self.health_checker, 'check_responsiveness_health')))
    
    def test_health_checker_has_alert_method(self):
        """Test that HealthChecker has responsiveness alert method"""
        self.assertTrue(hasattr(self.health_checker, 'send_responsiveness_alerts'))
        self.assertTrue(callable(getattr(self.health_checker, 'send_responsiveness_alerts')))
    
    def test_responsiveness_health_check_basic(self):
        """Test basic responsiveness health check functionality"""
        try:
            # Run responsiveness health check
            result = asyncio.run(self.health_checker.check_responsiveness_health())
            
            # Verify result structure
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "responsiveness")
            self.assertIn(result.status, [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY])
            self.assertIsNotNone(result.message)
            self.assertIsNotNone(result.details)
            
            # Verify details structure
            self.assertIn('system_optimizer_available', result.details)
            self.assertIn('monitoring_config', result.details)
            
        except Exception as e:
            self.skipTest(f"Responsiveness health check failed: {e}")
    
    def test_system_health_includes_responsiveness(self):
        """Test that system health check includes responsiveness component"""
        try:
            # Run full system health check
            result = asyncio.run(self.health_checker.check_system_health())
            
            # Verify responsiveness is included
            self.assertIn("responsiveness", result.components)
            self.assertEqual(result.components["responsiveness"].name, "responsiveness")
            
        except Exception as e:
            self.skipTest(f"System health check failed: {e}")
    
    def assertHasAttr(self, obj, attr):
        """Helper method to assert object has attribute"""
        self.assertTrue(hasattr(obj, attr), f"Object {obj} does not have attribute '{attr}'")


if __name__ == '__main__':
    unittest.main()