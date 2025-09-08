# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Input Validation Middleware

Provides comprehensive input validation and sanitization.
"""

import re
import html
import bleach
from urllib.parse import quote
from flask import request, abort
from werkzeug.exceptions import BadRequest

class EnhancedInputValidator:
    """Enhanced input validation and sanitization"""
    
    # Allowed HTML tags for rich text fields
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
    ALLOWED_ATTRIBUTES = {}
    
    @staticmethod
    def sanitize_html(text):
        """Sanitize HTML content"""
        if not text:
            return ""
        return bleach.clean(text, tags=EnhancedInputValidator.ALLOWED_TAGS, 
                          attributes=EnhancedInputValidator.ALLOWED_ATTRIBUTES)
    
    @staticmethod
    def sanitize_sql(text):
        """Sanitize text to prevent SQL injection"""
        if not text:
            return ""
        
        # Remove dangerous SQL keywords and characters
        dangerous_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\bUNION\s+SELECT)",
            r"(\b(EXEC|EXECUTE)\s*\()",
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def sanitize_xss(text):
        """Sanitize text to prevent XSS"""
        if not text:
            return ""
        
        # HTML encode dangerous characters
        text = html.escape(text)
        
        # Remove javascript: URLs
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Remove on* event handlers
        text = re.sub(r'\bon\w+\s*=', '', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def validate_length(text, max_length=10000):
        """Validate text length"""
        if text and len(text) > max_length:
            raise BadRequest(f"Input too long (max {max_length} characters)")
        return text
    
    @staticmethod
    def validate_filename(filename):
        """Validate and sanitize filename"""
        if not filename:
            return "unknown"
        
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Limit length
        if len(filename) > 100:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:95] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url):
        """Validate URL format and scheme"""
        if not url:
            return False
        
        # Only allow http and https
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Basic URL validation
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        return re.match(pattern, url) is not None

def enhanced_input_validation(f):
    """Decorator for enhanced input validation"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        validator = EnhancedInputValidator()
        
        # Validate form data
        if request.form:
            for key, value in request.form.items():
                # Length validation
                validator.validate_length(value)
                
                # XSS sanitization
                request.form = request.form.copy()
                request.form[key] = validator.sanitize_xss(value)
        
        # Validate JSON data
        if request.is_json:
            data = request.get_json()
            if data:
                _validate_json_recursive(data, validator)
        
        return f(*args, **kwargs)
    return decorated_function

def _validate_json_recursive(data, validator, depth=0):
    """Recursively validate JSON data"""
    if depth > 10:  # Prevent deep nesting attacks
        raise BadRequest("JSON data too deeply nested")
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                validator.validate_length(value)
                data[key] = validator.sanitize_xss(value)
            elif isinstance(value, (dict, list)):
                _validate_json_recursive(value, validator, depth + 1)
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                validator.validate_length(item)
                data[i] = validator.sanitize_xss(item)
            elif isinstance(item, (dict, list)):
                _validate_json_recursive(item, validator, depth + 1)
