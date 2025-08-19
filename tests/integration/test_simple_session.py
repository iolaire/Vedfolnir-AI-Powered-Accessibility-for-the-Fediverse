#!/usr/bin/env python3
"""
Simple test to create a platform and session for testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from unified_session_manager import UnifiedSessionManager as SessionManager
from models import User, PlatformConnection

def create_test_platform():
    """Create a test platform for the admin user"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).filter_by(username='admin').first()
        if not user:
            print("No admin user found")
            return False
            
        # Create a test platform
        platform = PlatformConnection(
            user_id=user.id,
            name="Test Platform",
            platform_type="pixelfed",
            instance_url="https://pixey.org",
            username="testuser",
            is_default=True,
            is_active=True
        )
        platform.access_token = "test_token_123"
        
        db_session.add(platform)
        db_session.commit()
        
        print(f"Created test platform with ID: {platform.id}")
        return platform.id
        
    except Exception as e:
        db_session.rollback()
        print(f"Error creating platform: {e}")
        return False
    finally:
        db_session.close()

def test_session_with_platform():
    """Test session creation with the platform"""
    config = Config()
    db_manager = DatabaseManager(config)
    session_manager = UnifiedSessionManager(db_manager)
    
    # First create a platform
    platform_id = create_test_platform()
    if not platform_id:
        return False
    
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).filter_by(username='admin').first()
        
        print(f"Testing session creation with user: {user.username}, platform: {platform_id}")
        
        # Create a session
        session_id = session_manager.create_session(user.id, platform_id)
        print(f"Created session: {session_id}")
        
        # Try to retrieve it
        context = session_manager.get_session_context(session_id)
        if context:
            print(f"✓ Session retrieved successfully")
            print(f"  Platform ID: {context['platform_connection_id']}")
            print(f"  User ID: {context['user_id']}")
            return True
        else:
            print("✗ Failed to retrieve session")
            return False
                
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_session_with_platform()
    sys.exit(0 if success else 1)