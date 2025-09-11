# Copyright (C) 2025 iolaire mcfadden.
# Utility Decorators

from functools import wraps
from flask import g, redirect, url_for, current_app, jsonify
from flask_login import current_user

def require_platform_context(func):
    """
    Decorator to ensure platform context exists
    Sets g.session_context for use in route
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Initialize g.session_context if it doesn't exist
            if not hasattr(g, 'session_context'):
                g.session_context = {}
            
            # Get current session context
            try:
                from app.core.session.middleware.session_middleware_v2 import get_current_session_context
                context = get_current_session_context()
                if context:
                    g.session_context.update(context)
            except Exception as e:
                current_app.logger.debug(f"Could not get session context: {e}")
            
            # If session context doesn't have platform, try to get it from PlatformService
            if not g.session_context.get('platform_connection_id'):
                try:
                    from app.services.platform.components.platform_service import PlatformService
                    platform_service = PlatformService()
                    platform_data = platform_service.get_user_platforms(include_stats=False)
                    current_platform = platform_data.get('current_platform')
                    
                    if current_platform:
                        # Handle both object and dictionary cases
                        if isinstance(current_platform, dict):
                            platform_id = current_platform.get('id')
                            platform_name = current_platform.get('name')
                            platform_type = current_platform.get('platform_type')
                            platform_instance_url = current_platform.get('instance_url', '')
                        else:
                            platform_id = getattr(current_platform, 'id', None)
                            platform_name = getattr(current_platform, 'name', None)
                            platform_type = getattr(current_platform, 'platform_type', None)
                            platform_instance_url = getattr(current_platform, 'instance_url', '')
                        
                        # Update g.session_context
                        g.session_context.update({
                            'platform_connection_id': platform_id,
                            'platform_name': platform_name,
                            'platform_type': platform_type,
                            'platform_instance_url': platform_instance_url
                        })
                        
                        # Set platform_connection_id for backward compatibility
                        g.platform_connection_id = platform_id
                        
                        current_app.logger.info(f"Platform context found via PlatformService: {platform_name}")
                    else:
                        # No platform available
                        return jsonify({
                            'success': False,
                            'error': 'No platform connection available. Please set up a platform connection first.',
                            'redirect': url_for('platform.manage')
                        }), 400
                        
                except Exception as e:
                    current_app.logger.error(f"Error getting platform context: {e}")
                    return jsonify({
                        'success': False,
                        'error': 'Failed to get platform context',
                        'details': str(e)
                    }), 500
            
            return func(*args, **kwargs)
            
        except Exception as e:
            current_app.logger.error(f"Error in require_platform_context decorator: {e}")
            return jsonify({
                'success': False,
                'error': 'Platform context error',
                'details': str(e)
            }), 500
    
    return wrapper

def get_platform_context_or_redirect():
    """
    Utility function to get platform context or redirect
    Returns: (platform_connection_id, context) or None if redirect needed
    """
    try:
        from app.core.session.middleware.session_middleware_v2 import get_current_session_context
        context = get_current_session_context()
        
        if not context or not context.get('platform_connection_id'):
            try:
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("No active platform connection found.", "Error")
            except Exception:
                pass
            return None
        
        return context['platform_connection_id'], context
        
    except Exception as e:
        current_app.logger.error(f"Platform context error: {e}")
        return None
