from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from security.core.security_middleware import rate_limit
from app.utils.decorators import standard_route, platform_route
from app.utils.error_handling import ErrorHandler
from app.services.caption_service import CaptionService

caption_bp = Blueprint('caption', __name__, url_prefix='/caption')

@caption_bp.route('/generation')
@login_required
@platform_route
@rate_limit(limit=10, window_seconds=60)
def generation():
    """Caption generation page"""
    caption_service = CaptionService()
    
    data, error = caption_service.get_caption_generation_data()
    
    if error:
        return ErrorHandler.handle_warning(error, "caption_generation", "platform.management")
    
    return render_template('caption_generation.html', **data)

@caption_bp.route('/settings')
@login_required
@platform_route
def settings():
    """Caption settings page"""
    return render_template('caption_settings.html')
