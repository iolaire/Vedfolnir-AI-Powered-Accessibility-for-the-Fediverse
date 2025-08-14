#!/usr/bin/env python3
"""
Test script to verify that static file requests don't create database sessions.
"""

import requests
import time
import sys
import os

def test_static_requests():
    """Test that static file requests don't create unnecessary sessions."""
    base_url = "http://127.0.0.1:5000"
    
    # List of static files to test
    static_files = [
        "/static/css/style.css",
        "/static/js/app.js", 
        "/static/images/Logo.png",
        "/static/favicons/favicon.ico"
    ]
    
    print("Testing static file requests...")
    print("=" * 50)
    
    for static_file in static_files:
        url = base_url + static_file
        print(f"Requesting: {static_file}")
        
        try:
            response = requests.get(url, timeout=5)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✓ Success")
            elif response.status_code == 404:
                print(f"  ⚠ File not found (expected for some files)")
            else:
                print(f"  ✗ Unexpected status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request failed: {e}")
        
        # Small delay between requests
        time.sleep(0.1)
    
    print("\n" + "=" * 50)
    print("Check the webapp.log file to verify that:")
    print("1. No 'Session created' messages for static file requests")
    print("2. No 'Session closed' messages for static file requests")
    print("3. Only actual page requests should create/close sessions")

if __name__ == "__main__":
    test_static_requests()