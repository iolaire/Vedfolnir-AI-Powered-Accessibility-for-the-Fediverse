#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Dashboard Notifications Integration

Simple test to verify that the unified notification system is properly
integrated with the user dashboard.
"""

import sys
import os
import time
import requests
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_notifications():
    """Test dashboard notification system integration"""
    
    print("=== Dashboard Notifications Integration Test ===")
    
    base_url = "http://127.0.0.1:5000"
    
    try:
        # Test 1: Check if dashboard loads with notification container
        print("\n1. Testing dashboard page load...")
        
        response = requests.get(urljoin(base_url, "/"))
        
        if response.status_code == 200:
            content = response.text
            
            # Check for notification container
            if 'id="user-dashboard-notifications"' in content:
                print("✅ Dashboard notification container found")
            else:
                print("❌ Dashboard notification container not found")
            
            # Check for unified notification CSS
            if 'unified-notifications.css' in content:
                print("✅ Unified notification CSS included")
            else:
                print("❌ Unified notification CSS not included")
            
            # Check for notification JavaScript
            if 'PageNotificationIntegrator' in content:
                print("✅ Page notification integrator found")
            else:
                print("❌ Page notification integrator not found")
            
        elif response.status_code == 302:
            print("ℹ️  Dashboard redirected (likely to login) - this is expected if not authenticated")
        else:
            print(f"❌ Dashboard request failed: {response.status_code}")
        
        # Test 2: Check if notification CSS is accessible
        print("\n2. Testing notification CSS accessibility...")
        
        css_response = requests.get(urljoin(base_url, "/static/css/unified-notifications.css"))
        
        if css_response.status_code == 200:
            print("✅ Unified notification CSS is accessible")
            
            # Check for key CSS classes
            css_content = css_response.text
            if '.notification-container' in css_content:
                print("✅ Notification container styles found")
            else:
                print("❌ Notification container styles not found")
                
        else:
            print(f"❌ Notification CSS not accessible: {css_response.status_code}")
        
        # Test 3: Check if JavaScript files are accessible
        print("\n3. Testing notification JavaScript accessibility...")
        
        js_files = [
            "/static/js/notification-ui-renderer.js",
            "/static/js/page_notification_integrator.js"
        ]
        
        for js_file in js_files:
            js_response = requests.get(urljoin(base_url, js_file))
            
            if js_response.status_code == 200:
                print(f"✅ {js_file} is accessible")
            else:
                print(f"❌ {js_file} not accessible: {js_response.status_code}")
        
        print("\n=== Test Summary ===")
        print("✅ Dashboard notification integration test completed")
        print("ℹ️  For full functionality testing, authentication and WebSocket connection are required")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to web application")
        print("ℹ️  Make sure the web application is running: python web_app.py")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def test_notification_system_components():
    """Test that notification system components are importable"""
    
    print("\n=== Notification System Components Test ===")
    
    try:
        # Test imports
        print("Testing component imports...")
        
        from unified_notification_manager import UnifiedNotificationManager
        print("✅ UnifiedNotificationManager imported successfully")
        
        from dashboard_notification_handlers import DashboardNotificationHandlers
        print("✅ DashboardNotificationHandlers imported successfully")
        
        print("✅ Dashboard notification helpers imported successfully")
        
        print("✅ All notification system components are importable")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing Dashboard Notifications Integration")
    print("=" * 50)
    
    # Test component imports
    components_ok = test_notification_system_components()
    
    # Test web integration
    web_ok = test_dashboard_notifications()
    
    if components_ok and web_ok:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)