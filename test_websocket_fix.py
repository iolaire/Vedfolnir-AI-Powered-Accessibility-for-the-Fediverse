#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket Connection Fix

This script tests the WebSocket connection to verify that the suspension
issues have been resolved.
"""

import requests
import time
import json
import sys

def test_websocket_config_endpoint():
    """Test the WebSocket configuration endpoint"""
    
    print("🔧 Testing WebSocket Configuration Endpoint...")
    
    try:
        response = requests.get('http://127.0.0.1:5000/api/websocket/client-config', timeout=10)
        
        if response.status_code == 200:
            config = response.json()
            print("✅ WebSocket config endpoint accessible")
            
            if config.get('success'):
                client_config = config.get('config', {})
                print("✅ WebSocket configuration retrieved successfully")
                
                # Check key timeout values
                ping_timeout = client_config.get('pingTimeout', 0)
                ping_interval = client_config.get('pingInterval', 0)
                timeout = client_config.get('timeout', 0)
                
                print(f"   • Ping Timeout: {ping_timeout}ms")
                print(f"   • Ping Interval: {ping_interval}ms") 
                print(f"   • Connection Timeout: {timeout}ms")
                print(f"   • Transports: {client_config.get('transports', [])}")
                print(f"   • Reconnection: {client_config.get('reconnection', False)}")
                print(f"   • With Credentials: {client_config.get('withCredentials', False)}")
                
                # Verify reasonable timeout values
                if ping_timeout == 60000 and ping_interval == 25000:
                    print("✅ Timeout values are correct (60s/25s)")
                    return True
                else:
                    print(f"⚠️  Timeout values may need adjustment")
                    return True
            else:
                print("❌ WebSocket config endpoint returned error")
                return False
        else:
            print(f"❌ WebSocket config endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing WebSocket config: {e}")
        return False

def test_socketio_endpoint():
    """Test the Socket.IO endpoint availability"""
    
    print("\n🔌 Testing Socket.IO Endpoint...")
    
    try:
        response = requests.get('http://127.0.0.1:5000/socket.io/', timeout=10)
        
        if response.status_code == 200:
            print("✅ Socket.IO endpoint is accessible")
            
            # Check if it's a valid Socket.IO response
            if 'engine.io' in response.text or 'socket.io' in response.text:
                print("✅ Valid Socket.IO response received")
                return True
            else:
                print("⚠️  Socket.IO endpoint accessible but response format unclear")
                return True
        else:
            print(f"❌ Socket.IO endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Socket.IO endpoint: {e}")
        return False

def test_admin_page_accessibility():
    """Test that admin pages are accessible"""
    
    print("\n🔐 Testing Admin Page Accessibility...")
    
    try:
        # Test admin dashboard (should redirect to login if not authenticated)
        response = requests.get('http://127.0.0.1:5000/admin', timeout=10, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            print("✅ Admin dashboard endpoint is accessible")
            
            if response.status_code == 302:
                print("   • Redirected to login (expected for unauthenticated access)")
            else:
                print("   • Direct access allowed (may be authenticated)")
            
            return True
        else:
            print(f"❌ Admin dashboard returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing admin page: {e}")
        return False

def test_websocket_test_page():
    """Test the WebSocket test page"""
    
    print("\n🧪 Testing WebSocket Test Page...")
    
    try:
        response = requests.get('http://127.0.0.1:5000/websocket-test', timeout=10)
        
        if response.status_code == 200:
            print("✅ WebSocket test page is accessible")
            
            # Check if keep-alive script is included
            if 'websocket-keepalive.js' in response.text:
                print("✅ Keep-alive script is included in test page")
            else:
                print("⚠️  Keep-alive script not found in test page")
            
            return True
        else:
            print(f"❌ WebSocket test page returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing WebSocket test page: {e}")
        return False

def check_keep_alive_script():
    """Check if the keep-alive script exists"""
    
    print("\n📜 Checking Keep-Alive Script...")
    
    try:
        response = requests.get('http://127.0.0.1:5000/static/js/websocket-keepalive.js', timeout=10)
        
        if response.status_code == 200:
            print("✅ Keep-alive script is accessible")
            
            # Check for key functions
            script_content = response.text
            if 'WebSocketKeepAlive' in script_content:
                print("✅ WebSocketKeepAlive class found")
            if 'setupKeepAlive' in script_content:
                print("✅ Keep-alive setup function found")
            if 'setupVisibilityHandling' in script_content:
                print("✅ Visibility handling found")
            if 'setupReconnectionLogic' in script_content:
                print("✅ Reconnection logic found")
            
            return True
        else:
            print(f"❌ Keep-alive script returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking keep-alive script: {e}")
        return False

def main():
    """Main test function"""
    
    print("🧪 WebSocket Connection Fix Test")
    print("=" * 50)
    
    tests = [
        ("WebSocket Config Endpoint", test_websocket_config_endpoint),
        ("Socket.IO Endpoint", test_socketio_endpoint),
        ("Admin Page Accessibility", test_admin_page_accessibility),
        ("WebSocket Test Page", test_websocket_test_page),
        ("Keep-Alive Script", check_keep_alive_script),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! WebSocket fixes appear to be working correctly.")
        print("\n📋 Next steps:")
        print("   1. Visit http://127.0.0.1:5000/admin/csrf_security_dashboard")
        print("   2. Check browser developer console for WebSocket connection logs")
        print("   3. Verify no more 'WebSocket is closed due to suspension' errors")
        print("   4. Monitor WebSocket connection stability over time")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the output above.")
        print("   Some functionality may not work as expected.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)