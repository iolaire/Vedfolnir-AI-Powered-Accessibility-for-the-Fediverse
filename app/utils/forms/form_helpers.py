# Copyright (C) 2025 iolaire mcfadden.
# Form Helper Utilities

from typing import Dict, Any, Optional
from flask import request

def populate_form_from_dict(form, data_dict: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None):
    """
    Populate form fields from dictionary with defaults
    
    Args:
        form: WTForm instance
        data_dict: Dictionary containing form data
        defaults: Default values for missing keys
    """
    if not data_dict:
        return
    
    defaults = defaults or {}
    
    for field_name in form._fields:
        if hasattr(form, field_name):
            field = getattr(form, field_name)
            value = data_dict.get(field_name, defaults.get(field_name))
            if value is not None:
                field.data = value

def create_settings_form_with_data(form_class, user_settings: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None):
    """
    Create form instance populated with user settings
    
    Args:
        form_class: Form class to instantiate
        user_settings: User settings dictionary
        defaults: Default values
        
    Returns:
        Populated form instance
    """
    form = form_class(request.form if request.method == 'POST' else None)
    if user_settings:
        populate_form_from_dict(form, user_settings, defaults)
    return form

def validate_and_extract_form_data(form, required_fields: Optional[list] = None) -> Dict[str, Any]:
    """
    Validate form and extract data with error handling
    
    Args:
        form: WTForm instance
        required_fields: List of required field names
        
    Returns:
        Dictionary of form data
        
    Raises:
        ValueError: If validation fails
    """
    if not form.validate():
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field}: {error}")
        raise ValueError(f"Form validation failed: {'; '.join(error_messages)}")
    
    # Extract form data
    form_data = {}
    for field_name in form._fields:
        if hasattr(form, field_name):
            field = getattr(form, field_name)
            form_data[field_name] = field.data
    
    # Check required fields
    if required_fields:
        missing_fields = [field for field in required_fields if not form_data.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return form_data

# Common form defaults
CAPTION_SETTINGS_DEFAULTS = {
    'max_posts_per_run': 50,
    'max_caption_length': 500,
    'optimal_min_length': 80,
    'optimal_max_length': 200,
    'reprocess_existing': False,
    'processing_delay': 1.0
}
