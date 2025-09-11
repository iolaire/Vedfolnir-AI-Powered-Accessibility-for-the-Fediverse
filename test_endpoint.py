#!/usr/bin/env python3
"""
Simple test to verify anonymous notification functionality works with the actual application
"""

import requests
import json

def test_anonymous_notification_endpoint():
    """Test the anonymous notification endpoint"""
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Check if the endpoint exists and responds
    print("Test 1: Checking anonymous notification endpoint...")
    try:
        response = requests.get(f"{base_url}/user-management/get-anonymous-notifications")
        print(f"Endpoint status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
        else:
            print(f"Response text: {response.text}")
            
    except Exception as e:
        print(f"Error connecting to endpoint: {e}")
    
    # Test 2: Check if the login page loads (to verify app is running)
    print("\nTest 2: Checking if login page loads...")
    try:
        response = requests.get(f"{base_url}/user-management/login")
        print(f"Login page status code: {response.status_code}")
        if response.status_code == 200:
            print("✓ Login page loads successfully")
            # Check if the notification container is present
            if 'unified-notification-container' in response.text:
                print("✓ Notification container found in login page")
            else:
                print("⚠ Notification container not found in login page")
        else:
            print(f"✗ Login page failed to load: {response.text}")
    except Exception as e:
        print(f"✗ Error connecting to login page: {e}")
    
    # Test 3: Check if the registration page loads
    print("\nTest 3: Checking if registration page loads...")
    try:
        response = requests.get(f"{base_url}/user-management/register")
        print(f"Registration page status code: {response.status_code}")
        if response.status_code == 200:
            print("✓ Registration page loads successfully")
            # Check if the notification container is present
            if 'unified-notification-container' in response.text:
                print("✓ Notification container found in registration page")
            else:
                print("⚠ Notification container not found in registration page")
        else:
            print(f"✗ Registration page failed to load: {response.text}")
    except Exception as e:
        print(f"✗ Error connecting to registration page: {e}")

if __name__ == "__main__":
    print("Testing anonymous notification functionality...")
    test_anonymous_notification_endpoint()
    print("\nTest completed!")