# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Health check endpoints for Docker container orchestration and monitoring.
Provides comprehensive health status for all application components.
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
import logging
import psutil
import os
import redis
import requests
from urllib.parse import urlparse
from sqlalchemy import text

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

@health_bp.route('/health')
def health_check():
    """
    Main health check endpoint for Docker container health checks.
    Returns comprehensive health status of all application components.
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'components': {}
        }
        
        overall_healthy = True
        
        # Check application health
        app_health = check_application_health()
        health_status['components']['application'] = app_health
        if not app_health['healthy']:
            overall_healthy = False
        
        # Check database connectivity
        db_health = check_database_health()
        health_status['components']['database'] = db_health
        if not db_health['healthy']:
            overall_healthy = False
        
        # Check Redis connectivity
        redis_health = check_redis_health()
        health_status['components']['redis'] = redis_health
        if not redis_health['healthy']:
            overall_healthy = False
        
        # Check external Ollama API
        ollama_health = check_ollama_health()
        health_status['components']['ollama'] = ollama_health
        # Ollama is not critical for basic health
        
        # Check RQ workers
        rq_health = check_rq_workers_health()
        health_status['components']['rq_workers'] = rq_health
        if not rq_health['healthy'] and os.getenv('RQ_ENABLE_INTEGRATED_WORKERS') == 'true':
            overall_healthy = False
        
        # Check system resources
        resource_health = check_system_resources()
        health_status['components']['resources'] = resource_health
        if not resource_health['healthy']:
            overall_healthy = False
        
        # Set overall status
        health_status['status'] = 'healthy' if overall_healthy else 'unhealthy'
        
        return jsonify(health_status), 200 if overall_healthy else 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@health_bp.route('/health/ready')
def readiness_check():
    """
    Readiness check endpoint for Kubernetes/Docker orchestration.
    Checks if the application is ready to serve traffic.
    """
    try:
        # Check critical dependencies
        db_health = check_database_health()
        redis_health = check_redis_health()
        
        ready = db_health['healthy'] and redis_health['healthy']
        
        return jsonify({
            'ready': ready,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'database': db_health['healthy'],
                'redis': redis_health['healthy']
            }
        }), 200 if ready else 503
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'ready': False,
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

@health_bp.route('/health/live')
def liveness_check():
    """
    Liveness check endpoint for Kubernetes/Docker orchestration.
    Simple check to verify the application is running.
    """
    return jsonify({
        'alive': True,
        'timestamp': datetime.utcnow().isoformat(),
        'uptime': get_uptime()
    }), 200

@health_bp.route('/metrics')
def metrics_endpoint():
    """
    Prometheus-compatible metrics endpoint for monitoring.
    """
    try:
        metrics = []
        
        # Application metrics
        metrics.append('# HELP vedfolnir_health_status Application health status (1=healthy, 0=unhealthy)')
        metrics.append('# TYPE vedfolnir_health_status gauge')
        
        # Get component health
        db_healthy = 1 if check_database_health()['healthy'] else 0
        redis_healthy = 1 if check_redis_health()['healthy'] else 0
        ollama_healthy = 1 if check_ollama_health()['healthy'] else 0
        
        metrics.append(f'vedfolnir_health_status{{component="database"}} {db_healthy}')
        metrics.append(f'vedfolnir_health_status{{component="redis"}} {redis_healthy}')
        metrics.append(f'vedfolnir_health_status{{component="ollama"}} {ollama_healthy}')
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        metrics.append('# HELP vedfolnir_cpu_usage_percent CPU usage percentage')
        metrics.append('# TYPE vedfolnir_cpu_usage_percent gauge')
        metrics.append(f'vedfolnir_cpu_usage_percent {cpu_percent}')
        
        metrics.append('# HELP vedfolnir_memory_usage_percent Memory usage percentage')
        metrics.append('# TYPE vedfolnir_memory_usage_percent gauge')
        metrics.append(f'vedfolnir_memory_usage_percent {memory.percent}')
        
        metrics.append('# HELP vedfolnir_disk_usage_percent Disk usage percentage')
        metrics.append('# TYPE vedfolnir_disk_usage_percent gauge')
        metrics.append(f'vedfolnir_disk_usage_percent {disk.percent}')
        
        # Uptime metric
        uptime = get_uptime()
        metrics.append('# HELP vedfolnir_uptime_seconds Application uptime in seconds')
        metrics.append('# TYPE vedfolnir_uptime_seconds counter')
        metrics.append(f'vedfolnir_uptime_seconds {uptime}')
        
        return '\n'.join(metrics), 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return f"# Error generating metrics: {e}\n", 500, {'Content-Type': 'text/plain; charset=utf-8'}

def check_application_health():
    """Check application-specific health indicators."""
    try:
        # Check if Flask app is properly initialized
        if not current_app:
            return {'healthy': False, 'message': 'Flask app not initialized'}
        
        # Check if database manager is available
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            return {'healthy': False, 'message': 'Database manager not available'}
        
        # Check if health checker is available
        health_checker = current_app.config.get('health_checker')
        if health_checker:
            try:
                uptime = health_checker.get_uptime()
                return {'healthy': True, 'message': f'Application running (uptime: {uptime:.1f}s)'}
            except Exception as e:
                return {'healthy': False, 'message': f'Health checker error: {e}'}
        
        return {'healthy': True, 'message': 'Application components available'}
        
    except Exception as e:
        return {'healthy': False, 'message': f'Application check failed: {e}'}

def check_database_health():
    """Check database connectivity and basic operations."""
    try:
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            return {'healthy': False, 'message': 'Database manager not available'}
        
        # Test database connection with timeout
        with db_manager.get_session() as session:
            result = session.execute(text('SELECT 1')).scalar()
            if result == 1:
                return {'healthy': True, 'message': 'Database connection OK'}
            else:
                return {'healthy': False, 'message': 'Database query returned unexpected result'}
                
    except Exception as e:
        return {'healthy': False, 'message': f'Database check failed: {e}'}

def check_redis_health():
    """Check Redis connectivity and basic operations."""
    try:
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            return {'healthy': False, 'message': 'Redis URL not configured'}
        
        # Parse Redis URL
        parsed = urlparse(redis_url)
        
        # Create Redis connection
        r = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            password=parsed.password,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Test ping
        if r.ping():
            # Test basic operations
            test_key = 'health_check_test'
            r.set(test_key, 'test_value', ex=60)
            value = r.get(test_key)
            r.delete(test_key)
            
            if value == b'test_value':
                return {'healthy': True, 'message': 'Redis connection and operations OK'}
            else:
                return {'healthy': False, 'message': 'Redis operations failed'}
        else:
            return {'healthy': False, 'message': 'Redis ping failed'}
            
    except Exception as e:
        return {'healthy': False, 'message': f'Redis check failed: {e}'}

def check_ollama_health():
    """Check external Ollama API connectivity."""
    try:
        ollama_url = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11434')
        
        # Test Ollama API with timeout
        response = requests.get(f'{ollama_url}/api/version', timeout=10)
        if response.status_code == 200:
            version_data = response.json()
            return {'healthy': True, 'message': f'Ollama API OK (version: {version_data.get("version", "unknown")})'}
        else:
            return {'healthy': False, 'message': f'Ollama API returned status {response.status_code}'}
            
    except requests.exceptions.Timeout:
        return {'healthy': False, 'message': 'Ollama API timeout'}
    except requests.exceptions.ConnectionError:
        return {'healthy': False, 'message': 'Ollama API connection failed'}
    except Exception as e:
        return {'healthy': False, 'message': f'Ollama check failed: {e}'}

def check_rq_workers_health():
    """Check RQ workers status if integrated workers are enabled."""
    try:
        if os.getenv('RQ_ENABLE_INTEGRATED_WORKERS') != 'true':
            return {'healthy': True, 'message': 'RQ workers disabled'}
        
        # Check if RQ integration is available
        try:
            from app.services.task.rq.gunicorn_integration import get_rq_integration
            integration = get_rq_integration()
            
            if integration:
                status = integration.get_worker_status()
                if status.get('initialized', False):
                    worker_count = status.get('worker_count', 0)
                    return {'healthy': True, 'message': f'RQ workers OK ({worker_count} workers)'}
                else:
                    return {'healthy': False, 'message': 'RQ workers not initialized'}
            else:
                return {'healthy': False, 'message': 'RQ integration not available'}
                
        except ImportError:
            return {'healthy': False, 'message': 'RQ integration module not found'}
            
    except Exception as e:
        return {'healthy': False, 'message': f'RQ workers check failed: {e}'}

def check_system_resources():
    """Check system resource usage."""
    try:
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 95:
            return {'healthy': False, 'message': f'Critical memory usage: {memory.percent}%'}
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > 95:
            return {'healthy': False, 'message': f'Critical disk usage: {disk.percent}%'}
        
        # Check CPU usage (average over 1 second)
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 95:
            return {'healthy': False, 'message': f'Critical CPU usage: {cpu_percent}%'}
        
        return {'healthy': True, 'message': f'Resources OK (CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%)'}
        
    except Exception as e:
        return {'healthy': False, 'message': f'Resource check failed: {e}'}

def get_uptime():
    """Get application uptime in seconds."""
    try:
        health_checker = current_app.config.get('health_checker')
        if health_checker and hasattr(health_checker, 'get_uptime'):
            return health_checker.get_uptime()
        else:
            # Fallback to process uptime
            import time
            return time.time() - psutil.Process().create_time()
    except Exception:
        return 0