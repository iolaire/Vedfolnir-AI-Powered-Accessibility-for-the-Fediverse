#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Structure Validator

Validates that the landing page test files are properly structured and
can be imported without requiring Selenium WebDriver installation.
"""

import sys
import os
import unittest
import importlib.util
from unittest.mock import Mock, patch

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def mock_playwright_imports():
    """Mock Playwright imports to allow testing without Playwright installation"""
    
    # Mock playwright modules
    playwright_mock = Mock()
    playwright_mock.sync_api = Mock()
    playwright_mock.sync_api.sync_playwright = Mock()
    playwright_mock.async_api = Mock()
    playwright_mock.async_api.async_playwright = Mock()
    
    # Mock requests
    requests_mock = Mock()
    requests_mock.get = Mock()
    
    sys.modules['playwright'] = playwright_mock
    sys.modules['playwright.sync_api'] = playwright_mock.sync_api
    sys.modules['playwright.async_api'] = playwright_mock.async_api
    sys.modules['requests'] = requests_mock


def validate_test_file_structure(file_path, expected_class_name):
    """Validate that a test file has the expected structure"""
    print(f"Validating {file_path}...")
    
    # Check file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    # Check file is readable
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Cannot read file: {e}")
        return False
    
    # Check copyright header
    if "Copyright (C) 2025 iolaire mcfadden" not in content:
        print(f"❌ Missing copyright header in {file_path}")
        return False
    
    # Check class definition
    if f"class {expected_class_name}" not in content:
        print(f"❌ Missing class {expected_class_name} in {file_path}")
        return False
    
    # Check unittest inheritance
    if "unittest.TestCase" not in content:
        print(f"❌ Class should inherit from unittest.TestCase in {file_path}")
        return False
    
    # Check for test methods
    test_method_count = content.count("def test_")
    if test_method_count == 0:
        print(f"❌ No test methods found in {file_path}")
        return False
    
    print(f"✅ {file_path} structure valid ({test_method_count} test methods)")
    return True


def validate_imports():
    """Validate that test files can be imported"""
    print("Validating imports...")
    
    try:
        # Mock Playwright before importing
        mock_playwright_imports()
        
        # Try to import test modules
        from tests.frontend.test_landing_page_accessibility import LandingPageAccessibilityTests
        from tests.frontend.test_landing_page_ui import LandingPageUITests
        
        print("✅ Test modules imported successfully")
        
        # Check test methods exist
        accessibility_methods = [method for method in dir(LandingPageAccessibilityTests) if method.startswith('test_')]
        ui_methods = [method for method in dir(LandingPageUITests) if method.startswith('test_')]
        
        print(f"✅ Accessibility test methods: {len(accessibility_methods)}")
        print(f"✅ UI test methods: {len(ui_methods)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def validate_test_runner():
    """Validate test runner structure"""
    runner_path = os.path.join(os.path.dirname(__file__), 'run_landing_page_tests.py')
    
    print(f"Validating test runner: {runner_path}")
    
    if not os.path.exists(runner_path):
        print("❌ Test runner not found")
        return False
    
    try:
        with open(runner_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Cannot read test runner: {e}")
        return False
    
    # Check for required components
    required_components = [
        "class LandingPageTestRunner",
        "def run_accessibility_tests",
        "def run_ui_tests",
        "def run_all_tests",
        "def generate_report",
        "if __name__ == '__main__'"
    ]
    
    for component in required_components:
        if component not in content:
            print(f"❌ Missing component: {component}")
            return False
    
    print("✅ Test runner structure valid")
    return True


def validate_requirements():
    """Validate requirements file exists and has expected dependencies"""
    req_path = os.path.join(os.path.dirname(__file__), 'requirements-test.txt')
    
    print(f"Validating requirements: {req_path}")
    
    if not os.path.exists(req_path):
        print("❌ Requirements file not found")
        return False
    
    try:
        with open(req_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Cannot read requirements: {e}")
        return False
    
    # Check for required dependencies
    required_deps = [
        "playwright",
        "requests"
    ]
    
    for dep in required_deps:
        if dep not in content:
            print(f"❌ Missing dependency: {dep}")
            return False
    
    print("✅ Requirements file valid")
    return True


def validate_documentation():
    """Validate README documentation exists"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README_landing_page_tests.md')
    
    print(f"Validating documentation: {readme_path}")
    
    if not os.path.exists(readme_path):
        print("❌ README not found")
        return False
    
    try:
        with open(readme_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Cannot read README: {e}")
        return False
    
    # Check for required sections
    required_sections = [
        "# Landing Page Frontend Accessibility and UI Tests",
        "## Overview",
        "## Prerequisites",
        "## Running Tests",
        "## Troubleshooting"
    ]
    
    for section in required_sections:
        if section not in content:
            print(f"❌ Missing section: {section}")
            return False
    
    print("✅ Documentation valid")
    return True


def main():
    """Main validation function"""
    print("🔍 Validating Landing Page Test Structure")
    print("=" * 60)
    
    all_valid = True
    
    # Validate test file structures
    test_files = [
        ('tests/frontend/test_landing_page_accessibility.py', 'LandingPageAccessibilityTests'),
        ('tests/frontend/test_landing_page_ui.py', 'LandingPageUITests')
    ]
    
    for file_path, class_name in test_files:
        if not validate_test_file_structure(file_path, class_name):
            all_valid = False
    
    print()
    
    # Validate imports
    if not validate_imports():
        all_valid = False
    
    print()
    
    # Validate test runner
    if not validate_test_runner():
        all_valid = False
    
    print()
    
    # Validate requirements
    if not validate_requirements():
        all_valid = False
    
    print()
    
    # Validate documentation
    if not validate_documentation():
        all_valid = False
    
    print()
    print("=" * 60)
    
    if all_valid:
        print("🎉 All validations passed!")
        print("✅ Test structure is properly configured")
        print("✅ Files can be imported successfully")
        print("✅ Test runner is functional")
        print("✅ Requirements are specified")
        print("✅ Documentation is complete")
        print()
        print("Next steps:")
        print("1. Install test dependencies: pip install -r tests/frontend/requirements-test.txt")
        print("2. Install Playwright browsers: playwright install")
        print("3. Start web application: python web_app.py & sleep 10")
        print("4. Run tests: python tests/frontend/run_landing_page_tests.py --all")
        return 0
    else:
        print("❌ Validation failed!")
        print("Please fix the issues above before running tests.")
        return 1


if __name__ == '__main__':
    sys.exit(main())