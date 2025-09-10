#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Maintenance Scheduler

Automated scheduler for regular security maintenance tasks including
CSRF audits, security scans, and compliance checks.
"""

import os
import sys
import logging
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityMaintenanceScheduler:
    """Automated security maintenance task scheduler"""
    
    def __init__(self):
        """Initialize security maintenance scheduler"""
        self.last_run_times = {}
        
    def run_daily_csrf_check(self):
        """Run daily CSRF security check"""
        logger.info("Running daily CSRF security check")
        
        try:
            # Run CSRF metrics collection
            os.system("python -c 'from app.core.security.monitoring.csrf_security_metrics import get_csrf_security_metrics; get_csrf_security_metrics().get_csrf_dashboard_data()'")
            
            # Check for high violation rates
            self._check_csrf_violation_rates()
            
            logger.info("Daily CSRF security check completed")
            
        except Exception as e:
            logger.error(f"Daily CSRF security check failed: {e}")
    
    def run_weekly_security_scan(self):
        """Run weekly security scan"""
        logger.info("Running weekly security scan")
        
        try:
            # Run template security scan
            os.system("python -m security.audit.csrf_template_scanner")
            
            # Run compliance validation
            os.system("python -m security.audit.csrf_compliance_validator")
            
            # Generate weekly security report
            self._generate_weekly_report()
            
            logger.info("Weekly security scan completed")
            
        except Exception as e:
            logger.error(f"Weekly security scan failed: {e}")
    
    def run_monthly_comprehensive_audit(self):
        """Run monthly comprehensive security audit"""
        logger.info("Running monthly comprehensive security audit")
        
        try:
            # Run comprehensive security test
            os.system("python scripts/security/comprehensive_security_test.py")
            
            # Run OWASP compliance check
            os.system("python scripts/security/owasp_compliance_validator.py")
            
            # Generate monthly audit report
            self._generate_monthly_audit_report()
            
            logger.info("Monthly comprehensive security audit completed")
            
        except Exception as e:
            logger.error(f"Monthly comprehensive security audit failed: {e}")
    
    def run_security_update_check(self):
        """Check for security updates"""
        logger.info("Checking for security updates")
        
        try:
            # Check for dependency updates
            result = os.system("pip list --outdated --format=json > /tmp/outdated_packages.json")
            
            if result == 0:
                logger.info("Security update check completed")
            else:
                logger.warning("Security update check had issues")
                
        except Exception as e:
            logger.error(f"Security update check failed: {e}")
    
    def _check_csrf_violation_rates(self):
        """Check CSRF violation rates and alert if high"""
        try:
            from app.core.security.monitoring.csrf_security_metrics import get_csrf_security_metrics
            
            csrf_metrics = get_csrf_security_metrics()
            compliance_metrics = csrf_metrics.get_compliance_metrics('24h')
            
            if compliance_metrics.violation_count > 50:
                logger.warning(f"High CSRF violation rate detected: {compliance_metrics.violation_count} violations in 24h")
                self._send_security_alert("High CSRF violation rate", 
                                        f"{compliance_metrics.violation_count} violations detected")
            
        except Exception as e:
            logger.error(f"Failed to check CSRF violation rates: {e}")
    
    def _generate_weekly_report(self):
        """Generate weekly security report"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'report_type': 'weekly_security_scan',
                'status': 'completed'
            }
            
            # Save report
            reports_dir = Path('security/reports')
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = reports_dir / f"weekly_security_report_{datetime.now().strftime('%Y%m%d')}.json"
            
            import json
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Weekly security report generated: {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}")
    
    def _generate_monthly_audit_report(self):
        """Generate monthly audit report"""
        try:
            from app.core.security.reporting.security_audit_system import get_security_audit_system
            
            audit_system = get_security_audit_system()
            report = audit_system.generate_comprehensive_audit_report("monthly")
            
            logger.info(f"Monthly audit report generated: {report.report_id}")
            
        except Exception as e:
            logger.error(f"Failed to generate monthly audit report: {e}")
    
    def _send_security_alert(self, alert_type: str, message: str):
        """Send security alert"""
        try:
            from app.core.security.monitoring.security_alerting import get_security_alert_manager
            
            alert_manager = get_security_alert_manager()
            alert_id = alert_manager.trigger_csrf_violation_alert(50, "scheduler")
            
            logger.info(f"Security alert sent: {alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send security alert: {e}")
    
    def setup_schedule(self):
        """Setup maintenance schedule"""
        logger.info("Setting up security maintenance schedule")
        
        # Daily tasks
        schedule.every().day.at("02:00").do(self.run_daily_csrf_check)
        schedule.every().day.at("03:00").do(self.run_security_update_check)
        
        # Weekly tasks
        schedule.every().monday.at("01:00").do(self.run_weekly_security_scan)
        
        # Monthly tasks
        schedule.every().month.do(self.run_monthly_comprehensive_audit)
        
        logger.info("Security maintenance schedule configured")
    
    def run_scheduler(self):
        """Run the maintenance scheduler"""
        logger.info("Starting security maintenance scheduler")
        
        self.setup_schedule()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Security maintenance scheduler stopped")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

def main():
    """Main scheduler function"""
    try:
        scheduler = SecurityMaintenanceScheduler()
        
        # Check if running in daemon mode
        if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
            scheduler.run_scheduler()
        else:
            # Run immediate maintenance check
            logger.info("Running immediate security maintenance check")
            scheduler.run_daily_csrf_check()
            scheduler.run_security_update_check()
            logger.info("Immediate security maintenance check completed")
            
    except Exception as e:
        logger.error(f"Security maintenance scheduler failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()