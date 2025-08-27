#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for /admin/storage/refresh endpoint with proper authentication and CSRF protection.
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """
    Create an authenticated session for testing
    
    Args:
        base_url: The base URL of the web application
        username: Username to login with (default: admin)
    
    Returns:
        tuple: (session, success) where session is requests.Session and success is bool
    """
    session = requests.Session()
    
    # Step 1: Get login page and CSRF token
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
    
    # Step 2: Prompt for password
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Step 3: Login
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

def test_storage_refresh_endpoint():
    """
    Test the /admin/storage/refresh endpoint with proper authentication and CSRF protection
    """
    print("=== Testing /admin/storage/refresh endpoint ===")
    
    base_url = "http://127.0.0.1:5000"
    
    # Create authenticated session
    session, login_success = create_authenticated_session(base_url)
    if not login_success:
        print("❌ Failed to authenticate. Cannot test storage refresh endpoint.")
        return False
    
    # Step 1: Get the storage dashboard page to extract CSRF token
    print("\n1. Getting storage dashboard page...")
    storage_page = session.get(urljoin(base_url, "/admin/storage"))
    if storage_page.status_code != 200:
        print(f"❌ Failed to get storage dashboard: {storage_page.status_code}")
        return False
    
    # Extract CSRF token from the storage page
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', storage_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in storage page")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token from storage page: {csrf_token[:20]}...")
    
    # Step 2: Test the storage refresh endpoint
    print("\n2. Testing storage refresh endpoint...")
    refresh_data = {
        'csrf_token': csrf_token
    }
    
    refresh_response = session.post(
        urljoin(base_url, "/admin/storage/refresh"), 
        data=refresh_data,
        allow_redirects=False  # Don't follow redirects to see the actual response
    )
    
    print(f"Response status: {refresh_response.status_code}")
    print(f"Response headers: {dict(refresh_response.headers)}")
    
    if refresh_response.status_code == 302:
        print(f"✅ Storage refresh successful (redirected to: {refresh_response.headers.get('Location', 'unknown')})")
        
        # Follow the redirect to see the result
        if 'Location' in refresh_response.headers:
            redirect_url = refresh_response.headers['Location']
            # Handle relative URLs
            if redirect_url.startswith('/'):
                redirect_url = urljoin(base_url, redirect_url)
            
            redirect_response = session.get(redirect_url)
            print(f"Redirect page status: {redirect_response.status_code}")
            
            # Check for success message in the redirected page
            if 'Storage data refreshed' in redirect_response.text:
                print("✅ Found success message in redirected page")
            else:
                print("⚠️  No success message found in redirected page")
        
        return True
    elif refresh_response.status_code == 200:
        print("✅ Storage refresh successful (no redirect)")
        return True
    elif refresh_response.status_code == 403:
        print("❌ Storage refresh failed: Forbidden (CSRF or permission issue)")
        print(f"Response content: {refresh_response.text[:500]}...")
        return False
    elif refresh_response.status_code == 500:
        print("❌ Storage refresh failed: Internal Server Error")
        print(f"Response content: {refresh_response.text[:500]}...")
        return False
    else:
        print(f"❌ Storage refresh failed: Unexpected status {refresh_response.status_code}")
        print(f"Response content: {refresh_response.text[:500]}...")
        return False

def main():
    """Main test execution"""
    try:
        success = test_storage_refresh_endpoint()
        if success:
            print("\n✅ Storage refresh endpoint test PASSED")
            return 0
        else:
            print("\n❌ Storage refresh endpoint test FAILED")
            return 1
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())