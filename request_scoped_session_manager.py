# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import time
from contextlib import contextmanager
from typing import Optional
from flask import g, has_request_context
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from database import DatabaseManager

logger = logging.getLogger(__name__)


class RequestScopedSessionManager:
    """Manages database sessions scoped to Flask requests to prevent DetachedInstanceError"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the request-scoped session manager.
        
        Args:
            db_manager: The database manager instance
        """
        self.db_manager = db_manager
        logger.info("RequestScopedSessionManager initialized")
    
    def get_request_session(self):
        """
        Get or create a database session for the current request.
        
        Returns:
            SQLAlchemy session object scoped to the current request
            
        Raises:
            RuntimeError: If called outside of Flask request context
        """
        if not has_request_context():
            raise RuntimeError("get_request_session() must be called within Flask request context")
        
        # Check if we already have a session for this request
        if not hasattr(g, 'db_session') or g.db_session is None:
            # Time session creation for performance monitoring
            start_time = time.time()
            
            try:
                # Create a new session for this request using the database manager
                g.db_session = self.db_manager.get_session()
                creation_duration = time.time() - start_time
                
                logger.debug("Created new request-scoped database session")
                
                # Record performance metrics
                self._record_session_creation(creation_duration)
                
            except Exception as e:
                creation_duration = time.time() - start_time
                logger.error(f"Failed to create request session in {creation_duration:.3f}s: {e}")
                self._record_session_error("creation_failed", str(e))
                raise
        
        return g.db_session
    
    def close_request_session(self):
        """
        Close the database session at the end of the request.
        
        This method should be called in Flask's teardown_request handler
        to ensure proper cleanup of database resources.
        """
        if not has_request_context():
            logger.warning("close_request_session() called outside Flask request context")
            return
        
        if hasattr(g, 'db_session') and g.db_session is not None:
            # Time session cleanup for performance monitoring
            start_time = time.time()
            
            try:
                # Close the session using the database manager
                self.db_manager.close_session(g.db_session)
                cleanup_duration = time.time() - start_time
                
                logger.debug("Closed request-scoped database session")
                
                # Record performance metrics
                self._record_session_closure(cleanup_duration)
                
            except Exception as e:
                cleanup_duration = time.time() - start_time
                logger.error(f"Error closing request session in {cleanup_duration:.3f}s: {e}")
                self._record_session_error("closure_failed", str(e))
            finally:
                # Remove the session from g
                g.db_session = None
                if hasattr(g, 'db_session'):
                    delattr(g, 'db_session')
    
    @contextmanager
    def session_scope(self):
        """
        Context manager for database operations with automatic commit/rollback.
        
        This provides a transactional scope around a series of operations.
        The session will be committed if no exceptions occur, otherwise
        it will be rolled back.
        
        Yields:
            SQLAlchemy session object
            
        Example:
            with session_manager.session_scope() as session:
                user = session.query(User).get(user_id)
                user.name = "New Name"
                # Automatic commit happens here if no exception
        """
        session = self.get_request_session()
        try:
            yield session
            session.commit()
            logger.debug("Database transaction committed successfully")
            self._record_session_commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction rolled back due to error: {e}")
            self._record_session_rollback()
            self._record_session_error("transaction_rollback", str(e))
            raise
    
    def ensure_session_attachment(self, obj):
        """
        Ensure that a database object is attached to the current request session.
        
        This method helps prevent DetachedInstanceError by reattaching objects
        to the current session if they become detached.
        
        Args:
            obj: SQLAlchemy model instance to ensure attachment
            
        Returns:
            The object attached to the current session
        """
        if obj is None:
            return None
        
        session = self.get_request_session()
        
        # Check if the object is already in this session
        try:
            if obj in session:
                return obj
        except (TypeError, AttributeError):
            # Handle cases where session is a Mock object or doesn't support 'in' operator
            pass
        
        # Time the reattachment operation
        start_time = time.time()
        
        try:
            # Try to merge the object into the current session
            attached_obj = session.merge(obj)
            reattachment_duration = time.time() - start_time
            
            logger.debug(f"Reattached {type(obj).__name__} object to request session")
            
            # Record performance metrics
            self._record_session_reattachment(type(obj).__name__, reattachment_duration)
            
            return attached_obj
        except SQLAlchemyError as e:
            reattachment_duration = time.time() - start_time
            logger.error(f"Failed to reattach object to session in {reattachment_duration:.3f}s: {e}")
            self._record_session_error("reattachment_failed", str(e))
            raise
    
    def is_session_active(self) -> bool:
        """
        Check if there is an active session for the current request.
        
        Returns:
            True if there is an active session, False otherwise
        """
        if not has_request_context():
            return False
        
        return hasattr(g, 'db_session') and g.db_session is not None
    
    def get_session_info(self) -> dict:
        """
        Get information about the current session for debugging purposes.
        
        Returns:
            Dictionary containing session information
        """
        info = {
            'has_request_context': has_request_context(),
            'has_session': False,
            'session_active': False,
            'session_dirty': False,
            'session_new': False,
            'session_deleted': False
        }
        
        if has_request_context() and hasattr(g, 'db_session'):
            session = g.db_session
            info.update({
                'has_session': True,
                'session_active': session.is_active,
                'session_dirty': bool(session.dirty),
                'session_new': bool(session.new),
                'session_deleted': bool(session.deleted)
            })
        
        return info
    
    def _record_session_creation(self, duration: float):
        """Record session creation metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_session_creation(duration)
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            logger.debug(f"Failed to record session creation metrics: {e}")
    
    def _record_session_closure(self, duration: float):
        """Record session closure metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_session_closure(duration)
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            logger.debug(f"Failed to record session closure metrics: {e}")
    
    def _record_session_commit(self):
        """Record session commit metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_session_commit()
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            logger.debug(f"Failed to record session commit metrics: {e}")
    
    def _record_session_rollback(self):
        """Record session rollback metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_session_rollback()
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            logger.debug(f"Failed to record session rollback metrics: {e}")
    
    def _record_session_reattachment(self, object_type: str, duration: float):
        """Record session reattachment metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_session_reattachment(object_type)
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            logger.debug(f"Failed to record session reattachment metrics: {e}")
    
    def _record_session_error(self, error_type: str, error_message: str):
        """Record session error metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_session_error(error_type, error_message)
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            logger.debug(f"Failed to record session error metrics: {e}")