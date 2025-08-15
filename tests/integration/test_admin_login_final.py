#!/usr/bin/env python3
"""
Test admin login with correct password and access to System Health dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from urllib.parse import urljoin

def test_admin_access_final():
    """Test admin access with correct password"""
    
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    try:
        # Step 1: Get login page
        print("Step 1: Getting login page...")
        login_page = session.get(urljoin(base_url, "/login"))
        print(f"Login page status: {login_page.status_code}")
        
        if login_page.status_code != 200:
            print(f"ERROR: Cannot access login page")
            return False
        
        # Step 2: Extract CSRF token
        print("Step 2: Extracting CSRF token...")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if not csrf_input:
                print("ERROR: CSRF token not found in login page")
                return False
            csrf_token = csrf_input.get('value')
            print(f"CSRF token found: {csrf_token[:20]}...")
        except ImportError:
            print("WARNING: BeautifulSoup not available, skipping CSRF token")
            csrf_token = ""
        
        # Step 3: Login as admin with correct password
        print("Step 3: Logging in as admin...")
        login_data = {
            'username': 'admin',
            'password': 'RPYMFCKE<$dOu_D)pe;Q_5;j',  # Correct admin password
            'csrf_token': csrf_token
        }
        
        login_response = session.post(urljoin(base_url, "/login"), data=login_data, allow_redirects=True)
        print(f"Login response status: {login_response.status_code}")
        print(f"Final URL after login: {login_response.url}")
        
        # Check if login was successful
        if 'login' in login_response.url:
            print("ERROR: Login failed - still on login page")
            # Check for error messages
            try:
                soup = BeautifulSoup(login_response.text, 'html.parser')
                flash_messages = soup.find_all(class_=['alert', 'flash-message', 'error', 'danger'])
                if flash_messages:
                    print("Error messages:")
                    for msg in flash_messages:
                        print(f"  - {msg.get_text().strip()}")
            except:
                pass
            return False
        else:
            print("SUCCESS: Login successful - redirected to dashboard")
        
        # Step 4: Try to access health dashboard
        print("Step 4: Accessing health dashboard...")
        health_response = session.get(urljoin(base_url, "/health/dashboard"), allow_redirects=False)
        print(f"Health dashboard status: {health_response.status_code}")
        
        if health_response.status_code == 200:
            print("SUCCESS: Admin can access System Health dashboard!")
            print("✅ ISSUE RESOLVED: Admin role identification working correctly")
            return True
        elif health_response.status_code == 302:
            redirect_location = health_response.headers.get('Location', '')
            print(f"ERROR: Health dashboard redirected to: {redirect_location}")
            if 'login' in redirect_location:
                print("  - Session may have expired or authentication failed")
            elif 'platform' in redirect_location:
                print("  - Still being redirected to platform setup (this was the original issue)")
            return False
        else:
            print(f"ERROR: Unexpected health dashboard status: {health_response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to web application. Is it running on localhost:5000?")
        return False
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        return False

if __name__ == '__main__':
    print("Testing admin access to System Health dashboard...")
    print("=" * 50)
    success = test_admin_access_final()
    print("=" * 50)
    if success:
        print("🎉 TEST PASSED: Admin can access System Health dashboard")
    else:
        print("❌ TEST FAILED: Admin cannot access System Health dashboard")
    sys.exit(0 if success else 1)