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
        from app.core.database.core.database_manager import DatabaseManager
        
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
        from app.core.database.core.database_manager import DatabaseManager
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

def check_storage_config():
    """Check storage management configuration"""
    try:
        max_storage_gb = os.getenv('CAPTION_MAX_STORAGE_GB')
        warning_threshold = os.getenv('STORAGE_WARNING_THRESHOLD', '80')
        monitoring_enabled = os.getenv('STORAGE_MONITORING_ENABLED', 'true')
        
        # Validate max storage GB
        if not max_storage_gb:
            print("❌ Storage config: CAPTION_MAX_STORAGE_GB not set")
            return False
        
        try:
            max_storage_float = float(max_storage_gb)
            if max_storage_float <= 0:
                print(f"❌ Storage config: CAPTION_MAX_STORAGE_GB must be positive, got: {max_storage_float}")
                return False
        except ValueError:
            print(f"❌ Storage config: CAPTION_MAX_STORAGE_GB must be numeric, got: '{max_storage_gb}'")
            return False
        
        # Validate warning threshold
        try:
            warning_float = float(warning_threshold)
            if warning_float <= 0 or warning_float > 100:
                print(f"❌ Storage config: STORAGE_WARNING_THRESHOLD must be between 0 and 100, got: {warning_float}")
                return False
        except ValueError:
            print(f"❌ Storage config: STORAGE_WARNING_THRESHOLD must be numeric, got: '{warning_threshold}'")
            return False
        
        # Validate monitoring enabled
        if monitoring_enabled.lower() not in ['true', 'false']:
            print(f"❌ Storage config: STORAGE_MONITORING_ENABLED must be 'true' or 'false', got: '{monitoring_enabled}'")
            return False
        
        print(f"✅ Storage config: Max={max_storage_gb}GB, Warning={warning_threshold}%, Monitoring={monitoring_enabled}")
        return True
        
    except Exception as e:
        print(f"❌ Storage config: Failed to validate ({e})")
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
    
    # Check storage management settings
    all_checks_passed &= check_env_variable("CAPTION_MAX_STORAGE_GB", "Storage limit", required=True)
    all_checks_passed &= check_env_variable("STORAGE_WARNING_THRESHOLD", "Storage warning threshold", required=False)
    all_checks_passed &= check_env_variable("STORAGE_MONITORING_ENABLED", "Storage monitoring", required=False)
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
    
    # Check storage configuration
    print("💾 Storage Configuration:")
    all_checks_passed &= check_storage_config()
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