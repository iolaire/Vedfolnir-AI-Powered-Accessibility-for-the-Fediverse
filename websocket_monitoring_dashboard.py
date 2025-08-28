# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Connection Monitoring Dashboard

Provides a real-time monitoring dashboard for WebSocket connections
in development environments with live metrics and connection status.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from flask import Flask, render_template_string, jsonify, request
import socketio
from websocket_debug_logger import get_debug_logger, DebugLevel


class WebSocketConnectionMonitor:
    """Monitor WebSocket connections and collect metrics"""
    
    def __init__(self):
        self.connections = {}
        self.metrics = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'connection_times': deque(maxlen=100),
            'message_rates': deque(maxlen=60),  # Last 60 seconds
            'error_rates': deque(maxlen=60)
        }
        self.events = deque(maxlen=1000)  # Last 1000 events
        self.namespaces = defaultdict(lambda: {'connections': 0, 'messages': 0})
        self.transports = defaultdict(int)
        self.lock = threading.Lock()
        self.logger = get_debug_logger('monitor', DebugLevel.DEBUG)
        
        # Start metrics collection thread
        self.metrics_thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self.metrics_thread.start()
        
    def register_connection(self, connection_id: str, namespace: str = '/', 
                          transport: str = 'websocket', user_id: str = None):
        """Register a new WebSocket connection"""
        with self.lock:
            connection_info = {
                'id': connection_id,
                'namespace': namespace,
                'transport': transport,
                'user_id': user_id,
                'connected_at': datetime.utcnow(),
                'last_activity': datetime.utcnow(),
                'messages_sent': 0,
                'messages_received': 0,
                'status': 'connected'
            }
            
            self.connections[connection_id] = connection_info
            self.metrics['total_connections'] += 1
            self.metrics['active_connections'] += 1
            self.namespaces[namespace]['connections'] += 1
            self.transports[transport] += 1
            
            self._add_event('connection_established', {
                'connection_id': connection_id,
                'namespace': namespace,
                'transport': transport,
                'user_id': user_id
            })
            
            self.logger.info(f"Connection registered: {connection_id} ({namespace}, {transport})")
            
    def unregister_connection(self, connection_id: str, reason: str = 'disconnect'):
        """Unregister a WebSocket connection"""
        with self.lock:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                connection['status'] = 'disconnected'
                connection['disconnected_at'] = datetime.utcnow()
                connection['disconnect_reason'] = reason
                
                self.metrics['active_connections'] -= 1
                self.namespaces[connection['namespace']]['connections'] -= 1
                self.transports[connection['transport']] -= 1
                
                # Calculate connection duration
                duration = (connection['disconnected_at'] - connection['connected_at']).total_seconds()
                self.metrics['connection_times'].append(duration)
                
                self._add_event('connection_closed', {
                    'connection_id': connection_id,
                    'reason': reason,
                    'duration': duration
                })
                
                self.logger.info(f"Connection unregistered: {connection_id} (reason: {reason})")
                
                # Move to history after some time
                threading.Timer(300, lambda: self._archive_connection(connection_id)).start()
                
    def record_message_sent(self, connection_id: str, event: str, data_size: int = 0):
        """Record a message sent through WebSocket"""
        with self.lock:
            if connection_id in self.connections:
                self.connections[connection_id]['messages_sent'] += 1
                self.connections[connection_id]['last_activity'] = datetime.utcnow()
                
                namespace = self.connections[connection_id]['namespace']
                self.namespaces[namespace]['messages'] += 1
                
            self.metrics['messages_sent'] += 1
            
            self._add_event('message_sent', {
                'connection_id': connection_id,
                'event': event,
                'data_size': data_size
            })
            
    def record_message_received(self, connection_id: str, event: str, data_size: int = 0):
        """Record a message received through WebSocket"""
        with self.lock:
            if connection_id in self.connections:
                self.connections[connection_id]['messages_received'] += 1
                self.connections[connection_id]['last_activity'] = datetime.utcnow()
                
                namespace = self.connections[connection_id]['namespace']
                self.namespaces[namespace]['messages'] += 1
                
            self.metrics['messages_received'] += 1
            
            self._add_event('message_received', {
                'connection_id': connection_id,
                'event': event,
                'data_size': data_size
            })
            
    def record_error(self, connection_id: str, error_type: str, error_message: str):
        """Record an error for a WebSocket connection"""
        with self.lock:
            if connection_id in self.connections:
                if 'errors' not in self.connections[connection_id]:
                    self.connections[connection_id]['errors'] = []
                    
                self.connections[connection_id]['errors'].append({
                    'type': error_type,
                    'message': error_message,
                    'timestamp': datetime.utcnow()
                })
                
            self.metrics['errors'] += 1
            
            if error_type in ['connection_failed', 'connection_error']:
                self.metrics['failed_connections'] += 1
                
            self._add_event('error', {
                'connection_id': connection_id,
                'error_type': error_type,
                'error_message': error_message
            })
            
            self.logger.error(f"Error recorded for {connection_id}: {error_type} - {error_message}")
            
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        with self.lock:
            active_connections = [
                conn for conn in self.connections.values() 
                if conn['status'] == 'connected'
            ]
            
            return {
                'total_connections': self.metrics['total_connections'],
                'active_connections': len(active_connections),
                'failed_connections': self.metrics['failed_connections'],
                'connections': active_connections,
                'namespaces': dict(self.namespaces),
                'transports': dict(self.transports)
            }
            
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        with self.lock:
            # Calculate rates
            current_time = time.time()
            message_rate = len([
                event for event in self.events 
                if event['timestamp'] > current_time - 60 and 
                event['type'] in ['message_sent', 'message_received']
            ])
            
            error_rate = len([
                event for event in self.events 
                if event['timestamp'] > current_time - 60 and event['type'] == 'error'
            ])
            
            # Connection time statistics
            connection_times = list(self.metrics['connection_times'])
            avg_connection_time = sum(connection_times) / len(connection_times) if connection_times else 0
            
            return {
                'messages_sent': self.metrics['messages_sent'],
                'messages_received': self.metrics['messages_received'],
                'total_messages': self.metrics['messages_sent'] + self.metrics['messages_received'],
                'errors': self.metrics['errors'],
                'message_rate_per_minute': message_rate,
                'error_rate_per_minute': error_rate,
                'avg_connection_time': avg_connection_time,
                'uptime': self._get_uptime()
            }
            
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        with self.lock:
            events = list(self.events)[-limit:]
            return [
                {
                    'timestamp': datetime.fromtimestamp(event['timestamp']).isoformat(),
                    'type': event['type'],
                    'data': event['data']
                }
                for event in events
            ]
            
    def _add_event(self, event_type: str, data: Dict[str, Any]):
        """Add an event to the event log"""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'data': data
        }
        self.events.append(event)
        
    def _archive_connection(self, connection_id: str):
        """Archive a disconnected connection"""
        with self.lock:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                if connection['status'] == 'disconnected':
                    del self.connections[connection_id]
                    self.logger.debug(f"Connection archived: {connection_id}")
                    
    def _collect_metrics(self):
        """Collect metrics periodically"""
        while True:
            try:
                current_time = time.time()
                
                with self.lock:
                    # Collect message rates
                    recent_messages = len([
                        event for event in self.events 
                        if event['timestamp'] > current_time - 60 and 
                        event['type'] in ['message_sent', 'message_received']
                    ])
                    self.metrics['message_rates'].append(recent_messages)
                    
                    # Collect error rates
                    recent_errors = len([
                        event for event in self.events 
                        if event['timestamp'] > current_time - 60 and event['type'] == 'error'
                    ])
                    self.metrics['error_rates'].append(recent_errors)
                    
                time.sleep(60)  # Collect every minute
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                time.sleep(60)
                
    def _get_uptime(self) -> float:
        """Get monitor uptime in seconds"""
        if hasattr(self, 'start_time'):
            return (datetime.utcnow() - self.start_time).total_seconds()
        return 0


class WebSocketMonitoringDashboard:
    """Flask-based monitoring dashboard for WebSocket connections"""
    
    def __init__(self, monitor: WebSocketConnectionMonitor, port: int = 5001):
        self.monitor = monitor
        self.port = port
        self.app = Flask(__name__)
        self.app.secret_key = 'websocket_monitor_dev_key'
        
        # Set up routes
        self._setup_routes()
        
        self.logger = get_debug_logger('dashboard', DebugLevel.INFO)
        
    def _setup_routes(self):
        """Set up Flask routes for the dashboard"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template_string(self._get_dashboard_template())
            
        @self.app.route('/api/status')
        def api_status():
            """API endpoint for connection status"""
            return jsonify(self.monitor.get_connection_status())
            
        @self.app.route('/api/metrics')
        def api_metrics():
            """API endpoint for metrics"""
            return jsonify(self.monitor.get_metrics_summary())
            
        @self.app.route('/api/events')
        def api_events():
            """API endpoint for recent events"""
            limit = request.args.get('limit', 50, type=int)
            return jsonify(self.monitor.get_recent_events(limit))
            
        @self.app.route('/api/connections/<connection_id>')
        def api_connection_details(connection_id):
            """API endpoint for connection details"""
            with self.monitor.lock:
                connection = self.monitor.connections.get(connection_id)
                if connection:
                    # Convert datetime objects to strings
                    connection_copy = connection.copy()
                    for key, value in connection_copy.items():
                        if isinstance(value, datetime):
                            connection_copy[key] = value.isoformat()
                    return jsonify(connection_copy)
                else:
                    return jsonify({'error': 'Connection not found'}), 404
                    
        @self.app.route('/api/export')
        def api_export():
            """API endpoint to export monitoring data"""
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': self.monitor.get_connection_status(),
                'metrics': self.monitor.get_metrics_summary(),
                'events': self.monitor.get_recent_events(1000)
            }
            return jsonify(data)
            
    def _get_dashboard_template(self) -> str:
        """Get the HTML template for the dashboard"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Monitoring Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .section h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .connection-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .connection-item {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
            background: #f9f9f9;
        }
        .connection-id {
            font-weight: bold;
            color: #667eea;
        }
        .connection-details {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        .event-list {
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
        }
        .event-item {
            padding: 5px;
            border-bottom: 1px solid #eee;
        }
        .event-timestamp {
            color: #666;
        }
        .event-type {
            font-weight: bold;
            color: #667eea;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-connected { background-color: #4CAF50; }
        .status-disconnected { background-color: #f44336; }
        .status-error { background-color: #ff9800; }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #5a6fd8;
        }
        .auto-refresh {
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>WebSocket Monitoring Dashboard</h1>
            <p>Real-time monitoring for WebSocket connections</p>
        </div>
        
        <button class="refresh-btn" onclick="refreshData()">Refresh Data</button>
        <label class="auto-refresh">
            <input type="checkbox" id="autoRefresh" checked> Auto-refresh (5s)
        </label>
        
        <div class="stats-grid" id="statsGrid">
            <!-- Stats will be populated by JavaScript -->
        </div>
        
        <div class="section">
            <h2>Active Connections</h2>
            <div class="connection-list" id="connectionList">
                <!-- Connections will be populated by JavaScript -->
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Events</h2>
            <div class="event-list" id="eventList">
                <!-- Events will be populated by JavaScript -->
            </div>
        </div>
    </div>
    
    <script>
        let autoRefreshInterval;
        
        function refreshData() {
            Promise.all([
                fetch('/api/status').then(r => r.json()),
                fetch('/api/metrics').then(r => r.json()),
                fetch('/api/events?limit=20').then(r => r.json())
            ]).then(([status, metrics, events]) => {
                updateStats(status, metrics);
                updateConnections(status.connections);
                updateEvents(events);
            }).catch(error => {
                console.error('Error fetching data:', error);
            });
        }
        
        function updateStats(status, metrics) {
            const statsGrid = document.getElementById('statsGrid');
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${status.active_connections}</div>
                    <div class="stat-label">Active Connections</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${status.total_connections}</div>
                    <div class="stat-label">Total Connections</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${metrics.total_messages}</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${metrics.message_rate_per_minute}</div>
                    <div class="stat-label">Messages/Min</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${metrics.errors}</div>
                    <div class="stat-label">Total Errors</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${metrics.avg_connection_time.toFixed(2)}s</div>
                    <div class="stat-label">Avg Connection Time</div>
                </div>
            `;
        }
        
        function updateConnections(connections) {
            const connectionList = document.getElementById('connectionList');
            
            if (connections.length === 0) {
                connectionList.innerHTML = '<p>No active connections</p>';
                return;
            }
            
            connectionList.innerHTML = connections.map(conn => `
                <div class="connection-item">
                    <div class="connection-id">
                        <span class="status-indicator status-${conn.status}"></span>
                        ${conn.id}
                    </div>
                    <div class="connection-details">
                        Namespace: ${conn.namespace} | Transport: ${conn.transport} | 
                        Messages: ${conn.messages_sent + conn.messages_received} |
                        Connected: ${new Date(conn.connected_at).toLocaleTimeString()}
                        ${conn.user_id ? ` | User: ${conn.user_id}` : ''}
                    </div>
                </div>
            `).join('');
        }
        
        function updateEvents(events) {
            const eventList = document.getElementById('eventList');
            
            if (events.length === 0) {
                eventList.innerHTML = '<p>No recent events</p>';
                return;
            }
            
            eventList.innerHTML = events.map(event => `
                <div class="event-item">
                    <span class="event-timestamp">${new Date(event.timestamp).toLocaleTimeString()}</span>
                    <span class="event-type">${event.type}</span>
                    ${JSON.stringify(event.data)}
                </div>
            `).join('');
        }
        
        function setupAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            
            function toggleAutoRefresh() {
                if (checkbox.checked) {
                    autoRefreshInterval = setInterval(refreshData, 5000);
                } else {
                    clearInterval(autoRefreshInterval);
                }
            }
            
            checkbox.addEventListener('change', toggleAutoRefresh);
            toggleAutoRefresh(); // Start auto-refresh if checked
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            setupAutoRefresh();
        });
    </script>
</body>
</html>
        '''
        
    def run(self, debug: bool = True, host: str = '127.0.0.1'):
        """Run the monitoring dashboard"""
        self.logger.info(f"Starting WebSocket monitoring dashboard on {host}:{self.port}")
        self.app.run(host=host, port=self.port, debug=debug, threaded=True)


# Global monitor instance
_global_monitor = None


def get_connection_monitor() -> WebSocketConnectionMonitor:
    """Get the global connection monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = WebSocketConnectionMonitor()
        _global_monitor.start_time = datetime.utcnow()
    return _global_monitor


def create_monitoring_dashboard(port: int = 5001) -> WebSocketMonitoringDashboard:
    """Create a monitoring dashboard"""
    monitor = get_connection_monitor()
    return WebSocketMonitoringDashboard(monitor, port)


def start_monitoring_dashboard(port: int = 5001, host: str = '127.0.0.1'):
    """Start the monitoring dashboard server"""
    dashboard = create_monitoring_dashboard(port)
    dashboard.run(debug=True, host=host)