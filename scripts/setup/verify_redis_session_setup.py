#!/usr/bin/env python3
"""
Redis Session Setup Verification Script

This script verifies that Redis session management is properly configured
and can connect to the Redis server.
"""

import os
import sys
import redis
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def verify_redis_connection():
    """Verify Redis connection and basic operations"""
    print("🔍 Verifying Redis connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Get Redis configuration
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_password = os.getenv("REDIS_PASSWORD")
    
    print(f"   Redis URL: {redis_url}")
    print(f"   Redis Host: {redis_host}")
    print(f"   Redis Port: {redis_port}")
    print(f"   Redis DB: {redis_db}")
    print(f"   Redis Password: {'Set' if redis_password else 'Not set'}")
    
    try:
        # Try to connect using URL first
        r = redis.from_url(redis_url)
        
        # Test basic operations
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test session operations
        session_prefix = os.getenv("REDIS_SESSION_PREFIX", "vedfolnir:session:")
        test_key = f"{session_prefix}test_session"
        test_data = {"user_id": "1", "test": "true"}  # Use strings instead of native types
        
        # Set test session data
        r.hset(test_key, mapping=test_data)
        r.expire(test_key, 60)  # Expire in 60 seconds
        
        # Retrieve test session data
        retrieved_data = r.hgetall(test_key)
        
        if retrieved_data:
            print("✅ Redis session operations working!")
            print(f"   Test data stored and retrieved: {retrieved_data}")
        else:
            print("❌ Redis session operations failed!")
            return False
        
        # Clean up test data
        r.delete(test_key)
        print("✅ Test cleanup completed!")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Make sure Redis server is running and accessible")
        return False
    except Exception as e:
        print(f"❌ Redis operation failed: {e}")
        return False

def verify_session_config():
    """Verify session configuration settings"""
    print("\n🔍 Verifying session configuration...")
    
    # Load environment variables
    load_dotenv()
    
    # Check required session settings
    required_settings = [
        ("FLASK_SECRET_KEY", "Flask secret key for session security"),
        ("REDIS_URL", "Redis connection URL"),
        ("REDIS_SESSION_PREFIX", "Redis session key prefix"),
        ("REDIS_SESSION_TIMEOUT", "Redis session timeout"),
    ]
    
    all_good = True
    
    for setting, description in required_settings:
        value = os.getenv(setting)
        if value:
            print(f"✅ {setting}: Set ({description})")
        else:
            print(f"❌ {setting}: Not set ({description})")
            all_good = False
    
    # Check optional settings
    optional_settings = [
        ("REDIS_HOST", "Redis host"),
        ("REDIS_PORT", "Redis port"),
        ("REDIS_DB", "Redis database number"),
        ("REDIS_PASSWORD", "Redis password"),
        ("SESSION_COOKIE_HTTPONLY", "HTTP-only session cookies"),
        ("SESSION_COOKIE_SECURE", "Secure session cookies"),
        ("SESSION_COOKIE_SAMESITE", "SameSite cookie policy"),
    ]
    
    print("\n📋 Optional session settings:")
    for setting, description in optional_settings:
        value = os.getenv(setting)
        if value:
            print(f"   {setting}: {value} ({description})")
        else:
            print(f"   {setting}: Default ({description})")
    
    return all_good

def verify_redis_session_manager():
    """Verify that RedisSessionManager can be imported and initialized"""
    print("\n🔍 Verifying RedisSessionManager...")
    
    try:
        from session_manager_v2 import SessionManagerV2
        from config import Config
        from database import DatabaseManager
        
        # Initialize configuration
        config = Config()
        
        # Initialize database manager (needed for session manager)
        db_manager = DatabaseManager(config)
        
        # Initialize Redis session manager
        session_manager = RedisSessionManager(
            db_manager=db_manager,
            redis_host=config.redis.host,
            redis_port=config.redis.port,
            redis_db=config.redis.db,
            redis_password=config.redis.password
        )
        
        print("✅ RedisSessionManager imported and initialized successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import RedisSessionManager: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to initialize RedisSessionManager: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Redis Session Setup Verification")
    print("=" * 50)
    
    # Verify configuration
    config_ok = verify_session_config()
    
    # Verify Redis connection
    redis_ok = verify_redis_connection()
    
    # Verify session manager
    manager_ok = verify_redis_session_manager()
    
    print("\n" + "=" * 50)
    print("📊 Verification Summary:")
    print(f"   Configuration: {'✅ OK' if config_ok else '❌ Issues found'}")
    print(f"   Redis Connection: {'✅ OK' if redis_ok else '❌ Failed'}")
    print(f"   Session Manager: {'✅ OK' if manager_ok else '❌ Failed'}")
    
    if config_ok and redis_ok and manager_ok:
        print("\n🎉 Redis session management is properly configured!")
        print("   Your application is ready to use Redis for session storage.")
        return True
    else:
        print("\n⚠️  Issues found with Redis session setup.")
        print("   Please check the configuration and Redis server status.")
        print("   See .kiro/steering/redis-session-management.md for setup guide.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
