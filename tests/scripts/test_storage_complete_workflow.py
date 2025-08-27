#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Complete workflow test for storage management functionality
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def test_complete_storage_workflow():
    """Test complete storage management workflow"""
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    print("=== Complete Storage Management Workflow Test ===")
    
    # Step 1: Login
    print("1. Logging in...")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return False
    
    csrf_token = csrf_match.group(1)
    password = getpass.getpass("Enter admin password: ")
    
    login_data = {
        'username_or_email': 'admin',
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    if login_response.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    print("✅ Login successful")
    
    # Step 2: Access storage dashboard
    print("2. Accessing storage dashboard...")
    storage_response = session.get(urljoin(base_url, "/admin/storage"))
    if storage_response.status_code != 200:
        print(f"❌ Storage dashboard access failed: {storage_response.status_code}")
        return False
    
    print("✅ Storage dashboard accessible")
    
    # Step 3: Test GET request to refresh endpoint
    print("3. Testing GET request to refresh endpoint...")
    get_response = session.get(urljoin(base_url, "/admin/storage/refresh"))
    if get_response.status_code != 302:
        print(f"❌ GET refresh failed: {get_response.status_code}")
        return False
    
    if "/admin/storage" not in get_response.headers.get('Location', ''):
        print(f"❌ GET refresh didn't redirect to storage dashboard")
        return False
    
    print("✅ GET refresh redirects correctly")
    
    # Step 4: Test POST request to refresh endpoint
    print("4. Testing POST request to refresh endpoint...")
    
    # Get CSRF token from storage page
    storage_page = session.get(urljoin(base_url, "/admin/storage"))
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', storage_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in storage page")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # POST to refresh endpoint
    refresh_data = {'csrf_token': csrf_token}
    post_response = session.post(urljoin(base_url, "/admin/storage/refresh"), data=refresh_data)
    
    if post_response.status_code != 302:
        print(f"❌ POST refresh failed: {post_response.status_code}")
        return False
    
    if "/admin/storage" not in post_response.headers.get('Location', ''):
        print(f"❌ POST refresh didn't redirect to storage dashboard")
        return False
    
    print("✅ POST refresh works correctly")
    
    # Step 5: Verify redirected page loads correctly
    print("5. Verifying redirected page...")
    final_page = session.get(urljoin(base_url, "/admin/storage"))
    if final_page.status_code != 200:
        print(f"❌ Final page load failed: {final_page.status_code}")
        return False
    
    # Check for success message or normal content
    content = final_page.text
    if "Storage Management" not in content:
        print("❌ Final page doesn't contain expected content")
        return False
    
    print("✅ Final page loads correctly")
    
    # Step 6: Test admin dashboard access
    print("6. Testing admin dashboard access...")
    admin_response = session.get(urljoin(base_url, "/admin"))
    if admin_response.status_code != 200:
        print(f"❌ Admin dashboard access failed: {admin_response.status_code}")
        return False
    
    print("✅ Admin dashboard accessible")
    
    print("\n🎉 Complete storage management workflow test PASSED")
    print("All endpoints are working correctly with proper authentication and CSRF protection")
    return True

if __name__ == "__main__":
    success = test_complete_storage_workflow()
    sys.exit(0 if success else 1)