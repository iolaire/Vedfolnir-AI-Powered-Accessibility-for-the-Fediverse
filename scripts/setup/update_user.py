#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User management tool for all user types.

This script allows you to create, update, or manage users of any role in the database.
Supports admin, reviewer, and regular users.
"""

import os
import sys
import logging
import secrets
import string
import getpass

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database.core.database_manager import DatabaseManager
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

def list_users(db_manager, role_filter=None):
    """List users, optionally filtered by role"""
    with db_manager.get_session() as session:
        if role_filter:
            users = session.query(User).filter_by(role=role_filter).all()
            role_name = role_filter.value
        else:
            users = session.query(User).all()
            role_name = "all"
        
        if not users:
            print(f"No {role_name} users found in database.")
            return []
        
        print(f"Found {len(users)} {role_name} user(s):")
        for i, user in enumerate(users, 1):
            status = "Active" if user.is_active else "Inactive"
            print(f"  {i}. {user.username} ({user.email}) - {user.role.value} - {status}")
        
        return users

def get_role_choice():
    """Get user role choice"""
    print("\nUser roles:")
    print("1. Admin")
    print("2. Reviewer") 
    print("3. User")
    
    while True:
        choice = input("Select role (1-3): ").strip()
        if choice == "1":
            return UserRole.ADMIN
        elif choice == "2":
            return UserRole.REVIEWER
        elif choice == "3":
            return UserRole.USER
        else:
            print("Please select 1, 2, or 3.")

def create_user(db_manager):
    """Create a new user interactively"""
    print("\n📝 Create New User")
    print("-" * 20)
    
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
    
    # Get role
    role = get_role_choice()
    
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
                role=role,
                is_active=True,
                email_verified=True
            )
            user.set_password(password)
            session.add(user)
            session.commit()
            
            print(f"✅ Successfully created {role.value} user '{username}'!")
            return True
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False

def update_user(db_manager, users):
    """Update an existing user"""
    if not users:
        print("No users to update.")
        return False
    
    print("\n📝 Update User")
    print("-" * 15)
    
    # Select user to update
    while True:
        try:
            choice = int(input(f"Select user to update (1-{len(users)}): "))
            if 1 <= choice <= len(users):
                user = users[choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(users)}")
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"\nUpdating user: {user.username} ({user.email}) - {user.role.value}")
    
    # Update fields
    new_username = input(f"New username (current: {user.username}, press Enter to keep): ").strip()
    new_email = input(f"New email (current: {user.email}, press Enter to keep): ").strip()
    
    # Role change
    change_role = input(f"Change role? Current: {user.role.value} (y/N): ").strip().lower() == 'y'
    new_role = None
    if change_role:
        new_role = get_role_choice()
    
    # Password change
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
    
    # Account status
    change_status = input(f"Change account status? Current: {'Active' if user.is_active else 'Inactive'} (y/N): ").strip().lower() == 'y'
    new_status = None
    if change_status:
        new_status = input("Set account as active? (y/N): ").strip().lower() == 'y'
    
    # Apply updates
    try:
        with db_manager.get_session() as session:
            user = session.merge(user)  # Reattach to session
            
            if new_username:
                user.username = new_username
            if new_email:
                user.email = new_email
            if new_role:
                user.role = new_role
            if new_password:
                user.set_password(new_password)
            if new_status is not None:
                user.is_active = new_status
            
            session.commit()
            print(f"✅ Successfully updated user!")
            return True
            
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False

def delete_user(db_manager, users):
    """Delete a user (with confirmation)"""
    if not users:
        print("No users to delete.")
        return False
    
    print("\n🗑️  Delete User")
    print("-" * 15)
    print("⚠️  WARNING: This will permanently delete the user!")
    
    # Select user to delete
    while True:
        try:
            choice = int(input(f"Select user to delete (1-{len(users)}): "))
            if 1 <= choice <= len(users):
                user = users[choice - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(users)}")
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"\nUser to delete: {user.username} ({user.email}) - {user.role.value}")
    
    # Confirmation
    confirm = input("Type 'DELETE' to confirm deletion: ").strip()
    if confirm != "DELETE":
        print("Deletion cancelled.")
        return False
    
    try:
        with db_manager.get_session() as session:
            user = session.merge(user)  # Reattach to session
            session.delete(user)
            session.commit()
            print(f"✅ Successfully deleted user '{user.username}'!")
            return True
            
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return False

def main():
    print("👥 Vedfolnir User Management")
    print("=" * 30)
    
    try:
        # Load environment and initialize database
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        config = Config()
        db_manager = DatabaseManager(config)
        
        while True:
            print("\nOptions:")
            print("1. List all users")
            print("2. List users by role")
            print("3. Create new user")
            print("4. Update existing user")
            print("5. Delete user")
            print("6. Exit")
            
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == "1":
                list_users(db_manager)
            
            elif choice == "2":
                print("\nFilter by role:")
                role = get_role_choice()
                list_users(db_manager, role)
            
            elif choice == "3":
                create_user(db_manager)
            
            elif choice == "4":
                users = list_users(db_manager)
                if users:
                    update_user(db_manager, users)
            
            elif choice == "5":
                users = list_users(db_manager)
                if users:
                    delete_user(db_manager, users)
            
            elif choice == "6":
                print("Goodbye!")
                break
            
            else:
                print("Invalid option. Please select 1-6.")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()