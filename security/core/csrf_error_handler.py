# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Error Handler

Comprehensive CSRF validation error handling with user-friendly responses,
form data preservation, and security event logging.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from flask import request, jsonify, render_template, redirect, url_for, flash
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import Forbidden
from security.core.security_utils import sanitize_for_log
from security.core.csrf_token_manager import get_csrf_token_manager, CSRFValidationContext
from security.monitoring.csrf_security_metrics import track_csrf_violation

logger = logging.getLogger(__name__)


class CSRFErrorHandler:
    """Handles CSRF validation failures with comprehensive error processing"""
    
    def __init__(self):
        """Initialize CSRF error handler"""
        self.error_messages = {
            'missing_token': 'Security token is missing. Please refresh the page and try again.',
            'invalid_token': 'Security token is invalid. Please refresh the page and try again.',
            'expired_token': 'Security token has expired. Please refresh the page and try again.',
            'token_mismatch': 'Security token mismatch. Please refresh the page and try again.',
            'general_csrf_error': 'Security validation failed. Please refresh the page and try again.'
        }
        
        self.retry_guidance = {
            'refresh_page': 'Refresh the page and try your action again.',
            'clear_cache': 'Clear your browser cache and cookies, then try again.',
            'different_browser': 'Try using a different browser or incognito mode.',
            'contact_support': 'If the problem persists, please contact support.'
        }
    
    def handle_csrf_failure(self, error: Exception, context: Optional[CSRFValidationContext] = None) -> Tuple[Any, int]:
        """Handle CSRF validation failure
        
        Args:
            error: CSRF error exception
            context: Validation context information
            
        Returns:
            Tuple of (response, status_code)
        """
        try:
            # Create validation context if not provided
            if context is None:
                context = CSRFValidationContext(
                    request_method=request.method,
                    endpoint=request.endpoint or 'unknown',
                    user_id=getattr(request, 'user_id', None)
                )
            
            # Determine error type
            error_type = self._classify_csrf_error(error)
            context.error_details = error_type
            context.validation_result = False
            
            # Log security violation
            self.log_csrf_violation(error, context)
            
            # Preserve form data if possible
            preserved_data = self.preserve_form_data(request.form.to_dict() if request.form else {})
            
            # Generate appropriate response
            if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                return self._create_json_error_response(error_type, context, preserved_data)
            else:
                return self._create_html_error_response(error_type, context, preserved_data)
                
        except Exception as handler_error:
            logger.error(f"Error in CSRF error handler: {sanitize_for_log(str(handler_error))}")
            return self._create_fallback_error_response()
    
    def _classify_csrf_error(self, error: Exception) -> str:
        """Classify the type of CSRF error
        
        Args:
            error: CSRF error exception
            
        Returns:
            Error type string
        """
        error_str = str(error).lower()
        
        if 'missing' in error_str or 'required' in error_str:
            return 'missing_token'
        elif 'expired' in error_str or 'timeout' in error_str:
            return 'expired_token'
        elif 'invalid' in error_str or 'malformed' in error_str:
            return 'invalid_token'
        elif 'mismatch' in error_str or 'session' in error_str:
            return 'token_mismatch'
        else:
            return 'general_csrf_error'
    
    def _create_json_error_response(self, error_type: str, context: CSRFValidationContext, 
                                  preserved_data: Optional[str]) -> Tuple[Dict[str, Any], int]:
        """Create JSON error response for AJAX requests
        
        Args:
            error_type: Type of CSRF error
            context: Validation context
            preserved_data: Preserved form data
            
        Returns:
            Tuple of (json_response, status_code)
        """
        # Generate new CSRF token for retry
        try:
            csrf_manager = get_csrf_token_manager()
            new_token = csrf_manager.generate_token()
        except Exception as e:
            logger.warning(f"Failed to generate new CSRF token: {e}")
            new_token = None
        
        response_data = {
            'success': False,
            'error': 'CSRF validation failed',
            'error_type': error_type,
            'message': self.error_messages.get(error_type, self.error_messages['general_csrf_error']),
            'retry_guidance': self._get_retry_guidance(error_type),
            'timestamp': datetime.now().isoformat(),
            'request_id': context.session_id[:8] if context.session_id else 'unknown'
        }
        
        # Add new token for retry if available
        if new_token:
            response_data['new_csrf_token'] = new_token
        
        # Add preserved data if available
        if preserved_data:
            response_data['preserved_data'] = preserved_data
        
        return response_data, 403
    
    def _create_html_error_response(self, error_type: str, context: CSRFValidationContext, 
                                  preserved_data: Optional[str]) -> Tuple[Any, int]:
        """Create HTML error response for form submissions
        
        Args:
            error_type: Type of CSRF error
            context: Validation context
            preserved_data: Preserved form data
            
        Returns:
            Tuple of (html_response, status_code)
        """
        # Flash error message
        error_message = self.error_messages.get(error_type, self.error_messages['general_csrf_error'])
        flash(error_message, 'error')
        
        # Add retry guidance
        retry_guidance = self._get_retry_guidance(error_type)
        if retry_guidance:
            flash(f"Suggestion: {retry_guidance}", 'info')
        
        # Note: Form data preservation disabled in database session mode
        # TODO: Implement database-based form data preservation if needed
        if preserved_data:
            flash('Please re-enter your form data and try submitting again.', 'info')
        
        # Redirect to referrer or home page
        redirect_url = request.referrer or url_for('index')
        
        try:
            return redirect(redirect_url), 403
        except Exception:
            # Fallback to error template
            return render_template('errors/csrf_error.html', 
                                 error_type=error_type,
                                 error_message=error_message,
                                 retry_guidance=retry_guidance), 403
    
    def _create_fallback_error_response(self) -> Tuple[Any, int]:
        """Create fallback error response when error handler fails
        
        Returns:
            Tuple of (response, status_code)
        """
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Security validation failed',
                'message': 'Please refresh the page and try again.'
            }), 403
        else:
            flash('Security validation failed. Please refresh the page and try again.', 'error')
            return redirect(request.referrer or url_for('index')), 403
    
    def _get_retry_guidance(self, error_type: str) -> str:
        """Get retry guidance for specific error type
        
        Args:
            error_type: Type of CSRF error
            
        Returns:
            Retry guidance string
        """
        guidance_map = {
            'missing_token': self.retry_guidance['refresh_page'],
            'invalid_token': self.retry_guidance['refresh_page'],
            'expired_token': self.retry_guidance['refresh_page'],
            'token_mismatch': self.retry_guidance['clear_cache'],
            'general_csrf_error': self.retry_guidance['refresh_page']
        }
        
        return guidance_map.get(error_type, self.retry_guidance['refresh_page'])
    
    def log_csrf_violation(self, error: Exception, context: CSRFValidationContext) -> None:
        """Log CSRF security violation
        
        Args:
            error: CSRF error exception
            context: Validation context
        """
        try:
            # Create security log entry
            log_data = {
                'event_type': 'csrf_violation',
                'error_type': context.error_details,
                'request_method': context.request_method,
                'endpoint': context.endpoint,
                'user_id': context.user_id,
                'session_id': context.session_id[:8] if context.session_id else 'unknown',
                'ip_address': sanitize_for_log(request.remote_addr) if request else 'unknown',
                'user_agent': sanitize_for_log(request.headers.get('User-Agent', 'unknown')) if request else 'unknown',
                'timestamp': context.timestamp.isoformat(),
                'error_message': sanitize_for_log(str(error))
            }
            
            # Log to security logger
            logger.warning(f"CSRF violation: {json.dumps(log_data)}")
            
            # Track violation in CSRF security metrics
            try:
                track_csrf_violation(
                    violation_type=context.error_details or 'general_csrf_error',
                    source_ip=log_data['ip_address'],
                    endpoint=context.endpoint,
                    user_agent=log_data['user_agent'],
                    user_id=context.user_id,
                    session_id=context.session_id or '',
                    request_method=context.request_method,
                    error_details={'error_message': str(error)}
                )
            except Exception as metrics_error:
                logger.warning(f"Failed to track CSRF violation in metrics: {sanitize_for_log(str(metrics_error))}")
            
            # Log to security audit system if available
            try:
                from security.logging.security_audit_logger import get_security_audit_logger
                security_logger = get_security_audit_logger()
                security_logger.log_security_violation(
                    violation_type='csrf_validation_failure',
                    details=log_data,
                    severity='MEDIUM'
                )
            except ImportError:
                logger.debug("Security audit logger not available")
            
        except Exception as log_error:
            logger.error(f"Failed to log CSRF violation: {sanitize_for_log(str(log_error))}")
    
    def preserve_form_data(self, form_data: Dict[str, Any]) -> Optional[str]:
        """Preserve form data for recovery after CSRF error
        
        Args:
            form_data: Form data to preserve
            
        Returns:
            Serialized form data or None
        """
        try:
            if not form_data:
                return None
            
            # Filter out sensitive fields
            sensitive_fields = {'password', 'csrf_token', 'secret', 'token', 'key'}
            filtered_data = {
                key: value for key, value in form_data.items()
                if not any(sensitive in key.lower() for sensitive in sensitive_fields)
            }
            
            if not filtered_data:
                return None
            
            # Serialize data
            preserved_data = json.dumps(filtered_data, ensure_ascii=False)
            
            # Limit size to prevent abuse
            if len(preserved_data) > 10000:  # 10KB limit
                logger.warning("Form data too large to preserve")
                return None
            
            return preserved_data
            
        except Exception as e:
            logger.warning(f"Failed to preserve form data: {sanitize_for_log(str(e))}")
            return None
    
    def recover_preserved_data(self) -> Optional[Dict[str, Any]]:
        """Recover preserved form data (disabled in database session mode)
        
        Returns:
            None (form data preservation disabled)
        """
        # Form data preservation disabled in database session mode
        # TODO: Implement database-based form data preservation if needed
        return None
    
    def generate_retry_guidance(self, context: CSRFValidationContext) -> str:
        """Generate specific retry guidance based on context
        
        Args:
            context: Validation context
            
        Returns:
            Specific retry guidance
        """
        guidance_parts = []
        
        # Add method-specific guidance
        if context.request_method == 'POST':
            guidance_parts.append("Refresh the page before resubmitting the form")
        elif context.request_method in ['PUT', 'PATCH', 'DELETE']:
            guidance_parts.append("Refresh the page before retrying the operation")
        
        # Add endpoint-specific guidance
        if context.endpoint and 'login' in context.endpoint:
            guidance_parts.append("Clear your browser cookies and try logging in again")
        elif context.endpoint and 'admin' in context.endpoint:
            guidance_parts.append("Ensure you have proper administrative permissions")
        
        # Add general guidance
        guidance_parts.append("If the problem persists, try using a different browser")
        
        return ". ".join(guidance_parts) + "."


# Global CSRF error handler instance
_csrf_error_handler: Optional[CSRFErrorHandler] = None


def get_csrf_error_handler() -> CSRFErrorHandler:
    """Get the global CSRF error handler instance
    
    Returns:
        CSRFErrorHandler instance
    """
    global _csrf_error_handler
    if _csrf_error_handler is None:
        _csrf_error_handler = CSRFErrorHandler()
    return _csrf_error_handler


def register_csrf_error_handlers(app):
    """Register CSRF error handlers with Flask app
    
    Args:
        app: Flask application instance
    """
    csrf_handler = get_csrf_error_handler()
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """Handle Flask-WTF CSRF errors"""
        return csrf_handler.handle_csrf_failure(error)
    
    @app.errorhandler(403)
    def handle_forbidden_error(error):
        """Handle 403 Forbidden errors (may include CSRF failures)"""
        # Check if this is a CSRF-related 403
        if 'csrf' in str(error).lower() or 'token' in str(error).lower():
            return csrf_handler.handle_csrf_failure(error)
        
        # Handle other 403 errors normally
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Access forbidden',
                'message': 'You do not have permission to access this resource.'
            }), 403
        else:
            return render_template('errors/403.html'), 403
    
    # Store handler in app for access by other components
    app.csrf_error_handler = csrf_handler
    
    logger.info("CSRF error handlers registered")
    return csrf_handler