#!/usr/bin/env python3
"""
Debug Login Issue

Simple script to test login functionality and identify issues.
"""

import requests
import time
from bs4 import BeautifulSoup

def extract_csrf_token(html_content):
    """Extract CSRF token from HTML form"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # First try hidden input field
        csrf_input = soup.find('input', {'name': 'csrf_token', 'type': 'hidden'})
        if csrf_input:
            return csrf_input.get('value')
        
        # Try any csrf_token input
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            return csrf_input.get('value')
        
        return None
    except Exception as e:
        print(f"   Error extracting CSRF token: {e}")
        return None

def test_login_step_by_step():
    """Test login step by step to identify the issue"""
    base_url = "http://127.0.0.1:5000"
    
    print("🔍 Login Troubleshooting - Step by Step")
    print("=" * 50)
    
    # Create a session for cookies
    session = requests.Session()
    
    try:
        # Step 1: Check if webapp is running
        print("1. Checking if webapp is accessible...")
        try:
            response = session.get(f"{base_url}/")
            print(f"   ✅ Webapp accessible: {response.status_code}")
            if response.status_code == 302:
                print(f"   Redirected to: {response.headers.get('Location', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ Webapp not accessible: {e}")
            return False
        
        # Step 2: Get login page
        print("\n2. Getting login page...")
        login_response = session.get(f"{base_url}/login")
        print(f"   Status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"   ❌ Login page failed: {login_response.status_code}")
            return False
        
        # Step 3: Extract CSRF token
        print("\n3. Extracting CSRF token...")
        csrf_token = extract_csrf_token(login_response.text)
        if csrf_token:
            print(f"   ✅ CSRF token found: {csrf_token[:16]}...")
        else:
            print("   ❌ No CSRF token found")
            print("   Login form HTML snippet:")
            soup = BeautifulSoup(login_response.text, 'html.parser')
            form = soup.find('form')
            if form:
                print(f"   {str(form)[:200]}...")
            return False
        
        # Step 4: Test with admin credentials
        print("\n4. Testing admin login...")
        admin_data = {
            'username_or_email': 'admin',
            'password': '5OIkH4M:%iaP7QbdU9wj2Sfj',  # From our test
            'csrf_token': csrf_token
        }
        
        admin_login = session.post(f"{base_url}/login", data=admin_data, allow_redirects=False)
        print(f"   Admin login status: {admin_login.status_code}")
        
        if admin_login.status_code == 302:
            print(f"   ✅ Admin login successful! Redirected to: {admin_login.headers.get('Location', 'Unknown')}")
            
            # Test dashboard access
            dashboard = session.get(f"{base_url}/")
            print(f"   Dashboard access: {dashboard.status_code}")
            if 'admin' in dashboard.text.lower() or 'dashboard' in dashboard.text.lower():
                print("   ✅ Dashboard content looks correct")
            else:
                print("   ⚠️  Dashboard content unclear")
            
        elif admin_login.status_code == 200:
            print("   ❌ Admin login returned form (likely failed)")
            # Check for error messages
            if 'error' in admin_login.text.lower():
                soup = BeautifulSoup(admin_login.text, 'html.parser')
                errors = soup.find_all(class_=['alert-danger', 'error', 'alert'])
                for error in errors:
                    print(f"   Error message: {error.get_text().strip()}")
        else:
            print(f"   ❌ Admin login failed with status: {admin_login.status_code}")
        
        # Step 5: Test with regular user credentials
        print("\n5. Testing regular user login...")
        
        # Get fresh CSRF token
        fresh_login = session.get(f"{base_url}/login")
        fresh_csrf = extract_csrf_token(fresh_login.text)
        
        user_data = {
            'username_or_email': 'iolaire',
            'password': 'user123',  # From our test
            'csrf_token': fresh_csrf
        }
        
        user_login = session.post(f"{base_url}/login", data=user_data, allow_redirects=False)
        print(f"   User login status: {user_login.status_code}")
        
        if user_login.status_code == 302:
            print(f"   ✅ User login successful! Redirected to: {user_login.headers.get('Location', 'Unknown')}")
        elif user_login.status_code == 200:
            print("   ❌ User login returned form (likely failed)")
        else:
            print(f"   ❌ User login failed with status: {user_login.status_code}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Login test error: {e}")
        return False

def main():
    """Run login troubleshooting"""
    print("🚀 Login Issue Troubleshooting")
    print("Testing login functionality to identify issues")
    print("=" * 50)
    
    # Wait for webapp
    print("Waiting for webapp to be ready...")
    time.sleep(2)
    
    success = test_login_step_by_step()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Login troubleshooting completed")
        print("Check the results above to identify any issues")
    else:
        print("❌ Login troubleshooting failed")
        print("There are issues that need to be resolved")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
