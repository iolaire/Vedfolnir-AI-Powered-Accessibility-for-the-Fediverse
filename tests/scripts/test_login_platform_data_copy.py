# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python3
"""
Test script to debug login route platform data copy execution
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def test_login_platform_data_copy():
    """Test login route platform data copy functionality"""
    
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    print("=== Testing Login Route Platform Data Copy ===")
    
    # Step 1: Get login page and CSRF token
    print("1. Getting login page...")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    # Extract CSRF token from meta tag
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Get admin credentials
    username = input("Enter username (default: admin): ").strip() or "admin"
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Step 3: Login
    print(f"2. Logging in as {username}...")
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    # Check if login was successful
    if login_response.status_code == 302:
        print("✅ Login successful (redirected)")
        redirect_url = login_response.headers.get('Location', '')
        print(f"   Redirected to: {redirect_url}")
        
        # Step 4: Test accessing caption generation page
        print("3. Testing caption generation page access...")
        caption_response = session.get(urljoin(base_url, "/caption_generation"))
        
        if caption_response.status_code == 200:
            print("✅ Caption generation page accessible")
            return True
        elif caption_response.status_code == 302:
            redirect_url = caption_response.headers.get('Location', '')
            print(f"⚠ Caption generation page redirected to: {redirect_url}")
            if 'platform' in redirect_url.lower():
                print("   This suggests platform context is missing")
            return False
        else:
            print(f"❌ Caption generation page failed: {caption_response.status_code}")
            return False
            
    elif login_response.status_code == 200:
        if 'login' in login_response.url.lower():
            print("❌ Login failed: Still on login page")
            # Check for error messages
            if 'Invalid username' in login_response.text:
                print("   Error: Invalid credentials")
            elif 'locked' in login_response.text.lower():
                print("   Error: Account locked")
            return False
        else:
            print("✅ Login successful")
            return True
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        return False

if __name__ == "__main__":
    success = test_login_platform_data_copy()
    print(f"\n=== Test Result: {'PASSED' if success else 'FAILED'} ===")
    sys.exit(0 if success else 1)