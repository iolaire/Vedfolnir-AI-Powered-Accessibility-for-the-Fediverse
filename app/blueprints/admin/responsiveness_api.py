# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Responsiveness API Routes

This module provides Flask routes for the responsiveness monitoring system,
including real-time metrics, cleanup operations, and performance optimization.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from models import UserRole
from app.core.security.core.security_middleware import rate_limit
from admin.security.admin_access_control import admin_required

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register responsiveness API routes"""
    
    @bp.route('/api/responsiveness/metrics')
    @login_required
    @admin_required
    @rate_limit(limit=60, window_seconds=60)
    def api_responsiveness_metrics():
        """API endpoint for responsiveness metrics"""
        try:
            # Get SystemOptimizer from current app
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({
                    'success': False,
                    'error': 'System optimizer not available'
                }), 503
            
            # Get performance metrics with responsiveness data
            metrics = system_optimizer.get_performance_metrics()
            
            # Get responsiveness check results
            responsiveness_check = system_optimizer.check_responsiveness()
            
            # Combine metrics with responsiveness analysis
            response_data = {
                'responsiveness_status': responsiveness_check['overall_status'],
                'responsive': responsiveness_check['responsive'],
                'issues': responsiveness_check['issues'],
                'memory_usage_percent': metrics['memory_usage_percent'],
                'memory_usage_mb': metrics['memory_usage_mb'],
                'cpu_usage_percent': metrics['cpu_usage_percent'],
                'avg_request_time': metrics['avg_request_time'],
                'slow_request_count': metrics['slow_request_count'],
                'total_requests': metrics['total_requests'],
                'requests_per_second': metrics['requests_per_second'],
                'connection_pool_utilization': metrics['connection_pool_utilization'],
                'active_connections': metrics['active_connections'],
                'max_connections': metrics['max_connections'],
                'background_tasks_count': metrics['background_tasks_count'],
                'blocked_requests': metrics['blocked_requests'],
                'cleanup_triggered': metrics.get('cleanup_triggered', False),
                'recent_slow_requests': metrics.get('recent_slow_requests', []),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return jsonify({
                'success': True,
                'data': response_data
            })
            
        except Exception as e:
            logger.error(f"Failed to get responsiveness metrics: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @bp.route('/api/responsiveness/check')
    @login_required
    @admin_required
    @rate_limit(limit=10, window_seconds=60)
    def api_responsiveness_check():
        """API endpoint for comprehensive responsiveness check"""
        try:
            # Get SystemOptimizer from current app
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({
                    'success': False,
                    'error': 'System optimizer not available'
                }), 503
            
            # Run comprehensive responsiveness check
            check_result = system_optimizer.check_responsiveness()
            
            # Log the check for audit purposes
            logger.info(f"Responsiveness check performed by admin {current_user.username}: "
                       f"Status={check_result['overall_status']}, Issues={len(check_result['issues'])}")
            
            return jsonify({
                'success': True,
                'data': check_result
            })
            
        except Exception as e:
            logger.error(f"Failed to perform responsiveness check: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @bp.route('/api/responsiveness/cleanup/memory', methods=['POST'])
    @login_required
    @admin_required
    @rate_limit(limit=5, window_seconds=300)  # Limited to 5 per 5 minutes
    def api_memory_cleanup():
        """API endpoint for triggering memory cleanup"""
        try:
            # Get SystemOptimizer from current app
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({
                    'success': False,
                    'error': 'System optimizer not available'
                }), 503
            
            # Check if cleanup is enabled
            if not system_optimizer.responsiveness_config.cleanup_enabled:
                return jsonify({
                    'success': False,
                    'error': 'Automated cleanup is disabled'
                }), 403
            
            # Trigger memory cleanup
            cleanup_result = system_optimizer.trigger_cleanup_if_needed()
            
            # Log the cleanup action
            logger.info(f"Manual memory cleanup triggered by admin {current_user.username}: "
                       f"Result={cleanup_result}")
            
            # Send notification about the cleanup
            from app.services.notification.helpers.notification_helpers import send_success_notification
            send_success_notification(
                'Memory cleanup operation completed successfully',
                'Memory Cleanup'
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'cleanup_triggered': cleanup_result,
                    'message': 'Memory cleanup operation completed',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to trigger memory cleanup: {e}")
            
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(
                f'Memory cleanup operation failed: {str(e)}',
                'Memory Cleanup Error'
            )
            
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @bp.route('/api/responsiveness/optimize/connections', methods=['POST'])
    @login_required
    @admin_required
    @rate_limit(limit=3, window_seconds=300)  # Limited to 3 per 5 minutes
    def api_optimize_connections():
        """API endpoint for optimizing database connections"""
        try:
            # Get database manager from current app
            db_manager = getattr(current_app, 'db_manager', None)
            if not db_manager:
                return jsonify({
                    'success': False,
                    'error': 'Database manager not available'
                }), 503
            
            # Get SystemOptimizer for connection cleanup
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if system_optimizer:
                # Trigger connection cleanup through SystemOptimizer
                system_optimizer._trigger_connection_cleanup()
            
            # Attempt to optimize connection pool if method exists
            optimization_result = {'connections_optimized': True}
            if hasattr(db_manager, 'optimize_connection_pool'):
                optimization_result = db_manager.optimize_connection_pool()
            
            # Log the optimization action
            logger.info(f"Connection optimization triggered by admin {current_user.username}: "
                       f"Result={optimization_result}")
            
            # Send notification about the optimization
            from app.services.notification.helpers.notification_helpers import send_success_notification
            send_success_notification(
                'Database connection optimization completed successfully',
                'Connection Optimization'
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'optimization_result': optimization_result,
                    'message': 'Connection optimization completed',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to optimize connections: {e}")
            
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(
                f'Connection optimization failed: {str(e)}',
                'Connection Optimization Error'
            )
            
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @bp.route('/api/responsiveness/health')
    @login_required
    @admin_required
    @rate_limit(limit=30, window_seconds=60)
    def api_responsiveness_health():
        """API endpoint for responsiveness health status"""
        try:
            # Get SystemOptimizer from current app
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({
                    'success': False,
                    'error': 'System optimizer not available'
                }), 503
            
            # Get health status with responsiveness monitoring
            health_status = system_optimizer.get_health_status()
            
            # Get current performance metrics for additional context
            metrics = system_optimizer.get_performance_metrics()
            
            # Combine health status with responsiveness context
            response_data = {
                'overall_status': health_status['status'],
                'components': health_status['components'],
                'responsiveness_monitoring': health_status.get('responsiveness_monitoring', True),
                'thresholds': health_status.get('thresholds', {}),
                'current_metrics': {
                    'memory_usage_percent': metrics['memory_usage_percent'],
                    'cpu_usage_percent': metrics['cpu_usage_percent'],
                    'connection_pool_utilization': metrics['connection_pool_utilization'],
                    'avg_request_time': metrics['avg_request_time'],
                    'background_tasks_count': metrics['background_tasks_count']
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return jsonify({
                'success': True,
                'data': response_data
            })
            
        except Exception as e:
            logger.error(f"Failed to get responsiveness health status: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @bp.route('/api/responsiveness/recommendations')
    @login_required
    @admin_required
    @rate_limit(limit=20, window_seconds=60)
    def api_responsiveness_recommendations():
        """API endpoint for responsiveness optimization recommendations"""
        try:
            # Get SystemOptimizer from current app
            system_optimizer = getattr(current_app, 'system_optimizer', None)
            if not system_optimizer:
                return jsonify({
                    'success': False,
                    'error': 'System optimizer not available'
                }), 503
            
            # Get recommendations with responsiveness focus
            recommendations = system_optimizer.get_recommendations()
            
            # Filter and enhance recommendations for responsiveness
            responsiveness_recommendations = []
            for rec in recommendations:
                if rec.get('action') in ['memory_cleanup', 'cpu_optimization', 'connection_pool_cleanup', 
                                       'background_task_optimization']:
                    responsiveness_recommendations.append({
                        'id': rec['id'],
                        'message': rec['message'],
                        'priority': rec['priority'],
                        'action': rec['action'],
                        'threshold': rec.get('threshold'),
                        'category': 'responsiveness',
                        'automated': rec.get('action') in ['memory_cleanup', 'connection_pool_cleanup']
                    })
            
            return jsonify({
                'success': True,
                'data': {
                    'recommendations': responsiveness_recommendations,
                    'total_count': len(responsiveness_recommendations),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to get responsiveness recommendations: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

