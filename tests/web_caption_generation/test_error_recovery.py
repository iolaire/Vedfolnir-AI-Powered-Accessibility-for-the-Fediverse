# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for error recovery and handling system
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import uuid
from datetime import datetime, timezone

from error_recovery_manager import ErrorRecoveryManager, ErrorCategory, RecoveryStrategy
from models import CaptionGenerationTask, TaskStatus, User, PlatformConnection
from database import DatabaseManager

class TestErrorRecoverySystem(unittest.TestCase):
    """Tests for error recovery and handling system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.recovery_manager = ErrorRecoveryManager()
        
        # Test data
        self.test_task_id = str(uuid.uuid4())
        self.test_user_id = 1
        self.test_platform_id = 1
        
        # Mock task
        self.mock_task = Mock(spec=CaptionGenerationTask)
        self.mock_task.id = self.test_task_id
        self.mock_task.user_id = self.test_user_id
        self.mock_task.platform_connection_id = self.test_platform_id
        self.mock_task.retry_count = 0
        self.mock_task.status = TaskStatus.RUNNING
    
    def test_error_categorization_authentication(self):
        """Test authentication error categorization"""
        auth_errors = [
            "Invalid access token",
            "Authentication failed",
            "Token expired",
            "Unauthorized access"
        ]
        
        for error_msg in auth_errors:
            category = self.recovery_manager.categorize_error(Exception(error_msg))
            self.assertEqual(category, ErrorCategory.AUTHENTICATION)
    
    def test_error_categorization_platform(self):
        """Test platform error categorization"""
        platform_errors = [
            "API rate limit exceeded",
            "Platform temporarily unavailable",
            "Connection timeout",
            "HTTP 503 Service Unavailable"
        ]
        
        for error_msg in platform_errors:
            category = self.recovery_manager.categorize_error(Exception(error_msg))
            self.assertEqual(category, ErrorCategory.PLATFORM)
    
    def test_error_categorization_resource(self):
        """Test resource error categorization"""
        resource_errors = [
            "Out of memory",
            "Disk space full",
            "Database connection failed",
            "File not found"
        ]
        
        for error_msg in resource_errors:
            category = self.recovery_manager.categorize_error(Exception(error_msg))
            self.assertEqual(category, ErrorCategory.RESOURCE)
    
    def test_error_categorization_validation(self):
        """Test validation error categorization"""
        validation_errors = [
            "Invalid input format",
            "Missing required field",
            "Value out of range",
            "Validation failed"
        ]
        
        for error_msg in validation_errors:
            category = self.recovery_manager.categorize_error(Exception(error_msg))
            self.assertEqual(category, ErrorCategory.VALIDATION)
    
    def test_error_categorization_unknown(self):
        """Test unknown error categorization"""
        unknown_error = Exception("Some unexpected error")
        category = self.recovery_manager.categorize_error(unknown_error)
        self.assertEqual(category, ErrorCategory.UNKNOWN)
    
    def test_recovery_strategy_authentication_error(self):
        """Test recovery strategy for authentication errors"""
        error = Exception("Invalid access token")
        strategy = self.recovery_manager.determine_recovery_strategy(
            error, self.mock_task
        )
        
        self.assertEqual(strategy, RecoveryStrategy.FAIL_FAST)
    
    def test_recovery_strategy_platform_error_with_retries(self):
        """Test recovery strategy for platform errors with retries available"""
        error = Exception("API rate limit exceeded")
        self.mock_task.retry_count = 1
        
        strategy = self.recovery_manager.determine_recovery_strategy(
            error, self.mock_task
        )
        
        self.assertEqual(strategy, RecoveryStrategy.RETRY_WITH_BACKOFF)
    
    def test_recovery_strategy_platform_error_max_retries(self):
        """Test recovery strategy for platform errors at max retries"""
        error = Exception("API rate limit exceeded")
        self.mock_task.retry_count = 3  # At max retries
        
        strategy = self.recovery_manager.determine_recovery_strategy(
            error, self.mock_task
        )
        
        self.assertEqual(strategy, RecoveryStrategy.FAIL_FAST)
    
    def test_recovery_strategy_resource_error(self):
        """Test recovery strategy for resource errors"""
        error = Exception("Out of memory")
        strategy = self.recovery_manager.determine_recovery_strategy(
            error, self.mock_task
        )
        
        self.assertEqual(strategy, RecoveryStrategy.NOTIFY_ADMIN)
    
    def test_recovery_strategy_validation_error(self):
        """Test recovery strategy for validation errors"""
        error = Exception("Invalid input format")
        strategy = self.recovery_manager.determine_recovery_strategy(
            error, self.mock_task
        )
        
        self.assertEqual(strategy, RecoveryStrategy.FAIL_FAST)
    
    async def test_handle_error_retry_strategy(self):
        """Test error handling with retry strategy"""
        error = Exception("API rate limit exceeded")
        
        # Mock task update
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        result = await self.recovery_manager.handle_error(
            error, self.test_task_id
        )
        
        # Verify retry was scheduled
        self.assertTrue(result['should_retry'])
        self.assertGreater(result['retry_delay'], 0)
        self.assertEqual(self.mock_task.retry_count, 1)
        self.assertEqual(self.mock_task.status, TaskStatus.QUEUED)
    
    async def test_handle_error_fail_fast_strategy(self):
        """Test error handling with fail fast strategy"""
        error = Exception("Invalid access token")
        
        # Mock task update
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        result = await self.recovery_manager.handle_error(
            error, self.test_task_id
        )
        
        # Verify task was failed
        self.assertFalse(result['should_retry'])
        self.assertEqual(self.mock_task.status, TaskStatus.FAILED)
        self.assertIsNotNone(self.mock_task.error_message)
        self.assertIsNotNone(self.mock_task.completed_at)
    
    async def test_handle_error_notify_admin_strategy(self):
        """Test error handling with notify admin strategy"""
        error = Exception("Out of memory")
        
        # Mock task update
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        # Mock admin notification
        with patch.object(self.recovery_manager, '_notify_admin') as mock_notify:
            result = await self.recovery_manager.handle_error(
                error, self.test_task_id
            )
            
            # Verify admin was notified
            mock_notify.assert_called_once()
            self.assertFalse(result['should_retry'])
            self.assertEqual(self.mock_task.status, TaskStatus.FAILED)
    
    def test_calculate_retry_delay_exponential_backoff(self):
        """Test exponential backoff calculation"""
        # Test different retry counts
        delays = []
        for retry_count in range(1, 5):
            delay = self.recovery_manager._calculate_retry_delay(retry_count)
            delays.append(delay)
        
        # Verify delays increase exponentially
        for i in range(1, len(delays)):
            self.assertGreater(delays[i], delays[i-1])
        
        # Verify reasonable bounds
        self.assertGreaterEqual(delays[0], 60)  # At least 1 minute
        self.assertLessEqual(delays[-1], 3600)  # At most 1 hour
    
    def test_get_user_friendly_message_authentication(self):
        """Test user-friendly message for authentication errors"""
        error = Exception("Invalid access token")
        message = self.recovery_manager.get_user_friendly_message(error)
        
        self.assertIn("authentication", message.lower())
        self.assertIn("credentials", message.lower())
    
    def test_get_user_friendly_message_platform(self):
        """Test user-friendly message for platform errors"""
        error = Exception("API rate limit exceeded")
        message = self.recovery_manager.get_user_friendly_message(error)
        
        self.assertIn("platform", message.lower())
        self.assertIn("try again", message.lower())
    
    def test_get_user_friendly_message_resource(self):
        """Test user-friendly message for resource errors"""
        error = Exception("Out of memory")
        message = self.recovery_manager.get_user_friendly_message(error)
        
        self.assertIn("system", message.lower())
        self.assertIn("administrator", message.lower())
    
    def test_get_user_friendly_message_validation(self):
        """Test user-friendly message for validation errors"""
        error = Exception("Invalid input format")
        message = self.recovery_manager.get_user_friendly_message(error)
        
        self.assertIn("input", message.lower())
        self.assertIn("check", message.lower())
    
    def test_get_user_friendly_message_unknown(self):
        """Test user-friendly message for unknown errors"""
        error = Exception("Some unexpected error")
        message = self.recovery_manager.get_user_friendly_message(error)
        
        self.assertIn("unexpected", message.lower())
        self.assertIn("support", message.lower())
    
    async def test_log_error_details(self):
        """Test error logging functionality"""
        error = Exception("Test error for logging")
        
        with patch('error_recovery_manager.logger') as mock_logger:
            await self.recovery_manager._log_error(
                error, self.test_task_id, ErrorCategory.PLATFORM
            )
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            log_call = mock_logger.error.call_args[0][0]
            self.assertIn(self.test_task_id, log_call)
            self.assertIn("PLATFORM", log_call)
    
    async def test_notify_admin_functionality(self):
        """Test admin notification functionality"""
        error = Exception("Critical system error")
        
        # Mock user and platform data
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.email = "test@test.com"
        
        mock_platform = Mock(spec=PlatformConnection)
        mock_platform.name = "Test Platform"
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_user, mock_platform
        ]
        
        with patch('error_recovery_manager.logger') as mock_logger:
            await self.recovery_manager._notify_admin(
                error, self.test_task_id, self.test_user_id, self.test_platform_id
            )
            
            # Verify admin notification was logged
            mock_logger.critical.assert_called_once()
            log_call = mock_logger.critical.call_args[0][0]
            self.assertIn("ADMIN NOTIFICATION", log_call)
            self.assertIn("testuser", log_call)
    
    async def test_error_recovery_integration(self):
        """Test complete error recovery integration"""
        # Simulate a platform error that should be retried
        error = Exception("Connection timeout")
        
        # Mock task retrieval and update
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        # Handle the error
        result = await self.recovery_manager.handle_error(error, self.test_task_id)
        
        # Verify complete recovery process
        self.assertTrue(result['should_retry'])
        self.assertIn('retry_delay', result)
        self.assertIn('user_message', result)
        self.assertIn('error_category', result)
        
        # Verify task was updated
        self.assertEqual(self.mock_task.retry_count, 1)
        self.assertEqual(self.mock_task.status, TaskStatus.QUEUED)
        self.mock_session.commit.assert_called_once()
    
    def test_error_recovery_statistics(self):
        """Test error recovery statistics tracking"""
        # Mock some error handling calls
        errors = [
            Exception("Invalid token"),
            Exception("Rate limit exceeded"),
            Exception("Out of memory"),
            Exception("Connection timeout")
        ]
        
        # Process errors and track statistics
        stats = {
            'authentication_errors': 0,
            'platform_errors': 0,
            'resource_errors': 0,
            'retries_attempted': 0,
            'failures': 0
        }
        
        for error in errors:
            category = self.recovery_manager.categorize_error(error)
            if category == ErrorCategory.AUTHENTICATION:
                stats['authentication_errors'] += 1
                stats['failures'] += 1
            elif category == ErrorCategory.PLATFORM:
                stats['platform_errors'] += 1
                stats['retries_attempted'] += 1
            elif category == ErrorCategory.RESOURCE:
                stats['resource_errors'] += 1
                stats['failures'] += 1
        
        # Verify statistics
        self.assertEqual(stats['authentication_errors'], 1)
        self.assertEqual(stats['platform_errors'], 2)
        self.assertEqual(stats['resource_errors'], 1)
        self.assertEqual(stats['retries_attempted'], 2)
        self.assertEqual(stats['failures'], 2)

if __name__ == '__main__':
    unittest.main()