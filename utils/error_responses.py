# Copyright (C) 2025 iolaire mcfadden.
# Standardized Error Response Helper

from flask import jsonify
from typing import Dict, Any, Optional

class ErrorCodes:
    """Standardized error codes"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

def create_error_response(
    code: str,
    message: str,
    details: Optional[str] = None,
    status_code: int = 500
) -> tuple:
    """
    Create standardized error response
    
    Args:
        code: Error code from ErrorCodes
        message: User-friendly error message
        details: Technical details for debugging (optional)
        status_code: HTTP status code
        
    Returns:
        tuple: (response, status_code)
    """
    response_data = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    
    if details:
        response_data["error"]["details"] = details
    
    return jsonify(response_data), status_code

def validation_error(message: str, details: Optional[str] = None):
    """Create validation error response"""
    return create_error_response(
        ErrorCodes.VALIDATION_ERROR,
        message,
        details,
        400
    )

def configuration_error(message: str, details: Optional[str] = None):
    """Create configuration error response"""
    return create_error_response(
        ErrorCodes.CONFIGURATION_ERROR,
        message,
        details,
        500
    )

def internal_error(message: str = "Internal server error", details: Optional[str] = None):
    """Create internal error response"""
    return create_error_response(
        ErrorCodes.INTERNAL_ERROR,
        message,
        details,
        500
    )
