#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Integration Test Runner

Comprehensive test runner for all configuration system integration tests.
Executes end-to-end tests, load tests, and failure scenario tests.
"""

import sys
import os
import unittest
import time
import argparse
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class ConfigurationTestRunner:
    """Test runner for configuration system integration tests"""
    
    def __init__(self):
        self.test_suites = {
            'e2e': {
                'name': 'End-to-End Configuration Flow Tests',
                'module': 'tests.integration.test_configuration_system_e2e',
                'description': 'Tests complete configuration flow from Admin UI to Application behavior'
            },
            'load': {
                'name': 'Configuration System Load Tests',
                'module': 'tests.performance.test_configuration_system_load',
                'description': 'Tests configuration system performance under high load'
            },
            'failure': {
                'name': 'Configuration Failure Scenario Tests',
                'module': 'tests.integration.test_configuration_failure_scenarios',
                'description': 'Tests configuration system behavior under failure conditions'
            },
            'unit': {
                'name': 'Configuration Unit Tests',
                'modules': [
                    'tests.unit.test_configuration_service',
                    'tests.unit.test_configuration_cache',
                    'tests.unit.test_configuration_event_bus',
                    'tests.unit.test_task_queue_configuration_adapter',
                    'tests.unit.test_session_configuration_adapter',
                    'tests.unit.test_alert_configuration_adapter',
                    'tests.unit.test_feature_flag_service',
                    'tests.unit.test_maintenance_mode_service'
                ],
                'description': 'Unit tests for individual configuration components'
            },
            'admin': {
                'name': 'Admin Configuration Interface Tests',
                'modules': [
                    'tests.admin.test_configuration_management',
                    'tests.admin.test_configuration_validation_feedback',
                    'tests.admin.test_configuration_impact_warnings',
                    'tests.admin.test_restart_requirement_indicators',
                    'tests.admin.test_configuration_dry_run'
                ],
                'description': 'Tests for admin configuration management interface'
            }
        }
        
        self.results = {}
    
    def run_test_suite(self, suite_name: str, verbose: bool = False) -> Dict[str, Any]:
        """Run a specific test suite"""
        if suite_name not in self.test_suites:
            raise ValueError(f"Unknown test suite: {suite_name}")
        
        suite_info = self.test_suites[suite_name]
        print(f"\\n{'='*60}")
        print(f"Running: {suite_info['name']}")
        print(f"Description: {suite_info['description']}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Create test loader
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Load tests from modules
        if 'module' in suite_info:
            # Single module
            try:
                module_suite = loader.loadTestsFromName(suite_info['module'])
                suite.addTest(module_suite)
            except Exception as e:
                print(f"Error loading module {suite_info['module']}: {e}")
                return {
                    'suite': suite_name,
                    'success': False,
                    'error': str(e),
                    'duration': 0,
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 0
                }
        
        elif 'modules' in suite_info:
            # Multiple modules
            for module_name in suite_info['modules']:
                try:
                    module_suite = loader.loadTestsFromName(module_name)
                    suite.addTest(module_suite)
                except Exception as e:
                    print(f"Warning: Could not load module {module_name}: {e}")
        
        # Run tests
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=sys.stdout,
            buffer=True
        )
        
        result = runner.run(suite)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Compile results
        suite_result = {
            'suite': suite_name,
            'success': result.wasSuccessful(),
            'duration': duration,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0
        }
        
        if result.failures:
            suite_result['failure_details'] = [
                {'test': str(test), 'traceback': traceback}
                for test, traceback in result.failures
            ]
        
        if result.errors:
            suite_result['error_details'] = [
                {'test': str(test), 'traceback': traceback}
                for test, traceback in result.errors
            ]
        
        # Print summary
        print(f"\\n{'-'*40}")
        print(f"Suite: {suite_info['name']}")
        print(f"Duration: {duration:.2f}s")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success: {'✅' if result.wasSuccessful() else '❌'}")
        
        return suite_result
    
    def run_all_suites(self, verbose: bool = False, exclude: List[str] = None) -> Dict[str, Any]:
        """Run all test suites"""
        exclude = exclude or []
        
        print("Configuration System Integration Test Runner")
        print("=" * 60)
        
        overall_start = time.time()
        all_results = {}
        
        for suite_name in self.test_suites:
            if suite_name in exclude:
                print(f"\\nSkipping suite: {suite_name}")
                continue
            
            try:
                result = self.run_test_suite(suite_name, verbose)
                all_results[suite_name] = result
            except Exception as e:
                print(f"\\nError running suite {suite_name}: {e}")
                all_results[suite_name] = {
                    'suite': suite_name,
                    'success': False,
                    'error': str(e),
                    'duration': 0,
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1
                }
        
        overall_end = time.time()
        overall_duration = overall_end - overall_start
        
        # Print overall summary
        self._print_overall_summary(all_results, overall_duration)
        
        return all_results
    
    def _print_overall_summary(self, results: Dict[str, Any], duration: float):
        """Print overall test summary"""
        print(f"\\n{'='*60}")
        print("OVERALL TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = sum(r.get('tests_run', 0) for r in results.values())
        total_failures = sum(r.get('failures', 0) for r in results.values())
        total_errors = sum(r.get('errors', 0) for r in results.values())
        successful_suites = sum(1 for r in results.values() if r.get('success', False))
        total_suites = len(results)
        
        print(f"Total duration: {duration:.2f}s")
        print(f"Test suites: {successful_suites}/{total_suites} successful")
        print(f"Total tests: {total_tests}")
        print(f"Failures: {total_failures}")
        print(f"Errors: {total_errors}")
        
        overall_success = total_failures == 0 and total_errors == 0
        print(f"Overall result: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
        
        # Print suite-by-suite results
        print(f"\\n{'-'*40}")
        print("Suite Results:")
        for suite_name, result in results.items():
            status = "✅" if result.get('success', False) else "❌"
            duration_str = f"{result.get('duration', 0):.2f}s"
            tests_str = f"{result.get('tests_run', 0)} tests"
            
            print(f"  {status} {suite_name:20} {duration_str:>8} {tests_str:>10}")
        
        # Print failure details if any
        if total_failures > 0 or total_errors > 0:
            print(f"\\n{'-'*40}")
            print("FAILURE/ERROR DETAILS:")
            
            for suite_name, result in results.items():
                if result.get('failures', 0) > 0:
                    print(f"\\nFailures in {suite_name}:")
                    for failure in result.get('failure_details', []):
                        print(f"  - {failure['test']}")
                
                if result.get('errors', 0) > 0:
                    print(f"\\nErrors in {suite_name}:")
                    for error in result.get('error_details', []):
                        print(f"  - {error['test']}")
    
    def list_suites(self):
        """List available test suites"""
        print("Available test suites:")
        print("-" * 40)
        
        for suite_name, suite_info in self.test_suites.items():
            print(f"{suite_name:15} - {suite_info['description']}")
    
    def validate_environment(self) -> bool:
        """Validate test environment"""
        print("Validating test environment...")
        
        # Check if required modules can be imported
        required_modules = [
            'config',
            'database',
            'models',
            'configuration_service',
            'system_configuration_manager'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError as e:
                missing_modules.append((module, str(e)))
        
        if missing_modules:
            print("❌ Environment validation failed!")
            print("Missing modules:")
            for module, error in missing_modules:
                print(f"  - {module}: {error}")
            return False
        
        print("✅ Environment validation passed!")
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Configuration System Integration Test Runner"
    )
    
    parser.add_argument(
        'suites',
        nargs='*',
        help='Test suites to run (default: all)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available test suites'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--exclude',
        nargs='*',
        default=[],
        help='Test suites to exclude'
    )
    
    parser.add_argument(
        '--validate-env',
        action='store_true',
        help='Validate test environment only'
    )
    
    args = parser.parse_args()
    
    runner = ConfigurationTestRunner()
    
    if args.list:
        runner.list_suites()
        return 0
    
    if args.validate_env:
        success = runner.validate_environment()
        return 0 if success else 1
    
    # Validate environment first
    if not runner.validate_environment():
        print("\\nEnvironment validation failed. Cannot run tests.")
        return 1
    
    try:
        if args.suites:
            # Run specific suites
            results = {}
            for suite_name in args.suites:
                if suite_name not in runner.test_suites:
                    print(f"Unknown test suite: {suite_name}")
                    return 1
                
                result = runner.run_test_suite(suite_name, args.verbose)
                results[suite_name] = result
            
            # Print summary for multiple suites
            if len(args.suites) > 1:
                overall_duration = sum(r.get('duration', 0) for r in results.values())
                runner._print_overall_summary(results, overall_duration)
        
        else:
            # Run all suites
            results = runner.run_all_suites(args.verbose, args.exclude)
        
        # Determine exit code
        success = all(r.get('success', False) for r in results.values())
        return 0 if success else 1
    
    except KeyboardInterrupt:
        print("\\n\\nTest run interrupted by user.")
        return 130
    
    except Exception as e:
        print(f"\\nUnexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())