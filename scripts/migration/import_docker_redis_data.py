# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Data Import Script for Docker Migration
Imports data from macOS Redis export into containerized Redis
"""

import os
import sys
import subprocess
import json
import logging
import time
from datetime import datetime
from pathlib import Path
import argparse
import redis

class DockerRedisImporter:
    def __init__(self, export_path, container_name="vedfolnir_redis"):
        """Initialize Redis importer for Docker containers"""
        self.export_path = Path(export_path)
        self.container_name = container_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'redis_import_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def validate_export_files(self):
        """Validate that required export files exist"""
        try:
            required_files = [
                self.export_path / "migration_manifest.json",
                self.export_path / "data" / "dump.rdb",
                self.export_path / "data" / "redis_keys.json"
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
        """Check if Redis container is running"""
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
                self.logger.info(f"Redis container '{self.container_name}' is running")
                return True
            else:
                self.logger.error(f"Redis container '{self.container_name}' is not running")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to check Docker container: {e}")
            return False
    
    def get_container_redis_info(self):
        """Get Redis connection info from container"""
        try:
            # Test Redis connection in container
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'redis-cli', 'ping'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error("Redis is not responding in container")
                return None
            
            # Get Redis info
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'redis-cli', 'info', 'server'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("Redis connection verified")
                return {'host': 'localhost', 'port': 6379, 'container': self.container_name}
            else:
                self.logger.error("Failed to get Redis info")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get container Redis info: {e}")
            return None
    
    def backup_existing_data(self):
        """Backup existing Redis data in container"""
        try:
            backup_file = f"/data/pre_import_backup_{self.timestamp}.rdb"
            
            self.logger.info("Creating backup of existing Redis data...")
            
            # Trigger BGSAVE in container
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'redis-cli', 'bgsave'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Wait for BGSAVE to complete
                time.sleep(2)
                
                # Copy current dump to backup
                subprocess.run([
                    'docker', 'exec', self.container_name,
                    'cp', '/data/dump.rdb', backup_file
                ], capture_output=True)
                
                self.logger.info(f"Backup created: {backup_file}")
                return backup_file
            else:
                self.logger.warning("Failed to create backup, continuing with import")
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
            return None
    
    def stop_redis_in_container(self):
        """Stop Redis server in container for dump file replacement"""
        try:
            self.logger.info("Stopping Redis server for dump file replacement...")
            
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'redis-cli', 'shutdown', 'nosave'
            ], capture_output=True, text=True)
            
            # Wait for Redis to stop
            time.sleep(3)
            
            self.logger.info("Redis server stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Redis: {e}")
            return False
    
    def import_redis_dump(self):
        """Import Redis dump file into container"""
        try:
            dump_file = self.export_path / "data" / "dump.rdb"
            
            self.logger.info("Importing Redis dump file...")
            
            # Copy dump file to container
            subprocess.run([
                'docker', 'cp', str(dump_file),
                f'{self.container_name}:/data/dump.rdb'
            ], check=True)
            
            # Set proper permissions
            subprocess.run([
                'docker', 'exec', self.container_name,
                'chown', 'redis:redis', '/data/dump.rdb'
            ], capture_output=True)
            
            self.logger.info("Dump file imported successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import dump file: {e}")
            return False
    
    def start_redis_in_container(self):
        """Start Redis server in container after dump import"""
        try:
            self.logger.info("Starting Redis server...")
            
            # Start Redis server
            subprocess.run([
                'docker', 'exec', '-d', self.container_name,
                'redis-server', '/usr/local/etc/redis/redis.conf'
            ], capture_output=True)
            
            # Wait for Redis to start
            for i in range(30):
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'redis-cli', 'ping'
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and 'PONG' in result.stdout:
                    self.logger.info("Redis server started successfully")
                    return True
                
                time.sleep(1)
            
            self.logger.error("Redis server failed to start within timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start Redis: {e}")
            return False
    
    def validate_imported_data(self):
        """Validate imported Redis data against original statistics"""
        try:
            self.logger.info("Validating imported Redis data...")
            
            # Get original statistics
            original_stats = self.manifest.get('statistics', {})
            original_key_count = original_stats.get('total_keys', 0)
            
            # Get current key count from container
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'redis-cli', 'dbsize'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error("Failed to get current key count")
                return None
            
            current_key_count = int(result.stdout.strip())
            
            # Load original keys for detailed validation
            keys_file = self.export_path / "data" / "redis_keys.json"
            with open(keys_file, 'r') as f:
                original_keys = json.load(f)
            
            # Validate sample keys
            sample_validation = {}
            sample_keys = list(original_keys.keys())[:10]  # Test first 10 keys
            
            for key in sample_keys:
                result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'redis-cli', 'exists', key
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    exists = int(result.stdout.strip()) == 1
                    sample_validation[key] = exists
            
            validation_results = {
                'original_key_count': original_key_count,
                'current_key_count': current_key_count,
                'key_count_match': original_key_count == current_key_count,
                'sample_keys_validated': len(sample_validation),
                'sample_keys_found': sum(sample_validation.values()),
                'validation_passed': True
            }
            
            if not validation_results['key_count_match']:
                validation_results['validation_passed'] = False
                self.logger.warning(f"Key count mismatch: {original_key_count} -> {current_key_count}")
            
            if validation_results['sample_keys_found'] != validation_results['sample_keys_validated']:
                validation_results['validation_passed'] = False
                self.logger.warning("Some sample keys not found in imported data")
            
            # Save validation results
            validation_file = Path(f"redis_import_validation_{self.timestamp}.json")
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            if validation_results['validation_passed']:
                self.logger.info("Redis data validation passed")
            else:
                self.logger.warning("Redis data validation found discrepancies")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Failed to validate imported data: {e}")
            return None
    
    def import_keys_manually(self):
        """Fallback method: Import keys manually from JSON"""
        try:
            self.logger.info("Attempting manual key import from JSON...")
            
            keys_file = self.export_path / "data" / "redis_keys.json"
            with open(keys_file, 'r') as f:
                keys_data = json.load(f)
            
            imported_count = 0
            failed_count = 0
            
            for key, data in keys_data.items():
                try:
                    key_type = data.get('type', 'string')
                    value = data.get('value')
                    ttl = data.get('ttl')
                    
                    if key_type == 'string':
                        cmd = ['redis-cli', 'set', key, str(value)]
                    elif key_type == 'hash':
                        cmd = ['redis-cli', 'hmset', key] + [f'{k}' for item in value.items() for k in item]
                    elif key_type == 'list':
                        cmd = ['redis-cli', 'lpush', key] + [str(v) for v in value]
                    elif key_type == 'set':
                        cmd = ['redis-cli', 'sadd', key] + [str(v) for v in value]
                    else:
                        continue  # Skip unsupported types
                    
                    result = subprocess.run([
                        'docker', 'exec', self.container_name
                    ] + cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        imported_count += 1
                        
                        # Set TTL if specified
                        if ttl and ttl > 0:
                            subprocess.run([
                                'docker', 'exec', self.container_name,
                                'redis-cli', 'expire', key, str(ttl)
                            ], capture_output=True)
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    continue
            
            self.logger.info(f"Manual import completed: {imported_count} keys imported, {failed_count} failed")
            return imported_count > 0
            
        except Exception as e:
            self.logger.error(f"Manual key import failed: {e}")
            return False
    
    def run_import(self):
        """Run complete Redis import process"""
        self.logger.info("Starting Redis data import for Docker migration")
        
        # Validate export files
        if not self.validate_export_files():
            return False
        
        # Check Docker container
        if not self.check_docker_container():
            return False
        
        # Get Redis info
        redis_info = self.get_container_redis_info()
        if not redis_info:
            return False
        
        # Backup existing data
        backup_file = self.backup_existing_data()
        
        # Stop Redis for dump replacement
        if not self.stop_redis_in_container():
            return False
        
        # Import dump file
        if not self.import_redis_dump():
            return False
        
        # Start Redis
        if not self.start_redis_in_container():
            return False
        
        # Validate imported data
        validation_results = self.validate_imported_data()
        if not validation_results:
            return False
        
        # If validation failed, try manual import
        if not validation_results['validation_passed']:
            self.logger.info("Attempting manual key import as fallback...")
            if self.import_keys_manually():
                # Re-validate after manual import
                validation_results = self.validate_imported_data()
        
        self.logger.info(f"Redis import completed")
        
        if backup_file:
            self.logger.info(f"Pre-import backup available: {backup_file}")
        
        if validation_results and not validation_results['validation_passed']:
            self.logger.warning("Import completed with validation warnings")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Import Redis data into Docker container')
    parser.add_argument('export_path', help='Path to Redis export directory')
    parser.add_argument('--container', help='Redis container name', default='vedfolnir_redis')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not Path(args.export_path).exists():
        print(f"❌ Export path does not exist: {args.export_path}")
        sys.exit(1)
    
    importer = DockerRedisImporter(args.export_path, args.container)
    success = importer.run_import()
    
    if success:
        print(f"\n✅ Redis import completed successfully")
        print(f"📋 Check log file: redis_import_{importer.timestamp}.log")
    else:
        print(f"\n❌ Redis import failed")
        print(f"📋 Check log file: redis_import_{importer.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()