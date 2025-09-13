# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Performance Dashboard Routes"""

from flask import render_template, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole
from app.utils.responses import success_response, error_response
from app.core.security.core.security_middleware import rate_limit
import psutil
import time
from datetime import datetime, timedelta

def register_routes(bp):
    """Register performance dashboard routes"""
    
    @bp.route('/performance')
    @login_required
    def performance_dashboard():
        """Performance monitoring dashboard"""
        if not current_user.role == UserRole.ADMIN:
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
            
        try:
            # Get initial performance data
            performance_data = _get_performance_metrics()
            
            return render_template('admin_performance.html',
                                 performance_data=performance_data)
                                 
        except Exception as e:
            current_app.logger.error(f"Error loading performance dashboard: {str(e)}")
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Error loading performance dashboard.", "Error")
            return redirect(url_for('admin.dashboard'))

    @bp.route('/api/performance/metrics')
    @login_required
    @rate_limit(limit=60, window_seconds=60)
    def api_performance_metrics():
        """Get real-time performance metrics"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            metrics = _get_performance_metrics()
            return success_response({'metrics': metrics})
        except Exception as e:
            return error_response(str(e), 500)

    @bp.route('/api/performance/history')
    @login_required
    @rate_limit(limit=30, window_seconds=60)
    def api_performance_history():
        """Get performance history data"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            # Get SystemOptimizer from current app if available
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if system_optimizer:
                history = system_optimizer.get_performance_history(hours=24)
            else:
                # Fallback to basic metrics
                history = _get_basic_performance_history()
            
            return success_response({'history': history})
        except Exception as e:
            return error_response(str(e), 500)

def _get_performance_metrics():
    """Get current performance metrics"""
    try:
        # System metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # Get SystemOptimizer metrics if available
        system_optimizer = getattr(current_app, 'system_optimizer', None)
        if system_optimizer:
            app_metrics = system_optimizer.get_performance_metrics()
        else:
            app_metrics = {}
        
        # Database connection metrics
        db_manager = getattr(current_app, 'db_manager', None)
        db_metrics = {}
        if db_manager and hasattr(db_manager, 'get_connection_pool_stats'):
            db_metrics = db_manager.get_connection_pool_stats()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2)
            },
            'application': {
                'avg_request_time': app_metrics.get('avg_request_time', 0),
                'requests_per_second': app_metrics.get('requests_per_second', 0),
                'slow_request_count': app_metrics.get('slow_request_count', 0),
                'total_requests': app_metrics.get('total_requests', 0),
                'background_tasks_count': app_metrics.get('background_tasks_count', 0)
            },
            'database': {
                'active_connections': db_metrics.get('active_connections', 0),
                'max_connections': db_metrics.get('max_connections', 0),
                'connection_pool_utilization': db_metrics.get('utilization_percent', 0)
            }
        }
    except Exception as e:
        current_app.logger.error(f"Error getting performance metrics: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }

def _get_basic_performance_history():
    """Get basic performance history when SystemOptimizer is not available"""
    # Generate sample historical data for the last 24 hours
    history = []
    now = datetime.now()
    
    for i in range(24):
        timestamp = now - timedelta(hours=i)
        # This would normally come from stored metrics
        history.append({
            'timestamp': timestamp.isoformat(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'requests_per_second': 0  # Would be tracked in real implementation
        })
    
    return list(reversed(history))