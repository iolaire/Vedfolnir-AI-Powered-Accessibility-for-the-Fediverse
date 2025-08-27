#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for storage override functionality
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

def test_override_status(session, base_url="http://127.0.0.1:5000"):
    """Test storage override status API"""
    print("\n=== Testing Override Status ===")
    
    # Test override status API endpoint
    status_url = urljoin(base_url, "/admin/storage/api/override/status")
    response = session.get(status_url)
    
    if response.status_code == 200:
        print("✅ Override status API accessible")
        try:
            status_data = response.json()
            if 'override_active' in status_data:
                print(f"✅ Override active: {status_data['override_active']}")
            if 'expires_at' in status_data:
                print(f"✅ Expires at: {status_data.get('expires_at', 'N/A')}")
            if 'reason' in status_data:
                print(f"✅ Reason: {status_data.get('reason', 'N/A')}")
            return True
        except Exception as e:
            print(f"❌ Failed to parse status JSON: {e}")
            return False
    else:
        print(f"❌ Override status API failed: {response.status_code}")
        return False

def test_override_statistics(session, base_url="http://127.0.0.1:5000"):
    """Test storage override statistics API"""
    print("\n=== Testing Override Statistics ===")
    
    # Test override statistics API endpoint
    stats_url = urljoin(base_url, "/admin/storage/api/override/statistics")
    response = session.get(stats_url)
    
    if response.status_code == 200:
        print("✅ Override statistics API accessible")
        try:
            stats_data = response.json()
            if 'total_overrides' in stats_data:
                print(f"✅ Total overrides: {stats_data['total_overrides']}")
            if 'active_overrides' in stats_data:
                print(f"✅ Active overrides: {stats_data['active_overrides']}")
            if 'recent_overrides' in stats_data:
                print(f"✅ Recent overrides: {len(stats_data['recent_overrides'])}")
            return True
        except Exception as e:
            print(f"❌ Failed to parse statistics JSON: {e}")
            return False
    else:
        print(f"❌ Override statistics API failed: {response.status_code}")
        return False

def test_override_page_access(session, base_url="http://127.0.0.1:5000"):
    """Test storage override page access"""
    print("\n=== Testing Override Page Access ===")
    
    # Test override page access
    override_url = urljoin(base_url, "/admin/storage/override")
    response = session.get(override_url)
    
    if response.status_code == 200:
        print("✅ Storage override page accessible")
        
        # Check for override management section
        if "Storage Override Management" in response.text:
            print("✅ Override management section found")
        else:
            print("⚠️ Override management section not found")
            
        # Check for current storage status
        if "Current Storage Status" in response.text:
            print("✅ Storage status section found")
        else:
            print("⚠️ Storage status section not found")
            
        # Check for override status section
        if "Override Status" in response.text:
            print("✅ Override status section found")
        else:
            print("⚠️ Override status section not found")
            
        return True
    else:
        print(f"❌ Storage override page access failed: {response.status_code}")
        return False

def test_override_form_availability(session, base_url="http://127.0.0.1:5000"):
    """Test override form availability logic"""
    print("\n=== Testing Override Form Availability ===")
    
    # Get override page to check form logic
    override_url = urljoin(base_url, "/admin/storage/override")
    response = session.get(override_url)
    
    if response.status_code != 200:
        print(f"❌ Could not access override page: {response.status_code}")
        return False
    
    # Check for correct conditional display
    if "Storage override is not needed - storage usage is within normal limits" in response.text:
        print("✅ Override form correctly hidden when storage is within limits")
        return True
    elif 'name="reason"' in response.text and 'name="duration_hours"' in response.text:
        print("✅ Override form correctly displayed when storage limits exceeded")
        return True
    else:
        print("⚠️ Override form logic unclear - checking for basic structure")
        
        # Check for basic page structure
        if "Storage Override Management" in response.text:
            print("✅ Override page structure looks correct")
            return True
        else:
            print("❌ Override page structure incomplete")
            return False

def main():
    """Main test execution"""
    print("=== Storage Override Test Suite ===")
    
    # Create authenticated session
    session, success = create_authenticated_session()
    if not success:
        print("❌ Authentication failed - cannot continue tests")
        return False
    
    # Run all tests
    tests = [
        test_override_status,
        test_override_statistics,
        test_override_page_access,
        test_override_form_availability
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func(session)
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print(f"\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All storage override tests passed!")
        return True
    else:
        print("❌ Some storage override tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)