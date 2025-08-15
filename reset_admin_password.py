#!/usr/bin/env python3
"""
Reset admin password for testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from models import User, UserRole

def reset_admin_password():
    """Reset admin password to a known value for testing"""
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    session = db_manager.get_session()
    try:
        # Find the first admin user
        admin_user = session.query(User).filter_by(
            role=UserRole.ADMIN,
            is_active=True
        ).first()
        
        if not admin_user:
            print("No active admin user found")
            return False
        
        # Reset password to a known value
        test_password = "admin123"
        admin_user.set_password(test_password)
        session.commit()
        
        print(f"Admin password reset successfully!")
        print(f"Username: {admin_user.username}")
        print(f"Password: {test_password}")
        
        # Verify the password works
        if admin_user.check_password(test_password):
            print("✓ Password verification successful")
            return True
        else:
            print("✗ Password verification failed")
            return False
        
    except Exception as e:
        session.rollback()
        print(f"Error resetting password: {e}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    success = reset_admin_password()
    sys.exit(0 if success else 1)