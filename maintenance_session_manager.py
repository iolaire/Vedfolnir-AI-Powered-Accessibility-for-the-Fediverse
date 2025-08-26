# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Session Manager

Manages user sessions during maintenance mode transitions, including
session invalidation and login prevention for non-admin users.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from redis_session_manager import RedisSessionManager
from models import User, UserRole
from database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Information about an active session"""
    session_id: str
    user_id: int
    username: str
    user_role: str
    created_at: datetime
    last_activity: datetime
    platform_connection_id: Optional[int] = None


class SessionInvalidationError(Exception):
    """Raised when session invalidation fails"""
    pass


class MaintenanceSessionManager:
    """
    Session manager for maintenance mode operations
    
    Features:
    - Selective session invalidation based on user role
    - Login prevention for non-admin users during maintenance
    - Session monitoring and reporting
    - Integration with Redis session backend
    """
    
    def __init__(self, redis_session_manager: RedisSessionManager, db_manager: DatabaseManager):
        """
        Initialize maintenance session manager
        
        Args:
            redis_session_manager: Redis session manager instance
            db_manager: Database manager for user lookups
        """
        self.redis_session_manager = redis_session_manager
        self.db_manager = db_manager
        
        # Track maintenance state
        self._login_prevention_active = False
        self._invalidated_sessions_count = 0
        
        # Statistics
        self._stats = {
            'sessions_invalidated': 0,
            'login_attempts_blocked': 0,
            'admin_sessions_preserved': 0,
            'errors': 0
        }
    
    def invalidate_non_admin_sessions(self) -> List[str]:
        """
        Invalidate all non-admin user sessions
        
        Returns:
            List of invalidated session IDs
            
        Raises:
            SessionInvalidationError: If invalidation fails
        """
        try:
            logger.info("Starting non-admin session invalidation for maintenance mode")
            
            invalidated_sessions = []
            admin_sessions_preserved = 0
            
            # Get all active sessions from Redis
            active_sessions = self._get_all_active_sessions()
            
            for session_info in active_sessions:
                try:
                    # Check if user is admin
                    if session_info.user_role == UserRole.ADMIN.value:
                        admin_sessions_preserved += 1
                        logger.debug(f"Preserving admin session for user {session_info.username}")
                        continue
                    
                    # Invalidate non-admin session
                    success = self.redis_session_manager.destroy_session(session_info.session_id)
                    if success:
                        invalidated_sessions.append(session_info.session_id)
                        logger.debug(f"Invalidated session for user {session_info.username}")
                    else:
                        logger.warning(f"Failed to invalidate session {session_info.session_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing session {session_info.session_id}: {str(e)}")
                    self._stats['errors'] += 1
            
            # Update statistics
            self._stats['sessions_invalidated'] += len(invalidated_sessions)
            self._stats['admin_sessions_preserved'] += admin_sessions_preserved
            self._invalidated_sessions_count = len(invalidated_sessions)
            
            logger.info(f"Invalidated {len(invalidated_sessions)} non-admin sessions, "
                       f"preserved {admin_sessions_preserved} admin sessions")
            
            return invalidated_sessions
            
        except Exception as e:
            logger.error(f"Error invalidating non-admin sessions: {str(e)}")
            self._stats['errors'] += 1
            raise SessionInvalidationError(f"Failed to invalidate sessions: {str(e)}")
    
    def prevent_non_admin_login(self) -> None:
        """
        Enable login prevention for non-admin users
        
        This sets a flag that can be checked during login attempts
        to prevent non-admin users from logging in during maintenance.
        """
        try:
            self._login_prevention_active = True
            logger.info("Enabled login prevention for non-admin users")
            
            # Store the prevention state in Redis for persistence across restarts
            try:
                self.redis_session_manager.redis_client.set(
                    "vedfolnir:maintenance:login_prevention",
                    "true",
                    ex=7200  # 2 hours expiration
                )
            except Exception as e:
                logger.warning(f"Failed to persist login prevention state in Redis: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error enabling login prevention: {str(e)}")
            self._stats['errors'] += 1
    
    def allow_non_admin_login(self) -> None:
        """
        Disable login prevention for non-admin users
        
        This removes the login prevention flag, allowing normal login behavior.
        """
        try:
            self._login_prevention_active = False
            logger.info("Disabled login prevention for non-admin users")
            
            # Remove the prevention state from Redis
            try:
                self.redis_session_manager.redis_client.delete("vedfolnir:maintenance:login_prevention")
            except Exception as e:
                logger.warning(f"Failed to remove login prevention state from Redis: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error disabling login prevention: {str(e)}")
            self._stats['errors'] += 1
    
    def is_login_prevented_for_user(self, user: User) -> bool:
        """
        Check if login should be prevented for a specific user
        
        Args:
            user: User attempting to login
            
        Returns:
            True if login should be prevented, False otherwise
        """
        try:
            # Admin users can always login
            if user.role == UserRole.ADMIN:
                return False
            
            # Check local state first
            if self._login_prevention_active:
                self._stats['login_attempts_blocked'] += 1
                return True
            
            # Check Redis state (for persistence across restarts)
            try:
                redis_state = self.redis_session_manager.redis_client.get("vedfolnir:maintenance:login_prevention")
                if redis_state == "true":
                    self._login_prevention_active = True  # Sync local state
                    self._stats['login_attempts_blocked'] += 1
                    return True
            except Exception as e:
                logger.warning(f"Failed to check Redis login prevention state: {str(e)}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking login prevention for user {user.username}: {str(e)}")
            self._stats['errors'] += 1
            # Default to allowing login on error to prevent lockout
            return False
    
    def get_active_non_admin_sessions(self) -> List[SessionInfo]:
        """
        Get list of active non-admin user sessions
        
        Returns:
            List of SessionInfo objects for non-admin sessions
        """
        try:
            active_sessions = self._get_all_active_sessions()
            non_admin_sessions = [
                session for session in active_sessions 
                if session.user_role != UserRole.ADMIN.value
            ]
            
            logger.debug(f"Found {len(non_admin_sessions)} active non-admin sessions")
            return non_admin_sessions
            
        except Exception as e:
            logger.error(f"Error getting active non-admin sessions: {str(e)}")
            self._stats['errors'] += 1
            return []
    
    def get_active_admin_sessions(self) -> List[SessionInfo]:
        """
        Get list of active admin user sessions
        
        Returns:
            List of SessionInfo objects for admin sessions
        """
        try:
            active_sessions = self._get_all_active_sessions()
            admin_sessions = [
                session for session in active_sessions 
                if session.user_role == UserRole.ADMIN.value
            ]
            
            logger.debug(f"Found {len(admin_sessions)} active admin sessions")
            return admin_sessions
            
        except Exception as e:
            logger.error(f"Error getting active admin sessions: {str(e)}")
            self._stats['errors'] += 1
            return []
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session management statistics
        
        Returns:
            Dictionary with session statistics
        """
        try:
            active_sessions = self._get_all_active_sessions()
            admin_sessions = len([s for s in active_sessions if s.user_role == UserRole.ADMIN.value])
            non_admin_sessions = len(active_sessions) - admin_sessions
            
            return {
                'total_active_sessions': len(active_sessions),
                'admin_sessions': admin_sessions,
                'non_admin_sessions': non_admin_sessions,
                'login_prevention_active': self._login_prevention_active,
                'invalidated_sessions_count': self._invalidated_sessions_count,
                'statistics': self._stats.copy()
            }
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {str(e)}")
            return {
                'total_active_sessions': 0,
                'admin_sessions': 0,
                'non_admin_sessions': 0,
                'login_prevention_active': self._login_prevention_active,
                'invalidated_sessions_count': self._invalidated_sessions_count,
                'statistics': self._stats.copy(),
                'error': str(e)
            }
    
    def cleanup_maintenance_state(self) -> bool:
        """
        Clean up maintenance-related session state
        
        Returns:
            True if cleanup was successful
        """
        try:
            # Reset local state
            self._login_prevention_active = False
            self._invalidated_sessions_count = 0
            
            # Clean up Redis state
            try:
                self.redis_session_manager.redis_client.delete("vedfolnir:maintenance:login_prevention")
            except Exception as e:
                logger.warning(f"Failed to clean up Redis maintenance state: {str(e)}")
            
            logger.info("Cleaned up maintenance session state")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up maintenance state: {str(e)}")
            self._stats['errors'] += 1
            return False
    
    def _get_all_active_sessions(self) -> List[SessionInfo]:
        """
        Get all active sessions with user information
        
        Returns:
            List of SessionInfo objects
        """
        try:
            active_sessions = []
            
            # Get session index from Redis
            session_index_key = "vedfolnir:session_index:all"
            session_ids = self.redis_session_manager.redis_client.smembers(session_index_key)
            
            # Get user information from database for efficient lookup
            user_cache = {}
            with self.db_manager.get_session() as db_session:
                users = db_session.query(User).all()
                user_cache = {user.id: user for user in users}
            
            # Process each session
            for session_id in session_ids:
                try:
                    session_context = self.redis_session_manager.get_session_context(session_id)
                    if not session_context:
                        continue
                    
                    user_id = session_context['user_id']
                    user = user_cache.get(user_id)
                    if not user:
                        continue
                    
                    session_info = SessionInfo(
                        session_id=session_id,
                        user_id=user_id,
                        username=user.username,
                        user_role=user.role.value,
                        created_at=datetime.fromisoformat(session_context['created_at']),
                        last_activity=datetime.fromisoformat(session_context['last_activity']),
                        platform_connection_id=session_context.get('platform_connection_id')
                    )
                    
                    active_sessions.append(session_info)
                    
                except Exception as e:
                    logger.warning(f"Error processing session {session_id}: {str(e)}")
                    continue
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Error getting all active sessions: {str(e)}")
            return []