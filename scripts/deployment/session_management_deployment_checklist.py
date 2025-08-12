#!/usr/bin/env python3
"""
Session Management Deployment Checklist and Validation

Comprehensive deployment preparation and validation script for session management system.
Includes pre-deployment checks, configuration validation, and rollback procedures.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import Config
from database import DatabaseManager
from session_manager import SessionManager
from flask_session_manager import FlaskSessionManager
from session_health_checker import get_session_health_checker
from session_alerting_system import get_alerting_system


@dataclass
class CheckResult:
    """Result of a deployment check"""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = None
    critical: bool = False


class SessionManagementDeploymentChecker:
    """Deployment checker for session management system"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = SessionManager(self.db_manager)
        self.flask_session_manager = FlaskSessionManager(self.db_manager)
        self.results: List[CheckResult] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_all_checks(self) -> bool:
        """Run all deployment checks"""
        self.logger.info("Starting session management deployment checks...")
        
        checks = [
            self._check_database_connectivity,
            self._check_session_tables,
            self._check_session_manager_functionality,
            self._check_flask_session_integration,
            self._check_session_health_monitoring,
            self._check_session_alerting_system,
            self._check_configuration_validity,
            self._check_security_settings,
            self._check_performance_requirements,
            self._check_cleanup_mechanisms,
            self._check_error_handling,
            self._check_logging_configuration
        ]
        
        for check in checks:
            try:
                result = check()
                self.results.append(result)
                
                status = "✅ PASS" if result.passed else "❌ FAIL"
                self.logger.info(f"{status} - {result.name}: {result.message}")
                
                if not result.passed and result.critical:
                    self.logger.error(f"CRITICAL FAILURE: {result.name}")
                    return False
                    
            except Exception as e:
                error_result = CheckResult(
                    name=check.__name__,
                    passed=False,
                    message=f"Check failed with exception: {str(e)}",
                    critical=True
                )
                self.results.append(error_result)
                self.logger.error(f"❌ ERROR - {check.__name__}: {str(e)}")
                return False
        
        return self._evaluate_overall_result()
    
    def _check_database_connectivity(self) -> CheckResult:
        """Check database connectivity and session table access"""
        try:
            with self.db_manager.get_session() as session:
                # Test basic connectivity
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                
                # Test session table access
                from models import UserSession
                session.query(UserSession).count()
                
            return CheckResult(
                name="Database Connectivity",
                passed=True,
                message="Database connection and session table access verified",
                critical=True
            )
        except Exception as e:
            return CheckResult(
                name="Database Connectivity",
                passed=False,
                message=f"Database connectivity failed: {str(e)}",
                critical=True
            )
    
    def _check_session_tables(self) -> CheckResult:
        """Check session-related database tables"""
        try:
            with self.db_manager.get_session() as session:
                from models import UserSession, User, PlatformConnection
                
                # Check table existence and basic structure
                tables_info = {}
                
                # UserSession table
                user_sessions_count = session.query(UserSession).count()
                tables_info['user_sessions'] = user_sessions_count
                
                # User table
                users_count = session.query(User).count()
                tables_info['users'] = users_count
                
                # PlatformConnection table
                platforms_count = session.query(PlatformConnection).count()
                tables_info['platform_connections'] = platforms_count
                
            return CheckResult(
                name="Session Database Tables",
                passed=True,
                message="All session-related tables accessible",
                details=tables_info,
                critical=True
            )
        except Exception as e:
            return CheckResult(
                name="Session Database Tables",
                passed=False,
                message=f"Session tables check failed: {str(e)}",
                critical=True
            )
    
    def _check_session_manager_functionality(self) -> CheckResult:
        """Check core session manager functionality"""
        try:
            # Test session creation (dry run)
            test_user_id = 1  # Assume test user exists
            test_platform_id = 1  # Assume test platform exists
            
            # Create test session
            session_id = self.session_manager.create_user_session(
                test_user_id, test_platform_id
            )
            
            if not session_id:
                return CheckResult(
                    name="Session Manager Functionality",
                    passed=False,
                    message="Failed to create test session",
                    critical=True
                )
            
            # Validate session
            is_valid = self.session_manager.validate_session(session_id, test_user_id)
            
            # Cleanup test session
            cleanup_success = self.session_manager._cleanup_session(session_id)
            
            if is_valid and cleanup_success:
                return CheckResult(
                    name="Session Manager Functionality",
                    passed=True,
                    message="Session manager core functionality verified",
                    critical=True
                )
            else:
                return CheckResult(
                    name="Session Manager Functionality",
                    passed=False,
                    message="Session validation or cleanup failed",
                    critical=True
                )
                
        except Exception as e:
            return CheckResult(
                name="Session Manager Functionality",
                passed=False,
                message=f"Session manager test failed: {str(e)}",
                critical=True
            )
    
    def _check_flask_session_integration(self) -> CheckResult:
        """Check Flask session manager integration"""
        try:
            from flask import Flask
            
            app = Flask(__name__)
            app.config['SECRET_KEY'] = 'test-key'
            
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    # Test Flask session creation
                    success = self.flask_session_manager.create_user_session(1, 1)
                    
                    if success:
                        # Test validation
                        valid = self.flask_session_manager.validate_session(1)
                        
                        # Test cleanup
                        self.flask_session_manager.clear_session()
                        
                        if valid:
                            return CheckResult(
                                name="Flask Session Integration",
                                passed=True,
                                message="Flask session integration working correctly"
                            )
            
            return CheckResult(
                name="Flask Session Integration",
                passed=False,
                message="Flask session integration test failed"
            )
            
        except Exception as e:
            return CheckResult(
                name="Flask Session Integration",
                passed=False,
                message=f"Flask integration test failed: {str(e)}"
            )
    
    def _check_session_health_monitoring(self) -> CheckResult:
        """Check session health monitoring system"""
        try:
            health_checker = get_session_health_checker(self.db_manager, self.session_manager)
            
            # Run health check
            system_health = health_checker.check_comprehensive_session_health()
            
            if system_health and system_health.status:
                return CheckResult(
                    name="Session Health Monitoring",
                    passed=True,
                    message=f"Health monitoring active - Status: {system_health.status.value}",
                    details={'status': system_health.status.value}
                )
            else:
                return CheckResult(
                    name="Session Health Monitoring",
                    passed=False,
                    message="Health monitoring system not responding"
                )
                
        except Exception as e:
            return CheckResult(
                name="Session Health Monitoring",
                passed=False,
                message=f"Health monitoring check failed: {str(e)}"
            )
    
    def _check_session_alerting_system(self) -> CheckResult:
        """Check session alerting system"""
        try:
            health_checker = get_session_health_checker(self.db_manager, self.session_manager)
            alerting_system = get_alerting_system(health_checker)
            
            # Test alert checking
            new_alerts = alerting_system.check_alerts()
            alert_summary = alerting_system.get_alert_summary()
            
            return CheckResult(
                name="Session Alerting System",
                passed=True,
                message="Alerting system operational",
                details={
                    'new_alerts': len(new_alerts) if new_alerts else 0,
                    'alert_summary': alert_summary
                }
            )
            
        except Exception as e:
            return CheckResult(
                name="Session Alerting System",
                passed=False,
                message=f"Alerting system check failed: {str(e)}"
            )
    
    def _check_configuration_validity(self) -> CheckResult:
        """Check session management configuration"""
        try:
            config_issues = []
            
            # Check session timeout settings
            if not hasattr(self.config.auth, 'session_lifetime'):
                config_issues.append("Missing session_lifetime configuration")
            elif self.config.auth.session_lifetime <= 0:
                config_issues.append("Invalid session_lifetime value")
            
            # Check database configuration
            if not self.config.storage.database_url:
                config_issues.append("Missing database_url configuration")
            
            # Check Flask secret key
            if not self.config.webapp.secret_key:
                config_issues.append("Missing Flask secret_key")
            
            if config_issues:
                return CheckResult(
                    name="Configuration Validity",
                    passed=False,
                    message=f"Configuration issues found: {', '.join(config_issues)}",
                    critical=True
                )
            else:
                return CheckResult(
                    name="Configuration Validity",
                    passed=True,
                    message="Configuration validation passed"
                )
                
        except Exception as e:
            return CheckResult(
                name="Configuration Validity",
                passed=False,
                message=f"Configuration check failed: {str(e)}",
                critical=True
            )
    
    def _check_security_settings(self) -> CheckResult:
        """Check security-related settings"""
        try:
            security_issues = []
            
            # Check if running in production mode
            if self.config.webapp.debug:
                security_issues.append("Debug mode enabled in production")
            
            # Check session security settings
            if len(self.config.webapp.secret_key) < 32:
                security_issues.append("Secret key too short (minimum 32 characters)")
            
            # Check CSRF protection
            csrf_enabled = os.getenv('WTF_CSRF_ENABLED', 'true').lower() == 'true'
            if not csrf_enabled:
                security_issues.append("CSRF protection disabled")
            
            if security_issues:
                return CheckResult(
                    name="Security Settings",
                    passed=False,
                    message=f"Security issues found: {', '.join(security_issues)}",
                    critical=True
                )
            else:
                return CheckResult(
                    name="Security Settings",
                    passed=True,
                    message="Security settings validated"
                )
                
        except Exception as e:
            return CheckResult(
                name="Security Settings",
                passed=False,
                message=f"Security check failed: {str(e)}"
            )
    
    def _check_performance_requirements(self) -> CheckResult:
        """Check performance-related requirements"""
        try:
            performance_metrics = {}
            
            # Test session creation performance
            start_time = time.time()
            session_id = self.session_manager.create_user_session(1, 1)
            creation_time = time.time() - start_time
            performance_metrics['session_creation_ms'] = creation_time * 1000
            
            # Test session validation performance
            start_time = time.time()
            if session_id:
                self.session_manager.validate_session(session_id, 1)
            validation_time = time.time() - start_time
            performance_metrics['session_validation_ms'] = validation_time * 1000
            
            # Cleanup
            if session_id:
                self.session_manager._cleanup_session(session_id)
            
            # Check performance thresholds
            performance_issues = []
            if creation_time > 1.0:  # 1 second threshold
                performance_issues.append(f"Session creation too slow: {creation_time:.2f}s")
            
            if validation_time > 0.5:  # 500ms threshold
                performance_issues.append(f"Session validation too slow: {validation_time:.2f}s")
            
            if performance_issues:
                return CheckResult(
                    name="Performance Requirements",
                    passed=False,
                    message=f"Performance issues: {', '.join(performance_issues)}",
                    details=performance_metrics
                )
            else:
                return CheckResult(
                    name="Performance Requirements",
                    passed=True,
                    message="Performance requirements met",
                    details=performance_metrics
                )
                
        except Exception as e:
            return CheckResult(
                name="Performance Requirements",
                passed=False,
                message=f"Performance check failed: {str(e)}"
            )
    
    def _check_cleanup_mechanisms(self) -> CheckResult:
        """Check session cleanup mechanisms"""
        try:
            # Test expired session cleanup
            cleanup_count = self.session_manager.cleanup_expired_sessions()
            
            # Test user session cleanup
            user_cleanup_count = self.session_manager.cleanup_user_sessions(1)
            
            return CheckResult(
                name="Cleanup Mechanisms",
                passed=True,
                message="Session cleanup mechanisms operational",
                details={
                    'expired_sessions_cleaned': cleanup_count,
                    'user_sessions_cleaned': user_cleanup_count
                }
            )
            
        except Exception as e:
            return CheckResult(
                name="Cleanup Mechanisms",
                passed=False,
                message=f"Cleanup mechanisms check failed: {str(e)}"
            )
    
    def _check_error_handling(self) -> CheckResult:
        """Check error handling mechanisms"""
        try:
            # Test invalid session handling
            invalid_result = self.session_manager.validate_session("invalid-id", 1)
            
            # Test invalid user handling
            invalid_user_result = self.session_manager.validate_session("test-id", 99999)
            
            # Both should return False without throwing exceptions
            if invalid_result is False and invalid_user_result is False:
                return CheckResult(
                    name="Error Handling",
                    passed=True,
                    message="Error handling mechanisms working correctly"
                )
            else:
                return CheckResult(
                    name="Error Handling",
                    passed=False,
                    message="Error handling not working as expected"
                )
                
        except Exception as e:
            return CheckResult(
                name="Error Handling",
                passed=False,
                message=f"Error handling check failed: {str(e)}"
            )
    
    def _check_logging_configuration(self) -> CheckResult:
        """Check logging configuration"""
        try:
            # Check if logs directory exists
            logs_dir = self.config.storage.logs_dir
            if not os.path.exists(logs_dir):
                return CheckResult(
                    name="Logging Configuration",
                    passed=False,
                    message=f"Logs directory does not exist: {logs_dir}"
                )
            
            # Check if logs directory is writable
            test_file = os.path.join(logs_dir, 'deployment_test.log')
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception:
                return CheckResult(
                    name="Logging Configuration",
                    passed=False,
                    message=f"Logs directory not writable: {logs_dir}"
                )
            
            return CheckResult(
                name="Logging Configuration",
                passed=True,
                message="Logging configuration validated"
            )
            
        except Exception as e:
            return CheckResult(
                name="Logging Configuration",
                passed=False,
                message=f"Logging check failed: {str(e)}"
            )
    
    def _evaluate_overall_result(self) -> bool:
        """Evaluate overall deployment readiness"""
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        critical_failures = sum(1 for r in self.results if not r.passed and r.critical)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"DEPLOYMENT READINESS SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total Checks: {total_checks}")
        self.logger.info(f"Passed: {passed_checks}")
        self.logger.info(f"Failed: {total_checks - passed_checks}")
        self.logger.info(f"Critical Failures: {critical_failures}")
        self.logger.info(f"Success Rate: {(passed_checks / total_checks * 100):.1f}%")
        
        # Deployment ready if no critical failures and >80% success rate
        deployment_ready = (critical_failures == 0 and 
                          (passed_checks / total_checks) >= 0.8)
        
        if deployment_ready:
            self.logger.info("✅ DEPLOYMENT READY")
        else:
            self.logger.error("❌ DEPLOYMENT NOT READY")
        
        return deployment_ready
    
    def generate_deployment_report(self) -> Dict[str, Any]:
        """Generate detailed deployment report"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'deployment_ready': self._evaluate_overall_result(),
            'checks': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'critical': r.critical,
                    'details': r.details
                }
                for r in self.results
            ],
            'summary': {
                'total_checks': len(self.results),
                'passed_checks': sum(1 for r in self.results if r.passed),
                'failed_checks': sum(1 for r in self.results if not r.passed),
                'critical_failures': sum(1 for r in self.results if not r.passed and r.critical)
            }
        }


def create_rollback_script():
    """Create rollback script for session management deployment"""
    rollback_script = '''#!/bin/bash
# Session Management Rollback Script

echo "Starting session management rollback..."

# 1. Stop application
echo "Stopping application..."
# Add your application stop commands here
# systemctl stop vedfolnir

# 2. Backup current database
echo "Backing up current database..."
timestamp=$(date +%Y%m%d_%H%M%S)
# Add database backup commands here
# pg_dump vedfolnir > /backup/vedfolnir_rollback_$timestamp.sql

# 3. Restore previous database state
echo "Restoring previous database state..."
# Add database restore commands here
# psql vedfolnir < /backup/vedfolnir_pre_session_management.sql

# 4. Restore previous application code
echo "Restoring previous application code..."
# Add code restore commands here
# git checkout previous-stable-tag

# 5. Restart application
echo "Restarting application..."
# Add application start commands here
# systemctl start vedfolnir

echo "Rollback completed. Please verify application functionality."
'''
    
    with open('rollback_session_management.sh', 'w') as f:
        f.write(rollback_script)
    
    os.chmod('rollback_session_management.sh', 0o755)
    print("✅ Rollback script created: rollback_session_management.sh")


def main():
    """Main deployment checker function"""
    print("🚀 Session Management Deployment Checker")
    print("=" * 50)
    
    checker = SessionManagementDeploymentChecker()
    
    # Run all checks
    deployment_ready = checker.run_all_checks()
    
    # Generate report
    report = checker.generate_deployment_report()
    
    # Save report to file
    report_file = f"session_management_deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Create rollback script
    create_rollback_script()
    
    # Exit with appropriate code
    if deployment_ready:
        print("\n🎉 Session management system is ready for deployment!")
        sys.exit(0)
    else:
        print("\n⚠️  Session management system is NOT ready for deployment.")
        print("Please address the failed checks before proceeding.")
        sys.exit(1)


if __name__ == '__main__':
    main()