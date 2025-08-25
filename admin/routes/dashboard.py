# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Dashboard Routes"""

from flask import render_template, current_app
from flask_login import login_required, current_user
from models import UserRole
from session_error_handlers import with_session_error_handling
import version

def register_routes(bp):
    """Register dashboard routes"""
    
    @bp.route('/')
    @bp.route('/dashboard')
    @login_required
    @with_session_error_handling
    def dashboard():
        """Admin landing page and dashboard overview"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        db_manager = current_app.config['db_manager']
        
        # Get basic system overview stats for landing page
        with db_manager.get_session() as session:
            from models import User, PlatformConnection, Image, Post
            from datetime import datetime, timedelta
            
            # Basic counts
            stats = {
                'total_users': session.query(User).count(),
                'active_users': session.query(User).filter_by(is_active=True).count(),
                'total_platforms': session.query(PlatformConnection).count(),
                'total_images': session.query(Image).count(),
                'total_posts': session.query(Post).count(),
            }
            
            # Recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            stats['new_users_24h'] = session.query(User).filter(User.created_at >= yesterday).count()
            stats['recent_logins'] = session.query(User).filter(User.last_login >= yesterday).count()
        
        # Get basic system health status
        try:
            health_checker = current_app.config.get('health_checker')
            if health_checker:
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    system_health = asyncio.create_task(health_checker.check_system_health())
                    system_health = loop.run_until_complete(system_health)
                    health_status = system_health.status.value
                except RuntimeError:
                    system_health = asyncio.run(health_checker.check_system_health())
                    health_status = system_health.status.value
            else:
                health_status = 'healthy'
        except Exception as e:
            current_app.logger.error(f"Error getting health status: {e}")
            health_status = 'unknown'
        
        return render_template('admin/admin_landing.html', 
                             stats=stats,
                             health_status=health_status,
                             app_version=version.__version__)
    
    @bp.route('/configuration')
    @login_required
    @with_session_error_handling
    def configuration_management():
        """System configuration management page"""
        if not current_user.role == UserRole.ADMIN:
            from flask import flash, redirect, url_for
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('admin.dashboard'))
            
        return render_template('configuration_management.html')

