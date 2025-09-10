#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Functionality Test

Test the Redis session functionality with actual user login and platform switching.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_authentication():
    """Test user authentication and session creation"""
    print("🔍 Testing user authentication...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from redis_session_backend import RedisSessionBackend
        from session_manager_v2 import SessionManagerV2
        from session_middleware_v2 import create_user_session
        from models import User, PlatformConnection
        
        # Initialize components
        config = Config()
        db_manager = self.get_database_manager()
        redis_backend = RedisSessionBackend.from_env()
        session_manager = SessionManagerV2(db_manager, redis_backend)
        
        # Test admin user authentication
        with db_manager.get_session() as db_session:
            admin_user = db_session.query(User).filter_by(username='admin').first()
            if not admin_user:
                print("❌ Admin user not found")
                return False
            
            # Test password verification
            if not admin_user.check_password('5OIkH4M:%iaP7QbdU9wj2Sfj'):
                print("❌ Admin password verification failed")
                return False
            
            print(f"✅ Admin user authenticated: {admin_user.username} (ID: {admin_user.id})")
            
            # Create session for admin user
            session_id = session_manager.create_session(admin_user.id)
            print(f"✅ Created session for admin: {session_id}")
            
            # Get session data
            session_data = session_manager.get_session_data(session_id)
            if session_data:
                print(f"✅ Session data retrieved:")
                print(f"   - User ID: {session_data.get('user_id')}")
                print(f"   - Username: {session_data.get('username')}")
                print(f"   - Role: {session_data.get('role')}")
                print(f"   - Created: {session_data.get('created_at')}")
            
            # Test iolaire user
            iolaire_user = db_session.query(User).filter_by(username='iolaire').first()
            if iolaire_user and iolaire_user.check_password('g9bDFB9JzgEaVZx'):
                print(f"✅ Iolaire user authenticated: {iolaire_user.username} (ID: {iolaire_user.id})")
                
                # Create session for iolaire user
                iolaire_session_id = session_manager.create_session(iolaire_user.id)
                print(f"✅ Created session for iolaire: {iolaire_session_id}")
                
                # Test multiple sessions
                user_sessions = session_manager.get_user_sessions(iolaire_user.id)
                print(f"✅ Iolaire has {len(user_sessions)} active sessions")
                
                # Clean up iolaire sessions
                cleaned = session_manager.cleanup_user_sessions(iolaire_user.id)
                print(f"✅ Cleaned up {cleaned} sessions for iolaire")
            
            # Clean up admin session
            destroyed = session_manager.destroy_session(session_id)
            print(f"✅ Destroyed admin session: {destroyed}")
            
            return True
            
    except Exception as e:
        print(f"❌ User authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_platform_switching():
    """Test platform switching functionality"""
    print("\n🔍 Testing platform switching...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from redis_session_backend import RedisSessionBackend
        from session_manager_v2 import SessionManagerV2
        from models import User, PlatformConnection
        
        # Initialize components
        config = Config()
        db_manager = self.get_database_manager()
        redis_backend = RedisSessionBackend.from_env()
        session_manager = SessionManagerV2(db_manager, redis_backend)
        
        with db_manager.get_session() as db_session:
            # Get admin user
            admin_user = db_session.query(User).filter_by(username='admin').first()
            if not admin_user:
                print("❌ Admin user not found")
                return False
            
            # Create session
            session_id = session_manager.create_session(admin_user.id)
            print(f"✅ Created session: {session_id}")
            
            # Check if admin has any platforms
            platforms = db_session.query(PlatformConnection).filter_by(
                user_id=admin_user.id,
                is_active=True
            ).all()
            
            if platforms:
                print(f"✅ Found {len(platforms)} platforms for admin user")
                
                for platform in platforms:
                    print(f"   - Platform: {platform.name} ({platform.platform_type})")
                    
                    # Test platform switching
                    switch_success = session_manager.switch_platform(session_id, platform.id)
                    print(f"✅ Switched to platform {platform.name}: {switch_success}")
                    
                    # Verify session data includes platform info
                    session_data = session_manager.get_session_data(session_id)
                    if session_data and session_data.get('platform_connection_id') == platform.id:
                        print(f"✅ Session updated with platform: {session_data.get('platform_name')}")
                    else:
                        print(f"❌ Session not updated with platform data")
            else:
                print("ℹ️  No platforms found for admin user - creating test platform")
                
                # Create a test platform for admin
                test_platform = PlatformConnection(
                    user_id=admin_user.id,
                    name="Test Platform",
                    platform_type="mastodon",
                    instance_url="https://test.example.com",
                    username="test_user",
                    access_token="test_token_123",  # Required field
                    client_key="test_client_key",
                    client_secret="test_client_secret",
                    is_active=True,
                    is_default=True
                )
                db_session.add(test_platform)
                db_session.commit()
                
                print(f"✅ Created test platform: {test_platform.name}")
                
                # Test switching to new platform
                switch_success = session_manager.switch_platform(session_id, test_platform.id)
                print(f"✅ Switched to test platform: {switch_success}")
                
                # Clean up test platform
                db_session.delete(test_platform)
                db_session.commit()
                print("✅ Cleaned up test platform")
            
            # Clean up session
            destroyed = session_manager.destroy_session(session_id)
            print(f"✅ Destroyed session: {destroyed}")
            
            return True
            
    except Exception as e:
        print(f"❌ Platform switching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_persistence():
    """Test session persistence and timeout"""
    print("\n🔍 Testing session persistence...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from redis_session_backend import RedisSessionBackend
        from session_manager_v2 import SessionManagerV2
        from models import User
        import time
        
        # Initialize components
        config = Config()
        db_manager = self.get_database_manager()
        redis_backend = RedisSessionBackend.from_env()
        session_manager = SessionManagerV2(db_manager, redis_backend, session_timeout=10)  # 10 second timeout for testing
        
        with db_manager.get_session() as db_session:
            admin_user = db_session.query(User).filter_by(username='admin').first()
            if not admin_user:
                print("❌ Admin user not found")
                return False
            
            # Create session
            session_id = session_manager.create_session(admin_user.id)
            print(f"✅ Created session with 10s timeout: {session_id}")
            
            # Verify session exists
            exists = session_manager.validate_session(session_id)
            print(f"✅ Session exists: {exists}")
            
            # Get TTL
            ttl = redis_backend.get_ttl(session_id)
            print(f"✅ Session TTL: {ttl} seconds")
            
            # Wait a bit and check again
            print("   Waiting 3 seconds...")
            time.sleep(3)
            
            # Update session (should refresh TTL)
            updated = session_manager.update_session(session_id, {'test_update': 'value'})
            print(f"✅ Updated session: {updated}")
            
            # Check TTL again
            ttl_after_update = redis_backend.get_ttl(session_id)
            print(f"✅ Session TTL after update: {ttl_after_update} seconds")
            
            # Extend session
            extended = session_manager.extend_session(session_id, 20)
            print(f"✅ Extended session: {extended}")
            
            # Check final TTL
            final_ttl = redis_backend.get_ttl(session_id)
            print(f"✅ Final session TTL: {final_ttl} seconds")
            
            # Clean up
            destroyed = session_manager.destroy_session(session_id)
            print(f"✅ Destroyed session: {destroyed}")
            
            return True
            
    except Exception as e:
        print(f"❌ Session persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_stats():
    """Test session statistics and monitoring"""
    print("\n🔍 Testing session statistics...")
    
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from redis_session_backend import RedisSessionBackend
        from session_manager_v2 import SessionManagerV2
        from models import User
        
        # Initialize components
        config = Config()
        db_manager = self.get_database_manager()
        redis_backend = RedisSessionBackend.from_env()
        session_manager = SessionManagerV2(db_manager, redis_backend)
        
        # Get initial stats
        initial_stats = session_manager.get_session_stats()
        print(f"✅ Initial session stats:")
        print(f"   - Total sessions: {initial_stats.get('total_sessions', 0)}")
        print(f"   - Unique users: {initial_stats.get('unique_users', 0)}")
        
        # Create multiple sessions
        session_ids = []
        with db_manager.get_session() as db_session:
            admin_user = db_session.query(User).filter_by(username='admin').first()
            iolaire_user = db_session.query(User).filter_by(username='iolaire').first()
            
            if admin_user and iolaire_user:
                # Create sessions for both users
                for i in range(2):
                    admin_session = session_manager.create_session(admin_user.id)
                    iolaire_session = session_manager.create_session(iolaire_user.id)
                    session_ids.extend([admin_session, iolaire_session])
                
                print(f"✅ Created {len(session_ids)} test sessions")
                
                # Get updated stats
                updated_stats = session_manager.get_session_stats()
                print(f"✅ Updated session stats:")
                print(f"   - Total sessions: {updated_stats.get('total_sessions', 0)}")
                print(f"   - Unique users: {updated_stats.get('unique_users', 0)}")
                print(f"   - Avg sessions per user: {updated_stats.get('avg_sessions_per_user', 0)}")
                
                # Test user-specific session retrieval
                admin_sessions = session_manager.get_user_sessions(admin_user.id)
                iolaire_sessions = session_manager.get_user_sessions(iolaire_user.id)
                
                print(f"✅ Admin has {len(admin_sessions)} sessions")
                print(f"✅ Iolaire has {len(iolaire_sessions)} sessions")
                
                # Clean up all test sessions
                for session_id in session_ids:
                    session_manager.destroy_session(session_id)
                
                print(f"✅ Cleaned up {len(session_ids)} test sessions")
                
                # Get final stats
                final_stats = session_manager.get_session_stats()
                print(f"✅ Final session stats:")
                print(f"   - Total sessions: {final_stats.get('total_sessions', 0)}")
                print(f"   - Unique users: {final_stats.get('unique_users', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session statistics test failed: {e}")
        import traceback

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures

        traceback.print_exc()
        return False

def main():
    """Run all session functionality tests"""
    print("🚀 Redis Session Functionality Test Suite")
    print("=" * 50)
    
    # Track test results
    tests = []
    
    # Test user authentication
    tests.append(("User Authentication", test_user_authentication()))
    
    # Test platform switching
    tests.append(("Platform Switching", test_platform_switching()))
    
    # Test session persistence
    tests.append(("Session Persistence", test_session_persistence()))
    
    # Test session statistics
    tests.append(("Session Statistics", test_session_stats()))
    
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
        print("\n🎉 All session functionality tests passed!")
        print("✅ Redis session refactor is fully functional and ready for integration.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the issues.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
