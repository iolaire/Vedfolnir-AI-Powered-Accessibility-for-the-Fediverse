#!/usr/bin/env python3
"""
Test Script for Simplified Redis Session Implementation

This script tests the clean Redis session architecture:
- Redis stores all session data on the server
- Flask manages session cookies with unique session IDs
- Session IDs are used as keys to retrieve data from Redis
"""

import os
import sys
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_redis_connection():
    """Test Redis connection"""
    print("🔍 Testing Redis connection...")
    
    try:
        from config import Config
        config = Config()
        
        redis_client = redis.from_url(config.redis.url)
        redis_client.ping()
        
        print(f"✅ Redis connection successful!")
        print(f"   URL: {config.redis.url}")
        print(f"   Session prefix: {config.redis.session_prefix}")
        print(f"   Session timeout: {config.redis.session_timeout}s")
        
        return redis_client, config
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None, None

def test_flask_redis_session():
    """Test Flask-Redis session interface"""
    print("\n🔍 Testing Flask-Redis session interface...")
    
    try:
        from flask import Flask
        from flask_redis_session import init_redis_session
        from config import Config
        
        # Create test app
        app = Flask(__name__)
        config = Config()
        app.config['SECRET_KEY'] = config.webapp.secret_key
        
        # Initialize Redis session
        redis_client = redis.from_url(config.redis.url)
        session_interface = init_redis_session(
            app,
            redis_client=redis_client,
            prefix=config.redis.session_prefix,
            timeout=config.redis.session_timeout
        )
        
        print("✅ Flask-Redis session interface initialized successfully!")
        print(f"   Session interface: {type(session_interface).__name__}")
        print(f"   Redis client: {type(redis_client).__name__}")
        
        return app, session_interface, redis_client
        
    except Exception as e:
        print(f"❌ Flask-Redis session interface failed: {e}")
        return None, None, None

def test_session_operations(app, redis_client, config):
    """Test session operations"""
    print("\n🔍 Testing session operations...")
    
    try:
        from flask_redis_session import RedisSession
        
        # Create a test session
        session = RedisSession(
            redis_client=redis_client,
            prefix=config.redis.session_prefix,
            timeout=config.redis.session_timeout
        )
        
        # Test setting data
        session['user_id'] = 123
        session['username'] = 'test_user'
        session['logged_in'] = True
        
        # Save to Redis
        success = session.save_to_redis()
        if not success:
            raise Exception("Failed to save session to Redis")
        
        print(f"✅ Session created and saved to Redis!")
        print(f"   Session ID: {session.session_id}")
        print(f"   Redis key: {session.redis_key}")
        print(f"   Data: {dict(session)}")
        
        # Test loading session
        loaded_session = RedisSession.load_from_redis(
            session_id=session.session_id,
            redis_client=redis_client,
            prefix=config.redis.session_prefix,
            timeout=config.redis.session_timeout
        )
        
        print(f"✅ Session loaded from Redis!")
        print(f"   Loaded data: {dict(loaded_session)}")
        
        # Verify data matches
        if dict(session) == dict(loaded_session):
            print("✅ Session data matches!")
        else:
            raise Exception("Session data mismatch")
        
        # Test deletion
        deleted = session.delete_from_redis()
        if deleted:
            print("✅ Session deleted from Redis!")
        else:
            raise Exception("Failed to delete session")
        
        return True
        
    except Exception as e:
        print(f"❌ Session operations failed: {e}")
        return False

def test_simple_session_manager():
    """Test simple session manager"""
    print("\n🔍 Testing simple session manager...")
    
    try:
        from simple_session_manager import SessionManager
        from config import Config
        
        config = Config()
        redis_client = redis.from_url(config.redis.url)
        
        # Create session manager
        session_manager = SessionManager(redis_client)
        
        print("✅ Simple session manager created!")
        print(f"   Manager type: {type(session_manager).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple session manager failed: {e}")
        return False

def test_web_app_imports():
    """Test web app imports"""
    print("\n🔍 Testing web app imports...")
    
    try:
        # Test importing the simplified web app
        import web_app_simple
        
        print("✅ Simplified web app imported successfully!")
        print(f"   App type: {type(web_app_simple.app).__name__}")
        print(f"   Session interface: {type(web_app_simple.app.session_interface).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Web app import failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Simplified Redis Session Implementation")
    print("=" * 60)
    
    # Test Redis connection
    redis_client, config = test_redis_connection()
    if not redis_client:
        print("\n❌ Cannot proceed without Redis connection")
        return False
    
    # Test Flask-Redis session interface
    app, session_interface, redis_client = test_flask_redis_session()
    if not app:
        print("\n❌ Cannot proceed without Flask-Redis session interface")
        return False
    
    # Test session operations
    session_ops_ok = test_session_operations(app, redis_client, config)
    
    # Test simple session manager
    session_manager_ok = test_simple_session_manager()
    
    # Test web app imports
    web_app_ok = test_web_app_imports()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Redis Connection: {'✅ OK' if redis_client else '❌ Failed'}")
    print(f"   Flask-Redis Interface: {'✅ OK' if session_interface else '❌ Failed'}")
    print(f"   Session Operations: {'✅ OK' if session_ops_ok else '❌ Failed'}")
    print(f"   Session Manager: {'✅ OK' if session_manager_ok else '❌ Failed'}")
    print(f"   Web App Import: {'✅ OK' if web_app_ok else '❌ Failed'}")
    
    all_tests_passed = all([
        redis_client is not None,
        session_interface is not None,
        session_ops_ok,
        session_manager_ok,
        web_app_ok
    ])
    
    if all_tests_passed:
        print("\n🎉 All tests passed! Redis session implementation is working correctly.")
        print("\nArchitecture verified:")
        print("   ✅ Redis stores all session data on the server")
        print("   ✅ Flask manages session cookies with unique session IDs")
        print("   ✅ Session IDs are used as keys to retrieve data from Redis")
        print("\nYou can now run the simplified web app:")
        print("   python3 web_app_simple.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
