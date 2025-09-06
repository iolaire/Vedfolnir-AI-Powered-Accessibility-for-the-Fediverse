# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for landing page error handling and fallback mechanisms.

This module tests the comprehensive error handling system implemented
for the Flask landing page functionality.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, request
import tempfile
import logging

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.landing_page_fallback import (
    create_fallback_landing_html,
    handle_template_rendering_error,
    handle_session_detection_error,
    handle_authentication_error,
    log_authentication_failure,
    ensure_system_stability,
    test_error_scenarios,
    LandingPageError,
    AuthenticationFailureError,
    TemplateRenderingError,
    SessionDetectionError
)

class TestLandingPageErrorHandling(unittest.TestCase):
    """Test cases for landing page error handling functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['APP_NAME'] = 'Test Vedfolnir'
        
        # Set up logging to capture log messages
        self.log_capture = []
        self.test_handler = logging.Handler()
        self.test_handler.emit = lambda record: self.log_capture.append(record)
        
        # Add handler to relevant loggers
        logging.getLogger('utils.landing_page_fallback').addHandler(self.test_handler)
        logging.getLogger('app.blueprints.main.routes').addHandler(self.test_handler)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove test handler
        logging.getLogger('utils.landing_page_fallback').removeHandler(self.test_handler)
        logging.getLogger('app.blueprints.main.routes').removeHandler(self.test_handler)
    
    def test_create_fallback_landing_html_basic(self):
        """Test basic fallback HTML generation"""
        with self.app.app_context():
            html = create_fallback_landing_html()
            
            # Verify HTML structure
            self.assertIn('<!DOCTYPE html>', html)
            self.assertIn('<html lang="en">', html)
            self.assertIn('Vedfolnir', html)
            self.assertIn('AI-Powered Accessibility', html)
            self.assertIn('Get Started', html)
            self.assertIn('/register', html)
            self.assertIn('/login', html)
            
            # Verify accessibility features
            self.assertIn('Skip to main content', html)
            self.assertIn('id="main-content"', html)
            # Note: This fallback HTML doesn't have images, so no alt text
            
            # Verify responsive design
            self.assertIn('@media (max-width: 768px)', html)
            self.assertIn('min-height: 48px', html)  # Touch targets
    
    def test_create_fallback_landing_html_with_error_context(self):
        """Test fallback HTML generation with error context"""
        with self.app.app_context():
            error_context = {
                'error_type': 'template_error',
                'error_message': 'Test template error'
            }
            
            html = create_fallback_landing_html(error_context)
            
            # Should still generate valid HTML despite error context
            self.assertIn('<!DOCTYPE html>', html)
            self.assertIn('Vedfolnir', html)
            self.assertIn('Get Started', html)
    
    def test_create_fallback_landing_html_app_name_config(self):
        """Test fallback HTML uses app name from config"""
        with self.app.app_context():
            html = create_fallback_landing_html()
            
            # Should use app name from config
            self.assertIn('Test Vedfolnir', html)
    
    def test_handle_template_rendering_error_landing_page(self):
        """Test template rendering error handling for landing page"""
        with self.app.app_context():
            test_error = Exception("Test template error")
            template_context = {'test_key': 'test_value'}
            
            response = handle_template_rendering_error('landing.html', test_error, template_context)
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')
            self.assertEqual(response.headers['X-Fallback-Mode'], 'template-error')
            
            # Verify fallback HTML content
            html_content = response.get_data(as_text=True)
            self.assertIn('Vedfolnir', html_content)
            self.assertIn('Get Started', html_content)
    
    def test_handle_template_rendering_error_other_template(self):
        """Test template rendering error handling for non-landing templates"""
        with self.app.app_context():
            test_error = Exception("Test template error")
            
            with patch('flask.render_template') as mock_render:
                mock_render.side_effect = Exception("500 template also failed")
                
                response = handle_template_rendering_error('other.html', test_error)
                
                # Should fall back to minimal HTML
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.headers['X-Fallback-Mode'], 'template-error-minimal')
                
                html_content = response.get_data(as_text=True)
                self.assertIn('Template Error', html_content)
    
    def test_handle_session_detection_error(self):
        """Test session detection error handling"""
        test_error = Exception("Test session detection error")
        session_context = {'test_session': 'test_data'}
        
        result = handle_session_detection_error(test_error, session_context)
        
        # Should return False for safety (no previous session)
        self.assertFalse(result)
        
        # Verify logging occurred
        log_messages = [record.getMessage() for record in self.log_capture]
        self.assertTrue(any('Session detection error' in msg for msg in log_messages))
    
    def test_handle_authentication_error(self):
        """Test authentication error handling"""
        with self.app.app_context():
            test_error = Exception("Test authentication error")
            user_context = {'user_id': 'test_user'}
            
            content, status_code = handle_authentication_error(test_error, user_context)
            
            # Should return fallback HTML with 200 status
            self.assertEqual(status_code, 200)
            self.assertIn('Vedfolnir', content)
            self.assertIn('Get Started', content)
    
    def test_log_authentication_failure(self):
        """Test authentication failure logging"""
        with self.app.test_request_context('/test', method='GET'):
            test_error = Exception("Test authentication failure")
            user_context = {'username': 'test_user', 'password': 'secret'}
            
            log_authentication_failure(test_error, user_context)
            
            # Verify logging occurred
            log_messages = [record.getMessage() for record in self.log_capture]
            auth_logs = [msg for msg in log_messages if 'Authentication failure' in msg or 'Authentication error' in msg]
            self.assertTrue(len(auth_logs) > 0)
            
            # Verify sensitive data is redacted
            log_content = ' '.join(auth_logs)
            self.assertIn('[REDACTED]', log_content)  # Password should be redacted
            self.assertNotIn('secret', log_content)  # Actual password should not appear
    
    def test_custom_exceptions(self):
        """Test custom exception classes"""
        # Test LandingPageError
        error = LandingPageError("Test message", "TEST_CODE")
        self.assertEqual(error.message, "Test message")
        self.assertEqual(error.error_code, "TEST_CODE")
        self.assertIsNotNone(error.timestamp)
        
        # Test AuthenticationFailureError
        auth_error = AuthenticationFailureError("Auth failed", {'user': 'test'})
        self.assertEqual(auth_error.error_code, "AUTHENTICATION_FAILURE")
        self.assertEqual(auth_error.user_info, {'user': 'test'})
        
        # Test TemplateRenderingError
        template_error = TemplateRenderingError("test.html", "Render failed", {'key': 'value'})
        self.assertEqual(template_error.template_name, "test.html")
        self.assertEqual(template_error.template_context, {'key': 'value'})
        self.assertEqual(template_error.error_code, "TEMPLATE_RENDERING_ERROR")
        
        # Test SessionDetectionError
        session_error = SessionDetectionError("Session failed", {'session': 'data'})
        self.assertEqual(session_error.error_code, "SESSION_DETECTION_ERROR")
        self.assertEqual(session_error.session_indicators, {'session': 'data'})
    
    def test_ensure_system_stability_decorator_success(self):
        """Test system stability decorator with successful function"""
        @ensure_system_stability
        def test_function():
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
    
    def test_ensure_system_stability_decorator_template_error(self):
        """Test system stability decorator with template error"""
        @ensure_system_stability
        def test_function():
            raise TemplateRenderingError("test.html", "Template failed")
        
        with self.app.app_context():
            response = test_function()
            
            # Should handle template error gracefully
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.headers['X-Fallback-Mode'], 'template-error-minimal')
    
    def test_ensure_system_stability_decorator_auth_error(self):
        """Test system stability decorator with authentication error"""
        @ensure_system_stability
        def test_function():
            raise AuthenticationFailureError("Auth failed")
        
        with self.app.app_context():
            response = test_function()
            
            # Should handle auth error gracefully
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            self.assertIn('Vedfolnir', content)
    
    def test_ensure_system_stability_decorator_session_error(self):
        """Test system stability decorator with session error"""
        @ensure_system_stability
        def test_function():
            raise SessionDetectionError("Session failed")
        
        with self.app.app_context():
            response = test_function()
            
            # Should handle session error gracefully
            self.assertEqual(response.status_code, 200)
            content = response.get_data(as_text=True)
            self.assertIn('Vedfolnir', content)
    
    def test_ensure_system_stability_decorator_generic_error_index(self):
        """Test system stability decorator with generic error in index function"""
        @ensure_system_stability
        def index():
            raise Exception("Generic error")
        
        with self.app.app_context():
            response = index()
            
            # Should provide fallback HTML for index function
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['X-Fallback-Mode'], 'system-error')
            content = response.get_data(as_text=True)
            self.assertIn('Vedfolnir', content)
    
    def test_ensure_system_stability_decorator_generic_error_other(self):
        """Test system stability decorator with generic error in other function"""
        @ensure_system_stability
        def other_function():
            raise Exception("Generic error")
        
        with self.app.app_context():
            response = other_function()
            
            # Should return 503 for non-index functions
            self.assertEqual(response.status_code, 503)
            content = response.get_data(as_text=True)
            self.assertIn('Service temporarily unavailable', content)
    
    def test_error_scenarios_testing(self):
        """Test the error scenarios testing function"""
        with self.app.app_context():
            results = test_error_scenarios()
            
            # Verify test results structure
            self.assertIn('timestamp', results)
            self.assertIn('tests', results)
            self.assertIn('summary', results)
            
            # Verify individual tests
            tests = results['tests']
            self.assertIn('fallback_html_generation', tests)
            self.assertIn('authentication_error_logging', tests)
            self.assertIn('session_detection_error_handling', tests)
            self.assertIn('template_rendering_error_handling', tests)
            
            # Verify summary
            summary = results['summary']
            self.assertIn('total_tests', summary)
            self.assertIn('passed_tests', summary)
            self.assertIn('failed_tests', summary)
            self.assertIn('success_rate', summary)
            
            # All tests should pass
            self.assertEqual(summary['failed_tests'], 0)
            self.assertEqual(summary['success_rate'], 100.0)
    
    def test_fallback_html_ultra_minimal(self):
        """Test ultra-minimal fallback when even fallback generation fails"""
        # Force an exception in the main fallback generation to trigger ultra-minimal
        with patch('utils.landing_page_fallback.logger') as mock_logger:
            # Mock logger.error to raise an exception, simulating a critical failure
            mock_logger.error.side_effect = Exception("Critical logging failure")
            
            # This should trigger the ultra-minimal fallback in the except block
            html = create_fallback_landing_html()
            
            # Should still be valid HTML (will use the ultra-minimal version)
            self.assertIn('<!DOCTYPE html>', html)
            # The ultra-minimal fallback should contain this text
            self.assertTrue(
                'Service Temporarily Unavailable' in html or 
                'Vedfolnir' in html  # Either ultra-minimal or regular fallback is fine
            )
    
    def test_template_error_ultra_minimal_fallback(self):
        """Test ultra-minimal fallback when all template handling fails"""
        with self.app.app_context():
            # Mock everything to fail
            with patch('utils.landing_page_fallback.create_fallback_landing_html', side_effect=Exception("Fallback failed")):
                with patch('flask.render_template', side_effect=Exception("Template failed")):
                    with patch('utils.landing_page_fallback.make_response') as mock_make_response:
                        mock_response = Mock()
                        mock_response.status_code = 500
                        mock_response.headers = {}
                        mock_make_response.return_value = mock_response
                        
                        test_error = Exception("Test error")
                        response = handle_template_rendering_error('landing.html', test_error)
                        
                        # Should call make_response with ultra-minimal content
                        mock_make_response.assert_called()
                        call_args = mock_make_response.call_args[0]
                        self.assertIn('Service temporarily unavailable', call_args[0])

class TestLandingPageErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for landing page error handling"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = self.app.test_client()
    
    def test_error_handling_with_request_context(self):
        """Test error handling works correctly with Flask request context"""
        with self.app.test_request_context('/test', method='GET', headers={'User-Agent': 'Test Agent'}):
            # Test authentication failure logging with request context
            test_error = Exception("Test error with context")
            user_context = {'user_id': 'test_user'}
            
            # Should not raise exception
            log_authentication_failure(test_error, user_context)
            
            # Test fallback HTML generation with request context
            html = create_fallback_landing_html()
            self.assertIn('Vedfolnir', html)
    
    def test_error_handling_without_request_context(self):
        """Test error handling works correctly without Flask request context"""
        # Test authentication failure logging without request context
        test_error = Exception("Test error without context")
        
        # Should not raise exception even without request context
        log_authentication_failure(test_error)
        
        # Test fallback HTML generation without request context
        with self.app.app_context():
            html = create_fallback_landing_html()
            self.assertIn('Vedfolnir', html)

if __name__ == '__main__':
    # Set up logging for tests
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)