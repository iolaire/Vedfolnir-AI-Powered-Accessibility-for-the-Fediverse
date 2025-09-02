#!/usr/bin/env python3
"""
Test Platform Session Fix - Following Correct Path

1. Load http://127.0.0.1:5000/login
2. Login with username and password  
3. Check redirect to dashboard (look for "Dashboard" text)
4. Check rendered page for "Platforms: pixel" text
5. Visit http://127.0.0.1:5000/caption_generation
6. Verify not redirected back to dashboard
"""

import requests
import sys
from urllib.parse import urljoin

# Test credentials
TEST_USERNAME = "iolaire@usa.net"
TEST_PASSWORD = "g9bDFB9JzgEaVZx"
BASE_URL = "http://127.0.0.1:5000"

class PlatformSessionTester:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        
        # Add browser-like headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_csrf_token(self, response_text):
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', response_text)
        return match.group(1) if match else None
    
    def step1_load_login(self):
        print("=== Step 1: Load Login Page ===")
        response = self.session.get(f"{BASE_URL}/login")
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Failed to load login page")
            return False
            
        self.csrf_token = self.get_csrf_token(response.text)
        if not self.csrf_token:
            print("❌ No CSRF token found")
            return False
            
        print("✅ Login page loaded, CSRF token extracted")
        return True
    
    def step2_login(self):
        print("\n=== Step 2: Login ===")
        login_data = {
            'username_or_email': TEST_USERNAME,  # Fixed: use correct field name
            'password': TEST_PASSWORD,
            'csrf_token': self.csrf_token
        }
        
        response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        # Debug: Check if login actually succeeded by looking for error messages
        error_indicators = ["Invalid username", "Invalid password", "Login failed", "Authentication failed", "Incorrect password"]
        found_error = False
        for indicator in error_indicators:
            if indicator in response.text:
                print(f"❌ Login failed - found error: {indicator}")
                found_error = True
                break
        
        if found_error:
            return False
        
        # Debug: Show cookies after login
        print("Cookies after login:")
        for cookie in self.session.cookies:
            print(f"  {cookie.name}: {cookie.value}")
        
        # Debug: Check if we're still on login page with form
        if 'name="username_or_email"' in response.text and 'name="password"' in response.text:
            print("❌ Still on login page - login may have failed")
            print("Response content (first 300 chars):")
            print(response.text[:300])
            return False
        
        if response.status_code != 200:
            print("❌ Login failed")
            return False
        
        # Add delay to ensure session is saved
        print("Waiting for session to be saved...")
        import time
        time.sleep(3)
            
        print("✅ Login completed")
        return True
    
    def step3_check_dashboard(self):
        print("\n=== Step 3: Check Dashboard ===")
        
        # Debug: Show cookies before dashboard request
        print("Cookies before dashboard request:")
        for cookie in self.session.cookies:
            print(f"  {cookie.name}: {cookie.value}")
        
        response = self.session.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code != 200:
            print("❌ Dashboard not accessible")
            return False
            
        if "login" in response.url and "next=" in response.url:
            print("❌ Redirected back to login")
            print("This suggests the session cookie is not being recognized")
            return False
            
        if "Dashboard" in response.text:
            print("✅ Found 'Dashboard' text")
            return True
        else:
            print("❌ 'Dashboard' text not found")
            # Show some content to see what we got
            print("Page content (first 200 chars):")
            print(response.text[:200])
            return False
    
    def step4_check_platforms_pixel(self):
        print("\n=== Step 4: Check 'Platforms: pixel' ===")
        response = self.session.get(f"{BASE_URL}/")
        
        if "Platforms: pixel" in response.text:
            print("✅ Found 'Platforms: pixel' text")
            return True
        else:
            print("❌ 'Platforms: pixel' text not found")
            # Show platform-related content for debugging
            lines = response.text.split('\n')
            platform_lines = [line.strip() for line in lines if 'pixel' in line.lower() or 'platform' in line.lower()]
            if platform_lines:
                print("Platform-related content:")
                for line in platform_lines[:5]:
                    if line:
                        print(f"  {line}")
            return False
    
    def step5_visit_caption_generation(self):
        print("\n=== Step 5: Visit Caption Generation ===")
        response = self.session.get(f"{BASE_URL}/caption_generation", allow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"URL: {response.url}")
        
        if response.status_code != 200:
            print("❌ Caption generation not accessible")
            return False
            
        print("✅ Caption generation page accessed")
        return True
    
    def step6_verify_no_redirect(self):
        print("\n=== Step 6: Verify No Redirect Back ===")
        response = self.session.get(f"{BASE_URL}/caption_generation", allow_redirects=False)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ No redirect - caption generation loads directly")
            return True
        elif response.status_code in [302, 303]:
            redirect_location = response.headers.get('Location', '')
            print(f"Redirect to: {redirect_location}")
            
            if 'platform_management' in redirect_location:
                print("❌ FAILED: Redirected to platform management - platform data lost!")
                return False
            elif redirect_location == '/' or 'dashboard' in redirect_location:
                print("❌ FAILED: Redirected back to dashboard")
                return False
            else:
                print("✅ Redirected to different page (acceptable)")
                return True
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
    
    def run_test(self):
        print("🚀 Platform Session Persistence Test")
        print("=" * 50)
        
        steps = [
            self.step1_load_login,
            self.step2_login,
            self.step3_check_dashboard,
            self.step4_check_platforms_pixel,
            self.step5_visit_caption_generation,
            self.step6_verify_no_redirect
        ]
        
        for i, step in enumerate(steps, 1):
            if not step():
                print(f"\n❌ TEST FAILED at step {i}")
                return False
        
        print("\n🎉 TEST PASSED: All steps completed successfully!")
        return True

def main():
    tester = PlatformSessionTester()
    try:
        success = tester.run_test()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to http://127.0.0.1:5000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
