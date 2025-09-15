#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Complete User Deletion Script

This script provides a user-friendly interface to completely delete a user and all their data.
It uses the comprehensive delete_user_data.py script to ensure all associated data is removed.

Features:
- Interactive user selection
- Comprehensive data deletion (posts, images, sessions, etc.)
- Dry-run capability to preview what will be deleted
- Safety confirmations
- Detailed deletion summary

Usage:
    python3 scripts/setup/delete_user.py
"""

import os
import sys
import logging
import subprocess

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
    """Get user role choice for filtering"""
    print("\nFilter by role:")
    print("1. Admin")
    print("2. Reviewer") 
    print("3. User")
    print("4. All users")
    
    while True:
        choice = input("Select role filter (1-4): ").strip()
        if choice == "1":
            return UserRole.ADMIN
        elif choice == "2":
            return UserRole.REVIEWER
        elif choice == "3":
            return UserRole.USER
        elif choice == "4":
            return None
        else:
            print("Please select 1, 2, 3, or 4.")

def select_user_to_delete(users):
    """Select a user from the list to delete"""
    if not users:
        print("No users available to delete.")
        return None
    
    print("\n🗑️  Select User to Delete")
    print("-" * 25)
    
    while True:
        try:
            choice = int(input(f"Select user to delete (1-{len(users)}): "))
            if 1 <= choice <= len(users):
                return users[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(users)}")
        except ValueError:
            print("Please enter a valid number.")

def run_dry_run_deletion(user_id, username):
    """Run a dry-run deletion to show what would be deleted"""
    print(f"\n📊 Running dry-run deletion for user: {username} (ID: {user_id})")
    print("=" * 60)
    
    try:
        # Run the delete_user_data.py script in dry-run mode
        script_path = os.path.join(os.path.dirname(__file__), '..', 'maintenance', 'delete_user_data.py')
        result = subprocess.run([
            sys.executable, script_path,
            '--user-id', str(user_id),
            '--dry-run'
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:")
            print(result.stderr)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running dry-run deletion: {e}")
        if e.stdout:
            print("Output:", e.stdout)
        if e.stderr:
            print("Error:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def run_actual_deletion(user_id, username):
    """Run the actual deletion"""
    print(f"\n🗑️  Deleting all data for user: {username} (ID: {user_id})")
    print("=" * 60)
    
    try:
        # Run the delete_user_data.py script with confirmation
        script_path = os.path.join(os.path.dirname(__file__), '..', 'maintenance', 'delete_user_data.py')
        result = subprocess.run([
            sys.executable, script_path,
            '--user-id', str(user_id),
            '--confirm'
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:")
            print(result.stderr)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running deletion: {e}")
        if e.stdout:
            print("Output:", e.stdout)
        if e.stderr:
            print("Error:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def delete_user_record(db_manager, user_id):
    """Delete the user record itself after all data has been cleaned up"""
    try:
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                username = user.username
                session.delete(user)
                session.commit()
                print(f"✅ Successfully deleted user record for '{username}'!")
                return True
            else:
                print(f"⚠️  User record with ID {user_id} not found (may have been deleted already)")
                return True
    except Exception as e:
        print(f"❌ Error deleting user record: {e}")
        return False

def confirm_deletion(user):
    """Get confirmation for deletion"""
    print(f"\n⚠️  FINAL CONFIRMATION")
    print("=" * 30)
    print(f"User to delete: {user.username} ({user.email}) - {user.role.value}")
    print("\n🚨 WARNING: This action is IRREVERSIBLE!")
    print("This will permanently delete:")
    print("  • User account")
    print("  • All posts and images")
    print("  • All processing runs")
    print("  • All platform connections")
    print("  • All sessions and cached data")
    print("  • All audit logs")
    print("  • All associated files and directories")
    
    # First, simple yes/no confirmation
    print(f"\nAre you absolutely sure you want to delete user '{user.username}'?")
    simple_confirm = input("Type 'yes' to continue or anything else to cancel: ").strip().lower()
    
    if simple_confirm != 'yes':
        print("❌ Deletion cancelled.")
        return False
    
    # Second, more specific confirmation
    print(f"\nFinal confirmation required.")
    print(f"To proceed, type exactly: DELETE {user.username}")
    print(f"(You must include the username '{user.username}' after DELETE)")
    confirmation = input("Final confirmation: ").strip()
    
    expected = f"DELETE {user.username}"
    if confirmation == expected:
        return True
    else:
        print(f"❌ Confirmation text did not match.")
        print(f"   Expected: DELETE {user.username}")
        print(f"   You typed: {confirmation}")
        print("   Deletion cancelled.")
        return False

def main():
    print("🗑️  Vedfolnir User Deletion Tool")
    print("=" * 35)
    print("This tool will completely delete a user and ALL their data.")
    print("Use with extreme caution - deletions are permanent!")
    print("\n💡 Confirmation Process:")
    print("   1. Select user to delete")
    print("   2. Review dry-run preview")
    print("   3. Type 'yes' to proceed")
    print("   4. Type 'DELETE username' to confirm")
    
    try:
        # Load environment and initialize database
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        config = Config()
        db_manager = DatabaseManager(config)
        
        while True:
            print("\n" + "=" * 50)
            print("Options:")
            print("1. List all users")
            print("2. List users by role")
            print("3. Delete a user")
            print("4. Exit")
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                list_users(db_manager)
            
            elif choice == "2":
                role = get_role_choice()
                list_users(db_manager, role)
            
            elif choice == "3":
                # Delete user workflow
                print("\n📋 Step 1: Select user to delete")
                users = list_users(db_manager)
                if not users:
                    continue
                
                user = select_user_to_delete(users)
                if not user:
                    continue
                
                print(f"\n📊 Step 2: Preview deletion for {user.username}")
                if not run_dry_run_deletion(user.id, user.username):
                    print("❌ Dry-run failed. Cannot proceed with deletion.")
                    continue
                
                print(f"\n❓ Step 3: Confirm deletion")
                proceed = input("\nDo you want to proceed with the actual deletion? (y/N): ").strip().lower()
                if proceed != 'y':
                    print("Deletion cancelled.")
                    continue
                
                if not confirm_deletion(user):
                    continue
                
                print(f"\n🗑️  Step 4: Execute deletion")
                if run_actual_deletion(user.id, user.username):
                    # Delete the user record itself
                    if delete_user_record(db_manager, user.id):
                        print(f"\n✅ User '{user.username}' and all associated data have been completely deleted!")
                    else:
                        print(f"\n⚠️  User data was deleted but there was an issue removing the user record.")
                else:
                    print(f"\n❌ Deletion failed. User '{user.username}' was not deleted.")
            
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