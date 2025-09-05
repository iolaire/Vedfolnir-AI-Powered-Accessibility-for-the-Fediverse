from flask import Blueprint, render_template
from flask_login import login_required
from app.services.platform_service import PlatformService

platform_bp = Blueprint('platform', __name__, url_prefix='/platform')

@platform_bp.route('/management')
@login_required
def management():
    """Platform management interface"""
    platform_service = PlatformService()
    platform_data = platform_service.get_user_platforms(include_stats=True)
    maintenance_status = platform_service.get_maintenance_status()
    
    return render_template(
        'platform_management.html',
        user_platforms=platform_data['platforms'],
        active_platform=platform_data['current_platform'],
        platform_stats=platform_data['platform_stats'],
        maintenance_status=maintenance_status
    )
