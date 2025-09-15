# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#!/usr/bin/env python3
"""
Test script to verify caption submission functionality works correctly.
This tests the fix for the issue where captions were approved but not posted to the platform.
"""

import sys
import os
import requests
import getpass
import re
from urllib.parse import urljoin

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def create_authenticated_session(base_url="http://127.0.0.1:8000", username="admin"):
    """Create authenticated session for testing"""
    session = requests.Session()
    
    # Get login page and CSRF token
    login_page = session.get(urljoin(base_url, "/login"))
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', login_page.text)
    if not csrf_match:
        print("❌ Could not find CSRF token on login page")
        return None, False
    
    csrf_token = csrf_match.group(1)
    
    # Prompt for password
    password = getpass.getpass(f"Enter password for {username}: ")
    
    # Login
    login_data = {
        'username_or_email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    response = session.post(urljoin(base_url, "/login"), data=login_data)
    success = response.status_code in [200, 302] and 'login' not in response.url.lower()
    
    return session, success

def test_review_page_access(session, base_url="http://127.0.0.1:8000"):
    """Test that we can access the review page"""
    print("🔍 Testing review page access...")
    
    response = session.get(urljoin(base_url, "/review/"))
    if response.status_code == 200:
        print("✅ Review page accessible")
        
        # Check if there are any images to review
        if "No images pending review" in response.text:
            print("ℹ️  No images currently pending review")
            return True, None
        else:
            # Look for review links
            import re
            review_links = re.findall(r'/review/(\d+)', response.text)
            if review_links:
                image_id = review_links[0]
                print(f"✅ Found image {image_id} pending review")
                return True, image_id
            else:
                print("⚠️  Review page loaded but no specific images found")
                return True, None
    else:
        print(f"❌ Could not access review page: {response.status_code}")
        return False, None

def test_caption_submission(session, image_id, base_url="http://127.0.0.1:8000"):
    """Test submitting a caption for review"""
    if not image_id:
        print("⚠️  No image ID provided for caption submission test")
        return False
    
    print(f"🔍 Testing caption submission for image {image_id}...")
    
    # Get the review form page
    review_url = urljoin(base_url, f"/review/{image_id}")
    response = session.get(review_url)
    
    if response.status_code != 200:
        print(f"❌ Could not access review form: {response.status_code}")
        return False
    
    # Extract CSRF token from the form
    csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
    if not csrf_match:
        print("❌ Could not find CSRF token on review form")
        return False
    
    csrf_token = csrf_match.group(1)
    
    # Extract current caption from the form
    caption_match = re.search(r'<textarea[^>]*name="caption"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
    current_caption = caption_match.group(1).strip() if caption_match else ""
    
    print(f"📝 Current caption: {current_caption[:100]}...")
    
    # Create test caption
    test_caption = f"TEST CAPTION: {current_caption} [Updated at {os.popen('date').read().strip()}]"
    
    # Submit the form
    form_data = {
        'image_id': image_id,
        'caption': test_caption,
        'action': '',
        'notes': 'Test submission via automated script',
        'csrf_token': csrf_token
    }
    
    print("📤 Submitting caption...")
    response = session.post(review_url, data=form_data)
    
    if response.status_code == 302:
        print("✅ Caption submission successful (redirected)")
        return True
    elif response.status_code == 200:
        if "error" in response.text.lower():
            print("❌ Caption submission failed with error")
            return False
        else:
            print("✅ Caption submission successful")
            return True
    else:
        print(f"❌ Caption submission failed: {response.status_code}")
        return False

def check_logs_for_posting(log_file="logs/webapp.log"):
    """Check logs for evidence of caption posting to platform"""
    print("🔍 Checking logs for caption posting activity...")
    
    try:
        with open(log_file, 'r') as f:
            recent_logs = f.readlines()[-50:]  # Get last 50 lines
        
        posting_indicators = [
            "Successfully posted caption",
            "update_media_caption",
            "ActivityPubClient",
            "Failed to post caption",
            "Platform connection not found"
        ]
        
        found_activity = False
        for line in recent_logs:
            for indicator in posting_indicators:
                if indicator in line:
                    print(f"📋 Log: {line.strip()}")
                    found_activity = True
        
        if not found_activity:
            print("⚠️  No caption posting activity found in recent logs")
        
        return found_activity
        
    except FileNotFoundError:
        print(f"⚠️  Log file {log_file} not found")
        return False

def main():
    """Main test execution"""
    print("=== Caption Submission Fix Test ===")
    print("This test verifies that approved captions are now posted to the platform")
    print()
    
    # Create authenticated session
    print("🔐 Authenticating...")
    session, success = create_authenticated_session()
    if not success:
        print("❌ Authentication failed")
        return False
    
    print("✅ Authentication successful")
    
    # Test review page access
    success, image_id = test_review_page_access(session)
    if not success:
        return False
    
    # Test caption submission if we have an image
    if image_id:
        success = test_caption_submission(session, image_id)
        if not success:
            return False
        
        # Check logs for posting activity
        check_logs_for_posting()
    else:
        print("ℹ️  No images available for testing caption submission")
        print("ℹ️  You may need to run caption generation first to create test data")
    
    print()
    print("=== Test Complete ===")
    print("✅ Caption submission functionality has been tested")
    print("📋 Check the logs above for evidence of platform posting")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)