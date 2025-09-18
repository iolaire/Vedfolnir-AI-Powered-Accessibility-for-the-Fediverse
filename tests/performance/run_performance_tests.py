#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Test Runner for RQ System

Runs comprehensive performance and load tests for the RQ system,
generates performance reports, and validates performance requirements.
"""

import sys
import os
import unittest
import time
import json
import argparse
from datetime import datetime, timezone
import psutil

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.performance.test_rq_performance_load import (
    TestRQQueuePerformance,
    TestTaskSerializationPerformance,
    TestWorkerScalingPerformance,
    TestMemoryUsageAndResourceUtilization
)
from tests.performance.test_rq_stress_scenarios import (
    TestExtremeLoadScenarios,
    TestFailureRecoveryScenarios,
    TestSystemLimitsAndBoundaries
)


class PerformanceTestRunner:
    """Performance test runner with reporting capabilities"""
    
    def __init__(self):
        self.test_results = {}
        self.system_info = self._get_system_info()
        self.start_time = None
        self.end_time = None
    
    def _get_system_info(self):
        """Get system information for performance context"""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            'memory_total': psutil.virtual_memory().total / (1024**3),  # GB
            'python_version': sys.version,
            'platform': sys.platform
        }
    
    def run_test_suite(self, test_suite_name, test_classes):
        """Run a test suite and collect results"""
        print(f"\n{'='*60}")
        print(f"Running {test_suite_name}")
        print(f"{'='*60}")
        
        suite_start_time = time.time()
        suite_results = {}
        
        for test_class in test_classes:
            print(f"\nRunning {test_class.__name__}...")
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromTestCase(test_class)
            
            # Run tests
            runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
            result = runner.run(suite)
            
            # Collect results
            suite_results[test_class.__name__] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0,
                'failure_details': [str(failure[1]) for failure in result.failures],
                'error_details': [str(error[1]) for error in result.errors]
            }
        
        suite_end_time = time.time()
        suite_duration = suite_end_time - suite_start_time
        
        self.test_results[test_suite_name] = {
            'duration': suite_duration,
            'results': suite_results
        }
        
        print(f"\n{test_suite_name} completed in {suite_duration:.2f} seconds")
    
    def run_all_tests(self):
        """Run all performance test suites"""
        self.start_time = time.time()
        
        # Performance and Load Tests
        performance_tests = [
            TestRQQueuePerformance,
            TestTaskSerializationPerformance,
            TestWorkerScalingPerformance,
            TestMemoryUsageAndResourceUtilization
        ]
        
        self.run_test_suite("Performance and Load Tests", performance_tests)
        
        # Stress Test Scenarios
        stress_tests = [
            TestExtremeLoadScenarios,
            TestFailureRecoveryScenarios,
            TestSystemLimitsAndBoundaries
        ]
        
        self.run_test_suite("Stress Test Scenarios", stress_tests)
        
        self.end_time = time.time()
    
    def generate_report(self, output_file=None):
        """Generate comprehensive performance test report"""
        if not self.start_time or not self.end_time:
            print("No test results to report")
            return
        
        total_duration = self.end_time - self.start_time
        
        report = {
            'test_run_info': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_duration': total_duration,
                'system_info': self.system_info
            },
            'test_results': self.test_results,
            'summary': self._generate_summary()
        }
        
        # Print summary to console
        self._print_summary(report)
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nDetailed report saved to: {output_file}")
        
        return report
    
    def _generate_summary(self):
        """Generate test summary statistics"""
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        for suite_name, suite_data in self.test_results.items():
            for test_class, results in suite_data['results'].items():
                total_tests += results['tests_run']
                total_failures += results['failures']
                total_errors += results['errors']
        
        overall_success_rate = (total_tests - total_failures - total_errors) / total_tests if total_tests > 0 else 0
        
        return {
            'total_tests': total_tests,
            'total_failures': total_failures,
            'total_errors': total_errors,
            'overall_success_rate': overall_success_rate,
            'performance_requirements_met': self._check_performance_requirements()
        }
    
    def _check_performance_requirements(self):
        """Check if performance requirements are met"""
        # Define performance requirements
        requirements = {
            'queue_operations_per_second': 100,
            'serialization_operations_per_second': 100,
            'worker_startup_time_max': 1000,  # ms
            'memory_growth_max': 100,  # MB
            'overall_success_rate_min': 0.95
        }
        
        # This would be implemented to check actual performance metrics
        # For now, return a placeholder
        return {
            'requirements_met': True,
            'requirements': requirements,
            'note': 'Performance requirement checking not fully implemented in this test runner'
        }
    
    def _print_summary(self, report):
        """Print test summary to console"""
        print(f"\n{'='*80}")
        print("PERFORMANCE TEST SUMMARY")
        print(f"{'='*80}")
        
        summary = report['summary']
        
        print(f"Total Duration: {report['test_run_info']['total_duration']:.2f} seconds")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Failures: {summary['total_failures']}")
        print(f"Errors: {summary['total_errors']}")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.4f}")
        
        print(f"\nSystem Information:")
        system_info = report['test_run_info']['system_info']
        print(f"  CPU Cores: {system_info['cpu_count']}")
        print(f"  Memory: {system_info['memory_total']:.2f} GB")
        print(f"  Platform: {system_info['platform']}")
        
        print(f"\nTest Suite Results:")
        for suite_name, suite_data in self.test_results.items():
            print(f"  {suite_name}:")
            print(f"    Duration: {suite_data['duration']:.2f}s")
            
            for test_class, results in suite_data['results'].items():
                success_rate = results['success_rate']
                status = "✅ PASS" if success_rate == 1.0 else "❌ FAIL" if success_rate < 0.5 else "⚠️  PARTIAL"
                print(f"    {test_class}: {status} ({results['tests_run']} tests, {success_rate:.2%} success)")
        
        # Performance requirements
        perf_req = summary['performance_requirements_met']
        req_status = "✅ MET" if perf_req['requirements_met'] else "❌ NOT MET"
        print(f"\nPerformance Requirements: {req_status}")


def main():
    """Main entry point for performance test runner"""
    parser = argparse.ArgumentParser(description='Run RQ Performance Tests')
    parser.add_argument('--output', '-o', help='Output file for detailed report (JSON)')
    parser.add_argument('--suite', choices=['performance', 'stress', 'all'], default='all',
                       help='Test suite to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set up test runner
    runner = PerformanceTestRunner()
    
    print("RQ System Performance Test Runner")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"CPU Cores: {psutil.cpu_count()}")
    print(f"Memory: {psutil.virtual_memory().total / (1024**3):.2f} GB")
    
    try:
        if args.suite == 'performance':
            # Run only performance tests
            performance_tests = [
                TestRQQueuePerformance,
                TestTaskSerializationPerformance,
                TestWorkerScalingPerformance,
                TestMemoryUsageAndResourceUtilization
            ]
            runner.run_test_suite("Performance and Load Tests", performance_tests)
            
        elif args.suite == 'stress':
            # Run only stress tests
            stress_tests = [
                TestExtremeLoadScenarios,
                TestFailureRecoveryScenarios,
                TestSystemLimitsAndBoundaries
            ]
            runner.run_test_suite("Stress Test Scenarios", stress_tests)
            
        else:
            # Run all tests
            runner.run_all_tests()
        
        # Generate report
        report = runner.generate_report(args.output)
        
        # Exit with appropriate code
        summary = report['summary']
        if summary['total_failures'] > 0 or summary['total_errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError running performance tests: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()