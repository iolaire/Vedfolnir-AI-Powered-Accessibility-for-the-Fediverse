from flask import Blueprint, render_template, redirect, url_for, current_app, request
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

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    from forms.user_management_forms import ProfileEditForm
    from models import User
    from unified_session_manager import unified_session_manager
    from notification_helpers import send_success_notification, send_error_notification
    import logging
    
    logger = logging.getLogger(__name__)
    form = ProfileEditForm()
    
    # Pre-populate form with current user data for GET requests
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    
    # Handle form submission
    if request.method == 'POST':
        logger.info(f"POST request received. Form validation: {form.validate_on_submit()}")
        logger.info(f"Form data: first_name={form.first_name.data}, last_name={form.last_name.data}, email={form.email.data}")
        logger.info(f"Form errors: {form.errors}")
        
        if form.validate_on_submit():
            logger.info("Form validation successful, attempting to update profile")
            try:
                with unified_session_manager.get_db_session() as db_session:
                    # Update user profile
                    user = db_session.query(User).filter_by(id=current_user.id).first()
                    if user:
                        logger.info(f"Found user {user.username}, updating profile")
                        old_first_name = user.first_name
                        old_last_name = user.last_name
                        old_email = user.email
                        
                        user.first_name = form.first_name.data
                        user.last_name = form.last_name.data
                        user.email = form.email.data
                        
                        logger.info(f"Updating from {old_first_name} {old_last_name} ({old_email}) to {user.first_name} {user.last_name} ({user.email})")
                        
                        db_session.commit()
                        logger.info("Database commit successful")
                        
                        # Send success notification
                        send_success_notification("Profile updated successfully!", "Profile Updated")
                        logger.info(f"Profile updated for user {user.username}")
                    else:
                        logger.error(f"User not found with id {current_user.id}")
                        send_error_notification("User not found.", "Update Failed")
            except Exception as e:
                logger.error(f"Error updating profile: {e}")
                send_error_notification("Profile update failed due to a system error.", "Update Error")
        else:
            logger.warning("Form validation failed")
    
    # Prepare profile data for display
    profile_data = {
        'username': current_user.username,
        'full_name': f"{current_user.first_name} {current_user.last_name}".strip(),
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'email': current_user.email,
        'role': current_user.role.value if current_user.role else 'User',
        'created_at': current_user.created_at,
        'last_login': current_user.last_login,
        'is_active': current_user.is_active,
        'email_verified': current_user.email_verified,
        'data_processing_consent': current_user.data_processing_consent,
        'data_processing_consent_date': current_user.data_processing_consent_date,
        'platform_count': 0  # Will be populated if needed
    }
    
    return render_template('user_management/profile.html', form=form, profile_data=profile_data)
