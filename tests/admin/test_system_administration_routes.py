# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test System Administration Routes

This module tests the system administration routes implementation
to ensure they work correctly with the consolidated monitoring framework.
"""

import unittest
import sys
import os
import requests
import getpass
import re
from urllib.parse import urljoin

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole

class TestSystemAdministrationRoutes(unittest.TestCase):
    """Test system administration routes functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.base_url = "http://127.0.0.1:5000"
        cls.session = requests.Session()
        
        # Test database connectivity
        try:
            config = Config()
            cls.db_manager = DatabaseManager(config)
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def test_system_administration_route_requires_authentication(self):
        """Test that system administration route requires authentication"""
        print("\n=== Testing System Administration Route Authentication ===")
        
        # Test unauthenticated access
        response = self.session.get(urljoin(self.base_url, "/admin/system"), allow_redirects=False)
        
        # Should redirect to login or return 401/403
        if response.status_code == 302:
            print(f"✅ Unauthenticated access properly redirected to login (status: {response.status_code})")
        elif response.status_code in [401, 403]:
            print(f"✅ Unauthenticated access properly blocked (status: {response.status_code})")
        else:
            print(f"❌ Unexpected response for unauthenticated access (status: {response.status_code})")
            print(f"Response content: {response.text[:200]}")
        
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_system_administration_route_with_admin_user(self):
        """Test system administration route with admin user"""
        print("\n=== Testing System Administration Route with Admin User ===")
        
        # Create authenticated session
        session, success = self._create_authenticated_session(username="admin")
        if not success:
            self.skipTest("Could not authenticate admin user")
        
        # Test system administration dashboard
        response = session.get(urljoin(self.base_url, "/admin/system"))
        
        if response.status_code == 200:
            print("✅ System administration dashboard loaded successfully")
            
            # Check for expected content
            content = response.text
            self.assertIn("System Administration", content)
            self.assertIn("System Health Overview", content)
            self.assertIn("Performance Metrics", content)
            self.assertIn("Resource Usage", content)
            print("✅ Dashboard contains expected content sections")
            
        else:
            print(f"❌ System administration dashboard failed to load (status: {response.status_code})")
            print(f"Response: {response.text[:500]}")
            self.fail(f"System administration dashboard returned status {response.status_code}")
    
    def test_system_health_api_endpoint(self):
        """Test system health API endpoint"""
        print("\n=== Testing System Health API Endpoint ===")
        
        # Create authenticated session
        session, success = self._create_authenticated_session(username="admin")
        if not success:
            self.skipTest("Could not authenticate admin user")
        
        # Test system health API
        response = session.get(urljoin(self.base_url, "/admin/system/api/health"))
        
        if response.status_code == 200:
            print("✅ System health API endpoint accessible")
            
            # Check JSON response
            try:
                data = response.json()
                expected_fields = ['status', 'cpu_usage', 'memory_usage', 'database_status', 'timestamp']
                
                for field in expected_fields:
                    self.assertIn(field, data)
                
                print("✅ System health API returns expected data structure")
                print(f"   System status: {data.get('status')}")
                print(f"   CPU usage: {data.get('cpu_usage')}%")
                print(f"   Memory usage: {data.get('memory_usage')}%")
                
            except ValueError as e:
                self.fail(f"System health API returned invalid JSON: {e}")
                
        else:
            print(f"❌ System health API failed (status: {response.status_code})")
            self.fail(f"System health API returned status {response.status_code}")
    
    def test_system_performance_api_endpoint(self):
        """Test system performance API endpoint"""
        print("\n=== Testing System Performance API Endpoint ===")
        
        # Create authenticated session
        session, success = self._create_authenticated_session(username="admin")
        if not success:
            self.skipTest("Could not authenticate admin user")
        
        # Test system performance API
        response = session.get(urljoin(self.base_url, "/admin/system/api/performance"))
        
        if response.status_code == 200:
            print("✅ System performance API endpoint accessible")
            
            # Check JSON response
            try:
                data = response.json()
                expected_fields = ['job_completion_rate', 'avg_processing_time', 'success_rate', 'error_rate']
                
                for field in expected_fields:
                    self.assertIn(field, data)
                
                print("✅ System performance API returns expected data structure")
                print(f"   Success rate: {data.get('success_rate')}%")
                print(f"   Error rate: {data.get('error_rate')}%")
                print(f"   Avg processing time: {data.get('avg_processing_time')}s")
                
            except ValueError as e:
                self.fail(f"System performance API returned invalid JSON: {e}")
                
        else:
            print(f"❌ System performance API failed (status: {response.status_code})")
            self.fail(f"System performance API returned status {response.status_code}")
    
    def test_system_resources_api_endpoint(self):
        """Test system resources API endpoint"""
        print("\n=== Testing System Resources API Endpoint ===")
        
        # Create authenticated session
        session, success = self._create_authenticated_session(username="admin")
        if not success:
            self.skipTest("Could not authenticate admin user")
        
        # Test system resources API
        response = session.get(urljoin(self.base_url, "/admin/system/api/resources"))
        
        if response.status_code == 200:
            print("✅ System resources API endpoint accessible")
            
            # Check JSON response
            try:
                data = response.json()
                expected_fields = ['cpu_percent', 'memory_percent', 'disk_percent', 'database_connections']
                
                for field in expected_fields:
                    self.assertIn(field, data)
                
                print("✅ System resources API returns expected data structure")
                print(f"   CPU: {data.get('cpu_percent')}%")
                print(f"   Memory: {data.get('memory_percent')}%")
                print(f"   Disk: {data.get('disk_percent')}%")
                print(f"   DB connections: {data.get('database_connections')}")
                
            except ValueError as e:
                self.fail(f"System resources API returned invalid JSON: {e}")
                
        else:
            print(f"❌ System resources API failed (status: {response.status_code})")
            self.fail(f"System resources API returned status {response.status_code}")
    
    def test_consolidated_monitoring_framework_integration(self):
        """Test that the routes properly use consolidated monitoring framework"""
        print("\n=== Testing Consolidated Monitoring Framework Integration ===")
        
        # Test that the SystemMonitor can be imported and initialized
        try:
            from app.services.monitoring.system.system_monitor import SystemMonitor
            from app.services.monitoring.performance.monitors.performance_monitor import get_performance_monitor
            
            # Initialize components
            config = Config()
            db_manager = DatabaseManager(config)
            system_monitor = SystemMonitor(db_manager)
            performance_monitor = get_performance_monitor()
            
            print("✅ Consolidated monitoring framework components imported successfully")
            
            # Test system health
            health = system_monitor.get_system_health()
            self.assertIsNotNone(health)
            self.assertIn(health.status, ['healthy', 'warning', 'critical'])
            print(f"✅ System health check successful (status: {health.status})")
            
            # Test performance metrics
            metrics = system_monitor.get_performance_metrics()
            self.assertIsNotNone(metrics)
            self.assertGreaterEqual(metrics.success_rate, 0)
            print(f"✅ Performance metrics check successful (success rate: {metrics.success_rate}%)")
            
            # Test resource usage
            resources = system_monitor.check_resource_usage()
            self.assertIsNotNone(resources)
            self.assertGreaterEqual(resources.cpu_percent, 0)
            print(f"✅ Resource usage check successful (CPU: {resources.cpu_percent}%)")
            
        except ImportError as e:
            self.fail(f"Failed to import consolidated monitoring framework: {e}")
        except Exception as e:
            self.fail(f"Error testing consolidated monitoring framework: {e}")
    
    def _create_authenticated_session(self, username="admin"):
        """Create authenticated session for testing"""
        session = requests.Session()
        
        try:
            # Get login page and CSRF token
            login_page = session.get(urljoin(self.base_url, "/login"))
            if login_page.status_code != 200:
                print(f"❌ Could not access login page (status: {login_page.status_code})")
                return session, False
            
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
            if not csrf_match:
                print("❌ Could not find CSRF token on login page")
                return session, False
            
            csrf_token = csrf_match.group(1)
            
            # Use admin password directly for testing
            password = "admin123"
            
            # Login
            login_data = {
                'username_or_email': username,
                'password': password,
                'csrf_token': csrf_token
            }
            
            response = session.post(urljoin(self.base_url, "/login"), data=login_data)
            
            # Debug the response
            print(f"Login response status: {response.status_code}")
            print(f"Login response URL: {response.url}")
            print(f"Login response headers: {dict(response.headers)}")
            
            # Check if we're redirected to dashboard or admin area
            success = (response.status_code in [200, 302] and 
                      ('dashboard' in response.url.lower() or 
                       'admin' in response.url.lower() or
                       'login' not in response.url.lower()))
            
            if success:
                print(f"✅ Successfully authenticated as {username}")
            else:
                print(f"❌ Authentication failed for {username}")
                print(f"Response content: {response.text[:300]}")
            
            return session, success
            
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return session, False

def main():
    """Main test execution"""
    print("=== System Administration Routes Test ===")
    
    # Check if web app is running
    try:
        response = requests.get("http://127.0.0.1:5000", timeout=5)
        print("✅ Web application is running")
    except requests.exceptions.RequestException:
        print("❌ Web application is not running. Please start it with: python web_app.py")
        return False
    
    # Run tests
    unittest.main(verbosity=2, exit=False)
    
    print("=== Test Complete ===")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)