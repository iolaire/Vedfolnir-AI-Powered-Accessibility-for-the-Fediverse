#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Check admin user in database and test password verification
"""

import os
import sys
import getpass

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole

def check_admin_user():
    """Check admin user details and test password"""
    
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("🔍 Admin User Database Check")
        print("=" * 40)
        
        # Get environment credentials
        env_username = config.auth.admin_username
        env_email = config.auth.admin_email
        env_password = config.auth.admin_password
        
        print(f"Environment Variables:")
        print(f"  Username: {env_username}")
        print(f"  Email: {env_email}")
        print(f"  Password: {'*' * len(env_password)}")
        print()
        
        # Check database
        session = db_manager.get_session()
        try:
            # Find admin users
            admin_users = session.query(User).filter_by(role=UserRole.ADMIN).all()
            
            print(f"Admin users in database: {len(admin_users)}")
            
            for i, user in enumerate(admin_users, 1):
                print(f"\nAdmin User #{i}:")
                print(f"  ID: {user.id}")
                print(f"  Username: {user.username}")
                print(f"  Email: {user.email}")
                print(f"  Active: {user.is_active}")
                print(f"  Role: {user.role.value}")
                print(f"  Created: {user.created_at}")
                print(f"  Last Login: {user.last_login}")
                
                # Test password verification
                print(f"  Password Test:")
                if user.check_password(env_password):
                    print(f"    ✅ Environment password matches database")
                else:
                    print(f"    ❌ Environment password does NOT match database")
                    
                    # Test with manual input
                    print(f"    Let's test with manual password input...")
                    manual_password = getpass.getpass(f"    Enter password for {user.username}: ")
                    if user.check_password(manual_password):
                        print(f"    ✅ Manual password matches database")
                        print(f"    ⚠️  This means your environment password is different from database")
                    else:
                        print(f"    ❌ Manual password also does not match")
            
            if not admin_users:
                print("❌ No admin users found in database!")
                print("   Run: python scripts/setup/init_admin_user.py")
                
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_admin_user()