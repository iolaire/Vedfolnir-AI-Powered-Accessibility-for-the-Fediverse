# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for User Registration Service

Tests the user registration and email verification functionality.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, UserRole, UserAuditLog
from services.user_management_service import UserRegistrationService, UserAuthenticationService

class TestUserRegistrationService(unittest.TestCase):
    """Test cases for UserRegistrationService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create in-DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db for testing
        self.engine = create_engine('mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create session
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()
        
        # Initialize service
        self.service = UserRegistrationService(
            db_session=self.db_session,
            base_url="http://localhost:5000"
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_session.close()
    
    def test_validate_email_address_valid(self):
        """Test email validation with valid email"""
        valid, result = self.service.validate_email_address("test@gmail.com")
        self.assertTrue(valid)
        self.assertEqual(result, "test@gmail.com")
    
    def test_validate_email_address_invalid(self):
        """Test email validation with invalid email"""
        valid, result = self.service.validate_email_address("invalid-email")
        self.assertFalse(valid)
        self.assertIn("@-sign", result.lower())
    
    def test_validate_username_valid(self):
        """Test username validation with valid username"""
        valid, message = self.service.validate_username("testuser123")
        self.assertTrue(valid)
        self.assertEqual(message, "Username is valid")
    
    def test_validate_username_too_short(self):
        """Test username validation with too short username"""
        valid, message = self.service.validate_username("ab")
        self.assertFalse(valid)
        self.assertIn("at least 3 characters", message)
    
    def test_validate_username_too_long(self):
        """Test username validation with too long username"""
        long_username = "a" * 65
        valid, message = self.service.validate_username(long_username)
        self.assertFalse(valid)
        self.assertIn("no more than 64 characters", message)
    
    def test_validate_username_invalid_characters(self):
        """Test username validation with invalid characters"""
        valid, message = self.service.validate_username("test@user")
        self.assertFalse(valid)
        self.assertIn("letters, numbers, hyphens, and underscores", message)
    
    def test_validate_username_already_taken(self):
        """Test username validation with existing username"""
        # Create existing user
        existing_user = User(
            username="existinguser",
            email="existing@test.com",
            role=UserRole.VIEWER
        )
        existing_user.set_password("password123")
        self.db_session.add(existing_user)
        self.db_session.commit()
        
        valid, message = self.service.validate_username("existinguser")
        self.assertFalse(valid)
        self.assertIn("already taken", message)
    
    def test_validate_password_valid(self):
        """Test password validation with valid password"""
        valid, message = self.service.validate_password("password123")
        self.assertTrue(valid)
        self.assertEqual(message, "Password is valid")
    
    def test_validate_password_too_short(self):
        """Test password validation with too short password"""
        valid, message = self.service.validate_password("pass1")
        self.assertFalse(valid)
        self.assertIn("at least 8 characters", message)
    
    def test_validate_password_no_letter(self):
        """Test password validation with no letters"""
        valid, message = self.service.validate_password("12345678")
        self.assertFalse(valid)
        self.assertIn("at least one letter and one number", message)
    
    def test_validate_password_no_number(self):
        """Test password validation with no numbers"""
        valid, message = self.service.validate_password("password")
        self.assertFalse(valid)
        self.assertIn("at least one letter and one number", message)
    
    def test_register_user_success(self):
        """Test successful user registration"""
        success, message, user = self.service.register_user(
            username="newuser",
            email="newuser@gmail.com",
            password="password123",
            role=UserRole.VIEWER,
            first_name="New",
            last_name="User"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "User registered successfully")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "newuser@gmail.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.role, UserRole.VIEWER)
        self.assertFalse(user.email_verified)  # Should require verification
        self.assertTrue(user.data_processing_consent)
        self.assertIsNotNone(user.email_verification_token)
    
    def test_register_user_duplicate_username(self):
        """Test user registration with duplicate username"""
        # Create existing user
        existing_user = User(
            username="existinguser",
            email="existing@test.com",
            role=UserRole.VIEWER
        )
        existing_user.set_password("password123")
        self.db_session.add(existing_user)
        self.db_session.commit()
        
        success, message, user = self.service.register_user(
            username="existinguser",
            email="newuser@test.com",
            password="password123"
        )
        
        self.assertFalse(success)
        self.assertIn("already taken", message)
        self.assertIsNone(user)
    
    def test_register_user_duplicate_email(self):
        """Test user registration with duplicate email"""
        # Create existing user
        existing_user = User(
            username="existinguser",
            email="existing@test.com",
            role=UserRole.VIEWER
        )
        existing_user.set_password("password123")
        self.db_session.add(existing_user)
        self.db_session.commit()
        
        success, message, user = self.service.register_user(
            username="newuser",
            email="existing@gmail.com",
            password="password123"
        )
        
        self.assertFalse(success)
        self.assertIn("already registered", message)
        self.assertIsNone(user)
    
    def test_verify_email_success(self):
        """Test successful email verification"""
        # Create user with verification token
        user = User(
            username="testuser",
            email="test@test.com",
            role=UserRole.VIEWER,
            email_verified=False
        )
        user.set_password("password123")
        token = user.generate_email_verification_token()
        self.db_session.add(user)
        self.db_session.commit()
        
        success, message, verified_user = self.service.verify_email(token)
        
        self.assertTrue(success)
        self.assertEqual(message, "Email verified successfully")
        self.assertIsNotNone(verified_user)
        self.assertTrue(verified_user.email_verified)
        self.assertIsNone(verified_user.email_verification_token)
    
    def test_verify_email_invalid_token(self):
        """Test email verification with invalid token"""
        success, message, user = self.service.verify_email("invalid_token")
        
        self.assertFalse(success)
        self.assertIn("Invalid or expired", message)
        self.assertIsNone(user)
    
    def test_verify_email_expired_token(self):
        """Test email verification with expired token"""
        # Create user with expired verification token
        user = User(
            username="testuser",
            email="test@test.com",
            role=UserRole.VIEWER,
            email_verified=False
        )
        user.set_password("password123")
        token = user.generate_email_verification_token()
        # Manually set sent_at to 25 hours ago (expired)
        user.email_verification_sent_at = datetime.utcnow() - timedelta(hours=25)
        self.db_session.add(user)
        self.db_session.commit()
        
        success, message, verified_user = self.service.verify_email(token)
        
        self.assertFalse(success)
        self.assertIn("expired", message)
        self.assertIsNone(verified_user)

class TestUserAuthenticationService(unittest.TestCase):
    """Test cases for UserAuthenticationService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create in-DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db for testing
        self.engine = create_engine('mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db', echo=False)
        Base.metadata.create_all(self.engine)
        
        # Create session
        Session = sessionmaker(bind=self.engine)
        self.db_session = Session()
        
        # Initialize service
        self.service = UserAuthenticationService(db_session=self.db_session)
        
        # Create test user
        self.test_user = User(
            username="testuser",
            email="test@test.com",
            role=UserRole.VIEWER,
            email_verified=True,
            is_active=True
        )
        self.test_user.set_password("password123")
        self.db_session.add(self.test_user)
        self.db_session.commit()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_session.close()
    
    def test_authenticate_user_success_username(self):
        """Test successful authentication with username"""
        success, message, user = self.service.authenticate_user(
            username_or_email="testuser",
            password="password123"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Login successful")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
    
    def test_authenticate_user_success_email(self):
        """Test successful authentication with email"""
        success, message, user = self.service.authenticate_user(
            username_or_email="test@test.com",
            password="password123"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Login successful")
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "test@test.com")
    
    def test_authenticate_user_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        success, message, user = self.service.authenticate_user(
            username_or_email="testuser",
            password="wrongpassword"
        )
        
        self.assertFalse(success)
        self.assertIn("Invalid password", message)
        self.assertIsNone(user)
    
    def test_authenticate_user_nonexistent(self):
        """Test authentication with non-existent user"""
        success, message, user = self.service.authenticate_user(
            username_or_email="nonexistent",
            password="password123"
        )
        
        self.assertFalse(success)
        self.assertIn("Invalid username/email or password", message)
        self.assertIsNone(user)
    
    def test_authenticate_user_unverified_email(self):
        """Test authentication with unverified email"""
        # Create unverified user
        unverified_user = User(
            username="unverified",
            email="unverified@test.com",
            role=UserRole.VIEWER,
            email_verified=False,
            is_active=True
        )
        unverified_user.set_password("password123")
        self.db_session.add(unverified_user)
        self.db_session.commit()
        
        success, message, user = self.service.authenticate_user(
            username_or_email="unverified",
            password="password123"
        )
        
        self.assertFalse(success)
        self.assertIn("not verified", message)
        self.assertIsNone(user)
    
    def test_authenticate_user_inactive(self):
        """Test authentication with inactive user"""
        # Create inactive user
        inactive_user = User(
            username="inactive",
            email="inactive@test.com",
            role=UserRole.VIEWER,
            email_verified=True,
            is_active=False
        )
        inactive_user.set_password("password123")
        self.db_session.add(inactive_user)
        self.db_session.commit()
        
        success, message, user = self.service.authenticate_user(
            username_or_email="inactive",
            password="password123"
        )
        
        self.assertFalse(success)
        self.assertIn("deactivated", message)
        self.assertIsNone(user)
    
    def test_authenticate_user_locked_account(self):
        """Test authentication with locked account"""
        # Lock the test user account
        self.test_user.account_locked = True
        self.db_session.commit()
        
        success, message, user = self.service.authenticate_user(
            username_or_email="testuser",
            password="password123"
        )
        
        self.assertFalse(success)
        self.assertIn("locked", message)
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()