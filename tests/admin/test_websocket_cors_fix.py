# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket CORS fix verification
"""

import sys
import os
import requests
import re
import getpass
from urllib.parse import urljoin

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_websocket_cors_headers():
    """Test that Socket.IO endpoints have proper CORS headers"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("=== WebSocket CORS Headers Test ===")
    print(f"Testing CORS headers at {base_url}")
    
    # Test Socket.IO endpoint with CORS headers
    print("\n1. Testing Socket.IO endpoint CORS headers...")
    
    headers = {
        'Origin': 'http://127.0.0.1:5000',
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type'
    }
    
    # Test OPTIONS request (preflight)
    options_response = requests.options(
        urljoin(base_url, "/socket.io/?EIO=4&transport=polling"),
        headers=headers
    )
    
    print(f"OPTIONS response status: {options_response.status_code}")
    print("CORS headers in response:")
    
    cors_headers = {
        'Access-Control-Allow-Origin': options_response.headers.get('Access-Control-Allow-Origin'),
        'Access-Control-Allow-Credentials': options_response.headers.get('Access-Control-Allow-Credentials'),
        'Access-Control-Allow-Methods': options_response.headers.get('Access-Control-Allow-Methods'),
        'Access-Control-Allow-Headers': options_response.headers.get('Access-Control-Allow-Headers'),
        'Access-Control-Max-Age': options_response.headers.get('Access-Control-Max-Age')
    }
    
    for header, value in cors_headers.items():
        if value:
            print(f"  ✅ {header}: {value}")
        else:
            print(f"  ❌ {header}: Not present")
    
    # Test GET request
    print("\n2. Testing Socket.IO GET request...")
    get_response = requests.get(
        urljoin(base_url, "/socket.io/?EIO=4&transport=polling"),
        headers={'Origin': 'http://127.0.0.1:5000'}
    )
    
    print(f"GET response status: {get_response.status_code}")
    
    if get_response.status_code == 200:
        print("✅ Socket.IO endpoint accessible")
        
        # Check CORS headers in GET response
        origin_header = get_response.headers.get('Access-Control-Allow-Origin')
        credentials_header = get_response.headers.get('Access-Control-Allow-Credentials')
        
        if origin_header:
            print(f"✅ CORS Origin header present: {origin_header}")
        else:
            print("❌ CORS Origin header missing")
            
        if credentials_header:
            print(f"✅ CORS Credentials header present: {credentials_header}")
        else:
            print("❌ CORS Credentials header missing")
            
    else:
        print(f"❌ Socket.IO endpoint not accessible: {get_response.status_code}")
    
    print("\n=== Test Complete ===")
    
    # Summary
    success = (
        options_response.status_code in [200, 204] and
        get_response.status_code == 200 and
        cors_headers['Access-Control-Allow-Origin'] is not None
    )
    
    if success:
        print("✅ CORS configuration appears to be working correctly")
        print("🎉 WebSocket connections should now work without CORS errors")
    else:
        print("❌ CORS configuration may need further adjustment")
    
    return success

def test_websocket_with_authentication():
    """Test WebSocket connection with authentication"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("\n=== Authenticated WebSocket Test ===")
    
    # Create session for authentication
    session = requests.Session()
    
    # Step 1: Get login page and CSRF token
    print("1. Getting login page...")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    # Extract CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token")
    
    # Step 2: Login
    username = "admin"
    password = getpass.getpass(f"Enter password for {username}: ")
    
    print(f"2. Logging in as {username}...")
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    if login_response.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    print("✅ Successfully logged in")
    
    # Step 3: Test authenticated Socket.IO connection
    print("3. Testing authenticated Socket.IO connection...")
    
    socketio_response = session.get(
        urljoin(base_url, "/socket.io/?EIO=4&transport=polling"),
        headers={'Origin': 'http://127.0.0.1:5000'}
    )
    
    if socketio_response.status_code == 200:
        print("✅ Authenticated Socket.IO connection successful")
        print(f"   Response length: {len(socketio_response.content)} bytes")
        
        # Check for session ID in response (indicates successful connection)
        response_text = socketio_response.text
        if 'sid' in response_text or 'session' in response_text:
            print("✅ Socket.IO session established")
        else:
            print("⚠️ Socket.IO response received but session unclear")
            
        return True
    else:
        print(f"❌ Authenticated Socket.IO connection failed: {socketio_response.status_code}")
        return False

def main():
    """Run all WebSocket CORS tests"""
    
    print("🔍 Testing WebSocket CORS Fix")
    print("=" * 50)
    
    # Test 1: CORS headers
    cors_success = test_websocket_cors_headers()
    
    # Test 2: Authenticated connection
    auth_success = test_websocket_with_authentication()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  CORS Headers: {'✅ PASS' if cors_success else '❌ FAIL'}")
    print(f"  Authenticated Connection: {'✅ PASS' if auth_success else '❌ FAIL'}")
    
    overall_success = cors_success and auth_success
    
    if overall_success:
        print("\n🎉 All tests passed! WebSocket CORS issue should be resolved.")
        print("💡 Users should no longer see 'access control checks' errors.")
    else:
        print("\n⚠️ Some tests failed. WebSocket issues may persist.")
        print("💡 Check server logs and browser console for more details.")
    
    return overall_success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)