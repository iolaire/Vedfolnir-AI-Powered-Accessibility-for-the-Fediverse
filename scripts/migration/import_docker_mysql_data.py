# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
MySQL Data Import Script for Docker Migration
Imports data from macOS MySQL export into containerized MySQL
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
import argparse
import time

class DockerMySQLImporter:
    def __init__(self, export_path, container_name="vedfolnir_mysql"):
        """Initialize MySQL importer for Docker containers"""
        self.export_path = Path(export_path)
        self.container_name = container_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'mysql_import_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def validate_export_files(self):
        """Validate that required export files exist"""
        try:
            required_files = [
                self.export_path / "migration_manifest.json",
                self.export_path / "schema" / "vedfolnir_schema.sql",
                self.export_path / "data" / "vedfolnir_data.sql"
            ]
            
            missing_files = []
            for file_path in required_files:
                if not file_path.exists():
                    missing_files.append(str(file_path))
            
            if missing_files:
                self.logger.error(f"Missing required files: {missing_files}")
                return False
            
            # Load and validate manifest
            with open(self.export_path / "migration_manifest.json", 'r') as f:
                self.manifest = json.load(f)
            
            self.logger.info("Export files validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate export files: {e}")
            return False
    
    def check_docker_container(self):
        """Check if MySQL container is running"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                self.logger.error("Failed to check Docker containers")
                return False
            
            running_containers = result.stdout.strip().split('\n')
            if self.container_name in running_containers:
                self.logger.info(f"MySQL container '{self.container_name}' is running")
                return True
            else:
                self.logger.error(f"MySQL container '{self.container_name}' is not running")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to check Docker container: {e}")
            return False
    
    def get_container_database_info(self):
        """Get database connection info from container environment"""
        try:
            # Get environment variables from container
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'printenv'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error("Failed to get container environment")
                return None
            
            env_vars = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
            
            # Extract database info
            database_info = {
                'database': env_vars.get('MYSQL_DATABASE', 'vedfolnir'),
                'user': env_vars.get('MYSQL_USER', 'vedfolnir'),
                'password': env_vars.get('MYSQL_PASSWORD', ''),
                'root_password': env_vars.get('MYSQL_ROOT_PASSWORD', '')
            }
            
            self.logger.info(f"Container database info extracted: {database_info['database']}")
            return database_info
            
        except Exception as e:
            self.logger.error(f"Failed to get container database info: {e}")
            return None
    
    def wait_for_mysql_ready(self, max_wait=60):
        """Wait for MySQL to be ready in container"""
        try:
            self.logger.info("Waiting for MySQL to be ready...")
            
            for i in range(max_wait):
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'mysqladmin', 'ping', '-h', 'localhost'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info("MySQL is ready")
                    return True
                
                time.sleep(1)
            
            self.logger.error("MySQL did not become ready within timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check MySQL readiness: {e}")
            return False
    
    def backup_existing_data(self, database_info):
        """Backup existing data in container before import"""
        try:
            backup_file = f"/tmp/pre_import_backup_{self.timestamp}.sql"
            
            self.logger.info("Creating backup of existing data...")
            
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'mysqldump',
                f'--user={database_info["user"]}',
                f'--password={database_info["password"]}',
                '--single-transaction',
                '--routines',
                '--triggers',
                database_info['database']
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Save backup inside container
                subprocess.run([
                    'docker', 'exec', '-i', self.container_name,
                    'bash', '-c', f'cat > {backup_file}'
                ], input=result.stdout, text=True)
                
                self.logger.info(f"Backup created: {backup_file}")
                return backup_file
            else:
                self.logger.warning("Failed to create backup, continuing with import")
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
            return None
    
    def import_database_schema(self, database_info):
        """Import database schema into container"""
        try:
            schema_file = self.export_path / "schema" / "vedfolnir_schema.sql"
            
            self.logger.info("Importing database schema...")
            
            # Copy schema file to container
            subprocess.run([
                'docker', 'cp', str(schema_file),
                f'{self.container_name}:/tmp/schema.sql'
            ], check=True)
            
            # Import schema
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'mysql',
                f'--user={database_info["user"]}',
                f'--password={database_info["password"]}',
                database_info['database'],
                '-e', 'source /tmp/schema.sql'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Schema imported successfully")
                return True
            else:
                self.logger.error(f"Schema import failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to import schema: {e}")
            return False
    
    def import_database_data(self, database_info):
        """Import database data into container"""
        try:
            data_file = self.export_path / "data" / "vedfolnir_data.sql"
            
            self.logger.info("Importing database data...")
            
            # Copy data file to container
            subprocess.run([
                'docker', 'cp', str(data_file),
                f'{self.container_name}:/tmp/data.sql'
            ], check=True)
            
            # Import data
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'mysql',
                f'--user={database_info["user"]}',
                f'--password={database_info["password"]}',
                database_info['database'],
                '-e', 'source /tmp/data.sql'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Data imported successfully")
                return True
            else:
                self.logger.error(f"Data import failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to import data: {e}")
            return False
    
    def validate_imported_data(self, database_info):
        """Validate imported data against original statistics"""
        try:
            self.logger.info("Validating imported data...")
            
            # Get original statistics
            original_stats = self.manifest.get('table_statistics', {})
            
            # Get current statistics from container
            current_stats = {}
            
            for table_name in original_stats.keys():
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'mysql',
                    f'--user={database_info["user"]}',
                    f'--password={database_info["password"]}',
                    database_info['database'],
                    '-e', f'SELECT COUNT(*) FROM `{table_name}`;'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parse count from output
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        count = int(lines[1])
                        current_stats[table_name] = {'row_count': count}
            
            # Compare statistics
            validation_results = {
                'tables_validated': len(current_stats),
                'validation_passed': True,
                'discrepancies': []
            }
            
            for table_name, original_data in original_stats.items():
                if table_name in current_stats:
                    original_count = original_data.get('row_count', 0)
                    current_count = current_stats[table_name].get('row_count', 0)
                    
                    if original_count != current_count:
                        discrepancy = {
                            'table': table_name,
                            'original_count': original_count,
                            'current_count': current_count
                        }
                        validation_results['discrepancies'].append(discrepancy)
                        validation_results['validation_passed'] = False
                        self.logger.warning(f"Row count mismatch in {table_name}: {original_count} -> {current_count}")
                else:
                    validation_results['validation_passed'] = False
                    self.logger.warning(f"Table {table_name} not found in imported data")
            
            # Save validation results
            validation_file = Path(f"import_validation_{self.timestamp}.json")
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            if validation_results['validation_passed']:
                self.logger.info("Data validation passed")
            else:
                self.logger.warning("Data validation found discrepancies")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Failed to validate imported data: {e}")
            return None
    
    def cleanup_temp_files(self):
        """Clean up temporary files in container"""
        try:
            subprocess.run([
                'docker', 'exec', self.container_name,
                'rm', '-f', '/tmp/schema.sql', '/tmp/data.sql'
            ], capture_output=True)
            
            self.logger.info("Temporary files cleaned up")
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp files: {e}")
    
    def run_import(self):
        """Run complete MySQL import process"""
        self.logger.info("Starting MySQL data import for Docker migration")
        
        # Validate export files
        if not self.validate_export_files():
            return False
        
        # Check Docker container
        if not self.check_docker_container():
            return False
        
        # Wait for MySQL to be ready
        if not self.wait_for_mysql_ready():
            return False
        
        # Get database info
        database_info = self.get_container_database_info()
        if not database_info:
            return False
        
        # Backup existing data
        backup_file = self.backup_existing_data(database_info)
        
        # Import schema
        if not self.import_database_schema(database_info):
            return False
        
        # Import data
        if not self.import_database_data(database_info):
            return False
        
        # Validate imported data
        validation_results = self.validate_imported_data(database_info)
        if not validation_results:
            return False
        
        # Cleanup
        self.cleanup_temp_files()
        
        self.logger.info(f"MySQL import completed successfully")
        
        if backup_file:
            self.logger.info(f"Pre-import backup available: {backup_file}")
        
        if not validation_results['validation_passed']:
            self.logger.warning("Import completed with validation warnings")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Import MySQL data into Docker container')
    parser.add_argument('export_path', help='Path to MySQL export directory')
    parser.add_argument('--container', help='MySQL container name', default='vedfolnir_mysql')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not Path(args.export_path).exists():
        print(f"❌ Export path does not exist: {args.export_path}")
        sys.exit(1)
    
    importer = DockerMySQLImporter(args.export_path, args.container)
    success = importer.run_import()
    
    if success:
        print(f"\n✅ MySQL import completed successfully")
        print(f"📋 Check log file: mysql_import_{importer.timestamp}.log")
    else:
        print(f"\n❌ MySQL import failed")
        print(f"📋 Check log file: mysql_import_{importer.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()