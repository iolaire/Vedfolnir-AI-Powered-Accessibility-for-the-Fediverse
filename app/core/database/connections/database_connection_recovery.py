# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Database Connection Recovery

Provides robust database connection recovery mechanisms to ensure
job processing continuity even when database connections are lost
or become unstable.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError, TimeoutError
from sqlalchemy.pool import QueuePool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from database import DatabaseManager
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class DatabaseConnectionRecovery:
    """Handles database connection recovery and monitoring"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._recovery_lock = threading.Lock()
        self._connection_healthy = True
        self._last_health_check = None
        self._health_check_interval = 30  # seconds
        self._recovery_attempts = 0
        self._max_recovery_attempts = 3
        self._recovery_callbacks = []
        
        # Connection monitoring
        self._failed_connections = 0
        self._connection_failures_threshold = 5
        self._monitoring_enabled = True
        
        # Register SQLAlchemy event listeners
        self._register_connection_events()
        
        logger.info("Database connection recovery initialized")
    
    def register_recovery_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register a callback to be called during recovery events"""
        self._recovery_callbacks.append(callback)
    
    def _register_connection_events(self):
        """Register SQLAlchemy event listeners for connection monitoring"""
        if not hasattr(self.db_manager, 'engine') or not self.db_manager.engine:
            logger.warning("Database engine not available for event registration")
            return
        
        try:
            @event.listens_for(self.db_manager.engine, "connect")
            def receive_connect(dbapi_connection, connection_record):
                logger.debug("Database connection established")
                self._connection_healthy = True
                self._failed_connections = 0
            
            @event.listens_for(self.db_manager.engine, "checkout")
            def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                logger.debug("Database connection checked out from pool")
            
            @event.listens_for(self.db_manager.engine, "checkin")
            def receive_checkin(dbapi_connection, connection_record):
                logger.debug("Database connection returned to pool")
            
            @event.listens_for(self.db_manager.engine, "invalidate")
            def receive_invalidate(dbapi_connection, connection_record, exception):
                logger.warning(f"Database connection invalidated: {sanitize_for_log(str(exception))}")
                self._handle_connection_failure(exception)
                
        except Exception as e:
            logger.warning(f"Failed to register database connection events: {sanitize_for_log(str(e))}")
            # Continue without event listeners - recovery will still work via health checks
    
    def _handle_connection_failure(self, exception: Exception):
        """Handle connection failure events"""
        self._failed_connections += 1
        self._connection_healthy = False
        
        logger.warning(f"Database connection failure #{self._failed_connections}: {sanitize_for_log(str(exception))}")
        
        # Trigger recovery if threshold exceeded
        if self._failed_connections >= self._connection_failures_threshold:
            logger.error(f"Connection failure threshold exceeded ({self._connection_failures_threshold})")
            self._trigger_automatic_recovery()
    
    def _trigger_automatic_recovery(self):
        """Trigger automatic connection recovery"""
        try:
            logger.info("Triggering automatic database connection recovery")
            success = self.recover_connection()
            
            if success:
                logger.info("Automatic database connection recovery successful")
                self._notify_recovery_callbacks("automatic_recovery_success", {
                    "failed_connections": self._failed_connections,
                    "recovery_attempts": self._recovery_attempts
                })
            else:
                logger.error("Automatic database connection recovery failed")
                self._notify_recovery_callbacks("automatic_recovery_failed", {
                    "failed_connections": self._failed_connections,
                    "recovery_attempts": self._recovery_attempts
                })
                
        except Exception as e:
            logger.error(f"Error in automatic recovery: {sanitize_for_log(str(e))}")
    
    def _notify_recovery_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify registered recovery callbacks"""
        for callback in self._recovery_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Recovery callback failed: {sanitize_for_log(str(e))}")
    
    def test_connection(self) -> bool:
        """
        Test database connection health
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            with self.db_manager.get_session() as session:
                # Simple query to test connection
                result = session.execute(text("SELECT 1 as test")).fetchone()
                if result and result.test == 1:
                    self._connection_healthy = True
                    self._last_health_check = time.time()
                    return True
                else:
                    logger.warning("Database connection test returned unexpected result")
                    self._connection_healthy = False
                    return False
                    
        except (SQLAlchemyError, DisconnectionError, OperationalError, TimeoutError) as e:
            logger.error(f"Database connection test failed: {sanitize_for_log(str(e))}")
            self._connection_healthy = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing database connection: {sanitize_for_log(str(e))}")
            self._connection_healthy = False
            return False
    
    def recover_connection(self) -> bool:
        """
        Recover database connection with retry logic
        
        Returns:
            bool: True if recovery was successful
        """
        with self._recovery_lock:
            logger.info("Starting database connection recovery")
            
            # Check if recovery is needed
            if self.test_connection():
                logger.info("Database connection is healthy, no recovery needed")
                return True
            
            # Attempt recovery
            for attempt in range(1, self._max_recovery_attempts + 1):
                logger.info(f"Database recovery attempt {attempt}/{self._max_recovery_attempts}")
                
                try:
                    # Dispose current engine and connections
                    self._dispose_connections()
                    
                    # Wait before retry
                    if attempt > 1:
                        wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                        logger.info(f"Waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                    
                    # Recreate engine
                    self._recreate_engine()
                    
                    # Test new connection
                    if self.test_connection():
                        logger.info(f"Database connection recovery successful on attempt {attempt}")
                        self._recovery_attempts = attempt
                        self._failed_connections = 0
                        
                        self._notify_recovery_callbacks("recovery_success", {
                            "attempt": attempt,
                            "total_attempts": self._max_recovery_attempts
                        })
                        
                        return True
                    
                except Exception as e:
                    logger.error(f"Recovery attempt {attempt} failed: {sanitize_for_log(str(e))}")
                    
                    self._notify_recovery_callbacks("recovery_attempt_failed", {
                        "attempt": attempt,
                        "error": str(e)
                    })
            
            # All recovery attempts failed
            logger.error(f"Database connection recovery failed after {self._max_recovery_attempts} attempts")
            self._recovery_attempts = self._max_recovery_attempts
            
            self._notify_recovery_callbacks("recovery_failed", {
                "total_attempts": self._max_recovery_attempts
            })
            
            return False
    
    def _dispose_connections(self):
        """Dispose current database connections"""
        try:
            if hasattr(self.db_manager, 'engine') and self.db_manager.engine:
                logger.info("Disposing database engine and connections")
                self.db_manager.engine.dispose()
            
            if hasattr(self.db_manager, 'dispose_engine'):
                self.db_manager.dispose_engine()
                
        except Exception as e:
            logger.error(f"Error disposing connections: {sanitize_for_log(str(e))}")
    
    def _recreate_engine(self):
        """Recreate database engine"""
        try:
            logger.info("Recreating database engine")
            
            # Reinitialize database manager
            if hasattr(self.db_manager, 'initialize_engine'):
                self.db_manager.initialize_engine()
            else:
                # Fallback: create new engine
                from config import Config
                config = Config()
                self.db_manager._create_engine(config.storage.database_url)
            
            # Re-register event listeners
            self._register_connection_events()
            
        except Exception as e:
            logger.error(f"Error recreating engine: {sanitize_for_log(str(e))}")
            raise
    
    @contextmanager
    def resilient_session(self, max_retries: int = 3):
        """
        Context manager for resilient database sessions with automatic recovery
        
        Args:
            max_retries: Maximum number of retry attempts
        """
        for attempt in range(1, max_retries + 1):
            try:
                with self.db_manager.get_session() as session:
                    yield session
                    return  # Success, exit retry loop
                    
            except (DisconnectionError, OperationalError, TimeoutError) as e:
                logger.warning(f"Database session failed (attempt {attempt}/{max_retries}): {sanitize_for_log(str(e))}")
                
                if attempt == max_retries:
                    logger.error("All database session attempts failed")
                    raise
                
                # Attempt recovery before retry
                logger.info("Attempting connection recovery before retry")
                recovery_success = self.recover_connection()
                
                if not recovery_success:
                    logger.error("Connection recovery failed, retrying anyway")
                
                # Brief pause before retry
                time.sleep(1)
                
            except Exception as e:
                # Non-connection related errors should not trigger recovery
                logger.error(f"Database session error (non-recoverable): {sanitize_for_log(str(e))}")
                raise
    
    def get_connection_health(self) -> Dict[str, Any]:
        """
        Get current connection health status
        
        Returns:
            Dict with connection health information
        """
        # Test connection if health check is stale
        current_time = time.time()
        if (not self._last_health_check or 
            current_time - self._last_health_check > self._health_check_interval):
            self.test_connection()
        
        return {
            "healthy": self._connection_healthy,
            "last_health_check": self._last_health_check,
            "failed_connections": self._failed_connections,
            "recovery_attempts": self._recovery_attempts,
            "max_recovery_attempts": self._max_recovery_attempts,
            "monitoring_enabled": self._monitoring_enabled
        }
    
    def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        Get database connection pool status
        
        Returns:
            Dict with connection pool information
        """
        try:
            if not hasattr(self.db_manager, 'engine') or not self.db_manager.engine:
                return {"error": "Database engine not available"}
            
            pool = self.db_manager.engine.pool
            
            if isinstance(pool, QueuePool):
                return {
                    "pool_type": "QueuePool",
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
            else:
                return {
                    "pool_type": type(pool).__name__,
                    "size": getattr(pool, 'size', lambda: 'unknown')(),
                    "checked_in": getattr(pool, 'checkedin', lambda: 'unknown')(),
                    "checked_out": getattr(pool, 'checkedout', lambda: 'unknown')()
                }
                
        except Exception as e:
            logger.error(f"Error getting connection pool status: {sanitize_for_log(str(e))}")
            return {"error": str(e)}
    
    def enable_monitoring(self):
        """Enable connection monitoring"""
        self._monitoring_enabled = True
        logger.info("Database connection monitoring enabled")
    
    def disable_monitoring(self):
        """Disable connection monitoring"""
        self._monitoring_enabled = False
        logger.info("Database connection monitoring disabled")
    
    def reset_failure_counters(self):
        """Reset connection failure counters"""
        self._failed_connections = 0
        self._recovery_attempts = 0
        logger.info("Database connection failure counters reset")

# Decorator for functions that need resilient database access
def with_database_recovery(db_recovery: DatabaseConnectionRecovery, max_retries: int = 3):
    """
    Decorator for functions that need resilient database access
    
    Args:
        db_recovery: DatabaseConnectionRecovery instance
        max_retries: Maximum number of retry attempts
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except (DisconnectionError, OperationalError, TimeoutError) as e:
                    logger.warning(f"Database operation failed (attempt {attempt}/{max_retries}): {sanitize_for_log(str(e))}")
                    
                    if attempt == max_retries:
                        logger.error("All database operation attempts failed")
                        raise
                    
                    # Attempt recovery before retry
                    recovery_success = db_recovery.recover_connection()
                    if not recovery_success:
                        logger.warning("Connection recovery failed, retrying anyway")
                    
                    # Brief pause before retry
                    time.sleep(1)
                    
                except Exception as e:
                    # Non-connection related errors should not trigger recovery
                    logger.error(f"Database operation error (non-recoverable): {sanitize_for_log(str(e))}")
                    raise
        
        return wrapper
    return decorator