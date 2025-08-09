# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Input validation utilities for security
"""
import re
import html
from typing import Any, Dict, Optional
from flask import request

class InputValidator:
    """Secure input validation and sanitization"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # Limit length
        value = value[:max_length]
        
        # HTML escape
        value = html.escape(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        return value.strip()
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = 0, max_val: int = 1000000) -> Optional[int]:
        """Validate integer input"""
        try:
            int_val = int(value)
            if min_val <= int_val <= max_val:
                return int_val
        except (ValueError, TypeError):
            pass
        return None
    
    @staticmethod
    def validate_boolean(value: Any) -> bool:
        """Validate boolean input"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    @staticmethod
    def validate_form_data(form_data: Dict[str, Any], schema: Dict[str, Dict]) -> Dict[str, Any]:
        """Validate form data against schema"""
        validated = {}
        
        for field, rules in schema.items():
            value = form_data.get(field)
            
            if value is None:
                if rules.get('required', False):
                    raise ValueError(f"Required field '{field}' is missing")
                continue
            
            field_type = rules.get('type', 'string')
            
            if field_type == 'string':
                max_length = rules.get('max_length', 1000)
                validated[field] = InputValidator.sanitize_string(value, max_length)
            elif field_type == 'integer':
                min_val = rules.get('min', 0)
                max_val = rules.get('max', 1000000)
                validated[field] = InputValidator.validate_integer(value, min_val, max_val)
            elif field_type == 'boolean':
                validated[field] = InputValidator.validate_boolean(value)
        
        return validated

def validate_request_data(schema: Dict[str, Dict]):
    """Decorator for request data validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                if request.method == 'POST':
                    if request.is_json:
                        data = request.get_json() or {}
                    else:
                        data = request.form.to_dict()
                    
                    validated_data = InputValidator.validate_form_data(data, schema)
                    request.validated_data = validated_data
                
                return func(*args, **kwargs)
            except ValueError as e:
                from flask import jsonify
                return jsonify({'success': False, 'error': str(e)}), 400
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
