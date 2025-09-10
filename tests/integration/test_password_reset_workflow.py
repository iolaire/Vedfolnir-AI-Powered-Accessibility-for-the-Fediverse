# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for password reset workflow
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.user_management_service import PasswordManagementService, UserAuthenticationService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


class TestPasswordResetWorkflow(MySQLIntegrationTestBase):
    """Test complete password reset workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = self.get_database_manager()
        
        # Create test user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="password_test_user",
            role=UserRole.VIEWER
        )
        
        self.test_users_to_cleanup = [self.user_helper]
    
    def tearDown(self):
        """Clean up test fixtures"""
        for user_helper in self.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass
    
    @patch('services.email_service.email_service.send_password_reset_email')
    def test_complete_password_reset_workflow(self, mock_send_email):
        """Test complete password reset workflow from initiation to login"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Store original password hash
            original_password_hash = self.test_user.password_hash
            
            # Step 1: Initiate password reset
            reset_success, reset_message = asyncio.run(password_service.initiate_password_reset(
                email=self.test_user.email,
                ip_address="127.0.0.1"
            ))
            
            self.assertTrue(reset_success)
            self.assertIn("password reset link has been sent", reset_message)
            mock_send_email.assert_called_once()
            
            # Verify reset token was generated
            db_session.refresh(self.test_user)
            self.assertIsNotNone(self.test_user.password_reset_token)
            self.assertIsNotNone(self.test_user.password_reset_sent_at)
            self.assertFalse(self.test_user.password_reset_used)
            
            # Step 2: Verify reset token
            token = self.test_user.password_reset_token
            verify_success, verify_message, verified_user = password_service.verify_reset_token(token)
            
            self.assertTrue(verify_success)
            self.assertEqual(verify_message, "Reset token is valid")
            self.assertIsNotNone(verified_user)
            self.assertEqual(verified_user.id, self.test_user.id)
            
            # Step 3: Reset password
            new_password = "newpassword123"
            password_success, password_message, reset_user = password_service.reset_password(
                token=token,
                new_password=new_password,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(password_success)
            self.assertEqual(password_message, "Password reset successfully")
            self.assertIsNotNone(reset_user)
            
            # Verify password was changed
            db_session.refresh(self.test_user)
            self.assertNotEqual(self.test_user.password_hash, original_password_hash)
            self.assertTrue(self.test_user.check_password(new_password))
            
            # Verify reset token was cleared
            self.assertIsNone(self.test_user.password_reset_token)
            self.assertTrue(self.test_user.password_reset_used)
            
            # Verify failed login attempts were reset
            self.assertEqual(self.test_user.failed_login_attempts, 0)
            
            # Step 4: Login with new password
            login_success, login_message, login_user = auth_service.authenticate_user(
                username_or_email=self.test_user.username,
                password=new_password,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(login_success)
            self.assertEqual(login_message, "Login successful")
            self.assertIsNotNone(login_user)
            
            # Step 5: Verify old password no longer works
            old_login_success, old_login_message, old_login_user = auth_service.authenticate_user(
                username_or_email=self.test_user.username,
                password="test_password_123",  # Original password
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(old_login_success)
            self.assertIn("Invalid password", old_login_message)
            self.assertIsNone(old_login_user)
            
            # Verify audit trail
            audit_logs = db_session.query(UserAuditLog).filter_by(user_id=self.test_user.id).all()
            actions = [log.action for log in audit_logs]
            self.assertIn("password_reset_requested", actions)
            self.assertIn("password_reset_completed", actions)
    
    @patch('services.email_service.email_service.send_password_reset_email')
    def test_password_reset_nonexistent_email(self, mock_send_email):
        """Test password reset with non-existent email (should still return success for security)"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Request reset for non-existent email
            reset_success, reset_message = asyncio.run(password_service.initiate_password_reset(
                email="nonexistent@test.com",
                ip_address="127.0.0.1"
            ))
            
            # Should still return success for security (don't reveal if email exists)
            self.assertTrue(reset_success)
            self.assertIn("password reset link has been sent", reset_message)
            
            # But no email should actually be sent
            mock_send_email.assert_not_called()
    
    def test_password_reset_token_expiration(self):
        """Test password reset with expired token"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Generate reset token and make it expired
            token = self.test_user.generate_password_reset_token()
            self.test_user.password_reset_sent_at = datetime.utcnow() - timedelta(hours=2)  # Expired
            db_session.commit()
            
            # Attempt to verify expired token
            verify_success, verify_message, verified_user = password_service.verify_reset_token(token)
            
            self.assertFalse(verify_success)
            self.assertEqual(verify_message, "Invalid or expired reset token")
            self.assertIsNone(verified_user)
            
            # Attempt to reset password with expired token
            password_success, password_message, reset_user = password_service.reset_password(
                token=token,
                new_password="newpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(password_success)
            self.assertEqual(password_message, "Invalid or expired reset token")
            self.assertIsNone(reset_user)
    
    def test_password_reset_invalid_token(self):
        """Test password reset with invalid token"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Attempt to verify invalid token
            verify_success, verify_message, verified_user = password_service.verify_reset_token("invalid_token")
            
            self.assertFalse(verify_success)
            self.assertEqual(verify_message, "Invalid or expired reset token")
            self.assertIsNone(verified_user)
            
            # Attempt to reset password with invalid token
            password_success, password_message, reset_user = password_service.reset_password(
                token="invalid_token",
                new_password="newpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(password_success)
            self.assertEqual(password_message, "Invalid or expired reset token")
            self.assertIsNone(reset_user)
    
    def test_password_reset_token_single_use(self):
        """Test that password reset tokens can only be used once"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Generate reset token
            token = self.test_user.generate_password_reset_token()
            db_session.commit()
            
            # Use token to reset password
            password_success1, password_message1, reset_user1 = password_service.reset_password(
                token=token,
                new_password="newpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(password_success1)
            self.assertEqual(password_message1, "Password reset successfully")
            
            # Attempt to use same token again
            password_success2, password_message2, reset_user2 = password_service.reset_password(
                token=token,
                new_password="anotherpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(password_success2)
            self.assertEqual(password_message2, "Invalid or expired reset token")
            self.assertIsNone(reset_user2)
            
            # Verify password wasn't changed the second time
            db_session.refresh(self.test_user)
            self.assertTrue(self.test_user.check_password("newpassword123"))
            self.assertFalse(self.test_user.check_password("anotherpassword123"))
    
    @patch('services.email_service.email_service.send_password_reset_email')
    def test_password_reset_rate_limiting(self, mock_send_email):
        """Test rate limiting for password reset requests"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # First request should succeed
            reset_success1, reset_message1 = asyncio.run(password_service.initiate_password_reset(
                email=self.test_user.email,
                ip_address="127.0.0.1"
            ))
            
            self.assertTrue(reset_success1)
            mock_send_email.assert_called_once()
            
            # Immediate second request should be rate limited
            reset_success2, reset_message2 = asyncio.run(password_service.initiate_password_reset(
                email=self.test_user.email,
                ip_address="127.0.0.1"
            ))
            
            self.assertFalse(reset_success2)
            self.assertIn("wait", reset_message2.lower())
            
            # Email should not be sent again
            self.assertEqual(mock_send_email.call_count, 1)
    
    def test_password_change_workflow(self):
        """Test authenticated user changing their own password"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            auth_service = UserAuthenticationService(db_session=db_session)
            
            # Store original password hash
            original_password_hash = self.test_user.password_hash
            
            # User changes their password
            change_success, change_message = password_service.change_password(
                user_id=self.test_user.id,
                current_password="test_password_123",  # Current password
                new_password="mynewpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(change_success)
            self.assertEqual(change_message, "Password changed successfully")
            
            # Verify password was changed
            db_session.refresh(self.test_user)
            self.assertNotEqual(self.test_user.password_hash, original_password_hash)
            self.assertTrue(self.test_user.check_password("mynewpassword123"))
            
            # Verify failed login attempts were reset
            self.assertEqual(self.test_user.failed_login_attempts, 0)
            self.assertFalse(self.test_user.account_locked)
            
            # Test login with new password
            login_success, login_message, login_user = auth_service.authenticate_user(
                username_or_email=self.test_user.username,
                password="mynewpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(login_success)
            self.assertEqual(login_message, "Login successful")
            
            # Verify audit log was created
            audit_logs = db_session.query(UserAuditLog).filter_by(
                user_id=self.test_user.id,
                action="password_changed"
            ).all()
            self.assertEqual(len(audit_logs), 1)
    
    def test_password_change_wrong_current_password(self):
        """Test password change with incorrect current password"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Store original password hash
            original_password_hash = self.test_user.password_hash
            
            # Attempt to change password with wrong current password
            change_success, change_message = password_service.change_password(
                user_id=self.test_user.id,
                current_password="wrongpassword",  # Wrong current password
                new_password="mynewpassword123",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(change_success)
            self.assertEqual(change_message, "Current password is incorrect")
            
            # Verify password was not changed
            db_session.refresh(self.test_user)
            self.assertEqual(self.test_user.password_hash, original_password_hash)
            self.assertFalse(self.test_user.check_password("mynewpassword123"))
            self.assertTrue(self.test_user.check_password("test_password_123"))
    
    def test_cleanup_expired_reset_tokens(self):
        """Test cleanup of expired password reset tokens"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create multiple users with expired reset tokens
            expired_users = []
            for i in range(3):
                user, helper = create_test_user_with_platforms(
                    self.db_manager,
                    username=f"expired_user_{i}",
                    role=UserRole.VIEWER
                )
                expired_users.append((user, helper))
                self.test_users_to_cleanup.append(helper)
                
                # Generate expired reset token
                token = user.generate_password_reset_token()
                user.password_reset_sent_at = datetime.utcnow() - timedelta(hours=2)  # Expired
                db_session.commit()
            
            # Create one user with valid reset token
            valid_user, valid_helper = create_test_user_with_platforms(
                self.db_manager,
                username="valid_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(valid_helper)
            valid_token = valid_user.generate_password_reset_token()
            db_session.commit()
            
            # Run cleanup
            cleanup_count = password_service.cleanup_expired_reset_tokens()
            
            # Should have cleaned up 3 expired tokens
            self.assertEqual(cleanup_count, 3)
            
            # Verify expired tokens were cleared
            for user, _ in expired_users:
                db_session.refresh(user)
                self.assertIsNone(user.password_reset_token)
                self.assertIsNone(user.password_reset_sent_at)
                self.assertFalse(user.password_reset_used)
            
            # Verify valid token was not cleared
            db_session.refresh(valid_user)
            self.assertIsNotNone(valid_user.password_reset_token)
            self.assertIsNotNone(valid_user.password_reset_sent_at)
            self.assertFalse(valid_user.password_reset_used)

if __name__ == '__main__':
    unittest.main()