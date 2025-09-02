# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification System Emergency CLI Tool

This command-line tool provides emergency management capabilities for the notification system,
including status monitoring, emergency activation/deactivation, recovery operations, and
rollback procedures.
"""

import sys
import os
import argparse
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from notification_emergency_recovery import (
    NotificationEmergencyRecovery, EmergencyLevel, RecoveryAction, FailureType
)
from unified_notification_manager import UnifiedNotificationManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NotificationEmergencyCLI:
    """Command-line interface for notification system emergency management"""
    
    def __init__(self):
        """Initialize the emergency CLI"""
        load_dotenv()
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Initialize emergency recovery system
        try:
            self.websocket_factory = WebSocketFactory(self.config)
            self.auth_handler = WebSocketAuthHandler(self.config)
            self.namespace_manager = WebSocketNamespaceManager()
            self.notification_manager = UnifiedNotificationManager(
                self.websocket_factory, self.auth_handler
            )
            
            self.emergency_recovery = NotificationEmergencyRecovery(
                self.notification_manager,
                self.websocket_factory,
                self.auth_handler,
                self.namespace_manager,
                self.db_manager
            )
            
            logger.info("Emergency CLI initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize emergency CLI: {e}")
            self.emergency_recovery = None
    
    def status(self) -> Dict[str, Any]:
        """Get notification system status"""
        try:
            if not self.emergency_recovery:
                return {"error": "Emergency recovery system not available"}
            
            status = self.emergency_recovery.get_emergency_status()
            
            print("=== Notification System Status ===")
            print(f"Emergency Active: {status.get('emergency_active', 'Unknown')}")
            print(f"Health Status: {status.get('health_status', 'Unknown')}")
            print(f"Last Health Check: {status.get('last_health_check', 'Unknown')}")
            
            fallback_systems = status.get('fallback_systems', {})
            print("\n=== Fallback Systems ===")
            print(f"Fallback Enabled: {fallback_systems.get('fallback_enabled', 'Unknown')}")
            print(f"Flash Fallback: {fallback_systems.get('flash_fallback_enabled', 'Unknown')}")
            print(f"Emergency Broadcast: {fallback_systems.get('emergency_broadcast_enabled', 'Unknown')}")
            
            stats = status.get('statistics', {})
            print("\n=== Statistics ===")
            print(f"Emergency Events: {stats.get('emergency_events', 0)}")
            print(f"Automatic Recoveries: {stats.get('automatic_recoveries', 0)}")
            print(f"Manual Interventions: {stats.get('manual_interventions', 0)}")
            print(f"Recovery Success Rate: {stats.get('recovery_success_rate', 0):.2%}")
            
            recent_events = status.get('recent_events', [])
            if recent_events:
                print("\n=== Recent Events ===")
                for event in recent_events[-5:]:  # Show last 5 events
                    print(f"- {event['timestamp']}: {event['failure_type']} "
                          f"(Level: {event['emergency_level']}, "
                          f"Success: {event['recovery_success']})")
            
            return status
            
        except Exception as e:
            error_msg = f"Failed to get status: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}
    
    def health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        try:
            if not self.emergency_recovery:
                return {"error": "Emergency recovery system not available"}
            
            print("=== Running Health Check ===")
            health_results = self.emergency_recovery.run_health_check()
            
            print(f"Overall Status: {health_results.get('overall_status', 'Unknown')}")
            print(f"Timestamp: {health_results.get('timestamp', 'Unknown')}")
            
            components = health_results.get('components', {})
            print("\n=== Component Status ===")
            for component, status in components.items():
                component_status = status.get('status', 'Unknown')
                print(f"{component}: {component_status}")
                if 'error' in status:
                    print(f"  Error: {status['error']}")
            
            issues = health_results.get('issues', [])
            if issues:
                print("\n=== Issues Detected ===")
                for issue in issues:
                    print(f"- {issue}")
            
            recommendations = health_results.get('recommendations', [])
            if recommendations:
                print("\n=== Recommendations ===")
                for rec in recommendations:
                    print(f"- {rec}")
            
            return health_results
            
        except Exception as e:
            error_msg = f"Health check failed: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}
    
    def activate_emergency(self, reason: str, triggered_by: str) -> bool:
        """Activate emergency mode"""
        try:
            if not self.emergency_recovery:
                print("ERROR: Emergency recovery system not available")
                return False
            
            print(f"=== Activating Emergency Mode ===")
            print(f"Reason: {reason}")
            print(f"Triggered by: {triggered_by}")
            
            success = self.emergency_recovery.activate_emergency_mode(reason, triggered_by)
            
            if success:
                print("✅ Emergency mode activated successfully")
                print("- Fallback systems enabled")
                print("- Emergency notifications sent to administrators")
                print("- System monitoring enhanced")
            else:
                print("❌ Failed to activate emergency mode")
            
            return success
            
        except Exception as e:
            error_msg = f"Failed to activate emergency mode: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False
    
    def deactivate_emergency(self, resolved_by: str) -> bool:
        """Deactivate emergency mode"""
        try:
            if not self.emergency_recovery:
                print("ERROR: Emergency recovery system not available")
                return False
            
            print(f"=== Deactivating Emergency Mode ===")
            print(f"Resolved by: {resolved_by}")
            
            success = self.emergency_recovery.deactivate_emergency_mode(resolved_by)
            
            if success:
                print("✅ Emergency mode deactivated successfully")
                print("- Normal operations restored")
                print("- Fallback systems disabled")
                print("- Recovery notification sent")
            else:
                print("❌ Failed to deactivate emergency mode")
                print("- System may not be healthy enough for normal operations")
                print("- Check health status and resolve issues first")
            
            return success
            
        except Exception as e:
            error_msg = f"Failed to deactivate emergency mode: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False
    
    def send_notification(self, title: str, message: str, priority: str = "high", 
                         target: str = "admins") -> bool:
        """Send emergency notification"""
        try:
            if not self.emergency_recovery:
                print("ERROR: Emergency recovery system not available")
                return False
            
            print(f"=== Sending Emergency Notification ===")
            print(f"Title: {title}")
            print(f"Message: {message}")
            print(f"Priority: {priority}")
            print(f"Target: {target}")
            
            # Determine target users
            target_users = None
            if target != "admins":
                # Parse specific user IDs if provided
                try:
                    target_users = [int(uid) for uid in target.split(',')]
                except ValueError:
                    print(f"WARNING: Invalid target format '{target}', sending to all admins")
            
            success = self.emergency_recovery.send_emergency_notification(
                title, message, target_users
            )
            
            if success:
                print("✅ Emergency notification sent successfully")
            else:
                print("❌ Failed to send emergency notification")
            
            return success
            
        except Exception as e:
            error_msg = f"Failed to send notification: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False
    
    def auto_recover(self) -> bool:
        """Attempt automatic recovery"""
        try:
            if not self.emergency_recovery:
                print("ERROR: Emergency recovery system not available")
                return False
            
            print("=== Attempting Automatic Recovery ===")
            
            # Simulate a recovery scenario by creating a test error
            test_error = Exception("Manual recovery test")
            context = {
                'affected_users': [],
                'component': 'manual_test',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            success = self.emergency_recovery.detect_and_recover(test_error, context)
            
            if success:
                print("✅ Automatic recovery completed successfully")
            else:
                print("❌ Automatic recovery failed")
                print("- Manual intervention may be required")
                print("- Check system health and logs for details")
            
            return success
            
        except Exception as e:
            error_msg = f"Auto recovery failed: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False
    
    def test_recovery(self) -> bool:
        """Test recovery mechanisms without affecting production"""
        try:
            print("=== Testing Recovery Mechanisms ===")
            
            # Test 1: Health check
            print("1. Testing health check...")
            health_results = self.health_check()
            health_ok = health_results.get('overall_status') != 'error'
            print(f"   Health check: {'✅ PASS' if health_ok else '❌ FAIL'}")
            
            # Test 2: Emergency notification
            print("2. Testing emergency notification...")
            notif_ok = self.send_notification(
                "Test Emergency Notification",
                "This is a test of the emergency notification system.",
                "low",
                "admins"
            )
            print(f"   Emergency notification: {'✅ PASS' if notif_ok else '❌ FAIL'}")
            
            # Test 3: Status reporting
            print("3. Testing status reporting...")
            status_results = self.status()
            status_ok = 'error' not in status_results
            print(f"   Status reporting: {'✅ PASS' if status_ok else '❌ FAIL'}")
            
            overall_success = health_ok and notif_ok and status_ok
            
            print(f"\n=== Recovery Test Results ===")
            print(f"Overall: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
            
            return overall_success
            
        except Exception as e:
            error_msg = f"Recovery test failed: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False
    
    def generate_report(self, output_file: Optional[str] = None) -> bool:
        """Generate emergency system report"""
        try:
            print("=== Generating Emergency System Report ===")
            
            # Collect system information
            status = self.status() if self.emergency_recovery else {"error": "System unavailable"}
            health = self.health_check() if self.emergency_recovery else {"error": "System unavailable"}
            
            report = {
                "report_timestamp": datetime.now(timezone.utc).isoformat(),
                "report_type": "emergency_system_status",
                "system_status": status,
                "health_check": health,
                "cli_version": "1.0.0",
                "generated_by": os.getenv('USER', 'unknown')
            }
            
            # Determine output file
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"emergency_report_{timestamp}.json"
            
            # Write report
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"✅ Report generated: {output_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to generate report: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Notification System Emergency CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                                    # Check system status
  %(prog)s health-check                              # Run health check
  %(prog)s activate-emergency --reason "System failure" --triggered-by "admin"
  %(prog)s deactivate-emergency --resolved-by "admin"
  %(prog)s send-notification --title "Alert" --message "Test message"
  %(prog)s auto-recover                              # Attempt automatic recovery
  %(prog)s test-recovery                             # Test recovery mechanisms
  %(prog)s generate-report --output emergency_report.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Get notification system status')
    
    # Health check command
    subparsers.add_parser('health-check', help='Run comprehensive health check')
    
    # Activate emergency command
    activate_parser = subparsers.add_parser('activate-emergency', help='Activate emergency mode')
    activate_parser.add_argument('--reason', required=True, help='Reason for emergency activation')
    activate_parser.add_argument('--triggered-by', required=True, help='Who triggered the emergency')
    
    # Deactivate emergency command
    deactivate_parser = subparsers.add_parser('deactivate-emergency', help='Deactivate emergency mode')
    deactivate_parser.add_argument('--resolved-by', required=True, help='Who resolved the emergency')
    
    # Send notification command
    notification_parser = subparsers.add_parser('send-notification', help='Send emergency notification')
    notification_parser.add_argument('--title', required=True, help='Notification title')
    notification_parser.add_argument('--message', required=True, help='Notification message')
    notification_parser.add_argument('--priority', default='high', choices=['low', 'medium', 'high', 'critical'], help='Notification priority')
    notification_parser.add_argument('--target', default='admins', help='Target users (admins or comma-separated user IDs)')
    
    # Auto recover command
    subparsers.add_parser('auto-recover', help='Attempt automatic recovery')
    
    # Test recovery command
    subparsers.add_parser('test-recovery', help='Test recovery mechanisms')
    
    # Generate report command
    report_parser = subparsers.add_parser('generate-report', help='Generate emergency system report')
    report_parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize CLI
    try:
        cli = NotificationEmergencyCLI()
    except Exception as e:
        print(f"ERROR: Failed to initialize emergency CLI: {e}")
        return 1
    
    # Execute command
    success = False
    
    try:
        if args.command == 'status':
            result = cli.status()
            success = 'error' not in result
            
        elif args.command == 'health-check':
            result = cli.health_check()
            success = result.get('overall_status') != 'error'
            
        elif args.command == 'activate-emergency':
            success = cli.activate_emergency(args.reason, args.triggered_by)
            
        elif args.command == 'deactivate-emergency':
            success = cli.deactivate_emergency(args.resolved_by)
            
        elif args.command == 'send-notification':
            success = cli.send_notification(args.title, args.message, args.priority, args.target)
            
        elif args.command == 'auto-recover':
            success = cli.auto_recover()
            
        elif args.command == 'test-recovery':
            success = cli.test_recovery()
            
        elif args.command == 'generate-report':
            success = cli.generate_report(args.output)
            
        else:
            print(f"ERROR: Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"ERROR: Command execution failed: {e}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())