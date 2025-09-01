#!/usr/bin/env python3
"""
Debug script to see what's causing the admin redirect
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from urllib.parse import urljoin

def debug_admin_redirect():
    """Debug admin redirect issue"""
    
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    try:
        # Step 1: Get login page
        print("Step 1: Getting login page...")
        login_page = session.get(urljoin(base_url, "/login"))
        print(f"Login page status: {login_page.status_code}")
        
        # Step 2: Extract CSRF token
        print("Step 2: Extracting CSRF token...")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            csrf_token = csrf_input.get('value') if csrf_input else ""
            print(f"CSRF token found: {csrf_token[:20]}..." if csrf_token else "No CSRF token found")
        except ImportError:
            print("WARNING: BeautifulSoup not available, skipping CSRF token")
            csrf_token = ""
        
        # Step 3: Login as admin
        print("Step 3: Logging in as admin...")
        login_data = {
            'username': 'admin',
            'password': 'RPYMFCKE<$dOu_D)pe;Q_5;j',
            'csrf_token': csrf_token
        }
        
        login_response = session.post(urljoin(base_url, "/login"), data=login_data, allow_redirects=False)
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response headers: {dict(login_response.headers)}")
        
        if login_response.status_code == 302:
            redirect_location = login_response.headers.get('Location', '')
            print(f"Login redirects to: {redirect_location}")
            
            # Follow the redirect
            follow_response = session.get(redirect_location, allow_redirects=False)
            print(f"Follow redirect status: {follow_response.status_code}")
            if follow_response.status_code == 302:
                next_redirect = follow_response.headers.get('Location', '')
                print(f"Next redirect to: {next_redirect}")
        
        # Step 4: Try to access health dashboard directly
        print("Step 4: Accessing health dashboard directly...")
        health_response = session.get(urljoin(base_url, "/health/dashboard"), allow_redirects=False)
        print(f"Health dashboard status: {health_response.status_code}")
        print(f"Health dashboard headers: {dict(health_response.headers)}")
        
        if health_response.status_code == 302:
            redirect_location = health_response.headers.get('Location', '')
            print(f"Health dashboard redirects to: {redirect_location}")
            
            # Check what's at the redirect location
            redirect_response = session.get(redirect_location, allow_redirects=False)
            print(f"Redirect location status: {redirect_response.status_code}")
            print(f"Redirect location headers: {dict(redirect_response.headers)}")
        
        # Step 5: Check session cookies
        print("Step 5: Checking session cookies...")
        print(f"Session cookies: {session.cookies}")
        
        # Step 6: Try accessing index page
        print("Step 6: Accessing index page...")
        index_response = session.get(urljoin(base_url, "/"), allow_redirects=False)
        print(f"Index status: {index_response.status_code}")
        print(f"Index headers: {dict(index_response.headers)}")
        
        if index_response.status_code == 302:
            redirect_location = index_response.headers.get('Location', '')
            print(f"Index redirects to: {redirect_location}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    print("Debugging admin redirect issue...")
    print("=" * 50)
    debug_admin_redirect()