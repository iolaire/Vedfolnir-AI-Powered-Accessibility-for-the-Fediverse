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
                existing_user.email_verified = True
            else:
                print(f"   Creating new admin user: {username}")
                admin_user = User(
                    username=username,
                    email=email,
                    role=UserRole.ADMIN,
                    is_active=True,
                    email_verified=True
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
    
    # Get Ollama configuration from user
    print("Ollama Configuration:")
    ollama_url = input("Ollama URL (default: http://10.0.0.1:11434): ").strip() or "http://10.0.0.1:11434"
    ollama_model = input("Ollama model (default: llava:7b): ").strip() or "llava:7b"
    
    # Get email configuration from user
    print("\nEmail Configuration:")
    print("Configure email settings for user notifications (verification, password reset, etc.)")
    configure_email = input("Configure email settings? (y/N) (default: y): ").strip().lower() == 'y' or "y"
    
    email_settings = {}
    if configure_email:
        email_settings['MAIL_SERVER'] = input("SMTP server (e.g., smtp.gmail.com): ").strip()
        email_settings['MAIL_PORT'] = input("SMTP port (default: 587): ").strip() or "587"
        email_settings['MAIL_USE_TLS'] = input("Use TLS? (Y/n): ").strip().lower() != 'n'
        email_settings['MAIL_USERNAME'] = input("SMTP username/email: ").strip()
        email_settings['MAIL_PASSWORD'] = input("SMTP password/app password: ").strip()
        email_settings['MAIL_DEFAULT_SENDER'] = input(f"Default sender email (default: {email_settings['MAIL_USERNAME']}): ").strip() or email_settings['MAIL_USERNAME']
    else:
        # Set default/disabled email settings
        email_settings = {
            'MAIL_SERVER': 'localhost',
            'MAIL_PORT': '587',
            'MAIL_USE_TLS': True,
            'MAIL_USERNAME': '',
            'MAIL_PASSWORD': '',
            'MAIL_DEFAULT_SENDER': 'noreply@localhost'
        }
    
    # Get security configuration
    print("\nSecurity Configuration:")
    print("Choose security mode:")
    print("1. Development (disable security) - Default")
    print("2. Testing (partial security)")
    print("3. Production (full security)")
    
    while True:
        choice = input("Enter choice (1-3) [1]: ").strip() or '1'
        if choice == '1':
            security_mode = 'development'
            security_settings = {
                'SECURITY_CSRF_ENABLED': 'false',
                'SECURITY_RATE_LIMITING_ENABLED': 'false',
                'SECURITY_INPUT_VALIDATION_ENABLED': 'false'
            }
            break
        elif choice == '2':
            security_mode = 'testing'
            security_settings = {
                'SECURITY_CSRF_ENABLED': 'false',
                'SECURITY_RATE_LIMITING_ENABLED': 'true',
                'SECURITY_INPUT_VALIDATION_ENABLED': 'true'
            }
            break
        elif choice == '3':
            security_mode = 'production'
            security_settings = {
                'SECURITY_CSRF_ENABLED': 'true',
                'SECURITY_RATE_LIMITING_ENABLED': 'true',
                'SECURITY_INPUT_VALIDATION_ENABLED': 'true'
            }
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    print(f"Selected: {security_mode.title()} mode")

    # Get Redis configuration
    print("\nRedis Configuration:")
    print("Configure Redis for session management (recommended for production)")
    configure_redis = input("Configure Redis settings? (Y/n) (default: Y): ").strip().lower() != 'n' or "Y"
    
    redis_settings = {}
    if configure_redis:
        redis_settings['REDIS_HOST'] = input("Redis host (default: localhost): ").strip() or "localhost"
        redis_settings['REDIS_PORT'] = input("Redis port (default: 6379): ").strip() or "6379"
        redis_settings['REDIS_DB'] = input("Redis database number (default: 0): ").strip() or "0"
        redis_settings['REDIS_PASSWORD'] = input("Redis password: ").strip() 
        redis_settings['REDIS_SSL'] = input("Use SSL? (y/N): ").strip().lower() == 'y'
        redis_settings['SESSION_STORAGE'] = 'redis'
    else:
        # Set default Redis settings but use database for sessions
        redis_settings = {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0',
            'REDIS_PASSWORD': 'redis password',
            'REDIS_SSL': False,
            'SESSION_STORAGE': 'database'
        }
    
    # Get admin details from user
    print("\nAdmin User Configuration:")
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
    if configure_email:
        print(f"  Email Server: {email_settings['MAIL_SERVER']}:{email_settings['MAIL_PORT']}")
        print(f"  Email Username: {email_settings['MAIL_USERNAME']}")
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
            env_content = env_content.replace(
                "OLLAMA_URL=CHANGE_ME_TO_OLLAMA_URL_AND_PORT",
                f"OLLAMA_URL={ollama_url}"
            )
            env_content = env_content.replace(
                "OLLAMA_MODEL=CHANGE_ME_TO_OLLAMA_MODEL",
                f"OLLAMA_MODEL={ollama_model}"
            )
            
            # Apply security settings
            import re
            for setting, value in security_settings.items():
                pattern = f'^{setting}=.*$'
                replacement = f'{setting}={value}'
                env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
            
            # Add email settings if not already present
            if 'MAIL_SERVER=' not in env_content:
                email_config = f"""
# Email Configuration (for user notifications)
MAIL_SERVER={email_settings['MAIL_SERVER']}
MAIL_PORT={email_settings['MAIL_PORT']}
MAIL_USE_TLS={'true' if email_settings['MAIL_USE_TLS'] else 'false'}
MAIL_USERNAME={email_settings['MAIL_USERNAME']}
MAIL_PASSWORD={email_settings['MAIL_PASSWORD']}
MAIL_DEFAULT_SENDER={email_settings['MAIL_DEFAULT_SENDER']}
"""
                env_content += email_config
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

# Ollama Configuration
OLLAMA_URL={ollama_url}
OLLAMA_MODEL={ollama_model}

# Security Settings
SECURITY_CSRF_ENABLED={security_settings['SECURITY_CSRF_ENABLED']}
SECURITY_RATE_LIMITING_ENABLED={security_settings['SECURITY_RATE_LIMITING_ENABLED']}
SECURITY_INPUT_VALIDATION_ENABLED={security_settings['SECURITY_INPUT_VALIDATION_ENABLED']}

# Email Configuration (for user notifications)
MAIL_SERVER={email_settings['MAIL_SERVER']}
MAIL_PORT={email_settings['MAIL_PORT']}
MAIL_USE_TLS={'true' if email_settings['MAIL_USE_TLS'] else 'false'}
MAIL_USERNAME={email_settings['MAIL_USERNAME']}
MAIL_PASSWORD={email_settings['MAIL_PASSWORD']}
MAIL_DEFAULT_SENDER={email_settings['MAIL_DEFAULT_SENDER']}
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