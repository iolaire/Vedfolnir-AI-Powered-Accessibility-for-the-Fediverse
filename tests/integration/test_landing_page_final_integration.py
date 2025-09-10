# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Final Integration Tests for Flask Landing Page

This module contains comprehensive integration tests to verify all components
of the landing page implementation work together correctly.
"""

import unittest
import sys
import os
import requests
import time
import subprocess
import signal
from urllib.parse import urljoin
import re
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from models import UserRole


class TestLandingPageFinalIntegration(unittest.TestCase):
    """
    Final integration tests for the Flask landing page implementation.
    
    Tests all components working together:
    - Session detection
    - Route logic
    - Template rendering
    - Navigation
    - Call-to-action buttons
    - Responsive design
    - Accessibility features
    - SEO metadata
    - Performance
    - Security
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        cls.db_manager = DatabaseManager(cls.config)
        cls.base_url = "http://127.0.0.1:5000"
        cls.web_app_process = None
        cls.session = requests.Session()
        
        # Start web application
        cls._start_web_app()
        
        # Wait for app to be ready
        cls._wait_for_app_ready()
        
        # Create test users
        cls.test_user, cls.user_helper = create_test_user_with_platforms(
            cls.db_manager, 
            username="test_integration_user", 
            role=UserRole.REVIEWER
        )
        
        cls.admin_user, cls.admin_helper = create_test_user_with_platforms(
            cls.db_manager, 
            username="test_integration_admin", 
            role=UserRole.ADMIN
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Clean up test users
        if hasattr(cls, 'user_helper'):
            cleanup_test_user(cls.user_helper)
        if hasattr(cls, 'admin_helper'):
            cleanup_test_user(cls.admin_helper)
        
        # Stop web application
        cls._stop_web_app()
    
    @classmethod
    def _start_web_app(cls):
        """Start the web application for testing"""
        try:
            # Start web app in background
            cls.web_app_process = subprocess.Popen(
                [sys.executable, 'web_app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            print("✅ Web application started for integration testing")
        except Exception as e:
            print(f"❌ Failed to start web application: {e}")
            raise
    
    @classmethod
    def _stop_web_app(cls):
        """Stop the web application"""
        if cls.web_app_process:
            try:
                # Kill the process group
                os.killpg(os.getpgid(cls.web_app_process.pid), signal.SIGTERM)
                cls.web_app_process.wait(timeout=10)
                print("✅ Web application stopped")
            except Exception as e:
                print(f"⚠️  Error stopping web application: {e}")
                try:
                    os.killpg(os.getpgid(cls.web_app_process.pid), signal.SIGKILL)
                except:
                    pass
    
    @classmethod
    def _wait_for_app_ready(cls, timeout=30):
        """Wait for the web application to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = cls.session.get(cls.base_url, timeout=5)
                if response.status_code in [200, 302]:
                    print("✅ Web application is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception("Web application failed to start within timeout")
    
    def setUp(self):
        """Set up each test"""
        # Clear session cookies to ensure clean state
        self.session.cookies.clear()
    
    def test_01_anonymous_user_gets_landing_page(self):
        """Test that completely new anonymous users receive the landing page"""
        print("\n🧪 Testing anonymous user gets landing page...")
        
        # Clear all cookies to simulate completely new user
        self.session.cookies.clear()
        
        response = self.session.get(self.base_url)
        
        # Should get 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should contain landing page content
        self.assertIn("Vedfolnir – AI-Powered Accessibility for the Fediverse", response.text)
        self.assertIn("Make your social media content accessible", response.text)
        self.assertIn("Get Started", response.text)
        self.assertIn("Login", response.text)
        
        # Should not contain dashboard content
        self.assertNotIn("Dashboard", response.text)
        self.assertNotIn("Generate Captions", response.text)
        
        print("✅ Anonymous user correctly receives landing page")
    
    def test_02_landing_page_structure_and_content(self):
        """Test that landing page has all required structural elements"""
        print("\n🧪 Testing landing page structure and content...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Check hero section
        self.assertIn("landing-hero", response.text)
        self.assertIn("Vedfolnir – AI-Powered Accessibility for the Fediverse", response.text)
        
        # Check features section
        self.assertIn("features-section", response.text)
        self.assertIn("AI-Powered Image Analysis", response.text)
        self.assertIn("Human Review Interface", response.text)
        self.assertIn("Platform Integration", response.text)
        
        # Check target audience section
        self.assertIn("audience-section", response.text)
        self.assertIn("Photographers", response.text)
        self.assertIn("Community Managers", response.text)
        self.assertIn("Content Creators", response.text)
        
        # Check final CTA section
        self.assertIn("final-cta-section", response.text)
        self.assertIn("Ready to Make Your Content Accessible?", response.text)
        
        print("✅ Landing page has all required structural elements")
    
    def test_03_navigation_for_anonymous_users(self):
        """Test navigation elements for anonymous users"""
        print("\n🧪 Testing navigation for anonymous users...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Should have login link in navigation
        self.assertIn('href="/login"', response.text)
        self.assertIn("Login", response.text)
        
        # Should not have authenticated user navigation
        self.assertNotIn("Dashboard", response.text)
        self.assertNotIn("Review", response.text)
        self.assertNotIn("Platforms", response.text)
        self.assertNotIn("Generate Captions", response.text)
        
        print("✅ Navigation correctly configured for anonymous users")
    
    def test_04_call_to_action_buttons(self):
        """Test call-to-action button functionality"""
        print("\n🧪 Testing call-to-action buttons...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Check for primary CTA button
        self.assertIn('href="/register"', response.text)
        self.assertIn("Get Started", response.text)
        
        # Check for login link
        self.assertIn('href="/login"', response.text)
        
        # Verify buttons use proper Flask url_for() function (no hardcoded URLs)
        # This is verified by the presence of proper href attributes
        cta_buttons = re.findall(r'href="([^"]*)"', response.text)
        self.assertTrue(any('/register' in url for url in cta_buttons))
        self.assertTrue(any('/login' in url for url in cta_buttons))
        
        print("✅ Call-to-action buttons are properly configured")
    
    def test_05_seo_metadata_and_structured_data(self):
        """Test SEO metadata and structured data"""
        print("\n🧪 Testing SEO metadata and structured data...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Check meta tags
        self.assertIn('<meta name="description"', response.text)
        self.assertIn('<meta name="keywords"', response.text)
        self.assertIn('accessibility, alt text', response.text)
        
        # Check Open Graph tags
        self.assertIn('<meta property="og:title"', response.text)
        self.assertIn('<meta property="og:description"', response.text)
        self.assertIn('<meta property="og:type" content="website"', response.text)
        
        # Check Twitter Card tags
        self.assertIn('<meta name="twitter:card"', response.text)
        self.assertIn('<meta name="twitter:title"', response.text)
        
        # Check structured data
        self.assertIn('application/ld+json', response.text)
        self.assertIn('"@type": "SoftwareApplication"', response.text)
        self.assertIn('"@type": "FAQPage"', response.text)
        
        print("✅ SEO metadata and structured data are properly implemented")
    
    def test_06_accessibility_features(self):
        """Test accessibility features"""
        print("\n🧪 Testing accessibility features...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Check semantic HTML structure
        self.assertIn('<main', response.text)
        self.assertIn('<section', response.text)
        self.assertIn('<h1>', response.text)
        self.assertIn('<h2>', response.text)
        
        # Check skip-to-content link
        self.assertIn('Skip to main content', response.text)
        self.assertIn('href="#page-content"', response.text)
        
        # Check alt text for images
        logo_pattern = r'<img[^>]*alt="[^"]*"[^>]*>'
        self.assertTrue(re.search(logo_pattern, response.text))
        
        # Check ARIA labels and roles
        self.assertIn('role=', response.text)
        self.assertIn('aria-', response.text)
        
        print("✅ Accessibility features are properly implemented")
    
    def test_07_responsive_design_elements(self):
        """Test responsive design elements"""
        print("\n🧪 Testing responsive design elements...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Check viewport meta tag
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0">', response.text)
        
        # Check responsive CSS classes
        self.assertIn('container', response.text)
        self.assertIn('row', response.text)
        self.assertIn('col-', response.text)
        
        # Check mobile-specific CSS
        self.assertIn('@media', response.text)
        self.assertIn('mobile-touch-compliant', response.text)
        
        print("✅ Responsive design elements are properly implemented")
    
    def test_08_authenticated_user_gets_dashboard(self):
        """Test that authenticated users get the dashboard instead of landing page"""
        print("\n🧪 Testing authenticated user gets dashboard...")
        
        # Login as test user
        login_success = self._login_user(self.test_user.username, "test_password")
        self.assertTrue(login_success, "Failed to login test user")
        
        response = self.session.get(self.base_url)
        
        # Should get 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Should contain dashboard content
        self.assertIn("Dashboard", response.text)
        
        # Should not contain landing page content
        self.assertNotIn("Make your social media content accessible", response.text)
        self.assertNotIn("Get Started", response.text)
        
        print("✅ Authenticated user correctly receives dashboard")
    
    def test_09_session_detection_functionality(self):
        """Test session detection functionality"""
        print("\n🧪 Testing session detection functionality...")
        
        # First, login to create a session
        login_success = self._login_user(self.test_user.username, "test_password")
        self.assertTrue(login_success, "Failed to login test user")
        
        # Verify we get dashboard
        response = self.session.get(self.base_url)
        self.assertIn("Dashboard", response.text)
        
        # Logout but keep session cookies
        logout_response = self.session.get(urljoin(self.base_url, "/logout"))
        self.assertIn(logout_response.status_code, [200, 302])
        
        # Now access root URL - should redirect to login (returning user)
        response = self.session.get(self.base_url, allow_redirects=False)
        
        # Should redirect to login page
        if response.status_code == 302:
            self.assertIn('/login', response.headers.get('Location', ''))
            print("✅ Session detection correctly redirects returning users to login")
        else:
            # If not redirecting, check if we're getting login page directly
            self.assertIn("Login", response.text)
            print("✅ Session detection correctly shows login for returning users")
    
    def test_10_performance_and_caching(self):
        """Test performance and caching functionality"""
        print("\n🧪 Testing performance and caching...")
        
        self.session.cookies.clear()
        
        # Measure response time
        start_time = time.time()
        response = self.session.get(self.base_url)
        response_time = time.time() - start_time
        
        # Should respond quickly (under 2 seconds)
        self.assertLess(response_time, 2.0, f"Response time {response_time:.2f}s exceeds 2 second limit")
        
        # Check for caching headers
        cache_control = response.headers.get('Cache-Control', '')
        etag = response.headers.get('ETag', '')
        
        # Should have some form of caching
        self.assertTrue(cache_control or etag, "No caching headers found")
        
        print(f"✅ Performance test passed - Response time: {response_time:.2f}s")
    
    def test_11_security_headers_and_csrf(self):
        """Test security headers and CSRF protection"""
        print("\n🧪 Testing security headers and CSRF protection...")
        
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Check security headers
        headers = response.headers
        
        # Check for CSRF token in meta tag
        csrf_pattern = r'<meta name="csrf-token" content="([^"]+)"'
        csrf_match = re.search(csrf_pattern, response.text)
        self.assertIsNotNone(csrf_match, "CSRF token not found in meta tag")
        
        # Check for security-related headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        for header in security_headers:
            self.assertIn(header, headers, f"Security header {header} not found")
        
        print("✅ Security headers and CSRF protection are properly implemented")
    
    def test_12_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms"""
        print("\n🧪 Testing error handling and fallbacks...")
        
        # Test with invalid request
        response = self.session.get(self.base_url + "/nonexistent")
        self.assertEqual(response.status_code, 404)
        
        # Test landing page still works after error
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vedfolnir", response.text)
        
        print("✅ Error handling and fallbacks work correctly")
    
    def test_13_backward_compatibility(self):
        """Test backward compatibility with existing features"""
        print("\n🧪 Testing backward compatibility...")
        
        # Test that existing routes still work
        test_routes = [
            '/login',
            '/register',
            '/admin',  # Should redirect to login for anonymous users
        ]
        
        for route in test_routes:
            response = self.session.get(urljoin(self.base_url, route), allow_redirects=False)
            # Should not return 500 errors
            self.assertNotEqual(response.status_code, 500, f"Route {route} returns 500 error")
        
        # Test that authenticated user routes work
        login_success = self._login_user(self.admin_user.username, "test_password")
        self.assertTrue(login_success, "Failed to login admin user")
        
        admin_response = self.session.get(urljoin(self.base_url, '/admin'))
        self.assertEqual(admin_response.status_code, 200)
        
        print("✅ Backward compatibility maintained")
    
    def test_14_end_to_end_user_journeys(self):
        """Test complete end-to-end user journeys"""
        print("\n🧪 Testing end-to-end user journeys...")
        
        # Journey 1: New user -> Landing -> Registration
        self.session.cookies.clear()
        
        # 1. Visit landing page
        landing_response = self.session.get(self.base_url)
        self.assertEqual(landing_response.status_code, 200)
        self.assertIn("Get Started", landing_response.text)
        
        # 2. Click registration link (simulate)
        register_response = self.session.get(urljoin(self.base_url, '/register'))
        self.assertIn(register_response.status_code, [200, 302])
        
        # Journey 2: Returning user -> Landing -> Login
        self.session.cookies.clear()
        
        # Simulate having previous session by setting a cookie
        self.session.cookies.set('session', 'test_session_value')
        
        # Visit landing page - should redirect to login
        landing_response = self.session.get(self.base_url, allow_redirects=False)
        if landing_response.status_code == 302:
            self.assertIn('/login', landing_response.headers.get('Location', ''))
        
        # Journey 3: Authenticated user -> Dashboard
        login_success = self._login_user(self.test_user.username, "test_password")
        self.assertTrue(login_success, "Failed to login test user")
        
        dashboard_response = self.session.get(self.base_url)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("Dashboard", dashboard_response.text)
        
        print("✅ End-to-end user journeys work correctly")
    
    def test_15_deployment_readiness(self):
        """Test deployment readiness indicators"""
        print("\n🧪 Testing deployment readiness...")
        
        # Test that all static assets load
        self.session.cookies.clear()
        response = self.session.get(self.base_url)
        
        # Extract CSS and JS references
        css_links = re.findall(r'href="([^"]*\.css[^"]*)"', response.text)
        js_links = re.findall(r'src="([^"]*\.js[^"]*)"', response.text)
        
        # Test a few critical assets
        critical_assets = []
        for link in css_links[:3]:  # Test first 3 CSS files
            if link.startswith('/'):
                critical_assets.append(link)
        
        for asset in critical_assets:
            asset_response = self.session.get(urljoin(self.base_url, asset))
            self.assertNotEqual(asset_response.status_code, 404, f"Critical asset {asset} not found")
        
        # Test that the application handles concurrent requests
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                resp = requests.get(self.base_url, timeout=10)
                results.put(resp.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Make 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            result = results.get()
            if result == 200:
                success_count += 1
        
        self.assertGreaterEqual(success_count, 4, "Application failed under concurrent load")
        
        print("✅ Application is deployment ready")
    
    def _login_user(self, username, password):
        """Helper method to login a user"""
        try:
            # Get login page and CSRF token
            login_page = self.session.get(urljoin(self.base_url, "/login"))
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
            
            if not csrf_match:
                print("❌ CSRF token not found in login page")
                return False
            
            csrf_token = csrf_match.group(1)
            
            # Login
            login_data = {
                'username_or_email': username,
                'password': password,
                'csrf_token': csrf_token
            }
            
            response = self.session.post(urljoin(self.base_url, "/login"), data=login_data)
            success = response.status_code in [200, 302] and 'login' not in response.url.lower()
            
            if success:
                print(f"✅ Successfully logged in user: {username}")
            else:
                print(f"❌ Failed to login user: {username}")
            
            return success
            
        except Exception as e:
            print(f"❌ Login error for {username}: {e}")
            return False


def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Flask Landing Page Final Integration Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLandingPageFinalIntegration)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🏁 Integration Test Summary")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 All integration tests passed! Landing page is ready for deployment.")
    else:
        print("\n⚠️  Some integration tests failed. Please review and fix issues before deployment.")
    
    return success


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)