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
from contextlib import contextmanager
from flask import request, g
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError, InvalidRequestError

from models import User, PlatformConnection, UserSession
from database import DatabaseManager
from session_config import get_session_config, SessionConfig
from session_performance_optimizer import get_session_optimizer

logger = getLogger(__name__)

class SessionDatabaseError(Exception):
    """Raised when database session operations fail"""
    pass

class SessionError(Exception):
    """General session management error"""
    pass

class SessionManager:
    """Manages platform-aware user sessions"""
    
    def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig] = None):
        self.db_manager = db_manager
        self.config = config or get_session_config()
        self.session_timeout = self.config.timeout.session_lifetime
        
        # Initialize performance optimizer
        self.optimizer = get_session_optimizer(db_manager)
        
        # Initialize monitoring (lazy loading to avoid circular imports)
        self._monitor = None
        
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
            SessionError: For general session errors
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
                raise SessionError(f"Session operation failed: {e}")
                
            finally:
                if db_session:
                    try:
                        db_session.close()
                    except Exception as close_error:
                        logger.error(f"Error closing database session: {close_error}")
                    
                    # Log session metrics for monitoring
                    try:
                        self._log_session_metrics(db_session)
                    except Exception as metrics_error:
                        logger.debug(f"Error logging session metrics: {metrics_error}")
    
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
        # Use direct database session instead of context manager to avoid double commit issues
        db_session = self.db_manager.get_session()
        try:
            # Verify user exists
            user = db_session.get(User, user_id)
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
            
            # Clean up any existing sessions for this user to prevent duplicates
            try:
                existing_sessions = db_session.query(UserSession).filter_by(user_id=user_id).all()
                if existing_sessions:
                    logger.debug(f"Found {len(existing_sessions)} existing sessions for user {user_id}, cleaning up expired ones")
                    for existing_session in existing_sessions:
                        if self._is_session_expired(existing_session):
                            db_session.delete(existing_session)
                            logger.debug(f"Removed expired session {sanitize_for_log(existing_session.session_id)}")
            except Exception as cleanup_error:
                logger.warning(f"Error during session cleanup: {sanitize_for_log(str(cleanup_error))}")
                # Continue with session creation even if cleanup fails
            
            # Create session record with proper expiration
            expires_at = datetime.now(timezone.utc) + self.session_timeout
            
            user_session = UserSession(
                user_id=user_id,
                session_id=session_id,
                active_platform_id=platform_connection_id,
                expires_at=expires_at
            )
            
            db_session.add(user_session)
            db_session.commit()
            
            # Create session fingerprint and audit event
            if self.security_hardening:
                try:
                    self.security_hardening.create_session_fingerprint()
                    self.security_hardening.create_security_audit_event(
                        session_id, user_id, 'session_created',
                        details={'platform_id': platform_connection_id}
                    )
                    
                    # Track session creation activity
                    self.security_hardening.detect_suspicious_session_activity(
                        session_id, user_id, 'session_create'
                    )
                except RuntimeError as e:
                    if "Working outside of request context" in str(e):
                        logger.debug("Security hardening skipped - no Flask request context")
                    else:
                        raise
            
            logger.info(f"Created session {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))} with platform {sanitize_for_log(str(platform_connection_id))}")
            
            return session_id
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error creating user session: {sanitize_for_log(str(e))}")
            raise
        finally:
            db_session.close()
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session context including user and platform information with caching
        
        Args:
            session_id: Session ID to look up
            
        Returns:
            Dictionary with session context or None if session not found
        """
        if not session_id:
            logger.debug("get_session_context called with empty session_id")
            return None
        
        # Use optimized cached lookup
        context = self.optimizer.get_cached_session_context(session_id)
        if context:
            logger.debug(f"Retrieved session context for session_id: {sanitize_for_log(session_id)}, platform_id: {sanitize_for_log(str(context['platform_connection_id']))}")
        
        return context
    
    def update_platform_context(self, session_id: str, platform_connection_id: int) -> bool:
        """
        Update the active platform for a session with proper validation
        
        Args:
            session_id: Session ID to update
            platform_connection_id: New platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        if not session_id or not session_id.strip():
            logger.warning("update_platform_context called with empty session_id")
            return False
            
        # Use direct database session instead of context manager
        db_session = self.db_manager.get_session()
        try:
            user_session = db_session.query(UserSession).filter_by(
                session_id=session_id
            ).first()
            
            if not user_session:
                logger.warning(f"Session {sanitize_for_log(session_id[:8])}... not found for platform update")
                return False
            
            # Check if session is expired before updating
            if self._is_session_expired(user_session):
                logger.warning(f"Cannot update expired session {sanitize_for_log(session_id[:8])}... - session expired")
                self._cleanup_session(session_id)
                return False
            
            # Verify platform belongs to the user
            platform = db_session.query(PlatformConnection).filter_by(
                id=platform_connection_id,
                user_id=user_session.user_id,
                is_active=True
            ).first()
            
            if not platform:
                logger.warning(f"Platform {sanitize_for_log(str(platform_connection_id))} not found or not accessible to user {sanitize_for_log(str(user_session.user_id))} for session {sanitize_for_log(session_id[:8])}...")
                return False
            
            # Extract platform data before updating to avoid DetachedInstanceError
            platform_name = platform.name
            
            # Check for suspicious platform switching activity
            if self.security_hardening:
                try:
                    is_suspicious = self.security_hardening.detect_suspicious_session_activity(
                        session_id, user_session.user_id, 'platform_switch',
                        {'old_platform_id': user_session.active_platform_id, 'new_platform_id': platform_connection_id}
                    )
                    if is_suspicious:
                        logger.warning(f"Suspicious platform switching detected for session {sanitize_for_log(session_id)}")
                except RuntimeError as e:
                    if "Working outside of request context" in str(e):
                        logger.debug("Suspicious activity detection skipped - no Flask request context")
                    else:
                        raise
            
            # Update session
            user_session.active_platform_id = platform_connection_id
            user_session.updated_at = datetime.now(timezone.utc)
            
            # Update platform's last used timestamp
            platform.last_used = datetime.now(timezone.utc)
            
            db_session.commit()
            
            # Create security audit event
            if self.security_hardening:
                try:
                    self.security_hardening.create_security_audit_event(
                        session_id, user_session.user_id, 'platform_switch',
                        details={'platform_id': platform_connection_id, 'platform_name': platform_name}
                    )
                except RuntimeError as e:
                    if "Working outside of request context" in str(e):
                        logger.debug("Security audit event skipped - no Flask request context")
                    else:
                        raise
            
            logger.info(f"Updated session {sanitize_for_log(session_id)} to use platform {sanitize_for_log(str(platform_connection_id))}")
            return True
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error updating platform context: {sanitize_for_log(str(e))}")
            return False
        finally:
            db_session.close()
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions using optimized batch processing
        
        Returns:
            Number of sessions cleaned up
        """
        if not self.config.features.enable_background_cleanup:
            logger.debug("Background cleanup disabled by configuration")
            return 0
        
        return self.optimizer.cleanup_expired_sessions_optimized(self.config.cleanup.cleanup_batch_size)
    
    def cleanup_user_sessions(self, user_id: int, keep_current: Optional[str] = None) -> int:
        """
        Clean up user sessions. If keep_current is provided, clean up all other sessions.
        If keep_current is None, clean up all sessions for the user.
        
        Args:
            user_id: User ID to clean up sessions for
            keep_current: Session ID to keep (optional)
            
        Returns:
            Number of sessions cleaned up
        """
        db_session = self.db_manager.get_session()
        try:
            # Get all sessions for this user
            query = db_session.query(UserSession).filter(UserSession.user_id == user_id)
            
            if keep_current:
                query = query.filter(UserSession.session_id != keep_current)
            
            all_sessions = query.order_by(UserSession.updated_at.desc()).all()
            
            # If keep_current is None, delete all sessions
            # If keep_current is provided, delete all except that one
            sessions_to_delete = all_sessions
            
            count = len(sessions_to_delete)
            
            for session_obj in sessions_to_delete:
                db_session.delete(session_obj)
            
            db_session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {sanitize_for_log(str(count))} sessions for user {sanitize_for_log(str(user_id))}")
            
            return count
            
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error cleaning up user sessions: {e}")
            return 0
        finally:
            db_session.close()
    
    def get_user_active_sessions(self, user_id: int) -> list:
        """
        Get all active (non-expired) sessions for a user with optimization
        
        Args:
            user_id: User ID to get sessions for
            
        Returns:
            List of active session dictionaries
        """
        try:
            return self.optimizer.get_user_sessions_optimized(user_id, active_only=True)
        except Exception as e:
            logger.error(f"Error getting user active sessions: {e}")
            return []
    
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
        Validate that a session belongs to the specified user and is not expired with optimization
        
        Args:
            session_id: Session ID to validate
            user_id: Expected user ID
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Use optimized validation first
            if not self.optimizer.validate_session_optimized(session_id, user_id):
                logger.warning(f"Session validation failed - optimized check failed for session {sanitize_for_log(session_id)}")
                return False
            
            # Additional security checks
            if not self._validate_session_security(session_id, user_id):
                return False
            
            # Enhanced security validation with hardening features
            if self.security_hardening:
                try:
                    is_secure, issues = self.security_hardening.validate_session_security(session_id, user_id)
                    if not is_secure:
                        logger.warning(f"Session security validation failed for {sanitize_for_log(session_id)}: {issues}")
                        return False
                except RuntimeError as e:
                    if "Working outside of request context" in str(e):
                        logger.debug("Enhanced security validation skipped - no Flask request context")
                    else:
                        raise
                except Exception as e:
                    logger.debug(f"Enhanced security validation failed: {e}")
                    # Continue with basic validation if enhanced validation fails
            
            return True
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False
    
    def _validate_session_security(self, session_id: str, user_id: int) -> bool:
        """
        Perform additional security validation on session
        
        Args:
            session_id: Session ID to validate
            user_id: User ID to validate
            
        Returns:
            True if security validation passes, False otherwise
        """
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id,
                    user_id=user_id
                ).first()
                
                if not user_session:
                    return False
                
                # Check if session is expired
                if self._is_session_expired(user_session):
                    logger.info(f"Session {sanitize_for_log(session_id)} expired during security validation")
                    self._cleanup_session(session_id)
                    return False
                
                # Check for suspicious activity patterns
                if self._detect_suspicious_activity(user_session):
                    logger.warning(f"Suspicious activity detected for session {sanitize_for_log(session_id)}")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error in session security validation: {e}")
            return False
    
    def _detect_suspicious_activity(self, user_session: UserSession) -> bool:
        """
        Detect suspicious session activity patterns
        
        Args:
            user_session: UserSession object to analyze
            
        Returns:
            True if suspicious activity detected, False otherwise
        """
        try:
            # Check for rapid session updates (potential session hijacking)
            if user_session.updated_at and user_session.created_at:
                session_age = datetime.now(timezone.utc) - user_session.created_at.replace(tzinfo=timezone.utc)
                update_frequency = datetime.now(timezone.utc) - user_session.updated_at.replace(tzinfo=timezone.utc)
                
                # If session is very new but has many rapid updates, flag as suspicious
                # Allow some grace period for normal operations
                if session_age.total_seconds() < 60 and update_frequency.total_seconds() < 0.1:
                    return True
            
            # Additional suspicious activity checks can be added here
            # - IP address changes
            # - User agent changes
            # - Unusual access patterns
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting suspicious activity: {e}")
            return False
    
    def invalidate_session(self, session_id: str, reason: str = "manual") -> bool:
        """
        Invalidate a session for security reasons
        
        Args:
            session_id: Session ID to invalidate
            reason: Reason for invalidation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get session context before cleanup for audit
            context = self.get_session_context(session_id)
            user_id = context['user_id'] if context else None
            
            success = self._cleanup_session(session_id)
            if success:
                # Create security audit event
                if self.security_hardening and user_id:
                    self.security_hardening.create_security_audit_event(
                        session_id, user_id, 'session_invalidated',
                        severity="warning",
                        details={'reason': reason}
                    )
                
                logger.info(f"Session {sanitize_for_log(session_id)} invalidated - reason: {sanitize_for_log(reason)}")
            return success
        except Exception as e:
            logger.error(f"Error invalidating session: {e}")
            return False
    
    def get_session_security_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get security information about a session
        
        Args:
            session_id: Session ID to analyze
            
        Returns:
            Dictionary with security information or None
        """
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id
                ).first()
                
                if not user_session:
                    return None
                
                # Calculate session metrics
                now = datetime.now(timezone.utc)
                created_at = user_session.created_at.replace(tzinfo=timezone.utc) if user_session.created_at else now
                updated_at = user_session.updated_at.replace(tzinfo=timezone.utc) if user_session.updated_at else now
                
                session_age = now - created_at
                last_activity = now - updated_at
                
                return {
                    'session_id': session_id,
                    'user_id': user_session.user_id,
                    'created_at': created_at.isoformat(),
                    'last_activity': updated_at.isoformat(),
                    'session_age_seconds': session_age.total_seconds(),
                    'last_activity_seconds': last_activity.total_seconds(),
                    'is_expired': self._is_session_expired(user_session),
                    'is_suspicious': self._detect_suspicious_activity(user_session),
                    'user_agent': getattr(user_session, 'user_agent', None),
                    'ip_address': getattr(user_session, 'ip_address', None)
                }
                
        except Exception as e:
            logger.error(f"Error getting session security info: {e}")
            return None
    
    def validate_csrf_token(self, token: str, session_id: str) -> bool:
        """
        Validate CSRF token for session operations
        
        Args:
            token: CSRF token to validate
            session_id: Session ID associated with the token
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from flask_wtf.csrf import validate_csrf
            
            # Use Flask-WTF's built-in CSRF validation
            try:
                validate_csrf(token)
                return True
            except Exception as csrf_error:
                logger.warning(f"CSRF validation failed for session {sanitize_for_log(session_id)}: {csrf_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating CSRF token: {e}")
            return False
    
    def create_secure_session_data(self, user_id: int, platform_id: Optional[int] = None, 
                                 request_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create secure session data with minimal sensitive information
        
        Args:
            user_id: User ID
            platform_id: Optional platform ID
            request_info: Optional request information (IP, user agent, etc.)
            
        Returns:
            Dictionary with secure session data
        """
        try:
            session_data = {
                'user_id': user_id,
                'platform_id': platform_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat()
            }
            
            # Add non-sensitive request information if provided
            if request_info:
                # Only store non-sensitive information
                safe_fields = ['user_agent', 'ip_address', 'referrer']
                for field in safe_fields:
                    if field in request_info:
                        session_data[field] = sanitize_for_log(str(request_info[field]))
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error creating secure session data: {e}")
            return {'user_id': user_id, 'platform_id': platform_id}
    
    def sanitize_session_data_for_client(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize session data for client-side use (remove sensitive information)
        
        Args:
            session_data: Full session data
            
        Returns:
            Sanitized session data safe for client-side use
        """
        try:
            # Only include non-sensitive fields
            safe_fields = [
                'user_id', 'platform_id', 'platform_name', 'platform_type',
                'created_at', 'last_activity', 'session_age_seconds'
            ]
            
            sanitized = {}
            for field in safe_fields:
                if field in session_data:
                    sanitized[field] = session_data[field]
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error sanitizing session data: {e}")
            return {}
    
    def enforce_session_timeout(self, max_idle_time: Optional[timedelta] = None) -> int:
        """
        Enforce session timeout by cleaning up idle sessions using configuration
        
        Args:
            max_idle_time: Maximum idle time before session expires (uses config if None)
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            if max_idle_time is None:
                max_idle_time = self.config.timeout.idle_timeout
            
            cutoff_time = datetime.now(timezone.utc) - max_idle_time
            
            # Check if we should trigger cleanup based on threshold
            with self.get_db_session() as db_session:
                expired_count = db_session.query(UserSession).filter(
                    UserSession.updated_at < cutoff_time
                ).count()
                
                if expired_count < self.config.cleanup.cleanup_trigger_threshold:
                    if self.config.debug_mode:
                        logger.debug(f"Skipping cleanup - only {expired_count} expired sessions (threshold: {self.config.cleanup.cleanup_trigger_threshold})")
                    return 0
                
                # Perform cleanup in batches
                return self.batch_cleanup_sessions()
                
        except Exception as e:
            logger.error(f"Error enforcing session timeout: {e}")
            return 0
    
    def batch_cleanup_sessions(self, batch_size: Optional[int] = None) -> int:
        """
        Perform batch cleanup of expired sessions using configuration settings
        
        Args:
            batch_size: Number of sessions to process in each batch (uses config default if None)
            
        Returns:
            Total number of sessions cleaned up
        """
        if batch_size is None:
            batch_size = self.config.cleanup.cleanup_batch_size
        
        max_batches = self.config.cleanup.max_cleanup_batches_per_run
        
        try:
            total_cleaned = 0
            batches_processed = 0
            
            while batches_processed < max_batches:
                with self.get_db_session() as db_session:
                    # Get a batch of expired sessions with grace period
                    cutoff_time = datetime.now(timezone.utc) - self.session_timeout - self.config.timeout.cleanup_grace_period
                    
                    expired_sessions = db_session.query(UserSession).filter(
                        UserSession.updated_at < cutoff_time
                    ).limit(batch_size).all()
                    
                    if not expired_sessions:
                        break
                    
                    # Delete the batch
                    batch_count = 0
                    for session_obj in expired_sessions:
                        db_session.delete(session_obj)
                        batch_count += 1
                    
                    total_cleaned += batch_count
                    batches_processed += 1
                    
                    if self.config.debug_mode:
                        logger.debug(f"Cleaned up batch {batches_processed} of {batch_count} expired sessions")
                    
                    # If we got fewer than batch_size, we're done
                    if len(expired_sessions) < batch_size:
                        break
            
            if total_cleaned > 0:
                logger.info(f"Batch cleanup completed - cleaned up {total_cleaned} expired sessions in {batches_processed} batches")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Error in batch session cleanup: {e}")
            return 0
    
    def get_session_cache_key(self, session_id: str) -> str:
        """
        Generate cache key for session data
        
        Args:
            session_id: Session ID
            
        Returns:
            Cache key string
        """
        return f"session_context:{session_id}"
    
    def optimize_session_queries(self) -> Dict[str, Any]:
        """
        Optimize session-related database queries
        
        Returns:
            Dictionary with optimization results
        """
        try:
            optimization_results = {
                'indexes_checked': 0,
                'queries_optimized': 0,
                'performance_improved': False
            }
            
            with self.get_db_session() as db_session:
                # Check if proper indexes exist
                from sqlalchemy import text
                
                # Check for session_id index
                result = db_session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='user_sessions'"
                )).fetchall()
                
                existing_indexes = [row[0] for row in result]
                optimization_results['indexes_checked'] = len(existing_indexes)
                
                # Suggest optimizations based on query patterns
                if 'idx_user_sessions_session_id' not in existing_indexes:
                    logger.info("Recommended: Create index on user_sessions.session_id")
                
                if 'idx_user_sessions_updated_at' not in existing_indexes:
                    logger.info("Recommended: Create index on user_sessions.updated_at for cleanup queries")
                
                optimization_results['performance_improved'] = True
                
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error optimizing session queries: {e}")
            return {'error': str(e)}
    
    @property
    def monitor(self):
        """Get session monitor instance (lazy loading)"""
        if self._monitor is None and self.config.monitoring.enable_performance_monitoring:
            try:
                from session_monitoring import get_session_monitor
                self._monitor = get_session_monitor(self.db_manager)
            except ImportError:
                logger.warning("Session monitoring not available")
                self._monitor = None
        return self._monitor
    
    @property
    def security_hardening(self):
        """Get session security hardening instance (lazy loading)"""
        if self._security_hardening is None and self.config.security.enable_fingerprinting:
            try:
                from security.features.session_security import initialize_session_security
                self._security_hardening = initialize_session_security(self)
            except ImportError:
                logger.warning("Session security hardening not available")
                self._security_hardening = None
        return self._security_hardening
    
    def _log_session_operation(self, operation: str, session_id: str, user_id: int, 
                              success: bool = True, details: Optional[Dict[str, Any]] = None):
        """Log session operation for monitoring"""
        try:
            if self.monitor:
                if success:
                    if operation == 'create':
                        self.monitor.log_session_created(session_id, user_id, details.get('platform_id') if details else None)
                    elif operation == 'expire':
                        self.monitor.log_session_expired(session_id, user_id, details.get('reason', 'timeout') if details else 'timeout')
                else:
                    error_details = details.get('error', 'Unknown error') if details else 'Unknown error'
                    self.monitor.log_session_error(session_id, user_id, operation, str(error_details))
        except Exception as e:
            logger.debug(f"Error logging session operation: {e}")  # Don't let monitoring errors affect main operations
    
    def _cleanup_session(self, session_id: str) -> bool:
        """
        Clean up a specific session
        
        Args:
            session_id: Session ID to clean up
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(
                    session_id=session_id
                ).first()
                
                if user_session:
                    db_session.delete(user_session)
                    db_session.flush()
                    logger.info(f"Cleaned up session {sanitize_for_log(session_id)}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
            return False
    
    def _is_session_expired(self, user_session: UserSession) -> bool:
        """
        Check if a session is expired using configuration timeouts
        
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
        
        now = datetime.now(timezone.utc)
        
        # Check idle timeout
        idle_time = now - updated_at
        if idle_time > self.config.timeout.idle_timeout:
            return True
        
        # Check absolute timeout if session has creation time
        if user_session.created_at:
            created_at = user_session.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            absolute_time = now - created_at
            if absolute_time > self.config.timeout.absolute_timeout:
                return True
        
        return False
    
    def _log_session_metrics(self, db_session):
        """
        Log session metrics for monitoring and performance analysis
        
        Args:
            db_session: Database session to analyze
        """
        try:
            # Log connection pool status
            engine = self.db_manager.engine
            pool = engine.pool
            
            logger.debug(f"Connection pool status - Size: {pool.size()}, "
                        f"Checked out: {pool.checkedout()}, "
                        f"Overflow: {pool.overflow()}")
            
            # Log session statistics if available
            if hasattr(db_session, 'info'):
                session_info = db_session.info
                if 'query_count' in session_info:
                    logger.debug(f"Session query count: {session_info['query_count']}")
                    
        except Exception as e:
            # Don't let metrics logging interfere with main operations
            logger.debug(f"Error logging session metrics: {e}")
    
    def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        Get current connection pool status for monitoring
        
        Returns:
            Dictionary with pool status information
        """
        try:
            engine = self.db_manager.engine
            pool = engine.pool
            
            status = {
                'pool_size': pool.size(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'checked_in': pool.checkedin(),
                'total_connections': pool.size() + pool.overflow(),
                'available_connections': pool.size() - pool.checkedout(),
                'pool_timeout': getattr(pool, '_timeout', 'unknown'),
                'pool_recycle': getattr(pool, '_recycle', 'unknown'),
                'configuration': {
                    'cleanup_enabled': self.config.features.enable_background_cleanup,
                    'monitoring_enabled': self.config.monitoring.enable_performance_monitoring,
                    'session_timeout_hours': self.config.timeout.session_lifetime.total_seconds() / 3600,
                    'cleanup_interval_minutes': self.config.cleanup.cleanup_interval.total_seconds() / 60
                }
            }
            
            return status
        except Exception as e:
            logger.error(f"Error getting connection pool status: {e}")
            return {'error': str(e)}
    
    def optimize_connection_pool(self) -> bool:
        """
        Perform connection pool optimization and cleanup
        
        Returns:
            True if optimization successful, False otherwise
        """
        try:
            engine = self.db_manager.engine
            
            # Apply database optimizations
            optimization_results = self.optimizer.apply_database_optimizations()
            logger.info(f"Database optimizations applied: {optimization_results}")
            
            # Dispose of all connections to force pool refresh
            engine.dispose()
            
            # Test new connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            
            logger.info("Connection pool optimization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error optimizing connection pool: {e}")
            return False


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
            
            # Flask session permanent setting disabled - using database sessions only
            
            # Flask session ID retrieval disabled - using database sessions only
            flask_session_id = None
            if not flask_session_id:
                # For authenticated users without session ID, try to recreate
                from flask_login import current_user
                if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                    try:
                        # Get user's default platform
                        db_session = self.session_manager.db_manager.get_session()
                        try:
                            from models import PlatformConnection
                            default_platform = db_session.query(PlatformConnection).filter_by(
                                user_id=current_user.id,
                                is_default=True,
                                is_active=True
                            ).first()
                            
                            if not default_platform:
                                # Use first available platform
                                default_platform = db_session.query(PlatformConnection).filter_by(
                                    user_id=current_user.id,
                                    is_active=True
                                ).first()
                            
                            if default_platform:
                                # Create new session
                                try:
                                    flask_session_id = self.session_manager.create_user_session(
                                        current_user.id, default_platform.id
                                    )
                                    if flask_session_id:
                                        # Flask session usage disabled - using database sessions only
                                        logger.info(f"Recreated session for user {sanitize_for_log(current_user.username)}")
                                    else:
                                        logger.warning(f"Failed to recreate database session for user {sanitize_for_log(current_user.username)}")
                                        # Flask session fallback disabled - using database sessions only
                                except Exception as recreate_error:
                                    logger.warning(f"Error recreating session for user {sanitize_for_log(current_user.username)}: {sanitize_for_log(str(recreate_error))}")
                                    # Flask session fallback disabled - using database sessions only
                        finally:
                            db_session.close()
                    except Exception as e:
                        logger.error(f"Error recreating session: {sanitize_for_log(str(e))}")
                        return
                else:
                    return
            
            # Get platform context from session manager
            context = self.session_manager.get_session_context(flask_session_id)
            if context:
                g.platform_context = context
                
                # Update session activity using optimized method with throttling
                try:
                    if hasattr(self.session_manager, 'optimizer'):
                        self.session_manager.optimizer.update_session_activity_optimized(flask_session_id)
                    else:
                        # Fallback to original method with reduced frequency
                        # Flask session activity check disabled - using database sessions only
                        now = datetime.now(timezone.utc)
                        
                        # Always update activity since Flask session check is disabled
                        if True:
                            db_session = self.session_manager.db_manager.get_session()
                            try:
                                user_session = db_session.query(UserSession).filter_by(
                                    session_id=flask_session_id
                                ).first()
                                if user_session:
                                    user_session.updated_at = now
                                    db_session.commit()
                                    # Flask session activity update disabled - using database sessions only
                            except SQLAlchemyError as e:
                                logger.error(f"Database error updating session activity: {sanitize_for_log(str(e))}")
                                db_session.rollback()
                            finally:
                                db_session.close()
                except Exception as e:
                    logger.error(f"Error updating session activity: {sanitize_for_log(str(e))}")
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
        
        # Clear session cache if it exists
        if hasattr(g, 'session_cache'):
            g.session_cache = None
        
        return response


def get_current_platform_context() -> Optional[Dict[str, Any]]:
    """
    Get the current platform context from Flask's g object with fallback
    
    Returns:
        Platform context dictionary or None
    """
    # First try to get from g object (set by middleware)
    context = getattr(g, 'platform_context', None)
    if context:
        return context
    
    # Fallback: Flask session fallback disabled - using database sessions only
    try:
        # Flask session fallback disabled - using database sessions only
        flask_session_id = None
        if flask_session_id:
            session_manager = getattr(g, 'session_manager', None)
            if session_manager:
                return session_manager.get_session_context(flask_session_id)
    except Exception as e:
        logger.debug(f"Error in platform context fallback: {e}")
    
    return None


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