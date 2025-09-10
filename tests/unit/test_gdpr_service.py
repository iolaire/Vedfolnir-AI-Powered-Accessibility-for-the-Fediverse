# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for GDPR Service
"""

import unittest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, UserRole, UserAuditLog
from services.gdpr_service import GDPRService
from config import Config
from app.core.database.core.database_manager import DatabaseManager

class TestGDPRService(unittest.TestCase):
    """Test GDPR Service functionality"""
    
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
        self.service = GDPRService(
            db_session=self.db_session,
            base_url="http://localhost:5000"
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.db_session.close()
    
    def test_export_user_data_complete(self):
        """Test complete user data export"""
        # Create some audit log entries
        UserAuditLog.log_action(
            self.db_session,
            action="login",
            user_id=self.test_user.id,
            details="User logged in",
            ip_address="127.0.0.1"
        )
        UserAuditLog.log_action(
            self.db_session,
            action="profile_update",
            user_id=self.test_user.id,
            details="User updated profile"
        )
        
        export_data = self.service.export_user_data(self.test_user.id)
        
        self.assertIsNotNone(export_data)
        self.assertIn('user_data', export_data)
        self.assertIn('audit_trail', export_data)
        self.assertIn('platform_connections', export_data)
        self.assertIn('export_metadata', export_data)
        
        # Verify user data completeness
        user_data = export_data['user_data']
        self.assertEqual(user_data['username'], self.test_user.username)
        self.assertEqual(user_data['email'], self.test_user.email)
        self.assertEqual(user_data['first_name'], self.test_user.first_name)
        self.assertEqual(user_data['last_name'], self.test_user.last_name)
        self.assertEqual(user_data['role'], self.test_user.role.value)
        self.assertIn('created_at', user_data)
        self.assertIn('data_processing_consent', user_data)
        
        # Verify audit trail
        audit_trail = export_data['audit_trail']
        self.assertEqual(len(audit_trail), 2)
        self.assertEqual(audit_trail[0]['action'], 'profile_update')  # Most recent first
        self.assertEqual(audit_trail[1]['action'], 'login')
        
        # Verify export metadata
        metadata = export_data['export_metadata']
        self.assertIn('export_date', metadata)
        self.assertIn('data_format', metadata)
        self.assertIn('gdpr_article', metadata)
        self.assertEqual(metadata['data_format'], 'JSON')
        self.assertEqual(metadata['gdpr_article'], 'Article 20 - Right to data portability')
    
    def test_export_user_data_invalid_user(self):
        """Test data export for non-existent user"""
        export_data = self.service.export_user_data(99999)
        self.assertIsNone(export_data)
    
    def test_export_user_data_json_serializable(self):
        """Test that exported data is JSON serializable"""
        export_data = self.service.export_user_data(self.test_user.id)
        
        # Should be able to serialize to JSON without errors
        try:
            json_str = json.dumps(export_data, default=str)
            self.assertIsInstance(json_str, str)
            
            # Should be able to deserialize back
            parsed_data = json.loads(json_str)
            self.assertIsInstance(parsed_data, dict)
        except (TypeError, ValueError) as e:
            self.fail(f"Export data is not JSON serializable: {e}")
    
    @patch('services.email_service.email_service.send_data_export_notification')
    def test_request_data_export(self, mock_send_email):
        """Test requesting data export with email notification"""
        mock_send_email.return_value = True
        
        result = asyncio.run(self.service.request_data_export(
            user_id=self.test_user.id,
            ip_address="127.0.0.1"
        ))
        
        success, message, export_data = result
        self.assertTrue(success)
        self.assertIn("data export completed", message)
        self.assertIsNotNone(export_data)
        
        # Verify email was sent
        mock_send_email.assert_called_once()
        
        # Verify audit log was created
        audit_logs = self.db_session.query(UserAuditLog).filter_by(
            user_id=self.test_user.id,
            action="gdpr_data_export_requested"
        ).all()
        self.assertEqual(len(audit_logs), 1)
    
    def test_delete_user_data_complete(self):
        """Test complete user data deletion"""
        user_id = self.test_user.id
        
        success, message = self.service.delete_user_data(
            user_id=user_id,
            deletion_type="complete",
            ip_address="127.0.0.1"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "User data deleted completely")
        
        # Verify user was deleted from database
        deleted_user = self.db_session.query(User).filter_by(id=user_id).first()
        self.assertIsNone(deleted_user)
    
    def test_delete_user_data_anonymize(self):
        """Test user data anonymization"""
        original_username = self.test_user.username
        original_email = self.test_user.email
        
        success, message = self.service.delete_user_data(
            user_id=self.test_user.id,
            deletion_type="anonymize",
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
    
    def test_delete_user_data_invalid_user(self):
        """Test deleting data for non-existent user"""
        success, message = self.service.delete_user_data(
            user_id=99999,
            deletion_type="complete",
            ip_address="127.0.0.1"
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "User not found")
    
    def test_delete_user_data_admin_protection(self):
        """Test that admin users cannot be deleted if they're the last admin"""
        # Make test user an admin
        self.test_user.role = UserRole.ADMIN
        self.db_session.commit()
        
        success, message = self.service.delete_user_data(
            user_id=self.test_user.id,
            deletion_type="complete",
            ip_address="127.0.0.1"
        )
        
        self.assertFalse(success)
        self.assertIn("Cannot delete the last admin user", message)
    
    def test_update_consent_status(self):
        """Test updating user consent status"""
        # Withdraw consent
        success, message = self.service.update_consent_status(
            user_id=self.test_user.id,
            consent_given=False,
            ip_address="127.0.0.1"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Consent status updated successfully")
        
        # Verify consent was withdrawn
        self.db_session.refresh(self.test_user)
        self.assertFalse(self.test_user.data_processing_consent)
        
        # Give consent again
        success, message = self.service.update_consent_status(
            user_id=self.test_user.id,
            consent_given=True,
            ip_address="127.0.0.1"
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Consent status updated successfully")
        
        # Verify consent was given
        self.db_session.refresh(self.test_user)
        self.assertTrue(self.test_user.data_processing_consent)
        self.assertIsNotNone(self.test_user.data_processing_consent_date)
    
    def test_update_consent_status_invalid_user(self):
        """Test updating consent for non-existent user"""
        success, message = self.service.update_consent_status(
            user_id=99999,
            consent_given=True,
            ip_address="127.0.0.1"
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "User not found")
    
    def test_get_user_consent_status(self):
        """Test getting user consent status"""
        consent_info = self.service.get_user_consent_status(self.test_user.id)
        
        self.assertIsNotNone(consent_info)
        self.assertIn('user_id', consent_info)
        self.assertIn('data_processing_consent', consent_info)
        self.assertIn('consent_date', consent_info)
        self.assertIn('can_withdraw_consent', consent_info)
        
        self.assertEqual(consent_info['user_id'], self.test_user.id)
        self.assertTrue(consent_info['data_processing_consent'])
        self.assertTrue(consent_info['can_withdraw_consent'])
    
    def test_get_user_consent_status_invalid_user(self):
        """Test getting consent status for non-existent user"""
        consent_info = self.service.get_user_consent_status(99999)
        self.assertIsNone(consent_info)
    
    def test_get_data_retention_info(self):
        """Test getting data retention information"""
        retention_info = self.service.get_data_retention_info(self.test_user.id)
        
        self.assertIsNotNone(retention_info)
        self.assertIn('user_id', retention_info)
        self.assertIn('account_created', retention_info)
        self.assertIn('last_activity', retention_info)
        self.assertIn('data_categories', retention_info)
        self.assertIn('retention_periods', retention_info)
        
        # Verify data categories
        data_categories = retention_info['data_categories']
        self.assertIn('personal_data', data_categories)
        self.assertIn('audit_logs', data_categories)
        self.assertIn('platform_connections', data_categories)
    
    def test_get_data_retention_info_invalid_user(self):
        """Test getting retention info for non-existent user"""
        retention_info = self.service.get_data_retention_info(99999)
        self.assertIsNone(retention_info)
    
    def test_validate_deletion_request(self):
        """Test deletion request validation"""
        # Valid deletion request
        is_valid, errors = self.service.validate_deletion_request(
            user_id=self.test_user.id,
            deletion_type="complete"
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid user
        is_valid, errors = self.service.validate_deletion_request(
            user_id=99999,
            deletion_type="complete"
        )
        self.assertFalse(is_valid)
        self.assertIn("User not found", errors)
        
        # Invalid deletion type
        is_valid, errors = self.service.validate_deletion_request(
            user_id=self.test_user.id,
            deletion_type="invalid_type"
        )
        self.assertFalse(is_valid)
        self.assertIn("Invalid deletion type", errors)
    
    def test_get_gdpr_compliance_report(self):
        """Test GDPR compliance report generation"""
        # Create some audit log entries for different GDPR actions
        gdpr_actions = [
            "gdpr_data_export_requested",
            "gdpr_consent_withdrawn",
            "gdpr_data_deleted"
        ]
        
        for action in gdpr_actions:
            UserAuditLog.log_action(
                self.db_session,
                action=action,
                user_id=self.test_user.id,
                details=f"GDPR action: {action}"
            )
        
        report = self.service.get_gdpr_compliance_report(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        self.assertIsNotNone(report)
        self.assertIn('report_period', report)
        self.assertIn('total_requests', report)
        self.assertIn('request_types', report)
        self.assertIn('compliance_metrics', report)
        
        # Verify request types
        request_types = report['request_types']
        self.assertIn('data_export', request_types)
        self.assertIn('consent_withdrawal', request_types)
        self.assertIn('data_deletion', request_types)
        
        self.assertEqual(request_types['data_export'], 1)
        self.assertEqual(request_types['consent_withdrawal'], 1)
        self.assertEqual(request_types['data_deletion'], 1)
    
    def test_cleanup_expired_export_data(self):
        """Test cleanup of expired export data"""
        # This would test cleanup of temporary export files
        # For now, we'll test the method exists and returns a count
        count = self.service.cleanup_expired_export_data()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)
    
    def test_verify_data_deletion_completeness(self):
        """Test verification of data deletion completeness"""
        user_id = self.test_user.id
        
        # Before deletion, verification should find data
        is_complete, remaining_data = self.service.verify_data_deletion_completeness(user_id)
        self.assertFalse(is_complete)
        self.assertGreater(len(remaining_data), 0)
        
        # Delete user data
        self.service.delete_user_data(
            user_id=user_id,
            deletion_type="complete",
            ip_address="127.0.0.1"
        )
        
        # After deletion, verification should confirm completeness
        is_complete, remaining_data = self.service.verify_data_deletion_completeness(user_id)
        self.assertTrue(is_complete)
        self.assertEqual(len(remaining_data), 0)

if __name__ == '__main__':
    unittest.main()