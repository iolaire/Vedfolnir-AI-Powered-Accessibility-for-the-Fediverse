# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Performance Optimizer

Implements performance optimizations for database sessions including:
- Database indexing for session queries
- Session context caching for request duration
- Query optimization for session validation
"""

import logging
import time
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from sqlalchemy import text, Index
from sqlalchemy.exc import SQLAlchemyError
from flask import g, has_request_context

from database import DatabaseManager
from models import UserSession, User, PlatformConnection

logger = logging.getLogger(__name__)


class SessionCache:
    """Request-scoped session context cache"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes TTL
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session context"""
        if session_id not in self._cache:
            return None
        
        # Check TTL
        timestamp = self._cache_timestamps.get(session_id, 0)
        if time.time() - timestamp > self._cache_ttl:
            self.invalidate(session_id)
            return None
        
        return self._cache[session_id]
    
    def set(self, session_id: str, context: Dict[str, Any]) -> None:
        """Cache session context"""
        self._cache[session_id] = context
        self._cache_timestamps[session_id] = time.time()
    
    def invalidate(self, session_id: str) -> None:
        """Invalidate cached session"""
        self._cache.pop(session_id, None)
        self._cache_timestamps.pop(session_id, None)
    
    def clear(self) -> None:
        """Clear all cached sessions"""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self._cache)


class SessionPerformanceOptimizer:
    """Optimizes database session performance"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._request_cache = None
        self._optimization_applied = False
    
    @property
    def request_cache(self) -> SessionCache:
        """Get request-scoped cache"""
        if not has_request_context():
            # Return a temporary cache for non-request contexts
            if self._request_cache is None:
                self._request_cache = SessionCache()
            return self._request_cache
        
        # Use Flask g for request-scoped caching
        if not hasattr(g, 'session_cache'):
            g.session_cache = SessionCache()
        return g.session_cache
    
    def apply_database_optimizations(self) -> Dict[str, Any]:
        """Apply database optimizations for session queries"""
        if self._optimization_applied:
            return {'status': 'already_applied', 'indexes_created': 0}
        
        results = {
            'status': 'success',
            'indexes_created': 0,
            'indexes_checked': 0,
            'errors': []
        }
        
        try:
            with self.db_manager.get_session() as db_session:
                # Check existing indexes
                existing_indexes = self._get_existing_indexes(db_session)
                results['indexes_checked'] = len(existing_indexes)
                
                # Create optimized indexes for session queries
                indexes_to_create = [
                    {
                        'name': 'idx_user_sessions_session_id_active',
                        'table': 'user_sessions',
                        'columns': ['session_id', 'is_active'],
                        'sql': 'CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id_active ON user_sessions(session_id, is_active)'
                    },
                    {
                        'name': 'idx_user_sessions_user_id_active',
                        'table': 'user_sessions', 
                        'columns': ['user_id', 'is_active'],
                        'sql': 'CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id_active ON user_sessions(user_id, is_active)'
                    },
                    {
                        'name': 'idx_user_sessions_expires_cleanup',
                        'table': 'user_sessions',
                        'columns': ['expires_at', 'is_active'],
                        'sql': 'CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_cleanup ON user_sessions(expires_at, is_active)'
                    },
                    {
                        'name': 'idx_user_sessions_last_activity',
                        'table': 'user_sessions',
                        'columns': ['last_activity', 'is_active'],
                        'sql': 'CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON user_sessions(last_activity, is_active)'
                    },
                    {
                        'name': 'idx_platform_connections_user_active',
                        'table': 'platform_connections',
                        'columns': ['user_id', 'is_active', 'is_default'],
                        'sql': 'CREATE INDEX IF NOT EXISTS idx_platform_connections_user_active ON platform_connections(user_id, is_active, is_default)'
                    }
                ]
                
                for index_info in indexes_to_create:
                    try:
                        if index_info['name'] not in existing_indexes:
                            db_session.execute(text(index_info['sql']))
                            results['indexes_created'] += 1
                            logger.info(f"Created index: {index_info['name']}")
                        else:
                            logger.debug(f"Index already exists: {index_info['name']}")
                    except SQLAlchemyError as e:
                        error_msg = f"Failed to create index {index_info['name']}: {e}"
                        results['errors'].append(error_msg)
                        logger.error(error_msg)
                
                db_session.commit()
                self._optimization_applied = True
                
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error applying database optimizations: {e}")
        
        return results
    
    def _get_existing_indexes(self, db_session) -> List[str]:
        """Get list of existing database indexes"""
        try:
            result = db_session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting existing indexes: {e}")
            return []
    
    def get_cached_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session context with caching"""
        if not session_id:
            return None
        
        # Try cache first
        cached = self.request_cache.get(session_id)
        if cached:
            logger.debug(f"Session context cache hit for {session_id[:8]}...")
            return cached
        
        # Cache miss - fetch from database
        context = self._fetch_session_context_optimized(session_id)
        if context:
            self.request_cache.set(session_id, context)
            logger.debug(f"Session context cached for {session_id[:8]}...")
        
        return context
    
    def _fetch_session_context_optimized(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Fetch session context with optimized query"""
        try:
            with self.db_manager.get_session() as db_session:
                # Use optimized query with joins to minimize database round trips
                from sqlalchemy.orm import joinedload
                
                user_session = db_session.query(UserSession).options(
                    joinedload(UserSession.user),
                    joinedload(UserSession.active_platform)
                ).filter(
                    UserSession.session_id == session_id,
                    UserSession.is_active == True
                ).first()
                
                if not user_session:
                    return None
                
                # Check expiration
                if user_session.is_expired():
                    logger.debug(f"Session {session_id[:8]}... is expired")
                    return None
                
                # Build context dictionary
                user = user_session.user
                platform = user_session.active_platform
                
                context = {
                    'session_id': session_id,
                    'user_id': user.id if user else None,
                    'user_username': user.username if user else None,
                    'user': user,
                    'platform_connection_id': platform.id if platform else None,
                    'platform_name': platform.name if platform else None,
                    'platform_type': platform.platform_type if platform else None,
                    'platform_connection': platform,
                    'created_at': user_session.created_at,
                    'updated_at': user_session.updated_at,
                    'expires_at': user_session.expires_at,
                    'last_activity': user_session.last_activity
                }
                
                return context
                
        except Exception as e:
            logger.error(f"Error fetching optimized session context: {e}")
            return None
    
    def validate_session_optimized(self, session_id: str, user_id: int) -> bool:
        """Optimized session validation"""
        if not session_id or not user_id:
            return False
        
        try:
            with self.db_manager.get_session() as db_session:
                # Single optimized query to validate session
                exists = db_session.query(UserSession).filter(
                    UserSession.session_id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                ).first() is not None
                
                return exists
                
        except Exception as e:
            logger.error(f"Error in optimized session validation: {e}")
            return False
    
    def cleanup_expired_sessions_optimized(self, batch_size: int = 100) -> int:
        """Optimized batch cleanup of expired sessions"""
        try:
            total_cleaned = 0
            
            with self.db_manager.get_session() as db_session:
                while True:
                    # Use optimized query with limit for batch processing
                    expired_sessions = db_session.query(UserSession).filter(
                        UserSession.expires_at < datetime.now(timezone.utc)
                    ).limit(batch_size).all()
                    
                    if not expired_sessions:
                        break
                    
                    # Batch delete
                    session_ids = [s.session_id for s in expired_sessions]
                    db_session.query(UserSession).filter(
                        UserSession.session_id.in_(session_ids)
                    ).delete(synchronize_session=False)
                    
                    batch_count = len(expired_sessions)
                    total_cleaned += batch_count
                    
                    # Invalidate cache for deleted sessions
                    for session_id in session_ids:
                        self.request_cache.invalidate(session_id)
                    
                    db_session.commit()
                    
                    # If we got fewer than batch_size, we're done
                    if batch_count < batch_size:
                        break
            
            if total_cleaned > 0:
                logger.info(f"Optimized cleanup removed {total_cleaned} expired sessions")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Error in optimized session cleanup: {e}")
            return 0
    
    def get_user_sessions_optimized(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user sessions with optimized query"""
        try:
            with self.db_manager.get_session() as db_session:
                query = db_session.query(UserSession).options(
                    joinedload(UserSession.active_platform)
                ).filter(UserSession.user_id == user_id)
                
                if active_only:
                    query = query.filter(
                        UserSession.is_active == True,
                        UserSession.expires_at > datetime.now(timezone.utc)
                    )
                
                sessions = query.order_by(UserSession.last_activity.desc()).all()
                
                # Convert to dictionaries
                session_list = []
                for session_obj in sessions:
                    platform = session_obj.active_platform
                    session_list.append({
                        'session_id': session_obj.session_id,
                        'platform_id': platform.id if platform else None,
                        'platform_name': platform.name if platform else None,
                        'platform_type': platform.platform_type if platform else None,
                        'created_at': session_obj.created_at,
                        'last_activity': session_obj.last_activity,
                        'expires_at': session_obj.expires_at,
                        'is_expired': session_obj.is_expired()
                    })
                
                return session_list
                
        except Exception as e:
            logger.error(f"Error getting optimized user sessions: {e}")
            return []
    
    def update_session_activity_optimized(self, session_id: str) -> bool:
        """Optimized session activity update with throttling"""
        if not session_id:
            return False
        
        # Check if we recently updated this session to avoid excessive updates
        cache_key = f"activity_update_{session_id}"
        if hasattr(g, cache_key):
            last_update = getattr(g, cache_key)
            if (datetime.now(timezone.utc) - last_update).total_seconds() < 60:
                return True  # Skip update if less than 1 minute since last update
        
        try:
            with self.db_manager.get_session() as db_session:
                # Single update query
                updated_rows = db_session.query(UserSession).filter(
                    UserSession.session_id == session_id,
                    UserSession.is_active == True
                ).update({
                    'last_activity': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                })
                
                db_session.commit()
                
                if updated_rows > 0:
                    # Mark as recently updated
                    if has_request_context():
                        setattr(g, cache_key, datetime.now(timezone.utc))
                    
                    # Invalidate cache to force refresh
                    self.request_cache.invalidate(session_id)
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error in optimized session activity update: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for session operations"""
        try:
            with self.db_manager.get_session() as db_session:
                # Get session statistics
                total_sessions = db_session.query(UserSession).count()
                active_sessions = db_session.query(UserSession).filter(
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                ).count()
                
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.expires_at < datetime.now(timezone.utc)
                ).count()
                
                # Get cache statistics
                cache_size = self.request_cache.size()
                
                # Get database connection pool info
                engine = self.db_manager.engine
                pool = engine.pool
                
                return {
                    'session_stats': {
                        'total_sessions': total_sessions,
                        'active_sessions': active_sessions,
                        'expired_sessions': expired_sessions,
                        'expiration_rate': expired_sessions / max(total_sessions, 1)
                    },
                    'cache_stats': {
                        'cache_size': cache_size,
                        'cache_enabled': True
                    },
                    'database_stats': {
                        'pool_size': pool.size(),
                        'checked_out': pool.checkedout(),
                        'overflow': pool.overflow(),
                        'optimizations_applied': self._optimization_applied
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def optimize_query_plan(self) -> Dict[str, Any]:
        """Analyze and optimize query execution plans"""
        try:
            results = {
                'analyzed_queries': 0,
                'optimizations': [],
                'recommendations': []
            }
            
            with self.db_manager.get_session() as db_session:
                # Analyze common session queries
                queries_to_analyze = [
                    {
                        'name': 'session_lookup',
                        'sql': 'SELECT * FROM user_sessions WHERE session_id = ? AND is_active = 1'
                    },
                    {
                        'name': 'user_sessions',
                        'sql': 'SELECT * FROM user_sessions WHERE user_id = ? AND is_active = 1'
                    },
                    {
                        'name': 'expired_cleanup',
                        'sql': 'SELECT * FROM user_sessions WHERE expires_at < ?'
                    }
                ]
                
                for query_info in queries_to_analyze:
                    try:
                        # Get query plan
                        explain_sql = f"EXPLAIN QUERY PLAN {query_info['sql']}"
                        plan = db_session.execute(text(explain_sql), {'param': 'test'}).fetchall()
                        
                        results['analyzed_queries'] += 1
                        
                        # Check if query uses index
                        plan_text = ' '.join([str(row) for row in plan])
                        if 'USING INDEX' not in plan_text.upper():
                            results['recommendations'].append(
                                f"Query '{query_info['name']}' may benefit from additional indexing"
                            )
                        else:
                            results['optimizations'].append(
                                f"Query '{query_info['name']}' is using indexes efficiently"
                            )
                            
                    except Exception as e:
                        logger.debug(f"Error analyzing query {query_info['name']}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error optimizing query plan: {e}")
            return {'error': str(e)}
    
    def clear_request_cache(self) -> None:
        """Clear request-scoped cache"""
        self.request_cache.clear()
        logger.debug("Session cache cleared")
    
    def invalidate_session_cache(self, session_id: str) -> None:
        """Invalidate specific session in cache"""
        self.request_cache.invalidate(session_id)
        logger.debug(f"Session cache invalidated for {session_id[:8]}...")


# Global optimizer instance
_global_optimizer: Optional[SessionPerformanceOptimizer] = None


def get_session_optimizer(db_manager: DatabaseManager) -> SessionPerformanceOptimizer:
    """Get global session performance optimizer instance"""
    global _global_optimizer
    
    if _global_optimizer is None:
        if db_manager is None:
            raise ValueError("db_manager must be provided to initialize SessionPerformanceOptimizer")
        _global_optimizer = SessionPerformanceOptimizer(db_manager)
    
    return _global_optimizer


def initialize_session_optimizations(db_manager: DatabaseManager) -> Dict[str, Any]:
    """Initialize session performance optimizations"""
    optimizer = get_session_optimizer(db_manager)
    results = optimizer.apply_database_optimizations()
    
    logger.info(f"Session optimizations initialized: {results}")
    return results


@contextmanager
def optimized_session_context(session_id: str, db_manager: DatabaseManager = None):
    """Context manager for optimized session operations"""
    optimizer = get_session_optimizer(db_manager)
    
    try:
        # Get cached context
        context = optimizer.get_cached_session_context(session_id)
        yield context
    finally:
        # Cleanup is handled automatically by request teardown
        pass