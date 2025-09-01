#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Quick User Account Unlock Script

Simple script to quickly unlock a user account by username.

Usage:
    python scripts/admin/quick_unlock_user.py <username>
    
Example:
    python scripts/admin/quick_unlock_user.py admin
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from models import User, UserAuditLog

def quick_unlock_user(username):
    """Quickly unlock a user account by username"""
    
    # Setup environment
    load_dotenv()
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Find user
        user = session.query(User).filter_by(username=username).first()
        
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        # Check if account needs unlocking
        if not user.account_locked and user.failed_login_attempts == 0:
            print(f"ℹ️  Account '{username}' is not locked")
            return True
        
        print(f"🔓 Unlocking account: {username}")
        print(f"   Current status: Locked={user.account_locked}, Failed attempts={user.failed_login_attempts}")
        
        # Unlock account
        user.unlock_account()
        
        # Log the action
        UserAuditLog.log_action(
            session,
            action="quick_account_unlock",
            user_id=user.id,
            details=f"Account quickly unlocked via script for user {username}",
            ip_address="127.0.0.1",
            user_agent="quick_unlock_user.py"
        )
        
        session.commit()
        
        print(f"✅ Account '{username}' successfully unlocked")
        return True

def main():
    """Main script execution"""
    if len(sys.argv) != 2:
        print("Usage: python scripts/admin/quick_unlock_user.py <username>")
        print("Example: python scripts/admin/quick_unlock_user.py admin")
        sys.exit(1)
    
    username = sys.argv[1]
    
    try:
        success = quick_unlock_user(username)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error unlocking user '{username}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()