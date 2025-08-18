# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Dashboard Routes"""

from flask import render_template, current_app
from flask_login import login_required, current_user
from models import UserRole
from session_error_handlers import with_session_error_handling

def register_routes(bp):
    """Register dashboard routes"""
    
    @bp.route('/')
    @bp.route('/dashboard')
    @login_required
    @with_session_error_handling
    def dashboard():
        """Admin landing page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        db_manager = current_app.config['db_manager']
        
        # Get system overview stats
        unified_session_manager = current_app.unified_session_manager

        with unified_session_manager.get_db_session() as session:
            from models import User, PlatformConnection, Image, Post
            
            stats = {
                'total_users': session.query(User).count(),
                'active_users': session.query(User).filter_by(is_active=True).count(),
                'total_platforms': session.query(PlatformConnection).count(),
                'total_images': session.query(Image).count(),
                'total_posts': session.query(Post).count(),
            }
        
        return render_template('dashboard.html', stats=stats)