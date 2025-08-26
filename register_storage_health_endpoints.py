# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Registration script for storage health endpoints.

This script registers storage health check endpoints with the Flask application
and integrates them with the existing health check infrastructure.
"""

import logging
from flask import Flask

from storage_health_endpoints import register_storage_health_endpoints

logger = logging.getLogger(__name__)


def register_all_storage_health_endpoints(app: Flask) -> None:
    """
    Register all storage health endpoints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    try:
        # Register storage health endpoints
        register_storage_health_endpoints(app)
        
        logger.info("All storage health endpoints registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register storage health endpoints: {e}")
        raise


def integrate_storage_health_with_general_health(app: Flask) -> None:
    """
    Integrate storage health checks with the general health endpoint.
    
    Args:
        app: Flask application instance
    """
    try:
        from storage_health_checker import StorageHealthChecker, StorageHealthStatus
        
        # Get existing general health endpoint and enhance it
        @app.route('/health/comprehensive')
        def comprehensive_health_with_storage():
            """Comprehensive health check including storage system."""
            try:
                # Get storage health checker
                from storage_health_endpoints import get_storage_health_checker
                storage_health_checker = get_storage_health_checker()
                
                # Get storage health
                storage_health = storage_health_checker.check_comprehensive_health()
                
                # Get other system health (if available)
                system_health = {'status': 'healthy'}  # Placeholder
                
                # Combine health results
                overall_healthy = (
                    storage_health.overall_status == StorageHealthStatus.HEALTHY and
                    system_health['status'] == 'healthy'
                )
                
                response = {
                    'status': 'healthy' if overall_healthy else 'unhealthy',
                    'timestamp': storage_health.timestamp.isoformat(),
                    'components': {
                        'storage': {
                            'status': storage_health.overall_status.value,
                            'healthy': storage_health.overall_status == StorageHealthStatus.HEALTHY,
                            'components_healthy': storage_health.summary['healthy_components'],
                            'components_total': storage_health.summary['total_components'],
                            'alerts_count': len(storage_health.alerts)
                        },
                        'system': system_health
                    }
                }
                
                status_code = 200 if overall_healthy else 503
                return response, status_code
                
            except Exception as e:
                logger.error(f"Comprehensive health check failed: {e}")
                return {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, 503
        
        logger.info("Storage health integrated with comprehensive health endpoint")
        
    except Exception as e:
        logger.error(f"Failed to integrate storage health with general health: {e}")


if __name__ == '__main__':
    # Example usage
    from flask import Flask
    
    app = Flask(__name__)
    
    # Register storage health endpoints
    register_all_storage_health_endpoints(app)
    
    # Integrate with general health
    integrate_storage_health_with_general_health(app)
    
    print("Storage health endpoints registered successfully!")
    print("Available endpoints:")
    print("- /health/storage - Basic storage health")
    print("- /health/storage/detailed - Detailed storage health")
    print("- /health/storage/configuration - Configuration health")
    print("- /health/storage/monitoring - Monitoring service health")
    print("- /health/storage/enforcement - Enforcement service health")
    print("- /health/storage/metrics - Storage metrics")
    print("- /health/storage/alerts - Storage alerts")
    print("- /health/storage/performance - Performance metrics")
    print("- /health/storage/ready - Readiness probe")
    print("- /health/storage/live - Liveness probe")
    print("- /health/comprehensive - Comprehensive health with storage")