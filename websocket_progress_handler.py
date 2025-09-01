# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Progress Handler

This module provides real-time progress updates using Flask-SocketIO WebSockets.
Replaces the Server-Sent Events (SSE) implementation for better real-time communication.
"""

import json
import logging
from typing import Dict, Set, Optional
from flask import request, current_app, session
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_login import current_user, login_user
from threading import Lock
from collections import defaultdict
from datetime import datetime, timedelta

from database import DatabaseManager
from progress_tracker import ProgressTracker
from task_queue_manager import TaskQueueManager
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
        
        # Track active connections per task
        self._connections: Dict[str, Set[str]] = defaultdict(set)
        self._connection_lock = Lock()
        
        # Rate limiting
        self._rate_limits: Dict[str, datetime] = {}
        self._rate_limit_window = timedelta(seconds=1)  # 1 request per second
        
        # Namespace manager (will be set by web_app.py)
        self._namespace_manager = None
        
        # Register SocketIO event handlers (legacy mode)
        self._register_handlers()
        
        logger.info("WebSocket Progress Handler initialized")
    
    def set_namespace_manager(self, namespace_manager):
        """
        Set the namespace manager for integration with new WebSocket system
        
        Args:
            namespace_manager: WebSocketNamespaceManager instance
        """
        self._namespace_manager = namespace_manager
        logger.info("WebSocket Progress Handler integrated with namespace manager")
    
    def _register_handlers(self):
        """Register SocketIO event handlers with security enhancements"""
        
        # Rate limiting storage
        self._rate_limits = {}
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection with rate limiting"""
            # Log detailed connection information
            from flask import request
            origin = request.headers.get('Origin')
            user_agent = request.headers.get('User-Agent', 'Unknown')
            referer = request.headers.get('Referer')
            
            logger.info(f"🔌 WebSocket connection attempt (Progress Handler):")
            logger.info(f"  - Origin: {origin}")
            logger.info(f"  - User-Agent: {user_agent[:100]}..." if user_agent and len(user_agent) > 100 else f"  - User-Agent: {user_agent}")
            logger.info(f"  - Referer: {referer}")
            logger.info(f"  - Remote Address: {sanitize_for_log(request.remote_addr)}")
            logger.info(f"  - Namespace: Default (/)")
            
            # Allow connection initially, authentication will be checked on specific events
            logger.info(f"WebSocket connection attempt from {sanitize_for_log(request.remote_addr)}")
            
            # Attempt to load user from session cookie
            user_id = None
            try:
                # Flask-SocketIO provides access to Flask's session
                if 'user_id' in session:
                    user_id = session['user_id']
                    logger.debug(f"User ID found in Flask session: {user_id}")
                    
                    # Load user using the unified_session_manager
                    unified_session_manager = current_app.unified_session_manager
                    if unified_session_manager:
                        user = unified_session_manager.get_user_by_id(user_id)
                        if user:
                            login_user(user) # Log in the user for Flask-Login context
                            logger.info(f"User {sanitize_for_log(str(user.id))} authenticated via WebSocket session")
                            
                            # Rate limiting check for authenticated users
                            if not self._check_rate_limit(str(user.id)):
                                logger.warning(f"Rate limit exceeded for user {sanitize_for_log(str(user.id))}")
                                emit('error', {'message': 'Rate limit exceeded'})
                                disconnect()
                                return False
                            
                            emit('connected', {'message': 'Connected successfully'})
                            return True
                        else:
                            logger.warning(f"User {sanitize_for_log(str(user_id))} not found in DB for WebSocket session")
                    else:
                        logger.warning("unified_session_manager not available in current_app for WebSocket auth")
                else:
                    logger.debug("No user_id found in Flask session for WebSocket connection")
            except Exception as e:
                logger.error(f"Error during WebSocket authentication: {e}", exc_info=True)
            
            # If authentication failed or user not found
            logger.info(f"Unauthenticated WebSocket connection from {sanitize_for_log(request.remote_addr)} - will require auth for specific events")
            emit('connected', {'message': 'Connected - authentication required for protected events'})
            
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect(auth=None):
            """Handle client disconnection"""
            if current_user and current_user.is_authenticated:
                user_id = str(current_user.id)
                logger.info(f"User {sanitize_for_log(user_id)} disconnected from WebSocket")
                self._cleanup_connection(request.sid)
        
        @self.socketio.on('join_task')
        def handle_join_task(data):
            """Handle client joining a task room with input validation"""
            if not current_user or not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            # Input validation
            if not isinstance(data, dict) or 'task_id' not in data:
                emit('error', {'message': 'Invalid request format'})
                return
            
            task_id = str(data['task_id']).strip()
            if not task_id or len(task_id) > 100:  # Reasonable task ID length limit
                emit('error', {'message': 'Invalid task ID'})
                return
            
            user_id = current_user.id
            
            # Verify user has access to this task
            if not self._verify_task_access(task_id, user_id):
                emit('error', {'message': 'Task not found or access denied'})
                logger.warning(f"User {sanitize_for_log(str(user_id))} attempted to join unauthorized task {sanitize_for_log(task_id)}")
                return
            
            # Join the task room
            join_room(task_id)
            
            # Track connection
            with self._connection_lock:
                self._connections[task_id].add(request.sid)
            
            logger.info(f"User {sanitize_for_log(str(user_id))} joined task {sanitize_for_log(task_id)} room")
            
            # Send current progress if available
            progress = self.progress_tracker.get_progress(task_id, user_id)
            if progress:
                emit('progress_update', progress.to_dict())
            else:
                # Check if task is completed
                if not self._is_task_active(task_id):
                    emit('task_completed', {'task_id': task_id, 'message': 'Task already completed'})
        
        return True
        
        @self.socketio.on('leave_task')
        def handle_leave_task(data):
            """Handle client leaving a task room"""
            if not current_user or not current_user.is_authenticated:
                return
            
            if not isinstance(data, dict) or 'task_id' not in data:
                return
            
            task_id = str(data['task_id']).strip()
            user_id = current_user.id
            
            # Leave the task room
            leave_room(task_id)
            
            # Remove from tracking
            with self._connection_lock:
                self._connections[task_id].discard(request.sid)
                if not self._connections[task_id]:
                    del self._connections[task_id]
            
            logger.info(f"User {sanitize_for_log(str(user_id))} left task {sanitize_for_log(task_id)} room")
        
        @self.socketio.on('cancel_task')
        def handle_cancel_task(data):
            """Handle task cancellation request"""
            if not current_user or not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            if not isinstance(data, dict) or 'task_id' not in data:
                emit('error', {'message': 'Invalid request format'})
                return
            
            task_id = str(data['task_id']).strip()
            user_id = current_user.id
            
            # Verify user has access to cancel this task
            if not self._verify_task_access(task_id, user_id):
                emit('error', {'message': 'Task not found or access denied'})
                return
            
            # Cancel the task
            success = self.task_queue_manager.cancel_task(task_id, user_id)
            
            if success:
                # Broadcast cancellation to all clients in the task room
                self.socketio.emit('task_cancelled', {
                    'task_id': task_id,
                    'message': 'Task cancelled by user'
                }, room=task_id)
                
                emit('task_cancelled', {'task_id': task_id, 'message': 'Task cancelled successfully'})
            else:
                emit('error', {'message': 'Failed to cancel task'})
        
        @self.socketio.on('get_task_status')
        def handle_get_task_status(data):
            """Handle request for current task status"""
            if not current_user or not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            if not isinstance(data, dict) or 'task_id' not in data:
                emit('error', {'message': 'Invalid request format'})
                return
            
            task_id = str(data['task_id']).strip()
            user_id = current_user.id
            
            # Verify access
            if not self._verify_task_access(task_id, user_id):
                emit('error', {'message': 'Task not found or access denied'})
                return
            
            # Get current progress
            progress = self.progress_tracker.get_progress(task_id, user_id)
            if progress:
                emit('progress_update', progress.to_dict())
            else:
                # Check if task is completed
                if not self._is_task_active(task_id):
                    emit('task_completed', {'task_id': task_id, 'message': 'Task completed'})
                else:
                    emit('task_status', {'task_id': task_id, 'status': 'no_progress_data'})
    
    def broadcast_progress_update(self, task_id: str, progress_data: dict):
        """
        Broadcast progress update to all connected clients for a task
        
        Args:
            task_id: Task ID to broadcast to
            progress_data: Progress data to broadcast
        """
        if self._namespace_manager:
            # Use new namespace system for broadcasting
            self._namespace_manager.broadcast_to_room(
                f"task_{task_id}", 'progress_update', progress_data
            )
        else:
            # Fallback to legacy broadcasting
            self.socketio.emit('progress_update', progress_data, room=task_id)
        
        logger.debug(f"Broadcasted progress update for task {sanitize_for_log(task_id)}")
    
    def broadcast_task_completion(self, task_id: str, results: dict):
        """
        Broadcast task completion to all connected clients
        
        Args:
            task_id: Task ID that completed
            results: Task completion results
        """
        completion_data = {
            'task_id': task_id,
            'results': results
        }
        
        if self._namespace_manager:
            # Use new namespace system for broadcasting
            self._namespace_manager.broadcast_to_room(
                f"task_{task_id}", 'task_completed', completion_data
            )
        else:
            # Fallback to legacy broadcasting
            self.socketio.emit('task_completed', completion_data, room=task_id)
        
        logger.info(f"Broadcasted task completion for task {sanitize_for_log(task_id)}")
        
        # Clean up connections for this task
        self.cleanup_task_connections(task_id)
    
    def broadcast_task_error(self, task_id: str, error_message: str):
        """
        Broadcast task error to all connected clients
        
        Args:
            task_id: Task ID that failed
            error_message: Error message
        """
        error_data = {
            'task_id': task_id,
            'error': error_message
        }
        
        if self._namespace_manager:
            # Use new namespace system for broadcasting
            self._namespace_manager.broadcast_to_room(
                f"task_{task_id}", 'task_error', error_data
            )
        else:
            # Fallback to legacy broadcasting
            self.socketio.emit('task_error', error_data, room=task_id)
        
        logger.error(f"Broadcasted task error for task {sanitize_for_log(task_id)}: {sanitize_for_log(error_message)}")
    
    def cleanup_task_connections(self, task_id: str):
        """Clean up all connections for a completed task"""
        with self._connection_lock:
            if task_id in self._connections:
                # Notify all connected clients that the task is complete
                self.socketio.emit('task_cleanup', {
                    'task_id': task_id,
                    'message': 'Task monitoring ended'
                }, room=task_id)
                
                connection_count = len(self._connections[task_id])
                del self._connections[task_id]
                logger.info(f"Cleaned up {connection_count} connections for completed task {sanitize_for_log(task_id)}")
    
    def _cleanup_connection(self, session_id: str):
        """Clean up a specific connection"""
        with self._connection_lock:
            for task_id, connections in list(self._connections.items()):
                connections.discard(session_id)
                if not connections:
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
            with self.db_manager.get_session() as session:
                from models import CaptionGenerationTask
                task = session.query(CaptionGenerationTask).filter_by(
                    id=task_id,
                    user_id=user_id
                ).first()
                return task is not None
        except Exception as e:
            logger.error(f"Error verifying task access: {e}")
            return False
    
    def _is_task_active(self, task_id: str) -> bool:
        """Check if task is still active/running"""
        try:
            with self.db_manager.get_session() as session:
                from models import CaptionGenerationTask, TaskStatus
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                if not task:
                    return False
                return task.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]
        except Exception as e:
            logger.error(f"Error checking task status: {e}")
            return False
    
    def get_connection_count(self, task_id: str) -> int:
        """Get number of active connections for a task"""
        with self._connection_lock:
            return len(self._connections.get(task_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        with self._connection_lock:
            return sum(len(connections) for connections in self._connections.values())

class AdminDashboardWebSocket:
    """WebSocket handler for admin dashboard real-time updates"""
    
    def __init__(self, socketio: SocketIO, db_manager: DatabaseManager):
        self.socketio = socketio
        self.db_manager = db_manager
        self.connected_admins = set()
        
        # Namespace manager (will be set by web_app.py)
        self._namespace_manager = None
        
        # Register admin-specific handlers
        self._register_admin_handlers()
        
        logger.info("Admin Dashboard WebSocket handler initialized")
    
    def set_namespace_manager(self, namespace_manager):
        """
        Set the namespace manager for integration with new WebSocket system
        
        Args:
            namespace_manager: WebSocketNamespaceManager instance
        """
        self._namespace_manager = namespace_manager
        logger.info("Admin Dashboard WebSocket handler integrated with namespace manager")
    
    def _register_admin_handlers(self):
        """Register admin-specific WebSocket handlers"""
        
        @self.socketio.on('join_admin_dashboard')
        def handle_join_admin_dashboard():
            """Handle admin joining dashboard room"""
            if not current_user or not current_user.is_authenticated:
                emit('error', {'message': 'Authentication required'})
                return
            
            from models import UserRole
            if current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Admin access required'})
                return
            
            # Join admin dashboard room
            join_room('admin_dashboard')
            self.connected_admins.add(request.sid)
            
            logger.info(f"Admin user {sanitize_for_log(str(current_user.id))} joined dashboard")
            emit('admin_dashboard_joined', {'message': 'Connected to admin dashboard'})
        
        @self.socketio.on('leave_admin_dashboard')
        def handle_leave_admin_dashboard():
            """Handle admin leaving dashboard room"""
            leave_room('admin_dashboard')
            self.connected_admins.discard(request.sid)
            
            if current_user and current_user.is_authenticated:
                logger.info(f"Admin user {sanitize_for_log(str(current_user.id))} left dashboard")
    
    def broadcast_system_metrics(self, metrics: dict):
        """Broadcast system metrics to admin dashboard"""
        metrics_data = {
            'type': 'system_metrics',
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self._namespace_manager:
            # Use new namespace system for admin broadcasting
            from models import UserRole
            self._namespace_manager.broadcast_to_namespace(
                '/admin', 'system_metrics_update', metrics_data, role_filter=UserRole.ADMIN
            )
        else:
            # Fallback to legacy broadcasting
            self.socketio.emit('system_metrics_update', metrics_data, room='admin_dashboard')
    
    def broadcast_job_update(self, job_data: dict):
        """Broadcast job update to admin dashboard"""
        job_update_data = {
            'type': 'job_update',
            'job': job_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self._namespace_manager:
            # Use new namespace system for admin broadcasting
            from models import UserRole
            self._namespace_manager.broadcast_to_namespace(
                '/admin', 'job_update', job_update_data, role_filter=UserRole.ADMIN
            )
        else:
            # Fallback to legacy broadcasting
            self.socketio.emit('job_update', job_update_data, room='admin_dashboard')
    
    def broadcast_alert(self, alert_data: dict):
        """Broadcast alert to admin dashboard"""
        alert_broadcast_data = {
            'type': 'alert',
            'alert': alert_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self._namespace_manager:
            # Use new namespace system for admin broadcasting
            from models import UserRole
            self._namespace_manager.broadcast_to_namespace(
                '/admin', 'admin_alert', alert_broadcast_data, role_filter=UserRole.ADMIN
            )
        else:
            # Fallback to legacy broadcasting
            self.socketio.emit('admin_alert', alert_broadcast_data, room='admin_dashboard')
    
    def get_connected_admin_count(self) -> int:
        """Get number of connected admin users"""
        return len(self.connected_admins)