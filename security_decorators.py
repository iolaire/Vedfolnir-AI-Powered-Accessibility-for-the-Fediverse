# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Conditional Security Decorators

Provides decorators that can be toggled on/off via environment variables.
"""

import os
from functools import wraps

# Import original decorators
try:
    from security.core.security_middleware import rate_limit, validate_csrf_token, validate_input_length
    from enhanced_input_validation import enhanced_input_validation
except ImportError:
    # Fallback if security modules not available
    def rate_limit(**kwargs):
        def decorator(f):
            return f
        return decorator
    
    def validate_csrf_token(f):
        return f
    
    def validate_input_length(**kwargs):
        def decorator(f):
            return f
        return decorator
    
    def enhanced_input_validation(f):
        return f

# Security toggles
RATE_LIMITING_ENABLED = os.getenv('SECURITY_RATE_LIMITING_ENABLED', 'true').lower() == 'true'
CSRF_ENABLED = os.getenv('SECURITY_CSRF_ENABLED', 'true').lower() == 'true'
INPUT_VALIDATION_ENABLED = os.getenv('SECURITY_INPUT_VALIDATION_ENABLED', 'true').lower() == 'true'

def conditional_rate_limit(**kwargs):
    """Rate limiting decorator that can be toggled via environment variable"""
    def decorator(f):
        if RATE_LIMITING_ENABLED:
            return rate_limit(**kwargs)(f)
        return f
    return decorator

def conditional_validate_csrf_token(f):
    """CSRF validation decorator that can be toggled via environment variable"""
    if CSRF_ENABLED:
        return validate_csrf_token(f)
    return f

def conditional_validate_input_length(**kwargs):
    """Input length validation decorator that can be toggled via environment variable"""
    def decorator(f):
        if INPUT_VALIDATION_ENABLED:
            return validate_input_length(**kwargs)(f)
        return f
    return decorator

def conditional_enhanced_input_validation(f):
    """Enhanced input validation decorator that can be toggled via environment variable"""
    if INPUT_VALIDATION_ENABLED:
        return enhanced_input_validation(f)
    return f