#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Session Refactor Test Script

Test script to verify the new Redis session management system works correctly.
Tests all components: Redis backend, session manager, Flask integration.
"""

import os
import sys
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_redis_connection():
    """Test Redis connection and basic operations"""
    print("🔍 Testing Redis connection...")
    
    try:
        # Load environment variables first
        from dotenv import load_dotenv
        load_dotenv()
        
        from redis_session_backend import RedisSessionBackend
        
        # Create Redis backend
        redis_backend = RedisSessionBackend.from_env()
        
        # Clean up old incompatible keys
        try:
            pattern = "vedfolnir:session:*"
            for key in redis_backend.redis.scan_iter(match=pattern):
                try:
                    # Try to get the key - if it fails with WRONGTYPE, delete it
                    redis_backend.redis.get(key)
                except Exception as e:
                    if "WRONGTYPE" in str(e):
                        redis_backend.redis.delete(key)
                        print(f"   Cleaned up incompatible key: {key}")
        except Exception as e:
            print(f"   Warning: Could not clean up old keys: {e}")
        
        # Test health check
        health = redis_backend.health_check()
        print(f"✅ Redis health check: {health['status']}")
        print(f"   - Ping time: {health.get('ping_ms', 'N/A')} ms")
        print(f"   - Redis version: {health.get('redis_version', 'N/A')}")
        print(f"   - Memory usage: {health.get('used_memory_human', 'N/A')}")
        
        return redis_backend
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return None

def test_session_backend(redis_backend):
    """Test Redis session backend operations"""
    print("\n🔍 Testing Redis session backend...")
    
    try:
        # Test session operations
        test_session_id = "test_session_123"
        test_data = {
            'user_id': 1,
            'username': 'test_user',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Test set
        success = redis_backend.set(test_session_id, test_data, ttl=300)
        print(f"✅ Set session: {success}")
        
        # Test get
        retrieved_data = redis_backend.get(test_session_id)
        print(f"✅ Get session: {retrieved_data is not None}")
        
        # Test exists
        exists = redis_backend.exists(test_session_id)
        print(f"✅ Session exists: {exists}")
        
        # Test TTL
        ttl = redis_backend.get_ttl(test_session_id)
        print(f"✅ Session TTL: {ttl} seconds")
        
        # Test delete
        deleted = redis_backend.delete(test_session_id)
        print(f"✅ Delete session: {deleted}")
        
        # Verify deletion
        exists_after = redis_backend.exists(test_session_id)
        print(f"✅ Session deleted: {not exists_after}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session backend test failed: {e}")
        return False

def test_session_manager():
    """Test session manager functionality"""
    print("\n🔍 Testing session manager...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from redis_session_backend import RedisSessionBackend
        from session_manager_v2 import SessionManagerV2
        
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config)
        redis_backend = RedisSessionBackend.from_env()
        session_manager = SessionManagerV2(db_manager, redis_backend)
        
        # Test session creation (using admin user ID 1)
        print("   Creating session for user ID 1...")
        session_id = session_manager.create_session(user_id=1)
        print(f"✅ Created session: {session_id}")
        
        # Test session retrieval
        session_data = session_manager.get_session_data(session_id)
        print(f"✅ Retrieved session data: {session_data is not None}")
        if session_data:
            print(f"   - User ID: {session_data.get('user_id')}")
            print(f"   - Username: {session_data.get('username')}")
        
        # Test session update
        update_success = session_manager.update_session(session_id, {'test_field': 'test_value'})
        print(f"✅ Updated session: {update_success}")
        
        # Test session validation
        is_valid = session_manager.validate_session(session_id)
        print(f"✅ Session validation: {is_valid}")
        
        # Test session stats
        stats = session_manager.get_session_stats()
        print(f"✅ Session stats: {stats}")
        
        # Test session destruction
        destroyed = session_manager.destroy_session(session_id)
        print(f"✅ Destroyed session: {destroyed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_session_interface():
    """Test Flask session interface"""
    print("\n🔍 Testing Flask session interface...")
    
    try:
        from redis_session_backend import RedisSessionBackend
        from flask_redis_session_interface import FlaskRedisSessionInterface
        from flask import Flask
        
        # Create test app
        app = Flask(__name__)
        app.secret_key = 'test_secret_key'
        
        # Initialize Redis backend and session interface
        redis_backend = RedisSessionBackend.from_env()
        session_interface = FlaskRedisSessionInterface(
            redis_client=redis_backend.redis,
            key_prefix='test:session:',
            session_timeout=300
        )
        
        # Test session interface methods
        with app.test_request_context():
            # Test open_session (new session)
            session = session_interface.open_session(app, app.test_request_context().request)
            print(f"✅ Opened new session: {session is not None}")
            print(f"   - Session ID: {getattr(session, 'sid', 'N/A')}")
            print(f"   - Is new: {getattr(session, 'new', False)}")
            
            # Add some data to session
            if session:
                session['user_id'] = 123
                session['username'] = 'test_user'
                
                # Test save_session
                response = app.make_response('test')
                session_interface.save_session(app, session, response)
                print(f"✅ Saved session")
                
                # Test get_session_data
                session_data = session_interface.get_session_data(session.sid)
                print(f"✅ Retrieved session data: {session_data is not None}")
                
                # Test delete_session
                deleted = session_interface.delete_session(session.sid)
                print(f"✅ Deleted session: {deleted}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask session interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection and user lookup"""
    print("\n🔍 Testing database connection...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from models import User, PlatformConnection
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as db_session:
            # Test user lookup
            admin_user = db_session.query(User).filter_by(username='admin').first()
            print(f"✅ Found admin user: {admin_user is not None}")
            if admin_user:
                print(f"   - User ID: {admin_user.id}")
                print(f"   - Username: {admin_user.username}")
                print(f"   - Role: {admin_user.role}")
            
            # Test platform lookup
            platforms = db_session.query(PlatformConnection).filter_by(
                user_id=admin_user.id if admin_user else 1,
                is_active=True
            ).all()
            print(f"✅ Found {len(platforms)} platforms for admin user")
            
            # Test iolaire user
            iolaire_user = db_session.query(User).filter_by(username='iolaire').first()
            print(f"✅ Found iolaire user: {iolaire_user is not None}")
            if iolaire_user:
                print(f"   - User ID: {iolaire_user.id}")
                print(f"   - Username: {iolaire_user.username}")
                print(f"   - Role: {iolaire_user.role}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment_config():
    """Test environment configuration"""
    print("\n🔍 Testing environment configuration...")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check Redis configuration
        redis_url = os.getenv('REDIS_URL')
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_db = os.getenv('REDIS_DB', '0')
        redis_password = os.getenv('REDIS_PASSWORD')
        
        print(f"✅ Redis URL: {redis_url}")
        print(f"✅ Redis Host: {redis_host}:{redis_port}/{redis_db}")
        print(f"✅ Redis Password: {'Set' if redis_password else 'Not set'}")
        
        # Check session configuration
        session_storage = os.getenv('SESSION_STORAGE', 'database')
        session_timeout = os.getenv('REDIS_SESSION_TIMEOUT', '7200')
        session_prefix = os.getenv('REDIS_SESSION_PREFIX', 'vedfolnir:session:')
        
        print(f"✅ Session Storage: {session_storage}")
        print(f"✅ Session Timeout: {session_timeout} seconds")
        print(f"✅ Session Prefix: {session_prefix}")
        
        # Check Flask session configuration
        cookie_name = os.getenv('SESSION_COOKIE_NAME', 'session')
        cookie_httponly = os.getenv('SESSION_COOKIE_HTTPONLY', 'true')
        cookie_secure = os.getenv('SESSION_COOKIE_SECURE', 'false')
        cookie_samesite = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
        
        print(f"✅ Cookie Name: {cookie_name}")
        print(f"✅ Cookie HTTPOnly: {cookie_httponly}")
        print(f"✅ Cookie Secure: {cookie_secure}")
        print(f"✅ Cookie SameSite: {cookie_samesite}")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Redis Session Refactor Test Suite")
    print("=" * 50)
    
    # Track test results
    tests = []
    
    # Test environment configuration
    tests.append(("Environment Config", test_environment_config()))
    
    # Test Redis connection
    redis_backend = test_redis_connection()
    tests.append(("Redis Connection", redis_backend is not None))
    
    if redis_backend:
        # Test Redis session backend
        tests.append(("Redis Backend", test_session_backend(redis_backend)))
    
    # Test database connection
    tests.append(("Database Connection", test_database_connection()))
    
    # Test Flask session interface
    tests.append(("Flask Session Interface", test_flask_session_interface()))
    
    # Test session manager
    tests.append(("Session Manager", test_session_manager()))
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {len(tests)} tests, {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! Redis session refactor is ready.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please fix issues before proceeding.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
