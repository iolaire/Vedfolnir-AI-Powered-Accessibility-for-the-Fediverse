#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify platform context functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from session_manager import SessionManager
from models import User, PlatformConnection
from platform_context_utils import ensure_platform_context, validate_platform_context, refresh_platform_context

def test_platform_context():
    """Test platform context functionality"""
    print("Testing platform context functionality...")
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    session_manager = SessionManager(db_manager)
    
    # Get a test user
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).filter_by(is_active=True).first()
        if not user:
            print("❌ No active users found in database")
            return False
        
        print(f"✅ Found test user: {user.username}")
        
        # Check user's platforms
        platforms = db_session.query(PlatformConnection).filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        if not platforms:
            print("❌ No active platforms found for user")
            return False
        
        print(f"✅ Found {len(platforms)} active platforms for user")
        for platform in platforms:
            print(f"   - {platform.name} ({platform.platform_type}) - Default: {platform.is_default}")
        
        # Test session creation
        default_platform = next((p for p in platforms if p.is_default), platforms[0])
        session_id = session_manager.create_user_session(user.id, default_platform.id)
        
        if not session_id:
            print("❌ Failed to create user session")
            return False
        
        print(f"✅ Created session: {session_id}")
        
        # Test session context retrieval
        context = session_manager.get_session_context(session_id)
        if not context:
            print("❌ Failed to retrieve session context")
            return False
        
        print(f"✅ Retrieved session context:")
        print(f"   - User ID: {context['user_id']}")
        print(f"   - Platform ID: {context['platform_connection_id']}")
        print(f"   - Platform Name: {context['platform_name']}")
        print(f"   - Platform Type: {context['platform_type']}")
        
        # Test platform switching
        if len(platforms) > 1:
            other_platform = next((p for p in platforms if p.id != default_platform.id), None)
            if other_platform:
                print(f"Testing platform switch to: {other_platform.name}")
                success = session_manager.update_platform_context(session_id, other_platform.id)
                
                if success:
                    print("✅ Platform switch successful")
                    
                    # Verify the switch
                    updated_context = session_manager.get_session_context(session_id)
                    if updated_context and updated_context['platform_connection_id'] == other_platform.id:
                        print(f"✅ Platform context updated to: {updated_context['platform_name']}")
                    else:
                        print("❌ Platform context not properly updated")
                        return False
                else:
                    print("❌ Platform switch failed")
                    return False
        
        # Clean up
        session_manager._cleanup_session(session_id)
        print("✅ Session cleaned up")
        
        print("\n🎉 All platform context tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_platform_context()
    sys.exit(0 if success else 1)