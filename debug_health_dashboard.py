#!/usr/bin/env python3
"""
Debug health dashboard access
"""

import sys
import os
sys.path.append('.')

from web_app import app
from flask import url_for
from bs4 import BeautifulSoup

def debug_health_dashboard():
    """Debug health dashboard access"""
    print("=== Health Dashboard Debug ===\n")
    
    with app.test_client() as client:
        # Login as admin
        response = client.get('/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'}).get('value')
        
        login_data = {
            'username': 'admin',
            'password': '(6wR6=P=$?>j?jX,f?zW<NvC',
            'csrf_token': csrf_token
        }
        
        response = client.post('/login', data=login_data, follow_redirects=True)
        print(f"Login status: {response.status_code}")
        
        # Try health dashboard
        response = client.get('/admin/health/dashboard', follow_redirects=False)
        print(f"Health dashboard status: {response.status_code}")
        
        if response.status_code == 302:
            print(f"Redirect location: {response.headers.get('Location')}")
            
            # Follow the redirect
            response = client.get(response.headers.get('Location'))
            print(f"After redirect status: {response.status_code}")
            print(f"After redirect content preview: {response.data.decode()[:200]}")
        elif response.status_code == 200:
            print("Health dashboard accessible!")
        else:
            print(f"Unexpected status: {response.status_code}")
            print(f"Response content: {response.data.decode()[:500]}")

if __name__ == '__main__':
    debug_health_dashboard()