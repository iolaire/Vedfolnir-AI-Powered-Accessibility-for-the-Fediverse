#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Final Integration Validation Script

This script performs comprehensive validation of the notification system migration
by running all critical tests and generating a final validation report.
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def run_test_suite(test_module: str, test_name: str) -> Dict[str, Any]:
    """Run a specific test suite and return results"""
    print(f"\n🧪 Running {test_name}...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'unittest', test_module, '-v'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        success = result.returncode == 0
        
        if success:
            print(f"✅ {test_name} PASSED ({duration:.2f}s)")
        else:
            print(f"❌ {test_name} FAILED ({duration:.2f}s)")
            if result.stderr:
                print(f"Error output: {result.stderr[:500]}...")
        
        return {
            'name': test_name,
            'module': test_module,
            'success': success,
            'duration': duration,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name} TIMED OUT")
        return {
            'name': test_name,
            'module': test_module,
            'success': False,
            'duration': 120,
            'error': 'Timeout after 2 minutes'
        }
    except Exception as e:
        print(f"💥 {test_name} ERROR: {e}")
        return {
            'name': test_name,
            'module': test_module,
            'success': False,
            'duration': 0,
            'error': str(e)
        }


def main():
    """Main validation execution"""
    print("🎯 NOTIFICATION SYSTEM FINAL INTEGRATION VALIDATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test suites to run
    test_suites = [
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_end_to_end_user_dashboard_notifications',
            'name': 'End-to-End User Dashboard Notifications'
        },
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_end_to_end_admin_dashboard_notifications',
            'name': 'End-to-End Admin Dashboard Notifications'
        },
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_websocket_connection_establishment_maintenance',
            'name': 'WebSocket Connection Establishment and Maintenance'
        },
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_notification_delivery_consistency_across_interfaces',
            'name': 'Notification Delivery Consistency'
        },
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_error_recovery_and_fallback_mechanisms',
            'name': 'Error Recovery and Fallback Mechanisms'
        },
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_security_and_penetration_testing',
            'name': 'Security and Penetration Testing'
        },
        {
            'module': 'tests.integration.test_notification_system_final_integration.TestNotificationSystemFinalIntegration.test_performance_under_load',
            'name': 'Performance Under Load'
        },
        {
            'module': 'tests.security.test_notification_security_penetration.TestNotificationSecurityPenetration.test_privilege_escalation_attempts',
            'name': 'Privilege Escalation Security Tests'
        },
        {
            'module': 'tests.security.test_notification_security_penetration.TestNotificationSecurityPenetration.test_injection_attacks',
            'name': 'Injection Attack Security Tests'
        }
    ]
    
    # Run all test suites
    results = []
    total_duration = 0
    
    for test_suite in test_suites:
        result = run_test_suite(test_suite['module'], test_suite['name'])
        results.append(result)
        total_duration += result.get('duration', 0)
    
    # Generate summary
    print("\n" + "=" * 80)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 80)
    
    passed_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Success Rate: {len(passed_tests)/len(results)*100:.1f}%")
    
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  - {test['name']}")
            if 'error' in test:
                print(f"    Error: {test['error']}")
    
    # Overall result
    overall_success = len(failed_tests) == 0
    
    if overall_success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ Notification system migration is VALIDATED for production deployment")
        print("\n📋 VALIDATION CHECKLIST:")
        print("✅ End-to-end notification delivery working")
        print("✅ WebSocket connections established and maintained")
        print("✅ Cross-interface notification consistency verified")
        print("✅ Error recovery and fallback mechanisms functional")
        print("✅ Security measures validated against penetration attempts")
        print("✅ Performance under load acceptable")
        print("✅ All security vulnerabilities blocked")
    else:
        print(f"\n❌ VALIDATION FAILED")
        print("⚠️  Some critical tests failed - review required before deployment")
    
    # Save detailed report
    report = {
        'timestamp': datetime.now().isoformat(),
        'overall_success': overall_success,
        'summary': {
            'total_tests': len(results),
            'passed_tests': len(passed_tests),
            'failed_tests': len(failed_tests),
            'success_rate': len(passed_tests)/len(results)*100,
            'total_duration': total_duration
        },
        'test_results': results
    }
    
    report_path = os.path.join(
        os.path.dirname(__file__), '..', 'reports',
        f'final_validation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_path}")
    print("=" * 80)
    
    return overall_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)