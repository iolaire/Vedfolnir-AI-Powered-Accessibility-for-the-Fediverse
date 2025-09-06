# Copyright (C) 2025 iolaire mcfadden.
# Request Helper Utilities

from typing import Dict, Any, Optional, Union
from flask import request, current_app
import re
import html
import logging

def extract_form_data(field_mapping: Dict[str, tuple]) -> Dict[str, Any]:
    """
    Extract and validate form data with type conversion
    
    Args:
        field_mapping: Dict of {field_name: (type, default_value)}
        
    Returns:
        Dictionary of extracted and converted form data
        
    Example:
        data = extract_form_data({
            'batch_size': (int, 10),
            'quality_threshold': (float, 0.7),
            'enabled': (bool, False)
        })
    """
    result = {}
    
    for field_name, (field_type, default_value) in field_mapping.items():
        raw_value = request.form.get(field_name)
        
        if raw_value is None:
            result[field_name] = default_value
        else:
            try:
                if field_type == bool:
                    # Handle checkbox values
                    result[field_name] = raw_value.lower() in ('true', '1', 'on', 'yes')
                else:
                    result[field_name] = field_type(raw_value)
            except (ValueError, TypeError):
                result[field_name] = default_value
    
    return result

def get_form_int(field_name: str, default: int = 0) -> int:
    """Get integer value from form with default"""
    try:
        return int(request.form.get(field_name, default))
    except (ValueError, TypeError):
        return default

def get_form_float(field_name: str, default: float = 0.0) -> float:
    """Get float value from form with default"""
    try:
        return float(request.form.get(field_name, default))
    except (ValueError, TypeError):
        return default

def get_form_bool(field_name: str, default: bool = False) -> bool:
    """Get boolean value from form with default"""
    value = request.form.get(field_name, '').lower()
    return value in ('true', '1', 'on', 'yes') if value else default

def validate_request_origin(request_obj) -> bool:
    """
    Validate request origin for security purposes.
    
    Args:
        request_obj: Flask request object
        
    Returns:
        True if request origin is valid, False if suspicious
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Check for common attack patterns in headers
        user_agent = request_obj.headers.get('User-Agent', '').lower()
        
        # Block obvious bot/scanner patterns
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap',
            'burp', 'w3af', 'acunetix', 'nessus'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in user_agent:
                logger.warning(f"Suspicious user agent detected: {user_agent}")
                return False
        
        # Check for suspicious referrer patterns
        referrer = request_obj.headers.get('Referer', '').lower()
        if referrer and any(suspicious in referrer for suspicious in ['malware', 'phishing', 'spam']):
            logger.warning(f"Suspicious referrer detected: {referrer}")
            return False
        
        # Check for excessive header count (potential attack)
        if len(request_obj.headers) > 50:
            logger.warning(f"Excessive headers detected: {len(request_obj.headers)}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating request origin: {e}")
        return True  # Default to allowing request if validation fails

def sanitize_user_input(input_value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input using existing enhanced validation system.
    
    Args:
        input_value: Raw user input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string safe for use
    """
    if not input_value or not isinstance(input_value, str):
        return ""
    
    try:
        # Use existing enhanced input validation
        from enhanced_input_validation import EnhancedInputValidator
        
        # Truncate to maximum length
        sanitized = input_value[:max_length]
        
        # Use existing HTML sanitization
        sanitized = EnhancedInputValidator.sanitize_html(sanitized)
        
        # Additional SQL sanitization
        sanitized = EnhancedInputValidator.sanitize_sql(sanitized)
        
        # Strip whitespace
        sanitized = sanitized.strip()
        
        return sanitized
        
    except ImportError:
        # Fallback to basic sanitization if enhanced validation not available
        sanitized = input_value[:max_length]
        sanitized = html.escape(sanitized)
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        return sanitized.strip()

def validate_url_parameter(param_value: str, allowed_chars: str = None) -> bool:
    """
    Validate URL parameter for security.
    
    Args:
        param_value: Parameter value to validate
        allowed_chars: Additional allowed characters (default: alphanumeric + common safe chars)
        
    Returns:
        True if parameter is safe, False otherwise
    """
    if not param_value:
        return True
    
    # Default allowed characters: alphanumeric, dash, underscore, dot
    if allowed_chars is None:
        allowed_chars = r'[a-zA-Z0-9\-_\.]'
    
    # Check if parameter contains only allowed characters
    pattern = f'^{allowed_chars}+$'
    return bool(re.match(pattern, param_value))

def get_client_ip() -> str:
    """
    Get client IP address, considering proxy headers.
    
    Returns:
        Client IP address string
    """
    # Check for forwarded IP (behind proxy)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(',')[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # Fall back to remote address
    return request.remote_addr or 'unknown'
