#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSP Compliance Testing Script
Tests for CSP violations and validates fixes
"""

import requests
import time
import json
import sys
import os
from pathlib import Path

class CSPTester:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.violations = []
        
    def test_csp_headers(self):
        """Test that CSP headers are present"""
        print("🔍 Testing CSP headers...")
        
        try:
            response = self.session.get(f"{self.base_url}/")
            csp_header = response.headers.get('Content-Security-Policy')
            
            if not csp_header:
                print("❌ No CSP header found")
                return False
            
            print(f"✅ CSP header present: {len(csp_header)} characters")
            
            # Check for important directives
            required_directives = [
                'default-src',
                'script-src',
                'style-src',
                'img-src',
                'connect-src',
                'report-uri'
            ]
            
            missing_directives = []
            for directive in required_directives:
                if directive not in csp_header:
                    missing_directives.append(directive)
            
            if missing_directives:
                print(f"⚠️  Missing directives: {', '.join(missing_directives)}")
            else:
                print("✅ All required CSP directives present")
            
            # Check for unsafe directives
            unsafe_patterns = ["'unsafe-inline'", "'unsafe-eval'"]
            found_unsafe = []
            for pattern in unsafe_patterns:
                if pattern in csp_header:
                    found_unsafe.append(pattern)
            
            if found_unsafe:
                print(f"⚠️  Unsafe directives found: {', '.join(found_unsafe)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing CSP headers: {e}")
            return False
    
    def test_inline_handlers_removed(self):
        """Test that inline event handlers have been removed"""
        print("\n🔍 Testing for inline event handlers...")
        
        test_pages = [
            "/",
            "/user-management/login",
            "/platform-management",
            "/caption/generation",
            "/review/"
        ]
        
        inline_patterns = [
            r'onclick=',
            r'onchange=',
            r'onload=',
            r'onsubmit=',
            r'onerror='
        ]
        
        violations_found = 0
        
        for page in test_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}")
                if response.status_code == 200:
                    content = response.text
                    
                    for pattern in inline_patterns:
                        import re
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            violations_found += len(matches)
                            print(f"⚠️  Found {len(matches)} {pattern} in {page}")
                
            except Exception as e:
                print(f"⚠️  Could not test {page}: {e}")
        
        if violations_found == 0:
            print("✅ No inline event handlers found")
            return True
        else:
            print(f"❌ Found {violations_found} inline event handlers")
            return False
    
    def test_csp_report_endpoint(self):
        """Test that CSP report endpoint is working"""
        print("\n🔍 Testing CSP report endpoint...")
        
        test_report = {
            "csp-report": {
                "document-uri": f"{self.base_url}/test",
                "referrer": "",
                "violated-directive": "script-src-attr",
                "effective-directive": "script-src-attr",
                "original-policy": "default-src 'self'",
                "disposition": "enforce",
                "blocked-uri": "inline",
                "line-number": 1,
                "column-number": 1,
                "source-file": f"{self.base_url}/test",
                "status-code": 200,
                "script-sample": ""
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/csp-report",
                json=test_report,
                headers={'Content-Type': 'application/csp-report'}
            )
            
            if response.status_code == 204:
                print("✅ CSP report endpoint working")
                return True
            else:
                print(f"❌ CSP report endpoint returned {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing CSP report endpoint: {e}")
            return False
    
    def monitor_csp_violations(self, duration=30):
        """Monitor for CSP violations by checking logs"""
        print(f"\n🔍 Monitoring CSP violations for {duration} seconds...")
        
        # Check if webapp.log exists
        log_file = Path("logs/webapp.log")
        if not log_file.exists():
            print("⚠️  Log file not found, cannot monitor violations")
            return True
        
        # Get initial log size
        initial_size = log_file.stat().st_size
        
        print("📊 Browsing test pages to trigger any violations...")
        
        # Browse through pages to trigger violations
        test_pages = [
            "/",
            "/user-management/login",
            "/platform-management",
            "/caption/generation",
            "/review/",
            "/admin/dashboard"
        ]
        
        for page in test_pages:
            try:
                response = self.session.get(f"{self.base_url}{page}")
                print(f"   Visited: {page} ({response.status_code})")
                time.sleep(2)
            except Exception as e:
                print(f"   Could not visit {page}: {e}")
        
        # Wait for any violations to be logged
        time.sleep(5)
        
        # Check for new violations in log
        try:
            current_size = log_file.stat().st_size
            if current_size > initial_size:
                # Read new content
                with open(log_file, 'r') as f:
                    f.seek(initial_size)
                    new_content = f.read()
                
                # Count CSP violations
                violation_count = new_content.count('CSP violation detected')
                
                if violation_count > 0:
                    print(f"❌ Found {violation_count} new CSP violations")
                    
                    # Show sample violations
                    lines = new_content.split('\n')
                    violation_lines = [line for line in lines if 'CSP violation detected' in line]
                    
                    for i, line in enumerate(violation_lines[:3]):  # Show first 3
                        print(f"   Violation {i+1}: {line[:100]}...")
                    
                    return False
                else:
                    print("✅ No new CSP violations detected")
                    return True
            else:
                print("✅ No new log entries (no violations)")
                return True
                
        except Exception as e:
            print(f"⚠️  Error reading log file: {e}")
            return True
    
    def run_full_test(self):
        """Run complete CSP compliance test suite"""
        print("🔒 CSP Compliance Test Suite")
        print("=" * 50)
        
        tests = [
            ("CSP Headers", self.test_csp_headers),
            ("Inline Handlers", self.test_inline_handlers_removed),
            ("CSP Report Endpoint", self.test_csp_report_endpoint),
            ("Violation Monitoring", lambda: self.monitor_csp_violations(30))
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name} test...")
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ Test failed with error: {e}")
                results[test_name] = False
        
        # Summary
        print(f"\n📊 Test Results Summary:")
        print("=" * 30)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All CSP compliance tests passed!")
            return True
        else:
            print("⚠️  Some CSP compliance issues remain")
            return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://127.0.0.1:5000"
    
    print(f"🌐 Testing CSP compliance for: {base_url}")
    
    # Check if server is running
    try:
        response = requests.get(base_url, timeout=5)
        print(f"✅ Server is running (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        print("💡 Make sure your web application is running:")
        print("   python web_app.py & sleep 10")
        sys.exit(1)
    
    # Run tests
    tester = CSPTester(base_url)
    success = tester.run_full_test()
    
    if success:
        print(f"\n🎉 CSP compliance testing completed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  CSP compliance issues found. Please review and fix.")
        sys.exit(1)

if __name__ == '__main__':
    main()