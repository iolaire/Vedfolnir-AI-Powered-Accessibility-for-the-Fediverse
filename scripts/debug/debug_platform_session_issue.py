#!/usr/bin/env python3
"""
Debug script to investigate platform session persistence issue

This script will:
1. Test login functionality
2. Test platform selection
3. Test session persistence between routes
4. Identify where platform data is being lost
"""

import os
import sys
import requests
import json
from urllib.parse import urljoin

# Test credentials
TEST_USERNAME = "iolaire"
TEST_PASSWORD = "user123"
BASE_URL = "http://localhost:5000"

class PlatformSessionDebugger:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        
    def get_csrf_token(self, response_text):
        """Extract CSRF token from HTML response"""
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', response_text)
        return match.group(1) if match else None
    
    def test_login(self):
        """Test login functionality"""
        print("=== Testing Login ===")
        
        # Get login page to extract CSRF token
        login_url = urljoin(self.base_url, "/user_management/login")
        response = self.session.get(login_url)
        print(f"Login page status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to get login page: {response.text}")
            return False
        
        # Extract CSRF token
        self.csrf_token = self.get_csrf_token(response.text)
        if not self.csrf_token:
            print("Failed to extract CSRF token from login page")
            return False
        
        print(f"CSRF token: {self.csrf_token}")
        
        # Perform login
        login_data = {
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD,
            'csrf_token': self.csrf_token
        }
        
        response = self.session.post(login_url, data=login_data, allow_redirects=False)
        print(f"Login response status: {response.status_code}")
        print(f"Login response headers: {dict(response.headers)}")
        
        if response.status_code in [302, 303]:
            print("Login successful (redirect received)")
            return True
        else:
            print(f"Login failed: {response.text}")
            return False
    
    def test_platform_management(self):
        """Test platform management page"""
        print("\n=== Testing Platform Management ===")
        
        platform_url = urljoin(self.base_url, "/platform_management")
        response = self.session.get(platform_url)
        print(f"Platform management status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to access platform management: {response.text}")
            return False, None
        
        # Check for platforms in the response
        platforms = []
        if "switch_platform" in response.text:
            import re
            platform_matches = re.findall(r'/switch_platform/(\d+)', response.text)
            platforms = [int(p) for p in platform_matches]
            print(f"Found platforms: {platforms}")
        
        return True, platforms
    
    def test_platform_switch(self, platform_id):
        """Test platform switching"""
        print(f"\n=== Testing Platform Switch to {platform_id} ===")
        
        switch_url = urljoin(self.base_url, f"/switch_platform/{platform_id}")
        response = self.session.get(switch_url, allow_redirects=False)
        print(f"Switch platform status: {response.status_code}")
        print(f"Switch platform headers: {dict(response.headers)}")
        
        if response.status_code in [302, 303]:
            print("Platform switch successful (redirect received)")
            return True
        else:
            print(f"Platform switch failed: {response.text}")
            return False
    
    def test_session_context(self):
        """Test session context API"""
        print("\n=== Testing Session Context ===")
        
        # Check if there's a session context API endpoint
        context_url = urljoin(self.base_url, "/api/session/context")
        response = self.session.get(context_url)
        print(f"Session context API status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                context_data = response.json()
                print(f"Session context: {json.dumps(context_data, indent=2)}")
                return context_data
            except:
                print("Failed to parse session context JSON")
        else:
            print("Session context API not available or failed")
        
        return None
    
    def test_caption_generation_access(self):
        """Test caption generation page access"""
        print("\n=== Testing Caption Generation Access ===")
        
        caption_url = urljoin(self.base_url, "/caption_generation")
        response = self.session.get(caption_url, allow_redirects=False)
        print(f"Caption generation status: {response.status_code}")
        print(f"Caption generation headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("Caption generation page accessible")
            return True
        elif response.status_code in [302, 303]:
            redirect_location = response.headers.get('Location', '')
            print(f"Caption generation redirected to: {redirect_location}")
            if 'platform_management' in redirect_location:
                print("ERROR: Redirected back to platform management - platform data lost!")
                return False
        else:
            print(f"Caption generation failed: {response.text}")
            return False
    
    def debug_cookies_and_session(self):
        """Debug cookies and session data"""
        print("\n=== Debugging Cookies and Session ===")
        
        print("Current cookies:")
        for cookie in self.session.cookies:
            print(f"  {cookie.name}: {cookie.value}")
        
        # Try to access a debug endpoint if available
        debug_url = urljoin(self.base_url, "/debug/session")
        response = self.session.get(debug_url)
        if response.status_code == 200:
            print(f"Debug session info: {response.text}")
    
    def run_full_test(self):
        """Run complete test suite"""
        print("Starting Platform Session Persistence Debug Test")
        print("=" * 50)
        
        # Step 1: Login
        if not self.test_login():
            print("FAILED: Login test failed")
            return False
        
        # Step 2: Access platform management
        success, platforms = self.test_platform_management()
        if not success:
            print("FAILED: Platform management access failed")
            return False
        
        if not platforms:
            print("FAILED: No platforms found")
            return False
        
        # Step 3: Switch to first platform
        platform_id = platforms[0]
        if not self.test_platform_switch(platform_id):
            print("FAILED: Platform switch failed")
            return False
        
        # Step 4: Test session context
        context = self.test_session_context()
        
        # Step 5: Debug cookies and session
        self.debug_cookies_and_session()
        
        # Step 6: Test caption generation access
        if not self.test_caption_generation_access():
            print("FAILED: Caption generation access failed - this is the main issue!")
            return False
        
        print("\nSUCCESS: All tests passed!")
        return True

def main():
    debugger = PlatformSessionDebugger()
    success = debugger.run_full_test()
    
    if not success:
        print("\nDEBUG TEST FAILED - Platform session persistence issue confirmed")
        sys.exit(1)
    else:
        print("\nDEBUG TEST PASSED - No platform session persistence issue found")
        sys.exit(0)

if __name__ == "__main__":
    main()
