# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test CSS extraction for user management templates.

This test verifies that inline styles have been successfully extracted from
user management templates and moved to external CSS files.
"""

import unittest
import os
import re
from pathlib import Path


class TestUserManagementCSSExtraction(unittest.TestCase):
    """Test CSS extraction for user management templates."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.templates_dir = self.project_root / "templates"
        self.user_mgmt_dir = self.templates_dir / "user_management"
        self.css_file = self.project_root / "static" / "css" / "security-extracted.css"
        
    def test_no_inline_styles_in_user_management_templates(self):
        """Test that user management templates have no inline styles."""
        template_files = [
            self.user_mgmt_dir / "reset_password.html",
            self.user_mgmt_dir / "change_password.html",
            self.templates_dir / "first_time_setup.html"
        ]
        
        inline_style_pattern = re.compile(r'style\s*=\s*["\'][^"\']*["\']')
        
        for template_file in template_files:
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                matches = inline_style_pattern.findall(content)
                self.assertEqual(
                    len(matches), 0,
                    f"Found inline styles in {template_file.name}: {matches}"
                )
    
    def test_no_style_blocks_in_templates(self):
        """Test that templates have no embedded style blocks."""
        template_files = [
            self.user_mgmt_dir / "reset_password.html",
            self.user_mgmt_dir / "change_password.html",
            self.templates_dir / "first_time_setup.html"
        ]
        
        style_block_pattern = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
        
        for template_file in template_files:
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                matches = style_block_pattern.findall(content)
                self.assertEqual(
                    len(matches), 0,
                    f"Found style blocks in {template_file.name}: {len(matches)} blocks"
                )
    
    def test_css_classes_exist_in_external_file(self):
        """Test that required CSS classes exist in external CSS file."""
        required_classes = [
            'password-strength',
            'password-strength-progress',
            'password-strength-bar',
            'setup-emoji-icon',
            'setup-step-circle',
            'platform-option',
            'platform-icon-lg',
            'list-group-numbered',
            'profile-edit-mode',
            'profile-view-mode',
            'user-form-container'
        ]
        
        if self.css_file.exists():
            with open(self.css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
                
            for css_class in required_classes:
                class_pattern = rf'\.{re.escape(css_class)}\s*\{{'
                self.assertRegex(
                    css_content, class_pattern,
                    f"CSS class '{css_class}' not found in security-extracted.css"
                )
        else:
            self.fail("security-extracted.css file not found")
    
    def test_javascript_uses_css_classes(self):
        """Test that JavaScript uses CSS classes instead of direct style manipulation."""
        template_files = [
            self.user_mgmt_dir / "reset_password.html",
            self.user_mgmt_dir / "change_password.html",
            self.templates_dir / "first_time_setup.html"
        ]
        
        # Check for profile.html specifically since it has the toggle function
        profile_file = self.user_mgmt_dir / "profile.html"
        if profile_file.exists():
            template_files.append(profile_file)
        
        # Pattern to find direct style.display manipulations (should be avoided)
        bad_pattern = re.compile(r'\.style\.display\s*=')
        
        for template_file in template_files:
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                matches = bad_pattern.findall(content)
                self.assertEqual(
                    len(matches), 0,
                    f"Found direct style.display manipulation in {template_file.name}: {matches}"
                )
    
    def test_css_custom_properties_for_progress_bars(self):
        """Test that progress bars use CSS custom properties."""
        template_files = [
            self.user_mgmt_dir / "reset_password.html",
            self.user_mgmt_dir / "change_password.html"
        ]
        
        # Pattern to find CSS custom property usage
        custom_prop_pattern = re.compile(r'setProperty\s*\(\s*["\']--progress-width["\']')
        
        for template_file in template_files:
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                matches = custom_prop_pattern.findall(content)
                # Should find at least one usage of CSS custom properties for progress
                if 'password-strength-bar' in content:
                    self.assertGreater(
                        len(matches), 0,
                        f"Progress bar in {template_file.name} should use CSS custom properties"
                    )
    
    def test_templates_use_semantic_css_classes(self):
        """Test that templates use semantic CSS classes."""
        template_files = [
            (self.user_mgmt_dir / "reset_password.html", ['password-strength', 'password-strength-bar']),
            (self.user_mgmt_dir / "change_password.html", ['password-strength', 'password-strength-bar']),
            (self.templates_dir / "first_time_setup.html", ['platform-option', 'setup-step-circle'])
        ]
        
        for template_file, expected_classes in template_files:
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for css_class in expected_classes:
                    self.assertIn(
                        css_class, content,
                        f"Template {template_file.name} should use CSS class '{css_class}'"
                    )


if __name__ == '__main__':
    unittest.main()