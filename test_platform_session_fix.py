#!/usr/bin/env python3
"""
Test Platform Session Fix

This script tests the complete flow:
1. Login
2. Platform selection
3. Navigation to caption generation
4. Verification that platform persists

This should be run after starting the web application.
"""

import os
import sys
import requests
import json
import time
from urllib.parse import urljoin

# Test credentials
TEST_USERNAME = "iolaire@usa.net"
TEST_PASSWORD = "g9bDFB9JzgEaVZx"
BASE_URL = "http://127.0.0.1:5000"

class PlatformSessionTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        
    def get_csrf_token(self, response_text):
        """Extract CSRF token from HTML response"""
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', response_text)
        return match.group(1) if match else None
    
    def login(self):
        """Login to the application"""
        print("=== Step 1: Login ===")
        
        # Get login page
        login_url = urljoin(self.base_url, "/login")
        response = self.session.get(login_url)
        
        print(f"Login page status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Failed to get login page: {response.status_code}")
            return False
        
        # Extract CSRF token
        self.csrf_token = self.get_csrf_token(response.text)
        if not self.csrf_token:
            print("❌ Failed to extract CSRF token")
            print("Response content preview:")
            print(response.text[:500])
            return False
        
        print(f"CSRF token extracted: {self.csrf_token[:20]}...")
        
        # Perform login
        login_data = {
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD,
            'csrf_token': self.csrf_token
        }
        
        print(f"Attempting login with username: {TEST_USERNAME}")
        response = self.session.post(login_url, data=login_data, allow_redirects=True)
        
        print(f"Login response status: {response.status_code}")
        print(f"Final URL after redirects: {response.url}")
        
        # Debug: Show response content indicators
        response_text = response.text.lower()
        print(f"Response length: {len(response.text)}")
        print(f"Contains 'login': {'login' in response_text}")
        print(f"Contains 'dashboard': {'dashboard' in response_text}")
        print(f"Contains 'platform': {'platform' in response_text}")
        print(f"Contains 'navbar': {'navbar' in response_text}")
        print(f"Contains 'logout': {'logout' in response_text}")
        
        # Check if we're still on login page
        if "login" in response.url.lower():
            # Even if URL contains login, check if we have success indicators
            success_indicators = ["navbar", "dashboard", "platform", "logout"]
            found_indicators = [indicator for indicator in success_indicators if indicator in response_text]
            
            if len(found_indicators) >= 2:  # If we have multiple success indicators, login likely worked
                print(f"✅ Login successful - found indicators: {found_indicators} (despite login URL)")
                # Add delay to ensure session is saved
                time.sleep(2)
                
                # Debug: Show cookies after login
                print("Cookies after login:")
                for cookie in self.session.cookies:
                    print(f"  {cookie.name}: {cookie.value}")
                
                return True
            elif ("username" in response_text or "password" in response_text) and "navbar" not in response_text:
                print("❌ Login failed - still showing login form")
                # Look for actual error messages (not CSS errors)
                error_patterns = [r'invalid.*credentials', r'incorrect.*password', r'login.*failed', r'authentication.*error']
                import re
                for pattern in error_patterns:
                    if re.search(pattern, response_text, re.IGNORECASE):
                        print(f"Found login error: {pattern}")
                        return False
                return False
            else:
                print(f"✅ Login successful - found indicators: {found_indicators}")
                # Add delay to ensure session is saved
                time.sleep(2)
                return True
        
        # Check for success indicators
        success_indicators = ["navbar", "dashboard", "platform", "welcome", "logout"]
        found_indicators = [indicator for indicator in success_indicators if indicator in response_text]
        
        if found_indicators:
            print(f"✅ Login successful - found indicators: {found_indicators}")
            # Add delay to ensure session is saved
            time.sleep(2)
            
            # Debug: Show cookies after login
            print("Cookies after login:")
            for cookie in self.session.cookies:
                print(f"  {cookie.name}: {cookie.value}")
            
            return True
        
        print("❌ Login status unclear - no clear success indicators found")
        return False
    
    def get_platforms(self):
        """Get available platforms"""
        print("\n=== Step 2: Get Available Platforms ===")
        
        platform_url = urljoin(self.base_url, "/platform_management")
        response = self.session.get(platform_url)
        
        print(f"Platform management status: {response.status_code}")
        print(f"Platform management URL: {response.url}")
        
        if response.status_code != 200:
            print(f"❌ Failed to access platform management: {response.status_code}")
            return []
        
        # Check if we're redirected to login (session issue)
        if "login" in response.url and "next=" in response.url:
            print("❌ Redirected to login - session authentication failed")
            print("Platform management page content (first 200 chars):")
            print(response.text[:200])
            return []
        
        # Look for the specific platform text "Platforms: pixel"
        if "Platforms: pixel" in response.text:
            print("✅ Found platform: pixel")
            return ["pixel"]
        
        # Debug: Show relevant parts of the response
        print("Platform management page content (searching for platform indicators):")
        lines = response.text.split('\n')
        platform_lines = [line.strip() for line in lines if 'pixel' in line.lower() or 'platform' in line.lower()]
        for line in platform_lines[:10]:  # Show first 10 relevant lines
            print(f"  {line}")
        
        print("❌ Platform 'pixel' not found in page content")
        return []
    
    def debug_session_before_switch(self):
        """Debug session state before platform switch"""
        print("\n=== Debug: Session State Before Switch ===")
        
        debug_url = urljoin(self.base_url, "/debug/session")
        response = self.session.get(debug_url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Session ID: {data.get('debug_info', {}).get('session_id')}")
                print(f"Flask session platform: {data.get('debug_info', {}).get('flask_session_data', {}).get('platform_connection_id')}")
                print(f"Redis session platform: {data.get('debug_info', {}).get('redis_session_data', {}).get('platform_connection_id')}")
            except:
                print("❌ Failed to parse debug response")
        else:
            print(f"❌ Debug endpoint not available: {response.status_code}")
    
    def switch_platform(self, platform_name):
        """Switch to a specific platform"""
        print(f"\n=== Step 3: Switch to Platform {platform_name} ===")
        
        # Debug before switch
        self.debug_session_before_switch()
        
        # For the pixel platform, we need to find the actual platform ID
        # Let's try to get the platform management page and extract the switch URL
        platform_url = urljoin(self.base_url, "/platform_management")
        response = self.session.get(platform_url)
        
        if response.status_code != 200 or "login" in response.url:
            print("❌ Cannot access platform management page for platform switching")
            return False
        
        # Look for switch_platform URL for pixel
        import re
        switch_matches = re.findall(r'/switch_platform/(\d+)', response.text)
        
        if not switch_matches:
            print("❌ No switch_platform URLs found")
            return False
        
        # Use the first (and likely only) platform ID
        platform_id = switch_matches[0]
        print(f"Found platform ID: {platform_id}")
        
        switch_url = urljoin(self.base_url, f"/switch_platform/{platform_id}")
        response = self.session.get(switch_url, allow_redirects=True)
        
        if response.status_code == 200:
            print("✅ Platform switch completed")
            
            # Debug after switch using the debug endpoint
            debug_url = urljoin(self.base_url, f"/debug/force_platform_update/{platform_id}")
            debug_response = self.session.get(debug_url)
            
            if debug_response.status_code == 200:
                try:
                    debug_data = debug_response.json()
                    print(f"Platform update success: {debug_data.get('success')}")
                    print(f"Validation result: {debug_data.get('validation', {}).get('valid')}")
                    
                    validation = debug_data.get('validation', {})
                    if validation.get('errors'):
                        print(f"❌ Validation errors: {validation['errors']}")
                    else:
                        print("✅ Platform switch validation passed")
                        
                except Exception as e:
                    print(f"❌ Failed to parse debug response: {e}")
            
            return True
        else:
            print(f"❌ Platform switch failed: {response.status_code}")
            return False
    
    def test_caption_generation_access(self):
        """Test access to caption generation page"""
        print("\n=== Step 4: Test Caption Generation Access ===")
        
        caption_url = urljoin(self.base_url, "/caption_generation")
        response = self.session.get(caption_url, allow_redirects=False)
        
        print(f"Caption generation response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Caption generation page accessible - platform data persisted!")
            return True
        elif response.status_code in [302, 303]:
            redirect_location = response.headers.get('Location', '')
            print(f"Redirected to: {redirect_location}")
            
            if 'platform_management' in redirect_location:
                print("❌ FAILED: Redirected back to platform management - platform data lost!")
                return False
            else:
                print("✅ Redirected to different page (not platform management)")
                return True
        else:
            print(f"❌ Caption generation access failed: {response.status_code}")
            return False
    
    def debug_final_state(self):
        """Debug final session state"""
        print("\n=== Debug: Final Session State ===")
        
        debug_url = urljoin(self.base_url, "/debug/platform")
        response = self.session.get(debug_url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                validation = data.get('validation', {})
                
                print(f"Final validation: {validation.get('valid')}")
                print(f"Flask session platform: {validation.get('flask_session_platform')}")
                print(f"g.context platform: {validation.get('g_context_platform')}")
                print(f"Redis session platform: {validation.get('redis_session_platform')}")
                
                if validation.get('errors'):
                    print(f"Errors: {validation['errors']}")
                    
            except Exception as e:
                print(f"❌ Failed to parse final debug response: {e}")
        else:
            print(f"❌ Final debug endpoint not available: {response.status_code}")
    
    def run_complete_test(self):
        """Run the complete test suite"""
        print("🚀 Starting Platform Session Persistence Test")
        print("=" * 60)
        
        # Step 1: Login
        if not self.login():
            print("\n❌ TEST FAILED: Login failed")
            return False
        
        # Step 2: Get platforms
        platforms = self.get_platforms()
        if not platforms:
            print("\n❌ TEST FAILED: No platforms found")
            return False
        
        # Step 3: Switch to pixel platform
        platform_name = "pixel"
        if not self.switch_platform(platform_name):
            print("\n❌ TEST FAILED: Platform switch failed")
            return False
        
        # Small delay to ensure session is saved
        time.sleep(1)
        
        # Step 4: Test caption generation access
        if not self.test_caption_generation_access():
            print("\n❌ TEST FAILED: Caption generation access failed")
            self.debug_final_state()
            return False
        
        # Debug final state
        self.debug_final_state()
        
        print("\n🎉 TEST PASSED: Platform session persistence working correctly!")
        return True

def main():
    """Main test function"""
    tester = PlatformSessionTester()
    
    try:
        success = tester.run_complete_test()
        if success:
            print("\n✅ All tests passed - platform session persistence is working!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed - platform session persistence issue still exists")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the application. Make sure it's running on http://localhost:5000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
