# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Container Metrics Collection for Docker Environment
Provides container-specific monitoring and health metrics
"""

import os
import time
import psutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from flask import Blueprint, jsonify, request
from flask_login import login_required

logger = logging.getLogger(__name__)


@dataclass
class ContainerMetrics:
    """Container metrics data structure"""
    timestamp: str
    container_id: str
    container_name: str
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_mb: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    process_count: int
    gunicorn_workers: int
    rq_workers_active: bool
    health_status: str


class ContainerMetricsCollector:
    """Collects and manages container-specific metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.is_container = self._detect_container_environment()
        self.container_id = self._get_container_id()
        self.container_name = self._get_container_name()
        
        logger.info(f"Container metrics collector initialized - Container: {self.is_container}")
    
    def _detect_container_environment(self) -> bool:
        """Detect if running in a container"""
        return (
            os.path.exists('/.dockerenv') or
            os.getenv('CONTAINER_ENV') == 'true' or
            os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup').read()
        )
    
    def _get_container_id(self) -> str:
        """Get container ID if available"""
        try:
            if os.path.exists('/proc/self/cgroup'):
                with open('/proc/self/cgroup', 'r') as f:
                    for line in f:
                        if 'docker' in line:
                            return line.split('/')[-1].strip()[:12]
            return os.getenv('HOSTNAME', 'unknown')
        except Exception:
            return 'unknown'
    
    def _get_container_name(self) -> str:
        """Get container name"""
        return os.getenv('CONTAINER_NAME', os.getenv('HOSTNAME', 'vedfolnir'))
    
    def collect_metrics(self) -> ContainerMetrics:
        """Collect current container metrics"""
        try:
            # Basic system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network_io = self._get_network_io()
            
            # Process information
            process_count = len(psutil.pids())
            gunicorn_workers = self._count_gunicorn_workers()
            
            # RQ worker status
            rq_workers_active = self._check_rq_workers()
            
            # Health status
            health_status = self._get_health_status()
            
            return ContainerMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                container_id=self.container_id,
                container_name=self.container_name,
                uptime_seconds=time.time() - self.start_time,
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory.used / (1024 * 1024),
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io=network_io,
                process_count=process_count,
                gunicorn_workers=gunicorn_workers,
                rq_workers_active=rq_workers_active,
                health_status=health_status
            )
            
        except Exception as e:
            logger.error(f"Error collecting container metrics: {e}")
            raise
    
    def _get_network_io(self) -> Dict[str, int]:
        """Get network I/O statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except Exception:
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0
            }
    
    def _count_gunicorn_workers(self) -> int:
        """Count active Gunicorn worker processes"""
        try:
            count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'gunicorn' in cmdline and 'web_app:app' in cmdline:
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return count
        except Exception:
            return 0
    
    def _check_rq_workers(self) -> bool:
        """Check if RQ workers are active"""
        try:
            if os.getenv('RQ_ENABLE_INTEGRATED_WORKERS', 'false').lower() != 'true':
                return False
            
            # Try to import and check RQ integration
            from app.services.task.rq.gunicorn_integration import get_rq_integration
            integration = get_rq_integration()
            
            if integration:
                status = integration.get_worker_status()
                return status.get('initialized', False)
            
            return False
        except Exception:
            return False
    
    def _get_health_status(self) -> str:
        """Get overall health status"""
        try:
            # Simple health check based on resource usage
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            if memory.percent > 95 or disk.percent > 95:
                return 'critical'
            elif memory.percent > 85 or disk.percent > 85:
                return 'warning'
            else:
                return 'healthy'
        except Exception:
            return 'unknown'
    
    def get_resource_limits(self) -> Dict[str, Any]:
        """Get container resource limits"""
        limits = {}
        
        # Memory limit
        memory_limit = os.getenv('MEMORY_LIMIT')
        if memory_limit:
            limits['memory_limit'] = memory_limit
        
        # CPU limit
        cpu_limit = os.getenv('CPU_LIMIT')
        if cpu_limit:
            limits['cpu_limit'] = cpu_limit
        
        # Gunicorn workers
        gunicorn_workers = os.getenv('GUNICORN_WORKERS')
        if gunicorn_workers:
            limits['gunicorn_workers'] = int(gunicorn_workers)
        
        return limits
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get container environment information"""
        return {
            'is_container': self.is_container,
            'container_id': self.container_id,
            'container_name': self.container_name,
            'flask_env': os.getenv('FLASK_ENV', 'production'),
            'flask_debug': os.getenv('FLASK_DEBUG', '0') == '1',
            'rq_integrated_workers': os.getenv('RQ_ENABLE_INTEGRATED_WORKERS', 'false').lower() == 'true',
            'json_logging': os.getenv('ENABLE_JSON_LOGGING', 'false').lower() == 'true',
            'python_version': os.sys.version.split()[0],
            'uptime_seconds': time.time() - self.start_time
        }


# Global metrics collector instance
_metrics_collector: Optional[ContainerMetricsCollector] = None


def get_metrics_collector() -> ContainerMetricsCollector:
    """Get or create the global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = ContainerMetricsCollector()
    return _metrics_collector


def create_container_metrics_blueprint() -> Blueprint:
    """Create Flask blueprint for container metrics endpoints"""
    bp = Blueprint('container_metrics', __name__, url_prefix='/api/container')
    
    @bp.route('/metrics')
    @login_required
    def get_metrics():
        """Get current container metrics"""
        try:
            collector = get_metrics_collector()
            metrics = collector.collect_metrics()
            
            return jsonify({
                'success': True,
                'data': {
                    'timestamp': metrics.timestamp,
                    'container': {
                        'id': metrics.container_id,
                        'name': metrics.container_name,
                        'uptime_seconds': metrics.uptime_seconds
                    },
                    'resources': {
                        'cpu_usage_percent': metrics.cpu_usage_percent,
                        'memory_usage_mb': metrics.memory_usage_mb,
                        'memory_usage_percent': metrics.memory_usage_percent,
                        'disk_usage_percent': metrics.disk_usage_percent
                    },
                    'network': metrics.network_io,
                    'processes': {
                        'total_count': metrics.process_count,
                        'gunicorn_workers': metrics.gunicorn_workers,
                        'rq_workers_active': metrics.rq_workers_active
                    },
                    'health_status': metrics.health_status
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting container metrics: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @bp.route('/environment')
    @login_required
    def get_environment():
        """Get container environment information"""
        try:
            collector = get_metrics_collector()
            env_info = collector.get_environment_info()
            resource_limits = collector.get_resource_limits()
            
            return jsonify({
                'success': True,
                'data': {
                    'environment': env_info,
                    'resource_limits': resource_limits
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting environment info: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @bp.route('/health')
    def get_health():
        """Get container health status (public endpoint for orchestration)"""
        try:
            collector = get_metrics_collector()
            metrics = collector.collect_metrics()
            
            # Simple health response for container orchestration
            is_healthy = metrics.health_status in ['healthy', 'warning']
            
            response = {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'timestamp': metrics.timestamp,
                'container_id': metrics.container_id,
                'uptime_seconds': metrics.uptime_seconds,
                'health_status': metrics.health_status
            }
            
            status_code = 200 if is_healthy else 503
            return jsonify(response), status_code
            
        except Exception as e:
            logger.error(f"Error getting container health: {e}")
            return jsonify({
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }), 500
    
    @bp.route('/logs')
    @login_required
    def get_recent_logs():
        """Get recent container logs"""
        try:
            log_type = request.args.get('type', 'app')  # app, gunicorn, rq
            lines = int(request.args.get('lines', 100))
            
            log_files = {
                'app': '/app/logs/app/vedfolnir.log',
                'gunicorn': '/app/logs/gunicorn_error.log',
                'rq': '/app/logs/rq/rq_worker.log'
            }
            
            log_file = log_files.get(log_type)
            if not log_file or not os.path.exists(log_file):
                return jsonify({
                    'success': False,
                    'error': f'Log file not found: {log_type}'
                }), 404
            
            # Read last N lines
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-lines:]
            
            return jsonify({
                'success': True,
                'data': {
                    'log_type': log_type,
                    'lines_requested': lines,
                    'lines_returned': len(log_lines),
                    'logs': [line.strip() for line in log_lines]
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return bp


def register_container_metrics(app):
    """Register container metrics blueprint with Flask app"""
    try:
        bp = create_container_metrics_blueprint()
        app.register_blueprint(bp)
        logger.info("Container metrics endpoints registered successfully")
    except Exception as e:
        logger.error(f"Failed to register container metrics endpoints: {e}")