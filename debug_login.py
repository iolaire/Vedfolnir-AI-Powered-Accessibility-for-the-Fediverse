#!/usr/bin/env python3
"""
Debug login process
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from urllib.parse import urljoin

def debug_login():
    """Debug the login process"""
    
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    try:
        # Get login page
        print("Getting login page...")
        login_page = session.get(urljoin(base_url, "/login"))
        print(f"Login page status: {login_page.status_code}")
        
        # Extract CSRF token
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            csrf_token = csrf_input.get('value') if csrf_input else ""
            print(f"CSRF token: {csrf_token}")
        except ImportError:
            csrf_token = ""
        
        # Try login
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        print("Attempting login...")
        login_response = session.post(urljoin(base_url, "/login"), data=login_data)
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response URL: {login_response.url}")
        
        # Check for error messages in response
        if login_response.status_code == 200:
            try:
                soup = BeautifulSoup(login_response.text, 'html.parser')
                # Look for flash messages
                flash_messages = soup.find_all(class_=['alert', 'flash-message', 'error', 'danger'])
                if flash_messages:
                    print("Flash messages found:")
                    for msg in flash_messages:
                        print(f"  - {msg.get_text().strip()}")
                
                # Check if we're still on login page
                if soup.find('form', {'action': '/login'}) or 'login' in login_response.url.lower():
                    print("Still on login page - login failed")
                else:
                    print("Login appears successful")
                    
            except ImportError:
                print("BeautifulSoup not available for detailed analysis")
                
        # Check cookies
        print("Session cookies:")
        for cookie in session.cookies:
            print(f"  {cookie.name}: {cookie.value[:50]}...")
            
    except Exception as e:
        print(f"Debug failed: {e}")

if __name__ == '__main__':
    debug_login()