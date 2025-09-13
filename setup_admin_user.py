#!/usr/bin/env python3
"""
Quick admin user setup for testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import app
from models import User, UserRole
from werkzeug.security import generate_password_hash

def setup_admin_user():
    """Set up admin user if it doesn't exist"""
    with app.app_context():
        db_manager = app.config['db_manager']
        with db_manager.get_session() as session:
            # Check if admin user exists
            admin_user = session.query(User).filter(User.username == 'admin').first()
            if not admin_user:
                # Create admin user
                admin_user = User(
                    username='admin',
                    email='admin@vedfolnir.local',
                    password_hash=generate_password_hash('@4r>bZAvv-WqUC4xz+6kb=|w'),
                    role=UserRole.ADMIN,
                    is_active=True
                )
                session.add(admin_user)
                session.commit()
                print('✅ Admin user created successfully')
                print(f'Username: admin')
                print(f'Password: @4r>bZAvv-WqUC4xz+6kb=|w')
            else:
                print('✅ Admin user already exists')
                print(f'Username: {admin_user.username}')
                print(f'Email: {admin_user.email}')
                print(f'Role: {admin_user.role}')

if __name__ == '__main__':
    setup_admin_user()