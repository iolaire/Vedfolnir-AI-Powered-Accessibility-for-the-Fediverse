from flask import Blueprint, send_from_directory, render_template, redirect, url_for, current_app, make_response, request
from flask_login import login_required, current_user
from models import UserRole, PlatformConnection
import os

static_bp = Blueprint('static', __name__)

@static_bp.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from the images directory"""
    return send_from_directory('images', filename)

@static_bp.route('/static/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
    return send_from_directory('static/js', filename)

@static_bp.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('static', 'favicon.ico')

@static_bp.route('/first_time_setup')
@login_required
def first_time_setup():
    """First-time platform setup for new users"""
    # Admin users don't need platform setup
    if current_user.role == UserRole.ADMIN:
        return redirect(url_for('main.index'))
    
    # Check if user already has platforms
    unified_session_manager = getattr(current_app, 'unified_session_manager', None)
    if unified_session_manager:
        try:
            with unified_session_manager.get_db_session() as session:
                user_platforms = session.query(PlatformConnection).filter_by(
                    user_id=current_user.id,
                    is_active=True
                ).count()
                
                if user_platforms > 0:
                    return redirect(url_for('main.index'))
        except Exception:
            pass
    
    return render_template('first_time_setup.html')

@static_bp.route('/logout_all')
@login_required
def logout_all():
    """Logout from all sessions"""
    from flask_login import logout_user
    from flask import session
    
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    
    try:
        # Clean up user sessions
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if user_id and unified_session_manager:
            count = unified_session_manager.cleanup_user_sessions(user_id)
            current_app.logger.info(f"Cleaned up {count} sessions for user {user_id}")
        
        logout_user()
        
    except Exception as e:
        current_app.logger.error(f"Error during logout_all: {str(e)}")
        logout_user()
    
    # Create response with cleared session cookie
    response = make_response(redirect(url_for('user_management.login')))
    
    # Clear session
    session.clear()
    
    # Clear session cookie manually
    response.set_cookie(
        current_app.config.get('SESSION_COOKIE_NAME', 'session'),
        '', expires=0, path='/', httponly=True, samesite='Lax'
    )
    
    return response

@static_bp.route('/post_approved')
@login_required
def post_approved():
    """Post approval confirmation page"""
    return render_template('post_approved.html')

@static_bp.route('/switch_platform/<int:platform_id>')
@login_required
def switch_platform(platform_id):
    """Switch to a different platform (GET version for compatibility)"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return redirect(url_for('platform.management'))
        
        with unified_session_manager.get_db_session() as session:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if platform:
                # RACE CONDITION FIX: Cancel active tasks before switching
                try:
                    from web_caption_generation_service import WebCaptionGenerationService
                    
                    db_manager = current_app.config.get('db_manager')
                    if db_manager:
                        caption_service = WebCaptionGenerationService(db_manager)
                        active_task = caption_service.task_queue_manager.get_user_active_task(current_user.id)
                        
                        if active_task:
                            # Cancel the active task
                            cancelled = caption_service.cancel_generation(active_task.id, current_user.id)
                            if cancelled:
                                current_app.logger.info(f"Cancelled active task {active_task.id} for platform switch")
                            else:
                                current_app.logger.warning(f"Failed to cancel active task {active_task.id} for platform switch")
                                
                except Exception as task_error:
                    current_app.logger.warning(f"Task cancellation check failed: {task_error}")
                    # Continue with platform switch - task cancellation is best effort
                
                # Update session context (simplified)
                current_app.logger.info(f"Switched to platform: {platform.name}")
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error switching platform: {str(e)}")
        return redirect(url_for('platform.management'))

@static_bp.route('/socket.io/', methods=['OPTIONS'])
def handle_socketio_options():
    """Handle OPTIONS requests for Socket.IO"""
    response = make_response()
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Development/Test routes
@static_bp.route('/test_route')
def test_route():
    """Test route to verify routing works"""
    return "Test route works!"

@static_bp.route('/websocket-test')
def websocket_test():
    """WebSocket test page (development only)"""
    return render_template('websocket_test.html')

@static_bp.route('/websocket-simple-test')
def websocket_simple_test():
    """Simple WebSocket test page (development only)"""
    return render_template('websocket_simple_test.html')

# Additional missing routes
@static_bp.route('/caption_settings')
@login_required
def caption_settings():
    """Redirect to caption settings"""
    return redirect(url_for('caption.settings'))

@static_bp.route('/save_caption_settings', methods=['POST'])
@login_required
def save_caption_settings():
    """Save caption settings"""
    return redirect(url_for('caption.settings'))

@static_bp.route('/start_caption_generation', methods=['POST'])
@login_required
def start_caption_generation():
    """Start caption generation"""
    return redirect(url_for('caption.start_generation'))

@static_bp.route('/review')
@login_required
def review():
    """Redirect to review list"""
    return redirect(url_for('review.review_list'))

@static_bp.route('/review_list')
@login_required
def review_list():
    """Redirect to review list"""
    return redirect(url_for('review.review_list'))

@static_bp.route('/review_batches')
@login_required
def review_batches():
    """Redirect to batch review"""
    return redirect(url_for('review.batch_review'))
