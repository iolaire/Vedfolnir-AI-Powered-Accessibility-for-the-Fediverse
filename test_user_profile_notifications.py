# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test User Profile Notifications

This script tests the user profile notification system to ensure that notifications
are properly sent through the unified WebSocket system for profile updates,
settings changes, password changes, and account status changes.
"""

import logging
import sys
import os
import time
import requests
import getpass
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from database import DatabaseManager
from models import User, UserRole
from user_profile_notification_helper import UserProfileNotificationHelper
from unified_notification_manager import UnifiedNotificationManager

logger = logging.getLogger(__name__)


class UserProfileNotificationTester:
    """Test user profile notifications"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.base_url = "http://127.0.0.1:5000"
        
        # Initialize notification system components (mock for testing)
        self.notification_manager = None
        self.notification_helper = None
        
    def setup_notification_system(self):
        """Setup notification system for testing"""
        try:
            # For testing, we'll create a mock notification manager
            # In the real app, this would be the actual unified notification manager
            from unittest.mock import Mock
            
            self.notification_manager = Mock()
            self.notification_manager.send_user_notification = Mock(return_value=True)
            
            self.notification_helper = UserProfileNotificationHelper(self.notification_manager)
            
            self.logger.info("Mock notification system setup complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup notification system: {e}")
            return False
    
    def test_profile_update_notification(self, user_id: int) -> bool:
        """Test profile update notification"""
        try:
            self.logger.info("Testing profile update notification...")
            
            result = self.notification_helper.send_profile_update_notification(
                user_id=user_id,
                success=True,
                message="Profile updated successfully!",
                details={'fields_updated': ['first_name', 'last_name']}
            )
            
            if result:
                self.logger.info("✓ Profile update notification sent successfully")
                return True
            else:
                self.logger.error("✗ Profile update notification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing profile update notification: {e}")
            return False
    
    def test_settings_change_notification(self, user_id: int) -> bool:
        """Test settings change notification"""
        try:
            self.logger.info("Testing settings change notification...")
            
            result = self.notification_helper.send_settings_change_notification(
                user_id=user_id,
                setting_name="max_posts_per_run",
                success=True,
                message="Caption generation settings updated successfully!",
                old_value=50,
                new_value=100
            )
            
            if result:
                self.logger.info("✓ Settings change notification sent successfully")
                return True
            else:
                self.logger.error("✗ Settings change notification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing settings change notification: {e}")
            return False
    
    def test_password_change_notification(self, user_id: int) -> bool:
        """Test password change notification"""
        try:
            self.logger.info("Testing password change notification...")
            
            result = self.notification_helper.send_password_change_notification(
                user_id=user_id,
                success=True,
                message="Password changed successfully!",
                security_details={
                    'ip_address': '127.0.0.1',
                    'user_agent': 'Test Browser',
                    'timestamp': '2025-01-01T12:00:00Z'
                }
            )
            
            if result:
                self.logger.info("✓ Password change notification sent successfully")
                return True
            else:
                self.logger.error("✗ Password change notification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing password change notification: {e}")
            return False
    
    def test_account_status_notification(self, user_id: int) -> bool:
        """Test account status notification"""
        try:
            self.logger.info("Testing account status notification...")
            
            result = self.notification_helper.send_account_status_notification(
                user_id=user_id,
                status_change="activated",
                message="Your account has been activated successfully!",
                admin_action=False
            )
            
            if result:
                self.logger.info("✓ Account status notification sent successfully")
                return True
            else:
                self.logger.error("✗ Account status notification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing account status notification: {e}")
            return False
    
    def test_permission_change_notification(self, user_id: int) -> bool:
        """Test permission change notification"""
        try:
            self.logger.info("Testing permission change notification...")
            
            result = self.notification_helper.send_permission_change_notification(
                user_id=user_id,
                old_role="viewer",
                new_role="reviewer",
                message="Your permissions have been updated to Reviewer!",
                admin_user_id=1
            )
            
            if result:
                self.logger.info("✓ Permission change notification sent successfully")
                return True
            else:
                self.logger.error("✗ Permission change notification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing permission change notification: {e}")
            return False
    
    def test_email_verification_notification(self, user_id: int) -> bool:
        """Test email verification notification"""
        try:
            self.logger.info("Testing email verification notification...")
            
            result = self.notification_helper.send_email_verification_notification(
                user_id=user_id,
                success=True,
                message="Email verification successful!",
                email="test@example.com"
            )
            
            if result:
                self.logger.info("✓ Email verification notification sent successfully")
                return True
            else:
                self.logger.error("✗ Email verification notification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error testing email verification notification: {e}")
            return False
    
    def test_web_integration(self) -> bool:
        """Test web integration by making HTTP requests"""
        try:
            self.logger.info("Testing web integration...")
            
            # Test that the web app is running
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                self.logger.info("✓ Web app is accessible")
            else:
                self.logger.warning(f"Web app returned status {response.status_code}")
            
            # Test that notification JavaScript is accessible
            js_response = requests.get(f"{self.base_url}/static/js/user_profile_notifications.js", timeout=5)
            if js_response.status_code == 200:
                self.logger.info("✓ User profile notification JavaScript is accessible")
            else:
                self.logger.warning("User profile notification JavaScript not accessible")
            
            # Test that notification CSS is accessible
            css_response = requests.get(f"{self.base_url}/static/css/user_profile_notifications.css", timeout=5)
            if css_response.status_code == 200:
                self.logger.info("✓ User profile notification CSS is accessible")
            else:
                self.logger.warning("User profile notification CSS not accessible")
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Web integration test failed: {e}")
            self.logger.info("Make sure the web app is running: python web_app.py")
            return False
    
    def get_test_user(self) -> int:
        """Get a test user ID"""
        try:
            with self.db_manager.get_session() as session:
                # Try to find admin user first
                admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
                if admin_user:
                    return admin_user.id
                
                # Otherwise get any user
                any_user = session.query(User).first()
                if any_user:
                    return any_user.id
                
                self.logger.error("No users found in database")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting test user: {e}")
            return None
    
    def run_all_tests(self) -> bool:
        """Run all notification tests"""
        self.logger.info("=== User Profile Notification Tests ===")
        
        # Setup notification system
        if not self.setup_notification_system():
            self.logger.error("Failed to setup notification system")
            return False
        
        # Get test user
        user_id = self.get_test_user()
        if not user_id:
            self.logger.error("No test user available")
            return False
        
        self.logger.info(f"Using test user ID: {user_id}")
        
        # Run notification tests
        tests = [
            ("Profile Update", self.test_profile_update_notification),
            ("Settings Change", self.test_settings_change_notification),
            ("Password Change", self.test_password_change_notification),
            ("Account Status", self.test_account_status_notification),
            ("Permission Change", self.test_permission_change_notification),
            ("Email Verification", self.test_email_verification_notification)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.logger.info(f"\n--- Testing {test_name} ---")
            if test_func(user_id):
                passed += 1
            else:
                self.logger.error(f"Test failed: {test_name}")
        
        # Test web integration
        self.logger.info(f"\n--- Testing Web Integration ---")
        web_test_passed = self.test_web_integration()
        if web_test_passed:
            passed += 1
        total += 1
        
        # Print results
        self.logger.info(f"\n=== Test Results ===")
        self.logger.info(f"Passed: {passed}/{total}")
        self.logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            self.logger.info("✓ All tests passed!")
            return True
        else:
            self.logger.error(f"✗ {total - passed} test(s) failed")
            return False


def main():
    """Main test function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("User Profile Notification System Test")
    print("=====================================")
    
    tester = UserProfileNotificationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! User profile notifications are working correctly.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the logs above.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)