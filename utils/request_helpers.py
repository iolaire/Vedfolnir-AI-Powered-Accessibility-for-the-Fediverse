# Copyright (C) 2025 iolaire mcfadden.
# Request Helper Utilities

from typing import Dict, Any, Optional, Union
from flask import request

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
