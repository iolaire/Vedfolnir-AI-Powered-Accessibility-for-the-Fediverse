# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for responsiveness error recovery functionality.

Tests the enhanced error handling with responsiveness recovery mechanisms,
including connection recovery, memory cleanup, and admin alert integration.
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from responsiveness_error_recovery import (
    ResponsivenessErrorRecoveryManager,
    ResponsivenessIssueType,
    ResponsivenessRecoveryAction,
    with_responsiveness_recovery
)
from database_responsiveness_recovery import (
    DatabaseResponsivenessRecoveryMixin,
    EnhancedDatabaseManager,
    with_database_recovery
)
from session_error_handling import SessionErrorHandler
from models import NotificationType, NotificationPriority

class TestResponsivenessErrorRecoveryManager(unittest.TestCase):
    """Test responsiveness error recovery manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_system_optimizer = Mock()
        self.recovery_manager = ResponsivenessErrorRecoveryManager(
            db_manager=self.mock_db_manager,
            system_optimizer=self.mock_system_optimizer
        )
    
    def test_initialization(self):
        """Test recovery manager initialization"""
        self.assertIsNotNone(self.recovery_manager.recovery_actions)
        self.assertIsNotNone(self.recovery_manager.performance_thresholds)
        self.assertEqual(self.recovery_manager.recovery_stats['total_recoveries'], 0)
        
        # Check that recovery actions are properly initialized
        self.assertIn(ResponsivenessIssueType.CONNECTION_LEAK, self.recovery_manager.recovery_actions)
        self.assertIn(ResponsivenessIssueType.MEMORY_LEAK, self.recovery_manager.recovery_actions)
        
        # Verify recovery actions have required attributes
        connection_actions = self.recovery_manager.recovery_actions[ResponsivenessIssueType.CONNECTION_LEAK]
        self.assertTrue(len(connection_actions) > 0)
        
        for action in connection_actions:
            self.assertIsInstance(action, ResponsivenessRecoveryAction)
            self.assertIsNotNone(action.action_type)
            self.assertIsNotNone(action.description)
            self.assertIsInstance(action.priority, int)
    
    @patch('responsiveness_error_recovery.send_admin_notification')
    async def test_handle_database_connection_recovery_success(self, mock_send_notification):
        """Test successful database connection recovery"""
        mock_send_notification.return_value = True
        
        # Mock successful connection recovery
        self.mock_db_manager.detect_and_cleanup_connection_leaks.return_value = {
            'cleaned_sessions': 3,
            'long_lived_sessions_found': 2,
            'cleanup_actions': ['cleaned_session_123', 'cleaned_session_456']
        }
        
        self.mock_db_manager.monitor_connection_health.return_value = {
            'overall_health': 'HEALTHY',
            'issues': [],
            'recommendations': []
        }
        
        # Mock successful connection test
        with patch.object(self.recovery_manager, '_test_database_connection', return_value=True):
            error = ConnectionError("Database connection lost")
            context = {'operation': 'test_operation', 'user_id': 1}
            
            result = await self.recovery_manager.handle_database_connection_recovery(error, context)
            
            # Verify recovery was successful
            self.assertTrue(result['success'])
            self.assertTrue(result['error_resolved'])
            self.assertGreater(len(result['actions_taken']), 0)
            self.assertGreater(result['recovery_time'], 0)
            
            # Verify admin notification was sent
            mock_send_notification.assert_called()
            call_args = mock_send_notification.call_args
            self.assertEqual(call_args[1]['notification_type'], NotificationType.SUCCESS)
            
            # Verify recovery statistics were updated
            self.assertEqual(self.recovery_manager.recovery_stats['total_recoveries'], 1)
            self.assertEqual(self.recovery_manager.recovery_stats['successful_recoveries'], 1)
            self.assertEqual(self.recovery_manager.recovery_stats['automatic_recoveries'], 1)
    
    @patch('responsiveness_error_recovery.send_admin_notification')
    async def test_handle_database_connection_recovery_failure(self, mock_send_notification):
        """Test failed database connection recovery"""
        mock_send_notification.return_value = True
        
        # Mock failed connection recovery
        self.mock_db_manager.detect_and_cleanup_connection_leaks.return_value = {
            'cleaned_sessions': 0,
            'long_lived_sessions_found': 0,
            'cleanup_actions': []
        }
        
        self.mock_db_manager.monitor_connection_health.return_value = {
            'overall_health': 'CRITICAL',
            'issues': ['Connection pool exhausted'],
            'recommendations': ['Restart database service']
        }
        
        # Mock failed connection test
        with patch.object(self.recovery_manager, '_test_database_connection', return_value=False):
            error = ConnectionError("Database connection lost")
            context = {'operation': 'test_operation', 'user_id': 1}
            
            result = await self.recovery_manager.handle_database_connection_recovery(error, context)
            
            # Verify recovery failed
            self.assertFalse(result['success'])
            self.assertFalse(result['error_resolved'])
            self.assertTrue(result['admin_notification_sent'])
            
            # Verify admin notification was sent for failure
            mock_send_notification.assert_called()
            call_args = mock_send_notification.call_args
            self.assertEqual(call_args[1]['notification_type'], NotificationType.ERROR)
            
            # Verify recovery statistics were updated
            self.assertEqual(self.recovery_manager.recovery_stats['total_recoveries'], 1)
            self.assertEqual(self.recovery_manager.recovery_stats['failed_recoveries'], 1)
    
    @patch('responsiveness_error_recovery.gc.collect')
    @patch('responsiveness_error_recovery.send_admin_notification')
    async def test_handle_session_memory_cleanup_recovery(self, mock_send_notification, mock_gc_collect):
        """Test session memory cleanup recovery"""
        mock_send_notification.return_value = True
        mock_gc_collect.return_value = None
        
        # Mock memory usage methods
        with patch.object(self.recovery_manager, '_get_memory_usage_mb', side_effect=[100.0, 95.0, 85.0]):
            with patch.object(self.recovery_manager, '_get_memory_usage_percent', return_value=75.0):
                with patch.object(self.recovery_manager, '_cleanup_expired_sessions', return_value=5):
                    with patch.object(self.recovery_manager, '_clear_application_caches', return_value={'caches_cleared': ['session_cache']}):
                        
                        error = MemoryError("Out of memory")
                        context = {'user_id': 1, 'session_id': 'test_session'}
                        
                        result = await self.recovery_manager.handle_session_memory_cleanup_recovery(error, context)
                        
                        # Verify recovery was successful
                        self.assertTrue(result['success'])
                        self.assertEqual(result['sessions_cleaned'], 5)
                        self.assertGreater(result['memory_freed_mb'], 0)
                        self.assertGreater(len(result['actions_taken']), 0)
                        
                        # Verify garbage collection was called
                        mock_gc_collect.assert_called()
                        
                        # Verify admin notification was sent
                        mock_send_notification.assert_called()
                        call_args = mock_send_notification.call_args
                        self.assertEqual(call_args[1]['notification_type'], NotificationType.SUCCESS)
    
    @patch('responsiveness_error_recovery.send_admin_notification')
    async def test_integrate_with_admin_alerts_success(self, mock_send_notification):
        """Test integration with admin alert system for successful recovery"""
        mock_send_notification.return_value = True
        
        recovery_result = {
            'success': True,
            'actions_taken': [
                {'action': 'garbage_collection', 'memory_freed_mb': 10.5},
                {'action': 'session_cleanup', 'sessions_cleaned': 3}
            ],
            'recovery_time': 5.2,
            'memory_freed_mb': 15.3
        }
        
        issue_type = ResponsivenessIssueType.MEMORY_LEAK
        
        result = await self.recovery_manager.integrate_with_admin_alerts(recovery_result, issue_type)
        
        # Verify integration was successful
        self.assertTrue(result)
        
        # Verify admin notification was sent with correct parameters
        mock_send_notification.assert_called_once()
        call_args = mock_send_notification.call_args
        
        self.assertEqual(call_args[1]['notification_type'], NotificationType.SUCCESS)
        self.assertEqual(call_args[1]['priority'], NotificationPriority.NORMAL)
        self.assertIn('Memory Leak', call_args[1]['title'])
        self.assertIn('successful', call_args[1]['message'])
        self.assertIn('15.3MB', call_args[1]['message'])
        
        # Verify system health data is included
        self.assertIn('system_health_data', call_args[1])
        health_data = call_args[1]['system_health_data']
        self.assertEqual(health_data['recovery_type'], 'memory_leak')
        self.assertTrue(health_data['recovery_success'])
        self.assertEqual(health_data['memory_freed_mb'], 15.3)
    
    @patch('responsiveness_error_recovery.send_admin_notification')
    async def test_integrate_with_admin_alerts_failure(self, mock_send_notification):
        """Test integration with admin alert system for failed recovery"""
        mock_send_notification.return_value = True
        
        recovery_result = {
            'success': False,
            'actions_taken': [
                {'action': 'garbage_collection', 'error': 'GC failed'},
                {'action': 'session_cleanup', 'result': 'no sessions found'}
            ],
            'recovery_time': 2.1,
            'memory_freed_mb': 0.0
        }
        
        issue_type = ResponsivenessIssueType.CONNECTION_LEAK
        
        result = await self.recovery_manager.integrate_with_admin_alerts(recovery_result, issue_type)
        
        # Verify integration was successful
        self.assertTrue(result)
        
        # Verify admin notification was sent with correct parameters
        mock_send_notification.assert_called_once()
        call_args = mock_send_notification.call_args
        
        self.assertEqual(call_args[1]['notification_type'], NotificationType.ERROR)
        self.assertEqual(call_args[1]['priority'], NotificationPriority.HIGH)
        self.assertIn('Connection Leak', call_args[1]['title'])
        self.assertIn('failed', call_args[1]['message'])
        self.assertTrue(call_args[1]['requires_admin_action'])
    
    async def test_extend_health_check_error_handling(self):
        """Test extending health check with recovery status"""
        # Mock some recovery history
        self.recovery_manager.recovery_stats = {
            'total_recoveries': 10,
            'successful_recoveries': 8,
            'failed_recoveries': 2,
            'automatic_recoveries': 10,
            'manual_recoveries': 0
        }
        
        self.recovery_manager.recovery_history = [
            {
                'type': 'database_connection_recovery',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': {'success': True, 'recovery_time': 2.5}
            },
            {
                'type': 'session_memory_cleanup_recovery',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': {'success': False, 'recovery_time': 1.2}
            }
        ]
        
        health_check_result = {
            'overall_health': 'HEALTHY',
            'issues': [],
            'recommendations': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        enhanced_result = await self.recovery_manager.extend_health_check_error_handling(health_check_result)
        
        # Verify recovery status was added
        self.assertIn('responsiveness_recovery', enhanced_result)
        recovery_status = enhanced_result['responsiveness_recovery']
        
        self.assertTrue(recovery_status['recovery_system_active'])
        self.assertEqual(recovery_status['total_recoveries'], 10)
        self.assertEqual(recovery_status['successful_recoveries'], 8)
        self.assertEqual(recovery_status['recovery_success_rate'], 0.8)
        self.assertEqual(len(recovery_status['recent_recovery_history']), 2)

class TestDatabaseResponsivenessRecoveryMixin(unittest.TestCase):
    """Test database responsiveness recovery mixin"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config = Mock()
        self.mock_config.responsiveness = Mock()
        
        # Create a test class that uses the mixin
        class TestDatabaseManager(DatabaseResponsivenessRecoveryMixin):
            def __init__(self, config):
                self.config = config
                self.engine = Mock()
                super().__init__()
        
        self.db_manager = TestDatabaseManager(self.mock_config)
    
    def test_initialization(self):
        """Test mixin initialization"""
        self.assertIsNotNone(self.db_manager.connection_recovery_config)
        self.assertIsNotNone(self.db_manager.recovery_stats)
        self.assertEqual(self.db_manager.recovery_stats['connection_recoveries'], 0)
    
    def test_is_connection_recoverable_error(self):
        """Test connection error recoverability detection"""
        # Test recoverable errors
        recoverable_errors = [
            ConnectionError("Connection refused"),
            Exception("MySQL server has gone away"),
            Exception("Lost connection to MySQL server"),
            Exception("Connection timeout")
        ]
        
        for error in recoverable_errors:
            with self.subTest(error=error):
                self.assertTrue(self.db_manager._is_connection_recoverable_error(error))
        
        # Test non-recoverable errors
        non_recoverable_errors = [
            ValueError("Invalid value"),
            TypeError("Type error"),
            Exception("Permission denied")
        ]
        
        for error in non_recoverable_errors:
            with self.subTest(error=error):
                self.assertFalse(self.db_manager._is_connection_recoverable_error(error))
    
    @patch('database_responsiveness_recovery.asyncio.wait_for')
    async def test_test_connection_with_timeout_success(self, mock_wait_for):
        """Test successful connection test with timeout"""
        # Mock successful connection test
        mock_session = Mock()
        mock_session.execute.return_value = None
        
        with patch.object(self.db_manager, 'get_session', return_value=mock_session):
            with patch.object(self.db_manager, 'close_session'):
                mock_wait_for.return_value = True
                
                result = await self.db_manager._test_connection_with_timeout()
                
                self.assertTrue(result)
                mock_wait_for.assert_called_once()
    
    @patch('database_responsiveness_recovery.asyncio.wait_for')
    async def test_test_connection_with_timeout_failure(self, mock_wait_for):
        """Test failed connection test with timeout"""
        # Mock timeout
        mock_wait_for.side_effect = asyncio.TimeoutError()
        
        result = await self.db_manager._test_connection_with_timeout()
        
        self.assertFalse(result)
    
    async def test_recreate_engine_connection_success(self):
        """Test successful engine connection recreation"""
        # Mock successful engine recreation
        mock_connection = Mock()
        mock_connection.execute.return_value = None
        mock_connection.close.return_value = None
        
        self.db_manager.engine.dispose.return_value = None
        self.db_manager.engine.connect.return_value = mock_connection
        
        result = await self.db_manager._recreate_engine_connection()
        
        self.assertTrue(result)
        self.db_manager.engine.dispose.assert_called_once()
        self.db_manager.engine.connect.assert_called_once()
    
    async def test_recreate_engine_connection_failure(self):
        """Test failed engine connection recreation"""
        # Mock failed engine recreation
        self.db_manager.engine.dispose.return_value = None
        self.db_manager.engine.connect.side_effect = Exception("Connection failed")
        
        result = await self.db_manager._recreate_engine_connection()
        
        self.assertFalse(result)

class TestSessionErrorHandlerRecovery(unittest.TestCase):
    """Test session error handler with memory cleanup recovery"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_cookie_manager = Mock()
        self.error_handler = SessionErrorHandler(self.mock_cookie_manager)
    
    def test_initialization_with_recovery(self):
        """Test error handler initialization with recovery capabilities"""
        self.assertIn('session_memory_error', self.error_handler.error_messages)
        self.assertIsNotNone(self.error_handler.memory_recovery_config)
        self.assertIsNotNone(self.error_handler.recovery_stats)
        self.assertEqual(self.error_handler.recovery_stats['memory_cleanups'], 0)
    
    def test_is_memory_related_error(self):
        """Test memory-related error detection"""
        # Test memory-related errors
        memory_errors = [
            MemoryError("Out of memory"),
            Exception("Memory allocation failed"),
            Exception("Session cache too large"),
            Exception("Resource exhausted")
        ]
        
        for error in memory_errors:
            with self.subTest(error=error):
                self.assertTrue(self.error_handler._is_memory_related_error(error))
        
        # Test non-memory errors
        non_memory_errors = [
            ValueError("Invalid value"),
            ConnectionError("Connection failed"),
            Exception("Authentication failed")
        ]
        
        for error in non_memory_errors:
            with self.subTest(error=error):
                self.assertFalse(self.error_handler._is_memory_related_error(error))
    
    @patch('session_error_handling.gc.collect')
    @patch('session_error_handling.send_admin_notification')
    async def test_attempt_session_memory_cleanup_success(self, mock_send_notification, mock_gc_collect):
        """Test successful session memory cleanup"""
        mock_send_notification.return_value = True
        mock_gc_collect.return_value = None
        
        # Mock memory usage methods
        with patch.object(self.error_handler, '_get_process_memory_mb', side_effect=[100.0, 95.0, 85.0]):
            with patch.object(self.error_handler, '_clear_session_caches', return_value={'caches_cleared': ['flask_session']}):
                
                error = MemoryError("Out of memory")
                
                result = await self.error_handler._attempt_session_memory_cleanup(error)
                
                # Verify cleanup was successful
                self.assertTrue(result['success'])
                self.assertGreater(result['memory_freed_mb'], 0)
                self.assertGreater(len(result['actions_taken']), 0)
                
                # Verify garbage collection was called
                mock_gc_collect.assert_called()
                
                # Verify admin notification was sent
                mock_send_notification.assert_called()
                
                # Verify recovery statistics were updated
                self.assertEqual(self.error_handler.recovery_stats['memory_cleanups'], 1)
                self.assertEqual(self.error_handler.recovery_stats['successful_cleanups'], 1)
    
    def test_get_session_recovery_stats(self):
        """Test getting session recovery statistics"""
        # Set up some test statistics
        self.error_handler.recovery_stats = {
            'memory_cleanups': 5,
            'successful_cleanups': 4,
            'failed_cleanups': 1,
            'total_memory_freed_mb': 25.5,
            'last_cleanup': datetime.now(timezone.utc)
        }
        
        stats = self.error_handler.get_session_recovery_stats()
        
        self.assertEqual(stats['memory_cleanups'], 5)
        self.assertEqual(stats['successful_cleanups'], 4)
        self.assertEqual(stats['failed_cleanups'], 1)
        self.assertEqual(stats['cleanup_success_rate'], 0.8)
        self.assertEqual(stats['total_memory_freed_mb'], 25.5)
        self.assertIsNotNone(stats['last_cleanup'])

class TestResponsivenessRecoveryDecorators(unittest.TestCase):
    """Test responsiveness recovery decorators"""
    
    @patch('responsiveness_error_recovery.get_responsiveness_recovery_manager')
    async def test_with_responsiveness_recovery_decorator_success(self, mock_get_manager):
        """Test responsiveness recovery decorator with successful recovery"""
        # Mock recovery manager
        mock_manager = Mock()
        mock_manager.handle_database_connection_recovery = AsyncMock(return_value={'success': True})
        mock_get_manager.return_value = mock_manager
        
        # Create test function with decorator
        @with_responsiveness_recovery(ResponsivenessIssueType.CONNECTION_LEAK)
        async def test_function():
            raise ConnectionError("Database connection lost")
        
        # Mock the integration method
        mock_manager.integrate_with_admin_alerts = AsyncMock(return_value=True)
        
        # The function should not raise an exception due to successful recovery
        try:
            await test_function()
        except ConnectionError:
            self.fail("Function should not raise exception after successful recovery")
    
    @patch('responsiveness_error_recovery.get_responsiveness_recovery_manager')
    async def test_with_responsiveness_recovery_decorator_failure(self, mock_get_manager):
        """Test responsiveness recovery decorator with failed recovery"""
        # Mock recovery manager
        mock_manager = Mock()
        mock_manager.handle_database_connection_recovery = AsyncMock(return_value={'success': False})
        mock_get_manager.return_value = mock_manager
        
        # Create test function with decorator
        @with_responsiveness_recovery(ResponsivenessIssueType.CONNECTION_LEAK)
        async def test_function():
            raise ConnectionError("Database connection lost")
        
        # Mock the integration method
        mock_manager.integrate_with_admin_alerts = AsyncMock(return_value=True)
        
        # The function should raise the original exception after failed recovery
        with self.assertRaises(ConnectionError):
            await test_function()

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)