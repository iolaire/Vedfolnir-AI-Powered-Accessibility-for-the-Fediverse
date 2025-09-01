#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Test Runner

This script runs comprehensive performance and load tests for the notification system,
generates detailed reports, and provides performance benchmarking capabilities.
"""

import sys
import os
import unittest
import time
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import psutil

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import test modules
from tests.performance.test_notification_performance import NotificationPerformanceTestSuite
from tests.performance.test_websocket_load import WebSocketLoadTestSuite
from tests.performance.test_memory_usage import MemoryUsageTestSuite


class PerformanceTestRunner:
    """Performance test runner with reporting capabilities"""
    
    def __init__(self):
        self.test_results = {}
        self.system_info = self._get_system_info()
        self.start_time = None
        self.end_time = None
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for test context"""
        return {
            'platform': sys.platform,
            'python_version': sys.version,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def run_notification_performance_tests(self) -> Dict[str, Any]:
        """Run notification performance tests"""
        print("=" * 60)
        print("RUNNING NOTIFICATION PERFORMANCE TESTS")
        print("=" * 60)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(NotificationPerformanceTestSuite)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        return {
            'test_suite': 'NotificationPerformanceTestSuite',
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'execution_time': end_time - start_time,
            'failure_details': [str(failure[1]) for failure in result.failures],
            'error_details': [str(error[1]) for error in result.errors]
        }
    
    def run_websocket_load_tests(self) -> Dict[str, Any]:
        """Run WebSocket load tests"""
        print("\n" + "=" * 60)
        print("RUNNING WEBSOCKET LOAD TESTS")
        print("=" * 60)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(WebSocketLoadTestSuite)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        return {
            'test_suite': 'WebSocketLoadTestSuite',
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'execution_time': end_time - start_time,
            'failure_details': [str(failure[1]) for failure in result.failures],
            'error_details': [str(error[1]) for error in result.errors]
        }
    
    def run_memory_usage_tests(self) -> Dict[str, Any]:
        """Run memory usage tests"""
        print("\n" + "=" * 60)
        print("RUNNING MEMORY USAGE TESTS")
        print("=" * 60)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(MemoryUsageTestSuite)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        return {
            'test_suite': 'MemoryUsageTestSuite',
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'execution_time': end_time - start_time,
            'failure_details': [str(failure[1]) for failure in result.failures],
            'error_details': [str(error[1]) for error in result.errors]
        }
    
    def run_all_tests(self, test_suites: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all performance tests or specified test suites"""
        self.start_time = time.time()
        
        available_suites = {
            'notification': self.run_notification_performance_tests,
            'websocket': self.run_websocket_load_tests,
            'memory': self.run_memory_usage_tests
        }
        
        if test_suites is None:
            test_suites = list(available_suites.keys())
        
        print(f"Running performance test suites: {', '.join(test_suites)}")
        print(f"System Info: {self.system_info['cpu_count']} CPUs, {self.system_info['memory_total_gb']:.1f}GB RAM")
        
        results = {}
        
        for suite_name in test_suites:
            if suite_name in available_suites:
                try:
                    results[suite_name] = available_suites[suite_name]()
                except Exception as e:
                    results[suite_name] = {
                        'test_suite': suite_name,
                        'error': f"Failed to run test suite: {e}",
                        'tests_run': 0,
                        'failures': 0,
                        'errors': 1,
                        'success_rate': 0,
                        'execution_time': 0
                    }
            else:
                print(f"Warning: Unknown test suite '{suite_name}'. Available: {list(available_suites.keys())}")
        
        self.end_time = time.time()
        self.test_results = results
        
        return results
    
    def generate_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive performance test report"""
        if not self.test_results:
            raise ValueError("No test results available. Run tests first.")
        
        # Calculate overall statistics
        total_tests = sum(result.get('tests_run', 0) for result in self.test_results.values())
        total_failures = sum(result.get('failures', 0) for result in self.test_results.values())
        total_errors = sum(result.get('errors', 0) for result in self.test_results.values())
        total_skipped = sum(result.get('skipped', 0) for result in self.test_results.values())
        total_execution_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        # Create comprehensive report
        report = {
            'report_metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'test_duration': total_execution_time,
                'system_info': self.system_info
            },
            'overall_summary': {
                'total_test_suites': len(self.test_results),
                'total_tests': total_tests,
                'total_failures': total_failures,
                'total_errors': total_errors,
                'total_skipped': total_skipped,
                'overall_success_rate': overall_success_rate,
                'total_execution_time': total_execution_time
            },
            'test_suite_results': self.test_results,
            'performance_benchmarks': self._calculate_benchmarks(),
            'recommendations': self._generate_recommendations()
        }
        
        # Save report to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nPerformance test report saved to: {output_file}")
        
        return report
    
    def _calculate_benchmarks(self) -> Dict[str, Any]:
        """Calculate performance benchmarks from test results"""
        benchmarks = {
            'notification_throughput': 'Not measured',
            'websocket_connection_capacity': 'Not measured',
            'memory_efficiency': 'Not measured',
            'concurrent_user_capacity': 'Not measured'
        }
        
        # Extract benchmarks from test results
        # This would be enhanced with actual performance metrics from tests
        
        return benchmarks
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []
        
        # Analyze test results and generate recommendations
        for suite_name, result in self.test_results.items():
            if result.get('failures', 0) > 0 or result.get('errors', 0) > 0:
                recommendations.append(f"Review failures in {suite_name} test suite")
            
            if result.get('success_rate', 0) < 95:
                recommendations.append(f"Improve reliability in {suite_name} - success rate is {result.get('success_rate', 0):.1f}%")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("All performance tests passed successfully")
            recommendations.append("Consider running tests with higher load parameters for stress testing")
        
        return recommendations
    
    def print_summary(self):
        """Print a summary of test results"""
        if not self.test_results:
            print("No test results available.")
            return
        
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        
        for suite_name, result in self.test_results.items():
            print(f"\n{result.get('test_suite', suite_name)}:")
            print(f"  Tests Run: {result.get('tests_run', 0)}")
            print(f"  Failures: {result.get('failures', 0)}")
            print(f"  Errors: {result.get('errors', 0)}")
            print(f"  Skipped: {result.get('skipped', 0)}")
            print(f"  Success Rate: {result.get('success_rate', 0):.2f}%")
            print(f"  Execution Time: {result.get('execution_time', 0):.2f}s")
            
            if result.get('failure_details'):
                print(f"  Failure Details: {len(result['failure_details'])} failures")
            
            if result.get('error_details'):
                print(f"  Error Details: {len(result['error_details'])} errors")
        
        # Overall summary
        total_tests = sum(result.get('tests_run', 0) for result in self.test_results.values())
        total_failures = sum(result.get('failures', 0) for result in self.test_results.values())
        total_errors = sum(result.get('errors', 0) for result in self.test_results.values())
        overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nOVERALL RESULTS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Total Failures: {total_failures}")
        print(f"  Total Errors: {total_errors}")
        print(f"  Overall Success Rate: {overall_success_rate:.2f}%")
        print(f"  Total Execution Time: {self.end_time - self.start_time:.2f}s" if self.end_time and self.start_time else "N/A")


def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='Run notification system performance tests')
    parser.add_argument(
        '--suites',
        nargs='+',
        choices=['notification', 'websocket', 'memory', 'all'],
        default=['all'],
        help='Test suites to run (default: all)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for detailed JSON report'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine which test suites to run
    if 'all' in args.suites:
        test_suites = ['notification', 'websocket', 'memory']
    else:
        test_suites = args.suites
    
    # Create test runner
    runner = PerformanceTestRunner()
    
    try:
        # Run tests
        print("Starting notification system performance tests...")
        print(f"Test suites: {', '.join(test_suites)}")
        
        results = runner.run_all_tests(test_suites)
        
        # Print summary
        runner.print_summary()
        
        # Generate detailed report if requested
        if args.output:
            report = runner.generate_report(args.output)
            print(f"\nDetailed report generated: {args.output}")
        
        # Determine exit code based on results
        total_failures = sum(result.get('failures', 0) for result in results.values())
        total_errors = sum(result.get('errors', 0) for result in results.values())
        
        if total_failures > 0 or total_errors > 0:
            print(f"\nPerformance tests completed with {total_failures} failures and {total_errors} errors.")
            sys.exit(1)
        else:
            print("\nAll performance tests passed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nPerformance tests interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError running performance tests: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()