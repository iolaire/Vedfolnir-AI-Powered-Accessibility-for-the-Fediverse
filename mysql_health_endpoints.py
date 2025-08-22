#!/usr/bin/env python3
"""
MySQL-Specific Health Check Endpoints for Vedfolnir

This module provides Flask routes for MySQL health checking, diagnostics,
and monitoring endpoints. These replace any SQLite-based health checks
and provide comprehensive MySQL-specific monitoring capabilities.
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from functools import wraps

from mysql_connection_validator import MySQLConnectionValidator
from config import Config

logger = logging.getLogger(__name__)

# Create Blueprint for MySQL health endpoints
mysql_health_bp = Blueprint('mysql_health', __name__, url_prefix='/health/mysql')

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

@mysql_health_bp.route('/', methods=['GET'])
@require_admin_or_health_check
def mysql_basic_health():
    """
    Basic MySQL health check endpoint.
    
    Returns:
        JSON response with basic MySQL health status
    """
    try:
        validator = MySQLConnectionValidator()
        health_result = validator.perform_health_check()
        
        response = {
            'status': health_result.status,
            'healthy': health_result.healthy,
            'timestamp': health_result.timestamp.isoformat(),
            'service': 'mysql',
            'version': '1.0'
        }
        
        # Add basic metrics for monitoring systems
        if health_result.metrics:
            response['metrics'] = {
                'response_time_ms': health_result.metrics.get('response_time_ms'),
                'connection_usage_percent': health_result.metrics.get('connection_usage_percent')
            }
        
        status_code = 200 if health_result.healthy else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"MySQL health check failed: {e}")
        return jsonify({
            'status': 'error',
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql'
        }), 503

@mysql_health_bp.route('/detailed', methods=['GET'])
@require_admin_or_health_check
def mysql_detailed_health():
    """
    Detailed MySQL health check with comprehensive metrics.
    
    Returns:
        JSON response with detailed MySQL health information
    """
    try:
        validator = MySQLConnectionValidator()
        health_result = validator.perform_health_check()
        
        response = {
            'status': health_result.status,
            'healthy': health_result.healthy,
            'timestamp': health_result.timestamp.isoformat(),
            'service': 'mysql',
            'details': health_result.details,
            'metrics': health_result.metrics
        }
        
        status_code = 200 if health_result.healthy else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Detailed MySQL health check failed: {e}")
        return jsonify({
            'status': 'error',
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql'
        }), 503

@mysql_health_bp.route('/connection', methods=['GET'])
@require_admin_or_health_check
def mysql_connection_validation():
    """
    MySQL connection validation endpoint.
    
    Returns:
        JSON response with connection validation results
    """
    try:
        validator = MySQLConnectionValidator()
        validation_result = validator.validate_connection()
        
        response = {
            'success': validation_result.success,
            'timestamp': datetime.now().isoformat(),
            'connection_time_ms': validation_result.connection_time_ms,
            'service': 'mysql'
        }
        
        if validation_result.success:
            response['server_info'] = validation_result.server_info.__dict__ if validation_result.server_info else {}
            response['validation_details'] = validation_result.validation_details
            response['recommendations'] = validation_result.recommendations
            response['warnings'] = validation_result.warnings
        else:
            response['error'] = validation_result.error_message
        
        status_code = 200 if validation_result.success else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"MySQL connection validation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql'
        }), 503

@mysql_health_bp.route('/compatibility', methods=['GET'])
@require_admin_or_health_check
def mysql_compatibility_check():
    """
    MySQL server compatibility check endpoint.
    
    Returns:
        JSON response with MySQL compatibility analysis
    """
    try:
        validator = MySQLConnectionValidator()
        compatibility_report = validator.get_server_compatibility_report()
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql',
            'compatibility_report': compatibility_report
        }
        
        status_code = 200 if compatibility_report.get('compatible', False) else 503
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"MySQL compatibility check failed: {e}")
        return jsonify({
            'compatible': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql'
        }), 503

@mysql_health_bp.route('/diagnostics', methods=['POST'])
@require_admin_or_health_check
def mysql_connection_diagnostics():
    """
    MySQL connection diagnostics endpoint.
    
    Expects JSON payload with 'database_url' field.
    
    Returns:
        JSON response with diagnostic information
    """
    try:
        data = request.get_json()
        if not data or 'database_url' not in data:
            return jsonify({
                'error': 'database_url is required in JSON payload'
            }), 400
        
        database_url = data['database_url']
        
        # Sanitize URL for logging (remove password)
        sanitized_url = database_url
        if '@' in sanitized_url:
            parts = sanitized_url.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split(':')
                sanitized_url = f"{user_pass[0]}:***@{parts[1]}"
        
        logger.info(f"Running MySQL diagnostics for: {sanitized_url}")
        
        validator = MySQLConnectionValidator()
        diagnostic_report = validator.diagnose_connection_issues(database_url)
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql',
            'diagnostic_report': diagnostic_report
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"MySQL diagnostics failed: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql'
        }), 500

@mysql_health_bp.route('/metrics', methods=['GET'])
@require_admin_or_health_check
def mysql_metrics():
    """
    MySQL performance metrics endpoint.
    
    Returns:
        JSON response with MySQL performance metrics
    """
    try:
        validator = MySQLConnectionValidator()
        health_result = validator.perform_health_check()
        
        # Format metrics for monitoring systems (Prometheus-style)
        metrics = {}
        if health_result.metrics:
            for key, value in health_result.metrics.items():
                if isinstance(value, (int, float)):
                    metrics[f"mysql_{key}"] = value
        
        # Add health status as metric
        metrics['mysql_healthy'] = 1 if health_result.healthy else 0
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql',
            'metrics': metrics
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"MySQL metrics collection failed: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql',
            'metrics': {'mysql_healthy': 0}
        }), 503

@mysql_health_bp.route('/status', methods=['GET'])
@require_admin_or_health_check
def mysql_status_summary():
    """
    MySQL status summary endpoint for dashboards.
    
    Returns:
        JSON response with MySQL status summary
    """
    try:
        validator = MySQLConnectionValidator()
        
        # Get basic health
        health_result = validator.perform_health_check()
        
        # Get validation info
        validation_result = validator.validate_connection()
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql',
            'overall_status': health_result.status,
            'healthy': health_result.healthy,
            'connection_valid': validation_result.success,
            'response_time_ms': health_result.metrics.get('response_time_ms', 0) if health_result.metrics else 0
        }
        
        # Add server info if available
        if validation_result.server_info:
            summary['server_version'] = validation_result.server_info.version
            summary['character_set'] = validation_result.server_info.character_set
            summary['ssl_support'] = validation_result.server_info.ssl_support
        
        # Add key metrics
        if health_result.metrics:
            summary['connection_usage_percent'] = health_result.metrics.get('connection_usage_percent', 0)
            summary['slow_query_ratio_percent'] = health_result.metrics.get('slow_query_ratio_percent', 0)
        
        # Add warnings and recommendations count
        summary['warnings_count'] = len(validation_result.warnings) if validation_result.warnings else 0
        summary['recommendations_count'] = len(validation_result.recommendations) if validation_result.recommendations else 0
        
        status_code = 200 if health_result.healthy and validation_result.success else 503
        return jsonify(summary), status_code
        
    except Exception as e:
        logger.error(f"MySQL status summary failed: {e}")
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'service': 'mysql',
            'overall_status': 'error',
            'healthy': False,
            'error': str(e)
        }), 503

# Health check endpoint for container orchestration (Docker, Kubernetes)
@mysql_health_bp.route('/ready', methods=['GET'])
def mysql_readiness_probe():
    """
    MySQL readiness probe for container orchestration.
    
    This endpoint is designed for container health checks and
    returns minimal response for performance.
    
    Returns:
        Simple JSON response indicating MySQL readiness
    """
    try:
        validator = MySQLConnectionValidator()
        validation_result = validator.validate_connection()
        
        if validation_result.success:
            return jsonify({'ready': True}), 200
        else:
            return jsonify({'ready': False}), 503
            
    except Exception:
        return jsonify({'ready': False}), 503

@mysql_health_bp.route('/live', methods=['GET'])
def mysql_liveness_probe():
    """
    MySQL liveness probe for container orchestration.
    
    This endpoint checks if the MySQL health check system itself is working.
    
    Returns:
        Simple JSON response indicating system liveness
    """
    try:
        # Just check if we can create a validator instance
        validator = MySQLConnectionValidator()
        return jsonify({'alive': True}), 200
    except Exception:
        return jsonify({'alive': False}), 503

def register_mysql_health_endpoints(app):
    """
    Register MySQL health check endpoints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(mysql_health_bp)
    logger.info("MySQL health check endpoints registered")
    
    # Add a general health endpoint that includes MySQL
    @app.route('/health')
    def general_health():
        """General health check that includes MySQL status."""
        try:
            validator = MySQLConnectionValidator()
            mysql_health = validator.perform_health_check()
            
            # Check Redis if configured
            redis_healthy = True
            try:
                redis_validation = validator._validate_redis_connection()
                redis_healthy = redis_validation[0]
            except:
                redis_healthy = False
            
            overall_healthy = mysql_health.healthy and redis_healthy
            
            response = {
                'status': 'healthy' if overall_healthy else 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'services': {
                    'mysql': {
                        'healthy': mysql_health.healthy,
                        'status': mysql_health.status
                    },
                    'redis': {
                        'healthy': redis_healthy
                    }
                }
            }
            
            status_code = 200 if overall_healthy else 503
            return jsonify(response), status_code
            
        except Exception as e:
            logger.error(f"General health check failed: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503
