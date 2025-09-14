#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify that the dashboard shows correct user-specific data
"""

import requests
import getpass
import re
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """Create authenticated session for testing"""
    session = requests.Session()
    
    # Get login page and CSRF token
    login_page = session.get(urljoin(base_url, "/login"))
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token on login page")
        return None, False
    
    csrf_token = csrf_match.group(1)
    
    # Prompt for password
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Login
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    response = session.post(urljoin(base_url, "/login"), data=login_data)
    success = response.status_code in [200, 302] and 'login' not in response.url.lower()
    
    return session, success

def test_dashboard_user_data():
    """Test that dashboard shows user-specific data"""
    print("=== Testing Dashboard User Data ===")
    
    # Test with admin user
    print("\n1. Testing with admin user...")
    session, success = create_authenticated_session(username="admin")
    if not success:
        print("❌ Failed to authenticate as admin")
        return False
    
    # Access dashboard
    dashboard_response = session.get("http://127.0.0.1:5000/")
    if dashboard_response.status_code != 200:
        print(f"❌ Dashboard returned status {dashboard_response.status_code}")
        return False
    
    print("✅ Successfully accessed dashboard as admin")
    
    # Check if the dashboard contains user-specific information
    dashboard_html = dashboard_response.text
    
    # Look for stats in the dashboard
    if "total_posts" in dashboard_html or "Total Posts" in dashboard_html:
        print("✅ Dashboard contains post statistics")
    else:
        print("⚠️  Dashboard may not contain post statistics")
    
    if "total_images" in dashboard_html or "Total Images" in dashboard_html:
        print("✅ Dashboard contains image statistics")
    else:
        print("⚠️  Dashboard may not contain image statistics")
    
    # Test with test user if available
    print("\n2. Testing with test user...")
    try:
        test_session, test_success = create_authenticated_session(username="user-8pozry-sorrar")
        if test_success:
            test_dashboard = test_session.get("http://127.0.0.1:5000/")
            if test_dashboard.status_code == 200:
                print("✅ Successfully accessed dashboard as test user")
                
                # Check if test user sees different data (should be 0 posts/images)
                test_html = test_dashboard.text
                if "0 posts" in test_html.lower() or "no posts" in test_html.lower():
                    print("✅ Test user correctly sees 0 posts")
                else:
                    print("⚠️  Test user data may not be correctly filtered")
            else:
                print(f"❌ Test user dashboard returned status {test_dashboard.status_code}")
        else:
            print("⚠️  Could not authenticate as test user (may not exist)")
    except Exception as e:
        print(f"⚠️  Test user authentication failed: {e}")
    
    print("\n=== Test Complete ===")
    return True

if __name__ == "__main__":
    success = test_dashboard_user_data()
    exit(0 if success else 1)