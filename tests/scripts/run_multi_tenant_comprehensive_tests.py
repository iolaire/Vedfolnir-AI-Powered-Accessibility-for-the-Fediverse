# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Test Runner for Multi-Tenant Caption Management

This script runs all comprehensive tests for the multi-tenant caption management system,
including unit tests, integration tests, security tests, performance tests, end-to-end tests,
error recovery tests, and load testing.
"""

import unittest
import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all test modules
from tests.test_multi_tenant_comprehensive import (
    TestMultiTenantUnitTests,
    TestMultiTenantIntegrationTests,
    TestMultiTenantSecurityTests,
    TestMultiTenantPerformanceTests,
    TestMultiTenantEndToEndTests,
    TestMultiTenantErrorRecoveryTests,
    TestMultiTenantLoadTests
)

from tests.test_multi_tenant_security_comprehensive import (
    TestAdminAuthorizationSecurity,
    TestCrossTenantAccessPrevention,
    TestInputValidationSecurity,
    TestSecurityAuditLogging,
    TestSessionSecurity
)

from tests.test_multi_tenant_performance_load import (
    TestConcurrentAdminOperations,
    TestLargeScaleMonitoring,
    TestMemoryUsageUnderLoad,
    TestDatabaseConnectionPoolPerformance
)

from tests.test_multi_tenant_error_recovery import (
    TestNetworkErrorRecovery,
    TestTimeoutErrorRecovery,
    TestDatabaseConnectionRecovery,
    TestSystemResilienceUnderLoad,
    TestAutomaticRetryLogic
)


class ComprehensiveTestRunner:
    """Comprehensive test runner for multi-tenant caption management"""
    
    def __init__(self):
        """Initialize the test runner"""
        self.test_suites = {
            'unit': {
                'description': 'Unit tests for all new service classes and methods',
                'classes': [TestMultiTenantUnitTests]
            },
            'integration': {
                'description': 'Integration tests for complete admin workflow scenarios',
                'classes': [TestMultiTenantIntegrationTests]
            },
            'security': {
                'description': 'Security tests for admin authorization and cross-tenant access prevention',
                'classes': [
                    TestMultiTenantSecurityTests,
                    TestAdminAuthorizationSecurity,
                    TestCrossTenantAccessPrevention,
                    TestInputValidationSecurity,
                    TestSecurityAuditLogging,
                    TestSessionSecurity
                ]
            },
            'performance': {
                'description': 'Performance tests for concurrent admin operations and large-scale monitoring',
                'classes': [
                    TestMultiTenantPerformanceTests,
                    TestConcurrentAdminOperations,
                    TestLargeScaleMonitoring,
                    TestMemoryUsageUnderLoad,
                    TestDatabaseConnectionPoolPerformance
                ]
            },
            'e2e': {
                'description': 'End-to-end tests for user and admin interfaces',
                'classes': [TestMultiTenantEndToEndTests]
            },
            'error_recovery': {
                'description': 'Automated testing for error recovery and system resilience',
                'classes': [
                    TestMultiTenantErrorRecoveryTests,
                    TestNetworkErrorRecovery,
                    TestTimeoutErrorRecovery,
                    TestDatabaseConnectionRecovery,
                    TestSystemResilienceUnderLoad,
                    TestAutomaticRetryLogic
                ]
            },
            'load': {
                'description': 'Load testing for multi-tenant scenarios with multiple concurrent users',
                'classes': [TestMultiTenantLoadTests]
            }
        }
    
    def create_test_suite(self, suite_names: List[str] = None) -> unittest.TestSuite:
        """
        Create a test suite with specified test categories.
        
        Args:
            suite_names: List of suite names to include. If None, includes all suites.
            
        Returns:
            unittest.TestSuite containing the selected tests
        """
        if suite_names is None:
            suite_names = list(self.test_suites.keys())
        
        suite = unittest.TestSuite()
        
        for suite_name in suite_names:
            if suite_name not in self.test_suites:
                print(f"Warning: Unknown test suite '{suite_name}'. Available suites: {list(self.test_suites.keys())}")
                continue
            
            print(f"Adding {suite_name} tests: {self.test_suites[suite_name]['description']}")
            
            for test_class in self.test_suites[suite_name]['classes']:
                tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
                suite.addTests(tests)
        
        return suite
    
    def run_tests(self, suite_names: List[str] = None, verbosity: int = 2) -> unittest.TestResult:
        """
        Run the comprehensive test suite.
        
        Args:
            suite_names: List of suite names to run. If None, runs all suites.
            verbosity: Test runner verbosity level
            
        Returns:
            unittest.TestResult with test results
        """
        print("="*80)
        print("MULTI-TENANT CAPTION MANAGEMENT - COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Create and run test suite
        suite = self.create_test_suite(suite_names)
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Print comprehensive summary
        self.print_test_summary(result, end_time - start_time, suite_names)
        
        return result
    
    def print_test_summary(self, result: unittest.TestResult, duration: float, suite_names: List[str] = None):
        """
        Print comprehensive test summary.
        
        Args:
            result: Test result object
            duration: Test execution duration in seconds
            suite_names: List of suite names that were run
        """
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE SUMMARY")
        print("="*80)
        
        # Basic statistics
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(getattr(result, 'skipped', []))
        successful = total_tests - failures - errors - skipped
        
        success_rate = (successful / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Test Execution Summary:")
        print(f"  Total tests run: {total_tests}")
        print(f"  Successful: {successful}")
        print(f"  Failures: {failures}")
        print(f"  Errors: {errors}")
        print(f"  Skipped: {skipped}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Execution time: {duration:.2f} seconds")
        print()
        
        # Suite breakdown
        if suite_names:
            print(f"Test Suites Executed:")
            for suite_name in suite_names:
                if suite_name in self.test_suites:
                    print(f"  ✓ {suite_name}: {self.test_suites[suite_name]['description']}")
            print()
        
        # Detailed failure and error reporting
        if failures:
            print(f"FAILURES ({len(failures)}):")
            print("-" * 40)
            for i, (test, traceback) in enumerate(failures, 1):
                print(f"{i}. {test}")
                # Extract the assertion error message
                lines = traceback.split('\n')
                for line in lines:
                    if 'AssertionError:' in line:
                        print(f"   {line.strip()}")
                        break
                print()
        
        if errors:
            print(f"ERRORS ({len(errors)}):")
            print("-" * 40)
            for i, (test, traceback) in enumerate(errors, 1):
                print(f"{i}. {test}")
                # Extract the error message
                lines = traceback.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ['Error:', 'Exception:']):
                        print(f"   {line.strip()}")
                        break
                print()
        
        # Performance insights
        if duration > 0:
            tests_per_second = total_tests / duration
            print(f"Performance Metrics:")
            print(f"  Tests per second: {tests_per_second:.1f}")
            print(f"  Average test duration: {duration/total_tests:.3f} seconds")
            print()
        
        # Test coverage insights
        print(f"Test Coverage Areas:")
        coverage_areas = [
            ("Unit Testing", "Service classes and methods"),
            ("Integration Testing", "Complete admin workflows"),
            ("Security Testing", "Authorization and access control"),
            ("Performance Testing", "Concurrent operations and monitoring"),
            ("End-to-End Testing", "User and admin interfaces"),
            ("Error Recovery Testing", "System resilience and recovery"),
            ("Load Testing", "Multi-tenant concurrent scenarios")
        ]
        
        for area, description in coverage_areas:
            if not suite_names or any(area.lower().replace(' ', '_').replace('-', '_') in suite_names for suite_names in [suite_names]):
                print(f"  ✓ {area}: {description}")
        
        print()
        
        # Final assessment
        if success_rate >= 95:
            print("🎉 EXCELLENT: Test suite passed with high success rate!")
        elif success_rate >= 85:
            print("✅ GOOD: Test suite passed with acceptable success rate.")
        elif success_rate >= 70:
            print("⚠️  WARNING: Test suite has moderate success rate. Review failures.")
        else:
            print("❌ CRITICAL: Test suite has low success rate. Immediate attention required.")
        
        print("="*80)
    
    def list_available_suites(self):
        """List all available test suites"""
        print("Available Test Suites:")
        print("="*50)
        for suite_name, suite_info in self.test_suites.items():
            print(f"{suite_name:15} - {suite_info['description']}")
            print(f"{'':15}   Classes: {len(suite_info['classes'])}")
        print()


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Runner for Multi-Tenant Caption Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_multi_tenant_comprehensive_tests.py                    # Run all tests
  python run_multi_tenant_comprehensive_tests.py --suites unit     # Run only unit tests
  python run_multi_tenant_comprehensive_tests.py --suites security performance  # Run security and performance tests
  python run_multi_tenant_comprehensive_tests.py --list            # List available test suites
  python run_multi_tenant_comprehensive_tests.py --quick           # Run quick test subset
        """
    )
    
    parser.add_argument(
        '--suites',
        nargs='*',
        help='Test suites to run (default: all). Available: unit, integration, security, performance, e2e, error_recovery, load'
    )
    
    parser.add_argument(
        '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Test output verbosity (0=quiet, 1=normal, 2=verbose)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available test suites and exit'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick test subset (unit and security tests only)'
    )
    
    parser.add_argument(
        '--no-performance',
        action='store_true',
        help='Skip performance and load tests (for faster execution)'
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = ComprehensiveTestRunner()
    
    # Handle list command
    if args.list:
        runner.list_available_suites()
        return 0
    
    # Determine which suites to run
    if args.quick:
        suite_names = ['unit', 'security']
    elif args.no_performance:
        suite_names = ['unit', 'integration', 'security', 'e2e', 'error_recovery']
    elif args.suites is not None:
        suite_names = args.suites
    else:
        suite_names = None  # Run all suites
    
    # Run tests
    try:
        result = runner.run_tests(suite_names, args.verbosity)
        
        # Return appropriate exit code
        if result.failures or result.errors:
            return 1
        else:
            return 0
            
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n\nTest execution failed with error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())