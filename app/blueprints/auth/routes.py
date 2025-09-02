from flask import Blueprint, render_template, redirect, url_for, make_response, current_app
from flask_login import login_required, current_user, logout_user
from models import UserRole, PlatformConnection
from unified_session_manager import unified_session_manager
from security.core.security_utils import sanitize_for_log
from app.utils.decorators import standard_route
from app.utils.error_handling import ErrorHandler

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/first_time_setup')
@login_required
@standard_route
def first_time_setup():
    """First-time platform setup for new users"""
    # Admin users don't need platform setup
    if current_user.role == UserRole.ADMIN:
        return redirect(url_for('index'))
    
    # Check if user already has platforms
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
    """Logout from all sessions"""
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    
    try:
        # Clean up user sessions
        if user_id:
            count = unified_session_manager.cleanup_user_sessions(user_id)
            current_app.logger.info(f"Cleaned up {count} sessions for user {sanitize_for_log(str(user_id))}")
        
        logout_user()
        ErrorHandler.handle_success("You have been logged out from all sessions", "logout_all")
        
    except Exception as e:
        current_app.logger.error(f"Error during logout_all: {sanitize_for_log(str(e))}")
        logout_user()
        from notification_helpers import send_error_notification
        send_error_notification("Error logging out from all sessions", "Error")
    
    # Create response with cleared session cookie
    response = make_response(redirect(url_for('user_management.login')))
    
    # Clear session cookie
    session_cookie_manager = getattr(current_app, 'session_cookie_manager', None)
    if session_cookie_manager:
        session_cookie_manager.clear_session_cookie(response)
    else:
        from flask import session
        session.clear()
        
        # Clear Redis session
        try:
            from redis_session_middleware import get_current_session_id
            current_session_id = get_current_session_id()
            if current_session_id and hasattr(unified_session_manager, 'destroy_session'):
                unified_session_manager.destroy_session(current_session_id)
        except Exception as redis_error:
            current_app.logger.warning(f"Could not clear Redis session: {redis_error}")
        
        # Clear session cookie manually
        response.set_cookie(
            current_app.config.get('SESSION_COOKIE_NAME', 'session'),
            '', expires=0, path='/', httponly=True, samesite='Lax'
        )
    
    return response
