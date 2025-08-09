#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Generate secure environment variables for Vedfolnir

This script generates the required secure environment variables and creates
a properly configured .env file.
"""

import secrets
import string
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import DatabaseManager
from models import User, UserRole

def generate_flask_secret_key():
    """Generate a secure Flask secret key"""
    return secrets.token_urlsafe(32)

def generate_platform_encryption_key():
    """Generate a Fernet encryption key for platform credentials"""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        print("Error: cryptography package is required. Install with: pip install cryptography")
        sys.exit(1)

def generate_secure_password(length=24):
    """Generate a secure password"""
    # Use a mix of characters but avoid ambiguous ones
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(chars) for _ in range(length))

def create_admin_user(username, email, password):
    """Create or update admin user in database"""
    try:
        # Load environment first to get config
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        config = Config()
        
        # Initialize database
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            # Check if admin user already exists
            existing_user = session.query(User).filter_by(username=username).first()
            
            if existing_user:
                print(f"   Updating existing admin user: {username}")
                existing_user.email = email
                existing_user.set_password(password)
                existing_user.role = UserRole.ADMIN
                existing_user.is_active = True
            else:
                print(f"   Creating new admin user: {username}")
                admin_user = User(
                    username=username,
                    email=email,
                    role=UserRole.ADMIN,
                    is_active=True
                )
                admin_user.set_password(password)
                session.add(admin_user)
            
            session.commit()
            return True
            
    except Exception as e:
        print(f"   ❌ Error creating admin user: {e}")
        return False

def main():
    print("🔐 Vedfolnir Environment Secrets Generator")
    print("=" * 50)
    print()
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        print("⚠️  Warning: .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. Existing .env file preserved.")
            print("You can manually edit your .env file or delete it and run this script again.")
            sys.exit(0)
    
    # Check if .env.example exists
    env_example_path = Path(".env.example")
    if not env_example_path.exists():
        print("⚠️  Warning: .env.example file not found!")
        print("This script will create a basic .env file, but you may want to copy from .env.example first.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. Please ensure .env.example exists or run from the project root directory.")
            sys.exit(0)
    
    print("Generating secure environment variables...")
    print()
    
    # Generate all required values
    flask_secret = generate_flask_secret_key()
    encryption_key = generate_platform_encryption_key()
    admin_password = generate_secure_password()
    
    # Get admin details from user
    print("Admin User Configuration:")
    admin_username = input("Admin username (default: admin): ").strip() or "admin"
    admin_email = input("Admin email: ").strip()
    
    if not admin_email:
        print("Error: Admin email is required")
        sys.exit(1)
    
    # Validate email format (basic)
    if "@" not in admin_email or "." not in admin_email.split("@")[-1]:
        print("Error: Please enter a valid email address")
        sys.exit(1)
    
    print()
    print("Generated values:")
    print(f"  Flask Secret Key: {flask_secret[:16]}... (32 chars)")
    print(f"  Encryption Key: {encryption_key[:16]}... (44 chars)")
    print(f"  Admin Username: {admin_username}")
    print(f"  Admin Email: {admin_email}")
    print(f"  Admin Password: {admin_password[:8]}... (24 chars)")
    print()
    
    # Create .env file
    try:
        # If .env.example exists, use it as a template
        if env_example_path.exists():
            print("Using .env.example as template...")
            with open(".env.example", "r") as f:
                env_content = f.read()
            
            # Replace placeholder values with generated ones
            env_content = env_content.replace(
                "FLASK_SECRET_KEY=CHANGE_ME_TO_A_SECURE_32_CHAR_SECRET_KEY",
                f"FLASK_SECRET_KEY={flask_secret}"
            )
            env_content = env_content.replace(
                "PLATFORM_ENCRYPTION_KEY=CHANGE_ME_TO_A_FERNET_ENCRYPTION_KEY",
                f"PLATFORM_ENCRYPTION_KEY={encryption_key}"
            )
        else:
            # Create a basic .env file
            env_content = f"""# Vedfolnir Configuration
# Generated automatically - DO NOT COMMIT TO VERSION CONTROL

# Flask Secret Key (for session security)
FLASK_SECRET_KEY={flask_secret}

# Platform Encryption Key (for database credential encryption)
PLATFORM_ENCRYPTION_KEY={encryption_key}

# Basic application settings
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=false
DATABASE_URL=sqlite:///storage/database/vedfolnir.db
LOG_LEVEL=INFO
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        # Set restrictive permissions (Unix-like systems only)
        if os.name != 'nt':  # Not Windows
            os.chmod(".env", 0o600)  # Read/write for owner only
        
        print("✅ Successfully created .env file!")
        print()
        
        # Create admin user in database
        print("Creating admin user in database...")
        if create_admin_user(admin_username, admin_email, admin_password):
            print("✅ Successfully created admin user in database!")
        else:
            print("❌ Failed to create admin user. You may need to run the application first to initialize the database.")
        
        print()
        print("Next steps:")
        print("1. Start the application:")
        print("   python web_app.py")
        print()
        print("2. Log in with your admin credentials:")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        print()
        print("⚠️  IMPORTANT: Save your admin password securely!")
        print("   Consider using a password manager.")
        print()
        print("📖 For more information, see: docs/security/environment-setup.md")
        
    except Exception as e:
        print(f"Error creating .env file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()