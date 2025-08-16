#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Verify Environment Setup for Vedfolnir

This script verifies that all required environment variables are properly configured
and that the application can start successfully.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def check_file_exists(filepath, description):
    """Check if a file exists and return status"""
    path = Path(filepath)
    if path.exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (NOT FOUND)")
        return False

def check_env_variable(var_name, description, required=True, min_length=None):
    """Check if an environment variable is set and meets requirements"""
    value = os.getenv(var_name)
    
    if not value:
        if required:
            print(f"❌ {description}: {var_name} (NOT SET)")
            return False
        else:
            print(f"⚠️  {description}: {var_name} (OPTIONAL - not set)")
            return True
    
    if min_length and len(value) < min_length:
        print(f"❌ {description}: {var_name} (TOO SHORT - minimum {min_length} characters)")
        return False
    
    # Don't print the actual value for security
    print(f"✅ {description}: {var_name} (SET - {len(value)} characters)")
    return True

def check_database_connection():
    """Check if database connection works"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        from database import DatabaseManager
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Try to get a session
        with db_manager.get_session() as session:
            # Try a simple query
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
        
        print("✅ Database connection: Working")
        return True
        
    except Exception as e:
        print(f"❌ Database connection: Failed ({e})")
        return False

def check_admin_user():
    """Check if admin user exists in database"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        from database import DatabaseManager
        from models import User, UserRole
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
            
            if admin_user:
                print(f"✅ Admin user: {admin_user.username} (ID: {admin_user.id})")
                return True
            else:
                print("❌ Admin user: No admin user found in database")
                return False
                
    except Exception as e:
        print(f"❌ Admin user check: Failed ({e})")
        return False

def check_encryption_key():
    """Check if platform encryption key is valid"""
    try:
        from cryptography.fernet import Fernet
        
        key = os.getenv('PLATFORM_ENCRYPTION_KEY')
        if not key:
            print("❌ Encryption key: PLATFORM_ENCRYPTION_KEY not set")
            return False
        
        # Try to create a Fernet instance to validate the key
        Fernet(key.encode())
        print("✅ Encryption key: Valid Fernet key format")
        return True
        
    except Exception as e:
        print(f"❌ Encryption key: Invalid format ({e})")
        return False

def check_flask_config():
    """Check Flask configuration"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        
        config = Config()
        
        # Check if config loads without errors
        webapp_config = config.webapp
        
        print(f"✅ Flask config: Host={webapp_config.host}, Port={webapp_config.port}")
        return True
        
    except Exception as e:
        print(f"❌ Flask config: Failed to load ({e})")
        return False

def check_email_config():
    """Check email configuration"""
    try:
        mail_server = os.getenv('MAIL_SERVER')
        mail_port = os.getenv('MAIL_PORT')
        mail_username = os.getenv('MAIL_USERNAME')
        mail_password = os.getenv('MAIL_PASSWORD')
        
        if not mail_server or not mail_port:
            print("⚠️  Email config: Basic settings missing (email features will be disabled)")
            return True  # Not critical for basic functionality
        
        if not mail_username or not mail_password:
            print("⚠️  Email config: Authentication missing (email features will be disabled)")
            return True  # Not critical for basic functionality
        
        # Try to validate port is numeric
        try:
            port_num = int(mail_port)
            if port_num < 1 or port_num > 65535:
                print(f"❌ Email config: Invalid port number {mail_port}")
                return False
        except ValueError:
            print(f"❌ Email config: Port must be numeric, got '{mail_port}'")
            return False
        
        print(f"✅ Email config: Server={mail_server}:{mail_port}, Username={mail_username}")
        return True
        
    except Exception as e:
        print(f"❌ Email config: Failed to validate ({e})")
        return False

def main():
    print("🔍 Vedfolnir Environment Setup Verification")
    print("=" * 50)
    print()
    
    all_checks_passed = True
    
    # Check required files
    print("📁 File Checks:")
    all_checks_passed &= check_file_exists(".env", ".env file")
    all_checks_passed &= check_file_exists(".env.example", ".env.example template")
    print()
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env")
    except Exception as e:
        print(f"❌ Failed to load .env file: {e}")
        all_checks_passed = False
        return
    
    print()
    
    # Check required environment variables
    print("🔐 Environment Variable Checks:")
    all_checks_passed &= check_env_variable("FLASK_SECRET_KEY", "Flask secret key", required=True, min_length=32)
    all_checks_passed &= check_env_variable("PLATFORM_ENCRYPTION_KEY", "Platform encryption key", required=True, min_length=32)
    all_checks_passed &= check_env_variable("DATABASE_URL", "Database URL", required=True)
    all_checks_passed &= check_env_variable("FLASK_HOST", "Flask host", required=False)
    all_checks_passed &= check_env_variable("FLASK_PORT", "Flask port", required=False)
    all_checks_passed &= check_env_variable("LOG_LEVEL", "Log level", required=False)
    
    # Check security settings
    all_checks_passed &= check_env_variable("SECURITY_CSRF_ENABLED", "CSRF protection", required=True)
    all_checks_passed &= check_env_variable("SECURITY_RATE_LIMITING_ENABLED", "Rate limiting", required=True)
    all_checks_passed &= check_env_variable("SECURITY_INPUT_VALIDATION_ENABLED", "Input validation", required=True)
    
    # Check email settings (optional but recommended)
    all_checks_passed &= check_env_variable("MAIL_SERVER", "Email server", required=False)
    all_checks_passed &= check_env_variable("MAIL_PORT", "Email port", required=False)
    all_checks_passed &= check_env_variable("MAIL_USE_TLS", "Email TLS", required=False)
    all_checks_passed &= check_env_variable("MAIL_USERNAME", "Email username", required=False)
    all_checks_passed &= check_env_variable("MAIL_PASSWORD", "Email password", required=False)
    all_checks_passed &= check_env_variable("MAIL_DEFAULT_SENDER", "Email default sender", required=False)
    print()
    
    # Check encryption key format
    print("🔑 Encryption Key Validation:")
    all_checks_passed &= check_encryption_key()
    print()
    
    # Check Flask configuration
    print("⚙️  Flask Configuration:")
    all_checks_passed &= check_flask_config()
    print()
    
    # Check email configuration
    print("📧 Email Configuration:")
    all_checks_passed &= check_email_config()
    print()
    
    # Check database connection
    print("🗄️  Database Checks:")
    all_checks_passed &= check_database_connection()
    all_checks_passed &= check_admin_user()
    print()
    
    # Final summary
    print("📋 Verification Summary:")
    if all_checks_passed:
        print("✅ All checks passed! Your environment is properly configured.")
        print()
        print("🚀 You can now start the application:")
        print("   python web_app.py")
        print()
        print("🌐 Then visit: http://localhost:5000")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print()
        print("🔧 To fix issues:")
        print("   1. Run: python scripts/setup/generate_env_secrets.py")
        print("   2. Or manually edit your .env file")
        print("   3. Run this verification script again")
        print()
        print("📖 For help, see: docs/security/environment-setup.md")
        sys.exit(1)

if __name__ == "__main__":
    main()