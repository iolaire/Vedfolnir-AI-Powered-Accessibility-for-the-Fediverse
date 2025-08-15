#!/usr/bin/env python3
"""
Test script to simulate admin login flow and dashboard access
"""

import sys
import os
sys.path.append('.')

from web_app import app
from flask import url_for
from models import User, UserRole
from database import DatabaseManager
from config import Config
from bs4 import BeautifulSoup

def test_full_admin_flow():
    """Test complete admin login and dashboard access flow"""
    print("=== Full Admin Flow Testing ===\n")
    
    with app.test_client() as client:
        # Step 1: Get login page
        print("Step 1: Getting login page...")
        response = client.get('/login')
        print(f"  Login page status: {response.status_code}")
        
        if response.status_code != 200:
            print("✗ Failed to get login page")
            return False
        
        # Step 2: Extract CSRF token
        print("Step 2: Extracting CSRF token...")
        soup = BeautifulSoup(response.data, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})
        
        if not csrf_token:
            print("✗ No CSRF token found")
            return False
        
        csrf_value = csrf_token.get('value')
        print(f"  CSRF token: {csrf_value[:20]}...")
        
        # Step 3: Attempt login
        print("Step 3: Attempting admin login...")
        login_data = {
            'username': 'admin',
            'password': '(6wR6=P=$?>j?jX,f?zW<NvC',
            'csrf_token': csrf_value
        }
        
        response = client.post('/login', data=login_data, follow_redirects=False)
        print(f"  Login response status: {response.status_code}")
        print(f"  Login response location: {response.headers.get('Location', 'None')}")
        
        if response.status_code != 302:
            print("✗ Login did not redirect (expected 302)")
            print(f"Response data: {response.data.decode()[:500]}")
            return False
        
        # Step 4: Follow redirect and check if we're logged in
        print("Step 4: Following login redirect...")
        response = client.get(response.headers['Location'])
        print(f"  Redirect response status: {response.status_code}")
        
        # Step 5: Try to access admin dashboard
        print("Step 5: Accessing admin dashboard...")
        response = client.get('/admin/dashboard')
        print(f"  Dashboard response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Successfully accessed admin dashboard")
            
            # Check if the page contains admin content
            page_content = response.data.decode()
            if 'Site Administration' in page_content:
                print("✓ Admin dashboard content verified")
                return True
            else:
                print("✗ Admin dashboard content not found")
                print(f"Page content preview: {page_content[:300]}")
                return False
        elif response.status_code == 302:
            print(f"✗ Dashboard redirected to: {response.headers.get('Location')}")
            return False
        else:
            print(f"✗ Dashboard returned status: {response.status_code}")
            return False

def test_admin_dashboard_content():
    """Test admin dashboard renders correctly with mock data"""
    print("\n=== Admin Dashboard Content Testing ===\n")
    
    with app.test_request_context():
        with app.test_client() as client:
            # Mock login by setting session
            with client.session_transaction() as sess:
                sess['_user_id'] = '1'  # Assuming admin user ID is 1
                sess['_fresh'] = True
            
            # Access dashboard
            response = client.get('/admin/dashboard')
            print(f"Dashboard access status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.data.decode()
                
                # Check for key admin dashboard elements
                checks = [
                    ('Site Administration', 'Main title'),
                    ('System Overview', 'Stats section'),
                    ('Total Users', 'User stats'),
                    ('User Management', 'Management section'),
                    ('System Health', 'Health section')
                ]
                
                all_found = True
                for check_text, description in checks:
                    if check_text in content:
                        print(f"✓ Found {description}: '{check_text}'")
                    else:
                        print(f"✗ Missing {description}: '{check_text}'")
                        all_found = False
                
                return all_found
            else:
                print(f"✗ Dashboard returned status: {response.status_code}")
                return False

if __name__ == '__main__':
    print("Starting comprehensive admin flow testing...\n")
    
    success = True
    
    # Run tests
    success &= test_full_admin_flow()
    success &= test_admin_dashboard_content()
    
    print(f"\n=== Final Summary ===")
    if success:
        print("✓ All admin flow tests passed")
        print("The admin functionality should work correctly.")
        print("\nIf you're still having issues:")
        print("1. Make sure the server is running: python web_app.py")
        print("2. Clear your browser cache and cookies")
        print("3. Try accessing http://127.0.0.1:5000/admin/ directly after login")
    else:
        print("✗ Some admin flow tests failed")
        print("There may be issues with the admin functionality.")