from flask import Blueprint, render_template, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from security.core.role_based_access import require_viewer_or_higher
from session_aware_decorators import with_session_error_handling, require_platform_context
from security.core.security_utils import sanitize_for_log
from app.utils.responses import success_response, error_response

review_bp = Blueprint('review', __name__, url_prefix='/review')

@review_bp.route('/')
@login_required
@require_viewer_or_higher
@require_platform_context
@with_session_error_handling
def index():
    """Review interface for generated captions"""
    try:
        from models import Image, ProcessingStatus
        from database import DatabaseManager
        from session_middleware_v2 import get_current_session_context
        
        db_manager = DatabaseManager()
        context = get_current_session_context()
        
        if not context or not context.get('platform_connection_id'):
            from notification_helpers import send_warning_notification
            send_warning_notification("No active platform connection found.", "Warning")
            return redirect(url_for('platform.management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Get images for review
        with db_manager.get_session() as session:
            images = session.query(Image).filter_by(
                user_id=current_user.id,
                platform_connection_id=platform_connection_id,
                processing_status=ProcessingStatus.COMPLETED
            ).order_by(Image.created_at.desc()).limit(20).all()
        
        return render_template('review.html', images=images)
        
    except Exception as e:
        current_app.logger.error(f"Error in review interface: {sanitize_for_log(str(e))}")
        from notification_helpers import send_error_notification
        send_error_notification("Error loading review interface.", "Error")
        return redirect(url_for('index'))

@review_bp.route('/<int:image_id>')
@login_required
@require_viewer_or_higher
@require_platform_context
@with_session_error_handling
def single(image_id):
    """Review single image"""
    try:
        from models import Image
        from database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            image = session.query(Image).filter_by(
                id=image_id,
                user_id=current_user.id
            ).first()
            
            if not image:
                from notification_helpers import send_error_notification
                send_error_notification("Image not found.", "Error")
                return redirect(url_for('review.index'))
        
        return render_template('review_single.html', image=image)
        
    except Exception as e:
        current_app.logger.error(f"Error in single review: {sanitize_for_log(str(e))}")
        return redirect(url_for('review.index'))

@review_bp.route('/batch')
@login_required
@require_platform_context
@with_session_error_handling
def batch():
    """Batch review interface"""
    try:
        from models import Image, ProcessingStatus
        from database import DatabaseManager
        from session_middleware_v2 import get_current_session_context
        
        db_manager = DatabaseManager()
        context = get_current_session_context()
        
        if not context or not context.get('platform_connection_id'):
            return redirect(url_for('platform.management'))
        
        platform_connection_id = context['platform_connection_id']
        
        # Get images for batch review
        with db_manager.get_session() as session:
            images = session.query(Image).filter_by(
                user_id=current_user.id,
                platform_connection_id=platform_connection_id,
                processing_status=ProcessingStatus.COMPLETED
            ).order_by(Image.created_at.desc()).limit(50).all()
        
        return render_template('batch_review.html', images=images)
        
    except Exception as e:
        current_app.logger.error(f"Error in batch review: {sanitize_for_log(str(e))}")
        return redirect(url_for('index'))
