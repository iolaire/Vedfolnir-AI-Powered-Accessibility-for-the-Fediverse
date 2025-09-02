from flask import Blueprint, render_template, redirect, url_for, make_response, current_app
from flask_login import login_required, current_user, logout_user
from models import UserRole, PlatformConnection
from session_aware_decorators import with_session_error_handling
from unified_session_manager import unified_session_manager
from security.core.security_utils import sanitize_for_log

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/first_time_setup')
@login_required
@with_session_error_handling
def first_time_setup():
    """First-time platform setup for new users"""
    # Admin users don't need platform setup - redirect to index
    if current_user.role == UserRole.ADMIN:
        return redirect(url_for('index'))
    
    # Check if user already has platforms - redirect if they do
    with unified_session_manager.get_db_session() as session:
        user_platforms = session.query(PlatformConnection).filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        if user_platforms > 0:
            return redirect(url_for('index'))
    
    return render_template('first_time_setup.html')

@auth_bp.route('/logout_all')
@login_required
def logout_all():
    """Logout from all sessions with database session management"""
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    
    try:
        # Database session cleanup: Clean up all user sessions
        if user_id:
            # Clear all database session records for the user
            count = unified_session_manager.cleanup_user_sessions(user_id)
            current_app.logger.info(f"Cleaned up {count} database sessions for user {sanitize_for_log(str(user_id))}")
        
        # Log out the user from Flask-Login
        logout_user()
        
        # Send info notification
        from notification_helpers import send_info_notification
        send_info_notification("You have been logged out from all sessions", "Information")
        
    except Exception as e:
        current_app.logger.error(f"Error during logout_all: {sanitize_for_log(str(e))}")
        # Still proceed with logout even if cleanup fails
        logout_user()
        # Send error notification
        from notification_helpers import send_error_notification
        send_error_notification("Error logging out from all sessions", "Error")
    
    # Create response with cleared session cookie
    response = make_response(redirect(url_for('user_management.login')))
    
    # Clear session cookie based on session type
    session_cookie_manager = getattr(current_app, 'session_cookie_manager', None)
    if session_cookie_manager:
        # Using fallback session manager - clear cookie
        session_cookie_manager.clear_session_cookie(response)
        current_app.logger.debug("Cleared session cookie using session_cookie_manager")
    else:
        # Using Redis sessions - clear Flask session and Redis session
        from flask import session
        session.clear()
        
        # Clear Redis session if we have a session ID
        try:
            from redis_session_middleware import get_current_session_id
            current_session_id = get_current_session_id()
            if current_session_id and hasattr(unified_session_manager, 'destroy_session'):
                unified_session_manager.destroy_session(current_session_id)
                current_app.logger.debug(f"Destroyed Redis session: {current_session_id}")
        except Exception as redis_error:
            current_app.logger.warning(f"Could not clear Redis session: {redis_error}")
        
        # Clear the session cookie manually for Redis sessions
        response.set_cookie(
            current_app.config.get('SESSION_COOKIE_NAME', 'session'),
            '',
            expires=0,
            path=current_app.config.get('SESSION_COOKIE_PATH', '/'),
            domain=current_app.config.get('SESSION_COOKIE_DOMAIN'),
            secure=current_app.config.get('SESSION_COOKIE_SECURE', False),
            httponly=current_app.config.get('SESSION_COOKIE_HTTPONLY', True),
            samesite=current_app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
        )
        current_app.logger.debug("Cleared session cookie manually for Redis sessions")
    
    return response
