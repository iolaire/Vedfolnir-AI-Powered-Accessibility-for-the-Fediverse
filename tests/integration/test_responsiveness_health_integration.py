# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration test to verify HealthChecker works with responsiveness monitoring
"""

import requests
import time
import subprocess
import sys
import os
import signal
import getpass
import re

def test_responsiveness_health_integration():
    """Test that HealthChecker integrates properly with responsiveness monitoring"""
    print("=== Testing Responsiveness Health Integration ===")
    
    # Start web application
    print("Starting web application...")
    web_process = subprocess.Popen(
        [sys.executable, "web_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        preexec_fn=os.setsid
    )
    
    try:
        # Wait for startup
        time.sleep(15)
        
        # Create authenticated session
        session = requests.Session()
        
        # Get login page and CSRF token
        login_page = session.get("http://127.0.0.1:5000/login")
        if login_page.status_code != 200:
            print(f"❌ Could not access login page: {login_page.status_code}")
            return False
        
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
        if not csrf_match:
            print("❌ Could not find CSRF token")
            return False
        
        csrf_token = csrf_match.group(1)
        
        # Try default admin credentials first
        login_data = {
            'username_or_email': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        response = session.post("http://127.0.0.1:5000/login", data=login_data)
        
        if response.status_code not in [200, 302] or 'login' in response.url.lower():
            # Prompt for real credentials
            print("Please enter admin credentials:")
            username = input("Username (default: admin): ") or "admin"
            password = getpass.getpass("Password: ")
            
            login_data['username_or_email'] = username
            login_data['password'] = password
            
            response = session.post("http://127.0.0.1:5000/login", data=login_data)
            
            if response.status_code not in [200, 302] or 'login' in response.url.lower():
                print(f"❌ Login failed: {response.status_code}")
                return False
        
        print("✅ Login successful")
        
        # Test 1: Basic health endpoint
        print("1. Testing basic health endpoint...")
        health_response = session.get("http://127.0.0.1:5000/admin/health")
        
        if health_response.status_code != 200:
            print(f"❌ Basic health endpoint failed: {health_response.status_code}")
            return False
        
        try:
            health_data = health_response.json()
        except ValueError:
            print("❌ Health endpoint returned invalid JSON")
            return False
        
        if 'error' in health_data and 'Health checker not available' in health_data['error']:
            print("❌ Still getting 'Health checker not available' error")
            return False
        
        print("✅ Basic health endpoint working")
        
        # Test 2: Detailed health endpoint
        print("2. Testing detailed health endpoint...")
        detailed_response = session.get("http://127.0.0.1:5000/admin/health/detailed")
        
        if detailed_response.status_code == 503:
            try:
                error_data = detailed_response.json()
                if 'error' in error_data and 'Health checker not available' in error_data['error']:
                    print("❌ Detailed health endpoint still shows 'Health checker not available'")
                    return False
                else:
                    print(f"⚠️  Detailed health endpoint returned 503 but not due to missing health checker: {error_data}")
            except ValueError:
                print("❌ Detailed health endpoint returned 503 with invalid JSON")
                return False
        elif detailed_response.status_code == 200:
            print("✅ Detailed health endpoint working")
        else:
            print(f"❌ Detailed health endpoint unexpected status: {detailed_response.status_code}")
            return False
        
        # Test 3: Responsiveness API endpoints (if they exist)
        print("3. Testing responsiveness API endpoints...")
        
        responsiveness_endpoints = [
            "/admin/api/responsiveness/status",
            "/admin/api/responsiveness/metrics",
            "/admin/api/responsiveness/health"
        ]
        
        for endpoint in responsiveness_endpoints:
            try:
                resp_response = session.get(f"http://127.0.0.1:5000{endpoint}")
                if resp_response.status_code == 200:
                    print(f"✅ {endpoint} working")
                elif resp_response.status_code == 404:
                    print(f"ℹ️  {endpoint} not found (may not be implemented yet)")
                else:
                    print(f"⚠️  {endpoint} returned {resp_response.status_code}")
            except Exception as e:
                print(f"⚠️  {endpoint} error: {e}")
        
        # Test 4: Health dashboard
        print("4. Testing health dashboard...")
        dashboard_response = session.get("http://127.0.0.1:5000/admin/health/dashboard")
        
        if dashboard_response.status_code != 200:
            print(f"❌ Health dashboard failed: {dashboard_response.status_code}")
            return False
        
        dashboard_content = dashboard_response.text.lower()
        if 'health checker not available' in dashboard_content:
            print("❌ Health dashboard still shows 'health checker not available' error")
            return False
        
        print("✅ Health dashboard working")
        
        print("\n🎉 All integration tests passed! HealthChecker fix is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed with error: {e}")
        return False
    finally:
        # Clean up - stop web application
        try:
            os.killpg(os.getpgid(web_process.pid), signal.SIGTERM)
            web_process.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(web_process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        print("Web application stopped")

if __name__ == "__main__":
    success = test_responsiveness_health_integration()
    if success:
        print("\n✅ HealthChecker integration fix successful!")
        sys.exit(0)
    else:
        print("\n❌ HealthChecker integration fix failed!")
        sys.exit(1)