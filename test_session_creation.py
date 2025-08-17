#!/usr/bin/env python3
"""
Test session creation directly to verify database lock fixes
"""

import sys
from config import Config
from database import DatabaseManager
from unified_session_manager import UnifiedSessionManager
from models import User, UserRole

def test_session_creation():
    """Test direct session creation to verify no database locks"""
    print("Testing session creation directly...")
    
    try:
        # Initialize configuration and managers
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = UnifiedSessionManager(db_manager)
        
        print("✓ Managers initialized successfully")
        
        # Get the admin user (should exist)
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(username='admin').first()
            if not admin_user:
                print("✗ Admin user not found")
                return False
            
            user_id = admin_user.id
            print(f"✓ Found admin user with ID: {user_id}")
        
        # Test session creation (this was causing the database lock)
        print("Creating user session...")
        try:
            session_id = session_manager.create_session(user_id)
            print(f"✓ Session created successfully: {session_id[:8]}...")
            
            # Test session retrieval
            print("Retrieving session context...")
            context = session_manager.get_session_context(session_id)
            if context:
                print(f"✓ Session context retrieved: user_id={context.get('user_id')}")
            else:
                print("✗ Failed to retrieve session context")
                return False
            
            # Test session cleanup
            print("Cleaning up session...")
            success = session_manager.destroy_session(session_id)
            if success:
                print("✓ Session cleaned up successfully")
            else:
                print("? Session cleanup returned False (may not exist)")
            
            return True
            
        except Exception as e:
            print(f"✗ Session creation failed: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Test setup failed: {e}")
        return False

if __name__ == "__main__":
    success = test_session_creation()
    sys.exit(0 if success else 1)