#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to debug the pause system functionality
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def test_pause_system():
    """Test the pause system functionality"""
    base_url = "http://127.0.0.1:5000"
    
    # Create session
    session = requests.Session()
    
    # Step 1: Get login page and CSRF token
    print("Getting login page...")
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
    
    # Step 2: Login as admin
    password = getpass.getpass("Enter admin password: ")
    
    print("Logging in as admin...")
    login_data = {
        'username_or_email': 'admin',
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    if login_response.status_code != 302 and 'login' in login_response.url.lower():
        print("❌ Login failed")
        return False
    
    print("✅ Successfully logged in as admin")
    
    # Step 3: Get the pause system page
    print("Getting pause system page...")
    pause_page = session.get(urljoin(base_url, "/admin/maintenance/pause-system"))
    if pause_page.status_code != 200:
        print(f"❌ Failed to get pause system page: {pause_page.status_code}")
        print(f"Response: {pause_page.text[:500]}")
        return False
    
    print("✅ Got pause system page")
    
    # Extract CSRF token from the pause page
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', pause_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in pause page")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token from pause page: {csrf_token[:20]}...")
    
    # Step 4: Test the pause system API
    print("Testing pause system API...")
    pause_data = {
        'action': 'pause_system',
        'reason': 'Testing system pause functionality',
        'duration': '15 minutes',
        'notifyUsers': 'on',
        'confirmPause': 'on',
        'csrf_token': csrf_token
    }
    
    print("Sending pause system request...")
    response = session.post(
        urljoin(base_url, "/admin/api/system-maintenance/execute"),
        data=pause_data
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 302:
        print(f"✅ Redirected to: {response.headers.get('Location')}")
        # Follow the redirect to see the result
        redirect_response = session.get(response.headers.get('Location'))
        print(f"Redirect page status: {redirect_response.status_code}")
        
        # Check for flash messages in the redirected page
        if 'alert-success' in redirect_response.text:
            print("✅ Success message found in response")
        elif 'alert-danger' in redirect_response.text or 'alert-error' in redirect_response.text:
            print("❌ Error message found in response")
        else:
            print("⚠️ No clear success/error message found")
            
        return True
    elif response.status_code == 200:
        try:
            result = response.json()
            print(f"JSON response: {result}")
            if result.get('success'):
                print("✅ Pause system successful")
                return True
            else:
                print(f"❌ Pause system failed: {result.get('message')}")
                return False
        except:
            print("❌ Non-JSON response received")
            print(f"Response text: {response.text[:500]}")
            return False
    else:
        print(f"❌ Unexpected response status: {response.status_code}")
        print(f"Response text: {response.text[:500]}")
        return False

if __name__ == "__main__":
    print("=== Testing Pause System Functionality ===")
    success = test_pause_system()
    print("=== Test Complete ===")
    sys.exit(0 if success else 1)