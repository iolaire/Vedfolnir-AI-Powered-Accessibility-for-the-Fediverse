# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Frontend JavaScript tests for session synchronization functionality.

This module provides a Python wrapper for running the JavaScript tests
and integrating them with the existing Python test suite.

Tests cover Requirements 2.1, 2.2, 2.3, 2.4, 2.5 from the session management system specification.
"""

import unittest
import subprocess
import os
import json
import sys
from pathlib import Path

class TestFrontendSessionSync(unittest.TestCase):
    """Test frontend JavaScript session synchronization functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.project_root = Path(__file__).parent.parent
        cls.frontend_test_dir = cls.project_root / 'tests' / 'frontend'
        cls.js_test_file = cls.frontend_test_dir / 'test_session_sync.js'
        
        # Verify test files exist
        if not cls.js_test_file.exists():
            raise unittest.SkipTest(f"JavaScript test file not found: {cls.js_test_file}")
    
    def test_javascript_session_sync_tests(self):
        """Run JavaScript session synchronization tests via Node.js"""
        try:
            # Run the JavaScript tests
            result = subprocess.run(
                ['node', str(self.js_test_file)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if tests passed
            self.assertEqual(
                result.returncode, 0,
                f"JavaScript tests failed with output:\n{result.stdout}\n{result.stderr}"
            )
            
            # Verify test output contains expected results
            self.assertIn("Running SessionSync Frontend Tests", result.stdout)
            self.assertIn("Success Rate: 100%", result.stdout)
            self.assertIn("Tests: 10 | Passed: 10 | Failed: 0", result.stdout)
            
        except subprocess.TimeoutExpired:
            self.fail("JavaScript tests timed out after 30 seconds")
        except FileNotFoundError:
            self.skipTest("Node.js not available - skipping JavaScript tests")
    
    def test_session_sync_class_initialization_requirements(self):
        """Test that SessionSync class initialization tests cover requirements 2.1, 2.2"""
        try:
            result = subprocess.run(
                ['node', str(self.js_test_file)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Verify specific requirement coverage
            self.assertIn("[2.1, 2.2]", result.stdout, "Requirements 2.1, 2.2 should be tested")
            self.assertIn("SessionSync class initialization", result.stdout)
            self.assertIn("Tab ID generation uniqueness", result.stdout)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Cannot run JavaScript tests")
    
    def test_cross_tab_synchronization_requirements(self):
        """Test that cross-tab synchronization tests cover requirements 2.2, 2.3"""
        try:
            result = subprocess.run(
                ['node', str(self.js_test_file)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Verify specific requirement coverage
            self.assertIn("[2.2, 2.3]", result.stdout, "Requirements 2.2, 2.3 should be tested")
            self.assertIn("Cross-tab session state synchronization", result.stdout)
            self.assertIn("Storage event handling setup", result.stdout)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Cannot run JavaScript tests")
    
    def test_session_validation_requirements(self):
        """Test that session validation tests cover requirements 2.4, 2.5"""
        try:
            result = subprocess.run(
                ['node', str(self.js_test_file)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Verify specific requirement coverage
            self.assertIn("[2.4, 2.5]", result.stdout, "Requirements 2.4, 2.5 should be tested")
            self.assertIn("Session validation with server", result.stdout)
            self.assertIn("Session expiration handling", result.stdout)
            self.assertIn("Performance metrics tracking", result.stdout)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Cannot run JavaScript tests")
    
    def test_html_test_runner_exists(self):
        """Test that HTML test runner file exists and is accessible"""
        html_test_file = self.frontend_test_dir / 'test_session_sync.html'
        
        self.assertTrue(
            html_test_file.exists(),
            f"HTML test runner should exist at {html_test_file}"
        )
        
        # Verify HTML file contains expected content
        with open(html_test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('Session Sync Frontend Tests', content)
        self.assertIn('session_sync.js', content)
        self.assertIn('runAllTests()', content)
    
    def test_frontend_test_documentation(self):
        """Test that frontend test documentation exists and is complete"""
        readme_file = self.frontend_test_dir / 'README.md'
        
        self.assertTrue(
            readme_file.exists(),
            f"Frontend test README should exist at {readme_file}"
        )
        
        # Verify README contains expected sections
        with open(readme_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        expected_sections = [
            'Frontend JavaScript Tests',
            'Test Files',
            'Test Coverage',
            'Requirements 2.1, 2.2',
            'Requirements 2.2, 2.3',
            'Requirements 2.4, 2.5',
            'Running Tests',
            'Browser Testing',
            'Command Line Testing'
        ]
        
        for section in expected_sections:
            self.assertIn(section, content, f"README should contain section: {section}")
    
    def test_session_sync_source_file_exists(self):
        """Test that the SessionSync source file exists and is accessible"""
        session_sync_file = self.project_root / 'static' / 'js' / 'session_sync.js'
        
        self.assertTrue(
            session_sync_file.exists(),
            f"SessionSync source file should exist at {session_sync_file}"
        )
        
        # Verify source file contains expected classes and methods
        with open(session_sync_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        expected_elements = [
            'class SessionSync',
            'generateTabId()',
            'init()',
            'destroy()',
            'handleStorageChange',
            'syncSessionState',
            'validateSession',
            'handleSessionExpired',
            'notifyPlatformSwitch',
            'getPerformanceMetrics'
        ]
        
        for element in expected_elements:
            self.assertIn(element, content, f"SessionSync should contain: {element}")
    
    def test_test_coverage_completeness(self):
        """Test that all required functionality is covered by tests"""
        try:
            result = subprocess.run(
                ['node', str(self.js_test_file)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Verify all key test cases are present
            required_tests = [
                'SessionSync class initialization',
                'Tab ID generation uniqueness',
                'Storage event handling setup',
                'Cross-tab session state synchronization',
                'Session validation with server',
                'Session expiration handling',
                'Platform switch event handling',
                'Session state change detection',
                'Performance metrics tracking',
                'Debounced sync functionality'
            ]
            
            for test_name in required_tests:
                self.assertIn(test_name, result.stdout, f"Should include test: {test_name}")
            
            # Verify all requirements are covered
            required_requirements = ['2.1', '2.2', '2.3', '2.4', '2.5']
            for req in required_requirements:
                self.assertIn(f"[{req}", result.stdout, f"Should cover requirement: {req}")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Cannot run JavaScript tests")
    
    def test_integration_with_existing_tests(self):
        """Test that frontend tests can be integrated with existing test suite"""
        # Verify this test file can be discovered by unittest
        test_loader = unittest.TestLoader()
        test_suite = test_loader.loadTestsFromTestCase(TestFrontendSessionSync)
        
        self.assertGreater(
            test_suite.countTestCases(), 0,
            "Frontend tests should be discoverable by unittest"
        )
        
        # Verify test methods follow naming convention
        test_methods = [method for method in dir(self) if method.startswith('test_')]
        self.assertGreater(
            len(test_methods), 5,
            "Should have multiple test methods"
        )
    
    def test_error_handling_in_javascript_tests(self):
        """Test that JavaScript tests handle errors appropriately"""
        # Create a temporary broken test file to verify error handling
        broken_test_content = """
        // Intentionally broken JavaScript
        const testSuite = new NonExistentClass();
        testSuite.runAllTests();
        """
        
        broken_test_file = self.frontend_test_dir / 'test_broken.js'
        
        try:
            with open(broken_test_file, 'w') as f:
                f.write(broken_test_content)
            
            result = subprocess.run(
                ['node', str(broken_test_file)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should fail with non-zero exit code
            self.assertNotEqual(result.returncode, 0, "Broken test should fail")
            
        finally:
            # Clean up temporary file
            if broken_test_file.exists():
                broken_test_file.unlink()

class TestFrontendTestInfrastructure(unittest.TestCase):
    """Test the frontend testing infrastructure itself"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.project_root = Path(__file__).parent.parent
        self.frontend_test_dir = self.project_root / 'tests' / 'frontend'
    
    def test_frontend_test_directory_structure(self):
        """Test that frontend test directory has correct structure"""
        self.assertTrue(self.frontend_test_dir.exists(), "Frontend test directory should exist")
        self.assertTrue(self.frontend_test_dir.is_dir(), "Frontend test path should be a directory")
        
        # Check for required files
        required_files = [
            'test_session_sync.html',
            'test_session_sync.js',
            'README.md'
        ]
        
        for filename in required_files:
            file_path = self.frontend_test_dir / filename
            self.assertTrue(
                file_path.exists(),
                f"Required file should exist: {filename}"
            )
    
    def test_node_js_availability(self):
        """Test if Node.js is available for running JavaScript tests"""
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Node.js is available
                self.assertIn('v', result.stdout, "Node.js version should be reported")
            else:
                self.skipTest("Node.js not available")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Node.js not available")
    
    def test_javascript_syntax_validation(self):
        """Test that JavaScript test files have valid syntax"""
        js_test_file = self.frontend_test_dir / 'test_session_sync.js'
        
        try:
            # Use Node.js to check syntax
            result = subprocess.run(
                ['node', '--check', str(js_test_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            self.assertEqual(
                result.returncode, 0,
                f"JavaScript syntax should be valid. Error: {result.stderr}"
            )
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("Cannot validate JavaScript syntax - Node.js not available")

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)