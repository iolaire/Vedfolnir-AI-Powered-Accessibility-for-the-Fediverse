# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Mode Monitor

Provides comprehensive monitoring and reporting for test mode operations.
Tracks test mode activity, performance metrics, validation results, and
provides cleanup and reset functionality.
"""

import logging
import threading
import json
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
from app.services.maintenance.components.maintenance_procedure_validator import MaintenanceProcedureValidator, ValidationResult

logger = logging.getLogger(__name__)


class TestModeStatus(Enum):
    """Test mode status values"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TestModeMetrics:
    """Test mode performance and activity metrics"""
    session_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: float
    total_operations: int
    operations_per_second: float
    blocked_operations: int
    allowed_operations: int
    admin_bypasses: int
    error_count: int
    memory_usage_mb: float
    cpu_usage_percent: float
    status: TestModeStatus


@dataclass
class TestModeReport:
    """Comprehensive test mode report"""
    report_id: str
    generated_at: datetime
    session_id: str
    test_mode_metrics: TestModeMetrics
    validation_result: Optional[ValidationResult]
    activity_log: List[Dict[str, Any]]
    performance_analysis: Dict[str, Any]
    recommendations: List[str]
    cleanup_status: Dict[str, Any]


class TestModeMonitor:
    """
    Monitors test mode operations and provides comprehensive reporting
    
    Features:
    - Real-time test mode activity monitoring
    - Performance metrics collection
    - Validation report generation
    - Test mode cleanup and reset
    - Historical test mode data tracking
    - Automated report generation
    """
    
    def __init__(self, maintenance_service: EnhancedMaintenanceModeService,
                 validator: Optional[MaintenanceProcedureValidator] = None):
        """
        Initialize test mode monitor
        
        Args:
            maintenance_service: Enhanced maintenance mode service instance
            validator: Maintenance procedure validator (optional)
        """
        self.maintenance_service = maintenance_service
        self.validator = validator or MaintenanceProcedureValidator(maintenance_service)
        
        # Monitoring state
        self._monitor_lock = threading.RLock()
        self._active_monitoring = False
        self._current_session: Optional[Dict[str, Any]] = None
        
        # Activity tracking
        self._activity_log: List[Dict[str, Any]] = []
        self._performance_samples: List[Dict[str, Any]] = []
        
        # Metrics collection
        self._metrics_collection_interval = 5.0  # seconds
        self._metrics_thread: Optional[threading.Thread] = None
        self._stop_metrics_collection = threading.Event()
        
        # Report storage
        self._reports_directory = "test_mode_reports"
        self._ensure_reports_directory()
        
        # Cleanup tracking
        self._cleanup_history: List[Dict[str, Any]] = []
        
        # Subscribers for real-time updates
        self._subscribers: Dict[str, Callable] = {}
        self._subscribers_lock = threading.RLock()
    
    def start_monitoring(self, session_id: Optional[str] = None) -> bool:
        """
        Start monitoring test mode activity
        
        Args:
            session_id: Test mode session ID to monitor (optional)
            
        Returns:
            True if monitoring started successfully
        """
        try:
            with self._monitor_lock:
                if self._active_monitoring:
                    logger.warning("Test mode monitoring is already active")
                    return False
                
                # Get current test mode status
                test_status = self.maintenance_service.get_test_mode_status()
                if not test_status.get('active', False):
                    logger.warning("Test mode is not active, cannot start monitoring")
                    return False
                
                # Initialize monitoring session
                monitoring_session_id = session_id or test_status.get('test_session_id', str(uuid.uuid4()))
                
                self._current_session = {
                    'monitoring_id': str(uuid.uuid4()),
                    'session_id': monitoring_session_id,
                    'started_at': datetime.now(timezone.utc),
                    'status': TestModeStatus.ACTIVE,
                    'initial_metrics': self._collect_current_metrics()
                }
                
                # Clear previous data
                self._activity_log.clear()
                self._performance_samples.clear()
                
                # Start metrics collection
                self._start_metrics_collection()
                
                self._active_monitoring = True
                
                # Log monitoring start
                self._log_activity('monitoring_started', {
                    'monitoring_id': self._current_session['monitoring_id'],
                    'session_id': monitoring_session_id
                })
                
                # Notify subscribers
                self._notify_subscribers('monitoring_started', self._current_session)
                
                logger.info(f"Started test mode monitoring for session {monitoring_session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error starting test mode monitoring: {str(e)}")
            return False
    
    def stop_monitoring(self) -> Optional[TestModeReport]:
        """
        Stop monitoring and generate final report
        
        Returns:
            Final test mode report or None if monitoring wasn't active
        """
        try:
            with self._monitor_lock:
                if not self._active_monitoring:
                    logger.warning("Test mode monitoring is not active")
                    return None
                
                # Stop metrics collection
                self._stop_metrics_collection_thread()
                
                # Update session status
                if self._current_session:
                    self._current_session['completed_at'] = datetime.now(timezone.utc)
                    self._current_session['status'] = TestModeStatus.COMPLETED
                
                # Generate final report
                final_report = self._generate_comprehensive_report()
                
                # Save report to file
                if final_report:
                    self._save_report_to_file(final_report)
                
                # Log monitoring stop
                self._log_activity('monitoring_stopped', {
                    'monitoring_id': self._current_session['monitoring_id'] if self._current_session else 'unknown',
                    'final_report_id': final_report.report_id if final_report else None
                })
                
                # Notify subscribers
                self._notify_subscribers('monitoring_stopped', final_report)
                
                self._active_monitoring = False
                
                logger.info("Stopped test mode monitoring and generated final report")
                return final_report
                
        except Exception as e:
            logger.error(f"Error stopping test mode monitoring: {str(e)}")
            return None
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get real-time test mode metrics
        
        Returns:
            Dictionary with current metrics
        """
        try:
            if not self._active_monitoring:
                return {'error': 'Monitoring not active'}
            
            # Get current test mode status
            test_status = self.maintenance_service.get_test_mode_status()
            
            # Collect current performance metrics
            current_metrics = self._collect_current_metrics()
            
            # Calculate derived metrics
            if self._current_session:
                duration = (datetime.now(timezone.utc) - self._current_session['started_at']).total_seconds()
                ops_per_second = test_status.get('total_operations_tested', 0) / duration if duration > 0 else 0
            else:
                duration = 0
                ops_per_second = 0
            
            return {
                'monitoring_active': True,
                'session_id': self._current_session['session_id'] if self._current_session else None,
                'monitoring_duration_seconds': duration,
                'test_mode_status': test_status,
                'current_metrics': current_metrics,
                'operations_per_second': ops_per_second,
                'activity_log_entries': len(self._activity_log),
                'performance_samples': len(self._performance_samples),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {str(e)}")
            return {'error': str(e)}
    
    def generate_validation_report(self, comprehensive: bool = True) -> Optional[ValidationResult]:
        """
        Generate validation report for current test mode session
        
        Args:
            comprehensive: Whether to run comprehensive validation
            
        Returns:
            Validation result or None if validation failed
        """
        try:
            if not self._active_monitoring:
                logger.warning("Cannot generate validation report - monitoring not active")
                return None
            
            logger.info("Generating test mode validation report")
            
            # Run validation
            validation_result = self.validator.validate_maintenance_procedures(
                test_duration_minutes=1,  # Short duration since we're already in test mode
                comprehensive=comprehensive
            )
            
            # Log validation completion
            self._log_activity('validation_completed', {
                'validation_status': validation_result.overall_status,
                'tests_run': validation_result.total_tests_run,
                'tests_passed': validation_result.tests_passed,
                'tests_failed': validation_result.tests_failed
            })
            
            # Notify subscribers
            self._notify_subscribers('validation_completed', validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error generating validation report: {str(e)}")
            return None
    
    def cleanup_test_mode_data(self, preserve_reports: bool = True) -> Dict[str, Any]:
        """
        Clean up test mode data and reset state
        
        Args:
            preserve_reports: Whether to preserve generated reports
            
        Returns:
            Cleanup status report
        """
        try:
            cleanup_start = datetime.now(timezone.utc)
            cleanup_id = str(uuid.uuid4())
            
            logger.info(f"Starting test mode cleanup (ID: {cleanup_id})")
            
            cleanup_status = {
                'cleanup_id': cleanup_id,
                'started_at': cleanup_start,
                'preserve_reports': preserve_reports,
                'actions_performed': [],
                'errors_encountered': [],
                'items_cleaned': 0
            }
            
            # Stop monitoring if active
            if self._active_monitoring:
                final_report = self.stop_monitoring()
                cleanup_status['actions_performed'].append('stopped_active_monitoring')
                if final_report:
                    cleanup_status['final_report_generated'] = final_report.report_id
            
            # Reset maintenance service test mode data
            try:
                reset_success = self.maintenance_service.reset_test_mode_data()
                if reset_success:
                    cleanup_status['actions_performed'].append('reset_maintenance_service_data')
                    cleanup_status['items_cleaned'] += 1
                else:
                    cleanup_status['errors_encountered'].append('failed_to_reset_maintenance_service_data')
            except Exception as e:
                cleanup_status['errors_encountered'].append(f'maintenance_service_reset_error: {str(e)}')
            
            # Clear monitoring data
            with self._monitor_lock:
                self._activity_log.clear()
                self._performance_samples.clear()
                self._current_session = None
                cleanup_status['actions_performed'].append('cleared_monitoring_data')
                cleanup_status['items_cleaned'] += 2
            
            # Clean up report files if not preserving
            if not preserve_reports:
                try:
                    reports_cleaned = self._cleanup_report_files()
                    cleanup_status['actions_performed'].append(f'cleaned_{reports_cleaned}_report_files')
                    cleanup_status['items_cleaned'] += reports_cleaned
                except Exception as e:
                    cleanup_status['errors_encountered'].append(f'report_cleanup_error: {str(e)}')
            
            # Complete cleanup
            cleanup_status['completed_at'] = datetime.now(timezone.utc)
            cleanup_status['duration_seconds'] = (cleanup_status['completed_at'] - cleanup_start).total_seconds()
            cleanup_status['success'] = len(cleanup_status['errors_encountered']) == 0
            
            # Record cleanup in history
            self._cleanup_history.append(cleanup_status)
            
            # Notify subscribers
            self._notify_subscribers('cleanup_completed', cleanup_status)
            
            logger.info(f"Test mode cleanup completed (ID: {cleanup_id}, Success: {cleanup_status['success']})")
            return cleanup_status
            
        except Exception as e:
            logger.error(f"Error during test mode cleanup: {str(e)}")
            return {
                'cleanup_id': cleanup_id if 'cleanup_id' in locals() else 'unknown',
                'success': False,
                'error': str(e),
                'completed_at': datetime.now(timezone.utc)
            }
    
    def get_monitoring_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get monitoring history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of historical monitoring data
        """
        try:
            # Get cleanup history
            cleanup_history = self._cleanup_history[-limit:] if self._cleanup_history else []
            
            # Get activity log
            activity_history = self._activity_log[-limit:] if self._activity_log else []
            
            # Combine and sort by timestamp
            all_history = []
            
            for cleanup in cleanup_history:
                all_history.append({
                    'type': 'cleanup',
                    'timestamp': cleanup.get('started_at', datetime.now(timezone.utc)),
                    'data': cleanup
                })
            
            for activity in activity_history:
                all_history.append({
                    'type': 'activity',
                    'timestamp': datetime.fromisoformat(activity.get('timestamp', datetime.now(timezone.utc).isoformat())),
                    'data': activity
                })
            
            # Sort by timestamp (most recent first)
            all_history.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return all_history[:limit]
            
        except Exception as e:
            logger.error(f"Error getting monitoring history: {str(e)}")
            return []
    
    def subscribe_to_updates(self, callback: Callable[[str, Any], None]) -> str:
        """
        Subscribe to real-time monitoring updates
        
        Args:
            callback: Callback function (event_type, data)
            
        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        
        with self._subscribers_lock:
            self._subscribers[subscription_id] = callback
        
        logger.debug(f"Added monitoring subscription {subscription_id}")
        return subscription_id
    
    def unsubscribe_from_updates(self, subscription_id: str) -> bool:
        """
        Unsubscribe from monitoring updates
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed
        """
        with self._subscribers_lock:
            if subscription_id in self._subscribers:
                del self._subscribers[subscription_id]
                logger.debug(f"Removed monitoring subscription {subscription_id}")
                return True
        
        return False
    
    def _start_metrics_collection(self):
        """Start background metrics collection thread"""
        try:
            self._stop_metrics_collection.clear()
            self._metrics_thread = threading.Thread(
                target=self._metrics_collection_loop,
                name="TestModeMetricsCollection",
                daemon=True
            )
            self._metrics_thread.start()
            logger.debug("Started metrics collection thread")
            
        except Exception as e:
            logger.error(f"Error starting metrics collection: {str(e)}")
    
    def _stop_metrics_collection_thread(self):
        """Stop background metrics collection thread"""
        try:
            if self._metrics_thread and self._metrics_thread.is_alive():
                self._stop_metrics_collection.set()
                self._metrics_thread.join(timeout=5.0)
                logger.debug("Stopped metrics collection thread")
                
        except Exception as e:
            logger.error(f"Error stopping metrics collection: {str(e)}")
    
    def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        try:
            while not self._stop_metrics_collection.is_set():
                try:
                    # Collect current metrics
                    metrics = self._collect_current_metrics()
                    
                    # Add timestamp
                    metrics['timestamp'] = datetime.now(timezone.utc).isoformat()
                    
                    # Store sample
                    self._performance_samples.append(metrics)
                    
                    # Limit sample history
                    if len(self._performance_samples) > 1000:
                        self._performance_samples = self._performance_samples[-500:]
                    
                except Exception as e:
                    logger.error(f"Error collecting metrics sample: {str(e)}")
                
                # Wait for next collection interval
                self._stop_metrics_collection.wait(self._metrics_collection_interval)
                
        except Exception as e:
            logger.error(f"Error in metrics collection loop: {str(e)}")
    
    def _collect_current_metrics(self) -> Dict[str, Any]:
        """
        Collect current performance metrics
        
        Returns:
            Dictionary with current metrics
        """
        try:
            import psutil
            import os
            
            # Get process info
            process = psutil.Process(os.getpid())
            
            # Get test mode status
            test_status = self.maintenance_service.get_test_mode_status()
            
            return {
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_usage_percent': process.cpu_percent(),
                'thread_count': process.num_threads(),
                'test_operations': test_status.get('total_operations_tested', 0),
                'blocked_operations': test_status.get('blocked_operations_count', 0),
                'allowed_operations': test_status.get('allowed_operations_count', 0),
                'admin_bypasses': test_status.get('admin_bypasses_count', 0),
                'errors': test_status.get('errors_count', 0)
            }
            
        except ImportError:
            # psutil not available, return basic metrics
            test_status = self.maintenance_service.get_test_mode_status()
            return {
                'memory_usage_mb': 0.0,
                'cpu_usage_percent': 0.0,
                'thread_count': 0,
                'test_operations': test_status.get('total_operations_tested', 0),
                'blocked_operations': test_status.get('blocked_operations_count', 0),
                'allowed_operations': test_status.get('allowed_operations_count', 0),
                'admin_bypasses': test_status.get('admin_bypasses_count', 0),
                'errors': test_status.get('errors_count', 0)
            }
        except Exception as e:
            logger.error(f"Error collecting current metrics: {str(e)}")
            return {'error': str(e)}
    
    def _generate_comprehensive_report(self) -> Optional[TestModeReport]:
        """
        Generate comprehensive test mode report
        
        Returns:
            Complete test mode report
        """
        try:
            if not self._current_session:
                return None
            
            # Generate test mode metrics
            test_metrics = self._generate_test_metrics()
            
            # Get validation result (if available)
            validation_result = None  # Could be enhanced to store validation results
            
            # Analyze performance data
            performance_analysis = self._analyze_performance_data()
            
            # Generate recommendations
            recommendations = self._generate_monitoring_recommendations(test_metrics, performance_analysis)
            
            # Get cleanup status
            cleanup_status = {'status': 'pending', 'message': 'Cleanup not yet performed'}
            
            # Create comprehensive report
            report = TestModeReport(
                report_id=str(uuid.uuid4()),
                generated_at=datetime.now(timezone.utc),
                session_id=self._current_session['session_id'],
                test_mode_metrics=test_metrics,
                validation_result=validation_result,
                activity_log=self._activity_log.copy(),
                performance_analysis=performance_analysis,
                recommendations=recommendations,
                cleanup_status=cleanup_status
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {str(e)}")
            return None
    
    def _generate_test_metrics(self) -> TestModeMetrics:
        """
        Generate test mode metrics from collected data
        
        Returns:
            Test mode metrics object
        """
        try:
            if not self._current_session:
                raise ValueError("No active session for metrics generation")
            
            # Get test mode status
            test_status = self.maintenance_service.get_test_mode_status()
            
            # Calculate duration
            started_at = self._current_session['started_at']
            completed_at = self._current_session.get('completed_at', datetime.now(timezone.utc))
            duration = (completed_at - started_at).total_seconds()
            
            # Calculate operations per second
            total_ops = test_status.get('total_operations_tested', 0)
            ops_per_second = total_ops / duration if duration > 0 else 0
            
            # Get latest metrics
            latest_metrics = self._performance_samples[-1] if self._performance_samples else {}
            
            return TestModeMetrics(
                session_id=self._current_session['session_id'],
                started_at=started_at,
                completed_at=completed_at if 'completed_at' in self._current_session else None,
                duration_seconds=duration,
                total_operations=total_ops,
                operations_per_second=ops_per_second,
                blocked_operations=test_status.get('blocked_operations_count', 0),
                allowed_operations=test_status.get('allowed_operations_count', 0),
                admin_bypasses=test_status.get('admin_bypasses_count', 0),
                error_count=test_status.get('errors_count', 0),
                memory_usage_mb=latest_metrics.get('memory_usage_mb', 0.0),
                cpu_usage_percent=latest_metrics.get('cpu_usage_percent', 0.0),
                status=self._current_session.get('status', TestModeStatus.ACTIVE)
            )
            
        except Exception as e:
            logger.error(f"Error generating test metrics: {str(e)}")
            # Return default metrics
            return TestModeMetrics(
                session_id='unknown',
                started_at=datetime.now(timezone.utc),
                completed_at=None,
                duration_seconds=0.0,
                total_operations=0,
                operations_per_second=0.0,
                blocked_operations=0,
                allowed_operations=0,
                admin_bypasses=0,
                error_count=1,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                status=TestModeStatus.ERROR
            )
    
    def _analyze_performance_data(self) -> Dict[str, Any]:
        """
        Analyze collected performance data
        
        Returns:
            Performance analysis results
        """
        try:
            if not self._performance_samples:
                return {'message': 'No performance data available'}
            
            # Calculate averages
            total_samples = len(self._performance_samples)
            avg_memory = sum(s.get('memory_usage_mb', 0) for s in self._performance_samples) / total_samples
            avg_cpu = sum(s.get('cpu_usage_percent', 0) for s in self._performance_samples) / total_samples
            
            # Find peaks
            max_memory = max(s.get('memory_usage_mb', 0) for s in self._performance_samples)
            max_cpu = max(s.get('cpu_usage_percent', 0) for s in self._performance_samples)
            
            # Calculate trends
            if total_samples >= 2:
                memory_trend = self._performance_samples[-1].get('memory_usage_mb', 0) - self._performance_samples[0].get('memory_usage_mb', 0)
                cpu_trend = self._performance_samples[-1].get('cpu_usage_percent', 0) - self._performance_samples[0].get('cpu_usage_percent', 0)
            else:
                memory_trend = 0
                cpu_trend = 0
            
            return {
                'sample_count': total_samples,
                'averages': {
                    'memory_mb': avg_memory,
                    'cpu_percent': avg_cpu
                },
                'peaks': {
                    'memory_mb': max_memory,
                    'cpu_percent': max_cpu
                },
                'trends': {
                    'memory_change_mb': memory_trend,
                    'cpu_change_percent': cpu_trend
                },
                'performance_status': 'good' if avg_memory < 100 and avg_cpu < 50 else 'high_usage'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance data: {str(e)}")
            return {'error': str(e)}
    
    def _generate_monitoring_recommendations(self, metrics: TestModeMetrics, 
                                           performance: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on monitoring data
        
        Args:
            metrics: Test mode metrics
            performance: Performance analysis
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        try:
            # Performance recommendations
            if performance.get('performance_status') == 'high_usage':
                recommendations.append("Consider optimizing test mode operations - high resource usage detected")
            
            # Operations recommendations
            if metrics.operations_per_second < 0.1:
                recommendations.append("Test mode operation rate is low - consider investigating performance bottlenecks")
            
            # Error recommendations
            if metrics.error_count > 0:
                recommendations.append(f"Test mode encountered {metrics.error_count} errors - review error logs")
            
            # Duration recommendations
            if metrics.duration_seconds > 300:  # 5 minutes
                recommendations.append("Test mode session was long-running - consider shorter test cycles")
            
            # Coverage recommendations
            if metrics.total_operations < 10:
                recommendations.append("Low test operation count - consider more comprehensive testing")
            
            # Success recommendations
            if metrics.error_count == 0 and metrics.total_operations > 0:
                recommendations.append("Test mode completed successfully - maintenance procedures validated")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return [f"Error generating recommendations: {str(e)}"]
    
    def _log_activity(self, activity_type: str, details: Dict[str, Any]):
        """
        Log test mode activity
        
        Args:
            activity_type: Type of activity
            details: Activity details
        """
        try:
            activity_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'activity_type': activity_type,
                'details': details
            }
            
            self._activity_log.append(activity_entry)
            
            # Limit activity log size
            if len(self._activity_log) > 1000:
                self._activity_log = self._activity_log[-500:]
            
            logger.debug(f"Logged test mode activity: {activity_type}")
            
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
    
    def _notify_subscribers(self, event_type: str, data: Any):
        """
        Notify subscribers of monitoring events
        
        Args:
            event_type: Type of event
            data: Event data
        """
        with self._subscribers_lock:
            for subscription_id, callback in self._subscribers.items():
                try:
                    callback(event_type, data)
                except Exception as e:
                    logger.error(f"Error in monitoring callback {subscription_id}: {str(e)}")
    
    def _ensure_reports_directory(self):
        """Ensure reports directory exists"""
        try:
            os.makedirs(self._reports_directory, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating reports directory: {str(e)}")
    
    def _save_report_to_file(self, report: TestModeReport):
        """
        Save report to file
        
        Args:
            report: Test mode report to save
        """
        try:
            filename = f"test_mode_report_{report.session_id}_{report.generated_at.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self._reports_directory, filename)
            
            # Convert report to dictionary
            report_dict = asdict(report)
            
            # Convert datetime objects to ISO strings
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                else:
                    return obj
            
            report_dict = convert_datetime(report_dict)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)
            
            logger.info(f"Saved test mode report to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving report to file: {str(e)}")
    
    def _cleanup_report_files(self, max_age_days: int = 30) -> int:
        """
        Clean up old report files
        
        Args:
            max_age_days: Maximum age of files to keep
            
        Returns:
            Number of files cleaned up
        """
        try:
            if not os.path.exists(self._reports_directory):
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            files_cleaned = 0
            
            for filename in os.listdir(self._reports_directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(self._reports_directory, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        files_cleaned += 1
            
            return files_cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up report files: {str(e)}")
            return 0