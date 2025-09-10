#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unified Notification System Demonstration

This script demonstrates the consolidated notification system functionality.
It shows how multiple notification types are now handled through a single unified system.
"""

import sys
import os
from unittest.mock import Mock
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notification.adapters.service_adapters import (
    StorageNotificationAdapter,
    PlatformNotificationAdapter,
    DashboardNotificationAdapter,
    MonitoringNotificationAdapter,
    PerformanceNotificationAdapter,
    HealthNotificationAdapter
)
from models import NotificationType, NotificationCategory, NotificationPriority

def demo_unified_notifications():
    """Demonstrate unified notification system"""
    print("🔔 Unified Notification System Demonstration")
    print("=" * 50)
    
    # Create a proper mock that passes isinstance check
    from app.services.notification.manager.unified_manager import UnifiedNotificationManager
    
    class MockUnifiedNotificationManager(UnifiedNotificationManager):
        def __init__(self):
            # Don't call super().__init__ to avoid dependencies
            self.call_count = 0
            self.last_message = None
        
        def send_user_notification(self, user_id, message):
            self.call_count += 1
            self.last_message = message
            return True
    
    mock_notification_manager = MockUnifiedNotificationManager()
    test_user_id = 1
    
    # 1. Storage Notifications
    print("\n📦 Storage Notifications")
    print("-" * 25)
    
    storage_adapter = StorageNotificationAdapter(mock_notification_manager)
    
    # Mock storage context
    storage_context = Mock()
    storage_context.is_blocked = True
    storage_context.reason = "Storage limit of 5GB exceeded (currently using 5.2GB)"
    storage_context.storage_gb = 5.2
    storage_context.limit_gb = 5.0
    storage_context.usage_percentage = 104.0
    storage_context.blocked_at = datetime.now(timezone.utc)
    storage_context.should_hide_form = True
    
    result = storage_adapter.send_storage_limit_notification(test_user_id, storage_context)
    print(f"✅ Storage notification sent: {result}")
    
    # Verify the call
    if mock_notification_manager.last_message:
        message = mock_notification_manager.last_message
        print(f"   Category: {message.category.value}")
        print(f"   Type: {message.type.value}")
        print(f"   Title: {message.title}")
        print(f"   Message: {message.message}")
    
    # 2. Platform Notifications
    print("\n🔗 Platform Notifications")
    print("-" * 26)
    
    platform_adapter = PlatformNotificationAdapter(mock_notification_manager)
    
    # Mock platform operation result
    operation_result = Mock()
    operation_result.success = True
    operation_result.message = "Successfully connected to Mastodon instance"
    operation_result.operation_type = "connect_platform"
    operation_result.platform_data = {"platform_name": "Mastodon", "instance": "mastodon.social"}
    operation_result.error_details = None
    operation_result.requires_refresh = False
    
    result = platform_adapter.send_platform_operation_notification(test_user_id, operation_result)
    print(f"✅ Platform notification sent: {result}")
    
    # 3. Dashboard Notifications
    print("\n📊 Dashboard Notifications")
    print("-" * 27)
    
    dashboard_adapter = DashboardNotificationAdapter(mock_notification_manager)
    
    result = dashboard_adapter.send_dashboard_update_notification(
        test_user_id,
        "stats_update",
        "Dashboard statistics have been refreshed",
        {"updated_at": datetime.now(timezone.utc).isoformat()}
    )
    print(f"✅ Dashboard notification sent: {result}")
    
    # 4. Monitoring Notifications
    print("\n📈 Monitoring Notifications")
    print("-" * 28)
    
    monitoring_adapter = MonitoringNotificationAdapter(mock_notification_manager)
    
    result = monitoring_adapter.send_monitoring_alert(
        test_user_id,
        "cpu_usage",
        "CPU usage has exceeded 85% for the last 5 minutes",
        "warning",
        {"cpu_percentage": 87.5, "duration_minutes": 5}
    )
    print(f"✅ Monitoring notification sent: {result}")
    
    # 5. Performance Notifications
    print("\n⚡ Performance Notifications")
    print("-" * 29)
    
    performance_adapter = PerformanceNotificationAdapter(mock_notification_manager)
    
    metrics = {
        "response_time": 2.8,
        "cpu_usage": 85.0,
        "memory_usage": 78.5,
        "active_connections": 150
    }
    
    result = performance_adapter.send_performance_alert(
        test_user_id,
        metrics,
        "Response time > 2.5s",
        "Consider scaling up server resources"
    )
    print(f"✅ Performance notification sent: {result}")
    
    # 6. Health Notifications
    print("\n🏥 Health Notifications")
    print("-" * 24)
    
    health_adapter = HealthNotificationAdapter(mock_notification_manager)
    
    result = health_adapter.send_health_alert(
        test_user_id,
        "database",
        "degraded",
        "Database response time is slower than normal",
        {"response_time_ms": 850, "threshold_ms": 500}
    )
    print(f"✅ Health notification sent: {result}")
    
    # Summary
    print("\n📋 Consolidation Summary")
    print("-" * 25)
    print("✅ All notification types now use unified system")
    print("✅ Consistent API across all notification categories")
    print("✅ Single point of maintenance and testing")
    print("✅ Improved performance and reliability")
    
    total_calls = mock_notification_manager.call_count
    print(f"\n📊 Total unified notifications sent: {total_calls}")
    
    # Show all categories covered
    print("\n🏷️  Notification Categories Consolidated:")
    categories = [
        NotificationCategory.STORAGE,
        NotificationCategory.PLATFORM,
        NotificationCategory.DASHBOARD,
        NotificationCategory.MONITORING,
        NotificationCategory.PERFORMANCE,
        NotificationCategory.HEALTH
    ]
    
    for category in categories:
        print(f"   • {category.value}")
    
    print("\n🎉 Unified Notification System Consolidation Complete!")

if __name__ == "__main__":
    demo_unified_notifications()
