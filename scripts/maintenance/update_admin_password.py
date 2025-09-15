#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to update admin password in the database
"""

import sys
import os
from werkzeug.security import generate_password_hash

def update_admin_password():
    """Update the admin user password"""
    try:
        # Import required modules
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from models import User, UserRole
        
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        
        new_password = "a[.meG#15n)@H-_<y]5d8TS%"
        
        print("Updating admin password...")
        
        with db_manager.get_session() as session:
            # Find the admin user
            admin_user = session.query(User).filter_by(username='admin').first()
            
            if not admin_user:
                print("❌ Admin user not found")
                return False
            
            # Update the password
            admin_user.password_hash = generate_password_hash(new_password)
            
            # Ensure the user is active and has admin role
            admin_user.is_active = True
            admin_user.role = UserRole.ADMIN
            admin_user.email_verified = True
            admin_user.account_locked = False
            
            session.commit()
            
            print("✅ Admin password updated successfully")
            print(f"Username: {admin_user.username}")
            print(f"Email: {admin_user.email}")
            print(f"Role: {admin_user.role}")
            print(f"Active: {admin_user.is_active}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating admin password: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = update_admin_password()
    sys.exit(0 if success else 1)