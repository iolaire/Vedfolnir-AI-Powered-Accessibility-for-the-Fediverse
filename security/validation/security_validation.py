#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security Validation Script

Validates that all critical security measures are properly implemented.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Validates security implementation"""
    
    def __init__(self):
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    def validate_all(self) -> Dict:
        """Run all security validations"""
        logger.info("Starting security validation...")
        
        # 1. Validate CSRF Protection
        self._validate_csrf_protection()
        
        # 2. Validate Input Validation
        self._validate_input_validation()
        
        # 3. Validate Security Headers
        self._validate_security_headers()
        
        # 4. Validate Session Security
        self._validate_session_security()
        
        # 5. Validate Error Handling
        self._validate_error_handling()
        
        # 6. Validate Logging Security
        self._validate_logging_security()
        
        # 7. Validate Authentication
        self._validate_authentication()
        
        # 8. Validate File Security
        self._validate_file_security()
        
        return {
            'total_checks': len(self.validation_results['passed']) + len(self.validation_results['failed']),
            'passed': len(self.validation_results['passed']),
            'failed': len(self.validation_results['failed']),
            'warnings': len(self.validation_results['warnings']),
            'results': self.validation_results
        }
    
    def _validate_csrf_protection(self):
        """Validate CSRF protection implementation"""
        logger.info("Validating CSRF protection...")
        
        # Check if Flask-WTF CSRF is imported
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            if 'from flask_wtf.csrf import CSRFProtect' in content:
                self.validation_results['passed'].append("CSRF: Flask-WTF CSRFProtect imported")
            else:
                self.validation_results['failed'].append("CSRF: Flask-WTF CSRFProtect not imported")
            
            if 'csrf = CSRFProtect()' in content:
                self.validation_results['passed'].append("CSRF: CSRFProtect initialized")
            else:
                self.validation_results['failed'].append("CSRF: CSRFProtect not initialized")
            
            if 'WTF_CSRF_TIME_LIMIT' in content:
                self.validation_results['passed'].append("CSRF: Time limit configured")
            else:
                self.validation_results['warnings'].append("CSRF: Time limit not configured")
        
        # Check CSRF validation decorator
        security_middleware_path = Path('security_middleware.py')
        if security_middleware_path.exists():
            with open(security_middleware_path, 'r') as f:
                content = f.read()
            
            if 'validate_csrf' in content and 'ValidationError' in content:
                self.validation_results['passed'].append("CSRF: Proper validation implemented")
            else:
                self.validation_results['failed'].append("CSRF: Proper validation not implemented")
    
    def _validate_input_validation(self):
        """Validate input validation implementation"""
        logger.info("Validating input validation...")
        
        # Check if enhanced input validation exists
        enhanced_validation_path = Path('enhanced_input_validation.py')
        if enhanced_validation_path.exists():
            self.validation_results['passed'].append("Input Validation: Enhanced validation module exists")
            
            with open(enhanced_validation_path, 'r') as f:
                content = f.read()
            
            if 'sanitize_xss' in content:
                self.validation_results['passed'].append("Input Validation: XSS sanitization implemented")
            else:
                self.validation_results['failed'].append("Input Validation: XSS sanitization missing")
            
            if 'sanitize_sql' in content:
                self.validation_results['passed'].append("Input Validation: SQL sanitization implemented")
            else:
                self.validation_results['failed'].append("Input Validation: SQL sanitization missing")
            
            if 'validate_length' in content:
                self.validation_results['passed'].append("Input Validation: Length validation implemented")
            else:
                self.validation_results['failed'].append("Input Validation: Length validation missing")
        else:
            self.validation_results['failed'].append("Input Validation: Enhanced validation module missing")
    
    def _validate_security_headers(self):
        """Validate security headers implementation"""
        logger.info("Validating security headers...")
        
        security_middleware_path = Path('security_middleware.py')
        if security_middleware_path.exists():
            with open(security_middleware_path, 'r') as f:
                content = f.read()
            
            required_headers = [
                ('Content-Security-Policy', 'CSP header'),
                ('X-Content-Type-Options', 'Content type options header'),
                ('X-Frame-Options', 'Frame options header'),
                ('X-XSS-Protection', 'XSS protection header'),
                ('Strict-Transport-Security', 'HSTS header'),
                ('Referrer-Policy', 'Referrer policy header')
            ]
            
            for header, description in required_headers:
                if header in content:
                    self.validation_results['passed'].append(f"Security Headers: {description} implemented")
                else:
                    self.validation_results['failed'].append(f"Security Headers: {description} missing")
            
            # Check for unsafe CSP directives
            if "'unsafe-inline'" in content:
                self.validation_results['warnings'].append("Security Headers: CSP contains unsafe-inline")
            else:
                self.validation_results['passed'].append("Security Headers: No unsafe-inline in CSP")
            
            if "'unsafe-eval'" in content:
                self.validation_results['warnings'].append("Security Headers: CSP contains unsafe-eval")
            else:
                self.validation_results['passed'].append("Security Headers: No unsafe-eval in CSP")
        else:
            self.validation_results['failed'].append("Security Headers: Security middleware missing")
    
    def _validate_session_security(self):
        """Validate session security configuration"""
        logger.info("Validating session security...")
        
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            session_configs = [
                ('SESSION_COOKIE_SECURE', 'Secure cookie flag'),
                ('SESSION_COOKIE_HTTPONLY', 'HttpOnly cookie flag'),
                ('SESSION_COOKIE_SAMESITE', 'SameSite cookie attribute'),
                ('PERMANENT_SESSION_LIFETIME', 'Session timeout')
            ]
            
            for config, description in session_configs:
                if config in content:
                    self.validation_results['passed'].append(f"Session Security: {description} configured")
                else:
                    self.validation_results['failed'].append(f"Session Security: {description} not configured")
    
    def _validate_error_handling(self):
        """Validate secure error handling"""
        logger.info("Validating error handling...")
        
        # Check if secure error handlers exist
        error_handlers_path = Path('secure_error_handlers.py')
        if error_handlers_path.exists():
            self.validation_results['passed'].append("Error Handling: Secure error handlers module exists")
            
            with open(error_handlers_path, 'r') as f:
                content = f.read()
            
            error_codes = ['400', '401', '403', '404', '429', '500']
            for code in error_codes:
                if f'@app.errorhandler({code})' in content:
                    self.validation_results['passed'].append(f"Error Handling: {code} error handler implemented")
                else:
                    self.validation_results['failed'].append(f"Error Handling: {code} error handler missing")
        else:
            self.validation_results['failed'].append("Error Handling: Secure error handlers module missing")
        
        # Check if error templates exist
        error_templates_dir = Path('templates/errors')
        if error_templates_dir.exists():
            self.validation_results['passed'].append("Error Handling: Error templates directory exists")
            
            for code in ['400', '401', '403', '404', '429', '500']:
                template_path = error_templates_dir / f'{code}.html'
                if template_path.exists():
                    self.validation_results['passed'].append(f"Error Handling: {code} error template exists")
                else:
                    self.validation_results['failed'].append(f"Error Handling: {code} error template missing")
        else:
            self.validation_results['failed'].append("Error Handling: Error templates directory missing")
    
    def _validate_logging_security(self):
        """Validate secure logging implementation"""
        logger.info("Validating logging security...")
        
        # Check if secure logging module exists
        secure_logging_path = Path('secure_logging.py')
        if secure_logging_path.exists():
            self.validation_results['passed'].append("Logging Security: Secure logging module exists")
            
            with open(secure_logging_path, 'r') as f:
                content = f.read()
            
            if 'SecureLogger' in content:
                self.validation_results['passed'].append("Logging Security: SecureLogger class implemented")
            else:
                self.validation_results['failed'].append("Logging Security: SecureLogger class missing")
            
            if '_sanitize_message' in content:
                self.validation_results['passed'].append("Logging Security: Message sanitization implemented")
            else:
                self.validation_results['failed'].append("Logging Security: Message sanitization missing")
            
            if 'sensitive_patterns' in content:
                self.validation_results['passed'].append("Logging Security: Sensitive data patterns defined")
            else:
                self.validation_results['failed'].append("Logging Security: Sensitive data patterns missing")
        else:
            self.validation_results['failed'].append("Logging Security: Secure logging module missing")
    
    def _validate_authentication(self):
        """Validate authentication security"""
        logger.info("Validating authentication security...")
        
        web_app_path = Path('web_app.py')
        if web_app_path.exists():
            with open(web_app_path, 'r') as f:
                content = f.read()
            
            # Check for authentication decorators
            auth_decorators = ['@login_required', '@role_required', '@platform_required']
            for decorator in auth_decorators:
                if decorator in content:
                    self.validation_results['passed'].append(f"Authentication: {decorator} decorator used")
                else:
                    self.validation_results['warnings'].append(f"Authentication: {decorator} decorator not found")
            
            # Check for rate limiting on login
            if '@rate_limit' in content and 'login' in content:
                self.validation_results['passed'].append("Authentication: Rate limiting on login implemented")
            else:
                self.validation_results['warnings'].append("Authentication: Rate limiting on login not found")
            
            # Check for session cleanup on logout
            if 'session.clear' in content and 'logout' in content:
                self.validation_results['passed'].append("Authentication: Session cleanup on logout implemented")
            else:
                self.validation_results['failed'].append("Authentication: Session cleanup on logout missing")
    
    def _validate_file_security(self):
        """Validate file operation security"""
        logger.info("Validating file security...")
        
        # Check for file validation functions
        files_to_check = ['web_app.py', 'security_middleware.py', 'enhanced_input_validation.py']
        
        file_security_found = False
        for file_path in files_to_check:
            path = Path(file_path)
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()
                
                if 'sanitize_filename' in content or 'validate_filename' in content:
                    self.validation_results['passed'].append(f"File Security: Filename validation found in {file_path}")
                    file_security_found = True
        
        if not file_security_found:
            self.validation_results['failed'].append("File Security: Filename validation not found")
        
        # Check for path traversal protection
        path_protection_found = False
        for file_path in files_to_check:
            path = Path(file_path)
            if path.exists():
                with open(path, 'r') as f:
                    content = f.read()
                
                if '..' in content and ('replace' in content or 'sanitize' in content):
                    self.validation_results['passed'].append(f"File Security: Path traversal protection found in {file_path}")
                    path_protection_found = True
                    break
        
        if not path_protection_found:
            self.validation_results['warnings'].append("File Security: Path traversal protection not clearly implemented")

def main():
    """Main function to run security validation"""
    validator = SecurityValidator()
    results = validator.validate_all()
    
    print(f"\n{'='*60}")
    print("SECURITY VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Checks: {results['total_checks']}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print(f"Warnings: {results['warnings']} ⚠️")
    
    if results['passed'] > 0:
        print(f"\n{'='*60}")
        print("PASSED VALIDATIONS")
        print(f"{'='*60}")
        for item in results['results']['passed']:
            print(f"✅ {item}")
    
    if results['failed'] > 0:
        print(f"\n{'='*60}")
        print("FAILED VALIDATIONS")
        print(f"{'='*60}")
        for item in results['results']['failed']:
            print(f"❌ {item}")
    
    if results['warnings'] > 0:
        print(f"\n{'='*60}")
        print("WARNINGS")
        print(f"{'='*60}")
        for item in results['results']['warnings']:
            print(f"⚠️  {item}")
    
    # Calculate security score
    total_critical = results['passed'] + results['failed']
    if total_critical > 0:
        security_score = (results['passed'] / total_critical) * 100
        print(f"\n{'='*60}")
        print(f"SECURITY SCORE: {security_score:.1f}%")
        print(f"{'='*60}")
        
        if security_score >= 90:
            print("🛡️  EXCELLENT: Security implementation is comprehensive")
        elif security_score >= 80:
            print("🔒 GOOD: Security implementation is solid with minor gaps")
        elif security_score >= 70:
            print("⚠️  FAIR: Security implementation needs improvement")
        else:
            print("🚨 POOR: Security implementation has critical gaps")
    
    return results['failed']

if __name__ == '__main__':
    import sys
    failed_count = main()
    sys.exit(failed_count)