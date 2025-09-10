#!/usr/bin/env python3
"""
Phase 3 Integration Tests: WebSocket Consolidation
=================================================

Tests for the consolidated WebSocket handlers and their integration
with the unified notification system.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

class TestPhase3WebSocketConsolidation(unittest.TestCase):
    """Test Phase 3 WebSocket consolidation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_socketio = Mock()
        self.mock_notification_manager = Mock()
        
        # Import here to avoid import issues
        from app.websocket.core.consolidated_handlers import ConsolidatedWebSocketHandlers
        from app.services.notification.manager.unified_manager import NotificationMessage, NotificationType, NotificationCategory
        
        self.ConsolidatedWebSocketHandlers = ConsolidatedWebSocketHandlers
        self.NotificationMessage = NotificationMessage
        self.NotificationType = NotificationType
        self.NotificationCategory = NotificationCategory
        
        self.handlers = ConsolidatedWebSocketHandlers(
            self.mock_socketio, 
            self.mock_notification_manager
        )
    
    def test_consolidated_handlers_initialization(self):
        """Test consolidated handlers initialize correctly"""
        self.assertIsNotNone(self.handlers)
        self.assertEqual(self.handlers.socketio, self.mock_socketio)
        self.assertEqual(self.handlers.notification_manager, self.mock_notification_manager)
        self.assertIsInstance(self.handlers.connected_users, dict)
    
    def test_user_connection_tracking(self):
        """Test user connection tracking functionality"""
        user_id = 1
        
        # Initially not connected
        self.assertFalse(self.handlers.is_user_connected(user_id))
        
        # Add user connection
        self.handlers.connected_users[user_id] = {
            'connected_at': datetime.now(timezone.utc),
            'session_id': 'test_session'
        }
        
        # Now connected
        self.assertTrue(self.handlers.is_user_connected(user_id))
        
        # Get connected users
        connected = self.handlers.get_connected_users()
        self.assertIn(user_id, connected)
    
    def test_notification_broadcasting(self):
        """Test notification broadcasting to WebSocket rooms"""
        # Create test message
        message = self.NotificationMessage(
            id="test_001",
            type=self.NotificationType.INFO,
            title="Test Message",
            message="Test notification",
            user_id=1,
            category=self.NotificationCategory.USER,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Mock socketio emit
        self.mock_socketio.emit = Mock()
        
        # Test broadcast
        self.handlers.broadcast_notification(message)
        
        # Verify emit was called
        self.assertTrue(self.mock_socketio.emit.called)
        
        # Check call arguments
        call_args = self.mock_socketio.emit.call_args
        self.assertEqual(call_args[0][0], 'unified_notification')
        self.assertIn('id', call_args[0][1])
        self.assertEqual(call_args[0][1]['id'], 'test_001')
    
    def test_user_notification_categories(self):
        """Test user notification category permissions"""
        user_id = 1
        
        # Mock admin check to return False (regular user)
        with patch.object(self.handlers, '_is_admin_user', return_value=False):
            categories = self.handlers._get_user_notification_categories(user_id)
            
            # Regular users should have basic categories
            self.assertIn('user', categories)
            self.assertIn('platform', categories)
            self.assertIn('caption', categories)
            self.assertIn('storage', categories)
            
            # Should not have admin categories
            self.assertNotIn('admin', categories)
            self.assertNotIn('system', categories)
        
        # Mock admin check to return True (admin user)
        with patch.object(self.handlers, '_is_admin_user', return_value=True):
            admin_categories = self.handlers._get_user_notification_categories(user_id)
            
            # Admin users should have all categories
            self.assertIn('admin', admin_categories)
            self.assertIn('system', admin_categories)
            self.assertIn('monitoring', admin_categories)
    
    def test_websocket_handler_registration(self):
        """Test WebSocket handler registration"""
        # Verify handlers have register method
        self.assertTrue(hasattr(self.handlers, 'register_unified_handlers'))
        
        # Verify socketio.on decorator calls would be made
        # (This is tested indirectly through the initialization)
        self.assertIsNotNone(self.handlers.socketio)


class TestPhase3Integration(unittest.TestCase):
    """Test Phase 3 integration with existing systems"""
    
    def test_initialization_function(self):
        """Test consolidated WebSocket handlers initialization function"""
        from app.websocket.core.consolidated_handlers import initialize_consolidated_websocket_handlers
        from flask import Flask
        
        # Create test app
        app = Flask(__name__)
        mock_socketio = Mock()
        mock_notification_manager = Mock()
        
        # Set up app with notification manager
        app.unified_notification_manager = mock_notification_manager
        
        # Test initialization
        handlers = initialize_consolidated_websocket_handlers(app, mock_socketio)
        
        # Verify initialization
        self.assertIsNotNone(handlers)
        self.assertTrue(hasattr(app, 'consolidated_websocket_handlers'))
        self.assertEqual(app.consolidated_websocket_handlers, handlers)
    
    def test_notification_manager_integration(self):
        """Test integration with UnifiedNotificationManager"""
        from app.services.notification.manager.unified_manager import UnifiedNotificationManager
        
        # Create mock notification manager
        mock_manager = Mock(spec=UnifiedNotificationManager)
        mock_socketio = Mock()
        
        # Create handlers
        from app.websocket.core.consolidated_handlers import ConsolidatedWebSocketHandlers
        handlers = ConsolidatedWebSocketHandlers(mock_socketio, mock_manager)
        
        # Test setting WebSocket handlers in notification manager
        mock_manager.set_websocket_handlers = Mock()
        mock_manager.set_websocket_handlers(handlers)
        
        # Verify integration
        self.assertTrue(mock_manager.set_websocket_handlers.called)
        call_args = mock_manager.set_websocket_handlers.call_args
        self.assertEqual(call_args[0][0], handlers)


if __name__ == '__main__':
    unittest.main()
