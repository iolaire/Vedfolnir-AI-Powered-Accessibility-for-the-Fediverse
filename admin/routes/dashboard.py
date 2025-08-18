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
        
        # Get system overview stats using db_manager directly
        # (Session management is now in Redis, database is for data storage)
        session = db_manager.get_session()
        try:
            from models import User, PlatformConnection, Image, Post
            
            stats = {
                'total_users': session.query(User).count(),
                'active_users': session.query(User).filter_by(is_active=True).count(),
                'total_platforms': session.query(PlatformConnection).count(),
                'total_images': session.query(Image).count(),
                'total_posts': session.query(Post).count(),
            }
        finally:
            db_manager.close_session(session)
        
        # Simple synchronous system health check
        system_health = get_simple_system_health(db_manager)
        
        return render_template('dashboard.html', stats=stats, system_health=system_health)

def get_simple_system_health(db_manager):
    """Get a simple system health status without async operations"""
    try:
        # Check database connectivity
        session = db_manager.get_session()
        try:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            db_healthy = True
        except Exception:
            db_healthy = False
        finally:
            db_manager.close_session(session)
        
        # Check if Ollama is accessible (simple HTTP check)
        ollama_healthy = True
        try:
            import httpx
            import os
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{ollama_url}/api/tags")
                ollama_healthy = response.status_code == 200
        except Exception:
            ollama_healthy = False
        
        # Check storage (basic directory check)
        storage_healthy = True
        try:
            import os
            storage_dirs = ['storage', 'storage/database', 'storage/images']
            for dir_path in storage_dirs:
                if not os.path.exists(dir_path):
                    storage_healthy = False
                    break
        except Exception:
            storage_healthy = False
        
        # Determine overall health
        if db_healthy and ollama_healthy and storage_healthy:
            return 'healthy'
        elif db_healthy:  # Database is most critical
            return 'warning'
        else:
            return 'critical'
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error checking system health: {e}")
        return 'warning'