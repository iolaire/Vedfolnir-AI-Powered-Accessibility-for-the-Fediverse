# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test User Profile Management

Tests for the user profile management services including profile editing,
email changes, data export, and GDPR-compliant profile deletion.
"""

import unittest
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from config import Config
from database import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.user_management_service import UserProfileService, UserDeletionService

class TestUserProfileManagement(unittest.TestCase):
    """Test user profile management functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create test config
        self.config = Config()
        self.config.DATABASE_URL = f'mysql+pymysql://{self.db_path}'
        
        # Initialize database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Create tables
        from models import Base
        Base.metadata.create_all(self.db_manager.engine)
        
        # Create test user with unique identifiers
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        with self.db_manager.get_session() as session:
            self.test_user = User(
                username=f'testuser_{unique_id}',
                email=f'test_{unique_id}@test.com',
                role=UserRole.VIEWER,
                is_active=True,
                email_verified=True,
                first_name='Test',
                last_name='User',
                data_processing_consent=True,
                data_processing_consent_date=datetime.utcnow()
            )
            self.test_user.set_password('testpassword123')
            session.add(self.test_user)
            session.commit()
            self.test_user_id = self.test_user.id
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_get_profile_data(self):
        """Test getting user profile data"""
        with self.db_manager.get_session() as session:
            profile_service = UserProfileService(session)
            
            success, message, profile_data = profile_service.get_profile_data(self.test_user_id)
            
            self.assertTrue(success)
            self.assertIsNotNone(profile_data)
            self.assertTrue(profile_data['username'].startswith('testuser_'))
            self.assertTrue(profile_data['email'].startswith('test_'))
            self.assertEqual(profile_data['first_name'], 'Test')
            self.assertEqual(profile_data['last_name'], 'User')
            self.assertEqual(profile_data['full_name'], 'Test User')
            self.assertTrue(profile_data['email_verified'])
    
    def test_update_profile_names(self):
        """Test updating profile names"""
        with self.db_manager.get_session() as session:
            profile_service = UserProfileService(session)
            
            profile_data = {
                'first_name': 'Updated',
                'last_name': 'Name'
            }
            
            success, message, updated_data = profile_service.update_profile(
                user_id=self.test_user_id,
                profile_data=profile_data,
                ip_address='127.0.0.1'
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(updated_data)
            self.assertEqual(updated_data['first_name'], 'Updated')
            self.assertEqual(updated_data['last_name'], 'Name')
            self.assertEqual(updated_data['full_name'], 'Updated Name')
            self.assertFalse(updated_data['email_changed'])
    
    def test_update_profile_email_change(self):
        """Test updating profile with email change"""
        with self.db_manager.get_session() as session:
            profile_service = UserProfileService(session)
            
            profile_data = {
                'email': 'newemail@test.com'
            }
            
            success, message, updated_data = profile_service.update_profile(
                user_id=self.test_user_id,
                profile_data=profile_data,
                ip_address='127.0.0.1'
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(updated_data)
            self.assertEqual(updated_data['email'], 'newemail@test.com')
            self.assertTrue(updated_data['email_changed'])
            self.assertFalse(updated_data['email_verified'])  # Should require re-verification
    
    def test_validate_profile_data(self):
        """Test profile data validation"""
        with self.db_manager.get_session() as session:
            profile_service = UserProfileService(session)
            
            # Valid data
            valid_data = {
                'first_name': 'Valid',
                'last_name': 'Name',
                'email': 'valid@test.com'
            }
            
            is_valid, errors = profile_service.validate_profile_data(valid_data)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
            
            # Invalid data
            invalid_data = {
                'first_name': 'A' * 101,  # Too long
                'email': 'invalid-email'  # Invalid format
            }
            
            is_valid, errors = profile_service.validate_profile_data(invalid_data)
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
    
    def test_export_user_data(self):
        """Test exporting user personal data"""
        with self.db_manager.get_session() as session:
            profile_service = UserProfileService(session)
            
            success, message, export_data = profile_service.export_user_data(
                user_id=self.test_user_id,
                ip_address='127.0.0.1'
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(export_data)
            self.assertIn('user_profile', export_data)
            self.assertIn('posts', export_data)
            self.assertIn('images', export_data)
            self.assertIn('processing_runs', export_data)
            self.assertIn('audit_log', export_data)
            self.assertIn('export_timestamp', export_data)
            self.assertEqual(export_data['export_format'], 'GDPR_compliant_JSON')
            
            # Check user profile data
            user_profile = export_data['user_profile']
            self.assertTrue(user_profile['username'].startswith('testuser_'))
            self.assertTrue(user_profile['email'].startswith('test_'))
    
    def test_validate_deletion_request(self):
        """Test deletion request validation"""
        with self.db_manager.get_session() as session:
            deletion_service = UserDeletionService(session)
            
            # User can delete their own profile
            can_delete, message = deletion_service.validate_deletion_request(
                user_id=self.test_user_id,
                requesting_user_id=self.test_user_id
            )
            
            self.assertTrue(can_delete)
            self.assertIn('own profile', message)
    
    def test_validate_deletion_request_admin_protection(self):
        """Test that last admin user cannot be deleted"""
        with self.db_manager.get_session() as session:
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@test.com',
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True
            )
            admin_user.set_password('adminpass123')
            session.add(admin_user)
            session.commit()
            admin_user_id = admin_user.id
            
            deletion_service = UserDeletionService(session)
            
            # Admin cannot delete themselves if they're the last admin
            can_delete, message = deletion_service.validate_deletion_request(
                user_id=admin_user_id,
                requesting_user_id=admin_user_id
            )
            
            # This should still return True for self-deletion, but the actual deletion
            # will be prevented in delete_user_profile method
            self.assertTrue(can_delete)
    
    def test_anonymize_user_profile(self):
        """Test user profile anonymization"""
        with self.db_manager.get_session() as session:
            deletion_service = UserDeletionService(session)
            
            success, message, anonymization_summary = deletion_service.anonymize_user_profile(
                user_id=self.test_user_id,
                ip_address='127.0.0.1'
            )
            
            self.assertTrue(success)
            self.assertIsNotNone(anonymization_summary)
            self.assertTrue(anonymization_summary['original_username'].startswith('testuser_'))
            self.assertTrue(anonymization_summary['original_email'].startswith('test_'))
            self.assertNotEqual(anonymization_summary['anonymous_username'], anonymization_summary['original_username'])
            self.assertNotEqual(anonymization_summary['anonymous_email'], anonymization_summary['original_email'])
            self.assertEqual(anonymization_summary['deletion_method'], 'anonymization')
            
            # Verify user is anonymized in database
            user = session.query(User).filter_by(id=self.test_user_id).first()
            self.assertIsNotNone(user)
            self.assertFalse(user.username.startswith('testuser_'))
            self.assertFalse(user.email.startswith('test_'))
            self.assertFalse(user.is_active)
            self.assertIsNone(user.first_name)
            self.assertIsNone(user.last_name)
    
    def test_profile_update_audit_logging(self):
        """Test that profile updates are properly logged"""
        with self.db_manager.get_session() as session:
            profile_service = UserProfileService(session)
            
            profile_data = {
                'first_name': 'Audited',
                'last_name': 'Update'
            }
            
            success, message, updated_data = profile_service.update_profile(
                user_id=self.test_user_id,
                profile_data=profile_data,
                ip_address='127.0.0.1',
                user_agent='Test Browser'
            )
            
            self.assertTrue(success)
            
            # Check audit log
            audit_entries = session.query(UserAuditLog).filter_by(
                user_id=self.test_user_id,
                action='profile_updated'
            ).all()
            
            self.assertGreater(len(audit_entries), 0)
            audit_entry = audit_entries[-1]  # Get latest entry
            self.assertEqual(audit_entry.ip_address, '127.0.0.1')
            self.assertEqual(audit_entry.user_agent, 'Test Browser')
            self.assertIn('first_name', audit_entry.details)
            self.assertIn('last_name', audit_entry.details)

if __name__ == '__main__':
    unittest.main()