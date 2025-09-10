# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for complete caption generation workflow
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import uuid
import asyncio
from datetime import datetime, timezone

from web_caption_generation_service import WebCaptionGenerationService
from app.services.task.core.task_queue_manager import TaskQueueManager
from progress_tracker import ProgressTracker
from models import (
    CaptionGenerationTask, TaskStatus, PlatformConnection, User,
    CaptionGenerationSettings, GenerationResults
)
from app.core.database.core.database_manager import DatabaseManager

class TestCaptionGenerationWorkflow(unittest.TestCase):
    """Integration tests for complete caption generation workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Create service components
        self.service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Test data
        self.test_user_id = 1
        self.test_platform_id = 1
        self.test_task_id = str(uuid.uuid4())
        
        # Mock user and platform
        self.mock_user = Mock(spec=User)
        self.mock_user.id = self.test_user_id
        self.mock_user.is_active = True
        
        self.mock_platform = Mock(spec=PlatformConnection)
        self.mock_platform.id = self.test_platform_id
        self.mock_platform.user_id = self.test_user_id
        self.mock_platform.is_active = True
    
    @patch('web_caption_generation_service.PlatformAwareCaptionAdapter')
    async def test_complete_generation_workflow(self, mock_adapter_class):
        """Test complete caption generation workflow from start to finish"""
        # Mock adapter
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter
        
        # Mock successful generation
        mock_results = GenerationResults(
            total_posts_processed=5,
            captions_generated=3,
            captions_updated=2,
            errors=[]
        )
        mock_adapter.generate_captions_for_user = AsyncMock(return_value=mock_results)
        
        # Mock validation
        self.service._validate_user_platform_access = AsyncMock()
        self.service._get_user_settings = AsyncMock(return_value=CaptionGenerationSettings())
        
        # Mock task creation
        with patch('web_caption_generation_service.CaptionGenerationTask') as mock_task_class:
            mock_task = Mock()
            mock_task.id = self.test_task_id
            mock_task_class.return_value = mock_task
            
            # Mock task queue operations
            self.service.task_queue_manager.enqueue_task = Mock(return_value=self.test_task_id)
            self.service.task_queue_manager.get_next_task = Mock(return_value=mock_task)
            self.service.task_queue_manager.complete_task = Mock(return_value=True)
            
            # Mock progress tracking
            self.service.progress_tracker.start_progress = Mock()
            self.service.progress_tracker.update_progress = Mock()
            self.service.progress_tracker.complete_progress = Mock()
            
            # Start generation
            task_id = await self.service.start_caption_generation(
                self.test_user_id, 
                self.test_platform_id
            )
            
            # Verify task was enqueued
            self.assertEqual(task_id, self.test_task_id)
            self.service.task_queue_manager.enqueue_task.assert_called_once()
            
            # Simulate background processing
            await self.service._process_single_task(mock_task)
            
            # Verify adapter was called
            mock_adapter.generate_captions_for_user.assert_called_once()
            
            # Verify task completion
            self.service.task_queue_manager.complete_task.assert_called_once_with(
                self.test_task_id, 
                success=True
            )
            
            # Verify progress tracking
            self.service.progress_tracker.start_progress.assert_called_once()
            self.service.progress_tracker.complete_progress.assert_called_once()
    
    def test_service_statistics_workflow(self):
        """Test service statistics retrieval"""
        # Mock queue statistics
        mock_queue_stats = {
            'queued': 3,
            'running': 2,
            'completed': 15,
            'failed': 1,
            'cancelled': 0,
            'total': 21,
            'active': 5
        }
        self.service.task_queue_manager.get_queue_stats = Mock(return_value=mock_queue_stats)
        
        # Mock active progress sessions
        mock_active_sessions = {'task1': Mock(), 'task2': Mock()}
        self.service.progress_tracker.get_active_progress_sessions = Mock(return_value=mock_active_sessions)
        
        # Get statistics
        stats = self.service.get_service_stats()
        
        # Verify statistics
        self.assertEqual(stats['queue_stats'], mock_queue_stats)
        self.assertEqual(stats['active_progress_sessions'], 2)
        self.assertIn('service_status', stats)
        self.assertIn('background_processors', stats)

if __name__ == '__main__':
    unittest.main()