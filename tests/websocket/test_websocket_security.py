# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Tests for WebSocket Security System

This module contains comprehensive tests for WebSocket security features including
CSRF protection, rate limiting, input validation, and abuse detection.
"""

import unittest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from websocket_security_manager import (
    WebSocketSecurityManager, WebSocketSecurityConfig, ConnectionInfo,
    WebSocketSecurityEventType
)
from websocket_abuse_detector import (
    WebSocketAbuseDetector, AbuseType, AbuseAction, AbusePattern,
    ConnectionMetrics
)
from app.core.security.monitoring.security_event_logger import SecurityEventSeverity


class TestWebSocketSecurityManager(unittest.TestCase):
    """Test WebSocket Security Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_session_manager = Mock()
        self.mock_db_session = Mock()
        
        # Setup mock database session
        self.mock_db_manager.get_session.return_value.__enter__.return_value = self.mock_db_session
        self.mock_db_manager.get_session.return_value.__exit__.return_value = None
        
        # Create security config
        self.security_config = WebSocketSecurityConfig(
            csrf_enabled=True,
            rate_limiting_enabled=True,
            input_validation_enabled=True,
            connection_monitoring_enabled=True,
            abuse_detection_enabled=True,
            max_connections_per_ip=5,
            max_connections_per_user=3,
            message_rate_limit=10
        )
        
        # Create security manager
        self.security_manager = WebSocketSecurityManager(
            self.mock_db_manager,
            self.mock_session_manager,
            self.security_config
        )
    
    @patch('websocket_security_manager.request')
    def test_validate_connection_success(self, mock_request):
        """Test successful connection validation"""
        # Setup mock request
        mock_request.remote_addr = '127.0.0.1'
        mock_request.headers = {'User-Agent': 'Test Browser'}
        
        # Setup mock session
        self.mock_session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'testuser'
        }
        
        # Mock user lookup
        mock_user = Mock()
        mock_user.role.value = 'user'
        self.mock_db_session.get.return_value = mock_user
        
        # Test connection validation
        allowed, reason, connection_info = self.security_manager.validate_connection(
            {'session_id': 'test_session'}, '/'
        )
        
        self.assertTrue(allowed)
        self.assertIsNone(reason)
        self.assertIsNotNone(connection_info)
        self.assertEqual(connection_info['user_id'], 1)
        self.assertEqual(connection_info['ip_address'], '127.0.0.1')
    
    @patch('websocket_security_manager.request')
    def test_validate_connection_rate_limit_exceeded(self, mock_request):
        """Test connection validation with rate limit exceeded"""
        # Setup mock request
        mock_request.remote_addr = '127.0.0.1'
        mock_request.headers = {'User-Agent': 'Test Browser'}
        
        # Simulate multiple connection attempts
        for i in range(self.security_config.connection_rate_limit + 1):
            allowed, reason, connection_info = self.security_manager.validate_connection(
                {'session_id': f'test_session_{i}'}, '/'
            )
            
            if i < self.security_config.connection_rate_limit:
                self.assertTrue(allowed)
            else:
                self.assertFalse(allowed)
                self.assertEqual(reason, "Connection rate limit exceeded")
    
    @patch('websocket_security_manager.request')
    def test_validate_connection_max_connections_per_ip(self, mock_request):
        """Test connection validation with max connections per IP exceeded"""
        # Setup mock request
        mock_request.remote_addr = '127.0.0.1'
        mock_request.headers = {'User-Agent': 'Test Browser'}
        
        # Create multiple connections from same IP
        for i in range(self.security_config.max_connections_per_ip):
            allowed, reason, connection_info = self.security_manager.validate_connection(
                {'session_id': f'test_session_{i}'}, '/'
            )
            self.assertTrue(allowed)
        
        # Next connection should be rejected
        allowed, reason, connection_info = self.security_manager.validate_connection(
            {'session_id': 'test_session_overflow'}, '/'
        )
        
        self.assertFalse(allowed)
        self.assertEqual(reason, "Too many connections from this IP")
    
    @patch('websocket_security_manager.request')
    def test_validate_connection_admin_namespace(self, mock_request):
        """Test admin namespace access validation"""
        # Setup mock request
        mock_request.remote_addr = '127.0.0.1'
        mock_request.headers = {'User-Agent': 'Test Browser'}
        
        # Setup mock session for regular user
        self.mock_session_manager.get_session_data.return_value = {
            'user_id': 1,
            'username': 'testuser'
        }
        
        # Mock regular user
        mock_user = Mock()
        mock_user.role.value = 'user'
        from models import UserRole
        mock_user.role = UserRole.USER
        self.mock_db_session.get.return_value = mock_user
        
        # Test admin namespace access (should be denied)
        allowed, reason, connection_info = self.security_manager.validate_connection(
            {'session_id': 'test_session'}, '/admin'
        )
        
        self.assertFalse(allowed)
        self.assertEqual(reason, "Admin access required")
    
    def test_validate_message_success(self):
        """Test successful message validation"""
        # Create a test connection
        connection = ConnectionInfo(
            session_id='test_session',
            user_id=1,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            namespace='/',
            connected_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            is_authenticated=True,
            is_admin=False
        )
        
        self.security_manager.active_connections['test_session'] = connection
        
        # Test message validation
        allowed, reason, sanitized_data = self.security_manager.validate_message(
            'message', {'content': 'Hello world'}, 'test_session'
        )
        
        self.assertTrue(allowed)
        self.assertIsNone(reason)
        self.assertIsNotNone(sanitized_data)
    
    def test_validate_message_rate_limit_exceeded(self):
        """Test message validation with rate limit exceeded"""
        # Create a test connection
        connection = ConnectionInfo(
            session_id='test_session',
            user_id=1,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            namespace='/',
            connected_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            is_authenticated=True,
            is_admin=False
        )
        
        self.security_manager.active_connections['test_session'] = connection
        
        # Send messages up to rate limit
        for i in range(self.security_config.message_rate_limit):
            allowed, reason, sanitized_data = self.security_manager.validate_message(
                'message', {'content': f'Message {i}'}, 'test_session'
            )
            self.assertTrue(allowed)
        
        # Next message should be rate limited
        allowed, reason, sanitized_data = self.security_manager.validate_message(
            'message', {'content': 'Rate limited message'}, 'test_session'
        )
        
        self.assertFalse(allowed)
        self.assertEqual(reason, "Message rate limit exceeded")
    
    def test_validate_message_invalid_event_type(self):
        """Test message validation with invalid event type"""
        # Create a test connection
        connection = ConnectionInfo(
            session_id='test_session',
            user_id=1,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            namespace='/',
            connected_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            is_authenticated=True,
            is_admin=False
        )
        
        self.security_manager.active_connections['test_session'] = connection
        
        # Test with invalid event type
        allowed, reason, sanitized_data = self.security_manager.validate_message(
            'invalid_event', {'content': 'Hello world'}, 'test_session'
        )
        
        self.assertFalse(allowed)
        self.assertEqual(reason, "Invalid event type")
    
    def test_validate_message_too_large(self):
        """Test message validation with oversized payload"""
        # Create a test connection
        connection = ConnectionInfo(
            session_id='test_session',
            user_id=1,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            namespace='/',
            connected_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            is_authenticated=True,
            is_admin=False
        )
        
        self.security_manager.active_connections['test_session'] = connection
        
        # Create oversized message
        large_content = 'x' * (self.security_config.max_message_size + 1)
        
        # Test with oversized message
        allowed, reason, sanitized_data = self.security_manager.validate_message(
            'message', {'content': large_content}, 'test_session'
        )
        
        self.assertFalse(allowed)
        self.assertEqual(reason, "Message too large")
    
    def test_cleanup_expired_connections(self):
        """Test cleanup of expired connections"""
        # Create expired connection
        old_time = datetime.now(timezone.utc) - timedelta(seconds=self.security_config.connection_timeout + 1)
        expired_connection = ConnectionInfo(
            session_id='expired_session',
            user_id=1,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            namespace='/',
            connected_at=old_time,
            last_activity=old_time,
            is_authenticated=True,
            is_admin=False
        )
        
        # Create active connection
        active_connection = ConnectionInfo(
            session_id='active_session',
            user_id=2,
            ip_address='127.0.0.2',
            user_agent='Test Browser',
            namespace='/',
            connected_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            is_authenticated=True,
            is_admin=False
        )
        
        self.security_manager.active_connections['expired_session'] = expired_connection
        self.security_manager.active_connections['active_session'] = active_connection
        
        # Run cleanup
        self.security_manager.cleanup_expired_connections()
        
        # Check that expired connection was removed
        self.assertNotIn('expired_session', self.security_manager.active_connections)
        self.assertIn('active_session', self.security_manager.active_connections)
    
    def test_get_security_stats(self):
        """Test security statistics generation"""
        # Create some test connections
        for i in range(3):
            connection = ConnectionInfo(
                session_id=f'test_session_{i}',
                user_id=i + 1,
                ip_address=f'127.0.0.{i + 1}',
                user_agent='Test Browser',
                namespace='/',
                connected_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                is_authenticated=True,
                is_admin=(i == 0)  # First connection is admin
            )
            self.security_manager.active_connections[f'test_session_{i}'] = connection
        
        # Get stats
        stats = self.security_manager.get_security_stats()
        
        # Verify stats
        self.assertEqual(stats['connections']['total'], 3)
        self.assertEqual(stats['connections']['authenticated'], 3)
        self.assertEqual(stats['connections']['admin'], 1)
        self.assertEqual(stats['connections']['anonymous'], 0)
        
        self.assertTrue(stats['security']['csrf_enabled'])
        self.assertTrue(stats['security']['rate_limiting_enabled'])
        self.assertTrue(stats['security']['input_validation_enabled'])
        self.assertTrue(stats['security']['abuse_detection_enabled'])


class TestWebSocketAbuseDetector(unittest.TestCase):
    """Test WebSocket Abuse Detector functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_security_logger = Mock()
        self.abuse_detector = WebSocketAbuseDetector(self.mock_security_logger)
    
    def test_track_connection(self):
        """Test connection tracking"""
        # Track a connection
        self.abuse_detector.track_connection(
            'test_session', 1, '127.0.0.1', 'Test Browser'
        )
        
        # Verify connection is tracked
        self.assertIn('test_session', self.abuse_detector.connection_metrics)
        
        metrics = self.abuse_detector.connection_metrics['test_session']
        self.assertEqual(metrics.user_id, 1)
        self.assertEqual(metrics.ip_address, '127.0.0.1')
        self.assertEqual(metrics.connection_attempts, 1)
    
    def test_track_message(self):
        """Test message tracking"""
        # First track a connection
        self.abuse_detector.track_connection(
            'test_session', 1, '127.0.0.1', 'Test Browser'
        )
        
        # Track messages
        for i in range(5):
            self.abuse_detector.track_message(
                'test_session', 'message', 100, False, False
            )
        
        # Verify message tracking
        metrics = self.abuse_detector.connection_metrics['test_session']
        self.assertEqual(metrics.total_messages, 5)
        self.assertIn('message', metrics.unique_event_types)
    
    def test_connection_flood_detection(self):
        """Test connection flood abuse detection"""
        # Simulate connection flood
        for i in range(25):  # Exceed threshold of 20
            self.abuse_detector.track_connection(
                f'test_session_{i}', None, '127.0.0.1', 'Test Browser'
            )
        
        # Verify abuse event was logged
        self.mock_security_logger.log_security_event.assert_called()
        
        # Check if IP is blocked
        self.assertTrue(self.abuse_detector.is_ip_blocked('127.0.0.1'))
    
    def test_message_flood_detection(self):
        """Test message flood abuse detection"""
        # Track a connection
        self.abuse_detector.track_connection(
            'test_session', 1, '127.0.0.1', 'Test Browser'
        )
        
        # Simulate message flood
        for i in range(105):  # Exceed threshold of 100
            self.abuse_detector.track_message(
                'test_session', 'message', 100, False, False
            )
        
        # Verify abuse event was logged
        self.mock_security_logger.log_security_event.assert_called()
    
    def test_authentication_abuse_detection(self):
        """Test authentication abuse detection"""
        # Track a connection
        self.abuse_detector.track_connection(
            'test_session', 1, '127.0.0.1', 'Test Browser'
        )
        
        # Simulate authentication failures
        for i in range(6):  # Exceed threshold of 5
            self.abuse_detector.track_authentication_failure('test_session')
        
        # Verify abuse event was logged
        self.mock_security_logger.log_security_event.assert_called()
    
    def test_is_ip_blocked(self):
        """Test IP blocking functionality"""
        # Initially not blocked
        self.assertFalse(self.abuse_detector.is_ip_blocked('127.0.0.1'))
        
        # Block IP
        block_until = datetime.now(timezone.utc) + timedelta(hours=1)
        self.abuse_detector.blocked_ips['127.0.0.1'] = block_until
        
        # Should be blocked
        self.assertTrue(self.abuse_detector.is_ip_blocked('127.0.0.1'))
        
        # Block expired IP
        expired_block = datetime.now(timezone.utc) - timedelta(hours=1)
        self.abuse_detector.blocked_ips['127.0.0.2'] = expired_block
        
        # Should not be blocked (expired)
        self.assertFalse(self.abuse_detector.is_ip_blocked('127.0.0.2'))
    
    def test_get_abuse_stats(self):
        """Test abuse statistics generation"""
        # Create some test data
        self.abuse_detector.track_connection(
            'test_session_1', 1, '127.0.0.1', 'Test Browser'
        )
        self.abuse_detector.track_connection(
            'test_session_2', 2, '127.0.0.2', 'Test Browser'
        )
        
        # Get stats
        stats = self.abuse_detector.get_abuse_stats()
        
        # Verify stats structure
        self.assertIn('abuse_events', stats)
        self.assertIn('blocks', stats)
        self.assertIn('connections', stats)
        self.assertIn('patterns', stats)
        
        self.assertEqual(stats['connections']['active_connections'], 2)
        self.assertEqual(stats['connections']['unique_ips'], 2)
        self.assertEqual(stats['connections']['unique_users'], 2)
    
    def test_cleanup_old_data(self):
        """Test cleanup of old tracking data"""
        # Create old connection
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        
        self.abuse_detector.track_connection(
            'old_session', 1, '127.0.0.1', 'Test Browser'
        )
        
        # Manually set old timestamp
        self.abuse_detector.connection_metrics['old_session'].last_activity = old_time
        
        # Create recent connection
        self.abuse_detector.track_connection(
            'recent_session', 2, '127.0.0.2', 'Test Browser'
        )
        
        # Run cleanup
        self.abuse_detector.cleanup_old_data()
        
        # Verify old data was cleaned up
        self.assertNotIn('old_session', self.abuse_detector.connection_metrics)
        self.assertIn('recent_session', self.abuse_detector.connection_metrics)


class TestWebSocketSecurityConfig(unittest.TestCase):
    """Test WebSocket Security Configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = WebSocketSecurityConfig()
        
        self.assertTrue(config.csrf_enabled)
        self.assertTrue(config.rate_limiting_enabled)
        self.assertTrue(config.input_validation_enabled)
        self.assertTrue(config.connection_monitoring_enabled)
        self.assertTrue(config.abuse_detection_enabled)
        
        self.assertEqual(config.connection_rate_limit, 10)
        self.assertEqual(config.message_rate_limit, 60)
        self.assertEqual(config.max_message_size, 10000)
        self.assertEqual(config.max_connections_per_ip, 20)
        self.assertEqual(config.max_connections_per_user, 10)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = WebSocketSecurityConfig(
            csrf_enabled=False,
            rate_limiting_enabled=False,
            connection_rate_limit=5,
            message_rate_limit=30,
            max_message_size=5000
        )
        
        self.assertFalse(config.csrf_enabled)
        self.assertFalse(config.rate_limiting_enabled)
        self.assertEqual(config.connection_rate_limit, 5)
        self.assertEqual(config.message_rate_limit, 30)
        self.assertEqual(config.max_message_size, 5000)
    
    def test_allowed_event_types(self):
        """Test allowed event types configuration"""
        config = WebSocketSecurityConfig()
        
        # Check default allowed event types
        self.assertIn('connect', config.allowed_event_types)
        self.assertIn('disconnect', config.allowed_event_types)
        self.assertIn('message', config.allowed_event_types)
        self.assertIn('admin_action', config.allowed_event_types)
        
        # Test custom allowed event types
        custom_events = {'custom_event', 'another_event'}
        config = WebSocketSecurityConfig(allowed_event_types=custom_events)
        
        self.assertEqual(config.allowed_event_types, custom_events)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)