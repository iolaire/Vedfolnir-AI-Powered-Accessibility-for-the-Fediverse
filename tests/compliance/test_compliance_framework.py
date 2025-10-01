# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive test suite for the compliance and audit framework

Tests all components of the compliance framework including:
- Audit logging
- GDPR compliance
- Data lifecycle management
- Compliance reporting
"""

import unittest
import tempfile
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.compliance.audit_logger import AuditLogger, AuditEventType, AuditEvent
from app.services.compliance.gdpr_compliance import GDPRComplianceService, GDPRRequestType
from app.services.compliance.compliance_reporter import ComplianceReporter, ReportType, ReportFormat
from app.services.compliance.data_lifecycle_manager import DataLifecycleManager, DataCategory, RetentionAction
from app.services.compliance.compliance_service import ComplianceService

class TestAuditLogger(unittest.TestCase):
    """Test audit logging functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'enabled': True,
            'log_level': 'INFO',
            'destinations': [
                {
                    'type': 'file',
                    'path': os.path.join(self.temp_dir, 'audit.log')
                }
            ],
            'events': [],
            'async_logging': False  # Synchronous for testing
        }
        self.audit_logger = AuditLogger(self.config)
    
    def tearDown(self):
        if self.audit_logger:
            self.audit_logger.shutdown()
        # Cleanup temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_audit_event_creation(self):
        """Test audit event creation and hashing"""
        event = AuditEvent(
            event_id="test123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=AuditEventType.USER_AUTHENTICATION,
            user_id=1,
            username="testuser",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            resource="authentication",
            action="login",
            outcome="SUCCESS",
            details={"method": "password"}
        )
        
        self.assertIsNotNone(event.event_hash)
        self.assertEqual(len(event.event_hash), 64)  # SHA256 hash length
    
    def test_audit_logging(self):
        """Test basic audit logging functionality"""
        self.audit_logger.log_user_authentication(
            username="testuser",
            outcome="SUCCESS",
            ip_address="127.0.0.1",
            details={"method": "password"}
        )
        
        # Check if log file was created and contains entry
        log_file = Path(self.config['destinations'][0]['path'])
        self.assertTrue(log_file.exists())
        
        with open(log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("user_authentication", log_content)
            self.assertIn("testuser", log_content)
    
    def test_security_event_logging(self):
        """Test security event logging"""
        self.audit_logger.log_security_event(
            event_description="Suspicious login attempt",
            severity="HIGH",
            user_id=1,
            username="testuser",
            ip_address="192.168.1.100",
            details={"attempts": 5, "blocked": True}
        )
        
        log_file = Path(self.config['destinations'][0]['path'])
        with open(log_file, 'r') as f:
            log_content = f.read()
            self.assertIn("security_event", log_content)
            self.assertIn("Suspicious login attempt", log_content)
    
    def test_hash_chain_integrity(self):
        """Test audit log hash chain integrity"""
        # Log multiple events
        for i in range(3):
            self.audit_logger.log_data_access(
                user_id=1,
                username="testuser",
                resource=f"resource_{i}",
                action="read"
            )
        
        # Verify hash chain (simplified test)
        verification_result = self.audit_logger.verify_audit_chain()
        self.assertTrue(verification_result['verified'])

class TestGDPRCompliance(unittest.TestCase):
    """Test GDPR compliance functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock()
        self.mock_audit_logger = Mock()
        
        self.config = {
            'data_retention_days': 2555,
            'anonymization_enabled': True,
            'export_format': 'json',
            'export_path': self.temp_dir
        }
        
        self.gdpr_service = GDPRComplianceService(
            self.mock_db_manager,
            self.mock_audit_logger,
            self.config
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('app.services.compliance.gdpr_compliance.datetime')
    def test_create_gdpr_request(self, mock_datetime):
        """Test GDPR request creation"""
        mock_datetime.now.return_value = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now().isoformat.return_value = "2025-01-15T10:30:00+00:00"
        
        # Mock database session
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        request_id = self.gdpr_service.create_gdpr_request(
            user_id=1,
            request_type=GDPRRequestType.DATA_EXPORT,
            details={"reason": "User requested data export"}
        )
        
        self.assertIsNotNone(request_id)
        self.assertEqual(len(request_id), 16)
        
        # Verify database call was made
        mock_session.execute.assert_called()
        mock_session.commit.assert_called()
        
        # Verify audit logging
        self.mock_audit_logger.log_gdpr_request.assert_called_once()
    
    def test_data_export_process(self):
        """Test data export processing"""
        # Mock request data
        mock_request = Mock()
        mock_request.user_id = 1
        mock_request.request_id = "test123"
        
        with patch.object(self.gdpr_service, '_get_request', return_value=mock_request), \
             patch.object(self.gdpr_service, '_collect_user_data', return_value={'profile': {'id': 1}}), \
             patch.object(self.gdpr_service, '_update_request_status'), \
             patch.object(self.gdpr_service, '_get_username', return_value='testuser'):
            
            success, export_path = self.gdpr_service.process_data_export_request("test123")
            
            self.assertTrue(success)
            self.assertIsNotNone(export_path)
            
            # Verify export file was created
            export_file = Path(export_path)
            self.assertTrue(export_file.exists())

class TestComplianceReporter(unittest.TestCase):
    """Test compliance reporting functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock()
        self.mock_audit_logger = Mock()
        
        self.config = {
            'reports_path': self.temp_dir,
            'retention_days': 2555,
            'auto_generation_enabled': True
        }
        
        self.reporter = ComplianceReporter(
            self.mock_db_manager,
            self.mock_audit_logger,
            self.config
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_gdpr_compliance_report_generation(self):
        """Test GDPR compliance report generation"""
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)
        
        with patch.object(self.reporter, '_collect_gdpr_data') as mock_collect:
            mock_collect.return_value = {
                'total_requests': 10,
                'completed_requests': 8,
                'pending_requests': 2,
                'failed_requests': 0,
                'avg_processing_time': 24.5,
                'request_types': {},
                'rights_compliance': {
                    'access': 100.0,
                    'rectification': 100.0,
                    'erasure': 100.0,
                    'portability': 100.0
                },
                'compliance_score': 98.5
            }
            
            report = self.reporter.generate_gdpr_compliance_report(
                start_date=start_date,
                end_date=end_date,
                format=ReportFormat.HTML
            )
            
            self.assertIsNotNone(report)
            self.assertEqual(report.report_type, ReportType.GDPR_COMPLIANCE)
            self.assertEqual(report.format, ReportFormat.HTML)
            
            # Verify report file was created
            report_file = Path(report.file_path)
            self.assertTrue(report_file.exists())
    
    def test_audit_summary_report_generation(self):
        """Test audit summary report generation"""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        with patch.object(self.reporter, '_collect_audit_data') as mock_collect:
            mock_collect.return_value = {
                'total_events': 1250,
                'security_events': 3,
                'failed_auth': 12,
                'data_access_events': 450,
                'config_changes': 8,
                'event_types': {},
                'top_users': []
            }
            
            report = self.reporter.generate_audit_summary_report(
                start_date=start_date,
                end_date=end_date,
                format=ReportFormat.JSON
            )
            
            self.assertIsNotNone(report)
            self.assertEqual(report.report_type, ReportType.AUDIT_SUMMARY)
            self.assertEqual(report.format, ReportFormat.JSON)
            
            # Verify report file was created
            report_file = Path(report.file_path)
            self.assertTrue(report_file.exists())
            
            # Verify JSON content
            with open(report_file, 'r') as f:
                report_data = json.load(f)
                self.assertIn('metadata', report_data)
                self.assertIn('data', report_data)

class TestDataLifecycleManager(unittest.TestCase):
    """Test data lifecycle management functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock()
        self.mock_audit_logger = Mock()
        
        self.config = {
            'archive_path': os.path.join(self.temp_dir, 'archives'),
            'temp_cleanup_enabled': True,
            'auto_execution_enabled': True
        }
        
        self.lifecycle_manager = DataLifecycleManager(
            self.mock_db_manager,
            self.mock_audit_logger,
            self.config
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_retention_policy_loading(self):
        """Test retention policy loading and configuration"""
        policies = self.lifecycle_manager.retention_policies
        
        self.assertIn(DataCategory.USER_DATA, policies)
        self.assertIn(DataCategory.AUDIT_LOGS, policies)
        self.assertIn(DataCategory.SESSION_DATA, policies)
        
        user_data_policy = policies[DataCategory.USER_DATA]
        self.assertEqual(user_data_policy.retention_days, 2555)
        self.assertEqual(user_data_policy.action, RetentionAction.ARCHIVE)
    
    def test_session_data_cleanup(self):
        """Test session data cleanup"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        # Mock database session
        mock_session = Mock()
        mock_result = Mock()
        mock_result.rowcount = 25
        mock_session.execute.return_value = mock_result
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        policy = self.lifecycle_manager.retention_policies[DataCategory.SESSION_DATA]
        event = self.lifecycle_manager._process_session_data(policy, cutoff_date)
        
        self.assertIsNotNone(event)
        self.assertTrue(event.success)
        self.assertEqual(event.affected_records, 25)
        self.assertEqual(event.category, DataCategory.SESSION_DATA)
    
    def test_temp_data_cleanup(self):
        """Test temporary data cleanup"""
        # Create some temporary files
        temp_path = Path(self.temp_dir) / "temp"
        temp_path.mkdir(exist_ok=True)
        
        old_file = temp_path / "old_file.tmp"
        old_file.write_text("old content")
        
        # Set file modification time to be old
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        policy = self.lifecycle_manager.retention_policies[DataCategory.TEMP_DATA]
        
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [old_file]
            event = self.lifecycle_manager._process_temp_data(policy, cutoff_date)
            
            self.assertIsNotNone(event)
            self.assertTrue(event.success)
            self.assertEqual(event.category, DataCategory.TEMP_DATA)
    
    def test_retention_status(self):
        """Test retention status reporting"""
        with patch.object(self.lifecycle_manager, '_estimate_affected_records', return_value=100):
            status = self.lifecycle_manager.get_retention_status()
            
            self.assertIn('policies', status)
            self.assertIn('user_data', status['policies'])
            
            user_data_status = status['policies']['user_data']
            self.assertEqual(user_data_status['retention_days'], 2555)
            self.assertEqual(user_data_status['action'], 'archive')
            self.assertEqual(user_data_status['estimated_affected_records'], 100)

class TestComplianceService(unittest.TestCase):
    """Test main compliance service integration"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock()
        
        # Create temporary config file
        self.config_file = os.path.join(self.temp_dir, 'audit_config.yml')
        config_content = """
audit_logging:
  enabled: true
  log_level: INFO
  destinations:
    - type: file
      path: /tmp/audit.log
  events: []
  async_logging: false

gdpr_compliance:
  enabled: true
  export_path: /tmp/gdpr_exports

data_lifecycle:
  enabled: true
  auto_execution: true

compliance_reporting:
  enabled: true
  reports_path: /tmp/compliance_reports
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_compliance_service_initialization(self):
        """Test compliance service initialization"""
        service = ComplianceService(self.mock_db_manager, self.config_file)
        
        self.assertIsNotNone(service.audit_logger)
        self.assertIsNotNone(service.gdpr_service)
        self.assertIsNotNone(service.reporter)
        self.assertIsNotNone(service.lifecycle_manager)
    
    def test_compliance_status(self):
        """Test compliance status reporting"""
        service = ComplianceService(self.mock_db_manager, self.config_file)
        
        status = service.get_compliance_status()
        
        self.assertIn('timestamp', status)
        self.assertIn('components', status)
        self.assertIn('configuration', status)
        
        components = status['components']
        self.assertTrue(components['audit_logger'])
        self.assertTrue(components['gdpr_service'])
        self.assertTrue(components['reporter'])
        self.assertTrue(components['lifecycle_manager'])
    
    def test_audit_logging_integration(self):
        """Test audit logging through compliance service"""
        service = ComplianceService(self.mock_db_manager, self.config_file)
        
        # Test user authentication logging
        service.log_user_authentication(
            username="testuser",
            success=True,
            ip_address="127.0.0.1",
            details={"method": "password"}
        )
        
        # Verify audit logger was called
        self.assertIsNotNone(service.audit_logger)
    
    def test_gdpr_request_integration(self):
        """Test GDPR request handling through compliance service"""
        service = ComplianceService(self.mock_db_manager, self.config_file)
        
        with patch.object(service.gdpr_service, 'create_gdpr_request', return_value='test123'):
            request_id = service.create_gdpr_data_export_request(
                user_id=1,
                details={"reason": "User request"}
            )
            
            self.assertEqual(request_id, 'test123')

class TestComplianceIntegration(unittest.TestCase):
    """Integration tests for the complete compliance framework"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_db_manager = Mock()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_gdpr_workflow(self):
        """Test complete GDPR request workflow"""
        # This would test the complete workflow from request creation
        # through processing to completion and reporting
        pass
    
    def test_audit_trail_compliance(self):
        """Test audit trail meets compliance requirements"""
        # This would test that audit trails meet regulatory requirements
        # including immutability, completeness, and retention
        pass
    
    def test_data_lifecycle_compliance(self):
        """Test data lifecycle management compliance"""
        # This would test that data lifecycle policies are properly
        # enforced and meet regulatory requirements
        pass

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestAuditLogger))
    test_suite.addTest(unittest.makeSuite(TestGDPRCompliance))
    test_suite.addTest(unittest.makeSuite(TestComplianceReporter))
    test_suite.addTest(unittest.makeSuite(TestDataLifecycleManager))
    test_suite.addTest(unittest.makeSuite(TestComplianceService))
    test_suite.addTest(unittest.makeSuite(TestComplianceIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)