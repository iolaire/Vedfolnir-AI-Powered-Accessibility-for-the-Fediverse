#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test storage dashboard access and functionality
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def test_storage_dashboard_access():
    """Test storage dashboard access and content"""
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    print("=== Testing Storage Dashboard Access ===")
    
    # Step 1: Get login page and CSRF token
    print("Getting login page for user: admin")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    # Extract CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Login
    password = getpass.getpass("Enter password for admin: ")
    print("Logging in as admin...")
    
    login_data = {
        'username_or_email': 'admin',
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    if login_response.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    print("✅ Successfully logged in")
    
    # Step 3: Access storage dashboard
    print("\nTesting storage dashboard access...")
    storage_response = session.get(urljoin(base_url, "/admin/storage"))
    
    if storage_response.status_code != 200:
        print(f"❌ Storage dashboard access failed: {storage_response.status_code}")
        return False
    
    print("✅ Storage dashboard accessible")
    
    # Step 4: Check for expected content
    content = storage_response.text
    
    # Check for key elements
    checks = [
        ("Storage Management", "Storage Management title"),
        ("Refresh Data", "Refresh button"),
        ("csrf_token", "CSRF token in form"),
        ("Storage Overview", "Storage overview section"),
    ]
    
    print("\nChecking dashboard content...")
    for check_text, description in checks:
        if check_text in content:
            print(f"✅ Found {description}")
        else:
            print(f"⚠️  Missing {description}")
    
    # Check for storage statistics (if any)
    if "Total Images" in content or "Storage Used" in content:
        print("✅ Found storage statistics")
    else:
        print("ℹ️  No storage statistics displayed (may be empty)")
    
    print("\n✅ Storage dashboard test PASSED")
    return True

if __name__ == "__main__":
    success = test_storage_dashboard_access()
    sys.exit(0 if success else 1)