#!/usr/bin/env python3
"""
Session Management End-to-End Test Runner

Comprehensive test runner for session management system including:
- End-to-end integration tests
- Load and performance tests
- Cross-browser compatibility tests
- Real-world scenario simulations
"""

import os
import sys
import unittest
import time
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class SessionManagementTestRunner:
    """Comprehensive test runner for session management system"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all session management tests"""
        self.start_time = time.time()
        print("🧪 Starting Session Management End-to-End Tests")
        print("=" * 60)
        
        # Test suites to run
        test_suites = [
            ('Unit Tests', self._run_unit_tests),
            ('Integration Tests', self._run_integration_tests),
            ('End-to-End Tests', self._run_e2e_tests),
            ('Load Tests', self._run_load_tests),
            ('Security Tests', self._run_security_tests),
            ('Performance Tests', self._run_performance_tests)
        ]
        
        for suite_name, test_function in test_suites:
            print(f"\n📋 Running {suite_name}...")
            try:
                result = test_function()
                self.test_results[suite_name] = result
                
                if result['passed']:
                    print(f"✅ {suite_name}: PASSED ({result['tests_run']} tests)")
                else:
                    print(f"❌ {suite_name}: FAILED ({result['failures']} failures, {result['errors']} errors)")
                    
            except Exception as e:
                print(f"💥 {suite_name}: ERROR - {str(e)}")
                self.test_results[suite_name] = {
                    'passed': False,
                    'error': str(e),
                    'tests_run': 0,
                    'failures': 0,
                    'errors': 1
                }
        
        self.end_time = time.time()
        return self._generate_summary()
    
    def _run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests for session management"""
        try:
            # Import and run session management unit tests
            from tests.test_session_management import SessionManagementTest
            from tests.test_session_decorators_integration import SessionDecoratorsIntegrationTest
            
            suite = unittest.TestSuite()
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(SessionManagementTest))
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(SessionDecoratorsIntegrationTest))
            
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            return {
                'passed': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'details': {
                    'failure_messages': [str(f[1]) for f in result.failures],
                    'error_messages': [str(e[1]) for e in result.errors]
                }
            }
            
        except ImportError as e:
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': f"Could not import unit tests: {str(e)}"
            }
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        try:
            from tests.test_session_integration import SessionIntegrationTest
            from tests.test_platform_switching_session_management import PlatformSwitchingSessionTest
            
            suite = unittest.TestSuite()
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(SessionIntegrationTest))
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(PlatformSwitchingSessionTest))
            
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            return {
                'passed': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
        except ImportError:
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': "Integration test modules not found"
            }
    
    def _run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests"""
        try:
            from tests.integration.test_session_management_e2e import SessionManagementE2ETest
            
            suite = unittest.TestLoader().loadTestsFromTestCase(SessionManagementE2ETest)
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            return {
                'passed': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
        except ImportError:
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': "E2E test module not found"
            }
    
    def _run_load_tests(self) -> Dict[str, Any]:
        """Run load and performance tests"""
        try:
            from tests.integration.test_session_management_e2e import SessionManagementLoadTest
            
            suite = unittest.TestLoader().loadTestsFromTestCase(SessionManagementLoadTest)
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            return {
                'passed': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
        except ImportError:
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': "Load test module not found"
            }
    
    def _run_security_tests(self) -> Dict[str, Any]:
        """Run security tests"""
        try:
            from tests.security.test_session_security_hardening import SessionSecurityHardeningTest
            
            suite = unittest.TestLoader().loadTestsFromTestCase(SessionSecurityHardeningTest)
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            return {
                'passed': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
        except ImportError:
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': "Security test module not found"
            }
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        try:
            from tests.performance.test_session_load import SessionLoadTest
            
            suite = unittest.TestLoader().loadTestsFromTestCase(SessionLoadTest)
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            return {
                'passed': result.wasSuccessful(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            }
            
        except ImportError:
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': "Performance test module not found"
            }
    
    def _run_frontend_tests(self) -> Dict[str, Any]:
        """Run frontend JavaScript tests"""
        try:
            # Check if Node.js and npm are available
            subprocess.run(['node', '--version'], check=True, capture_output=True)
            subprocess.run(['npm', '--version'], check=True, capture_output=True)
            
            # Run frontend tests
            result = subprocess.run(
                ['npm', 'test'],
                cwd='tests/frontend',
                capture_output=True,
                text=True
            )
            
            return {
                'passed': result.returncode == 0,
                'tests_run': 1,  # Placeholder
                'failures': 0 if result.returncode == 0 else 1,
                'errors': 0,
                'output': result.stdout,
                'error_output': result.stderr
            }
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                'passed': False,
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'error': "Frontend testing environment not available"
            }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = sum(result.get('tests_run', 0) for result in self.test_results.values())
        total_failures = sum(result.get('failures', 0) for result in self.test_results.values())
        total_errors = sum(result.get('errors', 0) for result in self.test_results.values())
        
        passed_suites = sum(1 for result in self.test_results.values() if result.get('passed', False))
        total_suites = len(self.test_results)
        
        overall_success = total_failures == 0 and total_errors == 0
        
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'overall_success': overall_success,
            'summary': {
                'total_test_suites': total_suites,
                'passed_suites': passed_suites,
                'failed_suites': total_suites - passed_suites,
                'total_tests': total_tests,
                'passed_tests': total_tests - total_failures - total_errors,
                'failed_tests': total_failures,
                'error_tests': total_errors,
                'success_rate': ((total_tests - total_failures - total_errors) / max(total_tests, 1)) * 100
            },
            'test_results': self.test_results
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("SESSION MANAGEMENT TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Overall Success: {'✅ YES' if summary['overall_success'] else '❌ NO'}")
        print()
        print("Test Suites:")
        print(f"  Total: {summary['summary']['total_test_suites']}")
        print(f"  Passed: {summary['summary']['passed_suites']}")
        print(f"  Failed: {summary['summary']['failed_suites']}")
        print()
        print("Individual Tests:")
        print(f"  Total: {summary['summary']['total_tests']}")
        print(f"  Passed: {summary['summary']['passed_tests']}")
        print(f"  Failed: {summary['summary']['failed_tests']}")
        print(f"  Errors: {summary['summary']['error_tests']}")
        print(f"  Success Rate: {summary['summary']['success_rate']:.1f}%")
        
        if not summary['overall_success']:
            print(f"\n{'='*60}")
            print("FAILED TEST DETAILS")
            print(f"{'='*60}")
            for suite_name, result in summary['test_results'].items():
                if not result.get('passed', False):
                    print(f"\n❌ {suite_name}:")
                    if 'error' in result:
                        print(f"   Error: {result['error']}")
                    if result.get('failures', 0) > 0:
                        print(f"   Failures: {result['failures']}")
                    if result.get('errors', 0) > 0:
                        print(f"   Errors: {result['errors']}")

def main():
    """Main test runner function"""
    runner = SessionManagementTestRunner()
    
    try:
        summary = runner.run_all_tests()
        runner.print_summary(summary)
        
        # Save detailed report
        report_file = f"session_management_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if summary['overall_success']:
            print("\n🎉 All session management tests passed!")
            sys.exit(0)
        else:
            print("\n⚠️  Some session management tests failed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner failed with error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()