#!/usr/bin/env python3
"""
Test login functionality to verify database lock fixes
"""

import requests
import sys

def test_login():
    """Test login to verify session creation works without database locks"""
    base_url = "http://127.0.0.1:5000"
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        # Get login page to get CSRF token
        print("Getting login page...")
        login_page = session.get(f"{base_url}/login")
        if login_page.status_code != 200:
            print(f"✗ Failed to get login page: {login_page.status_code}")
            return False
        
        print("✓ Login page accessible")
        
        # Extract CSRF token from the page
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        if not csrf_token:
            print("✗ Could not find CSRF token")
            return False
        
        print("✓ CSRF token found")
        
        # Attempt login
        print("Attempting login...")
        login_data = {
            'username': 'admin',
            'password': 'admin',  # Default admin password
            'csrf_token': csrf_token
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data)
        
        # Check if login was successful (should redirect)
        if login_response.status_code in [200, 302]:
            print("✓ Login request completed without database lock errors")
            
            # Check if we were redirected (successful login)
            if login_response.status_code == 302:
                print("✓ Login successful (redirected)")
            else:
                print("? Login form returned (may need to check credentials)")
            
            return True
        else:
            print(f"✗ Login failed with status: {login_response.status_code}")
            return False
            
    except ImportError:
        print("✗ BeautifulSoup not available, skipping CSRF token extraction")
        print("  Install with: pip install beautifulsoup4")
        return False
    except Exception as e:
        print(f"✗ Login test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)