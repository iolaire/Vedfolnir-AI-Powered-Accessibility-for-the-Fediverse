from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from security.core.role_based_access import require_viewer_or_higher, platform_access_required
from session_aware_decorators import with_session_error_handling
from security.core.security_utils import sanitize_for_log
from app.utils.responses import success_response, error_response

platform_bp = Blueprint('platform', __name__, url_prefix='/platform')

@platform_bp.route('/management')
@login_required
@require_viewer_or_higher
@with_session_error_handling
def management():
    """Platform management interface using shared platform identification"""
    try:
        from platform_utils.platform_identification import identify_user_platform
        from database import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Use shared 5-step platform identification
        result = identify_user_platform(
            current_user.id,
            current_app.config.get('redis_platform_manager'),
            db_manager,
            include_stats=True
        )
        
        # Get maintenance status for UI display
        maintenance_status_dict = None
        try:
            from enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
            from maintenance_response_helper import MaintenanceResponseHelper
            from configuration_service import ConfigurationService
            
            config_service = ConfigurationService()
            maintenance_service = EnhancedMaintenanceModeService(config_service, db_manager)
            response_helper = MaintenanceResponseHelper()
            
            maintenance_status = maintenance_service.get_maintenance_status()
            maintenance_status_dict = response_helper.create_maintenance_status_dict(maintenance_status)
        except Exception as e:
            current_app.logger.error(f"Error getting maintenance status for platform management: {str(e)}")
        
        # Platform management always shows the interface, even if no platforms
        return render_template('platform_management.html', 
                             platforms=result.user_platforms or [],
                             current_platform=result.current_platform,
                             platform_stats=result.platform_stats or {},
                             maintenance_status=maintenance_status_dict)
                             
    except Exception as e:
        current_app.logger.error(f"Error in platform management: {sanitize_for_log(str(e))}")
        # Send error notification
        from notification_helpers import send_error_notification
        send_error_notification("An error occurred while loading platform management.", "Error")
        return redirect(url_for('index'))

@platform_bp.route('/switch/<int:platform_id>')
@login_required
@require_viewer_or_higher
@platform_access_required
@with_session_error_handling
def switch_platform(platform_id):
    """Switch to a different platform using database sessions"""
    try:
        from request_scoped_session_manager import request_session_manager
        from models import PlatformConnection
        
        # Verify the platform belongs to the current user
        with request_session_manager.session_scope() as db_session:
            platform = db_session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not platform:
                from notification_helpers import send_error_notification
                send_error_notification("Platform not found or access denied.", "Error")
                return redirect(url_for('platform.management'))
            
            # Update session platform context
            from session_middleware_v2 import update_session_platform
            update_session_platform(platform_id)
            
            # Send success notification
            from notification_helpers import send_success_notification
            send_success_notification(f"Switched to platform: {platform.name}", "Success")
            
            return redirect(url_for('index'))
            
    except Exception as e:
        current_app.logger.error(f"Error switching platform: {sanitize_for_log(str(e))}")
        from notification_helpers import send_error_notification
        send_error_notification("Error switching platform.", "Error")
        return redirect(url_for('platform.management'))
