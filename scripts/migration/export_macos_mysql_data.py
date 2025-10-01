# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
MySQL Data Export Script for macOS to Docker Migration
Exports data from current macOS MySQL instance for containerized deployment
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
import argparse
import getpass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config

class MacOSMySQLExporter:
    def __init__(self, export_dir=None):
        """Initialize MySQL exporter for macOS data"""
        self.config = Config()
        self.export_dir = Path(export_dir) if export_dir else Path("./migration_exports")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.export_path = self.export_dir / f"mysql_export_{self.timestamp}"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'mysql_export_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_export_directory(self):
        """Create export directory structure"""
        try:
            self.export_path.mkdir(parents=True, exist_ok=True)
            (self.export_path / "data").mkdir(exist_ok=True)
            (self.export_path / "schema").mkdir(exist_ok=True)
            (self.export_path / "validation").mkdir(exist_ok=True)
            
            self.logger.info(f"Created export directory: {self.export_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create export directory: {e}")
            return False
    
    def get_database_connection_info(self):
        """Extract database connection info from config"""
        try:
            db_url = self.config.DATABASE_URL
            if not db_url:
                raise ValueError("DATABASE_URL not found in configuration")
            
            # Parse MySQL URL: mysql+pymysql://user:password@host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(db_url)
            
            connection_info = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 3306,
                'username': parsed.username,
                'password': parsed.password,
                'database': parsed.path.lstrip('/'),
                'charset': 'utf8mb4'
            }
            
            self.logger.info(f"Database connection info extracted for: {connection_info['database']}")
            return connection_info
        except Exception as e:
            self.logger.error(f"Failed to parse database connection: {e}")
            return None
    
    def export_database_schema(self, connection_info):
        """Export database schema without data"""
        try:
            schema_file = self.export_path / "schema" / "vedfolnir_schema.sql"
            
            cmd = [
                'mysqldump',
                f'--host={connection_info["host"]}',
                f'--port={connection_info["port"]}',
                f'--user={connection_info["username"]}',
                f'--password={connection_info["password"]}',
                '--no-data',
                '--routines',
                '--triggers',
                '--single-transaction',
                '--lock-tables=false',
                '--add-drop-table',
                '--default-character-set=utf8mb4',
                connection_info['database']
            ]
            
            self.logger.info("Exporting database schema...")
            with open(schema_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Schema exported successfully to: {schema_file}")
                return True
            else:
                self.logger.error(f"Schema export failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to export schema: {e}")
            return False
    
    def export_database_data(self, connection_info):
        """Export database data with proper handling of large tables"""
        try:
            data_file = self.export_path / "data" / "vedfolnir_data.sql"
            
            cmd = [
                'mysqldump',
                f'--host={connection_info["host"]}',
                f'--port={connection_info["port"]}',
                f'--user={connection_info["username"]}',
                f'--password={connection_info["password"]}',
                '--no-create-info',
                '--single-transaction',
                '--lock-tables=false',
                '--quick',
                '--extended-insert',
                '--default-character-set=utf8mb4',
                '--hex-blob',
                connection_info['database']
            ]
            
            self.logger.info("Exporting database data...")
            with open(data_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Data exported successfully to: {data_file}")
                return True
            else:
                self.logger.error(f"Data export failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to export data: {e}")
            return False
    
    def export_table_statistics(self, connection_info):
        """Export table statistics for validation"""
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=connection_info['host'],
                port=connection_info['port'],
                user=connection_info['username'],
                password=connection_info['password'],
                database=connection_info['database'],
                charset='utf8mb4'
            )
            
            stats = {}
            with connection.cursor() as cursor:
                # Get table list
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    count = cursor.fetchone()[0]
                    stats[table] = {'row_count': count}
                    
                    # Get table size
                    cursor.execute(f"""
                        SELECT 
                            ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'size_mb'
                        FROM information_schema.TABLES 
                        WHERE table_schema = '{connection_info['database']}' 
                        AND table_name = '{table}'
                    """)
                    size_result = cursor.fetchone()
                    if size_result:
                        stats[table]['size_mb'] = size_result[0]
            
            connection.close()
            
            # Save statistics
            stats_file = self.export_path / "validation" / "table_statistics.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            self.logger.info(f"Table statistics exported to: {stats_file}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to export table statistics: {e}")
            return None
    
    def create_migration_manifest(self, connection_info, stats):
        """Create migration manifest with export details"""
        try:
            manifest = {
                'export_timestamp': self.timestamp,
                'export_date': datetime.now().isoformat(),
                'source_database': {
                    'host': connection_info['host'],
                    'port': connection_info['port'],
                    'database': connection_info['database'],
                    'charset': connection_info['charset']
                },
                'export_files': {
                    'schema': 'schema/vedfolnir_schema.sql',
                    'data': 'data/vedfolnir_data.sql',
                    'statistics': 'validation/table_statistics.json'
                },
                'table_statistics': stats,
                'export_method': 'mysqldump',
                'migration_version': '1.0'
            }
            
            manifest_file = self.export_path / "migration_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            
            self.logger.info(f"Migration manifest created: {manifest_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create migration manifest: {e}")
            return False
    
    def validate_export(self):
        """Validate exported files"""
        try:
            schema_file = self.export_path / "schema" / "vedfolnir_schema.sql"
            data_file = self.export_path / "data" / "vedfolnir_data.sql"
            manifest_file = self.export_path / "migration_manifest.json"
            
            validation_results = {
                'schema_file_exists': schema_file.exists(),
                'data_file_exists': data_file.exists(),
                'manifest_file_exists': manifest_file.exists(),
                'schema_file_size': schema_file.stat().st_size if schema_file.exists() else 0,
                'data_file_size': data_file.stat().st_size if data_file.exists() else 0
            }
            
            # Check for basic SQL content
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    schema_content = f.read()
                    validation_results['schema_has_tables'] = 'CREATE TABLE' in schema_content
            
            if data_file.exists():
                with open(data_file, 'r') as f:
                    data_content = f.read(1000)  # Read first 1000 chars
                    validation_results['data_has_inserts'] = 'INSERT INTO' in data_content
            
            # Save validation results
            validation_file = self.export_path / "validation" / "export_validation.json"
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            all_valid = all([
                validation_results['schema_file_exists'],
                validation_results['data_file_exists'],
                validation_results['manifest_file_exists'],
                validation_results['schema_file_size'] > 0,
                validation_results['data_file_size'] > 0
            ])
            
            if all_valid:
                self.logger.info("Export validation passed")
            else:
                self.logger.warning("Export validation issues detected")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Export validation failed: {e}")
            return None
    
    def run_export(self):
        """Run complete MySQL export process"""
        self.logger.info("Starting MySQL data export for Docker migration")
        
        # Create export directory
        if not self.create_export_directory():
            return False
        
        # Get database connection info
        connection_info = self.get_database_connection_info()
        if not connection_info:
            return False
        
        # Prompt for password if not in config
        if not connection_info['password']:
            connection_info['password'] = getpass.getpass("Enter MySQL password: ")
        
        # Export schema
        if not self.export_database_schema(connection_info):
            return False
        
        # Export data
        if not self.export_database_data(connection_info):
            return False
        
        # Export statistics
        stats = self.export_table_statistics(connection_info)
        if not stats:
            return False
        
        # Create manifest
        if not self.create_migration_manifest(connection_info, stats):
            return False
        
        # Validate export
        validation_results = self.validate_export()
        if not validation_results:
            return False
        
        self.logger.info(f"MySQL export completed successfully")
        self.logger.info(f"Export location: {self.export_path}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Export macOS MySQL data for Docker migration')
    parser.add_argument('--export-dir', help='Export directory path', default='./migration_exports')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    exporter = MacOSMySQLExporter(args.export_dir)
    success = exporter.run_export()
    
    if success:
        print(f"\n✅ MySQL export completed successfully")
        print(f"📁 Export location: {exporter.export_path}")
        print(f"📋 Next step: Run import script on Docker environment")
    else:
        print(f"\n❌ MySQL export failed")
        print(f"📋 Check log file: mysql_export_{exporter.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()