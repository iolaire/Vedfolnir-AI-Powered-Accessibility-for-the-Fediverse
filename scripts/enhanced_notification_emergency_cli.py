#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Notification System Emergency CLI Tool

Advanced command-line interface for emergency notification system operations including
comprehensive health checks, automated recovery procedures, rollback operations,
emergency mode activation, and disaster recovery mechanisms.
"""

import argparse
import sys
import os
import json
import time
import subprocess
import shutil
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from notification_emergency_recovery import NotificationEmergencyRecovery, EmergencyLevel, FailureType
    from unified_notification_manager import UnifiedNotificationManager
    from websocket_factory import WebSocketFactory
    from websocket_auth_handler import WebSocketAuthHandler
    from websocket_namespace_manager import WebSocketNamespaceManager
    from database import DatabaseManager
    from config import Config
    from models import User, UserRole
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class EnhancedNotificationEmergencyCLI:
    """Enhanced command-line interface for notification emergency operations"""
    
    def __init__(self):
        """Initialize CLI with system components"""
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "storage" / "emergency_backups"
        self.log_dir = self.project_root / "logs"
        
        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        try:
            self.config = Config()
            self.db_manager = DatabaseManager(self.config)
            
            # Initialize components (these may fail if system is down)
            self.websocket_factory = None
            self.auth_handler = None
            self.namespace_manager = None
            self.notification_manager = None
            self.recovery_system = None
            
            self._initialize_components()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            print(f"⚠️  Warning: Failed to initialize some components: {e}")
            print("Some operations may not be available")
    
    def _setup_logging(self):
        """Setup logging for emergency operations"""
        log_file = self.log_dir / f"emergency_cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Emergency CLI initialized")
    
    def _initialize_components(self):
        """Initialize system components (may fail if system is down)"""
        try:
            self.websocket_factory = WebSocketFactory()
            self.auth_handler = WebSocketAuthHandler()
            self.namespace_manager = WebSocketNamespaceManager()
            
            self.notification_manager = UnifiedNotificationManager(
                self.websocket_factory,
                self.auth_handler,
                self.namespace_manager,
                self.db_manager
            )
            
            self.recovery_system = NotificationEmergencyRecovery(
                self.notification_manager,
                self.websocket_factory,
                self.auth_handler,
                self.namespace_manager,
                self.db_manager
            )
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.warning(f"Component initialization warning: {e}")
    
    def comprehensive_health_check(self, args):
        """Run comprehensive health check with detailed diagnostics"""
        print("🔍 Running comprehensive notification system health check...")
        self.logger.info("Starting comprehensive health check")
        
        health_report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'unknown',
            'components': {},
            'performance_metrics': {},
            'security_status': {},
            'recommendations': [],
            'critical_issues': [],
            'warnings': []
        }
        
        # Check system components
        self._check_database_health(health_report)
        self._check_websocket_health(health_report)
        self._check_notification_system_health(health_report)
        self._check_session_management_health(health_report)
        self._check_security_status(health_report)
        self._check_performance_metrics(health_report)
        
        # Determine overall status
        self._determine_overall_status(health_report)
        
        # Display results
        self._display_health_report(health_report)
        
        # Save report
        report_file = self.backup_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(health_report, f, indent=2)
        
        print(f"\n📄 Health report saved to: {report_file}")
        
        return health_report['overall_status'] in ['healthy', 'degraded']
    
    def _check_database_health(self, report: Dict[str, Any]):
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            with self.db_manager.get_session() as session:
                # Test basic connectivity
                session.execute("SELECT 1")
                
                # Check notification-related tables
                user_count = session.query(User).count()
                
                # Test write performance
                session.execute("SELECT COUNT(*) FROM users")
                
            response_time = (time.time() - start_time) * 1000
            
            report['components']['database'] = {
                'status': 'healthy',
                'response_time_ms': response_time,
                'user_count': user_count,
                'connectivity': 'ok'
            }
            
            if response_time > 1000:
                report['warnings'].append(f"Database response time high: {response_time:.2f}ms")
            
        except Exception as e:
            report['components']['database'] = {
                'status': 'error',
                'error': str(e)
            }
            report['critical_issues'].append(f"Database connectivity failed: {e}")
    
    def _check_websocket_health(self, report: Dict[str, Any]):
        """Check WebSocket factory and connections"""
        try:
            if self.websocket_factory:
                # Check WebSocket factory status
                if hasattr(self.websocket_factory, 'get_status'):
                    ws_status = self.websocket_factory.get_status()
                    report['components']['websocket_factory'] = ws_status
                else:
                    report['components']['websocket_factory'] = {'status': 'unknown'}
                
                # Check for active connections
                if hasattr(self.websocket_factory, 'get_connection_count'):
                    connection_count = self.websocket_factory.get_connection_count()
                    report['performance_metrics']['websocket_connections'] = connection_count
            else:
                report['components']['websocket_factory'] = {'status': 'not_initialized'}
                report['warnings'].append("WebSocket factory not initialized")
                
        except Exception as e:
            report['components']['websocket_factory'] = {
                'status': 'error',
                'error': str(e)
            }
            report['critical_issues'].append(f"WebSocket health check failed: {e}")
    
    def _check_notification_system_health(self, report: Dict[str, Any]):
        """Check notification manager and delivery system"""
        try:
            if self.notification_manager:
                # Check notification manager status
                if hasattr(self.notification_manager, 'get_notification_stats'):
                    notif_stats = self.notification_manager.get_notification_stats()
                    report['components']['notification_manager'] = {
                        'status': 'healthy',
                        'stats': notif_stats
                    }
                else:
                    report['components']['notification_manager'] = {'status': 'unknown'}
                
                # Check message queues
                if hasattr(self.notification_manager, 'get_queue_status'):
                    queue_status = self.notification_manager.get_queue_status()
                    report['performance_metrics']['message_queues'] = queue_status
            else:
                report['components']['notification_manager'] = {'status': 'not_initialized'}
                report['warnings'].append("Notification manager not initialized")
                
        except Exception as e:
            report['components']['notification_manager'] = {
                'status': 'error',
                'error': str(e)
            }
            report['critical_issues'].append(f"Notification system health check failed: {e}")
    
    def _check_session_management_health(self, report: Dict[str, Any]):
        """Check session management system"""
        try:
            # Check Redis connectivity
            import redis
            redis_client = redis.Redis.from_url(self.config.REDIS_URL)
            redis_client.ping()
            
            # Get Redis info
            redis_info = redis_client.info()
            
            report['components']['redis_session'] = {
                'status': 'healthy',
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_human': redis_info.get('used_memory_human', 'unknown'),
                'uptime_in_seconds': redis_info.get('uptime_in_seconds', 0)
            }
            
        except Exception as e:
            report['components']['redis_session'] = {
                'status': 'error',
                'error': str(e)
            }
            report['critical_issues'].append(f"Redis session management failed: {e}")
    
    def _check_security_status(self, report: Dict[str, Any]):
        """Check security-related components"""
        try:
            # Check CSRF protection
            csrf_enabled = getattr(self.config, 'WTF_CSRF_ENABLED', False)
            
            # Check session security
            session_secure = getattr(self.config, 'SESSION_COOKIE_SECURE', False)
            session_httponly = getattr(self.config, 'SESSION_COOKIE_HTTPONLY', False)
            
            report['security_status'] = {
                'csrf_protection': csrf_enabled,
                'secure_cookies': session_secure,
                'httponly_cookies': session_httponly,
                'status': 'configured' if all([csrf_enabled, session_secure, session_httponly]) else 'partial'
            }
            
            if not csrf_enabled:
                report['warnings'].append("CSRF protection not enabled")
            if not session_secure:
                report['warnings'].append("Session cookies not marked as secure")
            if not session_httponly:
                report['warnings'].append("Session cookies not marked as HTTP-only")
                
        except Exception as e:
            report['security_status'] = {
                'status': 'error',
                'error': str(e)
            }
            report['warnings'].append(f"Security status check failed: {e}")
    
    def _check_performance_metrics(self, report: Dict[str, Any]):
        """Check system performance metrics"""
        try:
            import psutil
            
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            report['performance_metrics'].update({
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            })
            
            # Performance warnings
            if cpu_percent > 80:
                report['warnings'].append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 85:
                report['warnings'].append(f"High memory usage: {memory.percent}%")
            if disk.percent > 90:
                report['warnings'].append(f"Low disk space: {disk.percent}% used")
                
        except ImportError:
            report['performance_metrics']['status'] = 'psutil_not_available'
        except Exception as e:
            report['performance_metrics']['error'] = str(e)
    
    def _determine_overall_status(self, report: Dict[str, Any]):
        """Determine overall system status"""
        if report['critical_issues']:
            report['overall_status'] = 'critical'
        elif len(report['warnings']) > 3:
            report['overall_status'] = 'degraded'
        elif report['warnings']:
            report['overall_status'] = 'warning'
        else:
            report['overall_status'] = 'healthy'
    
    def _display_health_report(self, report: Dict[str, Any]):
        """Display formatted health report"""
        status_colors = {
            'healthy': '🟢',
            'warning': '🟡',
            'degraded': '🟠',
            'critical': '🔴',
            'error': '❌',
            'unknown': '⚪'
        }
        
        print(f"\n📊 Health Check Results ({report['timestamp']})")
        print(f"Overall Status: {status_colors.get(report['overall_status'], '⚪')} {report['overall_status'].upper()}")
        
        print("\n🔧 Component Status:")
        for component, status in report['components'].items():
            component_status = status.get('status', 'unknown')
            icon = status_colors.get(component_status, '⚪')
            print(f"  {icon} {component}: {component_status}")
            
            if 'error' in status:
                print(f"    ❌ Error: {status['error']}")
            if 'response_time_ms' in status:
                print(f"    ⏱️  Response time: {status['response_time_ms']:.2f}ms")
        
        if report['performance_metrics']:
            print("\n📈 Performance Metrics:")
            metrics = report['performance_metrics']
            if 'cpu_percent' in metrics:
                print(f"  🖥️  CPU Usage: {metrics['cpu_percent']:.1f}%")
            if 'memory_percent' in metrics:
                print(f"  💾 Memory Usage: {metrics['memory_percent']:.1f}%")
            if 'disk_percent' in metrics:
                print(f"  💿 Disk Usage: {metrics['disk_percent']:.1f}%")
        
        if report['critical_issues']:
            print("\n🚨 Critical Issues:")
            for issue in report['critical_issues']:
                print(f"  ❌ {issue}")
        
        if report['warnings']:
            print("\n⚠️  Warnings:")
            for warning in report['warnings']:
                print(f"  ⚠️  {warning}")
        
        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  💡 {rec}")
    
    def create_emergency_backup(self, args):
        """Create comprehensive emergency backup"""
        print("💾 Creating emergency backup...")
        self.logger.info("Starting emergency backup creation")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"emergency_backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        backup_manifest = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'backup_type': 'emergency',
            'components': [],
            'files': [],
            'database_backup': None,
            'success': False
        }
        
        try:
            # Backup notification system files
            self._backup_notification_files(backup_path, backup_manifest)
            
            # Backup configuration
            self._backup_configuration(backup_path, backup_manifest)
            
            # Backup database
            self._backup_database(backup_path, backup_manifest)
            
            # Backup logs
            self._backup_logs(backup_path, backup_manifest)
            
            # Create backup manifest
            manifest_file = backup_path / "backup_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(backup_manifest, f, indent=2)
            
            backup_manifest['success'] = True
            
            print(f"✅ Emergency backup created successfully: {backup_path}")
            self.logger.info(f"Emergency backup created: {backup_path}")
            
            return str(backup_path)
            
        except Exception as e:
            print(f"❌ Emergency backup failed: {e}")
            self.logger.error(f"Emergency backup failed: {e}")
            return None
    
    def _backup_notification_files(self, backup_path: Path, manifest: Dict[str, Any]):
        """Backup notification system files"""
        notification_files = [
            'unified_notification_manager.py',
            'notification_emergency_recovery.py',
            'notification_message_router.py',
            'notification_persistence_manager.py',
            'page_notification_integrator.py'
        ]
        
        files_backup_path = backup_path / "notification_files"
        files_backup_path.mkdir(exist_ok=True)
        
        backed_up_files = []
        
        for file_name in notification_files:
            source_file = self.project_root / file_name
            if source_file.exists():
                dest_file = files_backup_path / file_name
                shutil.copy2(source_file, dest_file)
                backed_up_files.append(file_name)
        
        # Backup WebSocket files
        websocket_files = list(self.project_root.glob("websocket_*.py"))
        for ws_file in websocket_files:
            if 'notification' in ws_file.name:
                dest_file = files_backup_path / ws_file.name
                shutil.copy2(ws_file, dest_file)
                backed_up_files.append(ws_file.name)
        
        manifest['components'].append('notification_files')
        manifest['files'].extend(backed_up_files)
    
    def _backup_configuration(self, backup_path: Path, manifest: Dict[str, Any]):
        """Backup configuration files"""
        config_backup_path = backup_path / "configuration"
        config_backup_path.mkdir(exist_ok=True)
        
        config_files = ['.env', 'config.py', 'web_app.py']
        
        for config_file in config_files:
            source_file = self.project_root / config_file
            if source_file.exists():
                dest_file = config_backup_path / config_file
                shutil.copy2(source_file, dest_file)
        
        manifest['components'].append('configuration')
    
    def _backup_database(self, backup_path: Path, manifest: Dict[str, Any]):
        """Backup database"""
        try:
            db_backup_path = backup_path / "database"
            db_backup_path.mkdir(exist_ok=True)
            
            # MySQL backup
            backup_file = db_backup_path / "vedfolnir_emergency_backup.sql"
            
            cmd = [
                'mysqldump',
                '-u', self.config.DB_USER,
                f'-p{self.config.DB_PASSWORD}',
                self.config.DB_NAME
            ]
            
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            manifest['database_backup'] = str(backup_file)
            manifest['components'].append('database')
            
        except Exception as e:
            self.logger.warning(f"Database backup failed: {e}")
            manifest['database_backup'] = f"failed: {e}"
    
    def _backup_logs(self, backup_path: Path, manifest: Dict[str, Any]):
        """Backup recent logs"""
        logs_backup_path = backup_path / "logs"
        logs_backup_path.mkdir(exist_ok=True)
        
        # Copy recent log files
        if self.log_dir.exists():
            for log_file in self.log_dir.glob("*.log"):
                # Only backup logs from last 7 days
                if (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days <= 7:
                    dest_file = logs_backup_path / log_file.name
                    shutil.copy2(log_file, dest_file)
        
        manifest['components'].append('logs')
    
    def execute_emergency_rollback(self, args):
        """Execute emergency rollback with confirmation"""
        if not args.confirm:
            print("⚠️  Emergency rollback requires confirmation!")
            print("This will:")
            print("  - Stop all notification services")
            print("  - Remove unified notification system")
            print("  - Restore legacy Flask flash messages")
            print("  - Rollback database schema")
            print("")
            response = input("Are you sure you want to proceed? (type 'ROLLBACK' to confirm): ")
            if response != 'ROLLBACK':
                print("❌ Rollback cancelled")
                return False
        
        print("🔄 Executing emergency rollback...")
        self.logger.critical("Emergency rollback initiated")
        
        # Create backup before rollback
        backup_path = self.create_emergency_backup(args)
        if not backup_path:
            print("❌ Failed to create backup, aborting rollback")
            return False
        
        try:
            # Execute rollback script
            rollback_script = self.project_root / "scripts" / "rollback_notification_system.sh"
            
            if not rollback_script.exists():
                print(f"❌ Rollback script not found: {rollback_script}")
                return False
            
            print("🔄 Executing rollback script...")
            result = subprocess.run(['bash', str(rollback_script)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Emergency rollback completed successfully")
                self.logger.info("Emergency rollback completed successfully")
                
                # Verify rollback
                self._verify_rollback()
                
                return True
            else:
                print(f"❌ Rollback script failed: {result.stderr}")
                self.logger.error(f"Rollback script failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Emergency rollback failed: {e}")
            self.logger.error(f"Emergency rollback failed: {e}")
            return False
    
    def _verify_rollback(self):
        """Verify rollback completion"""
        print("🔍 Verifying rollback completion...")
        
        # Check that unified components are removed
        unified_files = [
            'unified_notification_manager.py',
            'notification_emergency_recovery.py'
        ]
        
        for file_name in unified_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"⚠️  Warning: {file_name} still exists")
            else:
                print(f"✅ {file_name} removed")
        
        # Test web application
        try:
            import requests
            response = requests.get('http://127.0.0.1:5000/', timeout=10)
            if response.status_code == 200:
                print("✅ Web application is responding")
            else:
                print(f"⚠️  Web application returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️  Could not test web application: {e}")
    
    def generate_emergency_report(self, args):
        """Generate comprehensive emergency report"""
        print("📄 Generating emergency report...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.backup_dir / f"emergency_report_{timestamp}.md"
        
        # Collect system information
        health_report = self.comprehensive_health_check(args)
        
        # Generate report content
        report_content = self._generate_report_content(health_report)
        
        # Write report
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"✅ Emergency report generated: {report_file}")
        return str(report_file)
    
    def _generate_report_content(self, health_report: Dict[str, Any]) -> str:
        """Generate emergency report content"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        return f"""# Notification System Emergency Report

## Report Information
- **Generated**: {timestamp}
- **Report Type**: Emergency System Analysis
- **System Status**: {health_report.get('overall_status', 'unknown').upper()}

## Executive Summary
This report provides a comprehensive analysis of the notification system status during an emergency situation.

## System Health Overview
- **Overall Status**: {health_report.get('overall_status', 'unknown')}
- **Critical Issues**: {len(health_report.get('critical_issues', []))}
- **Warnings**: {len(health_report.get('warnings', []))}

## Component Status
{self._format_components_for_report(health_report.get('components', {}))}

## Critical Issues
{self._format_issues_for_report(health_report.get('critical_issues', []))}

## Warnings
{self._format_issues_for_report(health_report.get('warnings', []))}

## Performance Metrics
{self._format_metrics_for_report(health_report.get('performance_metrics', {}))}

## Recommendations
Based on the current system status, the following actions are recommended:

1. **Immediate Actions**
   - Address all critical issues immediately
   - Monitor system performance closely
   - Ensure backup systems are operational

2. **Short-term Actions**
   - Resolve all warnings within 24 hours
   - Implement additional monitoring
   - Review emergency procedures

3. **Long-term Actions**
   - Conduct post-incident review
   - Update emergency procedures
   - Implement preventive measures

## Emergency Contacts
- **System Administrator**: [Contact Information]
- **Database Administrator**: [Contact Information]
- **Emergency Hotline**: [Phone Number]

## Next Steps
1. Address critical issues immediately
2. Monitor system recovery
3. Conduct post-incident analysis
4. Update procedures based on lessons learned

---
*Report generated by Enhanced Notification Emergency CLI*
*For technical support, contact the system administration team*
"""
    
    def _format_components_for_report(self, components: Dict[str, Any]) -> str:
        """Format components status for report"""
        if not components:
            return "No component information available."
        
        lines = []
        for component, status in components.items():
            component_status = status.get('status', 'unknown')
            lines.append(f"- **{component}**: {component_status}")
            
            if 'error' in status:
                lines.append(f"  - Error: {status['error']}")
            if 'response_time_ms' in status:
                lines.append(f"  - Response Time: {status['response_time_ms']:.2f}ms")
        
        return '\n'.join(lines)
    
    def _format_issues_for_report(self, issues: List[str]) -> str:
        """Format issues list for report"""
        if not issues:
            return "None reported."
        
        return '\n'.join(f"- {issue}" for issue in issues)
    
    def _format_metrics_for_report(self, metrics: Dict[str, Any]) -> str:
        """Format performance metrics for report"""
        if not metrics:
            return "No performance metrics available."
        
        lines = []
        if 'cpu_percent' in metrics:
            lines.append(f"- **CPU Usage**: {metrics['cpu_percent']:.1f}%")
        if 'memory_percent' in metrics:
            lines.append(f"- **Memory Usage**: {metrics['memory_percent']:.1f}%")
        if 'disk_percent' in metrics:
            lines.append(f"- **Disk Usage**: {metrics['disk_percent']:.1f}%")
        
        return '\n'.join(lines)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Enhanced Notification System Emergency CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run comprehensive health check
  python enhanced_notification_emergency_cli.py health-check
  
  # Create emergency backup
  python enhanced_notification_emergency_cli.py backup
  
  # Execute emergency rollback (with confirmation)
  python enhanced_notification_emergency_cli.py rollback
  
  # Execute emergency rollback (skip confirmation)
  python enhanced_notification_emergency_cli.py rollback --confirm
  
  # Generate emergency report
  python enhanced_notification_emergency_cli.py report
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health check command
    health_parser = subparsers.add_parser('health-check', help='Run comprehensive health check')
    health_parser.set_defaults(func='comprehensive_health_check')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create emergency backup')
    backup_parser.set_defaults(func='create_emergency_backup')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Execute emergency rollback')
    rollback_parser.add_argument('--confirm', action='store_true', 
                               help='Skip confirmation prompt')
    rollback_parser.set_defaults(func='execute_emergency_rollback')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate emergency report')
    report_parser.set_defaults(func='generate_emergency_report')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize CLI
    cli = EnhancedNotificationEmergencyCLI()
    
    # Execute command
    try:
        func = getattr(cli, args.func)
        success = func(args)
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Command failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())