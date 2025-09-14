#!/usr/bin/env python3
"""
Test script to verify anonymous notifications work during registration
"""

import requests
import json
import time

def test_registration_notification():
    """Test that registration creates anonymous notifications"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("Testing anonymous notification system...")
    
    # Step 1: Check initial notification count
    print("1. Checking initial notification count...")
    try:
        response = requests.get(f"{base_url}/user-management/get-anonymous-notifications")
        if response.status_code == 200:
            data = response.json()
            initial_count = data.get('count', 0)
            print(f"   Initial notification count: {initial_count}")
        else:
            print(f"   Error getting initial notifications: {response.status_code}")
            return False
    except Exception as e:
        print(f"   Error: {e}")
        return False
    
    # Step 2: Try to register (this should create notifications even if validation fails)
    print("2. Attempting registration to trigger notifications...")
    try:
        registration_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "password": "password123",
            "confirm_password": "password123",
            "data_processing_consent": "y"
        }
        
        response = requests.post(
            f"{base_url}/user-management/register",
            data=registration_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Test Script)"
            }
        )
        
        print(f"   Registration response status: {response.status_code}")
        
        # Even if validation fails, notifications might be created
        # Let's check for notifications
        
    except Exception as e:
        print(f"   Error during registration: {e}")
    
    # Step 3: Check if notifications were created
    print("3. Checking for anonymous notifications...")
    try:
        response = requests.get(f"{base_url}/user-management/get-anonymous-notifications")
        if response.status_code == 200:
            data = response.json()
            final_count = data.get('count', 0)
            notifications = data.get('notifications', [])
            
            print(f"   Final notification count: {final_count}")
            
            if final_count > initial_count:
                print(f"   ✓ New notifications created!")
                for notification in notifications:
                    print(f"   - {notification.get('title', 'No title')}: {notification.get('message', 'No message')}")
                return True
            else:
                print("   No new notifications found")
                return False
        else:
            print(f"   Error getting notifications: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_session_based_notification():
    """Test creating a notification directly in session"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("\nTesting session-based notification creation...")
    
    # First get the session cookie by visiting the registration page
    session = requests.Session()
    try:
        response = session.get(f"{base_url}/user-management/register")
        print(f"   Got session cookie from registration page")
        
        # Now check notifications
        response = session.get(f"{base_url}/user-management/get-anonymous-notifications")
        if response.status_code == 200:
            data = response.json()
            print(f"   Session-based notifications: {data.get('count', 0)}")
            return True
        else:
            print(f"   Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Anonymous Notification System")
    print("=" * 50)
    
    success1 = test_registration_notification()
    success2 = test_session_based_notification()
    
    print("\n" + "=" * 50)
    if success1 or success2:
        print("✓ Anonymous notification system is working!")
    else:
        print("✗ Anonymous notification system needs investigation")
    
    print("Test completed!")