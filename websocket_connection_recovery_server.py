# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Server-Side WebSocket Connection Recovery System

Provides server-side support for intelligent connection recovery including:
- Connection state management and restoration
- Client reconnection tracking and optimization
- Transport fallback coordination
- Suspension detection and handling
- Recovery metrics and monitoring
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json


class ConnectionState(Enum):
    """Connection states for tracking client connections"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    SUSPENDED = "suspended"
    POLLING_MODE = "polling_mode"
    TRANSPORT_FALLBACK = "transport_fallback"
    RECOVERY_FAILED = "recovery_failed"


@dataclass
class ClientConnectionInfo:
    """Information about a client connection"""
    session_id: str
    user_id: Optional[int]
    namespace: str
    state: ConnectionState
    transport: str
    
    # Connection tracking
    connect_time: datetime
    last_activity: datetime
    disconnect_time: Optional[datetime] = None
    
    # Recovery tracking
    reconnect_attempts: int = 0
    last_reconnect_time: Optional[datetime] = None
    recovery_start_time: Optional[datetime] = None
    
    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Transport tracking
    original_transports: List[str] = field(default_factory=lambda: ["websocket", "polling"])
    current_transports: List[str] = field(default_factory=lambda: ["websocket", "polling"])
    transport_fallback_active: bool = False
    
    # Suspension detection
    suspension_detected: bool = False
    polling_mode_active: bool = False
    polling_mode_start: Optional[datetime] = None


class WebSocketConnectionRecoveryServer:
    """
    Server-side WebSocket connection recovery system
    
    Manages client connection states, coordinates recovery efforts,
    and provides metrics for monitoring connection health.
    """
    
    def __init__(self, socketio_instance, config: Optional[Dict[str, Any]] = None):
        """
        Initialize server-side connection recovery
        
        Args:
            socketio_instance: Flask-SocketIO instance
            config: Configuration dictionary
        """
        self.socketio = socketio_instance
        self.config = self._merge_config(config or {})
        self.logger = logging.getLogger(__name__)
        
        # Connection tracking
        self.connections: Dict[str, ClientConnectionInfo] = {}
        self.connection_lock = threading.RLock()
        
        # Recovery coordination
        self.recovery_handlers: Dict[str, Callable] = {}
        self.recovery_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'transport_fallbacks': 0,
            'suspension_detections': 0
        }
        
        # Background tasks
        self.cleanup_thread = None
        self.monitoring_thread = None
        self.shutdown_event = threading.Event()
        
        self._setup_event_handlers()
        self._start_background_tasks()
        
        self.logger.info("WebSocket Connection Recovery Server initialized")
    
    def _merge_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with defaults"""
        defaults = {
            # Connection tracking
            'max_reconnect_attempts': 10,
            'reconnect_timeout': 300,  # 5 minutes
            'activity_timeout': 600,   # 10 minutes
            
            # Cleanup configuration
            'cleanup_interval': 300,   # 5 minutes
            'stale_connection_timeout': 1800,  # 30 minutes
            
            # Monitoring configuration
            'monitoring_interval': 60,  # 1 minute
            'metrics_retention': 3600,  # 1 hour
            
            # Transport fallback
            'enable_transport_fallback': True,
            'fallback_transports': ['polling'],
            'fallback_timeout': 30,    # 30 seconds
            
            # Suspension detection
            'suspension_threshold': 120,  # 2 minutes
            'polling_mode_timeout': 600,  # 10 minutes
        }
        
        return {**defaults, **user_config}