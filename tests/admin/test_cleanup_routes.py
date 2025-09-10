#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script to verify cleanup routes are working
"""

import requests
import sys
from config import Config

def test_cleanup_routes():
    """Test if cleanup routes are accessible"""
    base_url = "http://127.0.0.1:5000"
    
    # Test data for form submission
    test_data = {
        'days': 90,
        'dry_run': 'on'
    }
    
    print("Testing cleanup routes...")
    print("=" * 50)
    
    try:
        # Test if the server is running
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✓ Server is running (status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"✗ Server is not accessible: {e}")
        return False
    
    # Test the cleanup runs route
    try:
        print("\nTesting admin_cleanup_runs route...")
        response = requests.post(
            f"{base_url}/admin/cleanup/runs",
            data=test_data,
            timeout=10,
            allow_redirects=False  # Don't follow redirects to see the actual response
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            print("✓ Route responded with redirect (expected)")
            print(f"Redirect location: {response.headers.get('Location', 'Not specified')}")
        elif response.status_code == 401:
            print("✗ Authentication required - you need to be logged in")
        elif response.status_code == 403:
            print("✗ Access forbidden - insufficient permissions")
        elif response.status_code == 404:
            print("✗ Route not found")
        elif response.status_code == 500:
            print("✗ Server error")
            print(f"Response text: {response.text[:500]}")
        else:
            print(f"? Unexpected status code: {response.status_code}")
            print(f"Response text: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out - server may be hanging")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
    
    return True

def test_data_cleanup_import():
    """Test if DataCleanupManager can be imported and used"""
    print("\nTesting DataCleanupManager import...")
    print("=" * 50)
    
    try:
        from data_cleanup import DataCleanupManager
        print("✓ DataCleanupManager imported successfully")
        
        from app.core.database.core.database_manager import DatabaseManager
        config = Config()
        db_manager = DatabaseManager(config)
        
        cleanup_manager = DataCleanupManager(db_manager, config)
        print("✓ DataCleanupManager created successfully")
        
        # Test a simple dry run
        count = cleanup_manager.archive_old_processing_runs(days=90, dry_run=True)
        print(f"✓ Test cleanup returned: {count} items would be archived")
        
        return True
        
    except Exception as e:
        print(f"✗ Error with DataCleanupManager: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Main test function"""
    print("Vedfolnir Cleanup Route Test")
    print("=" * 50)
    
    # Test 1: DataCleanupManager functionality
    cleanup_works = test_data_cleanup_import()
    
    # Test 2: Web routes (only if server is running)
    routes_work = test_cleanup_routes()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"DataCleanupManager: {'✓ Working' if cleanup_works else '✗ Failed'}")
    print(f"Web Routes: {'✓ Accessible' if routes_work else '✗ Failed'}")
    
    if cleanup_works and not routes_work:
        print("\nThe cleanup functionality works, but web routes have issues.")
        print("This suggests an authentication, routing, or web framework problem.")
    elif not cleanup_works:
        print("\nThe cleanup functionality itself has issues.")
        print("This suggests a database or import problem.")
    
    print("\nTo run this test:")
    print("1. Make sure the web app is running: python web_app.py")
    print("2. Run this test: python test_cleanup_routes.py")

if __name__ == "__main__":
    main()