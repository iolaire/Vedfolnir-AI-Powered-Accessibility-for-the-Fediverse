#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Account Unlock Script

This script allows administrators to unlock user accounts that have been locked
due to failed login attempts or other security measures.

Usage:
    python scripts/admin/unlock_user_account.py --username <username>
    python scripts/admin/unlock_user_account.py --email <email>
    python scripts/admin/unlock_user_account.py --user-id <user_id>
    python scripts/admin/unlock_user_account.py --list-locked
    python scripts/admin/unlock_user_account.py --unlock-all
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from models import User, UserAuditLog
from services.user_management_service import UserAuthenticationService

def setup_environment():
    """Load environment configuration"""
    load_dotenv()
    config = Config()
    db_manager = DatabaseManager(config)
    return config, db_manager

def list_locked_accounts(db_manager):
    """List all locked user accounts"""
    print("=== Locked User Accounts ===")
    
    with db_manager.get_session() as session:
        locked_users = session.query(User).filter(
            (User.account_locked == True) | (User.failed_login_attempts >= 5)
        ).all()
        
        if not locked_users:
            print("✅ No locked accounts found")
            return []
        
        print(f"Found {len(locked_users)} locked accounts:")
        print()
        
        for user in locked_users:
            status_parts = []
            if user.account_locked:
                status_parts.append("LOCKED")
            if user.failed_login_attempts >= 5:
                status_parts.append(f"FAILED_ATTEMPTS({user.failed_login_attempts})")
            if not user.is_active:
                status_parts.append("INACTIVE")
            if not user.email_verified:
                status_parts.append("UNVERIFIED")
            
            status = " | ".join(status_parts)
            
            print(f"  ID: {user.id}")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Role: {user.role.value}")
            print(f"  Status: {status}")
            print(f"  Failed Attempts: {user.failed_login_attempts}")
            print(f"  Last Failed Login: {user.last_failed_login or 'Never'}")
            print(f"  Last Login: {user.last_login or 'Never'}")
            print(f"  Created: {user.created_at}")
            print("-" * 50)
        
        return locked_users

def find_user(db_manager, username=None, email=None, user_id=None):
    """Find a user by username, email, or ID"""
    with db_manager.get_session() as session:
        if user_id:
            user = session.query(User).filter_by(id=user_id).first()
        elif username:
            user = session.query(User).filter_by(username=username).first()
        elif email:
            user = session.query(User).filter_by(email=email).first()
        else:
            return None
        
        return user

def unlock_user_account(db_manager, user, admin_reason=None):
    """Unlock a specific user account"""
    
    with db_manager.get_session() as session:
        # Refresh user object in current session
        user = session.merge(user)
        
        # Check if account needs unlocking
        if not user.account_locked and user.failed_login_attempts == 0:
            print(f"ℹ️  Account for {user.username} is not locked")
            return False
        
        print(f"🔓 Unlocking account for user: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Current Status:")
        print(f"     - Account Locked: {user.account_locked}")
        print(f"     - Failed Attempts: {user.failed_login_attempts}")
        print(f"     - Last Failed Login: {user.last_failed_login}")
        
        # Unlock the account
        user.unlock_account()
        
        # Log the unlock action
        UserAuditLog.log_action(
            session,
            action="account_unlocked_script",
            user_id=user.id,
            details=f"Account unlocked via script. Reason: {admin_reason or 'Administrative unlock'}",
            ip_address="127.0.0.1",
            user_agent="unlock_user_account.py script"
        )
        
        session.commit()
        
        print("✅ Account successfully unlocked")
        print(f"   - Account Locked: {user.account_locked}")
        print(f"   - Failed Attempts: {user.failed_login_attempts}")
        print(f"   - Last Failed Login: {user.last_failed_login}")
        
        return True

def unlock_all_accounts(db_manager, admin_reason=None):
    """Unlock all locked accounts"""
    print("🔓 Unlocking all locked accounts...")
    
    locked_users = list_locked_accounts(db_manager)
    
    if not locked_users:
        return 0
    
    print(f"\nFound {len(locked_users)} accounts to unlock")
    
    # Confirm action
    response = input(f"Are you sure you want to unlock all {len(locked_users)} accounts? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Operation cancelled")
        return 0
    
    unlocked_count = 0
    
    for user in locked_users:
        try:
            if unlock_user_account(db_manager, user, admin_reason):
                unlocked_count += 1
            print()  # Add spacing between users
        except Exception as e:
            print(f"❌ Failed to unlock {user.username}: {e}")
    
    print(f"✅ Successfully unlocked {unlocked_count} out of {len(locked_users)} accounts")
    return unlocked_count

def display_user_info(user):
    """Display detailed user information"""
    print(f"=== User Information ===")
    print(f"ID: {user.id}")
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Role: {user.role.value}")
    print(f"Active: {user.is_active}")
    print(f"Email Verified: {user.email_verified}")
    print(f"Account Locked: {user.account_locked}")
    print(f"Failed Login Attempts: {user.failed_login_attempts}")
    print(f"Last Failed Login: {user.last_failed_login or 'Never'}")
    print(f"Last Login: {user.last_login or 'Never'}")
    print(f"Created: {user.created_at}")
    
    if user.first_name or user.last_name:
        print(f"Full Name: {user.get_full_name()}")

def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="Unlock user accounts that have been locked due to failed login attempts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all locked accounts
  python scripts/admin/unlock_user_account.py --list-locked
  
  # Unlock specific user by username
  python scripts/admin/unlock_user_account.py --username admin
  
  # Unlock specific user by email
  python scripts/admin/unlock_user_account.py --email admin@example.com
  
  # Unlock specific user by ID
  python scripts/admin/unlock_user_account.py --user-id 1
  
  # Unlock all locked accounts
  python scripts/admin/unlock_user_account.py --unlock-all
  
  # Unlock with custom reason
  python scripts/admin/unlock_user_account.py --username admin --reason "Password reset completed"
        """
    )
    
    # User identification options (mutually exclusive)
    user_group = parser.add_mutually_exclusive_group()
    user_group.add_argument('--username', help='Username to unlock')
    user_group.add_argument('--email', help='Email address to unlock')
    user_group.add_argument('--user-id', type=int, help='User ID to unlock')
    user_group.add_argument('--list-locked', action='store_true', help='List all locked accounts')
    user_group.add_argument('--unlock-all', action='store_true', help='Unlock all locked accounts')
    
    # Optional parameters
    parser.add_argument('--reason', help='Reason for unlocking (for audit log)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.username, args.email, args.user_id, args.list_locked, args.unlock_all]):
        parser.error("Must specify one of: --username, --email, --user-id, --list-locked, or --unlock-all")
    
    try:
        # Setup environment
        print("🔧 Setting up environment...")
        config, db_manager = setup_environment()
        print("✅ Environment setup complete")
        print()
        
        # Handle list locked accounts
        if args.list_locked:
            list_locked_accounts(db_manager)
            return 0
        
        # Handle unlock all accounts
        if args.unlock_all:
            unlocked_count = unlock_all_accounts(db_manager, args.reason)
            return 0 if unlocked_count >= 0 else 1
        
        # Handle specific user unlock
        print("🔍 Finding user...")
        user = find_user(db_manager, args.username, args.email, args.user_id)
        
        if not user:
            identifier = args.username or args.email or args.user_id
            print(f"❌ User not found: {identifier}")
            return 1
        
        print("✅ User found")
        print()
        
        # Display user information
        if args.verbose:
            display_user_info(user)
            print()
        
        # Check if confirmation is needed
        if not args.force:
            if user.account_locked or user.failed_login_attempts > 0:
                response = input(f"Unlock account for {user.username} ({user.email})? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("❌ Operation cancelled")
                    return 0
            else:
                print(f"ℹ️  Account for {user.username} is not locked")
                return 0
        
        # Unlock the account
        success = unlock_user_account(db_manager, user, args.reason)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)