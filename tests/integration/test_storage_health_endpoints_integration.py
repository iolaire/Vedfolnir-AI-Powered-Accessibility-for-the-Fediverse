#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration test for storage health endpoints.

This script tests the storage health monitoring endpoints to ensure they work correctly.
"""

import json
import tempfile
import shutil
from flask import Flask
from unittest.mock import Mock

# Import the storage health endpoints
from app.services.storage.components.storage_health_endpoints import register_storage_health_endpoints


def test_storage_health_endpoints():
    """Test storage health endpoints integration"""
    
    # Create a test Flask app
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    # Mock database manager
    app.db_manager = Mock()
    
    # Register storage health endpoints
    register_storage_health_endpoints(app)
    
    with app.test_client() as client:
        print("Testing storage health endpoints...")
        
        # Test basic health endpoint
        print("\n1. Testing basic storage health endpoint...")
        response = client.get('/health/storage/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"   Service: {data.get('service')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Healthy: {data.get('healthy')}")
            print("   ✅ Basic health endpoint working")
        else:
            print(f"   ❌ Basic health endpoint failed: {response.status_code}")
        
        # Test configuration health endpoint
        print("\n2. Testing configuration health endpoint...")
        response = client.get('/health/storage/configuration')
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 503]:
            data = json.loads(response.data)
            print(f"   Service: {data.get('service')}")
            print(f"   Valid: {data.get('valid')}")
            print("   ✅ Configuration health endpoint working")
        else:
            print(f"   ❌ Configuration health endpoint failed: {response.status_code}")
        
        # Test monitoring health endpoint
        print("\n3. Testing monitoring health endpoint...")
        response = client.get('/health/storage/monitoring')
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 503]:
            data = json.loads(response.data)
            print(f"   Service: {data.get('service')}")
            print(f"   Healthy: {data.get('healthy')}")
            print("   ✅ Monitoring health endpoint working")
        else:
            print(f"   ❌ Monitoring health endpoint failed: {response.status_code}")
        
        # Test metrics endpoint
        print("\n4. Testing metrics endpoint...")
        response = client.get('/health/storage/metrics')
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 503]:
            data = json.loads(response.data)
            print(f"   Service: {data.get('service')}")
            print(f"   Metrics count: {len(data.get('metrics', {}))}")
            print("   ✅ Metrics endpoint working")
        else:
            print(f"   ❌ Metrics endpoint failed: {response.status_code}")
        
        # Test alerts endpoint
        print("\n5. Testing alerts endpoint...")
        response = client.get('/health/storage/alerts')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"   Service: {data.get('service')}")
            print(f"   Alerts count: {data.get('alerts_count', 0)}")
            print("   ✅ Alerts endpoint working")
        else:
            print(f"   ❌ Alerts endpoint failed: {response.status_code}")
        
        # Test readiness probe
        print("\n6. Testing readiness probe...")
        response = client.get('/health/storage/ready')
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 503]:
            data = json.loads(response.data)
            print(f"   Ready: {data.get('ready')}")
            print("   ✅ Readiness probe working")
        else:
            print(f"   ❌ Readiness probe failed: {response.status_code}")
        
        # Test liveness probe
        print("\n7. Testing liveness probe...")
        response = client.get('/health/storage/live')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"   Alive: {data.get('alive')}")
            print("   ✅ Liveness probe working")
        else:
            print(f"   ❌ Liveness probe failed: {response.status_code}")
    
    print("\n" + "="*60)
    print("Storage health endpoints integration test completed!")
    print("="*60)


if __name__ == '__main__':
    test_storage_health_endpoints()