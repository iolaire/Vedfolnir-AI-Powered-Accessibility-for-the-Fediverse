#!/usr/bin/env python3
"""
Test registration to trigger email sending
"""

import requests
import time

def test_registration():
    """Test registration to see email template usage"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("Testing registration to check email template usage...")
    
    # Test registration with unique data
    test_data = {
        "username": f"testuser_{int(time.time())}",
        "email": f"test_{int(time.time())}@example.com",
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
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Check if registration was successful
            if "Registration successful" in response.text or "check your email" in response.text:
                print("✅ Registration appears successful")
            else:
                print("⚠ Registration may have failed or returned form with errors")
                
            # Save response for debugging
            with open('/tmp/registration_response.html', 'w') as f:
                f.write(response.text)
            print("Response saved to /tmp/registration_response.html")
        else:
            print(f"Registration failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"Error during registration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_registration()