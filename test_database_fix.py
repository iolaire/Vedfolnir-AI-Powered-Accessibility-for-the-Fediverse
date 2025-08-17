#!/usr/bin/env python3
"""
Test script to verify database lock fixes
"""

import sys
import time
from config import Config
from database import DatabaseManager
from unified_session_manager import UnifiedSessionManager

def test_database_connections():
    """Test multiple database connections to ensure no locks"""
    print("Testing database connection fixes...")
    
    try:
        # Initialize configuration and database manager
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = UnifiedSessionManager(db_manager)
        
        print("✓ Database manager initialized successfully")
        
        # Test multiple session creations (this was causing the lock)
        print("Testing session creation...")
        
        # Test 1: Create a session
        with db_manager.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"✓ Database query successful - found {user_count} users")
        
        print("✓ Session closed properly")
        
        # Test 2: Multiple concurrent sessions
        print("Testing multiple sessions...")
        sessions = []
        try:
            for i in range(3):
                session = db_manager.get_session()
                sessions.append(session)
                result = session.execute(text("SELECT 1"))
                print(f"✓ Session {i+1} created and tested")
            
            print("✓ Multiple sessions created without locks")
            
        finally:
            # Clean up sessions
            for i, session in enumerate(sessions):
                db_manager.close_session(session)
                print(f"✓ Session {i+1} closed")
        
        # Test 3: Session manager operations
        print("Testing session manager...")
        try:
            # This should not cause database locks anymore
            with session_manager.get_db_session() as db_session:
                result = db_session.execute(text("SELECT COUNT(*) FROM user_sessions"))
                session_count = result.scalar()
                print(f"✓ Session manager query successful - found {session_count} user sessions")
        except Exception as e:
            print(f"✗ Session manager test failed: {e}")
            return False
        
        print("✓ All database connection tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connections()
    sys.exit(0 if success else 1)