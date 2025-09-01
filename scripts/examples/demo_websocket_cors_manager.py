# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket CORS Manager Demonstration

This script demonstrates the functionality of the WebSocket CORS Manager,
including dynamic origin calculation, validation, and Flask integration.
"""

import os
import sys
from flask import Flask

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from websocket_cors_manager import CORSManager
from websocket_config_manager import WebSocketConfigManager
from config import Config


def demonstrate_cors_manager():
    """Demonstrate WebSocket CORS Manager functionality"""
    
    print("=== WebSocket CORS Manager Demonstration ===\n")
    
    # Initialize components
    print("1. Initializing WebSocket Configuration Manager...")
    config = Config()
    config_manager = WebSocketConfigManager(config)
    
    print("2. Initializing CORS Manager...")
    cors_manager = CORSManager(config_manager)
    
    # Show allowed origins
    print("\n3. Dynamic CORS Origins:")
    origins = cors_manager.get_allowed_origins()
    for i, origin in enumerate(origins, 1):
        print(f"   {i:2d}. {origin}")
    
    print(f"\n   Total origins: {len(origins)}")
    
    # Test origin validation
    print("\n4. Origin Validation Tests:")
    test_origins = [
        "http://localhost:5000",
        "https://127.0.0.1:3000",
        "http://malicious-site.com",
        "invalid-url"
    ]
    
    for origin in test_origins:
        is_valid = cors_manager.validate_origin(origin)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"   {origin:<30} -> {status}")
    
    # Test WebSocket-specific validation
    print("\n5. WebSocket Origin Validation:")
    websocket_origins = [
        ("http://localhost:5000", None),
        ("http://localhost:5000", "/admin"),
        ("http://evil.com", None)
    ]
    
    for origin, namespace in websocket_origins:
        is_valid, error = cors_manager.validate_websocket_origin(origin, namespace)
        status = "✅ VALID" if is_valid else f"❌ INVALID: {error}"
        namespace_str = f" (namespace: {namespace})" if namespace else ""
        print(f"   {origin}{namespace_str:<20} -> {status}")
    
    # Show SocketIO configuration
    print("\n6. SocketIO CORS Configuration:")
    socketio_config = cors_manager.get_cors_config_for_socketio()
    print(f"   CORS Credentials: {socketio_config['cors_credentials']}")
    print(f"   Allowed Origins: {len(socketio_config['cors_allowed_origins'])} origins")
    
    # Show debug information
    print("\n7. CORS Debug Information:")
    debug_info = cors_manager.get_cors_debug_info()
    
    print(f"   Environment:")
    for key, value in debug_info['environment'].items():
        print(f"     {key}: {value}")
    
    print(f"   Origin Patterns: {len(debug_info['origin_patterns'])} patterns")
    
    # Test Flask integration
    print("\n8. Flask Integration Test:")
    app = Flask(__name__)
    
    # Setup CORS
    cors_manager.setup_cors_headers(app)
    cors_manager.handle_preflight_requests(app)
    
    print("   ✅ CORS headers configured")
    print("   ✅ Preflight handlers configured")
    
    # Test with Flask test client
    with app.test_client() as client:
        # Test preflight request
        response = client.options('/', headers={
            'Origin': 'http://localhost:5000',
            'Access-Control-Request-Method': 'POST'
        })
        
        if response.status_code == 200:
            print("   ✅ Preflight request successful")
            print(f"      Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        else:
            print(f"   ❌ Preflight request failed: {response.status_code}")
    
    # Test protocol detection
    print("\n9. Protocol Detection Test:")
    with app.test_request_context('/', headers={'X-Forwarded-Proto': 'https'}):
        protocol = cors_manager.detect_protocol_from_request()
        print(f"   Detected protocol: {protocol}")
        
        dynamic_origin = cors_manager.get_dynamic_origin_for_client()
        print(f"   Dynamic client origin: {dynamic_origin}")
    
    print("\n=== Demonstration Complete ===")


def test_environment_configurations():
    """Test CORS manager with different environment configurations"""
    
    print("\n=== Environment Configuration Tests ===\n")
    
    # Test with custom host
    print("1. Testing with custom host configuration:")
    os.environ['FLASK_HOST'] = 'example.com'
    os.environ['FLASK_PORT'] = '8080'
    os.environ['FLASK_ENV'] = 'production'
    
    config = Config()
    config_manager = WebSocketConfigManager(config)
    cors_manager = CORSManager(config_manager)
    
    origins = cors_manager.get_allowed_origins()
    custom_origins = [origin for origin in origins if 'example.com' in origin]
    
    print(f"   Custom host origins found: {len(custom_origins)}")
    for origin in custom_origins:
        print(f"     - {origin}")
    
    # Test with explicit CORS origins
    print("\n2. Testing with explicit CORS origins:")
    os.environ['SOCKETIO_CORS_ORIGINS'] = 'http://app1.com,http://app2.com,https://app3.com'
    
    config_manager.reload_configuration()
    cors_manager.reload_configuration()
    
    origins = cors_manager.get_allowed_origins()
    explicit_origins = ['http://app1.com', 'http://app2.com', 'https://app3.com']
    
    print(f"   Explicit origins configured: {len(explicit_origins)}")
    for origin in explicit_origins:
        found = origin in origins
        status = "✅ Found" if found else "❌ Missing"
        print(f"     {origin} -> {status}")
    
    # Clean up environment
    for var in ['FLASK_HOST', 'FLASK_PORT', 'FLASK_ENV', 'SOCKETIO_CORS_ORIGINS']:
        if var in os.environ:
            del os.environ[var]
    
    print("\n   Environment cleaned up")


def performance_test():
    """Test CORS manager performance"""
    
    print("\n=== Performance Test ===\n")
    
    import time
    
    config = Config()
    config_manager = WebSocketConfigManager(config)
    cors_manager = CORSManager(config_manager)
    
    # Test origin calculation performance
    print("1. Origin calculation performance:")
    start_time = time.time()
    
    for _ in range(100):
        origins = cors_manager.get_allowed_origins()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"   100 origin calculations: {elapsed:.3f}s")
    print(f"   Average per calculation: {elapsed/100*1000:.2f}ms")
    
    # Test validation performance
    print("\n2. Origin validation performance:")
    origins = cors_manager.get_allowed_origins()
    test_origins = origins[:5] if len(origins) >= 5 else origins
    
    start_time = time.time()
    
    for _ in range(1000):
        for origin in test_origins:
            cors_manager.validate_origin(origin)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    total_validations = 1000 * len(test_origins)
    print(f"   {total_validations} validations: {elapsed:.3f}s")
    print(f"   Average per validation: {elapsed/total_validations*1000:.3f}ms")
    
    # Test caching effectiveness
    print("\n3. Caching effectiveness:")
    
    # Clear cache and measure first call
    cors_manager.clear_cache()
    start_time = time.time()
    origins1 = cors_manager.get_allowed_origins()
    first_call_time = time.time() - start_time
    
    # Measure cached call
    start_time = time.time()
    origins2 = cors_manager.get_allowed_origins()
    cached_call_time = time.time() - start_time
    
    speedup = first_call_time / cached_call_time if cached_call_time > 0 else float('inf')
    
    print(f"   First call (calculation): {first_call_time*1000:.2f}ms")
    print(f"   Cached call: {cached_call_time*1000:.2f}ms")
    print(f"   Speedup: {speedup:.1f}x")


if __name__ == '__main__':
    try:
        demonstrate_cors_manager()
        test_environment_configurations()
        performance_test()
        
    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted by user")
    except Exception as e:
        print(f"\n\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDemonstration finished.")