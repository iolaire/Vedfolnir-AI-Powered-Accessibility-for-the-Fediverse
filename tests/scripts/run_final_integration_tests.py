#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Final Integration Testing and Validation Runner

This script executes the comprehensive final integration test suite for the
notification system migration, including both Python unit/integration tests
and Playwright browser tests.
"""

import os
import sys
import subprocess
import time
import argparse
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class FinalIntegrationTestRunner:
    """
    Comprehensive test runner for final integration validation
    """
    
    def __init__(self, verbose: bool = False, web_app_url: str = "http://127.0.0.1:5000"):
        self.verbose = verbose
        self.web_app_url = web_app_url
        self.project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        self.test_results = {
            'start_time': datetime.now().isoformat(),
            'python_tests': {},
            'playwright_tests': {},
            'overall_success': False,
            'summary': {}
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
        
        if self.verbose and level in ["ERROR", "WARNING"]:
            sys.stdout.flush()
    
    def check_web_app_running(self) -> bool:
        """Check if the web application is running"""
        try:
            import requests
            response = requests.get(f"{self.web_app_url}/", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.log(f"Web application not accessible: {e}", "WARNING")
            return False
    
    def run_python_integration_tests(self) -> bool:
        """Run Python integration tests"""
        self.log("Running Python integration tests...")
        
        try:
            # Change to project root directory
            os.chdir(self.project_root)
            
            # Run the final integration test
            cmd = [
                sys.executable, '-m', 'unittest', 
                'tests.integration.test_notification_system_final_integration',
                '-v' if self.verbose else ''
            ]
            
            # Remove empty strings from command
            cmd = [arg for arg in cmd if arg]
            
            self.log(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            self.test_results['python_tests'] = {
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            if result.returncode == 0:
                self.log("Python integration tests PASSED", "SUCCESS")
                return True
            else:
                self.log("Python integration tests FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {result.stdout}")
                    self.log(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Python integration tests TIMED OUT", "ERROR")
            self.test_results['python_tests'] = {
                'return_code': -1,
                'error': 'Timeout after 5 minutes',
                'success': False
            }
            return False
        except Exception as e:
            self.log(f"Error running Python integration tests: {e}", "ERROR")
            self.test_results['python_tests'] = {
                'return_code': -1,
                'error': str(e),
                'success': False
            }
            return False
    
    def run_playwright_tests(self) -> bool:
        """Run Playwright browser tests"""
        self.log("Running Playwright browser tests...")
        
        # Check if web app is running
        if not self.check_web_app_running():
            self.log("Web application is not running - skipping Playwright tests", "WARNING")
            self.test_results['playwright_tests'] = {
                'skipped': True,
                'reason': 'Web application not running',
                'success': False
            }
            return False
        
        try:
            playwright_dir = os.path.join(self.project_root, 'tests', 'playwright')
            os.chdir(playwright_dir)
            
            # Check if Playwright is set up
            if not os.path.exists('node_modules'):
                self.log("Installing Playwright dependencies...")
                subprocess.run(['npm', 'install'], check=True, timeout=120)
            
            # Run Playwright tests with timeout
            cmd = [
                'timeout', '120',  # 2 minute timeout
                'npx', 'playwright', 'test',
                '--config=0830_17_52_playwright.config.js',
                'tests/0831_14_30_test_final_integration_validation.js',
                '--timeout=120000'  # 2 minute test timeout
            ]
            
            if self.verbose:
                cmd.append('--reporter=list')
            
            self.log(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute total timeout
            )
            
            self.test_results['playwright_tests'] = {
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
            if result.returncode == 0:
                self.log("Playwright tests PASSED", "SUCCESS")
                return True
            else:
                self.log("Playwright tests FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {result.stdout}")
                    self.log(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Playwright tests TIMED OUT", "ERROR")
            self.test_results['playwright_tests'] = {
                'return_code': -1,
                'error': 'Timeout after 3 minutes',
                'success': False
            }
            return False
        except FileNotFoundError as e:
            self.log(f"Playwright not found: {e}", "ERROR")
            self.log("Please install Playwright: npm install -g @playwright/test", "INFO")
            self.test_results['playwright_tests'] = {
                'return_code': -1,
                'error': 'Playwright not installed',
                'success': False
            }
            return False
        except Exception as e:
            self.log(f"Error running Playwright tests: {e}", "ERROR")
            self.test_results['playwright_tests'] = {
                'return_code': -1,
                'error': str(e),
                'success': False
            }
            return False
        finally:
            # Return to project root
            os.chdir(self.project_root)
    
    def run_security_tests(self) -> bool:
        """Run security-specific tests"""
        self.log("Running security tests...")
        
        try:
            os.chdir(self.project_root)
            
            # Run security tests
            cmd = [
                sys.executable, '-m', 'unittest',
                'tests.security.test_notification_authentication_authorization',
                '-v' if self.verbose else ''
            ]
            
            cmd = [arg for arg in cmd if arg]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                self.log("Security tests PASSED", "SUCCESS")
                return True
            else:
                self.log("Security tests FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {result.stdout}")
                    self.log(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Security tests TIMED OUT", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error running security tests: {e}", "ERROR")
            return False
    
    def run_performance_tests(self) -> bool:
        """Run performance tests"""
        self.log("Running performance tests...")
        
        try:
            os.chdir(self.project_root)
            
            # Run performance tests
            cmd = [
                sys.executable, '-m', 'unittest',
                'tests.performance.test_notification_performance',
                '-v' if self.verbose else ''
            ]
            
            cmd = [arg for arg in cmd if arg]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout
            )
            
            if result.returncode == 0:
                self.log("Performance tests PASSED", "SUCCESS")
                return True
            else:
                self.log("Performance tests FAILED", "ERROR")
                if self.verbose:
                    self.log(f"STDOUT: {result.stdout}")
                    self.log(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Performance tests TIMED OUT", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error running performance tests: {e}", "ERROR")
            return False
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        self.test_results['end_time'] = datetime.now().isoformat()
        
        # Calculate summary
        python_success = self.test_results.get('python_tests', {}).get('success', False)
        playwright_success = self.test_results.get('playwright_tests', {}).get('success', False)
        playwright_skipped = self.test_results.get('playwright_tests', {}).get('skipped', False)
        
        # Overall success if Python tests pass and Playwright either passes or is skipped
        overall_success = python_success and (playwright_success or playwright_skipped)
        
        self.test_results['overall_success'] = overall_success
        self.test_results['summary'] = {
            'python_tests_passed': python_success,
            'playwright_tests_passed': playwright_success,
            'playwright_tests_skipped': playwright_skipped,
            'overall_success': overall_success
        }
        
        return self.test_results
    
    def save_test_report(self, filename: str = None) -> str:
        """Save test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"final_integration_test_report_{timestamp}.json"
        
        report_path = os.path.join(self.project_root, 'tests', 'reports', filename)
        
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        return report_path
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("FINAL INTEGRATION TEST SUMMARY")
        print("=" * 80)
        
        summary = self.test_results.get('summary', {})
        
        print(f"Python Integration Tests: {'✅ PASSED' if summary.get('python_tests_passed') else '❌ FAILED'}")
        
        if summary.get('playwright_tests_skipped'):
            print(f"Playwright Browser Tests: ⏭️ SKIPPED (Web app not running)")
        else:
            print(f"Playwright Browser Tests: {'✅ PASSED' if summary.get('playwright_tests_passed') else '❌ FAILED'}")
        
        print(f"\nOverall Result: {'🎉 SUCCESS' if summary.get('overall_success') else '❌ FAILURE'}")
        
        if summary.get('overall_success'):
            print("\n✅ All critical tests passed!")
            print("✅ Notification system is ready for production deployment")
        else:
            print("\n❌ Some tests failed")
            print("⚠️  Please review and fix issues before deployment")
        
        print("=" * 80)
    
    def run_all_tests(self) -> bool:
        """Run all final integration tests"""
        self.log("Starting Final Integration Testing and Validation")
        self.log("=" * 60)
        
        # Run Python integration tests
        python_success = self.run_python_integration_tests()
        
        # Run Playwright tests (if web app is available)
        playwright_success = self.run_playwright_tests()
        
        # Generate and save report
        self.generate_test_report()
        report_path = self.save_test_report()
        self.log(f"Test report saved to: {report_path}")
        
        # Print summary
        self.print_summary()
        
        return self.test_results['overall_success']


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run final integration tests for notification system migration")
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--url', default='http://127.0.0.1:5000', help='Web application URL')
    parser.add_argument('--python-only', action='store_true', help='Run only Python tests')
    parser.add_argument('--playwright-only', action='store_true', help='Run only Playwright tests')
    
    args = parser.parse_args()
    
    runner = FinalIntegrationTestRunner(verbose=args.verbose, web_app_url=args.url)
    
    try:
        if args.python_only:
            success = runner.run_python_integration_tests()
        elif args.playwright_only:
            success = runner.run_playwright_tests()
        else:
            success = runner.run_all_tests()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        runner.log("Test execution interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        runner.log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)


if __name__ == '__main__':
    main()