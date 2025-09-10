# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin User Management Notification Handler

Stub implementation for test compatibility.
"""

"""
⚠️  DEPRECATED: This file is deprecated and will be removed in a future version.
Please use the unified notification system instead:
- unified_notification_manager.py (core system)
- notification_service_adapters.py (service adapters)
- notification_helpers.py (helper functions)
- app/websocket/core/consolidated_handlers.py (WebSocket handling)

Migration guide: docs/implementation/notification-consolidation-final-summary.md
"""

import warnings
warnings.warn(
    "This notification system is deprecated. Use the unified notification system instead.",
    DeprecationWarning,
    stacklevel=2
)

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class UserOperationContext:
    """User operation context"""
    
    def __init__(self, operation_type: str, user_id: int, details: Dict[str, Any] = None):
        self.operation_type = operation_type
        self.user_id = user_id
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class AdminUserManagementNotificationHandler:
    """
    Stub implementation for admin user management notifications
    """
    
    def __init__(self, notification_manager):
        self.notification_manager = notification_manager
        self.operation_types = {
            'user_created': 'User Created',
            'user_updated': 'User Updated', 
            'user_deleted': 'User Deleted',
            'user_role_changed': 'User Role Changed',
            'user_status_changed': 'User Status Changed',
            'user_password_reset': 'Password Reset',
            'user_permissions_changed': 'Permissions Changed'
        }
        self._notification_count = 0
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return {
            'total_notifications': self._notification_count,
            'supported_operations': len(self.operation_types)
        }
    
    def send_user_operation_notification(self, context: UserOperationContext) -> bool:
        """Send user operation notification (stub)"""
        self._notification_count += 1
        return True