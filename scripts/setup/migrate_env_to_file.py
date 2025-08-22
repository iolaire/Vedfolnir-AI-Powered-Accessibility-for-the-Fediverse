#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Migrate environment variables to .env file

This script helps migrate from the system environment variable approach
to the .env file approach for security settings.
"""

import os
import sys
from pathlib import Path

def main():
    print("🔄 Environment Variable to .env File Migration")
    print("=" * 50)
    print()
    
    # Check if .env file already exists
    env_path = Path(".env")
    if env_path.exists():
        print("⚠️  Warning: .env file already exists!")
        response = input("Do you want to update it with environment variables? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. Existing .env file preserved.")
            sys.exit(0)
    
    # Check if .env.example exists for template
    env_example_path = Path(".env.example")
    use_template = env_example_path.exists()
    
    # Required environment variables to migrate
    required_vars = [
        'FLASK_SECRET_KEY',
        'AUTH_ADMIN_USERNAME', 
        'AUTH_ADMIN_EMAIL',
        'AUTH_ADMIN_PASSWORD',
        'PLATFORM_ENCRYPTION_KEY'
    ]
    
    # Check which variables are set in environment
    found_vars = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            found_vars[var] = value
            print(f"✅ Found {var} in environment")
        else:
            missing_vars.append(var)
            print(f"❌ {var} not found in environment")
    
    if not found_vars:
        print()
        print("❌ No required environment variables found!")
        print("This script is for migrating existing environment variables to .env file.")
        print("If you need to set up new variables, use: python3 scripts/setup/generate_env_secrets.py")
        sys.exit(1)
    
    if missing_vars:
        print()
        print(f"⚠️  Warning: {len(missing_vars)} required variables are missing:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        response = input("Continue with partial migration? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. Please set all required environment variables first.")
            sys.exit(0)
    
    print()
    print(f"📝 Migrating {len(found_vars)} variables to .env file...")
    
    try:
        if use_template:
            print("Using .env.example as template...")
            with open(".env.example", "r") as f:
                env_content = f.read()
            
            # Replace placeholder values with environment variable values
            replacements = {
                "FLASK_SECRET_KEY=CHANGE_ME_TO_A_SECURE_32_CHAR_SECRET_KEY": f"FLASK_SECRET_KEY={found_vars.get('FLASK_SECRET_KEY', 'CHANGE_ME_TO_A_SECURE_32_CHAR_SECRET_KEY')}",
                "AUTH_ADMIN_USERNAME=admin_user_change_me": f"AUTH_ADMIN_USERNAME={found_vars.get('AUTH_ADMIN_USERNAME', 'admin_user_change_me')}",
                "AUTH_ADMIN_EMAIL=admin@example.com": f"AUTH_ADMIN_EMAIL={found_vars.get('AUTH_ADMIN_EMAIL', 'admin@example.com')}",
                "AUTH_ADMIN_PASSWORD=CHANGE_ME_TO_A_SECURE_PASSWORD": f"AUTH_ADMIN_PASSWORD={found_vars.get('AUTH_ADMIN_PASSWORD', 'CHANGE_ME_TO_A_SECURE_PASSWORD')}",
                "PLATFORM_ENCRYPTION_KEY=CHANGE_ME_TO_A_FERNET_ENCRYPTION_KEY": f"PLATFORM_ENCRYPTION_KEY={found_vars.get('PLATFORM_ENCRYPTION_KEY', 'CHANGE_ME_TO_A_FERNET_ENCRYPTION_KEY')}"
            }
            
            for old, new in replacements.items():
                env_content = env_content.replace(old, new)
        else:
            # Create basic .env file
            env_content = f"""# Vedfolnir Configuration
# Migrated from environment variables - DO NOT COMMIT TO VERSION CONTROL

# Flask Secret Key (for session security)
FLASK_SECRET_KEY={found_vars.get('FLASK_SECRET_KEY', 'CHANGE_ME_TO_A_SECURE_32_CHAR_SECRET_KEY')}

# Admin User Configuration
AUTH_ADMIN_USERNAME={found_vars.get('AUTH_ADMIN_USERNAME', 'admin_user_change_me')}
AUTH_ADMIN_EMAIL={found_vars.get('AUTH_ADMIN_EMAIL', 'admin@example.com')}
AUTH_ADMIN_PASSWORD={found_vars.get('AUTH_ADMIN_PASSWORD', 'CHANGE_ME_TO_A_SECURE_PASSWORD')}

# Platform Encryption Key (for database credential encryption)
PLATFORM_ENCRYPTION_KEY={found_vars.get('PLATFORM_ENCRYPTION_KEY', 'CHANGE_ME_TO_A_FERNET_ENCRYPTION_KEY')}

# Basic application settings
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=false
DATABASE_URL=mysql+pymysql://storage/database/vedfolnir.db
LOG_LEVEL=INFO
"""
        
        # Write .env file
        with open(".env", "w") as f:
            f.write(env_content)
        
        # Set restrictive permissions (Unix-like systems only)
        if os.name != 'nt':  # Not Windows
            os.chmod(".env", 0o600)  # Read/write for owner only
            print("✅ Set .env file permissions to 600")
        
        print("✅ Successfully created .env file!")
        print()
        
        # Show what was migrated
        print("Migrated variables:")
        for var in found_vars:
            print(f"   ✅ {var}")
        
        if missing_vars:
            print()
            print("Still need to set:")
            for var in missing_vars:
                print(f"   ❌ {var}")
            print("   Edit your .env file to add these values.")
        
        print()
        print("Next steps:")
        print("1. Verify your .env file: cat .env")
        print("2. Test the application: python web_app.py")
        print("3. (Optional) Unset environment variables:")
        for var in found_vars:
            print(f"   unset {var}")
        print()
        print("📖 For more information: docs/security/environment-setup.md")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()