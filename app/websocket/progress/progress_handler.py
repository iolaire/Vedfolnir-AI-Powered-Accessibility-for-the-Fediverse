# Copyright (C) 2025 iolaire mcfadden.
# WebSocket Progress Handler

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask_socketio import emit

logger = logging.getLogger(__name__)

class WebSocketProgressHandler:
    """Handles WebSocket progress updates for long-running operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def emit_progress(self, client_id: str, operation_id: str, progress: int, 
                     message: str = "", data: Optional[Dict[str, Any]] = None):
        """Emit progress update to specific client"""
        try:
            progress_data = {
                'operation_id': operation_id,
                'progress': progress,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data or {}
            }
            
            emit('progress_update', progress_data, room=client_id)
            self.logger.debug(f"Sent progress update to {client_id}: {progress}%")
            
        except Exception as e:
            self.logger.error(f"Error emitting progress: {e}")
    
    def emit_completion(self, client_id: str, operation_id: str, 
                       success: bool = True, result: Optional[Dict[str, Any]] = None):
        """Emit operation completion to specific client"""
        try:
            completion_data = {
                'operation_id': operation_id,
                'completed': True,
                'success': success,
                'timestamp': datetime.utcnow().isoformat(),
                'result': result or {}
            }
            
            emit('operation_complete', completion_data, room=client_id)
            self.logger.debug(f"Sent completion to {client_id}: success={success}")
            
        except Exception as e:
            self.logger.error(f"Error emitting completion: {e}")
