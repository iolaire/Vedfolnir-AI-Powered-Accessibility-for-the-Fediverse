#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test Platform Management Interface

Tests the web interface for platform management functionality.
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

# Import the web app and related modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlatformManagementInterface(unittest.TestCase):
    """Test platform management web interface"""
    
    def setUp(self):
        """Set up test environment"""
        pass
    
    def tearDown(self):
        """Clean up test environment"""
        pass
    
    def test_platform_management_route_exists(self):
        """Test that the platform management route exists in web_app.py"""
        from web_app import app
        
        # Check if the route is registered
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertIn('/platform_management', routes)
    
    def test_platform_management_api_routes_exist(self):
        """Test that platform management API routes exist"""
        from web_app import app
        
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertIn('/api/add_platform', routes)
        self.assertIn('/api/switch_platform/<int:platform_id>', routes)
        self.assertIn('/api/test_platform/<int:platform_id>', routes)
        self.assertIn('/api/delete_platform/<int:platform_id>', routes)
    
    def test_platform_management_imports_exist(self):
        """Test that required imports exist in web_app.py"""
        import web_app
        
        # Check if PlatformConnection is imported
        self.assertTrue(hasattr(web_app, 'PlatformConnection'))
    
    def test_platform_management_functions_exist(self):
        """Test that platform management functions exist in web_app.py"""
        import web_app
        
        # Check if the functions exist
        self.assertTrue(hasattr(web_app, 'platform_management'))
        self.assertTrue(hasattr(web_app, 'api_add_platform'))
        self.assertTrue(hasattr(web_app, 'api_switch_platform'))
        self.assertTrue(hasattr(web_app, 'api_test_platform'))
        self.assertTrue(hasattr(web_app, 'api_delete_platform'))
    
    def test_platform_management_javascript_file_exists(self):
        """Test that the JavaScript file for platform management exists"""
        js_path = os.path.join('static', 'js', 'platform_management.js')
        self.assertTrue(os.path.exists(js_path), "Platform management JavaScript file should exist")
    
    def test_platform_management_template_exists(self):
        """Test that the platform management template exists"""
        template_path = os.path.join('templates', 'platform_management.html')
        self.assertTrue(os.path.exists(template_path), "Platform management template should exist")


if __name__ == '__main__':
    unittest.main()