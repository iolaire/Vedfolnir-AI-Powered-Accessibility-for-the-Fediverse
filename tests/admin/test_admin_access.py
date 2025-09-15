#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test admin access and template serving
"""

import requests
import re
from urllib.parse import urljoin

def test_admin_access():
    """Test admin access and verify correct template is served"""
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    
    print("=== Testing Admin Access ===")
    
    # Step 1: Get login page
    print("1. Getting login page...")
    login_page = session.get(urljoin(base_url, "/login"))
    print(f"Login page status: {login_page.status_code}")
    print(f"Login page URL: {login_page.url}")
    
    # Extract CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    print(f"CSRF token found: {'Yes' if csrf_token else 'No'}")
    
    # Step 2: Login
    print("\n2. Attempting login...")
    login_data = {
        'username_or_email': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    print(f"Login response status: {login_response.status_code}")
    print(f"Login response URL: {login_response.url}")
    
    # Step 3: Test admin access
    print("\n3. Testing admin access...")
    admin_response = session.get(urljoin(base_url, "/admin"))
    print(f"Admin page status: {admin_response.status_code}")
    print(f"Admin page URL: {admin_response.url}")
    
    if admin_response.status_code == 200:
        print("✅ Successfully accessed admin page")
        
        # Check if it's actually the admin page
        if 'Admin Dashboard' in admin_response.text or 'admin' in admin_response.text.lower():
            print("✅ Admin page content confirmed")
        else:
            print("❌ Admin page content not found")
            
    else:
        print(f"❌ Failed to access admin page: {admin_response.status_code}")
    
    # Step 4: Test job management page specifically
    print("\n4. Testing job management page...")
    job_mgmt_response = session.get(urljoin(base_url, "/admin/job-management"))
    print(f"Job management status: {job_mgmt_response.status_code}")
    print(f"Job management URL: {job_mgmt_response.url}")
    
    if job_mgmt_response.status_code == 200:
        # Check page title
        title_match = re.search(r'<title>([^<]+)</title>', job_mgmt_response.text)
        title = title_match.group(1) if title_match else 'No title found'
        print(f"Page title: {title}")
        
        # Check for job management content
        if 'Job Management' in job_mgmt_response.text:
            print("✅ Job management page content confirmed")
            
            # Check for our specific fixes
            has_data_actions = 'data-action=' in job_mgmt_response.text
            has_onclick = 'onclick=' in job_mgmt_response.text
            has_setup_function = 'setupJobActionEventListeners' in job_mgmt_response.text
            
            print(f"Has data-action attributes: {'✅' if has_data_actions else '❌'}")
            print(f"Has onclick handlers: {'❌' if has_onclick else '✅'} (should be No)")
            print(f"Has setup function: {'✅' if has_setup_function else '❌'}")
            
            if has_data_actions and not has_onclick and has_setup_function:
                print("✅ CSP fix is properly deployed!")
            else:
                print("❌ CSP fix is not properly deployed")
                
        else:
            print("❌ Job management page content not found")
            print("Page content preview:", job_mgmt_response.text[:500])
    else:
        print(f"❌ Failed to access job management page: {job_mgmt_response.status_code}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_admin_access()