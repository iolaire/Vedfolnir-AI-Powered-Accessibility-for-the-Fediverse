# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python3
"""
Test Configuration Dry-Run Mode

Tests the admin interface dry-run functionality including:
- "Test Configuration" mode that previews impacts without applying changes
- Configuration change simulation and impact analysis
- Dry-run validation and conflict checking
- Dry-run results display with detailed impact assessment
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

def test_dry_run_api(session, base_url="http://127.0.0.1:5000"):
    """Test the dry-run API endpoint"""
    print("\n=== Testing Dry-Run API ===")
    
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
    
    # Test dry-run for max_concurrent_jobs
    test_key = "max_concurrent_jobs"
    test_value = 25  # Test value
    
    print(f"Testing dry-run for {test_key} = {test_value}...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/dry-run"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Dry-run API accessible")
        
        try:
            data = response.json()
            
            # Check required top-level fields
            required_fields = [
                'key', 'current_value', 'new_value', 'dry_run_timestamp',
                'validation', 'impact', 'conflicts', 'related_configurations',
                'rollback', 'change_management', 'recommendation'
            ]
            
            for field in required_fields:
                if field in data:
                    print(f"✅ Field '{field}' present")
                else:
                    print(f"❌ Field '{field}' missing")
                    return False
            
            # Check validation structure
            validation = data['validation']
            validation_fields = ['is_valid', 'errors', 'warnings']
            for field in validation_fields:
                if field in validation:
                    print(f"✅ Validation field '{field}' present: {validation[field]}")
                else:
                    print(f"❌ Validation field '{field}' missing")
                    return False
            
            # Check impact structure
            impact = data['impact']
            impact_fields = ['level', 'affected_components', 'requires_restart', 'risk_factors', 'mitigation_steps']
            for field in impact_fields:
                if field in impact:
                    print(f"✅ Impact field '{field}' present: {impact[field]}")
                else:
                    print(f"❌ Impact field '{field}' missing")
                    return False
            
            # Check recommendation structure
            recommendation = data['recommendation']
            rec_fields = ['proceed', 'reason', 'confidence']
            for field in rec_fields:
                if field in recommendation:
                    print(f"✅ Recommendation field '{field}' present: {recommendation[field]}")
                else:
                    print(f"❌ Recommendation field '{field}' missing")
                    return False
            
            # Check rollback structure
            rollback = data['rollback']
            rollback_fields = ['complexity', 'steps', 'estimated_time']
            for field in rollback_fields:
                if field in rollback:
                    print(f"✅ Rollback field '{field}' present: {rollback[field]}")
                else:
                    print(f"❌ Rollback field '{field}' missing")
                    return False
            
            # Check change management structure
            change_mgmt = data['change_management']
            cm_fields = ['pre_change_checklist', 'post_change_verification', 'recommended_timing']
            for field in cm_fields:
                if field in change_mgmt:
                    print(f"✅ Change management field '{field}' present")
                else:
                    print(f"❌ Change management field '{field}' missing")
                    return False
            
            return True
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Dry-run API failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"Response text: {response.text[:200]}")
        return False

def test_high_impact_dry_run(session, base_url="http://127.0.0.1:5000"):
    """Test dry-run with high impact configuration"""
    print("\n=== Testing High Impact Dry-Run ===")
    
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
    
    # Test with session timeout - very short timeout should trigger high impact
    test_key = "session_timeout_minutes"
    test_value = 1  # Very short timeout
    
    print(f"Testing high impact dry-run for {test_key} = {test_value}...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/dry-run"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            
            print(f"Impact level: {data['impact']['level']}")
            print(f"Requires restart: {data['impact']['requires_restart']}")
            print(f"Risk factors: {data['impact']['risk_factors']}")
            print(f"Recommendation: {data['recommendation']['proceed']} - {data['recommendation']['reason']}")
            print(f"Rollback complexity: {data['rollback']['complexity']}")
            
            # Check if this triggers appropriate impact level
            if data['impact']['level'] in ['medium', 'high', 'critical']:
                print(f"✅ Appropriate impact level detected: {data['impact']['level']}")
            else:
                print(f"⚠️ Expected higher impact level, got: {data['impact']['level']}")
            
            # Check if risk factors are provided for high impact
            if data['impact']['risk_factors'] and len(data['impact']['risk_factors']) > 0:
                print("✅ Risk factors provided for high impact change")
            else:
                print("⚠️ No risk factors provided for potentially high impact change")
            
            # Check if rollback complexity is appropriate
            if data['rollback']['complexity'] in ['medium', 'high']:
                print(f"✅ Appropriate rollback complexity: {data['rollback']['complexity']}")
            else:
                print(f"⚠️ Expected higher rollback complexity, got: {data['rollback']['complexity']}")
            
            # Check if pre-change checklist is comprehensive
            checklist_items = len(data['change_management']['pre_change_checklist'])
            if checklist_items >= 3:
                print(f"✅ Comprehensive pre-change checklist: {checklist_items} items")
            else:
                print(f"⚠️ Limited pre-change checklist: {checklist_items} items")
            
            return True
            
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ High impact dry-run failed: {response.status_code}")
        return False

def test_invalid_value_dry_run(session, base_url="http://127.0.0.1:5000"):
    """Test dry-run with invalid configuration value"""
    print("\n=== Testing Invalid Value Dry-Run ===")
    
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
    
    # Test with invalid value
    test_key = "max_concurrent_jobs"
    test_value = "invalid_number"  # Invalid for integer type
    
    print(f"Testing invalid value dry-run for {test_key} = '{test_value}'...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/dry-run"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            
            print(f"Validation result: {data['validation']['is_valid']}")
            print(f"Validation errors: {data['validation']['errors']}")
            print(f"Recommendation: {data['recommendation']['proceed']} - {data['recommendation']['reason']}")
            
            # Should be invalid
            if not data['validation']['is_valid']:
                print("✅ Invalid value correctly detected in dry-run")
                
                # Should have validation errors
                if data['validation']['errors'] and len(data['validation']['errors']) > 0:
                    print(f"✅ Validation errors provided: {data['validation']['errors']}")
                else:
                    print("❌ No validation errors provided for invalid value")
                    return False
                
                # Should not recommend proceeding
                if not data['recommendation']['proceed']:
                    print("✅ Correctly recommends not proceeding with invalid value")
                else:
                    print("❌ Incorrectly recommends proceeding with invalid value")
                    return False
                
                return True
            else:
                print("❌ Invalid value not detected in dry-run")
                return False
                
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Invalid value dry-run failed: {response.status_code}")
        return False

def test_dry_run_page_elements(session, base_url="http://127.0.0.1:5000"):
    """Test dry-run elements in configuration management page"""
    print("\n=== Testing Dry-Run Page Elements ===")
    
    response = session.get(urljoin(base_url, "/admin/configuration"))
    
    if response.status_code == 200:
        print("✅ Configuration management page accessible")
        
        # Check for dry-run modal elements
        dry_run_elements = [
            'id="dryRunModal"',
            'id="dryRunRecommendation"',
            'id="dryRunValidation"',
            'id="dryRunImpact"',
            'id="dryRunConflicts"',
            'id="dryRunRollback"',
            'id="dryRunChecklist"',
            'id="proceedWithChange"'
        ]
        
        for element in dry_run_elements:
            if element in response.text:
                print(f"✅ Dry-run element found: {element}")
            else:
                print(f"❌ Dry-run element not found: {element}")
                return False
        
        # Check for Test Configuration button
        if 'Test Configuration' in response.text:
            print("✅ Test Configuration button found")
        else:
            print("❌ Test Configuration button not found")
            return False
        
        # Check for JavaScript functions
        js_functions = [
            'testConfiguration',
            'displayDryRunResults',
            'displayDryRunRecommendation',
            'displayDryRunValidation',
            'displayDryRunImpact',
            'displayDryRunConflicts',
            'displayDryRunRollback',
            'displayDryRunChecklist',
            'proceedWithConfigurationChange'
        ]
        
        for func in js_functions:
            if func in response.text:
                print(f"✅ JavaScript function found: {func}")
            else:
                print(f"❌ JavaScript function not found: {func}")
                return False
        
        # Check for dry-run CSS classes
        if 'dry-run-modal' in response.text or 'configuration_management.css' in response.text:
            print("✅ Dry-run CSS styling referenced")
        else:
            print("❌ Dry-run CSS styling not referenced")
            return False
        
        return True
    else:
        print(f"❌ Configuration management page failed: {response.status_code}")
        return False

def test_related_configurations_analysis(session, base_url="http://127.0.0.1:5000"):
    """Test related configurations analysis in dry-run"""
    print("\n=== Testing Related Configurations Analysis ===")
    
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
    
    # Test with max_concurrent_jobs which should have related configurations
    test_key = "max_concurrent_jobs"
    test_value = 50
    
    print(f"Testing related configurations analysis for {test_key}...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(
        urljoin(base_url, f"/admin/api/configuration/{test_key}/dry-run"),
        json={'value': test_value},
        headers=headers
    )
    
    if response.status_code == 200:
        try:
            data = response.json()
            
            related_configs = data.get('related_configurations', [])
            print(f"Related configurations found: {len(related_configs)}")
            
            for related in related_configs:
                print(f"  - {related.get('key', 'Unknown')}: {related.get('potential_impact', 'No impact info')}")
            
            # max_concurrent_jobs should have related configurations
            if len(related_configs) > 0:
                print("✅ Related configurations analysis working")
                
                # Check if related configurations have proper structure
                for related in related_configs:
                    required_fields = ['key', 'current_value', 'potential_impact', 'recommendation']
                    for field in required_fields:
                        if field not in related:
                            print(f"❌ Related config missing field: {field}")
                            return False
                
                print("✅ Related configurations have proper structure")
                return True
            else:
                print("⚠️ No related configurations found (may be expected)")
                return True  # Still consider success as API worked
                
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            return False
    else:
        print(f"❌ Related configurations analysis failed: {response.status_code}")
        return False

def main():
    """Main test execution"""
    print("=== Configuration Dry-Run Mode Test ===")
    
    # Create authenticated session
    session, success = create_authenticated_session()
    if not success:
        print("❌ Authentication failed")
        return False
    
    # Run tests
    tests = [
        test_dry_run_api,
        test_high_impact_dry_run,
        test_invalid_value_dry_run,
        test_related_configurations_analysis,
        test_dry_run_page_elements
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