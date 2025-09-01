#!/usr/bin/env python3
"""
Check admin user password in database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from models import User, UserRole

def check_admin_password():
    """Check admin user password"""
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    session = db_manager.get_session()
    try:
        admin_users = session.query(User).filter_by(
            role=UserRole.ADMIN,
            is_active=True
        ).all()
        
        print(f"Found {len(admin_users)} active admin users:")
        
        for admin in admin_users:
            print(f"\nAdmin user: {admin.username}")
            print(f"  ID: {admin.id}")
            print(f"  Email: {admin.email}")
            print(f"  Created: {admin.created_at}")
            print(f"  Last login: {admin.last_login}")
            
            # Test common passwords
            test_passwords = ['admin123', 'admin', 'password', 'test123', 'vedfolnir']
            
            for password in test_passwords:
                if admin.check_password(password):
                    print(f"  ✓ Password is: {password}")
                    return admin.username, password
                    
            print(f"  ✗ Password not found in common list")
            
        return None, None
        
    finally:
        session.close()

if __name__ == '__main__':
    username, password = check_admin_password()
    if username and password:
        print(f"\nFound working credentials: {username} / {password}")
    else:
        print("\nNo working credentials found")