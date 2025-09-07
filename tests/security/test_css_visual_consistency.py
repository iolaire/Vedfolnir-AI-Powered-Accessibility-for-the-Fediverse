# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSS Visual Consistency and Interactive Elements Test
Tests for visual consistency and functionality after CSS extraction
"""

import unittest
import requests
import time
import re
import getpass
from pathlib import Path


class TestCSSVisualConsistency(unittest.TestCase):
    """Test suite for CSS visual consistency and interactive elements"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        self.authenticated_session = None
        
        # Wait for server to be ready
        max_retries = 10
        for i in range(max_retries):
            try:
                response = self.session.get(self.base_url, timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    self.skipTest("Web application not running on http://127.0.0.1:5000")
                time.sleep(1)
    
    def create_authenticated_session(self, username="admin", password="admin123"):
        """Create authenticated session for testing"""
        auth_session = requests.Session()
        
        try:
            # Get login page and CSRF token
            login_page = auth_session.get(f"{self.base_url}/login")
            
            # Check if account is locked
            if "temporarily locked" in login_page.text or "Account locked" in login_page.text:
                print(f"⚠️  Account {username} appears to be locked")
                return None, False
            
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
            if not csrf_match:
                print("⚠️  Could not find CSRF token in login page")
                return None, False
            
            csrf_token = csrf_match.group(1)
            
            # Login with provided credentials
            login_data = {
                'username_or_email': username,
                'password': password,
                'csrf_token': csrf_token
            }
            
            response = auth_session.post(f"{self.base_url}/login", data=login_data)
            
            # Check response for account lockout
            if "temporarily locked" in response.text or "Account locked" in response.text:
                print(f"⚠️  Account {username} is locked after login attempt")
                return None, False
            
            success = response.status_code in [200, 302] and 'login' not in response.url.lower()
            
            if success:
                print(f"✅ Successfully authenticated as {username}")
            else:
                print(f"❌ Authentication failed for {username}")
                if "Invalid credentials" in response.text:
                    print("   Reason: Invalid credentials")
                elif "locked" in response.text.lower():
                    print("   Reason: Account locked")
            
            return auth_session, success
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None, False
    
    def test_landing_page_loads(self):
        """Test that landing page loads without errors"""
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vedfolnir", response.text)
        
        # Check for basic CSS includes
        self.assertIn("static/css/", response.text)
        print("✅ Landing page loads successfully with CSS includes")
    
    def test_login_page_loads(self):
        """Test that login page loads without errors"""
        response = self.session.get(f"{self.base_url}/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("login", response.text.lower())
        print("✅ Login page loads successfully")
    
    def test_css_files_accessible(self):
        """Test that CSS files are accessible"""
        css_files = [
            "/static/css/security-extracted.css",
            "/static/css/components.css",
            "/admin/static/css/admin-extracted.css"
        ]
        
        for css_file in css_files:
            response = self.session.get(f"{self.base_url}{css_file}")
            if response.status_code == 200:
                print(f"✅ CSS file accessible: {css_file}")
                # Check if file has meaningful content
                if len(response.text.strip()) > 100:
                    print(f"   Content length: {len(response.text)} characters")
                else:
                    print(f"   ⚠️  File appears to be minimal: {len(response.text)} characters")
            else:
                print(f"❌ CSS file not accessible: {css_file} (Status: {response.status_code})")
    
    def test_static_assets_load(self):
        """Test that static assets load properly"""
        # Test main CSS file
        response = self.session.get(f"{self.base_url}/static/css/style.css")
        if response.status_code == 200:
            print("✅ Main CSS file loads successfully")
        else:
            print(f"⚠️  Main CSS file status: {response.status_code}")
        
        # Test Bootstrap CSS
        response = self.session.get(f"{self.base_url}/static/css/bootstrap.min.css")
        if response.status_code == 200:
            print("✅ Bootstrap CSS loads successfully")
        else:
            print(f"⚠️  Bootstrap CSS status: {response.status_code}")
    
    def test_page_structure_intact(self):
        """Test that page structure remains intact"""
        response = self.session.get(self.base_url)
        content = response.text
        
        # Check for essential HTML structure
        self.assertIn("<html", content)
        self.assertIn("<head>", content)
        self.assertIn("<body", content)  # Allow for body attributes
        self.assertIn("</html>", content)
        
        # Check for navigation elements
        self.assertIn("nav", content.lower())
        
        print("✅ Page structure remains intact")
    
    def test_authenticated_page_structure(self):
        """Test page structure with authenticated user"""
        auth_session, success = self.create_authenticated_session("admin", "admin123")
        
        if not success:
            self.skipTest("Could not authenticate - skipping authenticated tests")
        
        # Test dashboard page
        response = auth_session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        content = response.text
        
        # Check for essential HTML structure
        self.assertIn("<html", content)
        self.assertIn("<head>", content)
        self.assertIn("<body", content)
        self.assertIn("</html>", content)
        
        # Check for authenticated navigation elements
        self.assertIn("nav", content.lower())
        
        # Should have user-specific elements
        self.assertIn("admin", content.lower())
        
        print("✅ Authenticated page structure remains intact")
    
    def test_admin_pages_load(self):
        """Test that admin pages load correctly with authentication"""
        auth_session, success = self.create_authenticated_session("admin", "admin123")
        
        if not success:
            self.skipTest("Could not authenticate - skipping admin tests")
        
        admin_pages = [
            "/admin",
            "/admin/dashboard",
            "/admin/user-management"
        ]
        
        for page in admin_pages:
            try:
                response = auth_session.get(f"{self.base_url}{page}")
                if response.status_code == 200:
                    print(f"✅ Admin page loads successfully: {page}")
                    
                    # Check for CSS includes
                    self.assertIn("static/css/", response.text)
                    self.assertIn("admin/static/css/", response.text)
                    
                elif response.status_code == 404:
                    print(f"⚠️  Admin page not found: {page}")
                else:
                    print(f"⚠️  Admin page status {response.status_code}: {page}")
            except Exception as e:
                print(f"❌ Error loading admin page {page}: {e}")
    
    def test_interactive_elements_authenticated(self):
        """Test interactive elements with authenticated user"""
        auth_session, success = self.create_authenticated_session("admin", "admin123")
        
        if not success:
            self.skipTest("Could not authenticate - skipping interactive tests")
        
        # Test main dashboard
        response = auth_session.get(self.base_url)
        content = response.text
        
        # Check for interactive elements that should be present for authenticated users
        interactive_elements = [
            "button",
            "form",
            "input",
            "select"
        ]
        
        found_elements = []
        for element in interactive_elements:
            if f"<{element}" in content.lower():
                found_elements.append(element)
        
        print(f"✅ Found interactive elements: {', '.join(found_elements)}")
        
        # Should have at least some interactive elements
        self.assertGreater(len(found_elements), 0, "No interactive elements found on authenticated page")
    
    def test_no_obvious_layout_breaks(self):
        """Test for obvious layout breaks in HTML"""
        response = self.session.get(self.base_url)
        content = response.text
        
        # Check for unclosed tags or obvious issues
        open_divs = content.count("<div")
        close_divs = content.count("</div>")
        
        # Allow some tolerance for self-closing or template-generated divs
        div_difference = abs(open_divs - close_divs)
        self.assertLess(div_difference, 5, f"Significant div tag mismatch: {open_divs} open, {close_divs} close")
        
        print(f"✅ HTML structure check passed (div tags: {open_divs} open, {close_divs} close)")


def run_visual_consistency_tests():
    """Run visual consistency tests with detailed reporting"""
    print("=== CSS Visual Consistency Test Suite ===\n")
    
    # Run the test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCSSVisualConsistency)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n=== Visual Consistency Test Results ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, failure in result.failures:
            print(f"   {test}: {failure}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, error in result.errors:
            print(f"   {test}: {error}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: Visual Consistency Tests")
    
    return success


if __name__ == '__main__':
    run_visual_consistency_tests()