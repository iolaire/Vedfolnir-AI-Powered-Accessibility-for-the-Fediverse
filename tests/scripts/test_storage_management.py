#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for storage management functionality
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

def test_storage_dashboard(session, base_url="http://127.0.0.1:5000"):
    """Test storage dashboard access"""
    print("\n=== Testing Storage Dashboard ===")
    
    # Test storage dashboard access
    dashboard_url = urljoin(base_url, "/admin/storage")
    response = session.get(dashboard_url)
    
    if response.status_code == 200:
        print("✅ Storage dashboard accessible")
        
        # Check for storage metrics in the response
        if "Storage Usage" in response.text:
            print("✅ Storage usage metrics displayed")
        else:
            print("⚠️ Storage usage metrics not found in dashboard")
            
        if "Storage Configuration" in response.text:
            print("✅ Storage configuration section found")
        else:
            print("⚠️ Storage configuration section not found")
            
        return True
    else:
        print(f"❌ Storage dashboard access failed: {response.status_code}")
        return False

def test_storage_refresh(session, base_url="http://127.0.0.1:5000"):
    """Test storage refresh functionality"""
    print("\n=== Testing Storage Refresh ===")
    
    # Test GET request to refresh endpoint (should redirect)
    refresh_url = urljoin(base_url, "/admin/storage/refresh")
    response = session.get(refresh_url, allow_redirects=False)
    
    if response.status_code == 302:
        print("✅ GET request to refresh endpoint redirects properly")
    else:
        print(f"⚠️ GET request to refresh endpoint returned: {response.status_code}")
    
    # Test POST request to refresh endpoint
    # First get CSRF token from storage dashboard
    dashboard_url = urljoin(base_url, "/admin/storage")
    dashboard_response = session.get(dashboard_url)
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', dashboard_response.text)
    if not csrf_match:
        print("❌ Could not find CSRF token for refresh test")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # POST to refresh endpoint
    refresh_data = {'csrf_token': csrf_token}
    response = session.post(refresh_url, data=refresh_data)
    
    if response.status_code in [200, 302]:
        print("✅ POST request to refresh endpoint successful")
        return True
    else:
        print(f"❌ POST request to refresh endpoint failed: {response.status_code}")
        return False

def test_storage_data_api(session, base_url="http://127.0.0.1:5000"):
    """Test storage data API"""
    print("\n=== Testing Storage Data API ===")
    
    # Test storage data API endpoint
    data_url = urljoin(base_url, "/admin/storage/api/data")
    response = session.get(data_url)
    
    if response.status_code == 200:
        print("✅ Storage data API accessible")
        try:
            data = response.json()
            if 'storage_usage' in data:
                usage = data['storage_usage']
                print(f"✅ Current usage: {usage.get('current_usage_gb', 'N/A')} GB")
                print(f"✅ Max storage: {usage.get('max_storage_gb', 'N/A')} GB")
                print(f"✅ Usage percentage: {usage.get('usage_percentage', 'N/A')}%")
            if 'storage_status' in data:
                status = data['storage_status']
                print(f"✅ Storage status: {status.get('status', 'N/A')}")
                print(f"✅ Storage blocked: {status.get('is_blocked', 'N/A')}")
            return True
        except Exception as e:
            print(f"❌ Failed to parse data JSON: {e}")
            return False
    else:
        print(f"❌ Storage data API failed: {response.status_code}")
        return False

def test_storage_health(session, base_url="http://127.0.0.1:5000"):
    """Test storage health endpoint"""
    print("\n=== Testing Storage Health ===")
    
    # Test storage health endpoint
    health_url = urljoin(base_url, "/admin/storage/health")
    response = session.get(health_url)
    
    if response.status_code == 200:
        print("✅ Storage health endpoint accessible")
        try:
            health_data = response.json()
            if 'storage_health' in health_data:
                health = health_data['storage_health']
                print(f"✅ Health status: {health.get('status', 'N/A')}")
                print(f"✅ Monitoring enabled: {health.get('monitoring_enabled', 'N/A')}")
            return True
        except Exception as e:
            print(f"❌ Failed to parse health JSON: {e}")
            return False
    else:
        print(f"❌ Storage health endpoint failed: {response.status_code}")
        return False

def main():
    """Main test execution"""
    print("=== Storage Management Test Suite ===")
    
    # Create authenticated session
    session, success = create_authenticated_session()
    if not success:
        print("❌ Authentication failed - cannot continue tests")
        return False
    
    # Run all tests
    tests = [
        test_storage_dashboard,
        test_storage_refresh,
        test_storage_data_api,
        test_storage_health
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
        print("✅ All storage management tests passed!")
        return True
    else:
        print("❌ Some storage management tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)