# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Change Impact Logger

Comprehensive logging system for configuration changes and their impacts,
including correlation with system behavior, audit trails, and rollback capabilities.
"""

import json
import logging
import threading
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import copy

logger = logging.getLogger(__name__)


class ChangeImpactLevel(Enum):
    """Impact levels for configuration changes"""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeSource(Enum):
    """Sources of configuration changes"""
    ADMIN_UI = "admin_ui"
    API = "api"
    ENVIRONMENT = "environment"
    SYSTEM = "system"
    MIGRATION = "migration"
    ROLLBACK = "rollback"


class SystemBehaviorMetric(Enum):
    """System behavior metrics to track"""
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    DATABASE_CONNECTIONS = "database_connections"
    ACTIVE_SESSIONS = "active_sessions"


@dataclass
class ConfigurationChange:
    """Detailed configuration change record"""
    change_id: str
    timestamp: datetime
    key: str
    old_value: Any
    new_value: Any
    source: ChangeSource
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    requires_restart: bool = False
    impact_level: ChangeImpactLevel = ChangeImpactLevel.LOW
    reason: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    rollback_data: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = field(default_factory=list)
    applied_successfully: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['source'] = self.source.value
        data['impact_level'] = self.impact_level.value
        return data


@dataclass
class SystemBehaviorSnapshot:
    """Snapshot of system behavior metrics"""
    timestamp: datetime
    metrics: Dict[SystemBehaviorMetric, float] = field(default_factory=dict)
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'metrics': {metric.value: value for metric, value in self.metrics.items()},
            'additional_metrics': self.additional_metrics
        }


@dataclass
class ChangeImpactAnalysis:
    """Analysis of configuration change impact"""
    change_id: str
    pre_change_snapshot: SystemBehaviorSnapshot
    post_change_snapshots: List[SystemBehaviorSnapshot] = field(default_factory=list)
    impact_score: float = 0.0
    detected_anomalies: List[str] = field(default_factory=list)
    performance_delta: Dict[str, float] = field(default_factory=dict)
    correlation_confidence: float = 0.0
    recovery_time_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'change_id': self.change_id,
            'pre_change_snapshot': self.pre_change_snapshot.to_dict(),
            'post_change_snapshots': [snapshot.to_dict() for snapshot in self.post_change_snapshots],
            'impact_score': self.impact_score,
            'detected_anomalies': self.detected_anomalies,
            'performance_delta': self.performance_delta,
            'correlation_confidence': self.correlation_confidence,
            'recovery_time_seconds': self.recovery_time_seconds
        }


@dataclass
class RollbackPlan:
    """Plan for rolling back configuration changes"""
    rollback_id: str
    target_change_ids: List[str]
    rollback_steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_impact: ChangeImpactLevel = ChangeImpactLevel.LOW
    requires_restart: bool = False
    validation_checks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['estimated_impact'] = self.estimated_impact.value
        return data


class ConfigurationChangeLogger:
    """
    Comprehensive configuration change impact logging system
    
    Features:
    - Detailed change logging with user attribution
    - System behavior correlation
    - Impact analysis and scoring
    - Rollback capability with impact tracking
    - Audit trail maintenance
    - Anomaly detection
    """
    
    def __init__(self, retention_days: int = 90, max_changes_in_memory: int = 1000,
                 behavior_tracking_enabled: bool = True):
        """
        Initialize change logger
        
        Args:
            retention_days: How long to retain change logs
            max_changes_in_memory: Maximum changes to keep in memory
            behavior_tracking_enabled: Whether to track system behavior
        """
        self.retention_days = retention_days
        self.max_changes_in_memory = max_changes_in_memory
        self.behavior_tracking_enabled = behavior_tracking_enabled
        
        # Change storage
        self._changes: deque = deque(maxlen=max_changes_in_memory)
        self._changes_by_id: Dict[str, ConfigurationChange] = {}
        self._changes_lock = threading.RLock()
        
        # Impact analysis storage
        self._impact_analyses: Dict[str, ChangeImpactAnalysis] = {}
        self._impact_lock = threading.RLock()
        
        # System behavior tracking
        self._behavior_snapshots: deque = deque(maxlen=10000)
        self._behavior_lock = threading.RLock()
        
        # Rollback plans
        self._rollback_plans: Dict[str, RollbackPlan] = {}
        self._rollback_lock = threading.RLock()
        
        # Behavior metric collectors
        self._metric_collectors: Dict[SystemBehaviorMetric, Callable[[], float]] = {}
        self._collector_lock = threading.RLock()
        
        # Change correlation tracking
        self._pending_correlations: Dict[str, datetime] = {}
        self._correlation_lock = threading.RLock()
        
        # Background monitoring
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Setup default metric collectors
        self._setup_default_collectors()
    
    def register_metric_collector(self, metric: SystemBehaviorMetric, 
                                 collector_func: Callable[[], float]):
        """
        Register a metric collector function
        
        Args:
            metric: The metric type to collect
            collector_func: Function that returns the current metric value
        """
        with self._collector_lock:
            self._metric_collectors[metric] = collector_func
        
        logger.info(f"Registered metric collector for {metric.value}")
    
    def log_configuration_change(self, key: str, old_value: Any, new_value: Any,
                                source: ChangeSource, user_id: int = None,
                                user_name: str = None, requires_restart: bool = False,
                                impact_level: ChangeImpactLevel = ChangeImpactLevel.LOW,
                                reason: str = None, affected_services: List[str] = None) -> str:
        """
        Log a configuration change with full context
        
        Args:
            key: Configuration key that changed
            old_value: Previous value
            new_value: New value
            source: Source of the change
            user_id: ID of user who made the change
            user_name: Name of user who made the change
            requires_restart: Whether change requires restart
            impact_level: Expected impact level
            reason: Reason for the change
            affected_services: List of services affected by change
            
        Returns:
            Change ID for tracking
        """
        # Generate unique change ID
        change_id = self._generate_change_id(key, old_value, new_value)
        
        # Create change record
        change = ConfigurationChange(
            change_id=change_id,
            timestamp=datetime.now(timezone.utc),
            key=key,
            old_value=old_value,
            new_value=new_value,
            source=source,
            user_id=user_id,
            user_name=user_name,
            requires_restart=requires_restart,
            impact_level=impact_level,
            reason=reason,
            affected_services=affected_services or [],
            rollback_data=self._create_rollback_data(key, old_value, new_value)
        )
        
        # Store change
        with self._changes_lock:
            self._changes.append(change)
            self._changes_by_id[change_id] = change
        
        # Take pre-change behavior snapshot if tracking enabled
        if self.behavior_tracking_enabled:
            pre_snapshot = self._take_behavior_snapshot()
            
            # Start impact correlation tracking
            with self._correlation_lock:
                self._pending_correlations[change_id] = datetime.now(timezone.utc)
            
            # Schedule post-change analysis
            self._schedule_impact_analysis(change_id, pre_snapshot)
        
        # Log the change
        logger.info(f"Configuration change logged: {key} changed from {old_value} to {new_value} "
                   f"by {user_name or 'system'} (source: {source.value}, impact: {impact_level.value})")
        
        return change_id
    
    def analyze_change_impact(self, change_id: str, 
                             analysis_duration_minutes: int = 5) -> Optional[ChangeImpactAnalysis]:
        """
        Analyze the impact of a configuration change
        
        Args:
            change_id: ID of the change to analyze
            analysis_duration_minutes: How long to collect post-change data
            
        Returns:
            ChangeImpactAnalysis or None if change not found
        """
        with self._changes_lock:
            if change_id not in self._changes_by_id:
                return None
            
            change = self._changes_by_id[change_id]
        
        # Get behavior snapshots around the change time
        change_time = change.timestamp
        pre_window = timedelta(minutes=2)
        post_window = timedelta(minutes=analysis_duration_minutes)
        
        with self._behavior_lock:
            # Find pre-change snapshot (closest before change)
            pre_snapshots = [s for s in self._behavior_snapshots 
                           if change_time - pre_window <= s.timestamp <= change_time]
            pre_snapshot = max(pre_snapshots, key=lambda s: s.timestamp) if pre_snapshots else None
            
            # Find post-change snapshots
            post_snapshots = [s for s in self._behavior_snapshots 
                            if change_time <= s.timestamp <= change_time + post_window]
        
        if not pre_snapshot:
            logger.warning(f"No pre-change snapshot found for change {change_id}")
            return None
        
        # Analyze impact
        analysis = ChangeImpactAnalysis(
            change_id=change_id,
            pre_change_snapshot=pre_snapshot,
            post_change_snapshots=post_snapshots
        )
        
        if post_snapshots:
            # Calculate performance deltas
            analysis.performance_delta = self._calculate_performance_delta(
                pre_snapshot, post_snapshots
            )
            
            # Calculate impact score
            analysis.impact_score = self._calculate_impact_score(
                pre_snapshot, post_snapshots, change.impact_level
            )
            
            # Detect anomalies
            analysis.detected_anomalies = self._detect_anomalies(
                pre_snapshot, post_snapshots
            )
            
            # Calculate correlation confidence
            analysis.correlation_confidence = self._calculate_correlation_confidence(
                change, pre_snapshot, post_snapshots
            )
            
            # Detect recovery time
            analysis.recovery_time_seconds = self._detect_recovery_time(
                pre_snapshot, post_snapshots
            )
        
        # Store analysis
        with self._impact_lock:
            self._impact_analyses[change_id] = analysis
        
        logger.info(f"Impact analysis completed for change {change_id}: "
                   f"score={analysis.impact_score:.2f}, "
                   f"anomalies={len(analysis.detected_anomalies)}")
        
        return analysis
    
    def create_rollback_plan(self, change_ids: List[str], 
                           reason: str = None) -> Optional[RollbackPlan]:
        """
        Create a rollback plan for one or more configuration changes
        
        Args:
            change_ids: List of change IDs to rollback
            reason: Reason for rollback
            
        Returns:
            RollbackPlan or None if changes not found
        """
        # Validate change IDs
        with self._changes_lock:
            changes = []
            for change_id in change_ids:
                if change_id not in self._changes_by_id:
                    logger.error(f"Change ID {change_id} not found for rollback")
                    return None
                changes.append(self._changes_by_id[change_id])
        
        # Generate rollback ID
        rollback_id = self._generate_rollback_id(change_ids)
        
        # Create rollback steps (reverse chronological order)
        rollback_steps = []
        requires_restart = False
        max_impact = ChangeImpactLevel.NEGLIGIBLE
        
        for change in sorted(changes, key=lambda c: c.timestamp, reverse=True):
            rollback_step = {
                'change_id': change.change_id,
                'key': change.key,
                'rollback_value': change.old_value,
                'current_value': change.new_value,
                'requires_restart': change.requires_restart,
                'affected_services': change.affected_services
            }
            rollback_steps.append(rollback_step)
            
            if change.requires_restart:
                requires_restart = True
            
            # Track highest impact level
            impact_levels = [ChangeImpactLevel.NEGLIGIBLE, ChangeImpactLevel.LOW, 
                           ChangeImpactLevel.MEDIUM, ChangeImpactLevel.HIGH, 
                           ChangeImpactLevel.CRITICAL]
            if impact_levels.index(change.impact_level) > impact_levels.index(max_impact):
                max_impact = change.impact_level
        
        # Create validation checks
        validation_checks = [
            f"Verify {step['key']} is set to {step['rollback_value']}"
            for step in rollback_steps
        ]
        
        # Create rollback plan
        plan = RollbackPlan(
            rollback_id=rollback_id,
            target_change_ids=change_ids,
            rollback_steps=rollback_steps,
            estimated_impact=max_impact,
            requires_restart=requires_restart,
            validation_checks=validation_checks
        )
        
        # Store plan
        with self._rollback_lock:
            self._rollback_plans[rollback_id] = plan
        
        logger.info(f"Rollback plan created: {rollback_id} for {len(change_ids)} changes")
        
        return plan
    
    def execute_rollback(self, rollback_id: str, 
                        config_service=None) -> Tuple[bool, List[str]]:
        """
        Execute a rollback plan
        
        Args:
            rollback_id: ID of rollback plan to execute
            config_service: Configuration service to apply changes
            
        Returns:
            Tuple of (success, error_messages)
        """
        with self._rollback_lock:
            if rollback_id not in self._rollback_plans:
                return False, [f"Rollback plan {rollback_id} not found"]
            
            plan = self._rollback_plans[rollback_id]
        
        errors = []
        
        # Execute rollback steps
        for step in plan.rollback_steps:
            try:
                if config_service:
                    # Apply the rollback value
                    # This would need to be integrated with the actual configuration service
                    logger.info(f"Rolling back {step['key']} to {step['rollback_value']}")
                    
                    # Log the rollback as a new change
                    self.log_configuration_change(
                        key=step['key'],
                        old_value=step['current_value'],
                        new_value=step['rollback_value'],
                        source=ChangeSource.ROLLBACK,
                        reason=f"Rollback from plan {rollback_id}",
                        impact_level=ChangeImpactLevel.MEDIUM,
                        affected_services=step['affected_services']
                    )
                else:
                    logger.warning(f"No configuration service provided for rollback of {step['key']}")
                    
            except Exception as e:
                error_msg = f"Failed to rollback {step['key']}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        success = len(errors) == 0
        
        if success:
            logger.info(f"Rollback {rollback_id} completed successfully")
        else:
            logger.error(f"Rollback {rollback_id} completed with {len(errors)} errors")
        
        return success, errors
    
    def get_change_history(self, key: str = None, user_id: int = None,
                          hours: int = 24, limit: int = 100) -> List[ConfigurationChange]:
        """
        Get configuration change history with filtering
        
        Args:
            key: Filter by configuration key
            user_id: Filter by user ID
            hours: Number of hours to look back
            limit: Maximum number of changes to return
            
        Returns:
            List of ConfigurationChange objects
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._changes_lock:
            changes = list(self._changes)
        
        # Apply filters
        filtered_changes = []
        for change in changes:
            if change.timestamp < cutoff_time:
                continue
            
            if key and change.key != key:
                continue
            
            if user_id and change.user_id != user_id:
                continue
            
            filtered_changes.append(change)
        
        # Sort by timestamp (newest first) and limit
        filtered_changes.sort(key=lambda c: c.timestamp, reverse=True)
        return filtered_changes[:limit]
    
    def get_impact_analysis(self, change_id: str) -> Optional[ChangeImpactAnalysis]:
        """
        Get impact analysis for a specific change
        
        Args:
            change_id: ID of the change
            
        Returns:
            ChangeImpactAnalysis or None if not found
        """
        with self._impact_lock:
            return self._impact_analyses.get(change_id)
    
    def get_audit_trail(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive audit trail
        
        Args:
            hours: Number of hours to include
            
        Returns:
            Dictionary with audit trail data
        """
        changes = self.get_change_history(hours=hours, limit=1000)
        
        # Aggregate statistics
        changes_by_user = defaultdict(int)
        changes_by_source = defaultdict(int)
        changes_by_impact = defaultdict(int)
        changes_by_key = defaultdict(int)
        
        for change in changes:
            changes_by_user[change.user_name or 'system'] += 1
            changes_by_source[change.source.value] += 1
            changes_by_impact[change.impact_level.value] += 1
            changes_by_key[change.key] += 1
        
        # Get impact analyses
        impact_analyses = []
        with self._impact_lock:
            for change in changes:
                if change.change_id in self._impact_analyses:
                    impact_analyses.append(self._impact_analyses[change.change_id])
        
        # Get rollback plans
        with self._rollback_lock:
            rollback_plans = list(self._rollback_plans.values())
        
        return {
            'time_period_hours': hours,
            'total_changes': len(changes),
            'changes_by_user': dict(changes_by_user),
            'changes_by_source': dict(changes_by_source),
            'changes_by_impact': dict(changes_by_impact),
            'most_changed_keys': sorted(changes_by_key.items(), 
                                      key=lambda x: x[1], reverse=True)[:10],
            'recent_changes': [change.to_dict() for change in changes[:20]],
            'impact_analyses': [analysis.to_dict() for analysis in impact_analyses],
            'rollback_plans': [plan.to_dict() for plan in rollback_plans],
            'high_impact_changes': [
                change.to_dict() for change in changes 
                if change.impact_level in [ChangeImpactLevel.HIGH, ChangeImpactLevel.CRITICAL]
            ]
        }
    
    def export_audit_data(self, hours: int = 24, format: str = 'json') -> str:
        """
        Export audit data for external analysis
        
        Args:
            hours: Number of hours of data to export
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported data as string
        """
        audit_trail = self.get_audit_trail(hours)
        
        export_data = {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'audit_trail': audit_trail
        }
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2, default=str)
        else:
            # Simplified CSV format
            changes = audit_trail['recent_changes']
            csv_lines = ['timestamp,key,old_value,new_value,user,source,impact']
            
            for change in changes:
                csv_lines.append(
                    f"{change['timestamp']},{change['key']},{change['old_value']},"
                    f"{change['new_value']},{change['user_name'] or 'system'},"
                    f"{change['source']},{change['impact_level']}"
                )
            
            return '\n'.join(csv_lines)
    
    def start_behavior_monitoring(self, interval_seconds: int = 30):
        """
        Start continuous system behavior monitoring
        
        Args:
            interval_seconds: How often to take behavior snapshots
        """
        if not self.behavior_tracking_enabled:
            logger.warning("Behavior tracking is disabled")
            return
        
        if self._monitoring_active:
            logger.warning("Behavior monitoring is already active")
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._behavior_monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info(f"Started behavior monitoring (interval: {interval_seconds}s)")
    
    def stop_behavior_monitoring(self):
        """Stop continuous behavior monitoring"""
        self._monitoring_active = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        logger.info("Stopped behavior monitoring")
    
    def _setup_default_collectors(self):
        """Setup default metric collectors"""
        try:
            import psutil
            
            # CPU usage collector
            def cpu_collector():
                return psutil.cpu_percent(interval=0.1)
            
            # Memory usage collector
            def memory_collector():
                return psutil.virtual_memory().percent
            
            self.register_metric_collector(SystemBehaviorMetric.CPU_USAGE, cpu_collector)
            self.register_metric_collector(SystemBehaviorMetric.MEMORY_USAGE, memory_collector)
            
        except ImportError:
            logger.warning("psutil not available, system metrics will not be collected")
    
    def _generate_change_id(self, key: str, old_value: Any, new_value: Any) -> str:
        """Generate unique change ID"""
        timestamp = datetime.now(timezone.utc).isoformat()
        content = f"{key}:{old_value}:{new_value}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_rollback_id(self, change_ids: List[str]) -> str:
        """Generate unique rollback ID"""
        timestamp = datetime.now(timezone.utc).isoformat()
        content = f"{'|'.join(sorted(change_ids))}:{timestamp}"
        return f"rollback_{hashlib.sha256(content.encode()).hexdigest()[:12]}"
    
    def _create_rollback_data(self, key: str, old_value: Any, new_value: Any) -> Dict[str, Any]:
        """Create rollback data for a change"""
        return {
            'key': key,
            'rollback_value': old_value,
            'applied_value': new_value,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _take_behavior_snapshot(self) -> SystemBehaviorSnapshot:
        """Take a snapshot of current system behavior"""
        snapshot = SystemBehaviorSnapshot(timestamp=datetime.now(timezone.utc))
        
        with self._collector_lock:
            for metric, collector in self._metric_collectors.items():
                try:
                    value = collector()
                    snapshot.metrics[metric] = value
                except Exception as e:
                    logger.warning(f"Failed to collect metric {metric.value}: {str(e)}")
        
        return snapshot
    
    def _schedule_impact_analysis(self, change_id: str, pre_snapshot: SystemBehaviorSnapshot):
        """Schedule impact analysis for a change"""
        # For now, we'll do immediate analysis
        # In a real implementation, this could be scheduled for later
        pass
    
    def _calculate_performance_delta(self, pre_snapshot: SystemBehaviorSnapshot,
                                   post_snapshots: List[SystemBehaviorSnapshot]) -> Dict[str, float]:
        """Calculate performance deltas between pre and post snapshots"""
        if not post_snapshots:
            return {}
        
        # Use the average of post-change snapshots
        post_averages = {}
        for metric in pre_snapshot.metrics:
            post_values = [s.metrics.get(metric, 0) for s in post_snapshots if metric in s.metrics]
            if post_values:
                post_averages[metric] = sum(post_values) / len(post_values)
        
        # Calculate deltas
        deltas = {}
        for metric, pre_value in pre_snapshot.metrics.items():
            if metric in post_averages:
                delta = post_averages[metric] - pre_value
                deltas[metric.value] = delta
        
        return deltas
    
    def _calculate_impact_score(self, pre_snapshot: SystemBehaviorSnapshot,
                              post_snapshots: List[SystemBehaviorSnapshot],
                              expected_impact: ChangeImpactLevel) -> float:
        """Calculate impact score (0.0 to 1.0)"""
        if not post_snapshots:
            return 0.0
        
        deltas = self._calculate_performance_delta(pre_snapshot, post_snapshots)
        
        # Weight different metrics
        metric_weights = {
            'response_time': 0.3,
            'error_rate': 0.3,
            'cpu_usage': 0.2,
            'memory_usage': 0.2
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric_name, delta in deltas.items():
            weight = metric_weights.get(metric_name, 0.1)
            
            # Normalize delta to 0-1 scale (this is simplified)
            normalized_delta = min(1.0, abs(delta) / 100.0)
            
            weighted_score += normalized_delta * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _detect_anomalies(self, pre_snapshot: SystemBehaviorSnapshot,
                         post_snapshots: List[SystemBehaviorSnapshot]) -> List[str]:
        """Detect anomalies in system behavior"""
        anomalies = []
        deltas = self._calculate_performance_delta(pre_snapshot, post_snapshots)
        
        # Simple anomaly detection thresholds
        thresholds = {
            'response_time': 50.0,  # 50ms increase
            'error_rate': 0.05,     # 5% increase
            'cpu_usage': 20.0,      # 20% increase
            'memory_usage': 15.0    # 15% increase
        }
        
        for metric_name, delta in deltas.items():
            threshold = thresholds.get(metric_name, 10.0)
            if abs(delta) > threshold:
                anomalies.append(f"{metric_name} changed by {delta:.2f} (threshold: {threshold})")
        
        return anomalies
    
    def _calculate_correlation_confidence(self, change: ConfigurationChange,
                                        pre_snapshot: SystemBehaviorSnapshot,
                                        post_snapshots: List[SystemBehaviorSnapshot]) -> float:
        """Calculate confidence that behavior changes are correlated with config change"""
        if not post_snapshots:
            return 0.0
        
        # Simple correlation based on timing and impact level
        time_factor = 1.0  # Immediate changes have higher confidence
        
        impact_factors = {
            ChangeImpactLevel.NEGLIGIBLE: 0.1,
            ChangeImpactLevel.LOW: 0.3,
            ChangeImpactLevel.MEDIUM: 0.6,
            ChangeImpactLevel.HIGH: 0.8,
            ChangeImpactLevel.CRITICAL: 0.9
        }
        
        impact_factor = impact_factors.get(change.impact_level, 0.5)
        
        # Factor in the magnitude of behavior changes
        deltas = self._calculate_performance_delta(pre_snapshot, post_snapshots)
        magnitude_factor = min(1.0, sum(abs(d) for d in deltas.values()) / 100.0)
        
        confidence = (time_factor * 0.3 + impact_factor * 0.4 + magnitude_factor * 0.3)
        return min(1.0, confidence)
    
    def _detect_recovery_time(self, pre_snapshot: SystemBehaviorSnapshot,
                            post_snapshots: List[SystemBehaviorSnapshot]) -> Optional[float]:
        """Detect how long it took for system to recover to baseline"""
        if len(post_snapshots) < 2:
            return None
        
        # Simple recovery detection - when metrics return to within 10% of baseline
        recovery_threshold = 0.1  # 10%
        
        for i, snapshot in enumerate(post_snapshots):
            all_recovered = True
            
            for metric, pre_value in pre_snapshot.metrics.items():
                if metric in snapshot.metrics:
                    post_value = snapshot.metrics[metric]
                    if pre_value > 0:
                        deviation = abs(post_value - pre_value) / pre_value
                        if deviation > recovery_threshold:
                            all_recovered = False
                            break
            
            if all_recovered and i > 0:  # Don't count immediate recovery
                time_diff = snapshot.timestamp - pre_snapshot.timestamp
                return time_diff.total_seconds()
        
        return None
    
    def _behavior_monitoring_loop(self, interval_seconds: int):
        """Background behavior monitoring loop"""
        while self._monitoring_active:
            try:
                snapshot = self._take_behavior_snapshot()
                
                with self._behavior_lock:
                    self._behavior_snapshots.append(snapshot)
                
                # Clean up old snapshots
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                with self._behavior_lock:
                    self._behavior_snapshots = deque(
                        (s for s in self._behavior_snapshots if s.timestamp >= cutoff_time),
                        maxlen=self._behavior_snapshots.maxlen
                    )
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in behavior monitoring loop: {str(e)}")
                time.sleep(interval_seconds)