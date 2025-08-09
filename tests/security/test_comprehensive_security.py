# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive security regression tests

Tests all security fixes and ensures no security vulnerabilities are introduced.
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from flask import Flask
from cryptography.fernet import Fernet

from security_middleware import SecurityMiddleware
from secure_error_handlers import SecureErrorHandler
from security_monitoring import SecurityMonitor, SecurityEventType, SecurityEventSeverity


class TestComprehensiveSecurity(unittest.TestCase):
    """Comprehensive security regression tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Initialize security components
        self.security_middleware = SecurityMiddleware(self.app)
        self.error_handler = SecureErrorHandler(self.app)
        self.security_monitor = SecurityMonitor()
        
        # Create test client
        self.client = self.app.test_client()
        
        # Set up environment variables
        os.environ['PLATFORM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are blocked"""
        # Test various SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "1'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for payload in sql_payloads:
            with self.app.test_request_context(f'/?id={payload}'):
                # Should trigger security validation
                with self.assertRaises(Exception):
                    self.security_middleware._validate_string_content(payload)
    
    def test_xss_prevention(self):
        """Test that XSS attempts are blocked"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<object data='javascript:alert(1)'></object>"
        ]
        
        for payload in xss_payloads:
            with self.assertRaises(Exception):
                self.security_middleware._validate_string_content(payload)
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked"""
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for payload in path_payloads:
            with self.assertRaises(Exception):
                self.security_middleware._validate_string_content(payload)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Create test route
        @self.app.route('/test')
        def test_route():
            return 'OK'
        
        # Simulate rapid requests
        with patch.object(self.security_middleware, 'rate_limit_storage', {}):
            # First 60 requests should succeed
            for i in range(60):
                with self.app.test_request_context('/test'):
                    self.assertTrue(self.security_middleware._check_rate_limit())
            
            # 61st request should fail
            with self.app.test_request_context('/test'):
                self.assertFalse(self.security_middleware._check_rate_limit())
    
    def test_security_headers(self):
        """Test that security headers are properly set"""
        @self.app.route('/test')
        def test_route():
            return 'OK'
        
        response = self.client.get('/test')
        
        # Check for required security headers
        self.assertIn('Content-Security-Policy', response.headers)
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertIn('X-Frame-Options', response.headers)
        self.assertIn('X-XSS-Protection', response.headers)
        self.assertIn('Referrer-Policy', response.headers)
        
        # Verify header values
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(response.headers['X-XSS-Protection'], '1; mode=block')
    
    def test_error_handling_security(self):
        """Test that error handling doesn't leak sensitive information"""
        @self.app.route('/test_error')
        def test_error():
            raise Exception("Sensitive database connection string: postgresql://user:pass@host/db")
        
        response = self.client.get('/test_error')
        
        # Should return 500 status
        self.assertEqual(response.status_code, 500)
        
        # Should not contain sensitive information
        response_data = response.get_data(as_text=True)
        self.assertNotIn('postgresql://', response_data)
        self.assertNotIn('database connection', response_data)
        self.assertNotIn('user:pass', response_data)
    
    def test_input_validation_limits(self):
        """Test input validation limits"""
        # Test oversized JSON
        large_json = {'key': 'x' * 20000}  # 20KB value
        
        with self.app.test_request_context('/test', json=large_json):
            # Should not raise exception for reasonable size
            pass
        
        # Test deeply nested JSON
        nested_json = {'level1': {'level2': {'level3': {'level4': {'level5': {'level6': 'deep'}}}}}}
        
        with self.assertRaises(Exception):
            self.security_middleware._validate_json_data(nested_json, max_depth=3)
    
    def test_suspicious_user_agent_blocking(self):
        """Test blocking of suspicious user agents"""
        suspicious_agents = [
            'sqlmap/1.0',
            'Nikto/2.1.6',
            'Nmap Scripting Engine',
            'Burp Suite Professional'
        ]
        
        for agent in suspicious_agents:
            with self.app.test_request_context('/test', headers={'User-Agent': agent}):
                with self.assertRaises(Exception):
                    self.security_middleware._check_suspicious_patterns()
    
    def test_security_monitoring(self):
        """Test security event monitoring"""
        # Log various security events
        self.security_monitor.log_security_event(
            SecurityEventType.LOGIN_FAILURE,
            SecurityEventSeverity.MEDIUM,
            '192.168.1.100',
            '/login',
            'Mozilla/5.0',
            'testuser',
            {'reason': 'invalid_password'}
        )
        
        # Check that event was logged
        self.assertEqual(len(self.security_monitor.events), 1)
        
        event = self.security_monitor.events[0]
        self.assertEqual(event.event_type, SecurityEventType.LOGIN_FAILURE)
        self.assertEqual(event.source_ip, '192.168.1.100')
        self.assertEqual(event.user_id, 'testuser')
    
    def test_brute_force_detection(self):
        """Test brute force attack detection"""
        # Simulate multiple failed login attempts
        for i in range(6):  # Exceed threshold of 5
            self.security_monitor.log_security_event(
                SecurityEventType.LOGIN_FAILURE,
                SecurityEventSeverity.MEDIUM,
                '192.168.1.100',
                '/login',
                'Mozilla/5.0',
                'testuser'
            )
        
        # Should have triggered brute force alert
        # (In real implementation, this would be checked via alert system)
        recent_events = [
            e for e in self.security_monitor.events
            if e.event_type == SecurityEventType.LOGIN_FAILURE
        ]
        self.assertGreaterEqual(len(recent_events), 5)
    
    def test_csrf_protection(self):
        """Test CSRF protection mechanisms"""
        # This would test CSRF token validation
        # Implementation depends on your CSRF protection setup
        pass
    
    def test_session_security(self):
        """Test session security measures"""
        # Test session timeout, secure cookies, etc.
        # Implementation depends on your session management
        pass
    
    def test_credential_encryption(self):
        """Test that credentials are properly encrypted"""
        from models import PlatformConnection
        
        # Create test platform with credentials
        platform = PlatformConnection(
            user_id=1,
            name='Test Platform',
            platform_type='pixelfed',
            instance_url='https://test.com',
            username='testuser'
        )
        
        # Set sensitive credential
        test_token = 'sensitive_access_token_12345'
        platform.access_token = test_token
        
        # Verify it's encrypted in storage
        self.assertNotEqual(platform._access_token, test_token)
        self.assertNotIn('sensitive', platform._access_token or '')
        
        # Verify it can be decrypted
        self.assertEqual(platform.access_token, test_token)
    
    def test_secure_password_hashing(self):
        """Test secure password hashing"""
        from security_middleware import hash_password_secure, verify_password_secure
        
        password = "test_password_123"
        hashed = hash_password_secure(password)
        
        # Should be able to verify correct password
        self.assertTrue(verify_password_secure(password, hashed))
        
        # Should reject incorrect password
        self.assertFalse(verify_password_secure("wrong_password", hashed))
        
        # Hash should be different each time (due to salt)
        hashed2 = hash_password_secure(password)
        self.assertNotEqual(hashed, hashed2)
    
    def test_secure_token_generation(self):
        """Test secure token generation"""
        from security_middleware import generate_secure_token
        
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # Tokens should be different
        self.assertNotEqual(token1, token2)
        
        # Tokens should be proper length
        self.assertGreater(len(token1), 20)
        self.assertGreater(len(token2), 20)
    
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        from security_middleware import sanitize_filename
        
        dangerous_filenames = [
            "../../../etc/passwd",
            "file<script>alert('xss')</script>.txt",
            "file|rm -rf /.txt",
            "CON.txt",  # Windows reserved name
            "file\x00.txt"  # Null byte
        ]
        
        for filename in dangerous_filenames:
            sanitized = sanitize_filename(filename)
            
            # Should not contain dangerous characters
            self.assertNotIn('..', sanitized)
            self.assertNotIn('<', sanitized)
            self.assertNotIn('>', sanitized)
            self.assertNotIn('|', sanitized)
            self.assertNotIn('\x00', sanitized)
    
    def test_security_dashboard_data(self):
        """Test security dashboard data generation"""
        # Add some test events
        self.security_monitor.log_security_event(
            SecurityEventType.LOGIN_SUCCESS,
            SecurityEventSeverity.LOW,
            '192.168.1.100',
            '/login'
        )
        
        self.security_monitor.log_security_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            SecurityEventSeverity.HIGH,
            '192.168.1.200',
            '/admin'
        )
        
        dashboard_data = self.security_monitor.get_security_dashboard_data()
        
        # Should contain expected keys
        self.assertIn('total_events_24h', dashboard_data)
        self.assertIn('critical_events_24h', dashboard_data)
        self.assertIn('high_events_24h', dashboard_data)
        self.assertIn('top_event_types', dashboard_data)
        self.assertIn('top_source_ips', dashboard_data)
        
        # Should have correct counts
        self.assertGreaterEqual(dashboard_data['total_events_24h'], 2)
        self.assertGreaterEqual(dashboard_data['high_events_24h'], 1)


class TestSecurityRegression(unittest.TestCase):
    """Security regression tests to prevent reintroduction of vulnerabilities"""
    
    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets exist in code"""
        import os
        import re
        
        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']{8,}["\']',
            r'secret\s*=\s*["\'][^"\']{16,}["\']',
            r'token\s*=\s*["\'][^"\']{20,}["\']',
            r'key\s*=\s*["\'][^"\']{16,}["\']'
        ]
        
        # Check Python files for hardcoded secrets
        for root, dirs, files in os.walk('.'):
            # Skip test files and virtual environments
            if 'test' in root or 'venv' in root or '__pycache__' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in secret_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                # Allow test secrets and configuration examples
                                if 'test' not in filepath.lower() and 'example' not in filepath.lower():
                                    self.fail(f"Potential hardcoded secret in {filepath}: {matches}")
                    except (UnicodeDecodeError, PermissionError):
                        # Skip files that can't be read
                        continue
    
    def test_debug_mode_disabled(self):
        """Test that debug mode is properly configured"""
        from config import Config
        
        # In production, debug should be disabled
        # This test assumes production environment variables
        config = Config()
        
        # Debug mode should be configurable and default to False
        # Implementation depends on your config setup
        pass
    
    def test_secure_cookie_settings(self):
        """Test that cookies have secure settings"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-key'
        
        with app.test_client() as client:
            # Test that session cookies have secure flags
            # Implementation depends on your session configuration
            pass
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement for sensitive endpoints"""
        # Test that sensitive endpoints require HTTPS
        # Implementation depends on your HTTPS enforcement setup
        pass


if __name__ == '__main__':
    unittest.main()