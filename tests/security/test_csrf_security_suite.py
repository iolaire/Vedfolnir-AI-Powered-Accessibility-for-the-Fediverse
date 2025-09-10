# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Security Test Suite

Comprehensive unit and integration tests for CSRF token generation, validation,
and protection across all forms and AJAX endpoints.
"""

import unittest
import tempfile
import os
import json
import time
import secrets
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from flask import Flask, session, request, g
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFError
from wtforms import StringField, SubmitField

# Import CSRF components
from app.core.security.core.csrf_token_manager import (
    CSRFTokenManager, CSRFTokenError, CSRFValidationContext,
    get_csrf_token_manager, initialize_csrf_token_manager
)
from app.core.security.core.csrf_middleware import (
    CSRFMiddleware, csrf_exempt, require_csrf,
    initialize_csrf_middleware, get_csrf_middleware
)
from app.core.security.core.csrf_error_handler import (
    CSRFErrorHandler, get_csrf_error_handler, register_csrf_error_handlers
)

# Import test helpers
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import UserRole

class TestCSRFTokenGeneration(unittest.TestCase):
    """Test CSRF token generation and entropy validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-for-csrf-testing'
        self.app.config['WTF_CSRF_ENABLED'] = True
        
        self.csrf_manager = CSRFTokenManager(
            secret_key=self.app.config['SECRET_KEY'],
            token_lifetime=3600
        )
        
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def test_token_generation_basic(self):
        """Test basic CSRF token generation"""
        with self.app.test_request_context():
            token = self.csrf_manager.generate_token('test_session_123')
            
            # Token should be a string
            self.assertIsInstance(token, str)
            
            # Token should have expected format (session:timestamp:random:signature)
            parts = token.split(':')
            self.assertEqual(len(parts), 4)
            
            # Session ID should match
            self.assertEqual(parts[0], 'test_session_123')
            
            # Timestamp should be valid integer
            timestamp = int(parts[1])
            self.assertIsInstance(timestamp, int)
            self.assertGreater(timestamp, 0)
            
            # Random part should be hex string
            random_hex = parts[2]
            self.assertEqual(len(random_hex), 64)  # 32 bytes = 64 hex chars
            bytes.fromhex(random_hex)  # Should not raise exception
            
            # Signature should be present
            signature = parts[3]
            self.assertGreater(len(signature), 0)
    
    def test_token_entropy_validation(self):
        """Test that CSRF tokens have sufficient entropy"""
        with self.app.test_request_context():
            # Generate multiple tokens
            tokens = [self.csrf_manager.generate_token('test_session') for _ in range(100)]
            
            # All tokens should be unique
            self.assertEqual(len(set(tokens)), len(tokens))
            
            # Each token should have sufficient entropy
            for token in tokens[:10]:  # Test first 10 for performance
                parts = token.split(':')
                random_hex = parts[2]
                random_bytes = bytes.fromhex(random_hex)
                
                # Should be 32 bytes (256 bits)
                self.assertEqual(len(random_bytes), 32)
                
                # Should have good entropy (not all same bytes)
                unique_bytes = len(set(random_bytes))
                self.assertGreater(unique_bytes, 16)  # At least 16 different byte values
    
    def test_token_session_binding(self):
        """Test that tokens are properly bound to sessions"""
        with self.app.test_request_context():
            session_1 = 'session_123'
            session_2 = 'session_456'
            
            token_1 = self.csrf_manager.generate_token(session_1)
            token_2 = self.csrf_manager.generate_token(session_2)
            
            # Tokens should be different
            self.assertNotEqual(token_1, token_2)
            
            # Token 1 should validate for session 1 but not session 2
            self.assertTrue(self.csrf_manager.validate_token(token_1, session_1))
            self.assertFalse(self.csrf_manager.validate_token(token_1, session_2))
            
            # Token 2 should validate for session 2 but not session 1
            self.assertTrue(self.csrf_manager.validate_token(token_2, session_2))
            self.assertFalse(self.csrf_manager.validate_token(token_2, session_1))
    
    def test_token_expiration(self):
        """Test CSRF token expiration handling"""
        # Create manager with short lifetime for testing
        short_manager = CSRFTokenManager(
            secret_key=self.app.config['SECRET_KEY'],
            token_lifetime=1  # 1 second
        )
        
        with self.app.test_request_context():
            token = short_manager.generate_token('test_session')
            
            # Token should be valid immediately
            self.assertTrue(short_manager.validate_token(token, 'test_session'))
            
            # Wait for expiration
            time.sleep(2)
            
            # Token should now be expired
            self.assertFalse(short_manager.validate_token(token, 'test_session'))
            self.assertTrue(short_manager.is_token_expired(token))
    
    def test_token_signature_validation(self):
        """Test CSRF token signature validation"""
        with self.app.test_request_context():
            token = self.csrf_manager.generate_token('test_session')
            
            # Valid token should validate
            self.assertTrue(self.csrf_manager.validate_token(token, 'test_session'))
            
            # Tampered token should not validate
            parts = token.split(':')
            tampered_token = ':'.join(parts[:-1] + ['tampered_signature'])
            self.assertFalse(self.csrf_manager.validate_token(tampered_token, 'test_session'))
            
            # Token with wrong session should not validate
            self.assertFalse(self.csrf_manager.validate_token(token, 'wrong_session'))
    
    def test_token_malformed_handling(self):
        """Test handling of malformed CSRF tokens"""
        with self.app.test_request_context():
            malformed_tokens = [
                '',
                'invalid',
                'only:two:parts',
                'too:many:parts:here:extra',
                'session:invalid_timestamp:random:signature',
                'session:123:invalid_hex:signature',
                None
            ]
            
            for malformed_token in malformed_tokens:
                self.assertFalse(
                    self.csrf_manager.validate_token(malformed_token, 'test_session'),
                    f"Should reject malformed token: {malformed_token}"
                )
    
    def test_token_info_extraction(self):
        """Test CSRF token information extraction"""
        with self.app.test_request_context():
            token = self.csrf_manager.generate_token('test_session_123')
            
            info = self.csrf_manager.extract_token_info(token)
            
            # Should contain expected fields
            self.assertIn('session_id', info)
            self.assertIn('created_at', info)
            self.assertIn('expires_at', info)
            self.assertIn('is_expired', info)
            self.assertIn('entropy_bits', info)
            self.assertIn('signature_valid', info)
            
            # Values should be reasonable
            self.assertTrue(info['session_id'].startswith('test_ses'))
            self.assertFalse(info['is_expired'])
            self.assertEqual(info['entropy_bits'], 256)  # 64 hex chars * 4 bits
            self.assertTrue(info['signature_valid'])

class TestCSRFTokenValidation(unittest.TestCase):
    """Test CSRF token validation logic"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-for-validation'
        
        self.csrf_manager = CSRFTokenManager(
            secret_key=self.app.config['SECRET_KEY'],
            token_lifetime=3600
        )
        
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def test_valid_token_validation(self):
        """Test validation of valid CSRF tokens"""
        with self.app.test_request_context():
            session_id = 'valid_session_123'
            token = self.csrf_manager.generate_token(session_id)
            
            # Valid token should pass validation
            self.assertTrue(self.csrf_manager.validate_token(token, session_id))
    
    def test_invalid_session_rejection(self):
        """Test rejection of tokens with wrong session ID"""
        with self.app.test_request_context():
            token = self.csrf_manager.generate_token('session_1')
            
            # Should reject token for different session
            self.assertFalse(self.csrf_manager.validate_token(token, 'session_2'))
    
    def test_expired_token_rejection(self):
        """Test rejection of expired tokens"""
        # Create manager with very short lifetime
        short_manager = CSRFTokenManager(
            secret_key=self.app.config['SECRET_KEY'],
            token_lifetime=0  # Immediate expiration
        )
        
        with self.app.test_request_context():
            token = short_manager.generate_token('test_session')
            
            # Token should be immediately expired
            self.assertFalse(short_manager.validate_token(token, 'test_session'))
    
    def test_tampered_token_rejection(self):
        """Test rejection of tampered tokens"""
        with self.app.test_request_context():
            original_token = self.csrf_manager.generate_token('test_session')
            parts = original_token.split(':')
            
            # Test various tampering scenarios
            tampered_scenarios = [
                # Change session ID
                'different_session:' + ':'.join(parts[1:]),
                # Change timestamp
                ':'.join([parts[0], '999999999', parts[2], parts[3]]),
                # Change random part
                ':'.join([parts[0], parts[1], 'a' * 64, parts[3]]),
                # Change signature
                ':'.join(parts[:-1] + ['fake_signature'])
            ]
            
            for tampered_token in tampered_scenarios:
                self.assertFalse(
                    self.csrf_manager.validate_token(tampered_token, 'test_session'),
                    f"Should reject tampered token: {tampered_token[:50]}..."
                )
    
    def test_validation_context_creation(self):
        """Test CSRF validation context creation"""
        with self.app.test_request_context('/test', method='POST'):
            context = CSRFValidationContext(
                request_method='POST',
                endpoint='test_endpoint',
                user_id=123
            )
            
            # Check context properties
            self.assertEqual(context.request_method, 'POST')
            self.assertEqual(context.endpoint, 'test_endpoint')
            self.assertEqual(context.user_id, 123)
            self.assertIsInstance(context.timestamp, datetime)
            self.assertFalse(context.validation_result)
            self.assertIsNone(context.error_details)
            
            # Test context serialization
            context_dict = context.to_dict()
            self.assertIn('request_method', context_dict)
            self.assertIn('endpoint', context_dict)
            self.assertIn('user_id', context_dict)
            self.assertIn('timestamp', context_dict)

class TestCSRFFormProtection(unittest.TestCase):
    """Test CSRF protection for form submissions"""
    
    def setUp(self):
        """Set up test Flask app with forms"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-for-forms'
        self.app.config['WTF_CSRF_ENABLED'] = True
        
        # Create test form
        class TestForm(FlaskForm):
            name = StringField('Name')
            submit = SubmitField('Submit')
        
        self.TestForm = TestForm
        
        # Set up routes
        @self.app.route('/form', methods=['GET', 'POST'])
        def form_route():
            form = TestForm()
            if form.validate_on_submit():
                return 'Form submitted successfully'
            return f'Form errors: {form.errors}'
        
        @self.app.route('/form_no_csrf', methods=['POST'])
        @csrf_exempt
        def form_no_csrf():
            return 'No CSRF required'
        
        self.client = self.app.test_client()
        
        # Initialize CSRF components
        initialize_csrf_token_manager(self.app)
        initialize_csrf_middleware(self.app)
        register_csrf_error_handlers(self.app)
    
    def test_form_csrf_token_required(self):
        """Test that forms require CSRF tokens"""
        # POST without CSRF token should fail
        response = self.client.post('/form', data={'name': 'test'})
        self.assertEqual(response.status_code, 403)
    
    def test_form_csrf_token_validation(self):
        """Test form submission with valid CSRF token"""
        # Get form page to obtain CSRF token
        with self.client.session_transaction() as sess:
            # Simulate getting CSRF token from form
            csrf_manager = get_csrf_token_manager()
            
            with self.app.test_request_context():
                session['_id'] = 'test_session_123'
                csrf_token = csrf_manager.generate_token('test_session_123')
        
        # Submit form with valid CSRF token
        response = self.client.post('/form', data={
            'name': 'test',
            'csrf_token': csrf_token
        })
        
        # Should succeed (or at least not fail with CSRF error)
        self.assertNotEqual(response.status_code, 403)
    
    def test_form_csrf_exempt_decorator(self):
        """Test that @csrf_exempt decorator works"""
        # POST to exempt route should succeed without CSRF token
        response = self.client.post('/form_no_csrf', data={'name': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No CSRF required', response.data)
    
    def test_form_invalid_csrf_token(self):
        """Test form submission with invalid CSRF token"""
        # Submit form with invalid CSRF token
        response = self.client.post('/form', data={
            'name': 'test',
            'csrf_token': 'invalid_token'
        })
        
        # Should fail with CSRF error
        self.assertEqual(response.status_code, 403)

class TestCSRFAjaxProtection(unittest.TestCase):
    """Test CSRF protection for AJAX requests"""
    
    def setUp(self):
        """Set up test Flask app with AJAX endpoints"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-for-ajax'
        self.app.config['WTF_CSRF_ENABLED'] = True
        
        # Set up AJAX routes
        @self.app.route('/api/test', methods=['POST'])
        def api_test():
            return {'success': True, 'message': 'API call successful'}
        
        @self.app.route('/api/csrf_token', methods=['GET'])
        def get_csrf_token():
            csrf_manager = get_csrf_token_manager()
            token = csrf_manager.generate_token()
            return {'csrf_token': token}
        
        @self.app.route('/api/no_csrf', methods=['POST'])
        @csrf_exempt
        def api_no_csrf():
            return {'success': True, 'message': 'No CSRF required'}
        
        self.client = self.app.test_client()
        
        # Initialize CSRF components
        initialize_csrf_token_manager(self.app)
        initialize_csrf_middleware(self.app)
        register_csrf_error_handlers(self.app)
    
    def test_ajax_csrf_token_required(self):
        """Test that AJAX requests require CSRF tokens"""
        # AJAX POST without CSRF token should fail
        response = self.client.post('/api/test', 
                                  headers={'X-Requested-With': 'XMLHttpRequest'},
                                  json={'data': 'test'})
        self.assertEqual(response.status_code, 403)
    
    def test_ajax_csrf_token_validation(self):
        """Test AJAX request with valid CSRF token"""
        # Get CSRF token
        with self.client.session_transaction() as sess:
            csrf_manager = get_csrf_token_manager()
            
            with self.app.test_request_context():
                session['_id'] = 'test_ajax_session'
                csrf_token = csrf_manager.generate_token('test_ajax_session')
        
        # Make AJAX request with CSRF token in header
        response = self.client.post('/api/test',
                                  headers={
                                      'X-Requested-With': 'XMLHttpRequest',
                                      'X-CSRFToken': csrf_token
                                  },
                                  json={'data': 'test'})
        
        # Should succeed (or at least not fail with CSRF error)
        self.assertNotEqual(response.status_code, 403)
    
    def test_ajax_csrf_token_in_meta_tag(self):
        """Test CSRF token retrieval from meta tag for AJAX"""
        # This would test the JavaScript functionality
        # For now, test the server-side token generation
        
        response = self.client.get('/api/csrf_token')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn('csrf_token', data)
        self.assertIsInstance(data['csrf_token'], str)
        self.assertGreater(len(data['csrf_token']), 0)
    
    def test_ajax_csrf_error_response(self):
        """Test AJAX CSRF error response format"""
        # Make AJAX request without CSRF token
        response = self.client.post('/api/test',
                                  headers={'X-Requested-With': 'XMLHttpRequest'},
                                  json={'data': 'test'})
        
        self.assertEqual(response.status_code, 403)
        
        # Response should be JSON for AJAX requests
        if response.is_json:
            data = response.get_json()
            self.assertIn('error', data)
            self.assertIn('message', data)
    
    def test_ajax_csrf_exempt_endpoint(self):
        """Test AJAX request to CSRF-exempt endpoint"""
        # AJAX POST to exempt endpoint should succeed
        response = self.client.post('/api/no_csrf',
                                  headers={'X-Requested-With': 'XMLHttpRequest'},
                                  json={'data': 'test'})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

class TestCSRFMiddleware(unittest.TestCase):
    """Test CSRF middleware functionality"""
    
    def setUp(self):
        """Set up test Flask app with middleware"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-for-middleware'
        
        # Initialize middleware
        self.middleware = CSRFMiddleware(self.app)
        
        # Set up test routes
        @self.app.route('/protected', methods=['POST'])
        def protected_route():
            return 'Protected content'
        
        @self.app.route('/public', methods=['GET'])
        def public_route():
            return 'Public content'
        
        @self.app.route('/exempt', methods=['POST'])
        @csrf_exempt
        def exempt_route():
            return 'Exempt content'
        
        self.client = self.app.test_client()
    
    def test_middleware_get_request_exemption(self):
        """Test that GET requests are exempt from CSRF validation"""
        response = self.client.get('/public')
        self.assertEqual(response.status_code, 200)
    
    def test_middleware_post_request_protection(self):
        """Test that POST requests require CSRF validation"""
        response = self.client.post('/protected', data={'test': 'data'})
        # Should fail due to missing CSRF token
        self.assertEqual(response.status_code, 403)
    
    def test_middleware_exemption_configuration(self):
        """Test middleware exemption configuration"""
        # Add custom exemption
        self.middleware.exempt_endpoint('custom_endpoint')
        self.middleware.exempt_path('/custom/path')
        self.middleware.exempt_method('PATCH')
        
        # Check exemptions
        exemptions = self.middleware.get_exemptions()
        self.assertIn('custom_endpoint', exemptions['endpoints'])
        self.assertIn('/custom/path', exemptions['paths'])
        self.assertIn('PATCH', exemptions['methods'])
        
        # Remove exemption
        self.middleware.remove_exemption(endpoint='custom_endpoint')
        exemptions = self.middleware.get_exemptions()
        self.assertNotIn('custom_endpoint', exemptions['endpoints'])
    
    def test_middleware_validation_callback(self):
        """Test custom validation callback"""
        # Add custom callback
        def custom_callback(request):
            return request.path.startswith('/special/')
        
        self.middleware.add_validation_callback(custom_callback)
        
        # Check callback was added
        exemptions = self.middleware.get_exemptions()
        self.assertEqual(exemptions['callbacks'], 1)

class TestCSRFErrorHandling(unittest.TestCase):
    """Test CSRF error handling and user experience"""
    
    def setUp(self):
        """Set up test Flask app with error handling"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-for-errors'
        
        self.error_handler = CSRFErrorHandler()
        
        # Set up test routes
        @self.app.route('/form', methods=['POST'])
        def form_route():
            # Simulate CSRF validation failure
            raise CSRFError('CSRF token missing')
        
        @self.app.route('/api/test', methods=['POST'])
        def api_route():
            # Simulate CSRF validation failure for AJAX
            raise CSRFError('CSRF token invalid')
        
        self.client = self.app.test_client()
        
        # Register error handlers
        register_csrf_error_handlers(self.app)
    
    def test_csrf_error_classification(self):
        """Test CSRF error type classification"""
        test_errors = [
            (Exception('CSRF token missing'), 'missing_token'),
            (Exception('CSRF token expired'), 'expired_token'),
            (Exception('CSRF token invalid'), 'invalid_token'),
            (Exception('CSRF token mismatch'), 'token_mismatch'),
            (Exception('Unknown CSRF error'), 'general_csrf_error')
        ]
        
        for error, expected_type in test_errors:
            error_type = self.error_handler._classify_csrf_error(error)
            self.assertEqual(error_type, expected_type)
    
    def test_form_data_preservation(self):
        """Test form data preservation during CSRF errors"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'message': 'This is a test message',
            'password': 'secret123',  # Should be filtered out
            'csrf_token': 'token123'  # Should be filtered out
        }
        
        preserved = self.error_handler.preserve_form_data(form_data)
        self.assertIsNotNone(preserved)
        
        # Parse preserved data
        preserved_dict = json.loads(preserved)
        
        # Should contain non-sensitive fields
        self.assertIn('username', preserved_dict)
        self.assertIn('email', preserved_dict)
        self.assertIn('message', preserved_dict)
        
        # Should not contain sensitive fields
        self.assertNotIn('password', preserved_dict)
        self.assertNotIn('csrf_token', preserved_dict)
    
    def test_csrf_error_logging(self):
        """Test CSRF error logging"""
        with self.app.test_request_context('/test', method='POST'):
            context = CSRFValidationContext(
                request_method='POST',
                endpoint='test_endpoint',
                user_id=123
            )
            
            error = CSRFError('Test CSRF error')
            
            # Should not raise exception
            self.error_handler.log_csrf_violation(error, context)
    
    def test_retry_guidance_generation(self):
        """Test retry guidance generation"""
        context = CSRFValidationContext(
            request_method='POST',
            endpoint='login',
            user_id=None
        )
        
        guidance = self.error_handler.generate_retry_guidance(context)
        
        # Should contain helpful guidance
        self.assertIsInstance(guidance, str)
        self.assertGreater(len(guidance), 0)
        self.assertIn('refresh', guidance.lower())
    
    def test_preserved_data_recovery(self):
        """Test preserved form data recovery"""
        # Test with no preserved data
        with self.app.test_request_context():
            recovered = self.error_handler.recover_preserved_data()
            self.assertIsNone(recovered)
        
        # Test with preserved data in session
        with self.app.test_request_context():
            test_data = {'field': 'value'}
            session['_csrf_preserved_data'] = json.dumps(test_data)
            session['_csrf_preserved_timestamp'] = datetime.now().isoformat()
            
            recovered = self.error_handler.recover_preserved_data()
            self.assertEqual(recovered, test_data)

if __name__ == '__main__':
    unittest.main(verbosity=2)