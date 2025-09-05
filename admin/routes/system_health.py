# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MIGRATION NOTE: Flash messages in this file have been commented out as part of
# the notification system migration. The application now uses the unified
# WebSocket-based notification system. These comments should be replaced with
# appropriate unified notification calls in a future update.


from unified_notification_manager import UnifiedNotificationManager
"""Admin System Health Routes"""

from flask import render_template, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from session_error_handlers import with_session_error_handling
from security.core.security_middleware import rate_limit
import asyncio
from datetime import datetime, timezone

def register_routes(bp):
    """Register system health routes"""
    
    @bp.route('/health')
    @login_required
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
    def health_dashboard():
        """Enhanced health dashboard with multi-tenant caption management"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
            
        try:
            db_manager = current_app.config['db_manager']
            
            # Get system overview stats
            with db_manager.get_session() as session:
                from models import User, PlatformConnection, Image, Post
                
                stats = {
                    'total_users': session.query(User).count(),
                    'active_users': session.query(User).filter_by(is_active=True).count(),
                    'total_platforms': session.query(PlatformConnection).count(),
                    'total_images': session.query(Image).count(),
                    'total_posts': session.query(Post).count(),
                }
            
            # Get system metrics for multi-tenant management
            system_metrics = get_system_metrics(current_user.id)
            
            # Get active jobs for admin oversight
            active_jobs = get_active_jobs_for_admin(current_user.id)
            
            # Get system alerts
            system_alerts = get_system_alerts()
            
            # Get system configuration
            system_config = get_system_configuration()
            
            # Get health status
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
            
            return render_template('dashboard.html', 
                                 health=system_health,
                                 stats=stats,
                                 system_metrics=system_metrics,
                                 active_jobs=active_jobs,
                                 system_alerts=system_alerts,
                                 system_config=system_config)
            
        except Exception as e:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification(f'Error loading health dashboard: {str(e)}', 'Dashboard Error')
            return redirect(url_for('admin.dashboard'))

    @bp.route('/csrf_security_dashboard')
    @login_required
    def csrf_security_dashboard():
        """CSRF Security Dashboard - uses live data directly"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
        
        try:
            # Import and use the live CSRF metrics
            from security.monitoring.csrf_security_metrics import get_csrf_security_metrics
            csrf_metrics = get_csrf_security_metrics()
            dashboard_data = csrf_metrics.get_csrf_dashboard_data()
            
            return render_template('csrf_security_dashboard.html', dashboard_data=dashboard_data)
        
        except Exception as e:
            current_app.logger.error(f"Error loading CSRF dashboard data: {e}")
            # Fallback to basic data if live data fails
            dashboard_data = {
                'recent_violations': [],
                'compliance_metrics': {'24h': {'compliance_rate': 1.0, 'total_requests': 0, 'violation_count': 0, 'compliance_level': 'HIGH'}},
                'top_violation_ips': [],
                'top_violation_types': [],
                'top_violation_endpoints': [],
                'last_updated': None
            }
            return render_template('csrf_security_dashboard.html', dashboard_data=dashboard_data)

    @bp.route('/security_audit_dashboard')
    @login_required
    def security_audit_dashboard():
        """Security Audit Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
        return render_template('security_audit_dashboard.html')

    @bp.route('/security_audit')
    @login_required
    def security_audit():
        """Security Audit Dashboard (alias)"""
        return security_audit_dashboard()

    @bp.route('/session_health_dashboard')
    @login_required
    def session_health_dashboard():
        """Session Health Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
        return render_template('session_health_dashboard.html')

    @bp.route('/session_monitoring_dashboard')
    @login_required
    def session_monitoring_dashboard():
        """Session Monitoring Dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
        return render_template('session_monitoring_dashboard.html')

def get_system_metrics(admin_user_id):
    """Get system metrics for multi-tenant caption management"""
    try:
        # Import services
        from web_caption_generation_service import WebCaptionGenerationService
        from system_monitor import SystemMonitor
        
        # Get web caption generation service
        db_manager = current_app.config['db_manager']
        service = WebCaptionGenerationService(db_manager)
        
        # Get system metrics from the service
        metrics = service.get_system_metrics(admin_user_id)
        
        # Get additional metrics from system monitor
        monitor = SystemMonitor(db_manager)
        system_health = monitor.get_system_health()
        performance_metrics = monitor.get_performance_metrics()
        
        # Combine metrics
        combined_metrics = {
            'active_jobs': metrics.get('active_jobs', 0),
            'queued_jobs': metrics.get('queued_jobs', 0),
            'completed_today': metrics.get('completed_today', 0),
            'failed_jobs': metrics.get('failed_jobs', 0),
            'success_rate': metrics.get('success_rate', 0),
            'error_rate': metrics.get('error_rate', 0),
            'system_load': getattr(performance_metrics, 'resource_usage', {}).get('cpu_percent', 0),
            'avg_processing_time': metrics.get('avg_processing_time', 0)
        }
        
        return combined_metrics
        
    except Exception as e:
        current_app.logger.error(f"Error getting system metrics: {e}")
        return {
            'active_jobs': 0,
            'queued_jobs': 0,
            'completed_today': 0,
            'failed_jobs': 0,
            'success_rate': 0,
            'error_rate': 0,
            'system_load': 0,
            'avg_processing_time': 0
        }

def get_active_jobs_for_admin(admin_user_id):
    """Get active jobs for admin dashboard"""
    try:
        from web_caption_generation_service import WebCaptionGenerationService
        
        db_manager = current_app.config['db_manager']
        service = WebCaptionGenerationService(db_manager)
        
        # Get all active jobs with admin access
        jobs = service.get_all_active_jobs(admin_user_id)
        
        # Format jobs for display
        formatted_jobs = []
        for job in jobs:
            formatted_job = {
                'task_id': job.get('task_id', ''),
                'username': job.get('username', 'Unknown'),
                'user_email': job.get('user_email', ''),
                'platform_type': job.get('platform_type', 'unknown'),
                'platform_name': job.get('platform_name', 'Unknown Platform'),
                'status': job.get('status', 'unknown'),
                'progress_percentage': job.get('progress_percentage', 0),
                'current_step': job.get('current_step', 'Initializing'),
                'created_at': job.get('created_at'),
                'estimated_completion': job.get('estimated_completion', 'Calculating...')
            }
            formatted_jobs.append(formatted_job)
        
        return formatted_jobs
        
    except Exception as e:
        current_app.logger.error(f"Error getting active jobs: {e}")
        return []

def get_system_alerts():
    """Get system alerts for admin dashboard"""
    try:
        from alert_manager import AlertManager
        
        db_manager = current_app.config['db_manager']
        config = current_app.config.get('config')
        alert_manager = AlertManager(db_manager, config)
        
        # Get active alerts
        alerts = alert_manager.get_active_alerts()
        
        # Format alerts for display
        formatted_alerts = []
        for alert in alerts:
            formatted_alert = {
                'id': alert.get('id', ''),
                'title': alert.get('title', 'System Alert'),
                'message': alert.get('message', ''),
                'severity': alert.get('severity', 'info'),
                'created_at': alert.get('created_at')
            }
            formatted_alerts.append(formatted_alert)
        
        return formatted_alerts
        
    except Exception as e:
        current_app.logger.error(f"Error getting system alerts: {e}")
        return []

def get_system_configuration():
    """Get system configuration for admin dashboard"""
    try:
        db_manager = current_app.config['db_manager']
        
        with db_manager.get_session() as session:
            from models import SystemConfiguration
            
            # Get configuration values
            config = {}
            config_items = session.query(SystemConfiguration).all()
            
            for item in config_items:
                config[item.key] = item.value
            
            # Set defaults if not configured
            return {
                'max_concurrent_jobs': int(config.get('max_concurrent_jobs', 5)),
                'job_timeout_minutes': int(config.get('job_timeout_minutes', 30)),
                'max_retries': int(config.get('max_retries', 3)),
                'alert_threshold': int(config.get('alert_threshold', 80))
            }
        
    except Exception as e:
        current_app.logger.error(f"Error getting system configuration: {e}")
        return {
            'max_concurrent_jobs': 5,
            'job_timeout_minutes': 30,
            'max_retries': 3,
            'alert_threshold': 80
        }