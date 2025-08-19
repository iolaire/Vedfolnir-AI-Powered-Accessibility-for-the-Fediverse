# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Session Management System

This module provides session management using Redis as the backend storage,
eliminating database locking issues and providing better performance.
"""

import json
import uuid
import redis
from logging import getLogger
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from models import User, PlatformConnection
from database import DatabaseManager
from session_config import get_session_config, SessionConfig

logger = getLogger(__name__)

class RedisSessionError(Exception):
    """Raised when Redis session operations fail"""
    pass

class SessionValidationError(Exception):
    """Raised when session validation fails"""
    pass

class SessionExpiredError(SessionValidationError):
    """Raised when session has expired"""
    pass

class SessionNotFoundError(SessionValidationError):
    """Raised when session doesn't exist"""
    pass

class RedisSessionManager:
    """Session manager using Redis as backend storage"""
    
    def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig] = None, 
                 redis_host: str = 'localhost', redis_port: int = 6379, redis_db: int = 0,
                 redis_password: Optional[str] = None, redis_ssl: bool = False,
                 security_manager=None, monitor=None):
        """
        Initialize Redis session manager
        
        Args:
            db_manager: Database manager for user/platform lookups
            config: Session configuration
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            redis_password: Redis password
            redis_ssl: Whether to use SSL
            security_manager: Security manager instance
            monitor: Session monitor instance
        """
        self.db_manager = db_manager
        self.config = config or get_session_config()
        self.security_manager = security_manager
        self.monitor = monitor
        
        # Handle session_lifetime whether it's seconds (int) or timedelta object
        if isinstance(self.config.timeout.session_lifetime, timedelta):
            self.session_timeout = self.config.timeout.session_lifetime
        else:
            self.session_timeout = timedelta(seconds=self.config.timeout.session_lifetime)
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                ssl=redis_ssl,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test Redis connection
            # self.redis_client.ping()
            # logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise RedisSessionError(f"Redis connection failed: {e}")
        
        # Session key prefixes
        self.session_prefix = "vedfolnir:session:"
        self.user_sessions_prefix = "vedfolnir:user_sessions:"
        self.session_index_prefix = "vedfolnir:session_index:"
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session data"""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_sessions_key(self, user_id: int) -> str:
        """Get Redis key for user's session list"""
        return f"{self.user_sessions_prefix}{user_id}"
    
    def _get_session_index_key(self) -> str:
        """Get Redis key for session index"""
        return f"{self.session_index_prefix}all"
    
    def create_session(self, user_id: int, platform_connection_id: Optional[int] = None) -> str:
        """
        Create new Redis session and return session ID
        
        Args:
            user_id: ID of the user
            platform_connection_id: Optional platform connection ID
            
        Returns:
            Session ID string
            
        Raises:
            SessionValidationError: If user or platform is invalid
            RedisSessionError: If Redis operation fails
        """
        session_id = str(uuid.uuid4())
        
        try:
            # Verify user exists and is active using database
            with self.db_manager.get_session() as db_session:
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
            
            # Create session data (Redis doesn't handle None values, so convert to empty strings)
            session_data = {
                'session_id': session_id,
                'user_id': str(user_id),
                'active_platform_id': str(platform_connection_id) if platform_connection_id else '',
                'session_fingerprint': fingerprint or '',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'expires_at': expires_at.isoformat(),
                'is_active': 'true',
                'user_agent': self._get_user_agent() or '',
                'ip_address': self._get_client_ip() or ''
            }
            
            # Store session in Redis with expiration
            session_key = self._get_session_key(session_id)
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_index_key = self._get_session_index_key()
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Store session data
            pipe.hset(session_key, mapping=session_data)
            pipe.expire(session_key, int(self.session_timeout.total_seconds()))
            
            # Add to user's session list
            pipe.sadd(user_sessions_key, session_id)
            pipe.expire(user_sessions_key, int(self.session_timeout.total_seconds()))
            
            # Add to global session index
            pipe.sadd(session_index_key, session_id)
            
            # Execute all operations
            pipe.execute()
            
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
            
            # logger.info(f"Created Redis session {session_id} for user {user_id} with platform {platform_connection_id}")
            
            # Log to monitoring system
            if self.monitor:
                self.monitor.log_database_session_created(session_id, user_id, platform_connection_id)
            
            return session_id
            
        except SessionValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Error creating Redis session: {e}")
            raise RedisSessionError(f"Failed to create session: {e}")
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete session context from Redis
        
        Args:
            session_id: Session ID to look up
            
        Returns:
            Dictionary with session context or None if session not found/expired
        """
        if not session_id:
            logger.debug("get_session_context called with empty session_id")
            return None
        
        try:
            session_key = self._get_session_key(session_id)
            
            # Get session data from Redis
            session_data = self.redis_client.hgetall(session_key)
            
            if not session_data:
                logger.debug(f"No session found for session_id: {session_id[:8]}...")
                return None
            
            # Check if session is expired
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if expires_at < datetime.now(timezone.utc):
                logger.debug(f"Session expired for session_id: {session_id}")
                # Clean up expired session
                self._cleanup_session(session_id, session_data.get('user_id'))
                return None
            
            # Update last activity
            now = datetime.now(timezone.utc)
            pipe = self.redis_client.pipeline()
            pipe.hset(session_key, 'last_activity', now.isoformat())
            pipe.hset(session_key, 'updated_at', now.isoformat())
            pipe.execute()
            
            # Convert session data to context format
            context = {
                'session_id': session_data['session_id'],
                'user_id': int(session_data['user_id']),
                'platform_connection_id': int(session_data['active_platform_id']) if session_data.get('active_platform_id') and session_data['active_platform_id'] != '' else None,
                'created_at': session_data['created_at'],
                'last_activity': now.isoformat(),
                'expires_at': session_data['expires_at'],
                'is_active': session_data.get('is_active', 'true').lower() == 'true'
            }
            
            logger.debug(f"Retrieved session context for session_id: {session_id}, platform_id: {context.get('platform_connection_id')}")
            return context
            
        except Exception as e:
            logger.error(f"Error getting session context for session_id {session_id}: {e}")
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
                # Use comprehensive security validation if available
                # Note: This would need to be adapted for Redis
                pass
            
            # Fallback to basic validation
            context = self.get_session_context(session_id)
            return context is not None
            
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
            session_key = self._get_session_key(session_id)
            
            # Check if session exists
            if not self.redis_client.exists(session_key):
                return False
            
            # Update activity timestamp
            now = datetime.now(timezone.utc)
            pipe = self.redis_client.pipeline()
            pipe.hset(session_key, 'last_activity', now.isoformat())
            pipe.hset(session_key, 'updated_at', now.isoformat())
            pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False
    
    def update_platform_context(self, session_id: str, platform_connection_id: int) -> bool:
        """
        Update active platform for session using Redis platform management
        
        Args:
            session_id: Session ID to update
            platform_connection_id: New platform connection ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_key = self._get_session_key(session_id)
            
            # Get current session data
            session_data = self.redis_client.hgetall(session_key)
            if not session_data:
                logger.warning(f"Session {session_id[:8]}... not found for platform update")
                return False
            
            user_id = int(session_data['user_id'])
            
            # Verify platform belongs to the user using Redis platform manager
            # Import here to avoid circular imports
            from redis_platform_manager import get_redis_platform_manager
            import os
            
            encryption_key = os.getenv('PLATFORM_ENCRYPTION_KEY', 'default-key-change-in-production')
            redis_platform_manager = get_redis_platform_manager(
                self.redis_client,
                self.db_manager,
                encryption_key
            )
            
            # Get platform data from Redis (with database fallback)
            platform_data = redis_platform_manager.get_platform_by_id(platform_connection_id, user_id)
            
            if not platform_data:
                logger.warning(f"Platform {platform_connection_id} not found or not accessible to user {user_id}")
                return False
            
            if not platform_data.get('is_active', False):
                logger.warning(f"Platform {platform_connection_id} is not active for user {user_id}")
                return False
            
            # Update session in Redis
            now = datetime.now(timezone.utc)
            pipe = self.redis_client.pipeline()
            pipe.hset(session_key, 'active_platform_id', str(platform_connection_id))
            pipe.hset(session_key, 'updated_at', now.isoformat())
            pipe.hset(session_key, 'last_activity', now.isoformat())
            pipe.execute()
            
            # Update platform's last used timestamp in database (background operation)
            try:
                # This is a background update - don't fail the session update if it fails
                session = self.db_manager.get_session()
                try:
                    from models import PlatformConnection
                    platform = session.query(PlatformConnection).filter_by(
                        id=platform_connection_id,
                        user_id=user_id
                    ).first()
                    
                    if platform:
                        platform.last_used = now
                        session.commit()
                        logger.debug(f"Updated last_used timestamp for platform {platform_connection_id}")
                    
                finally:
                    self.db_manager.close_session(session)
                    
            except Exception as e:
                # Log but don't fail the session update
                logger.warning(f"Failed to update platform last_used timestamp: {e}")
            
            # Create security audit event
            self._create_security_audit_event(
                event_type='platform_switch',
                user_id=user_id,
                session_id=session_id,
                details={
                    'platform_id': platform_connection_id,
                    'platform_name': platform_data.get('name', 'Unknown')
                }
            )
            
            logger.info(f"Updated session {session_id[:8]}... platform context to {platform_connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating platform context: {e}")
            return False
    
    def destroy_session(self, session_id: str) -> bool:
        """
        Remove session from Redis
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_key = self._get_session_key(session_id)
            
            # Get session data before deletion
            session_data = self.redis_client.hgetall(session_key)
            if not session_data:
                return False
            
            user_id = int(session_data['user_id'])
            
            # Remove from all Redis structures
            pipe = self.redis_client.pipeline()
            pipe.delete(session_key)
            pipe.srem(self._get_user_sessions_key(user_id), session_id)
            pipe.srem(self._get_session_index_key(), session_id)
            pipe.execute()
            
            # Create security audit event
            self._create_security_audit_event(
                event_type='session_destroyed',
                user_id=user_id,
                session_id=session_id,
                details={}
            )
            
            # logger.info(f"Destroyed Redis session {session_id}")
            
            # Log to monitoring system
            if self.monitor:
                self.monitor.log_database_session_destroyed(session_id, user_id, 'manual')
            
            return True
            
        except Exception as e:
            logger.error(f"Error destroying session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from Redis
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            session_index_key = self._get_session_index_key()
            all_sessions = self.redis_client.smembers(session_index_key)
            
            expired_count = 0
            now = datetime.now(timezone.utc)
            
            for session_id in all_sessions:
                session_key = self._get_session_key(session_id)
                session_data = self.redis_client.hgetall(session_key)
                
                if not session_data:
                    # Session doesn't exist, remove from index
                    self.redis_client.srem(session_index_key, session_id)
                    expired_count += 1
                    continue
                
                # Check if expired
                try:
                    expires_at = datetime.fromisoformat(session_data['expires_at'])
                    if expires_at < now:
                        self._cleanup_session(session_id, session_data.get('user_id'))
                        expired_count += 1
                except (KeyError, ValueError):
                    # Invalid session data, clean it up
                    self._cleanup_session(session_id, session_data.get('user_id'))
                    expired_count += 1
            
            if expired_count > 0:
                # logger.info(f"Cleaned up {expired_count} expired Redis sessions")
                
                # Log to monitoring system
                if self.monitor:
                    self.monitor.log_database_session_cleanup(expired_count, 'expired')
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
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
            user_sessions_key = self._get_user_sessions_key(user_id)
            user_sessions = self.redis_client.smembers(user_sessions_key)
            
            count = 0
            for session_id in user_sessions:
                if keep_current and session_id == keep_current:
                    continue
                
                if self.destroy_session(session_id):
                    count += 1
            
            # if count > 0:
            #     logger.info(f"Cleaned up {count} Redis sessions for user {user_id}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up user sessions: {e}")
            return 0
    
    def _cleanup_session(self, session_id: str, user_id: Optional[str] = None):
        """Internal method to clean up a single session"""
        try:
            session_key = self._get_session_key(session_id)
            
            # Remove from all Redis structures
            pipe = self.redis_client.pipeline()
            pipe.delete(session_key)
            pipe.srem(self._get_session_index_key(), session_id)
            
            if user_id:
                pipe.srem(self._get_user_sessions_key(int(user_id)), session_id)
            
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    def _create_session_fingerprint(self) -> Optional[str]:
        """Create session fingerprint for security"""
        try:
            if self.security_manager:
                fingerprint = self.security_manager.create_session_fingerprint()
                # Convert fingerprint object to string if needed
                if hasattr(fingerprint, 'to_string'):
                    return fingerprint.to_string()
                elif isinstance(fingerprint, str):
                    return fingerprint
                else:
                    # Fallback: create a simple hash-based fingerprint
                    import hashlib
                    return hashlib.sha256(str(fingerprint).encode()).hexdigest()
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
        except Exception as e:
            logger.debug(f"Error creating security audit event: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get Redis session statistics"""
        try:
            session_index_key = self._get_session_index_key()
            total_sessions = self.redis_client.scard(session_index_key)
            
            # Get Redis info
            redis_info = self.redis_client.info()
            
            return {
                'total_sessions': total_sessions,
                'redis_connected_clients': redis_info.get('connected_clients', 0),
                'redis_used_memory': redis_info.get('used_memory_human', '0B'),
                'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                'redis_keyspace_misses': redis_info.get('keyspace_misses', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {}
    
    def get_db_session(self):
        """
        Compatibility method for database operations.
        
        NOTE: This is a compatibility layer for code that hasn't been migrated yet.
        Redis sessions handle session management, but database operations should
        use db_manager directly for better separation of concerns.
        """
        logger.warning("Using compatibility get_db_session() method. Consider migrating to db_manager.get_session() directly.")
        return self.db_manager.get_session()