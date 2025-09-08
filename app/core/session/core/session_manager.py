# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

"""
Consolidated Session Manager

Single session manager that uses Redis as primary storage with database fallback.
Combines the best features from session_manager_v2 and unified_session_manager.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from contextlib import contextmanager
from logging import getLogger

from flask import session, request, g
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from models import User, PlatformConnection, UserSession
from database import DatabaseManager

logger = getLogger(__name__)

class SessionError(Exception):
    """Base session error"""
    pass

class SessionManager:
    """Consolidated session manager with Redis primary and database fallback"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._redis_backend = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis backend with fallback"""
        try:
            from redis_session_backend import RedisSessionBackend
            self._redis_backend = RedisSessionBackend.from_env()
        except Exception as e:
            logger.warning(f"Redis unavailable, using database fallback: {e}")
            self._redis_backend = None
    
    @contextmanager
    def get_db_session(self):
        """Get database session with proper cleanup"""
        db_session = self.db_manager.get_session()
        try:
            yield db_session
        finally:
            db_session.close()
    
    def create_session(self, user_id: int, platform_connection_id: Optional[int] = None) -> Dict[str, Any]:
        """Create new session"""
        session_data = {
            'user_id': user_id,
            'platform_connection_id': platform_connection_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'session_id': str(uuid.uuid4())
        }
        
        redis_success = False
        db_success = False
        
        # Store in Redis if available
        if self._redis_backend:
            try:
                self._redis_backend.set_session(session_data['session_id'], session_data)
                redis_success = True
            except Exception as e:
                logger.warning(f"Redis session creation failed: {e}")
        
        # Always store in database for audit
        try:
            with self.get_db_session() as db_session:
                user_session = UserSession(
                    user_id=user_id,
                    active_platform_id=platform_connection_id,  # Fixed field name
                    session_id=session_data['session_id'],
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=2)  # Add required field
                )
                db_session.add(user_session)
                db_session.commit()
                db_success = True
        except Exception as e:
            logger.error(f"Database session creation failed: {e}")
        
        # LOGIC GAP FIX: Ensure at least one storage method succeeded
        if not redis_success and not db_success:
            raise RuntimeError("Session creation failed: unable to store session in Redis or database")
        
        if not db_success:
            logger.warning(f"Session {session_data['session_id']} created in Redis only - database audit failed")
        
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        # Try Redis first
        if self._redis_backend:
            try:
                return self._redis_backend.get_session(session_id)
            except Exception as e:
                logger.warning(f"Redis session retrieval failed: {e}")
        
        # Fallback to database
        try:
            with self.get_db_session() as db_session:
                user_session = db_session.query(UserSession).filter_by(session_id=session_id).first()
                if user_session:
                    return {
                        'user_id': user_session.user_id,
                        'platform_connection_id': user_session.active_platform_id,  # Fixed field name
                        'session_id': session_id,
                        'created_at': user_session.created_at.isoformat()
                    }
        except Exception as e:
            logger.error(f"Database session retrieval failed: {e}")
        
        return None
    
    def cleanup_user_sessions(self, user_id: int) -> int:
        """Clean up all sessions for a user"""
        count = 0
        
        # Clean Redis sessions
        if self._redis_backend:
            try:
                count += self._redis_backend.cleanup_user_sessions(user_id)
            except Exception as e:
                logger.warning(f"Redis session cleanup failed: {e}")
        
        # Clean database sessions
        try:
            with self.get_db_session() as db_session:
                deleted = db_session.query(UserSession).filter_by(user_id=user_id).delete()
                db_session.commit()
                count += deleted
        except Exception as e:
            logger.error(f"Database session cleanup failed: {e}")
        
        return count
