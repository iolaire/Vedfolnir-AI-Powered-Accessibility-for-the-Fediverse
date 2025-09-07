# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import re


class TestCSSFormContentClasses(unittest.TestCase):
    """Test CSS form and content classes for security enhancement."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.css_files = [
            'static/css/security-extracted.css',
            'static/css/components.css'
        ]
        
    def test_css_files_exist(self):
        """Test that required CSS files exist."""
        for css_file in self.css_files:
            with self.subTest(css_file=css_file):
                self.assertTrue(
                    os.path.exists(css_file),
                    f"CSS file {css_file} should exist"
                )
    
    def test_min_max_height_classes(self):
        """Test that min/max height container classes exist."""
        required_classes = [
            '.min-height-sm',
            '.min-height-md', 
            '.min-height-lg',
            '.min-height-xl',
            '.max-height-sm',
            '.max-height-md',
            '.max-height-lg', 
            '.max-height-xl',
            '.container-sm',
            '.container-md',
            '.container-lg',
            '.container-xl'
        ]
        
        css_content = self._read_css_files()
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                pattern = rf'{re.escape(css_class)}\s*\{{'
                self.assertRegex(
                    css_content,
                    pattern,
                    f"CSS class {css_class} should be defined"
                )
    
    def test_icon_sizing_classes(self):
        """Test that icon sizing classes exist."""
        required_classes = [
            '.icon-xs',
            '.icon-sm',
            '.icon-md',
            '.icon-lg',
            '.icon-xl',
            '.icon-2xl',
            '.icon-3xl',
            '.icon-4xl',
            '.login-icon',
            '.maintenance-icon',
            '.icon-button',
            '.icon-nav',
            '.icon-header',
            '.icon-hero',
            '.icon-display'
        ]
        
        css_content = self._read_css_files()
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                pattern = rf'{re.escape(css_class)}\s*\{{'
                self.assertRegex(
                    css_content,
                    pattern,
                    f"Icon class {css_class} should be defined"
                )
    
    def test_form_field_height_classes(self):
        """Test that form field height classes exist."""
        required_classes = [
            '.form-field-sm',
            '.form-field-md',
            '.form-field-lg',
            '.form-field-xl',
            '.textarea-sm',
            '.textarea-md',
            '.textarea-lg',
            '.textarea-xl',
            '.input-sm',
            '.input-md',
            '.input-lg',
            '.input-xl',
            '.caption-field',
            '.caption-container'
        ]
        
        css_content = self._read_css_files()
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                pattern = rf'{re.escape(css_class)}\s*\{{'
                self.assertRegex(
                    css_content,
                    pattern,
                    f"Form field class {css_class} should be defined"
                )
    
    def test_css_variables_defined(self):
        """Test that required CSS variables are defined."""
        required_variables = [
            '--caption-min-height',
            '--caption-max-height',
            '--icon-size-sm',
            '--icon-size-md',
            '--icon-size-lg',
            '--form-field-height-sm',
            '--form-field-height-md',
            '--form-field-height-lg',
            '--form-border-color',
            '--form-bg-color'
        ]
        
        css_content = self._read_css_files()
        
        for variable in required_variables:
            with self.subTest(variable=variable):
                pattern = rf'{re.escape(variable)}:\s*[^;]+;'
                self.assertRegex(
                    css_content,
                    pattern,
                    f"CSS variable {variable} should be defined"
                )
    
    def test_copyright_headers(self):
        """Test that CSS files have copyright headers."""
        for css_file in self.css_files:
            with self.subTest(css_file=css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn(
                        'Copyright (C) 2025 iolaire mcfadden',
                        content,
                        f"CSS file {css_file} should have copyright header"
                    )
    
    def test_form_utility_classes(self):
        """Test that form utility classes exist."""
        required_classes = [
            '.form-field-bordered',
            '.form-field-rounded',
            '.form-field-shadow',
            '.form-field-valid',
            '.form-field-invalid',
            '.form-group-compact',
            '.form-group-spaced',
            '.scrollable-content'
        ]
        
        css_content = self._read_css_files()
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                pattern = rf'{re.escape(css_class)}\s*\{{'
                self.assertRegex(
                    css_content,
                    pattern,
                    f"Form utility class {css_class} should be defined"
                )
    
    def _read_css_files(self):
        """Read all CSS files and return combined content."""
        content = ""
        for css_file in self.css_files:
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    content += f.read()
        return content


if __name__ == '__main__':
    unittest.main()