# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Server-Sent Events (SSE) Progress Handler

This module provides real-time progress updates using Server-Sent Events instead of WebSockets.
SSE is simpler, more reliable, and works better with strict CORS policies.
"""

import json
import time
import logging
from typing import Dict, Set, Optional, Generator
from flask import Response, request, stream_template
from flask_login import current_user, login_required
from threading import Lock
from collections import defaultdict
from datetime import datetime, timedelta

from database import DatabaseManager
from progress_tracker import ProgressTracker
from task_queue_manager import TaskQueueManager
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class SSEProgressHandler:
    """Handles Server-Sent Events for real-time progress updates"""
    
    def __init__(self, db_manager: DatabaseManager, progress_tracker: ProgressTracker, 
                 task_queue_manager: TaskQueueManager):
        self.db_manager = db_manager
        self.progress_tracker = progress_tracker
        self.task_queue_manager = task_queue_manager
        
        # Track active connections per task
        self._connections: Dict[str, Set[str]] = defaultdict(set)
        self._connection_lock = Lock()
        
        # Rate limiting
        self._rate_limits: Dict[str, datetime] = {}
        self._rate_limit_window = timedelta(seconds=1)  # 1 request per second
        
        logger.info("SSE Progress Handler initialized")
    
    def create_event_stream(self, task_id: str) -> Generator[str, None, None]:
        """
        Create a Server-Sent Events stream for a specific task
        
        Args:
            task_id: The task ID to monitor
            
        Yields:
            SSE formatted strings with progress updates
        """
        # Import here to avoid circular imports and ensure Flask context
        from flask_login import current_user
        
        # Authentication is already verified in the endpoint, so current_user should be valid
        user_id = str(getattr(current_user, 'id', 'unknown'))
        connection_id = f"{user_id}_{task_id}_{int(time.time())}"
        
        try:
            # Rate limiting check
            if not self._check_rate_limit(user_id):
                yield f"data: {json.dumps({'type': 'error', 'message': 'Rate limit exceeded'})}\n\n"
                return
            
            # Verify user has access to this task
            current_user_id = getattr(current_user, 'id', None)
            if not current_user_id:
                yield 'data: {"type": "error", "message": "User authentication error"}\n\n'
                return
            task_exists = self._verify_task_access(task_id, current_user_id)
            if not task_exists:
                # Task doesn't exist - send error and close connection
                yield f"data: {json.dumps({'type': 'error', 'message': 'Task not found or access denied'})}\n\n"
                logger.warning(f"User {sanitize_for_log(user_id)} attempted to connect to non-existent task {sanitize_for_log(task_id)}")
                return
            
            # Check if task is actually active
            task_active = self._is_task_active(task_id)
            if not task_active:
                # Task exists but is not active - send completion message and close
                completion_msg = {'type': 'task_completed', 'task_id': task_id, 'message': 'Task already completed'}
                logger.info(f"Sending task completion message to user {sanitize_for_log(user_id)} for task {sanitize_for_log(task_id)}: {completion_msg}")
                yield f"data: {json.dumps(completion_msg)}\n\n"
                logger.info(f"User {sanitize_for_log(user_id)} connected to completed task {sanitize_for_log(task_id)}")
                return
        except Exception as e:
            logger.error(f"Error in SSE stream initialization: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream initialization failed'})}\n\n"
            return
        
        # Register connection
        with self._connection_lock:
            self._connections[task_id].add(connection_id)
        
        logger.info(f"User {sanitize_for_log(user_id)} connected to task {sanitize_for_log(task_id)} via SSE - starting progress monitoring")
        
        try:
            # Send initial connection confirmation
            yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"
            
            # Send current progress if available
            progress = self.progress_tracker.get_progress(task_id, current_user_id)
            if progress:
                logger.debug(f"Sending initial progress for task {sanitize_for_log(task_id)}: {progress.progress_percent}% - {progress.current_step}")
                yield f"data: {json.dumps({'type': 'progress_update', **progress.to_dict()})}\n\n"
            else:
                logger.debug(f"No initial progress data for task {sanitize_for_log(task_id)}")
            
            # Keep connection alive and send updates
            last_update = time.time()
            connection_timeout = 300  # 5 minutes timeout
            start_time = time.time()
            
            while True:
                # Check for connection timeout
                if time.time() - start_time > connection_timeout:
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Connection timeout'})}\n\n"
                    break
                
                # Check if task is still active
                task_active = self._is_task_active(task_id)
                if task_exists and not task_active:
                    yield f"data: {json.dumps({'type': 'task_completed', 'task_id': task_id})}\n\n"
                    break
                
                # Get latest progress
                current_progress = self.progress_tracker.get_progress(task_id, current_user_id)
                if current_progress:
                    progress_data = current_progress.to_dict()
                    progress_data['type'] = 'progress_update'
                    logger.debug(f"Sending progress update for task {sanitize_for_log(task_id)}: {progress_data['progress_percent']}% - {progress_data['current_step']}")
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    last_update = time.time()
                else:
                    logger.debug(f"No progress data available for task {sanitize_for_log(task_id)}")
                
                # Send heartbeat every 30 seconds
                if time.time() - last_update > 30:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': int(time.time())})}\n\n"
                    last_update = time.time()
                
                # Sleep to avoid excessive polling
                time.sleep(1)  # Reduced to 1 second for more responsive updates
                
        except GeneratorExit:
            # Client disconnected
            logger.info(f"User {sanitize_for_log(user_id)} disconnected from task {sanitize_for_log(task_id)}")
        except Exception as e:
            logger.error(f"Error in SSE stream for task {sanitize_for_log(task_id)}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error occurred'})}\n\n"
        finally:
            # Clean up connection
            with self._connection_lock:
                self._connections[task_id].discard(connection_id)
                if not self._connections[task_id]:
                    del self._connections[task_id]
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        now = datetime.now()
        last_request = self._rate_limits.get(user_id)
        
        if last_request and now - last_request < self._rate_limit_window:
            return False
        
        self._rate_limits[user_id] = now
        return True
    
    def _verify_task_access(self, task_id: str, user_id: int) -> bool:
        """Verify user has access to the specified task"""
        try:
            session = self.db_manager.get_session()
            try:
                from models import CaptionGenerationTask
                task = session.query(CaptionGenerationTask).filter_by(
                    id=task_id,
                    user_id=user_id
                ).first()
                return task is not None
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error verifying task access: {e}")
            return False
    
    def _is_task_active(self, task_id: str) -> bool:
        """Check if task is still active/running"""
        try:
            session = self.db_manager.get_session()
            try:
                from models import CaptionGenerationTask, TaskStatus
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                if not task:
                    return False
                return task.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error checking task status: {e}")
            return False
    
    def broadcast_progress_update(self, task_id: str, progress_data: dict):
        """
        Broadcast progress update to all connected clients for a task
        Note: In SSE, clients poll for updates rather than receiving pushes
        """
        # Update the progress tracker - clients will pick this up on their next poll
        logger.debug(f"Progress update available for task {sanitize_for_log(task_id)}")
    
    def broadcast_task_completion(self, task_id: str, results: dict):
        """
        Broadcast task completion to all connected clients
        """
        logger.info(f"Task {sanitize_for_log(task_id)} completed, clients will be notified on next poll")
    
    def broadcast_task_error(self, task_id: str, error_message: str):
        """
        Broadcast task error to all connected clients
        """
        logger.error(f"Task {sanitize_for_log(task_id)} error: {sanitize_for_log(error_message)}")
    
    def cleanup_task_connections(self, task_id: str):
        """Clean up all connections for a completed task"""
        with self._connection_lock:
            if task_id in self._connections:
                connection_count = len(self._connections[task_id])
                del self._connections[task_id]
                logger.info(f"Cleaned up {connection_count} connections for completed task {sanitize_for_log(task_id)}")
    
    def get_connection_count(self, task_id: str) -> int:
        """Get number of active connections for a task"""
        with self._connection_lock:
            return len(self._connections.get(task_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        with self._connection_lock:
            return sum(len(connections) for connections in self._connections.values())