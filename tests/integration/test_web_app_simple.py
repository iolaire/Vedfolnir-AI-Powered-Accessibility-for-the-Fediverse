#!/usr/bin/env python3
"""
Test script to check for import errors in web_app_simple.py
"""

import sys
import traceback

def test_imports():
    """Test importing web_app_simple to catch any errors"""
    print("🔍 Testing web_app_simple.py imports...")
    
    try:
        import web_app_simple
        print("✅ web_app_simple.py imported successfully!")
        print(f"   App type: {type(web_app_simple.app)}")
        print(f"   Template folder: {web_app_simple.app.template_folder}")
        print(f"   Session interface: {type(web_app_simple.app.session_interface)}")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

def test_app_creation():
    """Test creating the Flask app"""
    print("\n🔍 Testing Flask app creation...")
    
    try:
        from flask import Flask
        import os
        
        # Test template directory creation
        template_dir = os.path.join(os.path.dirname(__file__), 'templates_simple')
        os.makedirs(template_dir, exist_ok=True)
        
        # Test Flask app with custom template folder
        app = Flask(__name__, template_folder='templates_simple')
        
        print("✅ Flask app created successfully!")
        print(f"   Template folder: {app.template_folder}")
        print(f"   Template directory exists: {os.path.exists(template_dir)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        traceback.print_exc()
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("\n🔍 Testing Redis connection...")
    
    try:
        from config import Config
        import redis
        
        config = Config()
        redis_client = redis.from_url(config.redis.url)
        redis_client.ping()
        
        print("✅ Redis connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing web_app_simple.py")
    print("=" * 40)
    
    # Test individual components
    redis_ok = test_redis_connection()
    app_creation_ok = test_app_creation()
    import_ok = test_imports()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"   Redis Connection: {'✅ OK' if redis_ok else '❌ Failed'}")
    print(f"   App Creation: {'✅ OK' if app_creation_ok else '❌ Failed'}")
    print(f"   Import Test: {'✅ OK' if import_ok else '❌ Failed'}")
    
    if all([redis_ok, app_creation_ok, import_ok]):
        print("\n🎉 All tests passed! web_app_simple.py should work.")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    return all([redis_ok, app_creation_ok, import_ok])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
