# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Maintenance Status Server-Sent Events (SSE) Implementation

Provides real-time maintenance status updates via Server-Sent Events.
Integrates with MaintenanceStatusAPI for live status broadcasting.
"""

import logging
import json
import threading
import time
import uuid
from typing import Dict, List, Optional, Generator, Any
from dataclasses import asdict
from datetime import datetime, timezone
from flask import Response

logger = logging.getLogger(__name__)


class MaintenanceStatusSSE:
    """
    Server-Sent Events implementation for maintenance status updates
    
    Features:
    - Real-time status broadcasting via SSE
    - Client connection management
    - Event filtering and subscription management
    - Heartbeat and connection monitoring
    - Integration with MaintenanceStatusAPI
    """
    
    def __init__(self, status_api):
        """
        Initialize SSE service
        
        Args:
            status_api: MaintenanceStatusAPI instance
        """
        self.status_api = status_api
        
        # Client connections
        self._clients: Dict[str, Dict[str, Any]] = {}
        self._clients_lock = threading.RLock()
        
        # Event queue for broadcasting
        self._event_queue: List[Dict[str, Any]] = []
        self._queue_lock = threading.RLock()
        
        # SSE configuration
        self.heartbeat_interval = 30  # seconds
        self.max_queue_size = 100
        self.connection_timeout = 300  # 5 minutes
        
        # Statistics
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'events_sent': 0,
            'heartbeats_sent': 0,
            'connection_errors': 0,
            'last_event_time': None
        }
        self._stats_lock = threading.RLock()
        
        # Subscribe to status API changes
        self._api_subscription_id = self.status_api.subscribe_to_status_changes(
            self._handle_status_change
        )
        
        # Start background tasks
        self._running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._heartbeat_thread.start()
        self._cleanup_thread.start()
        
        logger.info("Maintenance Status SSE service initialized")
    
    def create_event_stream(self, client_id: Optional[str] = None, 
                           event_types: Optional[List[str]] = None) -> Generator[str, None, None]:
        """
        Create SSE event stream for a client
        
        Args:
            client_id: Unique client identifier (optional, will generate if not provided)
            event_types: List of event types to subscribe to (optional, all if not provided)
            
        Yields:
            SSE formatted event strings
        """
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Register client
        client_info = {
            'id': client_id,
            'connected_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc),
            'event_types': event_types or [],
            'events_sent': 0,
            'active': True
        }
        
        with self._clients_lock:
            self._clients[client_id] = client_info
        
        with self._stats_lock:
            self._stats['total_connections'] += 1
            self._stats['active_connections'] += 1
        
        logger.info(f"SSE client {client_id} connected")
        
        try:
            # Send initial status
            try:
                initial_status = self.status_api.get_status()
                yield self._format_sse_event('status_update', asdict(initial_status))
            except Exception as e:
                logger.error(f"Error getting initial status for client {client_id}: {str(e)}")
                yield self._format_sse_event('error', {
                    'message': 'Unable to get initial status',
                    'error': str(e)
                })
            
            # Send connection confirmation
            yield self._format_sse_event('connection_established', {
                'client_id': client_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'subscribed_events': event_types or ['all']
            })
            
            # Stream events
            last_event_index = 0
            
            while self._running and client_info['active']:
                # Check for new events
                with self._queue_lock:
                    if last_event_index < len(self._event_queue):
                        # Send new events
                        for event in self._event_queue[last_event_index:]:
                            if self._should_send_event(event, client_info):
                                yield self._format_sse_event(event['type'], event['data'])
                                client_info['events_sent'] += 1
                                client_info['last_activity'] = datetime.now(timezone.utc)
                        
                        last_event_index = len(self._event_queue)
                
                # Small delay to prevent busy waiting
                time.sleep(0.1)
                
        except GeneratorExit:
            logger.debug(f"SSE client {client_id} disconnected (GeneratorExit)")
        except Exception as e:
            logger.error(f"Error in SSE stream for client {client_id}: {str(e)}")
            with self._stats_lock:
                self._stats['connection_errors'] += 1
        finally:
            # Clean up client
            with self._clients_lock:
                if client_id in self._clients:
                    self._clients[client_id]['active'] = False
                    del self._clients[client_id]
            
            with self._stats_lock:
                self._stats['active_connections'] -= 1
            
            logger.info(f"SSE client {client_id} disconnected")
    
    def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> int:
        """
        Broadcast event to all connected clients
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            Number of clients the event was queued for
        """
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'id': str(uuid.uuid4())
        }
        
        with self._queue_lock:
            self._event_queue.append(event)
            
            # Trim queue if too large
            if len(self._event_queue) > self.max_queue_size:
                self._event_queue = self._event_queue[-self.max_queue_size:]
        
        with self._stats_lock:
            self._stats['events_sent'] += 1
            self._stats['last_event_time'] = event['timestamp']
        
        active_clients = len([c for c in self._clients.values() if c['active']])
        logger.debug(f"Broadcast event {event_type} to {active_clients} clients")
        
        return active_clients
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client information dictionary or None if not found
        """
        with self._clients_lock:
            return self._clients.get(client_id, {}).copy() if client_id in self._clients else None
    
    def disconnect_client(self, client_id: str) -> bool:
        """
        Disconnect a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if client was found and disconnected
        """
        with self._clients_lock:
            if client_id in self._clients:
                self._clients[client_id]['active'] = False
                logger.info(f"Manually disconnected SSE client {client_id}")
                return True
        
        return False
    
    def get_sse_stats(self) -> Dict[str, Any]:
        """
        Get SSE service statistics
        
        Returns:
            Dictionary with SSE statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        with self._clients_lock:
            client_stats = {
                'active_clients': len([c for c in self._clients.values() if c['active']]),
                'total_clients': len(self._clients),
                'clients_by_event_type': self._get_clients_by_event_type()
            }
        
        with self._queue_lock:
            queue_stats = {
                'queue_size': len(self._event_queue),
                'max_queue_size': self.max_queue_size
            }
        
        return {
            'service_stats': stats,
            'client_stats': client_stats,
            'queue_stats': queue_stats,
            'configuration': {
                'heartbeat_interval': self.heartbeat_interval,
                'connection_timeout': self.connection_timeout
            }
        }
    
    def _handle_status_change(self, event_type: str, status_response):
        """
        Handle status changes from the API
        
        Args:
            event_type: Type of status change
            status_response: MaintenanceStatusResponse object
        """
        try:
            # Convert status response to dict for broadcasting
            status_data = asdict(status_response)
            
            # Broadcast the status change
            self.broadcast_event('maintenance_status_change', {
                'event_type': event_type,
                'status': status_data
            })
            
            logger.debug(f"Broadcast maintenance status change: {event_type}")
            
        except Exception as e:
            logger.error(f"Error handling status change: {str(e)}")
    
    def _should_send_event(self, event: Dict[str, Any], client_info: Dict[str, Any]) -> bool:
        """
        Determine if event should be sent to client
        
        Args:
            event: Event dictionary
            client_info: Client information
            
        Returns:
            True if event should be sent
        """
        # If client has no event type filter, send all events
        if not client_info['event_types']:
            return True
        
        # Check if event type matches client's subscription
        return event['type'] in client_info['event_types']
    
    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Format data as SSE event
        
        Args:
            event_type: Event type
            data: Event data
            
        Returns:
            SSE formatted string
        """
        try:
            json_data = json.dumps(data, default=str)
            return f"event: {event_type}\ndata: {json_data}\n\n"
        except Exception as e:
            logger.error(f"Error formatting SSE event: {str(e)}")
            return f"event: error\ndata: {{\"error\": \"Failed to format event\"}}\n\n"
    
    def _heartbeat_worker(self):
        """Background worker for sending heartbeats"""
        while self._running:
            try:
                time.sleep(self.heartbeat_interval)
                
                if not self._running:
                    break
                
                # Send heartbeat to all active clients
                heartbeat_data = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'active_clients': len([c for c in self._clients.values() if c['active']])
                }
                
                self.broadcast_event('heartbeat', heartbeat_data)
                
                with self._stats_lock:
                    self._stats['heartbeats_sent'] += 1
                
            except Exception as e:
                logger.error(f"Error in heartbeat worker: {str(e)}")
    
    def _cleanup_worker(self):
        """Background worker for cleaning up inactive clients"""
        while self._running:
            try:
                time.sleep(60)  # Run cleanup every minute
                
                if not self._running:
                    break
                
                current_time = datetime.now(timezone.utc)
                inactive_clients = []
                
                with self._clients_lock:
                    for client_id, client_info in self._clients.items():
                        # Check if client has been inactive too long
                        time_since_activity = (current_time - client_info['last_activity']).total_seconds()
                        
                        if time_since_activity > self.connection_timeout:
                            inactive_clients.append(client_id)
                    
                    # Remove inactive clients
                    for client_id in inactive_clients:
                        if client_id in self._clients:
                            self._clients[client_id]['active'] = False
                            del self._clients[client_id]
                            logger.info(f"Cleaned up inactive SSE client {client_id}")
                
                if inactive_clients:
                    with self._stats_lock:
                        self._stats['active_connections'] -= len(inactive_clients)
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {str(e)}")
    
    def _get_clients_by_event_type(self) -> Dict[str, int]:
        """Get count of clients by event type subscription"""
        event_type_counts = {}
        
        for client_info in self._clients.values():
            if client_info['active']:
                event_types = client_info['event_types'] or ['all']
                for event_type in event_types:
                    event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        return event_type_counts
    
    def shutdown(self):
        """Shutdown the SSE service"""
        logger.info("Shutting down Maintenance Status SSE service")
        
        self._running = False
        
        # Disconnect all clients
        with self._clients_lock:
            for client_info in self._clients.values():
                client_info['active'] = False
        
        # Unsubscribe from status API
        if self._api_subscription_id:
            self.status_api.unsubscribe(self._api_subscription_id)
        
        # Wait for background threads to finish
        if self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        logger.info("Maintenance Status SSE service shutdown complete")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.shutdown()
        except Exception as e:
            logger.error(f"Error during SSE service cleanup: {str(e)}")


def create_flask_sse_response(sse_service: MaintenanceStatusSSE, 
                             client_id: Optional[str] = None,
                             event_types: Optional[List[str]] = None) -> Response:
    """
    Create Flask Response object for SSE stream
    
    Args:
        sse_service: MaintenanceStatusSSE instance
        client_id: Optional client identifier
        event_types: Optional list of event types to subscribe to
        
    Returns:
        Flask Response object with SSE stream
    """
    def generate():
        try:
            for event in sse_service.create_event_stream(client_id, event_types):
                yield event
        except GeneratorExit:
            pass
        except Exception as e:
            logger.error(f"Error in SSE response generator: {str(e)}")
            yield f"event: error\ndata: {{\"error\": \"Stream error\"}}\n\n"
    
    response = Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )
    
    return response