# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple Test for System Administration Routes

Tests basic functionality without Flask context dependencies.
"""

import unittest
import sys
import os
from unittest.mock import Mock

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestSystemAdministrationSimple(unittest.TestCase):
    """Simple test for system administration routes"""
    
    def test_route_module_imports(self):
        """Test that the system administration module can be imported"""
        try:
            import app.blueprints.admin.system_administration
            self.assertTrue(True, "System administration module imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import system administration module: {e}")
    
    def test_route_registration_function_exists(self):
        """Test that the register_routes function exists"""
        import app.blueprints.admin.system_administration as sys_admin
        
        self.assertTrue(hasattr(sys_admin, 'register_routes'), 
                       "register_routes function should exist")
        self.assertTrue(callable(sys_admin.register_routes), 
                       "register_routes should be callable")
    
    def test_route_registration_calls_blueprint(self):
        """Test that route registration calls blueprint methods"""
        import app.blueprints.admin.system_administration as sys_admin
        
        # Create mock blueprint
        mock_bp = Mock()
        
        # Call register_routes
        sys_admin.register_routes(mock_bp)
        
        # Verify that blueprint.route was called multiple times
        self.assertTrue(mock_bp.route.called, "Blueprint route method should be called")
        
        # Check that multiple routes were registered
        call_count = mock_bp.route.call_count
        self.assertGreaterEqual(call_count, 6, f"Expected at least 6 route registrations, got {call_count}")
        
        # Verify specific routes were registered
        route_calls = [call[0][0] for call in mock_bp.route.call_args_list]
        expected_routes = ['/system', '/system/api/health', '/system/api/performance', 
                          '/system/api/resources', '/system/api/errors', '/system/api/stuck-jobs', 
                          '/system/api/queue-prediction']
        
        for expected_route in expected_routes:
            self.assertIn(expected_route, route_calls, 
                         f"Route {expected_route} should be registered")
    
    def test_consolidated_framework_imports(self):
        """Test that consolidated framework components can be imported"""
        try:
            from app.services.monitoring.system.system_monitor import SystemMonitor
            from app.services.monitoring.performance.monitors.performance_monitor import get_performance_monitor
            self.assertTrue(True, "Consolidated monitoring frameworks imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import consolidated monitoring frameworks: {e}")
    
    def test_template_file_exists(self):
        """Test that the admin template file exists"""
        template_path = os.path.join(os.path.dirname(__file__), '..', '..', 
                                   'admin', 'templates', 'admin_system_administration.html')
        self.assertTrue(os.path.exists(template_path), 
                       "System administration template should exist")
        
        # Verify template has basic content
        with open(template_path, 'r') as f:
            content = f.read()
            self.assertIn('System Administration', content, 
                         "Template should contain 'System Administration' title")
            self.assertIn('system-health-cards', content, 
                         "Template should contain system health cards")
            self.assertIn('performanceChart', content, 
                         "Template should contain performance chart")

if __name__ == '__main__':
    unittest.main()