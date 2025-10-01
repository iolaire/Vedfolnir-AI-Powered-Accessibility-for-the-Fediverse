# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Docker Compose Integration Test Runner
Comprehensive test runner for Docker Compose integration tests
"""

import unittest
import sys
import os
import argparse
import time
import requests
import docker
from datetime import datetime

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

class DockerComposeTestRunner:
    """Test runner for Docker Compose integration tests"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.base_url = "http://localhost:5000"
        self.test_modules = [
            'test_service_interactions',
            'test_activitypub_integration', 
            'test_ollama_integration',
            'test_websocket_functionality',
            'test_performance_benchmarks'
        ]
    
    def check_docker_compose_status(self):
        """Check if Docker Compose services are running"""
        print("🔍 Checking Docker Compose services...")
        
        try:
            containers = self.docker_client.containers.list()
            vedfolnir_containers = [c for c in containers if 'vedfolnir' in c.name.lower()]
            
            if not vedfolnir_containers:
                print("❌ No Vedfolnir containers found. Please start Docker Compose services first.")
                print("   Run: docker-compose up -d")
                return False
            
            print(f"✅ Found {len(vedfolnir_containers)} Vedfolnir containers:")
            for container in vedfolnir_containers:
                status = "🟢" if container.status == 'running' else "🔴"
                print(f"   {status} {container.name}: {container.status}")
            
            return True
            
        except docker.errors.DockerException as e:
            print(f"❌ Docker error: {e}")
            return False
    
    def wait_for_services(self, timeout=120):
        """Wait for services to be ready"""
        print("⏳ Waiting for services to be ready...")
        
        services = {
            'Web Application': f"{self.base_url}/health",
            'Database': f"{self.base_url}/api/health/database", 
            'Redis': f"{self.base_url}/api/health/redis"
        }
        
        start_time = time.time()
        
        for service_name, health_url in services.items():
            print(f"   Checking {service_name}...")
            
            for i in range(timeout):
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        print(f"   ✅ {service_name} ready")
                        break
                except requests.exceptions.RequestException:
                    pass
                
                if time.time() - start_time > timeout:
                    print(f"   ❌ {service_name} failed to start within timeout")
                    return False
                
                time.sleep(1)
            else:
                print(f"   ❌ {service_name} not responding")
                return False
        
        print("✅ All services ready")
        return True
    
    def run_test_suite(self, test_pattern=None, verbose=True):
        """Run the integration test suite"""
        print(f"\n🧪 Running Docker Compose Integration Tests")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_docker_compose_status():
            return False
        
        if not self.wait_for_services():
            return False
        
        # Discover and run tests
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test modules
        test_dir = os.path.dirname(__file__)
        
        if test_pattern:
            # Run specific test pattern
            pattern = f"*{test_pattern}*.py"
            discovered_tests = loader.discover(test_dir, pattern=pattern)
        else:
            # Run all integration tests
            for module_name in self.test_modules:
                try:
                    module = __import__(module_name, fromlist=[''])
                    module_tests = loader.loadTestsFromModule(module)
                    suite.addTests(module_tests)
                except ImportError as e:
                    print(f"⚠️ Could not import {module_name}: {e}")
                    continue
        
        if test_pattern:
            suite.addTests(discovered_tests)
        
        # Run tests
        runner = unittest.TextTestRunner(
            verbosity=2 if verbose else 1,
            stream=sys.stdout,
            buffer=False
        )
        
        print(f"\n🚀 Starting test execution...")
        result = runner.run(suite)
        
        # Report results
        self.report_results(result)
        
        return result.wasSuccessful()
    
    def report_results(self, result):
        """Report test results"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
        successful = total_tests - failures - errors - skipped
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failures: {failures}")
        print(f"🔥 Errors: {errors}")
        print(f"⏭️ Skipped: {skipped}")
        
        if result.wasSuccessful():
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Docker Compose integration is working correctly")
        else:
            print("\n⚠️ SOME TESTS FAILED")
            print("❌ Please review the failures above")
        
        # Detailed failure/error reporting
        if result.failures:
            print("\n🔍 FAILURE DETAILS:")
            for test, traceback in result.failures:
                print(f"\n❌ {test}:")
                print(traceback)
        
        if result.errors:
            print("\n🔍 ERROR DETAILS:")
            for test, traceback in result.errors:
                print(f"\n🔥 {test}:")
                print(traceback)
        
        print("\n" + "=" * 60)
    
    def run_specific_test(self, test_name):
        """Run a specific test"""
        print(f"🎯 Running specific test: {test_name}")
        
        # Check prerequisites
        if not self.check_docker_compose_status():
            return False
        
        if not self.wait_for_services():
            return False
        
        # Run specific test
        loader = unittest.TestLoader()
        
        try:
            # Try to load as module.class.method
            suite = loader.loadTestsFromName(test_name)
        except (ImportError, AttributeError):
            # Try to load as pattern
            test_dir = os.path.dirname(__file__)
            suite = loader.discover(test_dir, pattern=f"*{test_name}*.py")
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Docker Compose Integration Test Runner')
    parser.add_argument('--test', '-t', help='Run specific test (name or pattern)')
    parser.add_argument('--pattern', '-p', help='Run tests matching pattern')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--list', '-l', action='store_true', help='List available tests')
    
    args = parser.parse_args()
    
    runner = DockerComposeTestRunner()
    
    if args.list:
        print("📋 Available test modules:")
        for module in runner.test_modules:
            print(f"   • {module}")
        return
    
    if args.test:
        success = runner.run_specific_test(args.test)
    else:
        success = runner.run_test_suite(test_pattern=args.pattern, verbose=args.verbose)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()