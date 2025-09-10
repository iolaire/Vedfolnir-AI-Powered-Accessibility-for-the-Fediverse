# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security Configuration for Vedfolnir

This module contains security-related configuration settings and constants
to ensure consistent security practices across the application.
"""

from dataclasses import dataclass
from typing import Dict, List, Set
import os

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    
    # Session Security
    SESSION_TIMEOUT_HOURS: int = 24
    REMEMBER_COOKIE_DURATION_DAYS: int = 30
    SESSION_COOKIE_SECURE: bool = True  # Only send over HTTPS
    SESSION_COOKIE_HTTPONLY: bool = True  # Prevent XSS access
    SESSION_COOKIE_SAMESITE: str = 'Lax'  # CSRF protection
    
    # Password Security
    MIN_PASSWORD_LENGTH: int = 8
    MAX_PASSWORD_LENGTH: int = 128
    REQUIRE_SPECIAL_CHARS: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    
    # Input Validation
    MAX_USERNAME_LENGTH: int = 64
    MAX_EMAIL_LENGTH: int = 120
    MAX_CAPTION_LENGTH: int = 500
    MAX_FILENAME_LENGTH: int = 255
    MAX_URL_LENGTH: int = 2048
    
    # Rate Limiting
    LOGIN_ATTEMPTS_LIMIT: int = 5
    LOGIN_LOCKOUT_DURATION_MINUTES: int = 15
    API_RATE_LIMIT_PER_MINUTE: int = 60
    
    # File Upload Security
    ALLOWED_IMAGE_EXTENSIONS: Set[str] = frozenset({
        '.jpg', '.jpeg', '.png', '.gif', '.webp', 
        '.bmp', '.tiff', '.tif', '.heic', '.heif', '.avif'
    })
    MAX_FILE_SIZE_MB: int = 10
    
    # Content Security Policy
    CSP_DIRECTIVES: Dict[str, str] = None
    
    # CORS Settings
    CORS_ORIGINS: List[str] = None
    CORS_METHODS: List[str] = None
    
    def __post_init__(self):
        """Initialize default values that depend on environment"""
        if self.CSP_DIRECTIVES is None:
            self.CSP_DIRECTIVES = {
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com",  # Allow inline scripts, Bootstrap JS, Socket.IO, and unpkg for axe-core
                'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",   # Allow inline styles, Google Fonts, and Bootstrap CSS
                'img-src': "'self' data: https:",        # Allow images from self, data URLs, and HTTPS
                'font-src': "'self' https://fonts.gstatic.com",  # Allow Google Fonts
                'connect-src': "'self' https://fonts.googleapis.com https://fonts.gstatic.com",  # Allow font loading
                'frame-ancestors': "'none'",             # Prevent clickjacking
                'base-uri': "'self'",
                'form-action': "'self'"
            }
        
        if self.CORS_ORIGINS is None:
            self.CORS_ORIGINS = ['http://localhost:5000', 'https://localhost:5000']
        
        if self.CORS_METHODS is None:
            self.CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    
    def get_csp_header(self) -> str:
        """Generate Content Security Policy header value"""
        return '; '.join([f"{directive} {value}" for directive, value in self.CSP_DIRECTIVES.items()])
    
    def is_secure_environment(self) -> bool:
        """Check if running in a secure environment (HTTPS)"""
        return os.getenv('FLASK_ENV') == 'production' or os.getenv('HTTPS', '').lower() == 'true'

# Global security configuration instance
security_config = SecurityConfig()

# Security headers for Flask responses
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
}

# Sensitive data patterns for log sanitization
SENSITIVE_PATTERNS = [
    r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
    r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
    r'key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
    r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
    r'authorization["\']?\s*[:=]\s*["\']?([^"\'\\s]+)',
]

# Allowed HTML tags for user input (if HTML is ever allowed)
ALLOWED_HTML_TAGS = {
    'b', 'i', 'u', 'em', 'strong', 'br', 'p'
}

# Allowed HTML attributes
ALLOWED_HTML_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title'],
}