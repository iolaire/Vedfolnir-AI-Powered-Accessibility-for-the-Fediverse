# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session State Manager

Provides comprehensive session state management for concurrent sessions,
proper session isolation, and meaningful error messages for session-related failures.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from flask import g, has_request_context
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import DetachedInstanceError

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session state enumeration"""
    CREATED = "created"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class SessionInfo:
    """Information about a session"""
    session_id: str
    user_id: int
    state: SessionState
    created_at: datetime
    last_accessed: datetime
    platform_id: Optional[int] = None
    error_count: int = 0
    error_messages: List[str] = field(default_factory=list)
    thread_id: Optional[int] = None
    request_count: int = 0


class SessionStateManager:
    """Manages session state for concurrent sessions with proper isolation"""
    
    def __init__(self):
        """Initialize session state manager"""
        self._sessions: Dict[str, SessionInfo] = {}
        self._user_sessions: Dict[int, Set[str]] = {}
        self._lock = threading.RLock()
        self._cleanup_threshold = 100  # Clean up after this many sessions
        
    def create_session_state(self, session_id: str, user_id: int, platform_id: Optional[int] = None) -> SessionInfo:
        """Create session state tracking
        
        Args:
            session_id: Session ID
            user_id: User ID
            platform_id: Optional platform ID
            
        Returns:
            SessionInfo object
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            
            session_info = SessionInfo(
                session_id=session_id,
                user_id=user_id,
                state=SessionState.CREATED,
                created_at=now,
                last_accessed=now,
                platform_id=platform_id,
                thread_id=threading.get_ident()
            )
            
            self._sessions[session_id] = session_info
            
            # Track user sessions
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session_id)
            
            logger.debug(f"Created session state for {session_id} (user {user_id})")
            return session_info
    
    def update_session_state(self, session_id: str, state: SessionState, error_message: Optional[str] = None):
        """Update session state
        
        Args:
            session_id: Session ID
            state: New session state
            error_message: Optional error message
        """
        with self._lock:
            if session_id in self._sessions:
                session_info = self._sessions[session_id]
                session_info.state = state
                session_info.last_accessed = datetime.now(timezone.utc)
                
                if error_message:
                    session_info.error_count += 1
                    session_info.error_messages.append(error_message)
                    
                    # Limit error message history
                    if len(session_info.error_messages) > 10:
                        session_info.error_messages = session_info.error_messages[-10:]
                
                logger.debug(f"Updated session {session_id} state to {state.value}")
            else:
                logger.warning(f"Attempted to update non-existent session {session_id}")
    
    def get_session_state(self, session_id: str) -> Optional[SessionInfo]:
        """Get session state information
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionInfo object or None if not found
        """
        with self._lock:
            return self._sessions.get(session_id)
    
    def get_user_sessions(self, user_id: int) -> List[SessionInfo]:
        """Get all sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of SessionInfo objects
        """
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    def get_concurrent_sessions(self) -> Dict[int, List[SessionInfo]]:
        """Get all concurrent sessions grouped by user
        
        Returns:
            Dictionary mapping user IDs to their active sessions
        """
        with self._lock:
            concurrent = {}
            for user_id, session_ids in self._user_sessions.items():
                active_sessions = []
                for sid in session_ids:
                    if sid in self._sessions:
                        session_info = self._sessions[sid]
                        if session_info.state in [SessionState.CREATED, SessionState.ACTIVE]:
                            active_sessions.append(session_info)
                
                if active_sessions:
                    concurrent[user_id] = active_sessions
            
            return concurrent
    
    def cleanup_session_state(self, session_id: str):
        """Clean up session state
        
        Args:
            session_id: Session ID to clean up
        """
        with self._lock:
            if session_id in self._sessions:
                session_info = self._sessions[session_id]
                user_id = session_info.user_id
                
                # Remove from sessions
                del self._sessions[session_id]
                
                # Remove from user sessions
                if user_id in self._user_sessions:
                    self._user_sessions[user_id].discard(session_id)
                    if not self._user_sessions[user_id]:
                        del self._user_sessions[user_id]
                
                logger.debug(f"Cleaned up session state for {session_id}")
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired session states
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_sessions = []
            
            for session_id, session_info in self._sessions.items():
                age_hours = (now - session_info.last_accessed).total_seconds() / 3600
                if age_hours > max_age_hours or session_info.state == SessionState.EXPIRED:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self.cleanup_session_state(session_id)
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired session states")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics
        
        Returns:
            Dictionary with session statistics
        """
        with self._lock:
            stats = {
                'total_sessions': len(self._sessions),
                'active_sessions': 0,
                'error_sessions': 0,
                'users_with_sessions': len(self._user_sessions),
                'concurrent_users': 0,
                'average_errors_per_session': 0,
                'state_distribution': {}
            }
            
            total_errors = 0
            state_counts = {}
            
            for session_info in self._sessions.values():
                # Count by state
                state_name = session_info.state.value
                state_counts[state_name] = state_counts.get(state_name, 0) + 1
                
                if session_info.state == SessionState.ACTIVE:
                    stats['active_sessions'] += 1
                elif session_info.state == SessionState.ERROR:
                    stats['error_sessions'] += 1
                
                total_errors += session_info.error_count
            
            # Calculate concurrent users
            concurrent = self.get_concurrent_sessions()
            stats['concurrent_users'] = len(concurrent)
            
            # Calculate average errors
            if self._sessions:
                stats['average_errors_per_session'] = total_errors / len(self._sessions)
            
            stats['state_distribution'] = state_counts
            
            return stats
    
    @contextmanager
    def session_isolation_context(self, session_id: str):
        """Context manager for session isolation
        
        Args:
            session_id: Session ID to isolate
        """
        # Mark session as active
        self.update_session_state(session_id, SessionState.ACTIVE)
        
        # Store original g state if in Flask context
        original_g_state = None
        if has_request_context():
            original_g_state = getattr(g, '__dict__', {}).copy() if hasattr(g, '__dict__') else {}
        
        try:
            yield
        except DetachedInstanceError as e:
            self.update_session_state(session_id, SessionState.ERROR, f"DetachedInstanceError: {str(e)}")
            raise
        except SQLAlchemyError as e:
            self.update_session_state(session_id, SessionState.ERROR, f"SQLAlchemyError: {str(e)}")
            raise
        except Exception as e:
            self.update_session_state(session_id, SessionState.ERROR, f"Unexpected error: {str(e)}")
            raise
        finally:
            # Restore original g state if in Flask context
            if has_request_context() and original_g_state is not None:
                if hasattr(g, '__dict__'):
                    g.__dict__.clear()
                    g.__dict__.update(original_g_state)
    
    def generate_meaningful_error_message(self, error: Exception, session_id: str, endpoint: str) -> str:
        """Generate meaningful error message for session failures
        
        Args:
            error: The exception that occurred
            session_id: Session ID where error occurred
            endpoint: Endpoint where error occurred
            
        Returns:
            Meaningful error message
        """
        session_info = self.get_session_state(session_id)
        
        if isinstance(error, DetachedInstanceError):
            if session_info and session_info.error_count > 3:
                return (
                    "Your session has encountered multiple database connection issues. "
                    "Please refresh the page and log in again. If the problem persists, "
                    "contact support."
                )
            else:
                return (
                    "Your session has expired due to a database connection issue. "
                    "Please refresh the page to continue."
                )
        
        elif isinstance(error, SQLAlchemyError):
            return (
                "A database error occurred while processing your request. "
                "Please try again in a moment. If the problem continues, "
                "contact support."
            )
        
        else:
            return (
                f"An unexpected error occurred in {endpoint}. "
                "Please refresh the page and try again. If the problem persists, "
                "contact support with the following information: "
                f"Session ID: {session_id[:8]}..."
            )
    
    def detect_session_conflicts(self) -> List[Dict[str, Any]]:
        """Detect potential session conflicts
        
        Returns:
            List of detected conflicts
        """
        with self._lock:
            conflicts = []
            concurrent = self.get_concurrent_sessions()
            
            for user_id, sessions in concurrent.items():
                if len(sessions) > 1:
                    # Multiple active sessions for same user
                    conflicts.append({
                        'type': 'multiple_sessions',
                        'user_id': user_id,
                        'session_count': len(sessions),
                        'session_ids': [s.session_id for s in sessions]
                    })
                
                # Check for sessions with high error rates
                for session in sessions:
                    if session.error_count > 5:
                        conflicts.append({
                            'type': 'high_error_rate',
                            'user_id': user_id,
                            'session_id': session.session_id,
                            'error_count': session.error_count,
                            'recent_errors': session.error_messages[-3:]
                        })
            
            return conflicts


# Global session state manager instance
_session_state_manager = None


def get_session_state_manager() -> SessionStateManager:
    """Get the global session state manager instance
    
    Returns:
        SessionStateManager instance
    """
    global _session_state_manager
    if _session_state_manager is None:
        _session_state_manager = SessionStateManager()
    return _session_state_manager


def initialize_session_state_management():
    """Initialize session state management"""
    manager = get_session_state_manager()
    logger.info("Session state management initialized")
    return manager