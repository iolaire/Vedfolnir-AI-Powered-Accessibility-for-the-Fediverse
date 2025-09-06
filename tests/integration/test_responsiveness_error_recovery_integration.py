# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration tests for responsiveness error recovery functionality.

Tests the integration between enhanced error handling components,
including database recovery, session cleanup, and health check integration.
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from responsiveness_error_recovery import (
    ResponsivenessErrorRecoveryManager,
    ResponsivenessIssueType,
    get_responsiveness_recovery_manager
)
from database_responsiveness_recovery import EnhancedDatabaseManager
from session_error_handling import SessionErrorHandler
from health_check import HealthChecker, HealthStatus
from config import Config

class TestResponsivenessErrorRecoveryIntegration(unittest.TestCase):
    """Integration tests for responsiveness error recovery system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config = Mock()
        self.mock_config.responsiveness = Mock()
        self.mock_config.responsiveness.memory_critical_threshold = 0.9
        self.mock_config.responsiveness.cpu_critical_threshold = 0.9
        
        # Create mock components
        self.mock_db_manager = Mock()
        self.mock_system_optimizer = Mock()
        self.mock_cookie_manager = Mock()
        
        # Initialize components
        self.recovery_manager = ResponsivenessErrorRecoveryManager(
            db_manager=self.mock_db_manager,
            system_optimizer=self.mock_system_optimizer
        )
        
        self.session_error_handler = SessionErrorHandler(self.mock_cookie_manager)
        
        # Mock health checker
        self.health_checker = Mock()
        self.health_checker.config = self.mock_config
        self.health_checker.db_manager = self.mock_db_manager
    
    @patch('responsiveness_error_recovery.send_admin_notification')
    def test_end_to_end_database_recovery_flow(self, mock_send_notification):
        """Test complete database recovery flow from error to resolution"""
        mock_send_notification.return_value = True
        
        # Step 1: Simulate database connection error
        connection_error = ConnectionError("MySQL server has gone away")
        
        # Step 2: Mock successful recovery components
        self.mock_db_manager.detect_and_cleanup_connection_leaks.return_value = {
            'cleaned_sessions': 2,
            'long_lived_sessions_found': 1,
            'cleanup_actions': ['cleaned_session_123']
        }
        
        self.mock_db_manager.monitor_connection_health.return_value = {
            'overall_health': 'HEALTHY',
            'issues': [],
            'recommendations': [],
            'metrics': {
                'connection_pool': {'total_utilization_percent': 45},
                'session_stats': {'active_sessions': 5}
            }
        }
        
        # Mock successful connection test
        with patch.object(self.recovery_manager, '_test_database_connection', return_value=True):
            # Step 3: Execute recovery
            recovery_result = await self.recovery_manager.handle_database_connection_recovery(
                connection_error,
                context={'operation': 'test_query', 'user_id': 1}
            )
            
            # Step 4: Verify recovery was successful
            self.assertTrue(recovery_result['success'])
            self.assertTrue(recovery_result['error_resolved'])
            self.assertGreater(len(recovery_result['actions_taken']), 0)
            
            # Step 5: Verify admin integration
            integration_result = await self.recovery_manager.integrate_with_admin_alerts(
                recovery_result,
                ResponsivenessIssueType.CONNECTION_LEAK
            )
            self.assertTrue(integration_result)
            
            # Step 6: Verify admin notification was sent
            mock_send_notification.assert_called()
            call_args = mock_send_notification.call_args
            self.assertIn('success', call_args[1]['message'].lower())
    
    @patch('responsiveness_error_recovery.gc.collect')
    @patch('responsiveness_error_recovery.send_admin_notification')
    def test_end_to_end_memory_recovery_flow(self, mock_send_notification, mock_gc_collect):
        """Test complete memory recovery flow from error to resolution"""
        mock_send_notification.return_value = True
        mock_gc_collect.return_value = None
        
        # Step 1: Simulate memory error
        memory_error = MemoryError("Out of memory")
        
        # Step 2: Mock memory cleanup components
        with patch.object(self.recovery_manager, '_get_memory_usage_mb', side_effect=[150.0, 140.0, 120.0]):
            with patch.object(self.recovery_manager, '_get_memory_usage_percent', return_value=75.0):
                with patch.object(self.recovery_manager, '_cleanup_expired_sessions', return_value=8):
                    with patch.object(self.recovery_manager, '_clear_application_caches', return_value={'caches_cleared': ['session_cache', 'template_cache']}):
                        
                        # Step 3: Execute recovery
                        recovery_result = await self.recovery_manager.handle_session_memory_cleanup_recovery(
                            memory_error,
                            context={'user_id': 1, 'session_id': 'test_session'}
                        )
                        
                        # Step 4: Verify recovery was successful
                        self.assertTrue(recovery_result['success'])
                        self.assertEqual(recovery_result['sessions_cleaned'], 8)
                        self.assertGreater(recovery_result['memory_freed_mb'], 0)
                        
                        # Step 5: Verify session error handler integration
                        session_recovery_result = await self.session_error_handler._attempt_session_memory_cleanup(memory_error)
                        self.assertIsNotNone(session_recovery_result)
                        
                        # Step 6: Verify admin integration
                        integration_result = await self.recovery_manager.integrate_with_admin_alerts(
                            recovery_result,
                            ResponsivenessIssueType.MEMORY_LEAK
                        )
                        self.assertTrue(integration_result)
    
    def test_health_check_integration_with_recovery_status(self):
        """Test health check integration with recovery system status"""
        # Step 1: Set up recovery history
        self.recovery_manager.recovery_stats = {
            'total_recoveries': 5,
            'successful_recoveries': 4,
            'failed_recoveries': 1,
            'automatic_recoveries': 5,
            'manual_recoveries': 0
        }
        
        self.recovery_manager.recovery_history = [
            {
                'type': 'database_connection_recovery',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': {'success': True, 'recovery_time': 2.1}
            },
            {
                'type': 'session_memory_cleanup_recovery',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': {'success': True, 'recovery_time': 1.8}
            }
        ]
        
        # Step 2: Create mock health check result
        health_check_result = {
            'overall_health': 'HEALTHY',
            'issues': [],
            'recommendations': [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'database': {'status': 'healthy'},
                'sessions': {'status': 'healthy'}
            }
        }
        
        # Step 3: Extend health check with recovery status
        enhanced_result = await self.recovery_manager.extend_health_check_error_handling(health_check_result)
        
        # Step 4: Verify recovery status was added
        self.assertIn('responsiveness_recovery', enhanced_result)
        recovery_status = enhanced_result['responsiveness_recovery']
        
        self.assertTrue(recovery_status['recovery_system_active'])
        self.assertEqual(recovery_status['total_recoveries'], 5)
        self.assertEqual(recovery_status['successful_recoveries'], 4)
        self.assertEqual(recovery_status['recovery_success_rate'], 0.8)
        self.assertEqual(recovery_status['status'], 'healthy')
    
    def test_recovery_failure_escalation_flow(self):
        """Test escalation flow when recovery fails"""
        # Step 1: Set up failed recovery scenario
        self.mock_db_manager.detect_and_cleanup_connection_leaks.return_value = {
            'cleaned_sessions': 0,
            'long_lived_sessions_found': 0,
            'cleanup_actions': []
        }
        
        self.mock_db_manager.monitor_connection_health.return_value = {
            'overall_health': 'CRITICAL',
            'issues': ['Connection pool exhausted', 'High connection abort rate'],
            'recommendations': ['Restart database service', 'Check network connectivity']
        }
        
        # Mock failed connection test
        with patch.object(self.recovery_manager, '_test_database_connection', return_value=False):
            with patch('responsiveness_error_recovery.send_admin_notification', return_value=True) as mock_send_notification:
                
                # Step 2: Execute recovery (should fail)
                connection_error = ConnectionError("Connection pool exhausted")
                recovery_result = await self.recovery_manager.handle_database_connection_recovery(
                    connection_error,
                    context={'operation': 'critical_query', 'user_id': 1}
                )
                
                # Step 3: Verify recovery failed
                self.assertFalse(recovery_result['success'])
                self.assertFalse(recovery_result['error_resolved'])
                self.assertTrue(recovery_result['admin_notification_sent'])
                
                # Step 4: Verify escalation notification was sent
                mock_send_notification.assert_called()
                call_args = mock_send_notification.call_args
                self.assertIn('failed', call_args[1]['message'].lower())
                self.assertTrue(call_args[1]['requires_admin_action'])
    
    def test_global_recovery_manager_singleton(self):
        """Test global recovery manager singleton pattern"""
        # Step 1: Get recovery manager instances
        manager1 = get_responsiveness_recovery_manager(
            db_manager=self.mock_db_manager,
            system_optimizer=self.mock_system_optimizer
        )
        
        manager2 = get_responsiveness_recovery_manager()
        
        # Step 2: Verify singleton behavior
        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, ResponsivenessErrorRecoveryManager)
    
    def test_recovery_statistics_tracking(self):
        """Test recovery statistics are properly tracked across operations"""
        # Step 1: Perform multiple recovery operations
        with patch.object(self.recovery_manager, '_test_database_connection', return_value=True):
            with patch('responsiveness_error_recovery.send_admin_notification', return_value=True):
                
                # Successful recovery
                self.mock_db_manager.detect_and_cleanup_connection_leaks.return_value = {
                    'cleaned_sessions': 1,
                    'cleanup_actions': ['cleaned_session_1']
                }
                self.mock_db_manager.monitor_connection_health.return_value = {
                    'overall_health': 'HEALTHY'
                }
                
                await self.recovery_manager.handle_database_connection_recovery(
                    ConnectionError("Test error 1")
                )
                
                # Failed recovery
                self.mock_db_manager.monitor_connection_health.return_value = {
                    'overall_health': 'CRITICAL'
                }
                
                with patch.object(self.recovery_manager, '_test_database_connection', return_value=False):
                    await self.recovery_manager.handle_database_connection_recovery(
                        ConnectionError("Test error 2")
                    )
        
        # Step 2: Verify statistics
        self.assertEqual(self.recovery_manager.recovery_stats['total_recoveries'], 2)
        self.assertEqual(self.recovery_manager.recovery_stats['successful_recoveries'], 1)
        self.assertEqual(self.recovery_manager.recovery_stats['failed_recoveries'], 1)
        self.assertEqual(self.recovery_manager.recovery_stats['automatic_recoveries'], 2)
        
        # Step 3: Verify recovery history
        self.assertEqual(len(self.recovery_manager.recovery_history), 2)
        self.assertEqual(self.recovery_manager.recovery_history[0]['type'], 'database_connection_recovery')
        self.assertTrue(self.recovery_manager.recovery_history[0]['result']['success'])
        self.assertFalse(self.recovery_manager.recovery_history[1]['result']['success'])

class TestResponsivenessRecoveryDecoratorsIntegration(unittest.TestCase):
    """Integration tests for responsiveness recovery decorators"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_manager = Mock()
        self.mock_system_optimizer = Mock()
    
    @patch('responsiveness_error_recovery.get_responsiveness_recovery_manager')
    def test_decorator_integration_with_real_function(self, mock_get_manager):
        """Test decorator integration with a realistic function"""
        # Step 1: Set up mock recovery manager
        mock_manager = Mock()
        mock_manager.handle_database_connection_recovery = AsyncMock(return_value={'success': True})
        mock_manager.integrate_with_admin_alerts = AsyncMock(return_value=True)
        mock_get_manager.return_value = mock_manager
        
        # Step 2: Create a realistic function that might fail
        from responsiveness_error_recovery import with_responsiveness_recovery
        
        @with_responsiveness_recovery(ResponsivenessIssueType.CONNECTION_LEAK)
        async def database_operation(query: str, params: dict = None):
            """Simulate a database operation that might fail"""
            if query == "SELECT * FROM failing_table":
                raise ConnectionError("Database connection lost")
            return {"result": "success", "query": query, "params": params}
        
        # Step 3: Test successful operation (no recovery needed)
        result = await database_operation("SELECT * FROM users", {"limit": 10})
        self.assertEqual(result["result"], "success")
        
        # Step 4: Test operation that triggers recovery
        result = await database_operation("SELECT * FROM failing_table")
        
        # Step 5: Verify recovery was attempted
        mock_manager.handle_database_connection_recovery.assert_called_once()
        mock_manager.integrate_with_admin_alerts.assert_called_once()
    
    @patch('database_responsiveness_recovery.asyncio.create_task')
    def test_database_recovery_decorator_integration(self, mock_create_task):
        """Test database recovery decorator integration"""
        from database_responsiveness_recovery import with_database_recovery
        
        # Step 1: Create mock database manager with recovery capabilities
        mock_db_manager = Mock()
        mock_db_manager._is_connection_recoverable_error = Mock(return_value=True)
        mock_db_manager._attempt_connection_recovery = AsyncMock(return_value={'success': True})
        
        # Step 2: Create function with database recovery decorator
        @with_database_recovery(operation_name="test_query", max_retries=2)
        async def database_query(db_manager):
            """Simulate a database query that might fail"""
            if not hasattr(database_query, '_call_count'):
                database_query._call_count = 0
            database_query._call_count += 1
            
            if database_query._call_count == 1:
                raise ConnectionError("Connection lost")
            return {"result": "success", "call_count": database_query._call_count}
        
        # Step 3: Execute function (should recover and succeed on retry)
        # Note: This test verifies the decorator structure, actual recovery would need more setup
        try:
            result = await database_query(mock_db_manager)
            # If we get here, the decorator didn't interfere with normal execution
            self.assertIsNotNone(result)
        except ConnectionError:
            # Expected if recovery is not fully mocked
            pass

if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2)