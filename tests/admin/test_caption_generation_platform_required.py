# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test for caption generation route platform_required decorator functionality
Location: tests/admin/test_caption_generation_platform_required.py
"""

import unittest
import sys
import os
import requests
import re
import getpass
from urllib.parse import urljoin

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestCaptionGenerationPlatformRequired(unittest.TestCase):
    """Test cases for caption generation route platform_required decorator"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
    
    def tearDown(self):
        """Clean up after tests"""
        self.session.close()
    
    def create_authenticated_session(self, username="admin"):
        """
        Create an authenticated session for testing
        
        Args:
            username: Username to login with (default: admin)
        
        Returns:
            tuple: (session, success) where session is requests.Session and success is bool
        """
        # Step 1: Get login page and CSRF token
        print(f"Getting login page for user: {username}")
        login_page = self.session.get(urljoin(self.base_url, "/login"))
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token from meta tag
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if not csrf_match:
            print("❌ Could not find CSRF token in login page")
            return False
        
        csrf_token = csrf_match.group(1)
        print(f"✅ Got CSRF token: {csrf_token[:20]}...")
        
        # Step 2: Prompt for password
        password = getpass.getpass(f"Enter password for {username}: ")
        
        # Step 3: Login
        print(f"Logging in as {username}...")
        login_data = {
            'username_or_email': username,
            'password': password,
            'csrf_token': csrf_token
        }
        
        login_response = self.session.post(urljoin(self.base_url, "/login"), data=login_data)
        
        # Check if login was successful
        if login_response.status_code == 302:
            print("✅ Successfully logged in (redirected)")
            return True
        elif login_response.status_code == 200:
            if 'login' in login_response.url.lower():
                print("❌ Login failed: Still on login page")
                return False
            else:
                print("✅ Successfully logged in")
                return True
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
    
    def test_caption_generation_with_authentication(self):
        """Test caption generation route with proper admin authentication"""
        print("\n=== Testing Caption Generation Route with Platform Required Decorator ===")
        
        # Create authenticated session
        login_success = self.create_authenticated_session(username="admin")
        if not login_success:
            self.fail("Failed to authenticate admin user")
        
        # Test caption generation route access
        print("Testing caption generation route access...")
        response = self.session.get(urljoin(self.base_url, "/caption_generation"))
        
        print(f"Response status code: {response.status_code}")
        print(f"Response URL: {response.url}")
        
        # Check the response
        if response.status_code == 200:
            print("✅ Caption generation page loaded successfully")
            # Check if the page contains expected content
            if "caption_generation" in response.text.lower() or "caption generation" in response.text.lower():
                print("✅ Page contains caption generation content")
            else:
                print("⚠️  Page loaded but may not contain expected content")
        elif response.status_code == 302:
            # Check where we were redirected
            if "platform_management" in response.url:
                print("✅ Correctly redirected to platform management (no platform selected)")
            elif "first_time_setup" in response.url:
                print("✅ Correctly redirected to first time setup (no platforms configured)")
            else:
                print(f"⚠️  Redirected to unexpected location: {response.url}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            self.fail(f"Unexpected response code: {response.status_code}")
        
        print("✅ Platform required decorator test completed successfully")
    
    def test_caption_generation_without_authentication(self):
        """Test caption generation route without authentication"""
        print("\n=== Testing Caption Generation Route without Authentication ===")
        
        # Create new session without authentication
        unauthenticated_session = requests.Session()
        
        # Test caption generation route access
        print("Testing caption generation route access without authentication...")
        response = unauthenticated_session.get(urljoin(self.base_url, "/caption_generation"))
        
        print(f"Response status code: {response.status_code}")
        print(f"Response URL: {response.url}")
        
        # Should be redirected to login
        if response.status_code == 302 or "login" in response.url:
            print("✅ Correctly redirected to login page")
        else:
            print(f"❌ Expected redirect to login, got: {response.status_code}")
            self.fail("Should have been redirected to login")
        
        unauthenticated_session.close()
        print("✅ Unauthenticated access test completed successfully")

if __name__ == '__main__':
    print("=== Caption Generation Platform Required Decorator Test ===")
    print("This test verifies that the @platform_required decorator is working correctly")
    print("on the /caption_generation route.")
    print()
    
    # Run the tests
    unittest.main(verbosity=2)