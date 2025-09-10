# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unified Session Manager

Provides a unified session management interface that works with the database
and provides context managers for session management.
"""

import logging
from contextlib import contextmanager
from typing import Optional, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import Config
from models import Base

logger = logging.getLogger(__name__)

class SessionError(Exception):
    """Base session error"""
    pass

class SessionValidationError(SessionError):
    """Session validation error"""
    pass

class SessionExpiredError(SessionError):
    """Session expired error"""
    pass

class SessionNotFoundError(SessionError):
    """Session not found error"""
    pass

class SessionDatabaseError(SessionError):
    """Session database error"""
    pass

class UnifiedSessionManager:
    """Unified session manager that provides database session management"""
    
    def __init__(self, db_manager=None):
        """Initialize unified session manager"""
        self.config = Config()
        self.db_manager = db_manager
        self._redis_backend = None
        
        if db_manager:
            # Use provided database manager
            self.engine = db_manager.engine
            self.SessionLocal = db_manager.SessionFactory
        else:
            # Create database engine
            self.engine = create_engine(
                self.config.storage.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        
        # Initialize Redis backend
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis backend with fallback"""
        try:
            from app.core.session.redis.manager import RedisSessionBackend
            self._redis_backend = RedisSessionBackend.from_env()
        except Exception as e:
            logger.warning(f"Redis unavailable, using database fallback: {e}")
            self._redis_backend = None
    
    @contextmanager
    def get_db_session(self):
        """Get database session with proper cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data by ID"""
        try:
            with self.get_db_session() as session:
                from models import UserSession
                user_session = session.query(UserSession).filter_by(session_id=session_id).first()
                if user_session:
                    return {
                        'user_id': user_session.user_id,
                        'session_id': session_id,
                        'created_at': user_session.created_at.isoformat()
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

# Global instance
unified_session_manager = UnifiedSessionManager()