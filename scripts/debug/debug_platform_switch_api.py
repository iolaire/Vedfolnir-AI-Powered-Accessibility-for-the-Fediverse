#!/usr/bin/env python3
"""
Debug Platform Switch API Call

This script tests the platform switching API endpoint to identify the 400 error.
"""

import requests
import json
import time

def test_platform_switch():
    """Test the platform switch API endpoint"""
    
    base_url = "http://localhost:5000"
    
    print("Testing Platform Switch API...")
    
    # First, try to login
    login_data = {
        'username': 'iolaire',  # User who owns platform ID 2
        'password': 'g9bDFB9JzgEaVZx'  # Correct password
    }
    
    session = requests.Session()
    
    # Get login page to get CSRF token
    print("1. Getting login page...")
    login_page = session.get(f"{base_url}/login")
    if login_page.status_code != 200:
        print(f"✗ Failed to get login page: {login_page.status_code}")
        return False
    
    # Extract CSRF token from login page
    csrf_token = None
    if 'csrf_token' in login_page.text:
        # Simple extraction - in real app you'd parse HTML properly
        import re
        match = re.search(r'name="csrf_token".*?value="([^"]+)"', login_page.text)
        if match:
            csrf_token = match.group(1)
            print(f"✓ Found CSRF token: {csrf_token[:10]}...")
    
    if not csrf_token:
        print("✗ Could not find CSRF token")
        return False
    
    # Login
    print("2. Attempting login...")
    login_data['csrf_token'] = csrf_token
    login_response = session.post(f"{base_url}/login", data=login_data)
    
    if login_response.status_code == 302:  # Redirect after successful login
        print("✓ Login successful")
    else:
        print(f"✗ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text[:200]}...")
        return False
    
    # Get session state to verify login
    print("3. Checking session state...")
    session_state = session.get(f"{base_url}/api/session/state")
    if session_state.status_code == 200:
        state_data = session_state.json()
        print(f"✓ Session state: authenticated={state_data.get('authenticated')}, user={state_data.get('user', {}).get('username')}")
    else:
        print(f"✗ Failed to get session state: {session_state.status_code}")
    
    # Get CSRF token for API call
    print("4. Getting CSRF token for API call...")
    csrf_response = session.get(f"{base_url}/api/csrf-token")
    if csrf_response.status_code == 200:
        csrf_data = csrf_response.json()
        api_csrf_token = csrf_data.get('csrf_token')
        print(f"✓ Got API CSRF token: {api_csrf_token[:10]}...")
    else:
        print(f"✗ Failed to get CSRF token: {csrf_response.status_code}")
        return False
    
    # Test platform switch
    print("5. Testing platform switch...")
    switch_data = {
        'csrf_token': api_csrf_token
    }
    
    switch_response = session.post(
        f"{base_url}/api/switch_platform/2", 
        json=switch_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Platform switch response: {switch_response.status_code}")
    print(f"Response headers: {dict(switch_response.headers)}")
    print(f"Response body: {switch_response.text}")
    
    if switch_response.status_code == 200:
        print("✓ Platform switch successful!")
        return True
    else:
        print(f"✗ Platform switch failed with {switch_response.status_code}")
        return False

if __name__ == "__main__":
    # Wait a moment for web app to fully start
    print("Waiting for web app to start...")
    time.sleep(2)
    
    success = test_platform_switch()
    if success:
        print("\n✅ Platform switch test passed!")
    else:
        print("\n❌ Platform switch test failed!")
