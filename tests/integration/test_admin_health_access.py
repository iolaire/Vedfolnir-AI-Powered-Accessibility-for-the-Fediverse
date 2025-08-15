#!/usr/bin/env python3
"""
Test script to verify admin user can access System Health dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import DatabaseManager
from models import User, UserRole
from flask_login import login_user
from web_app import app

def test_admin_health_access():
    """Test that admin user can access health dashboard"""
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with app.app_context():
        # Get admin user from database
        session = db_manager.get_session()
        try:
            admin_user = session.query(User).filter_by(
                username='admin',
                role=UserRole.ADMIN,
                is_active=True
            ).first()
            
            if not admin_user:
                print("ERROR: Admin user not found")
                return False
            
            print(f"Found admin user: {admin_user.username} (ID: {admin_user.id})")
            print(f"Admin role: {admin_user.role}")
            print(f"Admin active: {admin_user.is_active}")
            
            # Check role permissions
            has_admin_permission = admin_user.has_permission(UserRole.ADMIN)
            print(f"Has admin permission: {has_admin_permission}")
            
            # Test the role_required decorator logic
            from web_app import role_required
            
            # Simulate the role check that happens in the decorator
            server_user = session.query(User).get(admin_user.id)
            if server_user and server_user.is_active:
                has_permission = server_user.has_permission(UserRole.ADMIN)
                print(f"Server-side permission check: {has_permission}")
                
                if has_permission:
                    print("SUCCESS: Admin user should be able to access System Health dashboard")
                    return True
                else:
                    print("ERROR: Admin user does not have required permissions")
                    return False
            else:
                print("ERROR: Admin user not found or inactive in server-side check")
                return False
                
        finally:
            session.close()

if __name__ == '__main__':
    success = test_admin_health_access()
    sys.exit(0 if success else 1)