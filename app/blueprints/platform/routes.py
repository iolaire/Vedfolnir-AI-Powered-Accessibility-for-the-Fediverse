from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from app.utils.decorators import standard_route, safe_execute
from app.utils.error_handling import ErrorHandler
from app.services.platform_service import PlatformService

platform_bp = Blueprint('platform', __name__, url_prefix='/platform')

@platform_bp.route('/management')
@login_required
@standard_route
@safe_execute('platform_management')
def management():
    """Platform management interface"""
    platform_service = PlatformService()
    
    # Get platform data
    platform_data = platform_service.get_user_platforms(include_stats=True)
    
    # Get maintenance status
    maintenance_status = platform_service.get_maintenance_status()
    
    return render_template('platform_management.html', 
                         platforms=platform_data['platforms'],
                         current_platform=platform_data['current_platform'],
                         platform_stats=platform_data['platform_stats'],
                         maintenance_status=maintenance_status)

@platform_bp.route('/switch/<int:platform_id>')
@login_required
@standard_route
def switch_platform(platform_id):
    """Switch to a different platform"""
    platform_service = PlatformService()
    
    success, message = platform_service.switch_platform(platform_id)
    
    if success:
        ErrorHandler.handle_success(message, "switch_platform")
        return redirect(url_for('index'))
    else:
        return ErrorHandler.handle_error(
            message, 
            "switch_platform",
            "platform.management",
            message
        )
