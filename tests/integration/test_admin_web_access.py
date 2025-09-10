#!/usr/bin/env python3
"""
Test script to verify admin user can access System Health dashboard via web interface
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
from web_app import app
import requests
from urllib.parse import urljoin

def test_admin_web_access():
    """Test admin access via web interface"""
    
    base_url = "http://localhost:5000"
    
    # Create a session
    session = requests.Session()
    
    try:
        # Step 1: Get login page
        print("Step 1: Getting login page...")
        login_page = session.get(urljoin(base_url, "/login"))
        print(f"Login page status: {login_page.status_code}")
        
        if login_page.status_code != 200:
            print(f"ERROR: Cannot access login page")
            return False
        
        # Step 2: Extract CSRF token
        print("Step 2: Extracting CSRF token...")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if not csrf_input:
                print("ERROR: CSRF token not found in login page")
                return False
            csrf_token = csrf_input.get('value')
            print(f"CSRF token found: {csrf_token[:20]}...")
        except ImportError:
            print("WARNING: BeautifulSoup not available, skipping CSRF token")
            csrf_token = ""
        
        # Step 3: Login as admin
        print("Step 3: Logging in as admin...")
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        login_response = session.post(urljoin(base_url, "/login"), data=login_data, allow_redirects=False)
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response headers: {dict(login_response.headers)}")
        
        if login_response.status_code == 302:
            redirect_location = login_response.headers.get('Location', '')
            print(f"Login redirect to: {redirect_location}")
            
            if 'login' in redirect_location:
                print("ERROR: Login failed - redirected back to login page")
                return False
            else:
                print("SUCCESS: Login successful - redirected to dashboard")
        elif login_response.status_code == 200:
            if 'login' in login_response.url:
                print("ERROR: Login failed - still on login page")
                return False
            else:
                print("SUCCESS: Login successful")
        else:
            print(f"ERROR: Unexpected login response status: {login_response.status_code}")
            return False
        
        # Step 4: Try to access health dashboard
        print("Step 4: Accessing health dashboard...")
        health_response = session.get(urljoin(base_url, "/health/dashboard"), allow_redirects=False)
        print(f"Health dashboard status: {health_response.status_code}")
        
        if health_response.status_code == 200:
            print("SUCCESS: Admin can access System Health dashboard")
            return True
        elif health_response.status_code == 302:
            redirect_location = health_response.headers.get('Location', '')
            print(f"ERROR: Health dashboard redirected to: {redirect_location}")
            return False
        else:
            print(f"ERROR: Unexpected health dashboard status: {health_response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to web application. Is it running on localhost:5000?")
        return False
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        return False

if __name__ == '__main__':
    success = test_admin_web_access()
    sys.exit(0 if success else 1)