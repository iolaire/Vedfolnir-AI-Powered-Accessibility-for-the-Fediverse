# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Mode Decorators

Provides decorators for blocking job creation during maintenance mode
with proper HTTP responses and maintenance message display.
"""

import logging
from functools import wraps
from typing import Optional, Callable, Any
from flask import jsonify, request, current_app, render_template
from models import UserRole

logger = logging.getLogger(__name__)


def maintenance_mode_check(allow_admin_bypass: bool = True, 
                          custom_message: Optional[str] = None,
                          return_json: bool = None) -> Callable:
    """
    Decorator to check maintenance mode and block job creation
    
    Args:
        allow_admin_bypass: Allow admin users to bypass maintenance mode
        custom_message: Custom maintenance message (overrides configured reason)
        return_json: Force JSON response (auto-detected if None)
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            try:
                # Get maintenance mode service from app context
                maintenance_service = getattr(current_app, 'maintenance_service', None)
                if not maintenance_service:
                    # If no maintenance service available, allow operation
                    logger.warning("Maintenance service not available, allowing operation")
                    return f(*args, **kwargs)
                
                # Check if maintenance mode is enabled
                if not maintenance_service.is_maintenance_mode():
                    # Not in maintenance mode, proceed normally
                    return f(*args, **kwargs)
                
                # Maintenance mode is enabled - check for admin bypass
                if allow_admin_bypass:
                    try:
                        from flask_login import current_user
                        if hasattr(current_user, 'role') and current_user.role == UserRole.ADMIN:
                            logger.info(f"Admin user {current_user.id} bypassing maintenance mode for {f.__name__}")
                            return f(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Error checking admin bypass: {str(e)}")
                
                # Get maintenance reason
                if custom_message:
                    maintenance_reason = custom_message
                else:
                    maintenance_reason = maintenance_service.get_maintenance_reason()
                    if not maintenance_reason:
                        maintenance_reason = "System is currently under maintenance. Please try again later."
                
                # Determine response format
                should_return_json = return_json
                if should_return_json is None:
                    # Auto-detect based on request
                    should_return_json = (
                        request.is_json or 
                        'application/json' in request.headers.get('Accept', '') or
                        request.path.startswith('/api/')
                    )
                
                # Log maintenance mode block
                logger.info(f"Blocked {f.__name__} due to maintenance mode: {maintenance_reason}")
                
                if should_return_json:
                    # Return JSON response for API endpoints
                    return jsonify({
                        'success': False,
                        'error': 'Service temporarily unavailable',
                        'maintenance_mode': True,
                        'maintenance_reason': maintenance_reason,
                        'message': maintenance_reason
                    }), 503  # Service Unavailable
                else:
                    # Return HTML response for web endpoints
                    try:
                        return render_template(
                            'errors/maintenance.html',
                            maintenance_reason=maintenance_reason,
                            title='Service Under Maintenance'
                        ), 503
                    except Exception as template_error:
                        logger.error(f"Error rendering maintenance template: {str(template_error)}")
                        # Fallback to simple HTML response
                        html_response = f"""
                        <!DOCTYPE html>
                        <html>
                        <head><title>Service Under Maintenance</title></head>
                        <body>
                            <h1>Service Under Maintenance</h1>
                            <p>{maintenance_reason}</p>
                            <p><a href="/">Return to Home</a></p>
                        </body>
                        </html>
                        """
                        from flask import Response
                        return Response(html_response, status=503, mimetype='text/html')
                
            except Exception as e:
                logger.error(f"Error in maintenance mode check for {f.__name__}: {str(e)}")
                # On error, allow operation to proceed (fail open)
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def block_job_creation(allow_admin_bypass: bool = True,
                      custom_message: Optional[str] = None) -> Callable:
    """
    Decorator specifically for blocking job creation during maintenance mode
    
    Args:
        allow_admin_bypass: Allow admin users to bypass maintenance mode
        custom_message: Custom maintenance message
        
    Returns:
        Decorator function
    """
    return maintenance_mode_check(
        allow_admin_bypass=allow_admin_bypass,
        custom_message=custom_message or "Job creation is temporarily disabled during maintenance.",
        return_json=True  # Job creation endpoints typically return JSON
    )


def block_user_operations(allow_admin_bypass: bool = True,
                         custom_message: Optional[str] = None) -> Callable:
    """
    Decorator for blocking general user operations during maintenance mode
    
    Args:
        allow_admin_bypass: Allow admin users to bypass maintenance mode
        custom_message: Custom maintenance message
        
    Returns:
        Decorator function
    """
    return maintenance_mode_check(
        allow_admin_bypass=allow_admin_bypass,
        custom_message=custom_message or "This operation is temporarily unavailable during maintenance.",
        return_json=None  # Auto-detect response format
    )


def maintenance_status_info() -> dict:
    """
    Get current maintenance status information for templates and APIs
    
    Returns:
        Dictionary with maintenance status information
    """
    try:
        from flask import current_app
        
        maintenance_service = getattr(current_app, 'maintenance_service', None)
        if not maintenance_service:
            return {
                'maintenance_mode': False,
                'maintenance_reason': None,
                'service_available': False
            }
        
        maintenance_info = maintenance_service.get_maintenance_status()
        
        return {
            'maintenance_mode': maintenance_info.enabled,
            'maintenance_reason': maintenance_info.reason,
            'maintenance_status': maintenance_info.status.value,
            'last_updated': maintenance_info.last_updated.isoformat() if maintenance_info.last_updated else None,
            'service_available': True
        }
        
    except Exception as e:
        logger.error(f"Error getting maintenance status info: {str(e)}")
        return {
            'maintenance_mode': False,
            'maintenance_reason': None,
            'service_available': False,
            'error': str(e)
        }


# Template context processor for maintenance status
def inject_maintenance_status():
    """
    Template context processor to inject maintenance status into all templates
    
    Returns:
        Dictionary with maintenance status for templates
    """
    return {'maintenance_status': maintenance_status_info()}