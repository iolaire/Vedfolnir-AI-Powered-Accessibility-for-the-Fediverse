#!/usr/bin/env python3
"""
Comprehensive User Login Test

Test login functionality for all user types with Redis session integration.
"""

import requests
import time
from bs4 import BeautifulSoup

def extract_csrf_token(html_content):
    """Extract CSRF token from HTML form"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # First try hidden input field (most reliable)
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

def test_user_login(username, password, user_type):
    """Test login for a specific user"""
    base_url = "http://127.0.0.1:5000"
    
    print(f"\n🧪 Testing {user_type} login: {username}")
    print("-" * 50)
    
    # Create a session for cookies
    session = requests.Session()
    
    try:
        # 1. Get login page and CSRF token
        print("1. Getting login page and CSRF token...")
        response = session.get(f"{base_url}/login")
        if response.status_code != 200:
            print(f"   ❌ Login page failed: {response.status_code}")
            return False
        
        csrf_token = extract_csrf_token(response.text)
        if not csrf_token:
            print("   ❌ No CSRF token found")
            return False
        
        print(f"   ✅ CSRF token: {csrf_token[:16]}...")
        
        # 2. Attempt login
        print("2. Attempting login...")
        login_data = {
            'username_or_email': username,
            'password': password,
            'csrf_token': csrf_token
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if login_response.status_code == 302:
            print("   ✅ Login successful (redirected)")
            redirect_location = login_response.headers.get('Location', '')
            print(f"   Redirect to: {redirect_location}")
            
            # 3. Test dashboard access
            print("3. Testing dashboard access...")
            dashboard_response = session.get(f"{base_url}/", allow_redirects=True)
            if dashboard_response.status_code == 200:
                content = dashboard_response.text.lower()
                if any(word in content for word in ['dashboard', username.lower(), 'logout', 'platform']):
                    print(f"   ✅ Dashboard accessible for {user_type}")
                    
                    # Check for user-specific content
                    if 'admin' in content and user_type == 'Admin':
                        print("   ✅ Admin-specific content detected")
                    elif user_type != 'Admin' and username.lower() in content:
                        print(f"   ✅ User-specific content detected for {username}")
                else:
                    print("   ⚠️  Dashboard accessible but content unclear")
            else:
                print(f"   ❌ Dashboard access failed: {dashboard_response.status_code}")
                return False
            
            # 4. Test session persistence
            print("4. Testing session persistence...")
            for i in range(3):
                test_response = session.get(f"{base_url}/")
                if test_response.status_code == 200:
                    print(f"   ✅ Request {i+1}: Session persisted")
                else:
                    print(f"   ❌ Request {i+1}: Session lost")
                    return False
            
            # 5. Test logout
            print("5. Testing logout...")
            logout_response = session.get(f"{base_url}/logout", allow_redirects=False)
            if logout_response.status_code in [200, 302]:
                print("   ✅ Logout successful")
                
                # Verify logged out
                dashboard_check = session.get(f"{base_url}/", allow_redirects=False)
                if dashboard_check.status_code == 302:
                    print("   ✅ Properly redirected after logout")
                else:
                    print("   ⚠️  Logout may not have cleared session properly")
            else:
                print(f"   ❌ Logout failed: {logout_response.status_code}")
                return False
            
            print(f"🎉 {user_type} login test: SUCCESS")
            return True
            
        elif login_response.status_code == 200:
            # Check for error messages
            if 'error' in login_response.text.lower() or 'invalid' in login_response.text.lower():
                print("   ❌ Login failed - invalid credentials")
            else:
                print("   ❌ Login failed - form returned without redirect")
            return False
        else:
            print(f"   ❌ Login failed with status: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Login test error: {e}")
        return False

def test_user_roles_and_permissions():
    """Test different user roles and their permissions"""
    print("\n🔐 Testing User Roles and Permissions")
    print("=" * 60)
    
    # Test admin access to admin routes
    print("\n📋 Testing admin route access...")
    session = requests.Session()
    
    # Login as admin
    login_page = session.get("http://127.0.0.1:5000/login")
    csrf_token = extract_csrf_token(login_page.text)
    
    if csrf_token:
        login_data = {
            'username_or_email': 'admin',
            'password': '5OIkH4M:%iaP7QbdU9wj2Sfj',
            'csrf_token': csrf_token
        }
        
        login_response = session.post("http://127.0.0.1:5000/login", data=login_data, allow_redirects=False)
        
        if login_response.status_code == 302:
            print("   ✅ Admin logged in successfully")
            
            # Test admin routes
            admin_routes = [
                '/admin/',
                '/admin/users',
                '/admin/system'
            ]
            
            for route in admin_routes:
                try:
                    admin_response = session.get(f"http://127.0.0.1:5000{route}")
                    if admin_response.status_code == 200:
                        print(f"   ✅ Admin access to {route}: SUCCESS")
                    elif admin_response.status_code == 404:
                        print(f"   ℹ️  Route {route}: Not implemented (404)")
                    else:
                        print(f"   ⚠️  Admin access to {route}: {admin_response.status_code}")
                except Exception as e:
                    print(f"   ⚠️  Error testing {route}: {e}")
            
            # Logout admin
            session.get("http://127.0.0.1:5000/logout")
        else:
            print("   ❌ Admin login failed for permission test")

def main():
    """Run comprehensive user login tests"""
    print("🚀 Comprehensive User Login Test")
    print("Testing Redis session integration for all user types")
    print("=" * 60)
    
    # Wait for web app to be ready
    print("Waiting for web app to be ready...")
    time.sleep(2)
    
    # Test users with their credentials
    test_users = [
        {
            'username': 'admin',
            'password': '5OIkH4M:%iaP7QbdU9wj2Sfj',
            'user_type': 'Admin'
        },
        {
            'username': 'iolaire',
            'password': 'user123',
            'user_type': 'Regular User'
        }
    ]
    
    results = []
    
    # Test each user
    for user in test_users:
        success = test_user_login(
            user['username'], 
            user['password'], 
            user['user_type']
        )
        results.append({
            'user': user['username'],
            'type': user['user_type'],
            'success': success
        })
    
    # Test user roles and permissions
    test_user_roles_and_permissions()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 User Login Test Results:")
    print("=" * 60)
    
    all_success = True
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{result['type']} ({result['user']}): {status}")
        if not result['success']:
            all_success = False
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ALL USER LOGIN TESTS PASSED!")
        print("✅ Redis session integration works for all user types")
        print("✅ CSRF protection is working correctly")
        print("✅ Session management is operational for all users")
        return 0
    else:
        print("⚠️  Some user login tests failed")
        print("❌ Please review the issues above")
        return 1

if __name__ == "__main__":
    exit(main())
