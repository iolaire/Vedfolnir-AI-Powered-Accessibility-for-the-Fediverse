# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Database Connection Monitoring Demo

This script demonstrates the enhanced DatabaseManager connection monitoring features
including session lifecycle tracking, connection pool monitoring, and leak detection.
"""

import sys
import os
import json
import time
from datetime import datetime

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database.core.database_manager import DatabaseManager
from config import Config


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_json(data, title=""):
    """Print JSON data in a formatted way"""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))


def demonstrate_session_lifecycle_tracking(db_manager):
    """Demonstrate session lifecycle tracking"""
    print_section("Session Lifecycle Tracking Demo")
    
    print("Initial session stats:")
    initial_stats = db_manager.get_session_lifecycle_stats()
    print_json(initial_stats)
    
    print("\nCreating 3 test sessions...")
    sessions = []
    for i in range(3):
        session = db_manager.get_session()
        sessions.append(session)
        print(f"Created session {i+1}")
    
    print("\nSession stats after creating sessions:")
    stats_after_create = db_manager.get_session_lifecycle_stats()
    print_json(stats_after_create)
    
    print("\nClosing 2 sessions...")
    for i in range(2):
        db_manager.close_session(sessions[i])
        print(f"Closed session {i+1}")
    
    print("\nFinal session stats:")
    final_stats = db_manager.get_session_lifecycle_stats()
    print_json(final_stats)
    
    # Clean up remaining session
    db_manager.close_session(sessions[2])


def demonstrate_performance_monitoring(db_manager):
    """Demonstrate enhanced performance monitoring"""
    print_section("Enhanced Performance Monitoring Demo")
    
    try:
        print("Getting MySQL performance stats with responsiveness metrics...")
        perf_stats = db_manager.get_mysql_performance_stats()
        print_json(perf_stats, "Performance Statistics")
        
        # Highlight key responsiveness metrics
        if 'connection_pool' in perf_stats:
            pool_info = perf_stats['connection_pool']
            print(f"\n🔍 Key Responsiveness Metrics:")
            print(f"   Pool Utilization: {pool_info.get('utilization_percent', 'N/A')}%")
            print(f"   Total Utilization: {pool_info.get('total_utilization_percent', 'N/A')}%")
            print(f"   Alert Level: {pool_info.get('alert', 'N/A')}")
            
            if 'alert_message' in pool_info:
                print(f"   Alert Message: {pool_info['alert_message']}")
        
        if 'connection_health' in perf_stats:
            print(f"   Connection Health: {perf_stats['connection_health']}")
        
        if 'connection_abort_rate' in perf_stats:
            print(f"   Connection Abort Rate: {perf_stats['connection_abort_rate']}%")
            
    except Exception as e:
        print(f"⚠️  Performance monitoring not available (likely no MySQL connection): {e}")


def demonstrate_connection_health_monitoring(db_manager):
    """Demonstrate comprehensive connection health monitoring"""
    print_section("Connection Health Monitoring Demo")
    
    try:
        print("Running comprehensive connection health check...")
        health_report = db_manager.monitor_connection_health()
        print_json(health_report, "Health Report")
        
        # Highlight key health indicators
        print(f"\n🏥 Health Summary:")
        print(f"   Overall Health: {health_report.get('overall_health', 'UNKNOWN')}")
        
        if health_report.get('issues'):
            print(f"   Issues Found: {len(health_report['issues'])}")
            for issue in health_report['issues']:
                print(f"     - {issue}")
        else:
            print(f"   Issues Found: None")
        
        if health_report.get('recommendations'):
            print(f"   Recommendations: {len(health_report['recommendations'])}")
            for rec in health_report['recommendations']:
                print(f"     - {rec}")
        else:
            print(f"   Recommendations: None")
            
    except Exception as e:
        print(f"⚠️  Health monitoring not available (likely no MySQL connection): {e}")


def demonstrate_connection_testing(db_manager):
    """Demonstrate enhanced connection testing"""
    print_section("Enhanced Connection Testing Demo")
    
    try:
        print("Testing MySQL connection with health monitoring...")
        success, message = db_manager.test_mysql_connection()
        
        print(f"Connection Test Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Details: {message}")
        
    except Exception as e:
        print(f"⚠️  Connection testing not available (likely no MySQL connection): {e}")


def demonstrate_leak_detection_and_cleanup(db_manager):
    """Demonstrate connection leak detection and cleanup"""
    print_section("Connection Leak Detection & Cleanup Demo")
    
    print("Running connection leak detection...")
    cleanup_result = db_manager.detect_and_cleanup_connection_leaks()
    print_json(cleanup_result, "Cleanup Results")
    
    print(f"\n🔧 Cleanup Summary:")
    print(f"   Long-lived sessions found: {cleanup_result.get('long_lived_sessions_found', 0)}")
    print(f"   Sessions cleaned: {cleanup_result.get('cleaned_sessions', 0)}")
    print(f"   Cleanup actions: {len(cleanup_result.get('cleanup_actions', []))}")
    
    if cleanup_result.get('cleanup_actions'):
        print("   Actions taken:")
        for action in cleanup_result['cleanup_actions']:
            print(f"     - {action}")


def main():
    """Main demonstration function"""
    print("🚀 Database Connection Monitoring Demo")
    print("=" * 60)
    print("This demo showcases the enhanced DatabaseManager features:")
    print("- Session lifecycle tracking")
    print("- Connection pool monitoring")
    print("- Performance metrics with responsiveness alerts")
    print("- Connection health monitoring")
    print("- Leak detection and cleanup")
    
    try:
        # Initialize configuration
        print("\n📋 Initializing configuration...")
        config = Config()
        
        # Create DatabaseManager
        print("🔧 Creating DatabaseManager with monitoring features...")
        db_manager = DatabaseManager(config)
        print("✅ DatabaseManager initialized successfully")
        
        # Run demonstrations
        demonstrate_session_lifecycle_tracking(db_manager)
        demonstrate_performance_monitoring(db_manager)
        demonstrate_connection_health_monitoring(db_manager)
        demonstrate_connection_testing(db_manager)
        demonstrate_leak_detection_and_cleanup(db_manager)
        
        print_section("Demo Complete")
        print("✅ All database connection monitoring features demonstrated successfully!")
        print("\n📊 Summary of Enhanced Features:")
        print("   ✓ Session lifecycle tracking with leak detection")
        print("   ✓ Connection pool utilization monitoring")
        print("   ✓ Responsiveness metrics and alerts")
        print("   ✓ Comprehensive health monitoring")
        print("   ✓ Automatic connection leak cleanup")
        print("   ✓ Enhanced error handling with diagnostic information")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)