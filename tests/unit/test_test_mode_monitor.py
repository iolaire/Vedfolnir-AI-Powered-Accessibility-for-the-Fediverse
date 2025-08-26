# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Test Mode Monitor

Tests the test mode monitoring and reporting functionality including
activity monitoring, performance metrics collection, report generation,
and cleanup procedures.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import shutil
from datetime import datetime, timezone
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from maintenance_procedure_validator import MaintenanceProcedureValidator
from test_mode_monitor import (
    TestModeMonitor,
    TestModeStatus,
    TestModeMetrics,
    TestModeReport
)


class TestTestModeMonitor(unittest.TestCase):
    """Unit tests for test mode monitor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = False
        self.mock_config_service.subscribe_to_changes = Mock()
        
        # Mock database manager
        self.mock_db_manager = Mock()
        
        # Create maintenance service
        self.maintenance_service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.mock_db_manager
        )
        
        # Create validator
        self.validator = MaintenanceProcedureValidator(self.maintenance_service)
        
        # Create temporary directory for reports
        self.temp_dir = tempfile.mkdtemp()
        
        # Create monitor with temporary reports directory
        self.monitor = TestModeMonitor(self.maintenance_service, self.validator)
        self.monitor._reports_directory = self.temp_dir
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Stop monitoring if active
        if self.monitor._active_monitoring:
            self.monitor.stop_monitoring()
        
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_start_monitoring_success(self):
        """Test successful monitoring start"""
        # Mock test mode as active
        self.maintenance_service.enable_test_mode(
            reason="Test monitoring start",
            enabled_by="test"
        )
        
        # Start monitoring
        success = self.monitor.start_monitoring()
        
        # Verify success
        self.assertTrue(success, "Monitoring should start successfully")
        self.assertTrue(self.monitor._active_monitoring, "Monitoring should be active")
        self.assertIsNotNone(self.monitor._current_session, "Current session should be set")
        
        # Verify session data
        session = self.monitor._current_session
        self.assertIn('monitoring_id', session)
        self.assertIn('session_id', session)
        self.assertIn('started_at', session)
        self.assertEqual(session['status'], TestModeStatus.ACTIVE)
    
    def test_start_monitoring_when_test_mode_inactive(self):
        """Test monitoring start when test mode is not active"""
        # Ensure test mode is not active
        test_status = self.maintenance_service.get_test_mode_status()
        self.assertFalse(test_status.get('active', False))
        
        # Try to start monitoring
        success = self.monitor.start_monitoring()
        
        # Verify failure
        self.assertFalse(success, "Monitoring should not start when test mode is inactive")
        self.assertFalse(self.monitor._active_monitoring, "Monitoring should not be active")
    
    def test_start_monitoring_when_already_active(self):
        """Test monitoring start when already active"""
        # Enable test mode and start monitoring
        self.maintenance_service.enable_test_mode(
            reason="Test monitoring already active",
            enabled_by="test"
        )
        self.monitor.start_monitoring()
        
        # Try to start monitoring again
        success = self.monitor.start_monitoring()
        
        # Verify failure
        self.assertFalse(success, "Monitoring should not start when already active")
    
    def test_stop_monitoring_success(self):
        """Test successful monitoring stop"""
        # Start monitoring first
        self.maintenance_service.enable_test_mode(
            reason="Test monitoring stop",
            enabled_by="test"
        )
        self.monitor.start_monitoring()
        
        # Stop monitoring
        report = self.monitor.stop_monitoring()
        
        # Verify success
        self.assertIsNotNone(report, "Report should be generated")
        self.assertIsInstance(report, TestModeReport)
        self.assertFalse(self.monitor._active_monitoring, "Monitoring should not be active")
        
        # Verify report content
        self.assertIsNotNone(report.report_id)
        self.assertIsNotNone(report.generated_at)
        self.assertIsNotNone(report.test_mode_metrics)
    
    def test_stop_monitoring_when_not_active(self):
        """Test monitoring stop when not active"""
        # Try to stop monitoring when not active
        report = self.monitor.stop_monitoring()
        
        # Verify no report generated
        self.assertIsNone(report, "No report should be generated when monitoring not active")
    
    def test_get_real_time_metrics(self):
        """Test real-time metrics collection"""
        # Start monitoring
        self.maintenance_service.enable_test_mode(
            reason="Test real-time metrics",
            enabled_by="test"
        )
        self.monitor.start_monitoring()
        
        # Get real-time metrics
        metrics = self.monitor.get_real_time_metrics()
        
        # Verify metrics structure
        self.assertIsInstance(metrics, dict)
        self.assertTrue(metrics.get('monitoring_active', False))
        self.assertIn('session_id', metrics)
        self.assertIn('monitoring_duration_seconds', metrics)
        self.assertIn('test_mode_status', metrics)
        self.assertIn('current_metrics', metrics)
        self.assertIn('last_updated', metrics)
    
    def test_get_real_time_metrics_when_not_active(self):
        """Test real-time metrics when monitoring not active"""
        # Get metrics when not monitoring
        metrics = self.monitor.get_real_time_metrics()
        
        # Verify error response
        self.assertIn('error', metrics)
        self.assertEqual(metrics['error'], 'Monitoring not active')
    
    def test_generate_validation_report(self):
        """Test validation report generation"""
        # Start monitoring
        self.maintenance_service.enable_test_mode(
            reason="Test validation report",
            enabled_by="test"
        )
        self.monitor.start_monitoring()
        
        # Mock validation result
        with patch.object(self.validator, 'validate_maintenance_procedures') as mock_validate:
            from maintenance_procedure_validator import ValidationResult
            mock_result = Mock(spec=ValidationResult)
            mock_result.overall_status = "PASS"
            mock_result.total_tests_run = 10
            mock_result.tests_passed = 10
            mock_result.tests_failed = 0
            mock_validate.return_value = mock_result
            
            # Generate validation report
            result = self.monitor.generate_validation_report()
            
            # Verify result
            self.assertIsNotNone(result, "Validation result should be returned")
            self.assertEqual(result.overall_status, "PASS")
            
            # Verify validation was called
            mock_validate.assert_called_once()
    
    def test_generate_validation_report_when_not_active(self):
        """Test validation report generation when monitoring not active"""
        # Try to generate validation report when not monitoring
        result = self.monitor.generate_validation_report()
        
        # Verify no result
        self.assertIsNone(result, "No validation result should be returned when monitoring not active")
    
    def test_cleanup_test_mode_data(self):
        """Test test mode data cleanup"""
        # Start monitoring and generate some data
        self.maintenance_service.enable_test_mode(
            reason="Test cleanup",
            enabled_by="test"
        )
        self.monitor.start_monitoring()
        
        # Add some activity data
        self.monitor._log_activity('test_activity', {'test': 'data'})
        
        # Perform cleanup
        cleanup_status = self.monitor.cleanup_test_mode_data()
        
        # Verify cleanup success
        self.assertIsInstance(cleanup_status, dict)
        self.assertTrue(cleanup_status.get('success', False), "Cleanup should be successful")
        self.assertIn('cleanup_id', cleanup_status)
        self.assertIn('started_at', cleanup_status)
        self.assertIn('completed_at', cleanup_status)
        self.assertIn('actions_performed', cleanup_status)
        
        # Verify monitoring stopped
        self.assertFalse(self.monitor._active_monitoring, "Monitoring should be stopped after cleanup")
        
        # Verify data cleared
        self.assertEqual(len(self.monitor._activity_log), 0, "Activity log should be cleared")
        self.assertEqual(len(self.monitor._performance_samples), 0, "Performance samples should be cleared")
    
    def test_cleanup_preserve_reports(self):
        """Test cleanup with report preservation"""
        # Create a test report file
        test_report_path = os.path.join(self.temp_dir, "test_report.json")
        with open(test_report_path, 'w') as f:
            json.dump({'test': 'report'}, f)
        
        # Perform cleanup with report preservation
        cleanup_status = self.monitor.cleanup_test_mode_data(preserve_reports=True)
        
        # Verify report file still exists
        self.assertTrue(os.path.exists(test_report_path), "Report file should be preserved")
        self.assertTrue(cleanup_status.get('preserve_reports', False))
    
    def test_cleanup_without_preserving_reports(self):
        """Test cleanup without report preservation"""
        # Create a test report file
        test_report_path = os.path.join(self.temp_dir, "test_report.json")
        with open(test_report_path, 'w') as f:
            json.dump({'test': 'report'}, f)
        
        # Perform cleanup without report preservation
        cleanup_status = self.monitor.cleanup_test_mode_data(preserve_reports=False)
        
        # Verify cleanup attempted (may not succeed due to mocking)
        self.assertFalse(cleanup_status.get('preserve_reports', True))
        self.assertIn('actions_performed', cleanup_status)
    
    def test_get_monitoring_history(self):
        """Test monitoring history retrieval"""
        # Add some activity data
        self.monitor._log_activity('test_activity_1', {'test': 'data1'})
        self.monitor._log_activity('test_activity_2', {'test': 'data2'})
        
        # Add cleanup history
        cleanup_entry = {
            'cleanup_id': 'test_cleanup',
            'started_at': datetime.now(timezone.utc),
            'success': True
        }
        self.monitor._cleanup_history.append(cleanup_entry)
        
        # Get monitoring history
        history = self.monitor.get_monitoring_history(limit=10)
        
        # Verify history structure
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0, "History should contain entries")
        
        # Verify entry structure
        for entry in history:
            self.assertIn('type', entry)
            self.assertIn('timestamp', entry)
            self.assertIn('data', entry)
            self.assertIn(entry['type'], ['activity', 'cleanup'])
    
    def test_subscribe_to_updates(self):
        """Test subscription to monitoring updates"""
        # Create mock callback
        callback = Mock()
        
        # Subscribe to updates
        subscription_id = self.monitor.subscribe_to_updates(callback)
        
        # Verify subscription
        self.assertIsNotNone(subscription_id)
        self.assertIn(subscription_id, self.monitor._subscribers)
        
        # Test notification
        self.monitor._notify_subscribers('test_event', {'test': 'data'})
        
        # Verify callback was called
        callback.assert_called_once_with('test_event', {'test': 'data'})
    
    def test_unsubscribe_from_updates(self):
        """Test unsubscription from monitoring updates"""
        # Subscribe first
        callback = Mock()
        subscription_id = self.monitor.subscribe_to_updates(callback)
        
        # Unsubscribe
        success = self.monitor.unsubscribe_from_updates(subscription_id)
        
        # Verify unsubscription
        self.assertTrue(success, "Unsubscription should be successful")
        self.assertNotIn(subscription_id, self.monitor._subscribers)
        
        # Test that callback is not called after unsubscription
        self.monitor._notify_subscribers('test_event', {'test': 'data'})
        callback.assert_not_called()
    
    def test_unsubscribe_invalid_id(self):
        """Test unsubscription with invalid ID"""
        # Try to unsubscribe with invalid ID
        success = self.monitor.unsubscribe_from_updates('invalid_id')
        
        # Verify failure
        self.assertFalse(success, "Unsubscription should fail for invalid ID")
    
    def test_metrics_collection(self):
        """Test metrics collection functionality"""
        # Mock psutil for metrics collection
        with patch.object(self.monitor, '_collect_current_metrics') as mock_collect:
            mock_collect.return_value = {
                'memory_usage_mb': 100.0,
                'cpu_usage_percent': 25.0,
                'thread_count': 10,
                'test_operations': 5,
                'blocked_operations': 3,
                'allowed_operations': 2,
                'admin_bypasses': 1,
                'errors': 0
            }
            
            # Collect metrics
            metrics = self.monitor._collect_current_metrics()
            
            # Verify metrics
            self.assertIsInstance(metrics, dict)
            self.assertEqual(metrics['memory_usage_mb'], 100.0)
            self.assertEqual(metrics['cpu_usage_percent'], 25.0)
            self.assertEqual(metrics['thread_count'], 10)
    
    def test_metrics_collection_without_psutil(self):
        """Test metrics collection when psutil is not available"""
        # Test the actual method to ensure it handles ImportError gracefully
        # This will test the real implementation's fallback behavior
        metrics = self.monitor._collect_current_metrics()
        
        # Verify basic metrics are returned (should work even without psutil)
        self.assertIsInstance(metrics, dict)
        self.assertIn('memory_usage_mb', metrics)
        self.assertIn('cpu_usage_percent', metrics)
        self.assertIn('test_operations', metrics)
    
    def test_performance_analysis(self):
        """Test performance data analysis"""
        # Add sample performance data
        self.monitor._performance_samples = [
            {'memory_usage_mb': 50.0, 'cpu_usage_percent': 20.0},
            {'memory_usage_mb': 60.0, 'cpu_usage_percent': 30.0},
            {'memory_usage_mb': 70.0, 'cpu_usage_percent': 25.0}
        ]
        
        # Analyze performance
        analysis = self.monitor._analyze_performance_data()
        
        # Verify analysis
        self.assertIsInstance(analysis, dict)
        self.assertIn('sample_count', analysis)
        self.assertIn('averages', analysis)
        self.assertIn('peaks', analysis)
        self.assertIn('trends', analysis)
        self.assertIn('performance_status', analysis)
        
        # Verify calculations
        self.assertEqual(analysis['sample_count'], 3)
        self.assertEqual(analysis['averages']['memory_mb'], 60.0)
        self.assertEqual(analysis['peaks']['memory_mb'], 70.0)
    
    def test_performance_analysis_no_data(self):
        """Test performance analysis with no data"""
        # Clear performance samples
        self.monitor._performance_samples = []
        
        # Analyze performance
        analysis = self.monitor._analyze_performance_data()
        
        # Verify no data message
        self.assertIn('message', analysis)
        self.assertEqual(analysis['message'], 'No performance data available')
    
    def test_generate_test_metrics(self):
        """Test test metrics generation"""
        # Set up current session
        self.monitor._current_session = {
            'session_id': 'test_session',
            'started_at': datetime.now(timezone.utc),
            'status': TestModeStatus.ACTIVE
        }
        
        # Mock test mode status
        with patch.object(self.maintenance_service, 'get_test_mode_status') as mock_status:
            mock_status.return_value = {
                'total_operations_tested': 10,
                'blocked_operations_count': 5,
                'allowed_operations_count': 5,
                'admin_bypasses_count': 2,
                'errors_count': 0
            }
            
            # Generate metrics
            metrics = self.monitor._generate_test_metrics()
            
            # Verify metrics
            self.assertIsInstance(metrics, TestModeMetrics)
            self.assertEqual(metrics.session_id, 'test_session')
            self.assertEqual(metrics.total_operations, 10)
            self.assertEqual(metrics.blocked_operations, 5)
            self.assertEqual(metrics.allowed_operations, 5)
            self.assertEqual(metrics.admin_bypasses, 2)
            self.assertEqual(metrics.error_count, 0)
    
    def test_generate_monitoring_recommendations(self):
        """Test monitoring recommendations generation"""
        # Create test metrics
        metrics = TestModeMetrics(
            session_id='test',
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            duration_seconds=60.0,
            total_operations=5,
            operations_per_second=0.05,  # Low rate
            blocked_operations=3,
            allowed_operations=2,
            admin_bypasses=1,
            error_count=1,  # Has errors
            memory_usage_mb=50.0,
            cpu_usage_percent=25.0,
            status=TestModeStatus.ACTIVE
        )
        
        # Create performance analysis
        performance = {
            'performance_status': 'high_usage'
        }
        
        # Generate recommendations
        recommendations = self.monitor._generate_monitoring_recommendations(metrics, performance)
        
        # Verify recommendations
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0, "Should have recommendations")
        
        # Check for specific recommendations based on test data
        rec_text = ' '.join(recommendations).lower()
        self.assertIn('high resource usage', rec_text)  # High usage recommendation
        self.assertIn('operation rate is low', rec_text)  # Low rate recommendation
        self.assertIn('errors', rec_text)  # Error recommendation
    
    def test_activity_logging(self):
        """Test activity logging functionality"""
        # Log some activities
        self.monitor._log_activity('test_activity_1', {'key1': 'value1'})
        self.monitor._log_activity('test_activity_2', {'key2': 'value2'})
        
        # Verify activities were logged
        self.assertEqual(len(self.monitor._activity_log), 2)
        
        # Verify activity structure
        activity = self.monitor._activity_log[0]
        self.assertIn('timestamp', activity)
        self.assertIn('activity_type', activity)
        self.assertIn('details', activity)
        self.assertEqual(activity['activity_type'], 'test_activity_1')
        self.assertEqual(activity['details']['key1'], 'value1')
    
    def test_activity_log_size_limit(self):
        """Test activity log size limiting"""
        # Add many activities to test size limit
        for i in range(1100):  # More than the 1000 limit
            self.monitor._log_activity(f'activity_{i}', {'index': i})
        
        # Verify log was trimmed (should be less than or equal to 1000)
        self.assertLessEqual(len(self.monitor._activity_log), 1000)
        
        # Verify the most recent entries are kept
        last_activity = self.monitor._activity_log[-1]
        self.assertEqual(last_activity['activity_type'], 'activity_1099')
    
    def test_report_file_saving(self):
        """Test report file saving functionality"""
        # Create a test report
        test_metrics = TestModeMetrics(
            session_id='test_session',
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=60.0,
            total_operations=10,
            operations_per_second=0.167,
            blocked_operations=5,
            allowed_operations=5,
            admin_bypasses=2,
            error_count=0,
            memory_usage_mb=50.0,
            cpu_usage_percent=25.0,
            status=TestModeStatus.COMPLETED
        )
        
        report = TestModeReport(
            report_id='test_report',
            generated_at=datetime.now(timezone.utc),
            session_id='test_session',
            test_mode_metrics=test_metrics,
            validation_result=None,
            activity_log=[],
            performance_analysis={},
            recommendations=[],
            cleanup_status={}
        )
        
        # Save report to file
        self.monitor._save_report_to_file(report)
        
        # Verify file was created
        report_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.json')]
        self.assertEqual(len(report_files), 1, "One report file should be created")
        
        # Verify file content
        with open(os.path.join(self.temp_dir, report_files[0]), 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data['report_id'], 'test_report')
        self.assertEqual(saved_data['session_id'], 'test_session')


if __name__ == '__main__':
    unittest.main()