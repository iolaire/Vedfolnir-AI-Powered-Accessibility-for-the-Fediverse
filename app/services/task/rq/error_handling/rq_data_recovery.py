# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Data Recovery

Recovery procedures for corrupted or invalid task data.
Provides automated and manual recovery mechanisms for data integrity issues.
"""

import logging
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus, User, PlatformConnection, JobPriority
from .rq_task_validator import RQTaskValidator, ValidationResult

logger = logging.getLogger(__name__)


class RecoveryMethod(Enum):
    """Available recovery methods"""
    RESTORE_FROM_BACKUP = "restore_from_backup"
    RECONSTRUCT_FROM_LOGS = "reconstruct_from_logs"
    MANUAL_RECOVERY = "manual_recovery"
    RESET_TO_DEFAULTS = "reset_to_defaults"
    PARTIAL_RECOVERY = "partial_recovery"


class RecoveryStatus(Enum):
    """Recovery operation status"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    NOT_RECOVERABLE = "not_recoverable"


class RecoveryResult:
    """Result of data recovery operation"""
    
    def __init__(self):
        self.status = RecoveryStatus.FAILED
        self.method_used = None
        self.recovered_data = None
        self.recovery_notes = []
        self.validation_result = None
        self.recovery_timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'status': self.status.value,
            'method_used': self.method_used.value if self.method_used else None,
            'recovered_data': self.recovered_data,
            'recovery_notes': self.recovery_notes,
            'validation_result': self.validation_result.to_dict() if self.validation_result else None,
            'recovery_timestamp': self.recovery_timestamp.isoformat()
        }


class RQDataRecovery:
    """Data recovery system for corrupted or invalid task data"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis,
                 task_validator: RQTaskValidator, config: Optional[Dict[str, Any]] = None):
        """
        Initialize RQ Data Recovery
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for recovery state
            task_validator: Task validator for validation during recovery
            config: Optional configuration for recovery
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.task_validator = task_validator
        self.config = config or {}
        
        # Recovery configuration
        self.backup_retention_days = self.config.get('backup_retention_days', 7)
        self.max_recovery_attempts = self.config.get('max_recovery_attempts', 3)
        self.enable_auto_recovery = self.config.get('enable_auto_recovery', True)
        
        # Redis keys for recovery data
        self.backup_key_prefix = "rq:backup"
        self.recovery_log_key = "rq:recovery_log"
        self.recovery_state_key = "rq:recovery_state"
        
        logger.info("RQ Data Recovery initialized with comprehensive recovery capabilities")
    
    def create_task_backup(self, task: CaptionGenerationTask) -> bool:
        """
        Create backup of task data before processing
        
        Args:
            task: The task to backup
            
        Returns:
            bool: True if backup was created successfully
        """
        try:
            backup_data = {
                'task_id': task.id,
                'user_id': task.user_id,
                'platform_connection_id': task.platform_connection_id,
                'status': task.status.value if task.status else None,
                'priority': task.priority.value if task.priority else None,
                'settings': task.settings,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message,
                'backup_timestamp': datetime.now(timezone.utc).isoformat(),
                'backup_version': 1
            }
            
            # Calculate backup hash for integrity
            backup_json = json.dumps(backup_data, sort_keys=True, default=str)
            backup_hash = hashlib.sha256(backup_json.encode()).hexdigest()
            backup_data['backup_hash'] = backup_hash
            
            # Store backup in Redis
            backup_key = f"{self.backup_key_prefix}:{task.id}"
            
            self.redis_connection.setex(
                backup_key,
                86400 * self.backup_retention_days,  # TTL based on retention
                json.dumps(backup_data, default=str)
            )
            
            logger.debug(f"Created backup for task {sanitize_for_log(task.id)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create task backup: {sanitize_for_log(str(e))}")
            return False
    
    def recover_corrupted_task(self, task_id: str, 
                              corruption_details: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        """
        Attempt to recover corrupted task data
        
        Args:
            task_id: The ID of the corrupted task
            corruption_details: Optional details about the corruption
            
        Returns:
            RecoveryResult with recovery details
        """
        result = RecoveryResult()
        
        try:
            logger.info(f"Starting recovery for corrupted task {sanitize_for_log(task_id)}")
            
            # Try recovery methods in order of preference
            recovery_methods = [
                RecoveryMethod.RESTORE_FROM_BACKUP,
                RecoveryMethod.RECONSTRUCT_FROM_LOGS,
                RecoveryMethod.PARTIAL_RECOVERY,
                RecoveryMethod.RESET_TO_DEFAULTS
            ]
            
            for method in recovery_methods:
                try:
                    recovery_attempt = self._attempt_recovery(task_id, method, corruption_details)
                    
                    if recovery_attempt.status in [RecoveryStatus.SUCCESS, RecoveryStatus.PARTIAL_SUCCESS]:
                        result = recovery_attempt
                        break
                        
                except Exception as e:
                    logger.warning(f"Recovery method {method.value} failed: {sanitize_for_log(str(e))}")
                    result.recovery_notes.append(f"Method {method.value} failed: {str(e)}")
            
            # Log recovery attempt
            self._log_recovery_attempt(task_id, result, corruption_details)
            
            return result
            
        except Exception as e:
            logger.error(f"Recovery process failed for task {sanitize_for_log(task_id)}: {sanitize_for_log(str(e))}")
            result.status = RecoveryStatus.FAILED
            result.recovery_notes.append(f"Recovery process failed: {str(e)}")
            return result
    
    def _attempt_recovery(self, task_id: str, method: RecoveryMethod, 
                         corruption_details: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        """Attempt recovery using specific method"""
        result = RecoveryResult()
        result.method_used = method
        
        if method == RecoveryMethod.RESTORE_FROM_BACKUP:
            return self._restore_from_backup(task_id, result)
        elif method == RecoveryMethod.RECONSTRUCT_FROM_LOGS:
            return self._reconstruct_from_logs(task_id, result)
        elif method == RecoveryMethod.PARTIAL_RECOVERY:
            return self._partial_recovery(task_id, result, corruption_details)
        elif method == RecoveryMethod.RESET_TO_DEFAULTS:
            return self._reset_to_defaults(task_id, result)
        else:
            result.recovery_notes.append(f"Unknown recovery method: {method.value}")
            return result
    
    def _restore_from_backup(self, task_id: str, result: RecoveryResult) -> RecoveryResult:
        """Restore task from backup data"""
        try:
            # Get backup data
            backup_key = f"{self.backup_key_prefix}:{task_id}"
            backup_data_json = self.redis_connection.get(backup_key)
            
            if not backup_data_json:
                result.recovery_notes.append("No backup data found")
                return result
            
            backup_data = json.loads(backup_data_json)
            
            # Verify backup integrity
            stored_hash = backup_data.pop('backup_hash', None)
            if stored_hash:
                backup_json = json.dumps(backup_data, sort_keys=True, default=str)
                calculated_hash = hashlib.sha256(backup_json.encode()).hexdigest()
                
                if calculated_hash != stored_hash:
                    result.recovery_notes.append("Backup data integrity check failed")
                    return result
            
            # Restore task data
            session = self.db_manager.get_session()
            try:
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    result.recovery_notes.append("Task not found in database")
                    return result
                
                # Restore fields from backup
                task.user_id = backup_data.get('user_id')
                task.platform_connection_id = backup_data.get('platform_connection_id')
                task.settings = backup_data.get('settings')
                task.error_message = None  # Clear error message on recovery
                
                # Restore status and priority
                if backup_data.get('status'):
                    task.status = TaskStatus(backup_data['status'])
                
                if backup_data.get('priority'):
                    task.priority = JobPriority(backup_data['priority'])
                
                # Restore timestamps
                if backup_data.get('created_at'):
                    task.created_at = datetime.fromisoformat(backup_data['created_at'].replace('Z', '+00:00'))
                
                session.commit()
                
                # Validate restored data
                result.validation_result = self.task_validator.validate_task_for_enqueue(task)
                
                if result.validation_result.is_valid:
                    result.status = RecoveryStatus.SUCCESS
                    result.recovered_data = backup_data
                    result.recovery_notes.append("Successfully restored from backup")
                else:
                    result.status = RecoveryStatus.PARTIAL_SUCCESS
                    result.recovered_data = backup_data
                    result.recovery_notes.append("Restored from backup but validation issues remain")
                
            finally:
                session.close()
            
            return result
            
        except Exception as e:
            result.recovery_notes.append(f"Backup restoration failed: {str(e)}")
            return result
    
    def _reconstruct_from_logs(self, task_id: str, result: RecoveryResult) -> RecoveryResult:
        """Reconstruct task data from logs"""
        try:
            # This would analyze logs to reconstruct task data
            # For now, we'll implement a placeholder
            
            result.recovery_notes.append("Log reconstruction not yet implemented")
            
            # In a full implementation, you would:
            # 1. Search through error logs, performance logs, etc.
            # 2. Extract task-related information
            # 3. Reconstruct the task data from log entries
            # 4. Validate the reconstructed data
            
            return result
            
        except Exception as e:
            result.recovery_notes.append(f"Log reconstruction failed: {str(e)}")
            return result
    
    def _partial_recovery(self, task_id: str, result: RecoveryResult, 
                         corruption_details: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        """Attempt partial recovery of task data"""
        try:
            session = self.db_manager.get_session()
            try:
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    result.recovery_notes.append("Task not found for partial recovery")
                    return result
                
                recovery_applied = False
                
                # Try to recover user information
                if not task.user_id or task.user_id <= 0:
                    # Try to find user from platform connection
                    if task.platform_connection_id:
                        platform_conn = session.query(PlatformConnection).filter_by(
                            id=task.platform_connection_id
                        ).first()
                        
                        if platform_conn:
                            task.user_id = platform_conn.user_id
                            recovery_applied = True
                            result.recovery_notes.append("Recovered user_id from platform connection")
                
                # Try to recover platform connection
                if not task.platform_connection_id and task.user_id:
                    # Find active platform connection for user
                    platform_conn = session.query(PlatformConnection).filter_by(
                        user_id=task.user_id,
                        is_active=True
                    ).first()
                    
                    if platform_conn:
                        task.platform_connection_id = platform_conn.id
                        recovery_applied = True
                        result.recovery_notes.append("Recovered platform_connection_id from user")
                
                # Try to recover settings
                if not task.settings or not isinstance(task.settings, dict):
                    # Set default settings
                    task.settings = {
                        'caption_length': 300,
                        'include_hashtags': True,
                        'language': 'en',
                        'recovered': True,
                        'recovery_timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    recovery_applied = True
                    result.recovery_notes.append("Applied default settings")
                
                # Try to recover priority
                if not task.priority:
                    task.priority = JobPriority.NORMAL
                    recovery_applied = True
                    result.recovery_notes.append("Set default priority")
                
                # Try to recover status
                if not task.status:
                    task.status = TaskStatus.QUEUED
                    recovery_applied = True
                    result.recovery_notes.append("Reset status to QUEUED")
                
                if recovery_applied:
                    session.commit()
                    
                    # Validate partially recovered data
                    result.validation_result = self.task_validator.validate_task_for_enqueue(task)
                    
                    if result.validation_result.is_valid:
                        result.status = RecoveryStatus.PARTIAL_SUCCESS
                        result.recovered_data = {
                            'user_id': task.user_id,
                            'platform_connection_id': task.platform_connection_id,
                            'settings': task.settings,
                            'priority': task.priority.value if task.priority else None,
                            'status': task.status.value if task.status else None
                        }
                        result.recovery_notes.append("Partial recovery successful")
                    else:
                        result.recovery_notes.append("Partial recovery applied but validation failed")
                else:
                    result.recovery_notes.append("No partial recovery could be applied")
                
            finally:
                session.close()
            
            return result
            
        except Exception as e:
            result.recovery_notes.append(f"Partial recovery failed: {str(e)}")
            return result
    
    def _reset_to_defaults(self, task_id: str, result: RecoveryResult) -> RecoveryResult:
        """Reset task to default values as last resort"""
        try:
            session = self.db_manager.get_session()
            try:
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                
                if not task:
                    result.recovery_notes.append("Task not found for reset")
                    return result
                
                # Reset to minimal viable state
                original_user_id = task.user_id
                original_platform_id = task.platform_connection_id
                
                # Keep original IDs if they exist and are valid
                if not original_user_id or original_user_id <= 0:
                    result.recovery_notes.append("Cannot reset - no valid user_id")
                    return result
                
                if not original_platform_id or original_platform_id <= 0:
                    result.recovery_notes.append("Cannot reset - no valid platform_connection_id")
                    return result
                
                # Reset all other fields to defaults
                task.status = TaskStatus.FAILED  # Mark as failed due to corruption
                task.priority = JobPriority.NORMAL
                task.settings = {
                    'caption_length': 300,
                    'include_hashtags': True,
                    'language': 'en',
                    'reset_recovery': True,
                    'recovery_reason': 'Data corruption - reset to defaults',
                    'recovery_timestamp': datetime.now(timezone.utc).isoformat()
                }
                task.error_message = "Task data was corrupted and reset to defaults"
                task.completed_at = datetime.now(timezone.utc)
                
                session.commit()
                
                result.status = RecoveryStatus.PARTIAL_SUCCESS
                result.recovered_data = {
                    'user_id': task.user_id,
                    'platform_connection_id': task.platform_connection_id,
                    'status': task.status.value,
                    'priority': task.priority.value,
                    'settings': task.settings,
                    'reset_applied': True
                }
                result.recovery_notes.append("Reset to default values - task marked as failed")
                
            finally:
                session.close()
            
            return result
            
        except Exception as e:
            result.recovery_notes.append(f"Reset to defaults failed: {str(e)}")
            return result
    
    def validate_recovery_integrity(self, task_id: str, 
                                   recovery_result: RecoveryResult) -> ValidationResult:
        """
        Validate the integrity of recovered data
        
        Args:
            task_id: The task ID that was recovered
            recovery_result: The recovery result to validate
            
        Returns:
            ValidationResult for the recovery
        """
        try:
            # Use the task validator to validate recovery
            validation_data = {
                'task_id': task_id,
                'recovery_method': recovery_result.method_used.value if recovery_result.method_used else None,
                'original_data': None,  # Would be populated with original corrupted data
                'recovered_data': recovery_result.recovered_data
            }
            
            return self.task_validator.validate_corrupted_task_recovery(task_id, validation_data)
            
        except Exception as e:
            logger.error(f"Recovery integrity validation failed: {sanitize_for_log(str(e))}")
            
            # Create a failed validation result
            from .rq_task_validator import ValidationResult
            result = ValidationResult()
            result.add_error(f"Recovery integrity validation failed: {str(e)}", code="RECOVERY_VALIDATION_ERROR")
            return result
    
    def _log_recovery_attempt(self, task_id: str, recovery_result: RecoveryResult,
                             corruption_details: Optional[Dict[str, Any]] = None) -> None:
        """Log recovery attempt for audit purposes"""
        try:
            log_entry = {
                'task_id': task_id,
                'recovery_timestamp': recovery_result.recovery_timestamp.isoformat(),
                'recovery_status': recovery_result.status.value,
                'method_used': recovery_result.method_used.value if recovery_result.method_used else None,
                'recovery_notes': recovery_result.recovery_notes,
                'corruption_details': corruption_details,
                'validation_passed': recovery_result.validation_result.is_valid if recovery_result.validation_result else None
            }
            
            # Store in Redis log
            pipe = self.redis_connection.pipeline()
            pipe.lpush(self.recovery_log_key, json.dumps(log_entry, default=str))
            pipe.ltrim(self.recovery_log_key, 0, 999)  # Keep last 1000 entries
            pipe.execute()
            
            logger.info(f"Logged recovery attempt for task {sanitize_for_log(task_id)}: {recovery_result.status.value}")
            
        except Exception as e:
            logger.warning(f"Failed to log recovery attempt: {sanitize_for_log(str(e))}")
    
    def get_recovery_history(self, task_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recovery history
        
        Args:
            task_id: Optional task ID to filter by
            limit: Maximum number of entries to return
            
        Returns:
            List of recovery log entries
        """
        try:
            log_entries_json = self.redis_connection.lrange(self.recovery_log_key, 0, limit - 1)
            
            entries = []
            for entry_json in log_entries_json:
                try:
                    entry = json.loads(entry_json)
                    
                    # Filter by task_id if specified
                    if task_id and entry.get('task_id') != task_id:
                        continue
                    
                    entries.append(entry)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse recovery log entry: {sanitize_for_log(str(e))}")
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get recovery history: {sanitize_for_log(str(e))}")
            return []
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        try:
            history = self.get_recovery_history(limit=200)
            
            stats = {
                'total_recoveries': len(history),
                'recovery_methods': {},
                'recovery_status': {},
                'success_rate': 0,
                'recent_recoveries': 0
            }
            
            # Analyze recovery data
            successful_recoveries = 0
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            for entry in history:
                # Count by method
                method = entry.get('method_used', 'unknown')
                stats['recovery_methods'][method] = stats['recovery_methods'].get(method, 0) + 1
                
                # Count by status
                status = entry.get('recovery_status', 'unknown')
                stats['recovery_status'][status] = stats['recovery_status'].get(status, 0) + 1
                
                # Count successful recoveries
                if status in ['success', 'partial_success']:
                    successful_recoveries += 1
                
                # Count recent recoveries
                try:
                    recovery_time = datetime.fromisoformat(entry['recovery_timestamp'].replace('Z', '+00:00'))
                    if recovery_time > recent_cutoff:
                        stats['recent_recoveries'] += 1
                except (ValueError, KeyError):
                    pass
            
            # Calculate success rate
            if len(history) > 0:
                stats['success_rate'] = (successful_recoveries / len(history)) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get recovery statistics: {sanitize_for_log(str(e))}")
            return {'error': 'Failed to retrieve recovery statistics'}
    
    def cleanup_old_backups(self, older_than_days: int = None) -> int:
        """
        Clean up old backup data
        
        Args:
            older_than_days: Remove backups older than this many days
            
        Returns:
            Number of backups cleaned up
        """
        if older_than_days is None:
            older_than_days = self.backup_retention_days
        
        try:
            backup_keys = self.redis_connection.keys(f"{self.backup_key_prefix}:*")
            cleaned_count = 0
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            
            for key in backup_keys:
                try:
                    backup_data_json = self.redis_connection.get(key)
                    if backup_data_json:
                        backup_data = json.loads(backup_data_json)
                        backup_timestamp_str = backup_data.get('backup_timestamp')
                        
                        if backup_timestamp_str:
                            backup_timestamp = datetime.fromisoformat(backup_timestamp_str.replace('Z', '+00:00'))
                            
                            if backup_timestamp < cutoff_time:
                                self.redis_connection.delete(key)
                                cleaned_count += 1
                                
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                    # Delete corrupted backup entries
                    self.redis_connection.delete(key)
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old backup entries")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {sanitize_for_log(str(e))}")
            return 0
    
    def get_backup_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get backup status for a specific task
        
        Args:
            task_id: The task ID to check
            
        Returns:
            Backup status information or None if no backup exists
        """
        try:
            backup_key = f"{self.backup_key_prefix}:{task_id}"
            backup_data_json = self.redis_connection.get(backup_key)
            
            if backup_data_json:
                backup_data = json.loads(backup_data_json)
                
                return {
                    'exists': True,
                    'backup_timestamp': backup_data.get('backup_timestamp'),
                    'backup_version': backup_data.get('backup_version', 1),
                    'has_integrity_hash': 'backup_hash' in backup_data,
                    'ttl': self.redis_connection.ttl(backup_key)
                }
            else:
                return {
                    'exists': False,
                    'backup_timestamp': None,
                    'backup_version': None,
                    'has_integrity_hash': False,
                    'ttl': -1
                }
                
        except Exception as e:
            logger.error(f"Failed to get backup status: {sanitize_for_log(str(e))}")
            return None