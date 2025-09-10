#!/usr/bin/env python3
"""
Test script to diagnose admin routing issues
"""

import sys
import os
sys.path.append('.')

from web_app import app
from flask import url_for
from models import User, UserRole
from app.core.database.core.database_manager import DatabaseManager
from config import Config

def test_admin_routes():
    """Test admin route registration and functionality"""
    print("=== Admin Route Testing ===\n")
    
    with app.test_request_context():
        # Test URL generation
        try:
            admin_dashboard_url = url_for('admin.dashboard')
            print(f"✓ Admin dashboard URL: {admin_dashboard_url}")
        except Exception as e:
            print(f"✗ Error generating admin.dashboard URL: {e}")
            return False
        
        try:
            admin_root_url = url_for('admin.dashboard')  # Should map to /admin/
            print(f"✓ Admin root URL: {admin_root_url}")
        except Exception as e:
            print(f"✗ Error generating admin root URL: {e}")
        
        # List admin-specific routes
        print("\n=== Admin Routes ===")
        admin_routes = [rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith('admin.')]
        for rule in admin_routes:
            print(f"  {rule.endpoint}: {rule.rule}")
        
        return True

def test_admin_user():
    """Test admin user existence and credentials"""
    print("\n=== Admin User Testing ===\n")
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    session = db_manager.get_session()
    try:
        # Check if admin user exists
        admin_user = session.query(User).filter_by(username='admin').first()
        
        if admin_user:
            print(f"✓ Admin user found: {admin_user.username}")
            print(f"  - Role: {admin_user.role}")
            print(f"  - Active: {admin_user.is_active}")
            print(f"  - Created: {admin_user.created_at}")
            
            # Test password
            test_password = "(6wR6=P=$?>j?jX,f?zW<NvC"
            if admin_user.check_password(test_password):
                print(f"✓ Admin password verification successful")
                return True
            else:
                print(f"✗ Admin password verification failed")
                return False
        else:
            print("✗ Admin user not found")
            return False
            
    except Exception as e:
        print(f"✗ Error checking admin user: {e}")
        return False
    finally:
        session.close()

def test_admin_template():
    """Test admin template existence"""
    print("\n=== Admin Template Testing ===\n")
    
    template_paths = [
        'admin/templates/dashboard.html'
    ]
    
    for template_path in template_paths:
        full_path = os.path.join(os.getcwd(), template_path)
        if os.path.exists(full_path):
            print(f"✓ Template found: {template_path}")
            return True
        else:
            print(f"✗ Template not found: {template_path}")
    
    return False

def test_admin_blueprint():
    """Test admin blueprint registration"""
    print("\n=== Admin Blueprint Testing ===\n")
    
    # Check if admin blueprint is registered
    admin_blueprint = None
    for blueprint_name, blueprint in app.blueprints.items():
        if blueprint_name == 'admin':
            admin_blueprint = blueprint
            break
    
    if admin_blueprint:
        print(f"✓ Admin blueprint registered: {admin_blueprint.name}")
        print(f"  - URL prefix: {admin_blueprint.url_prefix}")
        print(f"  - Template folder: {admin_blueprint.template_folder}")
        return True
    else:
        print("✗ Admin blueprint not found")
        return False

def test_flask_app():
    """Test Flask app with admin access simulation"""
    print("\n=== Flask App Testing ===\n")
    
    with app.test_client() as client:
        # Test admin dashboard access (should redirect to login)
        response = client.get('/admin/dashboard')
        print(f"Admin dashboard GET /admin/dashboard: {response.status_code}")
        
        if response.status_code == 302:
            print("✓ Correctly redirects unauthenticated users")
        elif response.status_code == 200:
            print("✗ Allows unauthenticated access (security issue)")
        else:
            print(f"✗ Unexpected response: {response.status_code}")
        
        # Test admin root access
        response = client.get('/admin/')
        print(f"Admin root GET /admin/: {response.status_code}")
        
        return True

if __name__ == '__main__':
    print("Starting admin route diagnostics...\n")
    
    success = True
    
    # Run all tests
    success &= test_admin_routes()
    success &= test_admin_user()
    success &= test_admin_template()
    success &= test_admin_blueprint()
    success &= test_flask_app()
    
    print(f"\n=== Summary ===")
    if success:
        print("✓ All tests passed - admin functionality should work")
    else:
        print("✗ Some tests failed - admin functionality may have issues")
    
    print("\nTo test manually:")
    print("1. Start the server: python web_app.py")
    print("2. Go to: http://127.0.0.1:5000/login")
    print("3. Login with: admin / (6wR6=P=$?>j?jX,f?zW<NvC")
    print("4. Navigate to: http://127.0.0.1:5000/admin/dashboard")