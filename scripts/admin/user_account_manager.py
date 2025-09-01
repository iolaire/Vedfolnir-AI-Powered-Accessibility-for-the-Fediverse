#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Account Manager Script

Comprehensive script for managing user accounts including unlocking, 
activating/deactivating, and viewing account status.

Usage:
    python scripts/admin/user_account_manager.py <action> [options]

Actions:
    unlock <username>           - Unlock a specific user account
    unlock-all                  - Unlock all locked accounts
    list-locked                 - List all locked accounts
    list-users                  - List all users with their status
    activate <username>         - Activate a user account
    deactivate <username>       - Deactivate a user account
    reset-password <username>   - Reset user password (generates new one)
    user-info <username>        - Show detailed user information
    verify-email <username>     - Mark user email as verified
"""

import sys
import os
import argparse
import secrets
import string
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from models import User, UserAuditLog, UserRole

def setup_environment():
    """Load environment configuration"""
    load_dotenv()
    config = Config()
    db_manager = DatabaseManager(config)
    return config, db_manager

def find_user_by_username(session, username):
    """Find user by username"""
    return session.query(User).filter_by(username=username).first()

def generate_secure_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def list_all_users(db_manager):
    """List all users with their status"""
    print("=== All Users ===")
    
    with db_manager.get_session() as session:
        users = session.query(User).order_by(User.created_at.desc()).all()
        
        if not users:
            print("No users found")
            return
        
        print(f"Found {len(users)} users:")
        print()
        
        for user in users:
            status_parts = []
            if not user.is_active:
                status_parts.append("INACTIVE")
            if user.account_locked:
                status_parts.append("LOCKED")
            if user.failed_login_attempts > 0:
                status_parts.append(f"FAILED_ATTEMPTS({user.failed_login_attempts})")
            if not user.email_verified:
                status_parts.append("UNVERIFIED")
            
            status = " | ".join(status_parts) if status_parts else "ACTIVE"
            
            print(f"  {user.id:3d} | {user.username:20s} | {user.email:30s} | {user.role.value:10s} | {status}")
        
        print()
        print("Legend: INACTIVE=Account disabled, LOCKED=Login locked, FAILED_ATTEMPTS=Failed login count, UNVERIFIED=Email not verified")

def unlock_user(db_manager, username):
    """Unlock a user account"""
    with db_manager.get_session() as session:
        user = find_user_by_username(session, username)
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        if not user.account_locked and user.failed_login_attempts == 0:
            print(f"ℹ️  Account '{username}' is not locked")
            return True
        
        print(f"🔓 Unlocking account: {username}")
        
        # Unlock account
        user.unlock_account()
        
        # Log the action
        UserAuditLog.log_action(
            session,
            action="admin_account_unlock",
            user_id=user.id,
            details=f"Account unlocked by admin script for user {username}",
            ip_address="127.0.0.1",
            user_agent="user_account_manager.py"
        )
        
        session.commit()
        
        print(f"✅ Account '{username}' successfully unlocked")
        return True

def activate_user(db_manager, username):
    """Activate a user account"""
    with db_manager.get_session() as session:
        user = find_user_by_username(session, username)
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        if user.is_active:
            print(f"ℹ️  Account '{username}' is already active")
            return True
        
        print(f"✅ Activating account: {username}")
        
        user.is_active = True
        
        # Log the action
        UserAuditLog.log_action(
            session,
            action="admin_account_activate",
            user_id=user.id,
            details=f"Account activated by admin script for user {username}",
            ip_address="127.0.0.1",
            user_agent="user_account_manager.py"
        )
        
        session.commit()
        
        print(f"✅ Account '{username}' successfully activated")
        return True

def deactivate_user(db_manager, username):
    """Deactivate a user account"""
    with db_manager.get_session() as session:
        user = find_user_by_username(session, username)
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        if not user.is_active:
            print(f"ℹ️  Account '{username}' is already inactive")
            return True
        
        print(f"⚠️  Deactivating account: {username}")
        
        user.is_active = False
        
        # Log the action
        UserAuditLog.log_action(
            session,
            action="admin_account_deactivate",
            user_id=user.id,
            details=f"Account deactivated by admin script for user {username}",
            ip_address="127.0.0.1",
            user_agent="user_account_manager.py"
        )
        
        session.commit()
        
        print(f"✅ Account '{username}' successfully deactivated")
        return True

def reset_user_password(db_manager, username):
    """Reset user password to a new random password"""
    with db_manager.get_session() as session:
        user = find_user_by_username(session, username)
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        # Generate new password
        new_password = generate_secure_password()
        
        print(f"🔑 Resetting password for: {username}")
        
        # Set new password
        user.set_password(new_password)
        
        # Clear any password reset tokens
        user.password_reset_token = None
        user.password_reset_sent_at = None
        user.password_reset_used = False
        
        # Unlock account if it was locked
        if user.account_locked or user.failed_login_attempts > 0:
            user.unlock_account()
            print("   Also unlocked the account")
        
        # Log the action
        UserAuditLog.log_action(
            session,
            action="admin_password_reset",
            user_id=user.id,
            details=f"Password reset by admin script for user {username}",
            ip_address="127.0.0.1",
            user_agent="user_account_manager.py"
        )
        
        session.commit()
        
        print(f"✅ Password reset successfully")
        print(f"   New password: {new_password}")
        print(f"   ⚠️  Please provide this password to the user securely!")
        return True

def verify_user_email(db_manager, username):
    """Mark user email as verified"""
    with db_manager.get_session() as session:
        user = find_user_by_username(session, username)
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        if user.email_verified:
            print(f"ℹ️  Email for '{username}' is already verified")
            return True
        
        print(f"✉️  Verifying email for: {username}")
        
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_sent_at = None
        
        # Log the action
        UserAuditLog.log_action(
            session,
            action="admin_email_verify",
            user_id=user.id,
            details=f"Email verified by admin script for user {username}",
            ip_address="127.0.0.1",
            user_agent="user_account_manager.py"
        )
        
        session.commit()
        
        print(f"✅ Email for '{username}' successfully verified")
        return True

def show_user_info(db_manager, username):
    """Show detailed user information"""
    with db_manager.get_session() as session:
        user = find_user_by_username(session, username)
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        print(f"=== User Information: {username} ===")
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role.value}")
        print(f"Full Name: {user.get_full_name()}")
        print()
        print("Account Status:")
        print(f"  Active: {user.is_active}")
        print(f"  Email Verified: {user.email_verified}")
        print(f"  Account Locked: {user.account_locked}")
        print(f"  Failed Login Attempts: {user.failed_login_attempts}")
        print(f"  GDPR Consent: {user.data_processing_consent}")
        print()
        print("Timestamps:")
        print(f"  Created: {user.created_at}")
        print(f"  Last Login: {user.last_login or 'Never'}")
        print(f"  Last Failed Login: {user.last_failed_login or 'Never'}")
        print(f"  GDPR Consent Date: {user.data_processing_consent_date or 'Not given'}")
        print()
        
        # Show platform connections
        if user.platform_connections:
            print("Platform Connections:")
            for pc in user.platform_connections:
                status = "Active" if pc.is_active else "Inactive"
                default = " (Default)" if pc.is_default else ""
                print(f"  - {pc.name} ({pc.platform_type}) - {status}{default}")
        else:
            print("Platform Connections: None")
        
        return True

def unlock_all_accounts(db_manager):
    """Unlock all locked accounts"""
    with db_manager.get_session() as session:
        locked_users = session.query(User).filter(
            (User.account_locked == True) | (User.failed_login_attempts >= 5)
        ).all()
        
        if not locked_users:
            print("✅ No locked accounts found")
            return 0
        
        print(f"Found {len(locked_users)} locked accounts")
        
        # Confirm action
        response = input(f"Are you sure you want to unlock all {len(locked_users)} accounts? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return 0
        
        unlocked_count = 0
        
        for user in locked_users:
            try:
                print(f"🔓 Unlocking: {user.username}")
                user.unlock_account()
                
                # Log the action
                UserAuditLog.log_action(
                    session,
                    action="admin_bulk_unlock",
                    user_id=user.id,
                    details=f"Account unlocked in bulk operation by admin script",
                    ip_address="127.0.0.1",
                    user_agent="user_account_manager.py"
                )
                
                unlocked_count += 1
            except Exception as e:
                print(f"❌ Failed to unlock {user.username}: {e}")
        
        session.commit()
        
        print(f"✅ Successfully unlocked {unlocked_count} out of {len(locked_users)} accounts")
        return unlocked_count

def list_locked_accounts(db_manager):
    """List all locked accounts"""
    with db_manager.get_session() as session:
        locked_users = session.query(User).filter(
            (User.account_locked == True) | (User.failed_login_attempts >= 5)
        ).all()
        
        if not locked_users:
            print("✅ No locked accounts found")
            return
        
        print(f"=== Locked Accounts ({len(locked_users)} found) ===")
        
        for user in locked_users:
            status_parts = []
            if user.account_locked:
                status_parts.append("LOCKED")
            if user.failed_login_attempts >= 5:
                status_parts.append(f"FAILED_ATTEMPTS({user.failed_login_attempts})")
            
            status = " | ".join(status_parts)
            
            print(f"  {user.username:20s} | {user.email:30s} | {status}")
            print(f"    Last Failed: {user.last_failed_login or 'Never'}")
            print()

def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description="User Account Manager - Comprehensive user account management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Actions:
  unlock <username>           Unlock a specific user account
  unlock-all                  Unlock all locked accounts  
  list-locked                 List all locked accounts
  list-users                  List all users with status
  activate <username>         Activate a user account
  deactivate <username>       Deactivate a user account
  reset-password <username>   Reset user password (generates new one)
  user-info <username>        Show detailed user information
  verify-email <username>     Mark user email as verified

Examples:
  python scripts/admin/user_account_manager.py unlock admin
  python scripts/admin/user_account_manager.py list-locked
  python scripts/admin/user_account_manager.py reset-password admin
  python scripts/admin/user_account_manager.py user-info admin
        """
    )
    
    parser.add_argument('action', help='Action to perform')
    parser.add_argument('username', nargs='?', help='Username (required for user-specific actions)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Validate action
    valid_actions = [
        'unlock', 'unlock-all', 'list-locked', 'list-users',
        'activate', 'deactivate', 'reset-password', 'user-info', 'verify-email'
    ]
    
    if args.action not in valid_actions:
        print(f"❌ Invalid action: {args.action}")
        print(f"Valid actions: {', '.join(valid_actions)}")
        return 1
    
    # Check if username is required
    user_actions = ['unlock', 'activate', 'deactivate', 'reset-password', 'user-info', 'verify-email']
    if args.action in user_actions and not args.username:
        print(f"❌ Username required for action: {args.action}")
        return 1
    
    try:
        # Setup environment
        config, db_manager = setup_environment()
        
        # Execute action
        if args.action == 'unlock':
            success = unlock_user(db_manager, args.username)
        elif args.action == 'unlock-all':
            success = unlock_all_accounts(db_manager) >= 0
        elif args.action == 'list-locked':
            list_locked_accounts(db_manager)
            success = True
        elif args.action == 'list-users':
            list_all_users(db_manager)
            success = True
        elif args.action == 'activate':
            success = activate_user(db_manager, args.username)
        elif args.action == 'deactivate':
            success = deactivate_user(db_manager, args.username)
        elif args.action == 'reset-password':
            success = reset_user_password(db_manager, args.username)
        elif args.action == 'user-info':
            success = show_user_info(db_manager, args.username)
        elif args.action == 'verify-email':
            success = verify_user_email(db_manager, args.username)
        else:
            print(f"❌ Action not implemented: {args.action}")
            success = False
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)