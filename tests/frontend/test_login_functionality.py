#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test login functionality to identify issues after session management changes
"""

import sys
import traceback
from datetime import datetime, timezone

def test_basic_imports():
    """Test that all required modules can be imported"""
    print("Testing basic imports...")
    try:
        from web_app import app
        from models import User, PlatformConnection, UserSession
        from session_manager import SessionManager
        from database import DatabaseManager
        from config import Config
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection and table existence"""
    print("Testing database connection...")
    try:
        from config import Config
        from database import DatabaseManager
        from models import User, PlatformConnection, UserSession
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as db_session:
            # Test basic query
            user_count = db_session.query(User).count()
            platform_count = db_session.query(PlatformConnection).count()
            session_count = db_session.query(UserSession).count()
            
            print(f"✅ Database connection successful")
            print(f"   Users: {user_count}")
            print(f"   Platforms: {platform_count}")
            print(f"   Sessions: {session_count}")
            return True
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        traceback.print_exc()
        return False

def create_test_user():
    """Create a test user for authentication testing"""
    print("Creating test user...")
    try:
        from config import Config
        from database import DatabaseManager
        from models import User, UserRole, PlatformConnection
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as db_session:
            # Check if test user already exists
            existing_user = db_session.query(User).filter_by(username='test_user').first()
            if existing_user:
                print("✅ Test user already exists")
                return existing_user.id
            
            # Create test user
            test_user = User(
                username='test_user',
                email='test@test.com',
                role=UserRole.ADMIN,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            test_user.set_password('test123')
            
            db_session.add(test_user)
            db_session.flush()  # Get the user ID
            
            # Create a test platform connection for the user
            test_platform = PlatformConnection(
                user_id=test_user.id,
                name='Test Platform',
                platform_type='pixelfed',
                instance_url='https://test.example.com',
                username='test_user',
                _access_token='test_token',
                is_active=True,
                is_default=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db_session.add(test_platform)
            db_session.commit()
            
            print(f"✅ Created test user: {test_user.username} (ID: {test_user.id})")
            print(f"✅ Created test platform: {test_platform.name} (ID: {test_platform.id})")
            return test_user.id
            
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        traceback.print_exc()
        return None

def cleanup_test_user(user_id):
    """Remove the test user after testing"""
    if not user_id:
        return
        
    print("Cleaning up test user...")
    try:
        from config import Config
        from database import DatabaseManager
        from models import User, UserSession, PlatformConnection
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as db_session:
            # Clean up any sessions for this user first
            sessions = db_session.query(UserSession).filter_by(user_id=user_id).all()
            for session in sessions:
                db_session.delete(session)
            
            # Clean up any platform connections for this user
            platforms = db_session.query(PlatformConnection).filter_by(user_id=user_id).all()
            for platform in platforms:
                db_session.delete(platform)
            
            # Remove the test user
            test_user = db_session.query(User).get(user_id)
            if test_user:
                db_session.delete(test_user)
                db_session.commit()
                print(f"✅ Cleaned up test user and associated data (ID: {user_id})")
            
    except Exception as e:
        print(f"❌ Error cleaning up test user: {e}")
        traceback.print_exc()

def test_user_authentication():
    """Test user authentication functionality"""
    print("Testing user authentication...")
    test_user_id = None
    try:
        from config import Config
        from database import DatabaseManager
        from models import User
        
        # Create test user
        test_user_id = create_test_user()
        if not test_user_id:
            return False
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as db_session:
            # Get the test user
            user = db_session.query(User).get(test_user_id)
            if not user:
                print("❌ Test user not found")
                return False
            
            print(f"✅ Found test user: {user.username}")
            print(f"   Active: {user.is_active}")
            print(f"   Role: {user.role}")
            
            # Test password checking with known password
            if user.check_password('test123'):
                print("✅ Password authentication works")
                return True
            else:
                print("❌ Password authentication failed")
                return False
            
    except Exception as e:
        print(f"❌ User authentication error: {e}")
        traceback.print_exc()
        return False
    finally:
        # Always clean up the test user
        cleanup_test_user(test_user_id)

def test_session_creation():
    """Test session creation functionality"""
    print("Testing session creation...")
    test_user_id = None
    try:
        from web_app import app
        from session_manager import SessionManager
        from database import DatabaseManager
        from config import Config
        from models import User, PlatformConnection
        
        # Create test user
        test_user_id = create_test_user()
        if not test_user_id:
            return False
        
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = SessionManager(db_manager)
        
        with app.app_context():
            with db_manager.get_session() as db_session:
                user = db_session.query(User).get(test_user_id)
                # Get the platform that belongs to the test user
                platform = db_session.query(PlatformConnection).filter_by(user_id=test_user_id).first()
                
                if not user:
                    print("❌ Test user not found for session creation test")
                    return False
                
                if not platform:
                    print("❌ No platform found for test user")
                    return False
                
                print(f"Testing session creation for user {user.username} with platform {platform.name}")
                
                # Test session creation
                session_id = session_manager.create_user_session(user.id, platform.id)
                print(f"✅ Session created: {session_id}")
                
                # Test session context retrieval
                context = session_manager.get_session_context(session_id)
                if context:
                    print(f"✅ Session context retrieved")
                    print(f"   User: {context.get('user_username')}")
                    print(f"   Platform: {context.get('platform_name')}")
                    return True
                else:
                    print("❌ Session context retrieval failed")
                    return False
                    
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        traceback.print_exc()
        return False
    finally:
        # Clean up the test user
        cleanup_test_user(test_user_id)

def test_login_flow():
    """Test the complete login flow including dashboard access"""
    print("Testing login flow...")
    test_user_id = None
    try:
        from web_app import app
        from database import DatabaseManager
        from config import Config
        from models import User, PlatformConnection
        
        # Create test user
        test_user_id = create_test_user()
        if not test_user_id:
            return False
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with app.test_client() as client:
            with app.app_context():
                # Get test user credentials
                with db_manager.get_session() as db_session:
                    user = db_session.query(User).get(test_user_id)
                    if not user:
                        print("❌ Test user not found for login test")
                        return False
                    
                    # Test login page access
                    response = client.get('/login')
                    if response.status_code != 200:
                        print(f"❌ Login page not accessible: {response.status_code}")
                        return False
                    
                    print("✅ Login page accessible")
                    
                    # Disable CSRF for testing
                    app.config['WTF_CSRF_ENABLED'] = False
                    
                    # Test login with known password
                    response = client.post('/login', data={
                        'username': user.username,
                        'password': 'test123'
                    }, follow_redirects=False)
                    
                    if response.status_code == 302:
                        print(f"✅ Login successful - redirected")
                        location = response.headers.get('Location', '')
                        print(f"   Redirect location: {location}")
                        
                        # Now test if we can access the dashboard
                        dashboard_response = client.get('/', follow_redirects=False)
                        print(f"   Dashboard access status: {dashboard_response.status_code}")
                        
                        if dashboard_response.status_code == 200:
                            print("✅ Dashboard accessible after login")
                            
                            # Check if the dashboard contains expected content
                            dashboard_content = dashboard_response.get_data(as_text=True)
                            if 'Dashboard' in dashboard_content or 'Vedfolnir' in dashboard_content:
                                print("✅ Dashboard content loaded correctly")
                                return True
                            else:
                                print("❌ Dashboard content doesn't look right")
                                print(f"   Content preview: {dashboard_content[:200]}...")
                                return False
                                
                        elif dashboard_response.status_code == 302:
                            redirect_location = dashboard_response.headers.get('Location', '')
                            print(f"❌ Dashboard redirected to: {redirect_location}")
                            
                            if '/login' in redirect_location:
                                print("❌ Dashboard redirected back to login - authentication not persisting")
                                
                                # Let's check what's in the session
                                print("   Debugging session state...")
                                
                                # Try to access a simple authenticated endpoint
                                profile_response = client.get('/profile', follow_redirects=False)
                                print(f"   Profile access status: {profile_response.status_code}")
                                
                                return False
                            else:
                                print(f"❌ Dashboard redirected to unexpected location: {redirect_location}")
                                return False
                        else:
                            print(f"❌ Dashboard returned unexpected status: {dashboard_response.status_code}")
                            return False
                        
                    else:
                        print(f"❌ Login attempt failed with status: {response.status_code}")
                        print(f"   Response data: {response.get_data(as_text=True)[:200]}...")
                        return False
                    
    except Exception as e:
        print(f"❌ Login flow error: {e}")
        traceback.print_exc()
        return False
    finally:
        # Clean up the test user
        cleanup_test_user(test_user_id)

def test_session_persistence():
    """Test session persistence after login"""
    print("Testing session persistence...")
    test_user_id = None
    try:
        from web_app import app
        from database import DatabaseManager
        from config import Config
        from models import User, UserSession
        from flask import session
        
        # Create test user
        test_user_id = create_test_user()
        if not test_user_id:
            return False
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with app.test_client() as client:
            with app.app_context():
                # Disable CSRF for testing
                app.config['WTF_CSRF_ENABLED'] = False
                
                with db_manager.get_session() as db_session:
                    user = db_session.query(User).get(test_user_id)
                    
                    # Perform login
                    response = client.post('/login', data={
                        'username': user.username,
                        'password': 'test123'
                    }, follow_redirects=False)
                    
                    if response.status_code == 302:
                        print("✅ Login successful")
                        
                        # Check if session was created in database
                        sessions = db_session.query(UserSession).filter_by(user_id=test_user_id).all()
                        print(f"   Sessions in database for user: {len(sessions)}")
                        
                        if sessions:
                            latest_session = sessions[-1]
                            print(f"   Latest session ID: {latest_session.session_id}")
                            print(f"   Session platform: {latest_session.active_platform_id}")
                            
                            # Check if Flask session has the session ID
                            with client.session_transaction() as sess:
                                flask_session_id = sess.get('_id')
                                print(f"   Flask session _id: {flask_session_id}")
                                print(f"   Flask session keys: {list(sess.keys())}")
                                
                                if flask_session_id:
                                    if flask_session_id == latest_session.session_id:
                                        print("✅ Flask session matches database session")
                                    else:
                                        print("❌ Flask session ID doesn't match database session")
                                        return False
                                else:
                                    print("❌ No session ID in Flask session")
                                    return False
                        else:
                            print("❌ No session created in database")
                            return False
                        
                        # Now test if authentication persists
                        dashboard_response = client.get('/', follow_redirects=False)
                        if dashboard_response.status_code == 200:
                            print("✅ Authentication persists - dashboard accessible")
                            return True
                        else:
                            print(f"❌ Authentication doesn't persist - dashboard status: {dashboard_response.status_code}")
                            return False
                    else:
                        print(f"❌ Login failed with status: {response.status_code}")
                        return False
                    
    except Exception as e:
        print(f"❌ Session persistence test error: {e}")
        traceback.print_exc()
        return False
    finally:
        # Clean up the test user
        cleanup_test_user(test_user_id)

def main():
    """Run all tests"""
    print("🧪 Testing Login Functionality After Session Management Changes")
    print("=" * 60)
    
    tests = [
        test_basic_imports,
        test_database_connection,
        test_user_authentication,
        test_session_creation,
        test_login_flow,
        test_session_persistence
    ]
    
    results = []
    for test in tests:
        print()
        result = test()
        results.append(result)
        if not result:
            print(f"❌ Test failed: {test.__name__}")
            break
        else:
            print(f"✅ Test passed: {test.__name__}")
    
    print()
    print("=" * 60)
    if all(results):
        print("🎉 All tests passed! Login functionality is working.")
    else:
        print("💥 Some tests failed. Login functionality has issues.")
        print("\nFailed tests:")
        for i, (test, result) in enumerate(zip(tests, results)):
            if not result:
                print(f"  - {test.__name__}")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)