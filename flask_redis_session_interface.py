# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Flask Redis Session Interface

Custom Flask session interface that uses Redis as the backend storage.
This replaces Flask's default filesystem-based sessions with Redis storage
while maintaining full compatibility with Flask's session API.
"""

import json
import uuid
import redis
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
from logging import getLogger

logger = getLogger(__name__)

class RedisSession(CallbackDict, SessionMixin):
    """Session implementation that stores data in Redis"""
    
    def __init__(self, initial=None, sid=None, new=False):
        def on_update(self):
            self.modified = True
        
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False
        self.permanent = True  # Enable permanent sessions for timeout control
    
    def __setitem__(self, key, value):
        """Override to ensure modifications are tracked"""
        CallbackDict.__setitem__(self, key, value)
        self.modified = True
    
    def __delitem__(self, key):
        """Override to ensure deletions are tracked"""
        CallbackDict.__delitem__(self, key)
        self.modified = True
    
    def update(self, *args, **kwargs):
        """Override to ensure updates are tracked"""
        CallbackDict.update(self, *args, **kwargs)
        self.modified = True
    
    def pop(self, key, default=None):
        """Override to ensure pops are tracked"""
        result = CallbackDict.pop(self, key, default)
        self.modified = True
        return result
    
    def clear(self):
        """Override to ensure clears are tracked"""
        CallbackDict.clear(self)
        self.modified = True

class FlaskRedisSessionInterface(SessionInterface):
    """Flask session interface using Redis as backend storage"""
    
    def __init__(self, redis_client: redis.Redis, key_prefix: str = 'vedfolnir:session:', 
                 session_timeout: int = 7200, config_service=None):
        """
        Initialize Redis session interface
        
        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis keys
            session_timeout: Session timeout in seconds (default: 2 hours)
            config_service: Configuration service for dynamic timeout (optional)
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._default_session_timeout = session_timeout
        self.config_service = config_service
        
        # Initialize session timeout from configuration or use default
        self.session_timeout = self._get_configured_session_timeout()
    
    def _get_configured_session_timeout(self) -> int:
        """
        Get session timeout from configuration service or use default
        
        Returns:
            Session timeout in seconds
        """
        if self.config_service:
            try:
                # Get timeout in minutes from configuration and convert to seconds
                timeout_minutes = self.config_service.get_config('session_timeout_minutes', 120)
                if timeout_minutes is None:
                    return self._default_session_timeout
                return int(timeout_minutes) * 60
            except Exception as e:
                logger.warning(f"Failed to get session timeout from configuration: {e}")
                return self._default_session_timeout
        return self._default_session_timeout
    
    def update_session_timeout_from_config(self):
        """
        Update session timeout from configuration service
        
        This method can be called when configuration changes to update the timeout
        """
        new_timeout = self._get_configured_session_timeout()
        if new_timeout != self.session_timeout:
            old_timeout = self.session_timeout
            self.session_timeout = new_timeout
            logger.info(f"Updated Flask session interface timeout from {old_timeout} to {new_timeout} seconds")
    
    def _generate_sid(self) -> str:
        """Generate a secure session ID"""
        return str(uuid.uuid4())
    
    def _get_redis_key(self, sid: str) -> str:
        """Get Redis key for session ID"""
        return f"{self.key_prefix}{sid}"
    
    def _serialize_session(self, session_data: Dict[str, Any]) -> str:
        """Serialize session data to JSON string"""
        # Create a copy to avoid modifying the original
        data_to_save = session_data.copy()
        
        # Add/update metadata (don't overwrite _created_at if it exists)
        if '_created_at' not in data_to_save:
            data_to_save['_created_at'] = datetime.now(timezone.utc).isoformat()
        data_to_save['_last_activity'] = datetime.now(timezone.utc).isoformat()
        
        return json.dumps(data_to_save, default=str)
    
    def _deserialize_session(self, session_str: str) -> Dict[str, Any]:
        """Deserialize session data from JSON string"""
        try:
            return json.loads(session_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to deserialize session data: {e}")
            return {}
    
    def open_session(self, app, request):
        """
        Open a session for the request
        
        Returns:
            RedisSession instance or None if no session
        """
        # Get session ID from cookie
        cookie_name = getattr(app, 'session_cookie_name', app.config.get('SESSION_COOKIE_NAME', 'session'))
        sid = request.cookies.get(cookie_name)
        
        if not sid:
            # No session cookie, create new session
            sid = self._generate_sid()
            return RedisSession(sid=sid, new=True)
        
        # Try to load session from Redis
        try:
            redis_key = self._get_redis_key(sid)
            session_data_str = self.redis.get(redis_key)
            
            if session_data_str:
                # Session exists in Redis
                session_data = self._deserialize_session(session_data_str)
                
                # Check if session has expired (additional check beyond Redis TTL)
                last_activity_str = session_data.get('_last_activity')
                if last_activity_str:
                    try:
                        last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                        # Use current configured timeout for expiration check
                        current_timeout = self._get_configured_session_timeout()
                        if datetime.now(timezone.utc) - last_activity > timedelta(seconds=current_timeout):
                            # Session expired, delete it
                            self.redis.delete(redis_key)
                            logger.debug(f"Session {sid} expired, creating new session")
                            sid = self._generate_sid()
                            return RedisSession(sid=sid, new=True)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid last_activity timestamp in session {sid}: {e}")
                
                # Preserve all session data including Flask-Login data
                # Only exclude our internal metadata fields
                internal_metadata = {'_created_at', '_last_activity', '_last_updated'}
                flask_session_data = {k: v for k, v in session_data.items() 
                                    if k not in internal_metadata}
                
                logger.info(f"Loading session {sid} with data: {flask_session_data}")
                
                return RedisSession(flask_session_data, sid=sid, new=False)
            else:
                # Session not found in Redis, create new one
                logger.debug(f"Session {sid} not found in Redis, creating new session")
                sid = self._generate_sid()
                return RedisSession(sid=sid, new=True)
                
        except redis.RedisError as e:
            logger.error(f"Redis error opening session: {e}")
            # Fallback: create new session
            sid = self._generate_sid()
            return RedisSession(sid=sid, new=True)
    
    def save_session(self, app, session, response):
        """
        Save session data to Redis and set cookie
        
        Args:
            app: Flask application instance
            session: Session object to save
            response: Response object to set cookie on
        """
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        
        # Debug logging
        logger.info(f"save_session called for session {getattr(session, 'sid', 'no-sid')}")
        logger.info(f"Session data: {dict(session) if session else 'empty'}")
        logger.info(f"Session new: {getattr(session, 'new', 'unknown')}")
        logger.info(f"Session modified: {getattr(session, 'modified', 'unknown')}")
        
        # Don't save if session is None
        if session is None:
            logger.info("Skipping save: session is None")
            return
        
        # If session should be deleted
        if hasattr(session, 'should_delete') and session.should_delete:
            if hasattr(session, 'sid') and session.sid:
                try:
                    redis_key = self._get_redis_key(session.sid)
                    self.redis.delete(redis_key)
                    logger.info(f"Deleted session {session.sid} from Redis")
                except redis.RedisError as e:
                    logger.error(f"Redis error deleting session: {e}")
            
            # Clear cookie
            cookie_name = getattr(app, 'session_cookie_name', app.config.get('SESSION_COOKIE_NAME', 'session'))
            response.delete_cookie(
                cookie_name,
                domain=domain,
                path=path
            )
            return
        
        # Skip saving if session is empty and new (but allow saving if it has data)
        if session.new and not dict(session):
            logger.info("Skipping save: session is new and empty")
            return
        
        # Always save if session has data or is modified
        if dict(session) or getattr(session, 'modified', False):
            try:
                redis_key = self._get_redis_key(session.sid)
                session_data = dict(session)
                
                # Add metadata
                session_data['_last_activity'] = datetime.now(timezone.utc).isoformat()
                if session.new:
                    session_data['_created_at'] = datetime.now(timezone.utc).isoformat()
                
                session_str = self._serialize_session(session_data)
                
                logger.info(f"Saving session {session.sid} with data: {session_data}")
                
                # Get current configured timeout (in case it changed)
                current_timeout = self._get_configured_session_timeout()
                
                # Set with expiration
                self.redis.setex(redis_key, current_timeout, session_str)
                
                # Mark session as no longer new or modified
                session.new = False
                session.modified = False
                
                logger.info(f"Successfully saved session {session.sid} to Redis")
                
            except redis.RedisError as e:
                logger.error(f"Redis error saving session: {e}")
                # Don't set cookie if we can't save to Redis
                return
            except Exception as e:
                logger.error(f"Unexpected error saving session: {e}")
                return
        else:
            logger.info(f"Skipping save: session {session.sid} has no data and is not modified")
        
        # Set cookie (always set cookie if we have a session ID)
        if hasattr(session, 'sid') and session.sid:
            cookie_exp = None
            if getattr(session, 'permanent', False):
                # Use current configured timeout for cookie expiration
                current_timeout = self._get_configured_session_timeout()
                cookie_exp = datetime.now(timezone.utc) + timedelta(seconds=current_timeout)
            
            cookie_name = getattr(app, 'session_cookie_name', app.config.get('SESSION_COOKIE_NAME', 'session'))
            response.set_cookie(
                cookie_name,
                session.sid,
                expires=cookie_exp,
                httponly=self.get_cookie_httponly(app),
                domain=domain,
                path=path,
                secure=self.get_cookie_secure(app),
                samesite=self.get_cookie_samesite(app)
            )
            
            logger.info(f"Set session cookie for session {session.sid}")
    
    def get_session_data(self, sid: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID (for external access)
        
        Args:
            sid: Session ID
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            redis_key = self._get_redis_key(sid)
            session_data_str = self.redis.get(redis_key)
            
            if session_data_str:
                return self._deserialize_session(session_data_str)
            return None
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting session data: {e}")
            return None
    
    def delete_session(self, sid: str) -> bool:
        """
        Delete session by session ID
        
        Args:
            sid: Session ID to delete
            
        Returns:
            True if session was deleted, False otherwise
        """
        try:
            redis_key = self._get_redis_key(sid)
            result = self.redis.delete(redis_key)
            return result > 0
            
        except redis.RedisError as e:
            logger.error(f"Redis error deleting session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (Redis handles this automatically with TTL)
        This method is for compatibility and additional cleanup if needed.
        
        Returns:
            Number of sessions cleaned up (always 0 since Redis handles TTL)
        """
        # Redis automatically handles expiration with TTL
        # This method exists for compatibility with other session interfaces
        return 0
    
    def get_user_sessions(self, user_id: int) -> list:
        """
        Get all session IDs for a specific user
        
        Args:
            user_id: User ID to find sessions for
            
        Returns:
            List of session IDs for the user
        """
        try:
            # Scan for all session keys
            pattern = f"{self.key_prefix}*"
            user_sessions = []
            
            for key in self.redis.scan_iter(match=pattern):
                session_data_str = self.redis.get(key)
                if session_data_str:
                    session_data = self._deserialize_session(session_data_str)
                    if session_data.get('user_id') == user_id:
                        # Extract session ID from key
                        sid = key.decode('utf-8').replace(self.key_prefix, '')
                        user_sessions.append(sid)
            
            return user_sessions
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting user sessions: {e}")
            return []
    
    def cleanup_user_sessions(self, user_id: int) -> int:
        """
        Clean up all sessions for a specific user
        
        Args:
            user_id: User ID to clean up sessions for
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            user_sessions = self.get_user_sessions(user_id)
            count = 0
            
            for sid in user_sessions:
                if self.delete_session(sid):
                    count += 1
            
            logger.info(f"Cleaned up {count} sessions for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up user sessions: {e}")
            return 0
