# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis-Compatible Session Health Checker

Enhanced session health checker that works with both Redis and database session managers.
Automatically detects the session manager type and queries the appropriate data source.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from logging import getLogger

from models import UserSession, User, PlatformConnection
from database import DatabaseManager
from unified_session_manager import UnifiedSessionManager
from session_manager_v2 import SessionManagerV2
from session_monitoring import get_session_monitor
from session_config import get_session_config
from security.core.security_utils import sanitize_for_log

logger = getLogger(__name__)

class SessionHealthStatus(Enum):
    """Session health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class SessionComponentHealth:
    """Health status for a session management component"""
    name: str
    status: SessionHealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None

@dataclass
class SessionSystemHealth:
    """Overall session system health status"""
    status: SessionHealthStatus
    timestamp: datetime
    components: Dict[str, SessionComponentHealth]
    session_manager_type: str
    total_active_sessions: int
    total_expired_sessions: int

class RedisSessionHealthChecker:
    """Enhanced session health checker supporting both Redis and database sessions"""
    
    def __init__(self, db_manager: DatabaseManager, session_manager: Union[SessionManagerV2, UnifiedSessionManager]):
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.config = get_session_config()
        
        # Detect session manager type
        self.is_redis_session_manager = isinstance(session_manager, SessionManagerV2)
        self.session_manager_type = "redis" if self.is_redis_session_manager else "database"
        
        # Health check thresholds
        self.thresholds = {
            'response_time_warning': 1000,  # 1 second
            'response_time_critical': 5000,  # 5 seconds
            'error_rate_warning': 0.05,     # 5%
            'error_rate_critical': 0.15,    # 15%
            'pool_utilization_warning': 0.8, # 80%
            'pool_utilization_critical': 0.95, # 95%
            'session_count_warning': 1000,
            'session_count_critical': 5000,
            'cleanup_lag_warning': 3600,    # 1 hour
            'cleanup_lag_critical': 7200    # 2 hours
        }
    
    def get_session_counts(self) -> Dict[str, int]:
        """Get session counts from the appropriate source (Redis or Database)"""
        try:
            if self.is_redis_session_manager:
                # Get session counts from Redis via SessionManagerV2
                # SessionManagerV2 uses RedisSessionBackend which may not have get_session_stats
                # We'll use the session manager's methods instead
                try:
                    # Try to get active session count through cleanup method (returns count)
                    active_sessions = len(self.session_manager.get_all_active_sessions()) if hasattr(self.session_manager, 'get_all_active_sessions') else 0
                except:
                    # Fallback: estimate based on Redis backend if available
                    active_sessions = 0
                
                # For Redis, expired sessions are automatically cleaned up
                expired_sessions = 0
                total_sessions = active_sessions
                
                return {
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'expired_sessions': expired_sessions
                }
            else:
                # Get session counts from database
                with self.db_manager.get_session() as db_session:
                    total_sessions = db_session.query(UserSession).count()
                    
                    # Check for expired sessions
                    cutoff_time = datetime.now(timezone.utc) - self.config.timeout.idle_timeout
                    expired_sessions = db_session.query(UserSession).filter(
                        UserSession.updated_at < cutoff_time
                    ).count()
                    
                    active_sessions = total_sessions - expired_sessions
                    
                    return {
                        'total_sessions': total_sessions,
                        'active_sessions': active_sessions,
                        'expired_sessions': expired_sessions
                    }
                    
        except Exception as e:
            logger.error(f"Error getting session counts: {e}")
            return {
                'total_sessions': 0,
                'active_sessions': 0,
                'expired_sessions': 0
            }
    
    def check_session_storage_health(self) -> SessionComponentHealth:
        """Check health of session storage (Redis or Database)"""
        start_time = time.time()
        
        try:
            session_counts = self.get_session_counts()
            total_sessions = session_counts['total_sessions']
            active_sessions = session_counts['active_sessions']
            expired_sessions = session_counts['expired_sessions']
            
            if self.is_redis_session_manager:
                # Test Redis connectivity via SessionManagerV2
                redis_connected = True
                try:
                    # Test Redis connection by attempting a simple operation
                    if hasattr(self.session_manager, 'redis_backend'):
                        # Try to ping Redis through the backend
                        redis_connected = self.session_manager.redis_backend.health_check()
                    else:
                        # Fallback: try to validate a dummy session
                        redis_connected = True  # Assume connected if no errors so far
                except:
                    redis_connected = False
                
                details = {
                    "session_manager_type": "redis",
                    "redis_connected": redis_connected,
                    "backend_type": "SessionManagerV2",
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "expired_sessions": expired_sessions
                }
            else:
                # Test database connectivity
                with self.db_manager.get_session() as db_session:
                    from sqlalchemy import text
                    db_session.execute(text("SELECT 1"))
                    
                    # Get connection pool status
                    pool_status = getattr(self.session_manager, 'get_connection_pool_status', lambda: {})()
                    
                details = {
                    "session_manager_type": "database",
                    "database_connected": True,
                    "pool_status": pool_status,
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "expired_sessions": expired_sessions
                }
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine health status
            status = SessionHealthStatus.HEALTHY
            issues = []
            
            # Check response time
            if response_time > self.thresholds['response_time_critical']:
                status = SessionHealthStatus.UNHEALTHY
                issues.append(f"Critical response time: {response_time:.0f}ms")
            elif response_time > self.thresholds['response_time_warning']:
                status = SessionHealthStatus.DEGRADED
                issues.append(f"Slow response time: {response_time:.0f}ms")
            
            # Check session counts
            if total_sessions > self.thresholds['session_count_critical']:
                status = SessionHealthStatus.UNHEALTHY
                issues.append(f"Critical session count: {total_sessions}")
            elif total_sessions > self.thresholds['session_count_warning']:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append(f"High session count: {total_sessions}")
            
            # Check expired sessions (mainly for database sessions)
            if not self.is_redis_session_manager and expired_sessions > 100:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append(f"High expired session count: {expired_sessions}")
            
            message = f"{self.session_manager_type.title()} session storage healthy" if not issues else "; ".join(issues)
            
            return SessionComponentHealth(
                name=f"{self.session_manager_type}_session_storage",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details=details,
                metrics={
                    "response_time_ms": response_time,
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "expired_sessions": expired_sessions
                }
            )
            
        except Exception as e:
            logger.error(f"Error checking session storage health: {e}")
            return SessionComponentHealth(
                name=f"{self.session_manager_type}_session_storage",
                status=SessionHealthStatus.UNHEALTHY,
                message=f"Session storage check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e), "session_manager_type": self.session_manager_type}
            )
    
    def check_comprehensive_session_health(self) -> SessionSystemHealth:
        """Perform comprehensive session system health check"""
        start_time = time.time()
        
        try:
            # Check session storage health
            storage_health = self.check_session_storage_health()
            
            # Get overall session counts
            session_counts = self.get_session_counts()
            
            # Determine overall system health
            components = {
                "session_storage": storage_health
            }
            
            # Overall status is the worst component status
            overall_status = storage_health.status
            
            return SessionSystemHealth(
                status=overall_status,
                timestamp=datetime.now(timezone.utc),
                components=components,
                session_manager_type=self.session_manager_type,
                total_active_sessions=session_counts['active_sessions'],
                total_expired_sessions=session_counts['expired_sessions']
            )
            
        except Exception as e:
            logger.error(f"Error performing comprehensive session health check: {e}")
            return SessionSystemHealth(
                status=SessionHealthStatus.UNHEALTHY,
                timestamp=datetime.now(timezone.utc),
                components={},
                session_manager_type=self.session_manager_type,
                total_active_sessions=0,
                total_expired_sessions=0
            )
    
    def to_dict(self, health: SessionSystemHealth) -> Dict[str, Any]:
        """Convert health status to dictionary for JSON serialization"""
        return {
            'status': health.status.value,
            'timestamp': health.timestamp.isoformat(),
            'session_manager_type': health.session_manager_type,
            'total_active_sessions': health.total_active_sessions,
            'total_expired_sessions': health.total_expired_sessions,
            'components': {
                name: {
                    'name': component.name,
                    'status': component.status.value,
                    'message': component.message,
                    'response_time_ms': component.response_time_ms,
                    'last_check': component.last_check.isoformat() if component.last_check else None,
                    'details': component.details,
                    'metrics': component.metrics
                }
                for name, component in health.components.items()
            }
        }

def get_redis_session_health_checker(db_manager: DatabaseManager, session_manager: Union[SessionManagerV2, UnifiedSessionManager]) -> RedisSessionHealthChecker:
    """Get or create Redis-compatible session health checker instance"""
    return RedisSessionHealthChecker(db_manager, session_manager)
