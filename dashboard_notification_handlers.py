# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Dashboard Notification Handlers

WebSocket event handlers for user dashboard real-time notifications.
Integrates with the unified notification system to provide real-time updates
for caption processing, platform operations, and system status.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import current_app
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user

from unified_notification_manager import UnifiedNotificationManager, NotificationMessage, NotificationType, NotificationPriority, NotificationCategory
from models import ProcessingStatus, UserRole

logger = logging.getLogger(__name__)


class DashboardNotificationHandlers:
    """
    WebSocket event handlers for user dashboard notifications
    
    Provides real-time notification delivery for:
    - Caption processing progress and status updates
    - Platform operation status messages and errors
    - System maintenance and status notifications
    - User activity and statistics updates
    """
    
    def __init__(self, socketio, notification_manager: UnifiedNotificationManager):
        """
        Initialize dashboard notification handlers
        
        Args:
            socketio: SocketIO instance
            notification_manager: Unified notification manager
        """
        self.socketio = socketio
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
        
        # Register event handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register WebSocket event handlers for dashboard notifications"""
        
        @self.socketio.on('connect', namespace='/')
        def handle_dashboard_connect(auth):
            """Handle user dashboard WebSocket connection"""
            try:
                if not current_user.is_authenticated:
                    self.logger.warning("Unauthenticated user attempted dashboard WebSocket connection")
                    return False
                
                user_id = current_user.id
                session_id = auth.get('session_id') if auth else None
                
                # Join user-specific room for targeted notifications
                join_room(f'user_{user_id}')
                
                # Join dashboard-specific room
                join_room('dashboard_users')
                
                # Replay any pending notifications for the user
                pending_count = self.notification_manager.replay_messages_for_user(user_id)
                
                self.logger.info(f"User {user_id} connected to dashboard WebSocket, replayed {pending_count} messages")
                
                # Send connection confirmation
                emit('dashboard_connected', {
                    'status': 'connected',
                    'user_id': user_id,
                    'pending_messages': pending_count,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                return True
                
            except Exception as e:
                self.logger.error(f"Error handling dashboard WebSocket connection: {e}")
                return False
        
        @self.socketio.on('disconnect', namespace='/')
        def handle_dashboard_disconnect(sid=None):
            """Handle user dashboard WebSocket disconnection"""
            try:
                if current_user.is_authenticated:
                    user_id = current_user.id
                    
                    # Leave user-specific room
                    leave_room(f'user_{user_id}')
                    leave_room('dashboard_users')
                    
                    self.logger.info(f"User {user_id} disconnected from dashboard WebSocket")
                
            except Exception as e:
                self.logger.error(f"Error handling dashboard WebSocket disconnection: {e}")
        
        @self.socketio.on('request_stats_update', namespace='/')
        def handle_stats_update_request():
            """Handle request for dashboard statistics update"""
            try:
                if not current_user.is_authenticated:
                    return
                
                user_id = current_user.id
                
                # Get updated statistics
                stats = self.get_dashboard_stats(user_id)
                
                # Send stats update
                emit('stats_updated', {
                    'stats': stats,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
                self.logger.debug(f"Sent stats update to user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Error handling stats update request: {e}")
                emit('error', {'message': 'Failed to update statistics'})
    
    def send_caption_progress_notification(self, user_id: int, progress_data: Dict[str, Any]):
        """
        Send caption processing progress notification
        
        Args:
            user_id: Target user ID
            progress_data: Progress information
        """
        try:
            # Create progress notification
            notification = NotificationMessage(
                id=f"caption_progress_{progress_data.get('task_id', 'default')}",
                type=NotificationType.INFO,
                title="Caption Generation Progress",
                message=progress_data.get('message', 'Processing images...'),
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.CAPTION,
                data={
                    'progress': progress_data.get('progress', 0),
                    'total': progress_data.get('total', 0),
                    'current': progress_data.get('current', 0),
                    'task_id': progress_data.get('task_id'),
                    'status': progress_data.get('status', 'processing')
                }
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, notification)
            
            if success:
                self.logger.debug(f"Sent caption progress notification to user {user_id}")
            else:
                self.logger.warning(f"Failed to send caption progress notification to user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending caption progress notification: {e}")
    
    def send_caption_status_notification(self, user_id: int, status_data: Dict[str, Any]):
        """
        Send caption processing status notification
        
        Args:
            user_id: Target user ID
            status_data: Status information
        """
        try:
            status = status_data.get('status')
            
            # Determine notification type based on status
            if status == 'completed':
                notification_type = NotificationType.SUCCESS
                title = "Caption Generation Complete"
                message = f"Successfully generated {status_data.get('count', 0)} captions"
            elif status == 'failed':
                notification_type = NotificationType.ERROR
                title = "Caption Generation Failed"
                message = status_data.get('error', 'An error occurred during caption generation')
            elif status == 'cancelled':
                notification_type = NotificationType.WARNING
                title = "Caption Generation Cancelled"
                message = "Caption generation was cancelled by user request"
            else:
                notification_type = NotificationType.INFO
                title = "Caption Generation Status"
                message = status_data.get('message', f'Status: {status}')
            
            # Create status notification
            notification = NotificationMessage(
                id=f"caption_status_{status_data.get('task_id', 'default')}",
                type=notification_type,
                title=title,
                message=message,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.CAPTION,
                data=status_data
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, notification)
            
            if success:
                self.logger.info(f"Sent caption status notification to user {user_id}: {status}")
            else:
                self.logger.warning(f"Failed to send caption status notification to user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending caption status notification: {e}")
    
    def send_platform_status_notification(self, user_id: int, platform_data: Dict[str, Any]):
        """
        Send platform operation status notification
        
        Args:
            user_id: Target user ID
            platform_data: Platform status information
        """
        try:
            status = platform_data.get('status')
            platform_name = platform_data.get('platform_name', 'Platform')
            
            # Determine notification type based on status
            if status == 'connected':
                notification_type = NotificationType.SUCCESS
                title = "Platform Connected"
                message = f"Successfully connected to {platform_name}"
            elif status == 'disconnected':
                notification_type = NotificationType.WARNING
                title = "Platform Disconnected"
                message = f"Lost connection to {platform_name}"
            elif status == 'error':
                notification_type = NotificationType.ERROR
                title = "Platform Error"
                message = f"Error with {platform_name}: {platform_data.get('error', 'Unknown error')}"
            elif status == 'switched':
                notification_type = NotificationType.INFO
                title = "Platform Switched"
                message = f"Switched to {platform_name}"
            else:
                notification_type = NotificationType.INFO
                title = "Platform Status"
                message = f"{platform_name}: {status}"
            
            # Create platform notification
            notification = NotificationMessage(
                id=f"platform_status_{platform_data.get('platform_id', 'default')}",
                type=notification_type,
                title=title,
                message=message,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                category=NotificationCategory.PLATFORM,
                data=platform_data
            )
            
            # Send via unified notification manager
            success = self.notification_manager.send_user_notification(user_id, notification)
            
            if success:
                self.logger.info(f"Sent platform status notification to user {user_id}: {status}")
            else:
                self.logger.warning(f"Failed to send platform status notification to user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending platform status notification: {e}")
    
    def send_system_notification(self, message: str, notification_type: NotificationType = NotificationType.INFO,
                               title: str = "System Notification", target_users: Optional[list] = None):
        """
        Send system notification to users
        
        Args:
            message: Notification message
            notification_type: Type of notification
            title: Notification title
            target_users: List of user IDs to target (None for all dashboard users)
        """
        try:
            if target_users is None:
                # Broadcast to all dashboard users
                self.socketio.emit('system_notification', {
                    'type': notification_type.value,
                    'title': title,
                    'message': message,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, room='dashboard_users', namespace='/')
                
                self.logger.info(f"Broadcast system notification to all dashboard users: {title}")
            else:
                # Send to specific users
                for user_id in target_users:
                    notification = NotificationMessage(
                        id=f"system_{datetime.now(timezone.utc).timestamp()}",
                        type=notification_type,
                        title=title,
                        message=message,
                        user_id=user_id,
                        priority=NotificationPriority.NORMAL,
                        category=NotificationCategory.SYSTEM
                    )
                    
                    self.notification_manager.send_user_notification(user_id, notification)
                
                self.logger.info(f"Sent system notification to {len(target_users)} users: {title}")
            
        except Exception as e:
            self.logger.error(f"Error sending system notification: {e}")
    
    def send_maintenance_notification(self, message: str, maintenance_type: str = "maintenance",
                                    estimated_duration: Optional[int] = None):
        """
        Send maintenance notification to all dashboard users
        
        Args:
            message: Maintenance message
            maintenance_type: Type of maintenance
            estimated_duration: Estimated duration in minutes
        """
        try:
            notification_data = {
                'type': 'warning',
                'title': 'System Maintenance',
                'message': message,
                'maintenance_type': maintenance_type,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            if estimated_duration:
                notification_data['estimated_duration'] = estimated_duration
                notification_data['message'] += f" (Estimated duration: {estimated_duration} minutes)"
            
            # Broadcast to all dashboard users
            self.socketio.emit('maintenance_notification', notification_data, 
                             room='dashboard_users', namespace='/')
            
            self.logger.info(f"Sent maintenance notification to all dashboard users: {message}")
            
        except Exception as e:
            self.logger.error(f"Error sending maintenance notification: {e}")
    
    def send_stats_update(self, user_id: int, stats: Dict[str, Any]):
        """
        Send dashboard statistics update to user
        
        Args:
            user_id: Target user ID
            stats: Updated statistics
        """
        try:
            # Send stats update via WebSocket
            self.socketio.emit('stats_updated', {
                'stats': stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, room=f'user_{user_id}', namespace='/')
            
            # Also send as notification if significant changes
            if self.has_significant_stats_change(stats):
                notification = NotificationMessage(
                    id=f"stats_update_{datetime.now(timezone.utc).timestamp()}",
                    type=NotificationType.INFO,
                    title="Statistics Updated",
                    message="Your dashboard statistics have been updated",
                    user_id=user_id,
                    priority=NotificationPriority.LOW,
                    category=NotificationCategory.USER,
                    data={'stats': stats}
                )
                
                self.notification_manager.send_user_notification(user_id, notification)
            
            self.logger.debug(f"Sent stats update to user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending stats update: {e}")
    
    def get_dashboard_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get current dashboard statistics for user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing dashboard statistics
        """
        try:
            # This would integrate with the existing stats system
            # For now, return placeholder stats
            return {
                'total_posts': 0,
                'total_images': 0,
                'pending_review': 0,
                'posted': 0,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard stats for user {user_id}: {e}")
            return {}
    
    def has_significant_stats_change(self, stats: Dict[str, Any]) -> bool:
        """
        Check if statistics change is significant enough to notify
        
        Args:
            stats: Statistics data
            
        Returns:
            True if change is significant, False otherwise
        """
        # Simple heuristic - could be enhanced with more sophisticated logic
        pending_review = stats.get('pending_review', 0)
        return pending_review > 10  # Notify if more than 10 items pending review


def register_dashboard_notification_handlers(socketio, notification_manager: UnifiedNotificationManager):
    """
    Register dashboard notification handlers with SocketIO
    
    Args:
        socketio: SocketIO instance
        notification_manager: Unified notification manager
        
    Returns:
        DashboardNotificationHandlers instance
    """
    return DashboardNotificationHandlers(socketio, notification_manager)