# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSS Security Enhancement Monitoring Script

This script monitors the health and performance of the CSS Security Enhancement
deployment, checking for issues with CSS file loading, template rendering,
and Content Security Policy compliance.
"""

import os
import sys
import time
import requests
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class CSSSecurityMonitor:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.css_files = [
            "static/css/security-extracted.css",
            "static/css/components.css", 
            "admin/static/css/admin-extracted.css"
        ]
        self.test_pages = [
            "/",
            "/login",
            "/caption_generation",
            "/admin"
        ]
        self.alerts = []
        
    def check_application_health(self):
        """Check if the application is responding"""
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Application healthy (HTTP {response.status_code})")
                return True
            else:
                self.alerts.append(f"Application returned HTTP {response.status_code}")
                print(f"❌ Application unhealthy (HTTP {response.status_code})")
                return False
        except requests.exceptions.RequestException as e:
            self.alerts.append(f"Application unreachable: {e}")
            print(f"❌ Application unreachable: {e}")
            return False
    
    def check_css_files(self):
        """Check CSS file accessibility and integrity"""
        print("\n=== CSS File Health Check ===")
        all_healthy = True
        
        for css_file in self.css_files:
            # Check local file exists
            if os.path.exists(css_file):
                file_size = os.path.getsize(css_file)
                print(f"✅ {css_file} exists locally ({file_size} bytes)")
                
                # Check HTTP accessibility
                css_url = f"{self.base_url}/{css_file}"
                try:
                    response = requests.get(css_url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {css_url} accessible via HTTP")
                        
                        # Check content type
                        content_type = response.headers.get('content-type', '')
                        if 'text/css' in content_type:
                            print(f"✅ {css_file} has correct content-type")
                        else:
                            self.alerts.append(f"{css_file} has incorrect content-type: {content_type}")
                            print(f"⚠️  {css_file} content-type: {content_type}")
                    else:
                        self.alerts.append(f"{css_url} returned HTTP {response.status_code}")
                        print(f"❌ {css_url} returned HTTP {response.status_code}")
                        all_healthy = False
                except requests.exceptions.RequestException as e:
                    self.alerts.append(f"{css_url} request failed: {e}")
                    print(f"❌ {css_url} request failed: {e}")
                    all_healthy = False
            else:
                self.alerts.append(f"{css_file} does not exist locally")
                print(f"❌ {css_file} does not exist locally")
                all_healthy = False
        
        return all_healthy
    
    def check_inline_styles(self):
        """Check for remaining inline styles in templates"""
        print("\n=== Inline Style Detection ===")
        try:
            # Run the CSS extraction helper
            result = subprocess.run([
                sys.executable, 
                "tests/scripts/css_extraction_helper.py"
            ], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..', '..'))
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "No inline styles found" in output:
                    print("✅ No inline styles detected")
                    return True
                else:
                    print(f"⚠️  Inline styles detected:\n{output}")
                    self.alerts.append(f"Inline styles found: {output}")
                    return False
            else:
                print(f"❌ CSS extraction helper failed: {result.stderr}")
                self.alerts.append(f"CSS extraction helper failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error running inline style check: {e}")
            self.alerts.append(f"Inline style check error: {e}")
            return False
    
    def check_page_load_times(self):
        """Monitor page load performance"""
        print("\n=== Page Load Performance ===")
        all_healthy = True
        
        for page in self.test_pages:
            url = f"{self.base_url}{page}"
            try:
                start_time = time.time()
                response = requests.get(url, timeout=30)
                load_time = time.time() - start_time
                
                if response.status_code == 200:
                    if load_time < 5.0:
                        print(f"✅ {page} loaded in {load_time:.2f}s")
                    elif load_time < 10.0:
                        print(f"⚠️  {page} loaded in {load_time:.2f}s (slow)")
                        self.alerts.append(f"{page} slow load time: {load_time:.2f}s")
                    else:
                        print(f"❌ {page} loaded in {load_time:.2f}s (very slow)")
                        self.alerts.append(f"{page} very slow load time: {load_time:.2f}s")
                        all_healthy = False
                else:
                    print(f"❌ {page} returned HTTP {response.status_code}")
                    self.alerts.append(f"{page} returned HTTP {response.status_code}")
                    all_healthy = False
            except requests.exceptions.RequestException as e:
                print(f"❌ {page} request failed: {e}")
                self.alerts.append(f"{page} request failed: {e}")
                all_healthy = False
        
        return all_healthy
    
    def check_template_integrity(self):
        """Check template syntax and structure"""
        print("\n=== Template Integrity Check ===")
        try:
            # Check for template syntax errors
            from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
            
            template_dirs = ['templates', 'admin/templates']
            errors = []
            
            for template_dir in template_dirs:
                if os.path.exists(template_dir):
                    env = Environment(loader=FileSystemLoader(template_dir))
                    for root, dirs, files in os.walk(template_dir):
                        for file in files:
                            if file.endswith('.html'):
                                template_path = os.path.relpath(os.path.join(root, file), template_dir)
                                try:
                                    env.get_template(template_path)
                                except TemplateSyntaxError as e:
                                    errors.append(f'{template_path}: {e}')
            
            if errors:
                print(f"❌ Found {len(errors)} template errors:")
                for error in errors:
                    print(f"   {error}")
                self.alerts.extend(errors)
                return False
            else:
                print("✅ All templates have valid syntax")
                return True
                
        except Exception as e:
            print(f"❌ Template integrity check failed: {e}")
            self.alerts.append(f"Template integrity check failed: {e}")
            return False
    
    def check_logs_for_errors(self):
        """Check application logs for CSS-related errors"""
        print("\n=== Log Error Analysis ===")
        log_file = "logs/webapp.log"
        
        if not os.path.exists(log_file):
            print(f"⚠️  Log file {log_file} not found")
            return True
        
        try:
            # Check last 100 lines for CSS/template errors
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            css_errors = []
            template_errors = []
            
            for line in recent_lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['css', 'style', 'stylesheet']):
                    if any(error_keyword in line_lower for error_keyword in ['error', 'failed', 'exception']):
                        css_errors.append(line.strip())
                
                if any(keyword in line_lower for keyword in ['template', 'jinja']):
                    if any(error_keyword in line_lower for error_keyword in ['error', 'failed', 'exception']):
                        template_errors.append(line.strip())
            
            if css_errors:
                print(f"❌ Found {len(css_errors)} CSS-related errors in logs:")
                for error in css_errors[-5:]:  # Show last 5
                    print(f"   {error}")
                self.alerts.extend(css_errors)
            
            if template_errors:
                print(f"❌ Found {len(template_errors)} template-related errors in logs:")
                for error in template_errors[-5:]:  # Show last 5
                    print(f"   {error}")
                self.alerts.extend(template_errors)
            
            if not css_errors and not template_errors:
                print("✅ No CSS or template errors found in recent logs")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            self.alerts.append(f"Log file read error: {e}")
            return False
    
    def generate_report(self):
        """Generate monitoring report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = {
            "timestamp": timestamp,
            "status": "healthy" if not self.alerts else "issues_detected",
            "alerts": self.alerts,
            "checks_performed": [
                "application_health",
                "css_file_accessibility", 
                "inline_style_detection",
                "page_load_performance",
                "template_integrity",
                "log_error_analysis"
            ]
        }
        
        # Save report to file
        report_dir = "logs/monitoring"
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"css_security_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n=== Monitoring Report ===")
        print(f"Timestamp: {timestamp}")
        print(f"Status: {report['status']}")
        print(f"Alerts: {len(self.alerts)}")
        print(f"Report saved to: {report_file}")
        
        return report
    
    def run_full_check(self):
        """Run all monitoring checks"""
        print("=== CSS Security Enhancement Monitor ===")
        print(f"Starting monitoring at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        checks = [
            ("Application Health", self.check_application_health),
            ("CSS Files", self.check_css_files),
            ("Inline Styles", self.check_inline_styles),
            ("Page Load Times", self.check_page_load_times),
            ("Template Integrity", self.check_template_integrity),
            ("Log Errors", self.check_logs_for_errors)
        ]
        
        results = {}
        for check_name, check_func in checks:
            try:
                results[check_name] = check_func()
            except Exception as e:
                print(f"❌ {check_name} check failed with exception: {e}")
                self.alerts.append(f"{check_name} check exception: {e}")
                results[check_name] = False
        
        # Generate final report
        report = self.generate_report()
        
        # Print summary
        print(f"\n=== Summary ===")
        healthy_checks = sum(1 for result in results.values() if result)
        total_checks = len(results)
        print(f"Healthy checks: {healthy_checks}/{total_checks}")
        
        if self.alerts:
            print(f"Total alerts: {len(self.alerts)}")
            print("Recent alerts:")
            for alert in self.alerts[-5:]:
                print(f"  - {alert}")
        else:
            print("✅ All checks passed - system healthy")
        
        return len(self.alerts) == 0

def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CSS Security Enhancement Monitor")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="Base URL to monitor")
    parser.add_argument("--continuous", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--interval", type=int, default=300, help="Monitoring interval in seconds (default: 300)")
    
    args = parser.parse_args()
    
    monitor = CSSSecurityMonitor(args.url)
    
    if args.continuous:
        print(f"Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                monitor.run_full_check()
                print(f"\nNext check in {args.interval} seconds...")
                time.sleep(args.interval)
                monitor.alerts = []  # Reset alerts for next check
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
    else:
        # Single check
        healthy = monitor.run_full_check()
        sys.exit(0 if healthy else 1)

if __name__ == "__main__":
    main()