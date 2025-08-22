# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for password management functionality
"""

import unittest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from config import Config
from database import DatabaseManager
from models import User, UserRole
from services.user_management_service import PasswordManagementService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestPasswordManagementService(unittest.TestCase):
    """Test password management service functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_password_user",
            role=UserRole.VIEWER
        )
        
        # Initialize password service
        with self.db_manager.get_session() as db_session:
            self.password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
    
    def test_password_reset_token_generation(self):
        """Test password reset token generation"""
        with self.db_manager.get_session() as db_session:
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            
            # Generate reset token
            token = user.generate_password_reset_token()
            
            self.assertIsNotNone(token)
            self.assertGreater(len(token), 32)  # URL-safe base64 encoded token is longer than 32 chars
            self.assertEqual(user.password_reset_token, token)
            self.assertIsNotNone(user.password_reset_sent_at)
    
    def test_password_reset_token_verification(self):
        """Test password reset token verification"""
        with self.db_manager.get_session() as db_session:
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            
            # Generate and verify token
            token = user.generate_password_reset_token()
            db_session.commit()
            
            # Valid token should verify
            self.assertTrue(user.verify_password_reset_token(token))
            
            # Invalid token should not verify
            self.assertFalse(user.verify_password_reset_token("invalid_token"))
            
            # Expired token should not verify
            user.password_reset_sent_at = datetime.utcnow() - timedelta(hours=2)
            db_session.commit()
            self.assertFalse(user.verify_password_reset_token(token))
    
    @patch('services.email_service.email_service.send_password_reset_email')
    def test_initiate_password_reset(self, mock_send_email):
        """Test password reset initiation"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Test with valid email
            result = asyncio.run(password_service.initiate_password_reset(
                email=self.test_user.email,
                ip_address="127.0.0.1"
            ))
            
            success, message = result
            self.assertTrue(success)
            self.assertIn("password reset link has been sent", message)
            
            # Verify token was generated
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            self.assertIsNotNone(user.password_reset_token)
    
    @patch('services.email_service.email_service.send_password_reset_email')
    def test_initiate_password_reset_nonexistent_email(self, mock_send_email):
        """Test password reset with non-existent email"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Test with non-existent email (should still return success for security)
            result = asyncio.run(password_service.initiate_password_reset(
                email="nonexistent@test.com",
                ip_address="127.0.0.1"
            ))
            
            success, message = result
            self.assertTrue(success)
            self.assertIn("password reset link has been sent", message)
    
    def test_verify_reset_token_service(self):
        """Test reset token verification through service"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            token = user.generate_password_reset_token()
            db_session.commit()
            
            # Valid token
            valid, message, returned_user = password_service.verify_reset_token(token)
            self.assertTrue(valid)
            self.assertEqual(message, "Reset token is valid")
            self.assertEqual(returned_user.id, user.id)
            
            # Invalid token
            valid, message, returned_user = password_service.verify_reset_token("invalid")
            self.assertFalse(valid)
            self.assertEqual(message, "Invalid or expired reset token")
            self.assertIsNone(returned_user)
    
    def test_reset_password_service(self):
        """Test password reset through service"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            old_password_hash = user.password_hash
            token = user.generate_password_reset_token()
            db_session.commit()
            
            # Reset password
            success, message, reset_user = password_service.reset_password(
                token=token,
                new_password="new_secure_password123",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "Password reset successfully")
            self.assertEqual(reset_user.id, user.id)
            
            # Verify password was changed
            db_session.refresh(user)
            self.assertNotEqual(user.password_hash, old_password_hash)
            self.assertTrue(user.check_password("new_secure_password123"))
            
            # Verify token was cleared
            self.assertIsNone(user.password_reset_token)
            self.assertTrue(user.password_reset_used)
    
    def test_change_password_service(self):
        """Test password change through service"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            old_password_hash = user.password_hash
            
            # Change password
            success, message = password_service.change_password(
                user_id=user.id,
                current_password="test_password_123",  # Default test password
                new_password="new_secure_password456",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "Password changed successfully")
            
            # Verify password was changed
            db_session.refresh(user)
            self.assertNotEqual(user.password_hash, old_password_hash)
            self.assertTrue(user.check_password("new_secure_password456"))
            
            # Verify failed login attempts were reset
            self.assertEqual(user.failed_login_attempts, 0)
            self.assertFalse(user.account_locked)
    
    def test_change_password_wrong_current(self):
        """Test password change with wrong current password"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Try to change with wrong current password
            success, message = password_service.change_password(
                user_id=self.test_user.id,
                current_password="wrong_password",
                new_password="new_secure_password456",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(success)
            self.assertEqual(message, "Current password is incorrect")
    
    def test_cleanup_expired_reset_tokens(self):
        """Test cleanup of expired reset tokens"""
        with self.db_manager.get_session() as db_session:
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            user = db_session.query(User).filter_by(id=self.test_user.id).first()
            
            # Generate token and make it expired
            token = user.generate_password_reset_token()
            user.password_reset_sent_at = datetime.utcnow() - timedelta(hours=2)
            db_session.commit()
            
            # Cleanup expired tokens
            count = password_service.cleanup_expired_reset_tokens()
            
            self.assertEqual(count, 1)
            
            # Verify token was cleared
            db_session.refresh(user)
            self.assertIsNone(user.password_reset_token)
            self.assertIsNone(user.password_reset_sent_at)
            self.assertFalse(user.password_reset_used)

if __name__ == '__main__':
    unittest.main()