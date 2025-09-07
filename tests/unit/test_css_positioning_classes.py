# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import re


class TestCSSPositioningClasses(unittest.TestCase):
    """Test that positioning CSS classes are properly defined in components.css"""
    
    def setUp(self):
        """Set up test by reading the components.css file"""
        self.css_file_path = os.path.join('static', 'css', 'components.css')
        self.assertTrue(os.path.exists(self.css_file_path), 
                       f"CSS file not found at {self.css_file_path}")
        
        with open(self.css_file_path, 'r', encoding='utf-8') as f:
            self.css_content = f.read()
    
    def test_bulk_select_positioning_classes_exist(self):
        """Test that bulk select positioning classes are defined"""
        required_classes = [
            '.bulk-select-position',
            '.bulk-select-overlay',
            '.bulk-select-checkbox'
        ]
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, self.css_content,
                            f"CSS class {css_class} not found in components.css")
    
    def test_checkbox_scale_classes_exist(self):
        """Test that checkbox scaling classes are defined"""
        required_classes = [
            '.checkbox-scale-sm',
            '.checkbox-scale-md', 
            '.checkbox-scale-lg'
        ]
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, self.css_content,
                            f"CSS class {css_class} not found in components.css")
    
    def test_cursor_classes_exist(self):
        """Test that cursor utility classes are defined"""
        required_classes = [
            '.cursor-move',
            '.cursor-grab',
            '.cursor-grabbing',
            '.cursor-pointer',
            '.cursor-default'
        ]
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, self.css_content,
                            f"CSS class {css_class} not found in components.css")
    
    def test_overflow_classes_exist(self):
        """Test that overflow utility classes are defined"""
        required_classes = [
            '.overflow-hidden',
            '.overflow-auto',
            '.overflow-scroll',
            '.overflow-visible'
        ]
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, self.css_content,
                            f"CSS class {css_class} not found in components.css")
    
    def test_positioning_utility_classes_exist(self):
        """Test that positioning utility classes are defined"""
        required_classes = [
            '.position-absolute',
            '.position-relative',
            '.top-10',
            '.left-10',
            '.z-index-10'
        ]
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, self.css_content,
                            f"CSS class {css_class} not found in components.css")
    
    def test_transform_utility_classes_exist(self):
        """Test that transform utility classes are defined"""
        required_classes = [
            '.transform-scale-sm',
            '.transform-scale-md',
            '.transform-scale-lg',
            '.transform-scale-xl'
        ]
        
        for css_class in required_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, self.css_content,
                            f"CSS class {css_class} not found in components.css")
    
    def test_bulk_select_position_properties(self):
        """Test that bulk-select-position has correct CSS properties"""
        # Find the .bulk-select-position class definition
        pattern = r'\.bulk-select-position\s*\{([^}]+)\}'
        match = re.search(pattern, self.css_content, re.DOTALL)
        
        self.assertIsNotNone(match, "Could not find .bulk-select-position class definition")
        
        properties = match.group(1)
        self.assertIn('position: absolute', properties)
        self.assertIn('top: 10px', properties)
        self.assertIn('left: 10px', properties)
        self.assertIn('z-index: 10', properties)
    
    def test_checkbox_scale_properties(self):
        """Test that checkbox scale classes have correct transform properties"""
        scale_tests = [
            ('.checkbox-scale-sm', 'scale(1.2)'),
            ('.checkbox-scale-md', 'scale(1.5)'),
            ('.checkbox-scale-lg', 'scale(1.8)')
        ]
        
        for css_class, expected_scale in scale_tests:
            with self.subTest(css_class=css_class, expected_scale=expected_scale):
                pattern = rf'{re.escape(css_class)}\s*\{{([^}}]+)\}}'
                match = re.search(pattern, self.css_content, re.DOTALL)
                
                self.assertIsNotNone(match, f"Could not find {css_class} class definition")
                
                properties = match.group(1)
                self.assertIn(f'transform: {expected_scale}', properties)
    
    def test_cursor_move_properties(self):
        """Test that cursor-move class has correct cursor property"""
        pattern = r'\.cursor-move\s*\{([^}]+)\}'
        match = re.search(pattern, self.css_content, re.DOTALL)
        
        self.assertIsNotNone(match, "Could not find .cursor-move class definition")
        
        properties = match.group(1)
        self.assertIn('cursor: move', properties)
    
    def test_css_file_has_copyright_header(self):
        """Test that the CSS file has the required copyright header"""
        self.assertTrue(self.css_content.startswith('/* Copyright (C) 2025 iolaire mcfadden.'),
                       "CSS file missing required copyright header")
    
    def test_css_syntax_validity(self):
        """Basic test for CSS syntax validity"""
        # Count opening and closing braces
        open_braces = self.css_content.count('{')
        close_braces = self.css_content.count('}')
        
        self.assertEqual(open_braces, close_braces, 
                        "Mismatched braces in CSS file - possible syntax error")
        
        # Check for common syntax issues
        self.assertNotIn(';;', self.css_content, "Double semicolons found in CSS")
        self.assertNotIn('{{', self.css_content, "Double opening braces found in CSS")
        self.assertNotIn('}}', self.css_content, "Double closing braces found in CSS")


if __name__ == '__main__':
    unittest.main()