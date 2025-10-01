# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Complete Migration Test Script
Tests the complete data migration process with validation
"""

import os
import sys
import subprocess
import json
import logging
import time
import requests
from datetime import datetime
from pathlib import Path
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class CompleteMigrationTester:
    def __init__(self, export_dir="./migration_exports"):
        """Initialize complete migration tester"""
        self.export_dir = Path(export_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'migration_test_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Test configuration
        self.docker_compose_file = 'docker-compose.yml'
        self.app_url = 'http://localhost:5000'
        self.containers = {
            'mysql': 'vedfolnir_mysql',
            'redis': 'vedfolnir_redis',
            'app': 'vedfolnir_app'
        }
        
    def run_export_scripts(self):
        """Run data export scripts"""
        try:
            self.logger.info("Running data export scripts...")
            
            # Export MySQL data
            mysql_export_cmd = [
                'python', 'scripts/migration/export_macos_mysql_data.py',
                '--export-dir', str(self.export_dir)
            ]
            
            result = subprocess.run(mysql_export_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"MySQL export failed: {result.stderr}")
                return False
            
            self.logger.info("MySQL export completed")
            
            # Export Redis data
            redis_export_cmd = [
                'python', 'scripts/migration/export_macos_redis_data.py',
                '--export-dir', str(self.export_dir)
            ]
            
            result = subprocess.run(redis_export_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Redis export failed: {result.stderr}")
                return False
            
            self.logger.info("Redis export completed")
            
            # Migrate configuration
            config_migrate_cmd = [
                'python', 'scripts/migration/migrate_configuration.py',
                '--source', '.env',
                '--target', '.env.docker'
            ]
            
            result = subprocess.run(config_migrate_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Configuration migration failed: {result.stderr}")
                return False
            
            self.logger.info("Configuration migration completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Export scripts failed: {e}")
            return False
    
    def start_docker_environment(self):
        """Start Docker Compose environment"""
        try:
            self.logger.info("Starting Docker Compose environment...")
            
            # Stop any existing containers
            subprocess.run(['docker-compose', 'down'], capture_output=True)
            
            # Start containers
            result = subprocess.run([
                'docker-compose', 'up', '-d'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Docker Compose start failed: {result.stderr}")
                return False
            
            # Wait for containers to be ready
            self.logger.info("Waiting for containers to be ready...")
            time.sleep(30)
            
            # Check container status
            for service, container in self.containers.items():
                result = subprocess.run([
                    'docker', 'ps', '--filter', f'name={container}', '--format', '{{.Status}}'
                ], capture_output=True, text=True)
                
                if 'Up' not in result.stdout:
                    self.logger.error(f"Container {container} is not running")
                    return False
            
            self.logger.info("Docker environment started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Docker environment: {e}")
            return False
    
    def run_import_scripts(self):
        """Run data import scripts"""
        try:
            self.logger.info("Running data import scripts...")
            
            # Find latest export directories
            mysql_exports = list(self.export_dir.glob("mysql_export_*"))
            redis_exports = list(self.export_dir.glob("redis_export_*"))
            
            if not mysql_exports:
                self.logger.error("No MySQL export found")
                return False
            
            if not redis_exports:
                self.logger.error("No Redis export found")
                return False
            
            # Use latest exports
            latest_mysql_export = max(mysql_exports, key=lambda p: p.stat().st_mtime)
            latest_redis_export = max(redis_exports, key=lambda p: p.stat().st_mtime)
            
            # Import MySQL data
            mysql_import_cmd = [
                'python', 'scripts/migration/import_docker_mysql_data.py',
                str(latest_mysql_export),
                '--container', self.containers['mysql']
            ]
            
            result = subprocess.run(mysql_import_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"MySQL import failed: {result.stderr}")
                return False
            
            self.logger.info("MySQL import completed")
            
            # Import Redis data
            redis_import_cmd = [
                'python', 'scripts/migration/import_docker_redis_data.py',
                str(latest_redis_export),
                '--container', self.containers['redis']
            ]
            
            result = subprocess.run(redis_import_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"Redis import failed: {result.stderr}")
                return False
            
            self.logger.info("Redis import completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Import scripts failed: {e}")
            return False
    
    def test_application_functionality(self):
        """Test application functionality after migration"""
        try:
            self.logger.info("Testing application functionality...")
            
            # Wait for application to be ready
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.app_url}/health", timeout=5)
                    if response.status_code == 200:
                        break
                except:
                    pass
                
                time.sleep(2)
            else:
                self.logger.error("Application health check failed")
                return False
            
            # Test basic endpoints
            test_endpoints = [
                ('/', 'GET', 'Landing page'),
                ('/login', 'GET', 'Login page'),
                ('/health', 'GET', 'Health check'),
            ]
            
            test_results = []
            
            for endpoint, method, description in test_endpoints:
                try:
                    if method == 'GET':
                        response = requests.get(f"{self.app_url}{endpoint}", timeout=10)
                    
                    success = response.status_code in [200, 302]
                    test_results.append({
                        'endpoint': endpoint,
                        'method': method,
                        'description': description,
                        'status_code': response.status_code,
                        'success': success
                    })
                    
                    if success:
                        self.logger.info(f"✅ {description}: {response.status_code}")
                    else:
                        self.logger.warning(f"❌ {description}: {response.status_code}")
                        
                except Exception as e:
                    test_results.append({
                        'endpoint': endpoint,
                        'method': method,
                        'description': description,
                        'error': str(e),
                        'success': False
                    })
                    self.logger.warning(f"❌ {description}: {e}")
            
            # Save test results
            results_file = Path(f"functionality_test_results_{self.timestamp}.json")
            with open(results_file, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            success_count = sum(1 for result in test_results if result.get('success', False))
            total_tests = len(test_results)
            
            self.logger.info(f"Functionality tests: {success_count}/{total_tests} passed")
            
            return success_count == total_tests
            
        except Exception as e:
            self.logger.error(f"Application functionality test failed: {e}")
            return False
    
    def test_database_connectivity(self):
        """Test database connectivity and data integrity"""
        try:
            self.logger.info("Testing database connectivity...")
            
            # Test MySQL connectivity
            mysql_test = subprocess.run([
                'docker', 'exec', self.containers['mysql'],
                'mysql', '-u', 'vedfolnir', '-p', 'vedfolnir',
                '-e', 'SELECT COUNT(*) FROM users;'
            ], capture_output=True, text=True)
            
            if mysql_test.returncode != 0:
                self.logger.error("MySQL connectivity test failed")
                return False
            
            self.logger.info("✅ MySQL connectivity test passed")
            
            # Test Redis connectivity
            redis_test = subprocess.run([
                'docker', 'exec', self.containers['redis'],
                'redis-cli', 'ping'
            ], capture_output=True, text=True)
            
            if redis_test.returncode != 0 or 'PONG' not in redis_test.stdout:
                self.logger.error("Redis connectivity test failed")
                return False
            
            self.logger.info("✅ Redis connectivity test passed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database connectivity test failed: {e}")
            return False
    
    def test_external_services(self):
        """Test external service connectivity (Ollama)"""
        try:
            self.logger.info("Testing external service connectivity...")
            
            # Test Ollama connectivity from container
            ollama_test = subprocess.run([
                'docker', 'exec', self.containers['app'],
                'curl', '-f', 'http://host.docker.internal:11434/api/version'
            ], capture_output=True, text=True)
            
            if ollama_test.returncode == 0:
                self.logger.info("✅ Ollama connectivity test passed")
                return True
            else:
                self.logger.warning("⚠️ Ollama connectivity test failed (external service may not be running)")
                return True  # Don't fail migration test for external service
                
        except Exception as e:
            self.logger.warning(f"External service test failed: {e}")
            return True  # Don't fail migration test for external service
    
    def generate_migration_report(self, test_results):
        """Generate comprehensive migration report"""
        try:
            report = {
                'migration_timestamp': self.timestamp,
                'migration_date': datetime.now().isoformat(),
                'test_results': test_results,
                'overall_success': all(test_results.values()),
                'export_location': str(self.export_dir),
                'docker_containers': self.containers,
                'application_url': self.app_url
            }
            
            # Add container status
            container_status = {}
            for service, container in self.containers.items():
                result = subprocess.run([
                    'docker', 'ps', '--filter', f'name={container}',
                    '--format', '{{.Names}}\t{{.Status}}\t{{.Ports}}'
                ], capture_output=True, text=True)
                
                container_status[service] = result.stdout.strip()
            
            report['container_status'] = container_status
            
            # Save report
            report_file = Path(f"migration_report_{self.timestamp}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Migration report generated: {report_file}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration report: {e}")
            return None
    
    def run_complete_test(self):
        """Run complete migration test process"""
        self.logger.info("Starting complete migration test")
        
        test_results = {}
        
        # Step 1: Export data
        test_results['export'] = self.run_export_scripts()
        if not test_results['export']:
            self.logger.error("Export phase failed, stopping test")
            return False
        
        # Step 2: Start Docker environment
        test_results['docker_start'] = self.start_docker_environment()
        if not test_results['docker_start']:
            self.logger.error("Docker start phase failed, stopping test")
            return False
        
        # Step 3: Import data
        test_results['import'] = self.run_import_scripts()
        if not test_results['import']:
            self.logger.error("Import phase failed, stopping test")
            return False
        
        # Step 4: Test application functionality
        test_results['functionality'] = self.test_application_functionality()
        
        # Step 5: Test database connectivity
        test_results['database'] = self.test_database_connectivity()
        
        # Step 6: Test external services
        test_results['external_services'] = self.test_external_services()
        
        # Generate report
        report = self.generate_migration_report(test_results)
        
        # Overall success
        overall_success = all(test_results.values())
        
        if overall_success:
            self.logger.info("🎉 Complete migration test PASSED")
        else:
            self.logger.warning("⚠️ Complete migration test completed with issues")
        
        return overall_success

def main():
    parser = argparse.ArgumentParser(description='Test complete data migration process')
    parser.add_argument('--export-dir', help='Export directory path', default='./migration_exports')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--skip-export', action='store_true', help='Skip export phase (use existing exports)')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = CompleteMigrationTester(args.export_dir)
    
    if args.skip_export:
        tester.logger.info("Skipping export phase as requested")
        # Start from Docker environment
        test_results = {}
        test_results['export'] = True  # Assume export was successful
        
        test_results['docker_start'] = tester.start_docker_environment()
        if test_results['docker_start']:
            test_results['import'] = tester.run_import_scripts()
            test_results['functionality'] = tester.test_application_functionality()
            test_results['database'] = tester.test_database_connectivity()
            test_results['external_services'] = tester.test_external_services()
        
        overall_success = all(test_results.values())
    else:
        overall_success = tester.run_complete_test()
    
    if overall_success:
        print(f"\n✅ Complete migration test PASSED")
        print(f"📁 Export location: {tester.export_dir}")
        print(f"📋 Check log file: migration_test_{tester.timestamp}.log")
    else:
        print(f"\n❌ Complete migration test FAILED")
        print(f"📋 Check log file: migration_test_{tester.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()