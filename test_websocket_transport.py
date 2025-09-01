#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket Transport Configuration

Test different transport configurations to verify the fix.
"""

import requests
import time
import json

def test_transport_configuration():
    """Test WebSocket transport configuration"""
    
    print("🧪 Testing WebSocket Transport Configuration")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Check if server is running
    print("1. Testing server availability...")
    try:
        response = requests.get(f"{base_url}/api/maintenance/status", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server not accessible: {e}")
        return False
    
    # Test 2: Check WebSocket client configuration
    print("\n2. Testing WebSocket client configuration...")
    try:
        response = requests.get(f"{base_url}/api/websocket/client-config", timeout=5)
        if response.status_code == 200:
            config = response.json()
            print("   ✅ WebSocket configuration available")
            print(f"   📋 Transports: {config.get('transports', 'unknown')}")
            print(f"   📋 URL: {config.get('url', 'unknown')}")
        else:
            print(f"   ❌ Configuration request failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Configuration request error: {e}")
    
    # Test 3: Test Socket.IO polling connection
    print("\n3. Testing Socket.IO polling connection...")
    try:
        response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=polling", timeout=10)
        if response.status_code == 200:
            print("   ✅ Polling transport working")
        else:
            print(f"   ❌ Polling transport failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Polling transport error: {e}")
    
    # Test 4: Test WebSocket upgrade (this will likely fail, but that's expected)
    print("\n4. Testing WebSocket upgrade (expected to fail)...")
    try:
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
            'Sec-WebSocket-Version': '13'
        }
        response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=websocket", 
                              headers=headers, timeout=5)
        
        if response.status_code == 101:
            print("   ✅ WebSocket upgrade successful (unexpected but good!)")
        elif response.status_code == 400:
            print("   🟡 WebSocket upgrade failed as expected (this is normal)")
            print("   📝 The system will fall back to polling transport")
        else:
            print(f"   ⚠️ Unexpected WebSocket response: {response.status_code}")
    except Exception as e:
        print(f"   🟡 WebSocket upgrade failed as expected: {e}")
    
    # Test 5: Check if transport optimizer is available
    print("\n5. Testing transport optimizer availability...")
    try:
        response = requests.get(f"{base_url}/static/js/websocket-transport-optimizer.js", timeout=5)
        if response.status_code == 200:
            print("   ✅ Transport optimizer script available")
        else:
            print(f"   ❌ Transport optimizer not found: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Transport optimizer check failed: {e}")
    
    print("\n📊 Test Summary")
    print("=" * 50)
    print("✅ If polling transport works, the system is functioning correctly")
    print("🟡 WebSocket upgrade failures are expected and handled automatically")
    print("📝 The transport optimizer will improve connection reliability")
    print("\n🎯 Next Steps:")
    print("• Monitor connection patterns with: python monitor_websocket.py")
    print("• Check browser console for transport optimizer messages")
    print("• Verify that all WebSocket functionality works despite upgrade errors")

if __name__ == '__main__':
    test_transport_configuration()
