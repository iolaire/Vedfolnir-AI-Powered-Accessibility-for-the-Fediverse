#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSS Security Test Runner - Comprehensive test suite for CSS security enhancement
"""

import os
import sys
import unittest
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.scripts.css_security_scanner import CSSSecurityScanner


def run_css_security_tests(verbose=False, report=False):
    """Run CSS security test suite"""
    
    if report:
        print("=== CSS Security Enhancement Pre-Test Report ===\n")
        scanner = CSSSecurityScanner()
        scanner.generate_report()
        print("\n" + "="*50 + "\n")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add CSS security enhancement tests
    try:
        from tests.security.test_css_security_enhancement import TestCSSSecurityEnhancement
        suite.addTests(loader.loadTestsFromTestCase(TestCSSSecurityEnhancement))
        print("✅ Loaded CSS Security Enhancement tests")
    except ImportError as e:
        print(f"❌ Failed to load CSS Security Enhancement tests: {e}")
    
    # Add CSP compliance tests
    try:
        from tests.security.test_csp_compliance import TestCSPCompliance
        suite.addTests(loader.loadTestsFromTestCase(TestCSPCompliance))
        print("✅ Loaded CSP Compliance tests")
    except ImportError as e:
        print(f"❌ Failed to load CSP Compliance tests: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\n❌ Failed Tests:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n💥 Error Tests:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed'}")
    
    return success


def main():
    parser = argparse.ArgumentParser(description='CSS Security Test Runner')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose test output')
    parser.add_argument('--report', '-r', action='store_true', help='Show pre-test report')
    parser.add_argument('--scan-only', action='store_true', help='Only run CSS scanner, no tests')
    
    args = parser.parse_args()
    
    if args.scan_only:
        scanner = CSSSecurityScanner()
        scanner.generate_report()
        return
    
    success = run_css_security_tests(verbose=args.verbose, report=args.report)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()