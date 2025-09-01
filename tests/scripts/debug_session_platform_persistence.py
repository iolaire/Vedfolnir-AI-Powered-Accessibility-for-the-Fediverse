# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug Session Platform Context Persistence

This script investigates why browser sessions don't maintain platform_connection_id consistently
and tests the session middleware's ability to populate g.session_context with platform data.
"""

import sys
import os
import requests
import re
import getpass
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """Create an authenticated session for testing"""
    session = requests.Session()
    
    # Step 1: Get login page and CSRF token
    print(f"Getting login page for user: {username}")
    login_page = session.get(urljoin(base_url, "/login"))
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return session, False
    
    # Extract CSRF token from meta tag
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token in login page")
        return session, False
    
    csrf_token = csrf_match.group(1)
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Prompt for password
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Step 3: Login
    print(f"Logging in as {username}...")
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    login_response = session.post(urljoin(base_url, "/login"), data=login_data)
    
    # Check if login was successful
    if login_response.status_code == 302:
        print("✅ Successfully logged in (redirected)")
        return session, True
    elif login_response.status_code == 200:
        if 'login' in login_response.url.lower():
            print("❌ Login failed: Still on login page")
            return session, False
        else:
            print("✅ Successfully logged in")
            return session, True
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        return session, False

def test_session_platform_context(session, base_url):
    """Test session platform context persistence"""
    print("\n=== Testing Session Platform Context ===")
    
    # Test 1: Check current session context via debug endpoint
    print("\n1. Checking current session context...")
    debug_response = session.get(urljoin(base_url, "/debug/session"))
    if debug_response.status_code == 200:
        debug_data = debug_response.json()
        print(f"✅ Session context: {debug_data}")
        
        # Check if platform context exists
        if 'platform_connection_id' in debug_data:
            print(f"✅ Platform connection ID found: {debug_data['platform_connection_id']}")
        else:
            print("❌ No platform connection ID in session context")
            
        if 'platform_name' in debug_data:
            print(f"✅ Platform name found: {debug_data['platform_name']}")
        else:
            print("❌ No platform name in session context")
    else:
        print(f"❌ Failed to get session context: {debug_response.status_code}")
        return False
    
    # Test 2: Access platform management page
    print("\n2. Testing platform management page access...")
    platform_mgmt_response = session.get(urljoin(base_url, "/platform_management"))
    if platform_mgmt_response.status_code == 200:
        print("✅ Platform management page accessible")
        
        # Check if platform data is displayed
        if 'platform_connection_id' in debug_data and debug_data['platform_connection_id']:
            platform_name = debug_data.get('platform_name', 'Unknown')
            if platform_name.lower() in platform_mgmt_response.text.lower():
                print(f"✅ Current platform '{platform_name}' displayed on page")
            else:
                print(f"❌ Current platform '{platform_name}' not found on page")
    else:
        print(f"❌ Platform management page not accessible: {platform_mgmt_response.status_code}")
    
    # Test 3: Access caption generation page
    print("\n3. Testing caption generation page access...")
    caption_response = session.get(urljoin(base_url, "/caption_generation"))
    if caption_response.status_code == 200:
        print("✅ Caption generation page accessible")
        
        # Check if platform context is available
        if 'platform_connection_id' in debug_data and debug_data['platform_connection_id']:
            print("✅ Platform context should be available for caption generation")
        else:
            print("❌ No platform context available for caption generation")
    elif caption_response.status_code == 302:
        print(f"❌ Caption generation page redirected: {caption_response.headers.get('Location', 'Unknown')}")
        return False
    else:
        print(f"❌ Caption generation page error: {caption_response.status_code}")
        return False
    
    return True

def test_platform_switching(session, base_url):
    """Test platform switching functionality"""
    print("\n=== Testing Platform Switching ===")
    
    # Get available platforms
    print("\n1. Getting available platforms...")
    debug_response = session.get(urljoin(base_url, "/debug/session"))
    if debug_response.status_code != 200:
        print("❌ Cannot get session context")
        return False
    
    debug_data = debug_response.json()
    current_platform_id = debug_data.get('platform_connection_id')
    
    if not current_platform_id:
        print("❌ No current platform connection")
        return False
    
    print(f"✅ Current platform ID: {current_platform_id}")
    
    # Get platform management page to find other platforms
    platform_mgmt_response = session.get(urljoin(base_url, "/platform_management"))
    if platform_mgmt_response.status_code != 200:
        print("❌ Cannot access platform management")
        return False
    
    # Look for platform switch links
    platform_links = re.findall(r'/switch_platform/(\d+)', platform_mgmt_response.text)
    available_platforms = [int(pid) for pid in platform_links if int(pid) != current_platform_id]
    
    if not available_platforms:
        print("ℹ️ No other platforms available for switching test")
        return True
    
    # Test switching to another platform
    target_platform_id = available_platforms[0]
    print(f"\n2. Switching to platform {target_platform_id}...")
    
    switch_response = session.get(urljoin(base_url, f"/switch_platform/{target_platform_id}"))
    if switch_response.status_code == 302:
        print("✅ Platform switch request completed (redirected)")
    else:
        print(f"❌ Platform switch failed: {switch_response.status_code}")
        return False
    
    # Verify the switch worked
    print("\n3. Verifying platform switch...")
    debug_response = session.get(urljoin(base_url, "/debug/session"))
    if debug_response.status_code == 200:
        new_debug_data = debug_response.json()
        new_platform_id = new_debug_data.get('platform_connection_id')
        
        if new_platform_id == target_platform_id:
            print(f"✅ Platform successfully switched to {new_platform_id}")
        else:
            print(f"❌ Platform switch failed: expected {target_platform_id}, got {new_platform_id}")
            return False
    else:
        print("❌ Cannot verify platform switch")
        return False
    
    # Test caption generation access after switch
    print("\n4. Testing caption generation after platform switch...")
    caption_response = session.get(urljoin(base_url, "/caption_generation"))
    if caption_response.status_code == 200:
        print("✅ Caption generation accessible after platform switch")
    elif caption_response.status_code == 302:
        print(f"❌ Caption generation redirected after switch: {caption_response.headers.get('Location', 'Unknown')}")
        return False
    else:
        print(f"❌ Caption generation error after switch: {caption_response.status_code}")
        return False
    
    # Switch back to original platform
    print(f"\n5. Switching back to original platform {current_platform_id}...")
    switch_back_response = session.get(urljoin(base_url, f"/switch_platform/{current_platform_id}"))
    if switch_back_response.status_code == 302:
        print("✅ Switched back to original platform")
    else:
        print(f"❌ Failed to switch back: {switch_back_response.status_code}")
    
    return True

def test_session_persistence_across_requests(session, base_url):
    """Test session persistence across multiple requests"""
    print("\n=== Testing Session Persistence Across Requests ===")
    
    # Make multiple requests and check if platform context persists
    for i in range(5):
        print(f"\nRequest {i+1}/5:")
        
        # Get session context
        debug_response = session.get(urljoin(base_url, "/debug/session"))
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            platform_id = debug_data.get('platform_connection_id')
            platform_name = debug_data.get('platform_name')
            
            if platform_id:
                print(f"✅ Platform context persisted: {platform_name} (ID: {platform_id})")
            else:
                print("❌ Platform context lost")
                return False
        else:
            print(f"❌ Cannot get session context: {debug_response.status_code}")
            return False
        
        # Access a different page to test persistence
        if i % 2 == 0:
            test_response = session.get(urljoin(base_url, "/platform_management"))
        else:
            test_response = session.get(urljoin(base_url, "/"))
        
        if test_response.status_code != 200:
            print(f"❌ Page access failed: {test_response.status_code}")
            return False
    
    print("✅ Session platform context persisted across all requests")
    return True

def main():
    """Main test execution"""
    print("=== Session Platform Context Persistence Debug ===")
    
    base_url = "http://127.0.0.1:5000"
    
    # Create authenticated session
    session, success = create_authenticated_session(base_url)
    if not success:
        print("❌ Failed to create authenticated session")
        return False
    
    # Run tests
    tests = [
        ("Session Platform Context", lambda: test_session_platform_context(session, base_url)),
        ("Platform Switching", lambda: test_platform_switching(session, base_url)),
        ("Session Persistence", lambda: test_session_persistence_across_requests(session, base_url))
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print('='*60)
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)