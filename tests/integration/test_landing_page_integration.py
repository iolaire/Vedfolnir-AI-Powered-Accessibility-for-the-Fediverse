# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Flask Landing Page functionality

This module tests the complete user journey flows for the landing page:
- Landing page to registration flow
- Landing page to login flow  
- Authenticated user bypass
- Logout behavior
- Session state transitions

Requirements tested: 1.1, 1.2, 1.3, 6.1, 6.2
"""

import unittest
import requests
import re
import time
import logging
from urllib.parse import urljoin, urlparse
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# Set up logging for test debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLandingPageIntegration(unittest.TestCase):
    """Integration tests for landing page user journeys"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with configuration"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        cls.base_url = "http://127.0.0.1:5000"
        cls.test_users_to_cleanup = []
        
        # Test if web app is running
        try:
            response = requests.get(cls.base_url, timeout=5)
            if response.status_code not in [200, 302, 403]:
                raise Exception(f"Web app not accessible: {response.status_code}")
        except Exception as e:
            raise unittest.SkipTest(f"Web application not running at {cls.base_url}: {e}")
    
    def setUp(self):
        """Set up each test"""
        self.session = requests.Session()
        self.test_user = None
        self.user_helper = None
    
    def tearDown(self):
        """Clean up after each test"""
        # Close session
        if hasattr(self, 'session'):
            self.session.close()
        
        # Clean up test user
        if self.user_helper:
            try:
                cleanup_test_user(self.user_helper)
            except Exception as e:
                logger.warning(f"Failed to cleanup test user: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test class"""
        # Clean up any remaining test users
        for user_helper in cls.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass
    
    def _get_csrf_token(self, url):
        """Extract CSRF token from a page"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            # Try meta tag first
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
            if csrf_match:
                return csrf_match.group(1)
            
            # Try input field
            csrf_match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', response.text)
            if csrf_match:
                return csrf_match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Failed to get CSRF token from {url}: {e}")
            return None
    
    def _create_test_user(self, username="testuser", email="test@example.com", 
                         password="testpass123", role=UserRole.VIEWER, verified=True):
        """Create a test user for integration tests"""
        try:
            self.test_user, self.user_helper = create_test_user_with_platforms(
                self.db_manager,
                username=username,
                role=role
            )
            
            # Update user with custom email and password if needed
            if self.test_user and (email != "test@example.com" or password != "testpass123"):
                with self.db_manager.get_session() as db_session:
                    user = db_session.query(User).get(self.test_user.id)
                    if user:
                        if email != "test@example.com":
                            user.email = email
                        if password != "testpass123":
                            user.set_password(password)
                        db_session.commit()
            
            # Set email as verified if requested
            if verified and self.test_user:
                with self.db_manager.get_session() as db_session:
                    user = db_session.query(User).get(self.test_user.id)
                    if user:
                        user.email_verified = True
                        user.email_verification_token = None
                        db_session.commit()
            
            return self.test_user
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            return None
    
    def _login_user(self, username, password):
        """Login a user and return success status"""
        try:
            # Get login page and CSRF token
            login_url = urljoin(self.base_url, "/login")
            csrf_token = self._get_csrf_token(login_url)
            
            if not csrf_token:
                logger.error("Could not get CSRF token for login")
                return False
            
            # Submit login form
            login_data = {
                'username_or_email': username,
                'password': password,
                'csrf_token': csrf_token
            }
            
            response = self.session.post(login_url, data=login_data, allow_redirects=False)
            
            # Check for successful login (redirect)
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                # Successful login should redirect away from login page
                return 'login' not in location.lower()
            
            return False
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def _logout_user(self):
        """Logout current user"""
        try:
            logout_url = urljoin(self.base_url, "/logout")
            # Don't follow redirects to avoid redirect loops
            response = self.session.get(logout_url, allow_redirects=False)
            # Logout should redirect (302) or return success (200)
            return response.status_code in [200, 302]
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    def _clear_session_cookies(self):
        """Clear session cookies to simulate new user"""
        # Clear all cookies
        self.session.cookies.clear()
    
    def _set_previous_session_cookie(self):
        """Set a cookie to simulate a returning user"""
        # Set a cookie that would indicate previous session
        self.session.cookies.set('vedfolnir_returning_user', 'true', domain='127.0.0.1')
        # Also set a session cookie to simulate Flask session
        self.session.cookies.set('session', 'fake_session_data_12345', domain='127.0.0.1')
    
    def test_new_anonymous_user_gets_landing_page(self):
        """
        Test that completely new anonymous users see the landing page
        Requirements: 1.1 - Anonymous visitor sees landing page
        """
        logger.info("Testing: New anonymous user gets landing page")
        
        # Clear all cookies to simulate completely new user
        self._clear_session_cookies()
        
        # Visit root URL
        response = self.session.get(self.base_url)
        
        # Should get 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should contain landing page content
        self.assertIn("Vedfolnir", response.text)
        self.assertIn("AI-Powered Accessibility", response.text)
        self.assertIn("Fediverse", response.text)
        
        # Should contain call-to-action elements
        self.assertIn("Get Started", response.text.replace("Create Account", "Get Started"))
        self.assertIn("Login", response.text)
        
        # Should contain key landing page sections
        self.assertIn("features", response.text.lower())
        self.assertIn("accessibility", response.text.lower())
        
        logger.info("✓ New anonymous user correctly receives landing page")
    
    def test_authenticated_user_bypasses_landing_page(self):
        """
        Test that authenticated users bypass landing page and see dashboard
        Requirements: 1.2 - Authenticated user sees dashboard
        """
        logger.info("Testing: Authenticated user bypasses landing page")
        
        # Create and login test user
        user = self._create_test_user("authtest", "authtest@example.com")
        self.assertIsNotNone(user, "Failed to create test user")
        
        login_success = self._login_user("authtest", "test_password_123")
        self.assertTrue(login_success, "Failed to login test user")
        
        # Visit root URL while authenticated
        response = self.session.get(self.base_url)
        
        # Should get 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should NOT contain landing page content
        self.assertNotIn("Get Started", response.text)
        self.assertNotIn("Create Account", response.text)
        
        # Should contain dashboard content
        self.assertIn("Dashboard", response.text)
        
        # Should contain authenticated user elements
        self.assertIn("Logout", response.text)
        
        logger.info("✓ Authenticated user correctly bypasses landing page")
    
    def test_returning_user_redirected_to_login(self):
        """
        Test that users with previous session cookies are redirected to login
        Requirements: 1.3 - Anonymous user with previous session redirects to login
        """
        logger.info("Testing: Returning user redirected to login")
        
        # Clear cookies first
        self._clear_session_cookies()
        
        # Set cookies to simulate returning user
        self._set_previous_session_cookie()
        
        # Visit root URL
        response = self.session.get(self.base_url, allow_redirects=False)
        
        # Should get redirect (302)
        self.assertEqual(response.status_code, 302)
        
        # Should redirect to login page
        location = response.headers.get('Location', '')
        self.assertIn('login', location.lower())
        
        # Follow redirect to verify we end up at login page
        response = self.session.get(self.base_url, allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", response.text)
        self.assertIn("password", response.text.lower())
        
        logger.info("✓ Returning user correctly redirected to login")
    
    def test_landing_to_registration_flow(self):
        """
        Test complete user journey from landing page to registration
        Requirements: 6.1, 6.2 - CTA buttons navigate to registration
        """
        logger.info("Testing: Landing to registration flow")
        
        # Start as new anonymous user
        self._clear_session_cookies()
        
        # Visit landing page
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
        # Look for registration link/button
        # The landing page should have a link to registration
        self.assertIn("register", response.text.lower())
        
        # Visit registration page
        register_url = urljoin(self.base_url, "/register")
        response = self.session.get(register_url)
        
        # Should successfully load registration page
        self.assertEqual(response.status_code, 200)
        self.assertIn("register", response.text.lower())
        self.assertIn("username", response.text.lower())
        self.assertIn("email", response.text.lower())
        self.assertIn("password", response.text.lower())
        
        logger.info("✓ Landing to registration flow works correctly")
    
    def test_landing_to_login_flow(self):
        """
        Test user journey from landing page to login
        Requirements: 6.1, 6.2 - Login link navigates to login page
        """
        logger.info("Testing: Landing to login flow")
        
        # Start as new anonymous user
        self._clear_session_cookies()
        
        # Visit landing page
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
        # Should contain login link
        self.assertIn("Login", response.text)
        
        # Visit login page
        login_url = urljoin(self.base_url, "/login")
        response = self.session.get(login_url)
        
        # Should successfully load login page
        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", response.text)
        self.assertIn("password", response.text.lower())
        self.assertIn("username", response.text.lower())
        
        logger.info("✓ Landing to login flow works correctly")
    
    def test_logout_returns_to_appropriate_page(self):
        """
        Test that logout behavior returns user to appropriate page
        Requirements: Session state transitions
        """
        logger.info("Testing: Logout returns to appropriate page")
        
        # Create and login test user
        user = self._create_test_user("logouttest", "logouttest@example.com")
        self.assertIsNotNone(user, "Failed to create test user")
        
        login_success = self._login_user("logouttest", "test_password_123")
        self.assertTrue(login_success, "Failed to login test user")
        
        # Verify we're logged in (dashboard should be accessible)
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard", response.text)
        
        # Logout
        logout_success = self._logout_user()
        self.assertTrue(logout_success, "Failed to logout user")
        
        # Visit root URL after logout
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
        # Should see landing page (not dashboard)
        self.assertNotIn("Dashboard", response.text)
        self.assertIn("Vedfolnir", response.text)
        self.assertIn("AI-Powered Accessibility", response.text)
        
        logger.info("✓ Logout correctly returns to landing page")
    
    def test_session_state_transitions(self):
        """
        Test various session state transitions
        Requirements: 1.1, 1.2, 1.3 - All session state handling
        """
        logger.info("Testing: Session state transitions")
        
        # Test 1: New user -> Landing page
        self._clear_session_cookies()
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("AI-Powered Accessibility", response.text)
        logger.info("✓ New user -> Landing page")
        
        # Test 2: Set returning user cookie -> Redirect to login
        self._set_previous_session_cookie()
        response = self.session.get(self.base_url, allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        location = response.headers.get('Location', '')
        self.assertIn('login', location.lower())
        logger.info("✓ Returning user -> Redirect to login")
        
        # Test 3: Login -> Dashboard
        user = self._create_test_user("statetest", "statetest@example.com")
        self.assertIsNotNone(user, "Failed to create test user")
        
        login_success = self._login_user("statetest", "test_password_123")
        self.assertTrue(login_success, "Failed to login test user")
        
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard", response.text)
        logger.info("✓ Authenticated user -> Dashboard")
        
        # Test 4: Logout -> Landing page (with returning user cookie)
        self._logout_user()
        response = self.session.get(self.base_url, allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # After logout, should either see landing page or be redirected to login
        # depending on session detection logic
        self.assertTrue(
            "AI-Powered Accessibility" in response.text or "Login" in response.text,
            "After logout, should see either landing page or login page"
        )
        logger.info("✓ Logout -> Appropriate page")
        
        logger.info("✓ All session state transitions work correctly")
    
    def test_landing_page_accessibility_elements(self):
        """
        Test that landing page contains required accessibility elements
        Requirements: Accessibility compliance
        """
        logger.info("Testing: Landing page accessibility elements")
        
        # Start as new anonymous user
        self._clear_session_cookies()
        
        # Visit landing page
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
        # Check for semantic HTML elements
        self.assertIn("<main", response.text.lower())
        self.assertIn("<h1", response.text.lower())
        self.assertIn("<h2", response.text.lower())
        
        # Check for skip-to-content link
        self.assertIn("skip", response.text.lower())
        
        # Check for proper meta tags
        self.assertIn('meta name="description"', response.text)
        self.assertIn('meta property="og:', response.text)
        
        # Check for structured data
        self.assertIn('application/ld+json', response.text)
        
        logger.info("✓ Landing page contains required accessibility elements")
    
    def test_landing_page_cta_buttons_functionality(self):
        """
        Test that CTA buttons have correct URLs and functionality
        Requirements: 6.1, 6.2 - CTA button functionality
        """
        logger.info("Testing: Landing page CTA buttons functionality")
        
        # Start as new anonymous user
        self._clear_session_cookies()
        
        # Visit landing page
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
        # Check for registration CTA
        # Look for links to registration page
        self.assertTrue(
            "/register" in response.text or "register" in response.text.lower(),
            "Landing page should contain registration CTA"
        )
        
        # Check for login link
        self.assertTrue(
            "/login" in response.text or "Login" in response.text,
            "Landing page should contain login link"
        )
        
        # Test that registration URL is accessible
        register_url = urljoin(self.base_url, "/register")
        response = self.session.get(register_url)
        self.assertEqual(response.status_code, 200)
        
        # Test that login URL is accessible
        login_url = urljoin(self.base_url, "/login")
        response = self.session.get(login_url)
        self.assertEqual(response.status_code, 200)
        
        logger.info("✓ Landing page CTA buttons work correctly")
    
    def test_landing_page_performance(self):
        """
        Test landing page performance characteristics
        Requirements: Performance optimization
        """
        logger.info("Testing: Landing page performance")
        
        # Start as new anonymous user
        self._clear_session_cookies()
        
        # Measure response time
        start_time = time.time()
        response = self.session.get(self.base_url)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should respond quickly (under 2 seconds as per design)
        self.assertLess(response_time, 2.0, f"Landing page took {response_time:.2f}s, should be under 2s")
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should have reasonable content length (not empty, not too large)
        content_length = len(response.text)
        self.assertGreater(content_length, 1000, "Landing page content seems too small")
        self.assertLess(content_length, 500000, "Landing page content seems too large")
        
        logger.info(f"✓ Landing page performance: {response_time:.2f}s, {content_length} bytes")
    
    def test_error_handling_and_fallbacks(self):
        """
        Test error handling and fallback behavior
        Requirements: Error handling and graceful degradation
        """
        logger.info("Testing: Error handling and fallbacks")
        
        # Test with invalid session data
        self._clear_session_cookies()
        
        # Set malformed session cookie
        self.session.cookies.set('session', 'invalid_session_data', domain='127.0.0.1')
        
        # Should still work (fallback to landing page)
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        
        # Should contain landing page content (fallback behavior)
        self.assertIn("Vedfolnir", response.text)
        
        logger.info("✓ Error handling and fallbacks work correctly")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)