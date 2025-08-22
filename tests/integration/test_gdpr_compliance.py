# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for GDPR compliance workflows
"""

import unittest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from config import Config
from database import DatabaseManager
from models import User, UserRole, UserAuditLog
from services.gdpr_service import GDPRService
from services.user_management_service import UserProfileService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


class TestGDPRCompliance(MySQLIntegrationTestBase):
    """Test GDPR compliance integration workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = self.get_database_manager()
        
        self.test_users_to_cleanup = []
    
    def tearDown(self):
        """Clean up test fixtures"""
        for user_helper in self.test_users_to_cleanup:
            try:
                cleanup_test_user(user_helper)
            except Exception:
                pass
    
    @patch('services.email_service.email_service.send_data_export_notification')
    def test_complete_data_export_workflow(self, mock_send_email):
        """Test complete GDPR data export workflow (Article 20)"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user with some activity
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_export_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Create some audit log entries to export
            UserAuditLog.log_action(
                db_session,
                action="login",
                user_id=test_user.id,
                details="User logged in",
                ip_address="127.0.0.1"
            )
            UserAuditLog.log_action(
                db_session,
                action="profile_update",
                user_id=test_user.id,
                details="User updated profile"
            )
            
            # Request data export
            success, message, export_data = asyncio.run(gdpr_service.request_data_export(
                user_id=test_user.id,
                ip_address="127.0.0.1"
            ))
            
            self.assertTrue(success)
            self.assertIn("data export completed", message)
            self.assertIsNotNone(export_data)
            
            # Verify export data structure
            self.assertIn('user_data', export_data)
            self.assertIn('audit_trail', export_data)
            self.assertIn('platform_connections', export_data)
            self.assertIn('export_metadata', export_data)
            
            # Verify user data completeness
            user_data = export_data['user_data']
            self.assertEqual(user_data['username'], test_user.username)
            self.assertEqual(user_data['email'], test_user.email)
            self.assertEqual(user_data['role'], test_user.role.value)
            
            # Verify audit trail
            audit_trail = export_data['audit_trail']
            self.assertGreaterEqual(len(audit_trail), 2)
            
            # Verify export metadata
            metadata = export_data['export_metadata']
            self.assertIn('export_date', metadata)
            self.assertEqual(metadata['gdpr_article'], 'Article 20 - Right to data portability')
            
            # Verify data is JSON serializable
            json_str = json.dumps(export_data, default=str)
            self.assertIsInstance(json_str, str)
            
            # Verify email notification was sent
            mock_send_email.assert_called_once()
            
            # Verify audit log was created for the export request
            export_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="gdpr_data_export_requested"
            ).all()
            self.assertEqual(len(export_logs), 1)
    
    @patch('services.email_service.email_service.send_data_deletion_confirmation')
    def test_complete_data_deletion_workflow(self, mock_send_email):
        """Test complete GDPR data deletion workflow (Article 17)"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_delete_user",
                role=UserRole.VIEWER
            )
            user_id = test_user.id
            user_email = test_user.email
            
            # Create some audit log entries
            UserAuditLog.log_action(
                db_session,
                action="login",
                user_id=test_user.id,
                details="User logged in"
            )
            
            # Request complete data deletion
            success, message = gdpr_service.delete_user_data(
                user_id=user_id,
                deletion_type="complete",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "User data deleted completely")
            
            # Verify user was deleted from database
            deleted_user = db_session.query(User).filter_by(id=user_id).first()
            self.assertIsNone(deleted_user)
            
            # Verify email confirmation was sent
            mock_send_email.assert_called_once()
            
            # Verify audit logs for the deletion still exist (for compliance)
            deletion_logs = db_session.query(UserAuditLog).filter_by(
                user_id=user_id,
                action="gdpr_data_deleted"
            ).all()
            self.assertEqual(len(deletion_logs), 1)
    
    @patch('services.email_service.email_service.send_data_deletion_confirmation')
    def test_data_anonymization_workflow(self, mock_send_email):
        """Test GDPR data anonymization workflow"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_anonymize_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            original_username = test_user.username
            original_email = test_user.email
            
            # Request data anonymization
            success, message = gdpr_service.delete_user_data(
                user_id=test_user.id,
                deletion_type="anonymize",
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "User data anonymized successfully")
            
            # Verify data was anonymized
            db_session.refresh(test_user)
            self.assertNotEqual(test_user.username, original_username)
            self.assertNotEqual(test_user.email, original_email)
            self.assertIsNone(test_user.first_name)
            self.assertIsNone(test_user.last_name)
            self.assertFalse(test_user.is_active)
            
            # Verify user record still exists (anonymized)
            anonymized_user = db_session.query(User).filter_by(id=test_user.id).first()
            self.assertIsNotNone(anonymized_user)
            
            # Verify email confirmation was sent
            mock_send_email.assert_called_once()
    
    @patch('services.email_service.email_service.send_consent_withdrawal_confirmation')
    def test_consent_withdrawal_workflow(self, mock_send_email):
        """Test GDPR consent withdrawal workflow (Article 7)"""
        mock_send_email.return_value = True
        
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user with consent
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_consent_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Verify initial consent
            self.assertTrue(test_user.data_processing_consent)
            self.assertIsNotNone(test_user.data_processing_consent_date)
            
            # Withdraw consent
            success, message = gdpr_service.update_consent_status(
                user_id=test_user.id,
                consent_given=False,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "Consent status updated successfully")
            
            # Verify consent was withdrawn
            db_session.refresh(test_user)
            self.assertFalse(test_user.data_processing_consent)
            
            # Verify audit log was created
            consent_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="gdpr_consent_withdrawn"
            ).all()
            self.assertEqual(len(consent_logs), 1)
            
            # Re-give consent
            success, message = gdpr_service.update_consent_status(
                user_id=test_user.id,
                consent_given=True,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            
            # Verify consent was given again
            db_session.refresh(test_user)
            self.assertTrue(test_user.data_processing_consent)
            self.assertIsNotNone(test_user.data_processing_consent_date)
    
    def test_data_rectification_workflow(self):
        """Test GDPR data rectification workflow (Article 16)"""
        with self.db_manager.get_session() as db_session:
            profile_service = UserProfileService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_rectify_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Update profile data (rectification)
            rectification_data = {
                'first_name': 'Corrected',
                'last_name': 'Name'
            }
            
            success, message, updated_user = profile_service.update_profile(
                user_id=test_user.id,
                profile_data=rectification_data,
                ip_address="127.0.0.1"
            )
            
            self.assertTrue(success)
            self.assertEqual(message, "Profile updated successfully")
            
            # Verify data was rectified
            self.assertEqual(updated_user.first_name, "Corrected")
            self.assertEqual(updated_user.last_name, "Name")
            
            # Verify audit log was created
            rectification_logs = db_session.query(UserAuditLog).filter_by(
                user_id=test_user.id,
                action="profile_updated"
            ).all()
            self.assertEqual(len(rectification_logs), 1)
    
    def test_data_retention_compliance(self):
        """Test data retention compliance"""
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_retention_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Get data retention information
            retention_info = gdpr_service.get_data_retention_info(test_user.id)
            
            self.assertIsNotNone(retention_info)
            self.assertIn('user_id', retention_info)
            self.assertIn('account_created', retention_info)
            self.assertIn('data_categories', retention_info)
            self.assertIn('retention_periods', retention_info)
            
            # Verify data categories are documented
            data_categories = retention_info['data_categories']
            self.assertIn('personal_data', data_categories)
            self.assertIn('audit_logs', data_categories)
            self.assertIn('platform_connections', data_categories)
            
            # Verify retention periods are specified
            retention_periods = retention_info['retention_periods']
            self.assertIn('personal_data', retention_periods)
            self.assertIn('audit_logs', retention_periods)
    
    def test_gdpr_compliance_report(self):
        """Test GDPR compliance reporting"""
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user and perform GDPR actions
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_report_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Simulate various GDPR actions
            gdpr_actions = [
                "gdpr_data_export_requested",
                "gdpr_consent_withdrawn",
                "gdpr_data_deleted"
            ]
            
            for action in gdpr_actions:
                UserAuditLog.log_action(
                    db_session,
                    action=action,
                    user_id=test_user.id,
                    details=f"GDPR action: {action}",
                    ip_address="127.0.0.1"
                )
            
            # Generate compliance report
            report = gdpr_service.get_gdpr_compliance_report(
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
            
            self.assertIsNotNone(report)
            self.assertIn('report_period', report)
            self.assertIn('total_requests', report)
            self.assertIn('request_types', report)
            self.assertIn('compliance_metrics', report)
            
            # Verify request types are tracked
            request_types = report['request_types']
            self.assertIn('data_export', request_types)
            self.assertIn('consent_withdrawal', request_types)
            self.assertIn('data_deletion', request_types)
            
            # Verify counts
            self.assertEqual(request_types['data_export'], 1)
            self.assertEqual(request_types['consent_withdrawal'], 1)
            self.assertEqual(request_types['data_deletion'], 1)
    
    def test_data_deletion_verification(self):
        """Test verification of complete data deletion"""
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_verify_user",
                role=UserRole.VIEWER
            )
            user_id = test_user.id
            
            # Before deletion, verification should find data
            is_complete, remaining_data = gdpr_service.verify_data_deletion_completeness(user_id)
            self.assertFalse(is_complete)
            self.assertGreater(len(remaining_data), 0)
            
            # Delete user data
            gdpr_service.delete_user_data(
                user_id=user_id,
                deletion_type="complete",
                ip_address="127.0.0.1"
            )
            
            # After deletion, verification should confirm completeness
            is_complete, remaining_data = gdpr_service.verify_data_deletion_completeness(user_id)
            self.assertTrue(is_complete)
            self.assertEqual(len(remaining_data), 0)
    
    def test_gdpr_admin_protection(self):
        """Test that admin users cannot be deleted if they're the last admin"""
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create admin user
            admin_user, admin_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_admin_user",
                role=UserRole.ADMIN
            )
            self.test_users_to_cleanup.append(admin_helper)
            
            # Attempt to delete the admin user
            success, message = gdpr_service.delete_user_data(
                user_id=admin_user.id,
                deletion_type="complete",
                ip_address="127.0.0.1"
            )
            
            self.assertFalse(success)
            self.assertIn("Cannot delete the last admin user", message)
            
            # Verify admin user still exists
            admin_still_exists = db_session.query(User).filter_by(id=admin_user.id).first()
            self.assertIsNotNone(admin_still_exists)
    
    def test_consent_status_tracking(self):
        """Test comprehensive consent status tracking"""
        with self.db_manager.get_session() as db_session:
            gdpr_service = GDPRService(
                db_session=db_session,
                base_url="http://localhost:5000"
            )
            
            # Create test user
            test_user, test_helper = create_test_user_with_platforms(
                self.db_manager,
                username="gdpr_consent_track_user",
                role=UserRole.VIEWER
            )
            self.test_users_to_cleanup.append(test_helper)
            
            # Get initial consent status
            consent_info = gdpr_service.get_user_consent_status(test_user.id)
            
            self.assertIsNotNone(consent_info)
            self.assertEqual(consent_info['user_id'], test_user.id)
            self.assertTrue(consent_info['data_processing_consent'])
            self.assertTrue(consent_info['can_withdraw_consent'])
            self.assertIsNotNone(consent_info['consent_date'])
            
            # Withdraw consent
            gdpr_service.update_consent_status(
                user_id=test_user.id,
                consent_given=False,
                ip_address="127.0.0.1"
            )
            
            # Check updated consent status
            updated_consent_info = gdpr_service.get_user_consent_status(test_user.id)
            self.assertFalse(updated_consent_info['data_processing_consent'])
            
            # Re-give consent
            gdpr_service.update_consent_status(
                user_id=test_user.id,
                consent_given=True,
                ip_address="127.0.0.1"
            )
            
            # Check final consent status
            final_consent_info = gdpr_service.get_user_consent_status(test_user.id)
            self.assertTrue(final_consent_info['data_processing_consent'])
            self.assertIsNotNone(final_consent_info['consent_date'])

if __name__ == '__main__':
    unittest.main()