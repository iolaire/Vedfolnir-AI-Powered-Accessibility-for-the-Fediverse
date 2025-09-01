#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test login functionality for Vedfolnir web application
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def test_web_app_accessibility():
    """Test if the web application is accessible"""
    base_url = "http://127.0.0.1:5000"
    
    try:
        print("🔍 Testing web application accessibility...")
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Web application is accessible")
            return True
        else:
            print(f"❌ Web application returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to web application. Is it running on http://127.0.0.1:5000?")
        return False
    except Exception as e:
        print(f"❌ Error accessing web application: {e}")
        return False

def test_login_page():
    """Test if the login page is accessible and has required elements"""
    base_url = "http://127.0.0.1:5000"
    
    try:
        print("🔍 Testing login page accessibility...")
        response = requests.get(urljoin(base_url, "/login"), timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Login page returned status code: {response.status_code}")
            return False
        
        # Check for login form elements
        content = response.text
        
        # Check for username/email field
        if 'name="username_or_email"' not in content and 'name="username"' not in content:
            print("❌ Login form missing username/email field")
            return False
        
        # Check for password field
        if 'name="password"' not in content:
            print("❌ Login form missing password field")
            return False
        
        # Check for CSRF token
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', content)
        if not csrf_match:
            print("⚠️  No CSRF token found (may be disabled for testing)")
        else:
            print("✅ CSRF token found in login page")
        
        print("✅ Login page is accessible and has required form elements")
        return True
        
    except Exception as e:
        print(f"❌ Error testing login page: {e}")
        return False

def test_login_functionality():
    """Test actual login functionality with user credentials"""
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    try:
        print("🔍 Testing login functionality...")
        
        # Get login page and extract CSRF token
        login_page = session.get(urljoin(base_url, "/login"))
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token
        csrf_token = None
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            print(f"✅ Got CSRF token: {csrf_token[:20]}...")
        
        # Get admin credentials
        username = input("Enter username (default: admin): ").strip() or "admin"
        password = getpass.getpass(f"Enter password for {username}: ")
        
        # Prepare login data
        login_data = {
            'username_or_email': username,
            'password': password
        }
        
        # Add CSRF token if available
        if csrf_token:
            login_data['csrf_token'] = csrf_token
        
        # Attempt login
        print(f"🔐 Attempting login as {username}...")
        login_response = session.post(urljoin(base_url, "/login"), data=login_data)
        
        # Check login result
        if login_response.status_code == 302:
            # Successful login (redirect)
            print("✅ Login successful (redirected)")
            
            # Test accessing a protected page
            dashboard_response = session.get(base_url)
            if dashboard_response.status_code == 200:
                print("✅ Can access dashboard after login")
                
                # Check if we're actually logged in (look for logout link or user info)
                if 'logout' in dashboard_response.text.lower() or 'dashboard' in dashboard_response.text.lower():
                    print("✅ Login verification successful - user is authenticated")
                    return True
                else:
                    print("⚠️  Login may have failed - no logout link found")
                    return False
            else:
                print(f"❌ Cannot access dashboard after login: {dashboard_response.status_code}")
                return False
                
        elif login_response.status_code == 200:
            # Still on login page - check for error messages
            if 'login' in login_response.url.lower():
                print("❌ Login failed - still on login page")
                if 'invalid' in login_response.text.lower() or 'error' in login_response.text.lower():
                    print("   Possible reason: Invalid credentials")
                return False
            else:
                print("✅ Login successful")
                return True
        else:
            print(f"❌ Login failed with status code: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during login test: {e}")
        return False

def main():
    """Main test execution"""
    print("=== Vedfolnir Web Application Login Test ===")
    print()
    
    # Test 1: Web application accessibility
    if not test_web_app_accessibility():
        print("\n❌ Web application is not accessible. Please ensure it's running:")
        print("   python web_app.py & sleep 10")
        return False
    
    print()
    
    # Test 2: Login page accessibility
    if not test_login_page():
        print("\n❌ Login page test failed")
        return False
    
    print()
    
    # Test 3: Login functionality
    if not test_login_functionality():
        print("\n❌ Login functionality test failed")
        return False
    
    print()
    print("✅ All login tests passed successfully!")
    print("🎉 Web application is working correctly and login functionality is operational")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)