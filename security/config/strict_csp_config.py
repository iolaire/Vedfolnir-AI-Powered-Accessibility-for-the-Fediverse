# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Strict Content Security Policy configuration for CSS security enhancement testing
"""

import secrets
import time
import re
from flask import g


class StrictCSPConfig:
    """Configuration for strict Content Security Policy without unsafe-inline"""
    
    @staticmethod
    def get_strict_csp_policy(nonce=None):
        """
        Generate strict CSP policy without unsafe-inline for styles
        
        Args:
            nonce: CSP nonce for scripts (optional)
            
        Returns:
            str: Strict CSP policy string
        """
        if nonce is None:
            try:
                nonce = getattr(g, 'csp_nonce', None)
            except RuntimeError:
                # Outside application context
                nonce = None
            
            if nonce is None:
                nonce = secrets.token_urlsafe(16)
        
        # Strict CSP policy - NO unsafe-inline for styles
        policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com; "
            f"style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # NO unsafe-inline
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self' wss: ws:; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"object-src 'none'; "
            f"media-src 'self'; "
            f"worker-src 'none'; "
            f"manifest-src 'self'; "
            f"upgrade-insecure-requests"
        )
        
        return policy
    
    @staticmethod
    def get_development_csp_policy(nonce=None):
        """
        Generate development CSP policy with some relaxed restrictions for testing
        
        Args:
            nonce: CSP nonce for scripts (optional)
            
        Returns:
            str: Development CSP policy string
        """
        if nonce is None:
            try:
                nonce = getattr(g, 'csp_nonce', None)
            except RuntimeError:
                # Outside application context
                nonce = None
            
            if nonce is None:
                nonce = secrets.token_urlsafe(16)
        
        # Development CSP policy - still strict but allows localhost
        policy = (
            f"default-src 'self' localhost:* 127.0.0.1:*; "
            f"script-src 'self' 'nonce-{nonce}' localhost:* 127.0.0.1:* https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com; "
            f"style-src 'self' localhost:* 127.0.0.1:* https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # NO unsafe-inline
            f"img-src 'self' data: https: localhost:* 127.0.0.1:*; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net localhost:* 127.0.0.1:*; "
            f"connect-src 'self' wss: ws: localhost:* 127.0.0.1:*; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"object-src 'none'; "
            f"media-src 'self' localhost:* 127.0.0.1:*; "
            f"worker-src 'none'; "
            f"manifest-src 'self'"
        )
        
        return policy
    
    @staticmethod
    def get_report_only_csp_policy(nonce=None):
        """
        Generate CSP policy for report-only mode (testing without blocking)
        
        Args:
            nonce: CSP nonce for scripts (optional)
            
        Returns:
            str: Report-only CSP policy string
        """
        if nonce is None:
            try:
                nonce = getattr(g, 'csp_nonce', None)
            except RuntimeError:
                # Outside application context
                nonce = None
            
            if nonce is None:
                nonce = secrets.token_urlsafe(16)
        
        # Report-only policy for testing
        policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com; "
            f"style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # NO unsafe-inline
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self' wss: ws:; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"object-src 'none'; "
            f"media-src 'self'; "
            f"report-uri /api/csp-report"
        )
        
        return policy
    
    @staticmethod
    def validate_csp_policy(policy_string):
        """
        Validate that CSP policy meets security requirements
        
        Args:
            policy_string: CSP policy string to validate
            
        Returns:
            dict: Validation results with issues found
        """
        issues = []
        warnings = []
        
        # Check for unsafe-inline in style-src
        if "'unsafe-inline'" in policy_string and "style-src" in policy_string:
            # Extract style-src directive
            style_src_match = re.search(r'style-src\s+([^;]+)', policy_string)
            if style_src_match and "'unsafe-inline'" in style_src_match.group(1):
                issues.append("style-src contains 'unsafe-inline' - violates CSS security requirements")
        
        # Check for unsafe-eval
        if "'unsafe-eval'" in policy_string:
            issues.append("Policy contains 'unsafe-eval' - security risk")
        
        # Check for wildcard sources
        if " * " in policy_string or policy_string.startswith("* ") or policy_string.endswith(" *"):
            warnings.append("Policy contains wildcard (*) sources - consider being more specific")
        
        # Check for data: in script-src
        if "script-src" in policy_string and "data:" in policy_string:
            script_src_match = re.search(r'script-src\s+([^;]+)', policy_string)
            if script_src_match and "data:" in script_src_match.group(1):
                warnings.append("script-src contains 'data:' - potential security risk")
        
        # Check for missing directives
        required_directives = ['default-src', 'script-src', 'style-src', 'object-src', 'base-uri']
        for directive in required_directives:
            if directive not in policy_string:
                warnings.append(f"Missing recommended directive: {directive}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'policy': policy_string
        }


class CSPTestingMiddleware:
    """Middleware for testing CSP compliance"""
    
    def __init__(self, app=None, strict_mode=False, report_only=False):
        self.app = app
        self.strict_mode = strict_mode
        self.report_only = report_only
        self.csp_violations = []
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize CSP testing middleware"""
        app.after_request(self.add_csp_headers)
        
        # Add CSP violation reporting endpoint
        @app.route('/api/csp-report', methods=['POST'])
        def csp_report():
            """Handle CSP violation reports"""
            from flask import request, jsonify
            
            try:
                violation_data = request.get_json()
                self.csp_violations.append({
                    'timestamp': time.time(),
                    'violation': violation_data,
                    'user_agent': request.headers.get('User-Agent'),
                    'ip': request.remote_addr
                })
                
                # Log violation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"CSP Violation: {violation_data}")
                
                return jsonify({'status': 'received'}), 200
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"CSP report error: {e}")
                return jsonify({'error': 'Invalid report'}), 400
    
    def add_csp_headers(self, response):
        """Add CSP headers to response"""
        try:
            from flask import g
            nonce = getattr(g, 'csp_nonce', secrets.token_urlsafe(16))
            
            if self.strict_mode:
                policy = StrictCSPConfig.get_strict_csp_policy(nonce)
            else:
                policy = StrictCSPConfig.get_development_csp_policy(nonce)
            
            if self.report_only:
                response.headers['Content-Security-Policy-Report-Only'] = policy
            else:
                response.headers['Content-Security-Policy'] = policy
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"CSP header error: {e}")
        
        return response
    
    def get_violations(self):
        """Get recorded CSP violations"""
        return self.csp_violations.copy()
    
    def clear_violations(self):
        """Clear recorded violations"""
        self.csp_violations.clear()