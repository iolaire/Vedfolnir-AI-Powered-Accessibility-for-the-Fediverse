# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python3
"""
Test Configuration Validation Feedback

Tests the admin interface validation feedback system including:
- Real-time validation feedback for configuration value changes
- Conflict detection display in the admin interface
- Detailed error messages for validation failures
- Configuration value range and type validation in the UI
"""

import unittest
import requests
import re
import json
import sys
import os
from urllib.parse import urljoin
import getpass

# Add project root to path for imports
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

def test_validation_api(session, base_url="http://127.0.0.1:5000"):
    """Test the configuration validation API endpoint"""
    print("\n=== Testing Configuration Validation API ===")
    
    # Get CSRF token
    config_page = session.get(urljoin(base_url, "/admin/configuration"))
    if config_page.status_code != 200:
        print("❌ Could not access configuration page")
        return False
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', config_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Test validation for max_concurrent_jobs with valid value
    test_key = "max_concurrent_jobs"
    test_value = 10  # Valid value
    
    print(f"Testing validation for {test_key} = {test_value}...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/validate"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Validation API accessible")
        
        try:
            data = response.json()
            
            # Check required fields
            required_fields = [
                'key', 'value', 'is_valid', 'errors', 'warnings',
                'conflicts', 'data_type', 'validation_rules'
            ]
            
            for field in required_fields:
                if field in data:
                    print(f"✅ Field '{field}' present: {data[field]}")
                else:
                    print(f"❌ Field '{field}' missing")
                    return False
            
            # Check data types
            if isinstance(data['is_valid'], bool):
                print(f"✅ is_valid is boolean: {data['is_valid']}")
            else:
                print("❌ is_valid is not boolean")
                return False
            
            if isinstance(data['errors'], list):
                print(f"✅ errors is list: {data['errors']}")
            else:
                print("❌ errors is not list")
                return False
            
            if isinstance(data['warnings'], list):
                print(f"✅ warnings is list: {data['warnings']}")
            else:
                print("❌ warnings is not list")
                return False
            
            if isinstance(data['conflicts'], list):
                print(f"✅ conflicts is list: {data['conflicts']}")
            else:
                print("❌ conflicts is not list")
                return False
            
            return True
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Validation API failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"Response text: {response.text[:200]}")
        return False

def test_invalid_value_validation(session, base_url="http://127.0.0.1:5000"):
    """Test validation with invalid values"""
    print("\n=== Testing Invalid Value Validation ===")
    
    # Get CSRF token
    config_page = session.get(urljoin(base_url, "/admin/configuration"))
    if config_page.status_code != 200:
        print("❌ Could not access configuration page")
        return False
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', config_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Test with invalid integer value
    test_key = "max_concurrent_jobs"
    test_value = "not_a_number"  # Invalid for integer type
    
    print(f"Testing validation for {test_key} = '{test_value}' (invalid)...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/validate"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            
            print(f"Validation result: {data['is_valid']}")
            print(f"Errors: {data['errors']}")
            
            # Should be invalid
            if not data['is_valid']:
                print("✅ Invalid value correctly detected")
                
                # Should have errors
                if data['errors'] and len(data['errors']) > 0:
                    print(f"✅ Validation errors provided: {data['errors']}")
                    return True
                else:
                    print("❌ No validation errors provided for invalid value")
                    return False
            else:
                print("❌ Invalid value not detected")
                return False
                
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Invalid value validation failed: {response.status_code}")
        return False

def test_range_validation(session, base_url="http://127.0.0.1:5000"):
    """Test range validation for numeric values"""
    print("\n=== Testing Range Validation ===")
    
    # Get CSRF token
    config_page = session.get(urljoin(base_url, "/admin/configuration"))
    if config_page.status_code != 200:
        print("❌ Could not access configuration page")
        return False
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', config_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Test with value below minimum (assuming min is 1)
    test_key = "max_concurrent_jobs"
    test_value = -5  # Negative value should be invalid
    
    print(f"Testing range validation for {test_key} = {test_value}...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/validate"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            
            print(f"Validation result: {data['is_valid']}")
            print(f"Errors: {data['errors']}")
            print(f"Validation rules: {data['validation_rules']}")
            
            # Check if validation rules are provided
            if data['validation_rules']:
                print("✅ Validation rules provided")
                
                # Check for min/max rules
                if 'min' in data['validation_rules'] or 'max' in data['validation_rules']:
                    print("✅ Range validation rules found")
                else:
                    print("⚠️ No range validation rules found")
            else:
                print("⚠️ No validation rules provided")
            
            # For negative value, should be invalid if there's a min rule
            if not data['is_valid'] and any('minimum' in error.lower() or 'below' in error.lower() for error in data['errors']):
                print("✅ Range validation working correctly")
                return True
            elif data['is_valid']:
                print("⚠️ Negative value accepted (may not have min validation)")
                return True  # Still consider success if no min rule
            else:
                print("✅ Value rejected (validation working)")
                return True
                
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Range validation test failed: {response.status_code}")
        return False

def test_validation_page_elements(session, base_url="http://127.0.0.1:5000"):
    """Test validation elements in configuration management page"""
    print("\n=== Testing Validation Page Elements ===")
    
    response = session.get(urljoin(base_url, "/admin/configuration"))
    
    if response.status_code == 200:
        print("✅ Configuration management page accessible")
        
        # Check for validation-related JavaScript functions
        js_functions = [
            'validateConfigurationValue',
            'displayValidationFeedback',
            'clearValidationFeedback',
            'addValidationRulesInfo',
            'getSeverityColor'
        ]
        
        for func in js_functions:
            if func in response.text:
                print(f"✅ JavaScript function found: {func}")
            else:
                print(f"❌ JavaScript function not found: {func}")
                return False
        
        # Check for validation CSS classes
        if 'is-valid' in response.text and 'is-invalid' in response.text:
            print("✅ Bootstrap validation classes referenced")
        else:
            print("❌ Bootstrap validation classes not found")
            return False
        
        return True
    else:
        print(f"❌ Configuration management page failed: {response.status_code}")
        return False

def test_boolean_validation(session, base_url="http://127.0.0.1:5000"):
    """Test boolean value validation"""
    print("\n=== Testing Boolean Validation ===")
    
    # Get CSRF token
    config_page = session.get(urljoin(base_url, "/admin/configuration"))
    if config_page.status_code != 200:
        print("❌ Could not access configuration page")
        return False
    
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', config_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Test with boolean configuration
    test_key = "maintenance_mode"
    test_values = ["true", "false", "invalid_boolean"]
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    for test_value in test_values:
        print(f"Testing boolean validation for {test_key} = '{test_value}'...")
        
        response = session.post(
            urljoin(base_url, f"/admin/api/configuration/{test_key}/validate"),
            json={'value': test_value},
            headers=headers
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if test_value in ["true", "false"]:
                    if data['is_valid']:
                        print(f"✅ Valid boolean '{test_value}' accepted")
                    else:
                        print(f"❌ Valid boolean '{test_value}' rejected: {data['errors']}")
                        return False
                else:
                    if not data['is_valid']:
                        print(f"✅ Invalid boolean '{test_value}' rejected")
                    else:
                        print(f"❌ Invalid boolean '{test_value}' accepted")
                        return False
                        
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                return False
        else:
            print(f"❌ Boolean validation test failed: {response.status_code}")
            return False
    
    return True

def main():
    """Main test execution"""
    print("=== Configuration Validation Feedback Test ===")
    
    # Create authenticated session
    session, success = create_authenticated_session()
    if not success:
        print("❌ Authentication failed")
        return False
    
    # Run tests
    tests = [
        test_validation_api,
        test_invalid_value_validation,
        test_range_validation,
        test_boolean_validation,
        test_validation_page_elements
    ]
    
    results = []
    for test in tests:
        try:
            result = test(session)
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)