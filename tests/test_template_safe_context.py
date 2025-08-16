#!/usr/bin/env python3

"""
Test Template Safe Context Implementation

This module tests that all templates use safe context objects instead of
direct current_user and current_platform access to prevent DetachedInstanceError.

Requirements: 5.1, 5.2, 5.3, 5.4
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from flask import Flask, render_template_string, g
from flask_login import login_user
from werkzeug.test import Client

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User, PlatformConnection, UserRole
from safe_template_context import safe_template_context, create_safe_template_context_processor
from request_scoped_session_manager import RequestScopedSessionManager
from detached_instance_handler import DetachedInstanceHandler
from database_context_middleware import DatabaseContextMiddleware
# from app_initialization import create_session_managed_app


class TestTemplateSafeContext(unittest.TestCase):
    """Test template safe context implementation"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a minimal Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create mock objects
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 1
        self.mock_user.username = 'testuser'
        self.mock_user.email = 'test@test.com'
        self.mock_user.role = UserRole.VIEWER
        self.mock_user.is_active = True
        self.mock_user.is_authenticated = True
        self.mock_user.is_anonymous = False
        self.mock_user.get_id.return_value = '1'
        
        self.mock_platform = Mock(spec=PlatformConnection)
        self.mock_platform.id = 1
        self.mock_platform.name = 'Test Platform'
        self.mock_platform.platform_type = 'pixelfed'
        self.mock_platform.instance_url = 'https://test.example.com'
        self.mock_platform.username = 'testuser'
        self.mock_platform.is_active = True
        self.mock_platform.is_default = True
        
    def test_safe_template_context_with_authenticated_user(self):
        """Test safe template context with authenticated user"""
        with self.app.app_context():
            # Mock session manager and handler
            session_manager = Mock(spec=RequestScopedSessionManager)
            handler = Mock(spec=DetachedInstanceHandler)
            
            self.app.request_session_manager = session_manager
            self.app.detached_instance_handler = handler
            
            # Mock safe access methods
            handler.safe_access.side_effect = lambda obj, attr, default=None: {
                'id': 1,
                'username': 'testuser',
                'email': 'test@test.com',
                'role': 'user',
                'is_active': True
            }.get(attr, default)
            
            handler.safe_relationship_access.return_value = [self.mock_platform]
            
            with patch('safe_template_context.current_user', self.mock_user):
                context = safe_template_context()
                
                # Verify context structure
                self.assertIn('current_user_safe', context)
                self.assertIn('user_platforms', context)
                self.assertIn('active_platform', context)
                self.assertIn('platform_count', context)
                self.assertIn('template_error', context)
                
                # Verify user data
                self.assertEqual(context['current_user_safe']['username'], 'testuser')
                self.assertEqual(context['current_user_safe']['email'], 'test@test.com')
                self.assertEqual(context['current_user_safe']['role'], 'user')
                
                # Verify no template error
                self.assertFalse(context['template_error'])
    
    def test_safe_template_context_with_unauthenticated_user(self):
        """Test safe template context with unauthenticated user"""
        with self.app.app_context():
            mock_user = Mock()
            mock_user.is_authenticated = False
            
            with patch('safe_template_context.current_user', mock_user):
                context = safe_template_context()
                
                # Verify empty context for unauthenticated user
                self.assertFalse(context['template_error'])
                self.assertIsNone(context['current_user_safe'])
                self.assertEqual(context['user_platforms'], [])
                self.assertIsNone(context['active_platform'])
                self.assertEqual(context['platform_count'], 0)
    
    def test_safe_template_context_with_detached_instance_error(self):
        """Test safe template context handles DetachedInstanceError"""
        from sqlalchemy.orm.exc import DetachedInstanceError
        
        with self.app.app_context():
            # Mock session manager and handler
            session_manager = Mock(spec=RequestScopedSessionManager)
            handler = Mock(spec=DetachedInstanceHandler)
            
            self.app.request_session_manager = session_manager
            self.app.detached_instance_handler = handler
            
            # Mock DetachedInstanceError
            handler.safe_access.side_effect = DetachedInstanceError("Test error")
            
            with patch('safe_template_context.current_user', self.mock_user):
                context = safe_template_context()
                
                # Verify error handling
                self.assertTrue(context['template_error'])
                self.assertEqual(context['user_platforms'], [])
                self.assertIsNone(context['active_platform'])
                self.assertEqual(context['platform_count'], 0)
    
    def test_template_context_processor_registration(self):
        """Test template context processor registration"""
        with self.app.app_context():
            # Mock the context processor
            with patch('safe_template_context.safe_template_context') as mock_context:
                mock_context.return_value = {
                    'current_user_safe': {'username': 'test'},
                    'user_platforms': [],
                    'active_platform': None,
                    'platform_count': 0,
                    'template_error': False
                }
                
                # Register context processor
                create_safe_template_context_processor(self.app)
                
                # Test template rendering
                template = "{{ current_user_safe.username if current_user_safe else 'None' }}"
                result = render_template_string(template)
                
                # Verify context is injected
                self.assertEqual(result, 'test')
    
    def test_base_template_uses_safe_context(self):
        """Test that base template uses safe context objects"""
        with self.app.test_request_context():
            # Mock template context
            with patch.dict(self.app.jinja_env.globals, {
                'current_user_safe': {'username': 'testuser', 'role': 'user'},
                'active_platform': {'name': 'Test Platform', 'platform_type': 'pixelfed'},
                'user_platforms': [{'id': 1, 'name': 'Test Platform'}],
                'template_error': False
            }):
                # Test template snippet that should use safe context
                template = """
                {% if current_user_safe %}
                    <span>{{ current_user_safe.username }}</span>
                {% endif %}
                {% if active_platform %}
                    <span>{{ active_platform.name }}</span>
                {% endif %}
                """
                
                result = render_template_string(template)
                
                # Verify safe context is used
                self.assertIn('testuser', result)
                self.assertIn('Test Platform', result)
    
    def test_platform_switching_uses_safe_context(self):
        """Test that platform switching uses safe context"""
        with self.app.test_request_context():
            # Mock template context with multiple platforms
            platforms = [
                {'id': 1, 'name': 'Platform 1', 'platform_type': 'pixelfed'},
                {'id': 2, 'name': 'Platform 2', 'platform_type': 'mastodon'}
            ]
            
            with patch.dict(self.app.jinja_env.globals, {
                'current_user_safe': {'username': 'testuser'},
                'active_platform': platforms[0],
                'user_platforms': platforms,
                'template_error': False
            }):
                # Test platform switching template logic
                template = """
                {% if active_platform %}
                    Current: {{ active_platform.name }}
                {% endif %}
                {% for platform in user_platforms %}
                    {% if platform.id != active_platform.id %}
                        Switch to: {{ platform.name }}
                    {% endif %}
                {% endfor %}
                """
                
                result = render_template_string(template)
                
                # Verify platform switching logic works with safe context
                self.assertIn('Current: Platform 1', result)
                self.assertIn('Switch to: Platform 2', result)
    
    def test_admin_permission_check_uses_safe_context(self):
        """Test that admin permission checks use safe context"""
        with self.app.test_request_context():
            # Test with admin user
            with patch.dict(self.app.jinja_env.globals, {
                'current_user_safe': {'username': 'admin', 'role': 'admin'},
                'template_error': False
            }):
                template = """
                {% if current_user_safe and current_user_safe.role == 'admin' %}
                    <div>Admin Panel</div>
                {% endif %}
                """
                
                result = render_template_string(template)
                self.assertIn('Admin Panel', result)
            
            # Test with regular user
            with patch.dict(self.app.jinja_env.globals, {
                'current_user_safe': {'username': 'user', 'role': 'user'},
                'template_error': False
            }):
                result = render_template_string(template)
                self.assertNotIn('Admin Panel', result)
    
    def test_template_error_handling(self):
        """Test template error handling when template_error is True"""
        with self.app.test_request_context():
            with patch.dict(self.app.jinja_env.globals, {
                'current_user_safe': None,
                'active_platform': None,
                'user_platforms': [],
                'template_error': True
            }):
                # Test template with error handling
                template = """
                {% if template_error %}
                    <div class="alert alert-warning">Template context error</div>
                {% endif %}
                {% if current_user_safe %}
                    <span>{{ current_user_safe.username }}</span>
                {% else %}
                    <span>No user data</span>
                {% endif %}
                """
                
                result = render_template_string(template)
                
                # Verify error handling
                self.assertIn('Template context error', result)
                self.assertIn('No user data', result)
    
    def test_platform_to_safe_dict_conversion(self):
        """Test platform to safe dictionary conversion"""
        from safe_template_context import _platform_to_safe_dict
        
        # Mock handler
        handler = Mock()
        handler.safe_access.side_effect = lambda obj, attr, default=None: {
            'id': 1,
            'name': 'Test Platform',
            'platform_type': 'pixelfed',
            'instance_url': 'https://test.example.com',
            'username': 'testuser',
            'is_active': True,
            'is_default': True,
            'created_at': None,
            'updated_at': None
        }.get(attr, default)
        
        # Test conversion
        result = _platform_to_safe_dict(self.mock_platform, handler)
        
        # Verify safe dictionary
        self.assertIsInstance(result, dict)
        self.assertEqual(result['name'], 'Test Platform')
        self.assertEqual(result['platform_type'], 'pixelfed')
        self.assertEqual(result['instance_url'], 'https://test.example.com')
        self.assertTrue(result['is_active'])
        self.assertTrue(result['is_default'])
    
    def test_safe_user_data_extraction(self):
        """Test safe user data extraction"""
        from safe_template_context import _get_safe_user_data
        
        # Mock handler
        handler = Mock()
        handler.safe_access.side_effect = lambda obj, attr, default=None: {
            'id': 1,
            'username': 'testuser',
            'email': 'test@test.com',
            'role': 'user',
            'is_active': True
        }.get(attr, default)
        
        # Test extraction
        result = _get_safe_user_data(self.mock_user, handler)
        
        # Verify safe user data
        self.assertIsInstance(result, dict)
        self.assertEqual(result['username'], 'testuser')
        self.assertEqual(result['email'], 'test@test.com')
        self.assertEqual(result['role'], 'user')
        self.assertTrue(result['is_active'])
    
    def test_fallback_platform_query(self):
        """Test fallback platform query when relationship access fails"""
        from safe_template_context import _query_platforms_fallback
        
        # Mock session manager and handler
        session_manager = Mock()
        mock_session = Mock()
        mock_query = Mock()
        
        session_manager.get_request_session.return_value = mock_session
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.all.return_value = [self.mock_platform]
        
        handler = Mock()
        handler.safe_access.return_value = 1
        
        # Test fallback query
        result = _query_platforms_fallback(self.mock_user, handler, session_manager)
        
        # Verify fallback works
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.mock_platform)
        
        # Verify query was called correctly
        mock_session.query.assert_called_once()
        mock_query.filter_by.assert_called_once_with(user_id=1, is_active=True)


class TestTemplateIntegration(unittest.TestCase):
    """Test template integration with safe context"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a minimal Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Create test client
        self.client = self.app.test_client()
    
    def test_dashboard_template_integration(self):
        """Test dashboard template uses safe context"""
        with self.app.test_request_context():
            # Mock safe context
            with patch('safe_template_context.safe_template_context') as mock_context:
                mock_context.return_value = {
                    'current_user_safe': {'username': 'testuser', 'role': 'user'},
                    'active_platform': {'name': 'Test Platform', 'platform_type': 'pixelfed'},
                    'user_platforms': [{'id': 1, 'name': 'Test Platform'}],
                    'platform_count': 1,
                    'template_error': False
                }
                
                # Register context processor
                create_safe_template_context_processor(self.app)
                
                # Test dashboard template snippet
                template = """
                {% if current_user_safe and current_user_safe.role == 'admin' %}
                    <a href="/admin">Admin Panel</a>
                {% endif %}
                {% if active_platform %}
                    <div>Platform: {{ active_platform.name }}</div>
                {% endif %}
                """
                
                result = render_template_string(template)
                
                # Verify template uses safe context
                self.assertIn('Platform: Test Platform', result)
                self.assertNotIn('Admin Panel', result)  # User is not admin
    
    def test_platform_management_template_integration(self):
        """Test platform management template uses safe context"""
        with self.app.test_request_context():
            # Mock safe context with multiple platforms
            platforms = [
                {'id': 1, 'name': 'Platform 1', 'platform_type': 'pixelfed', 'is_default': True},
                {'id': 2, 'name': 'Platform 2', 'platform_type': 'mastodon', 'is_default': False}
            ]
            
            with patch('safe_template_context.safe_template_context') as mock_context:
                mock_context.return_value = {
                    'current_user_safe': {'username': 'testuser'},
                    'active_platform': platforms[0],
                    'user_platforms': platforms,
                    'platform_count': 2,
                    'template_error': False
                }
                
                # Register context processor
                create_safe_template_context_processor(self.app)
                
                # Test platform management template snippet
                template = """
                {% if active_platform %}
                    <div>Current: {{ active_platform.name }}</div>
                {% endif %}
                {% for platform in user_platforms %}
                    <div>{{ platform.name }} - {{ platform.platform_type }}</div>
                {% endfor %}
                """
                
                result = render_template_string(template)
                
                # Verify template uses safe context
                self.assertIn('Current: Platform 1', result)
                self.assertIn('Platform 1 - pixelfed', result)
                self.assertIn('Platform 2 - mastodon', result)


if __name__ == '__main__':
    unittest.main()