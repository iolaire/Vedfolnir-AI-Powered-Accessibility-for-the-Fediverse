# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for complete user registration and verification workflow
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from config import Config
from database import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.user_management_service import UserRegistrationService, UserAuthenticationService
from services.email_service import EmailService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


class TestUserRegistrationWorkflow(MySQLIntegrationTestBase):
    """Test complete user registration and verification workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = self.get_database_manager()
        
        # Initialize services
        with self.db_manager.get_session() as db_session:
            self.registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            self.auth_service = UserAuthenticationService(db_session=db_session)
        
        self.test_users_to_cleanup = []
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up any test users created during tests
        for user_helper in self.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass  # Ignore cleanup errors
    
    @patch('services.email_service.email_service.send_verification_email')
    def test_complete_registration_workflow(self, mock_send_email):
        """Test complete user registration workflow from start to login"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Step 1: Register new user
            success, message, user = registration_service.register_user(
                username="integrationtest",
                email="integration@test.com",
                password="testpass123",
                role=UserRole.VIEWER,
                first_name="Integration",
                last_name="Test",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "User registered successfully")
            self.assertIsNotNone(user)
            self.assertEqual(user.username, "integrationtest")
            self.assertEqual(user.email, "integration@test.com")
            self.assertFalse(user.email_verified)  # Should require verification
            self.assertIsNotNone(user.email_verification_token)
            
            # Step 2: Send verification email
            email_success, email_message = asyncio.run(
                registration_service.send_verification_email(user)
            )
            
            self.assertTrue(email_success)
            self.assertEqual(email_message, "Verification email sent successfully")
            mock_send_email.assert_called_once()
            
            # Step 3: Attempt login before verification (should fail)
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="integrationtest",
                password="testpass123",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(auth_success)
            self.assertIn("not verified", auth_message)
            self.assertIsNone(auth_user)
            
            # Step 4: Verify email
            token = user.email_verification_token
            verify_success, verify_message, verified_user = registration_service.verify_email(
                token=token,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(verify_success)
            self.assertEqual(verify_message, "Email verified successfully")
            self.assertIsNotNone(verified_user)
            self.assertTrue(verified_user.email_verified)
            self.assertIsNone(verified_user.email_verification_token)
            
            # Step 5: Login after verification (should succeed)
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="integrationtest",
                password="testpass123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(auth_success)
            self.assertEqual(auth_message, "Login successful")
            self.assertIsNotNone(auth_user)
            self.assertEqual(auth_user.username, "integrationtest")
            
            # Step 6: Verify audit trail was created
            audit_logs = db_session.query(UserAuditLog).filter_by(user_id=user.id).all()
            self.assertGreater(len(audit_logs), 0)
            
            # Should have logs for registration, email verification, and login
            actions = [log.action for log in audit_logs]
            self.assertIn("user_registered", actions)
            self.assertIn("email_verified", actions)
            self.assertIn("user_login_success", actions)
    
    @patch('services.email_service.email_service.send_verification_email')
    def test_registration_with_duplicate_username(self, mock_send_email):
        """Test registration workflow with duplicate username"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create first user
            success1, message1, user1 = registration_service.register_user(
                username="duplicatetest",
                email="first@test.com",
                password="testpass123",
                role=UserRole.VIEWER
            )
            
            self.assertTrue(success1)
            self.assertIsNotNone(user1)
            
            # Attempt to create second user with same username
            success2, message2, user2 = registration_service.register_user(
                username="duplicatetest",  # Same username
                email="second@test.com",  # Different email
                password="testpass123",
                role=UserRole.VIEWER
            )
            
            self.assertFalse(success2)
            self.assertIn("already taken", message2)
            self.assertIsNone(user2)
    
    @patch('services.email_service.email_service.send_verification_email')
    def test_registration_with_duplicate_email(self, mock_send_email):
        """Test registration workflow with duplicate email"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create first user
            success1, message1, user1 = registration_service.register_user(
                username="emailtest1",
                email="duplicate@test.com",
                password="testpass123",
                role=UserRole.VIEWER
            )
            
            self.assertTrue(success1)
            self.assertIsNotNone(user1)
            
            # Attempt to create second user with same email
            success2, message2, user2 = registration_service.register_user(
                username="emailtest2",  # Different username
                email="duplicate@test.com",  # Same email
                password="testpass123",
                role=UserRole.VIEWER
            )
            
            self.assertFalse(success2)
            self.assertIn("already registered", message2)
            self.assertIsNone(user2)
    
    def test_email_verification_token_expiration(self):
        """Test email verification with expired token"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create user
            success, message, user = registration_service.register_user(
                username="expiredtest",
                email="expired@test.com",
                password="testpass123",
                role=UserRole.VIEWER,
                require_email_verification=True
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(user)
            
            # Get the token and manually expire it
            token = user.email_verification_token
            user.email_verification_sent_at = datetime.utcnow() - timedelta(hours=25)  # Expired
            db_session.commit()
            
            # Attempt verification with expired token
            verify_success, verify_message, verified_user = registration_service.verify_email(
                token=token,
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(verify_success)
            self.assertIn("expired", verify_message)
            self.assertIsNone(verified_user)
    
    @patch('services.email_service.email_service.send_verification_email')
    def test_resend_verification_email_workflow(self, mock_send_email):
        """Test resending verification email workflow"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create user
            success, message, user = registration_service.register_user(
                username="resendtest",
                email="resend@test.com",
                password="testpass123",
                role=UserRole.VIEWER
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(user)
            
            # Send initial verification email
            email_success1, email_message1 = asyncio.run(
                registration_service.send_verification_email(user)
            )
            self.assertTrue(email_success1)
            
            # Resend verification email
            resend_success, resend_message = asyncio.run(
                registration_service.resend_verification_email(
                    user_id=user.id,
                    ip_address="127.0.0.1"
                )
            )
            
            self.assertTrue(resend_success)
            self.assertIn("sent successfully", resend_message)
            
            # Should have been called twice (initial + resend)
            self.assertEqual(mock_send_email.call_count, 2)
    
    def test_resend_verification_email_rate_limiting(self):
        """Test rate limiting for resending verification emails"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create user
            success, message, user = registration_service.register_user(
                username="ratelimittest",
                email="ratelimit@test.com",
                password="testpass123",
                role=UserRole.VIEWER
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(user)
            
            # Set recent email sent timestamp
            user.email_verification_sent_at = datetime.utcnow() - timedelta(minutes=2)  # 2 minutes ago
            db_session.commit()
            
            # Attempt to resend too soon (should be rate limited)
            resend_success, resend_message = asyncio.run(
                registration_service.resend_verification_email(
                    user_id=user.id,
                    ip_address="127.0.0.1"
                )
            )
            
            self.assertFalse(resend_success)
            self.assertIn("wait", resend_message)
            self.assertIn("minutes", resend_message)
    
    def test_login_with_email_address(self):
        """Test login using email address instead of username"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create and verify user
            success, message, user = registration_service.register_user(
                username="emaillogintest",
                email="emaillogin@test.com",
                password="testpass123",
                role=UserRole.VIEWER,
                require_email_verification=False  # Skip verification for this test
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(user)
            
            # Login with email address
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="emaillogin@test.com",  # Using email
                password="testpass123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(auth_success)
            self.assertEqual(auth_message, "Login successful")
            self.assertIsNotNone(auth_user)
            self.assertEqual(auth_user.username, "emaillogintest")
    
    def test_failed_login_attempts_and_lockout(self):
        """Test failed login attempts and account lockout"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create and verify user
            success, message, user = registration_service.register_user(
                username="lockouttest",
                email="lockout@test.com",
                password="testpass123",
                role=UserRole.VIEWER,
                require_email_verification=False
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(user)
            
            # Make multiple failed login attempts
            for i in range(5):  # Max attempts before lockout
                auth_success, auth_message, auth_user = auth_service.authenticate_user(
                    username_or_email="lockouttest",
                    password="wrongpassword",
                    ip_address="127.0.0.1"
                )
                
                self.assertFalse(auth_success)
                self.assertIsNone(auth_user)
                
                if i < 4:  # Not locked yet
                    self.assertIn("Invalid password", auth_message)
                    self.assertIn("attempts remaining", auth_message)
                else:  # Should be locked now
                    self.assertIn("locked", auth_message)
            
            # Verify user is locked
            db_session.refresh(user)
            self.assertTrue(user.account_locked)
            self.assertEqual(user.failed_login_attempts, 5)
            
            # Attempt login with correct password (should still fail due to lockout)
            auth_success, auth_message, auth_user = auth_service.authenticate_user(
                username_or_email="lockouttest",
                password="testpass123",  # Correct password
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(auth_success)
            self.assertIn("locked", auth_message)
            self.assertIsNone(auth_user)

if __name__ == '__main__':
    unittest.main()