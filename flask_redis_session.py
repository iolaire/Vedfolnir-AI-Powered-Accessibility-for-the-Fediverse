# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Flask-Redis Session Implementation

This module provides a clean Flask session interface that stores all session data in Redis
while using Flask's built-in session cookie management for session IDs.

Architecture:
- Flask manages session cookies containing unique session IDs
- Redis stores all session data using session IDs as keys
- Session data is automatically serialized/deserialized
- Automatic expiration and cleanup
"""

import os
import json
import uuid
import redis
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from flask import Flask, request, g
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
import logging

logger = logging.getLogger(__name__)

class RedisSession(CallbackDict, SessionMixin):
    """Session object that stores data in Redis"""
    
    def __init__(self, initial=None, session_id=None, redis_client=None, prefix="session:", timeout=7200):
        def on_update(self):
            self.modified = True
            
        CallbackDict.__init__(self, initial, on_update)
        self.session_id = session_id
        self.redis_client = redis_client
        self.prefix = prefix
        self.timeout = timeout
        self.modified = False
        self.new = session_id is None
        
        if self.new:
            self.session_id = str(uuid.uuid4())
            self.permanent = True
    
    @property
    def redis_key(self):
        """Get the Redis key for this session"""
        return f"{self.prefix}{self.session_id}"
    
    def save_to_redis(self):
        """Save session data to Redis"""
        if not self.redis_client:
            return False
            
        try:
            # Serialize session data
            session_data = dict(self)
            session_json = json.dumps(session_data, default=str)
            
            # Store in Redis with expiration
            self.redis_client.setex(
                self.redis_key,
                self.timeout,
                session_json
            )
            
            self.modified = False
            logger.debug(f"Saved session {self.session_id} to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session to Redis: {e}")
            return False
    
    @classmethod
    def load_from_redis(cls, session_id, redis_client, prefix="session:", timeout=7200):
        """Load session data from Redis"""
        if not session_id or not redis_client:
            return cls(redis_client=redis_client, prefix=prefix, timeout=timeout)
        
        try:
            redis_key = f"{prefix}{session_id}"
            session_json = redis_client.get(redis_key)
            
            if session_json:
                # Deserialize session data
                session_data = json.loads(session_json.decode('utf-8'))
                session = cls(
                    initial=session_data,
                    session_id=session_id,
                    redis_client=redis_client,
                    prefix=prefix,
                    timeout=timeout
                )
                session.new = False
                session.modified = False
                
                # Refresh expiration
                redis_client.expire(redis_key, timeout)
                
                logger.debug(f"Loaded session {session_id} from Redis")
                return session
            else:
                logger.debug(f"Session {session_id} not found in Redis")
                
        except Exception as e:
            logger.error(f"Failed to load session from Redis: {e}")
        
        # Return new session if loading failed
        return cls(redis_client=redis_client, prefix=prefix, timeout=timeout)
    
    def delete_from_redis(self):
        """Delete session from Redis"""
        if not self.redis_client or not self.session_id:
            return False
            
        try:
            result = self.redis_client.delete(self.redis_key)
            logger.debug(f"Deleted session {self.session_id} from Redis")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")
            return False

class RedisSessionInterface(SessionInterface):
    """Flask session interface that uses Redis for storage"""
    
    def __init__(self, redis_client, prefix="session:", timeout=7200):
        self.redis_client = redis_client
        self.prefix = prefix
        self.timeout = timeout
    
    def open_session(self, app: Flask, request) -> Optional[RedisSession]:
        """Open a session from the request"""
        # Get session ID from cookie
        session_id = request.cookies.get(app.session_cookie_name)
        
        # Load session from Redis
        session = RedisSession.load_from_redis(
            session_id=session_id,
            redis_client=self.redis_client,
            prefix=self.prefix,
            timeout=self.timeout
        )
        
        return session
    
    def save_session(self, app: Flask, session: RedisSession, response) -> None:
        """Save session and set cookie"""
        if not session:
            return
        
        # Save to Redis if modified
        if session.modified or session.new:
            session.save_to_redis()
        
        # Set session cookie
        if session.session_id:
            # Calculate cookie expiration
            expires = None
            if session.permanent:
                expires = datetime.now(timezone.utc) + timedelta(seconds=self.timeout)
            
            # Set the session cookie
            response.set_cookie(
                app.session_cookie_name,
                session.session_id,
                expires=expires,
                httponly=True,
                secure=app.config.get('SESSION_COOKIE_SECURE', False),
                samesite=app.config.get('SESSION_COOKIE_SAMESITE', 'Lax'),
                domain=app.config.get('SESSION_COOKIE_DOMAIN'),
                path=app.config.get('SESSION_COOKIE_PATH', '/')
            )
            
            logger.debug(f"Set session cookie for session {session.session_id}")

def init_redis_session(app: Flask, redis_client=None, **kwargs) -> RedisSessionInterface:
    """Initialize Redis session management for Flask app"""
    
    # Create Redis client if not provided
    if redis_client is None:
        import os
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = redis.from_url(redis_url)
    
    # Configuration
    import os
    prefix = kwargs.get('prefix', os.getenv('REDIS_SESSION_PREFIX', 'vedfolnir:session:'))
    timeout = kwargs.get('timeout', int(os.getenv('REDIS_SESSION_TIMEOUT', '7200')))
    
    # Create session interface
    session_interface = RedisSessionInterface(
        redis_client=redis_client,
        prefix=prefix,
        timeout=timeout
    )
    
    # Configure Flask session settings
    app.config.setdefault('SESSION_COOKIE_NAME', 'session')
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SECURE', os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true')
    app.config.setdefault('SESSION_COOKIE_SAMESITE', os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'))
    
    # Set the session interface
    app.session_interface = session_interface
    
    logger.info(f"Initialized Redis session management with prefix '{prefix}' and timeout {timeout}s")
    
    return session_interface

def cleanup_expired_sessions(redis_client, prefix="session:"):
    """Clean up expired sessions from Redis"""
    try:
        # Redis automatically handles expiration, but we can clean up any orphaned keys
        pattern = f"{prefix}*"
        keys = redis_client.keys(pattern)
        
        expired_count = 0
        for key in keys:
            # Check if key exists (Redis may have already expired it)
            if not redis_client.exists(key):
                expired_count += 1
        
        logger.info(f"Redis session cleanup completed. {expired_count} expired sessions found.")
        return expired_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")
        return 0

def get_session_info(redis_client, session_id, prefix="session:"):
    """Get information about a session"""
    try:
        redis_key = f"{prefix}{session_id}"
        
        # Check if session exists
        exists = redis_client.exists(redis_key)
        if not exists:
            return None
        
        # Get TTL
        ttl = redis_client.ttl(redis_key)
        
        # Get session data
        session_json = redis_client.get(redis_key)
        session_data = json.loads(session_json.decode('utf-8')) if session_json else {}
        
        return {
            'session_id': session_id,
            'exists': True,
            'ttl': ttl,
            'data_keys': list(session_data.keys()),
            'data_size': len(session_json) if session_json else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return None
