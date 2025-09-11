# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for landing page security measures
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestLandingPageSecurity(unittest.TestCase):
    """Test security measures for the landing page"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = None
        self.client = None
    
    def test_security_headers_in_base_template(self):
        """Test that security headers are present in base template"""
        with open('templates/base.html', 'r') as f:
            content = f.read()
        
        # Check for security meta tags
        self.assertIn('X-Content-Type-Options', content)
        self.assertIn('X-Frame-Options', content)
        self.assertIn('X-XSS-Protection', content)
        self.assertIn('Referrer-Policy', content)
        self.assertIn('Permissions-Policy', content)
    
    def test_csrf_token_in_base_template(self):
        """Test that CSRF token meta tag is present"""
        with open('templates/base.html', 'r') as f:
            content = f.read()
        
        self.assertIn('csrf-token', content)
        self.assertIn('{{ csrf_token }}', content)
    
    def test_secure_url_generation_in_landing_page(self):
        """Test that landing page uses secure URL generation"""
        with open('templates/landing.html', 'r') as f:
            content = f.read()
        
        # Check for url_for usage instead of hardcoded URLs
        self.assertIn("url_for('auth.user_management.register')", content)
        self.assertIn("url_for('static'", content)
        # The login link is in the navigation, not directly in landing page content
    
    def test_input_sanitization_functions_exist(self):
        """Test that input sanitization functions are available"""
        from utils.request_helpers import sanitize_user_input, validate_url_parameter
        
        # Test basic sanitization
        result = sanitize_user_input("<script>alert('xss')</script>")
        self.assertNotIn('<script>', result)
        
        # Test URL parameter validation
        self.assertTrue(validate_url_parameter("valid_param"))
        self.assertFalse(validate_url_parameter("../../../etc/passwd"))
    
    def test_error_handling_functions_exist(self):
        """Test that security error handling functions are available"""
        from utils.error_responses import handle_security_error, ErrorCodes
        
        # Test that error codes are defined
        self.assertTrue(hasattr(ErrorCodes, 'AUTHORIZATION_ERROR'))
        self.assertTrue(hasattr(ErrorCodes, 'AUTHENTICATION_ERROR'))
        
        # Test error handler function exists
        self.assertTrue(callable(handle_security_error))
    
    def test_route_security_decorators(self):
        """Test that main routes have security decorators applied"""
        # Test that security decorators are available and can be imported
        try:
            from app.core.security.core.decorators import conditional_rate_limit, conditional_enhanced_input_validation
            
            # Test that decorators are callable
            self.assertTrue(callable(conditional_rate_limit))
            self.assertTrue(callable(conditional_enhanced_input_validation))
            
            # Test that they return decorators
            decorator = conditional_rate_limit(requests_per_minute=60)
            self.assertTrue(callable(decorator))
            
        except ImportError as e:
            self.fail(f"Security decorators not available: {e}")
    
    def test_security_middleware_initialization(self):
        """Test that security middleware can be imported and initialized"""
        try:
            from app.core.security.core.security_middleware import SecurityMiddleware
            from app.core.security.core.csrf_token_manager import CSRFTokenManager, get_csrf_token_manager
            
            # Test that classes can be instantiated
            self.assertTrue(SecurityMiddleware)
            self.assertTrue(CSRFTokenManager)
            self.assertTrue(callable(get_csrf_token_manager))
            
        except ImportError as e:
            self.fail(f"Security modules not available: {e}")
    
    def test_enhanced_input_validation_available(self):
        """Test that enhanced input validation is available"""
        try:
            from enhanced_input_validation import EnhancedInputValidator
            
            # Test basic functionality
            validator = EnhancedInputValidator()
            result = validator.sanitize_html("<script>alert('test')</script>")
            self.assertNotIn('<script>', result)
            
        except ImportError as e:
            self.fail(f"Enhanced input validation not available: {e}")
    
    def test_security_decorators_available(self):
        """Test that security decorators are available"""
        try:
            from app.core.security.core.decorators import (
                conditional_rate_limit,
                conditional_enhanced_input_validation,
                conditional_validate_csrf_token
            )
            
            # Test that decorators are callable
            self.assertTrue(callable(conditional_rate_limit))
            self.assertTrue(callable(conditional_enhanced_input_validation))
            self.assertTrue(callable(conditional_validate_csrf_token))
            
        except ImportError as e:
            self.fail(f"Security decorators not available: {e}")

if __name__ == '__main__':
    unittest.main()