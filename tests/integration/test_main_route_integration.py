# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, session
from flask_login import LoginManager, AnonymousUserMixin
from app.blueprints.main.routes import main_bp


class TestMainRouteIntegration(unittest.TestCase):
    """Integration tests for the main route three-way logic"""
    
    def setUp(self):
        """Set up test Flask app with login manager"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        
        # Set up Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.anonymous_user = AnonymousUserMixin
        
        # Register blueprint
        self.app.register_blueprint(main_bp)
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test context"""
        self.app_context.pop()
    
    @patch('app.blueprints.main.routes.render_template')
    def test_anonymous_user_no_session_gets_landing(self, mock_render_template):
        """Test that anonymous users with no session get landing page"""
        mock_render_template.return_value = "Landing Page"
        
        with self.client as c:
            response = c.get('/')
            
            # Should render landing template
            mock_render_template.assert_called_with('landing.html')
    
    @patch('app.blueprints.main.routes.has_previous_session')
    def test_anonymous_user_with_session_redirects_to_login(self, mock_has_previous_session):
        """Test that anonymous users with previous session redirect to login"""
        mock_has_previous_session.return_value = True
        
        with self.client as c:
            response = c.get('/')
            
            # Should redirect (status code 302)
            self.assertEqual(response.status_code, 302)
            # Should redirect to login (though the endpoint doesn't exist in test)
            # The redirect will fail but we can verify the attempt was made
    
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.render_template')
    def test_session_detection_integration(self, mock_render_template, mock_has_previous_session):
        """Test that session detection is properly integrated"""
        mock_has_previous_session.return_value = False
        mock_render_template.return_value = "Landing Page"
        
        with self.client as c:
            response = c.get('/')
            
            # Verify session detection was called
            mock_has_previous_session.assert_called_once()
            # Should render landing page for new user
            mock_render_template.assert_called_with('landing.html')
    
    @patch('app.blueprints.main.routes.current_app')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.render_template')
    def test_error_handling_with_logging(self, mock_render_template, mock_has_previous_session, mock_current_app):
        """Test error handling and logging integration"""
        # Set up mock logger
        mock_logger = MagicMock()
        mock_current_app.logger = mock_logger
        
        # Make session detection raise an exception
        mock_has_previous_session.side_effect = Exception("Session detection error")
        mock_render_template.return_value = "Landing Page Fallback"
        
        with self.client as c:
            response = c.get('/')
            
            # Should log the error
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error in index route", error_call)
            
            # Should fall back to landing page
            mock_render_template.assert_called_with('landing.html')
    
    def test_route_accessibility_without_login_required(self):
        """Test that the main route is accessible without authentication"""
        with patch('app.blueprints.main.routes.render_template', return_value="Landing Page"):
            with self.client as c:
                response = c.get('/')
                
                # Should not get 401 Unauthorized or redirect to login
                self.assertNotEqual(response.status_code, 401)
                # Should get 200 OK (or 302 for redirect cases)
                self.assertIn(response.status_code, [200, 302])


if __name__ == '__main__':
    unittest.main()