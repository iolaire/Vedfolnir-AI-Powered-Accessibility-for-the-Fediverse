#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to check the system metrics endpoint
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """Create an authenticated session for testing"""
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

def test_system_metrics_endpoint():
    """Test the system metrics endpoint"""
    print("=== Testing System Metrics Endpoint ===")
    
    # Create authenticated session
    session, success = create_authenticated_session()
    if not success:
        print("❌ Failed to authenticate")
        return False
    
    # Test the system metrics endpoint
    print("Testing /admin/api/system-metrics endpoint...")
    try:
        response = session.get("http://127.0.0.1:5000/admin/api/system-metrics")
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Endpoint returned JSON data:")
                print(f"Success: {data.get('success')}")
                if data.get('success'):
                    metrics = data.get('metrics', {})
                    print(f"Active jobs: {metrics.get('active_jobs', 'N/A')}")
                    print(f"Completed today: {metrics.get('completed_today', 'N/A')}")
                    print(f"Failed jobs: {metrics.get('failed_jobs', 'N/A')}")
                    print(f"System load: {metrics.get('system_load', 'N/A')}")
                else:
                    print(f"❌ API returned success=false: {data.get('error')}")
            except Exception as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Response text: {response.text[:500]}")
        else:
            print(f"❌ Endpoint returned status {response.status_code}")
            print(f"Response text: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_system_metrics_endpoint()
    sys.exit(0 if success else 1)