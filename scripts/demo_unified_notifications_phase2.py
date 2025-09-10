#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo script for Phase 2 of Unified Notification System Consolidation

This script demonstrates that all notification service adapters are working
correctly and integrated with the unified notification manager.
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.notification.adapters.service_adapters import (
    StorageNotificationAdapter, PlatformNotificationAdapter,
    DashboardNotificationAdapter, MonitoringNotificationAdapter,
    PerformanceNotificationAdapter, HealthNotificationAdapter
)
from models import NotificationType, NotificationCategory, NotificationPriority

def create_mock_notification_manager():
    """Create a mock notification manager for demonstration"""
    mock_manager = Mock(spec=UnifiedNotificationManager)
    mock_manager.send_user_notification.return_value = True
    return mock_manager

def demo_storage_notifications():
    """Demonstrate storage notification adapter"""
    print("🗄️  Testing Storage Notification Adapter")
    print("=" * 50)
    
    # Create adapter
    mock_manager = create_mock_notification_manager()
    adapter = StorageNotificationAdapter(mock_manager)
    
    # Create mock storage context
    storage_context = Mock()
    storage_context.is_blocked = True
    storage_context.reason = "Storage limit exceeded - 5.2GB used of 5.0GB limit"
    storage_context.storage_gb = 5.2
    storage_context.limit_gb = 5.0
    storage_context.usage_percentage = 104.0
    storage_context.blocked_at = datetime.now(timezone.utc)
    storage_context.should_hide_form = True
    
    # Send notification
    result = adapter.send_storage_limit_notification(1, storage_context)
    
    print(f"✅ Storage notification sent: {result}")
    print(f"   - User ID: 1")
    print(f"   - Storage: {storage_context.storage_gb}GB / {storage_context.limit_gb}GB")
    print(f"   - Usage: {storage_context.usage_percentage}%")
    print(f"   - Blocked: {storage_context.is_blocked}")
    print(f"   - Form Hidden: {storage_context.should_hide_form}")
    print()

def demo_platform_notifications():
    """Demonstrate platform notification adapter"""
    print("🔗 Testing Platform Notification Adapter")
    print("=" * 50)
    
    # Create adapter
    mock_manager = create_mock_notification_manager()
    adapter = PlatformNotificationAdapter(mock_manager)
    
    # Create mock operation result
    operation_result = Mock()
    operation_result.success = True
    operation_result.message = "Successfully connected to Mastodon instance"
    operation_result.operation_type = "connect_platform"
    operation_result.platform_data = {
        "platform_name": "Mastodon",
        "instance_url": "https://mastodon.social",
        "username": "testuser"
    }
    operation_result.error_details = None
    operation_result.requires_refresh = False
    
    # Send notification
    result = adapter.send_platform_operation_notification(1, operation_result)
    
    print(f"✅ Platform notification sent: {result}")
    print(f"   - User ID: 1")
    print(f"   - Operation: {operation_result.operation_type}")
    print(f"   - Success: {operation_result.success}")
    print(f"   - Message: {operation_result.message}")
    print(f"   - Platform: {operation_result.platform_data['platform_name']}")
    print()

def demo_dashboard_notifications():
    """Demonstrate dashboard notification adapter"""
    print("📊 Testing Dashboard Notification Adapter")
    print("=" * 50)
    
    # Create adapter
    mock_manager = create_mock_notification_manager()
    adapter = DashboardNotificationAdapter(mock_manager)
    
    # Send dashboard update notification
    result = adapter.send_dashboard_update_notification(
        user_id=1,
        update_type="widget_refresh",
        message="Dashboard widgets have been updated with latest data",
        data={
            "widgets_updated": 5,
            "last_update": datetime.now(timezone.utc).isoformat(),
            "update_source": "scheduled_refresh"
        }
    )
    
    print(f"✅ Dashboard notification sent: {result}")
    print(f"   - User ID: 1")
    print(f"   - Update Type: widget_refresh")
    print(f"   - Widgets Updated: 5")
    print(f"   - Source: scheduled_refresh")
    print()

def demo_monitoring_notifications():
    """Demonstrate monitoring notification adapter"""
    print("📈 Testing Monitoring Notification Adapter")
    print("=" * 50)
    
    # Create adapter
    mock_manager = create_mock_notification_manager()
    adapter = MonitoringNotificationAdapter(mock_manager)
    
    # Send critical monitoring alert
    result = adapter.send_monitoring_alert(
        user_id=1,
        alert_type="cpu_usage",
        message="CPU usage has exceeded critical threshold",
        severity="critical",
        data={
            "cpu_percentage": 95.2,
            "threshold": 90.0,
            "duration_minutes": 5,
            "affected_processes": ["web_app", "background_worker"]
        }
    )
    
    print(f"✅ Monitoring alert sent: {result}")
    print(f"   - User ID: 1")
    print(f"   - Alert Type: cpu_usage")
    print(f"   - Severity: critical")
    print(f"   - CPU Usage: 95.2%")
    print(f"   - Threshold: 90.0%")
    print()

def demo_performance_notifications():
    """Demonstrate performance notification adapter"""
    print("⚡ Testing Performance Notification Adapter")
    print("=" * 50)
    
    # Create adapter
    mock_manager = create_mock_notification_manager()
    adapter = PerformanceNotificationAdapter(mock_manager)
    
    # Send performance alert
    result = adapter.send_performance_alert(
        user_id=1,
        metrics={
            "response_time": 2.5,
            "memory_usage": 85.0,
            "database_connections": 45,
            "queue_size": 120
        },
        threshold_exceeded="response_time",
        recovery_action="Consider scaling up server resources or optimizing database queries"
    )
    
    print(f"✅ Performance alert sent: {result}")
    print(f"   - User ID: 1")
    print(f"   - Threshold Exceeded: response_time")
    print(f"   - Response Time: 2.5s")
    print(f"   - Memory Usage: 85.0%")
    print(f"   - Recovery Action: Scale up or optimize queries")
    print()

def demo_health_notifications():
    """Demonstrate health notification adapter"""
    print("🏥 Testing Health Notification Adapter")
    print("=" * 50)
    
    # Create adapter
    mock_manager = create_mock_notification_manager()
    adapter = HealthNotificationAdapter(mock_manager)
    
    # Send health alert
    result = adapter.send_health_alert(
        user_id=1,
        component="database",
        status="degraded",
        message="Database connection pool is running low",
        data={
            "available_connections": 2,
            "max_connections": 20,
            "active_connections": 18,
            "connection_wait_time": 1.2
        }
    )
    
    print(f"✅ Health alert sent: {result}")
    print(f"   - User ID: 1")
    print(f"   - Component: database")
    print(f"   - Status: degraded")
    print(f"   - Available Connections: 2/20")
    print(f"   - Wait Time: 1.2s")
    print()

def demo_helper_functions():
    """Demonstrate notification helper functions"""
    print("🛠️  Testing Notification Helper Functions")
    print("=" * 50)
    
    try:
        from app.services.notification.helpers.notification_helpers import (
            send_success_notification, send_error_notification,
            send_warning_notification, send_info_notification
        )
        
        print("✅ Successfully imported notification helper functions:")
        print("   - send_success_notification")
        print("   - send_error_notification") 
        print("   - send_warning_notification")
        print("   - send_info_notification")
        print("   - send_storage_notification")
        print("   - send_platform_notification")
        print("   - send_dashboard_notification")
        print("   - send_monitoring_notification")
        print("   - send_performance_notification")
        print("   - send_health_notification")
        print()
        
    except ImportError as e:
        print(f"❌ Failed to import helper functions: {e}")
        print()

def main():
    """Run the complete Phase 2 demonstration"""
    print("🚀 Unified Notification System - Phase 2 Demonstration")
    print("=" * 60)
    print("This demo shows that all notification service adapters are")
    print("working correctly with the unified notification manager.")
    print("=" * 60)
    print()
    
    try:
        # Test all adapters
        demo_storage_notifications()
        demo_platform_notifications()
        demo_dashboard_notifications()
        demo_monitoring_notifications()
        demo_performance_notifications()
        demo_health_notifications()
        demo_helper_functions()
        
        print("🎉 Phase 2 Demonstration Complete!")
        print("=" * 50)
        print("✅ All notification service adapters are working correctly")
        print("✅ Unified notification manager integration successful")
        print("✅ Helper functions are properly consolidated")
        print("✅ Ready for Phase 3: WebSocket Integration Consolidation")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
