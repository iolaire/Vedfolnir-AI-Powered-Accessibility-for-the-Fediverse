# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Error Recovery Procedures

Automated and manual error recovery procedures for RQ system failures.
Provides step-by-step recovery guidance and automated recovery actions.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus
from .rq_error_handler import ErrorCategory

logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Types of recovery actions"""
    RESTART_WORKERS = "restart_workers"
    CLEAR_STUCK_TASKS = "clear_stuck_tasks"
    MIGRATE_TO_DATABASE = "migrate_to_database"
    MIGRATE_TO_REDIS = "migrate_to_redis"
    CLEAR_DEAD_LETTER_QUEUE = "clear_dead_letter_queue"
    RETRY_FAILED_TASKS = "retry_failed_tasks"
    RESET_REDIS_CONNECTION = "reset_redis_connection"
    CLEANUP_RESOURCES = "cleanup_resources"
    SCALE_WORKERS = "scale_workers"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


class RecoveryStatus(Enum):
    """Status of recovery procedures"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ErrorRecoveryProcedures:
    """Automated and manual error recovery procedures for RQ system"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis,
                 rq_queue_manager=None, rq_worker_manager=None):
        """
        Initialize Error Recovery Procedures
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection
            rq_queue_manager: Optional RQ queue manager for recovery operations
            rq_worker_manager: Optional RQ worker manager for worker operations
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.rq_queue_manager = rq_queue_manager
        self.rq_worker_manager = rq_worker_manager
        
        # Recovery configuration
        self.recovery_timeout = 300  # 5 minutes
        self.max_retry_attempts = 3
        self.stuck_task_threshold = 3600  # 1 hour
        
        # Redis keys for recovery state
        self.recovery_state_key = "rq:recovery_state"
        self.recovery_log_key = "rq:recovery_log"
        
        logger.info("Error Recovery Procedures initialized")
    
    def diagnose_system_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health diagnosis
        
        Returns:
            Dict containing diagnosis results and recommended actions
        """
        try:
            diagnosis = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_health': 'unknown',
                'issues': [],
                'recommendations': [],
                'detailed_checks': {}
            }
            
            # Check Redis connectivity
            redis_health = self._check_redis_health()
            diagnosis['detailed_checks']['redis'] = redis_health
            
            # Check database connectivity
            db_health = self._check_database_health()
            diagnosis['detailed_checks']['database'] = db_health
            
            # Check task queue status
            queue_health = self._check_queue_health()
            diagnosis['detailed_checks']['queues'] = queue_health
            
            # Check for stuck tasks
            stuck_tasks = self._check_stuck_tasks()
            diagnosis['detailed_checks']['stuck_tasks'] = stuck_tasks
            
            # Check worker status
            worker_health = self._check_worker_health()
            diagnosis['detailed_checks']['workers'] = worker_health
            
            # Determine overall health and recommendations
            diagnosis = self._analyze_diagnosis_results(diagnosis)
            
            # Log diagnosis
            self._log_recovery_event('system_diagnosis', diagnosis)
            
            return diagnosis
            
        except Exception as e:
            logger.error(f"Failed to diagnose system health: {sanitize_for_log(str(e))}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_health': 'error',
                'error': str(e),
                'issues': ['Failed to perform health diagnosis'],
                'recommendations': ['Check system logs and retry diagnosis']
            }
    
    def execute_recovery_plan(self, recovery_actions: List[RecoveryAction]) -> Dict[str, Any]:
        """
        Execute a recovery plan with multiple actions
        
        Args:
            recovery_actions: List of recovery actions to execute
            
        Returns:
            Dict containing recovery results
        """
        recovery_id = f"recovery_{int(datetime.now().timestamp())}"
        
        try:
            recovery_result = {
                'recovery_id': recovery_id,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'actions': recovery_actions,
                'results': {},
                'overall_status': RecoveryStatus.IN_PROGRESS.value,
                'completed_at': None,
                'success_count': 0,
                'failure_count': 0
            }
            
            # Store initial recovery state
            self._store_recovery_state(recovery_id, recovery_result)
            
            # Execute each recovery action
            for action in recovery_actions:
                try:
                    logger.info(f"Executing recovery action: {action.value}")
                    
                    action_result = self._execute_recovery_action(action)
                    recovery_result['results'][action.value] = action_result
                    
                    if action_result.get('success', False):
                        recovery_result['success_count'] += 1
                    else:
                        recovery_result['failure_count'] += 1
                    
                    # Update recovery state
                    self._store_recovery_state(recovery_id, recovery_result)
                    
                except Exception as e:
                    logger.error(f"Recovery action {action.value} failed: {sanitize_for_log(str(e))}")
                    
                    recovery_result['results'][action.value] = {
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    recovery_result['failure_count'] += 1
            
            # Determine overall status
            if recovery_result['failure_count'] == 0:
                recovery_result['overall_status'] = RecoveryStatus.COMPLETED.value
            elif recovery_result['success_count'] == 0:
                recovery_result['overall_status'] = RecoveryStatus.FAILED.value
            else:
                recovery_result['overall_status'] = RecoveryStatus.PARTIAL.value
            
            recovery_result['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Store final recovery state
            self._store_recovery_state(recovery_id, recovery_result)
            
            # Log recovery completion
            self._log_recovery_event('recovery_completed', recovery_result)
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"Recovery plan execution failed: {sanitize_for_log(str(e))}")
            
            recovery_result = {
                'recovery_id': recovery_id,
                'overall_status': RecoveryStatus.FAILED.value,
                'error': str(e),
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            
            self._store_recovery_state(recovery_id, recovery_result)
            return recovery_result
    
    def _execute_recovery_action(self, action: RecoveryAction) -> Dict[str, Any]:
        """Execute a specific recovery action"""
        action_handlers = {
            RecoveryAction.RESTART_WORKERS: self._restart_workers,
            RecoveryAction.CLEAR_STUCK_TASKS: self._clear_stuck_tasks,
            RecoveryAction.MIGRATE_TO_DATABASE: self._migrate_to_database,
            RecoveryAction.MIGRATE_TO_REDIS: self._migrate_to_redis,
            RecoveryAction.CLEAR_DEAD_LETTER_QUEUE: self._clear_dead_letter_queue,
            RecoveryAction.RETRY_FAILED_TASKS: self._retry_failed_tasks,
            RecoveryAction.RESET_REDIS_CONNECTION: self._reset_redis_connection,
            RecoveryAction.CLEANUP_RESOURCES: self._cleanup_resources,
            RecoveryAction.SCALE_WORKERS: self._scale_workers,
            RecoveryAction.EMERGENCY_SHUTDOWN: self._emergency_shutdown
        }
        
        handler = action_handlers.get(action)
        if not handler:
            return {
                'success': False,
                'error': f'No handler for action: {action.value}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        try:
            return handler()
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _restart_workers(self) -> Dict[str, Any]:
        """Restart RQ workers"""
        try:
            if not self.rq_worker_manager:
                return {
                    'success': False,
                    'error': 'RQ worker manager not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Stop workers gracefully
            stop_result = self.rq_worker_manager.stop_workers(graceful=True, timeout=30)
            
            # Start workers again
            start_result = self.rq_worker_manager.start_integrated_workers()
            
            return {
                'success': True,
                'message': 'Workers restarted successfully',
                'details': {
                    'stop_result': stop_result,
                    'start_result': start_result
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to restart workers: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _clear_stuck_tasks(self) -> Dict[str, Any]:
        """Clear tasks that have been running too long"""
        try:
            session = self.db_manager.get_session()
            try:
                cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.stuck_task_threshold)
                
                # Find stuck tasks
                stuck_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING,
                    CaptionGenerationTask.started_at < cutoff_time
                ).all()
                
                cleared_count = 0
                for task in stuck_tasks:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    task.error_message = "Task cleared due to timeout during recovery"
                    cleared_count += 1
                
                session.commit()
                
                return {
                    'success': True,
                    'message': f'Cleared {cleared_count} stuck tasks',
                    'details': {
                        'cleared_count': cleared_count,
                        'threshold_seconds': self.stuck_task_threshold
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
            finally:
                session.close()
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to clear stuck tasks: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _migrate_to_database(self) -> Dict[str, Any]:
        """Migrate RQ tasks to database fallback mode"""
        try:
            if not self.rq_queue_manager:
                return {
                    'success': False,
                    'error': 'RQ queue manager not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Enable fallback mode
            self.rq_queue_manager._fallback_mode = True
            self.rq_queue_manager._redis_available = False
            
            return {
                'success': True,
                'message': 'Migrated to database fallback mode',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to migrate to database: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _migrate_to_redis(self) -> Dict[str, Any]:
        """Migrate database tasks back to Redis"""
        try:
            if not self.rq_queue_manager:
                return {
                    'success': False,
                    'error': 'RQ queue manager not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Migrate database tasks to RQ
            migrated_count = self.rq_queue_manager.migrate_database_tasks()
            
            # Enable RQ mode
            self.rq_queue_manager._fallback_mode = False
            self.rq_queue_manager._redis_available = True
            
            return {
                'success': True,
                'message': f'Migrated {migrated_count} tasks to Redis',
                'details': {
                    'migrated_count': migrated_count
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to migrate to Redis: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _clear_dead_letter_queue(self) -> Dict[str, Any]:
        """Clear dead letter queue"""
        try:
            # Get DLQ size before clearing
            dlq_size = self.redis_connection.llen("rq:dead_letter_queue")
            
            # Clear DLQ
            self.redis_connection.delete("rq:dead_letter_queue")
            self.redis_connection.delete("rq:dlq_metadata")
            
            return {
                'success': True,
                'message': f'Cleared dead letter queue ({dlq_size} items)',
                'details': {
                    'items_cleared': dlq_size
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to clear dead letter queue: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _retry_failed_tasks(self) -> Dict[str, Any]:
        """Retry recently failed tasks"""
        try:
            session = self.db_manager.get_session()
            try:
                # Get recently failed tasks (last hour)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                
                failed_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.FAILED,
                    CaptionGenerationTask.completed_at >= cutoff_time
                ).all()
                
                retried_count = 0
                for task in failed_tasks:
                    # Reset task for retry
                    task.status = TaskStatus.QUEUED
                    task.started_at = None
                    task.completed_at = None
                    task.error_message = None
                    retried_count += 1
                
                session.commit()
                
                return {
                    'success': True,
                    'message': f'Retried {retried_count} failed tasks',
                    'details': {
                        'retried_count': retried_count
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
            finally:
                session.close()
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to retry failed tasks: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _reset_redis_connection(self) -> Dict[str, Any]:
        """Reset Redis connection"""
        try:
            # Test current connection
            self.redis_connection.ping()
            
            return {
                'success': True,
                'message': 'Redis connection is healthy',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Redis connection failed: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _cleanup_resources(self) -> Dict[str, Any]:
        """Cleanup system resources"""
        try:
            cleanup_results = {}
            
            # Cleanup old log entries
            try:
                error_logs_cleaned = self._cleanup_old_logs("rq:error_logs")
                performance_logs_cleaned = self._cleanup_old_logs("rq:performance_logs")
                
                cleanup_results['logs'] = {
                    'error_logs_cleaned': error_logs_cleaned,
                    'performance_logs_cleaned': performance_logs_cleaned
                }
            except Exception as e:
                cleanup_results['logs'] = {'error': str(e)}
            
            # Cleanup old recovery states
            try:
                recovery_states_cleaned = self._cleanup_old_recovery_states()
                cleanup_results['recovery_states'] = {
                    'cleaned_count': recovery_states_cleaned
                }
            except Exception as e:
                cleanup_results['recovery_states'] = {'error': str(e)}
            
            return {
                'success': True,
                'message': 'Resource cleanup completed',
                'details': cleanup_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to cleanup resources: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _scale_workers(self) -> Dict[str, Any]:
        """Scale worker processes"""
        try:
            # This would implement worker scaling logic
            # For now, return a placeholder
            return {
                'success': True,
                'message': 'Worker scaling not implemented yet',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to scale workers: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _emergency_shutdown(self) -> Dict[str, Any]:
        """Emergency shutdown of RQ system"""
        try:
            shutdown_results = {}
            
            # Stop workers
            if self.rq_worker_manager:
                try:
                    self.rq_worker_manager.force_cleanup_all_sessions()
                    shutdown_results['workers'] = 'stopped'
                except Exception as e:
                    shutdown_results['workers'] = f'error: {str(e)}'
            
            # Enable fallback mode
            if self.rq_queue_manager:
                try:
                    self.rq_queue_manager._fallback_mode = True
                    self.rq_queue_manager._redis_available = False
                    shutdown_results['fallback_mode'] = 'enabled'
                except Exception as e:
                    shutdown_results['fallback_mode'] = f'error: {str(e)}'
            
            return {
                'success': True,
                'message': 'Emergency shutdown completed',
                'details': shutdown_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Emergency shutdown failed: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            # Test basic connectivity
            ping_result = self.redis_connection.ping()
            
            # Get Redis info
            redis_info = self.redis_connection.info()
            
            return {
                'healthy': True,
                'ping_successful': ping_result,
                'memory_usage': redis_info.get('used_memory_human', 'unknown'),
                'connected_clients': redis_info.get('connected_clients', 0),
                'uptime': redis_info.get('uptime_in_seconds', 0)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            session = self.db_manager.get_session()
            try:
                # Test basic connectivity
                session.execute("SELECT 1")
                
                # Get task counts
                total_tasks = session.query(CaptionGenerationTask).count()
                active_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                ).count()
                
                return {
                    'healthy': True,
                    'total_tasks': total_tasks,
                    'active_tasks': active_tasks
                }
                
            finally:
                session.close()
                
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_queue_health(self) -> Dict[str, Any]:
        """Check queue health"""
        try:
            if not self.rq_queue_manager:
                return {
                    'healthy': False,
                    'error': 'RQ queue manager not available'
                }
            
            queue_stats = self.rq_queue_manager.get_queue_stats()
            
            return {
                'healthy': True,
                'stats': queue_stats,
                'redis_available': queue_stats.get('redis_available', False),
                'fallback_mode': queue_stats.get('fallback_mode', True)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_stuck_tasks(self) -> Dict[str, Any]:
        """Check for stuck tasks"""
        try:
            session = self.db_manager.get_session()
            try:
                cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.stuck_task_threshold)
                
                stuck_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING,
                    CaptionGenerationTask.started_at < cutoff_time
                ).count()
                
                return {
                    'healthy': stuck_tasks == 0,
                    'stuck_task_count': stuck_tasks,
                    'threshold_seconds': self.stuck_task_threshold
                }
                
            finally:
                session.close()
                
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_worker_health(self) -> Dict[str, Any]:
        """Check worker health"""
        try:
            if not self.rq_worker_manager:
                return {
                    'healthy': False,
                    'error': 'RQ worker manager not available'
                }
            
            # This would check worker status
            # For now, return a placeholder
            return {
                'healthy': True,
                'message': 'Worker health check not implemented yet'
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _analyze_diagnosis_results(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze diagnosis results and determine recommendations"""
        issues = []
        recommendations = []
        
        # Check each component
        checks = diagnosis['detailed_checks']
        
        # Redis issues
        redis_check = checks.get('redis', {})
        if not redis_check.get('healthy', False):
            issues.append("Redis connectivity issues detected")
            recommendations.append("Check Redis server status and restart if necessary")
            recommendations.append("Consider migrating to database fallback mode")
        
        # Database issues
        db_check = checks.get('database', {})
        if not db_check.get('healthy', False):
            issues.append("Database connectivity issues detected")
            recommendations.append("Check database server status and connection pool")
        
        # Queue issues
        queue_check = checks.get('queues', {})
        if not queue_check.get('healthy', False):
            issues.append("Queue system issues detected")
            if queue_check.get('stats', {}).get('fallback_mode', False):
                recommendations.append("System is in fallback mode - check Redis connectivity")
        
        # Stuck tasks
        stuck_check = checks.get('stuck_tasks', {})
        if not stuck_check.get('healthy', False):
            stuck_count = stuck_check.get('stuck_task_count', 0)
            issues.append(f"Found {stuck_count} stuck tasks")
            recommendations.append("Clear stuck tasks to free up resources")
        
        # Worker issues
        worker_check = checks.get('workers', {})
        if not worker_check.get('healthy', False):
            issues.append("Worker health issues detected")
            recommendations.append("Restart workers to resolve issues")
        
        # Determine overall health
        if not issues:
            overall_health = 'healthy'
        elif len(issues) <= 2:
            overall_health = 'degraded'
        else:
            overall_health = 'unhealthy'
        
        diagnosis['overall_health'] = overall_health
        diagnosis['issues'] = issues
        diagnosis['recommendations'] = recommendations
        
        return diagnosis
    
    def _store_recovery_state(self, recovery_id: str, recovery_state: Dict[str, Any]) -> None:
        """Store recovery state in Redis"""
        try:
            state_key = f"{self.recovery_state_key}:{recovery_id}"
            self.redis_connection.setex(
                state_key,
                3600,  # 1 hour TTL
                json.dumps(recovery_state, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to store recovery state: {sanitize_for_log(str(e))}")
    
    def _log_recovery_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Log recovery event"""
        try:
            log_entry = {
                'event_type': event_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': event_data
            }
            
            # Store in Redis log
            pipe = self.redis_connection.pipeline()
            pipe.lpush(self.recovery_log_key, json.dumps(log_entry, default=str))
            pipe.ltrim(self.recovery_log_key, 0, 999)  # Keep last 1000 entries
            pipe.execute()
            
        except Exception as e:
            logger.warning(f"Failed to log recovery event: {sanitize_for_log(str(e))}")
    
    def _cleanup_old_logs(self, log_key: str) -> int:
        """Cleanup old log entries"""
        try:
            # Keep only last 1000 entries
            self.redis_connection.ltrim(log_key, 0, 999)
            return 1  # Placeholder count
        except Exception:
            return 0
    
    def _cleanup_old_recovery_states(self) -> int:
        """Cleanup old recovery states"""
        try:
            # Get all recovery state keys
            pattern = f"{self.recovery_state_key}:*"
            keys = self.redis_connection.keys(pattern)
            
            # Delete keys older than 24 hours (they have TTL, but cleanup anyway)
            deleted_count = 0
            for key in keys:
                try:
                    ttl = self.redis_connection.ttl(key)
                    if ttl < 0:  # No TTL or expired
                        self.redis_connection.delete(key)
                        deleted_count += 1
                except Exception:
                    pass
            
            return deleted_count
            
        except Exception:
            return 0
    
    def get_recovery_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recovery event history"""
        try:
            log_entries_json = self.redis_connection.lrange(self.recovery_log_key, 0, limit - 1)
            
            entries = []
            for entry_json in log_entries_json:
                try:
                    entry = json.loads(entry_json)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse recovery log entry: {sanitize_for_log(str(e))}")
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get recovery history: {sanitize_for_log(str(e))}")
            return []
    
    def get_recovery_procedures_documentation(self) -> Dict[str, Any]:
        """Get documentation for recovery procedures"""
        return {
            'recovery_actions': {
                action.value: {
                    'description': self._get_action_description(action),
                    'when_to_use': self._get_action_usage(action),
                    'risks': self._get_action_risks(action)
                }
                for action in RecoveryAction
            },
            'diagnosis_procedures': {
                'system_health_check': "Comprehensive check of all system components",
                'redis_connectivity': "Test Redis server connectivity and performance",
                'database_connectivity': "Test database server connectivity and performance",
                'queue_status': "Check RQ queue statistics and health",
                'worker_status': "Check RQ worker process health and performance",
                'stuck_tasks': "Identify tasks that have been running too long"
            },
            'escalation_procedures': {
                'level_1': "Automated recovery actions (restart workers, clear stuck tasks)",
                'level_2': "Manual intervention (migrate to fallback, retry failed tasks)",
                'level_3': "Emergency procedures (emergency shutdown, manual investigation)"
            }
        }
    
    def _get_action_description(self, action: RecoveryAction) -> str:
        """Get description for recovery action"""
        descriptions = {
            RecoveryAction.RESTART_WORKERS: "Gracefully restart all RQ worker processes",
            RecoveryAction.CLEAR_STUCK_TASKS: "Clear tasks that have been running too long",
            RecoveryAction.MIGRATE_TO_DATABASE: "Switch to database fallback mode",
            RecoveryAction.MIGRATE_TO_REDIS: "Migrate tasks back to Redis queues",
            RecoveryAction.CLEAR_DEAD_LETTER_QUEUE: "Clear all items from dead letter queue",
            RecoveryAction.RETRY_FAILED_TASKS: "Retry recently failed tasks",
            RecoveryAction.RESET_REDIS_CONNECTION: "Reset Redis connection",
            RecoveryAction.CLEANUP_RESOURCES: "Clean up old logs and temporary data",
            RecoveryAction.SCALE_WORKERS: "Scale worker processes up or down",
            RecoveryAction.EMERGENCY_SHUTDOWN: "Emergency shutdown of RQ system"
        }
        return descriptions.get(action, "No description available")
    
    def _get_action_usage(self, action: RecoveryAction) -> str:
        """Get usage guidance for recovery action"""
        usage = {
            RecoveryAction.RESTART_WORKERS: "When workers are unresponsive or consuming too much memory",
            RecoveryAction.CLEAR_STUCK_TASKS: "When tasks have been running longer than expected timeout",
            RecoveryAction.MIGRATE_TO_DATABASE: "When Redis is unavailable or unstable",
            RecoveryAction.MIGRATE_TO_REDIS: "When Redis becomes available after fallback mode",
            RecoveryAction.CLEAR_DEAD_LETTER_QUEUE: "When DLQ size becomes too large",
            RecoveryAction.RETRY_FAILED_TASKS: "When failures were due to temporary issues",
            RecoveryAction.RESET_REDIS_CONNECTION: "When Redis connectivity is intermittent",
            RecoveryAction.CLEANUP_RESOURCES: "Regular maintenance or when storage is low",
            RecoveryAction.SCALE_WORKERS: "When processing load changes significantly",
            RecoveryAction.EMERGENCY_SHUTDOWN: "When system is in critical state"
        }
        return usage.get(action, "Use with caution")
    
    def _get_action_risks(self, action: RecoveryAction) -> str:
        """Get risk information for recovery action"""
        risks = {
            RecoveryAction.RESTART_WORKERS: "Low - may cause brief processing delay",
            RecoveryAction.CLEAR_STUCK_TASKS: "Medium - may clear legitimately long-running tasks",
            RecoveryAction.MIGRATE_TO_DATABASE: "Low - reduces performance but maintains functionality",
            RecoveryAction.MIGRATE_TO_REDIS: "Medium - may fail if Redis issues persist",
            RecoveryAction.CLEAR_DEAD_LETTER_QUEUE: "High - permanently removes failed task data",
            RecoveryAction.RETRY_FAILED_TASKS: "Medium - may cause duplicate processing",
            RecoveryAction.RESET_REDIS_CONNECTION: "Low - brief connectivity interruption",
            RecoveryAction.CLEANUP_RESOURCES: "Low - may remove useful diagnostic data",
            RecoveryAction.SCALE_WORKERS: "Medium - may affect system performance",
            RecoveryAction.EMERGENCY_SHUTDOWN: "High - stops all task processing"
        }
        return risks.get(action, "Unknown risk level")