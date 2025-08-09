#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security and Performance test runner for Task 5.3

Runs all security and performance tests with comprehensive reporting.
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_security_performance_tests(test_pattern=None, verbosity=2):
    """Run the security and performance test suite"""
    
    # Test modules
    test_modules = [
        'tests.security.test_credential_security',
        'tests.security.test_platform_access',
        'tests.performance.test_platform_queries',
        'tests.performance.test_platform_load'
    ]
    
    if test_pattern:
        test_modules = [m for m in test_modules if test_pattern in m]
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load tests from each module
    for module_name in test_modules:
        try:
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
            print(f"✓ Loaded tests from {module_name}")
        except Exception as e:
            print(f"✗ Failed to load {module_name}: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        buffer=True
    )
    
    print(f"\nRunning {suite.countTestCases()} security and performance tests...")
    print("=" * 70)
    
    result = runner.run(suite)
    
    # Print summary
    print("=" * 70)
    print(f"Security & Performance Tests Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 ALL SECURITY & PERFORMANCE TESTS PASSED!")
        print("\nTask 5.3: Security and Performance Testing - COMPLETE ✅")
    else:
        print(f"\n❌ {len(result.failures + result.errors)} TESTS FAILED")
    
    return success

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run security and performance tests')
    parser.add_argument('--pattern', help='Filter tests by pattern')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet output')
    
    args = parser.parse_args()
    
    verbosity = 1
    if args.verbose:
        verbosity = 2
    elif args.quiet:
        verbosity = 0
    
    print("Task 5.3: Security and Performance Testing")
    print("=" * 50)
    
    success = run_security_performance_tests(args.pattern, verbosity)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())