# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH the SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple Platform Context Test

Quick test to check if platform context is being set during login.
"""

import sys
import os
import requests
import re
import getpass
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_login_and_platform_context():
    """Test login and check if platform context is set"""
    session = requests.Session()
    base_url = "http://127.0.0.1:5000"
    
    print("=== Simple Platform Context Test ===")
    
    # Step 1: Get login page
    print("1. Getting login page...")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    # Extract CSRF token
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token")
    
    # Step 2: Login
    password = getpass.getpass("Enter admin password: ")
    
    print("2. Logging in...")
    login_data = {
        'username_or_email': 'admin',
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    if login_response.status_code != 302:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    print("✅ Login successful")
    
    # Step 3: Check session context
    print("3. Checking session context...")
    debug_response = session.get(urljoin(base_url, "/debug/session"))
    if debug_response.status_code != 200:
        print(f"❌ Failed to get session context: {debug_response.status_code}")
        return False
    
    debug_data = debug_response.json()
    print(f"Session context: {debug_data}")
    
    # Check for platform context
    has_platform_id = 'platform_connection_id' in debug_data.get('debug_info', {}).get('flask_session_data', {})
    has_platform_name = 'platform_name' in debug_data.get('debug_info', {}).get('flask_session_data', {})
    
    if has_platform_id and has_platform_name:
        platform_id = debug_data['debug_info']['flask_session_data']['platform_connection_id']
        platform_name = debug_data['debug_info']['flask_session_data']['platform_name']
        print(f"✅ Platform context found: {platform_name} (ID: {platform_id})")
        return True
    else:
        print("❌ No platform context found in Flask session")
        
        # Check if it's in Redis session data
        redis_data = debug_data.get('debug_info', {}).get('redis_session_data', {})
        if 'platform_connection_id' in redis_data:
            print(f"ℹ️ Platform context found in Redis but not Flask session")
        else:
            print("ℹ️ No platform context in Redis session either")
        
        return False

if __name__ == "__main__":
    success = test_login_and_platform_context()
    print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)