# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for landing page error handling.

This module tests the integration of error handling with the actual Flask application.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import tempfile
import logging

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestLandingPageErrorIntegration(unittest.TestCase):
    """Integration tests for landing page error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
        # Register the main blueprint
        try:
            from app.blueprints.main.routes import main_bp
            self.app.register_blueprint(main_bp)
        except ImportError:
            # If we can't import the blueprint, skip these tests
            self.skipTest("Main blueprint not available for testing")
        
        self.client = self.app.test_client()
    
    def test_landing_page_loads_successfully(self):
        """Test that the landing page loads successfully under normal conditions"""
        with self.app.app_context():
            # Mock the dependencies that might not be available in test environment
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated = False
                
                with patch('app.blueprints.main.routes.has_previous_session', return_value=False):
                    with patch('app.blueprints.main.routes.cached_render_template') as mock_render:
                        mock_render.return_value = "<html>Test Landing Page</html>"
                        
                        response = self.client.get('/')
                        
                        self.assertEqual(response.status_code, 200)
                        mock_render.assert_called_once_with('landing.html')
    
    def test_landing_page_handles_template_error(self):
        """Test that the landing page handles template rendering errors gracefully"""
        with self.app.app_context():
            # Mock the dependencies
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated = False
                
                with patch('app.blueprints.main.routes.has_previous_session', return_value=False):
                    with patch('app.blueprints.main.routes.cached_render_template') as mock_render:
                        # Simulate template rendering error
                        mock_render.side_effect = Exception("Template rendering failed")
                        
                        response = self.client.get('/')
                        
                        # Should still return a response (fallback HTML)
                        self.assertEqual(response.status_code, 200)
                        
                        # Should contain fallback content
                        html_content = response.get_data(as_text=True)
                        self.assertIn('Vedfolnir', html_content)
                        self.assertIn('Get Started', html_content)
    
    def test_landing_page_handles_authentication_error(self):
        """Test that the landing page handles authentication errors gracefully"""
        with self.app.app_context():
            # Mock authentication to raise an error
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated.side_effect = Exception("Authentication system error")
                
                with patch('app.blueprints.main.routes.has_previous_session', return_value=False):
                    with patch('app.blueprints.main.routes.cached_render_template') as mock_render:
                        mock_render.return_value = "<html>Test Landing Page</html>"
                        
                        response = self.client.get('/')
                        
                        # Should still return a successful response
                        self.assertEqual(response.status_code, 200)
                        
                        # Should have called the template render (fallback to anonymous user)
                        mock_render.assert_called_once_with('landing.html')
    
    def test_landing_page_handles_session_detection_error(self):
        """Test that the landing page handles session detection errors gracefully"""
        with self.app.app_context():
            # Mock the dependencies
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated = False
                
                with patch('app.blueprints.main.routes.has_previous_session') as mock_session:
                    # Simulate session detection error
                    mock_session.side_effect = Exception("Session detection failed")
                    
                    with patch('app.blueprints.main.routes.cached_render_template') as mock_render:
                        mock_render.return_value = "<html>Test Landing Page</html>"
                        
                        response = self.client.get('/')
                        
                        # Should still return a successful response
                        self.assertEqual(response.status_code, 200)
                        
                        # Should have called the template render (fallback to new user)
                        mock_render.assert_called_once_with('landing.html')
    
    def test_landing_page_redirects_authenticated_user(self):
        """Test that authenticated users are redirected to dashboard"""
        with self.app.app_context():
            # Mock authenticated user
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated = True
                mock_user.username = "test_user"
                
                with patch('app.blueprints.main.routes.render_dashboard') as mock_dashboard:
                    mock_dashboard.return_value = "<html>Dashboard</html>"
                    
                    response = self.client.get('/')
                    
                    # Should call render_dashboard
                    mock_dashboard.assert_called_once()
    
    def test_landing_page_redirects_returning_user(self):
        """Test that users with previous sessions are redirected to login"""
        with self.app.app_context():
            # Mock the dependencies
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated = False
                
                with patch('app.blueprints.main.routes.has_previous_session', return_value=True):
                    response = self.client.get('/')
                    
                    # Should redirect to login
                    self.assertEqual(response.status_code, 302)
                    # Note: The exact redirect location depends on url_for configuration
    
    def test_landing_page_system_stability_decorator(self):
        """Test that the system stability decorator works correctly"""
        with self.app.app_context():
            # Mock everything to fail catastrophically
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated.side_effect = Exception("Critical system failure")
                
                with patch('app.blueprints.main.routes.has_previous_session') as mock_session:
                    mock_session.side_effect = Exception("Session system failure")
                    
                    with patch('app.blueprints.main.routes.cached_render_template') as mock_render:
                        mock_render.side_effect = Exception("Template system failure")
                        
                        response = self.client.get('/')
                        
                        # System stability decorator should provide fallback
                        self.assertEqual(response.status_code, 200)
                        
                        # Should contain fallback content
                        html_content = response.get_data(as_text=True)
                        self.assertIn('Vedfolnir', html_content)
    
    def test_landing_page_error_headers(self):
        """Test that error responses include appropriate headers"""
        with self.app.app_context():
            # Mock template rendering to fail
            with patch('app.blueprints.main.routes.current_user') as mock_user:
                mock_user.is_authenticated = False
                
                with patch('app.blueprints.main.routes.has_previous_session', return_value=False):
                    with patch('app.blueprints.main.routes.cached_render_template') as mock_render:
                        mock_render.side_effect = Exception("Template error")
                        
                        response = self.client.get('/')
                        
                        # Should include fallback mode header
                        self.assertIn('X-Fallback-Mode', response.headers)
                        self.assertEqual(response.headers['X-Fallback-Mode'], 'system-error')

if __name__ == '__main__':
    # Set up logging for tests
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)