#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Connection Test

This script tests the WebSocket connection to identify and fix connection issues.
"""

import socketio
import time
import sys
import requests

def test_websocket_connection():
    """Test WebSocket connection to the server"""
    
    print("=== WebSocket Connection Test ===")
    
    # First, test if the server is responding to HTTP requests
    try:
        response = requests.get('http://127.0.0.1:5000/api/websocket/client-config')
        if response.status_code == 200:
            print("✅ Server is responding to HTTP requests")
            config = response.json()
            print(f"✅ WebSocket config endpoint working: {config.get('success', False)}")
        else:
            print(f"❌ Server HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return False
    
    # Test WebSocket connection
    print("\n--- Testing WebSocket Connection ---")
    
    # Create a SocketIO client
    sio = socketio.Client(
        logger=True,
        engineio_logger=True,
        reconnection=True,
        reconnection_attempts=3,
        reconnection_delay=1,
        reconnection_delay_max=5
    )
    
    connection_successful = False
    connection_error = None
    
    @sio.event
    def connect():
        nonlocal connection_successful
        connection_successful = True
        print("✅ WebSocket connected successfully!")
        sio.emit('test_message', {'data': 'Hello from test client'})
    
    @sio.event
    def disconnect():
        print("🔌 WebSocket disconnected")
    
    @sio.event
    def connect_error(data):
        nonlocal connection_error
        connection_error = data
        print(f"❌ WebSocket connection error: {data}")
    
    @sio.event
    def error(data):
        print(f"❌ WebSocket error: {data}")
    
    try:
        print("Attempting to connect to WebSocket server...")
        sio.connect('http://127.0.0.1:5000', 
                   transports=['websocket', 'polling'],
                   wait_timeout=10)
        
        # Wait a moment for connection to establish
        time.sleep(2)
        
        if connection_successful:
            print("✅ WebSocket connection test PASSED")
            
            # Test admin namespace
            print("\n--- Testing Admin Namespace ---")
            try:
                admin_sio = socketio.Client()
                admin_sio.connect('http://127.0.0.1:5000/admin', wait_timeout=5)
                print("✅ Admin namespace connection PASSED")
                admin_sio.disconnect()
            except Exception as e:
                print(f"⚠️ Admin namespace connection failed: {e}")
            
            sio.disconnect()
            return True
        else:
            print(f"❌ WebSocket connection test FAILED: {connection_error}")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket connection test FAILED with exception: {e}")
        return False
    finally:
        if sio.connected:
            sio.disconnect()

def test_socketio_server_status():
    """Test if SocketIO server is properly initialized"""
    
    print("\n=== SocketIO Server Status Test ===")
    
    try:
        # Test the SocketIO endpoint directly
        response = requests.get('http://127.0.0.1:5000/socket.io/?EIO=4&transport=polling')
        
        if response.status_code == 200:
            print("✅ SocketIO server is responding")
            print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
            
            # Check if it's a valid SocketIO response
            content = response.text
            if content.startswith('0'):  # SocketIO handshake response typically starts with '0'
                print("✅ SocketIO handshake response detected")
                return True
            else:
                print(f"⚠️ Unexpected SocketIO response: {content[:100]}...")
                return False
        else:
            print(f"❌ SocketIO server error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ SocketIO server test failed: {e}")
        return False

def main():
    """Main test execution"""
    
    print("Testing WebSocket connection to Vedfolnir server...")
    print("Make sure the web application is running on http://127.0.0.1:5000")
    print()
    
    # Test SocketIO server status first
    server_ok = test_socketio_server_status()
    
    if not server_ok:
        print("\n❌ SocketIO server is not responding properly")
        print("This indicates the WebSocket server is not properly initialized")
        return False
    
    # Test WebSocket connection
    connection_ok = test_websocket_connection()
    
    if connection_ok:
        print("\n✅ All WebSocket tests PASSED")
        print("The WebSocket connection is working correctly")
        return True
    else:
        print("\n❌ WebSocket connection tests FAILED")
        print("There are issues with the WebSocket connection")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)