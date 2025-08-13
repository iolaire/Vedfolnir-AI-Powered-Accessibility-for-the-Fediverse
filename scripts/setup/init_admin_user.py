#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Initialize the first admin user for the Vedfolnir web interface.
This script should be run once after setting up the database.
"""

import os
import sys
import secrets
import string

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from models import User, UserRole

def generate_secure_password(length=24):
    """Generate a secure password"""
    # Use a mix of characters but avoid ambiguous ones
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(chars) for _ in range(length))

def create_or_update_admin_user(username, email, password):
    """Create or update admin user in database"""
    try:
        # Load environment first to get config
        load_dotenv()
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            # Check if admin user already exists
            existing_user = session.query(User).filter_by(username=username).first()
            
            if existing_user:
                print(f"Admin user already exists: {existing_user.username}")
                response = input(f"Update existing admin user '{existing_user.username}' with new credentials? (y/N): ").strip().lower()
                if response == 'y':
                    existing_user.email = email
                    existing_user.set_password(password)
                    existing_user.role = UserRole.ADMIN
                    existing_user.is_active = True
                    session.commit()
                    print(f"Admin user '{username}' updated successfully")
                    return True, "updated"
                else:
                    print("Keeping existing admin user unchanged")
                    return True, "existing"
            else:
                print(f"Creating new admin user: {username}")
                admin_user = User(
                    username=username,
                    email=email,
                    role=UserRole.ADMIN,
                    is_active=True
                )
                admin_user.set_password(password)
                session.add(admin_user)
                session.commit()
                print(f"Admin user '{username}' created successfully")
                return True, "created"
            
    except Exception as e:
        print(f"Error creating/updating admin user: {e}")
        return False, "error"

def main():
    """Main function"""
    print("👤 Vedfolnir Admin User Setup")
    print("=" * 30)
    print()
    
    # Get admin details from user
    admin_username = input("Admin username (default: admin): ").strip() or "admin"
    admin_email = input("Admin email: ").strip()
    
    if not admin_email:
        print("Error: Admin email is required")
        sys.exit(1)
    
    # Validate email format (basic)
    if "@" not in admin_email or "." not in admin_email.split("@")[-1]:
        print("Error: Please enter a valid email address")
        sys.exit(1)
    
    # Generate secure password
    admin_password = generate_secure_password()
    
    print()
    print("Creating admin user in database...")
    
    # Create or update the admin user
    success, action = create_or_update_admin_user(admin_username, admin_email, admin_password)
    
    if success:
        print()
        if action == "created":
            print(f"✅ Admin user '{admin_username}' created successfully!")
        elif action == "updated":
            print(f"✅ Admin user '{admin_username}' updated successfully!")
        elif action == "existing":
            print(f"ℹ️  Existing admin user kept unchanged.")
        
        print()
        print("You can now log in to the web interface with these credentials:")
        print(f"  Username: {admin_username}")
        print(f"  Email: {admin_email}")
        print(f"  Password: {admin_password}")
        print()
        print("⚠️  IMPORTANT: Save your admin password securely!")
        print("   Consider using a password manager.")
        print()
        print("Next steps:")
        print("1. Start the application: python web_app.py")
        print("2. Open http://localhost:5000 in your browser")
        print("3. Log in with your admin credentials")
    else:
        print("\n❌ Failed to create/update admin user.")
        print("Make sure the database is accessible and environment variables are set.")
        sys.exit(1)

if __name__ == "__main__":
    main()