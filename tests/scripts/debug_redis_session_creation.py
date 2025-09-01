#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug Redis session creation to see what platform data is being stored
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2
from redis_session_backend import RedisSessionBackend
from models import User, PlatformConnection

def test_redis_session_creation():
    """Test Redis session creation with platform data"""
    print("=== Testing Redis Session Creation ===")
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Initialize Redis backend
    redis_backend = RedisSessionBackend(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        password=os.getenv('REDIS_PASSWORD', None)
    )
    
    # Initialize session manager
    session_manager = SessionManagerV2(
        db_manager=db_manager,
        redis_backend=redis_backend
    )
    
    # Get admin user
    with db_manager.get_session() as db_session:
        user = db_session.query(User).filter_by(username='admin').first()
        if not user:
            print("❌ Admin user not found")
            return False
        
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        
        # Get user's platforms
        platforms = db_session.query(PlatformConnection).filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        print(f"✅ Found {len(platforms)} active platforms for user")
        for platform in platforms:
            print(f"  - {platform.name} (ID: {platform.id}, default: {platform.is_default})")
        
        # Get default platform
        default_platform = next(
            (pc for pc in platforms if pc.is_default and pc.is_active),
            None
        )
        
        if not default_platform:
            default_platform = next(
                (pc for pc in platforms if pc.is_active),
                None
            )
        
        if default_platform:
            print(f"✅ Using platform: {default_platform.name} (ID: {default_platform.id})")
            platform_connection_id = default_platform.id
        else:
            print("❌ No active platform found")
            platform_connection_id = None
        
        # Create session with platform data
        print(f"\n=== Creating Redis Session ===")
        session_id = session_manager.create_session(
            user_id=user.id,
            platform_connection_id=platform_connection_id
        )
        
        if session_id:
            print(f"✅ Created session: {session_id}")
            
            # Get session data back
            session_data = session_manager.get_session_data(session_id)
            if session_data:
                print(f"✅ Retrieved session data:")
                for key, value in session_data.items():
                    print(f"  {key}: {value}")
                
                # Check for platform data
                platform_keys = ['platform_connection_id', 'platform_name', 'platform_type', 'platform_instance_url']
                platform_data_found = False
                
                for key in platform_keys:
                    if key in session_data:
                        print(f"✅ Platform data found: {key} = {session_data[key]}")
                        platform_data_found = True
                    else:
                        print(f"❌ Platform data missing: {key}")
                
                if platform_data_found:
                    print("✅ Session contains platform data")
                    return True
                else:
                    print("❌ Session missing platform data")
                    return False
            else:
                print("❌ Could not retrieve session data")
                return False
        else:
            print("❌ Failed to create session")
            return False

if __name__ == "__main__":
    success = test_redis_session_creation()
    sys.exit(0 if success else 1)