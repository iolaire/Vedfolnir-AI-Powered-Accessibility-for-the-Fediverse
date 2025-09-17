# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Gunicorn Integration for RQ Workers

Integrates RQ worker startup with Flask app initialization and provides
graceful shutdown handling for Gunicorn processes.
"""

import logging
import atexit
import os
import signal
import threading
import time
from typing import Optional, Dict, Any
import redis
from flask import Flask

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from .rq_worker_manager import RQWorkerManager
from .rq_config import RQConfig
from .config_loader import load_rq_config
from .monitoring_integration import RQMonitoringIntegration

logger = logging.getLogger(__name__)


class GunicornRQIntegration:
    """Manages RQ worker integration with Gunicorn lifecycle"""
    
    def __init__(self, app: Flask, db_manager: DatabaseManager):
        """
        Initialize Gunicorn RQ Integration
        
        Args:
            app: Flask application instance
            db_manager: Database manager instance
        """
        self.app = app
        self.db_manager = db_manager
        self.worker_manager: Optional[RQWorkerManager] = None
        self.redis_connection: Optional[redis.Redis] = None
        self.config: Optional[RQConfig] = None
        self.monitoring: Optional[RQMonitoringIntegration] = None
        
        # Integration state
        self._initialized = False
        self._shutdown_requested = False
        self._lock = threading.Lock()
        
        # Configuration
        self.enable_integrated_workers = os.getenv('RQ_ENABLE_INTEGRATED_WORKERS', 'true').lower() == 'true'
        self.enable_external_workers = os.getenv('RQ_ENABLE_EXTERNAL_WORKERS', 'false').lower() == 'true'
        self.startup_delay = int(os.getenv('RQ_STARTUP_DELAY', '5'))  # seconds
        
        logger.info(f"GunicornRQIntegration initialized - integrated: {self.enable_integrated_workers}, external: {self.enable_external_workers}")
    
    def initialize_with_app(self) -> bool:
        """
        Initialize RQ workers with Flask app context
        
        Returns:
            bool: True if initialization was successful
        """
        if self._initialized:
            logger.warning("RQ integration already initialized")
            return True
        
        try:
            with self._lock:
                # Initialize production configuration
                try:
                    self.config = load_rq_config()
                    logger.info(f"Loaded RQ configuration for {self.config.environment.value} environment")
                except Exception as e:
                    logger.error(f"Failed to load RQ configuration: {sanitize_for_log(str(e))}")
                    return False
                
                # Initialize Redis connection
                self.redis_connection = self._create_redis_connection()
                if not self.redis_connection:
                    logger.error("Failed to create Redis connection")
                    return False
                
                # Initialize worker manager
                self.worker_manager = RQWorkerManager(
                    redis_connection=self.redis_connection,
                    config=self.config,
                    db_manager=self.db_manager,
                    app_context=self.app
                )
                
                if not self.worker_manager.initialize():
                    logger.error("Failed to initialize RQ worker manager")
                    return False
                
                # Initialize monitoring integration
                if self.config.monitoring_config.enable_metrics or self.config.monitoring_config.enable_alerting:
                    self.monitoring = RQMonitoringIntegration(self.config)
                    self.monitoring.start()
                    logger.info("RQ monitoring integration started")
                
                # Register shutdown handlers
                self._register_shutdown_handlers()
                
                # Start workers with delay to allow app to fully initialize
                if self.startup_delay > 0:
                    logger.info(f"Delaying RQ worker startup by {self.startup_delay} seconds")
                    startup_thread = threading.Thread(
                        target=self._delayed_worker_startup,
                        daemon=True,
                        name="RQWorkerStartup"
                    )
                    startup_thread.start()
                else:
                    self._start_workers()
                
                self._initialized = True
                logger.info("RQ Gunicorn integration initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize RQ Gunicorn integration: {sanitize_for_log(str(e))}")
            return False
    
    def _create_redis_connection(self) -> Optional[redis.Redis]:
        """Create Redis connection with proper configuration"""
        try:
            connection_params = self.config.get_redis_connection_params()
            
            # Create Redis connection
            redis_conn = redis.Redis(**connection_params)
            
            # Test connection
            redis_conn.ping()
            
            logger.info("Redis connection established successfully")
            return redis_conn
            
        except Exception as e:
            logger.error(f"Failed to create Redis connection: {sanitize_for_log(str(e))}")
            return None
    
    def _delayed_worker_startup(self) -> None:
        """Start workers after delay"""
        try:
            time.sleep(self.startup_delay)
            
            if not self._shutdown_requested:
                self._start_workers()
                
        except Exception as e:
            logger.error(f"Error in delayed worker startup: {sanitize_for_log(str(e))}")
    
    def _start_workers(self) -> None:
        """Start RQ workers based on configuration"""
        try:
            success = True
            
            # Start integrated workers
            if self.enable_integrated_workers:
                logger.info("Starting integrated RQ workers")
                if not self.worker_manager.start_integrated_workers():
                    logger.error("Failed to start integrated workers")
                    success = False
                else:
                    logger.info("Integrated RQ workers started successfully")
            
            # Start external workers
            if self.enable_external_workers:
                logger.info("Starting external RQ workers")
                if not self.worker_manager.start_external_workers():
                    logger.error("Failed to start external workers")
                    success = False
                else:
                    logger.info("External RQ workers started successfully")
            
            if success:
                logger.info("All configured RQ workers started successfully")
            else:
                logger.warning("Some RQ workers failed to start")
                
        except Exception as e:
            logger.error(f"Error starting RQ workers: {sanitize_for_log(str(e))}")
    
    def _register_shutdown_handlers(self) -> None:
        """Register shutdown handlers for graceful cleanup"""
        try:
            # Register atexit handler for graceful shutdown
            atexit.register(self.shutdown_workers)
            
            # Register signal handlers for Gunicorn worker termination
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            logger.info("Shutdown handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register shutdown handlers: {sanitize_for_log(str(e))}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown_workers()
    
    def shutdown_workers(self) -> None:
        """Shutdown all RQ workers gracefully"""
        if self._shutdown_requested:
            return
        
        logger.info("Shutting down RQ workers")
        self._shutdown_requested = True
        
        try:
            with self._lock:
                if self.worker_manager:
                    # Stop all workers gracefully
                    timeout = int(os.getenv('RQ_SHUTDOWN_TIMEOUT', '30'))
                    success = self.worker_manager.stop_workers(graceful=True, timeout=timeout)
                    
                    if success:
                        logger.info("All RQ workers stopped gracefully")
                    else:
                        logger.warning("Some RQ workers did not stop gracefully")
                
                # Close Redis connection
                if self.redis_connection:
                # Stop monitoring
                if self.monitoring:
                    try:
                        self.monitoring.stop()
                        logger.info("RQ monitoring stopped")
                    except Exception as e:
                        logger.error(f"Error stopping RQ monitoring: {sanitize_for_log(str(e))}")
                
                # Close Redis connection
                if self.redis_connection:
                    try:
                        self.redis_connection.close()
                        logger.info("Redis connection closed")
                    except Exception as e:
                        logger.error(f"Error closing Redis connection: {sanitize_for_log(str(e))}")
                
                logger.info("RQ worker shutdown completed")
                
        except Exception as e:
            logger.error(f"Error during RQ worker shutdown: {sanitize_for_log(str(e))}")
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get status of all workers"""
        if not self.worker_manager:
            return {
                'initialized': False,
                'error': 'Worker manager not initialized'
            }
        
        status = self.worker_manager.get_worker_status()
        status.update({
            'gunicorn_integration': {
                'initialized': self._initialized,
                'shutdown_requested': self._shutdown_requested,
                'integrated_workers_enabled': self.enable_integrated_workers,
                'external_workers_enabled': self.enable_external_workers,
                'startup_delay': self.startup_delay
            }
        })
        
        # Add resource management status
        if self.worker_manager and self.worker_manager.resource_manager:
            status['resource_management'] = self.worker_manager.resource_manager.get_resource_status()
        
        # Add monitoring status
        if self.monitoring:
            status['monitoring'] = self.monitoring.get_monitoring_status()
        
        return status
    
    def restart_workers(self) -> bool:
        """Restart all workers"""
        if not self.worker_manager:
            logger.error("Worker manager not initialized")
            return False
        
        logger.info("Restarting all RQ workers")
        
        try:
            # Stop workers
            self.worker_manager.stop_workers(graceful=True, timeout=30)
            
            # Wait a moment
            time.sleep(2)
            
            # Start workers again
            self._start_workers()
            
            logger.info("RQ workers restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting RQ workers: {sanitize_for_log(str(e))}")
            return False
    
    def scale_workers(self, queue_name: str, count: int) -> bool:
        """Scale workers for a specific queue"""
        if not self.worker_manager:
            logger.error("Worker manager not initialized")
            return False
        
        return self.worker_manager.scale_workers(queue_name, count)


# Global integration instance
_gunicorn_rq_integration: Optional[GunicornRQIntegration] = None


def initialize_rq_workers(app: Flask, db_manager: DatabaseManager) -> Optional[GunicornRQIntegration]:
    """
    Initialize RQ workers when Gunicorn starts
    
    Args:
        app: Flask application instance
        db_manager: Database manager instance
        
    Returns:
        GunicornRQIntegration instance or None if initialization failed
    """
    global _gunicorn_rq_integration
    
    if _gunicorn_rq_integration is not None:
        logger.warning("RQ workers already initialized")
        return _gunicorn_rq_integration
    
    try:
        # Create integration instance
        integration = GunicornRQIntegration(app, db_manager)
        
        # Initialize with app context
        if integration.initialize_with_app():
            _gunicorn_rq_integration = integration
            logger.info("RQ workers initialized successfully with Gunicorn")
            return integration
        else:
            logger.error("Failed to initialize RQ workers with Gunicorn")
            return None
            
    except Exception as e:
        logger.error(f"Error initializing RQ workers: {sanitize_for_log(str(e))}")
        return None


def get_rq_integration() -> Optional[GunicornRQIntegration]:
    """Get the global RQ integration instance"""
    return _gunicorn_rq_integration


def cleanup_rq_workers() -> None:
    """Cleanup RQ workers (called on exit)"""
    global _gunicorn_rq_integration
    
    if _gunicorn_rq_integration:
        _gunicorn_rq_integration.shutdown_workers()
        _gunicorn_rq_integration = None