# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import re
import glob
from pathlib import Path


class TestCSSSecurityEnhancement(unittest.TestCase):
    """Test suite for CSS security enhancement implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.templates_dir = self.project_root / "templates"
        self.admin_templates_dir = self.project_root / "admin" / "templates"
        self.static_css_dir = self.project_root / "static" / "css"
        self.admin_static_css_dir = self.project_root / "admin" / "static" / "css"
        
        # Expected CSS files from the implementation
        self.expected_css_files = [
            "static/css/security-extracted.css",
            "static/css/components.css",
            "admin/static/css/admin-extracted.css"
        ]
        
        # CSS classes that should be used in templates
        self.expected_css_classes = [
            "progress-bar-dynamic",
            "progress-sm", "progress-md", "progress-lg",
            "hidden",
            "modal-overlay",
            "bulk-select-position",
            "bulk-select-checkbox", 
            "image-zoom-wrapper",
            "caption-container",
            "caption-field",
            "login-icon",
            "maintenance-icon"
        ]

    def test_no_inline_styles_in_templates(self):
        """Test that no inline styles remain in HTML templates"""
        inline_style_pattern = re.compile(r'style\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
        violations = []
        
        # Scan main templates
        template_files = glob.glob(str(self.templates_dir / "**" / "*.html"), recursive=True)
        
        # Scan admin templates
        if self.admin_templates_dir.exists():
            admin_template_files = glob.glob(str(self.admin_templates_dir / "**" / "*.html"), recursive=True)
            template_files.extend(admin_template_files)
        
        for template_file in template_files:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = inline_style_pattern.findall(content)
                if matches:
                    relative_path = os.path.relpath(template_file, self.project_root)
                    violations.append({
                        'file': relative_path,
                        'inline_styles': matches
                    })
        
        if violations:
            violation_details = []
            for violation in violations:
                violation_details.append(f"File: {violation['file']}")
                for style in violation['inline_styles']:
                    violation_details.append(f"  - {style}")
            
            self.fail(f"Found {len(violations)} template(s) with inline styles:\n" + 
                     "\n".join(violation_details))

    def test_css_files_exist_and_accessible(self):
        """Test that all new CSS files exist and are accessible"""
        missing_files = []
        
        for css_file_path in self.expected_css_files:
            full_path = self.project_root / css_file_path
            if not full_path.exists():
                missing_files.append(css_file_path)
            else:
                # Test that file is readable
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Verify it's not empty
                        if not content.strip():
                            missing_files.append(f"{css_file_path} (empty file)")
                except Exception as e:
                    missing_files.append(f"{css_file_path} (read error: {e})")
        
        if missing_files:
            self.fail(f"Missing or inaccessible CSS files:\n" + 
                     "\n".join(f"  - {file}" for file in missing_files))

    def test_css_class_usage_in_templates(self):
        """Test that CSS classes are properly used in templates"""
        template_files = glob.glob(str(self.templates_dir / "**" / "*.html"), recursive=True)
        
        # Add admin templates
        if self.admin_templates_dir.exists():
            admin_template_files = glob.glob(str(self.admin_templates_dir / "**" / "*.html"), recursive=True)
            template_files.extend(admin_template_files)
        
        # Read all template content
        all_template_content = ""
        for template_file in template_files:
            with open(template_file, 'r', encoding='utf-8') as f:
                all_template_content += f.read() + "\n"
        
        unused_classes = []
        for css_class in self.expected_css_classes:
            # Check for class usage in templates (class="..." or class='...')
            class_pattern = re.compile(rf'class\s*=\s*["\'][^"\']*\b{re.escape(css_class)}\b[^"\']*["\']', re.IGNORECASE)
            if not class_pattern.search(all_template_content):
                unused_classes.append(css_class)
        
        if unused_classes:
            self.fail(f"CSS classes not found in templates (may indicate missing implementation):\n" + 
                     "\n".join(f"  - {cls}" for cls in unused_classes))

    def test_css_files_have_copyright_headers(self):
        """Test that CSS files have proper copyright headers"""
        missing_headers = []
        
        for css_file_path in self.expected_css_files:
            full_path = self.project_root / css_file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check for copyright header
                    if "Copyright (C) 2025 iolaire mcfadden" not in content:
                        missing_headers.append(css_file_path)
        
        if missing_headers:
            self.fail(f"CSS files missing copyright headers:\n" + 
                     "\n".join(f"  - {file}" for file in missing_headers))

    def test_css_includes_in_base_templates(self):
        """Test that base templates include the new CSS files"""
        base_templates = [
            "templates/base.html",
            "admin/templates/base_admin.html"
        ]
        
        missing_includes = []
        
        for base_template in base_templates:
            template_path = self.project_root / base_template
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for CSS includes
                    expected_includes = []
                    if "admin" in base_template:
                        expected_includes = ["admin-extracted.css"]
                    else:
                        expected_includes = ["security-extracted.css", "components.css"]
                    
                    for css_file in expected_includes:
                        if css_file not in content:
                            missing_includes.append(f"{base_template} missing {css_file}")
        
        if missing_includes:
            self.fail(f"Base templates missing CSS includes:\n" + 
                     "\n".join(f"  - {include}" for include in missing_includes))

    def test_progress_bar_css_variables(self):
        """Test that progress bar CSS uses CSS variables for dynamic width"""
        css_files_to_check = [
            self.project_root / "static" / "css" / "security-extracted.css",
            self.project_root / "static" / "css" / "components.css"
        ]
        
        found_css_variables = False
        
        for css_file in css_files_to_check:
            if css_file.exists():
                with open(css_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for CSS variable usage for progress bars
                    if "var(--progress-width)" in content or "--progress-width" in content:
                        found_css_variables = True
                        break
        
        if not found_css_variables:
            self.fail("Progress bar CSS variables not found in CSS files")

    def test_modal_visibility_classes(self):
        """Test that modal visibility classes are defined in CSS"""
        css_files_to_check = [
            self.project_root / "static" / "css" / "security-extracted.css",
            self.project_root / "static" / "css" / "components.css"
        ]
        
        required_modal_classes = [".hidden", ".modal-overlay"]
        found_classes = []
        
        for css_file in css_files_to_check:
            if css_file.exists():
                with open(css_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for modal_class in required_modal_classes:
                        if modal_class in content:
                            found_classes.append(modal_class)
        
        missing_classes = [cls for cls in required_modal_classes if cls not in found_classes]
        
        if missing_classes:
            self.fail(f"Missing modal visibility classes in CSS:\n" + 
                     "\n".join(f"  - {cls}" for cls in missing_classes))


if __name__ == '__main__':
    unittest.main()