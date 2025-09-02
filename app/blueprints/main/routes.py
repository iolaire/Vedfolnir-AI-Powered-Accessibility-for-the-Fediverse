from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole, PlatformConnection, User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Main dashboard with platform-aware statistics"""
    try:
        # Get unified session manager from app
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        db_manager = getattr(current_app, 'config', {}).get('db_manager')
        
        if not unified_session_manager or not db_manager:
            return render_template('index.html', stats={}, current_platform=None)
        
        # Use unified session manager for database queries
        with unified_session_manager.get_db_session() as db_session:
            # Check if user has accessible platform connections
            platforms_query = db_session.query(PlatformConnection).filter_by(is_active=True)
            user_platforms = platforms_query.count()
            
            # Admin users can access dashboard without platforms
            if user_platforms == 0 and current_user.role != UserRole.ADMIN:
                return redirect(url_for('auth.first_time_setup'))
            
            # Get basic statistics
            stats = db_manager.get_processing_stats()
            platform_dict = None
            
            if current_user.role == UserRole.ADMIN:
                stats['admin_mode'] = True
                
                # Optimized: Single query with aggregation instead of 3 separate queries
                from sqlalchemy import func, case
                admin_stats = db_session.query(
                    func.count(User.id).label('total_users'),
                    func.sum(case((User.is_active == True, 1), else_=0)).label('active_users'),
                    func.count(PlatformConnection.id).label('total_platforms')
                ).outerjoin(PlatformConnection).first()
                
                stats['total_users'] = admin_stats.total_users or 0
                stats['active_users'] = admin_stats.active_users or 0
                stats['total_platforms'] = admin_stats.total_platforms or 0
            
            # Notification config
            notification_config = {
                'page_type': 'user_dashboard',
                'enabled_types': ['system', 'caption', 'platform', 'maintenance'],
                'auto_hide': True,
                'max_notifications': 5,
                'position': 'top-right',
                'show_progress': False
            }
            
            return render_template('index.html', stats=stats, current_platform=platform_dict,
                                 notification_config=notification_config)
            
    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('index.html', stats={}, current_platform=None)

@main_bp.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images - redirect to static blueprint"""
    return redirect(url_for('static.serve_image', filename=filename))

@main_bp.route('/caption_generation')
@login_required
def caption_generation():
    """Redirect to caption generation"""
    return redirect(url_for('caption.generation'))

@main_bp.route('/index')
def index_redirect():
    """Redirect /index to main dashboard"""
    return redirect(url_for('main.index'))

@main_bp.route('/logout')
def logout_redirect():
    """Redirect to user management logout"""
    return redirect(url_for('user_management.logout'))

@main_bp.route('/profile')
def profile_redirect():
    """Redirect to user management profile"""
    return redirect(url_for('user_management.profile'))
