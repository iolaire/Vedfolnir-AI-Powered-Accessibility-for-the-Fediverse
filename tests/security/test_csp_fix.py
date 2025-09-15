#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify CSP compliance fix for job management buttons
"""

import requests
import re
from urllib.parse import urljoin

def test_csp_compliance():
    """Test that the job management page is CSP compliant"""
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    
    print("=== Testing CSP Compliance Fix ===")
    
    # Login first
    print("1. Logging in...")
    login_page = session.get(urljoin(base_url, "/login"))
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    csrf_token = csrf_match.group(1) if csrf_match else ''
    
    login_data = {
        'username_or_email': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_token
    }
    
    session.post(urljoin(base_url, "/login"), data=login_data)
    
    # Get the job management page
    print("2. Getting job management page...")
    job_page = session.get(urljoin(base_url, "/admin/job-management"))
    
    if job_page.status_code != 200:
        print(f"❌ Failed to load job management page: {job_page.status_code}")
        return False
    
    print("✅ Job management page loaded successfully")
    
    # Check for CSP violations
    print("3. Checking for CSP compliance...")
    
    # Check that onclick handlers are removed
    onclick_count = job_page.text.count('onclick=')
    if onclick_count == 0:
        print("✅ No onclick handlers found (CSP compliant)")
    else:
        print(f"❌ Found {onclick_count} onclick handlers (CSP violation)")
        
        # Show which ones
        onclick_matches = re.findall(r'onclick="([^"]*)"', job_page.text)
        for match in onclick_matches[:5]:  # Show first 5
            print(f"  - onclick=\"{match}\"")
    
    # Check for data-action attributes
    data_action_count = job_page.text.count('data-action=')
    if data_action_count > 0:
        print(f"✅ Found {data_action_count} data-action attributes (CSP compliant)")
    else:
        print("❌ No data-action attributes found")
    
    # Check for specific data-action values
    expected_actions = [
        'admin-cancel-job',
        'personal-cancel-job', 
        'refresh-jobs',
        'toggle-auto-refresh',
        'view-job-details',
        'set-priority'
    ]
    
    found_actions = []
    for action in expected_actions:
        if f'data-action="{action}"' in job_page.text:
            found_actions.append(action)
            print(f"✅ Found data-action=\"{action}\"")
        else:
            print(f"⚠️  Missing data-action=\"{action}\"")
    
    # Check for event listener setup
    if 'setupJobActionEventListeners' in job_page.text:
        print("✅ Found setupJobActionEventListeners function")
    else:
        print("❌ Missing setupJobActionEventListeners function")
    
    if 'addEventListener(\'click\'' in job_page.text:
        print("✅ Found event delegation setup")
    else:
        print("❌ Missing event delegation setup")
    
    # Summary
    print("\n4. Summary:")
    csp_compliant = onclick_count == 0 and data_action_count > 0
    if csp_compliant:
        print("✅ Job management page is CSP compliant!")
        print(f"  - Removed all {onclick_count} onclick handlers")
        print(f"  - Added {data_action_count} data-action attributes")
        print(f"  - Found {len(found_actions)} expected actions")
    else:
        print("❌ Job management page has CSP violations")
    
    print("\n=== Test Complete ===")
    return csp_compliant

if __name__ == "__main__":
    test_csp_compliance()