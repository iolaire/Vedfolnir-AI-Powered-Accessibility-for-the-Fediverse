#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Maintenance Mode Test Runner

Executes all maintenance mode tests including end-to-end, load testing,
and failure scenario tests. Provides detailed reporting and performance analysis.
"""

import unittest
import sys
import os
import time
import json
from datetime import datetime, timezone
import argparse
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import test modules
from tests.integration.test_maintenance_mode_end_to_end import TestMaintenanceModeEndToEnd
from tests.performance.test_maintenance_mode_load import TestMaintenanceModeLoad
from tests.integration.test_maintenance_mode_failure_scenarios import TestMaintenanceModeFailureScenarios

# Import existing maintenance mode tests
from tests.unit.test_enhanced_maintenance_mode_service import TestEnhancedMaintenanceModeService
from tests.unit.test_enhanced_maintenance_mode_test_mode import TestEnhancedMaintenanceModeTestMode
from tests.unit.test_maintenance_operation_classifier import TestMaintenanceOperationClassifier
from tests.unit.test_maintenance_session_manager import TestMaintenanceSessionManager
from tests.unit.test_maintenance_status_api import TestMaintenanceStatusAPI
from tests.unit.test_emergency_maintenance_handler import TestEmergencyMaintenanceHandler
from tests.admin.test_maintenance_mode_middleware import TestMaintenanceModeMiddleware
from tests.admin.test_maintenance_mode_interface import TestMaintenanceModeAdminInterface


class MaintenanceModeTestRunner:
    """Comprehensive test runner for maintenance mode functionality"""
    
    def __init__(self):
        self.test_suites = {
            'unit': {
                'description': 'Unit tests for individual maintenance mode components',
                'test_classes': [
                    TestEnhancedMaintenanceModeService,
                    TestEnhancedMaintenanceModeTestMode,
                    TestMaintenanceOperationClassifier,
                    TestMaintenanceSessionManager,
                    TestMaintenanceStatusAPI,
                    TestEmergencyMaintenanceHandler
                ]
            },
            'integration': {
                'description': 'Integration tests for maintenance mode workflows',
                'test_classes': [
                    TestMaintenanceModeEndToEnd,
                    TestMaintenanceModeFailureScenarios
                ]
            },
            'performance': {
                'description': 'Performance and load tests for maintenance mode',
                'test_classes': [
                    TestMaintenanceModeLoad
                ]
            },
            'admin': {
                'description': 'Admin interface tests for maintenance mode',
                'test_classes': [
                    TestMaintenanceModeMiddleware,
                    TestMaintenanceModeAdminInterface
                ]
            }
        }
        
        self.results = {
            'start_time': None,
            'end_time': None,
            'duration': 0,
            'suites': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'error_tests': 0,
                'skipped_tests': 0,
                'success_rate': 0.0
            },
            'performance_data': {},
            'errors': [],
            'failures': []
        }
    
    def run_test_suite(self, suite_name, verbose=False):
        """Run a specific test suite"""
        if suite_name not in self.test_suites:
            print(f"❌ Unknown test suite: {suite_name}")
            return False
        
        suite_info = self.test_suites[suite_name]
        print(f"\n{'='*60}")
        print(f"Running {suite_name.upper()} Tests")
        print(f"{'='*60}")
        print(f"Description: {suite_info['description']}")
        print(f"Test classes: {len(suite_info['test_classes'])}")
        print()
        
        # Create test suite
        suite = unittest.TestSuite()
        for test_class in suite_info['test_classes']:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run tests with custom result collector
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=2 if verbose else 1,
            buffer=True
        )
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Collect results
        suite_results = {
            'start_time': start_time,
            'end_time': end_time,
            'duration': end_time - start_time,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'output': stream.getvalue(),
            'failure_details': result.failures,
            'error_details': result.errors
        }
        
        self.results['suites'][suite_name] = suite_results
        
        # Print summary
        print(f"\n{suite_name.upper()} Test Results:")
        print(f"  Tests run: {suite_results['tests_run']}")
        print(f"  Failures: {suite_results['failures']}")
        print(f"  Errors: {suite_results['errors']}")
        print(f"  Skipped: {suite_results['skipped']}")
        print(f"  Success rate: {suite_results['success_rate']:.1f}%")
        print(f"  Duration: {suite_results['duration']:.2f}s")
        
        if verbose and (result.failures or result.errors):
            print(f"\nDetailed output:")
            print(stream.getvalue())
        
        return result.wasSuccessful()
    
    def run_all_tests(self, verbose=False, suites=None):
        """Run all or specified test suites"""
        print("🧪 Comprehensive Maintenance Mode Test Suite")
        print("=" * 60)
        
        self.results['start_time'] = time.time()
        
        # Determine which suites to run
        suites_to_run = suites if suites else list(self.test_suites.keys())
        
        print(f"Running test suites: {', '.join(suites_to_run)}")
        print()
        
        overall_success = True
        
        for suite_name in suites_to_run:
            success = self.run_test_suite(suite_name, verbose)
            if not success:
                overall_success = False
        
        self.results['end_time'] = time.time()
        self.results['duration'] = self.results['end_time'] - self.results['start_time']
        
        # Calculate overall summary
        self._calculate_summary()
        
        # Print final summary
        self._print_final_summary()
        
        return overall_success
    
    def _calculate_summary(self):
        """Calculate overall test summary"""
        summary = self.results['summary']
        
        for suite_name, suite_results in self.results['suites'].items():
            summary['total_tests'] += suite_results['tests_run']
            passed = suite_results['tests_run'] - suite_results['failures'] - suite_results['errors']
            summary['passed_tests'] += passed
            summary['failed_tests'] += suite_results['failures']
            summary['error_tests'] += suite_results['errors']
            summary['skipped_tests'] += suite_results['skipped']
            
            # Collect failure and error details
            self.results['failures'].extend(suite_results['failure_details'])
            self.results['errors'].extend(suite_results['error_details'])
        
        if summary['total_tests'] > 0:
            summary['success_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
    
    def _print_final_summary(self):
        """Print final test summary"""
        print("\n" + "=" * 60)
        print("FINAL TEST SUMMARY")
        print("=" * 60)
        
        summary = self.results['summary']
        
        print(f"Total duration: {self.results['duration']:.2f}s")
        print(f"Total tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']} ✓")
        print(f"Failed: {summary['failed_tests']} ❌")
        print(f"Errors: {summary['error_tests']} ⚠️")
        print(f"Skipped: {summary['skipped_tests']} ⏭️")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        # Suite breakdown
        print(f"\nSuite Breakdown:")
        for suite_name, suite_results in self.results['suites'].items():
            status = "✓" if suite_results['success_rate'] == 100 else "❌"
            print(f"  {suite_name}: {suite_results['success_rate']:.1f}% {status}")
        
        # Performance highlights
        if 'performance' in self.results['suites']:
            print(f"\nPerformance Highlights:")
            perf_results = self.results['suites']['performance']
            print(f"  Performance tests: {perf_results['tests_run']}")
            print(f"  Performance duration: {perf_results['duration']:.2f}s")
        
        # Failure summary
        if self.results['failures'] or self.results['errors']:
            print(f"\nIssues Summary:")
            if self.results['failures']:
                print(f"  Failures: {len(self.results['failures'])}")
                for i, (test, traceback) in enumerate(self.results['failures'][:3]):
                    print(f"    {i+1}. {test}")
            
            if self.results['errors']:
                print(f"  Errors: {len(self.results['errors'])}")
                for i, (test, traceback) in enumerate(self.results['errors'][:3]):
                    print(f"    {i+1}. {test}")
        
        # Overall status
        if summary['success_rate'] == 100:
            print(f"\n🎉 ALL TESTS PASSED! Maintenance mode is ready for production.")
        elif summary['success_rate'] >= 90:
            print(f"\n✅ Tests mostly successful. Minor issues to address.")
        elif summary['success_rate'] >= 75:
            print(f"\n⚠️  Some test failures. Review and fix issues before deployment.")
        else:
            print(f"\n❌ Significant test failures. Major issues need resolution.")
    
    def generate_report(self, output_file=None):
        """Generate detailed test report"""
        report = {
            'test_run_info': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'duration': self.results['duration'],
                'suites_run': list(self.results['suites'].keys())
            },
            'summary': self.results['summary'],
            'suite_results': {}
        }
        
        # Add suite details (without full output to keep report manageable)
        for suite_name, suite_results in self.results['suites'].items():
            report['suite_results'][suite_name] = {
                'duration': suite_results['duration'],
                'tests_run': suite_results['tests_run'],
                'failures': suite_results['failures'],
                'errors': suite_results['errors'],
                'skipped': suite_results['skipped'],
                'success_rate': suite_results['success_rate']
            }
        
        # Add failure and error summaries
        report['issues'] = {
            'failure_count': len(self.results['failures']),
            'error_count': len(self.results['errors']),
            'failure_tests': [str(test) for test, _ in self.results['failures']],
            'error_tests': [str(test) for test, _ in self.results['errors']]
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {output_file}")
        
        return report
    
    def run_quick_validation(self):
        """Run a quick validation test to check if maintenance mode is working"""
        print("🚀 Quick Maintenance Mode Validation")
        print("=" * 40)
        
        # Run just the core unit tests
        quick_suites = ['unit']
        success = self.run_all_tests(verbose=False, suites=quick_suites)
        
        if success:
            print("\n✅ Quick validation PASSED - Maintenance mode core functionality is working")
        else:
            print("\n❌ Quick validation FAILED - Issues detected in core functionality")
        
        return success


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description='Comprehensive Maintenance Mode Test Runner')
    parser.add_argument('--suite', choices=['unit', 'integration', 'performance', 'admin', 'all'], 
                       default='all', help='Test suite to run')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose output including detailed test results')
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick validation tests only')
    parser.add_argument('--report', type=str, 
                       help='Generate detailed report to specified file')
    parser.add_argument('--list-suites', action='store_true', 
                       help='List available test suites')
    
    args = parser.parse_args()
    
    runner = MaintenanceModeTestRunner()
    
    if args.list_suites:
        print("Available test suites:")
        for suite_name, suite_info in runner.test_suites.items():
            print(f"  {suite_name}: {suite_info['description']}")
            print(f"    Classes: {len(suite_info['test_classes'])}")
        return 0
    
    if args.quick:
        success = runner.run_quick_validation()
    elif args.suite == 'all':
        success = runner.run_all_tests(verbose=args.verbose)
    else:
        success = runner.run_all_tests(verbose=args.verbose, suites=[args.suite])
    
    # Generate report if requested
    if args.report:
        runner.generate_report(args.report)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())