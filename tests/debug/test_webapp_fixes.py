# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify webapp error fixes
"""

import sys
import os
import requests
import time
import subprocess
import signal
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_webapp_startup():
    """Test that the webapp starts without errors"""
    print("=== Testing WebApp Startup ===")
    
    # Start the webapp in background
    webapp_process = None
    try:
        webapp_process = subprocess.Popen(
            [sys.executable, 'web_app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.join(os.path.dirname(__file__), '..', '..')
        )
        
        # Wait for startup
        print("Starting webapp...")
        time.sleep(10)
        
        # Check if process is still running
        if webapp_process.poll() is not None:
            stdout, stderr = webapp_process.communicate()
            print(f"❌ WebApp failed to start")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
        
        # Test basic connectivity
        try:
            response = requests.get('http://127.0.0.1:5000', timeout=5)
            if response.status_code in [200, 302]:
                print("✅ WebApp started successfully")
                return True
            else:
                print(f"❌ WebApp returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to webapp: {e}")
            return False
            
    finally:
        # Clean up process
        if webapp_process and webapp_process.poll() is None:
            webapp_process.terminate()
            time.sleep(2)
            if webapp_process.poll() is None:
                webapp_process.kill()

def test_admin_access():
    """Test admin interface access"""
    print("\n=== Testing Admin Interface ===")
    
    try:
        # Test admin route accessibility (should redirect to login)
        response = requests.get('http://127.0.0.1:5000/admin/users', timeout=5)
        if response.status_code in [200, 302]:
            print("✅ Admin interface accessible (redirects properly)")
            return True
        else:
            print(f"❌ Admin interface returned unexpected status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to access admin interface: {e}")
        return False

def test_websocket_endpoint():
    """Test WebSocket endpoint doesn't cause WSGI errors"""
    print("\n=== Testing WebSocket Endpoint ===")
    
    try:
        # Test socket.io endpoint
        response = requests.get('http://127.0.0.1:5000/socket.io/?EIO=4&transport=polling', timeout=5)
        # Should not return 500 error
        if response.status_code != 500:
            print("✅ WebSocket endpoint accessible without WSGI errors")
            return True
        else:
            print(f"❌ WebSocket endpoint returned 500 error")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to access WebSocket endpoint: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing WebApp Error Fixes")
    print("=" * 40)
    
    # Start webapp for testing
    webapp_process = None
    try:
        webapp_process = subprocess.Popen(
            [sys.executable, 'web_app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.join(os.path.dirname(__file__), '..', '..')
        )
        
        print("Starting webapp for testing...")
        time.sleep(10)
        
        # Run tests
        tests = [
            test_webapp_startup,
            test_admin_access,
            test_websocket_endpoint
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 40)
        print("Test Results Summary:")
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("✅ All tests passed! WebApp errors have been fixed.")
            return True
        else:
            print("❌ Some tests failed. Check the output above for details.")
            return False
            
    finally:
        # Clean up
        if webapp_process and webapp_process.poll() is None:
            webapp_process.terminate()
            time.sleep(2)
            if webapp_process.poll() is None:
                webapp_process.kill()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)