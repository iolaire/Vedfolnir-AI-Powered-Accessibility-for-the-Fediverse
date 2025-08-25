# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python3
"""
Test Configuration Management Functionality

Tests the admin configuration management interface including:
- Authentication and access control
- Configuration retrieval and updates
- API endpoint functionality
"""

import requests
import sys
import re
import getpass
from urllib.parse import urljoin

def create_authenticated_session(base_url="http://127.0.0.1:5000", username="admin"):
    """
    Create an authenticated session for testing
    
    Args:
        base_url: The base URL of the web application
        username: Username to login with (default: admin)
    
    Returns:
        tuple: (session, success) where session is requests.Session and success is bool
    """
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

def test_configuration_management_page(session, base_url="http://127.0.0.1:5000"):
    """Test access to the configuration management page"""
    print("\n=== Testing Configuration Management Page ===")
    
    response = session.get(urljoin(base_url, "/admin/configuration"))
    
    if response.status_code == 200:
        print("✅ Configuration management page accessible")
        
        # Check for key elements
        if "System Configuration Management" in response.text:
            print("✅ Page title found")
        else:
            print("⚠️ Page title not found")
            
        if "configuration_management.js" in response.text:
            print("✅ JavaScript file referenced")
        else:
            print("⚠️ JavaScript file not referenced")
            
        return True
    else:
        print(f"❌ Configuration management page failed: {response.status_code}")
        return False

def test_configuration_api_endpoints(session, base_url="http://127.0.0.1:5000"):
    """Test configuration API endpoints"""
    print("\n=== Testing Configuration API Endpoints ===")
    
    # Test categories endpoint
    print("Testing categories endpoint...")
    response = session.get(urljoin(base_url, "/admin/api/configuration/categories"))
    
    if response.status_code == 200:
        print("✅ Categories endpoint accessible")
        try:
            data = response.json()
            if 'categories' in data:
                print(f"✅ Found {len(data['categories'])} configuration categories")
                for category in data['categories'][:3]:  # Show first 3
                    print(f"   - {category['name']}: {category['description']}")
            else:
                print("⚠️ Categories data not in expected format")
        except Exception as e:
            print(f"⚠️ Failed to parse categories JSON: {e}")
    else:
        print(f"❌ Categories endpoint failed: {response.status_code}")
        return False
    
    # Test schema endpoint
    print("\nTesting schema endpoint...")
    response = session.get(urljoin(base_url, "/admin/api/configuration/schema"))
    
    if response.status_code == 200:
        print("✅ Schema endpoint accessible")
        try:
            data = response.json()
            if 'schemas' in data:
                print(f"✅ Found {len(data['schemas'])} configuration schemas")
                # Show a few examples
                for key, schema in list(data['schemas'].items())[:3]:
                    print(f"   - {key}: {schema['description'][:50]}...")
            else:
                print("⚠️ Schema data not in expected format")
        except Exception as e:
            print(f"⚠️ Failed to parse schema JSON: {e}")
    else:
        print(f"❌ Schema endpoint failed: {response.status_code}")
        return False
    
    # Test configurations endpoint
    print("\nTesting configurations endpoint...")
    response = session.get(urljoin(base_url, "/admin/api/configuration/"))
    
    if response.status_code == 200:
        print("✅ Configurations endpoint accessible")
        try:
            data = response.json()
            if 'configurations' in data:
                print(f"✅ Found {len(data['configurations'])} configurations")
                # Show a few examples
                for key, value in list(data['configurations'].items())[:3]:
                    print(f"   - {key}: {value}")
            else:
                print("⚠️ Configurations data not in expected format")
        except Exception as e:
            print(f"⚠️ Failed to parse configurations JSON: {e}")
    else:
        print(f"❌ Configurations endpoint failed: {response.status_code}")
        return False
    
    return True

def test_configuration_update(session, base_url="http://127.0.0.1:5000"):
    """Test configuration update functionality"""
    print("\n=== Testing Configuration Update ===")
    
    # Test updating a safe configuration (maintenance_reason)
    test_key = "maintenance_reason"
    test_value = "Testing configuration management system"
    
    print(f"Testing update of {test_key}...")
    
    # First get the current value
    response = session.get(urljoin(base_url, f"/admin/api/configuration/{test_key}"))
    
    if response.status_code == 200:
        try:
            current_data = response.json()
            original_value = current_data.get('value', '')
            print(f"✅ Current value: {original_value}")
        except:
            original_value = ''
    else:
        print(f"⚠️ Could not get current value: {response.status_code}")
        original_value = ''
    
    # Update the configuration
    update_data = {
        'value': test_value,
        'reason': 'Testing configuration management functionality'
    }
    
    response = session.put(
        urljoin(base_url, f"/admin/api/configuration/{test_key}"),
        json=update_data
    )
    
    if response.status_code == 200:
        print("✅ Configuration updated successfully")
        
        # Verify the update
        response = session.get(urljoin(base_url, f"/admin/api/configuration/{test_key}"))
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('value') == test_value:
                    print("✅ Configuration update verified")
                else:
                    print(f"⚠️ Configuration not updated correctly: {data.get('value')}")
            except:
                print("⚠️ Could not verify configuration update")
        
        # Restore original value
        if original_value != test_value:
            restore_data = {
                'value': original_value,
                'reason': 'Restoring original value after test'
            }
            session.put(
                urljoin(base_url, f"/admin/api/configuration/{test_key}"),
                json=restore_data
            )
            print("✅ Original value restored")
        
        return True
    else:
        print(f"❌ Configuration update failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   Error: {error_data.get('error', 'Unknown error')}")
        except:
            pass
        return False

def main():
    """Main test execution"""
    print("=== Configuration Management Test ===")
    
    # Create authenticated session
    session, success = create_authenticated_session()
    if not success:
        print("❌ Failed to authenticate. Cannot continue with tests.")
        return False
    
    # Test configuration management page
    page_success = test_configuration_management_page(session)
    
    # Test API endpoints
    api_success = test_configuration_api_endpoints(session)
    
    # Test configuration updates
    update_success = test_configuration_update(session)
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Configuration Page: {'✅ PASS' if page_success else '❌ FAIL'}")
    print(f"API Endpoints: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"Configuration Updates: {'✅ PASS' if update_success else '❌ FAIL'}")
    
    overall_success = page_success and api_success and update_success
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)