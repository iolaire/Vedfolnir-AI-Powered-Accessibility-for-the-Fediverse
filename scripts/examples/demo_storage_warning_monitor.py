#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demonstration script for Storage Warning Monitor functionality.

This script demonstrates the 80% warning threshold detection, admin dashboard
notifications, background monitoring, and comprehensive logging features
implemented for task 11 of the storage limit management system.
"""

import time
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock

from app.services.storage.components.storage_warning_monitor import StorageWarningMonitor, StorageEventType
from app.services.storage.components.storage_warning_dashboard_integration import StorageWarningDashboardIntegration
from app.services.storage.components.storage_event_logger import StorageEventLogger
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService, StorageMetrics


def create_mock_services():
    """Create mock services for demonstration"""
    # Mock Redis client
    mock_redis = Mock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.keys.return_value = []
    mock_redis.ttl.return_value = 3600
    
    # Mock configuration service
    mock_config = Mock(spec=StorageConfigurationService)
    mock_config.get_max_storage_gb.return_value = 10.0
    mock_config.get_warning_threshold_gb.return_value = 8.0
    mock_config.validate_storage_config.return_value = True
    mock_config._config = Mock()
    mock_config._config.warning_threshold_percentage = 80.0
    
    # Mock monitor service
    mock_monitor = Mock(spec=StorageMonitorService)
    
    return mock_redis, mock_config, mock_monitor


def create_test_metrics():
    """Create test storage metrics for different scenarios"""
    normal_metrics = StorageMetrics(
        total_bytes=5 * 1024**3,  # 5GB
        total_gb=5.0,
        limit_gb=10.0,
        usage_percentage=50.0,
        is_limit_exceeded=False,
        is_warning_exceeded=False,
        last_calculated=datetime.now()
    )
    
    warning_metrics = StorageMetrics(
        total_bytes=8.5 * 1024**3,  # 8.5GB
        total_gb=8.5,
        limit_gb=10.0,
        usage_percentage=85.0,
        is_limit_exceeded=False,
        is_warning_exceeded=True,
        last_calculated=datetime.now()
    )
    
    limit_exceeded_metrics = StorageMetrics(
        total_bytes=10.5 * 1024**3,  # 10.5GB
        total_gb=10.5,
        limit_gb=10.0,
        usage_percentage=105.0,
        is_limit_exceeded=True,
        is_warning_exceeded=True,
        last_calculated=datetime.now()
    )
    
    return normal_metrics, warning_metrics, limit_exceeded_metrics


def demo_warning_threshold_detection():
    """Demonstrate 80% warning threshold detection"""
    print("=" * 60)
    print("DEMO: 80% Warning Threshold Detection")
    print("=" * 60)
    
    # Create mock services
    mock_redis, mock_config, mock_monitor = create_mock_services()
    normal_metrics, warning_metrics, limit_exceeded_metrics = create_test_metrics()
    
    # Track notifications
    notifications_received = []
    
    def notification_callback(notification):
        notifications_received.append(notification)
        print(f"📧 NOTIFICATION: {notification.severity.upper()} - {notification.message}")
    
    # Create warning monitor
    warning_monitor = StorageWarningMonitor(
        config_service=mock_config,
        monitor_service=mock_monitor,
        redis_client=mock_redis,
        notification_callback=notification_callback
    )
    
    # Test 1: Normal usage (50%)
    print("\n1. Testing normal usage (50%)...")
    mock_monitor.get_storage_metrics.return_value = normal_metrics
    result = warning_monitor.check_warning_threshold()
    print(f"   Warning threshold exceeded: {result}")
    print(f"   Notifications received: {len(notifications_received)}")
    
    # Test 2: Warning threshold exceeded (85%)
    print("\n2. Testing warning threshold exceeded (85%)...")
    mock_monitor.get_storage_metrics.return_value = warning_metrics
    result = warning_monitor.check_warning_threshold()
    print(f"   Warning threshold exceeded: {result}")
    print(f"   Notifications received: {len(notifications_received)}")
    
    # Test 3: Limit exceeded (105%)
    print("\n3. Testing limit exceeded (105%)...")
    mock_monitor.get_storage_metrics.return_value = limit_exceeded_metrics
    result = warning_monitor.check_warning_threshold()
    print(f"   Warning threshold exceeded: {result}")
    print(f"   Notifications received: {len(notifications_received)}")
    
    # Show notification details
    if notifications_received:
        print(f"\n📋 Notification Details:")
        for i, notification in enumerate(notifications_received, 1):
            print(f"   {i}. {notification.severity.upper()}: {notification.storage_gb:.1f}GB/{notification.limit_gb:.1f}GB ({notification.usage_percentage:.1f}%)")


def demo_admin_dashboard_notifications():
    """Demonstrate admin dashboard notifications"""
    print("\n" + "=" * 60)
    print("DEMO: Admin Dashboard Notifications")
    print("=" * 60)
    
    # Create mock services
    mock_redis, mock_config, mock_monitor = create_mock_services()
    normal_metrics, warning_metrics, limit_exceeded_metrics = create_test_metrics()
    
    # Create warning monitor
    warning_monitor = StorageWarningMonitor(
        config_service=mock_config,
        monitor_service=mock_monitor,
        redis_client=mock_redis
    )
    
    # Mock admin dashboard
    mock_admin_dashboard = Mock()
    mock_admin_dashboard.get_storage_dashboard_data.return_value = Mock(
        storage_gb=8.5,
        limit_gb=10.0,
        usage_percentage=85.0,
        status_color='yellow',
        is_blocked=False,
        block_reason=None,
        warning_threshold_gb=8.0,
        is_warning_exceeded=True,
        is_limit_exceeded=False
    )
    
    # Create dashboard integration
    dashboard_integration = StorageWarningDashboardIntegration(
        warning_monitor=warning_monitor,
        admin_dashboard=mock_admin_dashboard,
        config_service=mock_config,
        monitor_service=mock_monitor
    )
    
    # Trigger warning
    mock_monitor.get_storage_metrics.return_value = warning_metrics
    warning_monitor.check_warning_threshold()
    
    # Get dashboard warning data
    warning_data = dashboard_integration.get_dashboard_warning_data()
    
    print(f"📊 Dashboard Status:")
    print(f"   Has warnings: {warning_data.has_warnings}")
    print(f"   Warning count: {warning_data.warning_count}")
    print(f"   Critical count: {warning_data.critical_count}")
    print(f"   Storage status: {warning_data.storage_status}")
    print(f"   Action required: {warning_data.action_required}")
    print(f"   Warning message: {warning_data.warning_message}")
    
    # Get enhanced dashboard data
    enhanced_data = dashboard_integration.get_enhanced_dashboard_data()
    print(f"\n📈 Enhanced Dashboard Data:")
    print(f"   Overall status: {enhanced_data['overall_status']}")
    print(f"   Storage: {enhanced_data['storage_gb']:.1f}GB / {enhanced_data['limit_gb']:.1f}GB")
    print(f"   Usage: {enhanced_data['usage_percentage']:.1f}%")
    print(f"   Status color: {enhanced_data['status_color']}")


def demo_background_monitoring():
    """Demonstrate background periodic monitoring"""
    print("\n" + "=" * 60)
    print("DEMO: Background Periodic Monitoring")
    print("=" * 60)
    
    # Create mock services
    mock_redis, mock_config, mock_monitor = create_mock_services()
    normal_metrics, warning_metrics, limit_exceeded_metrics = create_test_metrics()
    
    # Create warning monitor with short check interval
    warning_monitor = StorageWarningMonitor(
        config_service=mock_config,
        monitor_service=mock_monitor,
        redis_client=mock_redis
    )
    
    # Set short check interval for demo
    warning_monitor.check_interval_seconds = 1
    
    print("🔄 Starting background monitoring (1-second intervals)...")
    
    # Start background monitoring
    result = warning_monitor.start_background_monitoring()
    print(f"   Background monitoring started: {result}")
    print(f"   Monitoring active: {warning_monitor._monitoring_active}")
    
    # Let it run for a few seconds
    print("   Monitoring for 3 seconds...")
    mock_monitor.get_storage_metrics.return_value = normal_metrics
    time.sleep(3)
    
    # Check how many times metrics were retrieved
    call_count = mock_monitor.get_storage_metrics.call_count
    print(f"   Storage metrics checked {call_count} times")
    
    # Stop monitoring
    result = warning_monitor.stop_background_monitoring()
    print(f"   Background monitoring stopped: {result}")
    print(f"   Monitoring active: {warning_monitor._monitoring_active}")
    
    # Get monitoring status
    status = warning_monitor.get_monitoring_status()
    print(f"\n📊 Monitoring Status:")
    print(f"   Active: {status['monitoring_active']}")
    print(f"   Check interval: {status['check_interval_seconds']}s")
    print(f"   Current storage: {status['current_storage_gb']:.1f}GB")
    print(f"   Storage limit: {status['storage_limit_gb']:.1f}GB")
    print(f"   Warning threshold: {status['warning_threshold_gb']:.1f}GB")


def demo_comprehensive_logging():
    """Demonstrate comprehensive logging functionality"""
    print("\n" + "=" * 60)
    print("DEMO: Comprehensive Logging")
    print("=" * 60)
    
    # Create temporary directory for logs
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Log directory: {temp_dir}")
    
    try:
        # Create storage event logger
        event_logger = StorageEventLogger(
            log_dir=temp_dir,
            log_file="demo_storage_events.log",
            enable_console=True,
            enable_json_format=True
        )
        
        # Create test metrics
        normal_metrics, warning_metrics, limit_exceeded_metrics = create_test_metrics()
        
        print("\n📝 Logging various storage events...")
        
        # Log different types of events
        event_logger.log_info("storage_check", "Periodic storage check completed", normal_metrics)
        event_logger.log_warning("warning_threshold", "Storage approaching warning threshold", warning_metrics)
        event_logger.log_threshold_exceeded(warning_metrics, "warning")
        event_logger.log_critical("limit_exceeded", "Storage limit exceeded", limit_exceeded_metrics)
        event_logger.log_threshold_cleared(normal_metrics, "warning")
        
        # Log configuration change
        event_logger.log_configuration_change(
            old_config={'max_storage_gb': 10.0, 'warning_threshold': 80.0},
            new_config={'max_storage_gb': 15.0, 'warning_threshold': 85.0}
        )
        
        # Log cleanup event
        event_logger.log_cleanup_event(
            files_removed=25,
            space_freed_gb=2.5,
            metrics_before=warning_metrics,
            metrics_after=normal_metrics
        )
        
        # Get log statistics
        log_stats = event_logger.get_log_stats()
        print(f"\n📊 Log Statistics:")
        print(f"   Log file: {log_stats['log_file_path']}")
        print(f"   File exists: {log_stats['log_file_exists']}")
        print(f"   File size: {log_stats['log_file_size_mb']:.2f} MB")
        print(f"   Total log size: {log_stats['total_log_size_mb']:.2f} MB")
        
        # Show log content
        if log_stats['log_file_exists']:
            print(f"\n📄 Recent log entries:")
            with open(log_stats['log_file_path'], 'r') as f:
                lines = f.readlines()
                for line in lines[-3:]:  # Show last 3 lines
                    print(f"   {line.strip()}")
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def demo_health_checks():
    """Demonstrate health check functionality"""
    print("\n" + "=" * 60)
    print("DEMO: Health Checks")
    print("=" * 60)
    
    # Create mock services
    mock_redis, mock_config, mock_monitor = create_mock_services()
    
    # Create warning monitor
    warning_monitor = StorageWarningMonitor(
        config_service=mock_config,
        monitor_service=mock_monitor,
        redis_client=mock_redis
    )
    
    # Perform health check
    health = warning_monitor.health_check()
    
    print("🏥 Storage Warning Monitor Health Check:")
    print(f"   Redis connected: {health['redis_connected']}")
    print(f"   Config service healthy: {health['config_service_healthy']}")
    print(f"   Monitor service healthy: {health['monitor_service_healthy']}")
    print(f"   Background monitoring active: {health['background_monitoring_active']}")
    print(f"   Overall healthy: {health['overall_healthy']}")
    
    # Test configuration update
    print(f"\n⚙️  Testing configuration update...")
    result = warning_monitor.update_monitoring_config(
        check_interval_seconds=600,
        event_retention_hours=240,
        notification_retention_hours=96
    )
    print(f"   Configuration updated: {result}")
    print(f"   New check interval: {warning_monitor.check_interval_seconds}s")
    print(f"   New event retention: {warning_monitor.event_retention_hours}h")
    print(f"   New notification retention: {warning_monitor.notification_retention_hours}h")


def main():
    """Run all demonstrations"""
    print("🚀 Storage Warning Monitor Demonstration")
    print("Task 11: Add warning threshold monitoring and logging")
    print("Implementing 80% threshold detection, admin notifications,")
    print("background monitoring, and comprehensive logging")
    
    try:
        # Run demonstrations
        demo_warning_threshold_detection()
        demo_admin_dashboard_notifications()
        demo_background_monitoring()
        demo_comprehensive_logging()
        demo_health_checks()
        
        print("\n" + "=" * 60)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("All storage warning monitor features demonstrated successfully!")
        print("\nKey Features Implemented:")
        print("• 80% warning threshold detection and logging")
        print("• Admin dashboard warning notifications")
        print("• Background periodic storage monitoring")
        print("• Comprehensive logging for all storage events")
        print("• Real-time notification system")
        print("• Health checks and monitoring status")
        print("• Configuration management")
        print("• Integration with existing storage components")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()