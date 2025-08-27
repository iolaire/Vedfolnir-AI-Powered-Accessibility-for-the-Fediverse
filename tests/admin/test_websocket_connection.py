# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket connection functionality for admin pages
"""

import sys
import os
import requests
import re
import getpass
from urllib.parse import urljoin

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_websocket_connection():
    """Test WebSocket connection on admin pages"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("=== WebSocket Connection Test ===")
    print(f"Testing WebSocket functionality at {base_url}")
    
    # Create session for authentication
    session = requests.Session()
    
    # Step 1: Get login page and CSRF token
    print("\n1. Getting login page...")
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
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Login
    username = input("Enter admin username (default: admin): ").strip() or "admin"
    password = getpass.getpass(f"Enter password for {username}: ")
    
    print(f"\n2. Logging in as {username}...")
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    if login_response.status_code == 302:
        print("✅ Successfully logged in")
    elif login_response.status_code == 200 and 'login' not in login_response.url.lower():
        print("✅ Successfully logged in")
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    # Step 3: Access admin dashboard
    print("\n3. Accessing admin dashboard...")
    dashboard_response = session.get(urljoin(base_url, "/admin"))
    
    if dashboard_response.status_code != 200:
        print(f"❌ Failed to access admin dashboard: {dashboard_response.status_code}")
        return False
    
    print("✅ Admin dashboard accessible")
    
    # Step 4: Check for WebSocket elements
    print("\n4. Checking for WebSocket elements...")
    dashboard_html = dashboard_response.text
    
    # Check for Socket.IO script
    if 'socket.io' in dashboard_html:
        print("✅ Socket.IO script found in page")
    else:
        print("❌ Socket.IO script not found in page")
    
    # Check for WebSocket client script
    if 'websocket-client.js' in dashboard_html:
        print("✅ WebSocket client script found in page")
    else:
        print("❌ WebSocket client script not found in page")
    
    # Check for WebSocket status element
    if 'websocket-status' in dashboard_html:
        print("✅ WebSocket status element found in page")
    else:
        print("❌ WebSocket status element not found in page")
    
    # Step 5: Test WebSocket endpoint accessibility
    print("\n5. Testing WebSocket endpoint...")
    
    # Try to access the Socket.IO endpoint
    socketio_response = session.get(urljoin(base_url, "/socket.io/?EIO=4&transport=polling"))
    
    if socketio_response.status_code == 200:
        print("✅ Socket.IO endpoint accessible")
        print(f"   Response length: {len(socketio_response.content)} bytes")
    else:
        print(f"❌ Socket.IO endpoint not accessible: {socketio_response.status_code}")
    
    print("\n=== Test Complete ===")
    print("\nTo test WebSocket connection in browser:")
    print("1. Open browser developer tools (F12)")
    print("2. Go to admin dashboard")
    print("3. Check console for WebSocket connection messages")
    print("4. Look for 'VedfolnirWS' object in console")
    print("5. Try: window.VedfolnirWS.connect() if not auto-connected")
    
    return True

if __name__ == "__main__":
    try:
        success = test_websocket_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)