#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import time

def test_web_interface():
    """Test the actual web interface with real admin credentials"""
    base_url = "http://localhost:5000"
    timeout = 5
    
    # Use a session to maintain cookies like a real browser
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    try:
        print("🔐 Testing admin login...")
        
        # Get login page
        print(f"Getting login page from {base_url}/login...")
        login_page = session.get(f"{base_url}/login", timeout=timeout)
        print(f"Login page response: {login_page.status_code}")
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if not csrf_input:
            print("❌ No CSRF token found")
            return False
        
        csrf_token = csrf_input['value']
        print(f"✅ Got CSRF token: {csrf_token[:20]}...")
        
        # Login with admin credentials
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, timeout=timeout, allow_redirects=False)
        print(f"✅ Login response: {login_response.status_code}")
        
        if login_response.status_code == 302:
            print("✅ Login successful (redirected)")
        else:
            print("❌ Login failed")
            return False
        
        # Test user management access
        print("\n👥 Testing user management access...")
        user_mgmt = session.get(f"{base_url}/user_management", timeout=timeout)
        print(f"✅ User management status: {user_mgmt.status_code}")
        
        if user_mgmt.status_code != 200:
            print("❌ Cannot access user management")
            return False
        
        # Check if we can see the admin user in the table
        if 'admin' in user_mgmt.text and 'iolaire@iolaire.net' in user_mgmt.text:
            print("✅ Can see admin user in user management")
        else:
            print("❌ Cannot see admin user in user management")
        
        print("✅ User management interface is accessible")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_web_interface()
    if success:
        print("\n🎉 Web interface test PASSED!")
    else:
        print("\n💥 Web interface test FAILED!")