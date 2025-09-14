# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Health Check Endpoints for Vedfolnir

This module provides Flask routes for storage system health checking, monitoring,
and diagnostics endpoints. These integrate with the existing health check infrastructure
and provide comprehensive storage system monitoring capabilities.
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from functools import wraps

from .storage_health_checker import StorageHealthChecker, StorageHealthStatus
from .storage_configuration_service import StorageConfigurationService
from .storage_monitor_service import StorageMonitorService
from .storage_limit_enforcer import StorageLimitEnforcer

logger = logging.getLogger(__name__)

# Create Blueprint for storage health endpoints
storage_health_bp = Blueprint('storage_health', __name__, url_prefix='/health/storage')

def require_admin_or_health_check(f):
    """Decorator to require admin access or allow health check access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow health checks from localhost without authentication
        if request.remote_addr in ['127.0.0.1', '::1', 'localhost']:
            return f(*args, **kwargs)
        
        # For other requests, require admin authentication
        from flask_login import current_user
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def get_storage_health_checker():
    """Get or create storage health checker instance"""
    if not hasattr(current_app, '_storage_health_checker'):
        # Initialize storage services
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        
        # Try to get enforcer service if available
        enforcer_service = None
        try:
            # Get database manager from app context if available
            db_manager = getattr(current_app, 'db_manager', None)
            if db_manager:
                enforcer_service = StorageLimitEnforcer(
                    config_service=config_service,
                    monitor_service=monitor_service,
                    db_manager=db_manager
                )
        except Exception as e:
            logger.warning(f"Could not initialize storage enforcer for health checks: {e}")
        
        current_app._storage_health_checker = StorageHealthChecker(
            config_service=config_service,
            monitor_service=monitor_service,
            enforcer_service=enforcer_service
        )
    
    return current_app._storage_health_checker

@storage_health_bp.route('/', methods=['GET'])
@require_admin_or_health_check
def storage_basic_health():
    """
    Basic storage system health check endpoint.
    
    Returns:
        JSON response with basic storage system health status
    """
    try:
        health_checker = get_storage_health_checker()
        health_result = health_checker.check_comprehensive_health()
        
        response = {
            'status': health_result.overall_status.value,
            'healthy': health_result.overall_status == StorageHealthStatus.HEALTHY,
            'timestamp': health_result.timestamp.isoformat(),
            'service': 'storage',
            'version': '1.0'
        }
        
        # Add basic metrics for monitoring systems
        response['metrics'] = {
            'components_healthy': health_result.summary['healthy_components'],
            'components_total': health_result.summary['total_components'],
            'health_percentage': health_result.summary['health_percentage'],
            'alerts_count': len(health_result.alerts)
        }
        
        # Add storage usage if available
        if 'monitoring_storage_usage_gb' in health_result.performance_metrics:
            response['metrics']['storage_usage_gb'] = health_result.performance_metrics['monitoring_storage_usage_gb']
            response['metrics']['storage_limit_gb'] = health_result.performance_metrics['monitoring_storage_limit_gb']
            response['metrics']['usage_percentage'] = health_result.performance_metrics['monitoring_usage_percentage']
        
        status_code = 200 if health_result.overall_status == StorageHealthStatus.HEALTHY else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return jsonify({
            'status': 'error',
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage'
        }), 503

@storage_health_bp.route('/detailed', methods=['GET'])
@require_admin_or_health_check
def storage_detailed_health():
    """
    Detailed storage system health check with comprehensive information.
    
    Returns:
        JSON response with detailed storage system health information
    """
    try:
        health_checker = get_storage_health_checker()
        health_result = health_checker.check_comprehensive_health()
        
        # Convert components to serializable format
        components_data = {}
        for name, component in health_result.components.items():
            components_data[name] = {
                'status': component.status.value,
                'message': component.message,
                'response_time_ms': component.response_time_ms,
                'last_check': component.last_check.isoformat() if component.last_check else None,
                'details': component.details,
                'metrics': component.metrics
            }
        
        response = {
            'status': health_result.overall_status.value,
            'healthy': health_result.overall_status == StorageHealthStatus.HEALTHY,
            'timestamp': health_result.timestamp.isoformat(),
            'service': 'storage',
            'components': components_data,
            'summary': health_result.summary,
            'alerts': health_result.alerts,
            'performance_metrics': health_result.performance_metrics
        }
        
        status_code = 200 if health_result.overall_status == StorageHealthStatus.HEALTHY else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Detailed storage health check failed: {e}")
        return jsonify({
            'status': 'error',
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage'
        }), 503

@storage_health_bp.route('/configuration', methods=['GET'])
@require_admin_or_health_check
def storage_configuration_health():
    """
    Storage configuration health check endpoint.
    
    Returns:
        JSON response with storage configuration validation results
    """
    try:
        config_service = StorageConfigurationService()
        
        # Validate configuration
        is_valid = config_service.validate_storage_config()
        config_summary = config_service.get_configuration_summary()
        
        response = {
            'valid': is_valid,
            'timestamp': datetime.now().isoformat(),
            'service': 'storage_configuration',
            'configuration': config_summary
        }
        
        status_code = 200 if is_valid else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Storage configuration health check failed: {e}")
        return jsonify({
            'valid': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage_configuration'
        }), 503

@storage_health_bp.route('/monitoring', methods=['GET'])
@require_admin_or_health_check
def storage_monitoring_health():
    """
    Storage monitoring service health check endpoint.
    
    Returns:
        JSON response with storage monitoring service status
    """
    try:
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        
        # Get storage metrics
        metrics = monitor_service.get_storage_metrics()
        cache_info = monitor_service.get_cache_info()
        
        response = {
            'healthy': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'storage_monitoring',
            'storage_metrics': metrics.to_dict(),
            'cache_info': cache_info,
            'monitoring_enabled': config_service.is_storage_monitoring_enabled()
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Storage monitoring health check failed: {e}")
        return jsonify({
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage_monitoring'
        }), 503

@storage_health_bp.route('/enforcement', methods=['GET'])
@require_admin_or_health_check
def storage_enforcement_health():
    """
    Storage limit enforcement health check endpoint.
    
    Returns:
        JSON response with storage enforcement system status
    """
    try:
        # Try to get enforcer service
        db_manager = getattr(current_app, 'db_manager', None)
        if not db_manager:
            return jsonify({
                'healthy': False,
                'error': 'Database manager not available',
                'timestamp': datetime.now().isoformat(),
                'service': 'storage_enforcement'
            }), 503
        
        config_service = StorageConfigurationService()
        monitor_service = StorageMonitorService(config_service)
        enforcer_service = StorageLimitEnforcer(
            config_service=config_service,
            monitor_service=monitor_service,
            db_manager=db_manager
        )
        
        # Get enforcer health
        enforcer_health = enforcer_service.health_check()
        enforcement_stats = enforcer_service.get_enforcement_statistics()
        
        response = {
            'healthy': enforcer_health.get('overall_healthy', False),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage_enforcement',
            'health_details': enforcer_health,
            'enforcement_statistics': enforcement_stats
        }
        
        status_code = 200 if enforcer_health.get('overall_healthy', False) else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Storage enforcement health check failed: {e}")
        return jsonify({
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage_enforcement'
        }), 503

@storage_health_bp.route('/metrics', methods=['GET'])
@require_admin_or_health_check
def storage_metrics():
    """
    Storage system metrics endpoint for monitoring integration.
    
    Returns:
        JSON response with storage system metrics in monitoring-friendly format
    """
    try:
        health_checker = get_storage_health_checker()
        metrics = health_checker.get_storage_health_metrics()
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'service': 'storage',
            'metrics': metrics
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Storage metrics collection failed: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage',
            'metrics': {'storage_system_healthy': 0}
        }), 503

@storage_health_bp.route('/alerts', methods=['GET'])
@require_admin_or_health_check
def storage_alerts():
    """
    Storage system alerts endpoint.
    
    Returns:
        JSON response with current storage system alerts
    """
    try:
        health_checker = get_storage_health_checker()
        alerts = health_checker.get_storage_alerts()
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'service': 'storage',
            'alerts': alerts,
            'alerts_count': len(alerts)
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Storage alerts collection failed: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage',
            'alerts': [],
            'alerts_count': 0
        }), 503

@storage_health_bp.route('/performance', methods=['GET'])
@require_admin_or_health_check
def storage_performance():
    """
    Storage system performance metrics endpoint.
    
    Returns:
        JSON response with storage system performance information
    """
    try:
        health_checker = get_storage_health_checker()
        health_result = health_checker.check_comprehensive_health()
        
        # Extract performance-specific information
        performance_data = {
            'overall_response_time_ms': health_result.performance_metrics.get('total_response_time_ms', 0),
            'avg_component_response_time_ms': health_result.performance_metrics.get('avg_component_response_time_ms', 0),
            'max_component_response_time_ms': health_result.performance_metrics.get('max_component_response_time_ms', 0),
            'components_performance': {}
        }
        
        # Add component-specific performance metrics
        for name, component in health_result.components.items():
            if component.response_time_ms is not None:
                performance_data['components_performance'][name] = {
                    'response_time_ms': component.response_time_ms,
                    'status': component.status.value
                }
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'service': 'storage',
            'performance': performance_data
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Storage performance metrics collection failed: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'storage'
        }), 503

# Health check endpoint for container orchestration (Docker, Kubernetes)
@storage_health_bp.route('/ready', methods=['GET'])
def storage_readiness_probe():
    """
    Storage system readiness probe for container orchestration.
    
    This endpoint is designed for container health checks and
    returns minimal response for performance.
    
    Returns:
        Simple JSON response indicating storage system readiness
    """
    try:
        health_checker = get_storage_health_checker()
        health_result = health_checker.check_comprehensive_health()
        
        ready = health_result.overall_status in [StorageHealthStatus.HEALTHY, StorageHealthStatus.DEGRADED]
        
        if ready:
            return jsonify({'ready': True}), 200
        else:
            return jsonify({'ready': False}), 503
            
    except Exception:
        return jsonify({'ready': False}), 503

@storage_health_bp.route('/live', methods=['GET'])
def storage_liveness_probe():
    """
    Storage system liveness probe for container orchestration.
    
    This endpoint checks if the storage health check system itself is working.
    
    Returns:
        Simple JSON response indicating system liveness
    """
    try:
        # Just check if we can create a health checker instance
        health_checker = get_storage_health_checker()
        return jsonify({'alive': True}), 200
    except Exception:
        return jsonify({'alive': False}), 503

def register_storage_health_endpoints(app):
    """
    Register storage health check endpoints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(storage_health_bp)
    logger.info("Storage health check endpoints registered")
    
    # Add storage health to the general health endpoint
    @app.route('/health/storage-summary')
    @require_admin_or_health_check
    def storage_health_summary():
        """Storage health summary for integration with general health endpoint."""
        try:
            health_checker = get_storage_health_checker()
            health_result = health_checker.check_comprehensive_health()
            
            response = {
                'status': health_result.overall_status.value,
                'healthy': health_result.overall_status == StorageHealthStatus.HEALTHY,
                'timestamp': health_result.timestamp.isoformat(),
                'components_healthy': health_result.summary['healthy_components'],
                'components_total': health_result.summary['total_components'],
                'alerts_count': len(health_result.alerts)
            }
            
            status_code = 200 if health_result.overall_status == StorageHealthStatus.HEALTHY else 503
            return jsonify(response), status_code
            
        except Exception as e:
            logger.error(f"Storage health summary failed: {e}")
            return jsonify({
                'status': 'error',
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503