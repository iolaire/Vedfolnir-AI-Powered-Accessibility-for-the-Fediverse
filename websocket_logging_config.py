
# WebSocket Transport Logging Configuration

import logging

# Reduce Flask-SocketIO engine.io logging for upgrade errors
engineio_logger = logging.getLogger('engineio.server')
engineio_logger.setLevel(logging.WARNING)

# Create custom filter for WebSocket upgrade errors
class WebSocketUpgradeFilter(logging.Filter):
    def filter(self, record):
        # Reduce noise from expected upgrade failures
        if 'Invalid websocket upgrade' in record.getMessage():
            # Only log every 10th occurrence to reduce noise
            if not hasattr(self, 'upgrade_error_count'):
                self.upgrade_error_count = 0
            self.upgrade_error_count += 1
            return self.upgrade_error_count % 10 == 1
        return True

# Apply filter to engine.io logger
engineio_logger.addFilter(WebSocketUpgradeFilter())

print("🔧 WebSocket logging configuration applied")
