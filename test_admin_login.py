# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Quick test to find working admin credentials
"""

import requests
import re

def test_admin_login():
    """Test common admin passwords"""
    base_url = "http://127.0.0.1:5000"
    
    # Common passwords to try
    passwords = [
        'admin',
        'admin123', 
        'password',
        'test123',
        'vedfolnir',
        'abc1234',
        'admin1234',
        'password123'
    ]
    
    session = requests.Session()
    
    for password in passwords:
        try:
            # Get login page and CSRF token
            login_page = session.get(f"{base_url}/login")
            csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
            
            if not csrf_match:
                print("Could not find CSRF token")
                continue
                
            csrf_token = csrf_match.group(1)
            
            # Try login
            login_data = {
                'username_or_email': 'admin',
                'password': password,
                'csrf_token': csrf_token
            }
            
            response = session.post(f"{base_url}/login", data=login_data)
            
            # Check if login was successful
            if response.status_code in [200, 302] and 'login' not in response.url.lower():
                print(f"✅ SUCCESS: admin / {password}")
                return password
            else:
                print(f"❌ FAILED: admin / {password}")
                
        except Exception as e:
            print(f"❌ ERROR testing {password}: {e}")
    
    print("No working password found")
    return None

if __name__ == '__main__':
    test_admin_login()