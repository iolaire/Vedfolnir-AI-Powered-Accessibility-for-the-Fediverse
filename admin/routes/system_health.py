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
        """Comprehensive health check endpoint using HealthChecker"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Use the comprehensive health checker
            health_checker = current_app.config.get('health_checker')
            
            if health_checker:
                # Use the full health check system
                import asyncio
                try:
                    # Run the async health check
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        system_health = loop.run_until_complete(health_checker.check_system_health())
                        
                        # Convert to API format
                        health_status = {
                            'status': system_health.status.value,
                            'timestamp': system_health.timestamp.isoformat(),
                            'service': 'vedfolnir',
                            'components': {},
                            'uptime_seconds': system_health.uptime_seconds,
                            'version': system_health.version
                        }
                        
                        # Add component details
                        for name, component in system_health.components.items():
                            health_status['components'][name] = component.status.value
                            
                        return jsonify(health_status)
                        
                    finally:
                        loop.close()
                        
                except Exception as e:
                    current_app.logger.error(f"Comprehensive health check failed: {e}")
                    # Fall back to simple health check
                    pass
            
            # Fallback to simple health check if comprehensive check fails
            db_manager = current_app.config['db_manager']
            unified_session_manager = current_app.unified_session_manager
            
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'vedfolnir',
                'components': {}
            }
            
            # Check database health
            try:
                session = db_manager.get_session()
                try:
                    from sqlalchemy import text
                    session.execute(text("SELECT 1"))
                    health_status['components']['database'] = 'healthy'
                finally:
                    db_manager.close_session(session)
            except Exception as e:
                health_status['components']['database'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            # Check Redis session manager health
            try:
                if hasattr(unified_session_manager, 'get_session_stats'):
                    # Redis session manager
                    stats = unified_session_manager.get_session_stats()
                    health_status['components']['sessions'] = 'healthy'
                else:
                    # Database session manager
                    health_status['components']['sessions'] = 'healthy'
            except Exception as e:
                health_status['components']['sessions'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            # Simple Ollama check
            try:
                import httpx
                import os
                ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(f"{ollama_url}/api/tags")
                    if response.status_code == 200:
                        health_status['components']['ollama'] = 'healthy'
                    else:
                        health_status['components']['ollama'] = 'degraded'
                        health_status['status'] = 'degraded'
            except Exception as e:
                health_status['components']['ollama'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            # Simple storage check
            try:
                import os
                
                # Check database type and connection
                database_url = os.getenv('DATABASE_URL', "MySQL database")
                
                if database_url.startswith('mysql'):
                    # For MySQL, test the database connection itself
                    try:
                        session = db_manager.get_session()
                        try:
                            from sqlalchemy import text
                            session.execute(text("SELECT 1"))
                            health_status['components']['storage'] = 'healthy'
                        finally:
                            session.close()
                    except Exception as e:
                        health_status['components']['storage'] = f'unhealthy: MySQL connection failed - {str(e)}'
                        health_status['status'] = 'degraded'
                else:
                    # For MySQL, check directories
                    storage_dirs = ['storage', 'storage/database', 'storage/images']
                    storage_healthy = all(os.path.exists(d) for d in storage_dirs)
                    if storage_healthy:
                        health_status['components']['storage'] = 'healthy'
                    else:
                        health_status['components']['storage'] = 'degraded'
                        health_status['status'] = 'degraded'
                        
            except Exception as e:
                health_status['components']['storage'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            return jsonify(health_status)
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'vedfolnir',
                'error': f'Health check failed: {str(e)}'
            }), 503
            try:
                if hasattr(unified_session_manager, 'get_session_stats'):
                    # Redis session manager
                    stats = unified_session_manager.get_session_stats()
                    health_status['components']['redis_sessions'] = 'healthy'
                    health_status['components']['session_manager_type'] = 'redis'
                    health_status['components']['active_sessions'] = stats.get('total_sessions', 0)
                else:
                    # Database session manager
                    health_status['components']['database_sessions'] = 'healthy'
                    health_status['components']['session_manager_type'] = 'database'
            except Exception as e:
                health_status['components']['session_manager'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            return jsonify(health_status), 200
            
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

    @bp.route('/security_audit')
    @login_required
    @with_session_error_handling
    def security_audit():
        """Security Audit Dashboard (alias)"""
        return security_audit_dashboard()

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