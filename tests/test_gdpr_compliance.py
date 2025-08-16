# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
GDPR Compliance Tests

Tests for GDPR data subject rights and privacy management functionality.
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from config import Config
from database import DatabaseManager
from models import User, UserRole, GDPRAuditLog
from services.gdpr_service import GDPRDataSubjectService, GDPRPrivacyService
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestGDPRCompliance(unittest.TestCase):
    """Test GDPR compliance functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="gdpr_test_user",
            role=UserRole.VIEWER
        )
        
        # Initialize services
        self.gdpr_service = GDPRDataSubjectService(
            self.db_manager.get_session(),
            base_url="http://localhost:5000"
        )
        self.privacy_service = GDPRPrivacyService(
            self.db_manager.get_session()
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        cleanup_test_user(self.user_helper)
    
    def test_data_export_functionality(self):
        """Test personal data export functionality"""
        # Test data export
        success, message, export_data = self.gdpr_service.export_personal_data(
            user_id=self.test_user.id,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        self.assertTrue(success, f"Data export failed: {message}")
        self.assertIsNotNone(export_data)
        
        # Verify export structure
        self.assertIn('data_export_info', export_data)
        self.assertIn('personal_data', export_data)
        self.assertIn('data_categories', export_data)
        
        # Verify user data is included
        user_profile = export_data['personal_data']['user_profile']
        self.assertEqual(user_profile['username'], self.test_user.username)
        self.assertEqual(user_profile['email'], self.test_user.email)
        
        # Verify GDPR audit log entry was created
        session = self.db_manager.get_session()
        audit_entry = session.query(GDPRAuditLog).filter_by(
            user_id=self.test_user.id,
            action_type="data_export"
        ).first()
        
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.gdpr_article, "Article 20")
        self.assertEqual(audit_entry.status, "completed")
    
    def test_data_rectification_functionality(self):
        """Test data rectification functionality"""
        # Test data rectification
        rectification_data = {
            'first_name': 'Updated First',
            'last_name': 'Updated Last'
        }
        
        success, message, result = self.gdpr_service.rectify_personal_data(
            user_id=self.test_user.id,
            rectification_data=rectification_data,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        self.assertTrue(success, f"Data rectification failed: {message}")
        self.assertIsNotNone(result)
        
        # Verify changes were applied
        session = self.db_manager.get_session()
        updated_user = session.query(User).filter_by(id=self.test_user.id).first()
        self.assertEqual(updated_user.first_name, 'Updated First')
        self.assertEqual(updated_user.last_name, 'Updated Last')
        
        # Verify changes are in result
        self.assertIn('changes_made', result)
        self.assertTrue(len(result['changes_made']) > 0)
    
    def test_consent_management(self):
        """Test consent management functionality"""
        # Test giving consent
        success, message = self.privacy_service.record_consent(
            user_id=self.test_user.id,
            consent_type="data_processing",
            consent_given=True,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        self.assertTrue(success, f"Consent recording failed: {message}")
        
        # Verify consent was recorded
        session = self.db_manager.get_session()
        updated_user = session.query(User).filter_by(id=self.test_user.id).first()
        self.assertTrue(updated_user.data_processing_consent)
        self.assertIsNotNone(updated_user.data_processing_consent_date)
        
        # Test withdrawing consent
        success, message = self.privacy_service.record_consent(
            user_id=self.test_user.id,
            consent_type="data_processing",
            consent_given=False,
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        self.assertTrue(success, f"Consent withdrawal failed: {message}")
        
        # Verify consent was withdrawn
        updated_user = session.query(User).filter_by(id=self.test_user.id).first()
        self.assertFalse(updated_user.data_processing_consent)
    
    def test_consent_history(self):
        """Test consent history retrieval"""
        # Record some consent actions first
        self.privacy_service.record_consent(
            user_id=self.test_user.id,
            consent_type="data_processing",
            consent_given=True
        )
        
        self.privacy_service.record_consent(
            user_id=self.test_user.id,
            consent_type="data_processing",
            consent_given=False
        )
        
        # Get consent history
        success, message, history = self.privacy_service.get_consent_history(self.test_user.id)
        
        self.assertTrue(success, f"Consent history retrieval failed: {message}")
        self.assertIsNotNone(history)
        self.assertIn('consent_history', history)
        self.assertTrue(len(history['consent_history']) >= 2)
    
    def test_gdpr_compliance_validation(self):
        """Test GDPR compliance validation"""
        success, message, compliance_status = self.privacy_service.validate_gdpr_compliance(
            self.test_user.id
        )
        
        self.assertTrue(success, f"Compliance validation failed: {message}")
        self.assertIsNotNone(compliance_status)
        
        # Verify compliance structure
        self.assertIn('checks', compliance_status)
        self.assertIn('overall_compliant', compliance_status)
        self.assertIn('recommendations', compliance_status)
        
        # Verify specific checks
        checks = compliance_status['checks']
        self.assertIn('consent_given', checks)
        self.assertIn('data_minimization', checks)
        self.assertIn('security', checks)
    
    def test_privacy_report_generation(self):
        """Test privacy report generation"""
        success, message, report = self.privacy_service.generate_privacy_report(
            self.test_user.id
        )
        
        self.assertTrue(success, f"Privacy report generation failed: {message}")
        self.assertIsNotNone(report)
        
        # Verify report structure
        self.assertIn('report_info', report)
        self.assertIn('data_processing', report)
        self.assertIn('consent_management', report)
        self.assertIn('compliance_status', report)
    
    def test_data_processing_info(self):
        """Test data processing information retrieval"""
        success, message, processing_info = self.gdpr_service.get_data_processing_info(
            self.test_user.id
        )
        
        self.assertTrue(success, f"Data processing info retrieval failed: {message}")
        self.assertIsNotNone(processing_info)
        
        # Verify processing info structure
        self.assertIn('data_controller', processing_info)
        self.assertIn('data_categories', processing_info)
        self.assertIn('processing_purposes', processing_info)
        self.assertIn('user_rights', processing_info)
        self.assertIn('user_consent_status', processing_info)
    
    def test_gdpr_audit_logging(self):
        """Test GDPR-specific audit logging"""
        session = self.db_manager.get_session()
        
        # Create a GDPR audit log entry
        audit_entry = GDPRAuditLog.log_gdpr_action(
            session=session,
            action_type="test_action",
            gdpr_article="Article 15",
            user_id=self.test_user.id,
            action_details="Test GDPR action",
            request_data={"test": "data"},
            status="completed",
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        session.commit()
        
        # Verify audit entry was created
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.action_type, "test_action")
        self.assertEqual(audit_entry.gdpr_article, "Article 15")
        self.assertEqual(audit_entry.user_id, self.test_user.id)
        self.assertEqual(audit_entry.status, "completed")
        
        # Test status update
        audit_entry.update_status(session, "failed", {"error": "test error"})
        
        self.assertEqual(audit_entry.status, "failed")
        self.assertIsNotNone(audit_entry.completed_at)
    
    def test_user_gdpr_methods(self):
        """Test GDPR-related methods on User model"""
        # Test export_personal_data method
        export_data = self.test_user.export_personal_data()
        
        self.assertIsInstance(export_data, dict)
        self.assertIn('username', export_data)
        self.assertIn('email', export_data)
        self.assertIn('data_processing_consent', export_data)
        
        # Test consent methods
        original_consent = self.test_user.data_processing_consent
        
        self.test_user.give_consent()
        self.assertTrue(self.test_user.data_processing_consent)
        self.assertIsNotNone(self.test_user.data_processing_consent_date)
        
        self.test_user.withdraw_consent()
        self.assertFalse(self.test_user.data_processing_consent)
        
        # Test anonymize_data method
        original_username = self.test_user.username
        original_email = self.test_user.email
        
        anonymous_id = self.test_user.anonymize_data()
        
        self.assertIsNotNone(anonymous_id)
        self.assertNotEqual(self.test_user.username, original_username)
        self.assertNotEqual(self.test_user.email, original_email)
        self.assertFalse(self.test_user.is_active)
        self.assertFalse(self.test_user.data_processing_consent)


class TestGDPRFormsValidation(unittest.TestCase):
    """Test GDPR forms validation"""
    
    def test_form_imports(self):
        """Test that GDPR forms can be imported"""
        try:
            from forms.gdpr_forms import (
                DataExportRequestForm, DataRectificationForm, DataErasureRequestForm,
                ConsentManagementForm, PrivacyRequestForm, GDPRComplianceReportForm,
                DataPortabilityForm
            )
            
            # Just test that the classes exist and have the expected attributes
            # We can't instantiate them without Flask app context
            self.assertTrue(hasattr(DataExportRequestForm, 'export_format'))
            self.assertTrue(hasattr(DataRectificationForm, 'first_name'))
            self.assertTrue(hasattr(DataErasureRequestForm, 'erasure_type'))
            self.assertTrue(hasattr(ConsentManagementForm, 'data_processing_consent'))
            self.assertTrue(hasattr(PrivacyRequestForm, 'request_type'))
            self.assertTrue(hasattr(GDPRComplianceReportForm, 'report_type'))
            self.assertTrue(hasattr(DataPortabilityForm, 'destination_service'))
            
        except ImportError as e:
            self.fail(f"Failed to import GDPR forms: {e}")


if __name__ == '__main__':
    unittest.main()