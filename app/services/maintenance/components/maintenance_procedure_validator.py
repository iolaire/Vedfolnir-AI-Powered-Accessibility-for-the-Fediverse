# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Procedure Validator

Provides comprehensive validation of maintenance mode functionality through
test mode execution and analysis. Validates all maintenance procedures,
operation blocking, and system behavior during maintenance.
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import uuid

from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService, MaintenanceMode
from maintenance_operation_classifier import MaintenanceOperationClassifier, OperationType
from models import User, UserRole

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue found during testing"""
    severity: ValidationSeverity
    category: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    operation_context: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of maintenance procedure validation"""
    overall_status: str  # PASS, FAIL, WARNING
    test_session_id: str
    validation_timestamp: datetime
    total_tests_run: int
    tests_passed: int
    tests_failed: int
    tests_with_warnings: int
    issues: List[ValidationIssue]
    coverage_report: Dict[str, Any]
    performance_report: Dict[str, Any]
    recommendations: List[str]


class MaintenanceProcedureValidator:
    """
    Validates maintenance mode procedures through comprehensive testing
    
    Features:
    - Comprehensive test suite execution
    - Operation blocking validation
    - Admin bypass validation
    - Coverage analysis
    - Performance validation
    - Detailed reporting and recommendations
    """
    
    def __init__(self, maintenance_service: EnhancedMaintenanceModeService):
        """
        Initialize maintenance procedure validator
        
        Args:
            maintenance_service: Enhanced maintenance mode service instance
        """
        self.maintenance_service = maintenance_service
        self.operation_classifier = MaintenanceOperationClassifier()
        
        # Validation state
        self._validation_lock = threading.RLock()
        self._current_validation: Optional[Dict[str, Any]] = None
        
        # Test scenarios
        self._test_scenarios = self._initialize_test_scenarios()
        
        # Validation criteria
        self._validation_criteria = self._initialize_validation_criteria()
    
    def validate_maintenance_procedures(self, 
                                      test_duration_minutes: int = 5,
                                      comprehensive: bool = True) -> ValidationResult:
        """
        Run comprehensive validation of maintenance procedures
        
        Args:
            test_duration_minutes: Duration to run test mode validation
            comprehensive: Whether to run comprehensive tests (all scenarios)
            
        Returns:
            ValidationResult with complete validation report
        """
        try:
            logger.info("Starting comprehensive maintenance procedure validation")
            
            # Initialize validation session
            validation_session_id = str(uuid.uuid4())
            validation_start = datetime.now(timezone.utc)
            
            with self._validation_lock:
                self._current_validation = {
                    'session_id': validation_session_id,
                    'started_at': validation_start,
                    'issues': [],
                    'test_results': {},
                    'coverage_data': {},
                    'performance_data': {}
                }
            
            # Enable test mode
            test_mode_enabled = self.maintenance_service.enable_test_mode(
                reason=f"Comprehensive maintenance procedure validation (session: {validation_session_id})",
                duration=test_duration_minutes,
                enabled_by="maintenance_procedure_validator"
            )
            
            if not test_mode_enabled:
                raise Exception("Failed to enable test mode for validation")
            
            # Run validation test scenarios
            if comprehensive:
                test_results = self._run_comprehensive_validation()
            else:
                test_results = self._run_basic_validation()
            
            # Analyze test results
            coverage_report = self._analyze_test_coverage(test_results)
            performance_report = self._analyze_performance_metrics()
            issues = self._analyze_validation_issues(test_results)
            recommendations = self._generate_recommendations(issues, coverage_report)
            
            # Calculate overall status
            overall_status = self._calculate_overall_status(issues)
            
            # Complete test mode
            completion_result = self.maintenance_service.complete_test_mode()
            
            # Create validation result
            validation_result = ValidationResult(
                overall_status=overall_status,
                test_session_id=validation_session_id,
                validation_timestamp=validation_start,
                total_tests_run=sum(len(scenarios) for scenarios in test_results.values()),
                tests_passed=sum(1 for scenarios in test_results.values() 
                               for result in scenarios if result.get('passed', False)),
                tests_failed=sum(1 for scenarios in test_results.values() 
                               for result in scenarios if not result.get('passed', True)),
                tests_with_warnings=len([issue for issue in issues 
                                       if issue.severity == ValidationSeverity.WARNING]),
                issues=issues,
                coverage_report=coverage_report,
                performance_report=performance_report,
                recommendations=recommendations
            )
            
            logger.info(f"Maintenance procedure validation completed: {overall_status}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during maintenance procedure validation: {str(e)}")
            
            # Create error result
            return ValidationResult(
                overall_status="ERROR",
                test_session_id=validation_session_id if 'validation_session_id' in locals() else "unknown",
                validation_timestamp=datetime.now(timezone.utc),
                total_tests_run=0,
                tests_passed=0,
                tests_failed=1,
                tests_with_warnings=0,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="validation_error",
                    message=f"Validation failed with error: {str(e)}",
                    details={'error': str(e)},
                    timestamp=datetime.now(timezone.utc)
                )],
                coverage_report={},
                performance_report={},
                recommendations=["Fix validation error and retry"]
            )
    
    def _run_comprehensive_validation(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run comprehensive validation test scenarios
        
        Returns:
            Dictionary with test results by category
        """
        test_results = {}
        
        # Test operation blocking
        test_results['operation_blocking'] = self._test_operation_blocking()
        
        # Test admin bypass functionality
        test_results['admin_bypass'] = self._test_admin_bypass()
        
        # Test maintenance mode transitions
        test_results['mode_transitions'] = self._test_mode_transitions()
        
        # Test error handling
        test_results['error_handling'] = self._test_error_handling()
        
        # Test performance under load
        test_results['performance'] = self._test_performance_scenarios()
        
        return test_results
    
    def _run_basic_validation(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run basic validation test scenarios
        
        Returns:
            Dictionary with basic test results
        """
        test_results = {}
        
        # Basic operation blocking tests
        test_results['operation_blocking'] = self._test_operation_blocking()
        
        # Basic admin bypass tests
        test_results['admin_bypass'] = self._test_admin_bypass()
        
        return test_results
    
    def _test_operation_blocking(self) -> List[Dict[str, Any]]:
        """
        Test operation blocking functionality
        
        Returns:
            List of test results
        """
        test_results = []
        
        # Create test users
        regular_user = self._create_mock_user(UserRole.REVIEWER)
        
        # Test each operation type
        for operation_type in OperationType:
            if operation_type in [OperationType.ADMIN_OPERATIONS, OperationType.AUTHENTICATION]:
                continue  # Skip operations that should never be blocked
            
            # Get test endpoints for this operation type
            test_endpoints = self._get_test_endpoints_for_operation_type(operation_type)
            
            for endpoint in test_endpoints:
                try:
                    # Test operation blocking
                    is_blocked = self.maintenance_service.is_operation_blocked(endpoint, regular_user)
                    
                    # In test mode, operations should not actually be blocked
                    expected_blocked = False  # Test mode doesn't actually block
                    
                    test_result = {
                        'test_name': f'operation_blocking_{operation_type.value}_{endpoint}',
                        'operation_type': operation_type.value,
                        'endpoint': endpoint,
                        'user_role': 'reviewer',
                        'expected_blocked': expected_blocked,
                        'actual_blocked': is_blocked,
                        'passed': is_blocked == expected_blocked,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    test_results.append(test_result)
                    
                except Exception as e:
                    test_results.append({
                        'test_name': f'operation_blocking_{operation_type.value}_{endpoint}',
                        'operation_type': operation_type.value,
                        'endpoint': endpoint,
                        'error': str(e),
                        'passed': False,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
        
        return test_results
    
    def _test_admin_bypass(self) -> List[Dict[str, Any]]:
        """
        Test admin bypass functionality
        
        Returns:
            List of test results
        """
        test_results = []
        
        # Create admin user
        admin_user = self._create_mock_user(UserRole.ADMIN)
        
        # Test admin bypass for blocked operations
        blocked_operation_types = [
            OperationType.CAPTION_GENERATION,
            OperationType.JOB_CREATION,
            OperationType.PLATFORM_OPERATIONS,
            OperationType.BATCH_OPERATIONS,
            OperationType.USER_DATA_MODIFICATION,
            OperationType.IMAGE_PROCESSING
        ]
        
        for operation_type in blocked_operation_types:
            test_endpoints = self._get_test_endpoints_for_operation_type(operation_type)
            
            for endpoint in test_endpoints[:2]:  # Test first 2 endpoints per type
                try:
                    # Test admin bypass
                    is_blocked = self.maintenance_service.is_operation_blocked(endpoint, admin_user)
                    
                    # Admin operations should never be blocked
                    expected_blocked = False
                    
                    test_result = {
                        'test_name': f'admin_bypass_{operation_type.value}_{endpoint}',
                        'operation_type': operation_type.value,
                        'endpoint': endpoint,
                        'user_role': 'admin',
                        'expected_blocked': expected_blocked,
                        'actual_blocked': is_blocked,
                        'passed': is_blocked == expected_blocked,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    test_results.append(test_result)
                    
                except Exception as e:
                    test_results.append({
                        'test_name': f'admin_bypass_{operation_type.value}_{endpoint}',
                        'operation_type': operation_type.value,
                        'endpoint': endpoint,
                        'error': str(e),
                        'passed': False,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
        
        return test_results
    
    def _test_mode_transitions(self) -> List[Dict[str, Any]]:
        """
        Test maintenance mode transitions
        
        Returns:
            List of test results
        """
        test_results = []
        
        try:
            # Test current mode is TEST
            status = self.maintenance_service.get_maintenance_status()
            
            test_results.append({
                'test_name': 'test_mode_active',
                'expected_mode': 'test',
                'actual_mode': status.mode.value,
                'expected_test_mode': True,
                'actual_test_mode': status.test_mode,
                'passed': status.mode == MaintenanceMode.TEST and status.test_mode,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Test maintenance status reporting
            test_results.append({
                'test_name': 'maintenance_status_reporting',
                'is_active': status.is_active,
                'has_reason': status.reason is not None,
                'has_started_at': status.started_at is not None,
                'passed': status.is_active and status.reason and status.started_at,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            test_results.append({
                'test_name': 'mode_transitions_error',
                'error': str(e),
                'passed': False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        return test_results
    
    def _test_error_handling(self) -> List[Dict[str, Any]]:
        """
        Test error handling scenarios
        
        Returns:
            List of test results
        """
        test_results = []
        
        try:
            # Test operation blocking with invalid operation
            is_blocked = self.maintenance_service.is_operation_blocked(
                '/invalid/nonexistent/endpoint', 
                self._create_mock_user(UserRole.REVIEWER)
            )
            
            # Should not block unknown operations (fail-safe behavior)
            test_results.append({
                'test_name': 'invalid_operation_handling',
                'endpoint': '/invalid/nonexistent/endpoint',
                'expected_blocked': False,
                'actual_blocked': is_blocked,
                'passed': not is_blocked,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Test operation blocking with None user
            is_blocked_no_user = self.maintenance_service.is_operation_blocked(
                '/start_caption_generation', 
                None
            )
            
            test_results.append({
                'test_name': 'none_user_handling',
                'endpoint': '/start_caption_generation',
                'user': None,
                'expected_blocked': False,  # Test mode doesn't actually block
                'actual_blocked': is_blocked_no_user,
                'passed': not is_blocked_no_user,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            test_results.append({
                'test_name': 'error_handling_test_failed',
                'error': str(e),
                'passed': False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        return test_results
    
    def _test_performance_scenarios(self) -> List[Dict[str, Any]]:
        """
        Test performance under various scenarios
        
        Returns:
            List of test results
        """
        test_results = []
        
        try:
            # Test rapid operation checking
            start_time = datetime.now(timezone.utc)
            regular_user = self._create_mock_user(UserRole.REVIEWER)
            
            # Perform multiple rapid checks
            for i in range(10):
                self.maintenance_service.is_operation_blocked(
                    f'/test_operation_{i}', 
                    regular_user
                )
            
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Should complete within reasonable time (< 100ms for 10 operations)
            performance_acceptable = duration_ms < 100
            
            test_results.append({
                'test_name': 'rapid_operation_checking_performance',
                'operations_count': 10,
                'duration_ms': duration_ms,
                'avg_duration_per_operation_ms': duration_ms / 10,
                'performance_acceptable': performance_acceptable,
                'passed': performance_acceptable,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            test_results.append({
                'test_name': 'performance_test_failed',
                'error': str(e),
                'passed': False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        return test_results
    
    def _analyze_test_coverage(self, test_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Analyze test coverage across operation types and scenarios
        
        Args:
            test_results: Test results by category
            
        Returns:
            Coverage analysis report
        """
        try:
            # Count tested operation types
            tested_operation_types = set()
            total_tests = 0
            
            for category, results in test_results.items():
                total_tests += len(results)
                for result in results:
                    if 'operation_type' in result:
                        tested_operation_types.add(result['operation_type'])
            
            # Get all expected operation types (excluding admin and auth)
            all_operation_types = set(op.value for op in OperationType 
                                    if op not in [OperationType.ADMIN_OPERATIONS, 
                                                 OperationType.AUTHENTICATION,
                                                 OperationType.UNKNOWN])
            
            # Calculate coverage
            coverage_percentage = len(tested_operation_types) / len(all_operation_types) * 100
            missing_coverage = all_operation_types - tested_operation_types
            
            return {
                'total_tests_run': total_tests,
                'operation_types_tested': list(tested_operation_types),
                'operation_types_expected': list(all_operation_types),
                'coverage_percentage': coverage_percentage,
                'missing_coverage': list(missing_coverage),
                'test_categories': list(test_results.keys()),
                'coverage_status': 'GOOD' if coverage_percentage >= 80 else 'NEEDS_IMPROVEMENT'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing test coverage: {str(e)}")
            return {
                'error': str(e),
                'coverage_status': 'ERROR'
            }
    
    def _analyze_performance_metrics(self) -> Dict[str, Any]:
        """
        Analyze performance metrics from test mode
        
        Returns:
            Performance analysis report
        """
        try:
            # Get test mode status for performance data
            test_status = self.maintenance_service.get_test_mode_status()
            
            if not test_status.get('active', False):
                return {'message': 'Test mode not active, no performance data available'}
            
            # Generate test mode report for detailed metrics
            test_report = self.maintenance_service.generate_test_mode_report()
            performance_metrics = test_report.get('performance_metrics', {})
            
            # Analyze performance
            performance_status = 'GOOD'
            issues = []
            
            if 'operations_per_second' in performance_metrics:
                ops_per_sec = performance_metrics['operations_per_second']
                if ops_per_sec < 0.1:
                    performance_status = 'SLOW'
                    issues.append('Low operation processing rate')
            
            return {
                'test_session_id': test_status.get('test_session_id'),
                'total_operations_tested': test_status.get('total_operations_tested', 0),
                'duration_seconds': test_status.get('duration_seconds', 0),
                'performance_metrics': performance_metrics,
                'performance_status': performance_status,
                'performance_issues': issues
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance metrics: {str(e)}")
            return {
                'error': str(e),
                'performance_status': 'ERROR'
            }
    
    def _analyze_validation_issues(self, test_results: Dict[str, List[Dict[str, Any]]]) -> List[ValidationIssue]:
        """
        Analyze test results and identify validation issues
        
        Args:
            test_results: Test results by category
            
        Returns:
            List of validation issues
        """
        issues = []
        
        try:
            for category, results in test_results.items():
                for result in results:
                    if not result.get('passed', True):
                        # Determine severity
                        severity = ValidationSeverity.ERROR
                        if 'error' in result:
                            severity = ValidationSeverity.CRITICAL
                        elif category == 'performance':
                            severity = ValidationSeverity.WARNING
                        
                        # Create validation issue
                        issue = ValidationIssue(
                            severity=severity,
                            category=category,
                            message=f"Test failed: {result.get('test_name', 'unknown')}",
                            details=result,
                            timestamp=datetime.now(timezone.utc),
                            operation_context=result.get('endpoint')
                        )
                        
                        issues.append(issue)
            
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing validation issues: {str(e)}")
            return [ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="analysis_error",
                message=f"Failed to analyze validation issues: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.now(timezone.utc)
            )]
    
    def _generate_recommendations(self, issues: List[ValidationIssue], 
                                coverage_report: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on validation results
        
        Args:
            issues: List of validation issues
            coverage_report: Coverage analysis report
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        try:
            # Coverage recommendations
            coverage_percentage = coverage_report.get('coverage_percentage', 0)
            if coverage_percentage < 80:
                recommendations.append(
                    f"Improve test coverage: {coverage_percentage:.1f}% coverage is below recommended 80%"
                )
            
            missing_coverage = coverage_report.get('missing_coverage', [])
            if missing_coverage:
                recommendations.append(
                    f"Add tests for missing operation types: {', '.join(missing_coverage)}"
                )
            
            # Issue-based recommendations
            critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
            if critical_issues:
                recommendations.append(
                    f"Address {len(critical_issues)} critical issues before deploying maintenance mode"
                )
            
            error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
            if error_issues:
                recommendations.append(
                    f"Fix {len(error_issues)} error-level issues to improve maintenance mode reliability"
                )
            
            warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
            if warning_issues:
                recommendations.append(
                    f"Review {len(warning_issues)} warning-level issues for potential improvements"
                )
            
            # Performance recommendations
            performance_status = coverage_report.get('performance_status')
            if performance_status == 'SLOW':
                recommendations.append(
                    "Optimize maintenance mode performance - operation checking is slower than expected"
                )
            
            # General recommendations
            if not issues and coverage_percentage >= 80:
                recommendations.append(
                    "Maintenance mode validation passed - system is ready for production use"
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return [f"Error generating recommendations: {str(e)}"]
    
    def _calculate_overall_status(self, issues: List[ValidationIssue]) -> str:
        """
        Calculate overall validation status based on issues
        
        Args:
            issues: List of validation issues
            
        Returns:
            Overall status string
        """
        if not issues:
            return "PASS"
        
        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            return "CRITICAL"
        
        # Check for error issues
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        if error_issues:
            return "FAIL"
        
        # Only warnings
        warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        if warning_issues:
            return "WARNING"
        
        return "PASS"
    
    def _initialize_test_scenarios(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Initialize test scenarios for validation
        
        Returns:
            Dictionary of test scenarios by category
        """
        return {
            'operation_blocking': [
                {'operation_type': 'caption_generation', 'endpoints': ['/start_caption_generation']},
                {'operation_type': 'job_creation', 'endpoints': ['/api/jobs']},
                {'operation_type': 'platform_operations', 'endpoints': ['/api/switch_platform']},
                {'operation_type': 'batch_operations', 'endpoints': ['/api/batch_review']},
                {'operation_type': 'user_data_modification', 'endpoints': ['/api/user_settings']},
                {'operation_type': 'image_processing', 'endpoints': ['/api/image_upload']}
            ],
            'admin_bypass': [
                {'user_role': 'admin', 'should_bypass': True},
                {'user_role': 'reviewer', 'should_bypass': False}
            ],
            'error_handling': [
                {'scenario': 'invalid_endpoint', 'endpoint': '/invalid/endpoint'},
                {'scenario': 'none_user', 'user': None}
            ]
        }
    
    def _initialize_validation_criteria(self) -> Dict[str, Any]:
        """
        Initialize validation criteria and thresholds
        
        Returns:
            Dictionary of validation criteria
        """
        return {
            'coverage_threshold': 80.0,  # Minimum coverage percentage
            'performance_threshold_ms': 10.0,  # Maximum response time per operation
            'error_threshold': 0,  # Maximum allowed errors
            'warning_threshold': 5  # Maximum allowed warnings
        }
    
    def _get_test_endpoints_for_operation_type(self, operation_type: OperationType) -> List[str]:
        """
        Get test endpoints for a specific operation type
        
        Args:
            operation_type: Operation type to get endpoints for
            
        Returns:
            List of test endpoints
        """
        endpoint_map = {
            OperationType.CAPTION_GENERATION: [
                '/start_caption_generation',
                '/api/caption/generate',
                '/generate_captions'
            ],
            OperationType.JOB_CREATION: [
                '/api/jobs',
                '/create_job',
                '/queue_job'
            ],
            OperationType.PLATFORM_OPERATIONS: [
                '/api/switch_platform',
                '/api/add_platform',
                '/platform_management'
            ],
            OperationType.BATCH_OPERATIONS: [
                '/api/batch_review',
                '/bulk_operations',
                '/batch_process'
            ],
            OperationType.USER_DATA_MODIFICATION: [
                '/api/user_settings',
                '/profile_update',
                '/caption_settings'
            ],
            OperationType.IMAGE_PROCESSING: [
                '/api/image_upload',
                '/api/update_caption',
                '/image_process'
            ],
            OperationType.READ_OPERATIONS: [
                '/api/status',
                '/api/health',
                '/static/css/style.css'
            ]
        }
        
        return endpoint_map.get(operation_type, [f'/test_{operation_type.value}'])
    
    def _create_mock_user(self, role: UserRole) -> User:
        """
        Create a mock user for testing
        
        Args:
            role: User role to create
            
        Returns:
            Mock user object
        """
        from unittest.mock import Mock
        
        user = Mock(spec=User)
        user.id = 1 if role == UserRole.ADMIN else 2
        user.username = "admin" if role == UserRole.ADMIN else "reviewer"
        user.role = role
        
        return user