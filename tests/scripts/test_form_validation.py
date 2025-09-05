#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS be LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test form validation for login form
"""

import sys
import os

# Add project root to Python path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

def test_login_form_validation():
    """Test the LoginForm validation directly"""
    print("🔍 Testing LoginForm validation...")
    
    try:
        from forms.user_management_forms import LoginForm
        
        # Test 1: Empty form
        print("\n1. Testing empty form...")
        form = LoginForm()
        is_valid = form.validate()
        print(f"   Empty form valid: {is_valid}")
        if not is_valid:
            print("   Errors:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"     - {field}: {error}")
        
        # Test 2: Form with data
        print("\n2. Testing form with data...")
        form_data = {
            'username_or_email': 'admin',
            'password': ')z0p>14_S9>}samLqf0t?{!Y'
        }
        
        form = LoginForm(data=form_data)
        is_valid = form.validate()
        print(f"   Form with data valid: {is_valid}")
        print(f"   Username field data: '{form.username_or_email.data}'")
        print(f"   Password field data: '{form.password.data}'")
        
        if not is_valid:
            print("   Errors:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"     - {field}: {error}")
        
        # Test 3: Simulate web request data
        print("\n3. Testing with simulated request data...")
        
        # This simulates how Flask processes form data
        from werkzeug.datastructures import MultiDict
        request_data = MultiDict([
            ('username_or_email', 'admin'),
            ('password', ')z0p>14_S9>}samLqf0t?{!Y'),
            ('csrf_token', 'dummy_token')
        ])
        
        form = LoginForm(request_data)
        is_valid = form.validate()
        print(f"   Form with request data valid: {is_valid}")
        print(f"   Username field data: '{form.username_or_email.data}'")
        print(f"   Password field data: '{form.password.data}'")
        
        if not is_valid:
            print("   Errors:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"     - {field}: {error}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Error testing form validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_login_request():
    """Test making a manual login request to see what happens"""
    print("\n🔍 Testing manual login request...")
    
    try:
        import requests
        from urllib.parse import urljoin
        import re
        
        base_url = "http://127.0.0.1:5000"
        session = requests.Session()
        
        # Get login page first
        login_page = session.get(urljoin(base_url, "/login"))
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token
        csrf_token = None
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
        
        # Prepare form data exactly as a browser would
        form_data = {
            'username_or_email': 'admin',
            'password': ')z0p>14_S9>}samLqf0t?{!Y',
            'remember_me': 'false'  # Add this field
        }
        
        if csrf_token:
            form_data['csrf_token'] = csrf_token
        
        print(f"   Sending form data: {list(form_data.keys())}")
        
        # Make the request with proper headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': urljoin(base_url, "/login")
        }
        
        response = session.post(
            urljoin(base_url, "/login"), 
            data=form_data,
            headers=headers,
            allow_redirects=False  # Don't follow redirects automatically
        )
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            print("✅ Login successful (redirect)")
            print(f"   Redirect location: {response.headers.get('Location', 'Not specified')}")
            return True
        elif response.status_code == 200:
            print("❌ Login failed (no redirect)")
            # Check for error messages
            if 'Username or email is required' in response.text:
                print("   Error: Username field validation failed")
            if 'Password is required' in response.text:
                print("   Error: Password field validation failed")
            return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing manual login: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test execution"""
    print("=== Login Form Validation Test ===")
    
    # Test 1: Form validation
    form_valid = test_login_form_validation()
    
    # Test 2: Manual request
    request_success = test_manual_login_request()
    
    print("\n" + "="*50)
    print("\n📊 Test Summary:")
    print(f"   Form Validation: {'✅ Success' if form_valid else '❌ Failed'}")
    print(f"   Manual Request:  {'✅ Success' if request_success else '❌ Failed'}")
    
    return form_valid and request_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)