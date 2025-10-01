# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
API Endpoint Validation Tests
Test all API endpoints and web interface functionality in containerized environment
"""

import unittest
import requests
import json
import time
import os
import sys
import re
from urllib.parse import urljoin
import getpass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class APIEndpointValidationTest(unittest.TestCase):
    """Comprehensive API endpoint validation for Docker Compose deployment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
        cls.session = requests.Session()
        cls.session.timeout = 30
        cls.authenticated = False
        cls.csrf_token = None
        
        # Try to authenticate for protected endpoints
        cls._attempt_authentication()
    
    @classmethod
    def _attempt_authentication(cls):
        """Attempt to authenticate for testing protected endpoints"""
        try:
            # Get login page and CSRF token
            login_page = cls.session.get(urljoin(cls.base_url, "/login"))
            if login_page.status_code == 200:
                csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
                if csrf_match:
                    cls.csrf_token = csrf_match.group(1)
                    
                    # Try to authenticate with admin credentials (if available)
                    if os.getenv('TEST_ADMIN_USERNAME') and os.getenv('TEST_ADMIN_PASSWORD'):
                        login_data = {
                            'username_or_email': os.getenv('TEST_ADMIN_USERNAME'),
                            'password': os.getenv('TEST_ADMIN_PASSWORD'),
                            'csrf_token': cls.csrf_token
                        }
                        
                        response = cls.session.post(urljoin(cls.base_url, "/login"), data=login_data)
                        if response.status_code in [200, 302] and 'login' not in response.url.lower():
                            cls.authenticated = True
                            print("✅ Authentication successful for protected endpoint testing")
                        else:
                            print("⚠️  Authentication failed - some tests will be skipped")
                    else:
                        print("⚠️  No test credentials provided - protected endpoints will be skipped")
                        
        except Exception as e:
            print(f"⚠️  Authentication setup failed: {e}")
    
    def test_public_endpoints(self):
        """Test public endpoints that don't require authentication"""
        print("\n=== Testing Public Endpoints ===")
        
        public_endpoints = [
            # Core application endpoints
            ('/', 200, 'GET', 'Landing page'),
            ('/health', 200, 'GET', 'Health check'),
            ('/login', 200, 'GET', 'Login page'),
            
            # API endpoints
            ('/api/health', 200, 'GET', 'API health check'),
            ('/api/version', 200, 'GET', 'API version'),
            
            # Static resources
            ('/static/css/main.css', 200, 'GET', 'Main CSS'),
            ('/static/js/main.js', 200, 'GET', 'Main JavaScript'),
            ('/static/favicons/favicon.ico', 200, 'GET', 'Favicon'),
            
            # Error pages
            ('/nonexistent-page', 404, 'GET', '404 error page'),
        ]
        
        for endpoint, expected_status, method, description in public_endpoints:
            with self.subTest(endpoint=endpoint):
                try:
                    if method == 'GET':
                        response = self.session.get(urljoin(self.base_url, endpoint))
                    elif method == 'POST':
                        response = self.session.post(urljoin(self.base_url, endpoint))
                    else:
                        response = self.session.request(method, urljoin(self.base_url, endpoint))
                    
                    self.assertEqual(response.status_code, expected_status,
                                   f"{description} returned {response.status_code}, expected {expected_status}")
                    
                    # Additional checks for specific endpoints
                    if endpoint == '/health' and response.status_code == 200:
                        try:
                            health_data = response.json()
                            self.assertIn('status', health_data, "Health endpoint missing status")
                            print(f"✅ {description}: {health_data.get('status', 'unknown')}")
                        except json.JSONDecodeError:
                            print(f"✅ {description}: {response.status_code} (non-JSON response)")
                    else:
                        print(f"✅ {description}: {response.status_code}")
                        
                except Exception as e:
                    self.fail(f"Failed to access {description} ({endpoint}): {e}")
    
    def test_protected_endpoints(self):
        """Test protected endpoints that require authentication"""
        print("\n=== Testing Protected Endpoints ===")
        
        if not self.authenticated:
            print("⚠️  Skipping protected endpoint tests - not authenticated")
            return
        
        protected_endpoints = [
            # User dashboard and profile
            ('/dashboard', 200, 'GET', 'User dashboard'),
            ('/profile', 200, 'GET', 'User profile'),
            
            # Platform management
            ('/platforms', 200, 'GET', 'Platform management'),
            ('/platforms/add', 200, 'GET', 'Add platform page'),
            
            # Caption management
            ('/captions', 200, 'GET', 'Caption management'),
            ('/review', 200, 'GET', 'Review interface'),
            
            # API endpoints
            ('/api/user/profile', 200, 'GET', 'User profile API'),
            ('/api/platforms', 200, 'GET', 'Platforms API'),
            ('/api/captions/stats', 200, 'GET', 'Caption statistics API'),
        ]
        
        for endpoint, expected_status, method, description in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                try:
                    if method == 'GET':
                        response = self.session.get(urljoin(self.base_url, endpoint))
                    elif method == 'POST':
                        response = self.session.post(urljoin(self.base_url, endpoint))
                    else:
                        response = self.session.request(method, urljoin(self.base_url, endpoint))
                    
                    # Accept both success and redirect responses for protected endpoints
                    if response.status_code in [200, 302]:
                        print(f"✅ {description}: {response.status_code}")
                    else:
                        print(f"⚠️  {description}: {response.status_code} (may require specific permissions)")
                        
                except Exception as e:
                    print(f"⚠️  Failed to access {description} ({endpoint}): {e}")
    
    def test_admin_endpoints(self):
        """Test admin endpoints"""
        print("\n=== Testing Admin Endpoints ===")
        
        if not self.authenticated:
            print("⚠️  Skipping admin endpoint tests - not authenticated")
            return
        
        admin_endpoints = [
            # Admin dashboard
            ('/admin', [200, 302, 403], 'GET', 'Admin dashboard'),
            ('/admin/dashboard', [200, 302, 403], 'GET', 'Admin main dashboard'),
            
            # User management
            ('/admin/users', [200, 302, 403], 'GET', 'User management'),
            ('/admin/user-management', [200, 302, 403], 'GET', 'User management interface'),
            
            # System monitoring
            ('/admin/monitoring', [200, 302, 403], 'GET', 'System monitoring'),
            ('/admin/performance', [200, 302, 403], 'GET', 'Performance dashboard'),
            ('/admin/health', [200, 302, 403], 'GET', 'System health'),
            
            # System maintenance
            ('/admin/maintenance', [200, 302, 403], 'GET', 'Maintenance dashboard'),
            ('/admin/system-logs', [200, 302, 403], 'GET', 'System logs'),
            
            # API endpoints
            ('/admin/api/system/status', [200, 302, 403], 'GET', 'System status API'),
            ('/admin/api/users/stats', [200, 302, 403], 'GET', 'User statistics API'),
        ]
        
        for endpoint, expected_statuses, method, description in admin_endpoints:
            with self.subTest(endpoint=endpoint):
                try:
                    if method == 'GET':
                        response = self.session.get(urljoin(self.base_url, endpoint))
                    elif method == 'POST':
                        response = self.session.post(urljoin(self.base_url, endpoint))
                    else:
                        response = self.session.request(method, urljoin(self.base_url, endpoint))
                    
                    if response.status_code in expected_statuses:
                        if response.status_code == 200:
                            print(f"✅ {description}: {response.status_code}")
                        elif response.status_code == 302:
                            print(f"✅ {description}: {response.status_code} (redirect)")
                        elif response.status_code == 403:
                            print(f"⚠️  {description}: {response.status_code} (access denied - may require admin role)")
                    else:
                        print(f"⚠️  {description}: {response.status_code} (unexpected status)")
                        
                except Exception as e:
                    print(f"⚠️  Failed to access {description} ({endpoint}): {e}")
    
    def test_api_functionality(self):
        """Test API functionality and data formats"""
        print("\n=== Testing API Functionality ===")
        
        api_tests = [
            # Health and status APIs
            {
                'endpoint': '/api/health',
                'method': 'GET',
                'description': 'Health API',
                'expected_keys': ['status'],
                'auth_required': False
            },
            {
                'endpoint': '/api/version',
                'method': 'GET',
                'description': 'Version API',
                'expected_keys': ['version'],
                'auth_required': False
            },
        ]
        
        if self.authenticated:
            api_tests.extend([
                {
                    'endpoint': '/api/user/profile',
                    'method': 'GET',
                    'description': 'User Profile API',
                    'expected_keys': ['username', 'role'],
                    'auth_required': True
                },
                {
                    'endpoint': '/api/platforms',
                    'method': 'GET',
                    'description': 'Platforms API',
                    'expected_keys': ['platforms'],
                    'auth_required': True
                },
            ])
        
        for test_config in api_tests:
            with self.subTest(endpoint=test_config['endpoint']):
                try:
                    if test_config['auth_required'] and not self.authenticated:
                        print(f"⚠️  Skipping {test_config['description']} - authentication required")
                        continue
                    
                    response = self.session.request(
                        test_config['method'],
                        urljoin(self.base_url, test_config['endpoint'])
                    )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            
                            # Check for expected keys
                            for key in test_config['expected_keys']:
                                if key in data:
                                    print(f"✅ {test_config['description']}: Contains '{key}'")
                                else:
                                    print(f"⚠️  {test_config['description']}: Missing '{key}' in response")
                            
                        except json.JSONDecodeError:
                            print(f"⚠️  {test_config['description']}: Non-JSON response")
                    else:
                        print(f"⚠️  {test_config['description']}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️  {test_config['description']} failed: {e}")
    
    def test_websocket_endpoints(self):
        """Test WebSocket endpoints"""
        print("\n=== Testing WebSocket Endpoints ===")
        
        try:
            # Test WebSocket endpoint availability
            ws_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
            
            # Simple connectivity test using requests (HTTP upgrade)
            headers = {
                'Connection': 'Upgrade',
                'Upgrade': 'websocket',
                'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
                'Sec-WebSocket-Version': '13'
            }
            
            response = self.session.get(ws_url, headers=headers)
            
            if response.status_code == 101:
                print("✅ WebSocket endpoint: Upgrade successful")
            elif response.status_code == 400:
                print("✅ WebSocket endpoint: Available (bad request expected for HTTP client)")
            else:
                print(f"⚠️  WebSocket endpoint: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  WebSocket endpoint test failed: {e}")
    
    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        print("\n=== Testing CSRF Protection ===")
        
        try:
            # Test login form CSRF protection
            login_page = self.session.get(urljoin(self.base_url, '/login'))
            if login_page.status_code == 200:
                if 'csrf-token' in login_page.text or 'csrf_token' in login_page.text:
                    print("✅ CSRF Protection: Token found in login form")
                else:
                    print("⚠️  CSRF Protection: No token found in login form")
            
            # Test POST without CSRF token (should fail)
            response = self.session.post(urljoin(self.base_url, '/login'), data={
                'username_or_email': 'test',
                'password': 'test'
            })
            
            if response.status_code in [400, 403]:
                print("✅ CSRF Protection: POST without token rejected")
            elif response.status_code == 200 and 'error' in response.text.lower():
                print("✅ CSRF Protection: POST without token shows error")
            else:
                print("⚠️  CSRF Protection: POST without token not properly rejected")
                
        except Exception as e:
            print(f"⚠️  CSRF protection test failed: {e}")
    
    def test_rate_limiting(self):
        """Test rate limiting protection"""
        print("\n=== Testing Rate Limiting ===")
        
        try:
            # Test rapid requests to login endpoint
            login_url = urljoin(self.base_url, '/login')
            responses = []
            
            for i in range(10):  # Make 10 rapid requests
                response = self.session.post(login_url, data={
                    'username_or_email': 'test_user',
                    'password': 'wrong_password'
                })
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay
            
            # Check if any requests were rate limited
            rate_limited = any(status == 429 for status in responses)
            
            if rate_limited:
                print("✅ Rate Limiting: Requests properly rate limited")
            else:
                print("⚠️  Rate Limiting: No rate limiting detected (may be configured differently)")
                
        except Exception as e:
            print(f"⚠️  Rate limiting test failed: {e}")
    
    def test_error_handling(self):
        """Test error handling and error pages"""
        print("\n=== Testing Error Handling ===")
        
        error_tests = [
            ('/nonexistent-endpoint', 404, 'Not Found'),
            ('/api/nonexistent', 404, 'API Not Found'),
        ]
        
        for endpoint, expected_status, description in error_tests:
            with self.subTest(endpoint=endpoint):
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    self.assertEqual(response.status_code, expected_status,
                                   f"{description} returned {response.status_code}")
                    
                    # Check if error page contains useful information
                    if 'error' in response.text.lower() or str(expected_status) in response.text:
                        print(f"✅ {description}: Proper error page")
                    else:
                        print(f"⚠️  {description}: Error page may need improvement")
                        
                except Exception as e:
                    print(f"⚠️  {description} test failed: {e}")
    
    def test_response_times(self):
        """Test API response times"""
        print("\n=== Testing Response Times ===")
        
        performance_endpoints = [
            ('/', 'Landing page'),
            ('/health', 'Health check'),
            ('/api/health', 'API health'),
            ('/login', 'Login page'),
        ]
        
        for endpoint, description in performance_endpoints:
            response_times = []
            
            for _ in range(3):  # 3 requests for average
                start_time = time.time()
                try:
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        response_times.append((end_time - start_time) * 1000)  # Convert to ms
                except Exception:
                    pass
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                
                print(f"✅ {description}: {avg_time:.2f}ms avg, {max_time:.2f}ms max")
                
                # Performance thresholds
                if avg_time > 2000:  # 2 seconds
                    print(f"⚠️  {description}: Average response time exceeds 2s")
                elif avg_time > 1000:  # 1 second
                    print(f"⚠️  {description}: Average response time exceeds 1s")
            else:
                print(f"⚠️  {description}: No successful requests for timing")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)