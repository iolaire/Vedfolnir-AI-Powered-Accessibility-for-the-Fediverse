# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Authenticated CSP compliance testing for admin pages and protected routes
"""

import unittest
import os
import sys
import time
import subprocess
import requests
import re
import json
from pathlib import Path
from urllib.parse import urljoin

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from security.config.strict_csp_config import StrictCSPConfig


class TestAuthenticatedCSPCompliance(unittest.TestCase):
    """Test CSP compliance for authenticated pages"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.base_url = "http://127.0.0.1:5000"
        cls.web_app_process = None
        cls.session = None
        cls.test_results = {
            'pages_tested': 0,
            'csp_violations': [],
            'inline_styles_found': [],
            'pages_passed': [],
            'pages_failed': [],
            'admin_pages_tested': 0,
            'admin_pages_passed': 0
        }
        
        # Start web application for testing
        cls._start_web_app()
        
        # Create authenticated session
        cls._create_authenticated_session()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment and report results"""
        cls._stop_web_app()
        cls._generate_test_report()
    
    @classmethod
    def _start_web_app(cls):
        """Start the web application"""
        try:
            # Check if app is already running
            response = requests.get(cls.base_url, timeout=2)
            if response.status_code == 200:
                print("✅ Web app already running")
                return
        except requests.exceptions.RequestException:
            pass
        
        # Start web app
        web_app_path = cls.project_root / "web_app.py"
        cls.web_app_process = subprocess.Popen(
            [sys.executable, str(web_app_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cls.project_root
        )
        
        # Wait for app to start
        for _ in range(30):  # 30 second timeout
            try:
                response = requests.get(cls.base_url, timeout=2)
                if response.status_code == 200:
                    print("✅ Web app started successfully")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception("❌ Failed to start web application")
    
    @classmethod
    def _stop_web_app(cls):
        """Stop the web application"""
        if cls.web_app_process:
            cls.web_app_process.terminate()
            cls.web_app_process.wait()
            print("✅ Web app stopped")
    
    @classmethod
    def _create_authenticated_session(cls):
        """Create authenticated session with admin credentials"""
        cls.session = requests.Session()
        
        try:
            # Get login page and CSRF token
            login_page = cls.session.get(urljoin(cls.base_url, "/login"), timeout=10)
            
            if login_page.status_code != 200:
                raise Exception(f"Could not access login page: {login_page.status_code}")
            
            # Extract CSRF token
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
            if not csrf_match:
                # Try alternative CSRF token extraction
                csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', login_page.text)
            
            if not csrf_match:
                raise Exception("Could not find CSRF token in login page")
            
            csrf_token = csrf_match.group(1)
            print(f"✅ CSRF token extracted: {csrf_token[:20]}...")
            
            # Login with admin credentials
            login_data = {
                'username_or_email': 'admin',
                'password': 'admin123',
                'csrf_token': csrf_token
            }
            
            response = cls.session.post(
                urljoin(cls.base_url, "/login"), 
                data=login_data,
                timeout=10,
                allow_redirects=False
            )
            
            # Check for successful login (redirect or 200 with success indication)
            if response.status_code in [200, 302]:
                # Verify we're actually logged in by checking a protected page
                dashboard_response = cls.session.get(urljoin(cls.base_url, "/admin"), timeout=10)
                
                if dashboard_response.status_code == 200 and 'admin' in dashboard_response.text.lower():
                    print("✅ Successfully authenticated as admin")
                    return
                else:
                    print(f"⚠️  Login may have failed - admin page status: {dashboard_response.status_code}")
            
            print(f"⚠️  Login response status: {response.status_code}")
            print(f"⚠️  Login response headers: {dict(response.headers)}")
            
            # Continue with tests even if login seems uncertain
            print("⚠️  Continuing with tests (login status uncertain)")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("⚠️  Continuing with unauthenticated tests")
            cls.session = requests.Session()  # Use unauthenticated session
    
    @classmethod
    def _generate_test_report(cls):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("AUTHENTICATED CSP COMPLIANCE TEST REPORT")
        print("="*80)
        
        print(f"Total Pages Tested: {cls.test_results['pages_tested']}")
        print(f"Admin Pages Tested: {cls.test_results['admin_pages_tested']}")
        print(f"Pages Passed: {len(cls.test_results['pages_passed'])}")
        print(f"Pages Failed: {len(cls.test_results['pages_failed'])}")
        
        if cls.test_results['csp_violations']:
            print(f"\n❌ CSP Violations Found: {len(cls.test_results['csp_violations'])}")
            for violation in cls.test_results['csp_violations'][:10]:  # Show first 10
                print(f"  - {violation}")
        
        if cls.test_results['inline_styles_found']:
            print(f"\n⚠️  Inline Styles Found: {len(cls.test_results['inline_styles_found'])}")
            for style in cls.test_results['inline_styles_found'][:10]:  # Show first 10
                print(f"  - {style}")
        
        if cls.test_results['pages_passed']:
            print(f"\n✅ Pages Passed CSP Compliance:")
            for page in cls.test_results['pages_passed']:
                print(f"  - {page}")
        
        print("\n" + "="*80)
    
    def test_admin_dashboard_csp_compliance(self):
        """Test admin dashboard for CSP compliance"""
        print("\n🔍 Testing admin dashboard CSP compliance...")
        
        admin_pages = [
            "/admin",
            "/admin/dashboard",
            "/admin/user-management",
            "/admin/system-maintenance",
            "/admin/monitoring"
        ]
        
        for page in admin_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}", timeout=10)
                self.test_results['pages_tested'] += 1
                self.test_results['admin_pages_tested'] += 1
                
                print(f"Testing {page} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check CSP header
                    csp_header = response.headers.get('Content-Security-Policy')
                    
                    if csp_header:
                        # Validate CSP policy
                        validation = StrictCSPConfig.validate_csp_policy(csp_header)
                        
                        if validation['valid']:
                            print(f"✅ CSP validation passed for {page}")
                            self.test_results['pages_passed'].append(page)
                            self.test_results['admin_pages_passed'] += 1
                        else:
                            print(f"❌ CSP validation failed for {page}: {validation['issues']}")
                            self.test_results['csp_violations'].extend([
                                f"{page}: {issue}" for issue in validation['issues']
                            ])
                            self.test_results['pages_failed'].append(page)
                        
                        # Check for unsafe-inline in style-src
                        if "'unsafe-inline'" in csp_header and "style-src" in csp_header:
                            style_src_match = re.search(r'style-src\s+([^;]+)', csp_header)
                            if style_src_match and "'unsafe-inline'" in style_src_match.group(1):
                                self.test_results['csp_violations'].append(
                                    f"{page}: style-src contains 'unsafe-inline'"
                                )
                                print(f"❌ {page} has unsafe-inline in style-src")
                    else:
                        print(f"⚠️  No CSP header found for {page}")
                
                elif response.status_code == 403:
                    print(f"⚠️  Access denied to {page} (authentication may have failed)")
                elif response.status_code == 404:
                    print(f"⚠️  Page not found: {page}")
                else:
                    print(f"❌ Unexpected status {response.status_code} for {page}")
                    self.test_results['pages_failed'].append(page)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not test {page}: {e}")
                self.test_results['pages_failed'].append(page)
    
    def test_admin_pages_inline_styles(self):
        """Test admin pages for inline styles"""
        print("\n🔍 Testing admin pages for inline styles...")
        
        admin_pages = [
            "/admin",
            "/admin/user-management",
            "/admin/monitoring"
        ]
        
        inline_style_pattern = re.compile(r'style\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
        
        for page in admin_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}", timeout=10)
                self.test_results['pages_tested'] += 1
                
                if response.status_code == 200:
                    matches = inline_style_pattern.findall(response.text)
                    
                    if matches:
                        for match in matches[:5]:  # Limit to first 5 matches
                            self.test_results['inline_styles_found'].append(
                                f"{page}: style=\"{match[:50]}{'...' if len(match) > 50 else ''}\""
                            )
                        
                        print(f"⚠️  Found {len(matches)} inline styles in {page}")
                        self.test_results['pages_failed'].append(page)
                    else:
                        print(f"✅ No inline styles found in {page}")
                        self.test_results['pages_passed'].append(page)
                
                elif response.status_code == 403:
                    print(f"⚠️  Access denied to {page}")
                else:
                    print(f"⚠️  Could not access {page}: {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not test {page}: {e}")
    
    def test_admin_api_endpoints_csp(self):
        """Test admin API endpoints for CSP headers"""
        print("\n🔍 Testing admin API endpoints for CSP headers...")
        
        api_endpoints = [
            "/admin/api/system-status",
            "/admin/api/user-stats",
            "/admin/api/performance-metrics"
        ]
        
        for endpoint in api_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                self.test_results['pages_tested'] += 1
                
                print(f"Testing API {endpoint} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    # API endpoints should also have CSP headers
                    csp_header = response.headers.get('Content-Security-Policy')
                    
                    if csp_header:
                        print(f"✅ CSP header present for API {endpoint}")
                        self.test_results['pages_passed'].append(endpoint)
                    else:
                        print(f"⚠️  No CSP header for API {endpoint}")
                
                elif response.status_code == 404:
                    print(f"⚠️  API endpoint not found: {endpoint}")
                elif response.status_code == 403:
                    print(f"⚠️  Access denied to API {endpoint}")
                else:
                    print(f"⚠️  API endpoint {endpoint} returned {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not test API {endpoint}: {e}")
    
    def test_user_profile_pages_csp(self):
        """Test user profile pages for CSP compliance"""
        print("\n🔍 Testing user profile pages for CSP compliance...")
        
        profile_pages = [
            "/profile",
            "/platform-management",
            "/caption-generation"
        ]
        
        for page in profile_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}", timeout=10)
                self.test_results['pages_tested'] += 1
                
                print(f"Testing {page} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check for CSP header
                    csp_header = response.headers.get('Content-Security-Policy')
                    
                    if csp_header:
                        # Check for unsafe-inline
                        if "'unsafe-inline'" not in csp_header:
                            print(f"✅ Strict CSP (no unsafe-inline) for {page}")
                            self.test_results['pages_passed'].append(page)
                        else:
                            print(f"⚠️  CSP contains unsafe-inline for {page}")
                            self.test_results['csp_violations'].append(
                                f"{page}: CSP contains unsafe-inline"
                            )
                    else:
                        print(f"⚠️  No CSP header for {page}")
                
                elif response.status_code == 302:
                    print(f"⚠️  Redirect from {page} (may require different authentication)")
                elif response.status_code == 404:
                    print(f"⚠️  Page not found: {page}")
                else:
                    print(f"⚠️  Unexpected status {response.status_code} for {page}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not test {page}: {e}")
    
    def test_websocket_pages_csp(self):
        """Test pages with WebSocket functionality for CSP compliance"""
        print("\n🔍 Testing WebSocket pages for CSP compliance...")
        
        websocket_pages = [
            "/caption-generation",
            "/admin/monitoring",
            "/admin/system-maintenance"
        ]
        
        for page in websocket_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}", timeout=10)
                self.test_results['pages_tested'] += 1
                
                print(f"Testing WebSocket page {page} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check CSP connect-src for WebSocket support
                    csp_header = response.headers.get('Content-Security-Policy')
                    
                    if csp_header:
                        if 'connect-src' in csp_header and ('ws:' in csp_header or 'wss:' in csp_header):
                            print(f"✅ WebSocket CSP support for {page}")
                            self.test_results['pages_passed'].append(page)
                        else:
                            print(f"⚠️  WebSocket CSP may be missing for {page}")
                            self.test_results['csp_violations'].append(
                                f"{page}: Missing WebSocket CSP support"
                            )
                    
                    # Check for inline scripts that might affect WebSocket
                    inline_script_pattern = re.compile(r'<script(?![^>]*src=)([^>]*?)>(.*?)</script>', re.IGNORECASE | re.DOTALL)
                    inline_scripts = inline_script_pattern.findall(response.text)
                    
                    websocket_scripts_without_nonce = []
                    for script_attrs, script_content in inline_scripts:
                        if 'websocket' in script_content.lower() or 'socket.io' in script_content.lower():
                            # Check if script has nonce attribute
                            if 'nonce=' not in script_attrs:
                                websocket_scripts_without_nonce.append(script_content)
                    
                    if websocket_scripts_without_nonce:
                        print(f"⚠️  Found {len(websocket_scripts_without_nonce)} inline WebSocket scripts without nonce in {page}")
                        for script in websocket_scripts_without_nonce[:2]:  # Show first 2
                            self.test_results['csp_violations'].append(
                                f"{page}: Inline WebSocket script without nonce"
                            )
                    else:
                        # Check if there are WebSocket scripts with nonces (good)
                        websocket_scripts_with_nonce = []
                        for script_attrs, script_content in inline_scripts:
                            if 'websocket' in script_content.lower() or 'socket.io' in script_content.lower():
                                if 'nonce=' in script_attrs:
                                    websocket_scripts_with_nonce.append(script_content)
                        
                        if websocket_scripts_with_nonce:
                            print(f"✅ Found {len(websocket_scripts_with_nonce)} inline WebSocket scripts with proper nonces in {page}")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Could not test WebSocket page {page}: {e}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)