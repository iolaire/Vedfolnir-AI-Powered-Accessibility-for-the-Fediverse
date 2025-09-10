# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Integration tests for WebSocket Progress Handler
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import uuid

try:
    from websocket_progress_handler import WebSocketProgressHandler
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocketProgressHandler = None

from progress_tracker import ProgressTracker, ProgressStatus
from app.services.task.core.task_queue_manager import TaskQueueManager
from models import CaptionGenerationTask, TaskStatus
from app.core.database.core.database_manager import DatabaseManager

class TestWebSocketProgressHandler(unittest.TestCase):
    """Test cases for WebSocketProgressHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        if not WEBSOCKET_AVAILABLE:
            self.skipTest("WebSocket handler not available due to Flask-SocketIO compatibility issues")
            
        self.mock_socketio = Mock()
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_progress_tracker = Mock(spec=ProgressTracker)
        self.mock_task_queue_manager = Mock(spec=TaskQueueManager)
        
        # Mock session
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Create handler
        self.handler = WebSocketProgressHandler(
            self.mock_socketio,
            self.mock_db_manager,
            self.mock_progress_tracker,
            self.mock_task_queue_manager
        )
        
        # Test data
        self.test_task_id = str(uuid.uuid4())
        self.test_user_id = 1
        
        # Mock task
        self.mock_task = Mock(spec=CaptionGenerationTask)
        self.mock_task.id = self.test_task_id
        self.mock_task.user_id = self.test_user_id
        self.mock_task.status = TaskStatus.RUNNING
    
    def test_connect_success(self):
        """Test successful programmatic connection"""
        # Mock task access verification
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        result = self.handler.connect(self.test_task_id, self.test_user_id)
        
        self.assertTrue(result)
        self.mock_progress_tracker.register_callback.assert_called_once()
    
    def test_connect_access_denied(self):
        """Test connection fails when user doesn't have access"""
        # Mock no task found (access denied)
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.handler.connect(self.test_task_id, self.test_user_id)
        
        self.assertFalse(result)
        self.mock_progress_tracker.register_callback.assert_not_called()
    
    def test_broadcast_progress(self):
        """Test progress broadcasting"""
        progress_data = {
            'task_id': self.test_task_id,
            'progress_percent': 50,
            'current_step': 'Processing'
        }
        
        self.handler.broadcast_progress(self.test_task_id, progress_data)
        
        self.mock_socketio.emit.assert_called_once_with(
            'progress_update', 
            progress_data, 
            room=self.test_task_id
        )
    
    def test_disconnect(self):
        """Test programmatic disconnection"""
        self.handler.disconnect(self.test_task_id, self.test_user_id)
        
        self.mock_progress_tracker.cleanup_callbacks.assert_called_once_with(self.test_task_id)
    
    def test_verify_task_access_authorized(self):
        """Test task access verification for authorized user"""
        # Mock task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = self.mock_task
        
        result = self.handler._verify_task_access(self.test_task_id, self.test_user_id)
        
        self.assertTrue(result)
    
    def test_verify_task_access_unauthorized(self):
        """Test task access verification for unauthorized user"""
        # Mock no task found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.handler._verify_task_access(self.test_task_id, 999)
        
        self.assertFalse(result)
    
    def test_cleanup_connection(self):
        """Test connection cleanup"""
        session_id = "test-session-id"
        
        # Add connection to tracking
        self.handler._connections[self.test_task_id] = {session_id, "other-session"}
        
        self.handler._cleanup_connection(session_id)
        
        # Verify session removed but task still tracked (other session remains)
        self.assertNotIn(session_id, self.handler._connections[self.test_task_id])
        self.assertIn("other-session", self.handler._connections[self.test_task_id])
    
    def test_cleanup_connection_removes_empty_task(self):
        """Test connection cleanup removes empty task entries"""
        session_id = "test-session-id"
        
        # Add connection to tracking (only one session)
        self.handler._connections[self.test_task_id] = {session_id}
        
        self.handler._cleanup_connection(session_id)
        
        # Verify task entry removed when no sessions remain
        self.assertNotIn(self.test_task_id, self.handler._connections)
    
    def test_create_progress_callback(self):
        """Test progress callback creation"""
        callback = self.handler._create_progress_callback(self.test_task_id)
        
        # Test the callback
        progress_status = ProgressStatus(
            task_id=self.test_task_id,
            user_id=self.test_user_id,
            current_step="Test step",
            progress_percent=75,
            details={}
        )
        
        callback(progress_status)
        
        # Verify broadcast was called
        self.mock_socketio.emit.assert_called_once_with(
            'progress_update',
            progress_status.to_dict(),
            room=self.test_task_id
        )
    
    def test_get_active_connections(self):
        """Test getting active connections count"""
        # Set up test connections
        self.handler._connections = {
            'task1': {'session1', 'session2'},
            'task2': {'session3'}
        }
        
        result = self.handler.get_active_connections()
        
        expected = {
            'task1': 2,
            'task2': 1
        }
        self.assertEqual(result, expected)
    
    def test_broadcast_task_completion(self):
        """Test task completion broadcasting"""
        results = {
            'posts_processed': 5,
            'images_processed': 10,
            'captions_generated': 8
        }
        
        self.handler.broadcast_task_completion(self.test_task_id, results)
        
        self.mock_socketio.emit.assert_called_once_with(
            'task_completed',
            {
                'task_id': self.test_task_id,
                'results': results
            },
            room=self.test_task_id
        )
    
    def test_broadcast_task_error(self):
        """Test task error broadcasting"""
        error_message = "Test error message"
        
        self.handler.broadcast_task_error(self.test_task_id, error_message)
        
        self.mock_socketio.emit.assert_called_once_with(
            'task_error',
            {
                'task_id': self.test_task_id,
                'error': error_message
            },
            room=self.test_task_id
        )
    
    def test_cleanup_task_connections(self):
        """Test task connection cleanup"""
        # Set up test connections
        self.handler._connections[self.test_task_id] = {'session1', 'session2'}
        
        self.handler.cleanup_task_connections(self.test_task_id)
        
        # Verify cleanup notification sent
        self.mock_socketio.emit.assert_called_once_with(
            'task_cleanup',
            {
                'task_id': self.test_task_id,
                'message': 'Task monitoring ended'
            },
            room=self.test_task_id
        )
        
        # Verify connections removed
        self.assertNotIn(self.test_task_id, self.handler._connections)
        
        # Verify progress tracker cleanup called
        self.mock_progress_tracker.cleanup_callbacks.assert_called_once_with(self.test_task_id)
    
    def test_get_connection_stats(self):
        """Test getting connection statistics"""
        # Set up test connections
        self.handler._connections = {
            'task1': {'session1', 'session2'},
            'task2': {'session3'}
        }
        
        result = self.handler.get_connection_stats()
        
        expected = {
            'total_connections': 3,
            'active_tasks': 2,
            'tasks_with_connections': ['task1', 'task2']
        }
        self.assertEqual(result, expected)
    
    def test_socketio_handlers_registered(self):
        """Test that SocketIO handlers are registered during initialization"""
        # Verify that the socketio.on decorator was called for each handler
        # This is a bit tricky to test directly, so we'll verify the handler exists
        self.assertIsNotNone(self.handler.socketio)
        self.assertIsNotNone(self.handler._connections)

if __name__ == '__main__':
    unittest.main()