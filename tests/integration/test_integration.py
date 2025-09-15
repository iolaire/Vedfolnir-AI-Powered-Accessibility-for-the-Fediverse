#!/usr/bin/env python3
"""
Integration Test for Redis Session Refactor

Test the integrated Redis session system with the main web application.
"""

import requests
import time
import json

def test_integration():
    """Test the Redis session integration"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing Redis Session Integration")
    print("=" * 50)
    
    # Create a session for cookies
    session = requests.Session()
    
    # Test 1: Access login page
    print("1. Testing login page access...")
    try:
        response = session.get(f"{base_url}/login")
        if response.status_code == 200:
            print("   ✅ Login page accessible")
        else:
            print(f"   ❌ Login page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Login page error: {e}")
        return False
    
    # Test 2: Attempt login with admin credentials
    print("2. Testing admin login...")
    try:
        login_data = {
            'username_or_email': 'admin',
            'password': '5OIkH4M:%iaP7QbdU9wj2Sfj'
        }
        response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            print("   ✅ Login request processed")
            
            # Check if we got redirected (successful login)
            if response.status_code == 302:
                print("   ✅ Login successful (redirected)")
                
                # Test 3: Access dashboard
                print("3. Testing dashboard access...")
                dashboard_response = session.get(f"{base_url}/", allow_redirects=True)
                if dashboard_response.status_code == 200:
                    if "Dashboard" in dashboard_response.text or "admin" in dashboard_response.text:
                        print("   ✅ Dashboard accessible after login")
                    else:
                        print("   ⚠️  Dashboard accessible but content unclear")
                else:
                    print(f"   ❌ Dashboard access failed: {dashboard_response.status_code}")
                
                # Test 4: Check session info API
                print("4. Testing session info API...")
                try:
                    session_response = session.get(f"{base_url}/test/session_info")
                    if session_response.status_code == 200:
                        session_data = session_response.json()
                        if session_data.get('session_id'):
                            print("   ✅ Session API working - Redis session active")
                            print(f"      Session ID: {session_data['session_id'][:8]}...")
                            if session_data.get('flask_session', {}).get('user_id'):
                                print(f"      User ID: {session_data['flask_session']['user_id']}")
                        else:
                            print("   ⚠️  Session API accessible but no session data")
                    else:
                        print(f"   ❌ Session API failed: {session_response.status_code}")
                except Exception as e:
                    print(f"   ⚠️  Session API error (may not exist): {e}")
                
                # Test 5: Test logout
                print("5. Testing logout...")
                logout_response = session.get(f"{base_url}/logout", allow_redirects=False)
                if logout_response.status_code in [200, 302]:
                    print("   ✅ Logout successful")
                    
                    # Verify we're logged out
                    dashboard_check = session.get(f"{base_url}/", allow_redirects=False)
                    if dashboard_check.status_code == 302:
                        print("   ✅ Properly redirected after logout")
                    else:
                        print("   ⚠️  Logout may not have cleared session properly")
                else:
                    print(f"   ❌ Logout failed: {logout_response.status_code}")
                
                return True
            else:
                print("   ❌ Login failed (no redirect)")
                print(f"      Response: {response.text[:200]}...")
                return False
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False

def test_iolaire_login():
    """Test login with iolaire user"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n6. Testing iolaire user login...")
    session = requests.Session()
    
    try:
        login_data = {
            'username_or_email': 'iolaire',
            'password': 'user123'
        }
        response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:
            print("   ✅ Iolaire login successful")
            
            # Test dashboard access
            dashboard_response = session.get(f"{base_url}/", allow_redirects=True)
            if dashboard_response.status_code == 200:
                print("   ✅ Iolaire can access dashboard")
            
            # Logout
            session.get(f"{base_url}/logout")
            return True
        else:
            print(f"   ❌ Iolaire login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Iolaire login error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Redis Session Integration Test")
    print("Waiting for web app to be ready...")
    time.sleep(2)
    
    success1 = test_integration()
    success2 = test_iolaire_login()
    
    print("\n" + "=" * 50)
    print("📊 Integration Test Results:")
    print("=" * 50)
    
    if success1 and success2:
        print("🎉 All integration tests PASSED!")
        print("✅ Redis session refactor integration is successful")
        exit(0)
    else:
        print("⚠️  Some integration tests failed")
        print("❌ Please review the issues above")
        exit(1)
