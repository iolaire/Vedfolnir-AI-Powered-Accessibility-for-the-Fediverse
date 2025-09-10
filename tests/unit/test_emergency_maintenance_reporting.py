# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Emergency Maintenance Reporting

Tests emergency maintenance reporting functionality including activation logging,
deactivation validation, summary report generation, and comprehensive documentation.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.maintenance.emergency.emergency_maintenance_reporting import (
    EmergencyMaintenanceReporter,
    EmergencyActivationLog,
    EmergencyDeactivationLog,
    EmergencySummaryReport,
    ReportType,
    ReportSeverity
)


class TestEmergencyMaintenanceReporting(unittest.TestCase):
    """Test cases for EmergencyMaintenanceReporter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_emergency_handler = Mock()
        self.mock_job_termination_manager = Mock()
        
        # Create reporter instance
        self.reporter = EmergencyMaintenanceReporter(
            emergency_handler=self.mock_emergency_handler,
            job_termination_manager=self.mock_job_termination_manager
        )
        
        # Mock emergency handler status
        self.mock_emergency_handler.get_emergency_status.return_value = {
            'is_active': True,
            'invalidated_sessions_count': 5,
            'terminated_jobs_count': 3
        }
        
        # Mock job termination manager stats
        self.mock_job_termination_manager.get_termination_statistics.return_value = {
            'statistics': {
                'jobs_terminated': 3,
                'jobs_recovered': 2,
                'termination_failures': 0,
                'recovery_failures': 1,
                'notifications_sent': 3
            },
            'recovery_queue_size': 0,
            'recovery_rate_percent': 66.7
        }
    
    def test_log_emergency_activation_success(self):
        """Test successful emergency activation logging"""
        # Test activation logging
        activation_log = self.reporter.log_emergency_activation(
            activation_id="EMG_001",
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Critical system failure",
            severity=ReportSeverity.CRITICAL,
            affected_systems=["web_app", "database"],
            estimated_duration=60,
            authorization_level="admin",
            contact_information={"primary": "admin@example.com"},
            escalation_path=["team_lead", "manager"]
        )
        
        # Verify activation log
        self.assertIsInstance(activation_log, EmergencyActivationLog)
        self.assertEqual(activation_log.activation_id, "EMG_001")
        self.assertEqual(activation_log.triggered_by, "admin_user")
        self.assertEqual(activation_log.trigger_source, "manual")
        self.assertEqual(activation_log.reason, "Critical system failure")
        self.assertEqual(activation_log.severity, ReportSeverity.CRITICAL)
        self.assertEqual(activation_log.affected_systems, ["web_app", "database"])
        self.assertEqual(activation_log.estimated_duration, 60)
        
        # Verify log is stored
        stored_log = self.reporter._activation_logs.get("EMG_001")
        self.assertIsNotNone(stored_log)
        self.assertEqual(stored_log.activation_id, "EMG_001")
        
        # Verify statistics updated
        self.assertEqual(self.reporter._report_stats['total_activations'], 1)
        self.assertEqual(self.reporter._report_stats['most_common_triggers']['manual'], 1)
        self.assertEqual(self.reporter._report_stats['severity_distribution']['critical'], 1)
    
    def test_log_emergency_deactivation_success(self):
        """Test successful emergency deactivation logging"""
        # First create an activation log
        activation_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        activation_log = EmergencyActivationLog(
            activation_id="EMG_001",
            timestamp=activation_time,
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Test emergency",
            severity=ReportSeverity.HIGH,
            affected_systems=["web_app"],
            estimated_duration=30,
            authorization_level="admin",
            contact_information={},
            escalation_path=[]
        )
        self.reporter._activation_logs["EMG_001"] = activation_log
        
        # Test deactivation logging
        deactivation_log = self.reporter.log_emergency_deactivation(
            deactivation_id="EMD_001",
            activation_id="EMG_001",
            deactivated_by="admin_user",
            resolution_summary="Emergency resolved successfully",
            validation_checks={"system_responsive": True, "database_ok": True},
            lessons_learned=["Improve monitoring"],
            follow_up_actions=["Update procedures"]
        )
        
        # Verify deactivation log
        self.assertIsInstance(deactivation_log, EmergencyDeactivationLog)
        self.assertEqual(deactivation_log.deactivation_id, "EMD_001")
        self.assertEqual(deactivation_log.activation_id, "EMG_001")
        self.assertEqual(deactivation_log.deactivated_by, "admin_user")
        self.assertEqual(deactivation_log.resolution_summary, "Emergency resolved successfully")
        self.assertEqual(deactivation_log.recovery_status, "successful")
        self.assertGreater(deactivation_log.duration_minutes, 25)  # Should be around 30 minutes
        
        # Verify log is stored
        stored_log = self.reporter._deactivation_logs.get("EMD_001")
        self.assertIsNotNone(stored_log)
        
        # Verify statistics updated
        self.assertEqual(self.reporter._report_stats['total_deactivations'], 1)
        self.assertGreater(self.reporter._report_stats['average_emergency_duration'], 0)
    
    def test_log_emergency_deactivation_with_failures(self):
        """Test emergency deactivation logging with validation failures"""
        # Create activation log
        self.reporter._activation_logs["EMG_002"] = EmergencyActivationLog(
            activation_id="EMG_002",
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=15),
            triggered_by="admin_user",
            trigger_source="automated",
            reason="Test emergency",
            severity=ReportSeverity.MEDIUM,
            affected_systems=["web_app"],
            estimated_duration=15,
            authorization_level="admin",
            contact_information={},
            escalation_path=[]
        )
        
        # Test deactivation with failed validation checks
        deactivation_log = self.reporter.log_emergency_deactivation(
            deactivation_id="EMD_002",
            activation_id="EMG_002",
            deactivated_by="admin_user",
            resolution_summary="Emergency resolved with issues",
            validation_checks={
                "system_responsive": True,
                "database_ok": False,
                "session_management": True
            }
        )
        
        # Verify recovery status reflects failures
        self.assertIn("partial_failure", deactivation_log.recovery_status)
        self.assertIn("1 checks failed", deactivation_log.recovery_status)
    
    def test_generate_comprehensive_report_success(self):
        """Test comprehensive report generation"""
        # Setup activation and deactivation logs
        activation_log = self.reporter.log_emergency_activation(
            activation_id="EMG_003",
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Test comprehensive report",
            severity=ReportSeverity.HIGH
        )
        
        deactivation_log = self.reporter.log_emergency_deactivation(
            deactivation_id="EMD_003",
            activation_id="EMG_003",
            deactivated_by="admin_user",
            resolution_summary="Test resolution",
            validation_checks={"all_systems": True}
        )
        
        # Generate comprehensive report
        report = self.reporter.generate_comprehensive_report(
            activation_id="EMG_003",
            report_type=ReportType.SUMMARY,
            generated_by="test_user"
        )
        
        # Verify report structure
        self.assertIsInstance(report, EmergencySummaryReport)
        self.assertTrue(report.report_id.startswith("EMR_EMG_003_"))
        self.assertEqual(report.report_type, ReportType.SUMMARY)
        self.assertEqual(report.generated_by, "test_user")
        self.assertEqual(report.activation_log, activation_log)
        self.assertEqual(report.deactivation_log, deactivation_log)
        
        # Verify report components
        self.assertIsInstance(report.job_termination_summary, dict)
        self.assertIsInstance(report.session_impact_summary, dict)
        self.assertIsInstance(report.system_impact_assessment, dict)
        self.assertIsInstance(report.timeline, list)
        self.assertIsInstance(report.metrics, dict)
        self.assertIsInstance(report.recommendations, list)
        
        # Verify report is stored
        self.assertIn(report.report_id, self.reporter._summary_reports)
        
        # Verify statistics updated
        self.assertEqual(self.reporter._report_stats['total_reports_generated'], 1)
    
    def test_generate_comprehensive_report_no_activation(self):
        """Test comprehensive report generation with missing activation log"""
        # Test report generation for non-existent activation
        with self.assertRaises(ValueError) as context:
            self.reporter.generate_comprehensive_report(
                activation_id="NONEXISTENT",
                report_type=ReportType.SUMMARY,
                generated_by="test_user"
            )
        
        self.assertIn("No activation log found", str(context.exception))
    
    def test_validate_emergency_deactivation_success(self):
        """Test successful emergency deactivation validation"""
        # Mock all validation checks to pass
        self.reporter._check_system_components = Mock(return_value=True)
        self.reporter._check_database_connectivity = Mock(return_value=True)
        self.reporter._check_session_management = Mock(return_value=True)
        self.reporter._check_for_critical_errors = Mock(return_value=True)
        
        # Perform validation
        validation_results = self.reporter.validate_emergency_deactivation("EMG_004")
        
        # Verify all checks passed
        self.assertTrue(validation_results['emergency_handler_active'])
        self.assertTrue(validation_results['no_pending_job_recovery'])
        self.assertTrue(validation_results['system_components_responsive'])
        self.assertTrue(validation_results['database_connectivity'])
        self.assertTrue(validation_results['session_management_operational'])
        self.assertTrue(validation_results['no_critical_errors'])
    
    def test_validate_emergency_deactivation_failures(self):
        """Test emergency deactivation validation with failures"""
        # Mock some validation checks to fail
        self.mock_emergency_handler.get_emergency_status.return_value = {'is_active': False}
        self.mock_job_termination_manager.get_termination_statistics.return_value = {
            'recovery_queue_size': 5
        }
        self.reporter._check_system_components = Mock(return_value=False)
        self.reporter._check_database_connectivity = Mock(return_value=True)
        self.reporter._check_session_management = Mock(return_value=False)
        self.reporter._check_for_critical_errors = Mock(return_value=True)
        
        # Perform validation
        validation_results = self.reporter.validate_emergency_deactivation("EMG_005")
        
        # Verify failed checks
        self.assertFalse(validation_results['emergency_handler_active'])
        self.assertFalse(validation_results['no_pending_job_recovery'])
        self.assertFalse(validation_results['system_components_responsive'])
        self.assertFalse(validation_results['session_management_operational'])
        
        # Verify passed checks
        self.assertTrue(validation_results['database_connectivity'])
        self.assertTrue(validation_results['no_critical_errors'])
    
    def test_export_report_to_json_success(self):
        """Test successful report export to JSON"""
        # Create and generate a report
        self.reporter.log_emergency_activation(
            activation_id="EMG_006",
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Test JSON export"
        )
        
        report = self.reporter.generate_comprehensive_report(
            activation_id="EMG_006",
            generated_by="test_user"
        )
        
        # Export to JSON
        json_output = self.reporter.export_report_to_json(report.report_id)
        
        # Verify JSON is valid
        parsed_json = json.loads(json_output)
        self.assertIsInstance(parsed_json, dict)
        
        # Verify key fields are present
        self.assertEqual(parsed_json['report_type'], 'summary')
        self.assertEqual(parsed_json['generated_by'], 'test_user')
        self.assertIn('activation_log', parsed_json)
        self.assertIn('metrics', parsed_json)
        self.assertIn('recommendations', parsed_json)
    
    def test_export_report_to_json_not_found(self):
        """Test report export with non-existent report"""
        with self.assertRaises(ValueError) as context:
            self.reporter.export_report_to_json("NONEXISTENT_REPORT")
        
        self.assertIn("Report NONEXISTENT_REPORT not found", str(context.exception))
    
    def test_get_reporting_statistics(self):
        """Test reporting statistics collection"""
        # Create some test data
        self.reporter.log_emergency_activation(
            activation_id="EMG_007",
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Test statistics"
        )
        
        self.reporter.log_emergency_activation(
            activation_id="EMG_008",
            triggered_by="system",
            trigger_source="automated",
            reason="Automated emergency"
        )
        
        self.reporter.log_emergency_deactivation(
            deactivation_id="EMD_007",
            activation_id="EMG_007",
            deactivated_by="admin_user",
            resolution_summary="Resolved"
        )
        
        # Get statistics
        stats = self.reporter.get_reporting_statistics()
        
        # Verify statistics
        self.assertEqual(stats['report_statistics']['total_activations'], 2)
        self.assertEqual(stats['report_statistics']['total_deactivations'], 1)
        self.assertEqual(stats['active_emergencies'], 1)  # EMG_008 is still active
        self.assertEqual(stats['total_activation_logs'], 2)
        self.assertEqual(stats['total_deactivation_logs'], 1)
        
        # Verify trigger statistics
        self.assertEqual(stats['report_statistics']['most_common_triggers']['manual'], 1)
        self.assertEqual(stats['report_statistics']['most_common_triggers']['automated'], 1)
    
    def test_job_termination_summary_generation(self):
        """Test job termination summary generation"""
        # Test with job termination manager
        summary = self.reporter._generate_job_termination_summary()
        
        self.assertEqual(summary['status'], 'available')
        self.assertEqual(summary['jobs_terminated'], 3)
        self.assertEqual(summary['jobs_recovered'], 2)
        self.assertEqual(summary['recovery_rate_percent'], 66.7)
        self.assertEqual(summary['notifications_sent'], 3)
    
    def test_job_termination_summary_no_manager(self):
        """Test job termination summary without manager"""
        # Create reporter without job termination manager
        reporter_no_manager = EmergencyMaintenanceReporter(
            emergency_handler=self.mock_emergency_handler,
            job_termination_manager=None
        )
        
        summary = reporter_no_manager._generate_job_termination_summary()
        
        self.assertEqual(summary['status'], 'no_job_manager')
        self.assertIn('not available', summary['details'])
    
    def test_session_impact_summary_generation(self):
        """Test session impact summary generation"""
        summary = self.reporter._generate_session_impact_summary()
        
        self.assertEqual(summary['status'], 'available')
        self.assertEqual(summary['sessions_invalidated'], 5)
        self.assertEqual(summary['impact_assessment'], 'medium')  # 5 sessions is medium impact
    
    def test_system_impact_assessment_generation(self):
        """Test system impact assessment generation"""
        activation_log = EmergencyActivationLog(
            activation_id="EMG_TEST",
            timestamp=datetime.now(timezone.utc),
            triggered_by="test_user",
            trigger_source="manual",
            reason="Test impact assessment",
            severity=ReportSeverity.CRITICAL,
            affected_systems=["web_app", "database", "cache"],
            estimated_duration=60,
            authorization_level="admin",
            contact_information={},
            escalation_path=[]
        )
        
        assessment = self.reporter._generate_system_impact_assessment(activation_log)
        
        self.assertEqual(assessment['severity'], 'critical')
        self.assertEqual(assessment['affected_systems'], ["web_app", "database", "cache"])
        self.assertEqual(assessment['estimated_user_impact'], 'high')  # Critical severity = high impact
        self.assertEqual(assessment['business_impact'], 'service_disruption')
    
    def test_emergency_timeline_generation(self):
        """Test emergency timeline generation"""
        activation_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        deactivation_time = datetime.now(timezone.utc)
        
        activation_log = EmergencyActivationLog(
            activation_id="EMG_TIMELINE",
            timestamp=activation_time,
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Test timeline",
            severity=ReportSeverity.HIGH,
            affected_systems=["web_app"],
            estimated_duration=30,
            authorization_level="admin",
            contact_information={},
            escalation_path=[]
        )
        
        deactivation_log = EmergencyDeactivationLog(
            deactivation_id="EMD_TIMELINE",
            activation_id="EMG_TIMELINE",
            timestamp=deactivation_time,
            deactivated_by="admin_user",
            duration_minutes=30.0,
            resolution_summary="Test resolution",
            validation_checks={},
            recovery_status="successful",
            lessons_learned=[],
            follow_up_actions=[]
        )
        
        timeline = self.reporter._generate_emergency_timeline(activation_log, deactivation_log)
        
        # Verify timeline structure
        self.assertEqual(len(timeline), 2)
        
        # Verify activation event
        activation_event = timeline[0]
        self.assertEqual(activation_event['event'], 'emergency_activated')
        self.assertIn('admin_user', activation_event['description'])
        self.assertEqual(activation_event['details']['severity'], 'high')
        
        # Verify deactivation event
        deactivation_event = timeline[1]
        self.assertEqual(deactivation_event['event'], 'emergency_deactivated')
        self.assertIn('admin_user', deactivation_event['description'])
        self.assertEqual(deactivation_event['details']['duration_minutes'], 30.0)
    
    def test_recommendations_generation(self):
        """Test recommendations generation"""
        # Test with long duration emergency
        activation_log = EmergencyActivationLog(
            activation_id="EMG_RECS",
            timestamp=datetime.now(timezone.utc),
            triggered_by="admin_user",
            trigger_source="manual",
            reason="Test recommendations",
            severity=ReportSeverity.CRITICAL,
            affected_systems=["web_app"],
            estimated_duration=120,
            authorization_level="admin",
            contact_information={},
            escalation_path=[]
        )
        
        deactivation_log = EmergencyDeactivationLog(
            deactivation_id="EMD_RECS",
            activation_id="EMG_RECS",
            timestamp=datetime.now(timezone.utc),
            deactivated_by="admin_user",
            duration_minutes=90.0,  # Long duration
            resolution_summary="Test resolution",
            validation_checks={"system_ok": True, "database_ok": False},  # Failed check
            recovery_status="partial_failure",
            lessons_learned=[],
            follow_up_actions=["Fix database", "Update monitoring"]
        )
        
        recommendations = self.reporter._generate_recommendations(activation_log, deactivation_log)
        
        # Verify recommendations are generated
        self.assertGreater(len(recommendations), 0)
        
        # Check for specific recommendations
        duration_rec = any("faster emergency response" in rec for rec in recommendations)
        self.assertTrue(duration_rec)
        
        critical_rec = any("critical system monitoring" in rec for rec in recommendations)
        self.assertTrue(critical_rec)
        
        validation_rec = any("failed validation checks" in rec for rec in recommendations)
        self.assertTrue(validation_rec)
        
        followup_rec = any("follow-up actions" in rec for rec in recommendations)
        self.assertTrue(followup_rec)


if __name__ == '__main__':
    unittest.main()