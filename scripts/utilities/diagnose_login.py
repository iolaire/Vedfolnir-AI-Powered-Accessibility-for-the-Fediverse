#!/usr/bin/env python3
"""Diagnose login issues"""

import os
from pathlib import Path
from dotenv import load_dotenv
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User

print("🔍 Login Diagnosis")
print("=" * 40)

try:
    # Test 1: .env file and settings
    print("1. .env File Check:")
    env_path = Path(".env")
    if not env_path.exists():
        print("   ❌ .env file not found")
        print("   💡 Solution: Copy .env.example to .env and configure it")
        print("   💡 Or run: python3 scripts/setup/generate_env_secrets.py")
        exit(1)
    else:
        print("   ✅ .env file exists")
    
    # Load .env file
    load_dotenv()
    
    print("\n2. Required Settings:")
    required_vars = ['FLASK_SECRET_KEY', 'AUTH_ADMIN_USERNAME', 'AUTH_ADMIN_EMAIL', 'AUTH_ADMIN_PASSWORD', 'PLATFORM_ENCRYPTION_KEY']
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ❌ {var}: Not set in .env file")
            all_set = False
    
    if not all_set:
        print("\n❌ Missing settings in .env file.")
        print("   💡 Solution: Edit your .env file or run the setup script")
        print("   💡 Run: python3 scripts/setup/generate_env_secrets.py")
        exit(1)
    
    # Test 3: Configuration loading
    print("\n3. Configuration:")
    try:
        config = Config()
        print(f"   ✅ Config loaded successfully")
        print(f"   ✅ Admin username: {config.auth.admin_username}")
        print(f"   ✅ Admin email: {config.auth.admin_email}")
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        exit(1)
    
    # Test 3: Database connection
    print("\n3. Database:")
    try:
        db_manager = DatabaseManager(config)
        session = db_manager.get_session()
        
        # Test query
        user_count = session.query(User).count()
        print(f"   ✅ Database connected")
        print(f"   ✅ Total users: {user_count}")
        
        # Find admin user
        admin_user = session.query(User).filter_by(username=config.auth.admin_username).first()
        if admin_user:
            print(f"   ✅ Admin user found: {admin_user.username}")
            print(f"   ✅ Admin active: {admin_user.is_active}")
            
            # Test password
            password_ok = admin_user.check_password(config.auth.admin_password)
            print(f"   ✅ Password check: {password_ok}")
            
            if not password_ok:
                print("   ⚠️  Password mismatch - this is the login issue!")
        else:
            print(f"   ❌ Admin user not found")
        
        session.close()
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        exit(1)
    
    print("\n🎉 All checks passed!")
    print("\nIf you're still getting login errors:")
    print("1. Try clearing browser cookies/cache")
    print("2. Try an incognito/private browser window")
    print("3. Check browser developer tools for errors")
    print("4. Make sure you're typing the credentials exactly")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()