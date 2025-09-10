# Copyright (C) 2025 iolaire mcfadden.
# Standardized Response Helper Utilities

from flask import jsonify
from typing import Dict, Any, Optional

def success_response(data: Optional[Dict[str, Any]] = None, message: str = "Success") -> tuple:
    """Create standardized success response"""
    response_data = {
        "success": True,
        "message": message
    }
    
    if data:
        response_data["data"] = data
    
    return jsonify(response_data), 200

def error_response(message: str, status_code: int = 400, details: Optional[str] = None) -> tuple:
    """Simple error response helper"""
    response_data = {
        "success": False,
        "error": message
    }
    
    if details:
        response_data["details"] = details
    
    return jsonify(response_data), status_code

def validation_error_response(form_errors: Dict[str, list]) -> tuple:
    """Create response from form validation errors"""
    error_messages = []
    for field, errors in form_errors.items():
        for error in errors:
            error_messages.append(f"{field}: {error}")
    
    return error_response("Form validation failed: " + "; ".join(error_messages), 400)
