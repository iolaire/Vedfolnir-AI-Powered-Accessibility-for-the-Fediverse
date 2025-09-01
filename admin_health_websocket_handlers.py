# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Health WebSocket Handlers

This module provides WebSocket event handlers for admin system health notifications.
It integrates with the unified notification system to provide real-time health
monitoring and alerts via WebSocket connections in the admin namespace.

Requirements: 4.1, 4.2, 4.4, 4.5, 8.1, 8.3
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import current_app
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room, disconnect

from models import UserRole

logger = logging.getLogger(__name__)


def register_admin_health_websocket_handlers(socketio):
    """
    Register WebSocket event handlers for admin health notifications
    
    Args:
        socketio: Flask-SocketIO instance
    """
    
    @socketio.on('connect', namespace='/admin')
    def handle_admin_connect():
        """Handle admin WebSocket connection"""
        try:
            # Log detailed connection information
            from flask import request
            origin = request.headers.get('Origin')
            user_agent = request.headers.get('User-Agent', 'Unknown')
            referer = request.headers.get('Referer')
            
            logger.info(f"🔌 Admin WebSocket connection attempt:")
            logger.info(f"  - Origin: {origin}")
            logger.info(f"  - User-Agent: {user_agent[:100]}..." if user_agent and len(user_agent) > 100 else f"  - User-Agent: {user_agent}")
            logger.info(f"  - Referer: {referer}")
            logger.info(f"  - Namespace: /admin")
            
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                logger.warning(f"❌ Non-admin user attempted to connect to admin namespace: {current_user.id if current_user.is_authenticated else 'anonymous'}")
                disconnect()
                return False
            
            logger.info(f"✅ Admin user {current_user.id} connected to health monitoring")
            
            # Join admin health monitoring room
            join_room('admin_health_monitoring')
            
            # Initialize health notifications for this admin
            health_integration = getattr(current_app, 'admin_health_integration', None)
            if health_integration:
                result = health_integration.initialize_dashboard_notifications(current_user.id)
                
                # Send connection confirmation
                emit('health_monitoring_status', {
                    'connected': True,
                    'monitoring_active': result.get('health_monitoring_active', False),
                    'initial_health': result.get('initial_health_status', {}),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            else:
                # Send basic connection confirmation
                emit('health_monitoring_status', {
                    'connected': True,
                    'monitoring_active': False,
                    'error': 'Health integration service not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling admin WebSocket connection: {e}")
            emit('error', {'message': 'Connection failed'})
            disconnect()
            return False
    
    @socketio.on('disconnect', namespace='/admin')
    def handle_admin_disconnect(sid=None):
        """Handle admin WebSocket disconnection"""
        try:
            if current_user.is_authenticated:
                logger.info(f"Admin user {current_user.id} disconnected from health monitoring")
                leave_room('admin_health_monitoring')
            
        except Exception as e:
            logger.error(f"Error handling admin WebSocket disconnection: {e}")
    
    @socketio.on('request_health_update', namespace='/admin')
    def handle_health_update_request(data=None):
        """Handle request for immediate health update"""
        try:
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Access denied'})
                return
            
            force_update = data.get('force_update', False) if data else False
            
            # Get health integration service
            health_integration = getattr(current_app, 'admin_health_integration', None)
            if not health_integration:
                # Fallback to direct system monitor
                from system_monitor import SystemMonitor
                
                db_manager = current_app.config['db_manager']
                system_monitor = SystemMonitor(db_manager)
                
                health = system_monitor.get_system_health()
                
                emit('health_update', {
                    'success': True,
                    'health_status': health.to_dict(),
                    'update_type': 'direct_fallback',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return
            
            # Use health integration service
            result = health_integration.send_health_update_notification(
                user_id=current_user.id,
                force_update=force_update
            )
            
            emit('health_update', result)
            
        except Exception as e:
            logger.error(f"Error handling health update request: {e}")
            emit('error', {'message': 'Failed to get health update'})
    
    @socketio.on('configure_health_alerts', namespace='/admin')
    def handle_configure_health_alerts(data):
        """Handle health alert configuration"""
        try:
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Access denied'})
                return
            
            if not data or not isinstance(data, dict):
                emit('error', {'message': 'Invalid configuration data'})
                return
            
            # Get health integration service
            health_integration = getattr(current_app, 'admin_health_integration', None)
            if not health_integration:
                emit('error', {'message': 'Health monitoring service not available'})
                return
            
            # Configure health alerts
            result = health_integration.configure_health_alerts(current_user.id, data)
            
            emit('health_config_updated', result)
            
        except Exception as e:
            logger.error(f"Error configuring health alerts: {e}")
            emit('error', {'message': 'Failed to configure health alerts'})
    
    @socketio.on('start_health_monitoring', namespace='/admin')
    def handle_start_health_monitoring():
        """Handle request to start health monitoring"""
        try:
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Access denied'})
                return
            
            # Get health integration service
            health_integration = getattr(current_app, 'admin_health_integration', None)
            if not health_integration:
                emit('error', {'message': 'Health monitoring service not available'})
                return
            
            # Start health monitoring
            result = health_integration.initialize_dashboard_notifications(current_user.id)
            
            emit('health_monitoring_started', result)
            
            # Broadcast to all admin users
            emit('health_monitoring_status_change', {
                'monitoring_active': result.get('health_monitoring_active', False),
                'started_by': current_user.id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, room='admin_health_monitoring')
            
        except Exception as e:
            logger.error(f"Error starting health monitoring: {e}")
            emit('error', {'message': 'Failed to start health monitoring'})
    
    @socketio.on('stop_health_monitoring', namespace='/admin')
    def handle_stop_health_monitoring():
        """Handle request to stop health monitoring"""
        try:
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Access denied'})
                return
            
            # Get health integration service
            health_integration = getattr(current_app, 'admin_health_integration', None)
            if not health_integration:
                emit('error', {'message': 'Health monitoring service not available'})
                return
            
            # Stop health monitoring
            result = health_integration.stop_health_monitoring(current_user.id)
            
            emit('health_monitoring_stopped', result)
            
            # Broadcast to all admin users
            emit('health_monitoring_status_change', {
                'monitoring_active': False,
                'stopped_by': current_user.id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, room='admin_health_monitoring')
            
        except Exception as e:
            logger.error(f"Error stopping health monitoring: {e}")
            emit('error', {'message': 'Failed to stop health monitoring'})
    
    @socketio.on('get_health_status', namespace='/admin')
    def handle_get_health_status():
        """Handle request for current health monitoring status"""
        try:
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Access denied'})
                return
            
            # Get health integration service
            health_integration = getattr(current_app, 'admin_health_integration', None)
            if not health_integration:
                emit('error', {'message': 'Health monitoring service not available'})
                return
            
            # Get health monitoring status
            result = health_integration.get_health_monitoring_status(current_user.id)
            
            emit('health_status_response', result)
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            emit('error', {'message': 'Failed to get health status'})
    
    @socketio.on('acknowledge_health_alert', namespace='/admin')
    def handle_acknowledge_health_alert(data):
        """Handle health alert acknowledgment"""
        try:
            # Verify admin access
            if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
                emit('error', {'message': 'Access denied'})
                return
            
            if not data or 'alert_id' not in data:
                emit('error', {'message': 'Alert ID required'})
                return
            
            alert_id = data['alert_id']
            
            # Log acknowledgment
            logger.info(f"Admin {current_user.id} acknowledged health alert: {alert_id}")
            
            # Send acknowledgment confirmation
            emit('alert_acknowledged', {
                'success': True,
                'alert_id': alert_id,
                'acknowledged_by': current_user.id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Broadcast acknowledgment to other admin users
            emit('alert_acknowledgment_broadcast', {
                'alert_id': alert_id,
                'acknowledged_by': current_user.id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, room='admin_health_monitoring', include_self=False)
            
        except Exception as e:
            logger.error(f"Error acknowledging health alert: {e}")
            emit('error', {'message': 'Failed to acknowledge alert'})


def broadcast_health_notification_to_admins(socketio, notification_data: Dict[str, Any]) -> bool:
    """
    Broadcast health notification to all connected admin users
    
    Args:
        socketio: Flask-SocketIO instance
        notification_data: Notification data to broadcast
        
    Returns:
        True if broadcast successful, False otherwise
    """
    try:
        # Ensure notification is admin-only
        if not notification_data.get('admin_only', False):
            logger.warning("Attempted to broadcast non-admin notification to admin namespace")
            return False
        
        # Broadcast to admin health monitoring room
        socketio.emit('health_notification', notification_data, 
                     room='admin_health_monitoring', namespace='/admin')
        
        logger.debug(f"Broadcast health notification to admin users: {notification_data.get('title', 'Unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to broadcast health notification to admins: {e}")
        return False


def send_health_alert_to_admin(socketio, user_id: int, alert_data: Dict[str, Any]) -> bool:
    """
    Send health alert to specific admin user
    
    Args:
        socketio: Flask-SocketIO instance
        user_id: Admin user ID
        alert_data: Alert data to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Send to specific admin user session
        socketio.emit('health_alert', alert_data, 
                     room=f'user_{user_id}', namespace='/admin')
        
        logger.debug(f"Sent health alert to admin user {user_id}: {alert_data.get('title', 'Unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send health alert to admin user {user_id}: {e}")
        return False


def notify_health_monitoring_status_change(socketio, monitoring_active: bool, 
                                         changed_by: Optional[int] = None) -> bool:
    """
    Notify all admin users of health monitoring status change
    
    Args:
        socketio: Flask-SocketIO instance
        monitoring_active: Whether monitoring is now active
        changed_by: User ID who made the change (optional)
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        status_data = {
            'monitoring_active': monitoring_active,
            'changed_by': changed_by,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Broadcast to all admin users
        socketio.emit('health_monitoring_status_change', status_data,
                     room='admin_health_monitoring', namespace='/admin')
        
        logger.info(f"Notified admin users of health monitoring status change: {monitoring_active}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to notify health monitoring status change: {e}")
        return False