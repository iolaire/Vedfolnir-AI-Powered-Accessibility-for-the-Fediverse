# Copyright (C) 2025 iolaire mcfadden.
# Utility Decorators

from functools import wraps
from flask import g, redirect, url_for, current_app
from flask_login import current_user

def require_platform_context(func):
    """
    Decorator to ensure platform context exists
    Sets g.platform_connection_id for use in route
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get current session context
            from app.core.session.middleware.session_middleware_v2 import get_current_session_context
            context = get_current_session_context()
            
            # If session context doesn't have platform, try to get it from Redis using PlatformService
            if not context or not context.get('platform_connection_id'):
                try:
                    from app.services.platform.components.platform_service import PlatformService
                    platform_service = PlatformService()
                    platform_data = platform_service.get_user_platforms(include_stats=False)
                    current_platform = platform_data['current_platform']
                    
                    if current_platform:
                        # Set platform context in g for route use
                        g.platform_connection_id = current_platform.id
                        g.platform_context = {
                            'platform_connection_id': current_platform.id,
                            'platform_name': current_platform.name,
                            'platform_type': current_platform.platform_type,
                            'platform_instance_url': getattr(current_platform, 'instance_url', '')
                        }
                        current_app.logger.info(f"Platform context found via PlatformService: {current_platform.name}")
                        return func(*args, **kwargs)
                except Exception as e:
                    current_app.logger.error(f"Error getting platform from PlatformService: {e}")
            
            if not context or not context.get('platform_connection_id'):
                try:
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("No active platform connection found.", "Error")
                except Exception:
                    current_app.logger.warning("Could not send platform context error notification")
                
                return redirect(url_for('platform.management'))
            
            # Set platform context in g for route use
            g.platform_connection_id = context['platform_connection_id']
            g.platform_context = context
            
            return func(*args, **kwargs)
            
        except Exception as e:
            current_app.logger.error(f"Platform context validation error: {e}")
            return redirect(url_for('platform.management'))
    
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
