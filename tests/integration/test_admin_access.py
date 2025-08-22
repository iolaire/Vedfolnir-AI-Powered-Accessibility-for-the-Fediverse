#!/usr/bin/env python3
"""
Test script to verify admin access to health dashboard
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import app
from config import Config
from database import DatabaseManager
from models import User, UserRole

def test_admin_access():
    config = Config()
    db_manager = self.get_database_manager()
    
    with app.test_client() as client:
        # Get an admin user
        session = db_manager.get_session()
        try:
            admin_user = session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).first()
            if not admin_user:
                print("No admin user found!")
                return
            
            print(f"Testing with admin user: {admin_user.username}")
            print(f"User role: {admin_user.role}")
            print(f"User role value: {admin_user.role.value}")
            print(f"Has admin permission: {admin_user.has_permission(UserRole.ADMIN)}")
            
        finally:
            session.close()
        
        # Test login (this is simplified - in real app you'd need to handle sessions properly)
        print("\nTesting health dashboard access...")
        
        # For this test, we'll just check if the route exists and doesn't crash
        with app.app_context():
            from flask import url_for

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures

            health_url = url_for('health_dashboard')
            print(f"Health dashboard URL: {health_url}")

if __name__ == "__main__":
    test_admin_access()