# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Monitoring Dashboard

This module provides a web-based dashboard for monitoring system performance,
cache efficiency, query optimization, and background cleanup operations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user

from models import UserRole
from performance_cache_manager import PerformanceCacheManager
from database_query_optimizer import DatabaseQueryOptimizer
from background_cleanup_manager import BackgroundCleanupManager
from enhanced_admin_management_service import EnhancedAdminManagementService
from security.core.security_utils import sanitize_for_log
from security.core.role_based_access import require_admin

logger = logging.getLogger(__name__)

# Create blueprint for performance monitoring routes
performance_bp = Blueprint('performance', __name__, url_prefix='/admin/performance')

def get_performance_services():
    """Get performance monitoring services from current app"""
    cache_manager = getattr(current_app, 'cache_manager', None)
    query_optimizer = getattr(current_app, 'query_optimizer', None)
    cleanup_manager = getattr(current_app, 'cleanup_manager', None)
    enhanced_admin_service = getattr(current_app, 'enhanced_admin_service', None)
    
    return cache_manager, query_optimizer, cleanup_manager, enhanced_admin_service

@performance_bp.route('/dashboard')
@login_required
@require_admin
def performance_dashboard():
    """Main performance monitoring dashboard"""
    try:
        cache_manager, query_optimizer, cleanup_manager, enhanced_admin_service = get_performance_services()
        
        # Get basic performance metrics
        performance_data = {
            'cache_available': cache_manager is not None,
            'query_optimizer_available': query_optimizer is not None,
            'cleanup_manager_available': cleanup_manager is not None,
            'enhanced_service_available': enhanced_admin_service is not None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Get cache statistics if available
        if cache_manager:
            try:
                cache_stats = cache_manager.get_cache_stats()
                performance_data['cache_stats'] = cache_stats
            except Exception as e:
                logger.error(f"Error getting cache stats: {sanitize_for_log(str(e))}")
                performance_data['cache_error'] = str(e)
        
        # Get query performance statistics if available
        if query_optimizer:
            try:
                query_stats = query_optimizer.get_query_performance_stats()
                performance_data['query_stats'] = query_stats
            except Exception as e:
                logger.error(f"Error getting query stats: {sanitize_for_log(str(e))}")
                performance_data['query_error'] = str(e)
        
        # Get cleanup statistics if available
        if cleanup_manager:
            try:
                cleanup_stats = cleanup_manager.get_cleanup_stats(hours=24)
                performance_data['cleanup_stats'] = cleanup_stats
            except Exception as e:
                logger.error(f"Error getting cleanup stats: {sanitize_for_log(str(e))}")
                performance_data['cleanup_error'] = str(e)
        
        return render_template('performance_dashboard.html', 
                             performance_data=performance_data,
                             current_user=current_user)
        
    except Exception as e:
        logger.error(f"Error loading performance dashboard: {sanitize_for_log(str(e))}")
        return render_template('admin/error.html', 
                             error_message="Failed to load performance dashboard",
                             error_details=str(e)), 500

@performance_bp.route('/api/cache-stats')
@login_required
@require_admin
def api_cache_stats():
    """API endpoint for cache statistics"""
    try:
        cache_manager, _, _, _ = get_performance_services()
        
        if not cache_manager:
            return jsonify({'error': 'Cache manager not available'}), 503
        
        stats = cache_manager.get_cache_stats()
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats API: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/query-stats')
@login_required
@require_admin
def api_query_stats():
    """API endpoint for query performance statistics"""
    try:
        _, query_optimizer, _, _ = get_performance_services()
        
        if not query_optimizer:
            return jsonify({'error': 'Query optimizer not available'}), 503
        
        stats = query_optimizer.get_query_performance_stats()
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting query stats API: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/cleanup-stats')
@login_required
@require_admin
def api_cleanup_stats():
    """API endpoint for cleanup statistics"""
    try:
        hours = request.args.get('hours', 24, type=int)
        _, _, cleanup_manager, _ = get_performance_services()
        
        if not cleanup_manager:
            return jsonify({'error': 'Cleanup manager not available'}), 503
        
        stats = cleanup_manager.get_cleanup_stats(hours=hours)
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting cleanup stats API: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/system-metrics')
@login_required
@require_admin
def api_system_metrics():
    """API endpoint for comprehensive system performance metrics"""
    try:
        _, _, _, enhanced_admin_service = get_performance_services()
        
        if not enhanced_admin_service:
            return jsonify({'error': 'Enhanced admin service not available'}), 503
        
        metrics = enhanced_admin_service.get_system_performance_metrics()
        
        # Convert dataclass to dictionary for JSON serialization
        metrics_dict = {
            'cache_hit_rate': metrics.cache_hit_rate,
            'avg_query_time_ms': metrics.avg_query_time_ms,
            'total_cached_operations': metrics.total_cached_operations,
            'cache_memory_usage_mb': metrics.cache_memory_usage_mb,
            'background_cleanup_stats': metrics.background_cleanup_stats
        }
        
        return jsonify({
            'success': True,
            'data': metrics_dict,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system metrics API: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/request-performance')
@login_required
@require_admin
def api_request_performance():
    """API endpoint for request performance metrics"""
    try:
        # Get SystemOptimizer from current app
        system_optimizer = getattr(current_app, 'system_optimizer', None)
        if not system_optimizer:
            return jsonify({'error': 'System optimizer not available'}), 503
        
        # Get request performance metrics
        request_metrics = system_optimizer._get_request_performance_metrics()
        
        return jsonify({
            'success': True,
            'data': request_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting request performance metrics: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/slow-requests')
@login_required
@require_admin
def api_slow_requests():
    """API endpoint for slow request analysis"""
    try:
        # Get SystemOptimizer from current app
        system_optimizer = getattr(current_app, 'system_optimizer', None)
        if not system_optimizer:
            return jsonify({'error': 'System optimizer not available'}), 503
        
        # Get slow request analysis
        slow_request_analysis = system_optimizer.get_slow_request_analysis()
        
        return jsonify({
            'success': True,
            'data': slow_request_analysis,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting slow request analysis: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/cache-invalidate', methods=['POST'])
@login_required
@require_admin
def api_cache_invalidate():
    """API endpoint for cache invalidation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        cache_manager, _, _, enhanced_admin_service = get_performance_services()
        
        if not cache_manager:
            return jsonify({'error': 'Cache manager not available'}), 503
        
        invalidation_type = data.get('type')
        target_id = data.get('target_id')
        
        if invalidation_type == 'user' and target_id:
            # Invalidate user-specific caches
            if enhanced_admin_service:
                result = enhanced_admin_service.invalidate_user_related_caches(int(target_id))
            else:
                result = {'invalidated_cache_keys': cache_manager.invalidate_user_caches(int(target_id))}
            
            return jsonify({
                'success': True,
                'message': f'Invalidated caches for user {target_id}',
                'data': result,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        elif invalidation_type == 'job' and target_id:
            # Invalidate job-specific caches
            invalidated = cache_manager.invalidate_job_caches(target_id)
            
            return jsonify({
                'success': True,
                'message': f'Invalidated caches for job {target_id}',
                'data': {'invalidated_cache_keys': invalidated},
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        elif invalidation_type == 'all':
            # Invalidate all caches
            pattern = "vedfolnir:cache:*"
            invalidated = cache_manager.invalidate_pattern(pattern)
            
            return jsonify({
                'success': True,
                'message': 'Invalidated all caches',
                'data': {'invalidated_cache_keys': invalidated},
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        else:
            return jsonify({'error': 'Invalid invalidation type or missing target_id'}), 400
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/cleanup-run', methods=['POST'])
@login_required
@require_admin
def api_cleanup_run():
    """API endpoint for running manual cleanup operations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        _, _, _, enhanced_admin_service = get_performance_services()
        
        if not enhanced_admin_service:
            return jsonify({'error': 'Enhanced admin service not available'}), 503
        
        cleanup_type = data.get('cleanup_type')
        if not cleanup_type:
            return jsonify({'error': 'cleanup_type is required'}), 400
        
        # Run manual cleanup
        result = enhanced_admin_service.run_manual_cleanup(cleanup_type, current_user.id)
        
        return jsonify({
            'success': result.get('success', False),
            'data': result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error running manual cleanup: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/api/performance-report')
@login_required
@require_admin
def api_performance_report():
    """API endpoint for comprehensive performance report"""
    try:
        _, _, _, enhanced_admin_service = get_performance_services()
        
        if not enhanced_admin_service:
            return jsonify({'error': 'Enhanced admin service not available'}), 503
        
        # Get comprehensive performance report
        report = enhanced_admin_service.get_cache_performance_report(current_user.id)
        
        return jsonify({
            'success': True,
            'data': report,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance report: {sanitize_for_log(str(e))}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@performance_bp.route('/cache-management')
@login_required
@require_admin
def cache_management():
    """Cache management interface"""
    try:
        cache_manager, _, _, _ = get_performance_services()
        
        cache_data = {
            'cache_available': cache_manager is not None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if cache_manager:
            try:
                cache_stats = cache_manager.get_cache_stats()
                cache_data['stats'] = cache_stats
            except Exception as e:
                logger.error(f"Error getting cache stats for management: {sanitize_for_log(str(e))}")
                cache_data['error'] = str(e)
        
        return render_template('admin/cache_management.html',
                             cache_data=cache_data,
                             current_user=current_user)
        
    except Exception as e:
        logger.error(f"Error loading cache management: {sanitize_for_log(str(e))}")
        return render_template('admin/error.html',
                             error_message="Failed to load cache management",
                             error_details=str(e)), 500

@performance_bp.route('/cleanup-management')
@login_required
@require_admin
def cleanup_management():
    """Cleanup management interface"""
    try:
        _, _, cleanup_manager, _ = get_performance_services()
        
        cleanup_data = {
            'cleanup_available': cleanup_manager is not None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if cleanup_manager:
            try:
                cleanup_stats = cleanup_manager.get_cleanup_stats(hours=24)
                cleanup_data['stats'] = cleanup_stats
                
                # Get available cleanup types
                cleanup_data['available_types'] = [
                    'audit_logs',
                    'failed_tasks', 
                    'completed_tasks',
                    'cache_entries',
                    'processing_runs',
                    'orphaned_data'
                ]
            except Exception as e:
                logger.error(f"Error getting cleanup stats for management: {sanitize_for_log(str(e))}")
                cleanup_data['error'] = str(e)
        
        return render_template('admin/cleanup_management.html',
                             cleanup_data=cleanup_data,
                             current_user=current_user)
        
    except Exception as e:
        logger.error(f"Error loading cleanup management: {sanitize_for_log(str(e))}")
        return render_template('admin/error.html',
                             error_message="Failed to load cleanup management",
                             error_details=str(e)), 500

def register_performance_monitoring(app):
    """Register performance monitoring with Flask app"""
    app.register_blueprint(performance_bp)
    
    # Add template globals for performance monitoring
    @app.template_global()
    def get_cache_hit_rate():
        """Template global for cache hit rate"""
        try:
            cache_manager = getattr(app, 'cache_manager', None)
            if cache_manager:
                stats = cache_manager.get_cache_stats()
                return stats.get('cache_hit_rate', 0.0)
        except Exception:
            pass
        return 0.0
    
    @app.template_global()
    def get_system_performance_status():
        """Template global for system performance status"""
        try:
            enhanced_admin_service = getattr(app, 'enhanced_admin_service', None)
            if enhanced_admin_service:
                metrics = enhanced_admin_service.get_system_performance_metrics()
                
                # Determine status based on metrics
                if metrics.cache_hit_rate >= 80 and metrics.avg_query_time_ms <= 100:
                    return 'excellent'
                elif metrics.cache_hit_rate >= 60 and metrics.avg_query_time_ms <= 200:
                    return 'good'
                elif metrics.cache_hit_rate >= 40 and metrics.avg_query_time_ms <= 500:
                    return 'fair'
                else:
                    return 'poor'
        except Exception:
            pass
        return 'unknown'