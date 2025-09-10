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

def handle_security_error(message: str, status_code: int = 403):
    """
    Handle security-related errors with appropriate logging and response.
    
    Args:
        message: Security error message
        status_code: HTTP status code (default: 403 Forbidden)
        
    Returns:
        Flask response tuple
    """
    from flask import current_app, request
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Log security incident
    client_ip = request.remote_addr if request else 'unknown'
    user_agent = request.headers.get('User-Agent', 'unknown') if request else 'unknown'
    
    logger.warning(f"Security error: {message} | IP: {client_ip} | User-Agent: {user_agent}")
    
    # Return appropriate error response
    if status_code == 403:
        return create_error_response(
            ErrorCodes.AUTHORIZATION_ERROR,
            "Access denied",
            None,
            403
        )
    elif status_code == 401:
        return create_error_response(
            ErrorCodes.AUTHENTICATION_ERROR,
            "Authentication required",
            None,
            401
        )
    else:
        return create_error_response(
            ErrorCodes.INTERNAL_ERROR,
            "Security violation detected",
            None,
            status_code
        )
