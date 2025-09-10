#!/usr/bin/env python3
"""
Test Redis session management functionality
"""

import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_redis_session_creation():
    """Test Redis session creation and management"""
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from session_factory import create_session_manager
        from models import User, UserRole
        
        print("Testing Redis session creation...")
        
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = create_session_manager(db_manager)
        
        print(f"✓ Session manager type: {type(session_manager).__name__}")
        
        # Get the admin user (should exist)
        with db_manager.get_session() as db_session:
            admin_user = db_session.query(User).filter_by(username='admin').first()
            if not admin_user:
                print("✗ Admin user not found")
                return False
            
            user_id = admin_user.id
            print(f"✓ Found admin user with ID: {user_id}")
        
        # Test session creation
        print("Creating Redis session...")
        session_id = session_manager.create_session(user_id)
        print(f"✓ Session created successfully: {session_id[:8]}...")
        
        # Test session retrieval
        print("Retrieving session context...")
        context = session_manager.get_session_context(session_id)
        if context:
            print(f"✓ Session context retrieved: user_id={context.get('user_id')}")
            print(f"  Platform ID: {context.get('platform_connection_id')}")
            print(f"  Created at: {context.get('created_at')}")
            print(f"  Expires at: {context.get('expires_at')}")
        else:
            print("✗ Failed to retrieve session context")
            return False
        
        # Test session validation
        print("Validating session...")
        is_valid = session_manager.validate_session(session_id)
        if is_valid:
            print("✓ Session validation successful")
        else:
            print("✗ Session validation failed")
            return False
        
        # Test session activity update
        print("Updating session activity...")
        updated = session_manager.update_session_activity(session_id)
        if updated:
            print("✓ Session activity updated")
        else:
            print("✗ Session activity update failed")
            return False
        
        # Test session statistics
        if hasattr(session_manager, 'get_session_stats'):
            print("Getting session statistics...")
            stats = session_manager.get_session_stats()
            print(f"✓ Session stats: {stats}")
        
        # Test session cleanup
        print("Cleaning up session...")
        destroyed = session_manager.destroy_session(session_id)
        if destroyed:
            print("✓ Session destroyed successfully")
        else:
            print("✗ Session destruction failed")
            return False
        
        # Verify session is gone
        print("Verifying session cleanup...")
        context_after = session_manager.get_session_context(session_id)
        if context_after is None:
            print("✓ Session properly cleaned up")
        else:
            print("✗ Session still exists after cleanup")
            return False
        
        print("✅ All Redis session tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Redis session test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_sessions():
    """Test multiple concurrent Redis sessions"""
    try:
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from session_factory import create_session_manager
        from models import User
        
        print("\nTesting multiple concurrent sessions...")
        
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = create_session_manager(db_manager)
        
        # Get the admin user
        with db_manager.get_session() as db_session:
            admin_user = db_session.query(User).filter_by(username='admin').first()
            user_id = admin_user.id
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session_id = session_manager.create_session(user_id)
            sessions.append(session_id)
            print(f"✓ Created session {i+1}: {session_id[:8]}...")
        
        # Verify all sessions exist
        for i, session_id in enumerate(sessions):
            context = session_manager.get_session_context(session_id)
            if context:
                print(f"✓ Session {i+1} context retrieved")
            else:
                print(f"✗ Session {i+1} context not found")
                return False
        
        # Clean up all sessions
        for i, session_id in enumerate(sessions):
            destroyed = session_manager.destroy_session(session_id)
            if destroyed:
                print(f"✓ Session {i+1} destroyed")
            else:
                print(f"✗ Session {i+1} destruction failed")
                return False
        
        print("✅ Multiple session tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Multiple session test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔗 Redis Session Management Test")
    print("=" * 50)
    
    # Test single session
    single_ok = test_redis_session_creation()
    
    # Test multiple sessions
    multiple_ok = test_multiple_sessions()
    
    success = single_ok and multiple_ok
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All Redis session tests passed!")
        print("Redis session management is working correctly.")
    else:
        print("❌ Some Redis session tests failed.")
    
    sys.exit(0 if success else 1)