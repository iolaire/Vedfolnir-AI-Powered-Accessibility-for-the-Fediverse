#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test the admin job management page to verify the JavaScript fix
"""

import requests
import re
from urllib.parse import urljoin

def test_job_management_page():
    """Test the job management page JavaScript"""
    base_url = "http://127.0.0.1:8000"
    session = requests.Session()
    
    print("=== Testing Job Management Page JavaScript ===")
    
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
    
    # Check for the correct JavaScript endpoints
    print("3. Checking JavaScript content...")
    
    # Check if there's any JavaScript at all
    if '<script' in job_page.text:
        print("✅ Found JavaScript content in page")
        
        # Count script tags
        script_count = job_page.text.count('<script')
        print(f"  Script tags found: {script_count}")
        
        # Look for inline scripts vs external scripts
        inline_scripts = job_page.text.count('<script nonce=')
        external_scripts = job_page.text.count('<script src=')
        print(f"  Inline scripts: {inline_scripts}")
        print(f"  External scripts: {external_scripts}")
        
    else:
        print("❌ No JavaScript content found in page")
    
    # Check for specific function patterns
    patterns_to_check = [
        ('personalCancelJob', '/caption/api/cancel/'),
        ('adminCancelJob', '/admin/api/jobs/'),
        ('window.personalCancelJob', 'personal cancel function'),
        ('window.adminCancelJob', 'admin cancel function'),
        ('fetch(`/caption/api/cancel/', 'personal cancel fetch'),
        ('fetch(`/admin/api/jobs/', 'admin cancel fetch'),
    ]
    
    for pattern, description in patterns_to_check:
        if pattern in job_page.text:
            print(f"✅ Found {description}")
        else:
            print(f"❌ Missing {description}")
    
    # Check that the wrong endpoint is NOT present
    if '/api/cancel_task/' in job_page.text:
        print("❌ Found incorrect endpoint: /api/cancel_task/ (this should be fixed)")
    else:
        print("✅ Incorrect endpoint /api/cancel_task/ not found (good!)")
    
    print("\n4. Extracting JavaScript function snippets...")
    
    # Extract the personalCancelJob function
    personal_cancel_match = re.search(
        r'window\.personalCancelJob\s*=\s*function[^}]+fetch\(`([^`]+)`',
        job_page.text
    )
    if personal_cancel_match:
        endpoint = personal_cancel_match.group(1)
        print(f"Personal cancel endpoint in JS: {endpoint}")
        if '/caption/api/cancel/' in endpoint:
            print("✅ Personal cancel uses correct endpoint")
        else:
            print("❌ Personal cancel uses wrong endpoint")
    
    # Extract the adminCancelJob function
    admin_cancel_match = re.search(
        r'window\.adminCancelJob\s*=\s*function[^}]+fetch\(`([^`]+)`',
        job_page.text
    )
    if admin_cancel_match:
        endpoint = admin_cancel_match.group(1)
        print(f"Admin cancel endpoint in JS: {endpoint}")
        if '/admin/api/jobs/' in endpoint and '/cancel' in endpoint:
            print("✅ Admin cancel uses correct endpoint")
        else:
            print("❌ Admin cancel uses wrong endpoint")
    
    print("\n4. Saving page content for inspection...")
    
    # Save a portion of the page to see what's actually there
    with open('job_management_page_debug.html', 'w', encoding='utf-8') as f:
        f.write(job_page.text)
    
    print("✅ Page content saved to job_management_page_debug.html")
    
    # Look for any cancel-related JavaScript
    print("\n5. Searching for cancel-related JavaScript...")
    
    # Look for any function definitions
    function_matches = re.findall(r'function\s+(\w*[Cc]ancel\w*)', job_page.text)
    if function_matches:
        print(f"Found cancel-related functions: {function_matches}")
    
    # Look for window assignments
    window_matches = re.findall(r'window\.(\w*[Cc]ancel\w*)', job_page.text)
    if window_matches:
        print(f"Found window cancel assignments: {window_matches}")
    
    print("\n=== Test Complete ===")
    return True

if __name__ == "__main__":
    test_job_management_page()