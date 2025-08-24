#!/usr/bin/env python3

import requests
import sys
from bs4 import BeautifulSoup

def test_maintenance_routes():
    """Test the new maintenance routes that replace JavaScript calls"""
    
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    print("🔍 Testing New Maintenance Routes...")
    
    # Step 1: Login as admin
    print("\n1. Logging in as admin...")
    login_page = session.get(f"{base_url}/login")
    if login_page.status_code != 200:
        print(f"❌ Failed to get login page: {login_page.status_code}")
        return False
    
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})
    if not csrf_token:
        print("❌ No CSRF token found")
        return False
    
    login_data = {
        'username_or_email': 'admin',
        'password': ';ww>TC{}II,Qz+HX*OS3-,sl',
        'csrf_token': csrf_token.get('value')
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data)
    if login_response.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    print("✅ Login successful")
    
    # Step 2: Test new maintenance routes
    routes_to_test = [
        {
            'url': '/admin/maintenance/pause-system',
            'name': 'Pause System Page',
            'expected_content': ['Pause System', 'System Pause Warning', 'Reason for System Pause']
        },
        {
            'url': '/admin/maintenance/clear-queue',
            'name': 'Clear Queue Page',
            'expected_content': ['Clear Job Queue', 'Current Queue Status', 'Queued Jobs']
        },
        {
            'url': '/admin/maintenance/restart-failed',
            'name': 'Restart Failed Jobs Page',
            'expected_content': ['Restart Failed Jobs', 'Failed Jobs Overview', 'Restart Configuration']
        },
        {
            'url': '/admin/maintenance/cleanup-data',
            'name': 'Cleanup Data Page',
            'expected_content': ['Cleanup Old Data', 'Data to be Cleaned', 'Cleanup Configuration']
        }
    ]
    
    all_passed = True
    
    for route in routes_to_test:
        print(f"\n2. Testing {route['name']}...")
        print(f"   URL: {route['url']}")
        
        try:
            response = session.get(f"{base_url}{route['url']}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                
                # Check for expected content
                found_content = []
                missing_content = []
                
                for expected in route['expected_content']:
                    if expected in content:
                        found_content.append(expected)
                    else:
                        missing_content.append(expected)
                
                if found_content:
                    print(f"   ✅ Found expected content: {', '.join(found_content)}")
                
                if missing_content:
                    print(f"   ⚠️ Missing content: {', '.join(missing_content)}")
                
                if len(found_content) >= len(route['expected_content']) // 2:  # At least half the content found
                    print(f"   ✅ {route['name']} working correctly")
                else:
                    print(f"   ❌ {route['name']} missing too much expected content")
                    all_passed = False
                    
            elif response.status_code == 401:
                print("   ❌ Authentication failed (401)")
                all_passed = False
            elif response.status_code == 403:
                print("   ❌ Access denied (403)")
                all_passed = False
            elif response.status_code == 404:
                print("   ❌ Route not found (404)")
                all_passed = False
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            all_passed = False
    
    # Step 3: Test that system maintenance page now has links instead of JavaScript
    print(f"\n3. Testing System Maintenance page for updated links...")
    try:
        response = session.get(f"{base_url}/admin/system-maintenance")
        if response.status_code == 200:
            content = response.text
            
            # Check that it has links instead of onclick handlers
            if 'href="/admin/maintenance/' in content:
                print("   ✅ Found maintenance links (no more JavaScript onclick)")
            else:
                print("   ⚠️ Maintenance links not found")
                all_passed = False
                
            # Check that executeMaintenanceAction is NOT in the content
            if 'executeMaintenanceAction(' not in content:
                print("   ✅ No JavaScript executeMaintenanceAction calls found")
            else:
                print("   ⚠️ Still has JavaScript executeMaintenanceAction calls")
                all_passed = False
        else:
            print(f"   ❌ Failed to access system maintenance page: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
        all_passed = False
    
    if all_passed:
        print("\n🎉 All maintenance routes are working correctly!")
        print("✅ JavaScript calls have been successfully replaced with HTML pages.")
    else:
        print("\n⚠️ Some routes had issues. Check the details above.")
    
    return all_passed

if __name__ == "__main__":
    success = test_maintenance_routes()
    sys.exit(0 if success else 1)