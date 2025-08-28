# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive WebSocket CORS Standardization Test Runner

This module provides a comprehensive test runner for all WebSocket CORS standardization
tests, including unit tests, integration tests, network simulation tests, and
performance tests. It provides detailed reporting and test categorization.
"""

import unittest
import sys
import os
import time
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import all test modules
from test_websocket_cors_comprehensive import (
    TestWebSocketConfigManager,
    TestCORSManager,
    TestWebSocketAuthHandler,
    TestWebSocketFactory,
    TestWebSocketIntegration,
    TestCORSMultipleOrigins,
    TestErrorRecoverySimulation,
    TestPerformanceLoad,
    TestWebSocketTestRunner,
)

from test_websocket_integration_scenarios import (
    TestWebSocketConnectionScenarios,
    TestWebSocketNamespaceIntegration,
    TestWebSocketAuthenticationFlow,
    TestWebSocketCrossBrowserCompatibility,
)

from test_websocket_network_simulation import (
    TestNetworkFailureSimulation,
    TestTransportFallbackScenarios,
    TestConnectionResilienceScenarios,
    TestNetworkLatencySimulation,
)

from test_websocket_performance_load import (
    TestWebSocketConfigurationPerformance,
    TestWebSocketAuthenticationPerformance,
    TestWebSocketFactoryPerformance,
    TestWebSocketMemoryUsage,
)


class WebSocketTestResult:
    """Enhanced test result tracking"""
    
    def __init__(self):
        self.category_results = {}
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.total_duration = 0
        self.start_time = None
        self.end_time = None
    
    def add_category_result(self, category: str, result: unittest.TestResult, duration: float):
        """Add test result for a category"""
        self.category_results[category] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'duration': duration,
            'successful': result.wasSuccessful()
        }
        
        self.total_tests += result.testsRun
        self.total_failures += len(result.failures)
        self.total_errors += len(result.errors)
        self.total_duration += duration
    
    def get_overall_success_rate(self) -> float:
        """Get overall success rate"""
        if self.total_tests == 0:
            return 0
        return (self.total_tests - self.total_failures - self.total_errors) / self.total_tests * 100
    
    def is_successful(self) -> bool:
        """Check if all tests were successful"""
        return self.total_failures == 0 and self.total_errors == 0


class ComprehensiveWebSocketTestRunner:
    """Comprehensive test runner for WebSocket CORS standardization tests"""
    
    def __init__(self, verbosity: int = 2):
        self.verbosity = verbosity
        self.test_categories = {
            'unit': {
                'name': 'Unit Tests',
                'description': 'Unit tests for individual WebSocket components',
                'classes': [
                    TestWebSocketConfigManager,
                    TestCORSManager,
                    TestWebSocketAuthHandler,
                    TestWebSocketFactory,
                ]
            },
            'integration': {
                'name': 'Integration Tests',
                'description': 'End-to-end integration tests for WebSocket scenarios',
                'classes': [
                    TestWebSocketIntegration,
                    TestWebSocketConnectionScenarios,
                    TestWebSocketNamespaceIntegration,
                    TestWebSocketAuthenticationFlow,
                    TestWebSocketCrossBrowserCompatibility,
                ]
            },
            'cors': {
                'name': 'CORS Tests',
                'description': 'CORS-specific tests with multiple origin configurations',
                'classes': [
                    TestCORSMultipleOrigins,
                ]
            },
            'network': {
                'name': 'Network Simulation Tests',
                'description': 'Network condition simulation and error recovery tests',
                'classes': [
                    TestNetworkFailureSimulation,
                    TestTransportFallbackScenarios,
                    TestConnectionResilienceScenarios,
                    TestNetworkLatencySimulation,
                    TestErrorRecoverySimulation,
                ]
            },
            'performance': {
                'name': 'Performance Tests',
                'description': 'Performance and load testing for WebSocket components',
                'classes': [
                    TestWebSocketConfigurationPerformance,
                    TestWebSocketAuthenticationPerformance,
                    TestWebSocketFactoryPerformance,
                    TestWebSocketMemoryUsage,
                    TestPerformanceLoad,
                ]
            }
        }
    
    def run_category(self, category: str) -> unittest.TestResult:
        """Run tests for a specific category"""
        if category not in self.test_categories:
            raise ValueError(f"Unknown test category: {category}")
        
        category_info = self.test_categories[category]
        
        print(f"\n🧪 Running {category_info['name']}")
        print(f"   {category_info['description']}")
        print("   " + "=" * 60)
        
        # Create test suite for category
        suite = unittest.TestSuite()
        for test_class in category_info['classes']:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=self.verbosity, stream=sys.stdout)
        result = runner.run(suite)
        
        return result
    
    def run_all_tests(self, categories: Optional[List[str]] = None) -> WebSocketTestResult:
        """Run all tests or specified categories"""
        if categories is None:
            categories = list(self.test_categories.keys())
        
        overall_result = WebSocketTestResult()
        overall_result.start_time = datetime.now()
        
        print("🚀 Starting Comprehensive WebSocket CORS Standardization Tests")
        print("=" * 80)
        print(f"   Test Categories: {', '.join(categories)}")
        print(f"   Start Time: {overall_result.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Run each category
        for category in categories:
            if category not in self.test_categories:
                print(f"⚠️  Warning: Unknown category '{category}', skipping...")
                continue
            
            start_time = time.time()
            result = self.run_category(category)
            end_time = time.time()
            duration = end_time - start_time
            
            overall_result.add_category_result(category, result, duration)
            
            # Print category summary
            category_info = self.test_categories[category]
            success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
            
            print(f"\n📊 {category_info['name']} Summary:")
            print(f"   Tests run: {result.testsRun}")
            print(f"   Failures: {len(result.failures)}")
            print(f"   Errors: {len(result.errors)}")
            print(f"   Success rate: {success_rate:.1f}%")
            print(f"   Duration: {duration:.2f}s")
            
            if result.failures:
                print(f"\n❌ Failures in {category_info['name']}:")
                for test, traceback in result.failures:
                    print(f"   - {test}")
            
            if result.errors:
                print(f"\n💥 Errors in {category_info['name']}:")
                for test, traceback in result.errors:
                    print(f"   - {test}")
        
        overall_result.end_time = datetime.now()
        return overall_result
    
    def print_final_summary(self, result: WebSocketTestResult):
        """Print final test summary"""
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE WEBSOCKET TEST SUMMARY")
        print("=" * 80)
        
        print(f"📅 Test Execution:")
        print(f"   Start Time: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End Time: {result.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Total Duration: {result.total_duration:.2f}s")
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {result.total_tests}")
        print(f"   Total Failures: {result.total_failures}")
        print(f"   Total Errors: {result.total_errors}")
        print(f"   Overall Success Rate: {result.get_overall_success_rate():.1f}%")
        
        print(f"\n📋 Category Breakdown:")
        for category, category_result in result.category_results.items():
            category_info = self.test_categories[category]
            status = "✅ PASS" if category_result['successful'] else "❌ FAIL"
            
            print(f"   {status} {category_info['name']}:")
            print(f"      Tests: {category_result['tests_run']}")
            print(f"      Success Rate: {category_result['success_rate']:.1f}%")
            print(f"      Duration: {category_result['duration']:.2f}s")
        
        # Print recommendations
        print(f"\n💡 Recommendations:")
        
        if result.is_successful():
            print("   🎉 All tests passed! The WebSocket CORS standardization system is ready for production.")
            print("   📝 Consider running these tests regularly as part of your CI/CD pipeline.")
        else:
            print("   🔧 Some tests failed. Please review the failures and errors above.")
            print("   🐛 Focus on fixing unit tests first, then integration tests.")
            print("   ⚡ Performance issues may indicate need for optimization.")
        
        # Print test coverage areas
        print(f"\n🎯 Test Coverage Areas:")
        print("   ✅ Configuration Management")
        print("   ✅ CORS Origin Validation")
        print("   ✅ Authentication & Authorization")
        print("   ✅ WebSocket Factory & Setup")
        print("   ✅ End-to-End Integration")
        print("   ✅ Network Failure Simulation")
        print("   ✅ Performance & Load Testing")
        print("   ✅ Memory Usage & Leak Detection")
        
        if result.is_successful():
            print("\n🏆 COMPREHENSIVE WEBSOCKET CORS STANDARDIZATION TESTS: ALL PASSED!")
        else:
            print("\n⚠️  COMPREHENSIVE WEBSOCKET CORS STANDARDIZATION TESTS: SOME FAILURES")
        
        print("=" * 80)


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Comprehensive WebSocket CORS Standardization Test Runner')
    parser.add_argument(
        '--categories', 
        nargs='+', 
        choices=['unit', 'integration', 'cors', 'network', 'performance', 'all'],
        default=['all'],
        help='Test categories to run (default: all)'
    )
    parser.add_argument(
        '--verbosity', 
        type=int, 
        choices=[0, 1, 2], 
        default=2,
        help='Test output verbosity (0=quiet, 1=normal, 2=verbose)'
    )
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List available test categories and exit'
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = ComprehensiveWebSocketTestRunner(verbosity=args.verbosity)
    
    # List categories if requested
    if args.list_categories:
        print("📋 Available Test Categories:")
        print("=" * 50)
        for category, info in runner.test_categories.items():
            print(f"   {category}: {info['name']}")
            print(f"      {info['description']}")
            print(f"      Test Classes: {len(info['classes'])}")
        return 0
    
    # Determine categories to run
    categories = args.categories
    if 'all' in categories:
        categories = list(runner.test_categories.keys())
    
    try:
        # Run tests
        result = runner.run_all_tests(categories)
        
        # Print final summary
        runner.print_final_summary(result)
        
        # Return appropriate exit code
        return 0 if result.is_successful() else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\n💥 Test runner error: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)