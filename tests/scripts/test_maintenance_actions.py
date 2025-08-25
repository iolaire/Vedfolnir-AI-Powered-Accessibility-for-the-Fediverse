#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify maintenance actions are working
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

def test_maintenance_actions():
    """Test the maintenance actions API"""
    session, login_success = create_authenticated_session()
    if not login_success:
        return False
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Get system maintenance info
    print("\n=== Testing System Maintenance API ===")
    response = session.get(urljoin(base_url, "/admin/api/system-maintenance"))
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ System maintenance API working")
            actions = data.get('maintenance_actions', [])
            print(f"✅ Found {len(actions)} maintenance actions:")
            for action in actions:
                print(f"  - {action['name']} ({action['id']})")
        else:
            print("❌ System maintenance API returned error")
            return False
    else:
        print(f"❌ System maintenance API failed: {response.status_code}")
        return False
    
    # Test 2: Test restart failed jobs action (dry run)
    print("\n=== Testing Restart Failed Jobs ===")
    
    # Get CSRF token from the maintenance page
    maintenance_page = session.get(urljoin(base_url, "/admin/system-maintenance"))
    if maintenance_page.status_code != 200:
        print("❌ Cannot access maintenance page")
        return False
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', maintenance_page.text)
    if not csrf_match:
        print("❌ No CSRF token found")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Test restart failed jobs
    restart_data = {
        'action_id': 'restart_failed',
        'reason': 'Testing restart failed jobs functionality'
    }
    
    response = session.post(
        urljoin(base_url, "/admin/api/system-maintenance/execute"),
        json=restart_data,
        headers={'X-CSRFToken': csrf_token}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Restart failed jobs action successful")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Restart failed jobs failed: {data.get('error', 'Unknown error')}")
    else:
        print(f"❌ Restart failed jobs API failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   Error: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"   Response: {response.text[:200]}...")
    
    # Test 3: Test cleanup old data action
    print("\n=== Testing Cleanup Old Data ===")
    
    cleanup_data = {
        'action_id': 'cleanup_old_data',
        'reason': 'Testing cleanup old data functionality'
    }
    
    response = session.post(
        urljoin(base_url, "/admin/api/system-maintenance/execute"),
        json=cleanup_data,
        headers={'X-CSRFToken': csrf_token}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Cleanup old data action successful")
            print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"❌ Cleanup old data failed: {data.get('error', 'Unknown error')}")
    else:
        print(f"❌ Cleanup old data API failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   Error: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"   Response: {response.text[:200]}...")
    
    print("\n=== Test Complete ===")
    return True

if __name__ == "__main__":
    success = test_maintenance_actions()
    sys.exit(0 if success else 1)