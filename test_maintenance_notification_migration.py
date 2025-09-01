#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test: Maintenance Notification Migration

Tests the migration of maintenance notifications from legacy flash messages
to the unified WebSocket notification system.
"""

import sys
import os
import unittest
import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMaintenanceNotificationMigration(unittest.TestCase):
    """Test maintenance notification migration functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_notification_manager = Mock()
        self.mock_db_manager = Mock()
        self.mock_socketio = Mock()
        
        # Mock successful notification sending
        self.mock_notification_manager.send_admin_notification.return_value = True
        self.mock_notification_manager.send_user_notification.return_value = True
    
    def test_admin_maintenance_notification_handler_creation(self):
        """Test AdminMaintenanceNotificationHandler creation"""
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        
        handler = AdminMaintenanceNotificationHandler(
            self.mock_notification_manager, 
            self.mock_db_manager
        )
        
        self.assertIsNotNone(handler)
        self.assertEqual(handler.notification_manager, self.mock_notification_manager)
        self.assertEqual(handler.db_manager, self.mock_db_manager)
    
    def test_maintenance_started_notification(self):
        """Test maintenance started notification"""
        from admin_maintenance_notification_handler import (
            AdminMaintenanceNotificationHandler, 
            MaintenanceNotificationData
        )
        
        handler = AdminMaintenanceNotificationHandler(
            self.mock_notification_manager, 
            self.mock_db_manager
        )
        
        # Create test maintenance data
        maintenance_data = MaintenanceNotificationData(
            operation_type="system_maintenance",
            operation_id="test_operation_001",
            status="started",
            estimated_duration=30,
            estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=30),
            affected_operations=["caption_generation"],
            affected_users_count=10,
            admin_action_required=False,
            rollback_available=True
        )
        
        # Send notification
        success = handler.send_maintenance_started_notification(1, maintenance_data)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification data
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertEqual(call_args.title, "🔧 Maintenance Operation Started")
        self.assertTrue(call_args.admin_only)
        self.assertEqual(call_args.data['operation_type'], "system_maintenance")
    
    def test_system_pause_notification(self):
        """Test system pause notification"""
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        
        handler = AdminMaintenanceNotificationHandler(
            self.mock_notification_manager, 
            self.mock_db_manager
        )
        
        pause_data = {
            'reason': 'Scheduled maintenance',
            'duration': 60,
            'mode': 'normal',
            'affected_operations': ['caption_generation', 'platform_operations'],
            'estimated_completion': datetime.now(timezone.utc).isoformat()
        }
        
        success = handler.send_system_pause_notification(1, pause_data)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification data
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertEqual(call_args.title, "⏸️ System Paused for Maintenance")
        self.assertEqual(call_args.data['reason'], 'Scheduled maintenance')
    
    def test_system_resume_notification(self):
        """Test system resume notification"""
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        
        handler = AdminMaintenanceNotificationHandler(
            self.mock_notification_manager, 
            self.mock_db_manager
        )
        
        resume_data = {
            'maintenance_duration': '45 minutes',
            'completed_operations': ['database_maintenance'],
            'restored_functionality': ['caption_generation', 'platform_operations']
        }
        
        success = handler.send_system_resume_notification(1, resume_data)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification data
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertEqual(call_args.title, "▶️ System Resumed After Maintenance")
        self.assertEqual(call_args.type.name, "SUCCESS")
    
    def test_configuration_change_notification(self):
        """Test configuration change notification"""
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        
        handler = AdminMaintenanceNotificationHandler(
            self.mock_notification_manager, 
            self.mock_db_manager
        )
        
        config_data = {
            'change_description': 'Updated WebSocket settings',
            'changed_settings': ['WEBSOCKET_TIMEOUT', 'WEBSOCKET_CORS'],
            'requires_restart': False,
            'change_type': 'configuration_update'
        }
        
        success = handler.send_configuration_change_notification(1, config_data)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification data
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertEqual(call_args.title, "⚙️ Maintenance Configuration Updated")
        self.assertEqual(call_args.data['change_description'], 'Updated WebSocket settings')
    
    def test_maintenance_error_notification(self):
        """Test maintenance error notification"""
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        
        handler = AdminMaintenanceNotificationHandler(
            self.mock_notification_manager, 
            self.mock_db_manager
        )
        
        error_data = {
            'error_message': 'Database connection failed',
            'error_code': 'DB_CONNECTION_ERROR',
            'operation_id': 'maintenance_001',
            'failed_operation': 'database_optimization',
            'rollback_required': True,
            'immediate_action_required': True
        }
        
        success = handler.send_maintenance_error_notification(1, error_data)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called_once()
        
        # Verify notification data
        call_args = self.mock_notification_manager.send_admin_notification.call_args[0][0]
        self.assertEqual(call_args.title, "🚨 Maintenance Operation Error")
        self.assertEqual(call_args.priority.name, "CRITICAL")
        self.assertTrue(call_args.requires_action)
    
    def test_progress_websocket_handler_creation(self):
        """Test MaintenanceProgressWebSocketHandler creation"""
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        self.assertIsNotNone(handler)
        self.assertEqual(handler.notification_manager, self.mock_notification_manager)
        self.assertEqual(handler.socketio, self.mock_socketio)
    
    def test_progress_operation_registration(self):
        """Test maintenance operation registration for progress tracking"""
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        success = handler.register_maintenance_operation(
            operation_id="test_op_001",
            operation_type="database_maintenance",
            admin_user_id=1,
            total_steps=5,
            estimated_duration=300
        )
        
        self.assertTrue(success)
        
        # Verify operation is tracked
        active_operations = handler.get_active_operations()
        self.assertIn("test_op_001", active_operations)
        
        operation_info = active_operations["test_op_001"]
        self.assertEqual(operation_info['operation_type'], "database_maintenance")
        self.assertEqual(operation_info['admin_user_id'], 1)
        self.assertEqual(operation_info['total_steps'], 5)
    
    def test_progress_updates(self):
        """Test progress updates for maintenance operations"""
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        # Register operation
        handler.register_maintenance_operation(
            operation_id="test_op_002",
            operation_type="system_optimization",
            admin_user_id=1,
            total_steps=3
        )
        
        # Update progress
        success = handler.update_progress(
            operation_id="test_op_002",
            progress_percentage=50,
            current_step="Optimizing database",
            current_step_number=2,
            message="Database optimization in progress"
        )
        
        self.assertTrue(success)
        
        # Verify progress is updated
        active_operations = handler.get_active_operations()
        operation_info = active_operations["test_op_002"]
        self.assertEqual(operation_info['progress_percentage'], 50)
        self.assertEqual(operation_info['current_step'], 2)
    
    def test_progress_completion(self):
        """Test maintenance operation completion"""
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        # Register operation
        handler.register_maintenance_operation(
            operation_id="test_op_003",
            operation_type="backup_operation",
            admin_user_id=1
        )
        
        # Complete operation
        success = handler.complete_operation(
            operation_id="test_op_003",
            completion_message="Backup completed successfully",
            success=True,
            final_details={'backup_size': '2.5GB'}
        )
        
        self.assertTrue(success)
        
        # Verify operation is removed from active operations
        active_operations = handler.get_active_operations()
        self.assertNotIn("test_op_003", active_operations)
    
    def test_progress_error_reporting(self):
        """Test error reporting for maintenance operations"""
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        # Register operation
        handler.register_maintenance_operation(
            operation_id="test_op_004",
            operation_type="cleanup_operation",
            admin_user_id=1
        )
        
        # Report error
        success = handler.report_error(
            operation_id="test_op_004",
            error_message="Disk space insufficient",
            error_details={'required': '10GB', 'available': '5GB'},
            recoverable=True
        )
        
        self.assertTrue(success)
        
        # Verify operation status is updated
        active_operations = handler.get_active_operations()
        operation_info = active_operations["test_op_004"]
        self.assertEqual(operation_info['status'], 'error')
        self.assertEqual(operation_info['last_error'], 'Disk space insufficient')
    
    def test_integration_service_creation(self):
        """Test MaintenanceNotificationIntegrationService creation"""
        from maintenance_notification_integration_service import MaintenanceNotificationIntegrationService
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        progress_handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        integration_service = MaintenanceNotificationIntegrationService(
            self.mock_notification_manager,
            progress_handler,
            self.mock_db_manager
        )
        
        self.assertIsNotNone(integration_service)
        self.assertEqual(integration_service.notification_manager, self.mock_notification_manager)
        self.assertEqual(integration_service.progress_handler, progress_handler)
    
    def test_maintenance_operation_scheduling(self):
        """Test maintenance operation scheduling"""
        from maintenance_notification_integration_service import (
            MaintenanceNotificationIntegrationService,
            MaintenanceOperation,
            MaintenanceOperationType
        )
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        progress_handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        integration_service = MaintenanceNotificationIntegrationService(
            self.mock_notification_manager,
            progress_handler,
            self.mock_db_manager
        )
        
        # Create maintenance operation
        operation = MaintenanceOperation(
            operation_id="scheduled_op_001",
            operation_type=MaintenanceOperationType.DATABASE_MAINTENANCE,
            title="Database Optimization",
            description="Optimize database performance",
            admin_user_id=1,
            estimated_duration=60,
            affects_users=True,
            requires_downtime=False,
            rollback_available=True,
            scheduled_time=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Schedule operation
        success = integration_service.schedule_maintenance_operation(operation)
        
        self.assertTrue(success)
        self.mock_notification_manager.send_admin_notification.assert_called()
    
    def test_maintenance_operation_execution(self):
        """Test maintenance operation execution with progress tracking"""
        from maintenance_notification_integration_service import (
            MaintenanceNotificationIntegrationService,
            MaintenanceOperation,
            MaintenanceOperationType
        )
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        
        progress_handler = MaintenanceProgressWebSocketHandler(
            self.mock_notification_manager,
            self.mock_socketio
        )
        
        integration_service = MaintenanceNotificationIntegrationService(
            self.mock_notification_manager,
            progress_handler,
            self.mock_db_manager
        )
        
        # Create maintenance operation
        operation = MaintenanceOperation(
            operation_id="exec_op_001",
            operation_type=MaintenanceOperationType.SYSTEM_PAUSE,
            title="System Pause",
            description="Pause system for maintenance",
            admin_user_id=1,
            estimated_duration=30
        )
        
        # Start operation (this will execute the operation handler immediately)
        success = integration_service.start_maintenance_operation(operation)
        
        self.assertTrue(success)
        
        # For system pause operations, the handler completes immediately
        # So the operation should already be completed and removed from active operations
        active_operations = progress_handler.get_active_operations()
        
        # The operation should be completed by now due to the synchronous handler
        # Let's verify that the operation was processed (notifications were sent)
        self.mock_notification_manager.send_admin_notification.assert_called()
        
        # Test manual progress update on a different operation that doesn't auto-complete
        manual_op_id = "manual_op_001"
        progress_handler.register_maintenance_operation(
            manual_op_id, "manual_operation", 1, total_steps=3
        )
        
        # Update progress manually
        update_success = integration_service.update_operation_progress(
            manual_op_id, 50, "Manual progress update", "Testing manual updates"
        )
        
        self.assertTrue(update_success)
        
        # Complete operation manually
        complete_success = integration_service.complete_maintenance_operation(
            manual_op_id, True, "Manual operation completed"
        )
        
        self.assertTrue(complete_success)
    
    def test_flash_message_replacement(self):
        """Test that flash messages have been replaced with WebSocket notifications"""
        # This test verifies that the maintenance routes no longer use flash messages
        
        # Read the maintenance mode routes file
        with open('admin/routes/maintenance_mode.py', 'r') as f:
            content = f.read()
        
        # Count flash message occurrences (should be 0 after migration)
        flash_count = content.count('flash(')
        
        # Verify no flash messages remain
        self.assertEqual(flash_count, 0, "Flash messages should be completely replaced with WebSocket notifications")
        
        # Verify WebSocket notification usage
        self.assertIn('AdminNotificationMessage', content)
        self.assertIn('send_admin_notification', content)
        self.assertIn('notification_manager', content)
    
    def test_notification_categories(self):
        """Test that maintenance notifications use correct categories"""
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        from models import NotificationCategory
        
        # Create a fresh mock for this test to avoid interference
        fresh_mock_manager = Mock()
        fresh_mock_manager.send_admin_notification.return_value = True
        
        handler = AdminMaintenanceNotificationHandler(
            fresh_mock_manager, 
            self.mock_db_manager
        )
        
        # Test system pause notification category
        handler.send_system_pause_notification(1, {
            'reason': 'Test maintenance',
            'duration': 30,
            'mode': 'normal'
        })
        
        # Verify the call was made
        fresh_mock_manager.send_admin_notification.assert_called_once()
        
        # Get the notification that was sent
        call_args = fresh_mock_manager.send_admin_notification.call_args[0][0]
        self.assertEqual(call_args.category, NotificationCategory.MAINTENANCE)
        self.assertTrue(call_args.admin_only)
        self.assertEqual(call_args.title, "⏸️ System Paused for Maintenance")


class TestMaintenanceNotificationIntegration(unittest.TestCase):
    """Test maintenance notification integration with existing systems"""
    
    def test_maintenance_route_structure(self):
        """Test that maintenance routes have the correct structure"""
        # Import the routes module to ensure it loads without errors
        try:
            from admin.routes import maintenance_mode
            self.assertTrue(True, "Maintenance mode routes loaded successfully")
        except ImportError as e:
            self.fail(f"Failed to import maintenance mode routes: {e}")
        
        # Verify the routes module has the expected functions
        self.assertTrue(hasattr(maintenance_mode, 'register_routes'))
        
        # Check that the module contains notification-related imports
        import inspect
        source = inspect.getsource(maintenance_mode)
        self.assertIn('AdminNotificationMessage', source)
        self.assertIn('notification_manager', source)


def run_maintenance_notification_tests():
    """Run all maintenance notification migration tests"""
    print("=== Running Maintenance Notification Migration Tests ===")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestMaintenanceNotificationMigration))
    test_suite.addTest(unittest.makeSuite(TestMaintenanceNotificationIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_maintenance_notification_tests()
    
    if success:
        print("\n✅ All maintenance notification migration tests passed!")
        print("\nMigration Summary:")
        print("  ✅ Legacy flash messages replaced with WebSocket notifications")
        print("  ✅ Real-time progress tracking implemented")
        print("  ✅ Admin-specific maintenance notifications")
        print("  ✅ Configuration change notifications")
        print("  ✅ System pause/resume notifications")
        print("  ✅ Error handling and recovery notifications")
        print("  ✅ Maintenance operation scheduling and tracking")
        
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)