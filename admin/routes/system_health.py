# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin System Health Routes"""

from flask import render_template, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import UserRole
from session_error_handlers import with_session_error_handling
from security.core.security_middleware import rate_limit
import asyncio
from datetime import datetime, timezone

def register_routes(bp):
    """Register system health routes"""
    
    @bp.route('/health')
    @login_required
    @with_session_error_handling
    def health_check():
        """Basic health check endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            db_manager = current_app.config['db_manager']
            session = db_manager.get_session()
            try:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'service': 'vedfolnir'
                }), 200
            finally:
                session.close()
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'vedfolnir',
                'error': str(e)
            }), 503

    @bp.route('/health/detailed')
    @login_required
    @with_session_error_handling
    def health_check_detailed():
        """Detailed health check endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            health_checker = current_app.config.get('health_checker')
            if not health_checker:
                return jsonify({'error': 'Health checker not available'}), 503
            
            # Use existing event loop if available, create only if necessary
            try:
                loop = asyncio.get_running_loop()
                system_health = asyncio.create_task(health_checker.check_system_health())
                system_health = loop.run_until_complete(system_health)
            except RuntimeError:
                # No running loop, create new one
                system_health = asyncio.run(health_checker.check_system_health())
            
            health_dict = health_checker.to_dict(system_health)
            
            status_code = 200 if system_health.status.value != 'unhealthy' else 503
            
            return jsonify(health_dict), status_code
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'vedfolnir',
                'error': f'Health check failed: {str(e)}'
            }), 503

    @bp.route('/health/dashboard')
    @login_required
    @with_session_error_handling
    def health_dashboard():
        """Health dashboard for system administrators"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        try:
            # Create a basic health status when health checker is not available
            from collections import namedtuple
            
            health_checker = current_app.config.get('health_checker')
            if health_checker:
                try:
                    loop = asyncio.get_running_loop()
                    system_health = asyncio.create_task(health_checker.check_system_health())
                    system_health = loop.run_until_complete(system_health)
                except RuntimeError:
                    system_health = asyncio.run(health_checker.check_system_health())
            else:
                # Create basic health object when health checker is not available
                HealthStatus = namedtuple('HealthStatus', ['value'])
                BasicHealth = namedtuple('BasicHealth', ['status', 'timestamp', 'uptime_seconds', 'version', 'components'])
                system_health = BasicHealth(
                    status=HealthStatus('healthy'),
                    timestamp=datetime.now(timezone.utc),
                    uptime_seconds=0,
                    version='1.0.0',
                    components={}
                )
            
            return render_template('health_dashboard.html', health=system_health)
            
        except Exception as e:
            flash(f'Error loading health dashboard: {str(e)}', 'error')
            return redirect(url_for('admin.dashboard'))

    @bp.route('/csrf_security_dashboard')
    @login_required
    @with_session_error_handling
    def csrf_security_dashboard():
        """CSRF Security Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return render_template('csrf_security_dashboard.html')

    @bp.route('/security_audit_dashboard')
    @login_required
    @with_session_error_handling
    def security_audit_dashboard():
        """Security Audit Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return render_template('security_audit_dashboard.html')

    @bp.route('/session_health_dashboard')
    @login_required
    @with_session_error_handling
    def session_health_dashboard():
        """Session Health Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return render_template('session_health_dashboard.html')

    @bp.route('/session_monitoring_dashboard')
    @login_required
    @with_session_error_handling
    def session_monitoring_dashboard():
        """Session Monitoring Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return render_template('session_monitoring_dashboard.html')