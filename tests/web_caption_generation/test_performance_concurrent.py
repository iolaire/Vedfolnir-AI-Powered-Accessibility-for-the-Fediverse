# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Performance tests for concurrent caption generation scenarios
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import uuid
import time
from concurrent.futures import ThreadPoolExecutor

from web_caption_generation_service import WebCaptionGenerationService
from task_queue_manager import TaskQueueManager
from models import CaptionGenerationTask, TaskStatus, CaptionGenerationSettings
from database import DatabaseManager

class TestConcurrentPerformance(unittest.TestCase):
    """Performance tests for concurrent caption generation scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.service = WebCaptionGenerationService(self.mock_db_manager)
        
        # Test data
        self.test_users = list(range(1, 11))  # 10 test users
        self.test_platform_id = 1
    
    def test_concurrent_task_enqueueing(self):
        """Test concurrent task enqueueing performance"""
        # Mock validation and settings
        self.service._validate_user_platform_access = AsyncMock()
        self.service._get_user_settings = AsyncMock(return_value=CaptionGenerationSettings())
        
        # Mock task creation
        with patch('web_caption_generation_service.CaptionGenerationTask') as mock_task_class:
            mock_tasks = []
            for i, user_id in enumerate(self.test_users):
                mock_task = Mock()
                mock_task.id = f"task-{user_id}"
                mock_tasks.append(mock_task)
            
            mock_task_class.side_effect = mock_tasks
            
            # Mock task queue operations
            self.service.task_queue_manager.enqueue_task = Mock(
                side_effect=[f"task-{user_id}" for user_id in self.test_users]
            )
            
            async def enqueue_for_user(user_id):
                return await self.service.start_caption_generation(user_id, self.test_platform_id)
            
            # Measure concurrent enqueueing time
            start_time = time.time()
            
            async def run_concurrent_enqueuing():
                tasks = [enqueue_for_user(user_id) for user_id in self.test_users]
                return await asyncio.gather(*tasks)
            
            results = asyncio.run(run_concurrent_enqueuing())
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify all tasks were enqueued
            self.assertEqual(len(results), len(self.test_users))
            for i, result in enumerate(results):
                self.assertEqual(result, f"task-{self.test_users[i]}")
            
            # Performance assertion (should complete within reasonable time)
            self.assertLess(duration, 5.0, "Concurrent enqueueing took too long")
    
    def test_concurrent_status_checking(self):
        """Test concurrent status checking performance"""
        # Mock tasks
        mock_tasks = []
        for user_id in self.test_users:
            mock_task = Mock()
            mock_task.id = f"task-{user_id}"
            mock_task.user_id = user_id
            mock_task.status = TaskStatus.RUNNING
            mock_task.progress_percent = 50
            mock_task.current_step = "Processing"
            mock_task.error_message = None
            mock_task.results = None
            mock_task.is_completed.return_value = False
            mock_tasks.append(mock_task)
        
        self.service.task_queue_manager.get_task = Mock(side_effect=mock_tasks)
        
        # Mock progress tracking
        mock_progress = Mock()
        mock_progress.details = {'test': 'data'}
        self.service.progress_tracker.get_progress = Mock(return_value=mock_progress)
        
        def check_status_for_user(user_id):
            return self.service.get_generation_status(f"task-{user_id}", user_id)
        
        # Measure concurrent status checking time
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(check_status_for_user, user_id) 
                for user_id in self.test_users
            ]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all status checks completed
        self.assertEqual(len(results), len(self.test_users))
        for result in results:
            self.assertIsNotNone(result)
            self.assertEqual(result['status'], TaskStatus.RUNNING.value)
        
        # Performance assertion
        self.assertLess(duration, 2.0, "Concurrent status checking took too long")
    
    def test_queue_manager_concurrent_operations(self):
        """Test queue manager performance under concurrent operations"""
        queue_manager = TaskQueueManager(self.mock_db_manager, max_concurrent_tasks=5)
        
        # Mock database operations
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.first.return_value = None
        self.mock_session.query.return_value.filter_by.return_value.count.return_value = 0
        
        # Create test tasks
        test_tasks = []
        for user_id in self.test_users:
            task = CaptionGenerationTask(
                id=f"task-{user_id}",
                user_id=user_id,
                platform_connection_id=self.test_platform_id,
                status=TaskStatus.QUEUED
            )
            task.settings = CaptionGenerationSettings()
            test_tasks.append(task)
        
        def enqueue_task(task):
            return queue_manager.enqueue_task(task)
        
        # Measure concurrent enqueueing time
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(enqueue_task, task) for task in test_tasks]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all tasks were enqueued
        self.assertEqual(len(results), len(test_tasks))
        
        # Performance assertion
        self.assertLess(duration, 3.0, "Concurrent task enqueueing took too long")
    
    def test_memory_usage_under_load(self):
        """Test memory usage under concurrent load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many mock tasks
        large_user_list = list(range(1, 101))  # 100 users
        
        # Mock validation and settings
        self.service._validate_user_platform_access = AsyncMock()
        self.service._get_user_settings = AsyncMock(return_value=CaptionGenerationSettings())
        
        # Mock task creation
        with patch('web_caption_generation_service.CaptionGenerationTask') as mock_task_class:
            mock_tasks = []
            for user_id in large_user_list:
                mock_task = Mock()
                mock_task.id = f"task-{user_id}"
                mock_tasks.append(mock_task)
            
            mock_task_class.side_effect = mock_tasks
            
            # Mock task queue operations
            self.service.task_queue_manager.enqueue_task = Mock(
                side_effect=[f"task-{user_id}" for user_id in large_user_list]
            )
            
            async def process_large_batch():
                tasks = [
                    self.service.start_caption_generation(user_id, self.test_platform_id)
                    for user_id in large_user_list
                ]
                return await asyncio.gather(*tasks)
            
            # Process large batch
            results = asyncio.run(process_large_batch())
            
            # Check memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Verify processing completed
            self.assertEqual(len(results), len(large_user_list))
            
            # Memory usage should not increase excessively
            self.assertLess(memory_increase, 100, "Memory usage increased too much")
    
    def test_database_connection_pooling(self):
        """Test database connection handling under concurrent load"""
        # Mock multiple database sessions
        mock_sessions = [Mock() for _ in range(10)]
        self.mock_db_manager.get_session.side_effect = mock_sessions
        
        def simulate_database_operation(user_id):
            # Simulate a database-heavy operation
            service = WebCaptionGenerationService(self.mock_db_manager)
            return service.get_generation_status(f"task-{user_id}", user_id)
        
        # Mock task for each user
        for i, user_id in enumerate(self.test_users):
            mock_task = Mock()
            mock_task.id = f"task-{user_id}"
            mock_task.user_id = user_id
            mock_task.status = TaskStatus.QUEUED
            mock_task.progress_percent = 0
            mock_task.current_step = "Queued"
            mock_task.error_message = None
            mock_task.results = None
            mock_task.is_completed.return_value = False
            
            # Set up session mock for this user
            if i < len(mock_sessions):
                mock_sessions[i].query.return_value.filter_by.return_value.first.return_value = mock_task
        
        # Mock progress tracking
        mock_progress = Mock()
        mock_progress.details = {}
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(simulate_database_operation, user_id)
                for user_id in self.test_users
            ]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify database sessions were used
        self.assertGreater(self.mock_db_manager.get_session.call_count, 0)
        
        # Performance assertion
        self.assertLess(duration, 5.0, "Database operations took too long")
    
    def test_error_handling_under_concurrent_load(self):
        """Test error handling performance under concurrent load"""
        # Mock some operations to fail
        def mock_validation_with_failures(user_id, platform_id):
            if user_id % 3 == 0:  # Every third user fails
                raise ValueError(f"Validation failed for user {user_id}")
            return AsyncMock()()
        
        self.service._validate_user_platform_access = mock_validation_with_failures
        self.service._get_user_settings = AsyncMock(return_value=CaptionGenerationSettings())
        
        async def try_enqueue_for_user(user_id):
            try:
                return await self.service.start_caption_generation(user_id, self.test_platform_id)
            except ValueError as e:
                return f"error-{user_id}"
        
        start_time = time.time()
        
        async def run_with_errors():
            tasks = [try_enqueue_for_user(user_id) for user_id in self.test_users]
            return await asyncio.gather(*tasks)
        
        results = asyncio.run(run_with_errors())
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify mixed results (some success, some errors)
        success_count = sum(1 for r in results if not r.startswith("error-"))
        error_count = sum(1 for r in results if r.startswith("error-"))
        
        self.assertGreater(success_count, 0)
        self.assertGreater(error_count, 0)
        self.assertEqual(success_count + error_count, len(self.test_users))
        
        # Performance assertion (error handling shouldn't slow things down significantly)
        self.assertLess(duration, 5.0, "Error handling took too long")

if __name__ == '__main__':
    unittest.main()