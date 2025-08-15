# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Data Cleanup Routes"""

from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import UserRole, ProcessingStatus
from session_error_handlers import with_session_error_handling
from ..services.cleanup_service import CleanupService

def register_routes(bp):
    """Register cleanup routes"""
    
    @bp.route('/cleanup')
    @login_required
    @with_session_error_handling
    def cleanup():
        """Admin interface for data cleanup"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        db_manager = current_app.config['db_manager']
        cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
        
        stats = cleanup_service.get_cleanup_statistics()
        retention = {'processing_runs': 30, 'rejected_images': 7, 'posted_images': 30, 'error_images': 7}
        
        return render_template('admin_cleanup.html', stats=stats, users=stats.get('users', []), retention=retention)

    @bp.route('/cleanup/runs', methods=['POST'])
    @login_required
    @with_session_error_handling
    def cleanup_runs():
        """Archive old processing runs"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied', 'error')
            return redirect(url_for('admin.cleanup'))
            
        days = request.form.get('days', type=int)
        dry_run = 'dry_run' in request.form
        
        if not days or days < 1:
            flash('Invalid number of days', 'error')
            return redirect(url_for('admin.cleanup'))
        
        db_manager = current_app.config['db_manager']
        cleanup_service = CleanupService(db_manager, current_app.config.get('config'))
        
        result = cleanup_service.cleanup_old_processing_runs(days=days, dry_run=dry_run)
        
        if result['success']:
            flash(result['message'], 'info' if dry_run else 'success')
        else:
            flash(f'Error: {result["error"]}', 'error')
        
        return redirect(url_for('admin.cleanup'))