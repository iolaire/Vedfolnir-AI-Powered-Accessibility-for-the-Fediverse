# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Manager V2

Simplified, unified session manager that uses Redis as primary storage
with Flask session integration and database fallback for audit purposes.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from logging import getLogger

from flask import session, request, g
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from models import User, PlatformConnection, UserSession
from database import DatabaseManager
from redis_session_backend import RedisSessionBackend
from security.core.security_utils import sanitize_for_log

logger = getLogger(__name__)

class SessionError(Exception):
    """Base session error"""
    pass

class SessionNotFoundError(SessionError):
    """Session not found"""
    pass

class SessionExpiredError(SessionError):
    """Session expired"""
    pass

class SessionManagerV2:
    """
    Unified session manager using Redis with Flask session integration
    
    This manager provides:
    - Redis-backed Flask sessions
    - User authentication integration
    - Platform context management
    - Database audit trail
    - Session lifecycle management
    """
    
    def __init__(self, db_manager: DatabaseManager, redis_backend: RedisSessionBackend,
                 session_timeout: int = 7200):
        """
        Initialize session manager
        
        Args:
            db_manager: Database manager instance
            redis_backend: Redis backend instance
            session_timeout: Session timeout in seconds (default: 2 hours)
        """
        self.db_manager = db_manager
        self.redis_backend = redis_backend
        self.session_timeout = session_timeout
    
    def create_session(self, user_id: int, platform_connection_id: Optional[int] = None) -> str:
        """
        Create a new session for a user
        
        Args:
            user_id: User ID
            platform_connection_id: Optional platform connection ID
            
        Returns:
            Session ID
            
        Raises:
            SessionError: If session creation fails
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Get user information
            with self.db_manager.get_session() as db_session:
                user = db_session.query(User).options(
                    joinedload(User.platform_connections)
                ).filter_by(id=user_id, is_active=True).first()
                
                if not user:
                    raise SessionError(f"User {user_id} not found or inactive")
                
                # Get platform information if specified
                platform = None
                if platform_connection_id:
                    platform = db_session.query(PlatformConnection).filter_by(
                        id=platform_connection_id,
                        user_id=user_id,
                        is_active=True
                    ).first()
                    
                    if not platform:
                        logger.warning(f"Platform {platform_connection_id} not found for user {user_id}")
                        platform_connection_id = None
                
                # Create session data
                session_data = {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value if hasattr(user.role, 'value') else str(user.role),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'last_activity': datetime.now(timezone.utc).isoformat(),
                    'csrf_token': str(uuid.uuid4()),
                    'session_fingerprint': self._create_session_fingerprint()
                }
                
                # Add platform information if available
                if platform:
                    session_data.update({
                        'platform_connection_id': platform.id,
                        'platform_name': platform.name,
                        'platform_type': platform.platform_type.value if hasattr(platform.platform_type, 'value') else str(platform.platform_type),
                        'platform_instance_url': platform.instance_url
                    })
                
                # Store in Redis
                if not self.redis_backend.set(session_id, session_data, self.session_timeout):
                    raise SessionError("Failed to store session in Redis")
                
                # Create database audit record
                try:
                    db_session_record = UserSession(
                        session_id=session_id,
                        user_id=user.id,
                        active_platform_id=platform_connection_id,
                        created_at=datetime.now(timezone.utc),
                        last_activity=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.session_timeout),
                        is_active=True,
                        user_agent=request.headers.get('User-Agent', '') if request else '',
                        ip_address=request.remote_addr if request else ''
                    )
                    db_session.add(db_session_record)
                    db_session.commit()
                    
                except SQLAlchemyError as e:
                    logger.warning(f"Failed to create database session record: {e}")
                    # Don't fail session creation if database audit fails
                
                # Create security audit event
                self._create_security_audit_event(
                    'session_created',
                    user.id,
                    session_id,
                    {
                        'platform_connection_id': platform_connection_id,
                        'session_fingerprint': session_data.get('session_fingerprint')
                    }
                )
                
                logger.info(f"Created session {session_id} for user {sanitize_for_log(user.username)}")
                return session_id
                
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}")
            raise SessionError(f"Session creation failed: {e}")
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            data = self.redis_backend.get(session_id)
            if data:
                # Update last activity
                data['last_activity'] = datetime.now(timezone.utc).isoformat()
                self.redis_backend.set(session_id, data, self.session_timeout)
            return data
            
        except Exception as e:
            logger.error(f"Error getting session data for {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data
        
        Args:
            session_id: Session ID
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current session data
            session_data = self.redis_backend.get(session_id)
            if not session_data:
                return False
            
            # Apply updates
            session_data.update(updates)
            session_data['last_activity'] = datetime.now(timezone.utc).isoformat()
            
            # Save back to Redis
            return self.redis_backend.set(session_id, session_data, self.session_timeout)
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session
        
        Args:
            session_id: Session ID to destroy
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from Redis
            redis_success = self.redis_backend.delete(session_id)
            
            # Update database record
            try:
                with self.db_manager.get_session() as db_session:
                    db_session_record = db_session.query(UserSession).filter_by(session_id=session_id).first()
                    if db_session_record:
                        db_session_record.is_active = False
                        db_session_record.updated_at = datetime.now(timezone.utc)
                        db_session.commit()
                        
            except SQLAlchemyError as e:
                logger.warning(f"Failed to update database session record: {e}")
            
            logger.info(f"Destroyed session {session_id}")
            return redis_success
            
        except Exception as e:
            logger.error(f"Error destroying session {session_id}: {e}")
            return False
    
    def switch_platform(self, session_id: str, platform_connection_id: int) -> bool:
        """
        Switch platform for a session
        
        Args:
            session_id: Session ID
            platform_connection_id: New platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current session data
            session_data = self.redis_backend.get(session_id)
            if not session_data:
                return False
            
            user_id = session_data.get('user_id')
            if not user_id:
                return False
            
            # Get platform information
            with self.db_manager.get_session() as db_session:
                platform = db_session.query(PlatformConnection).filter_by(
                    id=platform_connection_id,
                    user_id=user_id,
                    is_active=True
                ).first()
                
                if not platform:
                    logger.warning(f"Platform {platform_connection_id} not found for user {user_id}")
                    return False
                
                # Update session data
                platform_updates = {
                    'platform_connection_id': platform.id,
                    'platform_name': platform.name,
                    'platform_type': platform.platform_type.value if hasattr(platform.platform_type, 'value') else str(platform.platform_type),
                    'platform_instance_url': platform.instance_url
                }
                
                success = self.update_session(session_id, platform_updates)
                
                if success:
                    # Update Flask session if this is the current session
                    if hasattr(g, 'session_id') and g.session_id == session_id:
                        session.update(platform_updates)
                    
                    logger.info(f"Switched session {session_id} to platform {sanitize_for_log(platform.name)}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error switching platform for session {session_id}: {e}")
            return False
    
    def cleanup_user_sessions(self, user_id: int, keep_current: bool = True) -> int:
        """
        Clean up all sessions for a user
        
        Args:
            user_id: User ID
            keep_current: Whether to keep the current session
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            current_session_id = getattr(g, 'session_id', None) if keep_current else None
            user_sessions = self.redis_backend.get_sessions_by_user(user_id)
            
            count = 0
            for session_id in user_sessions:
                if session_id != current_session_id:
                    if self.destroy_session(session_id):
                        count += 1
            
            logger.info(f"Cleaned up {count} sessions for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions for user {user_id}: {e}")
            return 0
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of session information dictionaries
        """
        try:
            session_ids = self.redis_backend.get_sessions_by_user(user_id)
            sessions = []
            
            for session_id in session_ids:
                session_data = self.redis_backend.get(session_id)
                if session_data:
                    # Get TTL
                    ttl = self.redis_backend.get_ttl(session_id)
                    
                    session_info = {
                        'session_id': session_id,
                        'created_at': session_data.get('created_at'),
                        'last_activity': session_data.get('last_activity'),
                        'platform_name': session_data.get('platform_name'),
                        'platform_type': session_data.get('platform_type'),
                        'ttl_seconds': ttl,
                        'is_current': session_id == getattr(g, 'session_id', None)
                    }
                    sessions.append(session_info)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate that a session exists and is active
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            return self.redis_backend.exists(session_id)
        except Exception as e:
            logger.error(f"Error validating session {session_id}: {e}")
            return False
    
    def extend_session(self, session_id: str, additional_seconds: int = None) -> bool:
        """
        Extend session timeout
        
        Args:
            session_id: Session ID
            additional_seconds: Additional seconds to add (default: reset to full timeout)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if additional_seconds is None:
                additional_seconds = self.session_timeout
            
            return self.redis_backend.update_ttl(session_id, additional_seconds)
            
        except Exception as e:
            logger.error(f"Error extending session {session_id}: {e}")
            return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics
        
        Returns:
            Dictionary with session statistics
        """
        try:
            total_sessions = self.redis_backend.get_session_count()
            
            # Get user distribution
            user_sessions = {}
            for session_id in self.redis_backend.get_all_sessions():
                session_data = self.redis_backend.get(session_id)
                if session_data:
                    user_id = session_data.get('user_id')
                    if user_id:
                        user_sessions[user_id] = user_sessions.get(user_id, 0) + 1
            
            return {
                'total_sessions': total_sessions,
                'unique_users': len(user_sessions),
                'avg_sessions_per_user': round(total_sessions / len(user_sessions), 2) if user_sessions else 0,
                'redis_health': self.redis_backend.health_check()
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                'total_sessions': 0,
                'unique_users': 0,
                'avg_sessions_per_user': 0,
                'error': str(e)
            }
    
    @contextmanager
    def get_db_session(self):
        """
        Context manager for database sessions (compatibility method)
        
        Yields:
            SQLAlchemy session object
        """
        with self.db_manager.get_session() as db_session:
            yield db_session
    
    # Security Methods (added for feature parity with UnifiedSessionManager)
    
    def _create_session_fingerprint(self) -> Optional[str]:
        """Create session fingerprint for security"""
        try:
            # Create a simple hash-based fingerprint using available request data
            import hashlib
            
            user_agent = self._get_user_agent() or ''
            client_ip = self._get_client_ip() or ''
            
            # Create fingerprint from user agent and IP
            fingerprint_data = f"{user_agent}:{client_ip}"
            fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            
            return fingerprint[:32]  # Return first 32 characters
            
        except Exception as e:
            logger.debug(f"Error creating session fingerprint: {e}")
            return None
    
    def _get_user_agent(self) -> Optional[str]:
        """Get user agent from request"""
        try:
            return request.headers.get('User-Agent')
        except Exception:
            return None
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address from request"""
        try:
            # Check for forwarded IP first (proxy/load balancer)
            forwarded_ip = request.environ.get('HTTP_X_FORWARDED_FOR')
            if forwarded_ip:
                # Take the first IP if multiple are present
                return forwarded_ip.split(',')[0].strip()
            
            # Fallback to direct connection IP
            return request.environ.get('REMOTE_ADDR')
        except Exception:
            return None
    
    def _create_security_audit_event(self, event_type: str, user_id: int, session_id: str, details: Dict[str, Any]):
        """Create security audit event"""
        try:
            # Log security event for audit purposes
            audit_data = {
                'event_type': event_type,
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'client_ip': self._get_client_ip(),
                'user_agent': self._get_user_agent(),
                'details': details
            }
            
            # Log to security audit log
            logger.info(f"Security audit event: {sanitize_for_log(audit_data)}")
            
            # Store in database for compliance (optional - could be implemented later)
            # This would integrate with a security audit service if available
            
        except Exception as e:
            logger.debug(f"Error creating security audit event: {e}")
