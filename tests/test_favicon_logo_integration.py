# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask
from web_app import app, validate_favicon_assets


class TestFaviconLogoIntegration(unittest.TestCase):
    """Test favicon and logo integration functionality"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()

    def test_required_favicon_assets_exist(self):
        """Test that required favicon assets exist"""
        required_assets = [
            'static/favicons/favicon.ico',
            'static/favicons/favicon-32x32.png',
            'static/favicons/favicon-16x16.png',
            'static/images/Logo.png'
        ]
        
        for asset in required_assets:
            asset_path = os.path.join(self.app.root_path, asset)
            self.assertTrue(
                os.path.exists(asset_path), 
                f"Missing required asset: {asset}"
            )

    def test_favicon_meta_tags_rendered(self):
        """Test that favicon meta tags are properly rendered in HTML responses"""
        with self.client as client:
            # Mock authentication to access protected routes
            with patch('flask_login.utils._get_user') as mock_user:
                mock_user.return_value = MagicMock()
                mock_user.return_value.is_authenticated = True
                mock_user.return_value.has_permission.return_value = True
                
                # Test that login page (public) contains favicon meta tags
                response = client.get('/login')
                self.assertEqual(response.status_code, 200)
                response_data = response.data.decode()
                
                # Check for favicon meta tags
                self.assertIn('favicon.ico', response_data)
                self.assertIn('apple-touch-icon', response_data)
                self.assertIn('manifest.json', response_data)

    def test_favicon_route_serves_file(self):
        """Test that the /favicon.ico route serves the favicon file"""
        response = self.client.get('/favicon.ico')
        
        # Should return the favicon file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/vnd.microsoft.icon')

    def test_favicon_cache_headers(self):
        """Test that favicon routes have proper cache headers"""
        response = self.client.get('/favicon.ico')
        
        # Check cache headers
        self.assertEqual(response.cache_control.max_age, 604800)  # 1 week
        self.assertTrue(response.cache_control.public)

    def test_static_favicon_cache_headers(self):
        """Test that static favicon files have proper cache headers"""
        response = self.client.get('/static/favicons/favicon-32x32.png')
        
        # Check cache headers are applied
        self.assertEqual(response.cache_control.max_age, 604800)  # 1 week
        self.assertTrue(response.cache_control.public)

    def test_logo_fallback_behavior(self):
        """Test that logo fallback behavior works when image is missing"""
        with self.client as client:
            # Mock authentication
            with patch('flask_login.utils._get_user') as mock_user:
                mock_user.return_value = MagicMock()
                mock_user.return_value.is_authenticated = True
                
                response = client.get('/login')
                response_data = response.data.decode()
                
                # Check that logo has onerror handler for fallback
                self.assertIn('onerror="this.style.display=\'none\'"', response_data)
                # Check that text fallback is present
                self.assertIn('navbar-brand-text', response_data)
                self.assertIn('Vedfolnir', response_data)

    def test_asset_validation_function(self):
        """Test the asset validation function"""
        # Test with existing assets
        result = validate_favicon_assets()
        self.assertTrue(result, "Asset validation should pass with existing assets")

    @patch('os.path.exists')
    def test_asset_validation_missing_assets(self, mock_exists):
        """Test asset validation with missing assets"""
        # Mock some assets as missing
        def mock_exists_side_effect(path):
            if 'favicon.ico' in path:
                return False
            return True
        
        mock_exists.side_effect = mock_exists_side_effect
        
        with patch('web_app.app.logger') as mock_logger:
            result = validate_favicon_assets()
            self.assertFalse(result, "Asset validation should fail with missing assets")
            mock_logger.warning.assert_called()

    def test_logo_accessibility_attributes(self):
        """Test that logo has proper accessibility attributes"""
        with self.client as client:
            # Mock authentication
            with patch('flask_login.utils._get_user') as mock_user:
                mock_user.return_value = MagicMock()
                mock_user.return_value.is_authenticated = True
                
                response = client.get('/login')
                response_data = response.data.decode()
                
                # Check for proper alt text
                self.assertIn('alt="Vedfolnir Logo"', response_data)
                # Check for ARIA label on navbar-brand
                self.assertIn('aria-label="Vedfolnir - Go to dashboard"', response_data)

    def test_manifest_json_content(self):
        """Test that manifest.json has proper content"""
        response = self.client.get('/static/favicons/manifest.json')
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        import json
        manifest_data = json.loads(response.data.decode())
        
        # Check required fields
        self.assertEqual(manifest_data['name'], 'Vedfolnir - Alt Text Bot')
        self.assertEqual(manifest_data['short_name'], 'Vedfolnir')
        self.assertIn('description', manifest_data)
        self.assertEqual(manifest_data['start_url'], '/')
        self.assertEqual(manifest_data['display'], 'standalone')
        self.assertIn('icons', manifest_data)
        self.assertIsInstance(manifest_data['icons'], list)
        self.assertGreater(len(manifest_data['icons']), 0)

    def test_logo_responsive_classes(self):
        """Test that logo has responsive CSS classes"""
        with self.client as client:
            # Mock authentication
            with patch('flask_login.utils._get_user') as mock_user:
                mock_user.return_value = MagicMock()
                mock_user.return_value.is_authenticated = True
                
                response = client.get('/login')
                response_data = response.data.decode()
                
                # Check for responsive classes
                self.assertIn('navbar-logo', response_data)
                self.assertIn('navbar-brand-text', response_data)
                self.assertIn('d-flex align-items-center', response_data)


if __name__ == '__main__':
    unittest.main()