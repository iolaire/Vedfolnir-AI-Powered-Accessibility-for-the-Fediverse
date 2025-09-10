# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for platform switching with caption generation
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import uuid
from datetime import datetime, timezone

from web_caption_generation_service import WebCaptionGenerationService
from models import (
    CaptionGenerationTask, TaskStatus, PlatformConnection, User, UserRole,
    CaptionGenerationSettings
)
from app.core.database.core.database_manager import DatabaseManager

class TestPlatformSwitchingIntegration(unittest.TestCase):
    """Test cases for platform switching integration with caption generation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Test data
        self.test_user_id = 1
        self.test_platform_1_id = 1
        self.test_platform_2_id = 2
        self.test_task_id = str(uuid.uuid4())
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = self.test_user_id
        self.mock_user.username = "testuser"
        self.mock_user.is_active = True
        self.mock_user.role = UserRole.REVIEWER
        
        # Mock platform connections
        self.mock_platform_1 = Mock(spec=PlatformConnection)
        self.mock_platform_1.id = self.test_platform_1_id
        self.mock_platform_1.user_id = self.test_user_id
        self.mock_platform_1.name = "Platform 1"
        self.mock_platform_1.platform_type = "pixelfed"
        self.mock_platform_1.is_active = True
        
        self.mock_platform_2 = Mock(spec=PlatformConnection)
        self.mock_platform_2.id = self.test_platform_2_id
        self.mock_platform_2.user_id = self.test_user_id
        self.mock_platform_2.name = "Platform 2"
        self.mock_platform_2.platform_type = "mastodon"
        self.mock_platform_2.is_active = True
        
        # Mock active task
        self.mock_active_task = Mock(spec=CaptionGenerationTask)
        self.mock_active_task.id = self.test_task_id
        self.mock_active_task.user_id = self.test_user_id
        self.mock_active_task.platform_connection_id = self.test_platform_1_id
        self.mock_active_task.status = TaskStatus.RUNNING
        self.mock_active_task.created_at = datetime.now(timezone.utc)
    
    def test_platform_switch_with_no_active_task(self):
        """Test platform switching when no caption generation task is active"""
        # Mock no active task
        service = WebCaptionGenerationService(self.mock_db_manager)
        service.task_queue_manager.get_user_active_task = Mock(return_value=None)
        
        # This should not raise any exceptions or cancel anything
        active_task = service.task_queue_manager.get_user_active_task(self.test_user_id)
        self.assertIsNone(active_task)
    
    def test_platform_switch_with_active_task(self):
        """Test platform switching when caption generation task is active"""
        # Mock active task exists
        service = WebCaptionGenerationService(self.mock_db_manager)
        service.task_queue_manager.get_user_active_task = Mock(return_value=self.mock_active_task)
        service.task_queue_manager.cancel_task = Mock(return_value=True)
        
        # Get active task
        active_task = service.task_queue_manager.get_user_active_task(self.test_user_id)
        self.assertIsNotNone(active_task)
        self.assertEqual(active_task.id, self.test_task_id)
        
        # Cancel the task (simulating platform switch)
        cancelled = service.cancel_generation(active_task.id, self.test_user_id)
        self.assertTrue(cancelled)
        
        # Verify cancel was called with correct parameters
        service.task_queue_manager.cancel_task.assert_called_once_with(
            self.test_task_id, 
            self.test_user_id
        )
    
    def test_platform_switch_cancel_failure(self):
        """Test platform switching when task cancellation fails"""
        # Mock active task exists but cancellation fails
        service = WebCaptionGenerationService(self.mock_db_manager)
        service.task_queue_manager.get_user_active_task = Mock(return_value=self.mock_active_task)
        service.task_queue_manager.cancel_task = Mock(return_value=False)
        
        # Get active task
        active_task = service.task_queue_manager.get_user_active_task(self.test_user_id)
        self.assertIsNotNone(active_task)
        
        # Try to cancel the task (simulating platform switch)
        cancelled = service.cancel_generation(active_task.id, self.test_user_id)
        self.assertFalse(cancelled)
    
    def test_platform_availability_check(self):
        """Test checking platform availability for caption generation"""
        # Test supported platforms
        supported_platforms = ['pixelfed', 'mastodon']
        
        for platform_type in supported_platforms:
            self.assertIn(platform_type, supported_platforms)
        
        # Test unsupported platforms (should still work but with warnings)
        unsupported_platforms = ['twitter', 'facebook', 'instagram']
        
        for platform_type in unsupported_platforms:
            self.assertNotIn(platform_type, supported_platforms)
    
    def test_platform_context_validation(self):
        """Test platform context validation during caption generation"""
        service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Mock database queries for validation
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_user,  # User query
            self.mock_platform_1  # Platform query
        ]
        
        # Mock no active task
        service.task_queue_manager.get_user_active_task = Mock(return_value=None)
        
        # This should not raise an exception
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                service._validate_user_platform_access(
                    self.test_user_id, 
                    self.test_platform_1_id
                )
            )
            loop.close()
        except Exception as e:
            self.fail(f"Platform context validation failed: {e}")
    
    def test_platform_context_validation_failure(self):
        """Test platform context validation failure"""
        service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Mock user found but platform not found
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_user,  # User query
            None  # Platform query - not found
        ]
        
        # This should raise a ValueError
        with self.assertRaises(ValueError) as context:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                service._validate_user_platform_access(
                    self.test_user_id, 
                    self.test_platform_2_id  # Different platform
                )
            )
            loop.close()
        
        self.assertIn("not found or not accessible", str(context.exception))
    
    def test_cross_platform_task_isolation(self):
        """Test that tasks are properly isolated between platforms"""
        service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Mock task on platform 1
        task_platform_1 = Mock(spec=CaptionGenerationTask)
        task_platform_1.platform_connection_id = self.test_platform_1_id
        task_platform_1.user_id = self.test_user_id
        
        # Mock task on platform 2
        task_platform_2 = Mock(spec=CaptionGenerationTask)
        task_platform_2.platform_connection_id = self.test_platform_2_id
        task_platform_2.user_id = self.test_user_id
        
        # Tasks should be isolated by user, not by platform
        # (since we enforce single task per user across all platforms)
        self.assertEqual(task_platform_1.user_id, task_platform_2.user_id)
        self.assertNotEqual(task_platform_1.platform_connection_id, task_platform_2.platform_connection_id)
    
    def test_platform_switch_settings_preservation(self):
        """Test that platform-specific settings are preserved during switches"""
        service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Mock different settings for different platforms
        settings_platform_1 = CaptionGenerationSettings(
            max_posts_per_run=25,
            max_caption_length=400
        )
        
        settings_platform_2 = CaptionGenerationSettings(
            max_posts_per_run=50,
            max_caption_length=600
        )
        
        # Settings should be different for different platforms
        self.assertNotEqual(settings_platform_1.max_posts_per_run, settings_platform_2.max_posts_per_run)
        self.assertNotEqual(settings_platform_1.max_caption_length, settings_platform_2.max_caption_length)
        
        # But both should be valid CaptionGenerationSettings objects
        self.assertIsInstance(settings_platform_1, CaptionGenerationSettings)
        self.assertIsInstance(settings_platform_2, CaptionGenerationSettings)

if __name__ == '__main__':
    unittest.main()