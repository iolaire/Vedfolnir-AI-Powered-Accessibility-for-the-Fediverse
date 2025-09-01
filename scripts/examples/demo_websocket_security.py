# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Security System Demonstration

This script demonstrates the WebSocket security features including CSRF protection,
rate limiting, input validation, and abuse detection.
"""

import logging
import time
import json
from datetime import datetime, timezone
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

# Import WebSocket security components
from websocket_security_manager import WebSocketSecurityManager, WebSocketSecurityConfig
from websocket_security_middleware import setup_websocket_security
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from config import Config
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HTML template for testing
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Security Demo</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .log { background: #f5f5f5; padding: 10px; height: 200px; overflow-y: scroll; font-family: monospace; }
        button { margin: 5px; padding: 10px 15px; }
        input { margin: 5px; padding: 5px; width: 200px; }
        .error { color: red; }
        .success { color: green; }
        .warning { color: orange; }
    </style>
</head>
<body>
    <div class="container">
        <h1>WebSocket Security Demo</h1>
        
        <div class="section">
            <h2>Connection Status</h2>
            <div id="connection-status">Disconnected</div>
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
        </div>
        
        <div class="section">
            <h2>Message Testing</h2>
            <input type="text" id="message-input" placeholder="Enter message" value="Hello World">
            <button onclick="sendMessage()">Send Message</button>
            <button onclick="sendLargeMessage()">Send Large Message</button>
            <button onclick="floodMessages()">Flood Messages (Rate Limit Test)</button>
        </div>
        
        <div class="section">
            <h2>Security Testing</h2>
            <button onclick="sendInvalidEvent()">Send Invalid Event</button>
            <button onclick="sendMaliciousPayload()">Send Malicious Payload</button>
            <button onclick="testCSRF()">Test CSRF Protection</button>
            <button onclick="testAdminAccess()">Test Admin Access</button>
        </div>
        
        <div class="section">
            <h2>Connection Testing</h2>
            <button onclick="multipleConnections()">Create Multiple Connections</button>
            <button onclick="rapidReconnect()">Rapid Reconnect Test</button>
        </div>
        
        <div class="section">
            <h2>Security Stats</h2>
            <button onclick="getSecurityStats()">Get Security Stats</button>
            <div id="security-stats"></div>
        </div>
        
        <div class="section">
            <h2>Event Log</h2>
            <button onclick="clearLog()">Clear Log</button>
            <div id="log" class="log"></div>
        </div>
    </div>

    <script>
        let socket = null;
        let connectionCount = 0;
        
        function log(message, type = 'info') {
            const logDiv = document.getElementById('log');
            const timestamp = new Date().toLocaleTimeString();
            const className = type === 'error' ? 'error' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : '';
            logDiv.innerHTML += `<div class="${className}">[${timestamp}] ${message}</div>`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }
        
        function updateConnectionStatus(status) {
            document.getElementById('connection-status').textContent = status;
        }
        
        function connect() {
            if (socket && socket.connected) {
                log('Already connected', 'warning');
                return;
            }
            
            socket = io('/', {
                transports: ['websocket', 'polling'],
                timeout: 20000,
                reconnection: true,
                reconnectionAttempts: 5
            });
            
            socket.on('connect', function() {
                log('Connected successfully', 'success');
                updateConnectionStatus('Connected');
            });
            
            socket.on('disconnect', function() {
                log('Disconnected', 'warning');
                updateConnectionStatus('Disconnected');
            });
            
            socket.on('connection_success', function(data) {
                log(`Connection success: ${JSON.stringify(data)}`, 'success');
            });
            
            socket.on('connection_error', function(data) {
                log(`Connection error: ${JSON.stringify(data)}`, 'error');
            });
            
            socket.on('message_blocked', function(data) {
                log(`Message blocked: ${JSON.stringify(data)}`, 'error');
            });
            
            socket.on('security_error', function(data) {
                log(`Security error: ${JSON.stringify(data)}`, 'error');
            });
            
            socket.on('error', function(data) {
                log(`Error: ${JSON.stringify(data)}`, 'error');
            });
            
            socket.on('security_alert', function(data) {
                log(`Security alert: ${JSON.stringify(data)}`, 'warning');
            });
            
            socket.on('message_response', function(data) {
                log(`Message response: ${JSON.stringify(data)}`, 'success');
            });
            
            socket.on('security_stats_response', function(data) {
                document.getElementById('security-stats').innerHTML = 
                    '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                log('Security stats received', 'success');
            });
        }
        
        function disconnect() {
            if (socket) {
                socket.disconnect();
                socket = null;
                updateConnectionStatus('Disconnected');
                log('Disconnected manually');
            }
        }
        
        function sendMessage() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            const message = document.getElementById('message-input').value;
            socket.emit('message', {
                content: message,
                timestamp: new Date().toISOString()
            });
            log(`Sent message: ${message}`);
        }
        
        function sendLargeMessage() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            const largeContent = 'x'.repeat(15000); // 15KB message
            socket.emit('message', {
                content: largeContent,
                timestamp: new Date().toISOString()
            });
            log('Sent large message (15KB)');
        }
        
        function floodMessages() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            log('Starting message flood test...');
            for (let i = 0; i < 70; i++) {
                setTimeout(() => {
                    socket.emit('message', {
                        content: `Flood message ${i}`,
                        timestamp: new Date().toISOString()
                    });
                }, i * 100); // Send every 100ms
            }
        }
        
        function sendInvalidEvent() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            socket.emit('invalid_event_type', {
                content: 'This should be blocked',
                timestamp: new Date().toISOString()
            });
            log('Sent invalid event type');
        }
        
        function sendMaliciousPayload() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            socket.emit('message', {
                content: '<script>alert("XSS")</script>',
                sql_injection: "'; DROP TABLE users; --",
                command_injection: "; rm -rf /",
                timestamp: new Date().toISOString()
            });
            log('Sent malicious payload');
        }
        
        function testCSRF() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            socket.emit('admin_action', {
                action: 'delete_user',
                target: 'testuser',
                csrf_token: 'invalid_token',
                timestamp: new Date().toISOString()
            });
            log('Sent request without valid CSRF token');
        }
        
        function testAdminAccess() {
            // Try to connect to admin namespace
            const adminSocket = io('/admin', {
                transports: ['websocket', 'polling']
            });
            
            adminSocket.on('connect', function() {
                log('Connected to admin namespace', 'success');
                adminSocket.disconnect();
            });
            
            adminSocket.on('connect_error', function(error) {
                log(`Admin connection failed: ${error}`, 'error');
            });
            
            log('Attempting admin namespace connection...');
        }
        
        function multipleConnections() {
            log('Creating multiple connections...');
            
            for (let i = 0; i < 25; i++) {
                setTimeout(() => {
                    const testSocket = io('/', {
                        transports: ['websocket', 'polling'],
                        forceNew: true
                    });
                    
                    testSocket.on('connect', function() {
                        log(`Test connection ${i} established`);
                        setTimeout(() => testSocket.disconnect(), 5000);
                    });
                    
                    testSocket.on('connect_error', function(error) {
                        log(`Test connection ${i} failed: ${error}`, 'error');
                    });
                }, i * 200);
            }
        }
        
        function rapidReconnect() {
            log('Starting rapid reconnect test...');
            
            for (let i = 0; i < 15; i++) {
                setTimeout(() => {
                    if (socket) {
                        socket.disconnect();
                    }
                    setTimeout(() => {
                        connect();
                    }, 100);
                }, i * 500);
            }
        }
        
        function getSecurityStats() {
            if (!socket || !socket.connected) {
                log('Not connected', 'error');
                return;
            }
            
            socket.emit('get_security_stats', {
                timestamp: new Date().toISOString()
            });
            log('Requested security stats');
        }
        
        function clearLog() {
            document.getElementById('log').innerHTML = '';
        }
        
        // Auto-connect on page load
        window.onload = function() {
            log('WebSocket Security Demo loaded');
            log('Click Connect to start testing');
        };
    </script>
</body>
</html>
"""


def create_demo_app():
    """Create Flask app with WebSocket security demo"""
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'demo-secret-key-change-in-production'
    
    # Initialize configuration and database
    config = Config()
    db_manager = DatabaseManager(config)
    session_manager = SessionManagerV2(db_manager)
    
    # Create WebSocket configuration
    ws_config_manager = WebSocketConfigManager(config)
    cors_manager = CORSManager(ws_config_manager)
    
    # Create security configuration
    security_config = WebSocketSecurityConfig(
        csrf_enabled=True,
        rate_limiting_enabled=True,
        input_validation_enabled=True,
        connection_monitoring_enabled=True,
        abuse_detection_enabled=True,
        max_connections_per_ip=10,
        max_connections_per_user=5,
        message_rate_limit=20,
        connection_rate_limit=5
    )
    
    # Create WebSocket factory with security
    ws_factory = WebSocketFactory(
        ws_config_manager, cors_manager, 
        db_manager, session_manager, security_config
    )
    
    # Create SocketIO instance
    socketio = ws_factory.create_socketio_instance(app)
    
    @app.route('/')
    def index():
        """Serve the demo page"""
        return render_template_string(HTML_TEMPLATE)
    
    @socketio.on('message')
    def handle_message(data):
        """Handle regular messages"""
        try:
            logger.info(f"Received message: {data}")
            emit('message_response', {
                'status': 'received',
                'original_data': data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            emit('error', {'message': 'Message handling failed'})
    
    @socketio.on('admin_action')
    def handle_admin_action(data):
        """Handle admin actions (requires CSRF protection)"""
        try:
            logger.info(f"Received admin action: {data}")
            # This would normally require CSRF validation
            emit('message_response', {
                'status': 'admin_action_received',
                'action': data.get('action'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling admin action: {e}")
            emit('error', {'message': 'Admin action failed'})
    
    @socketio.on('get_security_stats')
    def handle_get_security_stats(data):
        """Get security statistics"""
        try:
            # Get security stats from the factory
            stats = ws_factory.get_factory_status()
            emit('security_stats_response', stats)
        except Exception as e:
            logger.error(f"Error getting security stats: {e}")
            emit('error', {'message': 'Failed to get security stats'})
    
    @socketio.on('connect')
    def handle_connect():
        """Handle connection (security is handled by middleware)"""
        logger.info("Client connected")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle disconnection"""
        logger.info("Client disconnected")
    
    return app, socketio


def main():
    """Run the WebSocket security demo"""
    print("=" * 60)
    print("WebSocket Security System Demo")
    print("=" * 60)
    print()
    print("This demo showcases the WebSocket security features:")
    print("- CSRF Protection for WebSocket events")
    print("- Rate limiting for connections and messages")
    print("- Input validation and sanitization")
    print("- Connection monitoring and abuse detection")
    print("- Security event logging")
    print()
    print("Starting demo server...")
    print()
    
    try:
        # Create demo app
        app, socketio = create_demo_app()
        
        print("Demo server starting on http://127.0.0.1:5000")
        print("Open your browser and navigate to the URL above")
        print()
        print("Security Features Enabled:")
        print("- Connection rate limiting: 5 connections/minute per IP")
        print("- Message rate limiting: 20 messages/minute per user")
        print("- Max connections per IP: 10")
        print("- Max connections per user: 5")
        print("- Input validation and sanitization")
        print("- Abuse detection and automatic blocking")
        print()
        print("Test scenarios available in the web interface:")
        print("1. Normal message sending")
        print("2. Rate limit testing (message flood)")
        print("3. Connection limit testing")
        print("4. Invalid event type testing")
        print("5. Malicious payload testing")
        print("6. CSRF protection testing")
        print("7. Admin access testing")
        print("8. Security statistics monitoring")
        print()
        print("Press Ctrl+C to stop the demo")
        print("=" * 60)
        
        # Run the app
        socketio.run(app, host='127.0.0.1', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\nDemo stopped by user")
    except Exception as e:
        print(f"Error running demo: {e}")
        logger.exception("Demo error")


if __name__ == '__main__':
    main()