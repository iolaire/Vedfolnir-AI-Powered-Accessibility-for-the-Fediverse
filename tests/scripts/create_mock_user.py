#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Create Mock User Script

This script creates a mock user with platform connections for testing purposes.
It can be used standalone or imported into test files.

Usage:
    python tests/scripts/create_mock_user.py [--username USERNAME] [--role ROLE] [--no-platforms]
    
Examples:
    python tests/scripts/create_mock_user.py
    python tests/scripts/create_mock_user.py --username test_reviewer --role reviewer
    python tests/scripts/create_mock_user.py --username test_admin --role admin --no-platforms
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
from database import DatabaseManager
from models import UserRole
from tests.test_helpers.mock_user_helper import MockUserHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_user(username=None, role=UserRole.REVIEWER, with_platforms=True):
    """
    Create a mock user for testing.
    
    Args:
        username: Username for the user (auto-generated if None)
        role: User role
        with_platforms: Whether to create platform connections
        
    Returns:
        Tuple of (user, helper) for cleanup
    """
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Create mock user helper
        helper = MockUserHelper(db_manager)
        
        # Create the user
        user = helper.create_mock_user(
            username=username,
            role=role,
            with_platforms=with_platforms
        )
        
        print(f"✅ Successfully created mock user:")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")
        print(f"   ID: {user.id}")
        
        if with_platforms:
            platform_count = helper.get_created_platform_count()
            print(f"   Platforms: {platform_count} created")
        
        # Save user info for cleanup script
        cleanup_info_file = project_root / "tests" / "scripts" / ".last_created_user.txt"
        with open(cleanup_info_file, 'w') as f:
            f.write(f"{user.id}\n")
            for platform_id in helper.created_platforms:
                f.write(f"platform:{platform_id}\n")
        
        print(f"   Cleanup info saved to: {cleanup_info_file}")
        print("\n💡 Use 'python tests/scripts/cleanup_mock_user.py' to clean up this user")
        
        return user, helper
        
    except Exception as e:
        logger.error(f"Failed to create mock user: {e}")
        sys.exit(1)

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(
        description="Create a mock user for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Create user with default settings
  %(prog)s --username test_reviewer           # Create user with specific username
  %(prog)s --role admin                       # Create admin user
  %(prog)s --no-platforms                     # Create user without platforms
        """
    )
    
    parser.add_argument(
        '--username',
        help='Username for the mock user (auto-generated if not provided)'
    )
    
    parser.add_argument(
        '--role',
        choices=['admin', 'moderator', 'reviewer', 'viewer'],
        default='reviewer',
        help='Role for the mock user (default: reviewer)'
    )
    
    parser.add_argument(
        '--no-platforms',
        action='store_true',
        help='Do not create platform connections for the user'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert role string to enum
    role_map = {
        'admin': UserRole.ADMIN,
        'moderator': UserRole.MODERATOR,
        'reviewer': UserRole.REVIEWER,
        'viewer': UserRole.VIEWER
    }
    role = role_map[args.role]
    
    # Create the user
    create_mock_user(
        username=args.username,
        role=role,
        with_platforms=not args.no_platforms
    )

if __name__ == '__main__':
    main()