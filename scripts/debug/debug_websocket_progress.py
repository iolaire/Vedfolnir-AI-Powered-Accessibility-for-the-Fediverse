#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Debug WebSocket progress handler initialization
"""

import os
import sys
import signal
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def timeout_handler(signum, frame):
    print("❌ TIMEOUT: Operation took too long, likely hanging")
    sys.exit(1)

# Set timeout for 30 seconds
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

print("=== WebSocket Progress Handler Debug ===")

try:
    print("1. Loading basic configuration...")
    from config import Config
    config = Config()
    print("✅ Config loaded")
    
    print("2. Loading database manager...")
    from database import DatabaseManager
    db_manager = DatabaseManager(config)
    print("✅ Database manager loaded")
    
    print("3. Loading progress tracker...")
    from progress_tracker import ProgressTracker
    progress_tracker = ProgressTracker(db_manager)
    print("✅ Progress tracker loaded")
    
    print("4. Loading task queue manager...")
    from task_queue_manager import TaskQueueManager
    task_queue_manager = TaskQueueManager(db_manager)
    print("✅ Task queue manager loaded")
    
    print("5. Creating minimal Flask app...")
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.webapp.secret_key
    print("✅ Flask app created")
    
    print("6. Creating minimal SocketIO instance...")
    from flask_socketio import SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    print("✅ SocketIO instance created")
    
    print("7. Loading WebSocket progress handler...")
    from websocket_progress_handler import WebSocketProgressHandler, AdminDashboardWebSocket
    print("✅ WebSocket progress handler imported")
    
    print("8. Initializing WebSocket progress handler...")
    websocket_progress_handler = WebSocketProgressHandler(socketio, db_manager, progress_tracker, task_queue_manager)
    print("✅ WebSocket progress handler initialized")
    
    print("9. Initializing admin dashboard WebSocket...")
    admin_dashboard_websocket = AdminDashboardWebSocket(socketio, db_manager)
    print("✅ Admin dashboard WebSocket initialized")
    
    print("\n✅ All WebSocket progress components initialized successfully!")
    print("The WebSocket progress handler is not the source of the hang.")
    
except Exception as e:
    print(f"❌ Error during WebSocket progress handler debug: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cancel the alarm
    signal.alarm(0)