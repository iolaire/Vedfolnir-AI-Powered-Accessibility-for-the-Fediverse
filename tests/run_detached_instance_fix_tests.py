#!/usr/bin/env python3

# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Runner for DetachedInstanceError Fix

Comprehensive test runner for all DetachedInstanceError fix tests,
including Flask application context tests with standardized mock user helpers.
"""

import unittest
import sys
import os
import argparse
from typing import List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class DetachedInstanceFixTestRunner:
    """Test runner for DetachedInstanceError fix tests"""
    
    def __init__(self):
        self.test_suites = {
            'flask_integration': [
                'tests.test_detached_instance_fix_flask_integration',
            ],
            'web_routes': [
                'tests.test_detached_instance_fix_web_routes',
            ],
            'session_management': [
                'tests.test_session_management',
                'tests.test_session_integration',
                'tests.test_session_management_comprehensive',
            ],
            'database_context': [
                'tests.test_database_context_middleware',
                'tests.test_middleware_context',
            ],
            'session_decorators': [
                'tests.test_session_aware_decorators',
                'tests.test_session_decorators_integration',
            ],
            'error_handling': [
                'tests.test_detached_instance_handler',
                'tests.test_detached_instance_handler_simple',
            ],
            'template_context': [
                'tests.test_safe_template_context',
                'tests.test_template_safe_context',
            ],
            'performance': [
                'tests.test_session_performance_monitoring',
            ],
            'all': []  # Will be populated with all tests
        }
        
        # Populate 'all' suite
        all_tests = set()
        for suite_tests in self.test_suites.values():
            if suite_tests:  # Skip empty lists
                all_tests.update(suite_tests)
        self.test_suites['all'] = list(all_tests)
    
    def discover_tests(self, test_modules: List[str]) -> unittest.TestSuite:
        """Discover tests from specified modules"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        for module_name in test_modules:
            try:
                # Import the module
                module = __import__(module_name, fromlist=[''])
                
                # Load tests from module
                module_suite = loader.loadTestsFromModule(module)
                suite.addTest(module_suite)
                
                print(f"✅ Loaded tests from {module_name}")
                
            except ImportError as e:
                print(f"⚠️  Could not import {module_name}: {e}")
            except Exception as e:
                print(f"❌ Error loading tests from {module_name}: {e}")
        
        return suite
    
    def run_test_suite(self, suite_name: str, verbosity: int = 2) -> bool:
        """Run a specific test suite"""
        if suite_name not in self.test_suites:
            print(f"❌ Unknown test suite: {suite_name}")
            print(f"Available suites: {list(self.test_suites.keys())}")
            return False
        
        test_modules = self.test_suites[suite_name]
        if not test_modules:
            print(f"⚠️  No tests defined for suite: {suite_name}")
            return True
        
        print(f"\n{'='*80}")
        print(f"RUNNING TEST SUITE: {suite_name.upper()}")
        print(f"{'='*80}")
        print(f"Test modules: {test_modules}")
        print()
        
        # Discover and run tests
        suite = self.discover_tests(test_modules)
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        result = runner.run(suite)
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"TEST SUITE SUMMARY: {suite_name.upper()}")
        print(f"{'='*80}")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
        
        if result.failures:
            print(f"\n❌ FAILURES ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  • {test}: {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See details above'}")
        
        if result.errors:
            print(f"\n❌ ERRORS ({len(result.errors)}):")
            for test, traceback in result.errors:
                error_msg = traceback.split('\n')[-2] if traceback.split('\n') else str(traceback)
                print(f"  • {test}: {error_msg}")
        
        success = len(result.failures) == 0 and len(result.errors) == 0
        
        if success:
            print(f"\n🎉 TEST SUITE PASSED: {suite_name}")
        else:
            print(f"\n❌ TEST SUITE FAILED: {suite_name}")
        
        return success
    
    def run_flask_context_tests(self, verbosity: int = 2) -> bool:
        """Run all Flask context tests"""
        print(f"\n{'='*80}")
        print("RUNNING FLASK CONTEXT TESTS FOR DETACHED INSTANCE FIX")
        print(f"{'='*80}")
        print("These tests require Flask application context and use standardized mock user helpers")
        print()
        
        flask_suites = ['flask_integration', 'web_routes']
        all_passed = True
        
        for suite_name in flask_suites:
            success = self.run_test_suite(suite_name, verbosity)
            if not success:
                all_passed = False
        
        print(f"\n{'='*80}")
        print("FLASK CONTEXT TESTS SUMMARY")
        print(f"{'='*80}")
        
        if all_passed:
            print("🎉 ALL FLASK CONTEXT TESTS PASSED!")
            print("✅ DetachedInstanceError fix works correctly with Flask application context")
            print("✅ Standardized mock user helpers work properly")
            print("✅ Web routes handle session management correctly")
        else:
            print("❌ SOME FLASK CONTEXT TESTS FAILED")
            print("⚠️  Please review and fix issues before deploying")
        
        return all_passed
    
    def run_comprehensive_tests(self, verbosity: int = 2) -> bool:
        """Run comprehensive test suite"""
        print(f"\n{'='*80}")
        print("RUNNING COMPREHENSIVE DETACHED INSTANCE FIX TESTS")
        print(f"{'='*80}")
        
        # Test suites in order of importance
        test_order = [
            'flask_integration',
            'web_routes', 
            'session_management',
            'database_context',
            'session_decorators',
            'error_handling',
            'template_context',
            'performance'
        ]
        
        results = {}
        for suite_name in test_order:
            if suite_name in self.test_suites:
                results[suite_name] = self.run_test_suite(suite_name, verbosity)
        
        # Overall summary
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST RESULTS")
        print(f"{'='*80}")
        
        passed_suites = [name for name, passed in results.items() if passed]
        failed_suites = [name for name, passed in results.items() if not passed]
        
        print(f"Total test suites: {len(results)}")
        print(f"Passed: {len(passed_suites)}")
        print(f"Failed: {len(failed_suites)}")
        
        if passed_suites:
            print(f"\n✅ PASSED SUITES:")
            for suite in passed_suites:
                print(f"  • {suite}")
        
        if failed_suites:
            print(f"\n❌ FAILED SUITES:")
            for suite in failed_suites:
                print(f"  • {suite}")
        
        all_passed = len(failed_suites) == 0
        
        if all_passed:
            print(f"\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
            print("✅ DetachedInstanceError fix implementation is fully validated")
        else:
            print(f"\n❌ SOME TESTS FAILED")
            print("⚠️  Please address failures before considering implementation complete")
        
        return all_passed
    
    def list_available_suites(self):
        """List all available test suites"""
        print("Available test suites:")
        for suite_name, modules in self.test_suites.items():
            module_count = len(modules) if modules else 0
            print(f"  • {suite_name}: {module_count} test modules")
            if modules and len(modules) <= 5:  # Show modules for smaller suites
                for module in modules:
                    print(f"    - {module}")

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(
        description="Run DetachedInstanceError fix tests with Flask context support"
    )
    parser.add_argument(
        'suite',
        nargs='?',
        default='flask_context',
        help='Test suite to run (default: flask_context)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=2,
        help='Increase verbosity (use -v, -vv, or -vvv)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available test suites'
    )
    
    args = parser.parse_args()
    
    runner = DetachedInstanceFixTestRunner()
    
    if args.list:
        runner.list_available_suites()
        return 0
    
    # Special handling for flask_context
    if args.suite == 'flask_context':
        success = runner.run_flask_context_tests(args.verbose)
    elif args.suite == 'comprehensive':
        success = runner.run_comprehensive_tests(args.verbose)
    else:
        success = runner.run_test_suite(args.suite, args.verbose)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())