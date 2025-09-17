# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Task Serializer for Redis Storage

Handles efficient serialization and deserialization of task data for Redis storage
with validation and backward compatibility support.
"""

import json
import pickle
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import msgpack

from models import CaptionGenerationTask, TaskStatus, JobPriority
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


@dataclass
class RQTaskData:
    """Serializable task data structure for RQ"""
    task_id: str
    user_id: int
    platform_connection_id: int
    priority: str  # JobPriority value
    settings: Dict[str, Any]
    created_at: str  # ISO format datetime
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RQTaskData':
        """Create from dictionary loaded from storage"""
        return cls(**data)
    
    @classmethod
    def from_caption_task(cls, task: CaptionGenerationTask) -> 'RQTaskData':
        """Create from CaptionGenerationTask model"""
        settings = {}
        if task.settings:
            try:
                settings = task.settings.to_dict()
            except Exception as e:
                logger.warning(f"Failed to serialize task settings: {sanitize_for_log(str(e))}")
                settings = {}
        
        return cls(
            task_id=task.id,
            user_id=task.user_id,
            platform_connection_id=task.platform_connection_id,
            priority=task.priority.value if task.priority else JobPriority.NORMAL.value,
            settings=settings,
            created_at=task.created_at.isoformat() if task.created_at else datetime.now(timezone.utc).isoformat(),
            retry_count=task.retry_count or 0,
            max_retries=task.max_retries or 3
        )


class TaskSerializer:
    """Handles serialization/deserialization of task data for Redis storage"""
    
    def __init__(self, use_msgpack: bool = True):
        """
        Initialize TaskSerializer
        
        Args:
            use_msgpack: Whether to use msgpack for serialization (more efficient than JSON)
        """
        self.use_msgpack = use_msgpack
        self._serialization_version = "1.0"
    
    def serialize_task(self, task: CaptionGenerationTask) -> bytes:
        """
        Serialize CaptionGenerationTask for Redis storage
        
        Args:
            task: CaptionGenerationTask to serialize
            
        Returns:
            bytes: Serialized task data
            
        Raises:
            ValueError: If task data is invalid
            RuntimeError: If serialization fails
        """
        try:
            # Validate task data
            if not self.validate_task_data(task):
                raise ValueError(f"Invalid task data for task {task.id}")
            
            # Convert to RQTaskData
            rq_task_data = RQTaskData.from_caption_task(task)
            
            # Create serialization envelope
            envelope = {
                'version': self._serialization_version,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': rq_task_data.to_dict()
            }
            
            # Serialize using chosen method
            if self.use_msgpack:
                serialized = msgpack.packb(envelope, use_bin_type=True)
            else:
                serialized = json.dumps(envelope, ensure_ascii=False).encode('utf-8')
            
            logger.debug(f"Serialized task {sanitize_for_log(task.id)} ({len(serialized)} bytes)")
            return serialized
            
        except Exception as e:
            logger.error(f"Failed to serialize task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
            raise RuntimeError(f"Task serialization failed: {e}")
    
    def deserialize_task(self, data: bytes) -> RQTaskData:
        """
        Deserialize task data from Redis storage
        
        Args:
            data: Serialized task data
            
        Returns:
            RQTaskData: Deserialized task data
            
        Raises:
            ValueError: If data is invalid or corrupted
            RuntimeError: If deserialization fails
        """
        try:
            # Deserialize using appropriate method
            if self.use_msgpack:
                envelope = msgpack.unpackb(data, raw=False, strict_map_key=False)
            else:
                envelope = json.loads(data.decode('utf-8'))
            
            # Validate envelope structure
            if not isinstance(envelope, dict):
                raise ValueError("Invalid envelope structure")
            
            if 'data' not in envelope:
                raise ValueError("Missing data in envelope")
            
            # Check version compatibility
            version = envelope.get('version', '1.0')
            if not self._is_version_compatible(version):
                logger.warning(f"Potentially incompatible serialization version: {version}")
            
            # Extract and validate task data
            task_data_dict = envelope['data']
            if not self._validate_task_data_dict(task_data_dict):
                raise ValueError("Invalid task data structure")
            
            # Create RQTaskData object
            rq_task_data = RQTaskData.from_dict(task_data_dict)
            
            logger.debug(f"Deserialized task {sanitize_for_log(rq_task_data.task_id)}")
            return rq_task_data
            
        except Exception as e:
            logger.error(f"Failed to deserialize task data: {sanitize_for_log(str(e))}")
            raise RuntimeError(f"Task deserialization failed: {e}")
    
    def validate_task_data(self, task: CaptionGenerationTask) -> bool:
        """
        Validate CaptionGenerationTask data before serialization
        
        Args:
            task: Task to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check required fields
            if not task.id:
                logger.error("Task missing ID")
                return False
            
            if not task.user_id:
                logger.error(f"Task {sanitize_for_log(task.id)} missing user_id")
                return False
            
            if not task.platform_connection_id:
                logger.error(f"Task {sanitize_for_log(task.id)} missing platform_connection_id")
                return False
            
            # Validate ID format (should be UUID)
            try:
                import uuid
                uuid.UUID(task.id)
            except ValueError:
                logger.error(f"Task {sanitize_for_log(task.id)} has invalid ID format")
                return False
            
            # Validate user_id is positive integer
            if not isinstance(task.user_id, int) or task.user_id <= 0:
                logger.error(f"Task {sanitize_for_log(task.id)} has invalid user_id: {task.user_id}")
                return False
            
            # Validate platform_connection_id is positive integer
            if not isinstance(task.platform_connection_id, int) or task.platform_connection_id <= 0:
                logger.error(f"Task {sanitize_for_log(task.id)} has invalid platform_connection_id: {task.platform_connection_id}")
                return False
            
            # Validate priority
            if task.priority and task.priority not in JobPriority:
                logger.error(f"Task {sanitize_for_log(task.id)} has invalid priority: {task.priority}")
                return False
            
            # Validate retry counts
            if task.retry_count is not None and (not isinstance(task.retry_count, int) or task.retry_count < 0):
                logger.error(f"Task {sanitize_for_log(task.id)} has invalid retry_count: {task.retry_count}")
                return False
            
            if task.max_retries is not None and (not isinstance(task.max_retries, int) or task.max_retries < 0):
                logger.error(f"Task {sanitize_for_log(task.id)} has invalid max_retries: {task.max_retries}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating task data: {sanitize_for_log(str(e))}")
            return False
    
    def _validate_task_data_dict(self, data: Dict[str, Any]) -> bool:
        """Validate deserialized task data dictionary"""
        try:
            required_fields = ['task_id', 'user_id', 'platform_connection_id', 'priority', 'settings', 'created_at']
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field in task data: {field}")
                    return False
            
            # Validate field types
            if not isinstance(data['task_id'], str) or not data['task_id']:
                logger.error("Invalid task_id in deserialized data")
                return False
            
            if not isinstance(data['user_id'], int) or data['user_id'] <= 0:
                logger.error("Invalid user_id in deserialized data")
                return False
            
            if not isinstance(data['platform_connection_id'], int) or data['platform_connection_id'] <= 0:
                logger.error("Invalid platform_connection_id in deserialized data")
                return False
            
            if not isinstance(data['priority'], str):
                logger.error("Invalid priority in deserialized data")
                return False
            
            if not isinstance(data['settings'], dict):
                logger.error("Invalid settings in deserialized data")
                return False
            
            # Validate datetime format
            try:
                datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.error("Invalid created_at format in deserialized data")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating task data dictionary: {sanitize_for_log(str(e))}")
            return False
    
    def _is_version_compatible(self, version: str) -> bool:
        """Check if serialization version is compatible"""
        try:
            # For now, we only support version 1.0
            # In the future, this can be expanded for backward compatibility
            return version == "1.0"
        except Exception:
            return False
    
    def serialize_task_for_database_compatibility(self, rq_task_data: RQTaskData) -> CaptionGenerationTask:
        """
        Convert RQTaskData back to CaptionGenerationTask for database operations
        
        Args:
            rq_task_data: RQ task data to convert
            
        Returns:
            CaptionGenerationTask: Database model instance
        """
        try:
            # Create CaptionGenerationTask instance
            task = CaptionGenerationTask()
            task.id = rq_task_data.task_id
            task.user_id = rq_task_data.user_id
            task.platform_connection_id = rq_task_data.platform_connection_id
            
            # Convert priority string back to enum
            try:
                task.priority = JobPriority(rq_task_data.priority)
            except ValueError:
                task.priority = JobPriority.NORMAL
                logger.warning(f"Invalid priority {rq_task_data.priority}, defaulting to NORMAL")
            
            # Convert datetime string back to datetime
            try:
                task.created_at = datetime.fromisoformat(rq_task_data.created_at.replace('Z', '+00:00'))
            except ValueError:
                task.created_at = datetime.now(timezone.utc)
                logger.warning(f"Invalid created_at format, using current time")
            
            # Set retry information
            task.retry_count = rq_task_data.retry_count
            task.max_retries = rq_task_data.max_retries
            
            # Convert settings back to CaptionGenerationSettings
            if rq_task_data.settings:
                try:
                    from models import CaptionGenerationSettings
                    task.settings = CaptionGenerationSettings.from_dict(rq_task_data.settings)
                except Exception as e:
                    logger.warning(f"Failed to deserialize settings for task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
                    task.settings = None
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to convert RQTaskData to CaptionGenerationTask: {sanitize_for_log(str(e))}")
            raise RuntimeError(f"Task conversion failed: {e}")
    
    def get_serialization_stats(self) -> Dict[str, Any]:
        """Get serialization statistics and configuration"""
        return {
            'use_msgpack': self.use_msgpack,
            'version': self._serialization_version,
            'supported_versions': ['1.0'],
            'serialization_method': 'msgpack' if self.use_msgpack else 'json'
        }
    
    def test_serialization_roundtrip(self, task: CaptionGenerationTask) -> bool:
        """
        Test serialization/deserialization roundtrip for a task
        
        Args:
            task: Task to test
            
        Returns:
            bool: True if roundtrip successful, False otherwise
        """
        try:
            # Serialize
            serialized = self.serialize_task(task)
            
            # Deserialize
            deserialized = self.deserialize_task(serialized)
            
            # Convert back to CaptionGenerationTask
            reconstructed = self.serialize_task_for_database_compatibility(deserialized)
            
            # Compare key fields
            if (task.id == reconstructed.id and
                task.user_id == reconstructed.user_id and
                task.platform_connection_id == reconstructed.platform_connection_id and
                task.priority == reconstructed.priority):
                return True
            else:
                logger.error("Serialization roundtrip failed - data mismatch")
                return False
                
        except Exception as e:
            logger.error(f"Serialization roundtrip test failed: {sanitize_for_log(str(e))}")
            return False