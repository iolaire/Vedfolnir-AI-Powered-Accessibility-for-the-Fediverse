# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Input Validation and Sanitization for User Management

Provides comprehensive input validation and sanitization with security event logging.
"""

import re
import html
import logging
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union
from functools import wraps
from flask import request, abort, g
from sqlalchemy.orm import Session
from app.core.security.monitoring.security_event_logger import get_security_event_logger, SecurityEventType
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message: str, field: str = None, validation_type: str = None):
        self.message = message
        self.field = field
        self.validation_type = validation_type
        super().__init__(message)

class InputSanitizer:
    """Advanced input sanitization with security focus"""
    
    # Dangerous patterns for different attack types
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bUNION\s+SELECT)",
        r"(\b(EXEC|EXECUTE)\s*\()",
        r"(\bxp_cmdshell\b)",
        r"(\bsp_executesql\b)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
        r"<applet[^>]*>.*?</applet>",
        r"<meta[^>]*>",
        r"<link[^>]*>",
        r"javascript:",
        r"vbscript:",
        r"data:text/html",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"@import",
        r"<style[^>]*>.*?</style>",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"..%2f",
        r"..%5c",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"\b(cat|ls|dir|type|copy|move|del|rm|chmod|chown|ps|kill|wget|curl)\b",
        r"(\||&&|;|`|\$\(|\${)",
    ]
    
    @staticmethod
    def sanitize_text(
        text: str,
        max_length: int = 10000,
        allow_html: bool = False,
        strip_unicode: bool = True,
        normalize_whitespace: bool = True,
        skip_malicious_check: bool = False
    ) -> str:
        """
        Comprehensive text sanitization
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags
            strip_unicode: Whether to strip dangerous unicode characters
            normalize_whitespace: Whether to normalize whitespace
            skip_malicious_check: Whether to skip malicious pattern checking (for passwords)
            
        Returns:
            Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Length check
        if len(text) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)", validation_type="length")
        
        # Unicode normalization and dangerous character removal
        if strip_unicode:
            text = InputSanitizer._strip_dangerous_unicode(text)
        
        # Normalize whitespace
        if normalize_whitespace:
            text = InputSanitizer._normalize_whitespace(text)
        
        # HTML handling
        if not allow_html:
            text = html.escape(text, quote=True)
        else:
            text = InputSanitizer._sanitize_html(text)
        
        # Check for malicious patterns (skip for passwords and other sensitive fields)
        if not skip_malicious_check:
            InputSanitizer._check_malicious_patterns(text)
        
        return text.strip()
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize and validate email address"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required", validation_type="required")
        
        # Basic sanitization
        email = email.strip().lower()
        
        # Length check
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long", validation_type="length")
        
        # Basic format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format", validation_type="format")
        
        # Check for dangerous patterns
        if any(pattern in email for pattern in ['..', '@.', '.@', '@@']):
            raise ValidationError("Invalid email format", validation_type="format")
        
        return email
    
    @staticmethod
    def sanitize_username(username: str) -> str:
        """Sanitize and validate username"""
        if not username or not isinstance(username, str):
            raise ValidationError("Username is required", validation_type="required")
        
        # Basic sanitization
        username = username.strip()
        
        # Length check
        if len(username) < 3:
            raise ValidationError("Username too short (minimum 3 characters)", validation_type="length")
        if len(username) > 50:
            raise ValidationError("Username too long (maximum 50 characters)", validation_type="length")
        
        # Character validation
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username contains invalid characters", validation_type="format")
        
        # Reserved usernames
        reserved = ['admin', 'root', 'system', 'api', 'www', 'mail', 'ftp', 'test', 'guest', 'anonymous']
        if username.lower() in reserved:
            raise ValidationError("Username is reserved", validation_type="reserved")
        
        return username
    
    @staticmethod
    def sanitize_password(password: str, min_length: int = 8) -> str:
        """Validate password strength (without malicious pattern checking)"""
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required", validation_type="required")
        
        # Length check
        if len(password) < min_length:
            raise ValidationError(f"Password too short (minimum {min_length} characters)", validation_type="length")
        if len(password) > 128:
            raise ValidationError("Password too long (maximum 128 characters)", validation_type="length")
        
        # Strength validation (optional - can be disabled for admin passwords)
        import os
        if os.getenv('PASSWORD_STRENGTH_VALIDATION', 'true').lower() == 'true':
            strength_checks = [
                (r'[a-z]', "Password must contain lowercase letters"),
                (r'[A-Z]', "Password must contain uppercase letters"),
                (r'[0-9]', "Password must contain numbers"),
                (r'[!@#$%^&*(),.?":{}|<>]', "Password must contain special characters"),
            ]
            
            for pattern, message in strength_checks:
                if not re.search(pattern, password):
                    raise ValidationError(message, validation_type="strength")
            
            # Check for common weak patterns
            weak_patterns = [
                r'(.)\1{3,}',  # Repeated characters
                r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
                r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
            ]
            
            for pattern in weak_patterns:
                if re.search(pattern, password.lower()):
                    raise ValidationError("Password contains weak patterns", validation_type="strength")
        
        # Note: We don't check for malicious patterns in passwords as they may contain
        # legitimate special characters that could be flagged as SQL injection
        return password
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename or not isinstance(filename, str):
            return "unnamed_file"
        
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
        
        # Remove leading dots and spaces
        filename = filename.lstrip('. ')
        
        # Ensure it's not empty
        if not filename:
            filename = "unnamed_file"
        
        # Length limit
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            if ext:
                max_name_length = 255 - len(ext) - 1
                filename = name[:max_name_length] + '.' + ext
            else:
                filename = filename[:255]
        
        return filename
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize and validate URL"""
        if not url or not isinstance(url, str):
            raise ValidationError("URL is required", validation_type="required")
        
        url = url.strip()
        
        # Length check
        if len(url) > 2048:
            raise ValidationError("URL too long", validation_type="length")
        
        # Scheme validation
        if not url.startswith(('http://', 'https://')):
            raise ValidationError("URL must use HTTP or HTTPS", validation_type="scheme")
        
        # Basic URL format validation
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        if not re.match(url_pattern, url):
            raise ValidationError("Invalid URL format", validation_type="format")
        
        # Check for dangerous schemes in the URL content
        dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:', 'ftp:']
        url_lower = url.lower()
        for scheme in dangerous_schemes:
            if scheme in url_lower:
                raise ValidationError("URL contains dangerous scheme", validation_type="security")
        
        return url
    
    @staticmethod
    def _strip_dangerous_unicode(text: str) -> str:
        """Remove dangerous unicode characters"""
        # Normalize unicode
        text = unicodedata.normalize('NFKC', text)
        
        # Remove control characters except common whitespace
        allowed_control = {'\t', '\n', '\r'}
        text = ''.join(char for char in text if not unicodedata.category(char).startswith('C') or char in allowed_control)
        
        # Remove zero-width characters
        zero_width_chars = ['\u200b', '\u200c', '\u200d', '\ufeff']
        for char in zero_width_chars:
            text = text.replace(char, '')
        
        return text
    
    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize whitespace characters"""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Replace unicode whitespace with regular space
        text = re.sub(r'[\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]', ' ', text)
        
        return text
    
    @staticmethod
    def _sanitize_html(text: str) -> str:
        """Sanitize HTML content"""
        try:
            import bleach
            
            # Allowed tags and attributes for rich text
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            allowed_attributes = {
                '*': ['class'],
                'a': ['href', 'title'],
            }
            
            return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
            
        except ImportError:
            # Fallback to basic HTML escaping
            return html.escape(text, quote=True)
    
    @staticmethod
    def _check_malicious_patterns(text: str):
        """Check for malicious patterns in text"""
        text_lower = text.lower()
        
        # Check SQL injection patterns
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                raise ValidationError("Input contains potentially malicious SQL patterns", validation_type="security")
        
        # Check XSS patterns
        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                raise ValidationError("Input contains potentially malicious script patterns", validation_type="security")
        
        # Check path traversal patterns
        for pattern in InputSanitizer.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                raise ValidationError("Input contains path traversal patterns", validation_type="security")
        
        # Check command injection patterns (less strict for regular text)
        dangerous_commands = ['rm -rf', 'del /f', 'format c:', 'shutdown', 'reboot']
        for cmd in dangerous_commands:
            if cmd in text_lower:
                raise ValidationError("Input contains potentially dangerous commands", validation_type="security")

class EnhancedInputValidator:
    """Enhanced input validator with security event logging"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.security_logger = get_security_event_logger(db_session)
        self.sanitizer = InputSanitizer()
    
    def validate_form_data(self, form_data: Dict[str, Any], validation_rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate form data according to rules
        
        Args:
            form_data: Form data to validate
            validation_rules: Validation rules for each field
            
        Returns:
            Sanitized and validated form data
        """
        validated_data = {}
        errors = []
        
        for field_name, value in form_data.items():
            try:
                rules = validation_rules.get(field_name, {})
                validated_value = self._validate_field(field_name, value, rules)
                validated_data[field_name] = validated_value
                
            except ValidationError as e:
                errors.append(f"{field_name}: {e.message}")
                self._log_validation_failure(field_name, e.validation_type or "unknown", str(e))
        
        if errors:
            raise ValidationError("; ".join(errors), validation_type="form_validation")
        
        return validated_data
    
    def validate_json_data(self, json_data: Dict[str, Any], validation_rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Validate JSON data according to rules"""
        return self.validate_form_data(json_data, validation_rules)
    
    def _validate_field(self, field_name: str, value: Any, rules: Dict[str, Any]) -> Any:
        """Validate a single field according to its rules"""
        # Handle None/empty values
        if value is None or (isinstance(value, str) and not value.strip()):
            if rules.get('required', False):
                raise ValidationError(f"{field_name} is required", field_name, "required")
            return value
        
        # Convert to string for text processing
        if not isinstance(value, str):
            value = str(value)
        
        # Apply field-specific validation
        field_type = rules.get('type', 'text')
        
        if field_type == 'email':
            return self.sanitizer.sanitize_email(value)
        elif field_type == 'username':
            return self.sanitizer.sanitize_username(value)
        elif field_type == 'password':
            min_length = rules.get('min_length', 8)
            return self.sanitizer.sanitize_password(value, min_length)
        elif field_type == 'url':
            return self.sanitizer.sanitize_url(value)
        elif field_type == 'filename':
            return self.sanitizer.sanitize_filename(value)
        else:
            # Default text validation
            max_length = rules.get('max_length', 10000)
            allow_html = rules.get('allow_html', False)
            skip_malicious_check = rules.get('skip_malicious_check', False)
            return self.sanitizer.sanitize_text(value, max_length, allow_html, skip_malicious_check=skip_malicious_check)
    
    def _log_validation_failure(self, field_name: str, validation_type: str, error_message: str):
        """Log validation failures for security monitoring"""
        try:
            user_id = None
            if hasattr(g, 'current_user') and g.current_user:
                user_id = g.current_user.id
            
            self.security_logger.log_input_validation_failure(
                field_name=field_name,
                validation_type=validation_type,
                user_id=user_id
            )
            
            logger.warning(f"Input validation failed: {field_name} - {validation_type} - {sanitize_for_log(error_message)}")
            
        except Exception as e:
            logger.error(f"Error logging validation failure: {e}")

def validate_user_input(validation_rules: Dict[str, Dict[str, Any]]):
    """
    Decorator for validating user input
    
    Args:
        validation_rules: Dictionary of field validation rules
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check if input validation is enabled
                import os
                if os.getenv('SECURITY_INPUT_VALIDATION_ENABLED', 'true').lower() != 'true':
                    # Input validation is disabled, skip validation
                    return f(*args, **kwargs)
                
                # Get database session
                from app.core.database.core.database_manager import DatabaseManager
                from config import Config
                config = Config()
                db_manager = DatabaseManager(config)
                db_session = db_manager.get_session()
                
                validator = EnhancedInputValidator(db_session)
                
                # Validate form data
                if request.method in ['POST', 'PUT', 'PATCH'] and request.form:
                    try:
                        validated_data = validator.validate_form_data(dict(request.form), validation_rules)
                        g.validated_form_data = validated_data
                    except ValidationError as e:
                        abort(400, description=f"Validation error: {e.message}")
                
                # Validate JSON data
                if request.is_json and request.get_json():
                    try:
                        validated_data = validator.validate_json_data(request.get_json(), validation_rules)
                        g.validated_json_data = validated_data
                    except ValidationError as e:
                        abort(400, description=f"Validation error: {e.message}")
                
                db_session.close()
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in input validation decorator: {e}")
                # On error, allow the request but log the issue
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Common validation rule sets
USER_REGISTRATION_RULES = {
    'username': {'type': 'username', 'required': True},
    'email': {'type': 'email', 'required': True},
    'password': {'type': 'password', 'required': True, 'min_length': 8},
    'first_name': {'type': 'text', 'max_length': 100, 'required': False},
    'last_name': {'type': 'text', 'max_length': 100, 'required': False},
}

USER_LOGIN_RULES = {
    'username_or_email': {'type': 'text', 'required': True, 'max_length': 254},
    'password': {'type': 'text', 'required': True, 'max_length': 128, 'skip_malicious_check': True},
}

PROFILE_UPDATE_RULES = {
    'first_name': {'type': 'text', 'max_length': 100, 'required': False},
    'last_name': {'type': 'text', 'max_length': 100, 'required': False},
    'email': {'type': 'email', 'required': True},
}

PASSWORD_CHANGE_RULES = {
    'current_password': {'type': 'text', 'required': True, 'max_length': 128, 'skip_malicious_check': True},
    'new_password': {'type': 'password', 'required': True, 'min_length': 8},
    'confirm_password': {'type': 'text', 'required': True, 'max_length': 128, 'skip_malicious_check': True},
}

ADMIN_USER_CREATE_RULES = {
    'username': {'type': 'username', 'required': True},
    'email': {'type': 'email', 'required': True},
    'role': {'type': 'text', 'required': True, 'max_length': 20},
    'first_name': {'type': 'text', 'max_length': 100, 'required': False},
    'last_name': {'type': 'text', 'max_length': 100, 'required': False},
}