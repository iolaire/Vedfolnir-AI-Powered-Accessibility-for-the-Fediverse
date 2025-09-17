# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Worker Session Manager

Manages database sessions properly in RQ worker threads to prevent connection leaks
and ensure proper session lifecycle management.
"""

import logging
import threading
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class WorkerSessionManager:
    """Manages database sessions for RQ worker threads"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize WorkerSessionManager
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self._local = threading.local()
        self._session_count = 0
        self._lock = threading.Lock()
    
    def get_session(self) -> Session:
        """
        Get thread-local database session
        
        Returns:
            Session: SQLAlchemy session for current thread
        """
        if not hasattr(self._local, 'session') or self._local.session is None:
            try:
                self._local.session = self.db_manager.get_session()
                with self._lock:
                    self._session_count += 1
                
                thread_id = threading.get_ident()
                logger.debug(f"Created new database session for worker thread {thread_id}")
                
            except Exception as e:
                logger.error(f"Failed to create database session: {sanitize_for_log(str(e))}")
                raise
        
        return self._local.session
    
    def close_session(self) -> None:
        """Close thread-local session"""
        if hasattr(self._local, 'session') and self._local.session is not None:
            try:
                self._local.session.close()
                with self._lock:
                    self._session_count -= 1
                
                thread_id = threading.get_ident()
                logger.debug(f"Closed database session for worker thread {thread_id}")
                
            except Exception as e:
                logger.error(f"Error closing database session: {sanitize_for_log(str(e))}")
            finally:
                self._local.session = None
                if hasattr(self._local, 'session'):
                    delattr(self._local, 'session')
    
    def rollback_session(self) -> None:
        """Rollback current session if it exists"""
        if hasattr(self._local, 'session') and self._local.session is not None:
            try:
                self._local.session.rollback()
                logger.debug("Rolled back database session")
            except Exception as e:
                logger.error(f"Error rolling back database session: {sanitize_for_log(str(e))}")
    
    def commit_session(self) -> None:
        """Commit current session if it exists"""
        if hasattr(self._local, 'session') and self._local.session is not None:
            try:
                self._local.session.commit()
                logger.debug("Committed database session")
            except Exception as e:
                logger.error(f"Error committing database session: {sanitize_for_log(str(e))}")
                raise
    
    def ensure_session_cleanup(self) -> None:
        """Ensure session is properly cleaned up (for use in finally blocks)"""
        try:
            self.close_session()
        except Exception as e:
            logger.error(f"Error during session cleanup: {sanitize_for_log(str(e))}")
    
    def get_session_count(self) -> int:
        """Get current number of active sessions"""
        with self._lock:
            return self._session_count
    
    def has_active_session(self) -> bool:
        """Check if current thread has an active session"""
        return (hasattr(self._local, 'session') and 
                self._local.session is not None)
    
    def get_session_info(self) -> dict:
        """Get information about current session"""
        info = {
            'thread_id': threading.get_ident(),
            'has_session': self.has_active_session(),
            'total_sessions': self.get_session_count()
        }
        
        if self.has_active_session():
            try:
                session = self._local.session
                info.update({
                    'session_id': id(session),
                    'is_active': session.is_active,
                    'dirty_objects': len(session.dirty),
                    'new_objects': len(session.new),
                    'deleted_objects': len(session.deleted)
                })
            except Exception as e:
                info['session_error'] = str(e)
        
        return info