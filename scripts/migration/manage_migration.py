# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Migration Management Script
Unified interface for managing macOS to Docker migration process
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class MigrationManager:
    def __init__(self):
        """Initialize migration manager"""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'migration_manager_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Migration scripts
        self.scripts = {
            'export_mysql': 'scripts/migration/export_macos_mysql_data.py',
            'export_redis': 'scripts/migration/export_macos_redis_data.py',
            'migrate_config': 'scripts/migration/migrate_configuration.py',
            'import_mysql': 'scripts/migration/import_docker_mysql_data.py',
            'import_redis': 'scripts/migration/import_docker_redis_data.py',
            'test_migration': 'scripts/migration/test_complete_migration.py',
            'rollback': 'scripts/migration/rollback_to_macos.py'
        }
        
    def check_prerequisites(self):
        """Check migration prerequisites"""
        try:
            self.logger.info("Checking migration prerequisites...")
            
            prerequisites = {
                'docker': False,
                'docker_compose': False,
                'mysql_client': False,
                'redis_client': False,
                'python_deps': False
            }
            
            # Check Docker
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            prerequisites['docker'] = result.returncode == 0
            
            # Check Docker Compose
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            prerequisites['docker_compose'] = result.returncode == 0
            
            # Check MySQL client
            result = subprocess.run(['mysql', '--version'], capture_output=True, text=True)
            prerequisites['mysql_client'] = result.returncode == 0
            
            # Check Redis client
            result = subprocess.run(['redis-cli', '--version'], capture_output=True, text=True)
            prerequisites['redis_client'] = result.returncode == 0
            
            # Check Python dependencies
            try:
                import pymysql
                import redis
                import requests
                prerequisites['python_deps'] = True
            except ImportError:
                prerequisites['python_deps'] = False
            
            # Report results
            for prereq, status in prerequisites.items():
                status_icon = "✅" if status else "❌"
                self.logger.info(f"{status_icon} {prereq}: {'OK' if status else 'MISSING'}")
            
            all_met = all(prerequisites.values())
            
            if not all_met:
                self.logger.error("Some prerequisites are missing. Please install required tools.")
                return False
            
            self.logger.info("All prerequisites met")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check prerequisites: {e}")
            return False
    
    def run_export_phase(self, export_dir="./migration_exports"):
        """Run data export phase"""
        try:
            self.logger.info("Starting export phase...")
            
            # Export MySQL data
            mysql_cmd = ['python', self.scripts['export_mysql'], '--export-dir', export_dir]
            result = subprocess.run(mysql_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"MySQL export failed: {result.stderr}")
                return False
            
            self.logger.info("MySQL export completed")
            
            # Export Redis data
            redis_cmd = ['python', self.scripts['export_redis'], '--export-dir', export_dir]
            result = subprocess.run(redis_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Redis export failed: {result.stderr}")
                return False
            
            self.logger.info("Redis export completed")
            
            # Migrate configuration
            config_cmd = ['python', self.scripts['migrate_config']]
            result = subprocess.run(config_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Configuration migration failed: {result.stderr}")
                return False
            
            self.logger.info("Configuration migration completed")
            
            self.logger.info("Export phase completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Export phase failed: {e}")
            return False
    
    def run_import_phase(self, export_dir="./migration_exports"):
        """Run data import phase"""
        try:
            self.logger.info("Starting import phase...")
            
            # Find latest export directories
            export_path = Path(export_dir)
            mysql_exports = list(export_path.glob("mysql_export_*"))
            redis_exports = list(export_path.glob("redis_export_*"))
            
            if not mysql_exports or not redis_exports:
                self.logger.error("Export directories not found. Run export phase first.")
                return False
            
            latest_mysql = max(mysql_exports, key=lambda p: p.stat().st_mtime)
            latest_redis = max(redis_exports, key=lambda p: p.stat().st_mtime)
            
            # Import MySQL data
            mysql_cmd = ['python', self.scripts['import_mysql'], str(latest_mysql)]
            result = subprocess.run(mysql_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"MySQL import failed: {result.stderr}")
                return False
            
            self.logger.info("MySQL import completed")
            
            # Import Redis data
            redis_cmd = ['python', self.scripts['import_redis'], str(latest_redis)]
            result = subprocess.run(redis_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Redis import failed: {result.stderr}")
                return False
            
            self.logger.info("Redis import completed")
            
            self.logger.info("Import phase completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Import phase failed: {e}")
            return False
    
    def run_test_phase(self, export_dir="./migration_exports"):
        """Run migration testing phase"""
        try:
            self.logger.info("Starting test phase...")
            
            test_cmd = ['python', self.scripts['test_migration'], '--export-dir', export_dir, '--skip-export']
            result = subprocess.run(test_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Migration test failed: {result.stderr}")
                return False
            
            self.logger.info("Migration test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Test phase failed: {e}")
            return False
    
    def run_rollback(self):
        """Run rollback to macOS"""
        try:
            self.logger.info("Starting rollback to macOS...")
            
            rollback_cmd = ['python', self.scripts['rollback'], '--confirm']
            result = subprocess.run(rollback_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Rollback failed: {result.stderr}")
                return False
            
            self.logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def show_status(self):
        """Show migration status"""
        try:
            self.logger.info("Checking migration status...")
            
            status = {
                'export_exists': False,
                'docker_running': False,
                'macos_services': False,
                'config_files': {}
            }
            
            # Check for export directories
            export_dirs = list(Path('./migration_exports').glob("*_export_*"))
            status['export_exists'] = len(export_dirs) > 0
            
            # Check Docker containers
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
            if result.returncode == 0:
                running_containers = result.stdout.strip().split('\n')
                vedfolnir_containers = [c for c in running_containers if 'vedfolnir' in c]
                status['docker_running'] = len(vedfolnir_containers) > 0
            
            # Check macOS services
            result = subprocess.run(['brew', 'services', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                status['macos_services'] = 'started' in result.stdout
            
            # Check configuration files
            config_files = ['.env', '.env.docker', '.env.docker-compose', 'docker-compose.yml']
            for config_file in config_files:
                status['config_files'][config_file] = Path(config_file).exists()
            
            # Display status
            print("\n📊 Migration Status Report")
            print("=" * 50)
            
            export_icon = "✅" if status['export_exists'] else "❌"
            print(f"{export_icon} Export data: {'Available' if status['export_exists'] else 'Not found'}")
            
            docker_icon = "✅" if status['docker_running'] else "❌"
            print(f"{docker_icon} Docker containers: {'Running' if status['docker_running'] else 'Not running'}")
            
            macos_icon = "✅" if status['macos_services'] else "❌"
            print(f"{macos_icon} macOS services: {'Running' if status['macos_services'] else 'Not running'}")
            
            print("\n📁 Configuration Files:")
            for config_file, exists in status['config_files'].items():
                file_icon = "✅" if exists else "❌"
                print(f"  {file_icon} {config_file}")
            
            # Determine current deployment type
            if status['docker_running']:
                print("\n🐳 Current deployment: Docker Compose")
            elif status['macos_services']:
                print("\n🍎 Current deployment: macOS")
            else:
                print("\n❓ Current deployment: Unknown/Stopped")
            
            print("=" * 50)
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to check status: {e}")
            return None
    
    def interactive_migration(self):
        """Interactive migration wizard"""
        try:
            print("\n🚀 Vedfolnir Migration Wizard")
            print("=" * 50)
            
            # Check prerequisites
            if not self.check_prerequisites():
                print("❌ Prerequisites not met. Please install required tools.")
                return False
            
            # Show current status
            status = self.show_status()
            if not status:
                return False
            
            print("\n📋 Migration Options:")
            print("1. Full migration (export + import + test)")
            print("2. Export data only")
            print("3. Import data only")
            print("4. Test migration")
            print("5. Rollback to macOS")
            print("6. Show status")
            print("0. Exit")
            
            choice = input("\nSelect option (0-6): ").strip()
            
            if choice == '1':
                return self.run_full_migration()
            elif choice == '2':
                return self.run_export_phase()
            elif choice == '3':
                return self.run_import_phase()
            elif choice == '4':
                return self.run_test_phase()
            elif choice == '5':
                confirm = input("⚠️  Confirm rollback to macOS? (yes/no): ")
                if confirm.lower() == 'yes':
                    return self.run_rollback()
                else:
                    print("Rollback cancelled")
                    return True
            elif choice == '6':
                self.show_status()
                return True
            elif choice == '0':
                print("Migration wizard exited")
                return True
            else:
                print("Invalid option")
                return False
                
        except Exception as e:
            self.logger.error(f"Interactive migration failed: {e}")
            return False
    
    def run_full_migration(self, export_dir="./migration_exports"):
        """Run complete migration process"""
        try:
            self.logger.info("Starting full migration process...")
            
            # Phase 1: Export
            if not self.run_export_phase(export_dir):
                return False
            
            # Phase 2: Import
            if not self.run_import_phase(export_dir):
                return False
            
            # Phase 3: Test
            if not self.run_test_phase(export_dir):
                return False
            
            self.logger.info("🎉 Full migration completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Full migration failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Manage macOS to Docker migration')
    parser.add_argument('--action', choices=['export', 'import', 'test', 'rollback', 'status', 'full'], 
                       help='Migration action to perform')
    parser.add_argument('--export-dir', help='Export directory path', default='./migration_exports')
    parser.add_argument('--interactive', '-i', action='store_true', help='Run interactive wizard')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = MigrationManager()
    
    if args.interactive:
        success = manager.interactive_migration()
    elif args.action == 'export':
        success = manager.run_export_phase(args.export_dir)
    elif args.action == 'import':
        success = manager.run_import_phase(args.export_dir)
    elif args.action == 'test':
        success = manager.run_test_phase(args.export_dir)
    elif args.action == 'rollback':
        success = manager.run_rollback()
    elif args.action == 'status':
        success = manager.show_status() is not None
    elif args.action == 'full':
        success = manager.run_full_migration(args.export_dir)
    else:
        # Default to interactive mode
        success = manager.interactive_migration()
    
    if success:
        print(f"\n✅ Migration management completed successfully")
        print(f"📋 Check log file: migration_manager_{manager.timestamp}.log")
    else:
        print(f"\n❌ Migration management failed")
        print(f"📋 Check log file: migration_manager_{manager.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()