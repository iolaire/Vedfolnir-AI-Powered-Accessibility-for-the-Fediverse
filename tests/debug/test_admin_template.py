# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify admin template rendering
"""

import sys
import os
import requests
import time
import subprocess
import getpass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_admin_template_with_auth():
    """Test admin template rendering with authentication"""
    print("=== Testing Admin Template with Authentication ===")
    
    # Create a session for authentication
    session = requests.Session()
    
    try:
        # Get login page first to get CSRF token
        login_page = session.get('http://127.0.0.1:5000/user-management/login', timeout=10)
        if login_page.status_code != 200:
            print(f"❌ Failed to access login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token
        import re
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if not csrf_match:
            print("❌ Could not find CSRF token in login page")
            return False
        
        csrf_token = csrf_match.group(1)
        
        # Get admin credentials
        username = input("Enter admin username (default: admin): ").strip() or "admin"
        password = getpass.getpass("Enter admin password: ")
        
        # Login
        login_data = {
            'username_or_email': username,
            'password': password,
            'csrf_token': csrf_token
        }
        
        login_response = session.post('http://127.0.0.1:5000/user-management/login', 
                                    data=login_data, timeout=10)
        
        if login_response.status_code not in [200, 302]:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        # Check if login was successful (should redirect or show dashboard)
        if 'login' in login_response.url.lower():
            print("❌ Login failed - still on login page")
            return False
        
        print("✅ Login successful")
        
        # Now test admin user management page
        admin_response = session.get('http://127.0.0.1:5000/admin/users', timeout=10)
        
        if admin_response.status_code == 200:
            print("✅ Admin user management template rendered successfully")
            return True
        elif admin_response.status_code == 302:
            print(f"⚠️  Admin page redirected to: {admin_response.headers.get('Location', 'unknown')}")
            return False
        else:
            print(f"❌ Admin page returned status: {admin_response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_admin_template_without_auth():
    """Test admin template access without authentication (should redirect)"""
    print("\n=== Testing Admin Template without Authentication ===")
    
    try:
        response = requests.get('http://127.0.0.1:5000/admin/users', timeout=10)
        
        if response.status_code == 302:
            redirect_location = response.headers.get('Location', '')
            if 'login' in redirect_location.lower():
                print("✅ Admin page properly redirects to login when not authenticated")
                return True
            else:
                print(f"⚠️  Admin page redirects to unexpected location: {redirect_location}")
                return False
        else:
            print(f"❌ Admin page should redirect but returned: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Run admin template tests"""
    print("Testing Admin Template Rendering")
    print("=" * 40)
    
    # Start webapp for testing
    webapp_process = None
    try:
        webapp_process = subprocess.Popen(
            [sys.executable, 'web_app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.join(os.path.dirname(__file__), '..', '..')
        )
        
        print("Starting webapp for testing...")
        time.sleep(10)
        
        # Check if webapp is running
        try:
            response = requests.get('http://127.0.0.1:5000', timeout=5)
            if response.status_code not in [200, 302]:
                print(f"❌ WebApp not responding properly: {response.status_code}")
                return False
        except requests.exceptions.RequestException:
            print("❌ WebApp not responding")
            return False
        
        print("✅ WebApp is running")
        
        # Run tests
        tests = [
            test_admin_template_without_auth,
            test_admin_template_with_auth
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 40)
        print("Test Results Summary:")
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("✅ All admin template tests passed!")
            return True
        else:
            print("❌ Some admin template tests failed.")
            return False
            
    finally:
        # Clean up
        if webapp_process and webapp_process.poll() is None:
            webapp_process.terminate()
            time.sleep(2)
            if webapp_process.poll() is None:
                webapp_process.kill()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)