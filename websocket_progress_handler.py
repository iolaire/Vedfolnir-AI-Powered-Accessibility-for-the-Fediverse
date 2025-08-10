# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
WebSocket Progress Handler for Caption Generation

This module provides real-time progress updates to web clients using WebSocket connections.
It handles connection management, user authentication, and progress broadcasting.
"""

import logging
from typing import Dict, Set, Optional
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_login import current_user

from progress_tracker import ProgressTracker, ProgressStatus
from task_queue_manager import TaskQueueManager
from database import DatabaseManager
from models import CaptionGenerationTask
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class WebSocketProgressHandler:
    """Handles WebSocket connections for real-time progress updates"""
    
    def __init__(self, socketio: SocketIO, db_manager: DatabaseManager, 
                 progress_tracker: ProgressTracker, task_queue_manager: TaskQueueManager):
        self.socketio = socketio
        self.db_manager = db_manager
        self.progress_tracker = progress_tracker
        self.task_queue_manager = task_queue_manager
        
        # Track active connections: task_id -> set of session_ids
        self._connections: Dict[str, Set[str]] = {}
        
        # Register SocketIO event handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register SocketIO event handlers with security enhancements"""
        
        # Rate limiting storage
        self._rate_limits = {}
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection with rate limiting"""
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated WebSocket connection attempt from {sanitize_for_log(request.remote_addr)}")
                disconnect()
                return False
            
            # Rate limiting check
            if not self._check_connection_rate_limit():
                logger.warning(f"WebSocket connection rate limit exceeded for user {sanitize_for_log(str(current_user.id))}")
                disconnect()
                return False
            
            logger.info(f"WebSocket connected: user {sanitize_for_log(str(current_user.id))} session {sanitize_for_log(request.sid)}")
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            if current_user.is_authenticated:
                logger.info(f"WebSocket disconnected: user {sanitize_for_log(str(current_user.id))} session {sanitize_for_log(request.sid)}")
                self._cleanup_connection(request.sid)
        
        @self.socketio.on('join_task')
        def handle_join_task(data):
            """Handle client joining a task room with input validation"""
            if not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            # Input validation
            if not isinstance(data, dict):
                emit('error', {'message': 'Invalid data format'})
                return
            
            task_id = data.get('task_id')
            if not task_id or not isinstance(task_id, str):
                emit('error', {'message': 'Task ID required'})
                return
            
            # Validate task ID format (UUID)
            import uuid
            try:
                uuid.UUID(task_id)
            except ValueError:
                emit('error', {'message': 'Invalid task ID format'})
                return
            
            # Verify user has access to this task
            if not self._verify_task_access(task_id, current_user.id):
                emit('error', {'message': 'Access denied to task'})
                return
            
            # Join the task room
            join_room(task_id)
            
            # Track the connection
            if task_id not in self._connections:
                self._connections[task_id] = set()
            self._connections[task_id].add(request.sid)
            
            # Send current progress if available
            progress = self.progress_tracker.get_progress(task_id, current_user.id)
            if progress:
                emit('progress_update', progress.to_dict())
            
            logger.info(f"User {sanitize_for_log(str(current_user.id))} joined task {sanitize_for_log(task_id)} room")
        
        # Add other handlers with similar validation...
    
    def _check_connection_rate_limit(self, limit=10, window_seconds=60):
        """Check WebSocket connection rate limiting"""
        from datetime import datetime, timedelta
        
        user_id = current_user.id
        current_time = datetime.utcnow()
        
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = []
        
        # Clean old entries
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        self._rate_limits[user_id] = [
            timestamp for timestamp in self._rate_limits[user_id]
            if timestamp > cutoff_time
        ]
        
        # Check limit
        if len(self._rate_limits[user_id]) >= limit:
            return False
        
        # Add current connection
        self._rate_limits[user_id].append(current_time)
        return True
        
        @self.socketio.on('leave_task')
        def handle_leave_task(data):
            """Handle client leaving a task room"""
            if not current_user.is_authenticated:
                return
            
            task_id = data.get('task_id')
            if not task_id:
                return
            
            # Leave the task room
            leave_room(task_id)
            
            # Remove from connections tracking
            if task_id in self._connections:
                self._connections[task_id].discard(request.sid)
                if not self._connections[task_id]:
                    del self._connections[task_id]
            
            logger.info(f"User {sanitize_for_log(str(current_user.id))} left task {sanitize_for_log(task_id)} room")
        
        @self.socketio.on('cancel_task')
        def handle_cancel_task(data):
            """Handle task cancellation request"""
            if not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            task_id = data.get('task_id')
            if not task_id:
                emit('error', {'message': 'Task ID required'})
                return
            
            # Cancel the task
            success = self.task_queue_manager.cancel_task(task_id, current_user.id)
            
            if success:
                # Broadcast cancellation to all clients in the task room
                self.socketio.emit('task_cancelled', {
                    'task_id': task_id,
                    'message': 'Task cancelled by user'
                }, room=task_id)
                
                emit('task_cancelled', {'task_id': task_id, 'success': True})
                logger.info(f"Task {sanitize_for_log(task_id)} cancelled by user {sanitize_for_log(str(current_user.id))}")
            else:
                emit('error', {'message': 'Failed to cancel task'})
        
        @self.socketio.on('get_task_status')
        def handle_get_task_status(data):
            """Handle request for current task status"""
            if not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            task_id = data.get('task_id')
            if not task_id:
                emit('error', {'message': 'Task ID required'})
                return
            
            # Verify user has access to this task
            if not self._verify_task_access(task_id, current_user.id):
                emit('error', {'message': 'Access denied to task'})
                return
            
            # Get current progress
            progress = self.progress_tracker.get_progress(task_id, current_user.id)
            if progress:
                emit('progress_update', progress.to_dict())
            else:
                emit('error', {'message': 'Task not found'})
    
    def connect(self, task_id: str, user_id: int) -> bool:
        """
        Connect to progress updates for a task (programmatic interface)
        
        Args:
            task_id: The task ID to monitor
            user_id: The user ID for authorization
            
        Returns:
            bool: True if connection was successful
        """
        # Verify user has access to this task
        if not self._verify_task_access(task_id, user_id):
            return False
        
        # Register progress callback
        callback = self._create_progress_callback(task_id)
        self.progress_tracker.register_callback(task_id, callback)
        
        logger.info(f"Programmatic connection established for task {sanitize_for_log(task_id)}")
        return True
    
    def broadcast_progress(self, task_id: str, progress_data: Dict) -> None:
        """
        Broadcast progress update to all connected clients for a task
        
        Args:
            task_id: The task ID
            progress_data: Progress data to broadcast
        """
        self.socketio.emit('progress_update', progress_data, room=task_id)
        logger.debug(f"Broadcasted progress update for task {sanitize_for_log(task_id)}")
    
    def disconnect(self, task_id: str, user_id: int) -> None:
        """
        Disconnect from progress updates for a task (programmatic interface)
        
        Args:
            task_id: The task ID to stop monitoring
            user_id: The user ID
        """
        # Clean up progress callbacks
        self.progress_tracker.cleanup_callbacks(task_id)
        
        logger.info(f"Programmatic disconnection for task {sanitize_for_log(task_id)}")
    
    def _verify_task_access(self, task_id: str, user_id: int) -> bool:
        """
        Verify that a user has access to a task
        
        Args:
            task_id: The task ID to check
            user_id: The user ID to verify
            
        Returns:
            bool: True if user has access
        """
        session = self.db_manager.get_session()
        try:
            task = session.query(CaptionGenerationTask).filter_by(
                id=task_id,
                user_id=user_id
            ).first()
            
            return task is not None
            
        except Exception as e:
            logger.error(f"Error verifying task access: {sanitize_for_log(str(e))}")
            return False
        finally:
            session.close()
    
    def _cleanup_connection(self, session_id: str) -> None:
        """
        Clean up connection tracking when a client disconnects
        
        Args:
            session_id: The session ID that disconnected
        """
        # Remove session from all task connections
        tasks_to_remove = []
        for task_id, sessions in self._connections.items():
            sessions.discard(session_id)
            if not sessions:
                tasks_to_remove.append(task_id)
        
        # Remove empty task entries
        for task_id in tasks_to_remove:
            del self._connections[task_id]
    
    def _create_progress_callback(self, task_id: str):
        """
        Create a progress callback that broadcasts to WebSocket clients
        
        Args:
            task_id: The task ID to broadcast for
            
        Returns:
            Callable progress callback function
        """
        def progress_callback(progress_status: ProgressStatus):
            """Progress callback that broadcasts via WebSocket"""
            self.broadcast_progress(task_id, progress_status.to_dict())
        
        return progress_callback
    
    def get_active_connections(self) -> Dict[str, int]:
        """
        Get count of active connections per task
        
        Returns:
            Dict mapping task_id to connection count
        """
        return {task_id: len(sessions) for task_id, sessions in self._connections.items()}
    
    def broadcast_task_completion(self, task_id: str, results: Dict) -> None:
        """
        Broadcast task completion to all connected clients
        
        Args:
            task_id: The completed task ID
            results: Task completion results
        """
        self.socketio.emit('task_completed', {
            'task_id': task_id,
            'results': results
        }, room=task_id)
        
        logger.info(f"Broadcasted task completion for {sanitize_for_log(task_id)}")
    
    def broadcast_task_error(self, task_id: str, error_message: str) -> None:
        """
        Broadcast task error to all connected clients
        
        Args:
            task_id: The failed task ID
            error_message: Error message
        """
        self.socketio.emit('task_error', {
            'task_id': task_id,
            'error': error_message
        }, room=task_id)
        
        logger.info(f"Broadcasted task error for {sanitize_for_log(task_id)}: {sanitize_for_log(error_message)}")
    
    def cleanup_task_connections(self, task_id: str) -> None:
        """
        Clean up all connections for a completed task
        
        Args:
            task_id: The task ID to clean up
        """
        if task_id in self._connections:
            # Notify all connected clients that the task is complete
            self.socketio.emit('task_cleanup', {
                'task_id': task_id,
                'message': 'Task monitoring ended'
            }, room=task_id)
            
            # Remove from tracking
            del self._connections[task_id]
            
        # Clean up progress tracker callbacks
        self.progress_tracker.cleanup_callbacks(task_id)
        
        logger.info(f"Cleaned up connections for task {sanitize_for_log(task_id)}")
    
    def get_connection_stats(self) -> Dict[str, any]:
        """
        Get statistics about WebSocket connections
        
        Returns:
            Dict with connection statistics
        """
        total_connections = sum(len(sessions) for sessions in self._connections.values())
        
        return {
            'total_connections': total_connections,
            'active_tasks': len(self._connections),
            'tasks_with_connections': list(self._connections.keys())
        }