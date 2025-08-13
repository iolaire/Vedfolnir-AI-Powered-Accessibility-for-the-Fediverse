#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive test runner for the Vedfolnir web-integrated caption generation system
"""

import unittest
import sys
import os
import argparse
import time
from io import StringIO

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))

# Test suite categories
TEST_SUITES = {
    'unit': [
        'tests.test_web_caption_generation_service',
        'tests.test_task_queue_manager',
        'tests.test_progress_tracker',
        'tests.test_websocket_progress_handler'
    ],
    'integration': [
        'tests.web_caption_generation.test_integration_workflow'
    ],
    'security': [
        'tests.web_caption_generation.test_security_validation',
        'tests.security.test_comprehensive_security',
        'tests.security.test_platform_access'
    ],
    'performance': [
        'tests.web_caption_generation.test_performance_concurrent',
        'tests.performance.test_platform_load',
        'tests.performance.test_platform_queries'
    ],
    'web': [
        'tests.web_caption_generation.test_end_to_end_web',
        'tests.test_platform_management_interface'
    ],
    'error_handling': [
        'tests.web_caption_generation.test_error_recovery',
        'tests.test_database_error_handling'
    ],
    'platform': [
        'tests.test_platform_adapters_comprehensive',
        'tests.test_platform_switching_integration',
        'tests.integration.test_platform_web'
    ],
    'config': [
        'tests.test_configuration_examples',
        'tests.test_config_validation_script',
        'tests.test_config_multi_platform'
    ]
}

class TestResult:
    """Test result tracking"""
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.failures = []
        self.errors = []
        self.start_time = None
        self.end_time = None

class ComprehensiveTestRunner:
    """Comprehensive test runner with detailed reporting"""
    
    def __init__(self, verbosity=1):
        self.verbosity = verbosity
        self.results = {}
    
    def run_test_suite(self, suite_name, test_modules):
        """Run a specific test suite"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name.upper()} Tests")
        print(f"{'='*60}")
        
        suite_result = TestResult()
        suite_result.start_time = time.time()
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load tests from modules
        loaded_modules = 0
        for module_name in test_modules:
            try:
                # Check if the test file actually exists
                test_file = module_name.replace('.', '/') + '.py'
                if not os.path.exists(test_file):
                    if self.verbosity >= 1:
                        print(f"  ⚠ Skipped {module_name}: File not found")
                    continue
                
                module_suite = loader.loadTestsFromName(module_name)
                suite.addTest(module_suite)
                loaded_modules += 1
                if self.verbosity >= 2:
                    print(f"  ✓ Loaded {module_name}")
            except ImportError as e:
                if self.verbosity >= 1:
                    print(f"  ⚠ Skipped {module_name}: {e}")
                continue
            except Exception as e:
                if self.verbosity >= 1:
                    print(f"  ✗ Error loading {module_name}: {e}")
                continue
        
        if loaded_modules == 0:
            print(f"  No tests loaded for {suite_name} suite")
            return suite_result
        
        # Run tests
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=self.verbosity,
            buffer=True
        )
        
        test_result = runner.run(suite)
        
        # Process results
        suite_result.end_time = time.time()
        suite_result.total_tests = test_result.testsRun
        suite_result.failed_tests = len(test_result.failures)
        suite_result.error_tests = len(test_result.errors)
        suite_result.skipped_tests = len(test_result.skipped)
        suite_result.passed_tests = (
            suite_result.total_tests - 
            suite_result.failed_tests - 
            suite_result.error_tests - 
            suite_result.skipped_tests
        )
        suite_result.failures = test_result.failures
        suite_result.errors = test_result.errors
        
        # Print results
        duration = suite_result.end_time - suite_result.start_time
        print(f"\n{suite_name.upper()} Results:")
        print(f"  Tests run: {suite_result.total_tests}")
        print(f"  Passed: {suite_result.passed_tests}")
        print(f"  Failed: {suite_result.failed_tests}")
        print(f"  Errors: {suite_result.error_tests}")
        print(f"  Skipped: {suite_result.skipped_tests}")
        print(f"  Duration: {duration:.2f}s")
        
        # Print failures and errors if verbose
        if self.verbosity >= 2:
            if suite_result.failures:
                print(f"\nFailures in {suite_name}:")
                for test, traceback in suite_result.failures:
                    print(f"  FAIL: {test}")
                    if self.verbosity >= 3:
                        print(f"    {traceback}")
            
            if suite_result.errors:
                print(f"\nErrors in {suite_name}:")
                for test, traceback in suite_result.errors:
                    print(f"  ERROR: {test}")
                    if self.verbosity >= 3:
                        print(f"    {traceback}")
        
        self.results[suite_name] = suite_result
        return suite_result
    
    def run_all_suites(self, selected_suites=None):
        """Run all or selected test suites"""
        if selected_suites is None:
            selected_suites = list(TEST_SUITES.keys())
        
        print("Vedfolnir - Comprehensive Test Suite")
        print("=" * 60)
        print(f"Running test suites: {', '.join(selected_suites)}")
        
        total_start_time = time.time()
        
        for suite_name in selected_suites:
            if suite_name in TEST_SUITES:
                self.run_test_suite(suite_name, TEST_SUITES[suite_name])
            else:
                print(f"Unknown test suite: {suite_name}")
        
        total_end_time = time.time()
        
        # Print summary
        self.print_summary(total_end_time - total_start_time)
    
    def print_summary(self, total_duration):
        """Print comprehensive test summary"""
        print(f"\n{'='*60}")
        print("COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = sum(r.total_tests for r in self.results.values())
        total_passed = sum(r.passed_tests for r in self.results.values())
        total_failed = sum(r.failed_tests for r in self.results.values())
        total_errors = sum(r.error_tests for r in self.results.values())
        total_skipped = sum(r.skipped_tests for r in self.results.values())
        
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)" if total_tests > 0 else "Passed: 0")
        print(f"Failed: {total_failed}")
        print(f"Errors: {total_errors}")
        print(f"Skipped: {total_skipped}")
        
        # Suite breakdown
        print(f"\nSuite Breakdown:")
        for suite_name, result in self.results.items():
            status = "✓" if result.failed_tests == 0 and result.error_tests == 0 else "✗"
            print(f"  {status} {suite_name}: {result.passed_tests}/{result.total_tests} passed")
        
        # Overall status
        overall_success = total_failed == 0 and total_errors == 0
        print(f"\nOverall Status: {'PASS' if overall_success else 'FAIL'}")
        
        return overall_success

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for Vedfolnir"
    )
    parser.add_argument(
        '--suite', '-s',
        choices=list(TEST_SUITES.keys()) + ['all'],
        default='all',
        help='Test suite to run'
    )
    parser.add_argument(
        '--suites',
        nargs='+',
        choices=list(TEST_SUITES.keys()),
        help='Multiple test suites to run'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=1,
        help='Increase verbosity (use -vv for more verbose)'
    )
    parser.add_argument(
        '--list-suites',
        action='store_true',
        help='List available test suites'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run only unit and integration tests'
    )
    parser.add_argument(
        '--ci',
        action='store_true',
        help='Run in CI mode (minimal output, exit codes)'
    )
    
    args = parser.parse_args()
    
    # List suites if requested
    if args.list_suites:
        print("Available test suites:")
        for suite_name, modules in TEST_SUITES.items():
            print(f"  {suite_name}: {len(modules)} test modules")
            if args.verbose >= 2:
                for module in modules:
                    print(f"    - {module}")
        return 0
    
    # Determine verbosity
    verbosity = 0 if args.ci else args.verbose
    
    # Determine suites to run
    if args.quick:
        selected_suites = ['unit', 'integration']
    elif args.suites:
        selected_suites = args.suites
    elif args.suite == 'all':
        selected_suites = list(TEST_SUITES.keys())
    else:
        selected_suites = [args.suite]
    
    # Run tests
    runner = ComprehensiveTestRunner(verbosity=verbosity)
    runner.run_all_suites(selected_suites)
    
    # Return appropriate exit code
    overall_success = all(
        r.failed_tests == 0 and r.error_tests == 0 
        for r in runner.results.values()
    )
    
    return 0 if overall_success else 1

if __name__ == '__main__':
    sys.exit(main())