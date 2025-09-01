#!/usr/bin/env python3
"""
Debug Platform Switch Issues

This script helps debug platform switching issues by testing the Redis session
management and platform retrieval functionality.
"""

import os
import sys
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from redis_platform_manager import get_redis_platform_manager
from session_factory import create_session_manager

def debug_platform_switch():
    """Debug platform switching functionality"""
    
    print("Debugging Platform Switch Issues...")
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Create session manager (should be Redis-based)
    session_manager = create_session_manager(db_manager)
    print(f"Session manager type: {type(session_manager).__name__}")
    
    if not hasattr(session_manager, 'redis_client'):
        print("ERROR: Session manager doesn't have Redis client!")
        return False
    
    # Get Redis platform manager
    encryption_key = os.getenv('PLATFORM_ENCRYPTION_KEY', 'default-key-change-in-production')
    redis_platform_manager = get_redis_platform_manager(
        session_manager.redis_client,
        db_manager,
        encryption_key
    )
    
    # Test Redis connection
    try:
        session_manager.redis_client.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False
    
    # Test with a real user (assuming user ID 1 exists)
    test_user_id = 1
    
    try:
        # Check if user exists in database
        session = db_manager.get_session()
        try:
            from models import User, PlatformConnection
            user = session.query(User).filter_by(id=test_user_id).first()
            if not user:
                print(f"✗ User {test_user_id} not found in database")
                return False
            
            print(f"✓ User found: {user.username}")
            
            # Get user's platforms
            platforms = session.query(PlatformConnection).filter_by(
                user_id=test_user_id,
                is_active=True
            ).all()
            
            print(f"✓ User has {len(platforms)} active platforms")
            
            if not platforms:
                print("✗ No platforms found for user")
                return False
            
            # Test platform retrieval via Redis
            for platform in platforms:
                print(f"\nTesting platform {platform.id}: {platform.name}")
                
                # Test Redis platform manager
                platform_data = redis_platform_manager.get_platform_by_id(platform.id, test_user_id)
                if platform_data:
                    print(f"  ✓ Retrieved from Redis: {platform_data['name']}")
                    print(f"    Active: {platform_data.get('is_active', 'Unknown')}")
                    print(f"    Type: {platform_data.get('platform_type', 'Unknown')}")
                else:
                    print(f"  ✗ Failed to retrieve from Redis")
                
                # Test session creation and platform update
                session_id = session_manager.create_session(test_user_id, platform.id)
                if session_id:
                    print(f"  ✓ Created session: {session_id[:8]}...")
                    
                    # Test platform context update
                    success = session_manager.update_platform_context(session_id, platform.id)
                    if success:
                        print(f"  ✓ Updated platform context successfully")
                        
                        # Get session context
                        context = session_manager.get_session_context(session_id)
                        if context:
                            print(f"  ✓ Session context retrieved")
                            print(f"    User ID: {context.get('user_id')}")
                            print(f"    Platform ID: {context.get('active_platform_id')}")
                        else:
                            print(f"  ✗ Failed to get session context")
                    else:
                        print(f"  ✗ Failed to update platform context")
                    
                    # Clean up session
                    session_manager.destroy_session(session_id)
                    print(f"  ✓ Cleaned up session")
                else:
                    print(f"  ✗ Failed to create session")
                
                break  # Test only first platform
            
            return True
            
        finally:
            db_manager.close_session(session)
            
    except Exception as e:
        print(f"✗ Error during platform testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_platform_switch()
    if success:
        print("\n✓ Platform switch debugging completed!")
        sys.exit(0)
    else:
        print("\n✗ Platform switch debugging failed!")
        sys.exit(1)
