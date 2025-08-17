#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin user management tool.

This script allows you to create, update, or manage admin users in the database.
Admin credentials are stored in the database, not in environment variables.
"""

import os
import sys
import logging
import secrets
import string
import getpass

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import DatabaseManager
from models import User, UserRole

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_secure_password(length=24):
    """Generate a secure password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(chars) for _ in range(length))


def list_admin_users(db_manager):
    """List all admin users"""
    with db_manager.get_session() as session:
        admin_users = session.query(User).filter_by(role=UserRole.ADMIN).all()
        
        if not admin_users:
            print("No admin users found in database.")
            return []
        
        print(f"Found {len(admin_users)} admin user(s):")
        for i, user in enumerate(admin_users, 1):
            status = "Active" if user.is_active else "Inactive"
            print(f"  {i}. {user.username} ({user.email}) - {status}")
        
        return admin_users


def create_admin_user(db_manager):
    """Create a new admin user interactively"""
    print("\n📝 Create New Admin User")
    print("-" * 30)
    
    # Get username
    while True:
        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty.")
            continue
        if len(username) < 3:
            print("Username must be at least 3 characters.")
            continue
        break
    
    # Get email
    while True:
        email = input("Email: ").strip()
        if not email:
            print("Email cannot be empty.")
            continue
        if "@" not in email:
            print("Please enter a valid email address.")
            continue
        break
    
    # Get password
    print("\nPassword options:")
    print("1. Generate secure password automatically")
    print("2. Enter password manually")
    
    choice = input("Choose option (1 or 2): ").strip()
    
    if choice == "1":
        password = generate_secure_password()
        print(f"Generated password: {password}")
        print("⚠️  IMPORTANT: Save this password securely!")
    else:
        while True:
            password = getpass.getpass("Password: ")
            if len(password) < 8:
                print("Password must be at least 8 characters.")
                continue
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Passwords don't match.")
                continue
            break
    
    # Create user
    try:
        with db_manager.get_session() as session:
            # Check if username already exists
            existing = session.query(User).filter_by(username=username).first()
            if existing:
                print(f"❌ User '{username}' already exists!")
                return False
            
            # Create new user
            user = User(
                username=username,
                email=email,
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True
            )
            user.set_password(password)
            session.add(user)
            session.commit()
            
            print(f"✅ Successfully created admin user '{username}'!")
            return True
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False


def update_admin_user(db_manager, admin_users):
    """Update an existing admin user"""
    if not admin_users:
        print("No admin users to update.")
        return False
    
    print("\n📝 Update Admin User")
    print("-" * 20)
    
    # Select user to update
    while True:
        try:
            choice = int(input(f"Select user to update (1-{len(admin_users)}): "))
            if 1 <= choice <= len(admin_users):
                user = admin_users[choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(admin_users)}")
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"\nUpdating user: {user.username} ({user.email})")
    
    # Update fields
    new_username = input(f"New username (current: {user.username}, press Enter to keep): ").strip()
    new_email = input(f"New email (current: {user.email}, press Enter to keep): ").strip()
    
    change_password = input("Change password? (y/N): ").strip().lower() == 'y'
    new_password = None
    
    if change_password:
        print("\nPassword options:")
        print("1. Generate secure password automatically")
        print("2. Enter password manually")
        
        choice = input("Choose option (1 or 2): ").strip()
        
        if choice == "1":
            new_password = generate_secure_password()
            print(f"Generated password: {new_password}")
            print("⚠️  IMPORTANT: Save this password securely!")
        else:
            while True:
                new_password = getpass.getpass("New password: ")
                if len(new_password) < 8:
                    print("Password must be at least 8 characters.")
                    continue
                confirm = getpass.getpass("Confirm password: ")
                if new_password != confirm:
                    print("Passwords don't match.")
                    continue
                break
    
    # Apply updates
    try:
        with db_manager.get_session() as session:
            user = session.merge(user)  # Reattach to session
            
            if new_username:
                user.username = new_username
            if new_email:
                user.email = new_email
            if new_password:
                user.set_password(new_password)
            
            session.commit()
            print(f"✅ Successfully updated admin user!")
            return True
            
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False


def main():
    print("👤 Vedfolnir Admin User Management")
    print("=" * 40)
    
    try:
        # Load environment and initialize database
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        config = Config()
        db_manager = DatabaseManager(config)
        
        while True:
            print("\nOptions:")
            print("1. List admin users")
            print("2. Create new admin user")
            print("3. Update existing admin user")
            print("4. Exit")
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                list_admin_users(db_manager)
            
            elif choice == "2":
                create_admin_user(db_manager)
            
            elif choice == "3":
                admin_users = list_admin_users(db_manager)
                if admin_users:
                    update_admin_user(db_manager, admin_users)
            
            elif choice == "4":
                print("Goodbye!")
                break
            
            else:
                print("Invalid option. Please select 1-4.")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()