from functools import wraps
from flask import current_app, redirect, url_for
from flask_login import current_user
from app.core.security.core.security_middleware import rate_limit, validate_csrf_token
from app.core.security.core.role_based_access import require_viewer_or_higher
from session_aware_decorators import with_session_error_handling, require_platform_context
from app.core.security.core.security_utils import sanitize_for_log

def standard_route(func):
    """Standard route decorator combining common patterns"""
    @wraps(func)
    @with_session_error_handling
    @require_viewer_or_higher
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def platform_route(func):
    """Platform-required route decorator"""
    @wraps(func)
    @require_platform_context
    @standard_route
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def api_route(func):
    """API route decorator with CSRF and rate limiting"""
    @wraps(func)
    @validate_csrf_token
    @rate_limit(limit=20, window_seconds=60)
    @standard_route
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def safe_execute(operation_name):
    """Decorator for safe operation execution with logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Error in {operation_name}: {sanitize_for_log(str(e))}")
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification(f"Error in {operation_name}", "Error")
                return redirect(url_for('main.index'))
        return wrapper
    return decorator
