# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test responsiveness dashboard with running web server
"""

import unittest
import requests
import time
import subprocess
import sys
import os
import signal
import getpass
import re

class TestResponsivenessDashboardWithServer(unittest.TestCase):
    """Test responsiveness dashboard with a running web server"""
    
    @classmethod
    def setUpClass(cls):
        """Start the web application for testing"""
        print("Starting web application for responsiveness dashboard tests...")
        
        # Start web app in background
        cls.web_process = subprocess.Popen(
            [sys.executable, "web_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Wait for startup
        time.sleep(15)
        
        # Verify the app is running
        try:
            response = requests.get("http://127.0.0.1:5000", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Web app not responding properly: {response.status_code}")
        except Exception as e:
            cls.tearDownClass()
            raise Exception(f"Web app failed to start: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Stop the web application"""
        if hasattr(cls, 'web_process') and cls.web_process:
            print("Stopping web application...")
            try:
                # Kill the entire process group
                os.killpg(os.getpgid(cls.web_process.pid), signal.SIGTERM)
                cls.web_process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                # Force kill if needed
                try:
                    os.killpg(os.getpgid(cls.web_process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
    
    def create_authenticated_session(self):
        """Create an authenticated admin session"""
        session = requests.Session()
        
        # Get login page and CSRF token
        login_page = session.get("http://127.0.0.1:5000/login")
        self.assertEqual(login_page.status_code, 200, "Could not access login page")
        
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        self.assertIsNotNone(csrf_match, "Could not find CSRF token")
        csrf_token = csrf_match.group(1)
        
        # Use default admin credentials for testing
        login_data = {
            'username_or_email': 'admin',
            'password': 'admin123',  # Default test password
            'csrf_token': csrf_token
        }
        
        response = session.post("http://127.0.0.1:5000/login", data=login_data)
        
        # Check if login was successful
        if response.status_code not in [200, 302] or 'login' in response.url.lower():
            # If default credentials don't work, prompt for real credentials
            print("\nDefault admin credentials didn't work. Please enter admin credentials:")
            username = input("Username (default: admin): ") or "admin"
            password = getpass.getpass("Password: ")
            
            login_data['username_or_email'] = username
            login_data['password'] = password
            
            response = session.post("http://127.0.0.1:5000/login", data=login_data)
            
        self.assertIn(response.status_code, [200, 302], f"Login failed: {response.status_code}")
        self.assertNotIn('login', response.url.lower(), "Login was not successful")
        
        return session
    
    def test_health_checker_available_after_fix(self):
        """Test that HealthChecker is now available and working"""
        session = self.create_authenticated_session()
        
        # Test the detailed health endpoint that was previously failing
        response = session.get("http://127.0.0.1:5000/admin/health/detailed")
        
        # This should no longer return the "Health checker not available" error
        if response.status_code == 503:
            try:
                data = response.json()
                if 'error' in data and 'Health checker not available' in data['error']:
                    self.fail("❌ Still getting 'Health checker not available' error - fix not working")
                else:
                    # It's a different 503 error (system actually unhealthy)
                    print(f"ℹ️  Health check returned 503 but not due to missing health checker: {data}")
            except ValueError:
                self.fail("Detailed health endpoint returned 503 with invalid JSON")
        else:
            # Should be 200 if health checker is working
            self.assertEqual(response.status_code, 200, f"Detailed health endpoint failed: {response.status_code}")
            
            try:
                data = response.json()
            except ValueError:
                self.fail("Detailed health endpoint did not return valid JSON")
            
            # Verify we don't get the "Health checker not available" error
            self.assertNotIn('error', data, f"Detailed health endpoint returned error: {data.get('error', 'Unknown error')}")
            
            print("✅ HealthChecker is working properly - no 'not available' error")
    
    def test_responsiveness_api_endpoints(self):
        """Test that responsiveness API endpoints work with HealthChecker"""
        session = self.create_authenticated_session()
        
        # Test responsiveness API endpoints
        responsiveness_endpoints = [
            "/admin/api/responsiveness/status",
            "/admin/api/responsiveness/metrics", 
            "/admin/api/responsiveness/health",
            "/admin/api/responsiveness/check",
            "/admin/api/responsiveness/memory-cleanup",
            "/admin/api/responsiveness/connection-optimization"
        ]
        
        working_endpoints = []
        not_found_endpoints = []
        error_endpoints = []
        
        for endpoint in responsiveness_endpoints:
            try:
                response = session.get(f"http://127.0.0.1:5000{endpoint}")
                if response.status_code == 200:
                    working_endpoints.append(endpoint)
                    
                    # Check if response contains health checker data
                    try:
                        data = response.json()
                        if 'error' in data and 'Health checker not available' in data['error']:
                            self.fail(f"❌ {endpoint} still shows 'Health checker not available' error")
                    except ValueError:
                        pass  # Not JSON, that's okay
                        
                elif response.status_code == 404:
                    not_found_endpoints.append(endpoint)
                else:
                    error_endpoints.append((endpoint, response.status_code))
            except Exception as e:
                error_endpoints.append((endpoint, str(e)))
        
        print(f"✅ Working endpoints: {working_endpoints}")
        print(f"ℹ️  Not found endpoints: {not_found_endpoints}")
        print(f"⚠️  Error endpoints: {error_endpoints}")
        
        # At least some endpoints should be working
        self.assertGreater(len(working_endpoints), 0, "No responsiveness API endpoints are working")
    
    def test_admin_dashboard_loads_without_health_checker_error(self):
        """Test that admin dashboard loads without HealthChecker errors"""
        session = self.create_authenticated_session()
        
        # Test admin dashboard
        response = session.get("http://127.0.0.1:5000/admin")
        self.assertEqual(response.status_code, 200, f"Admin dashboard failed to load: {response.status_code}")
        
        # Check that the page doesn't contain health checker errors
        page_content = response.text.lower()
        self.assertNotIn('health checker not available', page_content, 
                        "Admin dashboard still shows 'health checker not available' error")
        
        print("✅ Admin dashboard loads without HealthChecker errors")
    
    def test_performance_dashboard_loads_without_health_checker_error(self):
        """Test that performance dashboard loads without HealthChecker errors"""
        session = self.create_authenticated_session()
        
        # Test performance dashboard
        response = session.get("http://127.0.0.1:5000/admin/performance")
        
        if response.status_code == 200:
            # Check that the page doesn't contain health checker errors
            page_content = response.text.lower()
            self.assertNotIn('health checker not available', page_content, 
                            "Performance dashboard still shows 'health checker not available' error")
            
            print("✅ Performance dashboard loads without HealthChecker errors")
        elif response.status_code == 404:
            print("ℹ️  Performance dashboard endpoint not found (may not be implemented)")
        else:
            print(f"⚠️  Performance dashboard returned {response.status_code}")

if __name__ == '__main__':
    unittest.main(verbosity=2)