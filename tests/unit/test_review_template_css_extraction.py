# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test suite for review template CSS extraction.

This test verifies that inline styles have been successfully extracted from
review templates and replaced with appropriate CSS classes.
"""

import unittest
import os
import re
from pathlib import Path


class TestReviewTemplateCSSExtraction(unittest.TestCase):
    """Test CSS extraction from review templates."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.template_dir = Path("templates")
        self.css_dir = Path("static/css")
        
        # Review template files to check
        self.review_templates = [
            "templates/review.html",
            "templates/review_batch.html", 
            "templates/review_batches.html"
        ]
        
        # CSS files that should contain extracted styles
        self.css_files = [
            "static/css/security-extracted.css",
            "static/css/components.css"
        ]
    
    def test_no_inline_styles_in_review_templates(self):
        """Test that review templates contain no inline styles."""
        inline_style_pattern = re.compile(r'style\s*=\s*["\'][^"\']*["\']')
        
        for template_path in self.review_templates:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all inline styles
                inline_styles = inline_style_pattern.findall(content)
                
                # Filter out acceptable inline styles (like CSS custom properties in JavaScript)
                problematic_styles = []
                for style in inline_styles:
                    # Skip styles that are clearly JavaScript-generated or acceptable
                    if 'z-index' in style.lower() and 'javascript' in content.lower():
                        continue
                    if '--progress-width' in style and 'javascript' in content.lower():
                        continue
                    problematic_styles.append(style)
                
                self.assertEqual(
                    len(problematic_styles), 0,
                    f"Found inline styles in {template_path}: {problematic_styles}"
                )
    
    def test_review_css_classes_exist(self):
        """Test that review-specific CSS classes exist in CSS files."""
        required_classes = [
            'review-progress-bar',
            'review-image-preview', 
            'review-card',
            'review-batch-stats',
            'review-filter-controls',
            'review-empty-state',
            'image-preview'
        ]
        
        # Read all CSS content
        all_css_content = ""
        for css_file in self.css_files:
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    all_css_content += f.read()
        
        # Check that each required class exists
        for css_class in required_classes:
            class_pattern = rf'\.{re.escape(css_class)}\s*\{{'
            self.assertTrue(
                re.search(class_pattern, all_css_content),
                f"CSS class '.{css_class}' not found in CSS files"
            )
    
    def test_progress_bar_css_variables(self):
        """Test that progress bar CSS variables are properly defined."""
        css_content = ""
        if os.path.exists("static/css/security-extracted.css"):
            with open("static/css/security-extracted.css", 'r', encoding='utf-8') as f:
                css_content = f.read()
        
        # Check for progress width variable
        self.assertIn(
            '--progress-width',
            css_content,
            "CSS custom property '--progress-width' not found"
        )
        
        # Check for review progress bar class
        self.assertIn(
            '.review-progress-bar',
            css_content,
            "CSS class '.review-progress-bar' not found"
        )
    
    def test_javascript_progress_bar_initialization(self):
        """Test that JavaScript properly initializes progress bars."""
        template_path = "templates/review_batches.html"
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for progress bar initialization JavaScript
            self.assertIn(
                'querySelectorAll(\'.review-progress-bar\')',
                content,
                "JavaScript progress bar initialization not found"
            )
            
            self.assertIn(
                'setProperty(\'--progress-width\'',
                content,
                "JavaScript CSS custom property setting not found"
            )
    
    def test_template_structure_preserved(self):
        """Test that template structure and functionality is preserved."""
        for template_path in self.review_templates:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check that templates still have proper structure
                self.assertIn('{% extends "base.html" %}', content)
                self.assertIn('{% block content %}', content)
                self.assertIn('{% endblock %}', content)
    
    def test_css_files_have_copyright_headers(self):
        """Test that CSS files have proper copyright headers."""
        for css_file in self.css_files:
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.assertTrue(
                    content.startswith('/* Copyright (C) 2025 iolaire mcfadden.'),
                    f"CSS file {css_file} missing copyright header"
                )
    
    def test_responsive_design_preserved(self):
        """Test that responsive design classes are included."""
        css_content = ""
        for css_file in self.css_files:
            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_content += f.read()
        
        # Check for responsive media queries
        self.assertIn(
            '@media (max-width: 768px)',
            css_content,
            "Mobile responsive styles not found"
        )
        
        # Check for review-specific responsive adjustments
        self.assertIn(
            'review-image-grid',
            css_content,
            "Review image grid styles not found"
        )


if __name__ == '__main__':
    unittest.main()