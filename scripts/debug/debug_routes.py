# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug routes for testing session authentication
"""

from flask import Blueprint, jsonify, session, current_app
from flask_login import current_user

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

@debug_bp.route('/session')
def debug_session():
    """Debug endpoint to check session state"""
    
    session_data = dict(session)
    
    # Check current_user state
    user_info = {
        'is_authenticated': current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False,
        'is_anonymous': current_user.is_anonymous if hasattr(current_user, 'is_anonymous') else True,
        'user_id': getattr(current_user, 'id', None),
        'username': getattr(current_user, 'username', None),
        'role': getattr(current_user, 'role', None)
    }
    
    return jsonify({
        'session_data': session_data,
        'current_user': user_info,
        'session_keys': list(session.keys())
    })

def register_debug_routes(app):
    """Register debug routes with the app"""
    app.register_blueprint(debug_bp)