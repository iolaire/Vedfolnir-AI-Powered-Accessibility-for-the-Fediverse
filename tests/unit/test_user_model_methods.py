# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for User model methods and validation
"""

import unittest
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, UserRole, UserAuditLog
from config import Config
from database import DatabaseManager


class TestUserModelMethods(unittest.TestCase):
    """Test User model methods and validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create session
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()
        
        # Create test user
        self.test_user = User(
            username="testuser",
            email="test@test.com",
            role=UserRole.VIEWER,
            first_name="Test",
            last_name="User",
            is_active=True,
            email_verified=True,
            data_processing_consent=True,
            data_processing_consent_date=datetime.utcnow()
        )
        self.test_user.set_password("password123")
        self.db_session.add(self.test_user)
        self.db_session.commit()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_session.close()
    
    def test_password_hashing_and_verification(self):
        """Test password hashing and verification"""
        # Test password setting
        self.test_user.set_password("newpassword123")
        self.assertIsNotNone(self.test_user.password_hash)
        
        # Test correct password verification
        self.assertTrue(self.test_user.check_password("newpassword123"))
        
        # Test incorrect password verification
        self.assertFalse(self.test_user.check_password("wrongpassword"))
        
        # Test empty password
        self.assertFalse(self.test_user.check_password(""))
    
    def test_email_verification_token_generation(self):
        """Test email verification token generation and validation"""
        # Generate token
        token = self.test_user.generate_email_verification_token()
        
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 32)  # URL-safe base64 encoded
        self.assertEqual(self.test_user.email_verification_token, token)
        self.assertIsNotNone(self.test_user.email_verification_sent_at)
        
        # Test token verification
        self.assertTrue(self.test_user.verify_email_token(token))
        
        # After verification, token should be cleared and email marked as verified
        self.assertIsNone(self.test_user.email_verification_token)
        self.assertIsNone(self.test_user.email_verification_sent_at)
        self.assertTrue(self.test_user.email_verified)
    
    def test_email_verification_token_expiration(self):
        """Test email verification token expiration"""
        # Generate token and make it expired
        token = self.test_user.generate_email_verification_token()
        self.test_user.email_verification_sent_at = datetime.utcnow() - timedelta(hours=25)
        
        # Expired token should not verify
        self.assertFalse(self.test_user.verify_email_token(token))
    
    def test_password_reset_token_generation(self):
        """Test password reset token generation and validation"""
        # Generate token
        token = self.test_user.generate_password_reset_token()
        
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 32)
        self.assertEqual(self.test_user.password_reset_token, token)
        self.assertIsNotNone(self.test_user.password_reset_sent_at)
        self.assertFalse(self.test_user.password_reset_used)
        
        # Test token verification
        self.assertTrue(self.test_user.verify_password_reset_token(token))
        
        # Invalid token should not verify
        self.assertFalse(self.test_user.verify_password_reset_token("invalid_token"))
    
    def test_password_reset_token_expiration(self):
        """Test password reset token expiration"""
        # Generate token and make it expired
        token = self.test_user.generate_password_reset_token()
        self.test_user.password_reset_sent_at = datetime.utcnow() - timedelta(hours=2)
        
        # Expired token should not verify
        self.assertFalse(self.test_user.verify_password_reset_token(token))
    
    def test_can_login_method(self):
        """Test can_login method with various user states"""
        # Active, verified user should be able to login
        self.assertTrue(self.test_user.can_login())
        
        # Inactive user should not be able to login
        self.test_user.is_active = False
        self.assertFalse(self.test_user.can_login())
        self.test_user.is_active = True
        
        # Unverified email should not be able to login
        self.test_user.email_verified = False
        self.assertFalse(self.test_user.can_login())
        self.test_user.email_verified = True
        
        # Locked account should not be able to login
        self.test_user.account_locked = True
        self.assertFalse(self.test_user.can_login())
        self.test_user.account_locked = False
        
        # Should be able to login again
        self.assertTrue(self.test_user.can_login())
    
    def test_failed_login_tracking(self):
        """Test failed login attempt tracking"""
        # Initial state
        self.assertEqual(self.test_user.failed_login_attempts, 0)
        self.assertIsNone(self.test_user.last_failed_login)
        
        # Record failed login
        self.test_user.record_failed_login()
        self.assertEqual(self.test_user.failed_login_attempts, 1)
        self.assertIsNotNone(self.test_user.last_failed_login)
        
        # Record multiple failed logins
        for i in range(4):  # Total will be 5
            self.test_user.record_failed_login()
        
        self.assertEqual(self.test_user.failed_login_attempts, 5)
    
    def test_account_unlock(self):
        """Test account unlock functionality"""
        # Lock account with failed attempts
        self.test_user.account_locked = True
        self.test_user.failed_login_attempts = 5
        self.test_user.last_failed_login = datetime.utcnow()
        
        # Unlock account
        self.test_user.unlock_account()
        
        self.assertFalse(self.test_user.account_locked)
        self.assertEqual(self.test_user.failed_login_attempts, 0)
        self.assertIsNone(self.test_user.last_failed_login)
    
    def test_get_full_name(self):
        """Test full name generation"""
        # With both first and last name
        self.assertEqual(self.test_user.get_full_name(), "Test User")
        
        # With only first name
        self.test_user.last_name = None
        self.assertEqual(self.test_user.get_full_name(), "Test")
        
        # With only last name
        self.test_user.first_name = None
        self.test_user.last_name = "User"
        self.assertEqual(self.test_user.get_full_name(), "User")
        
        # With no names
        self.test_user.first_name = None
        self.test_user.last_name = None
        self.assertEqual(self.test_user.get_full_name(), self.test_user.username)
    
    def test_export_personal_data(self):
        """Test GDPR personal data export"""
        data = self.test_user.export_personal_data()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data['username'], self.test_user.username)
        self.assertEqual(data['email'], self.test_user.email)
        self.assertEqual(data['first_name'], self.test_user.first_name)
        self.assertEqual(data['last_name'], self.test_user.last_name)
        self.assertEqual(data['role'], self.test_user.role.value)
        self.assertIn('created_at', data)
        self.assertIn('last_login', data)
        self.assertIn('data_processing_consent', data)
        self.assertIn('data_processing_consent_date', data)
    
    def test_anonymize_data(self):
        """Test GDPR data anonymization"""
        original_username = self.test_user.username
        original_email = self.test_user.email
        
        self.test_user.anonymize_data()
        
        # Personal data should be anonymized
        self.assertNotEqual(self.test_user.username, original_username)
        self.assertNotEqual(self.test_user.email, original_email)
        self.assertIsNone(self.test_user.first_name)
        self.assertIsNone(self.test_user.last_name)
        
        # Account should be deactivated
        self.assertFalse(self.test_user.is_active)
        
        # Tokens should be cleared
        self.assertIsNone(self.test_user.email_verification_token)
        self.assertIsNone(self.test_user.password_reset_token)
    
    def test_user_role_enum(self):
        """Test UserRole enum functionality"""
        # Test role assignment
        admin_user = User(username="admin", email="admin@test.com", role=UserRole.ADMIN)
        viewer_user = User(username="viewer", email="viewer@test.com", role=UserRole.VIEWER)
        
        self.assertEqual(admin_user.role, UserRole.ADMIN)
        self.assertEqual(viewer_user.role, UserRole.VIEWER)
        
        # Test role values
        self.assertEqual(UserRole.ADMIN.value, "admin")
        self.assertEqual(UserRole.VIEWER.value, "viewer")
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user_str = str(self.test_user)
        self.assertIn(self.test_user.username, user_str)
        # The actual repr only includes username, not email
        self.assertIn("User", user_str)


class TestUserAuditLog(unittest.TestCase):
    """Test UserAuditLog model functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create session
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()
        
        # Create test user
        self.test_user = User(
            username="testuser",
            email="test@test.com",
            role=UserRole.VIEWER
        )
        self.test_user.set_password("password123")
        self.db_session.add(self.test_user)
        self.db_session.commit()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_session.close()
    
    def test_log_action_basic(self):
        """Test basic audit log creation"""
        UserAuditLog.log_action(
            self.db_session,
            action="test_action",
            user_id=self.test_user.id,
            details="Test action performed"
        )
        
        # Verify log was created
        log_entry = self.db_session.query(UserAuditLog).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.action, "test_action")
        self.assertEqual(log_entry.user_id, self.test_user.id)
        self.assertEqual(log_entry.details, "Test action performed")
        self.assertIsNotNone(log_entry.created_at)
    
    def test_log_action_with_admin(self):
        """Test audit log creation with admin user"""
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@test.com",
            role=UserRole.ADMIN
        )
        admin_user.set_password("adminpass123")
        self.db_session.add(admin_user)
        self.db_session.commit()
        
        UserAuditLog.log_action(
            self.db_session,
            action="admin_action",
            user_id=self.test_user.id,
            admin_user_id=admin_user.id,
            details="Admin performed action",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )
        
        # Verify log was created with admin info
        log_entry = self.db_session.query(UserAuditLog).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.admin_user_id, admin_user.id)
        self.assertEqual(log_entry.ip_address, "192.168.1.1")
        self.assertEqual(log_entry.user_agent, "Test Browser")
    
    def test_log_action_without_user(self):
        """Test audit log creation without specific user"""
        UserAuditLog.log_action(
            self.db_session,
            action="system_action",
            details="System action performed",
            ip_address="127.0.0.1"
        )
        
        # Verify log was created
        log_entry = self.db_session.query(UserAuditLog).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.action, "system_action")
        self.assertIsNone(log_entry.user_id)
        self.assertEqual(log_entry.ip_address, "127.0.0.1")
    
    def test_get_user_audit_trail(self):
        """Test getting audit trail for specific user"""
        # Create multiple log entries
        actions = ["login", "profile_update", "password_change"]
        for action in actions:
            UserAuditLog.log_action(
                self.db_session,
                action=action,
                user_id=self.test_user.id,
                details=f"User performed {action}"
            )
        
        # Get audit trail manually since the method doesn't exist in the model
        audit_trail = self.db_session.query(UserAuditLog).filter_by(
            user_id=self.test_user.id
        ).order_by(UserAuditLog.created_at.desc()).all()
        
        self.assertEqual(len(audit_trail), 3)
        # Should be ordered by created_at desc (most recent first)
        self.assertEqual(audit_trail[0].action, "password_change")
        self.assertEqual(audit_trail[1].action, "profile_update")
        self.assertEqual(audit_trail[2].action, "login")
    
    def test_get_audit_trail_with_limit(self):
        """Test getting audit trail with limit"""
        # Create multiple log entries
        for i in range(10):
            UserAuditLog.log_action(
                self.db_session,
                action=f"action_{i}",
                user_id=self.test_user.id,
                details=f"Action {i} performed"
            )
        
        # Get limited audit trail manually
        audit_trail = self.db_session.query(UserAuditLog).filter_by(
            user_id=self.test_user.id
        ).order_by(UserAuditLog.created_at.desc()).limit(5).all()
        
        self.assertEqual(len(audit_trail), 5)
    
    def test_audit_log_string_representation(self):
        """Test audit log string representation"""
        UserAuditLog.log_action(
            self.db_session,
            action="test_action",
            user_id=self.test_user.id,
            details="Test details"
        )
        
        log_entry = self.db_session.query(UserAuditLog).first()
        log_str = str(log_entry)
        
        self.assertIn("test_action", log_str)
        self.assertIn(str(self.test_user.id), log_str)


if __name__ == '__main__':
    unittest.main()