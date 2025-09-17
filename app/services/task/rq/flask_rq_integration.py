# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Flask RQ Integration

Integrates RQ workers with Flask application lifecycle using Flask 2.2+ compatible
startup methods. Supports both integrated and external worker deployment strategies.
"""

import logging
import os
import atexit
from typing import Optional
from flask import Flask
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.core.security.core.security_utils import sanitize_for_log
from .rq_config import RQConfig
from .redis_connection_manager import RedisConnectionManager
from .rq_queue_manager import RQQueueManager
from .rq_worker_manager import RQWorkerManager

logger = logging.getLogger(__name__)


class FlaskRQIntegration:
    """Integrates RQ with Flask application lifecycle"""
    
    def __init__(self):
        self.rq_config: Optional[RQConfig] = None
        self.redis_manager: Optional[RedisConnectionManager] = None
        self.queue_manager: Optional[RQQueueManager] = None
        self.worker_manager: Optional[RQWorkerManager] = None
        self._initialized = False
    
    def init_app(self, app: Flask) -> bool:
        """
        Initialize RQ integration with Flask app
        
        Args:
            app: Flask application instance
            
        Returns:
            bool: True if initialization was successful
        """
        if self._initialized:
            logger.warning("RQ integration already initialized")
            return True
        
        try:
            # Store app reference
            self.app = app
            
            # Initialize configuration
            self.rq_config = RQConfig()
            if not self.rq_config.validate_config():
                logger.error("RQ configuration validation failed")
                return False
            
            # Get required services from app
            db_manager = app.config.get('db_manager')
            if not db_manager:
                logger.error("Database manager not found in Flask app config")
                return False
            
            # Initialize Redis connection manager
            self.redis_manager = RedisConnectionManager(self.rq_config)
            if not self.redis_manager.initialize():
                logger.warning("Redis connection failed - RQ will use fallback mode")
                # Continue initialization for fallback mode
            
            # Initialize security manager
            security_manager = CaptionSecurityManager(db_manager)
            
            # Initialize queue manager
            self.queue_manager = RQQueueManager(
                db_manager=db_manager,
                config=self.rq_config,
                security_manager=security_manager
            )
            
            # Initialize worker manager if Redis is available
            redis_connection = self.redis_manager.get_connection()
            if redis_connection:
                self.worker_manager = RQWorkerManager(
                    redis_connection=redis_connection,
                    config=self.rq_config,
                    db_manager=db_manager,
                    app_context=app
                )
                
                if not self.worker_manager.initialize():
                    logger.error("Failed to initialize RQ worker manager")
                    return False
            
            # Store references in app config
            app.config['rq_integration'] = self
            app.config['rq_queue_manager'] = self.queue_manager
            app.config['rq_worker_manager'] = self.worker_manager
            
            # Register cleanup on app teardown
            atexit.register(self.cleanup)
            
            self._initialized = True
            logger.info("RQ integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RQ integration: {sanitize_for_log(str(e))}")
            return False
    
    def start_workers(self) -> bool:
        """
        Start RQ workers based on configuration
        
        Returns:
            bool: True if workers started successfully
        """
        if not self._initialized:
            logger.error("RQ integration not initialized")
            return False
        
        if not self.worker_manager:
            logger.info("No worker manager available - running in fallback mode")
            return True
        
        try:
            worker_mode = os.getenv('WORKER_MODE', 'integrated')
            success = True
            
            if worker_mode in ['integrated', 'hybrid']:
                logger.info("Starting integrated RQ workers")
                success &= self.worker_manager.start_integrated_workers()
            
            if worker_mode in ['external', 'hybrid']:
                logger.info("Starting external RQ workers")
                success &= self.worker_manager.start_external_workers()
            
            if success:
                logger.info(f"RQ workers started successfully in {worker_mode} mode")
            else:
                logger.warning(f"Some RQ workers failed to start in {worker_mode} mode")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to start RQ workers: {sanitize_for_log(str(e))}")
            return False
    
    def stop_workers(self, graceful: bool = True, timeout: int = 30) -> bool:
        """
        Stop RQ workers
        
        Args:
            graceful: Whether to stop gracefully
            timeout: Timeout for graceful shutdown
            
        Returns:
            bool: True if workers stopped successfully
        """
        if not self.worker_manager:
            return True
        
        try:
            return self.worker_manager.stop_workers(graceful, timeout)
        except Exception as e:
            logger.error(f"Failed to stop RQ workers: {sanitize_for_log(str(e))}")
            return False
    
    def get_status(self) -> dict:
        """Get RQ integration status"""
        status = {
            'initialized': self._initialized,
            'redis_available': False,
            'queue_manager_available': self.queue_manager is not None,
            'worker_manager_available': self.worker_manager is not None,
            'workers_running': False
        }
        
        if self.redis_manager:
            health_status = self.redis_manager.get_health_status()
            status['redis_available'] = health_status.get('connected', False)
        
        if self.queue_manager:
            status.update(self.queue_manager.get_health_status())
        
        if self.worker_manager:
            worker_status = self.worker_manager.get_worker_status()
            status['workers_running'] = worker_status['total_workers'] > 0
            status['worker_details'] = worker_status
        
        return status
    
    def cleanup(self) -> None:
        """Cleanup RQ integration resources"""
        try:
            logger.info("Cleaning up RQ integration")
            
            # Stop workers
            if self.worker_manager:
                self.worker_manager.cleanup_and_stop()
            
            # Cleanup queue manager
            if self.queue_manager:
                self.queue_manager.cleanup()
            
            # Cleanup Redis connection
            if self.redis_manager:
                self.redis_manager.cleanup()
            
            logger.info("RQ integration cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during RQ integration cleanup: {sanitize_for_log(str(e))}")


# Global RQ integration instance
rq_integration = FlaskRQIntegration()


def initialize_rq_workers(app: Flask) -> Optional[RQWorkerManager]:
    """
    Initialize RQ workers when Flask app starts (Flask 2.2+ compatible)
    
    Args:
        app: Flask application instance
        
    Returns:
        RQWorkerManager instance or None if initialization failed
    """
    try:
        logger.info("Initializing RQ workers for Flask application")
        
        # Initialize RQ integration
        if not rq_integration.init_app(app):
            logger.error("Failed to initialize RQ integration")
            return None
        
        # Start workers
        if not rq_integration.start_workers():
            logger.warning("Some RQ workers failed to start")
        
        return rq_integration.worker_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize RQ workers: {sanitize_for_log(str(e))}")
        return None


def setup_rq_with_flask_app(app: Flask) -> bool:
    """
    Set up RQ integration with Flask app using modern Flask patterns
    
    Args:
        app: Flask application instance
        
    Returns:
        bool: True if setup was successful
    """
    try:
        # Use Flask's record_once for one-time initialization per app instance
        @app.record_once
        def init_rq_workers(state):
            """Initialize RQ workers once per application instance"""
            app = state.app
            
            # Initialize within app context
            with app.app_context():
                worker_manager = initialize_rq_workers(app)
                if worker_manager:
                    app.rq_worker_manager = worker_manager
                    logger.info("RQ workers initialized with Flask app")
                else:
                    logger.warning("RQ workers initialization failed or running in fallback mode")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up RQ with Flask app: {sanitize_for_log(str(e))}")
        return False


def create_rq_enabled_app(app: Flask) -> Flask:
    """
    Create Flask app with RQ integration enabled
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask app with RQ integration
    """
    try:
        # Set up RQ integration
        if setup_rq_with_flask_app(app):
            logger.info("Flask app created with RQ integration")
        else:
            logger.warning("Flask app created without RQ integration")
        
        return app
        
    except Exception as e:
        logger.error(f"Failed to create RQ-enabled Flask app: {sanitize_for_log(str(e))}")
        return app