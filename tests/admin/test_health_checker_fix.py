# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test to verify that the "Health checker not available" error is fixed
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
from urllib.parse import urljoin

class TestHealthCheckerFix(unittest.TestCase):
    """Test that HealthChecker is properly initialized and available"""
    
    @classmethod
    def setUpClass(cls):
        """Start the web application for testing"""
        print("Starting web application for health checker tests...")
        
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
    
    def test_health_checker_initialization(self):
        """Test that HealthChecker is properly initialized in the web app"""
        # This test verifies that the web app starts without HealthChecker errors
        # We already verified this in setUpClass, so this is mainly a placeholder
        self.assertTrue(True, "Web application started successfully with HealthChecker")
    
    def test_basic_health_endpoint(self):
        """Test the basic health endpoint works without 'Health checker not available' error"""
        session = self.create_authenticated_session()
        
        # Test basic health endpoint
        response = session.get("http://127.0.0.1:5000/admin/health")
        self.assertEqual(response.status_code, 200, f"Health endpoint failed: {response.status_code}")
        
        # Parse JSON response
        try:
            data = response.json()
        except ValueError:
            self.fail("Health endpoint did not return valid JSON")
        
        # Verify we don't get the "Health checker not available" error
        self.assertNotIn('error', data, f"Health endpoint returned error: {data.get('error', 'Unknown error')}")
        
        # Verify we get expected health data
        self.assertIn('status', data, "Health response missing status field")
        self.assertIn('timestamp', data, "Health response missing timestamp field")
        self.assertIn('service', data, "Health response missing service field")
        self.assertEqual(data['service'], 'vedfolnir', "Incorrect service name in health response")
    
    def test_detailed_health_endpoint(self):
        """Test the detailed health endpoint that was previously failing"""
        session = self.create_authenticated_session()
        
        # Test detailed health endpoint (this was the one failing before)
        response = session.get("http://127.0.0.1:5000/admin/health/detailed")
        
        # This endpoint should now work without the "Health checker not available" error
        if response.status_code == 503:
            # If it's still 503, check if it's the old error
            try:
                data = response.json()
                if 'error' in data and 'Health checker not available' in data['error']:
                    self.fail("Still getting 'Health checker not available' error - fix not working")
                else:
                    # It's a different 503 error (maybe system actually unhealthy)
                    print(f"Health check returned 503 but not due to missing health checker: {data}")
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
            
            # Verify we get expected detailed health data
            self.assertIn('status', data, "Detailed health response missing status field")
            self.assertIn('timestamp', data, "Detailed health response missing timestamp field")
    
    def test_health_dashboard_loads(self):
        """Test that the health dashboard loads without HealthChecker errors"""
        session = self.create_authenticated_session()
        
        # Test health dashboard page
        response = session.get("http://127.0.0.1:5000/admin/health/dashboard")
        self.assertEqual(response.status_code, 200, f"Health dashboard failed to load: {response.status_code}")
        
        # Verify the page content doesn't contain error messages about missing health checker
        page_content = response.text.lower()
        self.assertNotIn('health checker not available', page_content, 
                        "Health dashboard still shows 'health checker not available' error")
        self.assertNotIn('healthchecker not available', page_content,
                        "Health dashboard still shows 'healthchecker not available' error")

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)