# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time
import logging
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from flask import g, has_request_context, request
from sqlalchemy.pool import Pool
from sqlalchemy.engine import Engine


@dataclass
class SessionMetrics:
    """Container for session performance metrics"""
    session_creations: int = 0
    session_closures: int = 0
    session_rollbacks: int = 0
    session_commits: int = 0
    detached_instance_recoveries: int = 0
    session_reattachments: int = 0
    active_sessions: int = 0
    peak_active_sessions: int = 0
    total_session_duration: float = 0.0
    average_session_duration: float = 0.0
    session_errors: int = 0
    
    # Performance timing metrics
    session_creation_times: deque = field(default_factory=lambda: deque(maxlen=100))
    session_cleanup_times: deque = field(default_factory=lambda: deque(maxlen=100))
    recovery_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Database pool metrics
    pool_size: int = 0
    pool_checked_out: int = 0
    pool_overflow: int = 0
    pool_checked_in: int = 0


@dataclass
class RequestMetrics:
    """Container for request-level performance metrics"""
    request_id: str
    endpoint: str
    start_time: float
    end_time: Optional[float] = None
    session_operations: List[str] = field(default_factory=list)
    detached_instance_errors: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    database_queries: int = 0
    session_duration: float = 0.0


class SessionPerformanceMonitor:
    """
    Performance monitoring system for database session management.
    
    Tracks metrics for:
    - Session creation and cleanup operations
    - DetachedInstanceError recovery events
    - Database session pool usage
    - Performance timing for session-aware operations
    """
    
    def __init__(self, logger_name: str = __name__):
        """
        Initialize the performance monitor.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
        self.metrics = SessionMetrics()
        self.request_metrics: Dict[str, RequestMetrics] = {}
        self.lock = threading.Lock()
        
        # Performance thresholds for alerting
        self.slow_session_threshold = 1.0  # seconds
        self.high_recovery_rate_threshold = 0.1  # 10% of operations
        self.max_active_sessions_threshold = 50
        
        # Metrics history for trend analysis
        self.metrics_history: deque = deque(maxlen=1000)
        self.last_metrics_snapshot = time.time()
        
        self.logger.info("SessionPerformanceMonitor initialized")
    
    def start_request_monitoring(self, endpoint: str = None) -> str:
        """
        Start monitoring for a request.
        
        Args:
            endpoint: Request endpoint name
            
        Returns:
            Request ID for tracking
        """
        if not has_request_context():
            return "no-request-context"
        
        request_id = f"{id(request)}_{time.time()}"
        endpoint = endpoint or getattr(request, 'endpoint', 'unknown')
        
        with self.lock:
            self.request_metrics[request_id] = RequestMetrics(
                request_id=request_id,
                endpoint=endpoint,
                start_time=time.time()
            )
        
        # Store request ID in Flask g for easy access
        g.performance_request_id = request_id
        
        self.logger.debug(f"Started request monitoring: {request_id} ({endpoint})")
        return request_id
    
    def end_request_monitoring(self, request_id: str = None):
        """
        End monitoring for a request and log performance metrics.
        
        Args:
            request_id: Request ID to end monitoring for
        """
        if request_id is None:
            request_id = getattr(g, 'performance_request_id', None)
        
        if not request_id or request_id not in self.request_metrics:
            return
        
        with self.lock:
            request_metric = self.request_metrics[request_id]
            request_metric.end_time = time.time()
            
            # Calculate request duration
            duration = request_metric.end_time - request_metric.start_time
            
            # Log performance summary
            self._log_request_performance(request_metric, duration)
            
            # Clean up old request metrics
            del self.request_metrics[request_id]
    
    def record_session_creation(self, duration: float = None):
        """
        Record a session creation event.
        
        Args:
            duration: Time taken to create the session in seconds
        """
        with self.lock:
            self.metrics.session_creations += 1
            self.metrics.active_sessions += 1
            
            if self.metrics.active_sessions > self.metrics.peak_active_sessions:
                self.metrics.peak_active_sessions = self.metrics.active_sessions
            
            if duration is not None:
                self.metrics.session_creation_times.append(duration)
                
                # Alert on slow session creation
                if duration > self.slow_session_threshold:
                    self.logger.warning(f"Slow session creation detected: {duration:.3f}s")
        
        self._add_request_operation("session_creation")
        self.logger.debug(f"Session created (duration: {duration:.3f}s)" if duration else "Session created")
    
    def record_session_closure(self, duration: float = None):
        """
        Record a session closure event.
        
        Args:
            duration: Time taken to close the session in seconds
        """
        with self.lock:
            self.metrics.session_closures += 1
            if self.metrics.active_sessions > 0:
                self.metrics.active_sessions -= 1
            
            if duration is not None:
                self.metrics.session_cleanup_times.append(duration)
                
                # Alert on slow session cleanup
                if duration > self.slow_session_threshold:
                    self.logger.warning(f"Slow session cleanup detected: {duration:.3f}s")
        
        self._add_request_operation("session_closure")
        self.logger.debug(f"Session closed (duration: {duration:.3f}s)" if duration else "Session closed")
    
    def record_session_commit(self):
        """Record a session commit event."""
        with self.lock:
            self.metrics.session_commits += 1
        
        self._add_request_operation("session_commit")
        self.logger.debug("Session committed")
    
    def record_session_rollback(self):
        """Record a session rollback event."""
        with self.lock:
            self.metrics.session_rollbacks += 1
        
        self._add_request_operation("session_rollback")
        self.logger.debug("Session rolled back")
    
    def record_detached_instance_recovery(self, object_type: str, duration: float = None, success: bool = True):
        """
        Record a DetachedInstanceError recovery event.
        
        Args:
            object_type: Type of object that was recovered
            duration: Time taken for recovery in seconds
            success: Whether the recovery was successful
        """
        with self.lock:
            self.metrics.detached_instance_recoveries += 1
            
            if duration is not None:
                self.metrics.recovery_times.append(duration)
        
        # Update request-specific metrics
        try:
            if has_request_context():
                request_id = getattr(g, 'performance_request_id', None)
                if request_id and request_id in self.request_metrics:
                    with self.lock:
                        self.request_metrics[request_id].recovery_attempts += 1
                        if success:
                            self.request_metrics[request_id].successful_recoveries += 1
        except RuntimeError:
            # No Flask context available, skip request-specific tracking
            pass
        
        self._add_request_operation(f"detached_recovery_{object_type}")
        
        status = "successful" if success else "failed"
        duration_str = f" (duration: {duration:.3f}s)" if duration else ""
        self.logger.info(f"DetachedInstanceError recovery {status} for {object_type}{duration_str}")
    
    def record_session_reattachment(self, object_type: str):
        """
        Record a session reattachment event.
        
        Args:
            object_type: Type of object that was reattached
        """
        with self.lock:
            self.metrics.session_reattachments += 1
        
        self._add_request_operation(f"session_reattachment_{object_type}")
        self.logger.debug(f"Session reattachment for {object_type}")
    
    def record_session_error(self, error_type: str, error_message: str):
        """
        Record a session-related error.
        
        Args:
            error_type: Type of error that occurred
            error_message: Error message
        """
        with self.lock:
            self.metrics.session_errors += 1
        
        # Update request-specific metrics
        try:
            if has_request_context():
                request_id = getattr(g, 'performance_request_id', None)
                if request_id and request_id in self.request_metrics:
                    with self.lock:
                        if "DetachedInstanceError" in error_type:
                            self.request_metrics[request_id].detached_instance_errors += 1
        except RuntimeError:
            # No Flask context available, skip request-specific tracking
            pass
        
        self._add_request_operation(f"session_error_{error_type}")
        self.logger.error(f"Session error ({error_type}): {error_message}")
    
    def update_pool_metrics(self, engine: Engine):
        """
        Update database connection pool metrics.
        
        Args:
            engine: SQLAlchemy engine to get pool metrics from
        """
        if not hasattr(engine, 'pool'):
            return
        
        pool = engine.pool
        
        with self.lock:
            self.metrics.pool_size = pool.size()
            self.metrics.pool_checked_out = pool.checkedout()
            self.metrics.pool_overflow = pool.overflow()
            self.metrics.pool_checked_in = pool.checkedin()
        
        # Alert on pool exhaustion
        if self.metrics.pool_checked_out >= self.metrics.pool_size * 0.9:
            self.logger.warning(f"Database pool near exhaustion: {self.metrics.pool_checked_out}/{self.metrics.pool_size}")
    
    @contextmanager
    def time_operation(self, operation_name: str):
        """
        Context manager for timing operations.
        
        Args:
            operation_name: Name of the operation being timed
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.logger.debug(f"Operation '{operation_name}' took {duration:.3f}s")
            
            # Record operation in request metrics
            self._add_request_operation(f"timed_{operation_name}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary containing current metrics
        """
        with self.lock:
            # Calculate averages
            if self.metrics.session_creations > 0:
                self.metrics.average_session_duration = (
                    self.metrics.total_session_duration / self.metrics.session_creations
                )
            
            # Calculate recovery rate
            total_operations = (
                self.metrics.session_creations + 
                self.metrics.session_closures + 
                self.metrics.session_commits + 
                self.metrics.session_rollbacks
            )
            recovery_rate = (
                self.metrics.detached_instance_recoveries / total_operations 
                if total_operations > 0 else 0
            )
            
            # Calculate average timing metrics
            avg_creation_time = (
                sum(self.metrics.session_creation_times) / len(self.metrics.session_creation_times)
                if self.metrics.session_creation_times else 0
            )
            
            avg_cleanup_time = (
                sum(self.metrics.session_cleanup_times) / len(self.metrics.session_cleanup_times)
                if self.metrics.session_cleanup_times else 0
            )
            
            avg_recovery_time = (
                sum(self.metrics.recovery_times) / len(self.metrics.recovery_times)
                if self.metrics.recovery_times else 0
            )
            
            return {
                'timestamp': datetime.now().isoformat(),
                'session_metrics': {
                    'creations': self.metrics.session_creations,
                    'closures': self.metrics.session_closures,
                    'commits': self.metrics.session_commits,
                    'rollbacks': self.metrics.session_rollbacks,
                    'active_sessions': self.metrics.active_sessions,
                    'peak_active_sessions': self.metrics.peak_active_sessions,
                    'errors': self.metrics.session_errors,
                    'average_duration': self.metrics.average_session_duration
                },
                'recovery_metrics': {
                    'detached_instance_recoveries': self.metrics.detached_instance_recoveries,
                    'session_reattachments': self.metrics.session_reattachments,
                    'recovery_rate': recovery_rate
                },
                'performance_metrics': {
                    'avg_creation_time': avg_creation_time,
                    'avg_cleanup_time': avg_cleanup_time,
                    'avg_recovery_time': avg_recovery_time
                },
                'pool_metrics': {
                    'pool_size': self.metrics.pool_size,
                    'checked_out': self.metrics.pool_checked_out,
                    'overflow': self.metrics.pool_overflow,
                    'checked_in': self.metrics.pool_checked_in
                },
                'active_requests': len(self.request_metrics)
            }
    
    def get_performance_summary(self) -> str:
        """
        Get a formatted performance summary.
        
        Returns:
            Formatted string with performance summary
        """
        metrics = self.get_current_metrics()
        
        summary = f"""
Session Performance Summary:
===========================
Sessions: {metrics['session_metrics']['creations']} created, {metrics['session_metrics']['closures']} closed
Active: {metrics['session_metrics']['active_sessions']} (peak: {metrics['session_metrics']['peak_active_sessions']})
Commits: {metrics['session_metrics']['commits']}, Rollbacks: {metrics['session_metrics']['rollbacks']}
Errors: {metrics['session_metrics']['errors']}

Recovery Metrics:
================
Detached Instance Recoveries: {metrics['recovery_metrics']['detached_instance_recoveries']}
Session Reattachments: {metrics['recovery_metrics']['session_reattachments']}
Recovery Rate: {metrics['recovery_metrics']['recovery_rate']:.2%}

Performance Timing:
==================
Avg Creation Time: {metrics['performance_metrics']['avg_creation_time']:.3f}s
Avg Cleanup Time: {metrics['performance_metrics']['avg_cleanup_time']:.3f}s
Avg Recovery Time: {metrics['performance_metrics']['avg_recovery_time']:.3f}s

Database Pool:
=============
Pool Size: {metrics['pool_metrics']['pool_size']}
Checked Out: {metrics['pool_metrics']['checked_out']}
Overflow: {metrics['pool_metrics']['overflow']}
Checked In: {metrics['pool_metrics']['checked_in']}

Active Requests: {metrics['active_requests']}
        """.strip()
        
        return summary
    
    def log_periodic_summary(self, interval_seconds: int = 300):
        """
        Log a periodic performance summary.
        
        Args:
            interval_seconds: Interval between summaries in seconds
        """
        current_time = time.time()
        if current_time - self.last_metrics_snapshot >= interval_seconds:
            self.logger.info(f"Performance Summary:\n{self.get_performance_summary()}")
            
            # Take snapshot for history
            with self.lock:
                self.metrics_history.append({
                    'timestamp': current_time,
                    'metrics': self.get_current_metrics()
                })
            
            self.last_metrics_snapshot = current_time
    
    def _add_request_operation(self, operation: str):
        """
        Add an operation to the current request's metrics.
        
        Args:
            operation: Name of the operation
        """
        try:
            if has_request_context():
                request_id = getattr(g, 'performance_request_id', None)
                if request_id and request_id in self.request_metrics:
                    with self.lock:
                        self.request_metrics[request_id].session_operations.append(operation)
        except RuntimeError:
            # No Flask context available, skip request-specific tracking
            pass
    
    def _log_request_performance(self, request_metric: RequestMetrics, duration: float):
        """
        Log performance metrics for a completed request.
        
        Args:
            request_metric: Request metrics to log
            duration: Total request duration
        """
        # Calculate recovery success rate for this request
        recovery_success_rate = 0.0
        if request_metric.recovery_attempts > 0:
            recovery_success_rate = request_metric.successful_recoveries / request_metric.recovery_attempts
        
        # Log summary
        self.logger.info(
            f"Request {request_metric.endpoint} completed in {duration:.3f}s - "
            f"Operations: {len(request_metric.session_operations)}, "
            f"Detached errors: {request_metric.detached_instance_errors}, "
            f"Recovery attempts: {request_metric.recovery_attempts} "
            f"(success rate: {recovery_success_rate:.1%})"
        )
        
        # Log detailed operations if debug enabled
        if self.logger.isEnabledFor(logging.DEBUG):
            operations_summary = ", ".join(request_metric.session_operations)
            self.logger.debug(f"Request {request_metric.request_id} operations: {operations_summary}")
        
        # Alert on high error rates
        if request_metric.detached_instance_errors > 5:
            self.logger.warning(
                f"High DetachedInstanceError rate in request {request_metric.endpoint}: "
                f"{request_metric.detached_instance_errors} errors"
            )
        
        # Alert on poor recovery rates
        if request_metric.recovery_attempts > 0 and recovery_success_rate < 0.8:
            self.logger.warning(
                f"Poor recovery success rate in request {request_metric.endpoint}: "
                f"{recovery_success_rate:.1%} ({request_metric.successful_recoveries}/{request_metric.recovery_attempts})"
            )


# Global monitor instance
_global_monitor: Optional[SessionPerformanceMonitor] = None


def get_performance_monitor() -> SessionPerformanceMonitor:
    """
    Get the global performance monitor instance.
    
    Returns:
        SessionPerformanceMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SessionPerformanceMonitor()
    return _global_monitor


def initialize_performance_monitoring(app, session_manager, engine):
    """
    Initialize performance monitoring for the Flask application.
    
    Args:
        app: Flask application instance
        session_manager: RequestScopedSessionManager instance
        engine: SQLAlchemy engine instance
    """
    global _global_monitor
    _global_monitor = SessionPerformanceMonitor(f"{app.name}.session_performance")
    
    # Set up request-level monitoring
    @app.before_request
    def start_performance_monitoring():
        """Start performance monitoring for each request"""
        _global_monitor.start_request_monitoring()
        _global_monitor.update_pool_metrics(engine)
    
    @app.teardown_request
    def end_performance_monitoring(exception=None):
        """End performance monitoring for each request"""
        _global_monitor.end_request_monitoring()
        
        # Log periodic summary
        _global_monitor.log_periodic_summary()
    
    # Store monitor in app for access by other components
    app.session_performance_monitor = _global_monitor
    
    app.logger.info("Session performance monitoring initialized")
    return _global_monitor