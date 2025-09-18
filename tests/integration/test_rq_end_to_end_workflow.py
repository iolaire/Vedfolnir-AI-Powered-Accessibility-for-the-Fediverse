# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for RQ End-to-End Workflow

Tests complete task processing workflow from web interface to completion,
including Gunicorn integration, worker coordination, and WebSocket progress tracking.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
import json
from datetime import datetime, timezone
import redis
from rq import Queue, Job, Worker
from flask import Flask

from app.core.database.core.database_manager import DatabaseManager
from app.core.security.features.caption_security import CaptionSecurityManager
from app.services.task.rq.rq_queue_manager import RQQueueManager
from app.services.task.rq.rq_worker_manager import RQWorkerManager
from app.services.task.rq.rq_progress_tracker import RQProgressTracker
from app.services.task.web.rq_web_caption_service import RQWebCaptionService
from app.services.task.rq.rq_config import RQConfig, TaskPriority
from app.services.caption.caption_generation_settings import CaptionGenerationSettings
from models import CaptionGenerationTask, TaskStatus, JobPriority, User, UserRole, PlatformConnection


class TestRQEndToEndWorkflow(unittest.TestCase):
    """Test complete RQ workflow from web interface to task completion"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        # Mock Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        self.mock_security_manager = Mock(spec=CaptionSecurityManager)
        self.mock_security_manager.generate_secure_task_id.return_value = "secure-task-123"
        
        # Mock Redis connection
        self.mock_redis = Mock(spec=redis.Redis)
        self.mock_redis.ping.return_value = True
        
        # Create test configuration
        self.config = RQConfig()
        
        # Mock WebSocket manager
        self.mock_websocket_manager = Mock()
        
        # Initialize components
        with patch('app.services.task.rq.rq_queue_manager.RedisConnectionManager'):
            with patch('app.services.task.rq.rq_queue_manager.Queue') as mock_queue_class:
                # Mock queues
                self.mock_queues = {}
                for priority in ['urgent', 'high', 'normal', 'low']:
                    mock_queue = Mock(spec=Queue)
                    mock_queue.name = priority
                    mock_queue.count = 0
                    self.mock_queues[priority] = mock_queue
                
                mock_queue_class.side_effect = lambda name, **kwargs: self.mock_queues[name]
                
                self.rq_queue_manager = RQQueueManager(
                    self.mock_db_manager,
                    self.config,
                    self.mock_security_manager
                )
                self.rq_queue_manager.redis_connection = self.mock_redis
                self.rq_queue_manager.queues = self.mock_queues
                self.rq_queue_manager._redis_available = True
        
        # Initialize other components
        self.rq_worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            self.mock_queues
        )
        
        self.rq_progress_tracker = RQProgressTracker(
            self.mock_websocket_manager,
            self.mock_db_manager
        )
        
        self.rq_web_service = RQWebCaptionService(
            self.mock_db_manager,
            self.rq_queue_manager
        )
    
    def test_complete_task_workflow_success(self):
        """Test complete successful task workflow from submission to completion"""
        # Step 1: Web interface receives task submission
        user_id = 1
        platform_connection_id = 1
        settings = CaptionGenerationSettings(max_length=500, style='descriptive')
        
        # Mock user and platform connection
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.role = UserRole.USER
        
        mock_platform = Mock(spec=PlatformConnection)
        mock_platform.id = platform_connection_id
        mock_platform.user_id = user_id
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_user, mock_platform
        ]
        
        # Mock no existing active task
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock RQ enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "rq-job-123"
        self.mock_queues['normal'].enqueue.return_value = mock_job
        
        # Step 2: Submit task through web service
        task_id = self.rq_web_service.start_caption_generation(
            user_id=user_id,
            platform_connection_id=platform_connection_id,
            settings=settings,
            priority=TaskPriority.NORMAL
        )
        
        # Verify task was submitted
        self.assertEqual(task_id, "secure-task-123")
        self.mock_queues['normal'].enqueue.assert_called_once()
        
        # Step 3: Worker picks up and processes task
        # Mock task retrieval from database
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_task.platform_connection_id = platform_connection_id
        mock_task.status = TaskStatus.QUEUED
        mock_task.settings = settings
        
        # Mock job processing
        with patch('app.services.task.rq.rq_job_processor.RQJobProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_task.return_value = {
                'success': True,
                'task_id': task_id,
                'captions_generated': 5,
                'images_processed': 10,
                'processing_time': 30.5
            }
            mock_processor_class.return_value = mock_processor
            
            # Simulate job execution
            job_result = mock_processor.process_task(task_id)
            
            # Verify job processing
            self.assertTrue(job_result['success'])
            self.assertEqual(job_result['task_id'], task_id)
            self.assertEqual(job_result['captions_generated'], 5)
        
        # Step 4: Progress tracking and WebSocket updates
        # Mock progress updates during processing
        progress_updates = [
            {'progress': 25, 'message': 'Starting caption generation'},
            {'progress': 50, 'message': 'Processing images'},
            {'progress': 75, 'message': 'Generating captions'},
            {'progress': 100, 'message': 'Caption generation completed'}
        ]
        
        for update in progress_updates:
            self.rq_progress_tracker.update_task_progress(
                task_id, 
                update['progress'], 
                update['message']
            )
        
        # Verify WebSocket updates were sent
        self.assertEqual(self.mock_websocket_manager.emit.call_count, 4)
        
        # Step 5: Task completion and cleanup
        self.rq_progress_tracker.send_completion_notification(task_id, success=True)
        
        # Verify completion notification
        completion_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                          if 'task_completed' in str(call)]
        self.assertTrue(len(completion_calls) > 0)
    
    def test_task_workflow_with_failure_and_retry(self):
        """Test task workflow with failure and automatic retry"""
        # Step 1: Submit task
        user_id = 1
        platform_connection_id = 1
        settings = CaptionGenerationSettings(max_length=500)
        
        # Mock user and platform
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.role = UserRole.USER
        
        mock_platform = Mock(spec=PlatformConnection)
        mock_platform.id = platform_connection_id
        
        self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_user, mock_platform
        ]
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock RQ enqueue
        mock_job = Mock(spec=Job)
        mock_job.id = "retry-job-123"
        self.mock_queues['normal'].enqueue.return_value = mock_job
        
        task_id = self.rq_web_service.start_caption_generation(
            user_id=user_id,
            platform_connection_id=platform_connection_id,
            settings=settings
        )
        
        # Step 2: First processing attempt fails
        with patch('app.services.task.rq.rq_job_processor.RQJobProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_processor.process_task.side_effect = [
                # First attempt fails
                Exception("Network timeout during caption generation"),
                # Second attempt succeeds
                {
                    'success': True,
                    'task_id': task_id,
                    'captions_generated': 3,
                    'retry_count': 1
                }
            ]
            mock_processor_class.return_value = mock_processor
            
            # Step 3: Handle failure and retry
            try:
                # First attempt
                mock_processor.process_task(task_id)
                self.fail("Expected exception was not raised")
            except Exception as e:
                # Verify failure was handled
                self.assertIn("Network timeout", str(e))
                
                # Mock retry mechanism
                self.rq_progress_tracker.handle_task_failure(task_id, e)
                
                # Verify failure notification
                failure_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                               if 'task_failed' in str(call)]
                self.assertTrue(len(failure_calls) > 0)
                
                # Second attempt (retry)
                retry_result = mock_processor.process_task(task_id)
                
                # Verify retry success
                self.assertTrue(retry_result['success'])
                self.assertEqual(retry_result['retry_count'], 1)
    
    def test_concurrent_task_processing(self):
        """Test concurrent processing of multiple tasks"""
        # Create multiple tasks for different users
        tasks_data = []
        for i in range(5):
            user_id = i + 1
            platform_connection_id = 1
            
            # Mock user
            mock_user = Mock(spec=User)
            mock_user.id = user_id
            mock_user.role = UserRole.USER
            
            tasks_data.append({
                'user_id': user_id,
                'platform_connection_id': platform_connection_id,
                'user': mock_user
            })
        
        # Mock database queries for all users
        def mock_query_side_effect(*args, **kwargs):
            mock_query = Mock()
            mock_query.filter_by.return_value.first.side_effect = [
                task_data['user'] for task_data in tasks_data
            ] + [Mock(spec=PlatformConnection)] * len(tasks_data)
            mock_query.filter.return_value.first.return_value = None  # No active tasks
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # Mock RQ enqueue for all tasks
        mock_jobs = []
        for i in range(5):
            mock_job = Mock(spec=Job)
            mock_job.id = f"concurrent-job-{i}"
            mock_jobs.append(mock_job)
        
        self.mock_queues['normal'].enqueue.side_effect = mock_jobs
        
        # Submit all tasks concurrently
        submitted_tasks = []
        threads = []
        
        def submit_task(task_data):
            try:
                task_id = self.rq_web_service.start_caption_generation(
                    user_id=task_data['user_id'],
                    platform_connection_id=task_data['platform_connection_id'],
                    settings=CaptionGenerationSettings(max_length=500)
                )
                submitted_tasks.append(task_id)
            except Exception as e:
                submitted_tasks.append(f"ERROR: {e}")
        
        # Start all submission threads
        for task_data in tasks_data:
            thread = threading.Thread(target=submit_task, args=(task_data,))
            threads.append(thread)
            thread.start()
        
        # Wait for all submissions to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify all tasks were submitted successfully
        self.assertEqual(len(submitted_tasks), 5)
        for task_id in submitted_tasks:
            self.assertFalse(task_id.startswith("ERROR"))
        
        # Verify all tasks were enqueued
        self.assertEqual(self.mock_queues['normal'].enqueue.call_count, 5)
    
    def test_priority_queue_processing_order(self):
        """Test that tasks are processed in correct priority order"""
        # Submit tasks with different priorities
        priorities = [TaskPriority.LOW, TaskPriority.URGENT, TaskPriority.NORMAL, TaskPriority.HIGH]
        expected_order = [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]
        
        submitted_tasks = []
        
        for i, priority in enumerate(priorities):
            user_id = i + 1
            
            # Mock user
            mock_user = Mock(spec=User)
            mock_user.id = user_id
            mock_user.role = UserRole.USER
            
            mock_platform = Mock(spec=PlatformConnection)
            mock_platform.id = 1
            
            self.mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                mock_user, mock_platform
            ]
            self.mock_session.query.return_value.filter.return_value.first.return_value = None
            
            # Mock appropriate queue enqueue
            queue_name = priority.value
            mock_job = Mock(spec=Job)
            mock_job.id = f"{priority.value}-job-{i}"
            self.mock_queues[queue_name].enqueue.return_value = mock_job
            
            task_id = self.rq_web_service.start_caption_generation(
                user_id=user_id,
                platform_connection_id=1,
                settings=CaptionGenerationSettings(max_length=500),
                priority=priority
            )
            
            submitted_tasks.append((task_id, priority))
        
        # Verify tasks were enqueued to correct priority queues
        self.mock_queues['urgent'].enqueue.assert_called_once()
        self.mock_queues['high'].enqueue.assert_called_once()
        self.mock_queues['normal'].enqueue.assert_called_once()
        self.mock_queues['low'].enqueue.assert_called_once()
    
    def test_websocket_progress_tracking_integration(self):
        """Test WebSocket progress tracking integration"""
        task_id = "progress-task-123"
        user_id = 1
        
        # Mock WebSocket room management
        self.mock_websocket_manager.join_room.return_value = None
        self.mock_websocket_manager.leave_room.return_value = None
        
        # Test progress tracking lifecycle
        # 1. User connects and joins task room
        self.rq_progress_tracker.join_task_room(user_id, task_id)
        self.mock_websocket_manager.join_room.assert_called_with(f"task_{task_id}")
        
        # 2. Send progress updates
        progress_sequence = [
            (10, "Initializing caption generation"),
            (30, "Downloading images"),
            (60, "Processing with AI model"),
            (90, "Finalizing captions"),
            (100, "Caption generation completed")
        ]
        
        for progress, message in progress_sequence:
            self.rq_progress_tracker.update_task_progress(task_id, progress, message)
        
        # Verify all progress updates were sent
        progress_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                         if 'progress_update' in str(call)]
        self.assertEqual(len(progress_calls), 5)
        
        # 3. Send completion notification
        self.rq_progress_tracker.send_completion_notification(task_id, success=True)
        
        # 4. User leaves task room
        self.rq_progress_tracker.leave_task_room(user_id, task_id)
        self.mock_websocket_manager.leave_room.assert_called_with(f"task_{task_id}")
    
    def test_database_session_management_in_workers(self):
        """Test proper database session management in RQ workers"""
        # Mock worker session manager
        with patch('app.services.task.rq.worker_session_manager.WorkerSessionManager') as mock_session_manager_class:
            mock_session_manager = Mock()
            mock_session_manager_class.return_value = mock_session_manager
            
            # Mock database session
            mock_worker_session = Mock()
            mock_session_manager.get_session.return_value = mock_worker_session
            
            # Test worker processing with session management
            with patch('app.services.task.rq.rq_job_processor.RQJobProcessor') as mock_processor_class:
                mock_processor = Mock()
                mock_processor_class.return_value = mock_processor
                
                # Mock task processing that uses database
                def mock_process_task(task_id):
                    # Simulate database operations
                    session = mock_session_manager.get_session()
                    
                    # Mock task retrieval
                    task = session.query.return_value.filter_by.return_value.first.return_value
                    task.status = TaskStatus.RUNNING
                    session.commit()
                    
                    # Simulate processing
                    time.sleep(0.1)
                    
                    # Update task completion
                    task.status = TaskStatus.COMPLETED
                    session.commit()
                    
                    # Clean up session
                    mock_session_manager.close_session()
                    
                    return {'success': True, 'task_id': task_id}
                
                mock_processor.process_task.side_effect = mock_process_task
                
                # Process task
                result = mock_processor.process_task("session-test-task")
                
                # Verify session management
                mock_session_manager.get_session.assert_called()
                mock_session_manager.close_session.assert_called()
                self.assertTrue(result['success'])
    
    def test_error_handling_and_recovery(self):
        """Test comprehensive error handling and recovery mechanisms"""
        task_id = "error-test-task"
        
        # Test various error scenarios
        error_scenarios = [
            ("Redis connection lost", redis.ConnectionError("Connection failed")),
            ("Database timeout", Exception("Database operation timed out")),
            ("Invalid task data", ValueError("Invalid task configuration")),
            ("Worker crash", RuntimeError("Worker process crashed"))
        ]
        
        for error_description, error_exception in error_scenarios:
            with self.subTest(error=error_description):
                # Mock error occurrence
                with patch('app.services.task.rq.rq_job_processor.RQJobProcessor') as mock_processor_class:
                    mock_processor = Mock()
                    mock_processor.process_task.side_effect = error_exception
                    mock_processor_class.return_value = mock_processor
                    
                    # Test error handling
                    try:
                        mock_processor.process_task(task_id)
                        self.fail(f"Expected {error_description} was not raised")
                    except Exception as e:
                        # Verify error was caught
                        self.assertIsInstance(e, type(error_exception))
                        
                        # Test error reporting
                        self.rq_progress_tracker.handle_task_failure(task_id, e)
                        
                        # Verify error notification was sent
                        error_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                                     if 'task_failed' in str(call) or 'error' in str(call)]
                        self.assertTrue(len(error_calls) > 0)


class TestGunicornIntegration(unittest.TestCase):
    """Test RQ integration with Gunicorn processes"""
    
    def setUp(self):
        """Set up Gunicorn integration test fixtures"""
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_redis = Mock(spec=redis.Redis)
        self.config = RQConfig()
        
        # Mock Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    @patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker')
    def test_worker_startup_with_gunicorn(self, mock_integrated_worker_class):
        """Test RQ worker startup integration with Gunicorn"""
        # Mock integrated workers
        mock_workers = [Mock() for _ in range(2)]
        mock_integrated_worker_class.side_effect = mock_workers
        
        # Initialize worker manager
        worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            {}
        )
        
        # Configure integrated workers
        worker_manager.config.integrated_workers = [
            {'queues': ['urgent', 'high'], 'count': 1},
            {'queues': ['normal', 'low'], 'count': 1}
        ]
        
        # Test worker startup (simulating Gunicorn process start)
        with self.app.app_context():
            worker_manager.start_integrated_workers()
        
        # Verify workers were started
        for mock_worker in mock_workers:
            mock_worker.start.assert_called_once()
        
        # Verify worker coordination
        self.mock_redis.setex.assert_called()
    
    @patch('app.services.task.rq.rq_worker_manager.IntegratedRQWorker')
    def test_worker_coordination_across_gunicorn_processes(self, mock_integrated_worker_class):
        """Test worker coordination across multiple Gunicorn processes"""
        # Simulate multiple Gunicorn workers
        worker_managers = []
        
        for i in range(3):  # 3 Gunicorn processes
            mock_worker = Mock()
            mock_integrated_worker_class.return_value = mock_worker
            
            worker_manager = RQWorkerManager(
                self.mock_db_manager,
                self.mock_redis,
                self.config,
                {}
            )
            
            # Each process registers its workers
            worker_manager.register_worker_coordination()
            worker_managers.append(worker_manager)
        
        # Verify each process registered coordination
        self.assertEqual(self.mock_redis.setex.call_count, 3)
        
        # Test cleanup when processes shut down
        for worker_manager in worker_managers:
            worker_manager.cleanup_worker_coordination()
        
        # Verify cleanup was called for each process
        self.assertEqual(self.mock_redis.delete.call_count, 3)
    
    def test_graceful_shutdown_on_gunicorn_restart(self):
        """Test graceful worker shutdown when Gunicorn restarts"""
        # Mock worker manager with active workers
        worker_manager = RQWorkerManager(
            self.mock_db_manager,
            self.mock_redis,
            self.config,
            {}
        )
        
        # Mock active integrated workers
        mock_workers = [Mock() for _ in range(2)]
        worker_manager.integrated_workers = [
            {'worker': worker, 'worker_id': f'worker-{i}'}
            for i, worker in enumerate(mock_workers)
        ]
        
        # Mock external workers
        mock_processes = [Mock() for _ in range(2)]
        for i, process in enumerate(mock_processes):
            process.poll.return_value = None  # Still running
            process.terminate.return_value = None
            process.wait.return_value = 0
        
        worker_manager.external_workers = [
            {'process': process, 'pid': 1000 + i, 'worker_id': f'external-{i}'}
            for i, process in enumerate(mock_processes)
        ]
        
        # Test graceful shutdown (simulating Gunicorn SIGTERM)
        worker_manager.stop_workers(graceful=True, timeout=30)
        
        # Verify integrated workers were stopped gracefully
        for mock_worker in mock_workers:
            mock_worker.stop.assert_called_with(timeout=30)
        
        # Verify external processes were terminated gracefully
        for mock_process in mock_processes:
            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called_with(timeout=30)


class TestWebSocketProgressIntegration(unittest.TestCase):
    """Test WebSocket progress tracking integration"""
    
    def setUp(self):
        """Set up WebSocket integration test fixtures"""
        self.mock_websocket_manager = Mock()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        
        self.progress_tracker = RQProgressTracker(
            self.mock_websocket_manager,
            self.mock_db_manager
        )
    
    def test_real_time_progress_updates(self):
        """Test real-time progress updates via WebSocket"""
        task_id = "websocket-task-123"
        user_id = 1
        
        # Mock database session for progress persistence
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value = mock_session
        
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        # Test progress update sequence
        progress_updates = [
            (0, "Task started"),
            (25, "Downloading images"),
            (50, "Processing with AI"),
            (75, "Generating captions"),
            (100, "Task completed")
        ]
        
        for progress, message in progress_updates:
            self.progress_tracker.update_task_progress(task_id, progress, message)
            
            # Verify WebSocket emission
            self.mock_websocket_manager.emit.assert_called()
            
            # Verify database persistence
            self.assertEqual(mock_task.progress_percentage, progress)
            self.assertEqual(mock_task.progress_message, message)
            mock_session.commit.assert_called()
    
    def test_progress_persistence_for_reconnection(self):
        """Test progress persistence for user reconnection scenarios"""
        task_id = "reconnect-task-456"
        user_id = 1
        
        # Mock task with existing progress
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value = mock_session
        
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_task.progress_percentage = 60
        mock_task.progress_message = "Processing images"
        mock_task.status = TaskStatus.RUNNING
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        # Test getting current progress (simulating user reconnection)
        current_progress = self.progress_tracker.get_current_progress(task_id)
        
        # Verify current progress is retrieved from database
        self.assertEqual(current_progress['progress'], 60)
        self.assertEqual(current_progress['message'], "Processing images")
        self.assertEqual(current_progress['status'], TaskStatus.RUNNING.value)
    
    def test_multi_user_progress_isolation(self):
        """Test progress update isolation between different users"""
        # Create tasks for different users
        tasks = [
            {'task_id': 'user1-task', 'user_id': 1},
            {'task_id': 'user2-task', 'user_id': 2},
            {'task_id': 'user3-task', 'user_id': 3}
        ]
        
        # Mock database sessions for each task
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value = mock_session
        
        mock_tasks = []
        for task_data in tasks:
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = task_data['task_id']
            mock_task.user_id = task_data['user_id']
            mock_tasks.append(mock_task)
        
        # Mock database queries to return appropriate task
        def mock_query_filter(task_id):
            for mock_task in mock_tasks:
                if mock_task.id == task_id:
                    return mock_task
            return None
        
        mock_session.query.return_value.filter_by.return_value.first.side_effect = lambda: mock_query_filter
        
        # Send progress updates for each user's task
        for i, task_data in enumerate(tasks):
            progress = (i + 1) * 30  # Different progress for each
            message = f"Processing for user {task_data['user_id']}"
            
            self.progress_tracker.update_task_progress(
                task_data['task_id'], 
                progress, 
                message
            )
        
        # Verify WebSocket emissions were made for each task
        self.assertEqual(self.mock_websocket_manager.emit.call_count, 3)
        
        # Verify each emission was to the correct room
        emit_calls = self.mock_websocket_manager.emit.call_args_list
        for i, call in enumerate(emit_calls):
            expected_room = f"task_{tasks[i]['task_id']}"
            self.assertIn(expected_room, str(call))


if __name__ == '__main__':
    unittest.main()