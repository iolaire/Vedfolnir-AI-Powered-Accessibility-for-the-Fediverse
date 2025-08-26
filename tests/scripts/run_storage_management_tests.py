#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive test runner for storage management system.

Runs all storage management tests including unit tests, integration tests,
performance tests, and security tests.
"""

import unittest
import sys
import os
import time
import argparse
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class StorageTestResult(unittest.TextTestResult):
    """Custom test result class for detailed reporting"""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = []
        self.start_time = None
        self.end_time = None
    
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
    
    def stopTest(self, test):
        super().stopTest(test)
        self.end_time = time.time()
        
        test_time = self.end_time - self.start_time
        test_name = f"{test.__class__.__module__}.{test.__class__.__name__}.{test._testMethodName}"
        
        status = "PASS"
        if self.errors and self.errors[-1][0] == test:
            status = "ERROR"
        elif self.failures and self.failures[-1][0] == test:
            status = "FAIL"
        elif self.skipped and self.skipped[-1][0] == test:
            status = "SKIP"
        
        self.test_results.append({
            'name': test_name,
            'status': status,
            'time': test_time
        })


class StorageTestRunner:
    """Test runner for storage management tests"""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.test_suites = {
            'unit': [
                'tests.unit.test_storage_configuration_service',
                'tests.unit.test_storage_monitor_service',
                'tests.unit.test_storage_limit_enforcer',
                'tests.unit.test_storage_email_notification_service',
                'tests.unit.test_storage_user_notification_system',
                'tests.unit.test_storage_override_system',
                'tests.unit.test_storage_warning_monitor',
            ],
            'integration': [
                'tests.integration.test_storage_management_comprehensive',
                'tests.integration.test_storage_user_experience',
                'tests.integration.test_storage_limit_enforcer_integration',
                'tests.integration.test_storage_configuration_integration',
                'tests.integration.test_storage_user_notification_integration',
                'tests.integration.test_storage_warning_integration',
                'tests.integration.test_storage_web_routes_integration',
                'tests.integration.test_storage_caption_generation_integration',
                'tests.integration.test_storage_cleanup_integration',
            ],
            'admin': [
                'tests.admin.test_admin_storage_dashboard',
                'tests.admin.test_storage_dashboard_integration',
            ],
            'performance': [
                'tests.performance.test_storage_performance',
            ],
            'security': [
                'tests.security.test_storage_security',
            ]
        }
    
    def run_test_suite(self, suite_name):
        """Run a specific test suite"""
        if suite_name not in self.test_suites:
            print(f"Unknown test suite: {suite_name}")
            return False
        
        print(f"\n{'='*60}")
        print(f"Running {suite_name.upper()} tests for Storage Management")
        print(f"{'='*60}")
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load tests from modules
        for module_name in self.test_suites[suite_name]:
            try:
                module = __import__(module_name, fromlist=[''])
                suite.addTests(loader.loadTestsFromModule(module))
                print(f"✓ Loaded tests from {module_name}")
            except ImportError as e:
                print(f"✗ Failed to load {module_name}: {e}")
                continue
            except Exception as e:
                print(f"✗ Error loading {module_name}: {e}")
                continue
        
        # Run tests
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=self.verbosity,
            resultclass=StorageTestResult
        )
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Print results
        print(f"\n{suite_name.upper()} Test Results:")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped)}")
        print(f"Time: {end_time - start_time:.2f} seconds")
        
        # Print detailed results if verbose
        if self.verbosity > 1 and hasattr(result, 'test_results'):
            print(f"\nDetailed Results:")
            for test_result in result.test_results:
                status_symbol = {
                    'PASS': '✓',
                    'FAIL': '✗',
                    'ERROR': '⚠',
                    'SKIP': '○'
                }.get(test_result['status'], '?')
                
                print(f"  {status_symbol} {test_result['name']} ({test_result['time']:.3f}s)")
        
        # Print failures and errors
        if result.failures:
            print(f"\nFAILURES:")
            for test, traceback in result.failures:
                print(f"  {test}: {traceback}")
        
        if result.errors:
            print(f"\nERRORS:")
            for test, traceback in result.errors:
                print(f"  {test}: {traceback}")
        
        return len(result.failures) == 0 and len(result.errors) == 0
    
    def run_all_tests(self):
        """Run all storage management tests"""
        print("Running comprehensive storage management test suite...")
        
        all_passed = True
        suite_results = {}
        
        for suite_name in ['unit', 'integration', 'admin', 'performance', 'security']:
            success = self.run_test_suite(suite_name)
            suite_results[suite_name] = success
            if not success:
                all_passed = False
        
        # Print summary
        print(f"\n{'='*60}")
        print("STORAGE MANAGEMENT TEST SUMMARY")
        print(f"{'='*60}")
        
        for suite_name, success in suite_results.items():
            status = "PASS" if success else "FAIL"
            symbol = "✓" if success else "✗"
            print(f"{symbol} {suite_name.upper():12}: {status}")
        
        overall_status = "PASS" if all_passed else "FAIL"
        print(f"\nOverall Result: {overall_status}")
        
        return all_passed
    
    def run_quick_tests(self):
        """Run quick subset of tests for development"""
        print("Running quick storage management tests...")
        
        # Run only unit tests and basic integration tests
        quick_suites = ['unit']
        all_passed = True
        
        for suite_name in quick_suites:
            success = self.run_test_suite(suite_name)
            if not success:
                all_passed = False
        
        return all_passed
    
    def run_performance_tests(self):
        """Run only performance tests"""
        print("Running storage management performance tests...")
        return self.run_test_suite('performance')
    
    def run_security_tests(self):
        """Run only security tests"""
        print("Running storage management security tests...")
        return self.run_test_suite('security')


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Storage Management Test Runner')
    parser.add_argument('--suite', choices=['unit', 'integration', 'admin', 'performance', 'security', 'all', 'quick'],
                       default='all', help='Test suite to run')
    parser.add_argument('--verbose', '-v', action='count', default=2,
                       help='Increase verbosity')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Reduce verbosity')
    
    args = parser.parse_args()
    
    # Adjust verbosity
    verbosity = args.verbose
    if args.quiet:
        verbosity = 0
    
    # Create test runner
    runner = StorageTestRunner(verbosity=verbosity)
    
    # Run requested tests
    if args.suite == 'all':
        success = runner.run_all_tests()
    elif args.suite == 'quick':
        success = runner.run_quick_tests()
    elif args.suite == 'performance':
        success = runner.run_performance_tests()
    elif args.suite == 'security':
        success = runner.run_security_tests()
    else:
        success = runner.run_test_suite(args.suite)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()