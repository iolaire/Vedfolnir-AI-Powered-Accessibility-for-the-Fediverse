# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Security utilities for the Vedfolnir application.

This module provides security-related utility functions including input sanitization,
log injection prevention, and other security measures.
"""

import re
from typing import Any, Optional

def sanitize_for_log(value: Any) -> str:
    """
    Sanitize a value for safe logging to prevent log injection attacks.
    
    This function removes or escapes potentially dangerous characters that could
    be used for log injection attacks, including newlines, carriage returns,
    and other control characters.
    
    Args:
        value: The value to sanitize (will be converted to string)
        
    Returns:
        Sanitized string safe for logging
    """
    if value is None:
        return "None"
    
    # Convert to string
    str_value = str(value)
    
    # Remove or replace dangerous characters
    # Replace newlines and carriage returns with spaces
    str_value = re.sub(r'[\r\n]', ' ', str_value)
    
    # Replace other control characters with spaces
    str_value = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', str_value)
    
    # Replace multiple spaces with single space
    str_value = re.sub(r'\s+', ' ', str_value)
    
    # Trim whitespace
    str_value = str_value.strip()
    
    # Limit length to prevent log flooding
    max_length = 200
    if len(str_value) > max_length:
        str_value = str_value[:max_length] + "..."
    
    return str_value

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal and other file system attacks.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename safe for file system operations
    """
    if not filename:
        return "unnamed"
    
    # Remove directory traversal attempts
    filename = filename.replace('..', '')
    filename = filename.replace('/', '_')
    filename = filename.replace('\\', '_')
    
    # Remove other potentially dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
    
    # Ensure it doesn't start with a dot (hidden file)
    if filename.startswith('.'):
        filename = '_' + filename[1:]
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        if ext:
            max_name_length = max_length - len(ext) - 1
            filename = name[:max_name_length] + '.' + ext
        else:
            filename = filename[:max_length]
    
    return filename or "unnamed"

def validate_url(url: str) -> bool:
    """
    Validate that a URL is safe and well-formed.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if the URL is valid and safe, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL format validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False
    
    # Check for dangerous schemes
    if url.lower().startswith(('javascript:', 'data:', 'vbscript:', 'file:')):
        return False
    
    # Check length
    if len(url) > 2048:  # Reasonable URL length limit
        return False
    
    return True

def sanitize_html_input(text: str) -> str:
    """
    Sanitize HTML input to prevent XSS attacks.
    
    Args:
        text: The text to sanitize
        
    Returns:
        Sanitized text with HTML entities escaped
    """
    if not text:
        return ""
    
    # Convert to string to handle any type
    text = str(text)
    
    # Use markupsafe for proper HTML escaping
    try:
        from markupsafe import escape
        return str(escape(text))
    except ImportError:
        # Fallback to basic HTML entity escaping
        import html
        return html.escape(text, quote=True)

def validate_image_extension(filename: str) -> bool:
    """
    Validate that a filename has a safe image extension.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if the extension is a safe image format, False otherwise
    """
    if not filename:
        return False
    
    safe_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', 
        '.bmp', '.tiff', '.tif', '.heic', '.heif', '.avif'
    }
    
    # Get the extension in lowercase
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    ext = '.' + ext if ext else ''
    
    return ext in safe_extensions

def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Safely truncate text to a maximum length.
    
    Args:
        text: The text to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Truncate and add suffix
    truncated = text[:max_length - len(suffix)]
    
    # Try to break at a word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # Only break at word if it's not too far back
        truncated = truncated[:last_space]
    
    return truncated + suffix

def validate_user_input(text: str, max_length: int = 1000, allow_html: bool = False) -> Optional[str]:
    """
    Validate and sanitize user input.
    
    Args:
        text: The text to validate
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML (will be escaped if False)
        
    Returns:
        Sanitized text if valid, None if invalid
    """
    if not text or not isinstance(text, str):
        return None
    
    # Remove null bytes and other dangerous characters
    text = text.replace('\x00', '')
    
    # Check length
    if len(text) > max_length:
        return None
    
    # Sanitize HTML if not allowed
    if not allow_html:
        text = sanitize_html_input(text)
    
    # Basic validation - ensure it's not just whitespace
    if not text.strip():
        return None
    
    return text.strip()

def generate_safe_id(prefix: str = "", length: int = 12) -> str:
    """
    Generate a safe identifier string.
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part
        
    Returns:
        Safe identifier string
    """
    import secrets
    import string
    
    # Use URL-safe characters
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    if prefix:
        # Sanitize prefix
        safe_prefix = re.sub(r'[^a-zA-Z0-9_-]', '_', prefix)
        return f"{safe_prefix}_{random_part}"
    
    return random_part

def is_safe_path(path: str, base_dir: str) -> bool:
    """
    Check if a file path is safe (within the base directory).
    
    Args:
        path: The file path to check
        base_dir: The base directory that should contain the path
        
    Returns:
        True if the path is safe, False otherwise
    """
    import os
    
    try:
        # Resolve both paths to absolute paths
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_dir)
        
        # Check if the path is within the base directory
        return abs_path.startswith(abs_base + os.sep) or abs_path == abs_base
    except (OSError, ValueError):
        return False

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging or display.
    
    Args:
        data: The sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to leave visible at the end
        
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * 8  # Return fixed-length mask for short data
    
    visible_part = data[-visible_chars:] if visible_chars > 0 else ""
    mask_length = max(8, len(data) - visible_chars)
    
    return mask_char * mask_length + visible_part