from flask import Blueprint, render_template
from flask_login import login_required

platform_bp = Blueprint('platform', __name__, url_prefix='/platform')

@platform_bp.route('/management')
@login_required
def management():
    """Platform management interface"""
    return render_template('platform_management.html', platforms=[], current_platform=None)
