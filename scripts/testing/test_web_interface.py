#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Quick test script to check if the web interface is working properly
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

def test_web_interface():
    """Test basic web interface functionality"""
    print("🧪 Testing Web Interface...")
    
    # Start the web app
    print("Starting web application...")
    process = start_web_app()
    
    if not process:
        print("❌ Failed to start web application")
        return False
    
    # Wait for the app to start
    time.sleep(3)
    
    try:
        # Test basic connectivity
        print("Testing basic connectivity...")
        response = requests.get('http://localhost:5000', timeout=5)
        
        if response.status_code == 200:
            print("✅ Web interface is accessible")
            
            # Check if CSS files are loading
            if 'style.css' in response.text:
                print("✅ CSS files are referenced")
            else:
                print("⚠️  CSS files may not be loading properly")
            
            # Check if JavaScript files are loading
            if 'app.js' in response.text:
                print("✅ JavaScript files are referenced")
            else:
                print("⚠️  JavaScript files may not be loading properly")
            
            # Check if Bootstrap is loading
            if 'bootstrap' in response.text:
                print("✅ Bootstrap is referenced")
            else:
                print("⚠️  Bootstrap may not be loading properly")
            
            # Test CSS file accessibility
            css_response = requests.get('http://localhost:5000/static/css/style.css', timeout=5)
            if css_response.status_code == 200:
                print("✅ Main CSS file is accessible")
            else:
                print("❌ Main CSS file is not accessible")
            
            # Test fixes CSS file accessibility
            fixes_css_response = requests.get('http://localhost:5000/static/css/fixes.css', timeout=5)
            if fixes_css_response.status_code == 200:
                print("✅ Fixes CSS file is accessible")
            else:
                print("❌ Fixes CSS file is not accessible")
            
            # Test JavaScript file accessibility
            js_response = requests.get('http://localhost:5000/static/js/app.js', timeout=5)
            if js_response.status_code == 200:
                print("✅ Main JavaScript file is accessible")
            else:
                print("❌ Main JavaScript file is not accessible")
            
            print("\n🎉 Web interface appears to be working correctly!")
            return True
            
        else:
            print(f"❌ Web interface returned status code: {response.status_code}")
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
    success = test_web_interface()
    sys.exit(0 if success else 1)