#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demonstration script for storage health monitoring system.

This script demonstrates the comprehensive storage health monitoring capabilities
including health checks, dashboard integration, and alert system functionality.
"""

import json
import time
from datetime import datetime

from app.services.monitoring.health.checkers.storage_health_checker import StorageHealthChecker, StorageHealthStatus
from app.services.storage.components.storage_monitoring_dashboard_integration import StorageMonitoringDashboardIntegration
from app.services.storage.components.storage_alert_system import StorageAlertSystem
from app.services.storage.components.storage_configuration_service import StorageConfigurationService
from app.services.storage.components.storage_monitor_service import StorageMonitorService


def demo_storage_health_checker():
    """Demonstrate storage health checker functionality"""
    print("\n" + "=" * 60)
    print("DEMO: Storage Health Checker")
    print("=" * 60)
    
    # Initialize health checker
    print("🔧 Initializing storage health checker...")
    health_checker = StorageHealthChecker()
    
    # Perform comprehensive health check
    print("🏥 Performing comprehensive health check...")
    health_result = health_checker.check_comprehensive_health()
    
    print(f"📊 Overall Status: {health_result.overall_status.value}")
    print(f"📅 Timestamp: {health_result.timestamp}")
    print(f"🔧 Components: {len(health_result.components)}")
    
    # Display component health
    print("\n📋 Component Health:")
    for name, component in health_result.components.items():
        status_emoji = {
            StorageHealthStatus.HEALTHY: "✅",
            StorageHealthStatus.DEGRADED: "⚠️",
            StorageHealthStatus.UNHEALTHY: "❌",
            StorageHealthStatus.ERROR: "🚨"
        }.get(component.status, "❓")
        
        print(f"   {status_emoji} {name}: {component.status.value}")
        print(f"      Message: {component.message}")
        if component.response_time_ms:
            print(f"      Response Time: {component.response_time_ms:.1f}ms")
    
    # Display summary
    print(f"\n📈 Summary:")
    print(f"   Total Components: {health_result.summary['total_components']}")
    print(f"   Healthy: {health_result.summary['healthy_components']}")
    print(f"   Degraded: {health_result.summary['degraded_components']}")
    print(f"   Unhealthy: {health_result.summary['unhealthy_components']}")
    print(f"   Error: {health_result.summary['error_components']}")
    print(f"   Health Percentage: {health_result.summary['health_percentage']:.1f}%")
    
    # Display alerts
    if health_result.alerts:
        print(f"\n🚨 Alerts ({len(health_result.alerts)}):")
        for alert in health_result.alerts:
            severity_emoji = {
                'critical': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️'
            }.get(alert['severity'], '❓')
            print(f"   {severity_emoji} {alert['message']}")
    else:
        print("\n✅ No alerts - system is healthy!")
    
    # Display performance metrics
    print(f"\n⚡ Performance Metrics:")
    for metric, value in health_result.performance_metrics.items():
        if isinstance(value, (int, float)):
            print(f"   {metric}: {value:.2f}")
    
    return health_result


def demo_dashboard_integration():
    """Demonstrate dashboard integration functionality"""
    print("\n" + "=" * 60)
    print("DEMO: Dashboard Integration")
    print("=" * 60)
    
    # Initialize dashboard integration
    print("🔧 Initializing dashboard integration...")
    dashboard_integration = StorageMonitoringDashboardIntegration()
    
    # Get dashboard metrics
    print("📊 Getting dashboard metrics...")
    metrics = dashboard_integration.get_storage_dashboard_metrics()
    
    print("💾 Storage Usage:")
    if 'storage_usage' in metrics:
        usage = metrics['storage_usage']
        print(f"   Current: {usage['current_gb']:.2f}GB")
        print(f"   Limit: {usage['limit_gb']:.2f}GB")
        print(f"   Usage: {usage['usage_percentage']:.1f}%")
        print(f"   Limit Exceeded: {'Yes' if usage['is_limit_exceeded'] else 'No'}")
        print(f"   Warning Exceeded: {'Yes' if usage['is_warning_exceeded'] else 'No'}")
    
    print("\n🏥 System Health:")
    if 'system_health' in metrics:
        health = metrics['system_health']
        print(f"   Status: {health['overall_status']}")
        print(f"   Healthy Components: {health['healthy_components']}/{health['total_components']}")
        print(f"   Health Percentage: {health['health_percentage']:.1f}%")
    
    print("\n🛡️ Enforcement:")
    if 'enforcement' in metrics:
        enforcement = metrics['enforcement']
        print(f"   Currently Blocked: {'Yes' if enforcement['currently_blocked'] else 'No'}")
        print(f"   Total Checks: {enforcement['total_checks']}")
        print(f"   Blocks Enforced: {enforcement['blocks_enforced']}")
        print(f"   Automatic Unblocks: {enforcement['automatic_unblocks']}")
    
    # Get dashboard alerts
    print("\n🚨 Getting dashboard alerts...")
    alerts = dashboard_integration.get_storage_dashboard_alerts()
    
    if alerts:
        print(f"📢 Dashboard Alerts ({len(alerts)}):")
        for alert in alerts:
            severity_emoji = {
                'critical': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️'
            }.get(alert['severity'], '❓')
            print(f"   {severity_emoji} {alert['title']}: {alert['message']}")
    else:
        print("✅ No dashboard alerts!")
    
    # Demonstrate widget data
    print("\n🎛️ Widget Data Examples:")
    
    # Storage usage gauge
    gauge_data = dashboard_integration.get_storage_widget_data('storage_usage_gauge')
    if 'error' not in gauge_data:
        print(f"   📊 Usage Gauge: {gauge_data['value']:.1f}% ({gauge_data['status']})")
    
    # Storage health status
    health_data = dashboard_integration.get_storage_widget_data('storage_health_status')
    if 'error' not in health_data:
        print(f"   🏥 Health Status: {health_data['status']} ({health_data['color']})")
    
    return metrics, alerts


def demo_alert_system():
    """Demonstrate alert system functionality"""
    print("\n" + "=" * 60)
    print("DEMO: Alert System")
    print("=" * 60)
    
    # Initialize alert system
    print("🔧 Initializing alert system...")
    alert_system = StorageAlertSystem()
    
    # Check and generate alerts
    print("🚨 Checking and generating alerts...")
    alerts = alert_system.check_and_generate_alerts()
    
    if alerts:
        print(f"📢 Generated Alerts ({len(alerts)}):")
        for alert in alerts:
            severity_emoji = {
                'critical': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️'
            }.get(alert['severity'], '❓')
            print(f"   {severity_emoji} [{alert['type']}] {alert['message']}")
            if alert.get('details'):
                print(f"      Details: {json.dumps(alert['details'], indent=6)}")
    else:
        print("✅ No alerts generated - system is healthy!")
    
    # Demonstrate alert suppression
    print("\n🔇 Demonstrating alert suppression...")
    alert_system.suppress_alert_type('storage_limit_exceeded', duration_minutes=5)
    print("   Suppressed 'storage_limit_exceeded' alerts for 5 minutes")
    
    # Get alert statistics
    print("\n📊 Alert Statistics:")
    stats = alert_system.get_alert_statistics()
    print(f"   Suppressed Alerts: {stats['suppressed_alerts']}")
    print(f"   Alert Counts: {stats['alert_counts']}")
    print(f"   Total Alerts Sent: {stats['total_alerts_sent']}")
    if stats['suppressed_alert_types']:
        print(f"   Suppressed Types: {', '.join(stats['suppressed_alert_types'])}")
    
    return alerts, stats


def demo_performance_monitoring():
    """Demonstrate performance monitoring"""
    print("\n" + "=" * 60)
    print("DEMO: Performance Monitoring")
    print("=" * 60)
    
    # Initialize services
    config_service = StorageConfigurationService()
    monitor_service = StorageMonitorService(config_service)
    health_checker = StorageHealthChecker(config_service, monitor_service)
    
    print("⚡ Running performance tests...")
    
    # Run multiple health checks to collect performance data
    response_times = []
    for i in range(5):
        start_time = time.time()
        health_result = health_checker.check_comprehensive_health()
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        response_times.append(response_time)
        
        print(f"   Check {i+1}: {response_time:.1f}ms ({health_result.overall_status.value})")
        time.sleep(0.1)  # Brief pause between checks
    
    # Calculate performance statistics
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    min_response_time = min(response_times)
    
    print(f"\n📊 Performance Statistics:")
    print(f"   Average Response Time: {avg_response_time:.1f}ms")
    print(f"   Maximum Response Time: {max_response_time:.1f}ms")
    print(f"   Minimum Response Time: {min_response_time:.1f}ms")
    
    # Performance assessment
    if avg_response_time < 100:
        print("   ✅ Performance: Excellent")
    elif avg_response_time < 500:
        print("   ⚠️ Performance: Good")
    elif avg_response_time < 1000:
        print("   ⚠️ Performance: Acceptable")
    else:
        print("   🚨 Performance: Poor - needs attention")
    
    return {
        'avg_response_time': avg_response_time,
        'max_response_time': max_response_time,
        'min_response_time': min_response_time,
        'response_times': response_times
    }


def demo_monitoring_integration():
    """Demonstrate integration with existing monitoring"""
    print("\n" + "=" * 60)
    print("DEMO: Monitoring Integration")
    print("=" * 60)
    
    # Initialize dashboard integration
    dashboard_integration = StorageMonitoringDashboardIntegration()
    
    # Get monitoring summary
    print("📊 Getting monitoring summary...")
    summary = dashboard_integration.get_storage_monitoring_summary()
    
    print("🔍 Storage System Summary:")
    if 'storage_system' in summary:
        system = summary['storage_system']
        print(f"   Status: {system['status']}")
        print(f"   Usage: {system['usage_percentage']:.1f}%")
        print(f"   Limit Exceeded: {'Yes' if system['limit_exceeded'] else 'No'}")
        print(f"   Warning Exceeded: {'Yes' if system['warning_exceeded'] else 'No'}")
        print(f"   Currently Blocked: {'Yes' if system['currently_blocked'] else 'No'}")
        print(f"   Health: {system['health_percentage']:.1f}%")
        print(f"   Total Alerts: {system['alerts_count']}")
        print(f"   Critical Alerts: {system['critical_alerts']}")
        print(f"   Warning Alerts: {system['warning_alerts']}")
    
    return summary


def main():
    """Main demonstration function"""
    print("🚀 Storage Health Monitoring System Demonstration")
    print("=" * 60)
    print("This demo showcases the comprehensive storage health monitoring")
    print("capabilities including health checks, dashboard integration,")
    print("alert system, and performance monitoring.")
    
    try:
        # Run all demonstrations
        health_result = demo_storage_health_checker()
        metrics, alerts = demo_dashboard_integration()
        alert_results, alert_stats = demo_alert_system()
        performance_stats = demo_performance_monitoring()
        monitoring_summary = demo_monitoring_integration()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE - Summary")
        print("=" * 60)
        print("✅ Storage Health Checker: Comprehensive health monitoring")
        print("✅ Dashboard Integration: Real-time metrics and widgets")
        print("✅ Alert System: Intelligent alerting and suppression")
        print("✅ Performance Monitoring: Response time tracking")
        print("✅ Monitoring Integration: Unified monitoring dashboard")
        
        print(f"\n📊 Key Metrics:")
        print(f"   Overall Health: {health_result.overall_status.value}")
        print(f"   Components Monitored: {health_result.summary['total_components']}")
        print(f"   Health Percentage: {health_result.summary['health_percentage']:.1f}%")
        print(f"   Average Response Time: {performance_stats['avg_response_time']:.1f}ms")
        print(f"   Active Alerts: {len(health_result.alerts)}")
        
        print(f"\n🎯 System Capabilities:")
        print("• Comprehensive health monitoring for all storage components")
        print("• Real-time dashboard integration with widgets and metrics")
        print("• Intelligent alert system with suppression and rate limiting")
        print("• Performance monitoring and response time tracking")
        print("• Integration with existing monitoring infrastructure")
        print("• RESTful health check endpoints for external monitoring")
        print("• Container orchestration health probes (readiness/liveness)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)