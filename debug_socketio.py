#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug SocketIO initialization to identify the hanging issue
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== SocketIO Debug Test ===")

try:
    print("1. Loading configuration...")
    from config import Config
    config = Config()
    print("✅ Config loaded successfully")
    
    print("2. Creating Flask app...")
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.webapp.secret_key
    print("✅ Flask app created")
    
    print("3. Loading WebSocket components...")
    from websocket_config_manager import WebSocketConfigManager
    from websocket_cors_manager import CORSManager
    from websocket_factory import WebSocketFactory
    
    websocket_config_manager = WebSocketConfigManager(config)
    print("✅ WebSocket config manager loaded")
    
    websocket_cors_manager = CORSManager(websocket_config_manager)
    print("✅ WebSocket CORS manager loaded")
    
    websocket_factory = WebSocketFactory(websocket_config_manager, websocket_cors_manager)
    print("✅ WebSocket factory loaded")
    
    print("4. Creating SocketIO instance...")
    socketio = websocket_factory.create_socketio_instance(app)
    print("✅ SocketIO instance created successfully")
    
    print("5. Testing basic SocketIO functionality...")
    
    @socketio.on('connect')
    def test_connect():
        print("Test client connected")
        return True
    
    @socketio.on('disconnect')
    def test_disconnect():
        print("Test client disconnected")
    
    print("✅ SocketIO event handlers registered")
    
    print("6. Testing SocketIO configuration...")
    print(f"   - Async mode: {socketio.async_mode}")
    print(f"   - Server options: {socketio.server.eio.ping_timeout}s ping timeout")
    
    print("\n✅ All SocketIO components initialized successfully!")
    print("The issue is likely not with SocketIO initialization.")
    
    # Test a simple route
    @app.route('/test')
    def test_route():
        return "Test route working"
    
    print("\n7. Starting test server for 10 seconds...")
    import threading
    import time
    
    def stop_server():
        time.sleep(10)
        print("\n⏰ Stopping test server...")
        os._exit(0)
    
    # Start stop timer in background
    stop_thread = threading.Thread(target=stop_server)
    stop_thread.daemon = True
    stop_thread.start()
    
    # Start server
    print("🚀 Starting SocketIO server on http://127.0.0.1:5001...")
    socketio.run(app, host='127.0.0.1', port=5001, debug=False)
    
except Exception as e:
    print(f"❌ Error during SocketIO debug: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)