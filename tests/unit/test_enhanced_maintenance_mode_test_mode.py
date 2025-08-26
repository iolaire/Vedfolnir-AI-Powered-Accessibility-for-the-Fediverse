# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for Enhanced Maintenance Mode Service Test Mode functionality

Tests the test mode implementation including simulation behavior, logging,
validation reporting, and operation tracking.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone
import uuid

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_maintenance_mode_service import (
    EnhancedMaintenanceModeService, 
    MaintenanceMode, 
    MaintenanceStatus
)
from models import User, UserRole


class TestEnhancedMaintenanceModeTestMode(unittest.TestCase):
    """Test cases for enhanced maintenance mode test mode functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration service
        self.mock_config_service = Mock()
        self.mock_config_service.get_config.return_value = False
        self.mock_config_service.subscribe_to_changes = Mock()
        
        # Mock database manager
        self.mock_db_manager = Mock()
        
        # Create service instance
        self.service = EnhancedMaintenanceModeService(
            config_service=self.mock_config_service,
            db_manager=self.mock_db_manager
        )
        
        # Reset statistics for clean test state
        with self.service._stats_lock:
            self.service._stats = {
                'maintenance_activations': 0,
                'emergency_activations': 0,
                'test_mode_activations': 0,
                'blocked_operations': 0,
                'admin_bypasses': 0,
                'session_invalidations': 0,
                'test_mode_simulated_blocks': 0,
                'test_mode_operation_attempts': 0
            }
        
        # Create test users
        self.admin_user = Mock(spec=User)
        self.admin_user.id = 1
        self.admin_user.username = "admin"
        self.admin_user.role = UserRole.ADMIN
        
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 2
        self.regular_user.username = "user"
        self.regular_user.role = UserRole.REVIEWER
    
    def test_enable_test_mode_success(self):
        """Test successful test mode activation"""
        # Enable test mode
        result = self.service.enable_test_mode(
            reason="Testing maintenance procedures",
            duration=30,
            enabled_by="test_admin"
        )
        
        # Verify success
        self.assertTrue(result, "Test mode should be enabled successfully")
        
        # Verify maintenance status
        status = self.service.get_maintenance_status()
        self.assertTrue(status.is_active, "Maintenance should be active")
        self.assertEqual(status.mode, MaintenanceMode.TEST, "Mode should be TEST")
        self.assertTrue(status.test_mode, "Test mode flag should be True")
        self.assertEqual(status.reason, "Testing maintenance procedures")
        
        # Verify test mode data initialization
        test_status = self.service.get_test_mode_status()
        self.assertTrue(test_status['active'], "Test mode should be active")
        self.assertIsNotNone(test_status['test_session_id'], "Test session ID should be set")
        self.assertEqual(test_status['total_operations_tested'], 0, "No operations tested yet")
    
    def test_test_mode_simulation_recording(self):
        """Test that test mode records operation simulations correctly"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Testing operation blocking",
            enabled_by="test_admin"
        )
        
        # Test operation blocking (should not actually block but record simulation)
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            # Mock operation classification
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Test operation blocking
            is_blocked = self.service.is_operation_blocked('/start_caption_generation', self.regular_user)
            
            # Should not actually block in test mode
            self.assertFalse(is_blocked, "Operations should not be blocked in test mode")
        
        # Verify simulation was recorded
        test_status = self.service.get_test_mode_status()
        self.assertEqual(test_status['total_operations_tested'], 1, "One operation should be recorded")
        self.assertEqual(test_status['blocked_operations_count'], 1, "One blocked operation should be recorded")
        
        # Verify detailed simulation data
        report = self.service.generate_test_mode_report()
        simulations = report['detailed_simulations']
        self.assertEqual(len(simulations), 1, "One simulation should be recorded")
        
        simulation = simulations[0]
        self.assertEqual(simulation['operation'], '/start_caption_generation')
        self.assertEqual(simulation['operation_type'], 'caption_generation')
        self.assertEqual(simulation['user_id'], 2)
        self.assertEqual(simulation['user_role'], 'reviewer')
        self.assertTrue(simulation['would_block'], "Operation should be marked as would block")
        self.assertFalse(simulation['is_admin_bypass'], "Should not be admin bypass")
    
    def test_test_mode_admin_bypass_simulation(self):
        """Test that test mode correctly simulates admin bypasses"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Testing admin bypass",
            enabled_by="test_admin"
        )
        
        # Test admin user operation
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Test admin operation
            is_blocked = self.service.is_operation_blocked('/start_caption_generation', self.admin_user)
            
            # Should not block admin user
            self.assertFalse(is_blocked, "Admin operations should not be blocked")
        
        # Verify admin bypass was recorded
        test_status = self.service.get_test_mode_status()
        self.assertEqual(test_status['admin_bypasses_count'], 1, "One admin bypass should be recorded")
        
        # Verify simulation details
        report = self.service.generate_test_mode_report()
        simulations = report['detailed_simulations']
        self.assertEqual(len(simulations), 1, "One simulation should be recorded")
        
        simulation = simulations[0]
        self.assertEqual(simulation['user_role'], 'admin')
        self.assertTrue(simulation['is_admin_bypass'], "Should be marked as admin bypass")
    
    def test_test_mode_report_generation(self):
        """Test comprehensive test mode report generation"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Comprehensive testing",
            enabled_by="test_admin"
        )
        
        # Simulate multiple operations
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            
            # Test different operation types
            test_operations = [
                ('/start_caption_generation', OperationType.CAPTION_GENERATION, True),
                ('/api/platform/switch', OperationType.PLATFORM_OPERATIONS, True),
                ('/api/status', OperationType.READ_OPERATIONS, False),
                ('/admin/dashboard', OperationType.ADMIN_OPERATIONS, False)
            ]
            
            for operation, op_type, should_block in test_operations:
                mock_classifier.classify_operation.return_value = op_type
                mock_classifier.is_blocked_operation.return_value = should_block
                
                # Test with regular user
                self.service.is_operation_blocked(operation, self.regular_user)
                
                # Test with admin user
                self.service.is_operation_blocked(operation, self.admin_user)
        
        # Generate report
        report = self.service.generate_test_mode_report()
        
        # Verify report structure
        self.assertIn('report_generated_at', report)
        self.assertIn('test_session', report)
        self.assertIn('test_summary', report)
        self.assertIn('operation_type_analysis', report)
        self.assertIn('validation_results', report)
        self.assertIn('performance_metrics', report)
        self.assertIn('detailed_simulations', report)
        
        # Verify test summary
        summary = report['test_summary']
        self.assertEqual(summary['total_operations_tested'], 8, "Should have 8 total operations (4 ops × 2 users)")
        self.assertGreater(summary['blocked_operations_count'], 0, "Should have blocked operations")
        self.assertGreater(summary['admin_bypasses_count'], 0, "Should have admin bypasses")
        
        # Verify operation type analysis
        op_analysis = report['operation_type_analysis']
        self.assertIn('caption_generation', op_analysis)
        self.assertIn('platform_operations', op_analysis)
        self.assertIn('read_operations', op_analysis)
        self.assertIn('admin_operations', op_analysis)
        
        # Verify validation results
        validation = report['validation_results']
        self.assertIn('overall_status', validation)
        self.assertIn('coverage_analysis', validation)
        self.assertIn('blocking_accuracy', validation)
    
    def test_test_mode_validation_results(self):
        """Test test mode validation result generation"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Validation testing",
            enabled_by="test_admin"
        )
        
        # Simulate operations that should be blocked
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            
            # Mock expected blocked operations for TEST mode
            expected_blocked = [
                OperationType.CAPTION_GENERATION,
                OperationType.JOB_CREATION,
                OperationType.PLATFORM_OPERATIONS
            ]
            mock_classifier.get_blocked_operations_for_mode.return_value = expected_blocked
            
            # Test operations that should be blocked
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            self.service.is_operation_blocked('/start_caption_generation', self.regular_user)
            
            # Test operations that should not be blocked
            mock_classifier.classify_operation.return_value = OperationType.READ_OPERATIONS
            mock_classifier.is_blocked_operation.return_value = False
            self.service.is_operation_blocked('/api/status', self.regular_user)
        
        # Generate report and check validation
        report = self.service.generate_test_mode_report()
        validation = report['validation_results']
        
        # Should have validation results
        self.assertIn('overall_status', validation)
        self.assertIn('coverage_analysis', validation)
        self.assertIn('blocking_accuracy', validation)
        
        # Coverage analysis should show tested operation types
        coverage = validation['coverage_analysis']
        self.assertIn('tested_operation_types', coverage)
        self.assertIn('coverage_percentage', coverage)
    
    def test_test_mode_performance_metrics(self):
        """Test test mode performance metrics calculation"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Performance testing",
            enabled_by="test_admin"
        )
        
        # Simulate multiple operations with timing
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Simulate several operations
            for i in range(5):
                self.service.is_operation_blocked(f'/operation_{i}', self.regular_user)
        
        # Generate report and check performance metrics
        report = self.service.generate_test_mode_report()
        metrics = report['performance_metrics']
        
        # Should have performance data
        self.assertIn('total_operations', metrics)
        self.assertIn('test_duration_seconds', metrics)
        self.assertIn('operations_per_second', metrics)
        self.assertIn('performance_status', metrics)
        
        self.assertEqual(metrics['total_operations'], 5, "Should have 5 operations")
        self.assertGreaterEqual(metrics['test_duration_seconds'], 0, "Duration should be non-negative")
    
    def test_test_mode_completion(self):
        """Test test mode completion and final report generation"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Completion testing",
            enabled_by="test_admin"
        )
        
        # Simulate some operations
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            self.service.is_operation_blocked('/test_operation', self.regular_user)
        
        # Complete test mode
        completion_result = self.service.complete_test_mode()
        
        # Verify completion
        self.assertEqual(completion_result['status'], 'completed', "Test mode should be completed")
        self.assertIn('completion_time', completion_result)
        self.assertIn('final_report', completion_result)
        
        # Verify maintenance mode is disabled
        status = self.service.get_maintenance_status()
        self.assertFalse(status.is_active, "Maintenance should be disabled after completion")
        
        # Verify final report
        final_report = completion_result['final_report']
        self.assertIn('test_session', final_report)
        self.assertEqual(final_report['test_session']['status'], 'completed')
    
    def test_test_mode_data_reset(self):
        """Test test mode data reset functionality"""
        # Enable test mode and generate some data
        self.service.enable_test_mode(
            reason="Reset testing",
            enabled_by="test_admin"
        )
        
        # Simulate operation
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            self.service.is_operation_blocked('/test_operation', self.regular_user)
        
        # Verify data exists
        test_status = self.service.get_test_mode_status()
        self.assertEqual(test_status['total_operations_tested'], 1)
        
        # Reset test mode data
        reset_result = self.service.reset_test_mode_data()
        self.assertTrue(reset_result, "Reset should be successful")
        
        # Verify data is reset
        test_status = self.service.get_test_mode_status()
        self.assertFalse(test_status['active'], "Test mode should not be active after reset")
    
    def test_test_mode_error_handling(self):
        """Test test mode error handling and recording"""
        # Enable test mode
        self.service.enable_test_mode(
            reason="Error testing",
            enabled_by="test_admin"
        )
        
        # Simulate error in operation classification
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier_class.side_effect = Exception("Classification error")
            
            # This should handle the error gracefully
            is_blocked = self.service.is_operation_blocked('/error_operation', self.regular_user)
            
            # Should not block on error (fail-safe)
            self.assertFalse(is_blocked, "Should not block on classification error")
        
        # Check that error was recorded
        report = self.service.generate_test_mode_report()
        errors = report['errors']
        self.assertGreater(len(errors), 0, "Should have recorded errors")
        
        error = errors[0]
        self.assertIn('timestamp', error)
        self.assertIn('error', error)
        self.assertIn('operation', error)
    
    def test_test_mode_statistics_tracking(self):
        """Test that test mode statistics are properly tracked"""
        # Check initial statistics
        initial_stats = self.service.get_service_stats()
        initial_test_activations = initial_stats['statistics']['test_mode_activations']
        initial_simulated_blocks = initial_stats['statistics']['test_mode_simulated_blocks']
        initial_operation_attempts = initial_stats['statistics']['test_mode_operation_attempts']
        
        # Enable test mode
        self.service.enable_test_mode(
            reason="Statistics testing",
            enabled_by="test_admin"
        )
        
        # Simulate operations
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Simulate multiple operations
            for i in range(3):
                self.service.is_operation_blocked(f'/operation_{i}', self.regular_user)
        
        # Check updated statistics
        updated_stats = self.service.get_service_stats()
        
        # Verify test mode activation was counted
        self.assertEqual(
            updated_stats['statistics']['test_mode_activations'],
            initial_test_activations + 1,
            "Test mode activation should be counted"
        )
        
        # Verify simulated blocks were counted
        self.assertEqual(
            updated_stats['statistics']['test_mode_simulated_blocks'],
            initial_simulated_blocks + 3,
            "Simulated blocks should be counted"
        )
        
        # Verify operation attempts were counted
        self.assertEqual(
            updated_stats['statistics']['test_mode_operation_attempts'],
            initial_operation_attempts + 3,
            "Operation attempts should be counted"
        )


if __name__ == '__main__':
    unittest.main()