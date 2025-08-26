# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for Maintenance Procedure Validation

Tests the comprehensive validation of maintenance mode functionality through
test mode execution and analysis.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode
from maintenance_procedure_validator import (
    MaintenanceProcedureValidator, 
    ValidationSeverity,
    ValidationResult
)
from models import User, UserRole


class TestMaintenanceProcedureValidation(unittest.TestCase):
    """Integration tests for maintenance procedure validation"""
    
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
    
    def test_comprehensive_validation_execution(self):
        """Test comprehensive validation execution"""
        # Mock operation classifier
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            mock_classifier.get_blocked_operations_for_mode.return_value = [
                OperationType.CAPTION_GENERATION,
                OperationType.JOB_CREATION
            ]
            
            # Run comprehensive validation
            result = self.validator.validate_maintenance_procedures(
                test_duration_minutes=1,
                comprehensive=True
            )
            
            # Verify result structure
            self.assertIsInstance(result, ValidationResult)
            self.assertIsNotNone(result.test_session_id)
            self.assertIsInstance(result.validation_timestamp, datetime)
            self.assertGreaterEqual(result.total_tests_run, 0)
            self.assertIn(result.overall_status, ['PASS', 'FAIL', 'WARNING', 'CRITICAL', 'ERROR'])
            
            # Verify reports are generated
            self.assertIsInstance(result.coverage_report, dict)
            self.assertIsInstance(result.performance_report, dict)
            self.assertIsInstance(result.recommendations, list)
    
    def test_basic_validation_execution(self):
        """Test basic validation execution"""
        # Mock operation classifier
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            mock_classifier.get_blocked_operations_for_mode.return_value = [
                OperationType.CAPTION_GENERATION
            ]
            
            # Run basic validation
            result = self.validator.validate_maintenance_procedures(
                test_duration_minutes=1,
                comprehensive=False
            )
            
            # Verify result
            self.assertIsInstance(result, ValidationResult)
            self.assertGreaterEqual(result.total_tests_run, 0)
            
            # Basic validation should have fewer test categories
            self.assertLessEqual(len(result.coverage_report.get('test_categories', [])), 3)
    
    def test_operation_blocking_validation(self):
        """Test operation blocking validation"""
        # Enable test mode first
        self.maintenance_service.enable_test_mode(
            reason="Testing operation blocking validation",
            enabled_by="test"
        )
        
        # Mock operation classifier
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Test operation blocking validation
            test_results = self.validator._test_operation_blocking()
            
            # Verify test results
            self.assertIsInstance(test_results, list)
            self.assertGreater(len(test_results), 0)
            
            # Check test result structure
            for result in test_results:
                self.assertIn('test_name', result)
                self.assertIn('operation_type', result)
                self.assertIn('endpoint', result)
                self.assertIn('passed', result)
                self.assertIn('timestamp', result)
        
        # Clean up
        self.maintenance_service.complete_test_mode()
    
    def test_admin_bypass_validation(self):
        """Test admin bypass validation"""
        # Enable test mode first
        self.maintenance_service.enable_test_mode(
            reason="Testing admin bypass validation",
            enabled_by="test"
        )
        
        # Mock operation classifier
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Test admin bypass validation
            test_results = self.validator._test_admin_bypass()
            
            # Verify test results
            self.assertIsInstance(test_results, list)
            self.assertGreater(len(test_results), 0)
            
            # Check that admin tests are included
            admin_tests = [r for r in test_results if r.get('user_role') == 'admin']
            self.assertGreater(len(admin_tests), 0)
            
            # Admin tests should pass (not be blocked)
            for admin_test in admin_tests:
                self.assertFalse(admin_test.get('actual_blocked', True), 
                               "Admin operations should not be blocked")
        
        # Clean up
        self.maintenance_service.complete_test_mode()
    
    def test_mode_transitions_validation(self):
        """Test maintenance mode transitions validation"""
        # Enable test mode first
        self.maintenance_service.enable_test_mode(
            reason="Testing mode transitions validation",
            enabled_by="test"
        )
        
        # Test mode transitions validation
        test_results = self.validator._test_mode_transitions()
        
        # Verify test results
        self.assertIsInstance(test_results, list)
        self.assertGreater(len(test_results), 0)
        
        # Check for test mode validation
        test_mode_tests = [r for r in test_results if 'test_mode' in r.get('test_name', '')]
        self.assertGreater(len(test_mode_tests), 0)
        
        # Clean up
        self.maintenance_service.complete_test_mode()
    
    def test_error_handling_validation(self):
        """Test error handling validation"""
        # Enable test mode first
        self.maintenance_service.enable_test_mode(
            reason="Testing error handling validation",
            enabled_by="test"
        )
        
        # Test error handling validation
        test_results = self.validator._test_error_handling()
        
        # Verify test results
        self.assertIsInstance(test_results, list)
        self.assertGreater(len(test_results), 0)
        
        # Check for error handling tests
        error_tests = [r for r in test_results if 'handling' in r.get('test_name', '').lower() or 'invalid' in r.get('test_name', '').lower()]
        self.assertGreater(len(error_tests), 0)
        
        # Clean up
        self.maintenance_service.complete_test_mode()
    
    def test_performance_validation(self):
        """Test performance validation"""
        # Enable test mode first
        self.maintenance_service.enable_test_mode(
            reason="Testing performance validation",
            enabled_by="test"
        )
        
        # Test performance validation
        test_results = self.validator._test_performance_scenarios()
        
        # Verify test results
        self.assertIsInstance(test_results, list)
        self.assertGreater(len(test_results), 0)
        
        # Check for performance tests
        perf_tests = [r for r in test_results if 'performance' in r.get('test_name', '')]
        self.assertGreater(len(perf_tests), 0)
        
        # Performance tests should have timing data
        for perf_test in perf_tests:
            if perf_test.get('passed', False):
                self.assertIn('duration_ms', perf_test)
        
        # Clean up
        self.maintenance_service.complete_test_mode()
    
    def test_coverage_analysis(self):
        """Test test coverage analysis"""
        # Create mock test results
        test_results = {
            'operation_blocking': [
                {
                    'test_name': 'test_caption_generation',
                    'operation_type': 'caption_generation',
                    'passed': True
                },
                {
                    'test_name': 'test_job_creation',
                    'operation_type': 'job_creation',
                    'passed': True
                }
            ],
            'admin_bypass': [
                {
                    'test_name': 'test_admin_bypass',
                    'operation_type': 'platform_operations',
                    'passed': True
                }
            ]
        }
        
        # Analyze coverage
        coverage_report = self.validator._analyze_test_coverage(test_results)
        
        # Verify coverage report
        self.assertIsInstance(coverage_report, dict)
        self.assertIn('total_tests_run', coverage_report)
        self.assertIn('operation_types_tested', coverage_report)
        self.assertIn('coverage_percentage', coverage_report)
        self.assertIn('coverage_status', coverage_report)
        
        # Verify coverage calculation
        self.assertEqual(coverage_report['total_tests_run'], 3)
        self.assertIn('caption_generation', coverage_report['operation_types_tested'])
        self.assertIn('job_creation', coverage_report['operation_types_tested'])
        self.assertIn('platform_operations', coverage_report['operation_types_tested'])
    
    def test_performance_metrics_analysis(self):
        """Test performance metrics analysis"""
        # Enable test mode to generate performance data
        self.maintenance_service.enable_test_mode(
            reason="Testing performance metrics analysis",
            enabled_by="test"
        )
        
        # Simulate some operations to generate performance data
        with patch('maintenance_operation_classifier.MaintenanceOperationClassifier') as mock_classifier_class:
            mock_classifier = Mock()
            mock_classifier_class.return_value = mock_classifier
            
            from maintenance_operation_classifier import OperationType
            mock_classifier.classify_operation.return_value = OperationType.CAPTION_GENERATION
            mock_classifier.is_blocked_operation.return_value = True
            
            # Simulate operations
            regular_user = Mock(spec=User)
            regular_user.role = UserRole.REVIEWER
            
            for i in range(5):
                self.maintenance_service.is_operation_blocked(f'/test_op_{i}', regular_user)
        
        # Analyze performance metrics
        performance_report = self.validator._analyze_performance_metrics()
        
        # Verify performance report
        self.assertIsInstance(performance_report, dict)
        self.assertIn('performance_status', performance_report)
        
        # Clean up
        self.maintenance_service.complete_test_mode()
    
    def test_validation_issues_analysis(self):
        """Test validation issues analysis"""
        # Create mock test results with failures
        test_results = {
            'operation_blocking': [
                {
                    'test_name': 'test_success',
                    'passed': True
                },
                {
                    'test_name': 'test_failure',
                    'passed': False,
                    'endpoint': '/failed_endpoint'
                },
                {
                    'test_name': 'test_error',
                    'passed': False,
                    'error': 'Test error occurred'
                }
            ]
        }
        
        # Analyze validation issues
        issues = self.validator._analyze_validation_issues(test_results)
        
        # Verify issues analysis
        self.assertIsInstance(issues, list)
        self.assertEqual(len(issues), 2)  # Two failed tests
        
        # Check issue structure
        for issue in issues:
            self.assertIn(issue.severity, [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL])
            self.assertIsNotNone(issue.category)
            self.assertIsNotNone(issue.message)
            self.assertIsInstance(issue.details, dict)
            self.assertIsInstance(issue.timestamp, datetime)
    
    def test_recommendations_generation(self):
        """Test recommendations generation"""
        # Create mock issues and coverage report
        from maintenance_procedure_validator import ValidationIssue
        
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="operation_blocking",
                message="Test failed",
                details={},
                timestamp=datetime.now(timezone.utc)
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="performance",
                message="Slow performance",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        coverage_report = {
            'coverage_percentage': 60.0,
            'missing_coverage': ['batch_operations', 'image_processing'],
            'performance_status': 'SLOW'
        }
        
        # Generate recommendations
        recommendations = self.validator._generate_recommendations(issues, coverage_report)
        
        # Verify recommendations
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Check for coverage recommendations
        coverage_recs = [r for r in recommendations if 'coverage' in r.lower()]
        self.assertGreater(len(coverage_recs), 0)
        
        # Check for issue-based recommendations
        issue_recs = [r for r in recommendations if 'error' in r.lower() or 'issue' in r.lower()]
        self.assertGreater(len(issue_recs), 0)
    
    def test_overall_status_calculation(self):
        """Test overall status calculation"""
        from maintenance_procedure_validator import ValidationIssue
        
        # Test with no issues
        no_issues = []
        status = self.validator._calculate_overall_status(no_issues)
        self.assertEqual(status, "PASS")
        
        # Test with warnings only
        warning_issues = [
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="test",
                message="Warning",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
        ]
        status = self.validator._calculate_overall_status(warning_issues)
        self.assertEqual(status, "WARNING")
        
        # Test with errors
        error_issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="test",
                message="Error",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
        ]
        status = self.validator._calculate_overall_status(error_issues)
        self.assertEqual(status, "FAIL")
        
        # Test with critical issues
        critical_issues = [
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="test",
                message="Critical",
                details={},
                timestamp=datetime.now(timezone.utc)
            )
        ]
        status = self.validator._calculate_overall_status(critical_issues)
        self.assertEqual(status, "CRITICAL")
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        # Mock maintenance service to fail
        with patch.object(self.maintenance_service, 'enable_test_mode', return_value=False):
            # Run validation (should handle error gracefully)
            result = self.validator.validate_maintenance_procedures(
                test_duration_minutes=1,
                comprehensive=False
            )
            
            # Verify error result
            self.assertEqual(result.overall_status, "ERROR")
            self.assertEqual(result.tests_failed, 1)
            self.assertGreater(len(result.issues), 0)
            self.assertEqual(result.issues[0].severity, ValidationSeverity.CRITICAL)


if __name__ == '__main__':
    unittest.main()