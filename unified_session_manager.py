# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unified Session Management System

This module provides a single, comprehensive session management system using database
with a unified approach that eliminates session conflicts and complexity.
"""

from logging import getLogger
import uuid
from security.core.security_utils import sanitize_for_log
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError, InvalidRequestError

from models import User, PlatformConnection, UserSession
from database import DatabaseManager
from session_config import get_session_config, SessionConfig

logger = getLogger(__name__)

class SessionValidationError(Exception):
    """Raised when session validation fails"""
    pass

class SessionExpiredError(SessionValidationError):
    """Raised when session has expired"""
    pass

class SessionNotFoundError(SessionValidationError):
    """Raised when session doesn't exist"""
    pass

class SessionDatabaseError(Exception):
    """Raised when database session operations fail"""
    pass

class UnifiedSessionManager:
    """Single session manager using database as source of truth"""
    
    def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig] = None, security_manager=None, monitor=None, performance_optimizer=None):
        self.db_manager = db_manager
        self.config = config or get_session_config()
        self.session_timeout = timedelta(seconds=self.config.timeout.session_lifetime)
        
        # Initialize monitoring
        self.monitor = monitor
        self._monitor = None  # Keep for backward compatibility
        
        # Initialize security manager
        self.security_manager = security_manager
        
        # Initialize performance optimizer
        self.performance_optimizer = performance_optimizer
        
        # Initialize security hardening (lazy loading to avoid circular imports)
        self._security_hardening = None
    
    @property
    def security_hardening(self):
        """Lazy load security hardening to avoid circular imports"""
        if self._security_hardening is None:
            try:
                from security.features.session_security import SessionSecurityHardening
                self._security_hardening = SessionSecurityHardening()
            except ImportError:
                logger.debug("Session security hardening not available")
                self._security_hardening = None
        return self._security_hardening
    
    @contextmanager
    def get_db_session(self):
        """
        Context manager for database sessions with comprehensive error handling and cleanup
        
        Yields:
            SQLAlchemy session object
            
        Raises:
            SessionDatabaseError: For database-specific errors
        """
        db_session = None
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                db_session = self.db_manager.get_session()
                
                # Test connection health
                from sqlalchemy import text
                db_session.execute(text("SELECT 1"))
                
                yield db_session
                
                db_session.commit()
                
                # Log successful operation for monitoring
                logger.debug("Database session completed successfully")
                return
                
            except (DisconnectionError, TimeoutError, InvalidRequestError) as e:
                # Connection-related errors that might be recoverable
                retry_count += 1
                logger.warning(f"Database connection error (attempt {retry_count}/{max_retries}): {e}")
                
                if db_session:
                    try:
                        db_session.rollback()
                        db_session.close()
                    except Exception as cleanup_error:
                        logger.error(f"Error during session cleanup: {cleanup_error}")
                    db_session = None
                
                if retry_count >= max_retries:
                    logger.error(f"Database connection failed after {max_retries} attempts")
                    raise SessionDatabaseError(f"Database connection failed after {max_retries} attempts: {e}")
                
                # Brief delay before retry
                import time
                time.sleep(0.1 * retry_count)
                
            except SQLAlchemyError as e:
                # Database-specific errors
                if db_session:
                    try:
                        db_session.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {rollback_error}")
                
                logger.error(f"Database error in session: {e}")
                raise SessionDatabaseError(f"Database operation failed: {e}")
                
            except Exception as e:
                # General errors
                if db_session:
                    try:
                        db_session.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {rollback_error}")
                
                logger.error(f"Unexpected error in database session: {e}")
                raise SessionDatabaseError(f"Session operation failed: {e}")
                
            finally:
                if db_session:
                    try:
                        db_session.close()
                    except Exception as close_error:
                        logger.error(f"Error closing database session: {close_error}")
    
    def create_session(self, user_id: int, platform_connection_id: Optional[int] = None) -> str:
        """
        Create new database session and return session ID
        
        Args:
            user_id: ID of the user
            platform_connection_id: Optional platform connection ID
            
        Returns:
            Session ID string
            
        Raises:
            SessionValidationError: If user or platform is invalid
            SessionDatabaseError: If database operation fails
        """
        try:
            # First, clean up any existing sessions for this user to prevent conflicts
            self.cleanup_user_sessions(user_id)
            
            session_id = str(uuid.uuid4())
            
            with self.get_db_session() as db_session:
                # Verify user exists and is active
                user = db_session.get(User, user_id)
                if not user or not user.is_active:
                    raise SessionValidationError(f"User {user_id} not found or inactive")
                
                # Verify platform connection if provided
                if platform_connection_id:
                    platform = db_session.query(PlatformConnection).filter_by(
                        id=platform_connection_id,
                        user_id=user_id,
                        is_active=True
                    ).first()
                    if not platform:
                        raise SessionValidationError(f"Platform connection {platform_connection_id} not found or inactive")
                else:
                    # Use user's default platform if no specific platform provided
                    platform = db_session.query(PlatformConnection).filter_by(
                        user_id=user_id,
                        is_default=True,
                        is_active=True
                    ).first()
                    platform_connection_id = platform.id if platform else None
                
                # Create session fingerprint
                fingerprint = self._create_session_fingerprint()
                
                # Calculate expiration time
                expires_at = datetime.now(timezone.utc) + self.session_timeout
                
                # Create new user session
                user_session = UserSession(
                    user_id=user_id,
                    session_id=session_id,
                    active_platform_id=platform_connection_id,
                    session_fingerprint=fingerprint,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    last_activity=datetime.now(timezone.utc),
                    expires_at=expires_at,
                    is_active=True,
                    user_agent=self._get_user_agent(),
                    ip_address=self._get_client_ip()
                )
                
                db_session.add(user_session)
                db_session.commit()
                
                # Create security audit event
                self._create_security_audit_event(
                    event_type='session_created',
                    user_id=user_id,
                    session_id=session_id,
                    details={
                        'platform_connection_id': platform_connection_id,
                        'fingerprint': fingerprint
                    }
                )
                
                # Log session creation
                if self.monitor:
                    self.monitor.log_database_session_created(session_id, user_id, platform_connection_id)
                
                logger.info(f"Created session {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))} with platform {sanitize_for_log(str(platform_connection_id))}")
                
                # Log to monitoring system
                if self.monitor:
                    self.monitor.log_database_session_created(session_id, user_id, platform_connection_id)
                
                return session_id
                
        except SessionValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Error creating user session: {sanitize_for_log(str(e))}")
            # If there's still a constraint error, try to handle it gracefully
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Session ID collision detected for user {user_id}, retrying with cleanup")
                try:
                    # Force cleanup and retry once
                    self.cleanup_user_sessions(user_id)
                    return self._create_session_retry(user_id, platform_connection_id)
                except Exception as retry_e:
                    logger.error(f"Failed to create session after retry: {sanitize_for_log(str(retry_e))}")
                    raise SessionDatabaseError(f"Failed to create session after retry: {retry_e}")
            raise SessionDatabaseError(f"Failed to create session: {e}")
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete session context from database
        
        Args:
            session_id: Session ID to look up
            
        Returns:
            Dictionary with session context or None if session not found/expired
        """
        if not session_id:
            logger.debug("get_session_context called with empty session_id")
            return None
        
        try:
            with self.get_db_session() as db_session:
                # Use eager loading to avoid DetachedInstanceError
                user_session = db_session.query(UserSession).options(
                    joinedload(UserSession.user),
                    joinedload(UserSession.active_platform)
                ).filter_by(session_id=session_id, is_active=True).first()
                
                if not user_session:
                    logger.debug(f"No active session found for session_id: {sanitize_for_log(session_id[:8])}...")
                    return None
                
                # Check if session is expired
                if user_session.is_expired():
                    logger.debug(f"Session expired for session_id: {sanitize_for_log(session_id)}")
                    # Mark session as inactive
                    user_session.is_active = False
                    db_session.commit()
                    
                    # Log to monitoring system
                    if self.monitor:
                        self.monitor.log_database_session_expired(session_id, user_session.user_id)
                    
                    return None
                
                # Update last activity
                user_session.last_activity = datetime.now(timezone.utc)
                user_session.updated_at = datetime.now(timezone.utc)
                db_session.commit()
                
                # Convert to context dictionary
                context = user_session.to_context_dict()
                
                logger.debug(f"Retrieved session context for session_id: {sanitize_for_log(session_id)}, platform_id: {sanitize_for_log(str(context.get('platform_connection_id')))}")
                return context
                
        except Exception as e:
            logger.error(f"Error getting session context for session_id {sanitize_for_log(session_id)}: {e}")
            return None
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate session exists and is not expired
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            if self.security_manager:
                # Use comprehensive security validation
                user_session = self.security_manager.validate_session_comprehensive(session_id)
                return user_session is not None
            else:
                # Fallback to basic validation
                context = self.get_session_context(session_id)
                return context is not None
        except (SessionValidationError, SessionExpiredError, SessionNotFoundError):
            return False
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Update last activity timestamp
        
        Args:
            session_id: Session ID to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id,
                    is_active=True
                ).first()
                
                if not user_session:
                    return False
                
                if user_session.is_expired():
                    # Mark as inactive if expired
                    user_session.is_active = False
                    db_session.commit()
                    return False
                
                user_session.last_activity = datetime.now(timezone.utc)
                user_session.updated_at = datetime.now(timezone.utc)
                db_session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False
    
    def update_platform_context(self, session_id: str, platform_connection_id: int) -> bool:
        """
        Update active platform for session
        
        Args:
            session_id: Session ID to update
            platform_connection_id: New platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id,
                    is_active=True
                ).first()
                
                if not user_session:
                    logger.warning(f"Session {sanitize_for_log(session_id[:8])}... not found for platform update")
                    return False
                
                # Check if session is expired
                if user_session.is_expired():
                    logger.warning(f"Cannot update expired session {sanitize_for_log(session_id[:8])}...")
                    user_session.is_active = False
                    db_session.commit()
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
                user_session.last_activity = datetime.now(timezone.utc)
                
                # Update platform's last used timestamp
                platform.last_used = datetime.now(timezone.utc)
                
                db_session.commit()
                
                # Create security audit event
                self._create_security_audit_event(
                    event_type='platform_switch',
                    user_id=user_session.user_id,
                    session_id=session_id,
                    details={
                        'platform_id': platform_connection_id,
                        'platform_name': platform.name
                    }
                )
                
                logger.info(f"Updated session {sanitize_for_log(session_id)} to use platform {sanitize_for_log(str(platform_connection_id))}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating platform context: {sanitize_for_log(str(e))}")
            return False
    
    def destroy_session(self, session_id: str) -> bool:
        """
        Remove session from database
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id
                ).first()
                
                if user_session:
                    user_id = user_session.user_id
                    db_session.delete(user_session)
                    db_session.commit()
                    
                    # Create security audit event
                    self._create_security_audit_event(
                        event_type='session_destroyed',
                        user_id=user_id,
                        session_id=session_id,
                        details={}
                    )
                    
                    # Log session destruction
                    if self.monitor:
                        self.monitor.log_database_session_destroyed(session_id, user_id, 'manual')
                    
                    logger.info(f"Destroyed session {sanitize_for_log(session_id)}")
                    
                    # Log to monitoring system
                    if self.monitor:
                        self.monitor.log_database_session_destroyed(session_id, user_id, 'manual_logout')
                    
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error destroying session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            with self.get_db_session() as db_session:
                # Find expired sessions
                now = datetime.now(timezone.utc)
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.expires_at < now
                ).all()
                
                count = len(expired_sessions)
                
                # Delete expired sessions
                for user_session in expired_sessions:
                    db_session.delete(user_session)
                
                db_session.commit()
                
                # Log cleanup
                if self.monitor and count > 0:
                    self.monitor.log_session_cleanup(count, 'expired')
                
                if count > 0:
                    logger.info(f"Cleaned up {count} expired sessions")
                    
                    # Log to monitoring system
                    if self.monitor:
                        self.monitor.log_database_session_cleanup(count, 'expired')
                
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {sanitize_for_log(str(e))}")
            return 0
    
    def cleanup_user_sessions(self, user_id: int, keep_current: Optional[str] = None) -> int:
        """
        Clean up all sessions for a user, optionally keeping the current one
        
        Args:
            user_id: User ID
            keep_current: Session ID to keep (optional)
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            with self.get_db_session() as db_session:
                query = db_session.query(UserSession).filter_by(user_id=user_id)
                
                if keep_current:
                    query = query.filter(UserSession.session_id != keep_current)
                
                sessions_to_delete = query.all()
                count = len(sessions_to_delete)
                
                for user_session in sessions_to_delete:
                    db_session.delete(user_session)
                
                db_session.commit()
                
                if count > 0:
                    logger.info(f"Cleaned up {count} sessions for user {sanitize_for_log(str(user_id))}")
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up user sessions: {sanitize_for_log(str(e))}")
            return 0
    
    def _create_session_retry(self, user_id: int, platform_connection_id: Optional[int] = None) -> str:
        """
        Internal method to retry session creation after cleanup
        
        Args:
            user_id: User ID
            platform_connection_id: Optional platform connection ID
        
        Returns:
            Session ID if successful
            
        Raises:
            SessionDatabaseError: If retry fails
        """
        session_id = str(uuid.uuid4())
        
        with self.get_db_session() as db_session:
            # Create session fingerprint
            fingerprint = self._create_session_fingerprint()
            
            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + self.session_timeout
            
            # Create new user session
            user_session = UserSession(
                user_id=user_id,
                session_id=session_id,
                active_platform_id=platform_connection_id,
                session_fingerprint=fingerprint,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                expires_at=expires_at,
                is_active=True,
                user_agent=self._get_user_agent(),
                ip_address=self._get_client_ip()
            )
            
            db_session.add(user_session)
            db_session.commit()
            
            # Create security audit event
            self._create_security_audit_event(
                event_type='session_created',
                user_id=user_id,
                session_id=session_id,
                details={
                    'platform_connection_id': platform_connection_id,
                    'fingerprint': fingerprint,
                    'retry': True
                }
            )
            
            return session_id
    
    def _create_session_fingerprint(self) -> Optional[str]:
        """Create session fingerprint for security"""
        try:
            if self.security_manager:
                return self.security_manager.create_session_fingerprint()
            elif self.security_hardening:
                return self.security_hardening.create_session_fingerprint()
        except Exception as e:
            logger.debug(f"Error creating session fingerprint: {e}")
        return None
    
    def _get_user_agent(self) -> Optional[str]:
        """Get user agent from request"""
        try:
            from flask import request
            return request.headers.get('User-Agent')
        except Exception:
            return None
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address from request"""
        try:
            from flask import request
            return request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        except Exception:
            return None
    
    def _create_security_audit_event(self, event_type: str, user_id: int, session_id: str, details: Dict[str, Any]):
        """Create security audit event"""
        try:
            if self.security_manager:
                self.security_manager.create_security_audit_event(event_type, session_id, user_id, details)
            elif self.security_hardening:
                self.security_hardening.create_security_audit_event(
                    session_id, user_id, event_type, details
                )
        except Exception as e:
            logger.debug(f"Error creating security audit event: {e}")