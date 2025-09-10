# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Services Health Checks
Comprehensive health monitoring for multi-tenant admin services
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from app.core.database.core.database_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Health check result"""
    service: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None
    response_time_ms: float = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}

class AdminHealthChecker:
    """Comprehensive health checker for admin services"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        
    def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks"""
        logger.info("Running comprehensive admin services health check...")
        
        checks = {
            'database': self.check_database_health(),
            'redis': self.check_redis_health(),
            'admin_database_tables': self.check_admin_database_tables(),
            'feature_flags': self.check_feature_flags_system(),
            'admin_dashboard': self.check_admin_dashboard(),
            'admin_api': self.check_admin_api_endpoints(),
            'monitoring_system': self.check_monitoring_system(),
            'alert_system': self.check_alert_system(),
            'audit_logging': self.check_audit_logging(),
            'performance_metrics': self.check_performance_metrics(),
            'session_management': self.check_session_management(),
            'web_application': self.check_web_application()
        }
        
        return checks
    
    def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and admin tables"""
        start_time = time.time()
        
        try:
            with self.db_manager.get_session() as session:
                # Test basic connectivity
                session.execute("SELECT 1")
                
                # Check database version and type
                result = session.execute("SELECT VERSION()").scalar()
                
                response_time = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    service="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    details={
                        'version': result,
                        'connection_pool_size': self.config.get('DB_POOL_SIZE', 20)
                    },
                    response_time_ms=response_time
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {e}",
                response_time_ms=response_time
            )
    
    def check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity and configuration"""
        start_time = time.time()
        
        try:
            import redis
            
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                return HealthCheckResult(
                    service="redis",
                    status=HealthStatus.WARNING,
                    message="Redis URL not configured"
                )
            
            r = redis.from_url(redis_url)
            
            # Test connection
            ping_result = r.ping()
            
            # Get Redis info
            info = r.info()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                service="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
                details={
                    'version': info.get('redis_version'),
                    'connected_clients': info.get('connected_clients'),
                    'used_memory_human': info.get('used_memory_human'),
                    'ping_response': ping_result
                },
                response_time_ms=response_time
            )
            
        except ImportError:
            return HealthCheckResult(
                service="redis",
                status=HealthStatus.WARNING,
                message="Redis client not installed"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="redis",
                status=HealthStatus.CRITICAL,
                message=f"Redis connection failed: {e}",
                response_time_ms=response_time
            )
    
    def check_admin_database_tables(self) -> HealthCheckResult:
        """Check admin-specific database tables"""
        start_time = time.time()
        
        try:
            with self.db_manager.get_session() as session:
                # Check for admin tables
                admin_tables = [
                    'system_configuration',
                    'job_audit_log',
                    'alert_configuration', 
                    'system_alerts',
                    'performance_metrics'
                ]
                
                existing_tables = []
                missing_tables = []
                
                for table in admin_tables:
                    try:
                        session.execute(f"SELECT 1 FROM {table} LIMIT 1")
                        existing_tables.append(table)
                    except:
                        missing_tables.append(table)
                
                # Check for admin columns in caption_generation_tasks
                admin_columns = [
                    'priority', 'admin_notes', 'cancelled_by_admin',
                    'admin_user_id', 'retry_count', 'max_retries'
                ]
                
                existing_columns = []
                missing_columns = []
                
                try:
                    columns_result = session.execute("DESCRIBE caption_generation_tasks").fetchall()
                    existing_column_names = [row[0] for row in columns_result]
                    
                    for column in admin_columns:
                        if column in existing_column_names:
                            existing_columns.append(column)
                        else:
                            missing_columns.append(column)
                except:
                    missing_columns = admin_columns
                
                response_time = (time.time() - start_time) * 1000
                
                if missing_tables or missing_columns:
                    status = HealthStatus.WARNING
                    message = "Some admin database components missing"
                else:
                    status = HealthStatus.HEALTHY
                    message = "All admin database tables present"
                
                return HealthCheckResult(
                    service="admin_database_tables",
                    status=status,
                    message=message,
                    details={
                        'existing_tables': existing_tables,
                        'missing_tables': missing_tables,
                        'existing_columns': existing_columns,
                        'missing_columns': missing_columns
                    },
                    response_time_ms=response_time
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="admin_database_tables",
                status=HealthStatus.CRITICAL,
                message=f"Admin database check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_feature_flags_system(self) -> HealthCheckResult:
        """Check feature flags system"""
        start_time = time.time()
        
        try:
            from admin.feature_flags import FeatureFlagManager
            
            manager = FeatureFlagManager()
            flags = manager.list_flags()
            
            # Check for required admin flags
            required_flags = [
                'multi_tenant_admin',
                'admin_dashboard',
                'system_monitoring'
            ]
            
            missing_flags = []
            enabled_flags = []
            
            for flag in required_flags:
                if flag not in flags:
                    missing_flags.append(flag)
                elif flags[flag]['state'] == 'enabled':
                    enabled_flags.append(flag)
            
            response_time = (time.time() - start_time) * 1000
            
            if missing_flags:
                status = HealthStatus.WARNING
                message = f"Missing feature flags: {', '.join(missing_flags)}"
            else:
                status = HealthStatus.HEALTHY
                message = "Feature flags system operational"
            
            return HealthCheckResult(
                service="feature_flags",
                status=status,
                message=message,
                details={
                    'total_flags': len(flags),
                    'enabled_flags': enabled_flags,
                    'missing_flags': missing_flags
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="feature_flags",
                status=HealthStatus.CRITICAL,
                message=f"Feature flags system error: {e}",
                response_time_ms=response_time
            )
    
    def check_admin_dashboard(self) -> HealthCheckResult:
        """Check admin dashboard accessibility"""
        start_time = time.time()
        
        try:
            # Try to access admin dashboard endpoint
            response = requests.get(
                f"{self.base_url}/admin/dashboard",
                timeout=10,
                allow_redirects=False
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Check if we get a response (even if redirect to login)
            if response.status_code in [200, 302, 401, 403]:
                status = HealthStatus.HEALTHY
                message = "Admin dashboard accessible"
            else:
                status = HealthStatus.WARNING
                message = f"Admin dashboard returned status {response.status_code}"
            
            return HealthCheckResult(
                service="admin_dashboard",
                status=status,
                message=message,
                details={
                    'status_code': response.status_code,
                    'response_headers': dict(response.headers)
                },
                response_time_ms=response_time
            )
            
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                service="admin_dashboard",
                status=HealthStatus.WARNING,
                message="Web application not running"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="admin_dashboard",
                status=HealthStatus.CRITICAL,
                message=f"Admin dashboard check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_admin_api_endpoints(self) -> HealthCheckResult:
        """Check admin API endpoints"""
        start_time = time.time()
        
        try:
            # Test admin API endpoints
            endpoints_to_check = [
                '/admin/api/health',
                '/admin/api/system-status',
                '/admin/api/jobs'
            ]
            
            accessible_endpoints = []
            failed_endpoints = []
            
            for endpoint in endpoints_to_check:
                try:
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        timeout=5,
                        allow_redirects=False
                    )
                    
                    # Accept various status codes (auth required, etc.)
                    if response.status_code in [200, 401, 403, 404]:
                        accessible_endpoints.append(endpoint)
                    else:
                        failed_endpoints.append(f"{endpoint} ({response.status_code})")
                        
                except:
                    failed_endpoints.append(f"{endpoint} (connection failed)")
            
            response_time = (time.time() - start_time) * 1000
            
            if len(accessible_endpoints) >= len(endpoints_to_check) // 2:
                status = HealthStatus.HEALTHY
                message = "Admin API endpoints accessible"
            else:
                status = HealthStatus.WARNING
                message = "Some admin API endpoints not accessible"
            
            return HealthCheckResult(
                service="admin_api",
                status=status,
                message=message,
                details={
                    'accessible_endpoints': accessible_endpoints,
                    'failed_endpoints': failed_endpoints
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="admin_api",
                status=HealthStatus.CRITICAL,
                message=f"Admin API check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_monitoring_system(self) -> HealthCheckResult:
        """Check monitoring system components"""
        start_time = time.time()
        
        try:
            # Check if monitoring classes can be imported
            monitoring_components = []
            
            try:
                from app.services.monitoring.system.system_monitor import SystemMonitor
                monitoring_components.append('SystemMonitor')
            except ImportError:
                pass
            
            try:
                from monitoring_dashboard_service import MonitoringDashboardService
                monitoring_components.append('MonitoringDashboardService')
            except ImportError:
                pass
            
            # Check performance metrics table
            metrics_table_exists = False
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1 FROM performance_metrics LIMIT 1")
                    metrics_table_exists = True
            except:
                pass
            
            response_time = (time.time() - start_time) * 1000
            
            if monitoring_components and metrics_table_exists:
                status = HealthStatus.HEALTHY
                message = "Monitoring system components available"
            elif monitoring_components or metrics_table_exists:
                status = HealthStatus.WARNING
                message = "Partial monitoring system available"
            else:
                status = HealthStatus.WARNING
                message = "Monitoring system components not found"
            
            return HealthCheckResult(
                service="monitoring_system",
                status=status,
                message=message,
                details={
                    'available_components': monitoring_components,
                    'metrics_table_exists': metrics_table_exists
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="monitoring_system",
                status=HealthStatus.CRITICAL,
                message=f"Monitoring system check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_alert_system(self) -> HealthCheckResult:
        """Check alert system components"""
        start_time = time.time()
        
        try:
            # Check if alert manager can be imported
            alert_components = []
            
            try:
                from app.services.alerts.components.alert_manager import AlertManager
                alert_components.append('AlertManager')
            except ImportError:
                pass
            
            # Check alert configuration table
            alert_config_exists = False
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1 FROM alert_configuration LIMIT 1")
                    alert_config_exists = True
            except:
                pass
            
            # Check system alerts table
            alerts_table_exists = False
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1 FROM system_alerts LIMIT 1")
                    alerts_table_exists = True
            except:
                pass
            
            response_time = (time.time() - start_time) * 1000
            
            if alert_components and alert_config_exists and alerts_table_exists:
                status = HealthStatus.HEALTHY
                message = "Alert system fully operational"
            elif alert_components or alert_config_exists or alerts_table_exists:
                status = HealthStatus.WARNING
                message = "Partial alert system available"
            else:
                status = HealthStatus.WARNING
                message = "Alert system not configured"
            
            return HealthCheckResult(
                service="alert_system",
                status=status,
                message=message,
                details={
                    'available_components': alert_components,
                    'alert_config_exists': alert_config_exists,
                    'alerts_table_exists': alerts_table_exists
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="alert_system",
                status=HealthStatus.CRITICAL,
                message=f"Alert system check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_audit_logging(self) -> HealthCheckResult:
        """Check audit logging system"""
        start_time = time.time()
        
        try:
            # Check audit logger
            audit_components = []
            
            try:
                from audit_logger import AuditLogger
                audit_components.append('AuditLogger')
            except ImportError:
                pass
            
            # Check job audit log table
            audit_table_exists = False
            recent_audit_entries = 0
            
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1 FROM job_audit_log LIMIT 1")
                    audit_table_exists = True
                    
                    # Count recent audit entries
                    recent_cutoff = datetime.now() - timedelta(hours=24)
                    recent_audit_entries = session.execute(
                        "SELECT COUNT(*) FROM job_audit_log WHERE timestamp > %s",
                        (recent_cutoff,)
                    ).scalar()
                    
            except:
                pass
            
            response_time = (time.time() - start_time) * 1000
            
            if audit_components and audit_table_exists:
                status = HealthStatus.HEALTHY
                message = "Audit logging system operational"
            elif audit_components or audit_table_exists:
                status = HealthStatus.WARNING
                message = "Partial audit logging available"
            else:
                status = HealthStatus.WARNING
                message = "Audit logging not configured"
            
            return HealthCheckResult(
                service="audit_logging",
                status=status,
                message=message,
                details={
                    'available_components': audit_components,
                    'audit_table_exists': audit_table_exists,
                    'recent_audit_entries_24h': recent_audit_entries
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="audit_logging",
                status=HealthStatus.CRITICAL,
                message=f"Audit logging check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_performance_metrics(self) -> HealthCheckResult:
        """Check performance metrics collection"""
        start_time = time.time()
        
        try:
            # Check performance metrics table
            metrics_available = False
            recent_metrics = 0
            
            try:
                with self.db_manager.get_session() as session:
                    session.execute("SELECT 1 FROM performance_metrics LIMIT 1")
                    metrics_available = True
                    
                    # Count recent metrics
                    recent_cutoff = datetime.now() - timedelta(hours=1)
                    recent_metrics = session.execute(
                        "SELECT COUNT(*) FROM performance_metrics WHERE recorded_at > %s",
                        (recent_cutoff,)
                    ).scalar()
                    
            except:
                pass
            
            response_time = (time.time() - start_time) * 1000
            
            if metrics_available:
                if recent_metrics > 0:
                    status = HealthStatus.HEALTHY
                    message = "Performance metrics actively collected"
                else:
                    status = HealthStatus.WARNING
                    message = "Performance metrics table exists but no recent data"
            else:
                status = HealthStatus.WARNING
                message = "Performance metrics not configured"
            
            return HealthCheckResult(
                service="performance_metrics",
                status=status,
                message=message,
                details={
                    'metrics_table_exists': metrics_available,
                    'recent_metrics_1h': recent_metrics
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="performance_metrics",
                status=HealthStatus.CRITICAL,
                message=f"Performance metrics check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_session_management(self) -> HealthCheckResult:
        """Check session management system"""
        start_time = time.time()
        
        try:
            # Check Redis session manager
            session_components = []
            
            try:
                from session_manager_v2 import SessionManagerV2
                session_components.append('SessionManagerV2')
            except ImportError:
                pass
            
            try:
                from session_manager_v2 import SessionManagerV2
                session_components.append('SessionManagerV2')
            except ImportError:
                pass
            
            # Test Redis connectivity for sessions
            redis_sessions_working = False
            try:
                import redis
                redis_url = os.getenv('REDIS_URL')
                if redis_url:
                    r = redis.from_url(redis_url)
                    r.ping()
                    redis_sessions_working = True
            except:
                pass
            
            response_time = (time.time() - start_time) * 1000
            
            if session_components and redis_sessions_working:
                status = HealthStatus.HEALTHY
                message = "Session management system operational"
            elif session_components or redis_sessions_working:
                status = HealthStatus.WARNING
                message = "Partial session management available"
            else:
                status = HealthStatus.WARNING
                message = "Session management not fully configured"
            
            return HealthCheckResult(
                service="session_management",
                status=status,
                message=message,
                details={
                    'available_components': session_components,
                    'redis_sessions_working': redis_sessions_working
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="session_management",
                status=HealthStatus.CRITICAL,
                message=f"Session management check failed: {e}",
                response_time_ms=response_time
            )
    
    def check_web_application(self) -> HealthCheckResult:
        """Check web application health"""
        start_time = time.time()
        
        try:
            # Test main application endpoint
            response = requests.get(
                f"{self.base_url}/health",
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                message = "Web application healthy"
                
                try:
                    health_data = response.json()
                except:
                    health_data = {}
                    
            else:
                status = HealthStatus.WARNING
                message = f"Web application returned status {response.status_code}"
                health_data = {}
            
            return HealthCheckResult(
                service="web_application",
                status=status,
                message=message,
                details={
                    'status_code': response.status_code,
                    'health_data': health_data
                },
                response_time_ms=response_time
            )
            
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                service="web_application",
                status=HealthStatus.CRITICAL,
                message="Web application not accessible"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="web_application",
                status=HealthStatus.CRITICAL,
                message=f"Web application check failed: {e}",
                response_time_ms=response_time
            )
    
    def generate_health_report(self, results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        overall_status = HealthStatus.HEALTHY
        critical_issues = []
        warnings = []
        healthy_services = []
        
        for service, result in results.items():
            if result.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                critical_issues.append(f"{service}: {result.message}")
            elif result.status == HealthStatus.WARNING:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.WARNING
                warnings.append(f"{service}: {result.message}")
            elif result.status == HealthStatus.HEALTHY:
                healthy_services.append(service)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status.value,
            'summary': {
                'total_services': len(results),
                'healthy_services': len(healthy_services),
                'warnings': len(warnings),
                'critical_issues': len(critical_issues)
            },
            'healthy_services': healthy_services,
            'warnings': warnings,
            'critical_issues': critical_issues,
            'detailed_results': {
                service: {
                    'status': result.status.value,
                    'message': result.message,
                    'response_time_ms': result.response_time_ms,
                    'details': result.details
                }
                for service, result in results.items()
            }
        }

def main():
    parser = argparse.ArgumentParser(description='Admin Services Health Check')
    parser.add_argument('--service', help='Check specific service only')
    parser.add_argument('--output', help='Output file for health report')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                       help='Output format')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous health monitoring')
    parser.add_argument('--interval', type=int, default=60,
                       help='Interval for continuous monitoring (seconds)')
    
    args = parser.parse_args()
    
    checker = AdminHealthChecker()
    
    if args.continuous:
        logger.info(f"Starting continuous health monitoring (interval: {args.interval}s)")
        
        while True:
            try:
                results = checker.check_all_services()
                report = checker.generate_health_report(results)
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(report, f, indent=2)
                
                # Log critical issues
                if report['critical_issues']:
                    logger.error(f"Critical issues detected: {', '.join(report['critical_issues'])}")
                elif report['warnings']:
                    logger.warning(f"Warnings: {', '.join(report['warnings'])}")
                else:
                    logger.info("All services healthy")
                
                time.sleep(args.interval)
                
            except KeyboardInterrupt:
                logger.info("Health monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(args.interval)
    
    else:
        # Single health check run
        if args.service:
            # Check specific service
            method_name = f"check_{args.service}"
            if hasattr(checker, method_name):
                result = getattr(checker, method_name)()
                results = {args.service: result}
            else:
                print(f"Unknown service: {args.service}")
                sys.exit(1)
        else:
            # Check all services
            results = checker.check_all_services()
        
        report = checker.generate_health_report(results)
        
        if args.format == 'json':
            output = json.dumps(report, indent=2)
        else:
            # Text format
            output = f"Admin Services Health Check Report\n"
            output += f"{'=' * 40}\n"
            output += f"Timestamp: {report['timestamp']}\n"
            output += f"Overall Status: {report['overall_status'].upper()}\n"
            output += f"Services: {report['summary']['healthy_services']}/{report['summary']['total_services']} healthy\n"
            
            if report['critical_issues']:
                output += f"\n🚨 CRITICAL ISSUES:\n"
                for issue in report['critical_issues']:
                    output += f"  - {issue}\n"
            
            if report['warnings']:
                output += f"\n⚠️  WARNINGS:\n"
                for warning in report['warnings']:
                    output += f"  - {warning}\n"
            
            if report['healthy_services']:
                output += f"\n✅ HEALTHY SERVICES:\n"
                for service in report['healthy_services']:
                    output += f"  - {service}\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Health report saved to: {args.output}")
        else:
            print(output)
        
        # Exit with appropriate code
        if report['overall_status'] == 'critical':
            sys.exit(2)
        elif report['overall_status'] == 'warning':
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == '__main__':
    main()