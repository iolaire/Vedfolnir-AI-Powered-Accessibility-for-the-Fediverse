#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script to verify web interface authentication and styling
"""

import requests
import time
import subprocess
import sys
from threading import Thread

def start_web_app():
    """Start the web application in a subprocess"""
    try:
        process = subprocess.Popen([
            sys.executable, 'web_app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process
    except Exception as e:
        print(f"Failed to start web app: {e}")
        return None

def test_web_interface_with_auth():
    """Test web interface with authentication"""
    print("🧪 Testing Web Interface with Authentication...")
    
    # Start the web app
    print("Starting web application...")
    process = start_web_app()
    
    if not process:
        print("❌ Failed to start web application")
        return False
    
    # Wait for the app to start
    time.sleep(3)
    
    try:
        # Create a session for maintaining cookies
        session = requests.Session()
        
        # Set a proper browser user agent to avoid security blocks
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Test 1: Check if login page is accessible
        print("Testing login page accessibility...")
        login_response = session.get('http://localhost:5000/login', timeout=5)
        
        if login_response.status_code == 200:
            print("✅ Login page is accessible")
            
            # Test 2: Attempt to login with admin credentials
            print("Testing admin login...")
            login_data = {
                'username': 'admin',
                'password': '23424*(FSDFSF)'
            }
            
            # Get CSRF token if present
            if 'csrf_token' in login_response.text:
                # Simple extraction - in real app you'd parse properly
                import re
                csrf_match = re.search(r'name="csrf_token".*?value="([^"]+)"', login_response.text)
                if csrf_match:
                    login_data['csrf_token'] = csrf_match.group(1)
            
            login_post = session.post('http://localhost:5000/login', data=login_data, timeout=5)
            
            if login_post.status_code == 302 or 'dashboard' in login_post.text.lower():
                print("✅ Admin login successful")
                
                # Test 3: Access dashboard after login
                print("Testing dashboard access...")
                dashboard_response = session.get('http://localhost:5000/', timeout=5)
                
                if dashboard_response.status_code == 200:
                    print("✅ Dashboard is accessible after login")
                    
                    # Test 4: Check if CSS files are loading
                    if 'style.css' in dashboard_response.text:
                        print("✅ CSS files are referenced in dashboard")
                    else:
                        print("⚠️  CSS files may not be loading properly")
                    
                    # Test 5: Check if platform management is accessible
                    print("Testing platform management page...")
                    platform_response = session.get('http://localhost:5000/platform_management', timeout=5)
                    
                    if platform_response.status_code == 200:
                        print("✅ Platform management page is accessible")
                        
                        # Check for platform-specific content
                        if 'Platform Connections' in platform_response.text:
                            print("✅ Platform management content is present")
                        else:
                            print("⚠️  Platform management content may be missing")
                    else:
                        print(f"❌ Platform management page returned status: {platform_response.status_code}")
                    
                    # Test 6: Test CSS file accessibility
                    css_response = session.get('http://localhost:5000/static/css/fixes.css', timeout=5)
                    if css_response.status_code == 200:
                        print("✅ Fixes CSS file is accessible")
                    else:
                        print("❌ Fixes CSS file is not accessible")
                    
                    print("\n🎉 Web interface authentication and basic functionality working!")
                    return True
                    
                else:
                    print(f"❌ Dashboard returned status code: {dashboard_response.status_code}")
                    return False
                    
            else:
                print(f"❌ Login failed with status: {login_post.status_code}")
                print("Response text:", login_post.text[:200])
                return False
                
        else:
            print(f"❌ Login page returned status code: {login_response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to web interface: {e}")
        return False
    
    finally:
        # Clean up
        if process:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    success = test_web_interface_with_auth()
    sys.exit(0 if success else 1)