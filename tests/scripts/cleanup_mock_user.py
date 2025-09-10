#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Cleanup Mock User Script

This script cleans up mock users and their associated data created for testing purposes.
It can clean up the last created user or specific users by ID.

Usage:
    python tests/scripts/cleanup_mock_user.py [--user-id USER_ID] [--all] [--last]
    
Examples:
    python tests/scripts/cleanup_mock_user.py                    # Clean up last created user
    python tests/scripts/cleanup_mock_user.py --user-id 123     # Clean up specific user
    python tests/scripts/cleanup_mock_user.py --all             # Clean up all test users
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, PlatformConnection
from tests.test_helpers.mock_user_helper import MockUserHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_last_created_user():
    """Clean up the last created user based on saved info"""
    cleanup_info_file = project_root / "tests" / "scripts" / ".last_created_user.txt"
    
    if not cleanup_info_file.exists():
        print("❌ No last created user info found")
        print("   Create a user first with: python tests/scripts/create_mock_user.py")
        return False
    
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        helper = MockUserHelper(db_manager)
        
        # Read cleanup info
        with open(cleanup_info_file, 'r') as f:
            lines = f.read().strip().split('\n')
        
        if not lines or not lines[0]:
            print("❌ Invalid cleanup info file")
            return False
        
        user_id = int(lines[0])
        platform_ids = []
        
        for line in lines[1:]:
            if line.startswith('platform:'):
                platform_ids.append(int(line.split(':')[1]))
        
        # Set up helper tracking for cleanup
        helper.created_users = [user_id]
        helper.created_platforms = platform_ids
        
        # Perform cleanup
        helper.cleanup_mock_users()
        
        # Remove cleanup info file
        cleanup_info_file.unlink()
        
        print(f"✅ Successfully cleaned up user {user_id}")
        if platform_ids:
            print(f"   Cleaned up {len(platform_ids)} associated platforms")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to clean up last created user: {e}")
        return False

def cleanup_specific_user(user_id):
    """Clean up a specific user by ID"""
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        helper = MockUserHelper(db_manager)
        
        # Check if user exists
        session = db_manager.get_session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                print(f"❌ User {user_id} not found")
                return False
            
            username = user.username
            platform_count = len(user.platform_connections)
            
        finally:
            session.close()
        
        # Perform cleanup
        helper.cleanup_specific_user(user_id)
        
        print(f"✅ Successfully cleaned up user {user_id} ({username})")
        if platform_count > 0:
            print(f"   Cleaned up {platform_count} associated platforms")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to clean up user {user_id}: {e}")
        return False

def cleanup_all_test_users():
    """Clean up all users that appear to be test users"""
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        
        session = db_manager.get_session()
        try:
            # Find all users with test-like usernames or emails
            test_users = session.query(User).filter(
                User.username.like('test_%') | 
                User.email.like('test_%@%') |
                User.email.like('%@test.com')
            ).all()
            
            if not test_users:
                print("✅ No test users found to clean up")
                return True
            
            print(f"Found {len(test_users)} test users to clean up:")
            for user in test_users:
                print(f"   - {user.username} ({user.email}) - ID: {user.id}")
            
            # Confirm cleanup
            response = input("\nProceed with cleanup? (y/N): ").strip().lower()
            if response != 'y':
                print("Cleanup cancelled")
                return False
            
            # Clean up each user
            helper = MockUserHelper(db_manager)
            cleaned_count = 0
            
            for user in test_users:
                try:
                    helper.cleanup_specific_user(user.id)
                    cleaned_count += 1
                    print(f"   ✅ Cleaned up {user.username}")
                except Exception as e:
                    print(f"   ❌ Failed to clean up {user.username}: {e}")
            
            print(f"\n✅ Successfully cleaned up {cleaned_count}/{len(test_users)} test users")
            return True
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Failed to clean up all test users: {e}")
        return False

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(
        description="Clean up mock users created for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Clean up last created user
  %(prog)s --user-id 123          # Clean up specific user by ID
  %(prog)s --all                  # Clean up all test users (with confirmation)
        """
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        help='ID of specific user to clean up'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Clean up all test users (requires confirmation)'
    )
    
    parser.add_argument(
        '--last',
        action='store_true',
        help='Clean up last created user (default behavior)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine cleanup mode
    if args.all:
        success = cleanup_all_test_users()
    elif args.user_id:
        success = cleanup_specific_user(args.user_id)
    else:
        # Default: clean up last created user
        success = cleanup_last_created_user()
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()