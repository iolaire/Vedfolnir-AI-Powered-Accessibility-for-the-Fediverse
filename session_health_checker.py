# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Health Checker

Provides comprehensive health checking for session management components including
database sessions, cross-tab synchronization, platform switching, and performance monitoring.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from logging import getLogger

from models import UserSession, User, PlatformConnection
from database import DatabaseManager
from session_manager import SessionManager
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
    summary: Dict[str, Any]
    alerts: List[Dict[str, Any]]

class SessionHealthChecker:
    """Comprehensive health checker for session management system"""
    
    def __init__(self, db_manager: DatabaseManager, session_manager: SessionManager):
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.config = get_session_config()
        self.session_monitor = get_session_monitor(db_manager)
        
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
    
    def check_database_session_health(self) -> SessionComponentHealth:
        """Check database session management health"""
        start_time = time.time()
        
        try:
            # Test basic database session operations
            with self.session_manager.get_db_session() as db_session:
                # Test session creation and cleanup
                from sqlalchemy import text
                db_session.execute(text("SELECT 1"))
                
                # Get session statistics
                total_sessions = db_session.query(UserSession).count()
                
                # Check for expired sessions
                cutoff_time = datetime.now(timezone.utc) - self.config.timeout.idle_timeout
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at < cutoff_time
                ).count()
                
                # Check for stale sessions (very old)
                stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                stale_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at < stale_cutoff
                ).count()
                
                # Get connection pool status
                pool_status = self.session_manager.get_connection_pool_status()
                
            response_time = (time.time() - start_time) * 1000
            
            # Analyze health
            issues = []
            status = SessionHealthStatus.HEALTHY
            
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
            
            # Check expired sessions
            if expired_sessions > 100:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append(f"Many expired sessions: {expired_sessions}")
            
            # Check stale sessions
            if stale_sessions > 50:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append(f"Stale sessions detected: {stale_sessions}")
            
            # Check connection pool
            if 'pool_size' in pool_status and pool_status['pool_size'] > 0:
                utilization = pool_status['checked_out'] / pool_status['pool_size']
                if utilization > self.thresholds['pool_utilization_critical']:
                    status = SessionHealthStatus.UNHEALTHY
                    issues.append(f"Critical pool utilization: {utilization:.1%}")
                elif utilization > self.thresholds['pool_utilization_warning']:
                    if status == SessionHealthStatus.HEALTHY:
                        status = SessionHealthStatus.DEGRADED
                    issues.append(f"High pool utilization: {utilization:.1%}")
            
            message = "Database sessions healthy" if not issues else "; ".join(issues)
            
            return SessionComponentHealth(
                name="database_sessions",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "total_sessions": total_sessions,
                    "expired_sessions": expired_sessions,
                    "stale_sessions": stale_sessions,
                    "pool_status": pool_status
                },
                metrics={
                    "response_time_ms": response_time,
                    "session_count": total_sessions,
                    "expired_count": expired_sessions,
                    "pool_utilization": utilization if 'pool_size' in pool_status and pool_status['pool_size'] > 0 else 0
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Database session health check failed: {e}")
            
            return SessionComponentHealth(
                name="database_sessions",
                status=SessionHealthStatus.UNHEALTHY,
                message=f"Database session check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def check_session_monitoring_health(self) -> SessionComponentHealth:
        """Check session monitoring system health"""
        start_time = time.time()
        
        try:
            if not self.session_monitor:
                return SessionComponentHealth(
                    name="session_monitoring",
                    status=SessionHealthStatus.DEGRADED,
                    message="Session monitoring disabled",
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.now(timezone.utc),
                    details={"monitoring_enabled": False}
                )
            
            # Get monitoring statistics
            stats = self.session_monitor.get_session_statistics()
            health_report = self.session_monitor.get_session_health_report()
            
            response_time = (time.time() - start_time) * 1000
            
            # Analyze monitoring health
            monitoring_health = health_report.get('health_status', {})
            overall_health = monitoring_health.get('overall_health', 'unknown')
            issues = monitoring_health.get('issues', [])
            
            if overall_health == 'critical':
                status = SessionHealthStatus.UNHEALTHY
            elif overall_health == 'warning' or issues:
                status = SessionHealthStatus.DEGRADED
            else:
                status = SessionHealthStatus.HEALTHY
            
            message = f"Monitoring system {overall_health}"
            if issues:
                message += f" - {len(issues)} issues detected"
            
            return SessionComponentHealth(
                name="session_monitoring",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "monitoring_enabled": True,
                    "statistics": stats,
                    "health_report": health_report,
                    "issues": issues
                },
                metrics={
                    "response_time_ms": response_time,
                    "active_sessions": stats.get('session_counts', {}).get('active_sessions', 0),
                    "monitoring_buffer_size": stats.get('monitoring_health', {}).get('metrics_buffer_size', 0)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Session monitoring health check failed: {e}")
            
            return SessionComponentHealth(
                name="session_monitoring",
                status=SessionHealthStatus.UNHEALTHY,
                message=f"Monitoring check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def check_platform_switching_health(self) -> SessionComponentHealth:
        """Check platform switching functionality health"""
        start_time = time.time()
        
        try:
            with self.db_manager.get_session() as db_session:
                # Check platform connections
                total_platforms = db_session.query(PlatformConnection).count()
                active_platforms = db_session.query(PlatformConnection).filter_by(is_active=True).count()
                
                # Check for platform-related session issues
                sessions_with_platforms = db_session.query(UserSession).filter(
                    UserSession.active_platform_id.isnot(None)
                ).count()
                
                sessions_without_platforms = db_session.query(UserSession).filter(
                    UserSession.active_platform_id.is_(None)
                ).count()
                
                # Check for orphaned platform references
                orphaned_sessions = db_session.query(UserSession).outerjoin(
                    PlatformConnection, UserSession.active_platform_id == PlatformConnection.id
                ).filter(
                    UserSession.active_platform_id.isnot(None),
                    PlatformConnection.id.is_(None)
                ).count()
            
            response_time = (time.time() - start_time) * 1000
            
            # Analyze platform switching health
            issues = []
            status = SessionHealthStatus.HEALTHY
            
            if active_platforms == 0:
                status = SessionHealthStatus.UNHEALTHY
                issues.append("No active platform connections")
            elif orphaned_sessions > 0:
                status = SessionHealthStatus.DEGRADED
                issues.append(f"Orphaned platform sessions: {orphaned_sessions}")
            
            if sessions_without_platforms > sessions_with_platforms:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append("Many sessions without platform context")
            
            message = "Platform switching healthy" if not issues else "; ".join(issues)
            
            return SessionComponentHealth(
                name="platform_switching",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "total_platforms": total_platforms,
                    "active_platforms": active_platforms,
                    "sessions_with_platforms": sessions_with_platforms,
                    "sessions_without_platforms": sessions_without_platforms,
                    "orphaned_sessions": orphaned_sessions
                },
                metrics={
                    "response_time_ms": response_time,
                    "platform_count": active_platforms,
                    "orphaned_sessions": orphaned_sessions
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Platform switching health check failed: {e}")
            
            return SessionComponentHealth(
                name="platform_switching",
                status=SessionHealthStatus.UNHEALTHY,
                message=f"Platform switching check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def check_session_cleanup_health(self) -> SessionComponentHealth:
        """Check session cleanup system health"""
        start_time = time.time()
        
        try:
            with self.db_manager.get_session() as db_session:
                # Check cleanup effectiveness
                now = datetime.now(timezone.utc)
                
                # Sessions that should have been cleaned up
                cleanup_cutoff = now - self.config.timeout.idle_timeout - self.config.timeout.cleanup_grace_period
                overdue_cleanup = db_session.query(UserSession).filter(
                    UserSession.updated_at < cleanup_cutoff
                ).count()
                
                # Very old sessions (cleanup failure indicator)
                ancient_cutoff = now - timedelta(days=30)
                ancient_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at < ancient_cutoff
                ).count()
                
                # Recent cleanup activity (last 24 hours)
                recent_cutoff = now - timedelta(hours=24)
                recent_sessions = db_session.query(UserSession).filter(
                    UserSession.created_at >= recent_cutoff
                ).count()
            
            response_time = (time.time() - start_time) * 1000
            
            # Analyze cleanup health
            issues = []
            status = SessionHealthStatus.HEALTHY
            
            if ancient_sessions > 10:
                status = SessionHealthStatus.UNHEALTHY
                issues.append(f"Ancient sessions detected: {ancient_sessions}")
            elif overdue_cleanup > 50:
                status = SessionHealthStatus.DEGRADED
                issues.append(f"Overdue cleanup sessions: {overdue_cleanup}")
            elif overdue_cleanup > 10:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append(f"Some overdue cleanup: {overdue_cleanup}")
            
            # Check if cleanup is configured properly
            if not self.config.features.enable_background_cleanup:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append("Background cleanup disabled")
            
            message = "Session cleanup healthy" if not issues else "; ".join(issues)
            
            return SessionComponentHealth(
                name="session_cleanup",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "overdue_cleanup": overdue_cleanup,
                    "ancient_sessions": ancient_sessions,
                    "recent_sessions": recent_sessions,
                    "cleanup_enabled": self.config.features.enable_background_cleanup,
                    "cleanup_interval": self.config.cleanup.cleanup_interval.total_seconds()
                },
                metrics={
                    "response_time_ms": response_time,
                    "overdue_cleanup": overdue_cleanup,
                    "ancient_sessions": ancient_sessions
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Session cleanup health check failed: {e}")
            
            return SessionComponentHealth(
                name="session_cleanup",
                status=SessionHealthStatus.UNHEALTHY,
                message=f"Cleanup check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def check_session_security_health(self) -> SessionComponentHealth:
        """Check session security system health"""
        start_time = time.time()
        
        try:
            with self.db_manager.get_session() as db_session:
                # Check for security-related issues
                total_sessions = db_session.query(UserSession).count()
                
                # Check for sessions without proper user association
                orphaned_user_sessions = db_session.query(UserSession).outerjoin(
                    User, UserSession.user_id == User.id
                ).filter(User.id.is_(None)).count()
                
                # Check for inactive user sessions
                inactive_user_sessions = db_session.query(UserSession).join(
                    User, UserSession.user_id == User.id
                ).filter(User.is_active == False).count()
                
                # Check session age distribution
                now = datetime.now(timezone.utc)
                old_sessions = db_session.query(UserSession).filter(
                    UserSession.created_at < now - timedelta(hours=48)
                ).count()
            
            response_time = (time.time() - start_time) * 1000
            
            # Analyze security health
            issues = []
            status = SessionHealthStatus.HEALTHY
            
            if orphaned_user_sessions > 0:
                status = SessionHealthStatus.UNHEALTHY
                issues.append(f"Orphaned user sessions: {orphaned_user_sessions}")
            
            if inactive_user_sessions > 0:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.append(f"Inactive user sessions: {inactive_user_sessions}")
            
            # Check security configuration
            security_issues = []
            if not self.config.security.enable_fingerprinting:
                security_issues.append("Session fingerprinting disabled")
            
            if self.config.security.max_concurrent_sessions_per_user <= 0:
                security_issues.append("No concurrent session limit")
            
            if security_issues:
                if status == SessionHealthStatus.HEALTHY:
                    status = SessionHealthStatus.DEGRADED
                issues.extend(security_issues)
            
            message = "Session security healthy" if not issues else "; ".join(issues)
            
            return SessionComponentHealth(
                name="session_security",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={
                    "total_sessions": total_sessions,
                    "orphaned_user_sessions": orphaned_user_sessions,
                    "inactive_user_sessions": inactive_user_sessions,
                    "old_sessions": old_sessions,
                    "security_config": {
                        "fingerprinting_enabled": self.config.security.enable_fingerprinting,
                        "max_concurrent_sessions": self.config.security.max_concurrent_sessions_per_user
                    }
                },
                metrics={
                    "response_time_ms": response_time,
                    "orphaned_sessions": orphaned_user_sessions,
                    "inactive_user_sessions": inactive_user_sessions
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Session security health check failed: {e}")
            
            return SessionComponentHealth(
                name="session_security",
                status=SessionHealthStatus.UNHEALTHY,
                message=f"Security check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def check_comprehensive_session_health(self) -> SessionSystemHealth:
        """Perform comprehensive session system health check"""
        logger.info("Starting comprehensive session health check")
        
        # Run all component health checks
        components = {}
        
        # Database sessions
        components["database_sessions"] = self.check_database_session_health()
        
        # Session monitoring
        components["session_monitoring"] = self.check_session_monitoring_health()
        
        # Platform switching
        components["platform_switching"] = self.check_platform_switching_health()
        
        # Session cleanup
        components["session_cleanup"] = self.check_session_cleanup_health()
        
        # Session security
        components["session_security"] = self.check_session_security_health()
        
        # Determine overall status
        overall_status = SessionHealthStatus.HEALTHY
        for component in components.values():
            if component.status == SessionHealthStatus.UNHEALTHY:
                overall_status = SessionHealthStatus.UNHEALTHY
                break
            elif component.status == SessionHealthStatus.DEGRADED and overall_status == SessionHealthStatus.HEALTHY:
                overall_status = SessionHealthStatus.DEGRADED
        
        # Generate alerts
        alerts = []
        for component_name, component in components.items():
            if component.status != SessionHealthStatus.HEALTHY:
                alerts.append({
                    "component": component_name,
                    "severity": "critical" if component.status == SessionHealthStatus.UNHEALTHY else "warning",
                    "message": component.message,
                    "timestamp": component.last_check.isoformat() if component.last_check else None,
                    "details": component.details
                })
        
        # Generate summary
        summary = {
            "overall_status": overall_status.value,
            "total_components": len(components),
            "healthy_components": sum(1 for c in components.values() if c.status == SessionHealthStatus.HEALTHY),
            "degraded_components": sum(1 for c in components.values() if c.status == SessionHealthStatus.DEGRADED),
            "unhealthy_components": sum(1 for c in components.values() if c.status == SessionHealthStatus.UNHEALTHY),
            "total_alerts": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a["severity"] == "critical"),
            "warning_alerts": sum(1 for a in alerts if a["severity"] == "warning")
        }
        
        # Add performance metrics summary
        avg_response_time = sum(c.response_time_ms for c in components.values() if c.response_time_ms) / len(components)
        summary["avg_response_time_ms"] = avg_response_time
        
        system_health = SessionSystemHealth(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            components=components,
            summary=summary,
            alerts=alerts
        )
        
        logger.info(f"Session health check completed: {overall_status.value} ({len(alerts)} alerts)")
        return system_health
    
    def to_dict(self, system_health: SessionSystemHealth) -> Dict[str, Any]:
        """Convert SessionSystemHealth to dictionary for JSON serialization"""
        result = {
            "status": system_health.status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "summary": system_health.summary,
            "alerts": system_health.alerts,
            "components": {}
        }
        
        for component_name, component in system_health.components.items():
            result["components"][component_name] = {
                "name": component.name,
                "status": component.status.value,
                "message": component.message,
                "response_time_ms": component.response_time_ms,
                "last_check": component.last_check.isoformat() if component.last_check else None,
                "details": component.details,
                "metrics": component.metrics
            }
        
        return result

# Global session health checker instance
_session_health_checker = None

def get_session_health_checker(db_manager: DatabaseManager, session_manager: SessionManager) -> SessionHealthChecker:
    """Get or create global session health checker instance"""
    global _session_health_checker
    if _session_health_checker is None:
        _session_health_checker = SessionHealthChecker(db_manager, session_manager)
    return _session_health_checker