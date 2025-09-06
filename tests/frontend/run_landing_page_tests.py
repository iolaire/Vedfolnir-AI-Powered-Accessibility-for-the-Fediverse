#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Landing Page Test Runner

Comprehensive test runner for Flask landing page accessibility and UI tests using Playwright.
Provides detailed reporting and can run specific test suites or all tests.

Usage:
    python run_landing_page_tests.py --all                    # Run all tests
    python run_landing_page_tests.py --accessibility          # Run accessibility tests only
    python run_landing_page_tests.py --ui                     # Run UI tests only
    python run_landing_page_tests.py --quick                  # Run quick subset of tests
    python run_landing_page_tests.py --report                 # Generate detailed report

Prerequisites:
    pip install playwright
    playwright install
"""

import unittest
import sys
import os
import argparse
import time
import json
from datetime import datetime
from io import StringIO

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import test modules
from tests.frontend.test_landing_page_accessibility import LandingPageAccessibilityTests
from tests.frontend.test_landing_page_ui import LandingPageUITests


class TestResult:
    """Custom test result class for detailed reporting"""
    
    def __init__(self):
        self.tests_run = 0
        self.failures = []
        self.errors = []
        self.skipped = []
        self.successes = []
        self.start_time = None
        self.end_time = None
    
    def start_test(self, test):
        """Called when a test starts"""
        if self.start_time is None:
            self.start_time = time.time()
        self.tests_run += 1
    
    def add_success(self, test):
        """Called when a test passes"""
        self.successes.append(test)
    
    def add_failure(self, test, err):
        """Called when a test fails"""
        self.failures.append((test, err))
    
    def add_error(self, test, err):
        """Called when a test has an error"""
        self.errors.append((test, err))
    
    def add_skip(self, test, reason):
        """Called when a test is skipped"""
        self.skipped.append((test, reason))
    
    def stop_test(self, test):
        """Called when a test ends"""
        self.end_time = time.time()
    
    def get_duration(self):
        """Get total test duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def was_successful(self):
        """Check if all tests passed"""
        return len(self.failures) == 0 and len(self.errors) == 0
    
    def get_summary(self):
        """Get test summary"""
        return {
            'total': self.tests_run,
            'passed': len(self.successes),
            'failed': len(self.failures),
            'errors': len(self.errors),
            'skipped': len(self.skipped),
            'duration': self.get_duration(),
            'success_rate': (len(self.successes) / self.tests_run * 100) if self.tests_run > 0 else 0
        }


class LandingPageTestRunner:
    """Main test runner for landing page tests"""
    
    def __init__(self):
        self.results = TestResult()
    
    def run_accessibility_tests(self, verbosity=2):
        """Run accessibility tests"""
        print("🔍 Running Accessibility Tests...")
        print("=" * 60)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(LandingPageAccessibilityTests)
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        result = runner.run(suite)
        
        self._update_results(result)
        return result.wasSuccessful()
    
    def run_ui_tests(self, verbosity=2):
        """Run UI tests"""
        print("🎨 Running UI Tests...")
        print("=" * 60)
        
        suite = unittest.TestLoader().loadTestsFromTestCase(LandingPageUITests)
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        result = runner.run(suite)
        
        self._update_results(result)
        return result.wasSuccessful()
    
    def run_quick_tests(self, verbosity=2):
        """Run a quick subset of critical tests"""
        print("⚡ Running Quick Test Suite...")
        print("=" * 60)
        
        # Create a custom test suite with critical tests
        suite = unittest.TestSuite()
        
        # Add critical accessibility tests
        suite.addTest(LandingPageAccessibilityTests('test_semantic_html_structure'))
        suite.addTest(LandingPageAccessibilityTests('test_keyboard_navigation_skip_link'))
        suite.addTest(LandingPageAccessibilityTests('test_heading_hierarchy'))
        
        # Add critical UI tests
        suite.addTest(LandingPageUITests('test_visual_layout_desktop'))
        suite.addTest(LandingPageUITests('test_visual_layout_mobile'))
        suite.addTest(LandingPageUITests('test_button_functionality_and_navigation'))
        
        runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
        result = runner.run(suite)
        
        self._update_results(result)
        return result.wasSuccessful()
    
    def run_all_tests(self, verbosity=2):
        """Run all tests"""
        print("🚀 Running All Landing Page Tests...")
        print("=" * 60)
        
        success = True
        
        # Run accessibility tests
        if not self.run_accessibility_tests(verbosity):
            success = False
        
        print("\n" + "=" * 60 + "\n")
        
        # Run UI tests
        if not self.run_ui_tests(verbosity):
            success = False
        
        return success
    
    def _update_results(self, unittest_result):
        """Update our custom results from unittest result"""
        self.results.tests_run += unittest_result.testsRun
        self.results.failures.extend(unittest_result.failures)
        self.results.errors.extend(unittest_result.errors)
        self.results.skipped.extend(unittest_result.skipped)
        
        # Calculate successes
        total_issues = len(unittest_result.failures) + len(unittest_result.errors) + len(unittest_result.skipped)
        successes = unittest_result.testsRun - total_issues
        self.results.successes.extend(['success'] * successes)
    
    def generate_report(self):
        """Generate detailed test report"""
        summary = self.results.get_summary()
        
        print("\n" + "=" * 80)
        print("📊 LANDING PAGE TEST REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {summary['duration']:.2f} seconds")
        print()
        
        # Summary statistics
        print("📈 SUMMARY STATISTICS")
        print("-" * 40)
        print(f"Total Tests:     {summary['total']}")
        print(f"Passed:          {summary['passed']} ✅")
        print(f"Failed:          {summary['failed']} ❌")
        print(f"Errors:          {summary['errors']} 💥")
        print(f"Skipped:         {summary['skipped']} ⏭️")
        print(f"Success Rate:    {summary['success_rate']:.1f}%")
        print()
        
        # Requirements coverage
        print("📋 REQUIREMENTS COVERAGE")
        print("-" * 40)
        requirements_tested = [
            "3.1 - Semantic HTML elements for screen reader navigation",
            "3.2 - Appropriate alt text for all images",
            "3.3 - Proper color contrast ratios for text readability",
            "3.4 - Fully navigable using keyboard-only input",
            "3.5 - Proper heading hierarchy for content structure",
            "3.6 - Skip-to-content links for screen reader users",
            "4.1 - Display content in readable format on mobile devices",
            "4.2 - Maintain proper layout and functionality on tablets",
            "4.3 - Utilize full screen width effectively on desktop",
            "6.4 - Visual feedback for interactive elements",
            "6.5 - Button functionality and navigation",
            "6.6 - Hover states and visual feedback"
        ]
        
        for req in requirements_tested:
            print(f"✅ {req}")
        print()
        
        # Test categories
        print("🏷️  TEST CATEGORIES")
        print("-" * 40)
        categories = {
            "Responsive Design": "Tests across mobile, tablet, and desktop screen sizes",
            "WCAG Compliance": "Automated and manual accessibility testing",
            "Keyboard Navigation": "Full keyboard accessibility testing",
            "Visual Feedback": "Hover effects and interactive element testing",
            "Screen Reader Support": "Semantic HTML and ARIA testing",
            "Cross-Browser": "Multi-browser compatibility testing",
            "Performance": "Page load and rendering performance"
        }
        
        for category, description in categories.items():
            print(f"📂 {category}: {description}")
        print()
        
        # Failure details
        if self.results.failures:
            print("❌ FAILURES")
            print("-" * 40)
            for i, (test, error) in enumerate(self.results.failures, 1):
                print(f"{i}. {test}")
                print(f"   Error: {error}")
                print()
        
        # Error details
        if self.results.errors:
            print("💥 ERRORS")
            print("-" * 40)
            for i, (test, error) in enumerate(self.results.errors, 1):
                print(f"{i}. {test}")
                print(f"   Error: {error}")
                print()
        
        # Skipped tests
        if self.results.skipped:
            print("⏭️  SKIPPED TESTS")
            print("-" * 40)
            for i, (test, reason) in enumerate(self.results.skipped, 1):
                print(f"{i}. {test}")
                print(f"   Reason: {reason}")
                print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS")
        print("-" * 40)
        
        if summary['success_rate'] == 100:
            print("🎉 Excellent! All tests passed.")
            print("   - Landing page meets all accessibility and UI requirements")
            print("   - Ready for production deployment")
        elif summary['success_rate'] >= 90:
            print("✅ Very good! Most tests passed.")
            print("   - Address any remaining failures before deployment")
            print("   - Consider running tests in different environments")
        elif summary['success_rate'] >= 75:
            print("⚠️  Good progress, but improvements needed.")
            print("   - Review and fix failing tests")
            print("   - Focus on accessibility and responsive design issues")
        else:
            print("🚨 Significant issues found.")
            print("   - Major accessibility or UI problems detected")
            print("   - Requires immediate attention before deployment")
        
        print()
        print("🔧 NEXT STEPS")
        print("-" * 40)
        print("1. Review any failures or errors above")
        print("2. Fix identified issues in the landing page implementation")
        print("3. Re-run tests to verify fixes")
        print("4. Consider running tests with different browsers/devices")
        print("5. Perform manual testing with actual screen readers")
        print()
        
        return summary['success_rate'] == 100


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Landing Page Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_landing_page_tests.py --all                    # Run all tests
  python run_landing_page_tests.py --accessibility          # Accessibility tests only
  python run_landing_page_tests.py --ui                     # UI tests only
  python run_landing_page_tests.py --quick                  # Quick test suite
  python run_landing_page_tests.py --report                 # Generate detailed report
        """
    )
    
    parser.add_argument('--all', action='store_true', 
                       help='Run all tests (accessibility + UI)')
    parser.add_argument('--accessibility', action='store_true',
                       help='Run accessibility tests only')
    parser.add_argument('--ui', action='store_true',
                       help='Run UI tests only')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test suite (critical tests only)')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed test report')
    parser.add_argument('--verbose', '-v', action='count', default=2,
                       help='Increase verbosity (use -v, -vv, or -vvv)')
    
    args = parser.parse_args()
    
    # If no specific test type specified, run all
    if not any([args.all, args.accessibility, args.ui, args.quick]):
        args.all = True
    
    runner = LandingPageTestRunner()
    success = True
    
    try:
        if args.quick:
            success = runner.run_quick_tests(args.verbose)
        elif args.accessibility:
            success = runner.run_accessibility_tests(args.verbose)
        elif args.ui:
            success = runner.run_ui_tests(args.verbose)
        elif args.all:
            success = runner.run_all_tests(args.verbose)
        
        # Always generate report if requested or if running all tests
        if args.report or args.all:
            runner.generate_report()
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        return 1
    
    # Return appropriate exit code
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())