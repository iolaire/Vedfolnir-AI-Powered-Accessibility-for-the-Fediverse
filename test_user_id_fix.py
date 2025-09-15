#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify that user ID handling is fixed.
This script checks that database operations use integer user IDs instead of username strings.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, ProcessingRun, Post
import logging

def test_user_id_handling():
    """Test that user ID handling works correctly with integers"""
    
    print("=== Testing User ID Handling ===")
    
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("✅ Database connection established")
        
        # Test 1: Check that we can find users by username and get integer IDs
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(username='admin').first()
            if admin_user:
                print(f"✅ Found admin user: ID={admin_user.id} (type: {type(admin_user.id)})")
                assert isinstance(admin_user.id, int), f"User ID should be integer, got {type(admin_user.id)}"
            else:
                print("❌ Admin user not found")
                return False
        
        # Test 2: Check ProcessingRun creation with integer user_id
        print("\n=== Testing ProcessingRun Creation ===")
        with db_manager.get_session() as session:
            # Create a test processing run with integer user_id
            test_run = ProcessingRun(
                user_id=admin_user.id,  # Integer user ID
                batch_id="test_batch_user_id_fix"
            )
            session.add(test_run)
            session.commit()
            
            print(f"✅ Created ProcessingRun with user_id={test_run.user_id} (type: {type(test_run.user_id)})")
            assert isinstance(test_run.user_id, int), f"ProcessingRun user_id should be integer, got {type(test_run.user_id)}"
            
            # Clean up test run
            session.delete(test_run)
            session.commit()
            print("✅ Cleaned up test ProcessingRun")
        
        # Test 3: Check get_or_create_post with integer user_id
        print("\n=== Testing Post Creation ===")
        try:
            # This should work with integer user_id
            test_post = db_manager.get_or_create_post(
                post_id="test_post_user_id_fix",
                user_id=admin_user.id,  # Integer user ID
                post_url="https://example.com/test_post",
                post_content="Test post content"
            )
            print(f"✅ Created/retrieved Post with user_id={test_post.user_id} (type: {type(test_post.user_id)})")
            assert isinstance(test_post.user_id, int), f"Post user_id should be integer, got {type(test_post.user_id)}"
            
            # Clean up test post
            with db_manager.get_session() as session:
                session.delete(test_post)
                session.commit()
                print("✅ Cleaned up test Post")
                
        except Exception as e:
            print(f"❌ Post creation failed: {e}")
            return False
        
        print("\n=== All Tests Passed! ===")
        print("✅ User ID handling is working correctly with integers")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_user_id_handling()
    sys.exit(0 if success else 1)