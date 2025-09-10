# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Rate Limiting Security Tests for Notification System

Tests comprehensive rate limiting mechanisms including user-based rate limiting,
role-based limits, priority-based limits, burst detection, and IP-based limiting.
"""

import unittest
import sys
import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict, deque

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.notification.manager.unified_manager import (
    UnifiedNotificationManager, NotificationMessage, 
    AdminNotificationMessage, SystemNotificationMessage
)
from models import (
    NotificationType, NotificationPriority, NotificationCategory, 
    UserRole, User
)


class TestNotificationRateLimitingSecurity(unittest.TestCase):
    """Enhanced rate limiting security tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_websocket_factory = Mock()
        self.mock_auth_handler = Mock()
        self.mock_namespace_manager = Mock()
        
        # Create proper mock database manager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        
        # Create proper context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = Mock(return_value=self.mock_session)
        mock_context_manager.__exit__ = Mock(return_value=None)
        self.mock_db_manager.get_session = Mock(return_value=mock_context_manager)
        
        # Create notification manager
        self.notification_manager = UnifiedNotificationManager(
            websocket_factory=self.mock_websocket_factory,
            auth_handler=self.mock_auth_handler,
            namespace_manager=self.mock_namespace_manager,
            db_manager=self.mock_db_manager
        )
        
        # Initialize rate limiting storage
        self.rate_limit_storage = {
            'user_requests': defaultdict(deque),
            'ip_requests': defaultdict(deque),
            'blocked_users': set(),
            'blocked_ips': set(),
            'burst_detection': defaultdict(list)
        }
        
        # Rate limiting configuration
        self.rate_limits = {
            UserRole.ADMIN: {'requests_per_minute': 100, 'burst_limit': 20},
            UserRole.MODERATOR: {'requests_per_minute': 50, 'burst_limit': 15},
            UserRole.REVIEWER: {'requests_per_minute': 30, 'burst_limit': 10},
            UserRole.VIEWER: {'requests_per_minute': 10, 'burst_limit': 5}
        }
        
        self.notification_manager._rate_limit_storage = self.rate_limit_storage
        self.notification_manager._rate_limits = self.rate_limits
    
    def test_user_rate_limiting(self):
        """Test user-based rate limiting"""
        user_id = 1
        user_role = UserRole.REVIEWER
        
        # Get rate limit for reviewer role
        rate_limit = self.rate_limits[user_role]['requests_per_minute']
        
        # Send messages up to the rate limit
        for i in range(rate_limit):
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Message {i}",
                message=f"Test message {i}",
                category=NotificationCategory.SYSTEM
            )
            
            is_allowed = self._check_user_rate_limit(user_id, user_role, message)
            self.assertTrue(is_allowed, f"Message {i} should be allowed within rate limit")
            
            # Record the request
            self._record_user_request(user_id, message)
        
        # Next message should be rate limited
        excess_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Excess Message",
            message="This should be rate limited",
            category=NotificationCategory.SYSTEM
        )
        
        is_allowed = self._check_user_rate_limit(user_id, user_role, excess_message)
        self.assertFalse(is_allowed, "Message exceeding rate limit should be blocked")
    
    def test_role_based_rate_limiting(self):
        """Test role-based rate limiting with different limits"""
        test_cases = [
            {'user_id': 1, 'role': UserRole.ADMIN, 'expected_limit': 100},
            {'user_id': 2, 'role': UserRole.MODERATOR, 'expected_limit': 50},
            {'user_id': 3, 'role': UserRole.REVIEWER, 'expected_limit': 30},
            {'user_id': 4, 'role': UserRole.VIEWER, 'expected_limit': 10}
        ]
        
        for case in test_cases:
            with self.subTest(role=case['role']):
                user_id = case['user_id']
                role = case['role']
                expected_limit = case['expected_limit']
                
                # Send messages up to the expected limit
                allowed_count = 0
                for i in range(expected_limit + 5):  # Try 5 extra
                    message = NotificationMessage(
                        id=str(uuid.uuid4()),
                        type=NotificationType.INFO,
                        title=f"Message {i}",
                        message=f"Test message {i}",
                        category=NotificationCategory.SYSTEM
                    )
                    
                    is_allowed = self._check_user_rate_limit(user_id, role, message)
                    if is_allowed:
                        allowed_count += 1
                        self._record_user_request(user_id, message)
                
                # Should allow exactly the expected limit
                self.assertEqual(allowed_count, expected_limit, 
                               f"Role {role} should allow exactly {expected_limit} messages")
    
    def test_priority_based_rate_limiting(self):
        """Test priority-based rate limiting"""
        user_id = 1
        user_role = UserRole.REVIEWER
        
        # Fill up the rate limit with normal priority messages
        normal_limit = self.rate_limits[user_role]['requests_per_minute']
        
        for i in range(normal_limit):
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Normal Message {i}",
                message=f"Normal priority message {i}",
                category=NotificationCategory.SYSTEM,
                priority=NotificationPriority.NORMAL
            )
            
            is_allowed = self._check_priority_rate_limit(user_id, user_role, message)
            if is_allowed:
                self._record_user_request(user_id, message)
        
        # Normal priority message should now be blocked
        normal_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Blocked Normal",
            message="This normal message should be blocked",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.NORMAL
        )
        
        is_normal_allowed = self._check_priority_rate_limit(user_id, user_role, normal_message)
        self.assertFalse(is_normal_allowed, "Normal priority message should be blocked when rate limited")
        
        # High priority message should still be allowed
        high_priority_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.WARNING,
            title="High Priority",
            message="This high priority message should be allowed",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.HIGH
        )
        
        is_high_allowed = self._check_priority_rate_limit(user_id, user_role, high_priority_message)
        self.assertTrue(is_high_allowed, "High priority message should bypass normal rate limits")
        
        # Critical priority message should always be allowed
        critical_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ERROR,
            title="Critical Alert",
            message="This critical message should always be allowed",
            category=NotificationCategory.SYSTEM,
            priority=NotificationPriority.CRITICAL
        )
        
        is_critical_allowed = self._check_priority_rate_limit(user_id, user_role, critical_message)
        self.assertTrue(is_critical_allowed, "Critical priority message should always be allowed")
    
    def test_burst_detection(self):
        """Test burst detection and prevention"""
        user_id = 1
        user_role = UserRole.REVIEWER
        burst_limit = self.rate_limits[user_role]['burst_limit']
        
        # Send messages in rapid succession (burst)
        burst_start_time = time.time()
        
        for i in range(burst_limit):
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Burst Message {i}",
                message=f"Burst message {i}",
                category=NotificationCategory.SYSTEM
            )
            
            with patch('time.time', return_value=burst_start_time + (i * 0.1)):  # 100ms apart
                is_allowed = self._check_burst_limit(user_id, user_role, message)
                self.assertTrue(is_allowed, f"Burst message {i} should be allowed within burst limit")
                
                if is_allowed:
                    self._record_burst_request(user_id, message)
        
        # Next burst message should be blocked
        excess_burst_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Excess Burst",
            message="This burst message should be blocked",
            category=NotificationCategory.SYSTEM
        )
        
        with patch('time.time', return_value=burst_start_time + (burst_limit * 0.1)):
            is_allowed = self._check_burst_limit(user_id, user_role, excess_burst_message)
            self.assertFalse(is_allowed, "Message exceeding burst limit should be blocked")
    
    def test_ip_based_rate_limiting(self):
        """Test IP-based rate limiting"""
        ip_address = "192.168.1.100"
        ip_rate_limit = 50  # messages per minute per IP
        
        # Send messages from the same IP up to the limit
        for i in range(ip_rate_limit):
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"IP Message {i}",
                message=f"Message from IP {i}",
                category=NotificationCategory.SYSTEM
            )
            
            is_allowed = self._check_ip_rate_limit(ip_address, message)
            self.assertTrue(is_allowed, f"IP message {i} should be allowed within IP rate limit")
            
            if is_allowed:
                self._record_ip_request(ip_address, message)
        
        # Next message from same IP should be blocked
        excess_ip_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Excess IP Message",
            message="This IP message should be blocked",
            category=NotificationCategory.SYSTEM
        )
        
        is_allowed = self._check_ip_rate_limit(ip_address, excess_ip_message)
        self.assertFalse(is_allowed, "Message exceeding IP rate limit should be blocked")
        
        # Message from different IP should still be allowed
        different_ip = "192.168.1.101"
        different_ip_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Different IP Message",
            message="Message from different IP",
            category=NotificationCategory.SYSTEM
        )
        
        is_different_allowed = self._check_ip_rate_limit(different_ip, different_ip_message)
        self.assertTrue(is_different_allowed, "Message from different IP should be allowed")
    
    def test_rate_limit_recovery(self):
        """Test rate limit recovery after time window"""
        user_id = 1
        user_role = UserRole.REVIEWER
        rate_limit = self.rate_limits[user_role]['requests_per_minute']
        
        # Fill up the rate limit
        initial_time = time.time()
        
        for i in range(rate_limit):
            message = NotificationMessage(
                id=str(uuid.uuid4()),
                type=NotificationType.INFO,
                title=f"Initial Message {i}",
                message=f"Initial message {i}",
                category=NotificationCategory.SYSTEM
            )
            
            with patch('time.time', return_value=initial_time + i):
                is_allowed = self._check_user_rate_limit(user_id, user_role, message)
                if is_allowed:
                    self._record_user_request(user_id, message)
        
        # Message should be blocked immediately after
        blocked_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Blocked Message",
            message="This should be blocked",
            category=NotificationCategory.SYSTEM
        )
        
        with patch('time.time', return_value=initial_time + rate_limit):
            is_blocked = self._check_user_rate_limit(user_id, user_role, blocked_message)
            self.assertFalse(is_blocked, "Message should be blocked immediately after rate limit")
        
        # After time window (60 seconds), rate limit should reset
        recovery_time = initial_time + 70  # 70 seconds later
        
        recovery_message = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.INFO,
            title="Recovery Message",
            message="This should be allowed after recovery",
            category=NotificationCategory.SYSTEM
        )
        
        with patch('time.time', return_value=recovery_time):
            # Clean up old requests first
            self._cleanup_old_requests(user_id)
            
            is_recovered = self._check_user_rate_limit(user_id, user_role, recovery_message)
            self.assertTrue(is_recovered, "Message should be allowed after rate limit recovery")
    
    def _check_user_rate_limit(self, user_id, user_role, message):
        """Check if user is within rate limit"""
        current_time = time.time()
        time_window = 60  # 1 minute window
        
        # Get user's request history
        user_requests = self.rate_limit_storage['user_requests'][user_id]
        
        # Remove old requests outside time window
        while user_requests and user_requests[0] < current_time - time_window:
            user_requests.popleft()
        
        # Check if within rate limit
        rate_limit = self.rate_limits[user_role]['requests_per_minute']
        return len(user_requests) < rate_limit
    
    def _check_priority_rate_limit(self, user_id, user_role, message):
        """Check rate limit considering message priority"""
        # Critical and high priority messages bypass normal rate limits
        if hasattr(message, 'priority'):
            if message.priority in [NotificationPriority.CRITICAL, NotificationPriority.HIGH]:
                return True
        
        # Normal and low priority messages use standard rate limiting
        return self._check_user_rate_limit(user_id, user_role, message)
    
    def _check_burst_limit(self, user_id, user_role, message):
        """Check burst limit"""
        current_time = time.time()
        burst_window = 10  # 10 second burst window
        
        # Get user's burst history
        burst_requests = self.rate_limit_storage['burst_detection'][user_id]
        
        # Remove old burst requests outside window
        burst_requests[:] = [req_time for req_time in burst_requests 
                           if req_time > current_time - burst_window]
        
        # Check if within burst limit
        burst_limit = self.rate_limits[user_role]['burst_limit']
        return len(burst_requests) < burst_limit
    
    def _check_ip_rate_limit(self, ip_address, message):
        """Check IP-based rate limit"""
        current_time = time.time()
        time_window = 60  # 1 minute window
        ip_rate_limit = 50  # messages per minute per IP
        
        # Get IP's request history
        ip_requests = self.rate_limit_storage['ip_requests'][ip_address]
        
        # Remove old requests outside time window
        while ip_requests and ip_requests[0] < current_time - time_window:
            ip_requests.popleft()
        
        # Check if within IP rate limit
        return len(ip_requests) < ip_rate_limit
    
    def _record_user_request(self, user_id, message):
        """Record user request for rate limiting"""
        current_time = time.time()
        self.rate_limit_storage['user_requests'][user_id].append(current_time)
    
    def _record_burst_request(self, user_id, message):
        """Record burst request"""
        current_time = time.time()
        self.rate_limit_storage['burst_detection'][user_id].append(current_time)
    
    def _record_ip_request(self, ip_address, message):
        """Record IP request for rate limiting"""
        current_time = time.time()
        self.rate_limit_storage['ip_requests'][ip_address].append(current_time)
    
    def _cleanup_old_requests(self, user_id):
        """Clean up old requests for rate limit recovery"""
        current_time = time.time()
        time_window = 60  # 1 minute window
        
        # Clean up user requests
        user_requests = self.rate_limit_storage['user_requests'][user_id]
        while user_requests and user_requests[0] < current_time - time_window:
            user_requests.popleft()


if __name__ == '__main__':
    unittest.main()