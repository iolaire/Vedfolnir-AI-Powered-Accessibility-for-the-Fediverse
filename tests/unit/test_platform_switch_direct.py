#!/usr/bin/env python3
"""
Direct Platform Switch Test

This script tests the platform switching logic directly without going through the web interface.
"""

import os
import sys
from flask import Flask, g

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from redis_platform_manager import get_redis_platform_manager
from session_factory import create_session_manager
from models import User, PlatformConnection

def test_platform_switch_direct():
    """Test platform switching logic directly"""
    
    print("Testing Platform Switch Logic Directly...")
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Create session manager (should be Redis-based)
    session_manager = create_session_manager(db_manager)
    print(f"Session manager type: {type(session_manager).__name__}")
    
    # Get Redis platform manager
    encryption_key = os.getenv('PLATFORM_ENCRYPTION_KEY', 'default-key-change-in-production')
    redis_platform_manager = get_redis_platform_manager(
        session_manager.redis_client,
        db_manager,
        encryption_key
    )
    
    # Test with user ID 2 (iolaire) and platform ID 2
    test_user_id = 2
    test_platform_id = 2
    
    print(f"Testing with user {test_user_id} and platform {test_platform_id}")
    
    # Get user from database
    session = db_manager.get_session()
    try:
        user = session.query(User).filter_by(id=test_user_id).first()
        if not user:
            print(f"✗ User {test_user_id} not found")
            return False
        
        print(f"✓ User found: {user.username}")
        
        # Get platform from database
        platform = session.query(PlatformConnection).filter_by(
            id=test_platform_id,
            user_id=test_user_id,
            is_active=True
        ).first()
        
        if not platform:
            print(f"✗ Platform {test_platform_id} not found or not accessible to user {test_user_id}")
            return False
        
        print(f"✓ Platform found: {platform.name} (active: {platform.is_active})")
        
    finally:
        db_manager.close_session(session)
    
    # Load platforms to Redis
    platforms = redis_platform_manager.load_user_platforms_to_redis(test_user_id)
    print(f"✓ Loaded {len(platforms)} platforms to Redis")
    
    # Get platform data from Redis
    platform_data = redis_platform_manager.get_platform_by_id(test_platform_id, test_user_id)
    if not platform_data:
        print(f"✗ Platform {test_platform_id} not found in Redis for user {test_user_id}")
        return False
    
    print(f"✓ Platform data from Redis: {platform_data['name']} (active: {platform_data.get('is_active')})")
    
    # Verify platform is active
    if not platform_data.get('is_active', False):
        print(f"✗ Platform {test_platform_id} is not active")
        return False
    
    print("✓ Platform is active")
    
    # Create a user session
    session_id = session_manager.create_session(test_user_id, test_platform_id)
    if not session_id:
        print("✗ Failed to create session")
        return False
    
    print(f"✓ Created session: {session_id[:8]}...")
    
    # Test platform context update (this is what the API route does)
    success = session_manager.update_platform_context(session_id, test_platform_id)
    if not success:
        print("✗ Failed to update platform context")
        return False
    
    print("✓ Platform context updated successfully")
    
    # Get session context to verify
    context = session_manager.get_session_context(session_id)
    if not context:
        print("✗ Failed to get session context")
        return False
    
    print(f"✓ Session context retrieved:")
    print(f"  User ID: {context.get('user_id')}")
    print(f"  Platform Connection ID: {context.get('platform_connection_id')}")
    print(f"  Is Active: {context.get('is_active')}")
    
    # Clean up
    session_manager.destroy_session(session_id)
    print("✓ Session cleaned up")
    
    return True

def test_api_route_logic():
    """Test the actual API route logic"""
    
    print("\nTesting API Route Logic...")
    
    # Create a Flask app context for testing
    app = Flask(__name__)
    app.config.from_object(Config())
    
    # Initialize components
    db_manager = DatabaseManager(app.config)
    session_manager = create_session_manager(db_manager)
    
    encryption_key = os.getenv('PLATFORM_ENCRYPTION_KEY', 'default-key-change-in-production')
    redis_platform_manager = get_redis_platform_manager(
        session_manager.redis_client,
        db_manager,
        encryption_key
    )
    
    with app.app_context():
        # Simulate the API route logic
        platform_id = 2
        user_id = 2  # Simulating current_user.id
        
        print(f"Simulating API call: switch_platform({platform_id}) for user {user_id}")
        
        # Step 1: Get platform data (from the updated route)
        platform_data = redis_platform_manager.get_platform_by_id(platform_id, user_id)
        
        if not platform_data:
            print(f"✗ Platform {platform_id} not found for user {user_id}")
            print("This would return 404 in the API")
            return False
        
        print(f"✓ Platform data retrieved: {platform_data['name']}")
        
        # Step 2: Verify platform is active
        if not platform_data.get('is_active', False):
            print(f"✗ Platform {platform_id} is not active")
            print("This would return 400 in the API")
            return False
        
        print("✓ Platform is active")
        
        # Step 3: Create session and update platform context
        session_id = session_manager.create_session(user_id, platform_id)
        if not session_id:
            print("✗ Failed to create session")
            return False
        
        print(f"✓ Session created: {session_id[:8]}...")
        
        # Step 4: Update platform context (this is the critical part)
        from redis_session_middleware import update_session_platform
        
        # Simulate the g object with session info
        g.session_id = session_id
        
        success = update_session_platform(platform_id)
        if not success:
            print("✗ Failed to update session platform")
            print("This would return 500 in the API")
            return False
        
        print("✓ Session platform updated successfully")
        
        # Clean up
        session_manager.destroy_session(session_id)
        print("✓ Session cleaned up")
        
        print("✅ API route logic would succeed!")
        return True

if __name__ == "__main__":
    print("=" * 60)
    success1 = test_platform_switch_direct()
    
    print("\n" + "=" * 60)
    success2 = test_api_route_logic()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ All platform switch tests passed!")
        print("The 400 error might be due to authentication or CSRF issues, not the platform switching logic.")
    else:
        print("❌ Platform switch tests failed!")
        print("The issue is in the platform switching logic itself.")
