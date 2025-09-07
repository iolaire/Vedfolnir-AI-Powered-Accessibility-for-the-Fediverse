# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive CSS Inline Styles Security Test
Tests for remaining inline styles in HTML templates
"""

import unittest
import os
import re
import glob
from pathlib import Path


class TestCSSInlineStylesScan(unittest.TestCase):
    """Test suite for CSS inline styles security compliance"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.templates_dir = self.project_root / "templates"
        self.admin_templates_dir = self.project_root / "admin" / "templates"
        self.inline_style_pattern = re.compile(r'style\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
    
    def get_all_template_files(self):
        """Get all template files excluding email templates"""
        template_files = []
        
        # Main templates
        if self.templates_dir.exists():
            main_templates = glob.glob(str(self.templates_dir / "**" / "*.html"), recursive=True)
            # Filter out email templates as they require inline CSS for email client compatibility
            main_templates = [f for f in main_templates if '/emails/' not in f.replace('\\', '/')]
            template_files.extend(main_templates)
        
        # Admin templates
        if self.admin_templates_dir.exists():
            admin_templates = glob.glob(str(self.admin_templates_dir / "**" / "*.html"), recursive=True)
            template_files.extend(admin_templates)
        
        return template_files
    
    def test_no_inline_styles_in_templates(self):
        """Test that no inline styles remain in web templates"""
        template_files = self.get_all_template_files()
        files_with_inline_styles = []
        
        for template_file in template_files:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = self.inline_style_pattern.findall(content)
                
                if matches:
                    relative_path = os.path.relpath(template_file, self.project_root)
                    files_with_inline_styles.append({
                        'file': relative_path,
                        'styles': matches
                    })
        
        if files_with_inline_styles:
            error_msg = "Found inline styles in the following templates:\n"
            for file_info in files_with_inline_styles:
                error_msg += f"\n📄 {file_info['file']}:\n"
                for style in file_info['styles']:
                    error_msg += f"   • style=\"{style}\"\n"
            
            error_msg += f"\n❌ Total files with inline styles: {len(files_with_inline_styles)}"
            error_msg += "\n\n💡 These styles need to be extracted to external CSS files."
            error_msg += "\n📧 Note: Email templates are intentionally excluded from this test."
            
            self.fail(error_msg)
    
    def test_css_files_exist(self):
        """Test that all required CSS files exist"""
        required_css_files = [
            "static/css/security-extracted.css",
            "static/css/components.css",
            "admin/static/css/admin-extracted.css"
        ]
        
        missing_files = []
        for css_file in required_css_files:
            css_path = self.project_root / css_file
            if not css_path.exists():
                missing_files.append(css_file)
        
        if missing_files:
            self.fail(f"Missing required CSS files: {', '.join(missing_files)}")
    
    def test_css_files_have_content(self):
        """Test that CSS files have actual content"""
        css_files = [
            "static/css/security-extracted.css",
            "static/css/components.css",
            "admin/static/css/admin-extracted.css"
        ]
        
        empty_files = []
        for css_file in css_files:
            css_path = self.project_root / css_file
            if css_path.exists():
                with open(css_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # Check if file has meaningful content (more than just copyright header)
                    lines = [line.strip() for line in content.split('\n') if line.strip()]
                    non_comment_lines = [line for line in lines if not line.startswith('/*') and not line.startswith('*/')]
                    
                    if len(non_comment_lines) < 5:  # Should have at least some CSS rules
                        empty_files.append(css_file)
        
        if empty_files:
            self.fail(f"CSS files appear to be empty or have minimal content: {', '.join(empty_files)}")
    
    def test_email_templates_excluded(self):
        """Test that email templates are properly excluded from inline style checks"""
        email_templates_dir = self.templates_dir / "emails"
        
        if email_templates_dir.exists():
            email_templates = glob.glob(str(email_templates_dir / "**" / "*.html"), recursive=True)
            
            # Email templates should be allowed to have inline styles
            email_with_inline_styles = 0
            for template_file in email_templates:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = self.inline_style_pattern.findall(content)
                    if matches:
                        email_with_inline_styles += 1
            
            # This is informational - email templates are allowed to have inline styles
            print(f"📧 Email templates with inline styles: {email_with_inline_styles}/{len(email_templates)}")
            print("   (This is expected and allowed for email client compatibility)")
    
    def test_template_count_verification(self):
        """Test that we're scanning a reasonable number of templates"""
        template_files = self.get_all_template_files()
        
        # Should have at least 20 templates to scan
        self.assertGreaterEqual(len(template_files), 20, 
                               f"Expected at least 20 templates to scan, found {len(template_files)}")
        
        print(f"📊 Scanning {len(template_files)} template files for inline styles")


def run_comprehensive_scan():
    """Run comprehensive inline style scan with detailed reporting"""
    print("=== Comprehensive CSS Inline Styles Security Scan ===\n")
    
    # Run the test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCSSInlineStylesScan)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n=== Scan Results ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, failure in result.failures:
            print(f"   {test}: {failure}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, error in result.errors:
            print(f"   {test}: {error}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}: CSS Security Scan")
    
    return success


if __name__ == '__main__':
    run_comprehensive_scan()