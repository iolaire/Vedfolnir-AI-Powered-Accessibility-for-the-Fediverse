# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""WebSocket routes for real-time admin dashboard updates"""

from flask import current_app, request
from flask_login import current_user
from models import UserRole
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def register_websocket_routes(bp):
    """Register WebSocket routes for admin dashboard"""
    
    # WebSocket endpoints are now handled by Flask-SocketIO
    # See websocket_progress_handler.py for WebSocket event handlers
    pass

class AdminDashboardWebSocket:
    """WebSocket handler for admin dashboard real-time updates"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.connected_clients = set()
        self.update_interval = 5  # seconds
        
    def add_client(self, client_id, user_id):
        """Add a client to receive updates"""
        self.connected_clients.add((client_id, user_id))
        logger.info(f"Admin client {client_id} connected for user {user_id}")
    
    def remove_client(self, client_id):
        """Remove a client from updates"""
        self.connected_clients = {(cid, uid) for cid, uid in self.connected_clients if cid != client_id}
        logger.info(f"Admin client {client_id} disconnected")
    
    async def broadcast_job_update(self, job_data):
        """Broadcast job update to all connected admin clients"""
        message = {
            'type': 'job_update',
            'job': job_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self._broadcast_message(message)
    
    async def broadcast_system_metrics(self, metrics):
        """Broadcast system metrics update"""
        message = {
            'type': 'system_metrics',
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self._broadcast_message(message)
    
    async def broadcast_alert(self, alert_data):
        """Broadcast new alert to admin clients"""
        message = {
            'type': 'alert',
            'alert': alert_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self._broadcast_message(message)
    
    async def broadcast_job_completion(self, job_data):
        """Broadcast job completion notification"""
        message = {
            'type': 'job_completed',
            'job': job_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self._broadcast_message(message)
    
    async def broadcast_job_failure(self, job_data):
        """Broadcast job failure notification"""
        message = {
            'type': 'job_failed',
            'job': job_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self._broadcast_message(message)
    
    async def _broadcast_message(self, message):
        """Internal method to broadcast message to all connected clients"""
        if not self.connected_clients:
            return
        
        message_json = json.dumps(message)
        
        # In a real implementation, this would send to WebSocket clients
        # For now, we'll log the message
        logger.info(f"Broadcasting to {len(self.connected_clients)} admin clients: {message['type']}")
    
    async def start_periodic_updates(self):
        """Start periodic system updates"""
        while True:
            try:
                if self.connected_clients:
                    # Get current system metrics
                    metrics = await self._get_current_metrics()
                    await self.broadcast_system_metrics(metrics)
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in periodic updates: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _get_current_metrics(self):
        """Get current system metrics for broadcasting"""
        try:
            from web_caption_generation_service import WebCaptionGenerationService
            from system_monitor import SystemMonitor
            
            # Use a dummy admin user ID for system metrics
            admin_user_id = 1  # This should be a valid admin user ID
            
            service = WebCaptionGenerationService(self.db_manager)
            monitor = SystemMonitor(self.db_manager)
            
            # Get metrics
            metrics = service.get_system_metrics(admin_user_id)
            system_health = monitor.get_system_health()
            performance_metrics = monitor.get_performance_metrics()
            
            return {
                'active_jobs': metrics.get('active_jobs', 0),
                'queued_jobs': metrics.get('queued_jobs', 0),
                'completed_today': metrics.get('completed_today', 0),
                'failed_jobs': metrics.get('failed_jobs', 0),
                'success_rate': metrics.get('success_rate', 0),
                'error_rate': metrics.get('error_rate', 0),
                'system_load': performance_metrics.get('cpu_usage_percent', 0),
                'avg_processing_time': metrics.get('avg_processing_time', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {
                'active_jobs': 0,
                'queued_jobs': 0,
                'completed_today': 0,
                'failed_jobs': 0,
                'success_rate': 0,
                'error_rate': 0,
                'system_load': 0,
                'avg_processing_time': 0
            }

# Global WebSocket handler instance
dashboard_websocket_handler = None

def get_dashboard_websocket_handler(db_manager):
    """Get or create the dashboard WebSocket handler"""
    global dashboard_websocket_handler
    
    if dashboard_websocket_handler is None:
        dashboard_websocket_handler = AdminDashboardWebSocket(db_manager)
    
    return dashboard_websocket_handler