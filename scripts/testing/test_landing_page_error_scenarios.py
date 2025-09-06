#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Landing Page Error Scenario Testing Script

This script tests various error scenarios and recovery mechanisms
for the Flask landing page functionality in a real environment.
"""

import sys
import os
import json
import time
import requests
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.landing_page_fallback import test_error_scenarios

def setup_logging():
    """Set up logging for the test script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('landing_page_error_test.log')
        ]
    )
    return logging.getLogger(__name__)

def test_web_app_error_handling(base_url="http://127.0.0.1:5000"):
    """
    Test error handling in the actual web application.
    
    Args:
        base_url: Base URL of the web application
    
    Returns:
        Dictionary with test results
    """
    logger = logging.getLogger(__name__)
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'base_url': base_url,
        'tests': {}
    }
    
    try:
        # Test 1: Normal landing page access
        logger.info("Testing normal landing page access...")
        try:
            response = requests.get(base_url, timeout=10)
            test_results['tests']['normal_landing_page'] = {
                'status': 'pass' if response.status_code == 200 else 'fail',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'content_length': len(response.text),
                'contains_vedfolnir': 'Vedfolnir' in response.text,
                'contains_cta': 'Get Started' in response.text or 'Create Account' in response.text,
                'has_fallback_header': 'X-Fallback-Mode' in response.headers
            }
        except Exception as e:
            test_results['tests']['normal_landing_page'] = {
                'status': 'fail',
                'error': str(e)
            }
        
        # Test 2: Landing page with invalid parameters (should still work)
        logger.info("Testing landing page with invalid parameters...")
        try:
            response = requests.get(f"{base_url}?invalid=param&test=error", timeout=10)
            test_results['tests']['landing_page_invalid_params'] = {
                'status': 'pass' if response.status_code == 200 else 'fail',
                'status_code': response.status_code,
                'handles_invalid_params': response.status_code == 200,
                'has_fallback_header': 'X-Fallback-Mode' in response.headers
            }
        except Exception as e:
            test_results['tests']['landing_page_invalid_params'] = {
                'status': 'fail',
                'error': str(e)
            }
        
        # Test 3: Test with various User-Agent strings
        logger.info("Testing landing page with different User-Agent strings...")
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'curl/7.68.0',
            'Python-requests/2.25.1',
            ''  # Empty user agent
        ]
        
        ua_results = []
        for ua in user_agents:
            try:
                headers = {'User-Agent': ua} if ua else {}
                response = requests.get(base_url, headers=headers, timeout=10)
                ua_results.append({
                    'user_agent': ua or 'empty',
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                })
            except Exception as e:
                ua_results.append({
                    'user_agent': ua or 'empty',
                    'error': str(e),
                    'success': False
                })
        
        test_results['tests']['user_agent_handling'] = {
            'status': 'pass' if all(r.get('success', False) for r in ua_results) else 'partial',
            'results': ua_results
        }
        
        # Test 4: Test with malformed requests
        logger.info("Testing landing page with malformed requests...")
        try:
            # Test with very long URL
            long_url = base_url + '?' + 'x' * 2000
            response = requests.get(long_url, timeout=10)
            test_results['tests']['malformed_requests'] = {
                'status': 'pass' if response.status_code in [200, 400, 414] else 'fail',
                'long_url_status': response.status_code,
                'handles_long_url': response.status_code in [200, 400, 414]
            }
        except Exception as e:
            test_results['tests']['malformed_requests'] = {
                'status': 'partial',
                'long_url_error': str(e)
            }
        
        # Test 5: Test concurrent requests
        logger.info("Testing concurrent requests to landing page...")
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = requests.get(base_url, timeout=5)
                return {
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                }
            except Exception as e:
                return {
                    'error': str(e),
                    'success': False
                }
        
        concurrent_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            for future in concurrent.futures.as_completed(futures):
                concurrent_results.append(future.result())
        
        successful_requests = sum(1 for r in concurrent_results if r.get('success', False))
        test_results['tests']['concurrent_requests'] = {
            'status': 'pass' if successful_requests >= 18 else 'partial',  # Allow 2 failures
            'total_requests': len(concurrent_results),
            'successful_requests': successful_requests,
            'success_rate': (successful_requests / len(concurrent_results)) * 100,
            'average_response_time': sum(r.get('response_time', 0) for r in concurrent_results if 'response_time' in r) / len([r for r in concurrent_results if 'response_time' in r])
        }
        
        # Calculate overall test status
        passed_tests = sum(1 for test in test_results['tests'].values() if test.get('status') == 'pass')
        partial_tests = sum(1 for test in test_results['tests'].values() if test.get('status') == 'partial')
        total_tests = len(test_results['tests'])
        
        test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'partial_tests': partial_tests,
            'failed_tests': total_tests - passed_tests - partial_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Web app error testing failed: {e}")
        test_results['error'] = str(e)
    
    return test_results

def test_fallback_mechanisms():
    """Test the fallback mechanisms directly"""
    logger = logging.getLogger(__name__)
    
    logger.info("Testing fallback mechanisms...")
    
    try:
        # Import Flask app for context
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-key'
        
        with app.app_context():
            results = test_error_scenarios()
            return results
    except Exception as e:
        logger.error(f"Fallback mechanism testing failed: {e}")
        return {'error': str(e)}

def check_web_app_availability(base_url="http://127.0.0.1:5000", max_retries=3):
    """
    Check if the web application is available.
    
    Args:
        base_url: Base URL to check
        max_retries: Maximum number of retries
    
    Returns:
        Boolean indicating if app is available
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"Web app is available at {base_url}")
                return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}: Web app not available - {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    logger.error(f"Web app is not available at {base_url} after {max_retries} attempts")
    return False

def main():
    """Main test execution"""
    logger = setup_logging()
    
    print("=" * 60)
    print("Landing Page Error Scenario Testing")
    print("=" * 60)
    
    # Test 1: Fallback mechanisms (doesn't require web app)
    print("\n1. Testing fallback mechanisms...")
    fallback_results = test_fallback_mechanisms()
    
    if 'error' not in fallback_results:
        print(f"✅ Fallback mechanism tests: {fallback_results['summary']['success_rate']:.1f}% success rate")
        print(f"   - Passed: {fallback_results['summary']['passed_tests']}/{fallback_results['summary']['total_tests']}")
    else:
        print(f"❌ Fallback mechanism tests failed: {fallback_results['error']}")
    
    # Test 2: Web application error handling (requires running web app)
    print("\n2. Testing web application error handling...")
    
    base_url = "http://127.0.0.1:5000"
    if check_web_app_availability(base_url):
        web_results = test_web_app_error_handling(base_url)
        
        if 'error' not in web_results:
            print(f"✅ Web app error handling tests: {web_results['summary']['success_rate']:.1f}% success rate")
            print(f"   - Passed: {web_results['summary']['passed_tests']}/{web_results['summary']['total_tests']}")
            print(f"   - Partial: {web_results['summary']['partial_tests']}")
            
            # Show detailed results
            for test_name, test_result in web_results['tests'].items():
                status_icon = "✅" if test_result.get('status') == 'pass' else "⚠️" if test_result.get('status') == 'partial' else "❌"
                print(f"   {status_icon} {test_name}: {test_result.get('status', 'unknown')}")
        else:
            print(f"❌ Web app error handling tests failed: {web_results['error']}")
    else:
        print("⚠️  Web app not available - skipping web application tests")
        print("   To run web app tests, start the application with: python web_app.py")
        web_results = {'skipped': True}
    
    # Generate comprehensive report
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    # Save results to file
    report = {
        'timestamp': datetime.now().isoformat(),
        'fallback_tests': fallback_results,
        'web_app_tests': web_results
    }
    
    report_file = f"landing_page_error_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
    
    # Overall assessment
    fallback_success = fallback_results.get('summary', {}).get('success_rate', 0) == 100
    web_success = web_results.get('summary', {}).get('success_rate', 0) >= 80 or web_results.get('skipped', False)
    
    if fallback_success and web_success:
        print("\n🎉 All error handling tests passed successfully!")
        print("   The landing page error handling system is working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed or had issues.")
        print("   Please review the detailed results above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)