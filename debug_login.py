#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug login process to understand the form structure
"""

import requests
import re
from urllib.parse import urljoin

def debug_login():
    """Debug the login process"""
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    
    print("=== Login Debug ===")
    
    # Get login page
    print("1. Getting login page...")
    login_page = session.get(urljoin(base_url, "/login"))
    print(f"Status: {login_page.status_code}")
    print(f"URL: {login_page.url}")
    
    # Look for form action
    form_action_match = re.search(r'<form[^>]*action="([^"]*)"', login_page.text)
    if form_action_match:
        form_action = form_action_match.group(1)
        print(f"Form action: {form_action}")
    else:
        print("No form action found")
    
    # Look for input fields
    input_fields = re.findall(r'<input[^>]*name="([^"]*)"[^>]*>', login_page.text)
    print(f"Input fields found: {input_fields}")
    
    # Look for CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if csrf_match:
        csrf_token = csrf_match.group(1)
        print(f"CSRF token: {csrf_token[:20]}...")
    else:
        print("No CSRF token found")
    
    # Try different login endpoints
    print("\n2. Testing different login endpoints...")
    endpoints = ["/login", "/user-management/login", "/auth/login"]
    
    for endpoint in endpoints:
        try:
            response = session.get(urljoin(base_url, endpoint))
            print(f"{endpoint}: {response.status_code}")
            if response.status_code == 200:
                # Check if it has a login form
                if 'password' in response.text.lower() and 'username' in response.text.lower():
                    print(f"  ✅ Has login form")
                else:
                    print(f"  ❌ No login form")
        except Exception as e:
            print(f"{endpoint}: Error - {e}")
    
    print("\n3. Checking for error messages in login response...")
    # Try a login attempt to see what happens
    login_data = {
        'username_or_email': 'admin',
        'password': 'a[.meG#15n)@H-_<y]5d8TS%',
        'csrf_token': csrf_token if csrf_match else ''
    }
    
    response = session.post(urljoin(base_url, "/login"), data=login_data)
    print(f"Login attempt status: {response.status_code}")
    print(f"Login attempt URL: {response.url}")
    
    # Look for error messages
    error_patterns = [
        r'class="[^"]*error[^"]*"[^>]*>([^<]+)',
        r'class="[^"]*alert[^"]*"[^>]*>([^<]+)',
        r'Invalid.*credentials',
        r'Login.*failed',
        r'Authentication.*failed'
    ]
    
    for pattern in error_patterns:
        matches = re.findall(pattern, response.text, re.IGNORECASE)
        if matches:
            print(f"Error messages found: {matches}")
            break
    else:
        print("No obvious error messages found")
    
    # Check if we're actually logged in by trying to access admin page
    print("\n4. Testing admin access after login attempt...")
    admin_response = session.get(urljoin(base_url, "/admin"))
    print(f"Admin page status: {admin_response.status_code}")
    if admin_response.status_code == 200:
        print("✅ Successfully accessed admin page - login worked!")
    elif admin_response.status_code == 302:
        print(f"🔒 Redirected to: {admin_response.headers.get('Location', 'unknown')}")
    else:
        print(f"❌ Admin access failed: {admin_response.status_code}")

if __name__ == "__main__":
    debug_login()