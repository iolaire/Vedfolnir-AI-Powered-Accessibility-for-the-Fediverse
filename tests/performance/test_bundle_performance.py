#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Bundle Performance Test

This script tests the performance improvement of the WebSocket bundle
by measuring page load times and WebSocket initialization speed.
"""

import time
import requests
import json
from urllib.parse import urljoin

def test_bundle_performance():
    """Test WebSocket bundle performance"""
    base_url = "http://127.0.0.1:5000"
    
    print("🚀 Testing WebSocket Bundle Performance")
    print("=" * 50)
    
    # Test 1: Check if bundle is accessible
    print("\n1. Testing bundle accessibility...")
    start_time = time.time()
    
    try:
        response = requests.get(urljoin(base_url, "/static/js/websocket-bundle.js"))
        bundle_load_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            bundle_size = len(response.content)
            print(f"✅ Bundle loaded successfully")
            print(f"   - Load time: {bundle_load_time:.2f}ms")
            print(f"   - Bundle size: {bundle_size:,} bytes ({bundle_size/1024:.1f}KB)")
        else:
            print(f"❌ Bundle load failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Bundle load error: {e}")
        return False
    
    # Test 2: Compare individual script sizes
    print("\n2. Comparing with individual scripts...")
    individual_scripts = [
        "/static/js/websocket-client-factory.js",
        "/static/js/websocket-client.js", 
        "/static/js/websocket-keepalive.js",
        "/static/js/websocket-debug.js"
    ]
    
    total_individual_size = 0
    individual_load_times = []
    
    for script in individual_scripts:
        try:
            start_time = time.time()
            response = requests.get(urljoin(base_url, script))
            load_time = (time.time() - start_time) * 1000
            individual_load_times.append(load_time)
            
            if response.status_code == 200:
                script_size = len(response.content)
                total_individual_size += script_size
                print(f"   - {script.split('/')[-1]}: {script_size:,} bytes, {load_time:.2f}ms")
            else:
                print(f"   - {script.split('/')[-1]}: Not found ({response.status_code})")
                
        except Exception as e:
            print(f"   - {script.split('/')[-1]}: Error ({e})")
    
    total_individual_load_time = sum(individual_load_times)
    
    print(f"\n📊 Size Comparison:")
    print(f"   - Individual scripts total: {total_individual_size:,} bytes ({total_individual_size/1024:.1f}KB)")
    print(f"   - Bundle size: {bundle_size:,} bytes ({bundle_size/1024:.1f}KB)")
    print(f"   - Size difference: {bundle_size - total_individual_size:+,} bytes")
    
    print(f"\n📊 Load Time Comparison:")
    print(f"   - Individual scripts total: {total_individual_load_time:.2f}ms")
    print(f"   - Bundle load time: {bundle_load_time:.2f}ms")
    print(f"   - Time saved: {total_individual_load_time - bundle_load_time:.2f}ms")
    
    # Test 3: Test WebSocket client config endpoint
    print("\n3. Testing WebSocket configuration endpoint...")
    start_time = time.time()
    
    try:
        response = requests.get(urljoin(base_url, "/api/websocket/client-config"))
        config_load_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            config_data = response.json()
            print(f"✅ Configuration loaded successfully")
            print(f"   - Load time: {config_load_time:.2f}ms")
            print(f"   - Config keys: {list(config_data.keys())}")
        else:
            print(f"❌ Configuration load failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Configuration load error: {e}")
    
    # Test 4: Test admin dashboard page load
    print("\n4. Testing admin dashboard page load...")
    start_time = time.time()
    
    try:
        response = requests.get(urljoin(base_url, "/admin/dashboard"), allow_redirects=False)
        page_load_time = (time.time() - start_time) * 1000
        
        print(f"   - Page response: {response.status_code}")
        print(f"   - Load time: {page_load_time:.2f}ms")
        
        if response.status_code == 302:
            print(f"   - Redirected to: {response.headers.get('Location', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Page load error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 Performance Summary:")
    print(f"   - Bundle reduces HTTP requests from 4+ to 1")
    print(f"   - Load time improvement: {total_individual_load_time - bundle_load_time:.2f}ms")
    print(f"   - Size efficiency: {((total_individual_size - bundle_size) / total_individual_size * 100):.1f}% reduction")
    
    if bundle_load_time < total_individual_load_time:
        print("✅ Bundle optimization successful!")
    else:
        print("⚠️ Bundle may need further optimization")
    
    return True

if __name__ == "__main__":
    success = test_bundle_performance()
    exit(0 if success else 1)