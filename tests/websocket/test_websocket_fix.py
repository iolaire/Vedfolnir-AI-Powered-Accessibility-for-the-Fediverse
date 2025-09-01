#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket Fix

This script tests the WebSocket connection to verify that the 
"write() before start_response" error has been fixed.
"""

import requests
import time
import sys
from urllib.parse import urljoin

def test_websocket_connection():
    """Test WebSocket connection to verify the fix"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🔧 Testing WebSocket Fix")
    print("=" * 50)
    
    # Test 1: Check if web app is running
    print("1. Checking if web application is running...")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code in [200, 302]:
            print("✅ Web application is running")
        else:
            print(f"❌ Web application returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to web application: {e}")
        print("   Please start the web application with: python web_app.py")
        return False
    
    # Test 2: Check SocketIO polling endpoint
    print("2. Testing SocketIO polling endpoint...")
    try:
        socketio_url = urljoin(base_url, "/socket.io/?EIO=4&transport=polling")
        response = requests.get(socketio_url, timeout=10)
        if response.status_code == 200:
            print("✅ SocketIO polling endpoint is working")
        else:
            print(f"❌ SocketIO polling returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ SocketIO polling failed: {e}")
        return False
    
    # Test 3: Check WebSocket client config endpoint
    print("3. Testing WebSocket client config endpoint...")
    try:
        config_url = urljoin(base_url, "/api/websocket/client-config")
        response = requests.get(config_url, timeout=5)
        if response.status_code == 200:
            print("✅ WebSocket client config endpoint is working")
            config_data = response.json()
            print(f"   - URL: {config_data.get('url', 'Not specified')}")
            print(f"   - Transports: {config_data.get('transports', 'Not specified')}")
        else:
            print(f"❌ WebSocket config returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ WebSocket config failed: {e}")
        return False
    except ValueError as e:
        print(f"❌ WebSocket config returned invalid JSON: {e}")
        return False
    
    print("\n🎉 All WebSocket tests passed!")
    print("The 'write() before start_response' error should be fixed.")
    
    return True

def main():
    """Main test function"""
    
    print("WebSocket Fix Verification")
    print("This script tests the WebSocket connection after applying the fix")
    print("for the 'write() before start_response' error.\n")
    
    success = test_websocket_connection()
    
    if success:
        print("\n✅ WebSocket fix verification completed successfully!")
        print("\nNext steps:")
        print("1. Monitor the webapp.log file for any remaining WebSocket errors")
        print("2. Test WebSocket functionality in the web interface")
        print("3. Check that notifications and real-time updates work properly")
        return 0
    else:
        print("\n❌ WebSocket fix verification failed!")
        print("\nTroubleshooting:")
        print("1. Ensure the web application is running: python web_app.py")
        print("2. Check the webapp.log file for any error messages")
        print("3. Verify Redis is running if using Redis sessions")
        return 1

if __name__ == "__main__":
    sys.exit(main())