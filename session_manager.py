# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Session Management for Platform-Aware Database System

This module provides session management utilities that track user's active platform context
and handle platform switching, session cleanup, and security validation.
"""

from logging import getLogger
import uuid
from security.core.security_utils import sanitize_for_log
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from flask import session, request, g
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models import User, PlatformConnection, UserSession
from database import DatabaseManager

logger = getLogger(__name__)

class SessionManager:
    """Manages platform-aware user sessions"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session_timeout = timedelta(hours=24)  # Default session timeout
    
    def create_user_session(self, user_id: int, platform_connection_id: Optional[int] = None) -> str:
        """
        Create a new user session with optional platform context
        
        Args:
            user_id: ID of the user
            platform_connection_id: Optional platform connection ID to set as active
            
        Returns:
            Session ID string
            
        Raises:
            ValueError: If user or platform connection is invalid
        """
        db_session = self.db_manager.get_session()
        try:
            # Verify user exists
            user = db_session.query(User).get(user_id)
            if not user or not user.is_active:
                raise ValueError(f"User {user_id} not found or inactive")
            
            # Verify platform connection if provided
            if platform_connection_id:
                platform = db_session.query(PlatformConnection).filter_by(
                    id=platform_connection_id,
                    user_id=user_id,
                    is_active=True
                ).first()
                if not platform:
                    raise ValueError(f"Platform connection {platform_connection_id} not found or inactive")
            else:
                # Use user's default platform if no specific platform provided
                platform = db_session.query(PlatformConnection).filter_by(
                    user_id=user_id,
                    is_default=True,
                    is_active=True
                ).first()
                platform_connection_id = platform.id if platform else None
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create session record
            user_session = UserSession(
                user_id=user_id,
                session_id=session_id,
                active_platform_id=platform_connection_id
            )
            
            db_session.add(user_session)
            db_session.commit()
            
            logger.info(f"Created session {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))} with platform {sanitize_for_log(str(platform_connection_id))}")
            return session_id
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error creating session: {e}")
            raise
        finally:
            db_session.close()
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session context including user and platform information
        
        Args:
            session_id: Session ID to look up
            
        Returns:
            Dictionary with session context or None if session not found
        """
        try:
            db_session = self.db_manager.get_session()
            try:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id
                ).first()
                
                if not user_session:
                    return None
                
                # Check if session is expired
                if self._is_session_expired(user_session):
                    self._cleanup_session(user_session.session_id)
                    return None
                
                # Extract data from objects before closing session to avoid DetachedInstanceError
                user = user_session.user
                platform = user_session.active_platform
                
                context = {
                    'session_id': session_id,
                    'user_id': user.id if user else None,
                    'user_username': user.username if user else None,
                    'platform_connection_id': platform.id if platform else None,
                    'platform_name': platform.name if platform else None,
                    'platform_type': platform.platform_type if platform else None,
                    'created_at': user_session.created_at,
                    'updated_at': user_session.updated_at
                }
                
                return context
                
            except SQLAlchemyError as e:
                logger.error(f"Database error getting session context: {e}")
                return None
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return None
    
    def update_platform_context(self, session_id: str, platform_connection_id: int) -> bool:
        """
        Update the active platform for a session with proper validation
        
        Args:
            session_id: Session ID to update
            platform_connection_id: New platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        db_session = self.db_manager.get_session()
        try:
            user_session = db_session.query(UserSession).filter_by(
                session_id=session_id
            ).first()
            
            if not user_session:
                logger.warning(f"Session {sanitize_for_log(session_id)} not found for platform update")
                return False
            
            # Check if session is expired before updating
            if self._is_session_expired(user_session):
                logger.warning(f"Cannot update expired session {sanitize_for_log(session_id)}")
                self._cleanup_session(session_id)
                return False
            
            # Verify platform belongs to the user
            platform = db_session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                user_id=user_session.user_id,
                is_active=True
            ).first()
            
            if not platform:
                logger.warning(f"Platform {sanitize_for_log(str(platform_connection_id))} not found or not accessible to user {sanitize_for_log(str(user_session.user_id))}")
                return False
            
            # Update session
            user_session.active_platform_id = platform_connection_id
            user_session.updated_at = datetime.now(timezone.utc)
            
            # Update platform's last used timestamp
            platform.last_used = datetime.now(timezone.utc)
            
            db_session.commit()
            
            logger.info(f"Updated session {sanitize_for_log(session_id)} to use platform {sanitize_for_log(str(platform_connection_id))}")
            return True
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error updating platform context: {sanitize_for_log(str(e))}")
            return False
        except Exception as e:
            db_session.rollback()
            logger.error(f"Unexpected error updating platform context: {sanitize_for_log(str(e))}")
            return False
        finally:
            db_session.close()
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions using bulk delete for better performance
        
        Returns:
            Number of sessions cleaned up
        """
        db_session = self.db_manager.get_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - self.session_timeout
            
            # Use bulk delete for better performance, but handle timezone-naive datetimes
            # For safety, we'll use individual session checks instead of bulk delete
            sessions_to_delete = db_session.query(UserSession).all()
            count = 0
            for session_obj in sessions_to_delete:
                if self._is_session_expired(session_obj):
                    db_session.delete(session_obj)
                    count += 1
            
            db_session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {sanitize_for_log(str(count))} expired sessions")
            
            return count
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error cleaning up sessions: {e}")
            return 0
        finally:
            db_session.close()
    
    def cleanup_user_sessions(self, user_id: int, keep_current: Optional[str] = None) -> int:
        """
        Clean up expired sessions for a user, optionally keeping one current session.
        For concurrent sessions, only clean up expired sessions, not all sessions.
        
        Args:
            user_id: User ID to clean up sessions for
            keep_current: Session ID to keep (optional)
            
        Returns:
            Number of sessions cleaned up
        """
        db_session = self.db_manager.get_session()
        try:
            # Get all sessions for this user and check expiration safely
            query = db_session.query(UserSession).filter(UserSession.user_id == user_id)
            
            if keep_current:
                query = query.filter(UserSession.session_id != keep_current)
            
            all_sessions = query.all()
            sessions_to_delete = []
            
            for session_obj in all_sessions:
                if self._is_session_expired(session_obj):
                    sessions_to_delete.append(session_obj)
            
            count = len(sessions_to_delete)
            
            for session_obj in sessions_to_delete:
                db_session.delete(session_obj)
            
            db_session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {sanitize_for_log(str(count))} expired sessions for user {sanitize_for_log(str(user_id))}")
            
            return count
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error cleaning up user sessions: {e}")
            return 0
        finally:
            db_session.close()
    
    def get_user_active_sessions(self, user_id: int) -> list:
        """
        Get all active (non-expired) sessions for a user
        
        Args:
            user_id: User ID to get sessions for
            
        Returns:
            List of active session dictionaries
        """
        db_session = self.db_manager.get_session()
        try:
            # Get all sessions for this user and filter active ones safely
            all_sessions = db_session.query(UserSession).filter(
                UserSession.user_id == user_id
            ).order_by(UserSession.updated_at.desc()).all()
            
            active_sessions = []
            for session_obj in all_sessions:
                if not self._is_session_expired(session_obj):
                    active_sessions.append(session_obj)
            
            sessions_info = []
            for session_obj in active_sessions:
                platform = session_obj.active_platform
                sessions_info.append({
                    'session_id': session_obj.session_id,
                    'platform_id': platform.id if platform else None,
                    'platform_name': platform.name if platform else None,
                    'platform_type': platform.platform_type if platform else None,
                    'created_at': session_obj.created_at,
                    'updated_at': session_obj.updated_at,
                    'is_current': False  # Will be set by caller if needed
                })
            
            return sessions_info
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user sessions: {e}")
            return []
        finally:
            db_session.close()
    
    def cleanup_all_user_sessions(self, user_id: int) -> int:
        """
        Clean up ALL sessions for a user (for logout from all devices)
        
        Args:
            user_id: User ID to clean up sessions for
            
        Returns:
            Number of sessions cleaned up
        """
        db_session = self.db_manager.get_session()
        try:
            sessions_to_delete = db_session.query(UserSession).filter_by(user_id=user_id).all()
            count = len(sessions_to_delete)
            
            for session_obj in sessions_to_delete:
                db_session.delete(session_obj)
            
            db_session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up all {sanitize_for_log(str(count))} sessions for user {sanitize_for_log(str(user_id))}")
            
            return count
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error cleaning up all user sessions: {e}")
            return 0
        finally:
            db_session.close()
    
    def validate_session(self, session_id: str, user_id: int) -> bool:
        """
        Validate that a session belongs to the specified user and is not expired
        
        Args:
            session_id: Session ID to validate
            user_id: Expected user ID
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            context = self.get_session_context(session_id)
            
            if not context:
                return False
            
            return context['user_id'] == user_id
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False
    
    def _cleanup_session(self, session_id: str) -> bool:
        """
        Clean up a specific session
        
        Args:
            session_id: Session ID to clean up
            
        Returns:
            True if successful, False otherwise
        """
        db_session = self.db_manager.get_session()
        try:
            user_session = db_session.query(UserSession).filter_by(
                session_id=session_id
            ).first()
            
            if user_session:
                db_session.delete(user_session)
                db_session.commit()
                logger.info(f"Cleaned up session {sanitize_for_log(session_id)}")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error cleaning up session: {e}")
            return False
        finally:
            db_session.close()
    
    def _is_session_expired(self, user_session: UserSession) -> bool:
        """
        Check if a session is expired
        
        Args:
            user_session: UserSession object to check
            
        Returns:
            True if expired, False otherwise
        """
        if not user_session.updated_at:
            return True
        
        # Handle timezone-naive datetimes from legacy data
        updated_at = user_session.updated_at
        if updated_at.tzinfo is None:
            # Assume naive datetimes are UTC
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        
        return datetime.now(timezone.utc) - updated_at > self.session_timeout


class PlatformContextMiddleware:
    """Flask middleware for managing platform context in requests"""
    
    def __init__(self, app, session_manager: SessionManager):
        self.app = app
        self.session_manager = session_manager
        self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Set up platform context before each request with proper error handling"""
        # Initialize safe defaults first
        g.platform_context = None
        g.session_manager = self.session_manager
        
        try:
            # Skip for static files and health checks
            if request.endpoint in ['static', 'health']:
                return
            
            # Get session ID from Flask session
            flask_session_id = session.get('_id')
            if not flask_session_id:
                return
            
            # Get platform context from session manager
            context = self.session_manager.get_session_context(flask_session_id)
            if context:
                g.platform_context = context
                
                # Update session activity with proper database session management
                db_session = self.session_manager.db_manager.get_session()
                try:
                    user_session = db_session.query(UserSession).filter_by(
                        session_id=flask_session_id
                    ).first()
                    if user_session:
                        user_session.updated_at = datetime.now(timezone.utc)
                        db_session.commit()
                except SQLAlchemyError as e:
                    logger.error(f"Database error updating session activity: {sanitize_for_log(str(e))}")
                    db_session.rollback()
                finally:
                    db_session.close()
        except Exception as e:
            logger.error(f"Unexpected error in middleware before_request: {sanitize_for_log(str(e))}")
            # Ensure g has safe defaults even if there's an error
            g.platform_context = None
            g.session_manager = self.session_manager
    
    def after_request(self, response):
        """Clean up after request"""
        # Clean up any temporary context
        if hasattr(g, 'platform_context'):
            g.platform_context = None
        
        return response


def get_current_platform_context() -> Optional[Dict[str, Any]]:
    """
    Get the current platform context from Flask's g object
    
    Returns:
        Platform context dictionary or None
    """
    return getattr(g, 'platform_context', None)


def get_current_platform() -> Optional[PlatformConnection]:
    """
    Get the current platform connection from context using fresh database query
    
    Returns:
        PlatformConnection object or None
    """
    context = get_current_platform_context()
    if context and context.get('platform_connection_id'):
        # Import here to avoid circular imports
        from database import DatabaseManager
        from config import Config
        
        db_manager = DatabaseManager(Config())
        db_session = db_manager.get_session()
        try:
            return db_session.query(PlatformConnection).filter_by(
                id=context['platform_connection_id'],
                is_active=True
            ).first()
        finally:
            db_session.close()
    return None


def get_current_user_from_context() -> Optional[User]:
    """
    Get the current user from platform context using fresh database query
    
    Returns:
        User object or None
    """
    context = get_current_platform_context()
    if context and context.get('user_id'):
        # Import here to avoid circular imports
        from database import DatabaseManager
        from config import Config
        
        db_manager = DatabaseManager(Config())
        db_session = db_manager.get_session()
        try:
            return db_session.query(User).filter_by(
                id=context['user_id'],
                is_active=True
            ).first()
        finally:
            db_session.close()
    return None


def switch_platform_context(platform_connection_id: int) -> bool:
    """
    Switch the current session's platform context
    
    Args:
        platform_connection_id: ID of platform to switch to
        
    Returns:
        True if successful, False otherwise
    """
    context = get_current_platform_context()
    if not context:
        return False
    
    session_manager = getattr(g, 'session_manager', None)
    if not session_manager:
        return False
    
    return session_manager.update_platform_context(
        context['session_id'], 
        platform_connection_id
    )