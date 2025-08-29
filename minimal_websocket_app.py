#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Minimal WebSocket App to test SocketIO functionality
"""

import os
from dotenv import load_dotenv
from flask import Flask, jsonify

# Load environment variables
load_dotenv()

print("=== Starting Minimal WebSocket App ===")

# Create Flask app
app = Flask(__name__)

# Load configuration
from config import Config
config = Config()
app.config['SECRET_KEY'] = config.webapp.secret_key

print("✅ Flask app configured")

# Initialize WebSocket components
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_factory import WebSocketFactory

websocket_config_manager = WebSocketConfigManager(config)
websocket_cors_manager = CORSManager(websocket_config_manager)
websocket_factory = WebSocketFactory(websocket_config_manager, websocket_cors_manager)

print("✅ WebSocket components loaded")

# Create SocketIO instance
socketio = websocket_factory.create_socketio_instance(app)
print("✅ SocketIO instance created")

# Add basic routes
@app.route('/')
def index():
    return "Minimal WebSocket App Running"

@app.route('/api/websocket/client-config')
def websocket_config():
    """Provide WebSocket client configuration"""
    try:
        client_config = websocket_config_manager.get_client_config()
        
        # Add server capabilities
        server_capabilities = {
            'namespaces': ['/', '/admin'],
            'transports': client_config.get('transports', ['websocket', 'polling']),
            'features': ['reconnection', 'rooms', 'authentication', 'cors', 'error_handling', 'metrics'],
            'events': ['connect', 'disconnect', 'error', 'ping', 'pong', 'join_room', 'leave_room']
        }
        
        # Build complete configuration
        complete_config = {
            **client_config,
            'server_capabilities': server_capabilities,
            'config_version': '1.0.0',
            'generated_at': '2025-08-29T13:00:00.000000Z'
        }
        
        return jsonify({
            'success': True,
            'config': complete_config
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Add basic SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    print("Client connected to default namespace")
    return True

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected from default namespace")

@socketio.on('connect', namespace='/admin')
def handle_admin_connect():
    print("Client connected to admin namespace")
    return True

@socketio.on('disconnect', namespace='/admin')
def handle_admin_disconnect():
    print("Client disconnected from admin namespace")

@socketio.on('test_message')
def handle_test_message(data):
    print(f"Received test message: {data}")
    return {'status': 'received', 'data': data}

print("✅ SocketIO event handlers registered")

if __name__ == '__main__':
    try:
        print("🚀 Starting minimal WebSocket server on http://127.0.0.1:5000...")
        socketio.run(
            app,
            host='127.0.0.1',
            port=5000,
            debug=False,
            use_reloader=False  # Disable reloader to avoid issues
        )
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()