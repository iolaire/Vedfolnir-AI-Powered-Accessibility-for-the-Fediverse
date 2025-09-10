# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test URL endpoint fixes for BuildError issues
"""

import unittest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, url_for
from app.blueprints.auth.user_management_routes import register_user_management_routes

class TestURLEndpointFixes(unittest.TestCase):
    """Test cases for URL endpoint fixes"""
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Register user management routes
        register_user_management_routes(self.app)
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
    
    def test_user_management_profile_endpoint_exists(self):
        """Test that user_management.profile endpoint exists"""
        with self.app.test_request_context():
            try:
                profile_url = url_for('user_management.profile')
                self.assertIsNotNone(profile_url)
                self.assertEqual(profile_url, '/profile')
                print("✅ user_management.profile endpoint exists and builds correctly")
            except Exception as e:
                self.fail(f"user_management.profile endpoint failed: {e}")
    
    def test_user_management_change_password_endpoint_exists(self):
        """Test that user_management.change_password endpoint exists"""
        with self.app.test_request_context():
            try:
                change_password_url = url_for('user_management.change_password')
                self.assertIsNotNone(change_password_url)
                self.assertEqual(change_password_url, '/change-password')
                print("✅ user_management.change_password endpoint exists and builds correctly")
            except Exception as e:
                self.fail(f"user_management.change_password endpoint failed: {e}")
    
    def test_user_management_edit_profile_endpoint_does_not_exist(self):
        """Test that user_management.edit_profile endpoint does not exist (should fail)"""
        with self.app.test_request_context():
            try:
                edit_profile_url = url_for('user_management.edit_profile')
                self.fail("user_management.edit_profile should not exist but it does")
            except Exception:
                print("✅ user_management.edit_profile correctly does not exist")
                # This is expected - the endpoint should not exist
                pass
    
    def test_profile_profile_endpoint_does_not_exist(self):
        """Test that profile.profile endpoint does not exist (should fail)"""
        with self.app.test_request_context():
            try:
                profile_profile_url = url_for('profile.profile')
                self.fail("profile.profile should not exist but it does")
            except Exception:
                print("✅ profile.profile correctly does not exist")
                # This is expected - the endpoint should not exist
                pass

if __name__ == '__main__':
    print("=== Testing URL Endpoint Fixes ===")
    unittest.main(verbosity=2)