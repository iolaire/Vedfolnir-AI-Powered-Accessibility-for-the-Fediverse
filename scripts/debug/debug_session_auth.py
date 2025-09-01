#!/usr/bin/env python3
"""
Debug script to test session authentication
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def test_session_auth():
    """Test session authentication for API endpoints"""
    
    session = requests.Session()
    base_url = "http://127.0.0.1:5000"
    
    # Step 1: Get login page and CSRF token
    print("Getting login page...")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    # Extract CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Login
    password = getpass.getpass("Enter admin password: ")
    login_data = {
        'username_or_email': 'admin',
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data, allow_redirects=False)
    print(f"Login response: {login_response.status_code}")
    
    if login_response.status_code != 302:
        print("❌ Login failed")
        return False
    
    print("✅ Login successful")
    
    # Step 3: Test regular admin page (should work)
    print("\nTesting regular admin page...")
    admin_response = session.get(urljoin(base_url, "/admin/dashboard"))
    print(f"Admin dashboard: {admin_response.status_code}")
    
    # Step 4: Test API endpoints
    print("\nTesting API endpoints...")
    
    # Test categories (working)
    categories_response = session.get(urljoin(base_url, "/admin/api/configuration/categories"))
    print(f"Categories API: {categories_response.status_code}")
    
    # Test configurations (failing)
    configs_response = session.get(urljoin(base_url, "/admin/api/configuration/"))
    print(f"Configurations API: {configs_response.status_code}")
    
    if configs_response.status_code != 200:
        print("Response content:", configs_response.text[:200])
    
    # Step 5: Test a simple debug endpoint to see session data
    print("\nTesting debug endpoint...")
    debug_response = session.get(urljoin(base_url, "/debug/session"))
    print(f"Debug session: {debug_response.status_code}")
    if debug_response.status_code == 200:
        print("Session data:", debug_response.text[:500])

if __name__ == "__main__":
    test_session_auth()