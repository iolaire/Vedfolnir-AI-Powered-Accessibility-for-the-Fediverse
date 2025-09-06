# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Monitoring and Logging Infrastructure
Provides comprehensive monitoring, metrics collection, and diagnostic capabilities for session management
"""

import json
import time
import psutil
import gc
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from logging import getLogger
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from threading import Lock

from models import UserSession, User
from database import DatabaseManager
from security.core.security_utils import sanitize_for_log
from session_config import get_session_config, SessionConfig

logger = getLogger(__name__)

@dataclass
class SessionMetric:
    """Data class for session metrics"""
    timestamp: datetime
    metric_type: str
    session_id: str
    user_id: int
    value: float
    metadata: Dict[str, Any]

@dataclass
class SessionEvent:
    """Data class for session events"""
    timestamp: datetime
    event_type: str
    session_id: str
    user_id: int
    details: Dict[str, Any]
    severity: str = 'info'

@dataclass
class MemoryMetric:
    """Data class for memory metrics"""
    timestamp: datetime
    memory_usage_mb: float
    memory_percent: float
    available_memory_mb: float
    session_count: int
    gc_collections: Dict[str, int]
    object_counts: Dict[str, int]
    memory_growth_rate: float = 0.0

class SessionMonitor:
    """Comprehensive session monitoring and metrics collection for unified database sessions"""
    
    def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig] = None):
        self.db_manager = db_manager
        self.config = config or get_session_config()
        
        # Metrics storage
        self.metrics = deque(maxlen=10000)  # Keep last 10k metrics
        self.events = deque(maxlen=5000)    # Keep last 5k events
        self.metrics_lock = Lock()
        self.events_lock = Lock()
        self._lock = Lock()  # Main lock for thread safety
        
        # Initialize additional storage for monitoring
        self.metrics_buffer = deque(maxlen=1000)
        self.events_buffer = deque(maxlen=500)
        self.performance_stats = defaultdict(list)
        self.alert_thresholds = {
            'session_creation_rate': 10.0,
            'session_failure_rate': 0.1,
            'concurrent_sessions': 100
        }
        
        # Performance tracking
        self.session_performance = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.last_cleanup_time = datetime.now(timezone.utc)
        
        # Memory leak detection
        self.memory_metrics = deque(maxlen=1000)  # Keep last 1000 memory snapshots
        self.memory_lock = Lock()
        self.last_memory_check = datetime.now(timezone.utc)
        self.memory_baseline = None
        self.memory_growth_threshold = 50.0  # MB growth threshold
        self.memory_leak_alerts = deque(maxlen=100)
        
        # Memory pattern tracking
        self.session_memory_usage = defaultdict(float)  # Track memory per session
        self.object_growth_patterns = defaultdict(list)
        self.gc_stats_history = deque(maxlen=100)
        
        # Database session specific metrics
        self.db_session_metrics = {
            'total_sessions_created': 0,
            'total_sessions_destroyed': 0,
            'active_sessions': 0,
            'expired_sessions_cleaned': 0,
            'platform_switches': 0,
            'validation_failures': 0,
            'security_violations': 0
        }
        
        # Initialize monitoring
        self.log_system_startup()
    
    def log_database_session_created(self, session_id: str, user_id: int, platform_id: Optional[int] = None, 
                                   creation_time: float = None):
        """Log database session creation"""
        creation_time = creation_time or time.time()
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='database_session_created',
            session_id=session_id,
            user_id=user_id,
            details={
                'platform_id': platform_id,
                'creation_time_ms': creation_time * 1000,
                'session_type': 'database'
            }
        )
        
        self.log_event(event)
        
        # Record creation performance metric
        self.record_metric('session_creation_time', session_id, user_id, creation_time)
        
        logger.info(f"Database session created: {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))}")
    
    def log_database_session_destroyed(self, session_id: str, user_id: int, reason: str = 'logout'):
        """Log database session destruction"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='database_session_destroyed',
            session_id=session_id,
            user_id=user_id,
            details={
                'reason': reason,
                'session_type': 'database'
            }
        )
        
        self.log_event(event)
        logger.info(f"Database session destroyed: {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))}, reason: {reason}")
    
    def log_session_validation(self, session_id: str, user_id: int, is_valid: bool, 
                             validation_time: float = None, error: str = None):
        """Log session validation attempt"""
        validation_time = validation_time or time.time()
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_validation',
            session_id=session_id,
            user_id=user_id,
            details={
                'is_valid': is_valid,
                'validation_time_ms': validation_time * 1000,
                'error': error,
                'session_type': 'database'
            },
            severity='warning' if not is_valid else 'info'
        )
        
        self.log_event(event)
        
        # Record validation performance
        self.record_metric('session_validation_time', session_id, user_id, validation_time)
        
        if not is_valid:
            self.error_counts['validation_failed'] += 1
            logger.warning(f"Session validation failed: {sanitize_for_log(session_id)}, error: {error}")
    
    def log_platform_switch(self, session_id: str, user_id: int, old_platform_id: Optional[int], 
                           new_platform_id: int, switch_duration: float):
        """Log platform switch in database session"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='database_platform_switch',
            session_id=session_id,
            user_id=user_id,
            details={
                'old_platform_id': old_platform_id,
                'new_platform_id': new_platform_id,
                'switch_duration_ms': switch_duration * 1000,
                'session_type': 'database'
            }
        )
        
        self.log_event(event)
        
        # Record switch performance metric
        self.record_metric('database_platform_switch_duration', session_id, user_id, switch_duration)
        
        logger.info(f"Database session platform switch: {sanitize_for_log(session_id)}, "
                   f"from {old_platform_id} to {new_platform_id}")
    
    def log_session_activity_update(self, session_id: str, user_id: int, update_time: float = None):
        """Log session activity update"""
        update_time = update_time or time.time()
        
        # Only log every 5 minutes to avoid spam
        if not hasattr(self, '_last_activity_log'):
            self._last_activity_log = {}
        
        last_log = self._last_activity_log.get(session_id, 0)
        if update_time - last_log < 300:  # 5 minutes
            return
        
        self._last_activity_log[session_id] = update_time
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_activity_update',
            session_id=session_id,
            user_id=user_id,
            details={
                'update_time_ms': update_time * 1000,
                'session_type': 'database'
            }
        )
        
        self.log_event(event)
    
    def log_session_cleanup(self, cleaned_count: int, cleanup_type: str = 'expired'):
        """Log session cleanup operations"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='database_session_cleanup',
            session_id='system',
            user_id=0,
            details={
                'cleaned_count': cleaned_count,
                'cleanup_type': cleanup_type,
                'session_type': 'database'
            }
        )
        
        self.log_event(event)
        
        # Record cleanup metric
        self.record_metric('session_cleanup_count', 'system', 0, cleaned_count)
        
        logger.info(f"Database session cleanup: {cleaned_count} sessions cleaned ({cleanup_type})")
    
    def log_session_error(self, session_id: str, user_id: int, error_type: str, error_message: str):
        """Log session-related errors"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='database_session_error',
            session_id=session_id,
            user_id=user_id,
            details={
                'error_type': error_type,
                'error_message': error_message,
                'session_type': 'database'
            },
            severity='error'
        )
        
        self.log_event(event)
        
        # Track error counts
        self.error_counts[error_type] += 1
        self.record_metric('session_error_rate', session_id, user_id, 1.0)
        
        logger.error(f"Database session error: {sanitize_for_log(session_id)}, "
                    f"type: {error_type}, message: {sanitize_for_log(error_message)}")
    
    def log_cross_tab_sync(self, session_id: str, user_id: int, sync_type: str, sync_duration: float = None):
        """Log cross-tab synchronization events"""
        sync_duration = sync_duration or time.time()
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='cross_tab_sync',
            session_id=session_id,
            user_id=user_id,
            details={
                'sync_type': sync_type,
                'sync_duration_ms': sync_duration * 1000,
                'session_type': 'database'
            }
        )
        
        self.log_event(event)
        
        # Record sync performance
        self.record_metric('cross_tab_sync_duration', session_id, user_id, sync_duration)
    
    def get_database_session_metrics(self) -> Dict[str, Any]:
        """Get comprehensive database session metrics"""
        try:
            with self.db_manager.get_session() as db_session:
                # Active sessions
                active_sessions = db_session.query(UserSession).filter_by(is_active=True).count()
                
                # Total sessions
                total_sessions = db_session.query(UserSession).count()
                
                # Sessions by platform
                platform_sessions = db_session.query(
                    UserSession.active_platform_id,
                    db_session.query(UserSession).filter_by(
                        active_platform_id=UserSession.active_platform_id,
                        is_active=True
                    ).count().label('count')
                ).filter_by(is_active=True).group_by(UserSession.active_platform_id).all()
                
                # Recent activity (last hour)
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                recent_activity = db_session.query(UserSession).filter(
                    UserSession.last_activity > one_hour_ago,
                    UserSession.is_active == True
                ).count()
                
                # Expired sessions
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.expires_at < datetime.now(timezone.utc)
                ).count()
                
                return {
                    'active_sessions': active_sessions,
                    'total_sessions': total_sessions,
                    'recent_activity_count': recent_activity,
                    'expired_sessions': expired_sessions,
                    'platform_distribution': {
                        str(platform_id): count for platform_id, count in platform_sessions
                    },
                    'error_counts': dict(self.error_counts),
                    'last_cleanup': self.last_cleanup_time.isoformat(),
                    'session_type': 'database_only'
                }
                
        except Exception as e:
            logger.error(f"Error getting database session metrics: {e}")
            return {
                'error': str(e),
                'session_type': 'database_only'
            }
    
    def get_session_performance_stats(self) -> Dict[str, Any]:
        """Get session performance statistics"""
        with self.metrics_lock:
            if not self.metrics:
                return {'message': 'No metrics available'}
            
            # Group metrics by type
            metrics_by_type = defaultdict(list)
            for metric in self.metrics:
                metrics_by_type[metric.metric_type].append(metric.value)
            
            stats = {}
            for metric_type, values in metrics_by_type.items():
                if values:
                    stats[metric_type] = {
                        'count': len(values),
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'recent_avg': sum(values[-10:]) / min(len(values), 10)  # Last 10 values
                    }
            
            return {
                'performance_stats': stats,
                'total_metrics': len(self.metrics),
                'session_type': 'database_only'
            }
    
    def get_recent_session_events(self, limit: int = 100, event_type: str = None) -> List[Dict[str, Any]]:
        """Get recent session events"""
        with self.events_lock:
            events = list(self.events)
        
        # Filter by event type if specified
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Sort by timestamp (most recent first) and limit
        events.sort(key=lambda x: x.timestamp, reverse=True)
        events = events[:limit]
        
        return [asdict(event) for event in events]
    
    def log_system_startup(self):
        """Log system startup with database session info"""
        try:
            with self.db_manager.get_session() as db_session:
                active_sessions = db_session.query(UserSession).filter_by(is_active=True).count()
                
            startup_event = SessionEvent(
                timestamp=datetime.now(timezone.utc),
                event_type='system_startup',
                session_id='system',
                user_id=0,
                details={
                    'active_database_sessions': active_sessions,
                    'session_type': 'database_only',
                    'monitoring_initialized': True
                }
            )
            
            self.log_event(startup_event)
            logger.info(f"Session monitoring initialized - {active_sessions} active database sessions")
            
            # Initialize memory monitoring
            self._initialize_memory_monitoring()
            
        except Exception as e:
            logger.error(f"Error logging system startup: {e}")
    
    def record_metric(self, metric_type: str, session_id: str, user_id: int, 
                     value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a session metric"""
        metric = SessionMetric(
            timestamp=datetime.now(timezone.utc),
            metric_type=metric_type,
            session_id=session_id,
            user_id=user_id,
            value=value,
            metadata=metadata or {}
        )
        
        with self.metrics_lock:
            self.metrics.append(metric)
    
    def log_event(self, event: SessionEvent):
        """Log a session event"""
        with self.events_lock:
            self.events.append(event)
    
    def cleanup_old_metrics(self, max_age_hours: int = 24):
        """Clean up old metrics and events"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        with self.metrics_lock:
            # Remove old metrics
            self.metrics = deque(
                [m for m in self.metrics if m.timestamp > cutoff_time],
                maxlen=self.metrics.maxlen
            )
        
        with self.events_lock:
            # Remove old events
            self.events = deque(
                [e for e in self.events if e.timestamp > cutoff_time],
                maxlen=self.events.maxlen
            )
        
        self.last_cleanup_time = datetime.now(timezone.utc)
        logger.info(f"Cleaned up old session metrics and events (older than {max_age_hours} hours)")
    
    def _initialize_memory_monitoring(self):
        """Initialize memory leak detection monitoring"""
        try:
            # Take initial memory baseline
            memory_info = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            self.memory_baseline = {
                'system_memory_mb': memory_info.used / 1024 / 1024,
                'process_memory_mb': process_memory.rss / 1024 / 1024,
                'timestamp': datetime.now(timezone.utc)
            }
            
            logger.info(f"Memory monitoring initialized - baseline: {self.memory_baseline['process_memory_mb']:.1f}MB")
            
        except Exception as e:
            logger.error(f"Error initializing memory monitoring: {e}")
    
    def collect_memory_metrics(self) -> MemoryMetric:
        """Collect current memory usage metrics"""
        try:
            # System memory info
            memory_info = psutil.virtual_memory()
            
            # Process memory info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Garbage collection stats
            gc_stats = {}
            for i in range(3):  # GC generations 0, 1, 2
                gc_stats[f'gen_{i}'] = gc.get_count()[i]
            
            # Object counts for leak detection
            object_counts = {}
            try:
                # Count common object types that might leak
                object_counts['dict'] = len([obj for obj in gc.get_objects() if isinstance(obj, dict)])
                object_counts['list'] = len([obj for obj in gc.get_objects() if isinstance(obj, list)])
                object_counts['tuple'] = len([obj for obj in gc.get_objects() if isinstance(obj, tuple)])
                object_counts['function'] = len([obj for obj in gc.get_objects() if callable(obj)])
            except Exception as e:
                logger.debug(f"Error counting objects: {e}")
                object_counts = {'error': str(e)}
            
            # Get current session count
            with self.db_manager.get_session() as db_session:
                session_count = db_session.query(UserSession).filter_by(is_active=True).count()
            
            # Calculate memory growth rate
            memory_growth_rate = 0.0
            if self.memory_baseline:
                current_memory = process_memory.rss / 1024 / 1024
                baseline_memory = self.memory_baseline['process_memory_mb']
                memory_growth_rate = current_memory - baseline_memory
            
            metric = MemoryMetric(
                timestamp=datetime.now(timezone.utc),
                memory_usage_mb=process_memory.rss / 1024 / 1024,
                memory_percent=memory_info.percent,
                available_memory_mb=memory_info.available / 1024 / 1024,
                session_count=session_count,
                gc_collections=gc_stats,
                object_counts=object_counts,
                memory_growth_rate=memory_growth_rate
            )
            
            with self.memory_lock:
                self.memory_metrics.append(metric)
            
            return metric
            
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")
            return MemoryMetric(
                timestamp=datetime.now(timezone.utc),
                memory_usage_mb=0.0,
                memory_percent=0.0,
                available_memory_mb=0.0,
                session_count=0,
                gc_collections={},
                object_counts={'error': str(e)}
            )
    
    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks based on memory patterns"""
        alerts = []
        
        try:
            with self.memory_lock:
                if len(self.memory_metrics) < 10:  # Need at least 10 data points
                    return alerts
                
                recent_metrics = list(self.memory_metrics)[-10:]  # Last 10 measurements
                
                # Check for continuous memory growth
                memory_values = [m.memory_usage_mb for m in recent_metrics]
                if len(memory_values) >= 5:
                    # Calculate trend
                    x = list(range(len(memory_values)))
                    n = len(x)
                    sum_x = sum(x)
                    sum_y = sum(memory_values)
                    sum_xy = sum(x[i] * memory_values[i] for i in range(n))
                    sum_x2 = sum(x[i] ** 2 for i in range(n))
                    
                    # Linear regression slope
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                    
                    # Check for significant upward trend
                    if slope > 5.0:  # More than 5MB growth per measurement
                        alerts.append({
                            'type': 'memory_leak_suspected',
                            'severity': 'warning',
                            'message': f'Continuous memory growth detected: {slope:.1f}MB per measurement',
                            'details': {
                                'growth_rate_mb': slope,
                                'current_memory_mb': memory_values[-1],
                                'baseline_memory_mb': memory_values[0],
                                'measurements': len(memory_values)
                            },
                            'timestamp': datetime.now(timezone.utc)
                        })
                
                # Check for memory growth without session growth
                latest_metric = recent_metrics[-1]
                if len(recent_metrics) >= 5:
                    oldest_metric = recent_metrics[0]
                    memory_growth = latest_metric.memory_usage_mb - oldest_metric.memory_usage_mb
                    session_growth = latest_metric.session_count - oldest_metric.session_count
                    
                    # Alert if memory grew significantly but sessions didn't
                    if memory_growth > self.memory_growth_threshold and session_growth <= 0:
                        alerts.append({
                            'type': 'memory_growth_without_sessions',
                            'severity': 'warning',
                            'message': f'Memory grew {memory_growth:.1f}MB without session increase',
                            'details': {
                                'memory_growth_mb': memory_growth,
                                'session_growth': session_growth,
                                'current_memory_mb': latest_metric.memory_usage_mb,
                                'current_sessions': latest_metric.session_count
                            },
                            'timestamp': datetime.now(timezone.utc)
                        })
                
                # Check for excessive object growth
                if len(recent_metrics) >= 3:
                    latest_objects = latest_metric.object_counts
                    oldest_objects = recent_metrics[0].object_counts
                    
                    for obj_type in ['dict', 'list', 'tuple']:
                        if obj_type in latest_objects and obj_type in oldest_objects:
                            growth = latest_objects[obj_type] - oldest_objects[obj_type]
                            if growth > 10000:  # More than 10k new objects
                                alerts.append({
                                    'type': 'object_growth_detected',
                                    'severity': 'info',
                                    'message': f'High {obj_type} object growth: {growth} new objects',
                                    'details': {
                                        'object_type': obj_type,
                                        'growth_count': growth,
                                        'current_count': latest_objects[obj_type],
                                        'previous_count': oldest_objects[obj_type]
                                    },
                                    'timestamp': datetime.now(timezone.utc)
                                })
                
                # Store alerts for history
                for alert in alerts:
                    self.memory_leak_alerts.append(alert)
                    
                    # Log alerts
                    severity = alert['severity']
                    message = alert['message']
                    if severity == 'warning':
                        logger.warning(f"Memory leak detection: {message}")
                    else:
                        logger.info(f"Memory monitoring: {message}")
            
        except Exception as e:
            logger.error(f"Error in memory leak detection: {e}")
            alerts.append({
                'type': 'memory_detection_error',
                'severity': 'error',
                'message': f'Memory leak detection failed: {str(e)}',
                'timestamp': datetime.now(timezone.utc)
            })
        
        return alerts
    
    def trigger_memory_cleanup(self) -> Dict[str, Any]:
        """Trigger automated memory cleanup procedures"""
        cleanup_results = {
            'timestamp': datetime.now(timezone.utc),
            'actions_taken': [],
            'memory_before_mb': 0.0,
            'memory_after_mb': 0.0,
            'cleanup_successful': False
        }
        
        try:
            # Get memory before cleanup
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024
            cleanup_results['memory_before_mb'] = memory_before
            
            # Force garbage collection
            collected_objects = []
            for generation in range(3):
                collected = gc.collect(generation)
                collected_objects.append(collected)
                cleanup_results['actions_taken'].append(f'GC generation {generation}: {collected} objects')
            
            # Clean up expired sessions
            with self.db_manager.get_session() as db_session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at < cutoff_time,
                    UserSession.is_active == False
                ).count()
                
                if expired_sessions > 0:
                    db_session.query(UserSession).filter(
                        UserSession.updated_at < cutoff_time,
                        UserSession.is_active == False
                    ).delete()
                    db_session.commit()
                    cleanup_results['actions_taken'].append(f'Cleaned {expired_sessions} expired sessions')
            
            # Clear old metrics to free memory
            with self.memory_lock:
                old_count = len(self.memory_metrics)
                # Keep only last 500 metrics
                if old_count > 500:
                    self.memory_metrics = deque(list(self.memory_metrics)[-500:], maxlen=1000)
                    cleanup_results['actions_taken'].append(f'Cleared {old_count - 500} old memory metrics')
            
            # Clear old events
            with self.events_lock:
                old_count = len(self.events)
                if old_count > 2500:
                    self.events = deque(list(self.events)[-2500:], maxlen=5000)
                    cleanup_results['actions_taken'].append(f'Cleared {old_count - 2500} old events')
            
            # Get memory after cleanup
            memory_after = process.memory_info().rss / 1024 / 1024
            cleanup_results['memory_after_mb'] = memory_after
            cleanup_results['memory_freed_mb'] = memory_before - memory_after
            cleanup_results['cleanup_successful'] = True
            
            logger.info(f"Memory cleanup completed: freed {cleanup_results['memory_freed_mb']:.1f}MB")
            
        except Exception as e:
            logger.error(f"Error in memory cleanup: {e}")
            cleanup_results['error'] = str(e)
            cleanup_results['cleanup_successful'] = False
        
        return cleanup_results
    
    def get_memory_leak_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory leak detection report"""
        try:
            # Collect current metrics
            current_metric = self.collect_memory_metrics()
            
            # Detect leaks
            leak_alerts = self.detect_memory_leaks()
            
            # Calculate memory statistics
            with self.memory_lock:
                if self.memory_metrics:
                    memory_values = [m.memory_usage_mb for m in self.memory_metrics]
                    memory_stats = {
                        'current_mb': current_metric.memory_usage_mb,
                        'min_mb': min(memory_values),
                        'max_mb': max(memory_values),
                        'avg_mb': sum(memory_values) / len(memory_values),
                        'growth_from_baseline_mb': current_metric.memory_growth_rate,
                        'measurements_count': len(memory_values)
                    }
                else:
                    memory_stats = {'error': 'No memory metrics available'}
            
            # Get recent alerts
            recent_alerts = list(self.memory_leak_alerts)[-20:]  # Last 20 alerts
            
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'memory_statistics': memory_stats,
                'current_metrics': {
                    'memory_usage_mb': current_metric.memory_usage_mb,
                    'memory_percent': current_metric.memory_percent,
                    'available_memory_mb': current_metric.available_memory_mb,
                    'session_count': current_metric.session_count,
                    'gc_collections': current_metric.gc_collections,
                    'object_counts': current_metric.object_counts
                },
                'leak_detection': {
                    'current_alerts': leak_alerts,
                    'recent_alerts': recent_alerts,
                    'total_alerts': len(self.memory_leak_alerts)
                },
                'recommendations': self._generate_memory_recommendations(current_metric, leak_alerts)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating memory leak report: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'recommendations': ['Fix memory monitoring system']
            }
    
    def _generate_memory_recommendations(self, current_metric: MemoryMetric, alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        try:
            # Check memory usage level
            if current_metric.memory_usage_mb > 1000:  # More than 1GB
                recommendations.append("High memory usage detected - consider implementing memory limits")
            
            # Check for leak alerts
            leak_alerts = [a for a in alerts if a['type'] == 'memory_leak_suspected']
            if leak_alerts:
                recommendations.append("Memory leak suspected - review session cleanup and object lifecycle")
            
            # Check session to memory ratio
            if current_metric.session_count > 0:
                memory_per_session = current_metric.memory_usage_mb / current_metric.session_count
                if memory_per_session > 10:  # More than 10MB per session
                    recommendations.append(f"High memory per session ({memory_per_session:.1f}MB) - optimize session data storage")
            
            # Check object growth
            object_growth_alerts = [a for a in alerts if a['type'] == 'object_growth_detected']
            if object_growth_alerts:
                recommendations.append("High object growth detected - review object creation and cleanup")
            
            # Check GC efficiency
            if 'gen_0' in current_metric.gc_collections and current_metric.gc_collections['gen_0'] > 1000:
                recommendations.append("High GC activity - consider optimizing object creation patterns")
            
            # Default recommendation if no issues
            if not recommendations:
                recommendations.append("Memory usage appears normal - continue monitoring")
                
        except Exception as e:
            logger.error(f"Error generating memory recommendations: {e}")
            recommendations.append("Error generating recommendations - review memory monitoring system")
        
        return recommendations
    
    def get_monitoring_health(self) -> Dict[str, Any]:
        """Get monitoring system health status"""
        return {
            'status': 'healthy',
            'metrics_count': len(self.metrics),
            'events_count': len(self.events),
            'error_counts': dict(self.error_counts),
            'last_cleanup': self.last_cleanup_time.isoformat(),
            'session_type': 'database_only',
            'monitoring_active': True
        }
    
    def _initialize_monitoring(self):
        """Initialize monitoring system"""
        logger.info("Initializing session monitoring system")
        
        # Log initial system state
        self.log_system_startup()
    
    def log_system_startup(self):
        """Log system startup information"""
        try:
            with self.db_manager.get_session() as db_session:
                active_sessions = db_session.query(UserSession).filter_by(is_active=True).count()
                total_sessions = db_session.query(UserSession).count()
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.expires_at < datetime.now(timezone.utc)
                ).count()
                
            self.db_session_metrics['active_sessions'] = active_sessions
                
            startup_event = SessionEvent(
                timestamp=datetime.now(timezone.utc),
                event_type='system_startup',
                session_id='system',
                user_id=0,
                details={
                    'active_sessions_at_startup': active_sessions,
                    'total_sessions_at_startup': total_sessions,
                    'expired_sessions_at_startup': expired_sessions,
                    'monitoring_initialized': True,
                    'session_type': 'database_only'
                },
                severity='info'
            )
            
            self.record_event(startup_event)
            logger.info(f"Session monitoring initialized - {active_sessions} active sessions")
            
        except Exception as e:
            logger.error(f"Error logging system startup: {e}")
    
    def record_metric(self, metric_type: str, session_id: str, user_id: int, 
                     value: float, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a session metric
        
        Args:
            metric_type: Type of metric (e.g., 'session_duration', 'sync_time')
            session_id: Session ID
            user_id: User ID
            value: Metric value
            metadata: Additional metadata
        """
        try:
            metric = SessionMetric(
                timestamp=datetime.now(timezone.utc),
                metric_type=metric_type,
                session_id=session_id,
                user_id=user_id,
                value=value,
                metadata=metadata or {}
            )
            
            with self._lock:
                self.metrics_buffer.append(metric)
                self.performance_stats[metric_type].append(value)
                
                # Keep only recent performance stats
                if len(self.performance_stats[metric_type]) > 100:
                    self.performance_stats[metric_type] = self.performance_stats[metric_type][-100:]
            
            # Check for alerts
            self._check_metric_alerts(metric)
            
            logger.debug(f"Recorded metric: {metric_type} = {value} for session {sanitize_for_log(session_id)}")
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def record_event(self, event: SessionEvent):
        """
        Record a session event
        
        Args:
            event: SessionEvent object
        """
        try:
            with self._lock:
                self.events_buffer.append(event)
            
            # Log event based on severity
            log_message = f"Session event: {event.event_type} for session {sanitize_for_log(event.session_id)}"
            
            if event.severity == 'error':
                logger.error(log_message)
            elif event.severity == 'warning':
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # Check for alerts
            self._check_event_alerts(event)
            
        except Exception as e:
            logger.error(f"Error recording event: {e}")
    
    def log_session_created(self, session_id: str, user_id: int, platform_id: Optional[int] = None):
        """Log session creation"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_created',
            session_id=session_id,
            user_id=user_id,
            details={
                'platform_id': platform_id,
                'creation_method': 'standard'
            }
        )
        self.record_event(event)
        
        # Record creation rate metric
        self.record_metric('session_creation_rate', session_id, user_id, 1.0)
    
    def log_session_expired(self, session_id: str, user_id: int, reason: str = 'timeout'):
        """Log session expiration"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_expired',
            session_id=session_id,
            user_id=user_id,
            details={
                'expiration_reason': reason,
                'cleanup_performed': True
            },
            severity='info'
        )
        self.record_event(event)
    
    def log_session_error(self, session_id: str, user_id: int, error_type: str, error_details: str):
        """Log session error"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='session_error',
            session_id=session_id,
            user_id=user_id,
            details={
                'error_type': error_type,
                'error_details': sanitize_for_log(error_details)
            },
            severity='error'
        )
        self.record_event(event)
        
        # Record error rate metric
        self.record_metric('session_error_rate', session_id, user_id, 1.0)
    
    def log_platform_switch(self, session_id: str, user_id: int, old_platform_id: Optional[int], 
                           new_platform_id: int, switch_duration: float):
        """Log platform switch"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='platform_switch',
            session_id=session_id,
            user_id=user_id,
            details={
                'old_platform_id': old_platform_id,
                'new_platform_id': new_platform_id,
                'switch_duration_ms': switch_duration
            }
        )
        self.record_event(event)
        
        # Record switch performance metric
        self.record_metric('platform_switch_duration', session_id, user_id, switch_duration)
    
    def log_suspicious_activity(self, session_id: str, user_id: int, activity_type: str, details: Dict[str, Any]):
        """Log suspicious session activity"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='suspicious_activity',
            session_id=session_id,
            user_id=user_id,
            details={
                'activity_type': activity_type,
                **details
            },
            severity='warning'
        )
        self.record_event(event)
        
        # Record suspicious activity metric
        self.record_metric('suspicious_activity_rate', session_id, user_id, 1.0)
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive session statistics
        
        Returns:
            Dictionary with session statistics
        """
        try:
            with self.db_manager.get_session() as db_session:
                # Get basic session counts
                total_sessions = db_session.query(UserSession).count()
                
                # Get active sessions (not expired)
                now = datetime.now(timezone.utc)
                cutoff_time = now - timedelta(hours=48)  # Default session timeout
                
                active_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at >= cutoff_time
                ).count()
                
                # Get user statistics
                unique_users = db_session.query(UserSession.user_id).distinct().count()
            
            # Calculate performance statistics
            with self._lock:
                performance_stats = {}
                for metric_type, values in self.performance_stats.items():
                    if values:
                        performance_stats[metric_type] = {
                            'count': len(values),
                            'avg': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values),
                            'recent': values[-10:] if len(values) >= 10 else values
                        }
                
                # Get recent events summary
                recent_events = list(self.events_buffer)[-50:]  # Last 50 events
                event_summary = defaultdict(int)
                for event in recent_events:
                    event_summary[event.event_type] += 1
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'session_counts': {
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'unique_users': unique_users
                },
                'performance_stats': performance_stats,
                'recent_events': dict(event_summary),
                'monitoring_health': {
                    'metrics_buffer_size': len(self.metrics_buffer),
                    'events_buffer_size': len(self.events_buffer),
                    'monitoring_active': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {'error': str(e)}
    
    def get_session_health_report(self) -> Dict[str, Any]:
        """
        Generate session health report
        
        Returns:
            Dictionary with health report
        """
        try:
            stats = self.get_session_statistics()
            
            # Analyze health indicators
            health_indicators = {
                'overall_health': 'good',
                'issues': [],
                'recommendations': []
            }
            
            # Check session creation rate
            if 'session_creation_rate' in stats.get('performance_stats', {}):
                creation_stats = stats['performance_stats']['session_creation_rate']
                if creation_stats['avg'] > self.alert_thresholds['session_creation_rate']:
                    health_indicators['issues'].append('High session creation rate detected')
                    health_indicators['overall_health'] = 'warning'
            
            # Check error rates
            if 'session_error_rate' in stats.get('performance_stats', {}):
                error_stats = stats['performance_stats']['session_error_rate']
                if error_stats['avg'] > self.alert_thresholds['session_failure_rate']:
                    health_indicators['issues'].append('High session error rate detected')
                    health_indicators['overall_health'] = 'critical'
            
            # Check concurrent sessions
            active_sessions = stats.get('session_counts', {}).get('active_sessions', 0)
            if active_sessions > self.alert_thresholds['concurrent_sessions']:
                health_indicators['issues'].append('High number of concurrent sessions')
                health_indicators['overall_health'] = 'warning'
            
            # Generate recommendations
            if not health_indicators['issues']:
                health_indicators['recommendations'].append('Session system is operating normally')
            else:
                health_indicators['recommendations'].append('Review session management configuration')
                health_indicators['recommendations'].append('Consider implementing session cleanup policies')
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'health_status': health_indicators,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {'error': str(e)}
    
    def _check_metric_alerts(self, metric: SessionMetric):
        """Check if metric triggers any alerts"""
        try:
            # Implement alert logic based on thresholds
            if metric.metric_type in self.alert_thresholds:
                threshold = self.alert_thresholds[metric.metric_type]
                
                if metric.value > threshold:
                    logger.warning(f"Alert: {metric.metric_type} value {metric.value} exceeds threshold {threshold}")
                    
                    # Record alert event
                    alert_event = SessionEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type='metric_alert',
                        session_id=metric.session_id,
                        user_id=metric.user_id,
                        details={
                            'metric_type': metric.metric_type,
                            'value': metric.value,
                            'threshold': threshold
                        },
                        severity='warning'
                    )
                    self.record_event(alert_event)
                    
        except Exception as e:
            logger.error(f"Error checking metric alerts: {e}")
    
    def _check_event_alerts(self, event: SessionEvent):
        """Check if event triggers any alerts"""
        try:
            # Count recent events of the same type
            recent_events = [e for e in self.events_buffer 
                           if e.event_type == event.event_type 
                           and (datetime.now(timezone.utc) - e.timestamp).total_seconds() < 60]
            
            # Alert on high frequency of certain events
            if event.event_type in ['session_error', 'suspicious_activity'] and len(recent_events) > 5:
                logger.warning(f"Alert: High frequency of {event.event_type} events: {len(recent_events)} in last minute")
                
        except Exception as e:
            logger.error(f"Error checking event alerts: {e}")
    
    def export_metrics(self, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Export metrics for external analysis
        
        Args:
            start_time: Start time for export (optional)
            end_time: End time for export (optional)
            
        Returns:
            List of metric dictionaries
        """
        try:
            with self._lock:
                metrics = list(self.metrics_buffer)
            
            # Filter by time range if specified
            if start_time or end_time:
                filtered_metrics = []
                for metric in metrics:
                    if start_time and metric.timestamp < start_time:
                        continue
                    if end_time and metric.timestamp > end_time:
                        continue
                    filtered_metrics.append(metric)
                metrics = filtered_metrics
            
            # Convert to dictionaries
            return [asdict(metric) for metric in metrics]
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int = 7):
        """
        Clean up old monitoring data
        
        Args:
            retention_days: Number of days to retain data
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            with self._lock:
                # Clean up old metrics
                self.metrics_buffer = deque(
                    [m for m in self.metrics_buffer if m.timestamp >= cutoff_time],
                    maxlen=1000
                )
                
                # Clean up old events
                self.events_buffer = deque(
                    [e for e in self.events_buffer if e.timestamp >= cutoff_time],
                    maxlen=500
                )
            
            logger.info(f"Cleaned up monitoring data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old monitoring data: {e}")

# Global session monitor instance
session_monitor = None

def get_session_monitor(db_manager: DatabaseManager, config: Optional[SessionConfig] = None) -> Optional[SessionMonitor]:
    """Get or create global session monitor instance"""
    global session_monitor
    if session_monitor is None:
        session_config = config or get_session_config()
        if session_config.monitoring.enable_performance_monitoring:
            session_monitor = SessionMonitor(db_manager, session_config)
        else:
            return None
    return session_monitor

    def log_database_session_created(self, session_id: str, user_id: int, platform_id: Optional[int] = None):
        """Log database session creation"""
        self.db_session_metrics['total_sessions_created'] += 1
        self.db_session_metrics['active_sessions'] += 1
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_session_created',
            session_id=session_id,
            user_id=user_id,
            details={
                'platform_id': platform_id,
                'session_type': 'database',
                'total_created': self.db_session_metrics['total_sessions_created']
            }
        )
        
        with self.events_lock:
            self.events.append(event)
        
        # Record creation performance metric
        self.record_metric('session_creation', session_id, user_id, 1.0)
        
        logger.info(f"Database session created: {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))}")
    
    def log_database_session_destroyed(self, session_id: str, user_id: int, reason: str = 'logout'):
        """Log database session destruction"""
        self.db_session_metrics['total_sessions_destroyed'] += 1
        self.db_session_metrics['active_sessions'] = max(0, self.db_session_metrics['active_sessions'] - 1)
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_session_destroyed',
            session_id=session_id,
            user_id=user_id,
            details={
                'reason': reason,
                'session_type': 'database',
                'total_destroyed': self.db_session_metrics['total_sessions_destroyed']
            }
        )
        
        with self.events_lock:
            self.events.append(event)
        
        logger.info(f"Database session destroyed: {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))}, reason: {reason}")
    
    def log_database_session_validation_failure(self, session_id: str, user_id: int, failure_reason: str):
        """Log database session validation failure"""
        self.db_session_metrics['validation_failures'] += 1
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_session_validation_failed',
            session_id=session_id,
            user_id=user_id,
            details={
                'failure_reason': failure_reason,
                'session_type': 'database',
                'total_failures': self.db_session_metrics['validation_failures']
            },
            severity='warning'
        )
        
        with self.events_lock:
            self.events.append(event)
        
        # Record error metric
        self.record_metric('session_validation_error', session_id, user_id, 1.0)
        
        logger.warning(f"Database session validation failed: {sanitize_for_log(session_id)}, reason: {failure_reason}")
    
    def log_database_session_expired(self, session_id: str, user_id: int):
        """Log database session expiration"""
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_session_expired',
            session_id=session_id,
            user_id=user_id,
            details={
                'session_type': 'database',
                'auto_cleanup': True
            },
            severity='info'
        )
        
        with self.events_lock:
            self.events.append(event)
        
        logger.info(f"Database session expired: {sanitize_for_log(session_id)} for user {sanitize_for_log(str(user_id))}")
    
    def log_database_platform_switch(self, session_id: str, user_id: int, old_platform_id: Optional[int], 
                                   new_platform_id: int, switch_duration: float):
        """Log database session platform switch"""
        self.db_session_metrics['platform_switches'] += 1
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_platform_switch',
            session_id=session_id,
            user_id=user_id,
            details={
                'old_platform_id': old_platform_id,
                'new_platform_id': new_platform_id,
                'switch_duration_ms': switch_duration * 1000,
                'session_type': 'database',
                'total_switches': self.db_session_metrics['platform_switches']
            }
        )
        
        with self.events_lock:
            self.events.append(event)
        
        # Record switch performance metric
        self.record_metric('db_platform_switch_duration', session_id, user_id, switch_duration)
        
        logger.info(f"Database platform switch: session {sanitize_for_log(session_id)}, platform {old_platform_id} -> {new_platform_id}")
    
    def log_database_session_cleanup(self, cleaned_count: int, cleanup_type: str = 'expired'):
        """Log database session cleanup operation"""
        self.db_session_metrics['expired_sessions_cleaned'] += cleaned_count
        self.db_session_metrics['active_sessions'] = max(0, self.db_session_metrics['active_sessions'] - cleaned_count)
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_session_cleanup',
            session_id='system',
            user_id=0,
            details={
                'cleaned_count': cleaned_count,
                'cleanup_type': cleanup_type,
                'session_type': 'database',
                'total_cleaned': self.db_session_metrics['expired_sessions_cleaned']
            }
        )
        
        with self.events_lock:
            self.events.append(event)
        
        # Record cleanup metric
        self.record_metric('db_session_cleanup_count', 'system', 0, cleaned_count)
        
        logger.info(f"Database session cleanup: {cleaned_count} {cleanup_type} sessions cleaned")
    
    def log_database_session_security_violation(self, session_id: str, user_id: int, violation_type: str, details: Dict[str, Any]):
        """Log database session security violation"""
        self.db_session_metrics['security_violations'] += 1
        
        event = SessionEvent(
            timestamp=datetime.now(timezone.utc),
            event_type='db_session_security_violation',
            session_id=session_id,
            user_id=user_id,
            details={
                'violation_type': violation_type,
                'session_type': 'database',
                'violation_details': details,
                'total_violations': self.db_session_metrics['security_violations']
            },
            severity='error'
        )
        
        with self.events_lock:
            self.events.append(event)
        
        # Record security violation metric
        self.record_metric('db_session_security_violation', session_id, user_id, 1.0)
        
        logger.error(f"Database session security violation: {sanitize_for_log(session_id)}, type: {violation_type}")
    
    def get_database_session_metrics(self) -> Dict[str, Any]:
        """Get current database session metrics"""
        try:
            with self.db_manager.get_session() as db_session:
                # Get real-time database statistics
                active_sessions = db_session.query(UserSession).filter_by(is_active=True).count()
                total_sessions = db_session.query(UserSession).count()
                expired_sessions = db_session.query(UserSession).filter(
                    UserSession.expires_at < datetime.now(timezone.utc)
                ).count()
                
                # Get session age statistics
                oldest_session = db_session.query(UserSession).filter_by(is_active=True).order_by(UserSession.created_at).first()
                newest_session = db_session.query(UserSession).filter_by(is_active=True).order_by(UserSession.created_at.desc()).first()
                
                # Update metrics
                self.db_session_metrics['active_sessions'] = active_sessions
                
                return {
                    **self.db_session_metrics,
                    'real_time_active_sessions': active_sessions,
                    'real_time_total_sessions': total_sessions,
                    'real_time_expired_sessions': expired_sessions,
                    'oldest_session_age_hours': (
                        (datetime.now(timezone.utc) - oldest_session.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                        if oldest_session else 0
                    ),
                    'newest_session_age_minutes': (
                        (datetime.now(timezone.utc) - newest_session.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
                        if newest_session else 0
                    ),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting database session metrics: {e}")
            return {
                **self.db_session_metrics,
                'error': str(e),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    def get_database_session_health_status(self) -> Dict[str, Any]:
        """Get database session system health status"""
        try:
            metrics = self.get_database_session_metrics()
            
            # Calculate health indicators
            active_sessions = metrics.get('real_time_active_sessions', 0)
            validation_failures = metrics.get('validation_failures', 0)
            security_violations = metrics.get('security_violations', 0)
            
            # Determine health status
            health_status = 'healthy'
            issues = []
            
            if validation_failures > 10:
                health_status = 'warning'
                issues.append(f'High validation failures: {validation_failures}')
            
            if security_violations > 0:
                health_status = 'critical'
                issues.append(f'Security violations detected: {security_violations}')
            
            if active_sessions > 1000:
                health_status = 'warning'
                issues.append(f'High active session count: {active_sessions}')
            
            return {
                'status': health_status,
                'active_sessions': active_sessions,
                'validation_failures': validation_failures,
                'security_violations': security_violations,
                'issues': issues,
                'last_check': datetime.now(timezone.utc).isoformat(),
                'session_type': 'database_only'
            }
            
        except Exception as e:
            logger.error(f"Error getting database session health status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat(),
                'session_type': 'database_only'
            }
    
    def generate_database_session_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive database session report"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter events and metrics for the time period
            recent_events = [
                event for event in self.events 
                if event.timestamp >= cutoff_time and 'db_' in event.event_type
            ]
            
            recent_metrics = [
                metric for metric in self.metrics 
                if metric.timestamp >= cutoff_time and 'db_' in metric.metric_type
            ]
            
            # Analyze events
            event_counts = defaultdict(int)
            for event in recent_events:
                event_counts[event.event_type] += 1
            
            # Analyze metrics
            metric_stats = defaultdict(list)
            for metric in recent_metrics:
                metric_stats[metric.metric_type].append(metric.value)
            
            # Calculate averages
            metric_averages = {}
            for metric_type, values in metric_stats.items():
                if values:
                    metric_averages[metric_type] = {
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
            
            return {
                'report_period_hours': hours,
                'report_generated': datetime.now(timezone.utc).isoformat(),
                'session_type': 'database_only',
                'current_metrics': self.get_database_session_metrics(),
                'health_status': self.get_database_session_health_status(),
                'event_summary': dict(event_counts),
                'metric_summary': metric_averages,
                'total_events': len(recent_events),
                'total_metrics': len(recent_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error generating database session report: {e}")
            return {
                'error': str(e),
                'report_generated': datetime.now(timezone.utc).isoformat(),
                'session_type': 'database_only'
            }

def create_database_session_monitor(db_manager: DatabaseManager, config: Optional[SessionConfig] = None) -> SessionMonitor:
    """
    Create session monitor for database sessions
    
    Args:
        db_manager: Database manager instance
        config: Optional session configuration
        
    Returns:
        SessionMonitor instance configured for database sessions
    """
    monitor = SessionMonitor(db_manager, config)
    logger.info("Database session monitor created and initialized")
    return monitor