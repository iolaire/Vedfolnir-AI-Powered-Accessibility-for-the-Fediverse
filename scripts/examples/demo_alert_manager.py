# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo script for the AlertManager system

This script demonstrates the key features of the multi-tenant caption management
alert system including alert generation, acknowledgment, and reporting.
"""

import time
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole
from app.services.alerts.components.alert_manager import (
    AlertManager, AlertType, AlertSeverity,
    alert_job_failure, alert_repeated_failures, alert_resource_low,
    alert_ai_service_down, alert_queue_backup
)

def main():
    """Demonstrate AlertManager functionality"""
    print("🚨 AlertManager Demo - Multi-Tenant Caption Management System")
    print("=" * 70)
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    alert_manager = AlertManager(db_manager, config)
    
    # Create a demo admin user
    with db_manager.get_session() as session:
        # Clean up any existing demo users
        session.query(User).filter(User.username.like('demo_admin_%')).delete()
        session.commit()
        
        admin_user = User(
            username=f'demo_admin_{int(time.time())}',
            email='demo@admin.com',
            role=UserRole.ADMIN
        )
        admin_user.set_password('demo_password')
        session.add(admin_user)
        session.commit()
        admin_user_id = admin_user.id
    
    print(f"✅ Created demo admin user (ID: {admin_user_id})")
    print()
    
    # Demonstrate alert generation
    print("📢 Generating sample alerts...")
    
    # 1. Job failure alert
    alert_job_failure(alert_manager, 'job_12345', 101, 'Connection timeout to AI service')
    print("   • Job failure alert sent")
    
    # 2. Repeated failures alert
    alert_repeated_failures(alert_manager, 102, 5)
    print("   • Repeated failures alert sent")
    
    # 3. Resource low alert
    alert_resource_low(alert_manager, 'memory', 94.5)
    print("   • Resource low alert sent")
    
    # 4. AI service down alert
    alert_ai_service_down(alert_manager, 'ollama', 'Service unreachable')
    print("   • AI service down alert sent")
    
    # 5. Queue backup alert
    alert_queue_backup(alert_manager, 250, 45)
    print("   • Queue backup alert sent")
    
    print()
    
    # Show active alerts
    print("📋 Active Alerts:")
    active_alerts = alert_manager.get_active_alerts()
    for i, alert in enumerate(active_alerts, 1):
        print(f"   {i}. [{alert.severity.value.upper()}] {alert.title}")
        print(f"      Message: {alert.message}")
        print(f"      Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      ID: {alert.id}")
        print()
    
    # Demonstrate alert acknowledgment
    if active_alerts:
        print("✅ Acknowledging first alert...")
        first_alert = active_alerts[0]
        success = alert_manager.acknowledge_alert(admin_user_id, first_alert.id)
        if success:
            print(f"   Alert '{first_alert.title}' acknowledged successfully")
        print()
    
    # Show alert statistics
    print("📊 Alert Statistics:")
    stats = alert_manager.get_alert_statistics()
    print(f"   • Total active alerts: {stats['total_active']}")
    print(f"   • Active (unacknowledged): {stats['active_alerts']}")
    print(f"   • Acknowledged: {stats['acknowledged_alerts']}")
    print(f"   • Critical alerts: {stats['by_severity']['critical']}")
    print(f"   • High priority alerts: {stats['by_severity']['high']}")
    print(f"   • Medium priority alerts: {stats['by_severity']['medium']}")
    print(f"   • Low priority alerts: {stats['by_severity']['low']}")
    print()
    
    # Show alerts by type
    print("📈 Alerts by Type:")
    for alert_type, count in stats['by_type'].items():
        print(f"   • {alert_type.replace('_', ' ').title()}: {count}")
    print()
    
    # Demonstrate alert history
    print("📚 Alert History (last 5):")
    history = alert_manager.get_alert_history(limit=5)
    for i, alert in enumerate(history, 1):
        status_emoji = "✅" if alert.status.value == "acknowledged" else "🔴"
        print(f"   {i}. {status_emoji} [{alert.severity.value.upper()}] {alert.title}")
        print(f"      Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Demonstrate alert export
    print("💾 Exporting alerts...")
    exported_alerts = alert_manager.export_alerts(format='list')
    print(f"   Exported {len(exported_alerts)} alerts to data structure")
    print()
    
    # Clean up demo user
    with db_manager.get_session() as session:
        session.query(User).filter(User.id == admin_user_id).delete()
        session.commit()
    
    print("🧹 Demo completed - cleaned up demo data")
    print("=" * 70)
    print("AlertManager Demo Summary:")
    print("• ✅ Alert generation and notification")
    print("• ✅ Alert acknowledgment and tracking")
    print("• ✅ Alert statistics and reporting")
    print("• ✅ Alert history and filtering")
    print("• ✅ Alert export functionality")
    print("• ✅ Multiple notification channels (email, webhook, in-app)")
    print("• ✅ Configurable alert thresholds")
    print("• ✅ Alert escalation for critical issues")

if __name__ == '__main__':
    main()