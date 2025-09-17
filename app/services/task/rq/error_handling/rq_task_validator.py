# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
RQ Task Validator

Comprehensive task validation and data integrity checks for RQ operations.
Validates task data before enqueuing and during processing to ensure data integrity.
"""

import logging
import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple, Union
from enum import Enum
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.core.security_utils import sanitize_for_log
from models import CaptionGenerationTask, TaskStatus, User, PlatformConnection, JobPriority

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult:
    """Result of task validation"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.info = []
        self.data_integrity_hash = None
        self.validation_timestamp = datetime.now(timezone.utc)
    
    def add_error(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add validation error"""
        self.is_valid = False
        self.errors.append({
            'message': message,
            'field': field,
            'code': code,
            'severity': ValidationSeverity.ERROR.value
        })
    
    def add_warning(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add validation warning"""
        self.warnings.append({
            'message': message,
            'field': field,
            'code': code,
            'severity': ValidationSeverity.WARNING.value
        })
    
    def add_info(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        """Add validation info"""
        self.info.append({
            'message': message,
            'field': field,
            'code': code,
            'severity': ValidationSeverity.INFO.value
        })
    
    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all validation issues"""
        return self.errors + self.warnings + self.info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'data_integrity_hash': self.data_integrity_hash,
            'validation_timestamp': self.validation_timestamp.isoformat()
        }


class RQTaskValidator:
    """Comprehensive task validation and data integrity checker"""
    
    def __init__(self, db_manager: DatabaseManager, redis_connection: redis.Redis,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize RQ Task Validator
        
        Args:
            db_manager: Database manager instance
            redis_connection: Redis connection for validation state
            config: Optional configuration for validation
        """
        self.db_manager = db_manager
        self.redis_connection = redis_connection
        self.config = config or {}
        
        # Validation configuration
        self.max_task_id_length = self.config.get('max_task_id_length', 255)
        self.max_settings_size = self.config.get('max_settings_size', 10240)  # 10KB
        self.max_error_message_length = self.config.get('max_error_message_length', 2048)
        self.enable_integrity_checks = self.config.get('enable_integrity_checks', True)
        self.enable_cross_validation = self.config.get('enable_cross_validation', True)
        
        # Redis keys for validation state
        self.validation_cache_key = "rq:validation_cache"
        self.integrity_hash_key = "rq:integrity_hashes"
        
        # Validation patterns
        self.task_id_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        self.safe_string_pattern = re.compile(r'^[a-zA-Z0-9\s\-_.,!?()]+$')
        
        logger.info("RQ Task Validator initialized with comprehensive validation")
    
    def validate_task_for_enqueue(self, task: CaptionGenerationTask) -> ValidationResult:
        """
        Validate task before enqueuing to RQ
        
        Args:
            task: The task to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult()
        
        try:
            # Basic field validation
            self._validate_basic_fields(task, result)
            
            # Task ID validation
            self._validate_task_id(task, result)
            
            # User validation
            self._validate_user(task, result)
            
            # Platform connection validation
            self._validate_platform_connection(task, result)
            
            # Settings validation
            self._validate_settings(task, result)
            
            # Priority validation
            self._validate_priority(task, result)
            
            # Cross-validation checks
            if self.enable_cross_validation:
                self._validate_cross_references(task, result)
            
            # Data integrity checks
            if self.enable_integrity_checks:
                self._calculate_data_integrity_hash(task, result)
            
            # Store validation result
            self._store_validation_result(task.id, result)
            
            logger.debug(f"Task validation completed for {sanitize_for_log(task.id)}: valid={result.is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Task validation failed: {sanitize_for_log(str(e))}")
            result.add_error(f"Validation process failed: {str(e)}", code="VALIDATION_ERROR")
            return result
    
    def validate_task_during_processing(self, task: CaptionGenerationTask) -> ValidationResult:
        """
        Validate task during processing to ensure data integrity
        
        Args:
            task: The task being processed
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult()
        
        try:
            # Check if task exists and is in correct state
            self._validate_task_state(task, result)
            
            # Validate data integrity
            if self.enable_integrity_checks:
                self._validate_data_integrity(task, result)
            
            # Validate processing constraints
            self._validate_processing_constraints(task, result)
            
            # Check for data corruption
            self._check_data_corruption(task, result)
            
            logger.debug(f"Processing validation completed for {sanitize_for_log(task.id)}: valid={result.is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Processing validation failed: {sanitize_for_log(str(e))}")
            result.add_error(f"Processing validation failed: {str(e)}", code="PROCESSING_VALIDATION_ERROR")
            return result
    
    def validate_task_completion(self, task: CaptionGenerationTask, 
                                processing_result: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate task upon completion
        
        Args:
            task: The completed task
            processing_result: Optional processing result data
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult()
        
        try:
            # Validate completion state
            self._validate_completion_state(task, result)
            
            # Validate processing result
            if processing_result:
                self._validate_processing_result(processing_result, result)
            
            # Check completion timestamps
            self._validate_completion_timestamps(task, result)
            
            # Final data integrity check
            if self.enable_integrity_checks:
                self._validate_final_integrity(task, result)
            
            logger.debug(f"Completion validation completed for {sanitize_for_log(task.id)}: valid={result.is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Completion validation failed: {sanitize_for_log(str(e))}")
            result.add_error(f"Completion validation failed: {str(e)}", code="COMPLETION_VALIDATION_ERROR")
            return result
    
    def _validate_basic_fields(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate basic task fields"""
        # Task ID
        if not task.id:
            result.add_error("Task ID is required", field="id", code="MISSING_TASK_ID")
        elif len(task.id) > self.max_task_id_length:
            result.add_error(f"Task ID too long (max {self.max_task_id_length})", field="id", code="TASK_ID_TOO_LONG")
        
        # User ID
        if not task.user_id:
            result.add_error("User ID is required", field="user_id", code="MISSING_USER_ID")
        elif not isinstance(task.user_id, int) or task.user_id <= 0:
            result.add_error("User ID must be a positive integer", field="user_id", code="INVALID_USER_ID")
        
        # Platform connection ID
        if not task.platform_connection_id:
            result.add_error("Platform connection ID is required", field="platform_connection_id", code="MISSING_PLATFORM_CONNECTION_ID")
        elif not isinstance(task.platform_connection_id, int) or task.platform_connection_id <= 0:
            result.add_error("Platform connection ID must be a positive integer", field="platform_connection_id", code="INVALID_PLATFORM_CONNECTION_ID")
        
        # Status
        if task.status and task.status not in [status for status in TaskStatus]:
            result.add_error(f"Invalid task status: {task.status}", field="status", code="INVALID_STATUS")
    
    def _validate_task_id(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate task ID format and uniqueness"""
        if not task.id:
            return
        
        # Format validation
        if not self.task_id_pattern.match(task.id):
            result.add_error("Task ID contains invalid characters", field="id", code="INVALID_TASK_ID_FORMAT")
        
        # Check for potential security issues
        if any(char in task.id for char in ['<', '>', '"', "'", '&']):
            result.add_error("Task ID contains potentially unsafe characters", field="id", code="UNSAFE_TASK_ID")
        
        # Length validation (already checked in basic fields, but double-check)
        if len(task.id) < 8:
            result.add_warning("Task ID is very short, consider longer IDs for security", field="id", code="SHORT_TASK_ID")
        
        # Uniqueness check (in database)
        try:
            session = self.db_manager.get_session()
            try:
                existing_task = session.query(CaptionGenerationTask).filter_by(id=task.id).first()
                if existing_task and existing_task.id != task.id:
                    result.add_error("Task ID already exists", field="id", code="DUPLICATE_TASK_ID")
            finally:
                session.close()
        except Exception as e:
            result.add_warning(f"Could not check task ID uniqueness: {str(e)}", field="id", code="UNIQUENESS_CHECK_FAILED")
    
    def _validate_user(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate user exists and is active"""
        if not task.user_id:
            return
        
        try:
            session = self.db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=task.user_id).first()
                
                if not user:
                    result.add_error(f"User {task.user_id} not found", field="user_id", code="USER_NOT_FOUND")
                else:
                    # Check if user is active (assuming there's an is_active field)
                    if hasattr(user, 'is_active') and not user.is_active:
                        result.add_error(f"User {task.user_id} is not active", field="user_id", code="USER_INACTIVE")
                    
                    # Add user info for context
                    result.add_info(f"User validated: {user.username}", field="user_id", code="USER_VALIDATED")
                    
            finally:
                session.close()
                
        except Exception as e:
            result.add_warning(f"Could not validate user: {str(e)}", field="user_id", code="USER_VALIDATION_FAILED")
    
    def _validate_platform_connection(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate platform connection exists and is active"""
        if not task.platform_connection_id:
            return
        
        try:
            session = self.db_manager.get_session()
            try:
                platform_connection = session.query(PlatformConnection).filter_by(
                    id=task.platform_connection_id
                ).first()
                
                if not platform_connection:
                    result.add_error(
                        f"Platform connection {task.platform_connection_id} not found",
                        field="platform_connection_id",
                        code="PLATFORM_CONNECTION_NOT_FOUND"
                    )
                else:
                    # Check if connection is active
                    if not platform_connection.is_active:
                        result.add_error(
                            f"Platform connection {task.platform_connection_id} is not active",
                            field="platform_connection_id",
                            code="PLATFORM_CONNECTION_INACTIVE"
                        )
                    
                    # Check if connection belongs to the user
                    if platform_connection.user_id != task.user_id:
                        result.add_error(
                            f"Platform connection {task.platform_connection_id} does not belong to user {task.user_id}",
                            field="platform_connection_id",
                            code="PLATFORM_CONNECTION_USER_MISMATCH"
                        )
                    
                    # Add connection info for context
                    result.add_info(
                        f"Platform connection validated: {platform_connection.platform_name}",
                        field="platform_connection_id",
                        code="PLATFORM_CONNECTION_VALIDATED"
                    )
                    
            finally:
                session.close()
                
        except Exception as e:
            result.add_warning(
                f"Could not validate platform connection: {str(e)}",
                field="platform_connection_id",
                code="PLATFORM_CONNECTION_VALIDATION_FAILED"
            )
    
    def _validate_settings(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate task settings"""
        if not task.settings:
            result.add_warning("Task has no settings", field="settings", code="NO_SETTINGS")
            return
        
        try:
            # Check settings size
            settings_json = json.dumps(task.settings)
            if len(settings_json) > self.max_settings_size:
                result.add_error(
                    f"Settings too large (max {self.max_settings_size} bytes)",
                    field="settings",
                    code="SETTINGS_TOO_LARGE"
                )
            
            # Validate settings structure
            if not isinstance(task.settings, dict):
                result.add_error("Settings must be a dictionary", field="settings", code="INVALID_SETTINGS_TYPE")
                return
            
            # Check for required settings fields
            required_fields = ['caption_length', 'include_hashtags', 'language']
            for field in required_fields:
                if field not in task.settings:
                    result.add_warning(f"Missing recommended setting: {field}", field="settings", code="MISSING_SETTING")
            
            # Validate specific settings
            self._validate_caption_settings(task.settings, result)
            
            # Check for potentially unsafe settings
            self._validate_settings_security(task.settings, result)
            
        except Exception as e:
            result.add_error(f"Settings validation failed: {str(e)}", field="settings", code="SETTINGS_VALIDATION_ERROR")
    
    def _validate_caption_settings(self, settings: Dict[str, Any], result: ValidationResult) -> None:
        """Validate caption-specific settings"""
        # Caption length
        if 'caption_length' in settings:
            caption_length = settings['caption_length']
            if not isinstance(caption_length, int) or caption_length < 50 or caption_length > 2000:
                result.add_error(
                    "Caption length must be between 50 and 2000 characters",
                    field="settings.caption_length",
                    code="INVALID_CAPTION_LENGTH"
                )
        
        # Language
        if 'language' in settings:
            language = settings['language']
            if not isinstance(language, str) or len(language) != 2:
                result.add_error(
                    "Language must be a 2-character language code",
                    field="settings.language",
                    code="INVALID_LANGUAGE"
                )
        
        # Include hashtags
        if 'include_hashtags' in settings:
            include_hashtags = settings['include_hashtags']
            if not isinstance(include_hashtags, bool):
                result.add_error(
                    "include_hashtags must be a boolean",
                    field="settings.include_hashtags",
                    code="INVALID_INCLUDE_HASHTAGS"
                )
        
        # Custom prompt
        if 'custom_prompt' in settings:
            custom_prompt = settings['custom_prompt']
            if isinstance(custom_prompt, str) and len(custom_prompt) > 500:
                result.add_warning(
                    "Custom prompt is very long",
                    field="settings.custom_prompt",
                    code="LONG_CUSTOM_PROMPT"
                )
    
    def _validate_settings_security(self, settings: Dict[str, Any], result: ValidationResult) -> None:
        """Validate settings for security issues"""
        # Check for potentially dangerous keys
        dangerous_keys = ['eval', 'exec', 'import', '__', 'system', 'shell']
        
        def check_dict_recursively(d, path=""):
            for key, value in d.items():
                full_path = f"{path}.{key}" if path else key
                
                # Check key names
                if any(dangerous in str(key).lower() for dangerous in dangerous_keys):
                    result.add_warning(
                        f"Potentially unsafe setting key: {key}",
                        field=f"settings{full_path}",
                        code="UNSAFE_SETTING_KEY"
                    )
                
                # Check string values for injection patterns
                if isinstance(value, str):
                    if any(pattern in value.lower() for pattern in ['<script', 'javascript:', 'eval(', 'exec(']):
                        result.add_error(
                            f"Potentially unsafe setting value: {key}",
                            field=f"settings{full_path}",
                            code="UNSAFE_SETTING_VALUE"
                        )
                
                # Recursively check nested dictionaries
                elif isinstance(value, dict):
                    check_dict_recursively(value, full_path)
        
        try:
            check_dict_recursively(settings)
        except Exception as e:
            result.add_warning(f"Security validation failed: {str(e)}", field="settings", code="SECURITY_CHECK_FAILED")
    
    def _validate_priority(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate task priority"""
        if task.priority:
            if task.priority not in [priority for priority in JobPriority]:
                result.add_error(f"Invalid priority: {task.priority}", field="priority", code="INVALID_PRIORITY")
        else:
            result.add_info("No priority set, will use default", field="priority", code="DEFAULT_PRIORITY")
    
    def _validate_cross_references(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate cross-references between task fields"""
        try:
            session = self.db_manager.get_session()
            try:
                # Check if user owns the platform connection
                if task.user_id and task.platform_connection_id:
                    platform_connection = session.query(PlatformConnection).filter_by(
                        id=task.platform_connection_id,
                        user_id=task.user_id
                    ).first()
                    
                    if not platform_connection:
                        result.add_error(
                            "Platform connection does not belong to the specified user",
                            field="cross_reference",
                            code="CROSS_REFERENCE_MISMATCH"
                        )
                
                # Check for existing active tasks for the user
                if task.user_id:
                    active_tasks = session.query(CaptionGenerationTask).filter(
                        CaptionGenerationTask.user_id == task.user_id,
                        CaptionGenerationTask.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING])
                    ).count()
                    
                    if active_tasks > 0:
                        result.add_warning(
                            f"User has {active_tasks} active tasks",
                            field="cross_reference",
                            code="EXISTING_ACTIVE_TASKS"
                        )
                        
            finally:
                session.close()
                
        except Exception as e:
            result.add_warning(f"Cross-reference validation failed: {str(e)}", field="cross_reference", code="CROSS_REFERENCE_ERROR")
    
    def _calculate_data_integrity_hash(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Calculate data integrity hash for the task"""
        try:
            # Create hash of critical task data
            hash_data = {
                'id': task.id,
                'user_id': task.user_id,
                'platform_connection_id': task.platform_connection_id,
                'settings': task.settings,
                'priority': task.priority.value if task.priority else None
            }
            
            hash_string = json.dumps(hash_data, sort_keys=True, default=str)
            integrity_hash = hashlib.sha256(hash_string.encode()).hexdigest()
            
            result.data_integrity_hash = integrity_hash
            
            # Store hash for later validation
            self._store_integrity_hash(task.id, integrity_hash)
            
            result.add_info(f"Data integrity hash calculated: {integrity_hash[:16]}...", code="INTEGRITY_HASH_CALCULATED")
            
        except Exception as e:
            result.add_warning(f"Could not calculate integrity hash: {str(e)}", code="INTEGRITY_HASH_FAILED")
    
    def _validate_task_state(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate task state during processing"""
        # Check if task is in a valid processing state
        if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
            result.add_error(
                f"Task is not in a valid processing state: {task.status}",
                field="status",
                code="INVALID_PROCESSING_STATE"
            )
        
        # Check timestamps
        if task.status == TaskStatus.RUNNING and not task.started_at:
            result.add_error("Running task missing start timestamp", field="started_at", code="MISSING_START_TIMESTAMP")
        
        if task.started_at and task.completed_at and task.started_at > task.completed_at:
            result.add_error("Start timestamp after completion timestamp", field="timestamps", code="INVALID_TIMESTAMPS")
    
    def _validate_data_integrity(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate data integrity during processing"""
        try:
            # Get stored integrity hash
            stored_hash = self._get_integrity_hash(task.id)
            
            if stored_hash:
                # Recalculate hash
                hash_data = {
                    'id': task.id,
                    'user_id': task.user_id,
                    'platform_connection_id': task.platform_connection_id,
                    'settings': task.settings,
                    'priority': task.priority.value if task.priority else None
                }
                
                hash_string = json.dumps(hash_data, sort_keys=True, default=str)
                current_hash = hashlib.sha256(hash_string.encode()).hexdigest()
                
                if current_hash != stored_hash:
                    result.add_error(
                        "Data integrity check failed - task data has been modified",
                        code="DATA_INTEGRITY_VIOLATION"
                    )
                else:
                    result.add_info("Data integrity check passed", code="DATA_INTEGRITY_OK")
            else:
                result.add_warning("No stored integrity hash found", code="NO_INTEGRITY_HASH")
                
        except Exception as e:
            result.add_warning(f"Data integrity check failed: {str(e)}", code="INTEGRITY_CHECK_ERROR")
    
    def _validate_processing_constraints(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate processing constraints"""
        # Check processing time limits
        if task.started_at:
            processing_time = datetime.now(timezone.utc) - task.started_at
            max_processing_time = 3600  # 1 hour
            
            if processing_time.total_seconds() > max_processing_time:
                result.add_error(
                    f"Task processing time exceeded limit ({processing_time.total_seconds():.0f}s > {max_processing_time}s)",
                    field="processing_time",
                    code="PROCESSING_TIME_EXCEEDED"
                )
        
        # Check resource constraints (placeholder)
        # In a real implementation, you might check memory usage, CPU usage, etc.
        result.add_info("Processing constraints validated", code="CONSTRAINTS_OK")
    
    def _check_data_corruption(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Check for signs of data corruption"""
        # Check for null bytes or other corruption indicators
        if task.id and '\x00' in task.id:
            result.add_error("Task ID contains null bytes", field="id", code="DATA_CORRUPTION")
        
        # Check settings for corruption
        if task.settings:
            try:
                json.dumps(task.settings)
            except (TypeError, ValueError) as e:
                result.add_error(f"Settings data corruption detected: {str(e)}", field="settings", code="SETTINGS_CORRUPTION")
        
        # Check for extremely long strings that might indicate corruption
        if task.error_message and len(task.error_message) > self.max_error_message_length:
            result.add_warning(
                f"Error message unusually long ({len(task.error_message)} chars)",
                field="error_message",
                code="LONG_ERROR_MESSAGE"
            )
    
    def _validate_completion_state(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate task completion state"""
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            result.add_error(
                f"Task is not in a completion state: {task.status}",
                field="status",
                code="INVALID_COMPLETION_STATE"
            )
        
        # Check required completion fields
        if not task.completed_at:
            result.add_error("Completed task missing completion timestamp", field="completed_at", code="MISSING_COMPLETION_TIMESTAMP")
        
        if task.status == TaskStatus.FAILED and not task.error_message:
            result.add_warning("Failed task missing error message", field="error_message", code="MISSING_ERROR_MESSAGE")
    
    def _validate_processing_result(self, processing_result: Dict[str, Any], result: ValidationResult) -> None:
        """Validate processing result data"""
        required_fields = ['success', 'processing_time']
        
        for field in required_fields:
            if field not in processing_result:
                result.add_warning(f"Processing result missing field: {field}", field="processing_result", code="MISSING_RESULT_FIELD")
        
        # Validate specific fields
        if 'success' in processing_result and not isinstance(processing_result['success'], bool):
            result.add_error("Processing result 'success' must be boolean", field="processing_result.success", code="INVALID_SUCCESS_TYPE")
        
        if 'processing_time' in processing_result:
            processing_time = processing_result['processing_time']
            if not isinstance(processing_time, (int, float)) or processing_time < 0:
                result.add_error("Processing time must be a non-negative number", field="processing_result.processing_time", code="INVALID_PROCESSING_TIME")
    
    def _validate_completion_timestamps(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Validate completion timestamps"""
        if task.created_at and task.completed_at and task.created_at > task.completed_at:
            result.add_error("Creation timestamp after completion timestamp", field="timestamps", code="INVALID_COMPLETION_TIMESTAMPS")
        
        if task.started_at and task.completed_at and task.started_at > task.completed_at:
            result.add_error("Start timestamp after completion timestamp", field="timestamps", code="INVALID_COMPLETION_TIMESTAMPS")
        
        # Check for reasonable processing time
        if task.started_at and task.completed_at:
            processing_time = task.completed_at - task.started_at
            
            if processing_time.total_seconds() < 1:
                result.add_warning("Very short processing time", field="processing_time", code="SHORT_PROCESSING_TIME")
            elif processing_time.total_seconds() > 7200:  # 2 hours
                result.add_warning("Very long processing time", field="processing_time", code="LONG_PROCESSING_TIME")
    
    def _validate_final_integrity(self, task: CaptionGenerationTask, result: ValidationResult) -> None:
        """Final data integrity validation"""
        # This is similar to processing integrity check but for completion
        self._validate_data_integrity(task, result)
        
        # Additional completion-specific checks
        if task.status == TaskStatus.COMPLETED:
            result.add_info("Task completed successfully", code="COMPLETION_SUCCESS")
        elif task.status == TaskStatus.FAILED:
            result.add_info("Task failed as expected", code="COMPLETION_FAILED")
        elif task.status == TaskStatus.CANCELLED:
            result.add_info("Task cancelled", code="COMPLETION_CANCELLED")
    
    def _store_validation_result(self, task_id: str, validation_result: ValidationResult) -> None:
        """Store validation result in Redis"""
        try:
            validation_data = validation_result.to_dict()
            validation_key = f"{self.validation_cache_key}:{task_id}"
            
            self.redis_connection.setex(
                validation_key,
                3600,  # 1 hour TTL
                json.dumps(validation_data, default=str)
            )
            
        except Exception as e:
            logger.warning(f"Failed to store validation result: {sanitize_for_log(str(e))}")
    
    def _store_integrity_hash(self, task_id: str, integrity_hash: str) -> None:
        """Store integrity hash in Redis"""
        try:
            hash_key = f"{self.integrity_hash_key}:{task_id}"
            
            self.redis_connection.setex(
                hash_key,
                7200,  # 2 hours TTL
                integrity_hash
            )
            
        except Exception as e:
            logger.warning(f"Failed to store integrity hash: {sanitize_for_log(str(e))}")
    
    def _get_integrity_hash(self, task_id: str) -> Optional[str]:
        """Get stored integrity hash from Redis"""
        try:
            hash_key = f"{self.integrity_hash_key}:{task_id}"
            hash_value = self.redis_connection.get(hash_key)
            
            return hash_value.decode('utf-8') if hash_value else None
            
        except Exception as e:
            logger.warning(f"Failed to get integrity hash: {sanitize_for_log(str(e))}")
            return None
    
    def get_validation_result(self, task_id: str) -> Optional[ValidationResult]:
        """Get stored validation result"""
        try:
            validation_key = f"{self.validation_cache_key}:{task_id}"
            validation_data_json = self.redis_connection.get(validation_key)
            
            if validation_data_json:
                validation_data = json.loads(validation_data_json)
                
                # Reconstruct ValidationResult object
                result = ValidationResult()
                result.is_valid = validation_data.get('is_valid', False)
                result.errors = validation_data.get('errors', [])
                result.warnings = validation_data.get('warnings', [])
                result.info = validation_data.get('info', [])
                result.data_integrity_hash = validation_data.get('data_integrity_hash')
                
                if validation_data.get('validation_timestamp'):
                    result.validation_timestamp = datetime.fromisoformat(
                        validation_data['validation_timestamp'].replace('Z', '+00:00')
                    )
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get validation result: {sanitize_for_log(str(e))}")
            return None
    
    def validate_corrupted_task_recovery(self, task_id: str, 
                                       recovery_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate recovery procedures for corrupted task data
        
        Args:
            task_id: The task ID being recovered
            recovery_data: Recovery data to validate
            
        Returns:
            ValidationResult for recovery validation
        """
        result = ValidationResult()
        
        try:
            # Validate recovery data structure
            required_recovery_fields = ['recovery_method', 'original_data', 'recovered_data']
            
            for field in required_recovery_fields:
                if field not in recovery_data:
                    result.add_error(f"Missing recovery field: {field}", field=field, code="MISSING_RECOVERY_FIELD")
            
            # Validate recovery method
            valid_methods = ['restore_from_backup', 'reconstruct_from_logs', 'manual_recovery']
            recovery_method = recovery_data.get('recovery_method')
            
            if recovery_method not in valid_methods:
                result.add_error(f"Invalid recovery method: {recovery_method}", field="recovery_method", code="INVALID_RECOVERY_METHOD")
            
            # Validate recovered data integrity
            if 'recovered_data' in recovery_data:
                recovered_task_data = recovery_data['recovered_data']
                
                # Basic structure validation
                if not isinstance(recovered_task_data, dict):
                    result.add_error("Recovered data must be a dictionary", field="recovered_data", code="INVALID_RECOVERED_DATA_TYPE")
                else:
                    # Validate required fields in recovered data
                    required_task_fields = ['id', 'user_id', 'platform_connection_id']
                    
                    for field in required_task_fields:
                        if field not in recovered_task_data:
                            result.add_error(f"Recovered data missing field: {field}", field=f"recovered_data.{field}", code="MISSING_RECOVERED_FIELD")
            
            # Log recovery validation
            logger.info(f"Recovery validation completed for task {sanitize_for_log(task_id)}: valid={result.is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Recovery validation failed: {sanitize_for_log(str(e))}")
            result.add_error(f"Recovery validation failed: {str(e)}", code="RECOVERY_VALIDATION_ERROR")
            return result
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        try:
            # Get validation cache keys
            validation_keys = self.redis_connection.keys(f"{self.validation_cache_key}:*")
            
            stats = {
                'total_validations': len(validation_keys),
                'validation_results': {
                    'valid': 0,
                    'invalid': 0,
                    'with_warnings': 0,
                    'with_errors': 0
                },
                'common_errors': {},
                'common_warnings': {}
            }
            
            # Analyze validation results
            for key in validation_keys[:100]:  # Limit to avoid performance issues
                try:
                    validation_data_json = self.redis_connection.get(key)
                    if validation_data_json:
                        validation_data = json.loads(validation_data_json)
                        
                        if validation_data.get('is_valid', False):
                            stats['validation_results']['valid'] += 1
                        else:
                            stats['validation_results']['invalid'] += 1
                        
                        if validation_data.get('warnings'):
                            stats['validation_results']['with_warnings'] += 1
                        
                        if validation_data.get('errors'):
                            stats['validation_results']['with_errors'] += 1
                        
                        # Count error types
                        for error in validation_data.get('errors', []):
                            error_code = error.get('code', 'unknown')
                            stats['common_errors'][error_code] = stats['common_errors'].get(error_code, 0) + 1
                        
                        # Count warning types
                        for warning in validation_data.get('warnings', []):
                            warning_code = warning.get('code', 'unknown')
                            stats['common_warnings'][warning_code] = stats['common_warnings'].get(warning_code, 0) + 1
                            
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get validation statistics: {sanitize_for_log(str(e))}")
            return {'error': 'Failed to retrieve validation statistics'}
    
    def cleanup_validation_data(self, older_than_hours: int = 24) -> int:
        """
        Clean up old validation data
        
        Args:
            older_than_hours: Remove validation data older than this many hours
            
        Returns:
            Number of items cleaned up
        """
        try:
            cleaned_count = 0
            
            # Clean validation cache
            validation_keys = self.redis_connection.keys(f"{self.validation_cache_key}:*")
            
            for key in validation_keys:
                try:
                    ttl = self.redis_connection.ttl(key)
                    if ttl < 0:  # No TTL or expired
                        self.redis_connection.delete(key)
                        cleaned_count += 1
                except Exception:
                    pass
            
            # Clean integrity hashes
            hash_keys = self.redis_connection.keys(f"{self.integrity_hash_key}:*")
            
            for key in hash_keys:
                try:
                    ttl = self.redis_connection.ttl(key)
                    if ttl < 0:  # No TTL or expired
                        self.redis_connection.delete(key)
                        cleaned_count += 1
                except Exception:
                    pass
            
            logger.info(f"Cleaned up {cleaned_count} validation data items")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup validation data: {sanitize_for_log(str(e))}")
            return 0