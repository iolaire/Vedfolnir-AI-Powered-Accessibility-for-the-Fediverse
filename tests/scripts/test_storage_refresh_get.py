#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test GET request to /admin/storage/refresh endpoint with authentication.
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """Create an authenticated session for testing"""
    session = requests.Session()
    
    # Get login page and CSRF token
    print(f"Getting login page for user: {username}")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return session, False
    
    # Extract CSRF token from meta tag
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return session, False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Prompt for password
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Login
    print(f"Logging in as {username}...")
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    # Check if login was successful
    if login_response.status_code == 302:
        print("✅ Successfully logged in (redirected)")
        return session, True
    elif login_response.status_code == 200:
        if 'login' in login_response.url.lower():
            print("❌ Login failed: Still on login page")
            return session, False
        else:
            print("✅ Successfully logged in")
            return session, True
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        return session, False

def test_storage_refresh_get():
    """Test GET request to /admin/storage/refresh"""
    print("=== Testing GET /admin/storage/refresh endpoint ===")
    
    base_url = "http://127.0.0.1:5000"
    
    # Create authenticated session
    session, login_success = create_authenticated_session(base_url)
    if not login_success:
        print("❌ Failed to authenticate. Cannot test storage refresh endpoint.")
        return False
    
    # Test GET request to storage refresh
    print("\nTesting GET request to storage refresh...")
    refresh_response = session.get(
        urljoin(base_url, "/admin/storage/refresh"), 
        allow_redirects=False
    )
    
    print(f"Response status: {refresh_response.status_code}")
    
    if refresh_response.status_code == 302:
        redirect_location = refresh_response.headers.get('Location', '')
        print(f"✅ GET request handled correctly (redirected to: {redirect_location})")
        
        # Follow the redirect to see the message
        if redirect_location.startswith('/'):
            redirect_url = urljoin(base_url, redirect_location)
        else:
            redirect_url = redirect_location
            
        redirect_response = session.get(redirect_url)
        print(f"Redirect page status: {redirect_response.status_code}")
        
        # Check for info message
        if 'Use the refresh button' in redirect_response.text:
            print("✅ Found expected info message in redirected page")
        else:
            print("⚠️  Expected info message not found")
        
        return True
    else:
        print(f"❌ Unexpected response status: {refresh_response.status_code}")
        return False

def main():
    """Main test execution"""
    try:
        success = test_storage_refresh_get()
        if success:
            print("\n✅ GET storage refresh endpoint test PASSED")
            return 0
        else:
            print("\n❌ GET storage refresh endpoint test FAILED")
            return 1
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())