#!/usr/bin/env python3
"""
Test registration with valid email to trigger email sending
"""

import requests
import time

def test_registration():
    """Test registration to see email template usage"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("Testing registration with valid email...")
    
    # Test registration with valid email domain
    test_data = {
        "username": f"testuser_{int(time.time())}",
        "email": f"test_{int(time.time())}@gmail.com",
        "password": "password123",
        "confirm_password": "password123",
        "data_processing_consent": "y"
    }
    
    try:
        response = requests.post(
            f"{base_url}/user-management/register",
            data=test_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Test Script)"
            }
        )
        
        print(f"Registration response status: {response.status_code}")
        
        if response.status_code == 200:
            # Check if registration was successful
            if "Registration successful" in response.text or "check your email" in response.text:
                print("✅ Registration successful - email should be sent")
            else:
                print("⚠ Registration may have failed")
                # Check for validation errors
                if "is-invalid" in response.text:
                    print("Form has validation errors")
                
            print("Looking for email-related content...")
            if "verification email" in response.text.lower():
                print("✅ Page mentions verification email")
            
        else:
            print(f"Registration failed with status {response.status_code}")
            
    except Exception as e:
        print(f"Error during registration: {e}")

if __name__ == "__main__":
    test_registration()