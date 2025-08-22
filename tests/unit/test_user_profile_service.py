# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for User Profile Service
"""

import unittest
import asyncio
import os
import shutil
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, UserRole, UserAuditLog
from services.user_management_service import UserProfileService
from config import Config
from database import DatabaseManager

class TestUserProfileService(unittest.TestCase):
    """Test UserProfileService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create in-DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db for testing
        self.engine = create_engine('mysql+pymysql://DATABASE_URL=mysql+pymysql://test_user:test_pass@localhost/test_db', echo=False)
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
        
        # Initialize service
        self.service = UserProfileService(
            db_session=self.db_session,
            base_url="http://localhost:5000"
        )
        
        # Create test storage directory
        self.test_storage_dir = "test_storage"
        os.makedirs(self.test_storage_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_session.close()
        
        # Clean up test storage directory
        if os.path.exists(self.test_storage_dir):
            shutil.rmtree(self.test_storage_dir)
    
    def test_update_profile_basic_info(self):
        """Test updating basic profile information"""
        profile_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
        }
        
        success, message, updated_user = self.service.update_profile(
            user_id=self.test_user.id,
            profile_data=profile_data,
            ip_address="127.0.0.1"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Profile updated successfully")
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.first_name, "Updated")
        self.assertEqual(updated_user.last_name, "Name")
        
        # Verify audit log was created
        audit_logs = self.db_session.query(UserAuditLog).filter_by(
            user_id=self.test_user.id,
            action="profile_updated"
        ).all()
        self.assertEqual(len(audit_logs), 1)
    
    def test_update_profile_invalid_user(self):
        """Test updating profile for non-existent user"""
        profile_data = {'first_name': 'Test'}
        
        success, message, user = self.service.update_profile(
            user_id=99999,
            profile_data=profile_data
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "User not found")
        self.assertIsNone(user)
    
    def test_update_profile_empty_data(self):
        """Test updating profile with empty data"""
        success, message, user = self.service.update_profile(
            user_id=self.test_user.id,
            profile_data={}
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "No profile data provided")
        self.assertIsNone(user)
    
    @patch('services.email_service.email_service.send_verification_email')
    def test_change_email_success(self, mock_send_email):
        """Test successful email change"""
        mock_send_email.return_value = True
        
        result = asyncio.run(self.service.change_email(
            user_id=self.test_user.id,
            new_email="newemail@test.com",
            ip_address="127.0.0.1"
        ))
        
        success, message = result
        self.assertTrue(success)
        self.assertIn("verification email has been sent", message)
        
        # Email should not be changed yet (requires verification)
        self.db_session.refresh(self.test_user)
        self.assertEqual(self.test_user.email, "test@test.com")
        self.assertFalse(self.test_user.email_verified)
        self.assertIsNotNone(self.test_user.email_verification_token)
    
    def test_change_email_invalid_email(self):
        """Test email change with invalid email"""
        result = asyncio.run(self.service.change_email(
            user_id=self.test_user.id,
            new_email="invalid-email",
            ip_address="127.0.0.1"
        ))
        
        success, message = result
        self.assertFalse(success)
        self.assertIn("Invalid email address", message)
    
    def test_change_email_duplicate_email(self):
        """Test email change with already registered email"""
        # Create another user with the target email
        other_user = User(
            username="otheruser",
            email="existing@test.com",
            role=UserRole.VIEWER
        )
        other_user.set_password("password123")
        self.db_session.add(other_user)
        self.db_session.commit()
        
        result = asyncio.run(self.service.change_email(
            user_id=self.test_user.id,
            new_email="existing@test.com",
            ip_address="127.0.0.1"
        ))
        
        success, message = result
        self.assertFalse(success)
        self.assertIn("already registered", message)
    
    def test_get_user_profile(self):
        """Test getting user profile"""
        profile = self.service.get_user_profile(self.test_user.id)
        
        self.assertIsNotNone(profile)
        self.assertEqual(profile['username'], self.test_user.username)
        self.assertEqual(profile['email'], self.test_user.email)
        self.assertEqual(profile['first_name'], self.test_user.first_name)
        self.assertEqual(profile['last_name'], self.test_user.last_name)
        self.assertEqual(profile['role'], self.test_user.role.value)
        self.assertIn('created_at', profile)
        self.assertIn('last_login', profile)
    
    def test_get_user_profile_invalid_user(self):
        """Test getting profile for non-existent user"""
        profile = self.service.get_user_profile(99999)
        self.assertIsNone(profile)
    
    @patch('services.email_service.email_service.send_profile_deleted_confirmation')
    def test_delete_user_profile_success(self, mock_send_email):
        """Test successful user profile deletion"""
        mock_send_email.return_value = True
        
        # Create some test files to simulate user data
        user_dir = os.path.join(self.test_storage_dir, f"user_{self.test_user.id}")
        os.makedirs(user_dir, exist_ok=True)
        test_file = os.path.join(user_dir, "test_image.jpg")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        with patch('os.path.exists', return_value=True), \
             patch('shutil.rmtree') as mock_rmtree:
            
            result = asyncio.run(self.service.delete_user_profile(
                user_id=self.test_user.id,
                ip_address="127.0.0.1",
                storage_base_path=self.test_storage_dir
            ))
            
            success, message = result
            self.assertTrue(success)
            self.assertEqual(message, "User profile deleted successfully")
            
            # Verify user was deleted from database
            deleted_user = self.db_session.query(User).filter_by(id=self.test_user.id).first()
            self.assertIsNone(deleted_user)
            
            # Verify storage cleanup was called
            mock_rmtree.assert_called()
    
    def test_delete_user_profile_invalid_user(self):
        """Test deleting profile for non-existent user"""
        result = asyncio.run(self.service.delete_user_profile(
            user_id=99999,
            ip_address="127.0.0.1"
        ))
        
        success, message = result
        self.assertFalse(success)
        self.assertEqual(message, "User not found")
    
    def test_delete_user_profile_admin_protection(self):
        """Test that admin users cannot be deleted if they're the last admin"""
        # Make test user an admin
        self.test_user.role = UserRole.ADMIN
        self.db_session.commit()
        
        result = asyncio.run(self.service.delete_user_profile(
            user_id=self.test_user.id,
            ip_address="127.0.0.1"
        ))
        
        success, message = result
        self.assertFalse(success)
        self.assertIn("Cannot delete the last admin user", message)
    
    def test_export_user_data(self):
        """Test GDPR user data export"""
        # Create some audit log entries
        UserAuditLog.log_action(
            self.db_session,
            action="login",
            user_id=self.test_user.id,
            details="User logged in"
        )
        
        export_data = self.service.export_user_data(self.test_user.id)
        
        self.assertIsNotNone(export_data)
        self.assertIn('user_data', export_data)
        self.assertIn('audit_trail', export_data)
        self.assertIn('platform_connections', export_data)
        self.assertIn('export_metadata', export_data)
        
        # Verify user data
        user_data = export_data['user_data']
        self.assertEqual(user_data['username'], self.test_user.username)
        self.assertEqual(user_data['email'], self.test_user.email)
        
        # Verify audit trail
        audit_trail = export_data['audit_trail']
        self.assertGreater(len(audit_trail), 0)
        
        # Verify export metadata
        metadata = export_data['export_metadata']
        self.assertIn('export_date', metadata)
        self.assertIn('data_format', metadata)
        self.assertEqual(metadata['data_format'], 'JSON')
    
    def test_export_user_data_invalid_user(self):
        """Test data export for non-existent user"""
        export_data = self.service.export_user_data(99999)
        self.assertIsNone(export_data)
    
    def test_anonymize_user_data(self):
        """Test GDPR user data anonymization"""
        original_username = self.test_user.username
        original_email = self.test_user.email
        
        success, message = self.service.anonymize_user_data(
            user_id=self.test_user.id,
            ip_address="127.0.0.1"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "User data anonymized successfully")
        
        # Verify data was anonymized
        self.db_session.refresh(self.test_user)
        self.assertNotEqual(self.test_user.username, original_username)
        self.assertNotEqual(self.test_user.email, original_email)
        self.assertIsNone(self.test_user.first_name)
        self.assertIsNone(self.test_user.last_name)
        self.assertFalse(self.test_user.is_active)
        
        # Verify audit log was created
        audit_logs = self.db_session.query(UserAuditLog).filter_by(
            user_id=self.test_user.id,
            action="user_data_anonymized"
        ).all()
        self.assertEqual(len(audit_logs), 1)
    
    def test_validate_profile_data(self):
        """Test profile data validation"""
        # Valid data
        valid_data = {
            'first_name': 'John',
            'last_name': 'Doe'
        }
        is_valid, errors = self.service.validate_profile_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid data - too long names
        invalid_data = {
            'first_name': 'A' * 101,  # Too long
            'last_name': 'B' * 101    # Too long
        }
        is_valid, errors = self.service.validate_profile_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Invalid data - invalid characters
        invalid_data = {
            'first_name': 'John<script>',  # Contains HTML
            'last_name': 'Doe&amp;'       # Contains HTML entities
        }
        is_valid, errors = self.service.validate_profile_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_get_user_activity_summary(self):
        """Test getting user activity summary"""
        # Create some audit log entries
        actions = ["login", "profile_update", "password_change", "login"]
        for action in actions:
            UserAuditLog.log_action(
                self.db_session,
                action=action,
                user_id=self.test_user.id,
                details=f"User performed {action}"
            )
        
        summary = self.service.get_user_activity_summary(self.test_user.id)
        
        self.assertIsNotNone(summary)
        self.assertIn('total_actions', summary)
        self.assertIn('recent_actions', summary)
        self.assertIn('action_counts', summary)
        
        self.assertEqual(summary['total_actions'], 4)
        self.assertEqual(summary['action_counts']['login'], 2)
        self.assertEqual(summary['action_counts']['profile_update'], 1)
        self.assertEqual(summary['action_counts']['password_change'], 1)
    
    def test_get_user_activity_summary_invalid_user(self):
        """Test activity summary for non-existent user"""
        summary = self.service.get_user_activity_summary(99999)
        self.assertIsNone(summary)

if __name__ == '__main__':
    unittest.main()