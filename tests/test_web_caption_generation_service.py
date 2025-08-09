# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Unit tests for Web Caption Generation Service
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import uuid
from datetime import datetime, timezone

from web_caption_generation_service import WebCaptionGenerationService
from models import (
    CaptionGenerationTask, CaptionGenerationSettings, CaptionGenerationUserSettings,
    GenerationResults, TaskStatus, PlatformConnection, User
)
from database import DatabaseManager

class TestWebCaptionGenerationService(unittest.TestCase):
    """Test cases for WebCaptionGenerationService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Create service
        self.service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Test data
        self.test_user_id = 1
        self.test_platform_id = 1
        self.test_task_id = str(uuid.uuid4())
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = self.test_user_id
        self.mock_user.is_active = True
        
        # Mock platform connection
        self.mock_platform = Mock(spec=PlatformConnection)
        self.mock_platform.id = self.test_platform_id
        self.mock_platform.user_id = self.test_user_id
        self.mock_platform.is_active = True
        
        # Mock task
        self.mock_task = Mock(spec=CaptionGenerationTask)
        self.mock_task.id = self.test_task_id
        self.mock_task.user_id = self.test_user_id
        self.mock_task.platform_connection_id = self.test_platform_id
        self.mock_task.status = TaskStatus.QUEUED
        self.mock_task.created_at = datetime.now(timezone.utc)
        self.mock_task.progress_percent = 0
        self.mock_task.current_step = "Queued"
        self.mock_task.error_message = None
        self.mock_task.results = None
        self.mock_task.is_completed.return_value = False
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.service.db_manager)
        self.assertIsNotNone(self.service.task_queue_manager)
        self.assertIsNotNone(self.service.progress_tracker)
        self.assertIsNotNone(self.service._background_tasks)
        self.assertIsNotNone(self.service._shutdown_event)
    
    @patch('web_caption_generation_service.CaptionGenerationTask')
    async def test_start_caption_generation_success(self, mock_task_class):
        """Test successful caption generation start"""
        # Mock validation
        self.service._validate_user_platform_access = AsyncMock()
        self.service._get_user_settings = AsyncMock(return_value=CaptionGenerationSettings())
        
        # Mock task creation and enqueueing
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance
        self.service.task_queue_manager.enqueue_task = Mock(return_value=self.test_task_id)
        
        # Mock background processor
        self.service._ensure_background_processor = Mock()
        
        result = await self.service.start_caption_generation(
            self.test_user_id, 
            self.test_platform_id
        )
        
        self.assertEqual(result, self.test_task_id)
        self.service._validate_user_platform_access.assert_called_once_with(
            self.test_user_id, 
            self.test_platform_id
        )
        self.service.task_queue_manager.enqueue_task.assert_called_once()
        self.service._ensure_background_processor.assert_called_once()
    
    async def test_start_caption_generation_validation_failure(self):
        """Test caption generation start with validation failure"""
        # Mock validation to raise error
        self.service._validate_user_platform_access = AsyncMock(
            side_effect=ValueError("User not found")
        )
        
        with self.assertRaises(ValueError):
            await self.service.start_caption_generation(
                self.test_user_id, 
                self.test_platform_id
            )
    
    def test_get_generation_status_success(self):
        """Test successful status retrieval"""
        # Mock task queue manager
        self.service.task_queue_manager.get_task = Mock(return_value=self.mock_task)
        
        # Mock progress tracker
        mock_progress = Mock()
        mock_progress.details = {'test': 'details'}
        self.service.progress_tracker.get_progress = Mock(return_value=mock_progress)
        
        result = self.service.get_generation_status(self.test_task_id, self.test_user_id)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['task_id'], self.test_task_id)
        self.assertEqual(result['status'], TaskStatus.QUEUED.value)
        self.assertEqual(result['progress_percent'], 0)
        self.assertEqual(result['current_step'], "Queued")
        self.assertIn('progress_details', result)
    
    def test_get_generation_status_unauthorized(self):
        """Test status retrieval with unauthorized user"""
        # Mock task with different user
        self.mock_task.user_id = 999
        self.service.task_queue_manager.get_task = Mock(return_value=self.mock_task)
        
        result = self.service.get_generation_status(self.test_task_id, self.test_user_id)
        
        self.assertIsNone(result)
    
    def test_get_generation_status_not_found(self):
        """Test status retrieval when task not found"""
        self.service.task_queue_manager.get_task = Mock(return_value=None)
        
        result = self.service.get_generation_status(self.test_task_id, self.test_user_id)
        
        self.assertIsNone(result)
    
    def test_cancel_generation_success(self):
        """Test successful task cancellation"""
        self.service.task_queue_manager.cancel_task = Mock(return_value=True)
        
        result = self.service.cancel_generation(self.test_task_id, self.test_user_id)
        
        self.assertTrue(result)
        self.service.task_queue_manager.cancel_task.assert_called_once_with(
            self.test_task_id, 
            self.test_user_id
        )
    
    def test_cancel_generation_failure(self):
        """Test task cancellation failure"""
        self.service.task_queue_manager.cancel_task = Mock(return_value=False)
        
        result = self.service.cancel_generation(self.test_task_id, self.test_user_id)
        
        self.assertFalse(result)
    
    async def test_get_generation_results_success(self):
        """Test successful results retrieval"""
        # Mock completed task with results
        self.mock_task.is_completed.return_value = True
        mock_results = Mock(spec=GenerationResults)
        self.mock_task.results = mock_results
        
        self.service.task_queue_manager.get_task = Mock(return_value=self.mock_task)
        
        result = await self.service.get_generation_results(self.test_task_id, self.test_user_id)
        
        self.assertEqual(result, mock_results)
    
    async def test_get_generation_results_not_completed(self):
        """Test results retrieval for incomplete task"""
        # Mock incomplete task
        self.mock_task.is_completed.return_value = False
        self.service.task_queue_manager.get_task = Mock(return_value=self.mock_task)
        
        result = await self.service.get_generation_results(self.test_task_id, self.test_user_id)
        
        self.assertIsNone(result)
    
    async def test_validate_user_platform_access_success(self):
        """Test successful user platform access validation"""
        # Mock database queries
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_user,  # User query
            self.mock_platform  # Platform query
        ]
        
        # Mock no active task
        self.service.task_queue_manager.get_user_active_task = Mock(return_value=None)
        
        # Should not raise exception
        await self.service._validate_user_platform_access(
            self.test_user_id, 
            self.test_platform_id
        )
    
    async def test_validate_user_platform_access_user_not_found(self):
        """Test validation failure when user not found"""
        # Mock user not found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with self.assertRaises(ValueError) as context:
            await self.service._validate_user_platform_access(
                self.test_user_id, 
                self.test_platform_id
            )
        
        self.assertIn("not found or inactive", str(context.exception))
    
    async def test_validate_user_platform_access_platform_not_found(self):
        """Test validation failure when platform not found"""
        # Mock user found, platform not found
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_user,  # User query
            None  # Platform query
        ]
        
        with self.assertRaises(ValueError) as context:
            await self.service._validate_user_platform_access(
                self.test_user_id, 
                self.test_platform_id
            )
        
        self.assertIn("not found or not accessible", str(context.exception))
    
    async def test_validate_user_platform_access_active_task_exists(self):
        """Test validation failure when user has active task"""
        # Mock user and platform found
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            self.mock_user,  # User query
            self.mock_platform  # Platform query
        ]
        
        # Mock active task exists
        mock_active_task = Mock()
        mock_active_task.id = "active-task-id"
        self.service.task_queue_manager.get_user_active_task = Mock(return_value=mock_active_task)
        
        with self.assertRaises(ValueError) as context:
            await self.service._validate_user_platform_access(
                self.test_user_id, 
                self.test_platform_id
            )
        
        self.assertIn("already has an active", str(context.exception))
    
    async def test_get_user_settings_custom_settings(self):
        """Test getting user's custom settings"""
        # Mock custom settings found
        mock_user_settings = Mock(spec=CaptionGenerationUserSettings)
        mock_settings = CaptionGenerationSettings(max_posts_per_run=20)
        mock_user_settings.to_settings_dataclass.return_value = mock_settings
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user_settings
        
        result = await self.service._get_user_settings(self.test_user_id, self.test_platform_id)
        
        self.assertEqual(result.max_posts_per_run, 20)
    
    async def test_get_user_settings_default_settings(self):
        """Test getting default settings when no custom settings exist"""
        # Mock no custom settings found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = await self.service._get_user_settings(self.test_user_id, self.test_platform_id)
        
        # Should return default settings
        self.assertIsInstance(result, CaptionGenerationSettings)
        self.assertEqual(result.max_posts_per_run, 50)  # Default value
    
    def test_get_service_stats(self):
        """Test getting service statistics"""
        # Mock queue stats
        mock_queue_stats = {'queued': 2, 'running': 1, 'completed': 5}
        self.service.task_queue_manager.get_queue_stats = Mock(return_value=mock_queue_stats)
        
        # Mock active progress sessions
        mock_active_sessions = {'task1': Mock(), 'task2': Mock()}
        self.service.progress_tracker.get_active_progress_sessions = Mock(return_value=mock_active_sessions)
        
        result = self.service.get_service_stats()
        
        self.assertEqual(result['queue_stats'], mock_queue_stats)
        self.assertEqual(result['active_progress_sessions'], 2)
        self.assertEqual(result['background_processors'], 0)  # No background tasks in test
        self.assertEqual(result['service_status'], 'running')
    
    async def test_save_user_settings_new_settings(self):
        """Test saving new user settings"""
        # Mock no existing settings
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        settings = CaptionGenerationSettings(max_posts_per_run=25)
        
        result = await self.service.save_user_settings(
            self.test_user_id, 
            self.test_platform_id, 
            settings
        )
        
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
    
    async def test_save_user_settings_update_existing(self):
        """Test updating existing user settings"""
        # Mock existing settings
        mock_existing_settings = Mock(spec=CaptionGenerationUserSettings)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_existing_settings
        
        settings = CaptionGenerationSettings(max_posts_per_run=25)
        
        result = await self.service.save_user_settings(
            self.test_user_id, 
            self.test_platform_id, 
            settings
        )
        
        self.assertTrue(result)
        mock_existing_settings.update_from_dataclass.assert_called_once_with(settings)
        self.mock_session.commit.assert_called_once()
    
    async def test_get_user_task_history(self):
        """Test getting user task history"""
        # Mock task history
        mock_tasks = [self.mock_task]
        self.service.task_queue_manager.get_user_task_history = Mock(return_value=mock_tasks)
        
        result = await self.service.get_user_task_history(self.test_user_id, limit=5)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['task_id'], self.test_task_id)
        self.assertEqual(result[0]['status'], TaskStatus.QUEUED.value)
        
        self.service.task_queue_manager.get_user_task_history.assert_called_once_with(
            self.test_user_id, 
            5
        )

if __name__ == '__main__':
    unittest.main()