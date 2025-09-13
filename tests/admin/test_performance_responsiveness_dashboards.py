# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Performance and Responsiveness Dashboards

Tests the new admin performance and responsiveness dashboard functionality.
"""

import unittest
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from models import UserRole

class TestPerformanceResponsivenessDashboards(unittest.TestCase):
    """Test performance and responsiveness dashboard functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test admin user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, 
            username="test_admin_perf", 
            role=UserRole.ADMIN
        )
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_user(self.user_helper)
    
    def test_performance_dashboard_route_exists(self):
        """Test that performance dashboard route is registered"""
        try:
            from app.blueprints.admin.performance_dashboard import register_routes
            from flask import Blueprint
            
            # Create a test blueprint
            test_bp = Blueprint('test_admin', __name__)
            
            # Register routes should not raise an exception
            register_routes(test_bp)
            
            # Check that routes were added
            self.assertTrue(len(test_bp.deferred_functions) > 0)
            
        except Exception as e:
            self.fail(f"Performance dashboard route registration failed: {e}")
    
    def test_responsiveness_dashboard_route_exists(self):
        """Test that responsiveness dashboard route is registered"""
        try:
            from app.blueprints.admin.responsiveness_dashboard import register_routes
            from flask import Blueprint
            
            # Create a test blueprint
            test_bp = Blueprint('test_admin', __name__)
            
            # Register routes should not raise an exception
            register_routes(test_bp)
            
            # Check that routes were added
            self.assertTrue(len(test_bp.deferred_functions) > 0)
            
        except Exception as e:
            self.fail(f"Responsiveness dashboard route registration failed: {e}")
    
    def test_performance_metrics_function(self):
        """Test performance metrics helper function"""
        try:
            from app.blueprints.admin.performance_dashboard import _get_performance_metrics
            
            # Mock current_app for the test
            class MockApp:
                def __init__(self):
                    self.logger = self
                
                def error(self, msg):
                    pass
            
            import app.blueprints.admin.performance_dashboard as perf_module
            original_current_app = getattr(perf_module, 'current_app', None)
            perf_module.current_app = MockApp()
            
            try:
                metrics = _get_performance_metrics()
                
                # Check that metrics structure is correct
                self.assertIn('timestamp', metrics)
                self.assertIn('system', metrics)
                self.assertIn('application', metrics)
                self.assertIn('database', metrics)
                
                # Check system metrics
                system_metrics = metrics['system']
                self.assertIn('cpu_percent', system_metrics)
                self.assertIn('memory_percent', system_metrics)
                
            finally:
                # Restore original current_app
                if original_current_app:
                    perf_module.current_app = original_current_app
                
        except Exception as e:
            self.fail(f"Performance metrics function failed: {e}")
    
    def test_responsiveness_overview_function(self):
        """Test responsiveness overview helper function"""
        try:
            from app.blueprints.admin.responsiveness_dashboard import _get_responsiveness_overview
            
            # Mock current_app for the test
            class MockApp:
                def __init__(self):
                    self.logger = self
                
                def error(self, msg):
                    pass
            
            import app.blueprints.admin.responsiveness_dashboard as resp_module
            original_current_app = getattr(resp_module, 'current_app', None)
            resp_module.current_app = MockApp()
            
            try:
                overview = _get_responsiveness_overview()
                
                # Check that overview structure is correct
                self.assertIn('timestamp', overview)
                self.assertIn('overall_status', overview)
                self.assertIn('responsive', overview)
                self.assertIn('metrics', overview)
                
                # Check metrics structure
                metrics = overview['metrics']
                self.assertIn('memory_usage_percent', metrics)
                self.assertIn('cpu_usage_percent', metrics)
                
            finally:
                # Restore original current_app
                if original_current_app:
                    resp_module.current_app = original_current_app
                
        except Exception as e:
            self.fail(f"Responsiveness overview function failed: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=2)