#!/usr/bin/env python3

import requests
import sys
import re
from bs4 import BeautifulSoup

def test_profile_with_login():
    """Test the profile page with actual login"""
    base_url = "http://127.0.0.1:5000"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    try:
        print("Testing profile page with authentication...")
        
        # Get login page and extract CSRF token
        print("1. Getting login page...")
        response = session.get(f"{base_url}/user-management/login")
        if response.status_code != 200:
            print(f"✗ Login page not accessible: {response.status_code}")
            return False
        
        # Parse CSRF token from login form
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
            print(f"✓ CSRF token found: {csrf_token[:20]}...")
        else:
            print("⚠ No CSRF token found, proceeding without it")
        
        # Try to login with admin user
        print("2. Attempting login...")
        login_data = {
            'username_or_email': 'admin',
            'password': 'admin123',  # Default admin password
        }
        if csrf_token:
            login_data['csrf_token'] = csrf_token
        
        response = session.post(f"{base_url}/user-management/login", data=login_data)
        
        # Check if login was successful (should redirect)
        if response.status_code == 200 and "login" in response.url.lower():
            print("✗ Login failed - still on login page")
            # Try to find error message
            soup = BeautifulSoup(response.text, 'html.parser')
            error_divs = soup.find_all('div', class_=['alert-danger', 'error', 'notification'])
            if error_divs:
                for div in error_divs:
                    print(f"   Error: {div.get_text().strip()}")
            return False
        elif response.status_code in [200, 302]:
            print("✓ Login appears successful")
        else:
            print(f"✗ Unexpected login response: {response.status_code}")
            return False
        
        # Now test the profile page
        print("3. Testing profile page...")
        response = session.get(f"{base_url}/user-management/profile")
        
        if response.status_code != 200:
            print(f"✗ Profile page returned status: {response.status_code}")
            return False
        
        # Check if profile page loaded correctly
        if "Unable to load profile data" in response.text:
            print("✗ Profile page shows error: 'Unable to load profile data'")
            print("   This indicates the profile_data is None in the template")
            
            # Look for more specific error information
            soup = BeautifulSoup(response.text, 'html.parser')
            alert_divs = soup.find_all('div', class_='alert-danger')
            for div in alert_divs:
                print(f"   Alert: {div.get_text().strip()}")
            
            return False
        elif "User Profile" in response.text:
            print("✓ Profile page loaded successfully")
            
            # Check if profile data is displayed
            soup = BeautifulSoup(response.text, 'html.parser')
            username_cells = soup.find_all('td')
            profile_data_found = False
            for cell in username_cells:
                if 'admin' in cell.get_text():
                    profile_data_found = True
                    break
            
            if profile_data_found:
                print("✓ Profile data is being displayed")
            else:
                print("⚠ Profile page loaded but no profile data visible")
            
            return True
        else:
            print("✗ Profile page content unexpected")
            print(f"   Response length: {len(response.text)} characters")
            return False
        
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed - is the web server running?")
        return False
    except Exception as e:
        print(f"✗ Error testing profile page: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_profile_with_login()
    sys.exit(0 if success else 1)
