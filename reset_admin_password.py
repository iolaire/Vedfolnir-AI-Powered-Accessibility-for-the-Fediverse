#!/usr/bin/env python3
"""
Reset admin password utility
"""

import sys
import os
import secrets
import string

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(__file__))

def generate_secure_password(length=16):
    """Generate a secure password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))

def reset_admin_password():
    """Reset the admin user password"""
    try:
        from database import DatabaseManager
        from config import Config
        from models import User
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(username='admin').first()
            
            if not admin_user:
                print("❌ Admin user not found in database")
                return False
            
            # Generate new password or use provided one
            use_generated = input("Generate new password? (Y/n): ").strip().lower()
            
            if use_generated != 'n':
                new_password = generate_secure_password()
                print(f"Generated password: {new_password}")
            else:
                new_password = input("Enter new password: ").strip()
                if not new_password:
                    print("❌ Password cannot be empty")
                    return False
            
            # Update password
            admin_user.set_password(new_password)
            session.commit()
            
            print("✅ Admin password updated successfully!")
            print(f"Username: {admin_user.username}")
            print(f"New password: {new_password}")
            print("\n⚠️  Save this password securely!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating admin password: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Admin Password Reset Utility")
    print("=" * 35)
    
    success = reset_admin_password()
    
    if not success:
        sys.exit(1)