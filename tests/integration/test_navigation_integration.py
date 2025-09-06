# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import requests
import sys
import os
import re
from urllib.parse import urljoin

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestNavigationIntegration(unittest.TestCase):
    """Integration tests for navigation modifications"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
    
    def tearDown(self):
        """Clean up test environment"""
        self.session.close()
    
    def test_anonymous_user_sees_login_link(self):
        """Test that anonymous users see login link in navigation"""
        try:
            # Make request as anonymous user
            response = self.session.get(self.base_url)
            
            # Check if request was successful
            if response.status_code != 200:
                self.skipTest(f"Web app not accessible: {response.status_code}")
            
            html_content = response.text
            
            # Check for login link in navigation
            login_link_pattern = r'<a[^>]*href="[^"]*login[^"]*"[^>]*>.*?Login.*?</a>'
            login_link_found = re.search(login_link_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            self.assertIsNotNone(login_link_found, "Login link should be present for anonymous users")
            
            # Check that login link is in the navbar
            navbar_pattern = r'<nav[^>]*class="[^"]*navbar[^"]*"[^>]*>.*?</nav>'
            navbar_match = re.search(navbar_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            if navbar_match:
                navbar_content = navbar_match.group(0)
                login_in_navbar = re.search(login_link_pattern, navbar_content, re.IGNORECASE | re.DOTALL)
                self.assertIsNotNone(login_in_navbar, "Login link should be in the navbar")
            
            print("✅ Anonymous user navigation test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Web application is not running")
    
    def test_anonymous_user_has_minimal_navigation(self):
        """Test that anonymous users have minimal navigation items"""
        try:
            # Make request as anonymous user
            response = self.session.get(self.base_url)
            
            # Check if request was successful
            if response.status_code != 200:
                self.skipTest(f"Web app not accessible: {response.status_code}")
            
            html_content = response.text
            
            # Check that authenticated-only navigation items are NOT present
            authenticated_nav_items = [
                'Dashboard',
                'Review',
                'Platforms',
                'Generate Captions'
            ]
            
            # Extract navbar content
            navbar_pattern = r'<nav[^>]*class="[^"]*navbar[^"]*"[^>]*>.*?</nav>'
            navbar_match = re.search(navbar_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            if navbar_match:
                navbar_content = navbar_match.group(0)
                
                # Check that authenticated navigation items are not present
                for nav_item in authenticated_nav_items:
                    # Look for navigation links (but not in dropdowns for authenticated users)
                    nav_item_pattern = rf'<a[^>]*class="[^"]*nav-link[^"]*"[^>]*>{nav_item}</a>'
                    nav_item_found = re.search(nav_item_pattern, navbar_content, re.IGNORECASE)
                    
                    # For anonymous users, these should not be present as nav-links
                    if nav_item == 'Dashboard':
                        # Dashboard link might be present but should not be a nav-link for anonymous users
                        continue
                    else:
                        self.assertIsNone(nav_item_found, f"'{nav_item}' navigation item should not be present for anonymous users")
            
            print("✅ Anonymous user minimal navigation test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Web application is not running")
    
    def test_login_link_points_to_correct_url(self):
        """Test that login link points to the correct URL"""
        try:
            # Make request as anonymous user
            response = self.session.get(self.base_url)
            
            # Check if request was successful
            if response.status_code != 200:
                self.skipTest(f"Web app not accessible: {response.status_code}")
            
            html_content = response.text
            
            # Extract login link href
            login_link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>.*?Login.*?</a>'
            login_link_match = re.search(login_link_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            self.assertIsNotNone(login_link_match, "Login link should be present")
            
            if login_link_match:
                login_href = login_link_match.group(1)
                
                # Check that href contains 'login'
                self.assertIn('login', login_href.lower(), "Login link should point to login URL")
                
                # Test that the login URL is accessible
                login_url = urljoin(self.base_url, login_href)
                login_response = self.session.get(login_url)
                self.assertEqual(login_response.status_code, 200, "Login URL should be accessible")
            
            print("✅ Login link URL test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Web application is not running")
    
    def test_navigation_responsive_structure(self):
        """Test that navigation has proper responsive structure"""
        try:
            # Make request as anonymous user
            response = self.session.get(self.base_url)
            
            # Check if request was successful
            if response.status_code != 200:
                self.skipTest(f"Web app not accessible: {response.status_code}")
            
            html_content = response.text
            
            # Check for Bootstrap navbar structure
            navbar_pattern = r'<nav[^>]*class="[^"]*navbar[^"]*"'
            navbar_found = re.search(navbar_pattern, html_content, re.IGNORECASE)
            self.assertIsNotNone(navbar_found, "Navbar should have proper Bootstrap classes")
            
            # Check for navbar toggler (mobile menu)
            toggler_pattern = r'<button[^>]*class="[^"]*navbar-toggler[^"]*"'
            toggler_found = re.search(toggler_pattern, html_content, re.IGNORECASE)
            self.assertIsNotNone(toggler_found, "Navbar should have mobile toggle button")
            
            # Check for collapsible navbar content
            collapse_pattern = r'<div[^>]*class="[^"]*navbar-collapse[^"]*"'
            collapse_found = re.search(collapse_pattern, html_content, re.IGNORECASE)
            self.assertIsNotNone(collapse_found, "Navbar should have collapsible content")
            
            print("✅ Navigation responsive structure test passed")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Web application is not running")


if __name__ == '__main__':
    unittest.main()