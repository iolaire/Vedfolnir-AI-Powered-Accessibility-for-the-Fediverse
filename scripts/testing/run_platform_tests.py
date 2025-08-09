#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test runner for Task 5.1: Comprehensive Unit Testing

Runs all platform-aware unit tests and provides coverage reporting.
"""

import unittest
import sys
import os
from io import StringIO

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_suite(test_pattern=None, verbosity=2):
    """Run the comprehensive unit test suite"""
    
    # Test modules to run
    test_modules = [
        'tests.test_platform_models',
        'tests.test_platform_context', 
        'tests.test_platform_database',
        'tests.test_platform_encryption'
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
    
    print(f"\nRunning {suite.countTestCases()} tests...")
    print("=" * 70)
    
    result = runner.run(suite)
    
    # Print summary
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            # Safely extract error message without shell injection risk
            error_msg = str(traceback).split('AssertionError:')[-1].strip()[:200]
            print(f"- {test}: {error_msg}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            # Safely extract error message without shell injection risk
            error_msg = str(traceback).split('Exception:')[-1].strip()[:200]
            print(f"- {test}: {error_msg}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n❌ {len(result.failures + result.errors)} TESTS FAILED")
    
    return success

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run platform-aware unit tests')
    parser.add_argument('--pattern', help='Filter tests by pattern')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet output')
    
    args = parser.parse_args()
    
    verbosity = 1
    if args.verbose:
        verbosity = 2
    elif args.quiet:
        verbosity = 0
    
    print("Task 5.1: Comprehensive Unit Testing")
    print("=" * 50)
    
    success = run_test_suite(args.pattern, verbosity)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())