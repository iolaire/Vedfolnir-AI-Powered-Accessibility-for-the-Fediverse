#!/usr/bin/env python3
"""
Debug script to check admin user role
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole

def debug_admin_role():
    """Debug admin user role"""
    
    try:
        # Initialize database
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Get admin user
        session = db_manager.get_session()
        try:
            admin_user = session.query(User).filter_by(username='admin').first()
            
            if admin_user:
                print(f"Admin user found:")
                print(f"  ID: {admin_user.id}")
                print(f"  Username: {admin_user.username}")
                print(f"  Email: {admin_user.email}")
                print(f"  Role: {admin_user.role}")
                print(f"  Role type: {type(admin_user.role)}")
                print(f"  Is active: {admin_user.is_active}")
                print(f"  UserRole.ADMIN: {UserRole.ADMIN}")
                print(f"  UserRole.ADMIN type: {type(UserRole.ADMIN)}")
                print(f"  Role == UserRole.ADMIN: {admin_user.role == UserRole.ADMIN}")
                
                # Check password
                test_password = 'RPYMFCKE<$dOu_D)pe;Q_5;j'
                password_valid = admin_user.check_password(test_password)
                print(f"  Password valid: {password_valid}")
                
                # Check platform connections
                from models import PlatformConnection
                platforms = session.query(PlatformConnection).filter_by(
                    user_id=admin_user.id,
                    is_active=True
                ).all()
                print(f"  Platform connections: {len(platforms)}")
                for platform in platforms:
                    print(f"    - {platform.name} ({platform.platform_type})")
                
            else:
                print("Admin user not found!")
                
                # List all users
                all_users = session.query(User).all()
                print(f"All users ({len(all_users)}):")
                for user in all_users:
                    print(f"  - {user.username} (role: {user.role}, active: {user.is_active})")
        
        finally:
            session.close()
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Debugging admin user role...")
    print("=" * 50)
    debug_admin_role()