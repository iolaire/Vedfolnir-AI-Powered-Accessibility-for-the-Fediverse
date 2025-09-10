# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security tests for user management functionality
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.user_management_service import (
    UserRegistrationService, UserAuthenticationService, 
    PasswordManagementService, UserProfileService
)
from forms.user_management_forms import UserRegistrationForm, LoginForm
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestUserManagementSecurity(unittest.TestCase):
    """Test security aspects of user management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        self.test_users_to_cleanup = []
    
    def tearDown(self):
        """Clean up test fixtures"""
        for user_helper in self.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass
    
    def test_password_hashing_security(self):
        """Test that passwords are properly hashed and salted"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create two users with the same password
            success1, message1, user1 = registration_service.register_user(
                username="hashtest1",
                email="hashtest1@test.com",
                password="samepassword123",
                role=UserRole.VIEWER
            )
            
            success2, message2, user2 = registration_service.register_user(
                username="hashtest2",
                email="hashtest2@test.com",
                password="samepassword123",
                role=UserRole.VIEWER
            )
            
            self.assertTrue(success1)
            self.assertTrue(success2)
            
            # Password hashes should be different (due to salt)
            self.assertNotEqual(user1.password_hash, user2.password_hash)
            
            # Both should verify correctly
            self.assertTrue(user1.check_password("samepassword123"))
            self.assertTrue(user2.check_password("samepassword123"))
            
            # Neither should contain the plain password
            self.assertNotIn("samepassword123", user1.password_hash)
            self.assertNotIn("samepassword123", user2.password_hash)
    
    def test_authentication_timing_attack_protection(self):
        """Test protection against timing attacks in authentication"""
        with self.db_manager.get_session() as db_session:
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create a test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="timingtest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Time authentication with valid user, wrong password
            start_time = time.time()
            auth_service.authenticate_user(
                username_or_email="timingtest",
                password="wrongpassword",
                ip_address="127.0.0.1"
            )
            valid_user_time = time.time() - start_time
            
            # Time authentication with invalid user
            start_time = time.time()
            auth_service.authenticate_user(
                username_or_email="nonexistentuser",
                password="anypassword",
                ip_address="127.0.0.1"
            )
            invalid_user_time = time.time() - start_time
            
            # Times should be similar (within reasonable bounds)
            # This is a basic check - in production, more sophisticated timing analysis would be needed
            time_difference = abs(valid_user_time - invalid_user_time)
            self.assertLess(time_difference, 0.1)  # Less than 100ms difference
    
    def test_account_lockout_security(self):
        """Test account lockout mechanism for brute force protection"""
        with self.db_manager.get_session() as db_session:
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create a test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="lockouttest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Make multiple failed login attempts
            for i in range(5):  # Max attempts before lockout
                success, message, user = auth_service.authenticate_user(
                    username_or_email="lockouttest",
                    password="wrongpassword",
                    ip_address="127.0.0.1"
                )
                
                self.assertFalse(success)
                
                if i < 4:  # Not locked yet
                    self.assertIn("Invalid password", message)
                    self.assertIn("attempts remaining", message)
                else:  # Should be locked now
                    self.assertIn("locked", message)
            
            # Verify account is locked
            db_session.refresh(test_user)
            self.assertTrue(test_user.account_locked)
            
            # Even correct password should fail when locked
            success, message, user = auth_service.authenticate_user(
                username_or_email="lockouttest",
                password="test_password_123",  # Correct password
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(success)
            self.assertIn("locked", message)
    
    def test_password_reset_token_security(self):
        """Test security of password reset tokens"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="tokentest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Generate multiple reset tokens
            tokens = []
            for i in range(5):
                token = test_user.generate_password_reset_token()
                tokens.append(token)
                db_session.commit()
            
            # All tokens should be different
            self.assertEqual(len(set(tokens)), 5)
            
            # Tokens should be sufficiently long (cryptographically secure)
            for token in tokens:
                self.assertGreaterEqual(len(token), 32)
                # Should not contain predictable patterns
                self.assertNotIn("000", token)
                self.assertNotIn("111", token)
                self.assertNotIn("aaa", token)
            
            # Token should expire after time limit
            token = test_user.generate_password_reset_token()
            test_user.password_reset_sent_at = datetime.utcnow() - timedelta(hours=2)  # Expired
            db_session.commit()
            
            self.assertFalse(test_user.verify_password_reset_token(token))
    
    def test_email_verification_token_security(self):
        """Test security of email verification tokens"""
        with self.db_manager.get_session() as db_session:
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="emailtokentest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Generate multiple verification tokens
            tokens = []
            for i in range(5):
                token = test_user.generate_email_verification_token()
                tokens.append(token)
                db_session.commit()
            
            # All tokens should be different
            self.assertEqual(len(set(tokens)), 5)
            
            # Tokens should be sufficiently long
            for token in tokens:
                self.assertGreaterEqual(len(token), 32)
            
            # Token should expire after time limit
            token = test_user.generate_email_verification_token()
            test_user.email_verification_sent_at = datetime.utcnow() - timedelta(hours=25)  # Expired
            db_session.commit()
            
            self.assertFalse(test_user.verify_email_token(token))
    
    def test_input_validation_security(self):
        """Test input validation for security vulnerabilities"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Test SQL injection attempts in username
            malicious_usernames = [
                "'; DROP TABLE users; --",
                "admin' OR '1'='1",
                "user<script>alert('xss')</script>",
                "user\x00null",
                "user\r\nheader_injection"
            ]
            
            for malicious_username in malicious_usernames:
                success, message, user = registration_service.register_user(
                    username=malicious_username,
                    email="test@test.com",
                    password="password123",
                    role=UserRole.VIEWER
                )
                
                # Should either fail validation or sanitize input
                if success:
                    # If it succeeds, username should be sanitized
                    self.assertNotEqual(user.username, malicious_username)
                else:
                    # Should fail with appropriate error message
                    self.assertIn("invalid", message.lower())
            
            # Test email injection attempts
            malicious_emails = [
                "test@test.com\r\nBcc: attacker@evil.com",
                "test+<script>@test.com",
                "test@test.com\x00null"
            ]
            
            for malicious_email in malicious_emails:
                success, message, user = registration_service.register_user(
                    username="testuser",
                    email=malicious_email,
                    password="password123",
                    role=UserRole.VIEWER
                )
                
                # Should fail validation
                self.assertFalse(success)
                self.assertIn("email", message.lower())
    
    def test_session_security(self):
        """Test session security measures"""
        with self.db_manager.get_session() as db_session:
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="sessiontest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Test that sessions are invalidated after password change
            # This would require session manager integration
            # For now, we test that the user model tracks login state correctly
            
            # Successful login
            success, message, user = auth_service.authenticate_user(
                username_or_email="sessiontest",
                password="test_password_123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            
            # Verify last login was updated
            db_session.refresh(test_user)
            self.assertIsNotNone(test_user.last_login)
            
            # Verify failed login attempts were reset
            self.assertEqual(test_user.failed_login_attempts, 0)
    
    def test_audit_logging_security(self):
        """Test that security events are properly logged"""
        with self.db_manager.get_session() as db_session:
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="audittest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Failed login attempt
            auth_service.authenticate_user(
                username_or_email="audittest",
                password="wrongpassword",
                ip_address="192.168.1.100",
                user_agent="TestBrowser/1.0"
            )
            
            # Check audit log
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="user_login_failed"
            ).all()
            
            self.assertEqual(len(audit_logs), 1)
            audit_log = audit_logs[0]
            self.assertEqual(audit_log.ip_address, "192.168.1.100")
            self.assertEqual(audit_log.user_agent, "TestBrowser/1.0")
            self.assertIn("failed", audit_log.details.lower())
            
            # Successful login attempt
            auth_service.authenticate_user(
                username_or_email="audittest",
                password="test_password_123",
                ip_address="192.168.1.100",
                user_agent="TestBrowser/1.0"
            )
            
            # Check success audit log
            success_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="user_login_success"
            ).all()
            
            self.assertEqual(len(success_logs), 1)
    
    def test_rate_limiting_security(self):
        """Test rate limiting for various operations"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="ratelimituser",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Test email verification resend rate limiting
            # First resend should work
            success1, message1 = asyncio.run(registration_service.resend_verification_email(
                user_id=test_user.id,
                ip_address="127.0.0.1"
            ))
            
            # Immediate second resend should be rate limited
            success2, message2 = asyncio.run(registration_service.resend_verification_email(
                user_id=test_user.id,
                ip_address="127.0.0.1"
            ))
            
            self.assertFalse(success2)
            self.assertIn("wait", message2.lower())
    
    def test_privilege_escalation_protection(self):
        """Test protection against privilege escalation"""
        with self.db_manager.get_session() as db_session:
            profile_service = UserProfileService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create viewer user
            viewer_user, viewer_helper = create_test_user_with_platforms(
                self.db_manager,
                username="vieweruser",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(viewer_helper)
            
            # Attempt to escalate privileges through profile update
            malicious_data = {
                'role': UserRole.ADMIN.value,  # Trying to become admin
                'is_active': True,
                'email_verified': True
            }
            
            success, message, updated_user = profile_service.update_profile(
                user_id=viewer_user.id,
                profile_data=malicious_data,
                ip_address="127.0.0.1"
            )
            
            # Should either fail or ignore role change
            if success:
                db_session.refresh(viewer_user)
                self.assertEqual(viewer_user.role, UserRole.VIEWER)  # Role should not change
            else:
                self.assertIn("not allowed", message.lower())
    
    def test_information_disclosure_protection(self):
        """Test protection against information disclosure"""
        with self.db_manager.get_session() as db_session:
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Test that error messages don't reveal sensitive information
            
            # Non-existent user
            success, message, user = auth_service.authenticate_user(
                username_or_email="nonexistentuser",
                password="anypassword",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(success)
            # Should not reveal whether user exists
            self.assertNotIn("not found", message.lower())
            self.assertNotIn("does not exist", message.lower())
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="infotest",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Wrong password
            success, message, user = auth_service.authenticate_user(
                username_or_email="infotest",
                password="wrongpassword",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(success)
            # Should not reveal specific reason for failure
            self.assertIn("Invalid", message)
            self.assertNotIn("password_hash", message.lower())
            self.assertNotIn("database", message.lower())
    
    def test_csrf_protection_forms(self):
        """Test CSRF protection in forms"""
        from flask import Flask
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = True
        
        with app.app_context():
            # Registration form should have CSRF protection
            form = UserRegistrationForm()
            self.assertTrue(hasattr(form, 'csrf_token'))
            
            # Login form should have CSRF protection
            login_form = LoginForm()
            self.assertTrue(hasattr(login_form, 'csrf_token'))
    
    def test_data_sanitization(self):
        """Test that user data is properly sanitized"""
        with self.db_manager.get_session() as db_session:
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Test with potentially dangerous input
            success, message, user = registration_service.register_user(
                username="testuser",
                email="test@test.com",
                password="password123",
                role=UserRole.VIEWER,
                first_name="<script>alert('xss')</script>",
                last_name="'; DROP TABLE users; --"
            )
            
            if success:
                # Data should be sanitized
                self.assertNotIn("<script>", user.first_name or "")
                self.assertNotIn("DROP TABLE", user.last_name or "")
                self.assertNotIn("alert", user.first_name or "")

if __name__ == '__main__':
    unittest.main()