#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script to verify concurrent sessions work correctly.
This tests that the same user can have multiple active sessions with different platform contexts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from unified_session_manager import UnifiedSessionManager as SessionManager
from models import User, PlatformConnection

def test_concurrent_sessions():
    """Test that concurrent sessions work correctly"""
    print("Testing concurrent sessions...")
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    session_manager = UnifiedSessionManager(db_manager)
    
    # Get a test user and their platforms
    db_session = db_manager.get_session()
    try:
        # Find a user with multiple platforms
        user = db_session.query(User).filter_by(is_active=True).first()
        if not user:
            print("❌ No active users found for testing")
            return False
        
        platforms = db_session.query(PlatformConnection).filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        if len(platforms) < 2:
            print(f"❌ User {user.username} needs at least 2 platforms for concurrent session testing")
            return False
        
        print(f"✓ Testing with user: {user.username}")
        print(f"✓ Available platforms: {[p.name for p in platforms]}")
        
    finally:
        db_session.close()
    
    # Test 1: Create multiple sessions for the same user
    print("\n1. Creating multiple sessions for the same user...")
    
    session1_id = session_manager.create_session(user.id, platforms[0].id)
    session2_id = session_manager.create_session(user.id, platforms[1].id)
    
    print(f"✓ Created session 1: {session1_id} (platform: {platforms[0].name})")
    print(f"✓ Created session 2: {session2_id} (platform: {platforms[1].name})")
    
    # Test 2: Verify both sessions are active and have different platform contexts
    print("\n2. Verifying session contexts...")
    
    context1 = session_manager.get_session_context(session1_id)
    context2 = session_manager.get_session_context(session2_id)
    
    if not context1 or not context2:
        print("❌ Failed to get session contexts")
        return False
    
    if context1['platform_connection_id'] == context2['platform_connection_id']:
        print("❌ Sessions have the same platform context")
        return False
    
    print(f"✓ Session 1 platform: {context1['platform_connection'].name}")
    print(f"✓ Session 2 platform: {context2['platform_connection'].name}")
    
    # Test 3: Verify both sessions belong to the same user
    print("\n3. Verifying user isolation...")
    
    if context1['user_id'] != context2['user_id']:
        print("❌ Sessions belong to different users")
        return False
    
    if context1['user_id'] != user.id:
        print("❌ Sessions don't belong to the expected user")
        return False
    
    print(f"✓ Both sessions belong to user: {user.username}")
    
    # Test 4: Test platform switching in one session doesn't affect the other
    print("\n4. Testing platform switching isolation...")
    
    # Switch session1 to use the same platform as session2
    original_platform1 = context1['platform_connection_id']
    target_platform = context2['platform_connection_id']
    
    success = session_manager.update_platform_context(session1_id, target_platform)
    if not success:
        print("❌ Failed to switch platform context")
        return False
    
    # Verify session1 changed but session2 remained the same
    new_context1 = session_manager.get_session_context(session1_id)
    new_context2 = session_manager.get_session_context(session2_id)
    
    if new_context1['platform_connection_id'] != target_platform:
        print("❌ Session 1 platform didn't change")
        return False
    
    if new_context2['platform_connection_id'] != target_platform:
        print("❌ Session 2 platform changed unexpectedly")
        return False
    
    print(f"✓ Session 1 switched to: {new_context1['platform_connection'].name}")
    print(f"✓ Session 2 remained on: {new_context2['platform_connection'].name}")
    
    # Test 5: Test getting all active sessions for user
    print("\n5. Testing active sessions retrieval...")
    
    active_sessions = session_manager.get_user_active_sessions(user.id)
    
    if len(active_sessions) < 2:
        print(f"❌ Expected at least 2 active sessions, got {len(active_sessions)}")
        return False
    
    session_ids = [s['session_id'] for s in active_sessions]
    if session1_id not in session_ids or session2_id not in session_ids:
        print("❌ Not all created sessions found in active sessions")
        return False
    
    print(f"✓ Found {len(active_sessions)} active sessions")
    for sess in active_sessions:
        print(f"  - {sess['session_id'][:8]}... on {sess['platform_name']}")
    
    # Test 6: Test session cleanup only affects expired sessions
    print("\n6. Testing selective session cleanup...")
    
    # Clean up expired sessions (should not affect our fresh sessions)
    cleaned_count = session_manager.cleanup_user_sessions(user.id)
    
    # Verify our sessions are still active
    context1_after = session_manager.get_session_context(session1_id)
    context2_after = session_manager.get_session_context(session2_id)
    
    if not context1_after or not context2_after:
        print("❌ Sessions were incorrectly cleaned up")
        return False
    
    print(f"✓ Cleaned up {cleaned_count} expired sessions")
    print("✓ Active sessions preserved")
    
    # Test 7: Test individual session cleanup
    print("\n7. Testing individual session cleanup...")
    
    # Clean up session1 specifically
    success = session_manager._cleanup_session(session1_id)
    if not success:
        print("❌ Failed to clean up specific session")
        return False
    
    # Verify session1 is gone but session2 remains
    context1_final = session_manager.get_session_context(session1_id)
    context2_final = session_manager.get_session_context(session2_id)
    
    if context1_final is not None:
        print("❌ Session 1 was not cleaned up")
        return False
    
    if context2_final is None:
        print("❌ Session 2 was incorrectly cleaned up")
        return False
    
    print("✓ Session 1 cleaned up successfully")
    print("✓ Session 2 remains active")
    
    # Clean up remaining session
    session_manager._cleanup_session(session2_id)
    
    print("\n✅ All concurrent session tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_concurrent_sessions()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)