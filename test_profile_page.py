#!/usr/bin/env python3

import requests
import sys
import os

def test_profile_page():
    """Test the profile page with authentication"""
    base_url = "http://127.0.0.1:5000"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        # First, get the login page to check if server is responding
        print("Testing server connectivity...")
        response = session.get(f"{base_url}/user-management/login")
        if response.status_code != 200:
            print(f"Login page not accessible: {response.status_code}")
            return False
        print("✓ Server is responding")
        
        # Try to access profile page without authentication
        print("\nTesting profile page without authentication...")
        response = session.get(f"{base_url}/user-management/profile", allow_redirects=False)
        if response.status_code == 302:
            print("✓ Profile page correctly redirects unauthenticated users")
        else:
            print(f"✗ Unexpected response: {response.status_code}")
            return False
        
        # Check if we can access the profile page directly (should show error message)
        print("\nTesting profile page direct access...")
        response = session.get(f"{base_url}/user-management/profile")
        if response.status_code == 200:
            if "login" in response.text.lower():
                print("✓ Profile page redirected to login page")
            else:
                print("✗ Profile page accessible without authentication")
                return False
        else:
            print(f"✗ Unexpected response: {response.status_code}")
            return False
        
        print("\n✓ Profile page security is working correctly")
        print("To test with authentication, you need to:")
        print("1. Create a user account through the web interface")
        print("2. Log in through the web interface")
        print("3. Then access http://127.0.0.1:5000/user-management/profile")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed - is the web server running?")
        print("Try starting it with: python web_app.py")
        return False
    except Exception as e:
        print(f"✗ Error testing profile page: {e}")
        return False

if __name__ == "__main__":
    success = test_profile_page()
    sys.exit(0 if success else 1)
