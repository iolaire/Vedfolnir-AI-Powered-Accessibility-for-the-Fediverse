# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Session Backend

Simple Redis operations backend for session management.
Provides low-level Redis operations with connection management and error handling.
"""

import os
import json
import redis
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from logging import getLogger

logger = getLogger(__name__)

class RedisConnectionError(Exception):
    """Raised when Redis connection fails"""
    pass

class RedisSessionBackend:
    """Simple Redis backend for session operations"""
    
    def __init__(self, redis_url: Optional[str] = None, 
                 host: str = 'localhost', port: int = 6379, db: int = 0,
                 password: Optional[str] = None, ssl: bool = False,
                 key_prefix: str = 'vedfolnir:session:',
                 connection_pool_size: int = 10):
        """
        Initialize Redis session backend
        
        Args:
            redis_url: Redis URL (overrides other connection params)
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            ssl: Use SSL connection
            key_prefix: Prefix for Redis keys
            connection_pool_size: Connection pool size
        """
        self.key_prefix = key_prefix
        
        # Create Redis connection
        try:
            if redis_url:
                # Parse Redis URL
                self.redis = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            else:
                # Create connection pool
                pool_kwargs = {
                    'host': host,
                    'port': port,
                    'db': db,
                    'decode_responses': True,
                    'socket_connect_timeout': 5,
                    'socket_timeout': 5,
                    'retry_on_timeout': True,
                    'max_connections': connection_pool_size,
                    'health_check_interval': 30
                }
                
                # Add password if provided
                if password:
                    pool_kwargs['password'] = password
                
                # Add SSL if enabled (only for Redis 4.0+)
                if ssl:
                    try:
                        pool_kwargs['ssl'] = ssl
                        pool_kwargs['ssl_check_hostname'] = False
                        pool_kwargs['ssl_cert_reqs'] = None
                    except Exception:
                        # Fallback for older Redis versions
                        logger.warning("SSL not supported in this Redis version, using non-SSL connection")
                
                pool = redis.ConnectionPool(**pool_kwargs)
                self.redis = redis.Redis(connection_pool=pool)
            
            # Test connection
            self.redis.ping()
            logger.info("Redis session backend initialized successfully")
            
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise RedisConnectionError(f"Redis connection failed: {e}")
    
    @classmethod
    def from_env(cls) -> 'RedisSessionBackend':
        """
        Create Redis backend from environment variables
        
        Returns:
            RedisSessionBackend instance configured from environment
        """
        import os
        from dotenv import load_dotenv
        
        # Ensure environment variables are loaded
        load_dotenv()
        
        redis_url = os.getenv('REDIS_URL')
        redis_password = os.getenv('REDIS_PASSWORD')
        
        logger.debug(f"Redis URL from env: {redis_url[:20]}..." if redis_url else "No Redis URL")
        logger.debug(f"Redis password from env: {'***' if redis_password else 'None'}")
        
        if redis_url:
            return cls(redis_url=redis_url)
        else:
            return cls(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=redis_password,
                ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
                key_prefix=os.getenv('REDIS_SESSION_PREFIX', 'vedfolnir:session:')
            )
    
    def _get_key(self, session_id: str) -> str:
        """Get Redis key for session ID"""
        return f"{self.key_prefix}{session_id}"
    
    def _serialize_data(self, data: Dict[str, Any]) -> str:
        """Serialize session data to JSON"""
        # Add timestamp
        data['_last_updated'] = datetime.now(timezone.utc).isoformat()
        return json.dumps(data, default=str)
    
    def _deserialize_data(self, data_str: str) -> Dict[str, Any]:
        """Deserialize session data from JSON"""
        try:
            return json.loads(data_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to deserialize session data: {e}")
            return {}
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            key = self._get_key(session_id)
            data_str = self.redis.get(key)
            
            if data_str:
                return self._deserialize_data(data_str)
            return None
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting session {session_id}: {e}")
            return None
    
    def set(self, session_id: str, data: Dict[str, Any], ttl: int = 7200) -> bool:
        """
        Set session data with TTL
        
        Args:
            session_id: Session ID
            data: Session data dictionary
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(session_id)
            data_str = self._serialize_data(data.copy())
            
            result = self.redis.setex(key, ttl, data_str)
            return bool(result)
            
        except redis.RedisError as e:
            logger.error(f"Redis error setting session {session_id}: {e}")
            return False
    
    def delete(self, session_id: str) -> bool:
        """
        Delete session by session ID
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if session was deleted, False otherwise
        """
        try:
            key = self._get_key(session_id)
            result = self.redis.delete(key)
            return result > 0
            
        except redis.RedisError as e:
            logger.error(f"Redis error deleting session {session_id}: {e}")
            return False
    
    def exists(self, session_id: str) -> bool:
        """
        Check if session exists
        
        Args:
            session_id: Session ID to check
            
        Returns:
            True if session exists, False otherwise
        """
        try:
            key = self._get_key(session_id)
            return bool(self.redis.exists(key))
            
        except redis.RedisError as e:
            logger.error(f"Redis error checking session {session_id}: {e}")
            return False
    
    def update_ttl(self, session_id: str, ttl: int) -> bool:
        """
        Update session TTL
        
        Args:
            session_id: Session ID
            ttl: New TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(session_id)
            result = self.redis.expire(key, ttl)
            return bool(result)
            
        except redis.RedisError as e:
            logger.error(f"Redis error updating TTL for session {session_id}: {e}")
            return False
    
    def get_ttl(self, session_id: str) -> Optional[int]:
        """
        Get remaining TTL for session
        
        Args:
            session_id: Session ID
            
        Returns:
            TTL in seconds or None if session doesn't exist
        """
        try:
            key = self._get_key(session_id)
            ttl = self.redis.ttl(key)
            
            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but no TTL
                return -1
            else:
                return ttl
                
        except redis.RedisError as e:
            logger.error(f"Redis error getting TTL for session {session_id}: {e}")
            return None
    
    def get_all_sessions(self) -> List[str]:
        """
        Get all session IDs
        
        Returns:
            List of session IDs
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = []
            
            for key in self.redis.scan_iter(match=pattern):
                # Extract session ID from key
                session_id = key.replace(self.key_prefix, '')
                keys.append(session_id)
            
            return keys
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting all sessions: {e}")
            return []
    
    def get_sessions_by_user(self, user_id: int) -> List[str]:
        """
        Get all session IDs for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            List of session IDs for the user
        """
        try:
            pattern = f"{self.key_prefix}*"
            user_sessions = []
            
            for key in self.redis.scan_iter(match=pattern):
                data_str = self.redis.get(key)
                if data_str:
                    data = self._deserialize_data(data_str)
                    if data.get('user_id') == user_id:
                        session_id = key.replace(self.key_prefix, '')
                        user_sessions.append(session_id)
            
            return user_sessions
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting sessions for user {user_id}: {e}")
            return []
    
    def cleanup_user_sessions(self, user_id: int) -> int:
        """
        Delete all sessions for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions deleted
        """
        try:
            user_sessions = self.get_sessions_by_user(user_id)
            count = 0
            
            for session_id in user_sessions:
                if self.delete(session_id):
                    count += 1
            
            logger.info(f"Cleaned up {count} sessions for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions for user {user_id}: {e}")
            return 0
    
    def get_session_count(self) -> int:
        """
        Get total number of active sessions
        
        Returns:
            Number of active sessions
        """
        try:
            pattern = f"{self.key_prefix}*"
            count = 0
            
            for _ in self.redis.scan_iter(match=pattern):
                count += 1
            
            return count
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting session count: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection
        
        Returns:
            Health check results
        """
        try:
            # Test basic operations
            start_time = datetime.now()
            self.redis.ping()
            ping_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Get Redis info
            info = self.redis.info()
            
            return {
                'status': 'healthy',
                'ping_ms': round(ping_time, 2),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'redis_version': info.get('redis_version', 'unknown'),
                'session_count': self.get_session_count()
            }
            
        except redis.RedisError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'session_count': 0
            }
    
    def flush_all_sessions(self) -> int:
        """
        Delete all sessions (use with caution!)
        
        Returns:
            Number of sessions deleted
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = list(self.redis.scan_iter(match=pattern))
            
            if keys:
                count = self.redis.delete(*keys)
                logger.warning(f"Flushed {count} sessions from Redis")
                return count
            
            return 0
            
        except redis.RedisError as e:
            logger.error(f"Redis error flushing sessions: {e}")
            return 0
