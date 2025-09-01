#!/usr/bin/env python3
"""
Redis Session Implementation Demo

This script demonstrates the clean Redis session architecture in action:
- Redis stores all session data on the server
- Flask manages session cookies with unique session IDs  
- Session IDs are used as keys to retrieve data from Redis
"""

import os
import sys
import redis
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_redis_session_architecture():
    """Demonstrate the Redis session architecture"""
    print("🚀 Redis Session Architecture Demo")
    print("=" * 50)
    
    # Initialize Redis client
    from config import Config
    config = Config()
    redis_client = redis.from_url(config.redis.url)
    
    print(f"📡 Connected to Redis: {config.redis.url}")
    print(f"🔑 Session prefix: {config.redis.session_prefix}")
    print(f"⏰ Session timeout: {config.redis.session_timeout}s")
    print()
    
    # Step 1: Simulate Flask creating a session cookie with session ID
    print("Step 1: Flask creates session cookie with unique session ID")
    print("-" * 50)
    
    from flask_redis_session import RedisSession
    
    # Create a new session (simulates Flask session creation)
    session = RedisSession(
        redis_client=redis_client,
        prefix=config.redis.session_prefix,
        timeout=config.redis.session_timeout
    )
    
    session_id = session.session_id
    cookie_value = session_id  # This would be the cookie value sent to browser
    
    print(f"🍪 Session cookie created:")
    print(f"   Cookie name: session")
    print(f"   Cookie value (session ID): {cookie_value}")
    print(f"   HttpOnly: True")
    print(f"   Secure: True")
    print(f"   SameSite: Lax")
    print()
    
    # Step 2: Store session data in Redis
    print("Step 2: Store session data in Redis using session ID as key")
    print("-" * 50)
    
    # Simulate user login - store user data in session
    session['user_id'] = 123
    session['username'] = 'demo_user'
    session['logged_in'] = True
    session['login_time'] = '2025-08-19T18:46:00Z'
    session['platform_connection_id'] = 456
    session['role'] = 'admin'
    
    # Save to Redis
    session.save_to_redis()
    
    redis_key = session.redis_key
    print(f"💾 Session data stored in Redis:")
    print(f"   Redis key: {redis_key}")
    print(f"   Session data: {json.dumps(dict(session), indent=2)}")
    print()
    
    # Step 3: Simulate browser request with session cookie
    print("Step 3: Browser sends request with session cookie")
    print("-" * 50)
    
    # Simulate receiving a request with the session cookie
    incoming_session_id = cookie_value  # This comes from the browser cookie
    
    print(f"📨 Incoming request:")
    print(f"   Cookie: session={incoming_session_id}")
    print(f"   User-Agent: Mozilla/5.0 (Demo Browser)")
    print()
    
    # Step 4: Retrieve session data from Redis
    print("Step 4: Retrieve session data from Redis using session ID")
    print("-" * 50)
    
    # Load session data from Redis using the session ID
    loaded_session = RedisSession.load_from_redis(
        session_id=incoming_session_id,
        redis_client=redis_client,
        prefix=config.redis.session_prefix,
        timeout=config.redis.session_timeout
    )
    
    print(f"🔍 Retrieved from Redis:")
    print(f"   Redis key: {loaded_session.redis_key}")
    print(f"   Session data: {json.dumps(dict(loaded_session), indent=2)}")
    print()
    
    # Step 5: Use session data in application
    print("Step 5: Application uses session data")
    print("-" * 50)
    
    user_id = loaded_session.get('user_id')
    username = loaded_session.get('username')
    is_logged_in = loaded_session.get('logged_in')
    platform_id = loaded_session.get('platform_connection_id')
    role = loaded_session.get('role')
    
    print(f"👤 User information from session:")
    print(f"   User ID: {user_id}")
    print(f"   Username: {username}")
    print(f"   Logged in: {is_logged_in}")
    print(f"   Platform ID: {platform_id}")
    print(f"   Role: {role}")
    print()
    
    # Step 6: Update session data
    print("Step 6: Update session data (e.g., platform switch)")
    print("-" * 50)
    
    # Simulate platform switch
    loaded_session['platform_connection_id'] = 789
    loaded_session['platform_switch_time'] = '2025-08-19T18:47:00Z'
    loaded_session['last_activity'] = '2025-08-19T18:47:00Z'
    
    # Save updated data back to Redis
    loaded_session.save_to_redis()
    
    print(f"🔄 Session updated in Redis:")
    print(f"   New platform ID: {loaded_session.get('platform_connection_id')}")
    print(f"   Switch time: {loaded_session.get('platform_switch_time')}")
    print(f"   Same session ID: {loaded_session.session_id}")
    print(f"   Same Redis key: {loaded_session.redis_key}")
    print()
    
    # Step 7: Verify data persistence
    print("Step 7: Verify data persistence")
    print("-" * 50)
    
    # Load session again to verify updates were saved
    final_session = RedisSession.load_from_redis(
        session_id=session_id,
        redis_client=redis_client,
        prefix=config.redis.session_prefix,
        timeout=config.redis.session_timeout
    )
    
    print(f"✅ Final session state:")
    print(f"   Platform ID: {final_session.get('platform_connection_id')}")
    print(f"   User still logged in: {final_session.get('logged_in')}")
    print(f"   Session persistent: {final_session.session_id == session_id}")
    print()
    
    # Step 8: Show Redis storage details
    print("Step 8: Redis storage details")
    print("-" * 50)
    
    # Get raw Redis data
    raw_data = redis_client.get(redis_key)
    ttl = redis_client.ttl(redis_key)
    
    print(f"🗄️  Raw Redis storage:")
    print(f"   Key: {redis_key}")
    print(f"   TTL: {ttl} seconds")
    print(f"   Data size: {len(raw_data)} bytes")
    print(f"   Raw JSON: {raw_data.decode('utf-8')}")
    print()
    
    # Cleanup
    print("Step 9: Cleanup (logout)")
    print("-" * 50)
    
    # Delete session (simulates logout)
    deleted = final_session.delete_from_redis()
    
    print(f"🗑️  Session cleanup:")
    print(f"   Session deleted: {deleted}")
    print(f"   Redis key removed: {redis_key}")
    
    # Verify deletion
    exists = redis_client.exists(redis_key)
    print(f"   Key exists after deletion: {exists}")
    print()
    
    # Summary
    print("📋 Architecture Summary")
    print("=" * 50)
    print("✅ Redis stores ALL session data on the server")
    print("✅ Flask manages session cookies with unique session IDs")
    print("✅ Session IDs are used as keys to retrieve data from Redis")
    print("✅ Session data is automatically serialized/deserialized")
    print("✅ Automatic expiration prevents memory leaks")
    print("✅ Session updates are immediately persisted")
    print("✅ Clean separation between cookie management and data storage")
    print()
    
    print("🎯 Benefits:")
    print("   • Scalable: Multiple app instances can share Redis")
    print("   • Fast: Sub-millisecond session data access")
    print("   • Secure: Session data never sent to client")
    print("   • Reliable: Automatic cleanup and expiration")
    print("   • Simple: Clean Flask integration")

if __name__ == "__main__":
    demo_redis_session_architecture()
