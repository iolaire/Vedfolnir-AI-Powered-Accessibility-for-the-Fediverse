# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify HealthChecker initialization fix
"""

import requests
import time
import sys

def test_health_checker_availability():
    """Test that the health checker is now available"""
    print("=== Testing HealthChecker Availability Fix ===")
    
    # Start the web application
    print("Starting web application...")
    import subprocess
    import os
    
    # Start web app in background
    web_process = subprocess.Popen(
        [sys.executable, "web_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    # Wait for startup
    time.sleep(10)
    
    try:
        # Test the health endpoint that was failing
        print("Testing /admin/health/detailed endpoint...")
        
        # First, we need to login as admin
        session = requests.Session()
        
        # Get login page
        login_page = session.get("http://127.0.0.1:5000/login")
        if login_page.status_code != 200:
            print(f"❌ Could not access login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token
        import re
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if not csrf_match:
            print("❌ Could not find CSRF token")
            return False
        
        csrf_token = csrf_match.group(1)
        
        # Login as admin
        import getpass
        print("Please enter admin credentials:")
        username = input("Username (default: admin): ") or "admin"
        password = getpass.getpass("Password: ")
        
        login_data = {
            'username_or_email': username,
            'password': password,
            'csrf_token': csrf_token
        }
        
        login_response = session.post("http://127.0.0.1:5000/login", data=login_data)
        if login_response.status_code not in [200, 302] or 'login' in login_response.url.lower():
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        print("✅ Login successful")
        
        # Test the health endpoint
        health_response = session.get("http://127.0.0.1:5000/admin/health/detailed")
        
        if health_response.status_code == 200:
            print("✅ Health endpoint accessible")
            
            # Check if we get the "Health checker not available" error
            response_data = health_response.json()
            if 'error' in response_data and 'Health checker not available' in response_data['error']:
                print("❌ Still getting 'Health checker not available' error")
                return False
            else:
                print("✅ Health checker is working - no 'not available' error")
                print(f"Health status: {response_data.get('status', 'unknown')}")
                return True
        else:
            print(f"❌ Health endpoint returned status: {health_response.status_code}")
            print(f"Response: {health_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Clean up - terminate web process
        web_process.terminate()
        web_process.wait()
        print("Web application stopped")

if __name__ == "__main__":
    success = test_health_checker_availability()
    if success:
        print("\n✅ HealthChecker fix successful!")
        sys.exit(0)
    else:
        print("\n❌ HealthChecker fix failed!")
        sys.exit(1)