# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Responsiveness Dashboard Routes"""

from flask import render_template, jsonify, redirect, url_for, current_app, request
from flask_login import login_required, current_user
from models import UserRole
from app.utils.responses import success_response, error_response
from app.core.security.core.security_middleware import rate_limit
from datetime import datetime, timezone

def register_routes(bp):
    """Register responsiveness dashboard routes"""
    
    @bp.route('/responsiveness')
    @login_required
    def responsiveness_dashboard():
        """Responsiveness monitoring dashboard"""
        if not current_user.role == UserRole.ADMIN:
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('main.index'))
            
        try:
            # Get initial responsiveness data
            responsiveness_data = _get_responsiveness_overview()
            
            return render_template('admin_responsiveness.html',
                                 responsiveness_data=responsiveness_data)
                                 
        except Exception as e:
            current_app.logger.error(f"Error loading responsiveness dashboard: {str(e)}")
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Error loading responsiveness dashboard.", "Error")
            return redirect(url_for('admin.dashboard'))

    @bp.route('/api/responsiveness/overview')
    @login_required
    @rate_limit(limit=60, window_seconds=60)
    def api_responsiveness_overview():
        """Get responsiveness overview data"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            overview = _get_responsiveness_overview()
            return success_response({'overview': overview})
        except Exception as e:
            return error_response(str(e), 500)

    @bp.route('/api/responsiveness/check', methods=['POST'])
    @login_required
    @rate_limit(limit=10, window_seconds=60)
    def api_run_responsiveness_check():
        """Run comprehensive responsiveness check"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return error_response('System optimizer not available', 503)
            
            check_result = system_optimizer.check_responsiveness()
            
            # Log the check
            current_app.logger.info(f"Responsiveness check performed by {current_user.username}: "
                                  f"Status={check_result['overall_status']}")
            
            return success_response({'check_result': check_result})
        except Exception as e:
            return error_response(str(e), 500)

    @bp.route('/api/responsiveness/optimize', methods=['POST'])
    @login_required
    @rate_limit(limit=5, window_seconds=300)
    def api_optimize_responsiveness():
        """Trigger responsiveness optimization"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
            
        try:
            optimization_type = request.json.get('type', 'memory')
            
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return error_response('System optimizer not available', 503)
            
            if optimization_type == 'memory':
                result = system_optimizer.trigger_cleanup_if_needed()
                message = 'Memory cleanup completed'
            elif optimization_type == 'connections':
                system_optimizer._trigger_connection_cleanup()
                result = True
                message = 'Connection optimization completed'
            else:
                return error_response('Invalid optimization type', 400)
            
            # Log the optimization
            current_app.logger.info(f"Responsiveness optimization ({optimization_type}) "
                                  f"triggered by {current_user.username}")
            
            # Send notification
            from app.services.notification.helpers.notification_helpers import send_success_notification
            send_success_notification(message, 'Optimization Complete')
            
            return success_response({
                'optimization_result': result,
                'message': message,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            current_app.logger.error(f"Responsiveness optimization failed: {e}")
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(f'Optimization failed: {str(e)}', 'Optimization Error')
            return error_response(str(e), 500)

def _get_responsiveness_overview():
    """Get responsiveness overview data"""
    try:
        system_optimizer = getattr(current_app, 'system_optimizer', None)
        
        if system_optimizer:
            # Get comprehensive responsiveness data
            responsiveness_check = system_optimizer.check_responsiveness()
            performance_metrics = system_optimizer.get_performance_metrics()
            recommendations = system_optimizer.get_recommendations()
            
            # Filter recommendations for responsiveness
            responsiveness_recommendations = [
                rec for rec in recommendations 
                if rec.get('action') in ['memory_cleanup', 'cpu_optimization', 
                                       'connection_pool_cleanup', 'background_task_optimization']
            ]
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': responsiveness_check['overall_status'],
                'responsive': responsiveness_check['responsive'],
                'issues': responsiveness_check['issues'],
                'metrics': {
                    'memory_usage_percent': performance_metrics['memory_usage_percent'],
                    'cpu_usage_percent': performance_metrics['cpu_usage_percent'],
                    'avg_request_time': performance_metrics['avg_request_time'],
                    'slow_request_count': performance_metrics['slow_request_count'],
                    'connection_pool_utilization': performance_metrics['connection_pool_utilization'],
                    'background_tasks_count': performance_metrics['background_tasks_count'],
                    'blocked_requests': performance_metrics['blocked_requests']
                },
                'recommendations': responsiveness_recommendations,
                'thresholds': {
                    'memory_threshold': 80,
                    'cpu_threshold': 85,
                    'request_time_threshold': 2.0,
                    'connection_pool_threshold': 90
                }
            }
        else:
            # Fallback when SystemOptimizer is not available
            import psutil
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': 'healthy' if memory.percent < 80 and cpu_percent < 85 else 'warning',
                'responsive': memory.percent < 80 and cpu_percent < 85,
                'issues': [],
                'metrics': {
                    'memory_usage_percent': memory.percent,
                    'cpu_usage_percent': cpu_percent,
                    'avg_request_time': 0,
                    'slow_request_count': 0,
                    'connection_pool_utilization': 0,
                    'background_tasks_count': 0,
                    'blocked_requests': 0
                },
                'recommendations': [],
                'thresholds': {
                    'memory_threshold': 80,
                    'cpu_threshold': 85,
                    'request_time_threshold': 2.0,
                    'connection_pool_threshold': 90
                }
            }
            
    except Exception as e:
        current_app.logger.error(f"Error getting responsiveness overview: {e}")
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e),
            'overall_status': 'error',
            'responsive': False
        }