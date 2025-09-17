# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Worker Manager

Manages worker processes and their lifecycle within Gunicorn with proper coordination.
Supports both integrated workers (daemon threads) and external worker processes.
"""

import logging
import threading
import time
import uuid
import atexit
import subprocess
import os
from typing import Dict, List, Optional, Any
import redis
from flask import Flask

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from .rq_config import RQConfig, WorkerConfig
from .integrated_rq_worker import IntegratedRQWorker
from .resource_manager import RQResourceManager

logger = logging.getLogger(__name__)


class RQWorkerManager:
    """Manages RQ worker processes and their lifecycle within Gunicorn"""
    
    def __init__(self, redis_connection: redis.Redis, config: RQConfig, 
                 db_manager: DatabaseManager, app_context: Flask):
        """
        Initialize RQWorkerManager
        
        Args:
            redis_connection: Redis connection instance
            config: RQ configuration
            db_manager: Database manager instance
            app_context: Flask application instance
        """
        self.redis_connection = redis_connection
        self.config = config
        self.db_manager = db_manager
        self.app_context = app_context
        
        # Initialize resource manager if config is production config
        self.resource_manager: Optional[RQResourceManager] = None
        if hasattr(config, 'environment'):
            from .resource_manager import RQResourceManager
            self.resource_manager = RQResourceManager(config)
        
        # Worker management
        self.integrated_workers: Dict[str, IntegratedRQWorker] = {}
        self.external_workers: Dict[str, subprocess.Popen] = {}
        self.worker_configs: Dict[str, WorkerConfig] = {}
        
        # Coordination
        self.worker_id = self._generate_unique_worker_id()
        self.coordination_key = f"rq:workers:{self.worker_id}"
        self.shutdown_timeout = 30  # seconds
        
        # State management
        self._lock = threading.Lock()
        self._shutdown_requested = False
        self._initialized = False
        
        # Health monitoring
        self._health_check_interval = 30  # seconds
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_monitoring = False
        
        # Register cleanup on exit
        atexit.register(self.cleanup_and_stop)
    
    def _generate_unique_worker_id(self) -> str:
        """Generate unique worker manager ID"""
        return f"manager-{uuid.uuid4().hex[:8]}-{int(time.time())}"
    
    def initialize(self) -> bool:
        """Initialize worker manager"""
        if self._initialized:
            logger.warning("Worker manager already initialized")
            return True
        
        try:
            with self._lock:
                # Register worker coordination
                self.register_worker_coordination()
                
                # Load worker configurations
                self._load_worker_configurations()
                
                # Start health monitoring
                self._start_health_monitoring()
                
                # Start resource management
                if self.resource_manager:
                    self.resource_manager.start()
                    logger.info("RQ resource management started")
                
                self._initialized = True
                logger.info(f"RQ Worker Manager {self.worker_id} initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize RQ Worker Manager: {sanitize_for_log(str(e))}")
            return False
    
    def _load_worker_configurations(self) -> None:
        """Load worker configurations from config"""
        try:
            # Get worker configurations from environment or config
            worker_mode = os.getenv('WORKER_MODE', 'integrated')  # integrated, external, hybrid
            
            if worker_mode in ['integrated', 'hybrid']:
                self._load_integrated_worker_configs()
            
            if worker_mode in ['external', 'hybrid']:
                self._load_external_worker_configs()
                
            logger.info(f"Loaded worker configurations for mode: {worker_mode}")
            
        except Exception as e:
            logger.error(f"Failed to load worker configurations: {sanitize_for_log(str(e))}")
            raise
    
    def _load_integrated_worker_configs(self) -> None:
        """Load integrated worker configurations"""
        # Default integrated worker configuration
        integrated_configs = [
            {
                'worker_id': f'integrated-urgent-high-{self.worker_id}',
                'queues': ['urgent', 'high'],
                'count': int(os.getenv('RQ_URGENT_HIGH_WORKERS', '1'))
            },
            {
                'worker_id': f'integrated-normal-{self.worker_id}',
                'queues': ['normal'],
                'count': int(os.getenv('RQ_NORMAL_WORKERS', '2'))
            },
            {
                'worker_id': f'integrated-low-{self.worker_id}',
                'queues': ['low'],
                'count': int(os.getenv('RQ_LOW_WORKERS', '1'))
            }
        ]
        
        for config in integrated_configs:
            for i in range(config['count']):
                worker_id = f"{config['worker_id']}-{i}"
                self.worker_configs[worker_id] = WorkerConfig(
                    worker_id=worker_id,
                    queues=config['queues'],
                    worker_type='integrated',
                    concurrency=1,
                    memory_limit=int(os.getenv('RQ_WORKER_MEMORY_LIMIT', '512')),  # MB
                    timeout=int(os.getenv('RQ_WORKER_TIMEOUT', '3600')),  # seconds
                    health_check_interval=30
                )
    
    def _load_external_worker_configs(self) -> None:
        """Load external worker configurations"""
        # External workers for heavy processing
        external_configs = [
            {
                'worker_id': f'external-low-{self.worker_id}',
                'queues': ['low'],
                'count': int(os.getenv('RQ_EXTERNAL_LOW_WORKERS', '2'))
            }
        ]
        
        for config in external_configs:
            for i in range(config['count']):
                worker_id = f"{config['worker_id']}-{i}"
                self.worker_configs[worker_id] = WorkerConfig(
                    worker_id=worker_id,
                    queues=config['queues'],
                    worker_type='external',
                    concurrency=1,
                    memory_limit=int(os.getenv('RQ_EXTERNAL_WORKER_MEMORY_LIMIT', '1024')),  # MB
                    timeout=int(os.getenv('RQ_EXTERNAL_WORKER_TIMEOUT', '7200')),  # seconds
                    health_check_interval=60
                )
    
    def start_integrated_workers(self) -> bool:
        """Start integrated workers as daemon threads"""
        if not self._initialized:
            logger.error("Worker manager not initialized")
            return False
        
        success_count = 0
        total_count = 0
        
        try:
            with self._lock:
                for worker_id, config in self.worker_configs.items():
                    if config.worker_type != 'integrated':
                        continue
                    
                    total_count += 1
                    
                    try:
                        # Create integrated worker
                        worker = IntegratedRQWorker(
                            queues=config.queues,
                            redis_connection=self.redis_connection,
                            app_context=self.app_context,
                            db_manager=self.db_manager,
                            worker_id=worker_id
                        )
                        
                        # Set up callbacks for monitoring
                        worker.set_job_callbacks(
                            started=self._on_job_started,
                            finished=self._on_job_finished,
                            failed=self._on_job_failed
                        )
                        
                        # Start the worker
                        if worker.start():
                            self.integrated_workers[worker_id] = worker
                            success_count += 1
                            logger.info(f"Started integrated worker {worker_id} for queues {config.queues}")
                        else:
                            logger.error(f"Failed to start integrated worker {worker_id}")
                            
                    except Exception as e:
                        logger.error(f"Error starting integrated worker {worker_id}: {sanitize_for_log(str(e))}")
                
                logger.info(f"Started {success_count}/{total_count} integrated workers")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Failed to start integrated workers: {sanitize_for_log(str(e))}")
            return False
    
    def start_external_workers(self) -> bool:
        """Start external worker processes"""
        if not self._initialized:
            logger.error("Worker manager not initialized")
            return False
        
        success_count = 0
        total_count = 0
        
        try:
            with self._lock:
                for worker_id, config in self.worker_configs.items():
                    if config.worker_type != 'external':
                        continue
                    
                    total_count += 1
                    
                    try:
                        # Build RQ worker command
                        cmd = self._build_external_worker_command(config)
                        
                        # Start external process
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            env=os.environ.copy()
                        )
                        
                        self.external_workers[worker_id] = process
                        success_count += 1
                        logger.info(f"Started external worker {worker_id} (PID: {process.pid}) for queues {config.queues}")
                        
                    except Exception as e:
                        logger.error(f"Error starting external worker {worker_id}: {sanitize_for_log(str(e))}")
                
                logger.info(f"Started {success_count}/{total_count} external workers")
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Failed to start external workers: {sanitize_for_log(str(e))}")
            return False
    
    def _build_external_worker_command(self, config: WorkerConfig) -> List[str]:
        """Build command for external RQ worker"""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        cmd = [
            'rq', 'worker',
            '--url', redis_url,
            '--name', config.worker_id,
            '--job-timeout', str(config.timeout)
        ]
        
        # Add queues
        cmd.extend(config.queues)
        
        return cmd
    
    def stop_workers(self, graceful: bool = True, timeout: Optional[int] = None) -> bool:
        """
        Stop all workers
        
        Args:
            graceful: Whether to stop gracefully
            timeout: Timeout for graceful shutdown
            
        Returns:
            bool: True if all workers stopped successfully
        """
        if timeout is None:
            timeout = self.shutdown_timeout
        
        logger.info(f"Stopping all workers (graceful={graceful}, timeout={timeout}s)")
        
        success = True
        
        # Stop integrated workers
        success &= self._stop_integrated_workers(graceful, timeout)
        
        # Stop external workers
        success &= self._stop_external_workers(graceful, timeout)
        
        return success
    
    def _stop_integrated_workers(self, graceful: bool, timeout: int) -> bool:
        """Stop integrated workers"""
        success = True
        
        with self._lock:
            for worker_id, worker in list(self.integrated_workers.items()):
                try:
                    if worker.stop(timeout if graceful else 0):
                        logger.info(f"Stopped integrated worker {worker_id}")
                    else:
                        logger.warning(f"Failed to stop integrated worker {worker_id} gracefully")
                        success = False
                        
                except Exception as e:
                    logger.error(f"Error stopping integrated worker {worker_id}: {sanitize_for_log(str(e))}")
                    success = False
                finally:
                    # Remove from tracking
                    self.integrated_workers.pop(worker_id, None)
        
        return success
    
    def _stop_external_workers(self, graceful: bool, timeout: int) -> bool:
        """Stop external workers"""
        success = True
        
        with self._lock:
            for worker_id, process in list(self.external_workers.items()):
                try:
                    if graceful:
                        # Send SIGTERM for graceful shutdown
                        process.terminate()
                        try:
                            process.wait(timeout=timeout)
                            logger.info(f"Stopped external worker {worker_id} gracefully")
                        except subprocess.TimeoutExpired:
                            # Force kill if timeout exceeded
                            process.kill()
                            process.wait()
                            logger.warning(f"Force killed external worker {worker_id} after timeout")
                            success = False
                    else:
                        # Force kill immediately
                        process.kill()
                        process.wait()
                        logger.info(f"Force killed external worker {worker_id}")
                        
                except Exception as e:
                    logger.error(f"Error stopping external worker {worker_id}: {sanitize_for_log(str(e))}")
                    success = False
                finally:
                    # Remove from tracking
                    self.external_workers.pop(worker_id, None)
        
        return success
    
    def restart_worker(self, worker_id: str) -> bool:
        """Restart a specific worker"""
        logger.info(f"Restarting worker {worker_id}")
        
        # Check if it's an integrated worker
        if worker_id in self.integrated_workers:
            worker = self.integrated_workers[worker_id]
            return worker.restart(self.shutdown_timeout)
        
        # Check if it's an external worker
        elif worker_id in self.external_workers:
            config = self.worker_configs.get(worker_id)
            if not config:
                logger.error(f"No configuration found for worker {worker_id}")
                return False
            
            # Stop the external worker
            process = self.external_workers[worker_id]
            try:
                process.terminate()
                process.wait(timeout=self.shutdown_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            # Remove from tracking
            self.external_workers.pop(worker_id, None)
            
            # Start new external worker
            try:
                cmd = self._build_external_worker_command(config)
                new_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=os.environ.copy()
                )
                self.external_workers[worker_id] = new_process
                logger.info(f"Restarted external worker {worker_id} (PID: {new_process.pid})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to restart external worker {worker_id}: {sanitize_for_log(str(e))}")
                return False
        
        else:
            logger.error(f"Worker {worker_id} not found")
            return False
    
    def scale_workers(self, queue_name: str, count: int) -> bool:
        """
        Scale workers for a specific queue
        
        Args:
            queue_name: Name of the queue to scale
            count: Target number of workers
            
        Returns:
            bool: True if scaling was successful
        """
        logger.info(f"Scaling workers for queue {queue_name} to {count}")
        
        # This is a simplified implementation
        # In a full implementation, this would dynamically create/destroy workers
        
        current_workers = [
            worker_id for worker_id, config in self.worker_configs.items()
            if queue_name in config.queues
        ]
        
        current_count = len(current_workers)
        
        if count > current_count:
            # Need to add workers
            logger.info(f"Adding {count - current_count} workers for queue {queue_name}")
            # Implementation would create new workers here
            
        elif count < current_count:
            # Need to remove workers
            logger.info(f"Removing {current_count - count} workers for queue {queue_name}")
            # Implementation would stop excess workers here
        
        logger.info(f"Queue {queue_name} scaling completed")
        return True
    
    def register_worker_coordination(self) -> None:
        """Register this worker manager in Redis"""
        try:
            manager_info = {
                'manager_id': self.worker_id,
                'started_at': int(time.time()),
                'pid': os.getpid(),
                'integrated_workers': len([c for c in self.worker_configs.values() if c.worker_type == 'integrated']),
                'external_workers': len([c for c in self.worker_configs.values() if c.worker_type == 'external'])
            }
            
            self.redis_connection.hset(
                self.coordination_key,
                mapping=manager_info
            )
            self.redis_connection.expire(self.coordination_key, 300)  # 5 minutes
            
            logger.debug(f"Registered worker manager coordination for {self.worker_id}")
            
        except Exception as e:
            logger.error(f"Failed to register worker manager coordination: {sanitize_for_log(str(e))}")
    
    def cleanup_worker_coordination(self) -> None:
        """Clean up worker manager coordination"""
        try:
            self.redis_connection.delete(self.coordination_key)
            logger.debug(f"Cleaned up worker manager coordination for {self.worker_id}")
        except Exception as e:
            logger.debug(f"Failed to cleanup worker manager coordination: {sanitize_for_log(str(e))}")
    
    def _start_health_monitoring(self) -> None:
        """Start health monitoring thread"""
        if self._health_monitoring:
            return
        
        self._health_monitoring = True
        self._health_check_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True,
            name=f"HealthMonitor-{self.worker_id}"
        )
        self._health_check_thread.start()
        logger.info("Started worker health monitoring")
    
    def _health_monitor_loop(self) -> None:
        """Health monitoring loop"""
        while self._health_monitoring and not self._shutdown_requested:
            try:
                self._perform_health_checks()
                self.register_worker_coordination()  # Update TTL
                time.sleep(self._health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {sanitize_for_log(str(e))}")
                time.sleep(5)  # Short sleep on error
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all workers"""
        # Check integrated workers
        for worker_id, worker in list(self.integrated_workers.items()):
            if not worker.is_running():
                logger.warning(f"Integrated worker {worker_id} is not running - attempting restart")
                if not worker.restart():
                    logger.error(f"Failed to restart integrated worker {worker_id}")
        
        # Check external workers
        for worker_id, process in list(self.external_workers.items()):
            if process.poll() is not None:  # Process has terminated
                logger.warning(f"External worker {worker_id} has terminated - attempting restart")
                if not self.restart_worker(worker_id):
                    logger.error(f"Failed to restart external worker {worker_id}")
    
    def _on_job_started(self, job_id: str, worker_id: str) -> None:
        """Callback for job started"""
        logger.debug(f"Job {sanitize_for_log(job_id)} started on worker {worker_id}")
    
    def _on_job_finished(self, job_id: str, worker_id: str, success: bool) -> None:
        """Callback for job finished"""
        status = "completed" if success else "failed"
        logger.debug(f"Job {sanitize_for_log(job_id)} {status} on worker {worker_id}")
    
    def _on_job_failed(self, job_id: str, worker_id: str, error: str) -> None:
        """Callback for job failed"""
        logger.warning(f"Job {sanitize_for_log(job_id)} failed on worker {worker_id}: {sanitize_for_log(error)}")
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get status of all workers"""
        status = {
            'manager_id': self.worker_id,
            'initialized': self._initialized,
            'shutdown_requested': self._shutdown_requested,
            'health_monitoring': self._health_monitoring,
            'integrated_workers': {},
            'external_workers': {},
            'total_workers': len(self.integrated_workers) + len(self.external_workers)
        }
        
        # Get integrated worker status
        for worker_id, worker in self.integrated_workers.items():
            status['integrated_workers'][worker_id] = worker.get_worker_info()
        
        # Get external worker status
        for worker_id, process in self.external_workers.items():
            status['external_workers'][worker_id] = {
                'worker_id': worker_id,
                'pid': process.pid,
                'running': process.poll() is None,
                'returncode': process.returncode
            }
        
        return status
    
    def cleanup_and_stop(self) -> None:
        """Cleanup and stop all workers (called on exit)"""
        if self._shutdown_requested:
            return
        
        logger.info("Cleaning up and stopping RQ Worker Manager")
        self._shutdown_requested = True
        
        # Stop health monitoring
        self._health_monitoring = False
        
        # Stop resource management
        if self.resource_manager:
            self.resource_manager.stop()
            logger.info("RQ resource management stopped")
        
        # Stop all workers
        self.stop_workers(graceful=True, timeout=self.shutdown_timeout)
        
        # Cleanup coordination
        self.cleanup_worker_coordination()
        
        logger.info("RQ Worker Manager cleanup completed")