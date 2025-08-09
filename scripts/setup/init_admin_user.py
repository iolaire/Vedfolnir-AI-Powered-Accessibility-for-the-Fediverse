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
import logging
import getpass
from config import Config
from database import DatabaseManager
from models import User, UserRole

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_or_update_admin_user(db_manager, username, email, password):
    """Create an admin user if one doesn't exist, or update existing one"""
    session = db_manager.get_session()
    try:
        admin_exists = session.query(User).filter_by(role=UserRole.ADMIN).first()
        if admin_exists:
            logger.info(f"Admin user already exists: {admin_exists.username}")
            
            # Ask if user wants to update existing admin
            response = input(f"Update existing admin user '{admin_exists.username}' with new credentials? (y/N): ").strip().lower()
            if response == 'y':
                success = db_manager.update_user(
                    user_id=admin_exists.id,
                    username=username,
                    email=email,
                    password=password,
                    role=UserRole.ADMIN,
                    is_active=True
                )
                if success:
                    logger.info(f"Admin user '{username}' updated successfully")
                    return True, "updated"
                else:
                    logger.error("Failed to update admin user")
                    return False, "update_failed"
            else:
                logger.info("Keeping existing admin user unchanged")
                return True, "existing"
    finally:
        session.close()
    
    # Create the admin user
    user = db_manager.create_user(
        username=username,
        email=email,
        password=password,
        role=UserRole.ADMIN
    )
    
    if user:
        logger.info(f"Admin user '{username}' created successfully")
        return True, "created"
    else:
        logger.error("Failed to create admin user")
        return False, "create_failed"

def main():
    """Main function"""
    # Load configuration
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Check if admin credentials are provided in environment variables
    admin_username = config.auth.admin_username
    admin_email = config.auth.admin_email
    admin_password = config.auth.admin_password
    
    # If admin password is not set in environment, prompt for it
    if not admin_password:
        print("\nInitializing first admin user for Vedfolnir")
        print("==============================================\n")
        
        if not admin_username:
            admin_username = input("Admin username [admin]: ") or "admin"
        else:
            print(f"Admin username: {admin_username}")
            
        if not admin_email:
            admin_email = input("Admin email [admin@example.com]: ") or "admin@example.com"
        else:
            print(f"Admin email: {admin_email}")
            
        # Prompt for password and confirmation
        while True:
            admin_password = getpass.getpass("Admin password: ")
            if not admin_password:
                print("Password cannot be empty")
                continue
                
            confirm_password = getpass.getpass("Confirm password: ")
            if admin_password != confirm_password:
                print("Passwords do not match")
                continue
                
            break
    
    # Create or update the admin user
    success, action = create_or_update_admin_user(db_manager, admin_username, admin_email, admin_password)
    
    if success:
        if action == "created":
            print(f"\nAdmin user '{admin_username}' created successfully.")
        elif action == "updated":
            print(f"\nAdmin user '{admin_username}' updated successfully.")
        elif action == "existing":
            print(f"\nExisting admin user kept unchanged.")
        print("You can now log in to the web interface with these credentials.")
    else:
        if action == "create_failed":
            print("\nFailed to create admin user. Check the logs for details.")
        elif action == "update_failed":
            print("\nFailed to update admin user. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()