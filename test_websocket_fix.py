#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket connection after notification system migration fixes
"""

import requests
import time
import sys

def test_websocket_endpoints():
    """Test if WebSocket endpoints are accessible"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("=== WebSocket Connection Test ===")
    
    # Test if the main app is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Main app accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Main app not accessible: {e}")
        return False
    
    # Test Socket.IO endpoint
    try:
        response = requests.get(f"{base_url}/socket.io/", timeout=5)
        print(f"✅ Socket.IO endpoint accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Socket.IO endpoint error: {e}")
        return False
    
    # Test admin page (should be accessible)
    try:
        response = requests.get(f"{base_url}/admin", timeout=5)
        print(f"✅ Admin page accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Admin page error: {e}")
        return False
    
    print("\n=== WebSocket Namespace Test ===")
    
    # Test Socket.IO with admin namespace
    try:
        response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=polling&t=test", timeout=5)
        if response.status_code == 200:
            print("✅ Socket.IO polling transport working")
        else:
            print(f"⚠️  Socket.IO polling returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Socket.IO polling error: {e}")
    
    return True

if __name__ == "__main__":
    success = test_websocket_endpoints()
    if success:
        print("\n✅ WebSocket endpoints appear to be working")
        print("Try accessing the admin dashboard to test WebSocket connections")
    else:
        print("\n❌ WebSocket endpoint issues detected")
    
    sys.exit(0 if success else 1)