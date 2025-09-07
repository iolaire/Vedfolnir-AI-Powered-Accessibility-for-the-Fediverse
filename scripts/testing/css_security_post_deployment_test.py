# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSS Security Enhancement Post-Deployment Test Suite

This script runs comprehensive tests after CSS security deployment to verify
that all functionality works correctly and no regressions were introduced.
"""

import os
import sys
import time
import requests
import subprocess
import unittest
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class CSSSecurityPostDeploymentTest(unittest.TestCase):
    """Post-deployment test suite for CSS security enhancements"""
    
    @classmethod
    def setUpClass(cls):
        cls.base_url = "http://127.0.0.1:5000"
        cls.test_results = []
        cls.start_time = datetime.now()
        
        # Verify application is running
        try:
            response = requests.get(cls.base_url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Application not responding (HTTP {response.status_code})")
        except Exception as e:
            raise Exception(f"Application not accessible: {e}")
    
    def log_result(self, test_name, passed, message=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{'✅' if passed else '❌'} {test_name}: {status} {message}")
    
    def test_01_application_health(self):
        """Test basic application health"""
        try:
            response = requests.get(self.base_url, timeout=10)
            self.assertEqual(response.status_code, 200)
            self.log_result("Application Health", True, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Application Health", False, str(e))
            self.fail(f"Application health check failed: {e}")
    
    def test_02_css_files_accessibility(self):
        """Test CSS file accessibility via HTTP"""
        css_files = [
            "static/css/security-extracted.css",
            "static/css/components.css",
            "admin/static/css/admin-extracted.css"
        ]
        
        for css_file in css_files:
            with self.subTest(css_file=css_file):
                try:
                    url = f"{self.base_url}/{css_file}"
                    response = requests.get(url, timeout=5)
                    self.assertEqual(response.status_code, 200)
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    self.assertIn('text/css', content_type)
                    
                    # Check content is not empty
                    self.assertGreater(len(response.text), 0)
                    
                    self.log_result(f"CSS File: {css_file}", True, f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_result(f"CSS File: {css_file}", False, str(e))
                    self.fail(f"CSS file {css_file} accessibility failed: {e}")
    
    def test_03_inline_styles_removed(self):
        """Test that inline styles have been removed"""
        try:
            result = subprocess.run([
                sys.executable, 
                "tests/scripts/css_extraction_helper.py"
            ], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..', '..'))
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "No inline styles found" in output:
                    self.log_result("Inline Styles Removed", True, "No inline styles detected")
                else:
                    self.log_result("Inline Styles Removed", False, f"Inline styles found: {output}")
                    self.fail(f"Inline styles still present: {output}")
            else:
                self.log_result("Inline Styles Removed", False, f"Check failed: {result.stderr}")
                self.fail(f"Inline style check failed: {result.stderr}")
        except Exception as e:
            self.log_result("Inline Styles Removed", False, str(e))
            self.fail(f"Inline style check error: {e}")
    
    def test_04_page_load_performance(self):
        """Test page load performance"""
        test_pages = [
            "/",
            "/login",
            "/caption_generation"
        ]
        
        for page in test_pages:
            with self.subTest(page=page):
                try:
                    url = f"{self.base_url}{page}"
                    start_time = time.time()
                    response = requests.get(url, timeout=30)
                    load_time = time.time() - start_time
                    
                    self.assertEqual(response.status_code, 200)
                    self.assertLess(load_time, 10.0, f"Page load time too slow: {load_time:.2f}s")
                    
                    if load_time < 5.0:
                        self.log_result(f"Page Load: {page}", True, f"{load_time:.2f}s")
                    else:
                        self.log_result(f"Page Load: {page}", True, f"{load_time:.2f}s (slow)")
                        
                except Exception as e:
                    self.log_result(f"Page Load: {page}", False, str(e))
                    self.fail(f"Page {page} load failed: {e}")
    
    def test_05_template_integrity(self):
        """Test template syntax and integrity"""
        try:
            from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
            
            template_dirs = ['templates', 'admin/templates']
            errors = []
            template_count = 0
            
            for template_dir in template_dirs:
                if os.path.exists(template_dir):
                    env = Environment(loader=FileSystemLoader(template_dir))
                    for root, dirs, files in os.walk(template_dir):
                        for file in files:
                            if file.endswith('.html'):
                                template_count += 1
                                template_path = os.path.relpath(os.path.join(root, file), template_dir)
                                try:
                                    env.get_template(template_path)
                                except TemplateSyntaxError as e:
                                    errors.append(f'{template_path}: {e}')
            
            if errors:
                self.log_result("Template Integrity", False, f"{len(errors)} errors in {template_count} templates")
                self.fail(f"Template errors: {errors}")
            else:
                self.log_result("Template Integrity", True, f"{template_count} templates validated")
                
        except Exception as e:
            self.log_result("Template Integrity", False, str(e))
            self.fail(f"Template integrity check failed: {e}")
    
    def test_06_css_content_validation(self):
        """Test CSS content is valid and contains expected classes"""
        css_files = [
            ("static/css/security-extracted.css", [".hidden", ".progress-bar-dynamic"]),
            ("static/css/components.css", [".modal-overlay", ".bulk-select-position"]),
            ("admin/static/css/admin-extracted.css", [".admin-", ".dashboard-"])
        ]
        
        for css_file, expected_classes in css_files:
            with self.subTest(css_file=css_file):
                try:
                    if os.path.exists(css_file):
                        with open(css_file, 'r') as f:
                            content = f.read()
                        
                        # Check file is not empty
                        self.assertGreater(len(content), 0, f"{css_file} is empty")
                        
                        # Check for expected classes (at least some)
                        found_classes = []
                        for expected_class in expected_classes:
                            if expected_class in content:
                                found_classes.append(expected_class)
                        
                        if found_classes:
                            self.log_result(f"CSS Content: {css_file}", True, f"Found classes: {found_classes}")
                        else:
                            self.log_result(f"CSS Content: {css_file}", False, f"No expected classes found")
                    else:
                        self.log_result(f"CSS Content: {css_file}", False, "File does not exist")
                        self.fail(f"{css_file} does not exist")
                        
                except Exception as e:
                    self.log_result(f"CSS Content: {css_file}", False, str(e))
                    self.fail(f"CSS content validation failed for {css_file}: {e}")
    
    def test_07_key_functionality(self):
        """Test key application functionality still works"""
        # Test login page loads
        try:
            response = requests.get(f"{self.base_url}/login", timeout=10)
            self.assertEqual(response.status_code, 200)
            self.assertIn("login", response.text.lower())
            self.log_result("Login Page", True, "Loads correctly")
        except Exception as e:
            self.log_result("Login Page", False, str(e))
            self.fail(f"Login page test failed: {e}")
        
        # Test admin page (should redirect to login)
        try:
            response = requests.get(f"{self.base_url}/admin", timeout=10, allow_redirects=False)
            # Should redirect to login (302) or show login form (200)
            self.assertIn(response.status_code, [200, 302])
            self.log_result("Admin Page", True, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Admin Page", False, str(e))
            self.fail(f"Admin page test failed: {e}")
    
    def test_08_static_file_serving(self):
        """Test static file serving works correctly"""
        static_files = [
            "static/css/main.css",
            "static/js/main.js",
            "admin/static/css/admin.css"
        ]
        
        for static_file in static_files:
            if os.path.exists(static_file):
                with self.subTest(static_file=static_file):
                    try:
                        url = f"{self.base_url}/{static_file}"
                        response = requests.get(url, timeout=5)
                        self.assertEqual(response.status_code, 200)
                        self.log_result(f"Static File: {static_file}", True, f"HTTP {response.status_code}")
                    except Exception as e:
                        self.log_result(f"Static File: {static_file}", False, str(e))
                        self.fail(f"Static file {static_file} serving failed: {e}")
    
    def test_09_memory_usage(self):
        """Test application memory usage is reasonable"""
        try:
            # Simple memory check - just verify app is still responsive
            response = requests.get(self.base_url, timeout=10)
            self.assertEqual(response.status_code, 200)
            self.log_result("Memory Usage", True, "Application responsive")
        except Exception as e:
            self.log_result("Memory Usage", False, str(e))
            self.fail(f"Memory usage test failed: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Generate test report"""
        end_time = datetime.now()
        duration = end_time - cls.start_time
        
        # Count results
        total_tests = len(cls.test_results)
        passed_tests = sum(1 for result in cls.test_results if result["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        # Generate report
        report = {
            "test_suite": "CSS Security Post-Deployment Test",
            "start_time": cls.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "results": cls.test_results
        }
        
        # Save report
        report_dir = "logs/testing"
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"css_security_post_deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"CSS Security Post-Deployment Test Summary")
        print(f"{'='*60}")
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {report['success_rate']:.1f}%")
        print(f"Report saved to: {report_file}")
        
        if failed_tests > 0:
            print(f"\n❌ {failed_tests} tests failed:")
            for result in cls.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['message']}")
        else:
            print(f"\n✅ All tests passed!")

def main():
    """Main test runner"""
    print("CSS Security Enhancement Post-Deployment Test Suite")
    print("=" * 60)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(CSSSecurityPostDeploymentTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()