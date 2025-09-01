#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Security Test Runner for Notification System

Executes all security tests for the notification system migration and provides
detailed reporting on security validation results. Covers authentication,
authorization, input validation, XSS prevention, rate limiting, and abuse detection.
"""

import unittest
import sys
import os
import time
import json
from datetime import datetime, timezone
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import all security test modules
from test_notification_authentication_authorization import TestNotificationAuthenticationAuthorization
from test_notification_security_validation import (
    TestNotificationInputValidation,
    TestNotificationXSSPrevention, 
    TestNotificationRateLimiting,
    TestNotificationSecurityIntegration
)
from test_notification_abuse_detection import TestNotificationAbuseDetection

# Import enhanced security test modules
from test_notification_authentication_security import TestNotificationAuthenticationSecurity
from test_notification_authorization_security import TestNotificationAuthorizationSecurity
from test_notification_input_validation_security import TestNotificationInputValidationSecurity
from test_notification_xss_prevention_security import TestNotificationXSSPreventionSecurity
from test_notification_rate_limiting_security import TestNotificationRateLimitingSecurity


class SecurityTestResult:
    """Container for security test results"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.test_results = {}
        self.security_coverage = {}
        self.performance_metrics = {}
        
    def add_test_result(self, test_name, status, duration, error_message=None):
        """Add individual test result"""
        self.test_results[test_name] = {
            'status': status,
            'duration': duration,
            'error_message': error_message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.total_tests += 1
        if status == 'PASS':
            self.passed_tests += 1
        elif status == 'FAIL':
            self.failed_tests += 1
        elif status == 'ERROR':
            self.error_tests += 1
        elif status == 'SKIP':
            self.skipped_tests += 1
    
    def calculate_coverage(self):
        """Calculate security coverage metrics"""
        # Define security requirement categories
        security_categories = {
            'authentication': [
                'test_admin_role_permissions',
                'test_moderator_role_permissions', 
                'test_reviewer_role_permissions',
                'test_viewer_role_permissions',
                'test_websocket_authentication_integration',
                'test_authentication_token_validation'
            ],
            'authorization': [
                'test_namespace_authorization_admin',
                'test_namespace_authorization_non_admin',
                'test_message_routing_authorization',
                'test_unauthorized_access_prevention',
                'test_privilege_escalation_prevention',
                'test_cross_user_access_prevention'
            ],
            'input_validation': [
                'test_title_length_validation',
                'test_message_length_validation',
                'test_data_field_validation',
                'test_url_validation_in_action_urls',
                'test_json_serialization_safety'
            ],
            'xss_prevention': [
                'test_html_tag_sanitization',
                'test_javascript_injection_prevention',
                'test_html_entity_encoding',
                'test_attribute_value_encoding',
                'test_javascript_context_encoding',
                'test_css_context_encoding',
                'test_url_context_encoding',
                'test_content_security_policy_compliance'
            ],
            'rate_limiting': [
                'test_user_rate_limiting',
                'test_role_based_rate_limiting',
                'test_priority_based_rate_limiting',
                'test_burst_detection',
                'test_ip_based_rate_limiting',
                'test_rate_limit_recovery'
            ],
            'abuse_detection': [
                'test_content_similarity_detection',
                'test_frequency_analysis_detection',
                'test_behavioral_pattern_analysis',
                'test_coordinated_attack_detection',
                'test_session_hijacking_detection',
                'test_privilege_escalation_detection',
                'test_automated_threat_response'
            ]
        }
        
        # Calculate coverage for each category
        for category, required_tests in security_categories.items():
            passed_tests = 0
            total_tests = len(required_tests)
            
            for test_name in required_tests:
                # Find test in results (may have class prefix)
                for result_name, result in self.test_results.items():
                    if test_name in result_name and result['status'] == 'PASS':
                        passed_tests += 1
                        break
            
            coverage_percentage = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            self.security_coverage[category] = {
                'passed': passed_tests,
                'total': total_tests,
                'percentage': coverage_percentage
            }
    
    def generate_report(self):
        """Generate comprehensive security test report"""
        self.calculate_coverage()
        
        report = {
            'summary': {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'duration': (self.end_time - self.start_time) if self.start_time and self.end_time else 0,
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'error_tests': self.error_tests,
                'skipped_tests': self.skipped_tests,
                'success_rate': (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
            },
            'security_coverage': self.security_coverage,
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'compliance_status': self._assess_compliance_status()
        }
        
        return report
    
    def _assess_compliance_status(self):
        """Assess overall security compliance status"""
        compliance = {
            'overall_status': 'PASS',
            'critical_failures': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check for critical security failures
        critical_tests = [
            'test_admin_role_permissions',
            'test_javascript_injection_prevention',
            'test_unauthorized_access_prevention',
            'test_privilege_escalation_prevention'
        ]
        
        for test_name in critical_tests:
            for result_name, result in self.test_results.items():
                if test_name in result_name and result['status'] in ['FAIL', 'ERROR']:
                    compliance['critical_failures'].append({
                        'test': result_name,
                        'status': result['status'],
                        'error': result.get('error_message', 'Unknown error')
                    })
                    compliance['overall_status'] = 'FAIL'
        
        # Check coverage thresholds
        for category, coverage in self.security_coverage.items():
            if coverage['percentage'] < 80:
                compliance['warnings'].append(
                    f"Low coverage in {category}: {coverage['percentage']:.1f}% "
                    f"({coverage['passed']}/{coverage['total']} tests passed)"
                )
            elif coverage['percentage'] < 100:
                compliance['recommendations'].append(
                    f"Improve {category} coverage: {coverage['percentage']:.1f}% "
                    f"({coverage['passed']}/{coverage['total']} tests passed)"
                )
        
        return compliance


class SecurityTestRunner:
    """Comprehensive security test runner"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.result = SecurityTestResult()
        
    def run_all_security_tests(self):
        """Run all security tests and collect results"""
        print("🔒 Starting Comprehensive Notification Security Test Suite")
        print("=" * 70)
        
        self.result.start_time = time.time()
        
        # Define test suites
        test_suites = [
            ('Authentication & Authorization', TestNotificationAuthenticationAuthorization),
            ('Enhanced Authentication', TestNotificationAuthenticationSecurity),
            ('Enhanced Authorization', TestNotificationAuthorizationSecurity),
            ('Input Validation', TestNotificationInputValidation),
            ('Enhanced Input Validation', TestNotificationInputValidationSecurity),
            ('XSS Prevention', TestNotificationXSSPrevention),
            ('Enhanced XSS Prevention', TestNotificationXSSPreventionSecurity),
            ('Rate Limiting', TestNotificationRateLimiting),
            ('Enhanced Rate Limiting', TestNotificationRateLimitingSecurity),
            ('Security Integration', TestNotificationSecurityIntegration),
            ('Abuse Detection', TestNotificationAbuseDetection)
        ]
        
        overall_success = True
        
        for suite_name, test_class in test_suites:
            print(f"\n📋 Running {suite_name} Tests...")
            print("-" * 50)
            
            success = self._run_test_suite(suite_name, test_class)
            if not success:
                overall_success = False
        
        self.result.end_time = time.time()
        
        # Generate and display report
        self._display_summary_report()
        
        return overall_success
    
    def _run_test_suite(self, suite_name, test_class):
        """Run individual test suite"""
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_class)
        
        # Capture test output
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=2 if self.verbose else 1
        )
        
        # Run tests
        suite_start_time = time.time()
        test_result = runner.run(suite)
        suite_duration = time.time() - suite_start_time
        
        # Process results
        success = test_result.wasSuccessful()
        
        # Get all test methods from the test class
        all_test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        # Record individual test results with actual method names
        failed_tests = set()
        for test, error in test_result.failures + test_result.errors:
            test_name = f"{test_class.__name__}.{test._testMethodName}"
            status = 'FAIL' if (test, error) in test_result.failures else 'ERROR'
            self.result.add_test_result(test_name, status, 0, str(error))
            failed_tests.add(test._testMethodName)
        
        # Record successful tests with actual method names
        avg_test_duration = suite_duration / len(all_test_methods) if all_test_methods else 0
        
        for method_name in all_test_methods:
            if method_name not in failed_tests:
                test_name = f"{test_class.__name__}.{method_name}"
                self.result.add_test_result(test_name, 'PASS', avg_test_duration)
        
        # Calculate actual counts
        total_run = len(all_test_methods)
        failed_count = len(failed_tests)
        passed_count = total_run - failed_count
        
        # Display suite results
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {suite_name}: {passed_count}/{total_run} tests passed "
              f"({suite_duration:.2f}s)")
        
        if not success and self.verbose:
            print("   Failures:")
            for test, error in test_result.failures:
                print(f"   - {test._testMethodName}: FAIL")
            for test, error in test_result.errors:
                print(f"   - {test._testMethodName}: ERROR")
        
        return success
    
    def _display_summary_report(self):
        """Display comprehensive summary report"""
        report = self.result.generate_report()
        
        print("\n" + "=" * 70)
        print("🔒 SECURITY TEST SUMMARY REPORT")
        print("=" * 70)
        
        # Overall summary
        summary = report['summary']
        print(f"📊 Test Execution Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']} ✅")
        print(f"   Failed: {summary['failed_tests']} ❌")
        print(f"   Errors: {summary['error_tests']} ⚠️")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Duration: {summary['duration']:.2f} seconds")
        
        # Security coverage
        print(f"\n🛡️ Security Coverage Analysis:")
        for category, coverage in report['security_coverage'].items():
            percentage = coverage['percentage']
            status_icon = "✅" if percentage >= 90 else "⚠️" if percentage >= 70 else "❌"
            print(f"   {status_icon} {category.replace('_', ' ').title()}: "
                  f"{percentage:.1f}% ({coverage['passed']}/{coverage['total']})")
        
        # Compliance status
        compliance = report['compliance_status']
        print(f"\n🔐 Security Compliance Status: {compliance['overall_status']}")
        
        if compliance['critical_failures']:
            print("   ❌ Critical Security Failures:")
            for failure in compliance['critical_failures']:
                print(f"      - {failure['test']}: {failure['status']}")
        
        if compliance['warnings']:
            print("   ⚠️ Security Warnings:")
            for warning in compliance['warnings']:
                print(f"      - {warning}")
        
        if compliance['recommendations']:
            print("   💡 Recommendations:")
            for recommendation in compliance['recommendations']:
                print(f"      - {recommendation}")
        
        # Requirements compliance
        print(f"\n📋 Requirements Compliance:")
        requirements = [
            ("8.1", "Role-based notification access control", "authentication"),
            ("8.2", "Authentication and authorization validation", "authorization"), 
            ("8.3", "Input validation and sanitization", "input_validation"),
            ("8.4", "XSS prevention testing", "xss_prevention"),
            ("8.5", "Rate limiting and abuse detection", "rate_limiting")
        ]
        
        for req_id, req_desc, category in requirements:
            coverage = report['security_coverage'].get(category, {'percentage': 0})
            status_icon = "✅" if coverage['percentage'] >= 80 else "❌"
            print(f"   {status_icon} Requirement {req_id}: {req_desc} "
                  f"({coverage['percentage']:.1f}% coverage)")
        
        print("\n" + "=" * 70)
        
        # Save detailed report
        self._save_detailed_report(report)
    
    def _save_detailed_report(self, report):
        """Save detailed report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"notification_security_test_report_{timestamp}.json"
        report_path = os.path.join(os.path.dirname(__file__), '..', 'reports', report_filename)
        
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"📄 Detailed report saved: {report_path}")
        except Exception as e:
            print(f"⚠️ Could not save detailed report: {e}")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive notification security tests')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='Run quick security validation only')
    
    args = parser.parse_args()
    
    # Create and run security test runner
    runner = SecurityTestRunner(verbose=args.verbose)
    
    if args.quick:
        print("🚀 Running Quick Security Validation...")
        # Run only critical security tests
        success = runner._run_test_suite("Critical Security", TestNotificationAuthenticationAuthorization)
    else:
        # Run comprehensive security test suite
        success = runner.run_all_security_tests()
    
    # Exit with appropriate code
    exit_code = 0 if success else 1
    
    if success:
        print("\n🎉 All security tests passed! Notification system is secure.")
    else:
        print("\n⚠️ Some security tests failed. Please review and fix issues before deployment.")
    
    return exit_code


if __name__ == '__main__':
    exit(main())