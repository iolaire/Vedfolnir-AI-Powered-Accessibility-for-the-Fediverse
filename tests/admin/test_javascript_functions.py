# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test JavaScript functions in admin system maintenance page
"""

import unittest
import requests
import time
import sys
import os
import re
from urllib.parse import urljoin
import getpass

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestJavaScriptFunctions(unittest.TestCase):
    """Test JavaScript functions in admin system maintenance page"""
    
    def setUp(self):
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        
    def test_admin_system_maintenance_javascript_functions(self):
        """Test that JavaScript functions are properly defined in the admin system maintenance page"""
        
        # First, authenticate as admin
        success = self._authenticate_as_admin()
        if not success:
            self.skipTest("Could not authenticate as admin")
        
        # Access the admin system maintenance page
        response = self.session.get(urljoin(self.base_url, "/admin/system-maintenance"))
        
        # Check that the page loads successfully
        self.assertEqual(response.status_code, 200)
        
        # Check that the required JavaScript functions are defined in the page
        page_content = response.text
        
        # Check for function definitions
        self.assertIn('function viewSystemLogs()', page_content, "viewSystemLogs function should be defined")
        self.assertIn('function exportSystemReport()', page_content, "exportSystemReport function should be defined")
        self.assertIn('function checkSystemHealth()', page_content, "checkSystemHealth function should be defined")
        self.assertIn('function refreshMetrics()', page_content, "refreshMetrics function should be defined")
        self.assertIn('function initializeWebSocketHandlers()', page_content, "initializeWebSocketHandlers function should be defined")
        
        # Check for WebSocket client inclusion
        self.assertIn('websocket-client.js', page_content, "WebSocket client script should be included")
        
        # Check for proper script loading order (functions should be defined after WebSocket client)
        websocket_pos = page_content.find('websocket-client.js')
        functions_pos = page_content.find('function viewSystemLogs()')
        if websocket_pos != -1 and functions_pos != -1:
            self.assertLess(websocket_pos, functions_pos, "WebSocket client should load before page-specific functions")
        
        # Check for WebSocket status indicator
        self.assertIn('websocket-status', page_content, "WebSocket status indicator should be present")
        
        print("✅ All required JavaScript functions are properly defined")
        print("✅ WebSocket client integration is properly configured")
        print("✅ Script loading order is correct (using extra_js block)")
        
    def test_javascript_function_onclick_handlers(self):
        """Test that onclick handlers reference existing functions"""
        
        # Authenticate as admin
        success = self._authenticate_as_admin()
        if not success:
            self.skipTest("Could not authenticate as admin")
        
        # Get the admin system maintenance page
        response = self.session.get(urljoin(self.base_url, "/admin/system-maintenance"))
        self.assertEqual(response.status_code, 200)
        
        page_content = response.text
        
        # Find all onclick handlers and verify the functions exist
        onclick_patterns = [
            (r'onclick="viewSystemLogs\(\)"', 'function viewSystemLogs()'),
            (r'onclick="exportSystemReport\(\)"', 'function exportSystemReport()'),
            (r'onclick="checkSystemHealth\(\)"', 'function checkSystemHealth()'),
            (r'onclick="refreshMetrics\(\)"', 'function refreshMetrics()')
        ]
        
        for onclick_pattern, function_pattern in onclick_patterns:
            # Check if onclick handler exists
            onclick_match = re.search(onclick_pattern, page_content)
            if onclick_match:
                # Verify the corresponding function is defined
                function_match = re.search(function_pattern, page_content)
                self.assertTrue(function_match, f"Function {function_pattern} should be defined for onclick handler {onclick_pattern}")
                print(f"✅ {function_pattern} is properly defined for its onclick handler")
        
    def _authenticate_as_admin(self):
        """Authenticate as admin user"""
        try:
            # Get login page and CSRF token
            login_page = self.session.get(urljoin(self.base_url, "/login"))
            if login_page.status_code != 200:
                print(f"❌ Failed to get login page: {login_page.status_code}")
                return False
            
            # Extract CSRF token
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
            if not csrf_match:
                print("❌ Could not find CSRF token in login page")
                return False
            
            csrf_token = csrf_match.group(1)
            
            # Get admin password
            password = getpass.getpass("Enter admin password for JavaScript function test: ")
            
            # Login
            login_data = {
                'username_or_email': 'admin',
                'password': password,
                'csrf_token': csrf_token
            }
            
            login_response = self.session.post(urljoin(self.base_url, "/login"), data=login_data)
            
            # Check if login was successful
            if login_response.status_code == 302 or (login_response.status_code == 200 and 'login' not in login_response.url.lower()):
                print("✅ Successfully authenticated as admin")
                return True
            else:
                print("❌ Admin authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

def main():
    """Run JavaScript function tests"""
    print("=== JavaScript Function Test ===")
    print("This test verifies that all JavaScript functions are properly defined")
    print("and that onclick handlers reference existing functions.")
    print()
    
    # Check if web app is running
    try:
        response = requests.get("http://127.0.0.1:5000/", timeout=5)
        if response.status_code not in [200, 302]:  # 302 for redirect to login
            print("❌ Web application is not running or not healthy")
            print("Please start the web application with: python web_app.py")
            return False
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to web application at http://127.0.0.1:5000")
        print("Please start the web application with: python web_app.py")
        return False
    
    print("✅ Web application is running")
    print()
    
    # Run tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)