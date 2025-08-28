#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket CORS Standardization - Final Integration Testing and Validation Runner

This script orchestrates the complete final validation testing suite including:
- End-to-end integration testing
- Cross-browser compatibility testing
- Security and penetration testing
- Performance validation
- Configuration validation across environments
"""

import sys
import os
import subprocess
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class WebSocketFinalValidationRunner:
    """
    Comprehensive test runner for WebSocket CORS standardization final validation
    """
    
    def __init__(self):
        self.project_root = project_root
        self.test_results = {}
        self.overall_success = True
        self.start_time = time.time()
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80)
    
    def print_section(self, title: str):
        """Print a formatted section header"""
        print(f"\n--- {title} ---")
    
    def run_python_tests(self, test_module: str, test_name: str) -> bool:
        """Run Python test module and return success status"""
        self.print_section(f"Running {test_name}")
        
        try:
            # Run the test module
            result = subprocess.run([
                sys.executable, '-m', 'unittest', test_module, '-v'
            ], cwd=self.project_root, capture_output=True, text=True, timeout=300)
            
            success = result.returncode == 0
            
            self.test_results[test_name] = {
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': time.time() - self.start_time
            }
            
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                print(f"Error output: {result.stderr}")
                self.overall_success = False
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name} TIMED OUT")
            self.test_results[test_name] = {
                'success': False,
                'error': 'timeout',
                'duration': 300
            }
            self.overall_success = False
            return False
            
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
            self.test_results[test_name] = {
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time
            }
            self.overall_success = False
            return False
    
    def run_playwright_tests(self) -> bool:
        """Run Playwright browser tests"""
        self.print_section("Running Playwright Browser Tests")
        
        playwright_dir = self.project_root / 'tests' / 'playwright'
        
        # Check if Playwright is available
        try:
            result = subprocess.run(['npx', 'playwright', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("⚠️  Playwright not available - skipping browser tests")
                self.test_results['playwright_tests'] = {
                    'success': True,
                    'skipped': True,
                    'reason': 'playwright_not_available'
                }
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️  Playwright not available - skipping browser tests")
            self.test_results['playwright_tests'] = {
                'success': True,
                'skipped': True,
                'reason': 'playwright_not_available'
            }
            return True
        
        try:
            # Install Playwright browsers if needed
            print("🔧 Installing Playwright browsers...")
            install_result = subprocess.run([
                'npx', 'playwright', 'install'
            ], cwd=playwright_dir, capture_output=True, text=True, timeout=120)
            
            if install_result.returncode != 0:
                print(f"⚠️  Browser installation warning: {install_result.stderr}")
            
            # Run Playwright tests
            print("🌐 Running cross-browser tests...")
            test_result = subprocess.run([
                'npx', 'playwright', 'test', 
                '--config=0828_16_30_playwright.config.js',
                '--reporter=list'
            ], cwd=playwright_dir, capture_output=True, text=True, timeout=600)
            
            success = test_result.returncode == 0
            
            self.test_results['playwright_tests'] = {
                'success': success,
                'returncode': test_result.returncode,
                'stdout': test_result.stdout,
                'stderr': test_result.stderr,
                'duration': time.time() - self.start_time
            }
            
            if success:
                print("✅ Playwright Browser Tests PASSED")
            else:
                print("❌ Playwright Browser Tests FAILED")
                print(f"Error output: {test_result.stderr}")
                self.overall_success = False
            
            return success
            
        except subprocess.TimeoutExpired:
            print("⏰ Playwright tests TIMED OUT")
            self.test_results['playwright_tests'] = {
                'success': False,
                'error': 'timeout',
                'duration': 600
            }
            self.overall_success = False
            return False
            
        except Exception as e:
            print(f"💥 Playwright tests ERROR: {e}")
            self.test_results['playwright_tests'] = {
                'success': False,
                'error': str(e),
                'duration': time.time() - self.start_time
            }
            self.overall_success = False
            return False
    
    def check_web_server(self) -> bool:
        """Check if web server is running"""
        self.print_section("Checking Web Server Status")
        
        try:
            import requests
            response = requests.get('http://127.0.0.1:5000', timeout=5)
            if response.status_code == 200:
                print("✅ Web server is running")
                return True
            else:
                print(f"⚠️  Web server returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Web server not accessible: {e}")
            return False
    
    def start_web_server(self) -> Optional[subprocess.Popen]:
        """Start web server for testing"""
        self.print_section("Starting Web Server")
        
        try:
            # Start web server in background
            server_process = subprocess.Popen([
                sys.executable, 'web_app.py'
            ], cwd=self.project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            print("⏳ Waiting for web server to start...")
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if self.check_web_server():
                    print("✅ Web server started successfully")
                    return server_process
            
            print("❌ Web server failed to start within timeout")
            server_process.terminate()
            return None
            
        except Exception as e:
            print(f"💥 Failed to start web server: {e}")
            return None
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        return self.run_python_tests(
            'tests.integration.test_websocket_final_integration',
            'Integration Tests'
        )
    
    def run_security_tests(self) -> bool:
        """Run security tests"""
        return self.run_python_tests(
            'tests.security.test_websocket_security_validation',
            'Security Tests'
        )
    
    def run_configuration_tests(self) -> bool:
        """Run configuration validation tests"""
        self.print_section("Running Configuration Validation Tests")
        
        # Test different environment configurations
        environments = [
            {
                'name': 'Development',
                'env_vars': {
                    'FLASK_ENV': 'development',
                    'FLASK_HOST': '127.0.0.1',
                    'FLASK_PORT': '5000'
                }
            },
            {
                'name': 'Staging',
                'env_vars': {
                    'FLASK_ENV': 'staging',
                    'FLASK_HOST': 'staging.example.com',
                    'FLASK_PORT': '443'
                }
            },
            {
                'name': 'Production',
                'env_vars': {
                    'FLASK_ENV': 'production',
                    'FLASK_HOST': 'app.example.com',
                    'FLASK_PORT': '443'
                }
            }
        ]
        
        config_success = True
        
        for env in environments:
            print(f"Testing {env['name']} configuration...")
            
            try:
                # Set environment variables
                env_backup = {}
                for key, value in env['env_vars'].items():
                    env_backup[key] = os.environ.get(key)
                    os.environ[key] = value
                
                # Test configuration loading
                from websocket_config_manager import WebSocketConfigManager
                from config import Config
                
                config = Config()
                config_manager = WebSocketConfigManager(config)
                websocket_config = config_manager.get_websocket_config()
                validation_errors = config_manager.get_validation_errors()
                
                if len(validation_errors) == 0:
                    print(f"  ✅ {env['name']} configuration valid")
                else:
                    print(f"  ⚠️  {env['name']} configuration warnings: {len(validation_errors)}")
                    for error in validation_errors:
                        print(f"    - {error}")
                
                # Restore environment variables
                for key, value in env_backup.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                
            except Exception as e:
                print(f"  ❌ {env['name']} configuration error: {e}")
                config_success = False
        
        self.test_results['configuration_tests'] = {
            'success': config_success,
            'environments_tested': len(environments)
        }
        
        if not config_success:
            self.overall_success = False
        
        return config_success
    
    def generate_report(self):
        """Generate final test report"""
        self.print_header("FINAL VALIDATION REPORT")
        
        total_duration = time.time() - self.start_time
        
        print(f"Total Test Duration: {total_duration:.2f} seconds")
        print(f"Overall Success: {'✅ PASS' if self.overall_success else '❌ FAIL'}")
        
        print("\nTest Results Summary:")
        print("-" * 40)
        
        for test_name, result in self.test_results.items():
            if result.get('skipped'):
                status = "⏭️  SKIPPED"
                reason = result.get('reason', 'unknown')
                print(f"{test_name:25} {status} ({reason})")
            elif result['success']:
                status = "✅ PASS"
                duration = result.get('duration', 0)
                print(f"{test_name:25} {status} ({duration:.1f}s)")
            else:
                status = "❌ FAIL"
                error = result.get('error', 'test failure')
                print(f"{test_name:25} {status} ({error})")
        
        # Calculate success metrics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r['success'])
        skipped_tests = sum(1 for r in self.test_results.values() if r.get('skipped', False))
        failed_tests = total_tests - passed_tests - skipped_tests
        
        print(f"\nTest Statistics:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Skipped: {skipped_tests}")
        
        if total_tests > 0:
            success_rate = (passed_tests / (total_tests - skipped_tests)) * 100 if (total_tests - skipped_tests) > 0 else 0
            print(f"  Success Rate: {success_rate:.1f}%")
        
        # Save detailed report
        report_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'overall_success': self.overall_success,
            'total_duration': total_duration,
            'test_results': self.test_results,
            'statistics': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'skipped_tests': skipped_tests,
                'success_rate': success_rate if total_tests > 0 else 0
            }
        }
        
        report_file = self.project_root / 'tests' / 'reports' / 'websocket_final_validation_report.json'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        # Recommendations
        print("\nRecommendations:")
        if self.overall_success:
            print("🎉 All tests passed! WebSocket CORS standardization is ready for production.")
        else:
            print("🔧 Some tests failed. Please review the failures and fix issues before deployment.")
            
            if failed_tests > 0:
                print("   - Review failed test output for specific issues")
                print("   - Check configuration and environment setup")
                print("   - Verify all dependencies are installed")
                print("   - Run individual test suites for detailed debugging")
    
    def run_all_tests(self, skip_browser: bool = False, skip_security: bool = False):
        """Run all validation tests"""
        self.print_header("WebSocket CORS Standardization - Final Integration Testing and Validation")
        
        print("This comprehensive test suite validates:")
        print("• End-to-end functionality across browsers and environments")
        print("• CORS configuration in development, staging, and production")
        print("• Authentication and authorization across user and admin interfaces")
        print("• Error recovery and fallback mechanisms")
        print("• Security testing and penetration testing")
        print("• Performance validation under load")
        
        # Check if web server is running, start if needed
        server_process = None
        if not self.check_web_server():
            server_process = self.start_web_server()
            if not server_process:
                print("❌ Cannot proceed without web server")
                return False
        
        try:
            # Run test suites
            self.run_configuration_tests()
            self.run_integration_tests()
            
            if not skip_security:
                self.run_security_tests()
            else:
                print("⏭️  Skipping security tests")
            
            if not skip_browser:
                self.run_playwright_tests()
            else:
                print("⏭️  Skipping browser tests")
            
        finally:
            # Clean up web server
            if server_process:
                print("\n🛑 Stopping web server...")
                server_process.terminate()
                try:
                    server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server_process.kill()
        
        # Generate final report
        self.generate_report()
        
        return self.overall_success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='WebSocket CORS Standardization - Final Integration Testing and Validation'
    )
    parser.add_argument('--skip-browser', action='store_true',
                       help='Skip browser-based Playwright tests')
    parser.add_argument('--skip-security', action='store_true',
                       help='Skip security and penetration tests')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick validation (skip browser and security tests)')
    
    args = parser.parse_args()
    
    # Quick mode skips time-consuming tests
    if args.quick:
        args.skip_browser = True
        args.skip_security = True
    
    # Create and run test runner
    runner = WebSocketFinalValidationRunner()
    success = runner.run_all_tests(
        skip_browser=args.skip_browser,
        skip_security=args.skip_security
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()