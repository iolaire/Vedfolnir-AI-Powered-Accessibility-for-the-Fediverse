#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Tests Runner

Runs the security tests and generates a report of the results.
"""

import unittest
import sys
import os
import json
import time
from datetime import datetime, timezone
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def run_security_tests():
    """Run security tests and generate report"""
    
    # Import test modules
    from tests.security.test_notification_authentication_authorization import TestNotificationAuthenticationAuthorization
    from tests.security.test_notification_security_validation import (
        TestNotificationInputValidation, TestNotificationXSSPrevention, 
        TestNotificationRateLimiting, TestNotificationSecurityIntegration
    )
    from tests.security.test_notification_abuse_detection import TestNotificationAbuseDetection
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestNotificationAuthenticationAuthorization,
        TestNotificationInputValidation,
        TestNotificationXSSPrevention,
        TestNotificationRateLimiting,
        TestNotificationSecurityIntegration,
        TestNotificationAbuseDetection
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with custom result collector
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    
    start_time = time.time()
    result = runner.run(test_suite)
    end_time = time.time()
    
    # Generate report
    report = {
        "summary": {
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "total_tests": result.testsRun,
            "passed_tests": result.testsRun - len(result.failures) - len(result.errors),
            "failed_tests": len(result.failures),
            "error_tests": len(result.errors),
            "skipped_tests": len(result.skipped) if hasattr(result, 'skipped') else 0,
            "success_rate": ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
        },
        "test_results": {},
        "failures": [],
        "errors": []
    }
    
    # Add failure details
    for test, traceback in result.failures:
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        report["test_results"][test_name] = {
            "status": "FAIL",
            "error_message": traceback,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report["failures"].append({"test": test_name, "traceback": traceback})
    
    # Add error details
    for test, traceback in result.errors:
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        report["test_results"][test_name] = {
            "status": "ERROR", 
            "error_message": traceback,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report["errors"].append({"test": test_name, "traceback": traceback})
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"tests/security/reports/notification_security_test_report_{timestamp}.json"
    
    # Ensure reports directory exists
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n=== Security Test Results ===")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed_tests']}")
    print(f"Failed: {report['summary']['failed_tests']}")
    print(f"Errors: {report['summary']['error_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Duration: {report['summary']['duration']:.2f}s")
    print(f"Report saved to: {report_file}")
    
    if result.failures:
        print(f"\n=== Failures ({len(result.failures)}) ===")
        for test, traceback in result.failures:
            print(f"FAIL: {test}")
            print(f"  {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See full traceback in report'}")
    
    if result.errors:
        print(f"\n=== Errors ({len(result.errors)}) ===")
        for test, traceback in result.errors:
            print(f"ERROR: {test}")
            print(f"  {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'See full traceback in report'}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_security_tests()
    sys.exit(0 if success else 1)