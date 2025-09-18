# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for RQ WebSocket Progress Tracking

Tests WebSocket integration with RQ task processing, real-time progress updates,
multi-user session management, and reconnection handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import time
import threading
from datetime import datetime, timezone
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room

from app.core.database.core.database_manager import DatabaseManager
from app.services.task.rq.rq_progress_tracker import RQProgressTracker
from app.websocket.progress.progress_websocket_handler import ProgressWebSocketHandler
from app.websocket.core.websocket_manager import WebSocketManager
from models import CaptionGenerationTask, TaskStatus, User


class TestRQWebSocketIntegration(unittest.TestCase):
    """Test RQ WebSocket progress tracking integration"""
    
    def setUp(self):
        """Set up WebSocket integration test fixtures"""
        # Create Flask app with SocketIO
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        # Mock SocketIO
        self.mock_socketio = Mock(spec=SocketIO)
        
        # Mock dependencies
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Mock WebSocket manager
        self.mock_websocket_manager = Mock(spec=WebSocketManager)
        
        # Initialize components
        self.progress_tracker = RQProgressTracker(
            self.mock_websocket_manager,
            self.mock_db_manager
        )
        
        self.websocket_handler = ProgressWebSocketHandler(
            self.mock_socketio,
            self.progress_tracker
        )
    
    def test_task_progress_websocket_flow(self):
        """Test complete task progress WebSocket flow"""
        task_id = "websocket-flow-task-123"
        user_id = 1
        
        # Mock task in database
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_task.status = TaskStatus.RUNNING
        mock_task.progress_percentage = 0
        mock_task.progress_message = "Starting task"
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        # Step 1: User connects and joins task room
        with self.app.test_request_context():
            # Mock session data
            session_data = {'user_id': user_id}
            
            with patch('flask.session', session_data):
                # Test joining task room
                self.websocket_handler.join_task_room(task_id)
                
                # Verify room join
                expected_room = f"task_{task_id}"
                self.mock_websocket_manager.join_room.assert_called_with(expected_room)
        
        # Step 2: Send progress updates
        progress_sequence = [
            (10, "Initializing"),
            (25, "Downloading images"),
            (50, "Processing with AI"),
            (75, "Generating captions"),
            (90, "Finalizing"),
            (100, "Completed")
        ]
        
        for progress, message in progress_sequence:
            # Update progress
            self.progress_tracker.update_task_progress(task_id, progress, message)
            
            # Verify database update
            self.assertEqual(mock_task.progress_percentage, progress)
            self.assertEqual(mock_task.progress_message, message)
            self.mock_session.commit.assert_called()
            
            # Verify WebSocket emission
            self.mock_websocket_manager.emit.assert_called()
            
            # Get the last emit call
            last_emit_call = self.mock_websocket_manager.emit.call_args_list[-1]
            emit_args, emit_kwargs = last_emit_call
            
            # Verify emit parameters
            self.assertEqual(emit_args[0], 'progress_update')  # Event name
            self.assertIn('progress', emit_args[1])  # Data contains progress
            self.assertEqual(emit_args[1]['progress'], progress)
            self.assertEqual(emit_args[1]['message'], message)
            self.assertIn('room', emit_kwargs)  # Room specified
            self.assertEqual(emit_kwargs['room'], f"task_{task_id}")
        
        # Step 3: Send completion notification
        self.progress_tracker.send_completion_notification(task_id, success=True)
        
        # Verify completion emission
        completion_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                          if 'task_completed' in str(call)]
        self.assertTrue(len(completion_calls) > 0)
        
        # Step 4: User leaves task room
        with self.app.test_request_context():
            with patch('flask.session', session_data):
                self.websocket_handler.leave_task_room(task_id)
                
                # Verify room leave
                self.mock_websocket_manager.leave_room.assert_called_with(f"task_{task_id}")
    
    def test_multi_user_progress_isolation(self):
        """Test progress update isolation between multiple users"""
        # Create tasks for different users
        tasks = [
            {'task_id': 'user1-task', 'user_id': 1},
            {'task_id': 'user2-task', 'user_id': 2},
            {'task_id': 'user3-task', 'user_id': 3}
        ]
        
        # Mock tasks in database
        mock_tasks = {}
        for task_data in tasks:
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = task_data['task_id']
            mock_task.user_id = task_data['user_id']
            mock_task.status = TaskStatus.RUNNING
            mock_task.progress_percentage = 0
            mock_task.progress_message = "Starting"
            mock_tasks[task_data['task_id']] = mock_task
        
        # Mock database query to return appropriate task
        def mock_query_side_effect(*args, **kwargs):
            mock_query = Mock()
            def mock_filter_by(**filter_kwargs):
                task_id = filter_kwargs.get('id')
                mock_filter = Mock()
                mock_filter.first.return_value = mock_tasks.get(task_id)
                return mock_filter
            mock_query.filter_by = mock_filter_by
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # Simulate users joining their respective task rooms
        with self.app.test_request_context():
            for task_data in tasks:
                session_data = {'user_id': task_data['user_id']}
                with patch('flask.session', session_data):
                    self.websocket_handler.join_task_room(task_data['task_id'])
        
        # Send different progress updates for each task
        for i, task_data in enumerate(tasks):
            progress = (i + 1) * 30  # 30%, 60%, 90%
            message = f"Processing for user {task_data['user_id']}"
            
            self.progress_tracker.update_task_progress(
                task_data['task_id'], 
                progress, 
                message
            )
        
        # Verify each task received its own progress update
        emit_calls = self.mock_websocket_manager.emit.call_args_list
        
        # Should have 3 progress updates (one per task)
        progress_calls = [call for call in emit_calls if 'progress_update' in str(call)]
        self.assertEqual(len(progress_calls), 3)
        
        # Verify each update went to the correct room
        for i, call in enumerate(progress_calls):
            emit_args, emit_kwargs = call
            expected_room = f"task_{tasks[i]['task_id']}"
            self.assertEqual(emit_kwargs['room'], expected_room)
            
            # Verify progress data
            progress_data = emit_args[1]
            expected_progress = (i + 1) * 30
            self.assertEqual(progress_data['progress'], expected_progress)
    
    def test_user_reconnection_handling(self):
        """Test handling of user reconnection scenarios"""
        task_id = "reconnection-task-456"
        user_id = 1
        
        # Mock task with existing progress
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_task.status = TaskStatus.RUNNING
        mock_task.progress_percentage = 65
        mock_task.progress_message = "Processing images"
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.started_at = datetime.now(timezone.utc)
        
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        # Test user reconnection
        with self.app.test_request_context():
            session_data = {'user_id': user_id}
            with patch('flask.session', session_data):
                # User reconnects and requests current progress
                current_progress = self.websocket_handler.get_current_task_progress(task_id)
                
                # Verify current progress is retrieved from database
                self.assertEqual(current_progress['progress'], 65)
                self.assertEqual(current_progress['message'], "Processing images")
                self.assertEqual(current_progress['status'], TaskStatus.RUNNING.value)
                self.assertIn('task_id', current_progress)
                self.assertIn('created_at', current_progress)
                
                # User rejoins task room
                self.websocket_handler.join_task_room(task_id)
                
                # Verify room join and current progress emission
                self.mock_websocket_manager.join_room.assert_called_with(f"task_{task_id}")
                
                # Should emit current progress to newly connected user
                self.mock_websocket_manager.emit.assert_called()
                last_emit = self.mock_websocket_manager.emit.call_args_list[-1]
                emit_args, emit_kwargs = last_emit
                
                self.assertEqual(emit_args[0], 'current_progress')
                self.assertEqual(emit_args[1]['progress'], 65)
                self.assertEqual(emit_kwargs['room'], f"task_{task_id}")
    
    def test_websocket_error_handling(self):
        """Test WebSocket error handling scenarios"""
        task_id = "error-task-789"
        user_id = 1
        
        # Test database connection error
        self.mock_session.query.side_effect = Exception("Database connection lost")
        
        # Test progress update with database error
        try:
            self.progress_tracker.update_task_progress(task_id, 50, "Processing")
        except Exception:
            pass  # Should handle gracefully
        
        # Verify error was handled and WebSocket error was emitted
        error_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                      if 'error' in str(call) or 'task_error' in str(call)]
        self.assertTrue(len(error_calls) > 0)
        
        # Test WebSocket connection error
        self.mock_websocket_manager.emit.side_effect = Exception("WebSocket connection failed")
        
        # Reset database mock
        self.mock_session.query.side_effect = None
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        # Test progress update with WebSocket error
        try:
            self.progress_tracker.update_task_progress(task_id, 75, "Almost done")
        except Exception:
            pass  # Should handle gracefully
        
        # Verify database was still updated despite WebSocket error
        self.assertEqual(mock_task.progress_percentage, 75)
        self.assertEqual(mock_task.progress_message, "Almost done")
    
    def test_concurrent_websocket_operations(self):
        """Test concurrent WebSocket operations"""
        # Create multiple tasks
        task_ids = [f"concurrent-task-{i}" for i in range(5)]
        
        # Mock tasks
        mock_tasks = {}
        for task_id in task_ids:
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = task_id
            mock_task.user_id = 1
            mock_task.status = TaskStatus.RUNNING
            mock_task.progress_percentage = 0
            mock_task.progress_message = "Starting"
            mock_tasks[task_id] = mock_task
        
        # Mock database query
        def mock_query_side_effect(*args, **kwargs):
            mock_query = Mock()
            def mock_filter_by(**filter_kwargs):
                task_id = filter_kwargs.get('id')
                mock_filter = Mock()
                mock_filter.first.return_value = mock_tasks.get(task_id)
                return mock_filter
            mock_query.filter_by = mock_filter_by
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # Test concurrent progress updates
        threads = []
        results = []
        
        def update_progress(task_id, progress):
            try:
                self.progress_tracker.update_task_progress(task_id, progress, f"Progress {progress}")
                results.append(f"Success: {task_id}")
            except Exception as e:
                results.append(f"Error: {task_id} - {e}")
        
        # Start concurrent updates
        for i, task_id in enumerate(task_ids):
            thread = threading.Thread(target=update_progress, args=(task_id, (i + 1) * 20))
            threads.append(thread)
            thread.start()
        
        # Wait for all updates to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify all updates succeeded
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertTrue(result.startswith("Success"))
        
        # Verify WebSocket emissions
        progress_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                         if 'progress_update' in str(call)]
        self.assertEqual(len(progress_calls), 5)
    
    def test_websocket_room_management(self):
        """Test WebSocket room management for task isolation"""
        # Test multiple users with different tasks
        users_tasks = [
            {'user_id': 1, 'task_id': 'user1-task-a'},
            {'user_id': 1, 'task_id': 'user1-task-b'},  # Same user, different task
            {'user_id': 2, 'task_id': 'user2-task-a'},
            {'user_id': 3, 'task_id': 'user3-task-a'}
        ]
        
        # Test joining rooms
        with self.app.test_request_context():
            for user_task in users_tasks:
                session_data = {'user_id': user_task['user_id']}
                with patch('flask.session', session_data):
                    self.websocket_handler.join_task_room(user_task['task_id'])
        
        # Verify all rooms were joined
        join_calls = self.mock_websocket_manager.join_room.call_args_list
        self.assertEqual(len(join_calls), 4)
        
        # Verify correct room names
        expected_rooms = [f"task_{ut['task_id']}" for ut in users_tasks]
        actual_rooms = [call[0][0] for call in join_calls]
        self.assertEqual(set(actual_rooms), set(expected_rooms))
        
        # Test leaving rooms
        with self.app.test_request_context():
            for user_task in users_tasks:
                session_data = {'user_id': user_task['user_id']}
                with patch('flask.session', session_data):
                    self.websocket_handler.leave_task_room(user_task['task_id'])
        
        # Verify all rooms were left
        leave_calls = self.mock_websocket_manager.leave_room.call_args_list
        self.assertEqual(len(leave_calls), 4)
    
    def test_websocket_authentication_and_authorization(self):
        """Test WebSocket authentication and authorization"""
        task_id = "auth-task-123"
        
        # Test unauthorized access (no session)
        with self.app.test_request_context():
            with patch('flask.session', {}):  # No user_id in session
                # Should handle unauthorized access gracefully
                try:
                    self.websocket_handler.join_task_room(task_id)
                except Exception:
                    pass  # Expected to handle gracefully
                
                # Verify no room join occurred
                self.mock_websocket_manager.join_room.assert_not_called()
        
        # Test authorized access
        user_id = 1
        mock_task = Mock(spec=CaptionGenerationTask)
        mock_task.id = task_id
        mock_task.user_id = user_id
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_task
        
        with self.app.test_request_context():
            session_data = {'user_id': user_id}
            with patch('flask.session', session_data):
                # Should allow access to own task
                self.websocket_handler.join_task_room(task_id)
                
                # Verify room join occurred
                self.mock_websocket_manager.join_room.assert_called_with(f"task_{task_id}")
        
        # Test unauthorized access to another user's task
        other_user_id = 2
        with self.app.test_request_context():
            session_data = {'user_id': other_user_id}
            with patch('flask.session', session_data):
                # Should deny access to other user's task
                try:
                    self.websocket_handler.join_task_room(task_id)
                except Exception:
                    pass  # Expected to handle gracefully
                
                # Should not join room for unauthorized task
                # (join_room was called once above, should not be called again)
                self.assertEqual(self.mock_websocket_manager.join_room.call_count, 1)
    
    def test_websocket_performance_under_load(self):
        """Test WebSocket performance under high load"""
        # Create many concurrent tasks
        num_tasks = 50
        task_ids = [f"load-task-{i}" for i in range(num_tasks)]
        
        # Mock tasks
        mock_tasks = {}
        for i, task_id in enumerate(task_ids):
            mock_task = Mock(spec=CaptionGenerationTask)
            mock_task.id = task_id
            mock_task.user_id = i % 10  # 10 different users
            mock_task.status = TaskStatus.RUNNING
            mock_task.progress_percentage = 0
            mock_task.progress_message = "Starting"
            mock_tasks[task_id] = mock_task
        
        # Mock database query
        def mock_query_side_effect(*args, **kwargs):
            mock_query = Mock()
            def mock_filter_by(**filter_kwargs):
                task_id = filter_kwargs.get('id')
                mock_filter = Mock()
                mock_filter.first.return_value = mock_tasks.get(task_id)
                return mock_filter
            mock_query.filter_by = mock_filter_by
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        # Measure performance of rapid progress updates
        start_time = time.time()
        
        # Send rapid progress updates
        for i, task_id in enumerate(task_ids):
            progress = (i % 10) * 10  # 0-90% progress
            self.progress_tracker.update_task_progress(task_id, progress, f"Update {i}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance (should complete within reasonable time)
        self.assertLess(total_time, 5.0)  # Should complete within 5 seconds
        
        # Verify all updates were processed
        progress_calls = [call for call in self.mock_websocket_manager.emit.call_args_list 
                         if 'progress_update' in str(call)]
        self.assertEqual(len(progress_calls), num_tasks)
        
        # Calculate average time per update
        avg_time_per_update = total_time / num_tasks
        self.assertLess(avg_time_per_update, 0.1)  # Less than 100ms per update


if __name__ == '__main__':
    unittest.main()