#!/usr/bin/env python3
"""
Test Redis connection and session management
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_redis_connection():
    """Test Redis connection with configured settings"""
    try:
        import redis
        
        # Get Redis configuration from environment
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
        
        print(f"Testing Redis connection to {redis_host}:{redis_port}")
        print(f"Database: {redis_db}")
        print(f"Password: {'***' if redis_password else 'None'}")
        print(f"SSL: {redis_ssl}")
        print()
        
        # Create Redis client
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            ssl=redis_ssl,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test connection
        print("Testing connection...")
        client.ping()
        print("✓ Redis connection successful!")
        
        # Test basic operations
        print("\nTesting basic operations...")
        
        # Set a test key
        client.set('test_key', 'test_value', ex=60)  # Expire in 60 seconds
        print("✓ Set test key")
        
        # Get the test key
        value = client.get('test_key')
        if value == 'test_value':
            print("✓ Retrieved test key")
        else:
            print(f"✗ Retrieved wrong value: {value}")
            return False
        
        # Test hash operations (used for sessions)
        client.hset('test_hash', mapping={'field1': 'value1', 'field2': 'value2'})
        client.expire('test_hash', 60)
        print("✓ Set test hash")
        
        hash_data = client.hgetall('test_hash')
        if hash_data.get('field1') == 'value1':
            print("✓ Retrieved test hash")
        else:
            print(f"✗ Retrieved wrong hash data: {hash_data}")
            return False
        
        # Test set operations (used for session indexes)
        client.sadd('test_set', 'member1', 'member2')
        client.expire('test_set', 60)
        print("✓ Set test set")
        
        set_members = client.smembers('test_set')
        if 'member1' in set_members and 'member2' in set_members:
            print("✓ Retrieved test set")
        else:
            print(f"✗ Retrieved wrong set members: {set_members}")
            return False
        
        # Clean up test keys
        client.delete('test_key', 'test_hash', 'test_set')
        print("✓ Cleaned up test keys")
        
        # Get Redis info
        info = client.info()
        print(f"\nRedis server info:")
        print(f"  Version: {info.get('redis_version', 'unknown')}")
        print(f"  Connected clients: {info.get('connected_clients', 0)}")
        print(f"  Used memory: {info.get('used_memory_human', '0B')}")
        print(f"  Keyspace hits: {info.get('keyspace_hits', 0)}")
        print(f"  Keyspace misses: {info.get('keyspace_misses', 0)}")
        
        print("\n✅ All Redis tests passed!")
        return True
        
    except ImportError:
        print("✗ Redis package not installed. Install with: pip install redis")
        return False
    except redis.ConnectionError as e:
        print(f"✗ Redis connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Redis server is running")
        print("2. Check Redis host and port in .env file")
        print("3. Verify Redis password if authentication is enabled")
        print("4. Check firewall settings")
        return False
    except Exception as e:
        print(f"✗ Redis test failed: {e}")
        return False

def test_session_manager():
    """Test the Redis session manager"""
    try:
        from config import Config
        from database import DatabaseManager
        from session_manager_v2 import SessionManagerV2
        
        print("\nTesting Redis session manager...")
        
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Get Redis configuration
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
        
        # Create Redis session manager
        session_manager = RedisSessionManager(
            db_manager=db_manager,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
            redis_ssl=redis_ssl
        )
        
        print("✓ Redis session manager created")
        
        # Test session statistics
        stats = session_manager.get_session_stats()
        print(f"✓ Session stats: {stats}")
        
        # Test cleanup (should not fail even with no sessions)
        cleaned = session_manager.cleanup_expired_sessions()
        print(f"✓ Cleanup test: {cleaned} sessions cleaned")
        
        print("✅ Redis session manager tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Redis session manager test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔗 Redis Connection and Session Manager Test")
    print("=" * 50)
    
    # Test Redis connection
    redis_ok = test_redis_connection()
    
    if redis_ok:
        # Test session manager
        session_ok = test_session_manager()
        success = redis_ok and session_ok
    else:
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Redis session management is ready.")
    else:
        print("❌ Some tests failed. Check Redis configuration and server status.")
    
    sys.exit(0 if success else 1)