# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Task Serializer

Tests the task serialization and deserialization functionality for Redis storage
including validation, backward compatibility, and error handling.
"""

import unittest
from unittest.mock import Mock, patch
import json
import pickle
import msgpack
from datetime import datetime, timezone
from dataclasses import asdict

from app.services.task.rq.task_serializer import TaskSerializer, RQTaskData
from models import CaptionGenerationTask, TaskStatus, JobPriority
from app.services.caption.caption_generation_settings import CaptionGenerationSettings


class TestRQTaskData(unittest.TestCase):
    """Test RQTaskData dataclass functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_data = {
            'task_id': 'test-task-123',
            'user_id': 1,
            'platform_connection_id': 1,
            'priority': 'normal',
            'settings': {'max_length': 500, 'style': 'descriptive'},
            'created_at': '2025-01-15T10:30:00+00:00',
            'retry_count': 0,
            'max_retries': 3
        }
    
    def test_rq_task_data_creation(self):
        """Test RQTaskData creation from dictionary"""
        task_data = RQTaskData.from_dict(self.test_data)
        
        self.assertEqual(task_data.task_id, 'test-task-123')
        self.assertEqual(task_data.user_id, 1)
        self.assertEqual(task_data.platform_connection_id, 1)
        self.assertEqual(task_data.priority, 'normal')
        self.assertEqual(task_data.settings, {'max_length': 500, 'style': 'descriptive'})
        self.assertEqual(task_data.retry_count, 0)
        self.assertEqual(task_data.max_retries, 3)
    
    def test_rq_task_data_to_dict(self):
        """Test RQTaskData conversion to dictionary"""
        task_data = RQTaskData(**self.test_data)
        result_dict = task_data.to_dict()
        
        self.assertEqual(result_dict, self.test_data)
    
    def test_from_caption_task(self):
        """Test creating RQTaskData from CaptionGenerationTask"""
        # Mock CaptionGenerationSettings
        mock_settings = Mock(spec=CaptionGenerationSettings)
        mock_settings.to_dict.return_value = {'max_length': 500, 'style': 'descriptive'}
        
        # Create test task
        task = CaptionGenerationTask(
            id='test-task-456',
            user_id=2,
            platform_connection_id=3,
            priority=JobPriority.HIGH,
            settings=mock_settings,
            created_at=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            retry_count=1,
            max_retries=5
        )
        
        # Convert to RQTaskData
        rq_task_data = RQTaskData.from_caption_task(task)
        
        # Verify conversion
        self.assertEqual(rq_task_data.task_id, 'test-task-456')
        self.assertEqual(rq_task_data.user_id, 2)
        self.assertEqual(rq_task_data.platform_connection_id, 3)
        self.assertEqual(rq_task_data.priority, 'high')
        self.assertEqual(rq_task_data.settings, {'max_length': 500, 'style': 'descriptive'})
        self.assertEqual(rq_task_data.created_at, '2025-01-15T10:30:00+00:00')
        self.assertEqual(rq_task_data.retry_count, 1)
        self.assertEqual(rq_task_data.max_retries, 5)
    
    def test_from_caption_task_with_none_values(self):
        """Test creating RQTaskData from CaptionGenerationTask with None values"""
        # Create task with minimal data
        task = CaptionGenerationTask(
            id='test-task-789',
            user_id=3,
            platform_connection_id=4
        )
        
        # Convert to RQTaskData
        rq_task_data = RQTaskData.from_caption_task(task)
        
        # Verify defaults are applied
        self.assertEqual(rq_task_data.task_id, 'test-task-789')
        self.assertEqual(rq_task_data.user_id, 3)
        self.assertEqual(rq_task_data.platform_connection_id, 4)
        self.assertEqual(rq_task_data.priority, 'normal')  # Default priority
        self.assertEqual(rq_task_data.settings, {})  # Empty settings
        self.assertEqual(rq_task_data.retry_count, 0)  # Default retry count
        self.assertEqual(rq_task_data.max_retries, 3)  # Default max retries
        self.assertIsNotNone(rq_task_data.created_at)  # Should have timestamp
    
    def test_from_caption_task_settings_serialization_error(self):
        """Test handling of settings serialization errors"""
        # Mock settings that fail to serialize
        mock_settings = Mock(spec=CaptionGenerationSettings)
        mock_settings.to_dict.side_effect = Exception("Serialization failed")
        
        task = CaptionGenerationTask(
            id='test-task-error',
            user_id=1,
            platform_connection_id=1,
            settings=mock_settings
        )
        
        # Convert to RQTaskData (should handle error gracefully)
        rq_task_data = RQTaskData.from_caption_task(task)
        
        # Verify empty settings are used when serialization fails
        self.assertEqual(rq_task_data.settings, {})


class TestTaskSerializer(unittest.TestCase):
    """Test TaskSerializer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.serializer_msgpack = TaskSerializer(use_msgpack=True)
        self.serializer_json = TaskSerializer(use_msgpack=False)
        
        self.test_task_data = RQTaskData(
            task_id='test-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings={'max_length': 500, 'style': 'descriptive'},
            created_at='2025-01-15T10:30:00+00:00',
            retry_count=0,
            max_retries=3
        )
    
    def test_serialize_task_msgpack(self):
        """Test task serialization using msgpack"""
        serialized = self.serializer_msgpack.serialize_task(self.test_task_data)
        
        # Verify it's bytes
        self.assertIsInstance(serialized, bytes)
        
        # Verify it can be deserialized back
        deserialized = self.serializer_msgpack.deserialize_task(serialized)
        self.assertEqual(deserialized.task_id, self.test_task_data.task_id)
        self.assertEqual(deserialized.user_id, self.test_task_data.user_id)
        self.assertEqual(deserialized.settings, self.test_task_data.settings)
    
    def test_serialize_task_json(self):
        """Test task serialization using JSON"""
        serialized = self.serializer_json.serialize_task(self.test_task_data)
        
        # Verify it's bytes
        self.assertIsInstance(serialized, bytes)
        
        # Verify it can be deserialized back
        deserialized = self.serializer_json.deserialize_task(serialized)
        self.assertEqual(deserialized.task_id, self.test_task_data.task_id)
        self.assertEqual(deserialized.user_id, self.test_task_data.user_id)
        self.assertEqual(deserialized.settings, self.test_task_data.settings)
    
    def test_deserialize_task_msgpack(self):
        """Test task deserialization from msgpack"""
        # Serialize first
        serialized = self.serializer_msgpack.serialize_task(self.test_task_data)
        
        # Deserialize
        deserialized = self.serializer_msgpack.deserialize_task(serialized)
        
        # Verify all fields
        self.assertIsInstance(deserialized, RQTaskData)
        self.assertEqual(deserialized.task_id, 'test-task-123')
        self.assertEqual(deserialized.user_id, 1)
        self.assertEqual(deserialized.platform_connection_id, 1)
        self.assertEqual(deserialized.priority, 'normal')
        self.assertEqual(deserialized.settings, {'max_length': 500, 'style': 'descriptive'})
        self.assertEqual(deserialized.retry_count, 0)
        self.assertEqual(deserialized.max_retries, 3)
    
    def test_deserialize_task_json(self):
        """Test task deserialization from JSON"""
        # Serialize first
        serialized = self.serializer_json.serialize_task(self.test_task_data)
        
        # Deserialize
        deserialized = self.serializer_json.deserialize_task(serialized)
        
        # Verify all fields
        self.assertIsInstance(deserialized, RQTaskData)
        self.assertEqual(deserialized.task_id, 'test-task-123')
        self.assertEqual(deserialized.user_id, 1)
        self.assertEqual(deserialized.settings, {'max_length': 500, 'style': 'descriptive'})
    
    def test_validate_task_data_valid(self):
        """Test validation of valid task data"""
        task_dict = self.test_task_data.to_dict()
        
        result = self.serializer_msgpack.validate_task_data(task_dict)
        self.assertTrue(result)
    
    def test_validate_task_data_missing_required_fields(self):
        """Test validation with missing required fields"""
        # Missing task_id
        invalid_data = {
            'user_id': 1,
            'platform_connection_id': 1,
            'priority': 'normal',
            'settings': {},
            'created_at': '2025-01-15T10:30:00+00:00'
        }
        
        result = self.serializer_msgpack.validate_task_data(invalid_data)
        self.assertFalse(result)
    
    def test_validate_task_data_invalid_types(self):
        """Test validation with invalid field types"""
        # Invalid user_id type
        invalid_data = {
            'task_id': 'test-task-123',
            'user_id': 'not-an-integer',  # Should be int
            'platform_connection_id': 1,
            'priority': 'normal',
            'settings': {},
            'created_at': '2025-01-15T10:30:00+00:00'
        }
        
        result = self.serializer_msgpack.validate_task_data(invalid_data)
        self.assertFalse(result)
    
    def test_serialize_caption_generation_task(self):
        """Test serializing CaptionGenerationTask directly"""
        # Mock CaptionGenerationSettings
        mock_settings = Mock(spec=CaptionGenerationSettings)
        mock_settings.to_dict.return_value = {'max_length': 400}
        
        task = CaptionGenerationTask(
            id='direct-task-123',
            user_id=5,
            platform_connection_id=2,
            priority=JobPriority.URGENT,
            settings=mock_settings,
            created_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        # Serialize
        serialized = self.serializer_msgpack.serialize_caption_generation_task(task)
        
        # Verify it's bytes
        self.assertIsInstance(serialized, bytes)
        
        # Deserialize and verify
        deserialized = self.serializer_msgpack.deserialize_task(serialized)
        self.assertEqual(deserialized.task_id, 'direct-task-123')
        self.assertEqual(deserialized.user_id, 5)
        self.assertEqual(deserialized.platform_connection_id, 2)
        self.assertEqual(deserialized.priority, 'urgent')
        self.assertEqual(deserialized.settings, {'max_length': 400})
    
    def test_backward_compatibility_with_database_tasks(self):
        """Test backward compatibility with existing database task format"""
        # Simulate old database task format
        old_task_data = {
            'id': 'old-task-456',
            'user_id': 3,
            'platform_connection_id': 4,
            'status': 'queued',
            'priority': 'high',
            'created_at': '2025-01-15T08:00:00+00:00',
            'settings': {'legacy_field': 'value'}
        }
        
        # Test conversion from old format
        converted = self.serializer_msgpack.convert_from_database_format(old_task_data)
        
        # Verify conversion
        self.assertIsInstance(converted, RQTaskData)
        self.assertEqual(converted.task_id, 'old-task-456')
        self.assertEqual(converted.user_id, 3)
        self.assertEqual(converted.platform_connection_id, 4)
        self.assertEqual(converted.priority, 'high')
        self.assertEqual(converted.settings, {'legacy_field': 'value'})
    
    def test_serialization_error_handling(self):
        """Test error handling during serialization"""
        # Create task data with non-serializable content
        bad_task_data = RQTaskData(
            task_id='bad-task',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings={'function': lambda x: x},  # Non-serializable
            created_at='2025-01-15T10:30:00+00:00'
        )
        
        # Test that serialization handles the error gracefully
        with self.assertRaises(Exception):
            self.serializer_json.serialize_task(bad_task_data)
    
    def test_deserialization_error_handling(self):
        """Test error handling during deserialization"""
        # Test with corrupted data
        corrupted_data = b'corrupted-data-not-valid'
        
        with self.assertRaises(Exception):
            self.serializer_msgpack.deserialize_task(corrupted_data)
    
    def test_large_task_data_serialization(self):
        """Test serialization of large task data"""
        # Create task with large settings
        large_settings = {
            'large_list': list(range(1000)),
            'large_dict': {f'key_{i}': f'value_{i}' for i in range(100)},
            'large_string': 'x' * 10000
        }
        
        large_task_data = RQTaskData(
            task_id='large-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings=large_settings,
            created_at='2025-01-15T10:30:00+00:00'
        )
        
        # Test serialization and deserialization
        serialized = self.serializer_msgpack.serialize_task(large_task_data)
        deserialized = self.serializer_msgpack.deserialize_task(serialized)
        
        # Verify large data is preserved
        self.assertEqual(deserialized.settings['large_list'], large_settings['large_list'])
        self.assertEqual(deserialized.settings['large_dict'], large_settings['large_dict'])
        self.assertEqual(deserialized.settings['large_string'], large_settings['large_string'])
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters in task data"""
        unicode_task_data = RQTaskData(
            task_id='unicode-task-测试',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings={
                'description': 'Test with émojis 🚀 and unicode 中文',
                'special_chars': '©®™€£¥'
            },
            created_at='2025-01-15T10:30:00+00:00'
        )
        
        # Test serialization and deserialization with Unicode
        serialized = self.serializer_msgpack.serialize_task(unicode_task_data)
        deserialized = self.serializer_msgpack.deserialize_task(serialized)
        
        # Verify Unicode is preserved
        self.assertEqual(deserialized.task_id, 'unicode-task-测试')
        self.assertEqual(deserialized.settings['description'], 'Test with émojis 🚀 and unicode 中文')
        self.assertEqual(deserialized.settings['special_chars'], '©®™€£¥')
    
    def test_performance_comparison_msgpack_vs_json(self):
        """Test performance comparison between msgpack and JSON serialization"""
        import time
        
        # Create moderately complex task data
        complex_settings = {
            'nested_dict': {
                'level1': {
                    'level2': {
                        'data': list(range(100))
                    }
                }
            },
            'list_of_dicts': [{'id': i, 'value': f'item_{i}'} for i in range(50)]
        }
        
        complex_task_data = RQTaskData(
            task_id='perf-task-123',
            user_id=1,
            platform_connection_id=1,
            priority='normal',
            settings=complex_settings,
            created_at='2025-01-15T10:30:00+00:00'
        )
        
        # Test msgpack performance
        start_time = time.time()
        for _ in range(100):
            serialized_msgpack = self.serializer_msgpack.serialize_task(complex_task_data)
            self.serializer_msgpack.deserialize_task(serialized_msgpack)
        msgpack_time = time.time() - start_time
        
        # Test JSON performance
        start_time = time.time()
        for _ in range(100):
            serialized_json = self.serializer_json.serialize_task(complex_task_data)
            self.serializer_json.deserialize_task(serialized_json)
        json_time = time.time() - start_time
        
        # Verify both work and msgpack is generally faster (though this may vary)
        self.assertIsInstance(serialized_msgpack, bytes)
        self.assertIsInstance(serialized_json, bytes)
        
        # Log performance results (for informational purposes)
        print(f"Msgpack time: {msgpack_time:.4f}s, JSON time: {json_time:.4f}s")


class TestTaskSerializerIntegration(unittest.TestCase):
    """Integration tests for TaskSerializer with real data scenarios"""
    
    def test_full_task_lifecycle_serialization(self):
        """Test complete task lifecycle through serialization"""
        # Create initial task
        initial_task = CaptionGenerationTask(
            id='lifecycle-task-123',
            user_id=1,
            platform_connection_id=1,
            priority=JobPriority.NORMAL,
            status=TaskStatus.QUEUED,
            created_at=datetime.now(timezone.utc)
        )
        
        serializer = TaskSerializer(use_msgpack=True)
        
        # Serialize initial task
        serialized = serializer.serialize_caption_generation_task(initial_task)
        
        # Deserialize
        deserialized = serializer.deserialize_task(serialized)
        
        # Verify task data is preserved
        self.assertEqual(deserialized.task_id, 'lifecycle-task-123')
        self.assertEqual(deserialized.user_id, 1)
        self.assertEqual(deserialized.platform_connection_id, 1)
        self.assertEqual(deserialized.priority, 'normal')
        
        # Simulate task retry (increment retry count)
        deserialized.retry_count += 1
        
        # Re-serialize with updated data
        updated_serialized = serializer.serialize_task(deserialized)
        final_deserialized = serializer.deserialize_task(updated_serialized)
        
        # Verify retry count was updated
        self.assertEqual(final_deserialized.retry_count, 1)


if __name__ == '__main__':
    unittest.main()