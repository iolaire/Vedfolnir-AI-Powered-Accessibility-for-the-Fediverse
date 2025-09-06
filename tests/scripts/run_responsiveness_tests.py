#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Responsiveness Tests Runner

Comprehensive test runner for responsiveness monitoring features,
including unit tests, integration tests, and performance tests.
"""

import sys
import os
import unittest
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.test_helpers.responsiveness_test_helpers import (
    ResponsivenessTestConfig,
    ResponsivenessPerformanceTester,
    ResponsivenessTestValidator
)


class ResponsivenessTestRunner:
    """Comprehensive test runner for responsiveness features"""
    
    def __init__(self):
        self.config = ResponsivenessTestConfig()
        self.results = {
            'unit_tests': {},
            'integration_tests': {},
            'performance_tests': {},
            'admin_dashboard_tests': {},
            'summary': {}
        }
        self.start_time = time.time()
    
    def run_unit_tests(self) -> dict:
        """Run unit tests for responsiveness features"""
        print("🧪 Running Responsiveness Unit Tests...")
        
        unit_test_modules = [
            'tests.unit.test_system_optimizer_responsiveness',
            'tests.unit.test_enhanced_database_manager_responsiveness',
            'tests.unit.test_enhanced_background_cleanup_manager_responsiveness',
            'tests.unit.test_enhanced_session_monitoring_responsiveness',
            'tests.unit.test_health_check_responsiveness'
        ]
        
        unit_results = {}
        
        for module_name in unit_test_modules:
            print(f"  📋 Running {module_name}...")
            
            try:
                # Load and run test module
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromName(module_name)
                
                # Run tests
                runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
                result = runner.run(suite)
                
                unit_results[module_name] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success': result.wasSuccessful(),
                    'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0
                }
                
                if result.wasSuccessful():
                    print(f"    ✅ {module_name}: {result.testsRun} tests passed")
                else:
                    print(f"    ❌ {module_name}: {len(result.failures)} failures, {len(result.errors)} errors")
                
            except Exception as e:
                print(f"    ⚠️  {module_name}: Failed to run - {str(e)}")
                unit_results[module_name] = {
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1,
                    'success': False,
                    'error': str(e)
                }
        
        self.results['unit_tests'] = unit_results
        return unit_results
    
    def run_integration_tests(self) -> dict:
        """Run integration tests for responsiveness features"""
        print("🔗 Running Responsiveness Integration Tests...")
        
        integration_test_modules = [
            'tests.integration.test_responsiveness_admin_dashboard_integration',
            'tests.integration.test_responsiveness_integration',
            'tests.integration.test_responsiveness_error_recovery_integration'
        ]
        
        integration_results = {}
        
        for module_name in integration_test_modules:
            print(f"  📋 Running {module_name}...")
            
            try:
                # Load and run test module
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromName(module_name)
                
                # Run tests
                runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
                result = runner.run(suite)
                
                integration_results[module_name] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success': result.wasSuccessful(),
                    'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0
                }
                
                if result.wasSuccessful():
                    print(f"    ✅ {module_name}: {result.testsRun} tests passed")
                else:
                    print(f"    ❌ {module_name}: {len(result.failures)} failures, {len(result.errors)} errors")
                
            except Exception as e:
                print(f"    ⚠️  {module_name}: Failed to run - {str(e)}")
                integration_results[module_name] = {
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1,
                    'success': False,
                    'error': str(e)
                }
        
        self.results['integration_tests'] = integration_results
        return integration_results
    
    def run_performance_tests(self) -> dict:
        """Run performance tests for responsiveness features"""
        print("⚡ Running Responsiveness Performance Tests...")
        
        performance_test_modules = [
            'tests.performance.test_responsiveness_performance_integration'
        ]
        
        performance_results = {}
        
        for module_name in performance_test_modules:
            print(f"  📋 Running {module_name}...")
            
            try:
                # Load and run test module
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromName(module_name)
                
                # Run tests with timing
                start_time = time.time()
                runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
                result = runner.run(suite)
                execution_time = time.time() - start_time
                
                performance_results[module_name] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success': result.wasSuccessful(),
                    'execution_time': execution_time,
                    'avg_test_time': execution_time / result.testsRun if result.testsRun > 0 else 0
                }
                
                if result.wasSuccessful():
                    print(f"    ✅ {module_name}: {result.testsRun} tests passed in {execution_time:.2f}s")
                else:
                    print(f"    ❌ {module_name}: {len(result.failures)} failures, {len(result.errors)} errors")
                
            except Exception as e:
                print(f"    ⚠️  {module_name}: Failed to run - {str(e)}")
                performance_results[module_name] = {
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1,
                    'success': False,
                    'error': str(e)
                }
        
        self.results['performance_tests'] = performance_results
        return performance_results
    
    def run_admin_dashboard_tests(self) -> dict:
        """Run admin dashboard responsiveness tests"""
        print("🎛️  Running Admin Dashboard Responsiveness Tests...")
        
        admin_test_modules = [
            'tests.admin.test_responsiveness_dashboard'
        ]
        
        admin_results = {}
        
        for module_name in admin_test_modules:
            print(f"  📋 Running {module_name}...")
            
            try:
                # Load and run test module
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromName(module_name)
                
                # Run tests
                runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
                result = runner.run(suite)
                
                admin_results[module_name] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success': result.wasSuccessful(),
                    'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0
                }
                
                if result.wasSuccessful():
                    print(f"    ✅ {module_name}: {result.testsRun} tests passed")
                else:
                    print(f"    ❌ {module_name}: {len(result.failures)} failures, {len(result.errors)} errors")
                
            except Exception as e:
                print(f"    ⚠️  {module_name}: Failed to run - {str(e)}")
                admin_results[module_name] = {
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1,
                    'success': False,
                    'error': str(e)
                }
        
        self.results['admin_dashboard_tests'] = admin_results
        return admin_results
    
    def run_responsiveness_validation_tests(self) -> dict:
        """Run responsiveness validation tests"""
        print("✅ Running Responsiveness Validation Tests...")
        
        validator = ResponsivenessTestValidator()
        validation_results = {}
        
        # Test system metrics validation
        print("  📋 Testing system metrics validation...")
        
        test_metrics = [
            {
                'name': 'healthy_metrics',
                'data': {
                    'memory_usage_percent': 45.0,
                    'cpu_usage_percent': 25.0,
                    'connection_pool_utilization': 0.6,
                    'responsiveness_status': 'healthy'
                }
            },
            {
                'name': 'warning_metrics',
                'data': {
                    'memory_usage_percent': 85.0,
                    'cpu_usage_percent': 75.0,
                    'connection_pool_utilization': 0.9,
                    'responsiveness_status': 'warning'
                }
            },
            {
                'name': 'invalid_metrics',
                'data': {
                    'memory_usage_percent': 150.0,  # Invalid
                    'cpu_usage_percent': -10.0,     # Invalid
                    'connection_pool_utilization': 1.5,  # Invalid
                    'responsiveness_status': 'unknown'   # Invalid
                }
            }
        ]
        
        metrics_validation_results = {}
        for test_case in test_metrics:
            validation_result = validator.validate_system_metrics(test_case['data'])
            metrics_validation_results[test_case['name']] = validation_result
            
            if validation_result['valid']:
                print(f"    ✅ {test_case['name']}: Valid")
            else:
                print(f"    ❌ {test_case['name']}: Invalid - {len(validation_result['errors'])} errors")
        
        validation_results['metrics_validation'] = metrics_validation_results
        
        # Test responsiveness check validation
        print("  📋 Testing responsiveness check validation...")
        
        test_checks = [
            {
                'name': 'healthy_check',
                'data': {
                    'responsive': True,
                    'overall_status': 'healthy',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'issues': []
                }
            },
            {
                'name': 'critical_check',
                'data': {
                    'responsive': False,
                    'overall_status': 'critical',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'issues': [
                        {
                            'type': 'memory',
                            'severity': 'critical',
                            'message': 'Memory usage critical'
                        }
                    ]
                }
            },
            {
                'name': 'invalid_check',
                'data': {
                    'responsive': 'yes',  # Should be boolean
                    'overall_status': 'healthy',
                    'issues': 'none'  # Should be list
                }
            }
        ]
        
        check_validation_results = {}
        for test_case in test_checks:
            validation_result = validator.validate_responsiveness_check(test_case['data'])
            check_validation_results[test_case['name']] = validation_result
            
            if validation_result['valid']:
                print(f"    ✅ {test_case['name']}: Valid")
            else:
                print(f"    ❌ {test_case['name']}: Invalid - {len(validation_result['errors'])} errors")
        
        validation_results['check_validation'] = check_validation_results
        
        return validation_results
    
    def generate_summary(self) -> dict:
        """Generate test summary"""
        total_execution_time = time.time() - self.start_time
        
        # Calculate totals
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_success = 0
        
        for test_category in ['unit_tests', 'integration_tests', 'performance_tests', 'admin_dashboard_tests']:
            if test_category in self.results:
                for module_name, result in self.results[test_category].items():
                    total_tests += result.get('tests_run', 0)
                    total_failures += result.get('failures', 0)
                    total_errors += result.get('errors', 0)
                    if result.get('success', False):
                        total_success += 1
        
        summary = {
            'total_execution_time': total_execution_time,
            'total_test_modules': sum(len(self.results[cat]) for cat in ['unit_tests', 'integration_tests', 'performance_tests', 'admin_dashboard_tests'] if cat in self.results),
            'total_tests': total_tests,
            'total_failures': total_failures,
            'total_errors': total_errors,
            'successful_modules': total_success,
            'overall_success_rate': (total_tests - total_failures - total_errors) / total_tests if total_tests > 0 else 0,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.results['summary'] = summary
        return summary
    
    def save_results(self, output_file: str = None) -> str:
        """Save test results to file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"tests/reports/responsiveness_test_results_{timestamp}.json"
        
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save results
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        return output_file
    
    def print_summary(self):
        """Print test summary"""
        summary = self.results.get('summary', {})
        
        print("\n" + "="*60)
        print("🎯 RESPONSIVENESS TESTS SUMMARY")
        print("="*60)
        
        print(f"⏱️  Total execution time: {summary.get('total_execution_time', 0):.2f} seconds")
        print(f"📊 Total test modules: {summary.get('total_test_modules', 0)}")
        print(f"🧪 Total tests: {summary.get('total_tests', 0)}")
        print(f"✅ Successful modules: {summary.get('successful_modules', 0)}")
        print(f"❌ Total failures: {summary.get('total_failures', 0)}")
        print(f"⚠️  Total errors: {summary.get('total_errors', 0)}")
        print(f"📈 Overall success rate: {summary.get('overall_success_rate', 0):.1%}")
        
        # Category breakdown
        print("\n📋 Test Category Breakdown:")
        for category in ['unit_tests', 'integration_tests', 'performance_tests', 'admin_dashboard_tests']:
            if category in self.results:
                category_results = self.results[category]
                successful_modules = sum(1 for result in category_results.values() if result.get('success', False))
                total_modules = len(category_results)
                
                print(f"  {category.replace('_', ' ').title()}: {successful_modules}/{total_modules} modules passed")
        
        # Overall result
        overall_success = (
            summary.get('total_failures', 0) == 0 and 
            summary.get('total_errors', 0) == 0 and 
            summary.get('total_tests', 0) > 0
        )
        
        if overall_success:
            print("\n🎉 ALL RESPONSIVENESS TESTS PASSED!")
        else:
            print("\n⚠️  SOME RESPONSIVENESS TESTS FAILED")
        
        print("="*60)
    
    def run_all_tests(self) -> dict:
        """Run all responsiveness tests"""
        print("🚀 Starting Comprehensive Responsiveness Test Suite")
        print("="*60)
        
        # Run all test categories
        self.run_unit_tests()
        self.run_integration_tests()
        self.run_performance_tests()
        self.run_admin_dashboard_tests()
        self.run_responsiveness_validation_tests()
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        output_file = self.save_results()
        print(f"\n💾 Test results saved to: {output_file}")
        
        # Print summary
        self.print_summary()
        
        return self.results


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run responsiveness tests')
    parser.add_argument('--category', choices=['unit', 'integration', 'performance', 'admin', 'validation', 'all'], 
                       default='all', help='Test category to run')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = ResponsivenessTestRunner()
    
    # Run specified tests
    if args.category == 'unit':
        runner.run_unit_tests()
    elif args.category == 'integration':
        runner.run_integration_tests()
    elif args.category == 'performance':
        runner.run_performance_tests()
    elif args.category == 'admin':
        runner.run_admin_dashboard_tests()
    elif args.category == 'validation':
        runner.run_responsiveness_validation_tests()
    else:  # all
        runner.run_all_tests()
        return
    
    # Generate summary for individual categories
    runner.generate_summary()
    
    # Save results
    output_file = runner.save_results(args.output)
    print(f"\n💾 Test results saved to: {output_file}")
    
    # Print summary
    runner.print_summary()


if __name__ == '__main__':
    main()