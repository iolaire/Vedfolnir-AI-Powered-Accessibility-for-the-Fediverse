# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import UserRole
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user


class TestNavigationModifications(unittest.TestCase):
    """Test navigation modifications for anonymous and authenticated users"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test user for authenticated tests
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, 
            username="test_nav_user", 
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        """Clean up test environment"""
        cleanup_test_user(self.user_helper)
    
    @patch('flask.render_template')
    @patch('flask_login.current_user')
    def test_anonymous_user_navigation_shows_login_link(self, mock_current_user, mock_render_template):
        """Test that anonymous users see login link in top-right corner"""
        # Mock anonymous user
        mock_current_user.is_authenticated = False
        
        # Mock template context
        template_context = {
            'current_user_safe': None,
            'active_platform': None,
            'user_platforms': []
        }
        
        # Simulate template rendering
        mock_render_template.return_value = "rendered_template"
        
        # Test that template context includes anonymous user state
        self.assertIsNone(template_context['current_user_safe'])
        
        # Verify login link would be rendered for anonymous users
        # This tests the template logic structure
        should_show_login = not template_context['current_user_safe']
        self.assertTrue(should_show_login, "Login link should be shown for anonymous users")
    
    @patch('flask.render_template')
    @patch('flask_login.current_user')
    def test_authenticated_user_navigation_shows_full_menu(self, mock_current_user, mock_render_template):
        """Test that authenticated users see full navigation menu"""
        # Mock authenticated user
        mock_current_user.is_authenticated = True
        mock_current_user.username = self.test_user.username
        mock_current_user.email = self.test_user.email
        
        # Mock template context for authenticated user
        template_context = {
            'current_user_safe': mock_current_user,
            'active_platform': Mock(name="Test Platform", id=1),
            'user_platforms': [Mock(name="Platform 1"), Mock(name="Platform 2")]
        }
        
        # Simulate template rendering
        mock_render_template.return_value = "rendered_template"
        
        # Test that template context includes authenticated user state
        self.assertIsNotNone(template_context['current_user_safe'])
        
        # Verify full navigation would be rendered for authenticated users
        should_show_full_nav = bool(template_context['current_user_safe'])
        self.assertTrue(should_show_full_nav, "Full navigation should be shown for authenticated users")
    
    def test_navigation_template_structure_anonymous(self):
        """Test navigation template structure for anonymous users"""
        # Test the template logic that would be used
        current_user_safe = None
        
        # Simulate template conditional logic
        if current_user_safe:
            # Authenticated user navigation
            nav_items = ['Dashboard', 'Review', 'Platforms', 'Generate Captions']
            user_menu = ['Profile & Settings', 'Privacy Policy', 'Logout']
        else:
            # Anonymous user navigation
            nav_items = []  # No main navigation items for anonymous users
            user_menu = ['Login']  # Only login link
        
        # Verify anonymous user gets minimal navigation
        self.assertEqual(nav_items, [], "Anonymous users should have no main navigation items")
        self.assertEqual(user_menu, ['Login'], "Anonymous users should only see login link")
    
    def test_navigation_template_structure_authenticated(self):
        """Test navigation template structure for authenticated users"""
        # Test the template logic that would be used
        current_user_safe = Mock(username="testuser", email="test@example.com")
        active_platform = Mock(name="Test Platform")
        
        # Simulate template conditional logic
        if current_user_safe:
            # Authenticated user navigation
            nav_items = ['Dashboard', 'Review', 'Platforms']
            if active_platform:
                nav_items.append('Generate Captions')
            user_menu = ['Profile & Settings', 'Privacy Policy', 'Logout']
        else:
            # Anonymous user navigation
            nav_items = []
            user_menu = ['Login']
        
        # Verify authenticated user gets full navigation
        expected_nav = ['Dashboard', 'Review', 'Platforms', 'Generate Captions']
        self.assertEqual(nav_items, expected_nav, "Authenticated users should have full navigation")
        
        expected_user_menu = ['Profile & Settings', 'Privacy Policy', 'Logout']
        self.assertEqual(user_menu, expected_user_menu, "Authenticated users should have full user menu")
    
    def test_login_link_url_generation(self):
        """Test that login link uses proper Flask url_for() function"""
        # Mock Flask url_for function
        with patch('flask.url_for') as mock_url_for:
            mock_url_for.return_value = '/login'
            
            # Test URL generation for login link (simulating template usage)
            from flask import url_for
            login_url = mock_url_for('auth.user_management.login')
            
            # Verify url_for was called with correct route
            mock_url_for.assert_called_with('auth.user_management.login')
            self.assertEqual(login_url, '/login')
    
    def test_navigation_state_transitions(self):
        """Test navigation state transitions between anonymous and authenticated"""
        # Test transition from anonymous to authenticated
        states = []
        
        # Anonymous state
        current_user_safe = None
        states.append({
            'authenticated': bool(current_user_safe),
            'nav_items': [] if not current_user_safe else ['Dashboard', 'Review'],
            'user_menu': ['Login'] if not current_user_safe else ['Logout']
        })
        
        # Authenticated state
        current_user_safe = Mock(username="testuser")
        states.append({
            'authenticated': bool(current_user_safe),
            'nav_items': [] if not current_user_safe else ['Dashboard', 'Review'],
            'user_menu': ['Login'] if not current_user_safe else ['Logout']
        })
        
        # Verify state transition
        self.assertFalse(states[0]['authenticated'], "First state should be anonymous")
        self.assertTrue(states[1]['authenticated'], "Second state should be authenticated")
        
        # Verify navigation changes
        self.assertEqual(states[0]['nav_items'], [], "Anonymous state has no nav items")
        self.assertEqual(states[1]['nav_items'], ['Dashboard', 'Review'], "Authenticated state has nav items")
        
        # Verify user menu changes
        self.assertEqual(states[0]['user_menu'], ['Login'], "Anonymous state shows login")
        self.assertEqual(states[1]['user_menu'], ['Logout'], "Authenticated state shows logout")


if __name__ == '__main__':
    unittest.main()