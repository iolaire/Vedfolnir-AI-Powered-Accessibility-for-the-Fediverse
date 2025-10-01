# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Rollback to macOS Deployment Script
Provides procedures to revert from Docker Compose back to macOS deployment
"""

import os
import sys
import subprocess
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
import argparse
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class MacOSRollbackManager:
    def __init__(self, backup_dir="./migration_backups"):
        """Initialize rollback manager"""
        self.backup_dir = Path(backup_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'rollback_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Docker containers to stop
        self.containers = {
            'mysql': 'vedfolnir_mysql',
            'redis': 'vedfolnir_redis',
            'app': 'vedfolnir_app',
            'nginx': 'vedfolnir_nginx'
        }
        
        # macOS services to restart
        self.macos_services = [
            'mysql',
            'redis',
            'nginx'
        ]
        
    def create_rollback_backup(self):
        """Create backup of current Docker data before rollback"""
        try:
            self.logger.info("Creating rollback backup of Docker data...")
            
            rollback_backup_dir = self.backup_dir / f"rollback_backup_{self.timestamp}"
            rollback_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup Docker volumes
            docker_volumes = [
                './data/mysql',
                './data/redis',
                './storage',
                './logs',
                './config'
            ]
            
            for volume_path in docker_volumes:
                volume = Path(volume_path)
                if volume.exists():
                    backup_path = rollback_backup_dir / volume.name
                    if volume.is_dir():
                        shutil.copytree(volume, backup_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(volume, backup_path)
                    
                    self.logger.info(f"Backed up {volume} to {backup_path}")
            
            # Backup Docker configuration files
            config_files = [
                '.env.docker',
                '.env.docker-compose',
                'docker-compose.yml',
                'docker-compose.prod.yml',
                'docker-compose.dev.yml'
            ]
            
            for config_file in config_files:
                config_path = Path(config_file)
                if config_path.exists():
                    backup_path = rollback_backup_dir / config_file
                    shutil.copy2(config_path, backup_path)
                    self.logger.info(f"Backed up {config_file}")
            
            self.logger.info(f"Rollback backup created: {rollback_backup_dir}")
            return rollback_backup_dir
            
        except Exception as e:
            self.logger.error(f"Failed to create rollback backup: {e}")
            return None
    
    def stop_docker_environment(self):
        """Stop Docker Compose environment"""
        try:
            self.logger.info("Stopping Docker Compose environment...")
            
            # Stop all containers
            result = subprocess.run([
                'docker-compose', 'down', '-v'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.warning(f"Docker Compose down warning: {result.stderr}")
            
            # Force stop individual containers if needed
            for service, container in self.containers.items():
                result = subprocess.run([
                    'docker', 'stop', container
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info(f"Stopped container: {container}")
            
            # Remove containers
            for service, container in self.containers.items():
                result = subprocess.run([
                    'docker', 'rm', container
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info(f"Removed container: {container}")
            
            self.logger.info("Docker environment stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Docker environment: {e}")
            return False
    
    def restore_macos_configuration(self):
        """Restore macOS configuration files"""
        try:
            self.logger.info("Restoring macOS configuration...")
            
            # Restore original .env file
            env_backups = list(Path('.').glob('.env.backup_*'))
            if env_backups:
                latest_backup = max(env_backups, key=lambda p: p.stat().st_mtime)
                shutil.copy2(latest_backup, '.env')
                self.logger.info(f"Restored .env from {latest_backup}")
            else:
                self.logger.warning("No .env backup found, manual configuration may be needed")
            
            # Remove Docker-specific configuration files
            docker_configs = [
                '.env.docker',
                '.env.docker-compose'
            ]
            
            for config_file in docker_configs:
                config_path = Path(config_file)
                if config_path.exists():
                    config_path.unlink()
                    self.logger.info(f"Removed Docker config: {config_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore macOS configuration: {e}")
            return False
    
    def check_macos_services(self):
        """Check status of macOS services"""
        try:
            self.logger.info("Checking macOS services...")
            
            service_status = {}
            
            # Check Homebrew services
            result = subprocess.run([
                'brew', 'services', 'list'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    for service in self.macos_services:
                        if service in line:
                            status = 'started' if 'started' in line else 'stopped'
                            service_status[service] = status
                            self.logger.info(f"Service {service}: {status}")
            
            return service_status
            
        except Exception as e:
            self.logger.error(f"Failed to check macOS services: {e}")
            return {}
    
    def start_macos_services(self):
        """Start required macOS services"""
        try:
            self.logger.info("Starting macOS services...")
            
            services_to_start = []
            service_status = self.check_macos_services()
            
            for service in self.macos_services:
                if service_status.get(service) != 'started':
                    services_to_start.append(service)
            
            for service in services_to_start:
                self.logger.info(f"Starting {service}...")
                result = subprocess.run([
                    'brew', 'services', 'start', service
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info(f"✅ Started {service}")
                else:
                    self.logger.warning(f"⚠️ Failed to start {service}: {result.stderr}")
            
            # Wait for services to be ready
            time.sleep(10)
            
            # Verify services are running
            final_status = self.check_macos_services()
            all_running = all(final_status.get(service) == 'started' for service in self.macos_services)
            
            if all_running:
                self.logger.info("All macOS services started successfully")
            else:
                self.logger.warning("Some macOS services may not have started properly")
            
            return all_running
            
        except Exception as e:
            self.logger.error(f"Failed to start macOS services: {e}")
            return False
    
    def restore_database_data(self, mysql_backup_path=None):
        """Restore database data from backup if provided"""
        try:
            if not mysql_backup_path:
                self.logger.info("No MySQL backup path provided, skipping database restore")
                return True
            
            backup_path = Path(mysql_backup_path)
            if not backup_path.exists():
                self.logger.error(f"MySQL backup not found: {backup_path}")
                return False
            
            self.logger.info("Restoring MySQL database from backup...")
            
            # Find SQL backup file
            sql_files = list(backup_path.glob("**/*.sql"))
            if not sql_files:
                self.logger.error("No SQL backup files found")
                return False
            
            data_file = None
            for sql_file in sql_files:
                if 'data' in sql_file.name:
                    data_file = sql_file
                    break
            
            if not data_file:
                data_file = sql_files[0]  # Use first SQL file found
            
            # Restore database
            result = subprocess.run([
                'mysql', '-u', 'root', '-p', 'vedfolnir'
            ], input=data_file.read_text(), text=True, capture_output=True)
            
            if result.returncode == 0:
                self.logger.info("Database restored successfully")
                return True
            else:
                self.logger.error(f"Database restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to restore database: {e}")
            return False
    
    def restore_redis_data(self, redis_backup_path=None):
        """Restore Redis data from backup if provided"""
        try:
            if not redis_backup_path:
                self.logger.info("No Redis backup path provided, skipping Redis restore")
                return True
            
            backup_path = Path(redis_backup_path)
            if not backup_path.exists():
                self.logger.error(f"Redis backup not found: {backup_path}")
                return False
            
            self.logger.info("Restoring Redis data from backup...")
            
            # Find dump.rdb file
            dump_files = list(backup_path.glob("**/dump.rdb"))
            if not dump_files:
                self.logger.error("No Redis dump file found")
                return False
            
            dump_file = dump_files[0]
            
            # Find Redis data directory
            redis_data_dirs = [
                '/usr/local/var/db/redis/',
                '/opt/homebrew/var/db/redis/',
                '/var/db/redis/'
            ]
            
            redis_dir = None
            for data_dir in redis_data_dirs:
                if Path(data_dir).exists():
                    redis_dir = Path(data_dir)
                    break
            
            if not redis_dir:
                self.logger.error("Could not find Redis data directory")
                return False
            
            # Stop Redis, copy dump file, start Redis
            subprocess.run(['brew', 'services', 'stop', 'redis'], capture_output=True)
            time.sleep(2)
            
            shutil.copy2(dump_file, redis_dir / 'dump.rdb')
            self.logger.info(f"Copied Redis dump to {redis_dir}")
            
            subprocess.run(['brew', 'services', 'start', 'redis'], capture_output=True)
            time.sleep(5)
            
            self.logger.info("Redis data restored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore Redis data: {e}")
            return False
    
    def test_macos_deployment(self):
        """Test macOS deployment functionality"""
        try:
            self.logger.info("Testing macOS deployment...")
            
            # Test database connectivity
            result = subprocess.run([
                'mysql', '-u', 'vedfolnir', '-p', 'vedfolnir',
                '-e', 'SELECT 1;'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("✅ MySQL connectivity test passed")
            else:
                self.logger.warning("❌ MySQL connectivity test failed")
                return False
            
            # Test Redis connectivity
            result = subprocess.run([
                'redis-cli', 'ping'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and 'PONG' in result.stdout:
                self.logger.info("✅ Redis connectivity test passed")
            else:
                self.logger.warning("❌ Redis connectivity test failed")
                return False
            
            # Test application startup (non-blocking)
            self.logger.info("Testing application startup...")
            app_process = subprocess.Popen([
                'python', 'web_app.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a bit for startup
            time.sleep(10)
            
            # Check if process is still running
            if app_process.poll() is None:
                self.logger.info("✅ Application started successfully")
                app_process.terminate()
                app_process.wait()
                return True
            else:
                self.logger.warning("❌ Application failed to start")
                return False
                
        except Exception as e:
            self.logger.error(f"macOS deployment test failed: {e}")
            return False
    
    def generate_rollback_report(self, rollback_results):
        """Generate rollback report"""
        try:
            report = {
                'rollback_timestamp': self.timestamp,
                'rollback_date': datetime.now().isoformat(),
                'rollback_results': rollback_results,
                'overall_success': all(rollback_results.values()),
                'backup_location': str(self.backup_dir),
                'services_status': self.check_macos_services()
            }
            
            # Save report
            report_file = Path(f"rollback_report_{self.timestamp}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Rollback report generated: {report_file}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate rollback report: {e}")
            return None
    
    def run_rollback(self, mysql_backup=None, redis_backup=None):
        """Run complete rollback process"""
        self.logger.info("Starting rollback to macOS deployment")
        
        rollback_results = {}
        
        # Step 1: Create rollback backup
        rollback_backup_dir = self.create_rollback_backup()
        rollback_results['backup_created'] = rollback_backup_dir is not None
        
        # Step 2: Stop Docker environment
        rollback_results['docker_stopped'] = self.stop_docker_environment()
        
        # Step 3: Restore macOS configuration
        rollback_results['config_restored'] = self.restore_macos_configuration()
        
        # Step 4: Start macOS services
        rollback_results['services_started'] = self.start_macos_services()
        
        # Step 5: Restore database data (optional)
        rollback_results['database_restored'] = self.restore_database_data(mysql_backup)
        
        # Step 6: Restore Redis data (optional)
        rollback_results['redis_restored'] = self.restore_redis_data(redis_backup)
        
        # Step 7: Test macOS deployment
        rollback_results['deployment_tested'] = self.test_macos_deployment()
        
        # Generate report
        report = self.generate_rollback_report(rollback_results)
        
        # Overall success
        overall_success = all(rollback_results.values())
        
        if overall_success:
            self.logger.info("🎉 Rollback to macOS deployment COMPLETED successfully")
        else:
            self.logger.warning("⚠️ Rollback completed with issues")
        
        return overall_success

def main():
    parser = argparse.ArgumentParser(description='Rollback from Docker to macOS deployment')
    parser.add_argument('--backup-dir', help='Backup directory path', default='./migration_backups')
    parser.add_argument('--mysql-backup', help='Path to MySQL backup for restore')
    parser.add_argument('--redis-backup', help='Path to Redis backup for restore')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--confirm', action='store_true', help='Confirm rollback without prompt')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Confirmation prompt
    if not args.confirm:
        print("⚠️  WARNING: This will stop Docker containers and revert to macOS deployment")
        print("⚠️  Make sure you have backups of any important data")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Rollback cancelled")
            sys.exit(0)
    
    rollback_manager = MacOSRollbackManager(args.backup_dir)
    success = rollback_manager.run_rollback(args.mysql_backup, args.redis_backup)
    
    if success:
        print(f"\n✅ Rollback to macOS deployment COMPLETED successfully")
        print(f"📋 Check log file: rollback_{rollback_manager.timestamp}.log")
        print(f"📁 Rollback backup: {rollback_manager.backup_dir}")
    else:
        print(f"\n❌ Rollback completed with issues")
        print(f"📋 Check log file: rollback_{rollback_manager.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()