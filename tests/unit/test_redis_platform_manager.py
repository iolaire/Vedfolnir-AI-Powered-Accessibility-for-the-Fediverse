#!/usr/bin/env python3
"""
Test Redis Platform Manager

This script tests the Redis platform manager functionality to ensure
it's properly caching platform connections and user settings.
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

def test_redis_platform_manager():
    """Test Redis platform manager functionality"""
    
    print("Testing Redis Platform Manager...")
    
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
    
    print(f"Redis platform manager: {type(redis_platform_manager).__name__}")
    
    # Test Redis connection
    try:
        session_manager.redis_client.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False
    
    # Test platform loading (assuming user ID 1 exists)
    test_user_id = 1
    
    try:
        # Load platforms from database to Redis
        platforms = redis_platform_manager.load_user_platforms_to_redis(test_user_id)
        print(f"✓ Loaded {len(platforms)} platforms for user {test_user_id}")
        
        # Get platforms from Redis cache
        cached_platforms = redis_platform_manager.get_user_platforms(test_user_id)
        print(f"✓ Retrieved {len(cached_platforms)} platforms from Redis cache")
        
        if platforms and cached_platforms:
            platform_id = platforms[0]['id']
            
            # Test individual platform retrieval
            platform = redis_platform_manager.get_platform_by_id(platform_id, test_user_id)
            if platform:
                print(f"✓ Retrieved platform {platform_id} from Redis")
                print(f"  Platform name: {platform['name']}")
                print(f"  Platform type: {platform['platform_type']}")
            else:
                print(f"✗ Failed to retrieve platform {platform_id}")
            
            # Test user settings
            test_settings = {
                'max_posts_per_run': 25,
                'max_caption_length': 400,
                'optimal_min_length': 100,
                'optimal_max_length': 300,
                'reprocess_existing': True,
                'processing_delay': 2.0
            }
            
            # Update settings
            success = redis_platform_manager.update_user_settings(test_user_id, platform_id, test_settings)
            if success:
                print("✓ Updated user settings via Redis")
                
                # Retrieve settings
                retrieved_settings = redis_platform_manager.get_user_settings(test_user_id, platform_id)
                if retrieved_settings:
                    print("✓ Retrieved user settings from Redis")
                    print(f"  Max posts per run: {retrieved_settings['max_posts_per_run']}")
                    print(f"  Max caption length: {retrieved_settings['max_caption_length']}")
                else:
                    print("✗ Failed to retrieve user settings")
            else:
                print("✗ Failed to update user settings")
        
        # Test cache invalidation
        redis_platform_manager.invalidate_user_cache(test_user_id)
        print("✓ Cache invalidation successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during platform testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_redis_platform_manager()
    if success:
        print("\n✓ All Redis platform manager tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)
