#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Verify environment setup for Vedfolnir

This script checks that all required settings are properly configured in the .env file
and provides helpful feedback for any issues.
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import DatabaseManager
from models import User, UserRole

def check_environment_variable(name, description, validator=None):
    """Check if an environment variable is set and valid"""
    value = os.getenv(name)
    
    if not value:
        return False, f"❌ {name}: Not set"
    
    if validator:
        is_valid, message = validator(value)
        if not is_valid:
            return False, f"❌ {name}: {message}"
    
    # Mask sensitive values for display
    if len(value) > 16:
        display_value = f"{value[:8]}...{value[-4:]}"
    else:
        display_value = f"{value[:4]}..."
    
    return True, f"✅ {name}: Set ({display_value})"

def validate_flask_secret_key(value):
    """Validate Flask secret key"""
    if len(value) < 16:
        return False, "Too short (minimum 16 characters recommended)"
    if value in ["your-secret-key", "change-this", "development-key"]:
        return False, "Using default/example value (security risk)"
    return True, "Valid"

def validate_email(value):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        return False, "Invalid email format"
    return True, "Valid"

def validate_username(value):
    """Validate username"""
    if len(value) < 3:
        return False, "Too short (minimum 3 characters)"
    if len(value) > 64:
        return False, "Too long (maximum 64 characters)"
    if not re.match(r'^[a-zA-Z0-9_]+$', value):
        return False, "Invalid characters (use only letters, numbers, underscore)"
    return True, "Valid"

def validate_password(value):
    """Validate password strength"""
    if len(value) < 8:
        return False, "Too short (minimum 8 characters)"
    
    checks = [
        (r'[a-z]', "lowercase letter"),
        (r'[A-Z]', "uppercase letter"),
        (r'[0-9]', "number"),
        (r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', "special character")
    ]
    
    missing = []
    for pattern, description in checks:
        if not re.search(pattern, value):
            missing.append(description)
    
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    
    return True, "Strong"

def validate_encryption_key(value):
    """Validate Fernet encryption key"""
    try:
        from cryptography.fernet import Fernet
        # Try to create a Fernet instance to validate the key
        Fernet(value.encode() if isinstance(value, str) else value)
        return True, "Valid Fernet key"
    except Exception as e:
        return False, f"Invalid Fernet key: {str(e)}"

def main():
    print("🔍 Vedfolnir Environment Verification")
    print("=" * 50)
    print()
    
    # Check if .env file exists
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        print()
        print("To fix this:")
        print("1. Copy the template: cp .env.example .env")
        print("2. Or run the setup script: python3 scripts/setup/generate_env_secrets.py")
        print()
        return 1
    
    # Load .env file
    print(f"📁 Loading .env file...")
    load_dotenv()
    
    # Check file permissions
    if os.name != 'nt':  # Not Windows
        file_stat = env_path.stat()
        file_mode = oct(file_stat.st_mode)[-3:]
        if file_mode != '600':
            print(f"⚠️  Warning: .env file permissions are {file_mode} (should be 600)")
            print("   Fix with: chmod 600 .env")
            print()
    
    # Required environment variables with their validators
    required_vars = [
        ("FLASK_SECRET_KEY", "Flask application secret key", validate_flask_secret_key),
        ("PLATFORM_ENCRYPTION_KEY", "Platform credential encryption key", validate_encryption_key),
    ]
    
    all_good = True
    results = []
    
    for var_name, description, validator in required_vars:
        is_valid, message = check_environment_variable(var_name, description, validator)
        results.append((is_valid, message))
        if not is_valid:
            all_good = False
    
    # Display results
    for is_valid, message in results:
        print(message)
    
    print()
    
    if all_good:
        print("🎉 All required environment variables are properly configured!")
        print()
        print("You can now start the application:")
        print("  python web_app.py")
        print()
        
        # Test configuration loading
        try:
            print("Testing configuration loading...")
            from config import Config
            config = Config()
            print("✅ Configuration loaded successfully!")
            print(f"   Flask host: {config.webapp.host}:{config.webapp.port}")
        except Exception as e:
            print(f"❌ Configuration loading failed: {e}")
            all_good = False
        
        # Check admin user in database
        try:
            print("Checking admin user in database...")
            from config import Config
            config = Config()
            db_manager = DatabaseManager(config)
            with db_manager.get_session() as session:
                admin_users = session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).all()
                if admin_users:
                    print(f"✅ Found {len(admin_users)} active admin user(s):")
                    for user in admin_users:
                        print(f"   - {user.username} ({user.email})")
                else:
                    print("❌ No active admin users found in database!")
                    print("   Run the setup script to create an admin user: python3 scripts/setup/generate_env_secrets.py")
                    all_good = False
        except Exception as e:
            print(f"⚠️  Could not check database for admin users: {e}")
            print("   This is normal if the database hasn't been initialized yet.")
    else:
        print("❌ Some settings in .env file need attention.")
        print()
        print("To fix these issues:")
        print("1. Run the setup script: python3 scripts/setup/generate_env_secrets.py")
        print("2. Or manually edit your .env file with secure values")
        print("3. Run this verification again")
        print()
        print("📖 For detailed instructions: docs/security/environment-setup.md")
    
    # Check .env file status
    print()
    print(f"📁 .env file: {env_path.absolute()}")
    if os.name != 'nt':  # Not Windows
        file_stat = env_path.stat()
        print(f"   Permissions: {oct(file_stat.st_mode)[-3:]}")
        print(f"   Size: {file_stat.st_size} bytes")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())