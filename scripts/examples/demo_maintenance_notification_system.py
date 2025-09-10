#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo: Maintenance Notification System Integration

Demonstrates the unified maintenance notification system with real-time progress
updates, WebSocket integration, and comprehensive admin notifications.
"""

import sys
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_maintenance_notification_system():
    """
    Demonstrate the maintenance notification system integration
    """
    print("=== Maintenance Notification System Demo ===")
    
    try:
        # Import required modules
        from dotenv import load_dotenv
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from app.services.notification.manager.unified_manager import UnifiedNotificationManager
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler, MaintenanceNotificationData
        from maintenance_progress_websocket_handler import MaintenanceProgressWebSocketHandler
        from maintenance_notification_integration_service import (
            MaintenanceNotificationIntegrationService, 
            MaintenanceOperation, 
            MaintenanceOperationType
        )
        from models import User, UserRole
        
        # Load configuration
        load_dotenv()
        config = Config()
        db_manager = DatabaseManager(config)
        
        print("✅ Configuration loaded successfully")
        
        # Get admin user for testing
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
            if not admin_user:
                print("❌ No admin user found. Please create an admin user first.")
                return False
        
        print(f"✅ Found admin user: {admin_user.username}")
        
        # Create notification system components
        notification_manager = UnifiedNotificationManager(
            websocket_factory=None,  # Mock for demo
            auth_handler=None,  # Mock for demo
            namespace_manager=None,  # Mock for demo
            db_manager=db_manager
        )
        
        progress_handler = MaintenanceProgressWebSocketHandler(
            notification_manager=notification_manager,
            socketio_instance=None  # Mock for demo
        )
        
        integration_service = MaintenanceNotificationIntegrationService(
            notification_manager=notification_manager,
            progress_handler=progress_handler,
            db_manager=db_manager
        )
        
        print("✅ Notification system components initialized")
        
        # Demo 1: Basic maintenance notification
        print("\n--- Demo 1: Basic Maintenance Notifications ---")
        
        maintenance_handler = AdminMaintenanceNotificationHandler(
            notification_manager, db_manager
        )
        
        # Send system pause notification
        pause_success = maintenance_handler.send_system_pause_notification(
            admin_user.id, {
                'reason': 'Scheduled database maintenance',
                'duration': 30,
                'mode': 'normal',
                'affected_operations': ['caption_generation', 'platform_operations'],
                'estimated_completion': (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
            }
        )
        
        print(f"System pause notification: {'✅ Sent' if pause_success else '❌ Failed'}")
        
        # Send configuration change notification
        config_success = maintenance_handler.send_configuration_change_notification(
            admin_user.id, {
                'change_description': 'Updated WebSocket CORS settings',
                'changed_settings': ['WEBSOCKET_CORS_ORIGINS', 'WEBSOCKET_TIMEOUT'],
                'requires_restart': False,
                'change_type': 'configuration_update'
            }
        )
        
        print(f"Configuration change notification: {'✅ Sent' if config_success else '❌ Failed'}")
        
        # Demo 2: Progress tracking with WebSocket updates
        print("\n--- Demo 2: Progress Tracking with WebSocket Updates ---")
        
        operation_id = f"demo_maintenance_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Register maintenance operation
        register_success = progress_handler.register_maintenance_operation(
            operation_id=operation_id,
            operation_type="database_maintenance",
            admin_user_id=admin_user.id,
            total_steps=5,
            estimated_duration=120  # 2 minutes
        )
        
        print(f"Operation registration: {'✅ Success' if register_success else '❌ Failed'}")
        
        if register_success:
            # Simulate progress updates
            progress_steps = [
                (20, "Backing up database"),
                (40, "Optimizing tables"),
                (60, "Rebuilding indexes"),
                (80, "Updating statistics"),
                (100, "Maintenance completed")
            ]
            
            for progress, step_description in progress_steps:
                update_success = progress_handler.update_progress(
                    operation_id=operation_id,
                    progress_percentage=progress,
                    current_step=step_description,
                    message=f"Database maintenance: {step_description}"
                )
                
                print(f"Progress update ({progress}%): {'✅ Sent' if update_success else '❌ Failed'}")
                time.sleep(1)  # Simulate work time
        
        # Demo 3: Comprehensive maintenance operation
        print("\n--- Demo 3: Comprehensive Maintenance Operation ---")
        
        # Create maintenance operation
        maintenance_operation = MaintenanceOperation(
            operation_id=f"comprehensive_demo_{int(datetime.now(timezone.utc).timestamp())}",
            operation_type=MaintenanceOperationType.PERFORMANCE_OPTIMIZATION,
            title="System Performance Optimization",
            description="Comprehensive system performance optimization including database tuning and cache optimization",
            admin_user_id=admin_user.id,
            estimated_duration=15,  # 15 minutes
            affects_users=True,
            requires_downtime=False,
            rollback_available=True,
            scheduled_time=datetime.now(timezone.utc) + timedelta(minutes=1),
            auto_start=False
        )
        
        # Schedule the operation
        schedule_success = integration_service.schedule_maintenance_operation(maintenance_operation)
        print(f"Operation scheduling: {'✅ Success' if schedule_success else '❌ Failed'}")
        
        # Start the operation
        start_success = integration_service.start_maintenance_operation(maintenance_operation)
        print(f"Operation start: {'✅ Success' if start_success else '❌ Failed'}")
        
        if start_success:
            # Simulate some progress updates
            time.sleep(2)
            
            integration_service.update_operation_progress(
                maintenance_operation.operation_id,
                25,
                "Analyzing system performance",
                "Performance analysis in progress"
            )
            
            time.sleep(2)
            
            integration_service.update_operation_progress(
                maintenance_operation.operation_id,
                50,
                "Optimizing database queries",
                "Database optimization in progress"
            )
            
            time.sleep(2)
            
            integration_service.update_operation_progress(
                maintenance_operation.operation_id,
                75,
                "Tuning cache settings",
                "Cache optimization in progress"
            )
            
            time.sleep(2)
            
            # Complete the operation
            complete_success = integration_service.complete_maintenance_operation(
                maintenance_operation.operation_id,
                success=True,
                completion_message="Performance optimization completed successfully",
                final_details={
                    'performance_improvement': '15%',
                    'optimized_queries': 25,
                    'cache_hit_rate': '95%'
                }
            )
            
            print(f"Operation completion: {'✅ Success' if complete_success else '❌ Failed'}")
        
        # Demo 4: Error handling and recovery
        print("\n--- Demo 4: Error Handling and Recovery ---")
        
        error_operation_id = f"error_demo_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Register operation that will have an error
        error_register_success = progress_handler.register_maintenance_operation(
            operation_id=error_operation_id,
            operation_type="backup_operation",
            admin_user_id=admin_user.id,
            total_steps=3,
            estimated_duration=60
        )
        
        if error_register_success:
            # Simulate progress then error
            progress_handler.update_progress(
                error_operation_id, 30, "Creating backup files"
            )
            
            time.sleep(1)
            
            # Report an error
            error_success = progress_handler.report_error(
                error_operation_id,
                "Insufficient disk space for backup",
                error_details={
                    'required_space': '10GB',
                    'available_space': '5GB',
                    'error_code': 'DISK_SPACE_ERROR'
                },
                recoverable=True
            )
            
            print(f"Error reporting: {'✅ Success' if error_success else '❌ Failed'}")
            
            time.sleep(2)
            
            # Simulate recovery
            progress_handler.update_progress(
                error_operation_id, 60, "Cleaning up temporary files to free space"
            )
            
            time.sleep(1)
            
            progress_handler.update_progress(
                error_operation_id, 100, "Backup completed after cleanup"
            )
        
        # Demo 5: System resume notification
        print("\n--- Demo 5: System Resume Notification ---")
        
        resume_success = maintenance_handler.send_system_resume_notification(
            admin_user.id, {
                'maintenance_duration': '45 minutes',
                'completed_operations': ['database_maintenance', 'performance_optimization'],
                'restored_functionality': ['caption_generation', 'platform_operations', 'user_sessions']
            }
        )
        
        print(f"System resume notification: {'✅ Sent' if resume_success else '❌ Failed'}")
        
        # Demo 6: Active operations monitoring
        print("\n--- Demo 6: Active Operations Monitoring ---")
        
        active_operations = progress_handler.get_active_operations()
        print(f"Active operations count: {len(active_operations)}")
        
        for op_id, op_info in active_operations.items():
            print(f"  - {op_id}: {op_info['operation_type']} ({op_info['status']})")
        
        # Cleanup stale operations
        cleaned_count = progress_handler.cleanup_stale_operations(max_age_hours=1)
        print(f"Cleaned up {cleaned_count} stale operations")
        
        print("\n=== Demo Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        print(f"❌ Demo failed: {e}")
        return False


def demo_maintenance_error_scenarios():
    """
    Demonstrate error scenarios and recovery mechanisms
    """
    print("\n=== Error Scenarios Demo ===")
    
    try:
        from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
        from dotenv import load_dotenv
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from app.services.notification.manager.unified_manager import UnifiedNotificationManager
        from models import User, UserRole
        
        # Load configuration
        load_dotenv()
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Get admin user
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
            if not admin_user:
                print("❌ No admin user found")
                return False
        
        # Create notification manager
        notification_manager = UnifiedNotificationManager(
            websocket_factory=None,
            auth_handler=None,
            namespace_manager=None,
            db_manager=db_manager
        )
        
        maintenance_handler = AdminMaintenanceNotificationHandler(
            notification_manager, db_manager
        )
        
        # Demo critical error notification
        error_success = maintenance_handler.send_maintenance_error_notification(
            admin_user.id, {
                'error_message': 'Critical database connection failure during maintenance',
                'error_code': 'DB_CONNECTION_LOST',
                'operation_id': 'critical_maintenance_001',
                'failed_operation': 'database_optimization',
                'rollback_required': True,
                'immediate_action_required': True
            }
        )
        
        print(f"Critical error notification: {'✅ Sent' if error_success else '❌ Failed'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error scenarios demo failed: {e}")
        return False


if __name__ == "__main__":
    print("Starting Maintenance Notification System Demo...")
    
    # Run main demo
    main_success = demo_maintenance_notification_system()
    
    if main_success:
        # Run error scenarios demo
        error_success = demo_maintenance_error_scenarios()
        
        if error_success:
            print("\n🎉 All demos completed successfully!")
            print("\nThe maintenance notification system provides:")
            print("  ✅ Real-time WebSocket progress updates")
            print("  ✅ Comprehensive admin notifications")
            print("  ✅ Error handling and recovery")
            print("  ✅ Operation scheduling and tracking")
            print("  ✅ Configuration change notifications")
            print("  ✅ System pause/resume notifications")
            
            sys.exit(0)
        else:
            print("❌ Error scenarios demo failed")
            sys.exit(1)
    else:
        print("❌ Main demo failed")
        sys.exit(1)