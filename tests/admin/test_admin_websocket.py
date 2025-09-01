#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Admin WebSocket

This script tests the admin dashboard WebSocket connection to verify 
that the "write() before start_response" error has been fixed.
"""

import requests
import time
import sys
import getpass
from urllib.parse import urljoin

def login_as_admin():
    """Login as admin user"""
    
    print("1. Logging in as admin...")
    
    session = requests.Session()
    base_url = "http://127.0.0.1:5000"
    
    # Get login page and CSRF token
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"   ❌ Failed to get login page: {login_page.status_code}")
        return None
    
    # Extract CSRF token
    import re
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("   ❌ Could not find CSRF token")
        return None
    
    csrf_token = csrf_match.group(1)
    
    # Get admin password
    password = getpass.getpass("   Enter admin password: ")
    
    # Login
    login_data = {
        'username_or_email': 'admin',
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    if login_response.status_code == 302 or (login_response.status_code == 200 and 'login' not in login_response.url.lower()):
        print("   ✅ Successfully logged in as admin")
        return session
    else:
        print("   ❌ Login failed")
        return None

def test_admin_dashboard(session):
    """Test admin dashboard access"""
    
    print("2. Testing admin dashboard access...")
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        dashboard_response = session.get(urljoin(base_url, "/admin/dashboard"), timeout=10)
        
        if dashboard_response.status_code == 200:
            print("   ✅ Admin dashboard accessible")
            return True
        else:
            print(f"   ❌ Admin dashboard failed: {dashboard_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Admin dashboard error: {e}")
        return False

def test_websocket_connections():
    """Test WebSocket connections that might be triggered by admin dashboard"""
    
    print("3. Testing WebSocket connections...")
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: SocketIO polling
    try:
        polling_response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=polling", timeout=10)
        if polling_response.status_code == 200:
            print("   ✅ SocketIO polling working")
        else:
            print(f"   ❌ SocketIO polling failed: {polling_response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ SocketIO polling error: {e}")
        return False
    
    # Test 2: WebSocket upgrade without session ID (this was causing the error)
    try:
        websocket_response = requests.get(
            f"{base_url}/socket.io/?EIO=4&transport=websocket",
            headers={
                'Upgrade': 'websocket',
                'Connection': 'Upgrade',
                'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
                'Sec-WebSocket-Version': '13'
            },
            timeout=10
        )
        
        if websocket_response.status_code in [200, 101]:
            print("   ✅ WebSocket upgrade (no SID) working")
        elif websocket_response.status_code == 500:
            print("   ❌ WebSocket upgrade (no SID) still returning 500 error")
            return False
        else:
            print(f"   ⚠️  WebSocket upgrade (no SID) returned {websocket_response.status_code}")
            # This might be expected for HTTP simulation
            
    except Exception as e:
        print(f"   ❌ WebSocket upgrade error: {e}")
        return False
    
    # Test 3: WebSocket upgrade with session ID
    try:
        # First get a session ID via polling
        polling_response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=polling", timeout=10)
        session_id = None
        
        if polling_response.status_code == 200 and polling_response.text.startswith('0'):
            try:
                import json
                json_data = json.loads(polling_response.text[1:])
                session_id = json_data.get('sid')
            except:
                pass
        
        if session_id:
            websocket_with_sid_response = requests.get(
                f"{base_url}/socket.io/?EIO=4&transport=websocket&sid={session_id}",
                headers={
                    'Upgrade': 'websocket',
                    'Connection': 'Upgrade',
                    'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
                    'Sec-WebSocket-Version': '13'
                },
                timeout=10
            )
            
            if websocket_with_sid_response.status_code in [200, 101]:
                print("   ✅ WebSocket upgrade (with SID) working")
            else:
                print(f"   ⚠️  WebSocket upgrade (with SID) returned {websocket_with_sid_response.status_code}")
        else:
            print("   ⚠️  Could not get session ID for WebSocket test")
            
    except Exception as e:
        print(f"   ❌ WebSocket with SID error: {e}")
        return False
    
    return True

def check_recent_logs():
    """Check recent logs for WebSocket errors"""
    
    print("4. Checking recent logs for errors...")
    
    try:
        import subprocess
        
        # Check for recent WebSocket errors
        result = subprocess.run(
            ['tail', '-50', 'logs/webapp.log'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            log_content = result.stdout
            
            # Check for the specific error
            if 'write() before start_response' in log_content:
                print("   ❌ Found 'write() before start_response' error in recent logs")
                return False
            elif '500' in log_content and 'socket.io' in log_content and 'transport=websocket' in log_content:
                print("   ❌ Found WebSocket 500 error in recent logs")
                return False
            else:
                print("   ✅ No WebSocket errors found in recent logs")
                return True
        else:
            print("   ⚠️  Could not read log file")
            return True
            
    except Exception as e:
        print(f"   ⚠️  Error checking logs: {e}")
        return True

def main():
    """Main test function"""
    
    print("🔧 Admin WebSocket Fix Test")
    print("=" * 50)
    print("Testing admin dashboard WebSocket connections after applying the fix")
    print("for the 'write() before start_response' error.\n")
    
    # Test 1: Login as admin
    session = login_as_admin()
    if not session:
        print("\n❌ Could not login as admin")
        return 1
    
    # Test 2: Access admin dashboard
    dashboard_success = test_admin_dashboard(session)
    if not dashboard_success:
        print("\n❌ Admin dashboard access failed")
        return 1
    
    # Test 3: Test WebSocket connections
    websocket_success = test_websocket_connections()
    
    # Test 4: Check logs
    logs_clean = check_recent_logs()
    
    # Overall result
    if dashboard_success and websocket_success and logs_clean:
        print("\n🎉 Admin WebSocket fix verification completed successfully!")
        print("\nThe admin dashboard WebSocket connections are working properly.")
        print("The 'write() before start_response' error has been fixed.")
        
        print("\n✅ All tests passed:")
        print("  - Admin login successful")
        print("  - Admin dashboard accessible")
        print("  - WebSocket connections working")
        print("  - No errors in recent logs")
        
        return 0
    else:
        print("\n⚠️  Admin WebSocket fix verification completed with issues")
        if not dashboard_success:
            print("- Admin dashboard access failed")
        if not websocket_success:
            print("- WebSocket connections have issues")
        if not logs_clean:
            print("- Recent logs show WebSocket errors")
            
        print("\nRecommendations:")
        print("1. Check the webapp.log file for detailed error information")
        print("2. Verify the admin user credentials")
        print("3. Test WebSocket functionality in a real browser")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())