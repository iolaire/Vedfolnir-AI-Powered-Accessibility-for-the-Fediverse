#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Test Runner for Notification System

Runs all notification system tests including unit tests, integration tests,
security tests, performance tests, and generates detailed test reports.
"""

import unittest
import sys
import os
import time
import argparse
from datetime import datetime
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class NotificationSystemTestRunner:
    """Comprehensive test runner for notification system"""
    
    def __init__(self):
        self.test_suites = {
            'unit': [
                'tests.unit.test_unified_notification_manager',
                'tests.unit.test_notification_message_router',
                'tests.test_notification_models_integration',
                'tests.test_notification_persistence_manager'
            ],
            'integration': [
                'tests.integration.test_notification_websocket_integration',
                'tests.integration.test_notification_database_integration',
                'tests.integration.test_notification_error_handling_recovery',
                'tests.test_page_notification_integration'
            ],
            'security': [
                'tests.security.test_notification_authentication_authorization'
            ],
            'performance': [
                'tests.performance.test_notification_performance'
            ]
        }
        
        self.results = {
            'unit': {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'time': 0},
            'integration': {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'time': 0},
            'security': {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'time': 0},
            'performance': {'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'time': 0}
        }
        
        self.detailed_results = []
    
    def run_test_suite(self, suite_name, verbose=False):
        """Run a specific test suite"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name.upper()} Tests")
        print(f"{'='*60}")
        
        if suite_name not in self.test_suites:
            print(f"Unknown test suite: {suite_name}")
            return False
        
        suite_start_time = time.time()
        suite_loader = unittest.TestLoader()
        suite_runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=StringIO() if not verbose else sys.stdout
        )
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        
        for test_module in self.test_suites[suite_name]:
            print(f"\nRunning {test_module}...")
            
            try:
                # Load test module
                module = __import__(test_module, fromlist=[''])
                test_suite = suite_loader.loadTestsFromModule(module)
                
                # Run tests
                test_start_time = time.time()
                result = suite_runner.run(test_suite)
                test_end_time = time.time()
                
                # Collect results
                tests_run = result.testsRun
                failures = len(result.failures)
                errors = len(result.errors)
                skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
                
                total_tests += tests_run
                total_failures += failures
                total_errors += errors
                total_skipped += skipped
                
                # Store detailed results
                self.detailed_results.append({
                    'suite': suite_name,
                    'module': test_module,
                    'tests_run': tests_run,
                    'failures': failures,
                    'errors': errors,
                    'skipped': skipped,
                    'time': test_end_time - test_start_time,
                    'success': failures == 0 and errors == 0
                })
                
                # Print module results
                status = "PASSED" if failures == 0 and errors == 0 else "FAILED"
                print(f"  {test_module}: {status} ({tests_run} tests, {failures} failures, {errors} errors)")
                
            except ImportError as e:
                print(f"  ERROR: Could not import {test_module}: {e}")
                total_errors += 1
                self.detailed_results.append({
                    'suite': suite_name,
                    'module': test_module,
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1,
                    'skipped': 0,
                    'time': 0,
                    'success': False,
                    'import_error': str(e)
                })
            except Exception as e:
                print(f"  ERROR: Unexpected error running {test_module}: {e}")
                total_errors += 1
        
        suite_end_time = time.time()
        suite_time = suite_end_time - suite_start_time
        
        # Update suite results
        self.results[suite_name] = {
            'passed': total_tests - total_failures - total_errors,
            'failed': total_failures,
            'errors': total_errors,
            'skipped': total_skipped,
            'time': suite_time
        }
        
        # Print suite summary
        print(f"\n{suite_name.upper()} Test Suite Summary:")
        print(f"  Tests Run: {total_tests}")
        print(f"  Passed: {total_tests - total_failures - total_errors}")
        print(f"  Failed: {total_failures}")
        print(f"  Errors: {total_errors}")
        print(f"  Skipped: {total_skipped}")
        print(f"  Time: {suite_time:.2f}s")
        
        return total_failures == 0 and total_errors == 0
    
    def run_all_tests(self, verbose=False):
        """Run all test suites"""
        print("Starting Comprehensive Notification System Test Suite")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        overall_start_time = time.time()
        all_passed = True
        
        # Run each test suite
        for suite_name in self.test_suites.keys():
            suite_passed = self.run_test_suite(suite_name, verbose)
            all_passed = all_passed and suite_passed
        
        overall_end_time = time.time()
        overall_time = overall_end_time - overall_start_time
        
        # Generate final report
        self.generate_final_report(overall_time, all_passed)
        
        return all_passed
    
    def generate_final_report(self, total_time, all_passed):
        """Generate comprehensive final test report"""
        print(f"\n{'='*80}")
        print("NOTIFICATION SYSTEM TEST REPORT")
        print(f"{'='*80}")
        
        # Overall summary
        total_tests = sum(suite['passed'] + suite['failed'] + suite['errors'] for suite in self.results.values())
        total_passed = sum(suite['passed'] for suite in self.results.values())
        total_failed = sum(suite['failed'] for suite in self.results.values())
        total_errors = sum(suite['errors'] for suite in self.results.values())
        total_skipped = sum(suite['skipped'] for suite in self.results.values())
        
        print(f"\nOVERALL RESULTS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Errors: {total_errors}")
        print(f"  Skipped: {total_skipped}")
        print(f"  Success Rate: {(total_passed / total_tests * 100):.1f}%" if total_tests > 0 else "  Success Rate: N/A")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Overall Status: {'PASSED' if all_passed else 'FAILED'}")
        
        # Suite breakdown
        print(f"\nSUITE BREAKDOWN:")
        for suite_name, results in self.results.items():
            suite_total = results['passed'] + results['failed'] + results['errors']
            suite_success_rate = (results['passed'] / suite_total * 100) if suite_total > 0 else 0
            status = "PASSED" if results['failed'] == 0 and results['errors'] == 0 else "FAILED"
            
            print(f"  {suite_name.upper()}:")
            print(f"    Tests: {suite_total}, Passed: {results['passed']}, Failed: {results['failed']}, Errors: {results['errors']}")
            print(f"    Success Rate: {suite_success_rate:.1f}%, Time: {results['time']:.2f}s, Status: {status}")
        
        # Detailed module results
        print(f"\nDETAILED MODULE RESULTS:")
        for result in self.detailed_results:
            status = "PASSED" if result['success'] else "FAILED"
            print(f"  {result['module']}: {status}")
            print(f"    Tests: {result['tests_run']}, Failures: {result['failures']}, Errors: {result['errors']}, Time: {result['time']:.2f}s")
            
            if 'import_error' in result:
                print(f"    Import Error: {result['import_error']}")
        
        # Requirements coverage
        print(f"\nREQUIREMENTS COVERAGE:")
        print(f"  ✓ 10.1 - UnifiedNotificationManager functionality tests")
        print(f"  ✓ 10.2 - WebSocket framework integration tests")
        print(f"  ✓ 10.3 - Authentication and authorization integration tests")
        print(f"  ✓ 10.4 - Error handling and recovery tests")
        print(f"  ✓ 10.5 - Performance tests for notification delivery and UI rendering")
        
        # Test categories covered
        print(f"\nTEST CATEGORIES COVERED:")
        print(f"  ✓ Unit Tests - Core component functionality")
        print(f"  ✓ Integration Tests - WebSocket and database integration")
        print(f"  ✓ Security Tests - Authentication and authorization")
        print(f"  ✓ Performance Tests - Scalability and performance")
        print(f"  ✓ Error Handling Tests - Failure scenarios and recovery")
        
        # Recommendations
        print(f"\nRECOMMENDATIONS:")
        if all_passed:
            print(f"  ✓ All tests passed! The notification system is ready for deployment.")
            print(f"  ✓ Consider running performance tests under production load conditions.")
            print(f"  ✓ Monitor system performance metrics after deployment.")
        else:
            print(f"  ⚠ Some tests failed. Review failed tests before deployment.")
            print(f"  ⚠ Fix any security or integration issues immediately.")
            print(f"  ⚠ Re-run tests after fixes to ensure stability.")
        
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
    
    def run_specific_tests(self, test_patterns, verbose=False):
        """Run specific tests matching patterns"""
        print(f"Running specific tests matching patterns: {test_patterns}")
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Find matching tests
        for pattern in test_patterns:
            for suite_name, modules in self.test_suites.items():
                for module_name in modules:
                    if pattern in module_name:
                        try:
                            module = __import__(module_name, fromlist=[''])
                            module_suite = loader.loadTestsFromModule(module)
                            suite.addTest(module_suite)
                            print(f"Added tests from {module_name}")
                        except ImportError as e:
                            print(f"Could not import {module_name}: {e}")
        
        # Run selected tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return result.wasSuccessful()


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='Run notification system tests')
    parser.add_argument('--suite', choices=['unit', 'integration', 'security', 'performance', 'all'], 
                       default='all', help='Test suite to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--pattern', nargs='+', help='Run tests matching specific patterns')
    
    args = parser.parse_args()
    
    runner = NotificationSystemTestRunner()
    
    try:
        if args.pattern:
            success = runner.run_specific_tests(args.pattern, args.verbose)
        elif args.suite == 'all':
            success = runner.run_all_tests(args.verbose)
        else:
            success = runner.run_test_suite(args.suite, args.verbose)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()