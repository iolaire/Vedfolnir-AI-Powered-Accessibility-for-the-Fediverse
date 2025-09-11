# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask
from flask_login import AnonymousUserMixin
from app.blueprints.main.routes import main_bp


class TestMainRouteLogic(unittest.TestCase):
    """Test the three-way logic in the main route handler"""
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app.register_blueprint(main_bp)
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test context"""
        self.app_context.pop()
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.render_template')
    def test_new_anonymous_user_gets_landing_page(self, mock_render_template, mock_has_previous_session, mock_current_user):
        """Test that completely new anonymous users get the landing page"""
        # Setup mocks
        mock_current_user.is_authenticated = False
        mock_has_previous_session.return_value = False
        mock_render_template.return_value = "landing page content"
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Verify landing page template is rendered
            mock_render_template.assert_called_with('landing.html')
            self.assertEqual(result, "landing page content")
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.redirect')
    @patch('app.blueprints.main.routes.url_for')
    def test_returning_user_redirected_to_login(self, mock_url_for, mock_redirect, mock_has_previous_session, mock_current_user):
        """Test that users with previous session are redirected to login"""
        # Setup mocks
        mock_current_user.is_authenticated = False
        mock_has_previous_session.return_value = True
        mock_url_for.return_value = '/login'
        mock_redirect.return_value = "redirect to login"
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Verify redirect to login
            mock_url_for.assert_called_with('auth.user_management.login')
            mock_redirect.assert_called_with('/login')
            self.assertEqual(result, "redirect to login")
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.render_dashboard')
    def test_authenticated_user_gets_dashboard(self, mock_render_dashboard, mock_current_user):
        """Test that authenticated users get the dashboard"""
        # Setup mocks
        mock_current_user.is_authenticated = True
        mock_current_user.username = 'testuser'
        mock_render_dashboard.return_value = "dashboard content"
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Verify dashboard is rendered
            mock_render_dashboard.assert_called_once()
            self.assertEqual(result, "dashboard content")
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.render_template')
    @patch('app.blueprints.main.routes.current_app')
    def test_error_handling_fallback_to_landing(self, mock_current_app, mock_render_template, mock_has_previous_session, mock_current_user):
        """Test that errors fall back to landing page"""
        # Setup mocks to raise exception
        mock_current_user.is_authenticated = False
        mock_has_previous_session.side_effect = Exception("Test error")
        mock_render_template.return_value = "landing page fallback"
        mock_logger = MagicMock()
        mock_current_app.logger = mock_logger
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Verify error is logged and landing page is shown
            mock_logger.error.assert_called_once()
            mock_render_template.assert_called_with('landing.html')
            self.assertEqual(result, "landing page fallback")
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.current_app')
    def test_logging_for_each_user_type(self, mock_current_app, mock_has_previous_session, mock_current_user):
        """Test that appropriate logging occurs for each user type"""
        mock_logger = MagicMock()
        mock_current_app.logger = mock_logger
        
        # Test authenticated user logging
        mock_current_user.is_authenticated = True
        mock_current_user.username = 'testuser'
        
        with patch('app.blueprints.main.routes.render_dashboard', return_value="dashboard"):
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                index()
                mock_logger.info.assert_called_with("Authenticated user testuser accessing dashboard")
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test returning user logging
        mock_current_user.is_authenticated = False
        mock_has_previous_session.return_value = True
        
        with patch('app.blueprints.main.routes.redirect', return_value="redirect"), \
             patch('app.blueprints.main.routes.url_for', return_value="/login"):
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                index()
                mock_logger.info.assert_called_with("Anonymous user with previous session detected, redirecting to login")
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test new user logging
        mock_has_previous_session.return_value = False
        
        with patch('app.blueprints.main.routes.render_template', return_value="landing"):
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                index()
                mock_logger.info.assert_called_with("New anonymous user detected, showing landing page")


if __name__ == '__main__':
    unittest.main()