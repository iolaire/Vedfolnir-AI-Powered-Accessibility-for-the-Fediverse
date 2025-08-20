#!/usr/bin/env python3
"""
Test Flask Session Functionality

Test if Flask sessions are working properly with our Redis interface.
"""

import requests
from bs4 import BeautifulSoup
import time

def test_flask_session():
    """Test Flask session functionality"""
    print("🧪 Testing Flask Session Functionality")
    print("=" * 50)
    
    session = requests.Session()
    
    # Test 1: Login and check if Flask-Login data is saved
    print("1. Testing login and Flask session persistence...")
    
    # Get login page
    login_page = session.get('http://localhost:5000/login')
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    
    print(f"   CSRF Token: {csrf_token[:16]}...")
    print(f"   Cookies before login: {dict(session.cookies)}")
    
    # Login
    login_data = {
        'username_or_email': 'admin',
        'password': '5OIkH4M:%iaP7QbdU9wj2Sfj',
        'csrf_token': csrf_token
    }
    
    login_response = session.post('http://localhost:5000/login', data=login_data, allow_redirects=False)
    print(f"   Login response: {login_response.status_code}")
    print(f"   Cookies after login: {dict(session.cookies)}")
    
    # Test 2: Try to access dashboard immediately
    print("\n2. Testing immediate dashboard access...")
    dashboard_response = session.get('http://localhost:5000/', allow_redirects=False)
    print(f"   Dashboard response: {dashboard_response.status_code}")
    
    if dashboard_response.status_code == 302:
        redirect_location = dashboard_response.headers.get('Location', '')
        print(f"   Redirected to: {redirect_location}")
        if 'login' in redirect_location:
            print("   ❌ Still redirecting to login - Flask-Login not working")
        else:
            print("   ✅ Redirected elsewhere - might be working")
    elif dashboard_response.status_code == 200:
        print("   ✅ Dashboard accessible - Flask-Login working")
    
    # Test 3: Check if we can access a protected route
    print("\n3. Testing protected route access...")
    protected_response = session.get('http://localhost:5000/platform_management', allow_redirects=False)
    print(f"   Protected route response: {protected_response.status_code}")
    
    if protected_response.status_code == 302:
        redirect_location = protected_response.headers.get('Location', '')
        print(f"   Redirected to: {redirect_location}")
    elif protected_response.status_code == 200:
        print("   ✅ Protected route accessible")
    
    # Test 4: Wait and try again (test session persistence)
    print("\n4. Testing session persistence after delay...")
    time.sleep(2)
    
    delayed_response = session.get('http://localhost:5000/', allow_redirects=False)
    print(f"   Delayed dashboard response: {delayed_response.status_code}")
    
    if delayed_response.status_code == 302:
        redirect_location = delayed_response.headers.get('Location', '')
        print(f"   Redirected to: {redirect_location}")
    elif delayed_response.status_code == 200:
        print("   ✅ Session persisted correctly")

if __name__ == "__main__":
    test_flask_session()
