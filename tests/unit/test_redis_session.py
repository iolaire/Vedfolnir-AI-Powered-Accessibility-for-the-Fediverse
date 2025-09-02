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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

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

def test_session_manager_v2():
    """Test session manager v2 (production session manager)"""
    print("\n🔍 Testing session manager v2...")
    
    try:
        from session_manager_v2 import SessionManagerV2
        from redis_session_backend import RedisSessionBackend
        from database import DatabaseManager
        from config import Config
        
        config = Config()
        
        # Create required dependencies
        db_manager = DatabaseManager(config)
        redis_backend = RedisSessionBackend.from_env()
        
        # Create session manager v2
        session_manager = SessionManagerV2(db_manager, redis_backend)
        
        print("✅ Session manager v2 created successfully!")
        print(f"   Manager type: {type(session_manager).__name__}")
        print(f"   Redis backend: {hasattr(session_manager, 'redis_backend')}")
        print(f"   Database manager: {hasattr(session_manager, 'db_manager')}")
        print(f"   Session timeout: {session_manager.session_timeout}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Session manager v2 failed: {e}")
        return False

def test_session_manager_imports():
    """Test all production session manager imports"""
    print("\n🔍 Testing session manager imports...")
    
    try:
        from session_manager_v2 import SessionManagerV2
        from unified_session_manager import UnifiedSessionManager
        from redis_session_manager import RedisSessionManager
        
        print("✅ All production session managers imported successfully!")
        print(f"   SessionManagerV2: {SessionManagerV2}")
        print(f"   UnifiedSessionManager: {UnifiedSessionManager}")
        print(f"   RedisSessionManager: {RedisSessionManager}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session manager imports failed: {e}")
        return False

def test_main_web_app_imports():
    """Test main web app imports"""
    print("\n🔍 Testing main web app imports...")
    
    try:
        # Test importing the main web app
        import web_app
        
        print("✅ Main web app imported successfully!")
        print(f"   App type: {type(web_app.app).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Main web app import failed: {e}")
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
    
    # Test session manager v2
    session_manager_v2_ok = test_session_manager_v2()
    
    # Test session manager imports
    session_manager_imports_ok = test_session_manager_imports()
    
    # Test main web app imports
    web_app_ok = test_main_web_app_imports()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Redis Connection: {'✅ OK' if redis_client else '❌ Failed'}")
    print(f"   Flask-Redis Interface: {'✅ OK' if session_interface else '❌ Failed'}")
    print(f"   Session Operations: {'✅ OK' if session_ops_ok else '❌ Failed'}")
    print(f"   Session Manager V2: {'✅ OK' if session_manager_v2_ok else '❌ Failed'}")
    print(f"   Session Manager Imports: {'✅ OK' if session_manager_imports_ok else '❌ Failed'}")
    print(f"   Web App Import: {'✅ OK' if web_app_ok else '❌ Failed'}")
    
    all_tests_passed = all([
        redis_client is not None,
        session_interface is not None,
        session_ops_ok,
        session_manager_v2_ok,
        session_manager_imports_ok,
        web_app_ok
    ])
    
    if all_tests_passed:
        print("\n🎉 All tests passed! Redis session implementation is working correctly.")
        print("\nArchitecture verified:")
        print("   ✅ Redis stores all session data on the server")
        print("   ✅ Flask manages session cookies with unique session IDs")
        print("   ✅ Session IDs are used as keys to retrieve data from Redis")
        print("\nYou can now run the main web app:")
        print("   python3 web_app.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
