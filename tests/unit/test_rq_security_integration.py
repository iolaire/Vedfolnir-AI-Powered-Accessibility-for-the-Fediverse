# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for RQ Security Integration

Tests the integration of security mechanisms with RQ task processing,
including encryption, access control, and error sanitization.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import re
from datetime import datetime, timezone
import redis

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_security_manager import RQSecurityManager
from app.services.task.rq.rq_data_retention_manager import RQDataRetentionManager
from app.services.task.rq.retention_policy import RetentionPolicy
from app.services.task.rq.rq_job_processor import RQJobProcessor
from models import CaptionGenerationTask, TaskStatus, UserRole, User


class TestRQSecurityIntegration(unittest.TestCase):
    """Test RQ security integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock database manager
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        
        # Mock caption security manager
        self.mock_caption_security = Mock(spec=CaptionSecurityManager)
        self.mock_caption_security.generate_secure_task_id.return_value = "test-task-123"
        self.mock_caption_security.validate_task_id.return_value = True
        self.mock_caption_security.check_task_ownership.return_value = True
        
        # Set up environment for encryption (generate a proper Fernet key)
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key().decode()
        os.environ['PLATFORM_ENCRYPTION_KEY'] = test_key
        
        # Initialize RQ security manager
        self.rq_security_manager = RQSecurityManager(
            self.mock_db_manager,
            self.mock_redis,
            self.mock_caption_security
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        if 'PLATFORM_ENCRYPTION_KEY' in os.environ:
            del os.environ['PLATFORM_ENCRYPTION_KEY']
    
    def test_secure_task_id_generation(self):
        """Test secure task ID generation integration"""
        # Test that RQ security manager uses caption security manager
        task_id = self.rq_security_manager.generate_secure_task_id()
        
        self.assertEqual(task_id, "test-task-123")
        self.mock_caption_security.generate_secure_task_id.assert_called_once()
    
    def test_task_id_validation(self):
        """Test task ID validation integration"""
        # Test valid task ID
        result = self.rq_security_manager.validate_task_id("test-task-123")
        
        self.assertTrue(result)
        self.mock_caption_security.validate_task_id.assert_called_once_with("test-task-123")
    
    def test_task_data_encryption(self):
        """Test task data encryption for Redis storage"""
        # Test data with sensitive fields
        task_data = {
            'task_id': 'test-123',
            'user_id': 1,
            'access_token': 'sensitive_token',
            'normal_field': 'normal_value'
        }
        
        # Test encryption (uses real Fernet with test key)
        encrypted_data = self.rq_security_manager.encrypt_task_data(task_data)
        
        self.assertIsInstance(encrypted_data, bytes)
        self.assertGreater(len(encrypted_data), 0)
        
        # Test decryption
        decrypted_data = self.rq_security_manager.decrypt_task_data(encrypted_data)
        
        self.assertIsInstance(decrypted_data, dict)
        self.assertEqual(decrypted_data['task_id'], 'test-123')
        self.assertEqual(decrypted_data['user_id'], 1)
        self.assertEqual(decrypted_data['access_token'], 'sensitive_token')
        self.assertEqual(decrypted_data['normal_field'], 'normal_value')
    
    def test_worker_authentication(self):
        """Test RQ worker authentication"""
        worker_id = "worker-123"
        worker_token = "secure-token"
        
        # Mock Redis operations
        self.mock_redis.get.return_value = None  # No existing token
        self.mock_redis.setex.return_value = True
        self.mock_redis.hset.return_value = True
        self.mock_redis.expire.return_value = True
        
        # Register worker authentication
        self.rq_security_manager.register_worker_authentication(worker_id, worker_token)
        
        # Verify Redis calls
        self.mock_redis.setex.assert_called()
        self.mock_redis.hset.assert_called()
        
        # Test authentication validation
        import hashlib
        token_hash = hashlib.sha256(worker_token.encode()).hexdigest()
        self.mock_redis.get.return_value = token_hash.encode()
        
        result = self.rq_security_manager.validate_worker_authentication(worker_id, worker_token)
        self.assertTrue(result)
    
    def test_task_access_validation(self):
        """Test task access validation"""
        task_id = "test-task-123"
        user_id = 1
        
        # Mock Redis operations for RQ-specific validation
        self.mock_redis.hgetall.return_value = {
            b'user_id': b'1',
            b'created_at': datetime.now(timezone.utc).isoformat().encode()
        }
        
        # Test access validation
        result = self.rq_security_manager.validate_task_access(task_id, user_id)
        
        self.assertTrue(result)
        self.mock_caption_security.check_task_ownership.assert_called_once_with(task_id, user_id)
    
    def test_user_permissions_validation(self):
        """Test user permissions validation"""
        user_id = 1
        required_permissions = ['rq:task:create', 'rq:task:view']
        
        # Mock user with admin role
        mock_user = Mock()
        mock_user.role = UserRole.ADMIN
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        # Test permission validation
        result = self.rq_security_manager.validate_user_permissions(user_id, required_permissions)
        
        self.assertTrue(result)
    
    def test_error_message_sanitization(self):
        """Test error message sanitization to prevent information leakage"""
        # Test error with sensitive information
        error_message = "Database error: password=secret123 token=abc123 at /path/to/file"
        task_id = "test-task-123"
        
        sanitized = self.rq_security_manager.sanitize_error_message(error_message, task_id)
        
        # Verify sensitive data is redacted
        self.assertNotIn("secret123", sanitized)
        self.assertNotIn("abc123", sanitized)
        self.assertIn("[REDACTED]", sanitized)
        self.assertIn("[PATH]", sanitized)
    
    def test_security_event_logging(self):
        """Test security event logging"""
        event_type = "task_access_attempt"
        details = {
            'task_id': 'test-123',
            'user_id': 1,
            'access_token': 'sensitive_token'
        }
        
        # Mock Redis operations
        self.mock_redis.lpush.return_value = 1
        self.mock_redis.expire.return_value = True
        
        # Test security event logging
        self.rq_security_manager.log_security_event(event_type, details, user_id=1)
        
        # Verify Redis logging
        self.mock_redis.lpush.assert_called()
        self.mock_redis.expire.assert_called()
    
    def test_security_metrics_collection(self):
        """Test security metrics collection"""
        # Mock Redis scan operations
        self.mock_redis.scan_iter.side_effect = [
            [b'rq:security:worker_auth:worker1', b'rq:security:worker_auth:worker2'],  # Workers
            [b'rq:security:task_auth:task1'],  # Task auths
        ]
        self.mock_redis.llen.return_value = 5  # Security events
        
        # Get security metrics
        metrics = self.rq_security_manager.get_security_metrics()
        
        # Verify metrics structure
        self.assertIn('timestamp', metrics)
        self.assertIn('active_workers', metrics)
        self.assertIn('active_task_auths', metrics)
        self.assertIn('security_events_today', metrics)
        self.assertEqual(metrics['encryption_status'], 'active')


class TestRQDataRetentionManager(unittest.TestCase):
    """Test RQ data retention manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_config = Mock()
        self.mock_queues = {}
        
        # Initialize data retention manager
        self.retention_manager = RQDataRetentionManager(
            self.mock_db_manager,
            self.mock_redis,
            self.mock_config,
            self.mock_queues
        )
    
    def test_retention_policy_initialization(self):
        """Test retention policy initialization"""
        # Verify default policies are created
        self.assertIn('default', self.retention_manager.retention_policies)
        self.assertIn('development', self.retention_manager.retention_policies)
        self.assertIn('high_volume', self.retention_manager.retention_policies)
        self.assertIn('conservative', self.retention_manager.retention_policies)
        
        # Verify active policy is set
        self.assertEqual(self.retention_manager.active_policy.name, 'default')
    
    def test_retention_policy_switching(self):
        """Test switching retention policies"""
        # Switch to development policy
        result = self.retention_manager.set_retention_policy('development')
        
        self.assertTrue(result)
        self.assertEqual(self.retention_manager.active_policy.name, 'development')
        
        # Test invalid policy
        result = self.retention_manager.set_retention_policy('invalid_policy')
        self.assertFalse(result)
    
    def test_task_ttl_setting(self):
        """Test setting TTL for tasks based on status"""
        task_id = "test-task-123"
        
        # Mock Redis scan operations
        self.mock_redis.scan_iter.return_value = [
            b'rq:task:test-task-123',
            b'rq:progress:test-task-123'
        ]
        self.mock_redis.expire.return_value = True
        
        # Set TTL for completed task
        self.retention_manager.set_task_ttl(task_id, TaskStatus.COMPLETED)
        
        # Verify Redis expire calls
        self.mock_redis.expire.assert_called()
    
    def test_memory_usage_monitoring(self):
        """Test Redis memory usage monitoring"""
        # Mock Redis info response
        self.mock_redis.info.return_value = {
            'used_memory': 1024 * 1024 * 100  # 100 MB
        }
        
        # Check memory usage
        status = self.retention_manager.check_memory_usage()
        
        # Verify status structure
        self.assertIn('current_usage_mb', status)
        self.assertIn('usage_percentage', status)
        self.assertEqual(status['current_usage_mb'], 100.0)
    
    def test_cleanup_expired_data(self):
        """Test cleanup of expired data"""
        # Mock Redis operations
        self.mock_redis.scan_iter.return_value = [
            b'rq:task:old-task',
            b'rq:progress:old-progress'
        ]
        self.mock_redis.ttl.return_value = 0  # Expired
        self.mock_redis.delete.return_value = 1
        self.mock_redis.info.return_value = {'used_memory': 1024 * 1024 * 50}  # 50 MB
        
        # Perform cleanup
        results = self.retention_manager.cleanup_expired_data()
        
        # Verify cleanup results
        self.assertIn('items_cleaned', results)
        self.assertIn('memory_freed_mb', results)
        self.assertIn('categories', results)
    
    def test_retention_status_reporting(self):
        """Test comprehensive retention status reporting"""
        # Mock Redis operations
        self.mock_redis.info.return_value = {'used_memory': 1024 * 1024 * 75}  # 75 MB
        self.mock_redis.scan_iter.return_value = [b'test-key-1', b'test-key-2']
        
        # Get retention status
        status = self.retention_manager.get_retention_status()
        
        # Verify status structure
        self.assertIn('timestamp', status)
        self.assertIn('active_policy', status)
        self.assertIn('memory_usage', status)
        self.assertIn('monitoring', status)
        self.assertIn('cleanup_statistics', status)
        self.assertIn('data_counts', status)


class TestRQJobProcessorSecurity(unittest.TestCase):
    """Test RQ job processor security integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_security_manager = Mock(spec=RQSecurityManager)
        
        # Initialize job processor
        self.job_processor = RQJobProcessor(
            self.mock_db_manager,
            self.mock_redis,
            self.mock_security_manager
        )
    
    def test_task_processing_with_security_validation(self):
        """Test task processing with security validation"""
        task_id = "test-task-123"
        
        # Mock security validations
        self.mock_security_manager.validate_task_id.return_value = True
        self.mock_security_manager.validate_task_access.return_value = True
        
        # Mock task and platform connection
        mock_task = Mock()
        mock_task.id = task_id
        mock_task.user_id = 1
        mock_task.platform_connection_id = 1
        mock_task.settings = {}
        
        mock_platform = Mock()
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_task,  # First call for task
            mock_platform  # Second call for platform connection
        ]
        
        # Mock caption generation (this would normally be complex)
        with patch.object(self.job_processor, '_execute_caption_generation') as mock_execute:
            mock_execute.return_value = {
                'captions_generated': 5,
                'images_processed': 10,
                'processing_time': 30.5,
                'success_rate': 0.95
            }
            
            # Process task
            result = self.job_processor.process_task(task_id)
            
            # Verify security validations were called
            self.mock_security_manager.validate_task_id.assert_called_once_with(task_id)
            self.mock_security_manager.validate_task_access.assert_called_once_with(task_id, 1)
            
            # Verify security events were logged
            self.assertEqual(self.mock_security_manager.log_security_event.call_count, 2)  # Start and complete
            
            # Verify result
            self.assertTrue(result['success'])
            self.assertEqual(result['task_id'], task_id)
    
    def test_task_processing_security_failure(self):
        """Test task processing with security validation failure"""
        task_id = "invalid-task"
        
        # Mock security validation failure
        self.mock_security_manager.validate_task_id.return_value = False
        
        # Test that processing fails with security error
        with self.assertRaises(Exception) as context:
            self.job_processor.process_task(task_id)
        
        self.assertIn("Invalid task ID format", str(context.exception))
    
    def test_error_sanitization_in_processing(self):
        """Test error message sanitization during task processing"""
        task_id = "test-task-123"
        
        # Mock security validations to pass
        self.mock_security_manager.validate_task_id.return_value = True
        self.mock_security_manager.validate_task_access.return_value = True
        self.mock_security_manager.sanitize_error_message.return_value = "Sanitized error message"
        
        # Mock task retrieval to fail
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Test that error is sanitized
        with self.assertRaises(Exception) as context:
            self.job_processor.process_task(task_id)
        
        # Verify error sanitization was called
        self.mock_security_manager.sanitize_error_message.assert_called()
        
        # Verify security event was logged for failure
        security_calls = self.mock_security_manager.log_security_event.call_args_list
        failure_calls = [call for call in security_calls if 'failed' in call[0][0]]
        self.assertTrue(len(failure_calls) > 0)


if __name__ == '__main__':
    unittest.main()