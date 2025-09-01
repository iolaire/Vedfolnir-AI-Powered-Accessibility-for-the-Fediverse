#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug login functionality for Vedfolnir web application
"""

import requests
import sys
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def debug_login_attempt():
    """Debug login attempt with detailed output"""
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    try:
        print("🔍 Debugging login process...")
        
        # Step 1: Get login page
        print("\n1. Getting login page...")
        login_page = session.get(urljoin(base_url, "/login"))
        print(f"   Status: {login_page.status_code}")
        print(f"   URL: {login_page.url}")
        
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page: {login_page.status_code}")
            return False
        
        # Step 2: Extract CSRF token
        print("\n2. Extracting CSRF token...")
        csrf_token = None
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            print(f"   CSRF token: {csrf_token[:30]}...")
        else:
            print("   No CSRF token found")
        
        # Step 3: Check form fields
        print("\n3. Analyzing login form...")
        soup = BeautifulSoup(login_page.text, 'html.parser')
        form = soup.find('form')
        if form:
            print(f"   Form action: {form.get('action', 'Not specified')}")
            print(f"   Form method: {form.get('method', 'Not specified')}")
            
            # Find input fields
            inputs = form.find_all('input')
            print("   Form fields:")
            for inp in inputs:
                field_name = inp.get('name', 'unnamed')
                field_type = inp.get('type', 'text')
                print(f"     - {field_name} ({field_type})")
        else:
            print("   No form found!")
            return False
        
        # Step 4: Attempt login
        print("\n4. Attempting login...")
        username = "admin"
        password = "akdr)X&XCN>fe0<RT5$RP^ik"
        
        # Prepare login data
        login_data = {
            'username_or_email': username,
            'password': password
        }
        
        # Add CSRF token if available
        if csrf_token:
            login_data['csrf_token'] = csrf_token
        
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password)}")
        print(f"   CSRF token: {'Yes' if csrf_token else 'No'}")
        print(f"   Form data keys: {list(login_data.keys())}")
        
        # Make login request
        print("   Making POST request...")
        login_response = session.post(urljoin(base_url, "/login"), data=login_data)
        
        print(f"\n5. Login response:")
        print(f"   Status: {login_response.status_code}")
        print(f"   URL: {login_response.url}")
        print(f"   Redirected: {'Yes' if login_response.history else 'No'}")
        
        # Check for error messages in response
        if 'error' in login_response.text.lower() or 'invalid' in login_response.text.lower():
            print("\n6. Error analysis:")
            soup = BeautifulSoup(login_response.text, 'html.parser')
            
            # Look for flash messages
            flash_messages = soup.find_all(class_=re.compile(r'alert|flash|error|message'))
            if flash_messages:
                print("   Flash messages found:")
                for msg in flash_messages:
                    print(f"     - {msg.get_text().strip()}")
            
            # Look for form errors
            form_errors = soup.find_all(class_=re.compile(r'error|invalid'))
            if form_errors:
                print("   Form errors found:")
                for error in form_errors:
                    print(f"     - {error.get_text().strip()}")
        
        # Step 6: Test if login was successful
        print("\n7. Testing authentication status...")
        
        if login_response.status_code == 302:
            print("   Login appears successful (redirect)")
            
            # Follow redirect and test dashboard access
            dashboard_response = session.get(base_url)
            print(f"   Dashboard status: {dashboard_response.status_code}")
            
            if 'logout' in dashboard_response.text.lower():
                print("✅ Login successful - logout link found")
                return True
            else:
                print("❌ Login may have failed - no logout link")
                return False
                
        elif login_response.status_code == 200:
            if 'login' in login_response.url.lower():
                print("❌ Login failed - still on login page")
                
                # Try to extract specific error message
                soup = BeautifulSoup(login_response.text, 'html.parser')
                error_elements = soup.find_all(string=re.compile(r'invalid|error|incorrect|failed', re.I))
                if error_elements:
                    print("   Error messages:")
                    for error in error_elements[:3]:  # Show first 3 error messages
                        print(f"     - {error.strip()}")
                
                return False
            else:
                print("✅ Login successful")
                return True
        else:
            print(f"❌ Unexpected status code: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during login debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_authentication():
    """Test authentication directly against the database"""
    print("\n🔍 Testing direct database authentication...")
    
    try:
        # Add project root to Python path
        import os
        import sys
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        sys.path.insert(0, project_root)
        
        from dotenv import load_dotenv
        load_dotenv()
        from config import Config
        from database import DatabaseManager
        from services.user_service import UserService
        
        config = Config()
        db_manager = DatabaseManager(config)
        user_service = UserService(db_manager)
        
        username = "admin"
        password = "akdr)X&XCN>fe0<RT5$RP^ik"
        
        print(f"   Testing credentials for: {username}")
        
        # Test authentication
        user = user_service.authenticate_user(username, password)
        
        if user:
            print(f"✅ Direct authentication successful")
            print(f"   User ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role.value}")
            return True
        else:
            print("❌ Direct authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during direct authentication test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug execution"""
    print("=== Vedfolnir Login Debug Analysis ===")
    
    # Test 1: Direct database authentication
    db_auth_success = test_direct_authentication()
    
    print("\n" + "="*50)
    
    # Test 2: Web login process
    web_login_success = debug_login_attempt()
    
    print("\n" + "="*50)
    print("\n📊 Debug Summary:")
    print(f"   Direct DB Auth: {'✅ Success' if db_auth_success else '❌ Failed'}")
    print(f"   Web Login:      {'✅ Success' if web_login_success else '❌ Failed'}")
    
    if db_auth_success and not web_login_success:
        print("\n🔍 Analysis: Database authentication works but web login fails.")
        print("   This suggests an issue with the web login form or CSRF handling.")
    elif not db_auth_success:
        print("\n🔍 Analysis: Database authentication failed.")
        print("   This suggests an issue with the credentials or user service.")
    elif db_auth_success and web_login_success:
        print("\n🎉 Analysis: Both authentication methods work correctly!")
    
    return db_auth_success and web_login_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)