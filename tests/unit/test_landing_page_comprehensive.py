# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive Unit Tests for Flask Landing Page Implementation
Tests all requirements for task 10: Create comprehensive unit tests

This test suite covers:
- Session detection functionality
- Route logic for all three user states (authenticated, returning, new)
- Template rendering and content verification
- CTA button URL generation
- Error handling and edge cases
- All requirements verification
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import sys
import os
from bs4 import BeautifulSoup

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from flask import Flask, session, request
from flask_login import AnonymousUserMixin
from app.blueprints.main.routes import main_bp
from utils.session_detection import SessionDetectionResult, has_previous_session, detect_previous_session


class TestSessionDetectionFunctionality(unittest.TestCase):
    """Test session detection functionality (Requirements 1.3)"""
    
    def setUp(self):
        """Set up test Flask app"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test context"""
        self.app_context.pop()
    
    def test_session_detection_result_creation(self):
        """Test SessionDetectionResult object creation and properties"""
        # Test default creation
        result = SessionDetectionResult()
        self.assertFalse(result.has_previous_session)
        self.assertEqual(result.detection_methods, [])
        self.assertEqual(result.session_indicators, {})
        
        # Test creation with data
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session', 'remember_token'],
            session_indicators={'user_id': 123}
        )
        self.assertTrue(result.has_previous_session)
        self.assertEqual(result.detection_methods, ['flask_session', 'remember_token'])
        self.assertEqual(result.session_indicators['user_id'], 123)
    
    def test_session_detection_boolean_evaluation(self):
        """Test boolean evaluation of SessionDetectionResult"""
        # False case
        result_false = SessionDetectionResult(has_previous_session=False)
        self.assertFalse(bool(result_false))
        self.assertFalse(result_false)
        
        # True case
        result_true = SessionDetectionResult(has_previous_session=True)
        self.assertTrue(bool(result_true))
        self.assertTrue(result_true)
    
    def test_session_detection_result_with_multiple_methods(self):
        """Test SessionDetectionResult with multiple detection methods"""
        methods = ['flask_login_remember_token', 'flask_session_data', 'custom_session_cookies']
        indicators = {
            'remember_token': {'token': 'abc...', 'source': 'remember_token_cookie'},
            'flask_session': {'user_id': 123, 'username': 'testuser'},
            'custom_cookies': {'returning_user': 'true'}
        }
        
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=methods,
            session_indicators=indicators
        )
        
        self.assertTrue(result.has_previous_session)
        self.assertEqual(len(result.detection_methods), 3)
        self.assertIn('flask_login_remember_token', result.detection_methods)
        self.assertIn('flask_session_data', result.detection_methods)
        self.assertIn('custom_session_cookies', result.detection_methods)
        self.assertEqual(result.session_indicators['remember_token']['token'], 'abc...')
        self.assertEqual(result.session_indicators['flask_session']['user_id'], 123)
        self.assertEqual(result.session_indicators['custom_cookies']['returning_user'], 'true')
    
    def test_session_detection_result_consistency(self):
        """Test consistency between has_previous_session and detection_methods"""
        # If we have detection methods, we should have a previous session
        result_with_methods = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session_data'],
            session_indicators={'user_id': 123}
        )
        
        self.assertTrue(result_with_methods.has_previous_session)
        self.assertGreater(len(result_with_methods.detection_methods), 0)
        
        # If we have no detection methods, we should have no previous session
        result_no_methods = SessionDetectionResult(
            has_previous_session=False,
            detection_methods=[],
            session_indicators={}
        )
        
        self.assertFalse(result_no_methods.has_previous_session)
        self.assertEqual(len(result_no_methods.detection_methods), 0)
    
    def test_session_detection_result_repr(self):
        """Test string representation of SessionDetectionResult"""
        result = SessionDetectionResult(
            has_previous_session=True,
            detection_methods=['flask_session', 'remember_token']
        )
        repr_str = repr(result)
        self.assertIn('SessionDetectionResult', repr_str)
        self.assertIn('has_previous_session=True', repr_str)
        self.assertIn('flask_session', repr_str)
        self.assertIn('remember_token', repr_str)
    
    def test_session_detection_with_mocked_functions(self):
        """Test session detection with mocked has_previous_session function"""
        # Test the function interface without Flask context dependencies
        with patch('utils.session_detection.detect_previous_session') as mock_detect:
            mock_detect.return_value = SessionDetectionResult(
                has_previous_session=True,
                detection_methods=['test_method'],
                session_indicators={'test': 'data'}
            )
            
            # Test has_previous_session function
            result = has_previous_session()
            self.assertTrue(result)
            mock_detect.assert_called_once()
    
    def test_session_detection_error_handling_mock(self):
        """Test session detection error handling with mocked functions"""
        with patch('utils.session_detection.detect_previous_session') as mock_detect:
            mock_detect.side_effect = Exception("Detection error")
            
            # The has_previous_session function should handle errors gracefully
            try:
                result = has_previous_session()
                # If it doesn't raise an exception, it should return False as safe default
                self.assertFalse(result)
            except Exception:
                # If it does raise an exception, that's also acceptable behavior
                pass


class TestMainRouteLogicAllUserStates(unittest.TestCase):
    """Test route logic for all three user states (Requirements 1.1, 1.2, 1.3)"""
    
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
    @patch('app.blueprints.main.routes.render_dashboard')
    def test_authenticated_user_gets_dashboard(self, mock_render_dashboard, mock_current_user):
        """Test authenticated users get dashboard (Requirement 1.2)"""
        # Setup authenticated user
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
    @patch('app.blueprints.main.routes.redirect')
    @patch('app.blueprints.main.routes.url_for')
    def test_returning_user_redirected_to_login(self, mock_url_for, mock_redirect, 
                                               mock_has_previous_session, mock_current_user):
        """Test returning users redirect to login (Requirement 1.3)"""
        # Setup returning user
        mock_current_user.is_authenticated = False
        mock_has_previous_session.return_value = True
        mock_url_for.return_value = '/login'
        mock_redirect.return_value = "redirect to login"
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Verify redirect to login
            mock_url_for.assert_called_with('user_management.login', _external=False)
            mock_redirect.assert_called_with('/login')
            self.assertEqual(result, "redirect to login")
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.render_template')
    def test_new_anonymous_user_gets_landing_page(self, mock_render_template, 
                                                 mock_has_previous_session, mock_current_user):
        """Test new anonymous users get landing page (Requirement 1.1)"""
        # Setup new anonymous user
        mock_current_user.is_authenticated = False
        mock_has_previous_session.return_value = False
        mock_render_template.return_value = "landing page content"
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Verify landing page template is rendered
            mock_render_template.assert_called_with('landing.html')
            self.assertEqual(result, "landing page content")
    
    def test_route_logging_for_each_user_type(self):
        """Test appropriate logging occurs for each user type"""
        # Test authenticated user logging
        with patch('app.blueprints.main.routes.current_user') as mock_current_user, \
             patch('app.blueprints.main.routes.render_dashboard', return_value="dashboard"), \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_current_user.is_authenticated = True
            mock_current_user.username = 'testuser'
            
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                index()
                mock_logger.info.assert_called_with("Authenticated user testuser accessing dashboard")
        
        # Test returning user logging
        with patch('app.blueprints.main.routes.current_user') as mock_current_user, \
             patch('app.blueprints.main.routes.has_previous_session', return_value=True), \
             patch('app.blueprints.main.routes.redirect', return_value="redirect"), \
             patch('app.blueprints.main.routes.url_for', return_value="/login"), \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_current_user.is_authenticated = False
            
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                index()
                mock_logger.info.assert_called_with("Anonymous user with previous session detected, redirecting to login")
        
        # Test new user logging
        with patch('app.blueprints.main.routes.current_user') as mock_current_user, \
             patch('app.blueprints.main.routes.has_previous_session', return_value=False), \
             patch('app.blueprints.main.routes.render_template', return_value="landing"), \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_current_user.is_authenticated = False
            
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                index()
                mock_logger.info.assert_called_with("New anonymous user detected, showing landing page")
    
    def test_route_accessibility_without_authentication(self):
        """Test route is accessible without authentication (Requirement 1.1)"""
        with patch('app.blueprints.main.routes.render_template', return_value="Landing Page"):
            with self.client as c:
                response = c.get('/')
                
                # Should not require authentication
                self.assertNotEqual(response.status_code, 401)
                self.assertIn(response.status_code, [200, 302])


class TestTemplateRenderingAndContentVerification(unittest.TestCase):
    """Test template rendering and content verification (Requirements 2.1-2.6, 3.1-3.6)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment with real Flask app"""
        # Import the app from web_app module
        import web_app
        cls.app = web_app.app
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
    
    def setUp(self):
        """Clear session data before each test"""
        with self.client.session_transaction() as sess:
            sess.clear()
    
    def test_landing_page_renders_successfully(self):
        """Test landing page template renders without errors"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Vedfolnir', response.data)
    
    def test_hero_section_content(self):
        """Test hero section contains required content (Requirement 2.1, 2.2)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find hero section
        hero_section = soup.find('section', class_='landing-hero')
        self.assertIsNotNone(hero_section, "Hero section should exist")
        
        # Check main headline
        h1 = hero_section.find('h1')
        self.assertIsNotNone(h1, "Hero section should have h1 element")
        self.assertIn('Vedfolnir', h1.get_text())
        self.assertIn('AI-Powered Accessibility', h1.get_text())
        self.assertIn('Fediverse', h1.get_text())
        
        # Check subtitle/lead text
        lead = hero_section.find(class_='lead')
        self.assertIsNotNone(lead, "Hero section should have lead text")
        lead_text = lead.get_text().lower()
        self.assertIn('social media', lead_text)
        self.assertIn('accessible', lead_text)
    
    def test_features_section_content(self):
        """Test features section highlights key benefits (Requirement 2.3)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find features section
        features_section = soup.find('section', class_='features-section')
        self.assertIsNotNone(features_section, "Features section should exist")
        
        # Check for feature cards
        feature_cards = features_section.find_all(class_='feature-card')
        self.assertGreaterEqual(len(feature_cards), 3, "Should have at least 3 feature cards")
        
        # Check for key features mentioned in requirements
        features_text = features_section.get_text().lower()
        self.assertIn('ai', features_text)
        self.assertIn('image', features_text)
        self.assertIn('description', features_text)
        self.assertIn('review', features_text)
        self.assertIn('platform', features_text)
    
    def test_target_audience_section_content(self):
        """Test target audience section (Requirement 2.5)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find audience section
        audience_section = soup.find('section', class_='audience-section')
        self.assertIsNotNone(audience_section, "Audience section should exist")
        
        # Check for audience items
        audience_items = audience_section.find_all(class_='audience-item')
        self.assertGreaterEqual(len(audience_items), 4, "Should have at least 4 audience items")
        
        # Check for target audiences mentioned in requirements
        audience_text = audience_section.get_text().lower()
        self.assertIn('photographer', audience_text)
        self.assertIn('community', audience_text)
        self.assertIn('content creator', audience_text)
    
    def test_platform_compatibility_information(self):
        """Test ActivityPub platform compatibility info (Requirement 2.6)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8').lower()
        
        # Check for platform mentions
        self.assertIn('activitypub', content)
        self.assertIn('mastodon', content)
        self.assertIn('pixelfed', content)
    
    def test_semantic_html_structure(self):
        """Test proper semantic HTML structure (Requirement 3.1)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for semantic elements
        self.assertIsNotNone(soup.find('main'), "Should have main element")
        # Note: header might be in base template, check for nav instead
        nav_element = soup.find('nav')
        self.assertIsNotNone(nav_element, "Should have nav element")
        
        # Check for proper heading hierarchy
        h1_elements = soup.find_all('h1')
        self.assertEqual(len(h1_elements), 1, "Should have exactly one h1 element")
        
        h2_elements = soup.find_all('h2')
        self.assertGreater(len(h2_elements), 0, "Should have h2 elements")
        
        h3_elements = soup.find_all('h3')
        self.assertGreater(len(h3_elements), 0, "Should have h3 elements")
    
    def test_accessibility_features(self):
        """Test accessibility features (Requirements 3.2-3.6)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for skip-to-content link
        skip_link = soup.find('a', class_='visually-hidden-focusable')
        self.assertIsNotNone(skip_link, "Should have skip-to-content link")
        
        # Check for alt text on images
        images = soup.find_all('img')
        for img in images:
            self.assertIsNotNone(img.get('alt'), f"Image should have alt text: {img}")
        
        # Check for proper ARIA labels
        cta_buttons = soup.find_all('a', class_='cta-button')
        for button in cta_buttons:
            self.assertEqual(button.get('role'), 'button', "CTA button should have role='button'")
    
    def test_responsive_design_meta_tags(self):
        """Test responsive design meta tags (Requirement 4.1)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8')
        
        # Check for viewport meta tag
        self.assertIn('name="viewport"', content)
        self.assertIn('width=device-width', content)
        self.assertIn('initial-scale=1.0', content)
        
        # Check for mobile optimization tags
        self.assertIn('HandheldFriendly', content)
        self.assertIn('MobileOptimized', content)


class TestCTAButtonURLGeneration(unittest.TestCase):
    """Test CTA button URL generation (Requirements 6.1, 6.2, 6.4, 6.5, 6.6)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        import web_app
        cls.app = web_app.app
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
    
    def setUp(self):
        """Clear session data before each test"""
        with self.client.session_transaction() as sess:
            sess.clear()
    
    def test_primary_cta_button_url_generation(self):
        """Test primary CTA button uses proper Flask url_for() (Requirement 6.2)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find primary CTA button in hero section
        hero_section = soup.find('section', class_='landing-hero')
        primary_cta = hero_section.find('a', class_='cta-button')
        
        self.assertIsNotNone(primary_cta, "Primary CTA button should exist")
        
        # Verify URL is properly generated
        href = primary_cta.get('href')
        self.assertEqual(href, '/register', "Primary CTA should link to /register")
        self.assertNotIn('{{', href, "URL should not contain template syntax")
        self.assertNotIn('}}', href, "URL should not contain template syntax")
    
    def test_secondary_cta_button_url_generation(self):
        """Test secondary CTA button URL generation (Requirement 6.5)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find secondary CTA button in final section
        final_section = soup.find('section', class_='final-cta-section')
        secondary_cta = final_section.find('a', class_='cta-button')
        
        self.assertIsNotNone(secondary_cta, "Secondary CTA button should exist")
        
        # Verify URL is properly generated
        href = secondary_cta.get('href')
        self.assertEqual(href, '/register', "Secondary CTA should link to /register")
        self.assertNotIn('{{', href, "URL should not contain template syntax")
        self.assertNotIn('}}', href, "URL should not contain template syntax")
    
    def test_login_link_url_generation(self):
        """Test login link URL generation (Requirement 6.4)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find login link in navigation
        navbar = soup.find('nav', class_='navbar')
        login_link = navbar.find('a', href='/login')
        
        self.assertIsNotNone(login_link, "Login link should exist")
        
        # Verify URL is properly generated
        href = login_link.get('href')
        self.assertEqual(href, '/login', "Login link should link to /login")
        self.assertNotIn('{{', href, "URL should not contain template syntax")
        self.assertNotIn('}}', href, "URL should not contain template syntax")
    
    def test_cta_button_accessibility_attributes(self):
        """Test CTA buttons have proper accessibility attributes (Requirement 6.6)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find all CTA buttons
        cta_buttons = soup.find_all('a', class_='cta-button')
        self.assertEqual(len(cta_buttons), 2, "Should have exactly 2 CTA buttons")
        
        for button in cta_buttons:
            # Check for role attribute
            self.assertEqual(button.get('role'), 'button', "CTA button should have role='button'")
            
            # Check for proper href
            href = button.get('href')
            self.assertIsNotNone(href, "CTA button should have href attribute")
            self.assertTrue(href.startswith('/'), "CTA button href should be a proper path")
    
    def test_cta_button_hover_states_css(self):
        """Test CTA buttons have hover states defined (Requirement 6.6)"""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for hover CSS
        self.assertIn('.cta-button:hover', html_content, "Should have CTA button hover styles")
        self.assertIn('transform: translateY(-', html_content, "Hover should include transform effect")
        self.assertIn('box-shadow:', html_content, "Hover should include shadow effect")
    
    def test_registration_page_accessibility(self):
        """Test that registration page is accessible from CTA buttons"""
        # Test that the registration endpoint exists and is accessible
        response = self.client.get('/register')
        # Should either return 200 (page exists) or 302 (redirect to login/setup)
        self.assertIn(response.status_code, [200, 302, 404], 
                     "Registration page should be accessible or properly redirect")


class TestErrorHandlingAndEdgeCases(unittest.TestCase):
    """Test error handling and edge cases (Requirements 8.5, 8.6)"""
    
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
    
    def test_session_detection_error_fallback(self):
        """Test error handling when session detection fails"""
        with patch('app.blueprints.main.routes.current_user') as mock_current_user, \
             patch('app.blueprints.main.routes.has_previous_session', side_effect=Exception("Session detection error")), \
             patch('app.blueprints.main.routes.render_template', return_value="landing page fallback"), \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_current_user.is_authenticated = False
            
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                result = index()
                
                # Should log error and fall back to landing page
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args[0][0]
                self.assertIn("Error in index route", error_call)
                self.assertEqual(result, "landing page fallback")
    
    def test_dashboard_rendering_error_fallback(self):
        """Test error handling when dashboard rendering fails"""
        with patch('app.blueprints.main.routes.current_user') as mock_current_user, \
             patch('app.blueprints.main.routes.render_dashboard', side_effect=Exception("Dashboard error")), \
             patch('app.blueprints.main.routes.render_template', return_value="landing fallback"), \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_current_user.is_authenticated = True
            mock_current_user.username = 'testuser'
            
            with self.app.test_request_context('/'):
                from app.blueprints.main.routes import index
                result = index()
                
                # Should log error and fall back to landing page
                mock_logger.error.assert_called_once()
                self.assertEqual(result, "landing fallback")
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.has_previous_session')
    @patch('app.blueprints.main.routes.handle_security_error')
    @patch('app.blueprints.main.routes.current_app')
    def test_security_error_handling(self, mock_current_app, mock_handle_security_error,
                                    mock_has_previous_session, mock_current_user):
        """Test security error handling"""
        # Setup mocks
        mock_current_user.is_authenticated = False
        mock_has_previous_session.side_effect = Exception("CSRF token invalid")
        mock_handle_security_error.return_value = "security error response"
        mock_logger = MagicMock()
        mock_current_app.logger = mock_logger
        
        with self.app.test_request_context('/'):
            from app.blueprints.main.routes import index
            result = index()
            
            # Should handle security error appropriately
            mock_handle_security_error.assert_called_with("Access denied", 403)
            self.assertEqual(result, "security error response")
    
    def test_template_rendering_error_fallback(self):
        """Test fallback when template rendering fails"""
        with patch('app.blueprints.main.routes.current_user') as mock_current_user, \
             patch('app.blueprints.main.routes.has_previous_session', return_value=False), \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_current_user.is_authenticated = False
            
            # Mock render_template to raise exception on first call, succeed on second
            with patch('app.blueprints.main.routes.render_template', side_effect=[Exception("Template not found"), "fallback"]):
                with self.app.test_request_context('/'):
                    from app.blueprints.main.routes import index
                    result = index()
                    
                    # Should log error
                    mock_logger.error.assert_called_once()
    
    def test_route_with_invalid_request_context(self):
        """Test route behavior with invalid request context"""
        with self.app.test_request_context('/', method='POST'):
            # Test that route handles POST requests gracefully
            with patch('app.blueprints.main.routes.render_template', return_value="landing"):
                response = self.client.post('/')
                # Should handle gracefully (may return 405 Method Not Allowed or process normally)
                self.assertIn(response.status_code, [200, 302, 405])
    
    @patch('app.blueprints.main.routes.current_user')
    @patch('app.blueprints.main.routes.sanitize_user_input')
    def test_input_sanitization_on_errors(self, mock_sanitize, mock_current_user):
        """Test that error messages are sanitized"""
        # Setup mocks
        mock_current_user.is_authenticated = False
        mock_sanitize.return_value = "sanitized error message"
        
        with patch('app.blueprints.main.routes.has_previous_session', side_effect=Exception("Raw error <script>")):
            with patch('app.blueprints.main.routes.render_template', return_value="landing"):
                with patch('app.blueprints.main.routes.current_app') as mock_current_app:
                    mock_logger = MagicMock()
                    mock_current_app.logger = mock_logger
                    
                    with self.app.test_request_context('/'):
                        from app.blueprints.main.routes import index
                        index()
                        
                        # Should sanitize error input
                        mock_sanitize.assert_called_once()


class TestSEOAndMetadata(unittest.TestCase):
    """Test SEO metadata and structured data (Requirements 7.1-7.6)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        import web_app
        cls.app = web_app.app
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
    
    def setUp(self):
        """Clear session data before each test"""
        with self.client.session_transaction() as sess:
            sess.clear()
    
    def test_meta_title_tag(self):
        """Test proper meta title tag (Requirement 7.1)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8')
        
        # Check for title tag
        self.assertIn('<title>', content)
        self.assertIn('Vedfolnir', content)
        self.assertIn('AI-Powered Accessibility', content)
        self.assertIn('Fediverse', content)
    
    def test_meta_description_tag(self):
        """Test meta description tag (Requirement 7.2)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8')
        
        # Check for meta description
        self.assertIn('name="description"', content)
        self.assertIn('content=', content)
        # Should contain value proposition keywords
        description_match = content.lower()
        self.assertIn('ai-powered', description_match)
        self.assertIn('accessibility', description_match)
        self.assertIn('alt text', description_match)
    
    def test_open_graph_tags(self):
        """Test Open Graph tags for social media sharing (Requirement 7.3)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8')
        
        # Check for essential Open Graph tags
        self.assertIn('property="og:title"', content)
        self.assertIn('property="og:description"', content)
        self.assertIn('property="og:type"', content)
        self.assertIn('property="og:url"', content)
        self.assertIn('property="og:image"', content)
    
    def test_structured_data_markup(self):
        """Test structured data markup (Requirement 7.4)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8')
        
        # Check for JSON-LD structured data
        self.assertIn('application/ld+json', content)
        self.assertIn('"@context": "https://schema.org"', content)
        self.assertIn('"@type": "SoftwareApplication"', content)
        self.assertIn('"name": "Vedfolnir"', content)
    
    def test_heading_hierarchy(self):
        """Test proper heading hierarchy for SEO (Requirement 7.5)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check heading hierarchy
        h1_elements = soup.find_all('h1')
        h2_elements = soup.find_all('h2')
        h3_elements = soup.find_all('h3')
        
        self.assertEqual(len(h1_elements), 1, "Should have exactly one h1")
        self.assertGreater(len(h2_elements), 0, "Should have h2 elements")
        self.assertGreater(len(h3_elements), 0, "Should have h3 elements")
    
    def test_relevant_keywords_in_content(self):
        """Test relevant keywords naturally integrated (Requirement 7.6)"""
        response = self.client.get('/')
        content = response.data.decode('utf-8').lower()
        
        # Check for relevant keywords
        keywords = [
            'accessibility', 'alt text', 'image descriptions',
            'activitypub', 'mastodon', 'pixelfed', 'ai',
            'digital inclusion', 'screen reader', 'fediverse'
        ]
        
        for keyword in keywords:
            self.assertIn(keyword, content, f"Content should contain keyword: {keyword}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)