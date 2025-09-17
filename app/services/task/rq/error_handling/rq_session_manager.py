# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Session Manager

Manages database sessions properly in RQ worker threads to prevent connection leaks
and ensure proper session lifecycle management.
"""

import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.orm import Session

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class RQSessionManager:
    """Manages database sessions for RQ workers with proper lifecycle and cleanup"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize RQ Session Manager
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self._local = threading.local()
        self._session_registry: Dict[int, Dict[str, Any]] = {}
        self._registry_lock = threading.Lock()
        
        # Session configuration
        self.session_timeout = 300  # 5 minutes
        self.max_sessions_per_thread = 1
        self.cleanup_interval = 60  # 1 minute
        
        # Health monitoring
        self._last_cleanup = time.time()
        self._session_count = 0
        self._connection_errors = 0
        
        logger.info("RQ Session Manager initialized with proper lifecycle management")
    
    @contextmanager
    def get_session_context(self):
        """
        Get database session with proper context management and automatic cleanup
        
        Yields:
            Session: SQLAlchemy session with automatic cleanup
        """
        session = None
        thread_id = threading.get_ident()
        
        try:
            # Get or create session for current thread
            session = self._get_thread_session()
            
            # Register session
            self._register_session(thread_id, session)
            
            yield session
            
            # Commit if no exceptions occurred
            if session and session.is_active:
                session.commit()
                
        except SQLAlchemyError as e:
            # Rollback on database errors
            if session and session.is_active:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback session: {sanitize_for_log(str(rollback_error))}")
            
            self._connection_errors += 1
            logger.error(f"Database error in RQ session: {sanitize_for_log(str(e))}")
            raise
            
        except Exception as e:
            # Rollback on any other errors
            if session and session.is_active:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback session: {sanitize_for_log(str(rollback_error))}")
            
            logger.error(f"Unexpected error in RQ session: {sanitize_for_log(str(e))}")
            raise
            
        finally:
            # Always cleanup session
            if session:
                self._cleanup_session(thread_id, session)
    
    def _get_thread_session(self) -> Session:
        """Get or create session for current thread"""
        if not hasattr(self._local, 'session') or self._local.session is None:
            try:
                # Create new session
                self._local.session = self.db_manager.get_session()
                self._session_count += 1
                
                logger.debug(f"Created new database session for thread {threading.get_ident()}")
                
            except Exception as e:
                self._connection_errors += 1
                logger.error(f"Failed to create database session: {sanitize_for_log(str(e))}")
                raise
        
        return self._local.session
    
    def _register_session(self, thread_id: int, session: Session) -> None:
        """Register session in registry for monitoring"""
        with self._registry_lock:
            self._session_registry[thread_id] = {
                'session': session,
                'created_at': time.time(),
                'last_activity': time.time(),
                'query_count': 0
            }
    
    def _cleanup_session(self, thread_id: int, session: Session) -> None:
        """Cleanup session and remove from registry"""
        try:
            # Close session
            if session and not session.is_closed:
                session.close()
                self._session_count = max(0, self._session_count - 1)
            
            # Remove from thread local
            if hasattr(self._local, 'session'):
                self._local.session = None
            
            # Remove from registry
            with self._registry_lock:
                if thread_id in self._session_registry:
                    del self._session_registry[thread_id]
            
            logger.debug(f"Cleaned up database session for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session: {sanitize_for_log(str(e))}")
    
    def cleanup_session(self) -> None:
        """Manually cleanup current thread's session"""
        thread_id = threading.get_ident()
        
        if hasattr(self._local, 'session') and self._local.session:
            self._cleanup_session(thread_id, self._local.session)
    
    def cleanup_stale_sessions(self) -> int:
        """
        Cleanup stale sessions that have been idle too long
        
        Returns:
            int: Number of sessions cleaned up
        """
        current_time = time.time()
        cleaned_count = 0
        
        with self._registry_lock:
            stale_threads = []
            
            for thread_id, session_info in self._session_registry.items():
                # Check if session is stale
                idle_time = current_time - session_info['last_activity']
                
                if idle_time > self.session_timeout:
                    stale_threads.append(thread_id)
            
            # Cleanup stale sessions
            for thread_id in stale_threads:
                try:
                    session_info = self._session_registry[thread_id]
                    session = session_info['session']
                    
                    if session and not session.is_closed:
                        session.close()
                        self._session_count = max(0, self._session_count - 1)
                    
                    del self._session_registry[thread_id]
                    cleaned_count += 1
                    
                    logger.debug(f"Cleaned up stale session for thread {thread_id}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up stale session: {sanitize_for_log(str(e))}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale database sessions")
        
        self._last_cleanup = current_time
        return cleaned_count
    
    def force_cleanup_all_sessions(self) -> int:
        """
        Force cleanup of all registered sessions (emergency cleanup)
        
        Returns:
            int: Number of sessions cleaned up
        """
        cleaned_count = 0
        
        with self._registry_lock:
            thread_ids = list(self._session_registry.keys())
            
            for thread_id in thread_ids:
                try:
                    session_info = self._session_registry[thread_id]
                    session = session_info['session']
                    
                    if session and not session.is_closed:
                        session.close()
                        self._session_count = max(0, self._session_count - 1)
                    
                    del self._session_registry[thread_id]
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error in force cleanup: {sanitize_for_log(str(e))}")
            
            # Clear thread local storage
            if hasattr(self._local, 'session'):
                self._local.session = None
        
        logger.warning(f"Force cleaned up {cleaned_count} database sessions")
        return cleaned_count
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics for monitoring"""
        current_time = time.time()
        
        with self._registry_lock:
            active_sessions = len(self._session_registry)
            
            # Calculate session ages
            session_ages = []
            for session_info in self._session_registry.values():
                age = current_time - session_info['created_at']
                session_ages.append(age)
            
            avg_age = sum(session_ages) / len(session_ages) if session_ages else 0
            max_age = max(session_ages) if session_ages else 0
            
            return {
                'active_sessions': active_sessions,
                'total_sessions_created': self._session_count,
                'connection_errors': self._connection_errors,
                'average_session_age': avg_age,
                'max_session_age': max_age,
                'last_cleanup': self._last_cleanup,
                'stale_sessions': sum(1 for age in session_ages if age > self.session_timeout)
            }
    
    def is_healthy(self) -> bool:
        """Check if session manager is healthy"""
        try:
            stats = self.get_session_statistics()
            
            # Check for too many active sessions
            if stats['active_sessions'] > 10:
                return False
            
            # Check for too many connection errors
            if stats['connection_errors'] > 5:
                return False
            
            # Check for stale sessions
            if stats['stale_sessions'] > 3:
                return False
            
            # Check if cleanup is running regularly
            time_since_cleanup = time.time() - stats['last_cleanup']
            if time_since_cleanup > self.cleanup_interval * 2:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {sanitize_for_log(str(e))}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status"""
        try:
            stats = self.get_session_statistics()
            is_healthy = self.is_healthy()
            
            issues = []
            
            if stats['active_sessions'] > 10:
                issues.append(f"Too many active sessions: {stats['active_sessions']}")
            
            if stats['connection_errors'] > 5:
                issues.append(f"High connection error count: {stats['connection_errors']}")
            
            if stats['stale_sessions'] > 3:
                issues.append(f"Too many stale sessions: {stats['stale_sessions']}")
            
            time_since_cleanup = time.time() - stats['last_cleanup']
            if time_since_cleanup > self.cleanup_interval * 2:
                issues.append(f"Cleanup overdue by {time_since_cleanup - self.cleanup_interval:.1f}s")
            
            return {
                'healthy': is_healthy,
                'issues': issues,
                'statistics': stats,
                'recommendations': self._get_health_recommendations(stats, issues)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'issues': [f"Health check failed: {str(e)}"],
                'error': str(e)
            }
    
    def _get_health_recommendations(self, stats: Dict[str, Any], issues: List[str]) -> List[str]:
        """Get health recommendations based on current status"""
        recommendations = []
        
        if stats['active_sessions'] > 5:
            recommendations.append("Consider running cleanup_stale_sessions()")
        
        if stats['connection_errors'] > 2:
            recommendations.append("Check database connectivity and pool configuration")
        
        if stats['stale_sessions'] > 0:
            recommendations.append("Run regular session cleanup")
        
        if stats['max_session_age'] > self.session_timeout:
            recommendations.append("Some sessions are exceeding timeout - investigate long-running operations")
        
        return recommendations
    
    def run_maintenance(self) -> Dict[str, Any]:
        """Run maintenance operations"""
        try:
            # Cleanup stale sessions
            cleaned_sessions = self.cleanup_stale_sessions()
            
            # Reset error counters if they're getting high
            if self._connection_errors > 10:
                old_errors = self._connection_errors
                self._connection_errors = 0
                logger.info(f"Reset connection error counter from {old_errors} to 0")
            
            return {
                'success': True,
                'cleaned_sessions': cleaned_sessions,
                'maintenance_completed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Maintenance failed: {sanitize_for_log(str(e))}")
            return {
                'success': False,
                'error': str(e)
            }