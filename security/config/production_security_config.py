# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Production Security Configuration

Configures security settings for production environment including CSRF protection,
security headers, and monitoring.
"""

import os
import logging
from typing import Dict, Any
from flask import Flask

logger = logging.getLogger(__name__)


class ProductionSecurityConfig:
    """Production security configuration manager"""
    
    def __init__(self):
        """Initialize production security configuration"""
        self.csrf_config = {
            'WTF_CSRF_ENABLED': True,
            'WTF_CSRF_TIME_LIMIT': int(os.getenv('CSRF_TIME_LIMIT', '3600')),
            'WTF_CSRF_SSL_STRICT': os.getenv('FLASK_ENV') == 'production',
            'WTF_CSRF_CHECK_DEFAULT': True,
            'WTF_CSRF_METHODS': ['POST', 'PUT', 'PATCH', 'DELETE']
        }
        
        self.security_headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self'"
            )
        }
        
        self.monitoring_config = {
            'CSRF_VIOLATION_THRESHOLD': int(os.getenv('CSRF_VIOLATION_THRESHOLD', '10')),
            'MONITORING_ENABLED': os.getenv('SECURITY_MONITORING_ENABLED', 'true').lower() == 'true',
            'LOG_LEVEL': os.getenv('SECURITY_LOG_LEVEL', 'WARNING')
        }
    
    def configure_app(self, app: Flask) -> None:
        """Configure Flask app with production security settings"""
        logger.info("Configuring production security settings")
        
        # Configure CSRF protection
        for key, value in self.csrf_config.items():
            app.config[key] = value
        
        # Configure security headers
        @app.after_request
        def add_security_headers(response):
            for header, value in self.security_headers.items():
                response.headers[header] = value
            return response
        
        # Configure session security
        app.config.update({
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': 7200
        })
        
        logger.info("Production security configuration applied")
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate production security configuration"""
        return {
            'csrf_enabled': self.csrf_config['WTF_CSRF_ENABLED'],
            'security_headers_configured': len(self.security_headers) >= 5,
            'monitoring_enabled': self.monitoring_config['MONITORING_ENABLED'],
            'secret_key_set': bool(os.getenv('FLASK_SECRET_KEY')),
            'encryption_key_set': bool(os.getenv('PLATFORM_ENCRYPTION_KEY'))
        }
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security configuration status"""
        validation = self.validate_configuration()
        
        return {
            'csrf_protection': {
                'enabled': validation['csrf_enabled'],
                'time_limit': self.csrf_config['WTF_CSRF_TIME_LIMIT']
            },
            'security_headers': {
                'configured': validation['security_headers_configured'],
                'headers_count': len(self.security_headers)
            },
            'monitoring': {
                'enabled': validation['monitoring_enabled'],
                'violation_threshold': self.monitoring_config['CSRF_VIOLATION_THRESHOLD']
            },
            'overall_status': all(validation.values())
        }


def configure_production_security(app: Flask) -> ProductionSecurityConfig:
    """Configure production security for Flask app"""
    config = ProductionSecurityConfig()
    config.configure_app(app)
    return config