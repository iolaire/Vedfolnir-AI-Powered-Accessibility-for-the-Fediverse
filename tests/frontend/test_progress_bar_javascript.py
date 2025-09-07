# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test progress bar JavaScript functionality using CSS custom properties
"""

import unittest
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from models import UserRole


class TestProgressBarJavaScript(unittest.TestCase):
    """Test progress bar JavaScript utilities"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, 
            username="test_progress_user", 
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_user(self.user_helper)
    
    def test_progress_bar_utils_file_exists(self):
        """Test that progress bar utilities file exists"""
        utils_path = os.path.join('static', 'js', 'progress-bar-utils.js')
        self.assertTrue(os.path.exists(utils_path), "Progress bar utilities file should exist")
    
    def test_progress_bar_init_file_exists(self):
        """Test that progress bar initialization file exists"""
        init_path = os.path.join('static', 'js', 'progress-bar-init.js')
        self.assertTrue(os.path.exists(init_path), "Progress bar initialization file should exist")
    
    def test_progress_bar_utils_content(self):
        """Test that progress bar utilities contain required functions"""
        utils_path = os.path.join('static', 'js', 'progress-bar-utils.js')
        
        with open(utils_path, 'r') as f:
            content = f.read()
        
        # Check for required functions
        required_functions = [
            'updateProgressBar',
            'updateProgressBarById',
            'updateProgressBarBySelector',
            'animateProgressBar',
            'resetProgressBar',
            'completeProgressBar',
            'setProgressBarError',
            'createProgressBar'
        ]
        
        for func in required_functions:
            self.assertIn(func, content, f"Function {func} should be present in progress bar utilities")
    
    def test_css_custom_property_usage(self):
        """Test that progress bar utilities use CSS custom properties"""
        utils_path = os.path.join('static', 'js', 'progress-bar-utils.js')
        
        with open(utils_path, 'r') as f:
            content = f.read()
        
        # Check for CSS custom property usage
        self.assertIn('--progress-width', content, "Should use --progress-width CSS custom property")
        self.assertIn('setProperty', content, "Should use setProperty to set CSS custom properties")
        
        # Check that inline styles are not used
        self.assertNotIn('style.width =', content, "Should not use inline style.width")
    
    def test_caption_generation_js_uses_utils(self):
        """Test that caption generation JavaScript uses the progress bar utilities"""
        caption_js_path = os.path.join('static', 'js', 'caption_generation.js')
        
        with open(caption_js_path, 'r') as f:
            content = f.read()
        
        # Check that it uses the progress bar utilities
        self.assertIn('progressBarUtils', content, "Caption generation should use progressBarUtils")
        self.assertIn('--progress-width', content, "Should use CSS custom properties for progress")
        
        # Check that it doesn't use inline styles
        self.assertNotIn('style="width:', content, "Should not use inline width styles")
    
    def test_no_inline_styles_in_js_files(self):
        """Test that JavaScript files don't contain inline style assignments"""
        js_dir = os.path.join('static', 'js')
        
        for filename in os.listdir(js_dir):
            if filename.endswith('.js'):
                filepath = os.path.join(js_dir, filename)
                
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Check for problematic inline style patterns
                problematic_patterns = [
                    r'\.style\.width\s*=',
                    r'setAttribute\("style"',
                    r'innerHTML.*style=',
                ]
                
                for pattern in problematic_patterns:
                    self.assertNotRegex(
                        content, 
                        pattern, 
                        f"File {filename} should not contain inline style pattern: {pattern}"
                    )


if __name__ == '__main__':
    unittest.main()