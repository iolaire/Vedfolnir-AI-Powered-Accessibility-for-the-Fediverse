#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test dashboard user data using browser automation
"""

import time
import getpass
from playwright.sync_api import sync_playwright

def test_dashboard_with_browser():
    """Test dashboard using browser automation"""
    print("=== Testing Dashboard with Browser ===")
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.webkit.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Navigate to login page
            print("1. Navigating to login page...")
            page.goto("http://127.0.0.1:5000/login")
            page.wait_for_load_state('domcontentloaded')
            
            # Fill login form
            print("2. Filling login form...")
            password = "user2123"
            
            page.fill('input[name="username_or_email"]', 'does')
            page.fill('input[name="password"]', password)
            
            # Submit form
            print("3. Submitting login form...")
            page.click('button[type="submit"]')
            page.wait_for_load_state('domcontentloaded')
            
            # Check if we're redirected to dashboard
            current_url = page.url
            print(f"4. Current URL after login: {current_url}")
            
            if 'login' in current_url:
                print("❌ Login failed - still on login page")
                return False
            
            # Navigate to dashboard
            print("5. Navigating to dashboard...")
            page.goto("http://127.0.0.1:5000/")
            page.wait_for_load_state('domcontentloaded')
            
            # Check page content
            print("6. Checking dashboard content...")
            page_content = page.content()
            
            # Look for dashboard indicators
            if "Dashboard" in page_content or "Statistics" in page_content:
                print("✅ Dashboard loaded successfully")
            else:
                print("⚠️  Dashboard may not have loaded properly")
            
            # Look for user-specific data
            if "admin" in page_content.lower():
                print("✅ Dashboard shows admin user context")
            else:
                print("⚠️  Dashboard may not show user context")
            
            # Look for stats and check if they show user-specific data
            stats_found = False
            if any(term in page_content for term in ["Total Posts", "Total Images", "posts", "images"]):
                print("✅ Dashboard contains statistics")
                stats_found = True
                
                # Check if it shows 0 posts/images (expected for test user "does")
                if "0 posts" in page_content.lower() or "0 images" in page_content.lower():
                    print("✅ Dashboard shows user-specific data (0 posts/images for test user)")
                elif "10 posts" in page_content.lower() or "10 images" in page_content.lower():
                    print("❌ Dashboard still shows global data (10 posts) instead of user-specific data")
                else:
                    print("⚠️  Could not determine if data is user-specific")
            else:
                print("⚠️  Dashboard may not contain statistics")
            
            # Take a screenshot for debugging
            page.screenshot(path="dashboard_test.png")
            print("📸 Screenshot saved as dashboard_test.png")
            
            # Wait a bit to see the page
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_dashboard_with_browser()
    exit(0 if success else 1)