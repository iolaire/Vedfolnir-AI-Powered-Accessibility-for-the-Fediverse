# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Redis Data Export Script for macOS to Docker Migration
Exports data from current macOS Redis instance for containerized deployment
"""

import os
import sys
import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import argparse
import redis

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config

class MacOSRedisExporter:
    def __init__(self, export_dir=None):
        """Initialize Redis exporter for macOS data"""
        self.config = Config()
        self.export_dir = Path(export_dir) if export_dir else Path("./migration_exports")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.export_path = self.export_dir / f"redis_export_{self.timestamp}"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'redis_export_{self.timestamp}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_export_directory(self):
        """Create export directory structure"""
        try:
            self.export_path.mkdir(parents=True, exist_ok=True)
            (self.export_path / "data").mkdir(exist_ok=True)
            (self.export_path / "config").mkdir(exist_ok=True)
            (self.export_path / "validation").mkdir(exist_ok=True)
            
            self.logger.info(f"Created export directory: {self.export_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create export directory: {e}")
            return False
    
    def get_redis_connection_info(self):
        """Extract Redis connection info from config"""
        try:
            redis_url = getattr(self.config, 'REDIS_URL', 'redis://localhost:6379/0')
            
            # Parse Redis URL: redis://[:password@]host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(redis_url)
            
            connection_info = {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 6379,
                'password': parsed.password,
                'database': int(parsed.path.lstrip('/')) if parsed.path else 0,
                'url': redis_url
            }
            
            self.logger.info(f"Redis connection info extracted for: {connection_info['host']}:{connection_info['port']}")
            return connection_info
        except Exception as e:
            self.logger.error(f"Failed to parse Redis connection: {e}")
            return None
    
    def connect_to_redis(self, connection_info):
        """Create Redis connection"""
        try:
            r = redis.Redis(
                host=connection_info['host'],
                port=connection_info['port'],
                password=connection_info['password'],
                db=connection_info['database'],
                decode_responses=False  # Keep binary data intact
            )
            
            # Test connection
            r.ping()
            self.logger.info("Redis connection established")
            return r
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return None
    
    def export_redis_dump(self, connection_info):
        """Export Redis data using BGSAVE and copy dump.rdb"""
        try:
            r = self.connect_to_redis(connection_info)
            if not r:
                return False
            
            # Trigger background save
            self.logger.info("Triggering Redis BGSAVE...")
            r.bgsave()
            
            # Wait for BGSAVE to complete
            import time
            while True:
                try:
                    last_save = r.lastsave()
                    time.sleep(1)
                    current_save = r.lastsave()
                    if current_save > last_save:
                        break
                except:
                    time.sleep(1)
                    continue
            
            self.logger.info("BGSAVE completed")
            
            # Find Redis data directory
            redis_info = r.info('persistence')
            redis_dir = redis_info.get('rdb_last_save_time', None)
            
            # Common Redis data locations on macOS
            possible_locations = [
                '/usr/local/var/db/redis/dump.rdb',
                '/opt/homebrew/var/db/redis/dump.rdb',
                '/var/db/redis/dump.rdb',
                './dump.rdb'
            ]
            
            dump_source = None
            for location in possible_locations:
                if Path(location).exists():
                    dump_source = Path(location)
                    break
            
            if not dump_source:
                # Try to get Redis config dir
                try:
                    config_info = r.config_get('dir')
                    if config_info and 'dir' in config_info:
                        redis_dir = config_info['dir']
                        dump_source = Path(redis_dir) / 'dump.rdb'
                except:
                    pass
            
            if not dump_source or not dump_source.exists():
                self.logger.error("Could not locate Redis dump.rdb file")
                return False
            
            # Copy dump file
            dump_dest = self.export_path / "data" / "dump.rdb"
            shutil.copy2(dump_source, dump_dest)
            
            self.logger.info(f"Redis dump exported to: {dump_dest}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export Redis dump: {e}")
            return False
    
    def export_redis_keys_json(self, connection_info):
        """Export Redis keys as JSON for validation and backup"""
        try:
            r = self.connect_to_redis(connection_info)
            if not r:
                return False
            
            keys_data = {}
            all_keys = r.keys('*')
            
            self.logger.info(f"Exporting {len(all_keys)} Redis keys...")
            
            for key in all_keys:
                try:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                    key_type = r.type(key).decode('utf-8')
                    
                    if key_type == 'string':
                        value = r.get(key)
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8')
                            except:
                                value = f"<binary data: {len(value)} bytes>"
                        keys_data[key_str] = {'type': 'string', 'value': value}
                        
                    elif key_type == 'hash':
                        hash_data = r.hgetall(key)
                        decoded_hash = {}
                        for k, v in hash_data.items():
                            k_str = k.decode('utf-8') if isinstance(k, bytes) else str(k)
                            try:
                                v_str = v.decode('utf-8') if isinstance(v, bytes) else str(v)
                            except:
                                v_str = f"<binary data: {len(v)} bytes>"
                            decoded_hash[k_str] = v_str
                        keys_data[key_str] = {'type': 'hash', 'value': decoded_hash}
                        
                    elif key_type == 'list':
                        list_data = r.lrange(key, 0, -1)
                        decoded_list = []
                        for item in list_data:
                            try:
                                item_str = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                            except:
                                item_str = f"<binary data: {len(item)} bytes>"
                            decoded_list.append(item_str)
                        keys_data[key_str] = {'type': 'list', 'value': decoded_list}
                        
                    elif key_type == 'set':
                        set_data = r.smembers(key)
                        decoded_set = []
                        for item in set_data:
                            try:
                                item_str = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                            except:
                                item_str = f"<binary data: {len(item)} bytes>"
                            decoded_set.append(item_str)
                        keys_data[key_str] = {'type': 'set', 'value': decoded_set}
                        
                    elif key_type == 'zset':
                        zset_data = r.zrange(key, 0, -1, withscores=True)
                        decoded_zset = []
                        for member, score in zset_data:
                            try:
                                member_str = member.decode('utf-8') if isinstance(member, bytes) else str(member)
                            except:
                                member_str = f"<binary data: {len(member)} bytes>"
                            decoded_zset.append([member_str, score])
                        keys_data[key_str] = {'type': 'zset', 'value': decoded_zset}
                    
                    # Add TTL info
                    ttl = r.ttl(key)
                    if ttl > 0:
                        keys_data[key_str]['ttl'] = ttl
                        
                except Exception as e:
                    self.logger.warning(f"Failed to export key {key}: {e}")
                    continue
            
            # Save keys data
            keys_file = self.export_path / "data" / "redis_keys.json"
            with open(keys_file, 'w') as f:
                json.dump(keys_data, f, indent=2, default=str)
            
            self.logger.info(f"Redis keys exported to: {keys_file}")
            return keys_data
            
        except Exception as e:
            self.logger.error(f"Failed to export Redis keys: {e}")
            return None
    
    def export_redis_config(self, connection_info):
        """Export Redis configuration"""
        try:
            r = self.connect_to_redis(connection_info)
            if not r:
                return False
            
            # Get Redis configuration
            config_data = r.config_get('*')
            
            # Save configuration
            config_file = self.export_path / "config" / "redis_config.json"
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.logger.info(f"Redis configuration exported to: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export Redis configuration: {e}")
            return False
    
    def export_redis_info(self, connection_info):
        """Export Redis server information"""
        try:
            r = self.connect_to_redis(connection_info)
            if not r:
                return False
            
            # Get Redis info
            info_data = r.info()
            
            # Save info
            info_file = self.export_path / "validation" / "redis_info.json"
            with open(info_file, 'w') as f:
                json.dump(info_data, f, indent=2, default=str)
            
            self.logger.info(f"Redis info exported to: {info_file}")
            return info_data
            
        except Exception as e:
            self.logger.error(f"Failed to export Redis info: {e}")
            return None
    
    def create_migration_manifest(self, connection_info, keys_data, info_data):
        """Create migration manifest with export details"""
        try:
            manifest = {
                'export_timestamp': self.timestamp,
                'export_date': datetime.now().isoformat(),
                'source_redis': {
                    'host': connection_info['host'],
                    'port': connection_info['port'],
                    'database': connection_info['database']
                },
                'export_files': {
                    'dump': 'data/dump.rdb',
                    'keys': 'data/redis_keys.json',
                    'config': 'config/redis_config.json',
                    'info': 'validation/redis_info.json'
                },
                'statistics': {
                    'total_keys': len(keys_data) if keys_data else 0,
                    'memory_usage': info_data.get('used_memory_human', 'unknown') if info_data else 'unknown',
                    'redis_version': info_data.get('redis_version', 'unknown') if info_data else 'unknown'
                },
                'export_method': 'bgsave + keys export',
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
            dump_file = self.export_path / "data" / "dump.rdb"
            keys_file = self.export_path / "data" / "redis_keys.json"
            config_file = self.export_path / "config" / "redis_config.json"
            manifest_file = self.export_path / "migration_manifest.json"
            
            validation_results = {
                'dump_file_exists': dump_file.exists(),
                'keys_file_exists': keys_file.exists(),
                'config_file_exists': config_file.exists(),
                'manifest_file_exists': manifest_file.exists(),
                'dump_file_size': dump_file.stat().st_size if dump_file.exists() else 0,
                'keys_file_size': keys_file.stat().st_size if keys_file.exists() else 0
            }
            
            # Validate JSON files
            if keys_file.exists():
                try:
                    with open(keys_file, 'r') as f:
                        keys_data = json.load(f)
                        validation_results['keys_count'] = len(keys_data)
                except:
                    validation_results['keys_file_valid'] = False
            
            # Save validation results
            validation_file = self.export_path / "validation" / "export_validation.json"
            with open(validation_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            all_valid = all([
                validation_results['dump_file_exists'],
                validation_results['keys_file_exists'],
                validation_results['manifest_file_exists'],
                validation_results['dump_file_size'] > 0
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
        """Run complete Redis export process"""
        self.logger.info("Starting Redis data export for Docker migration")
        
        # Create export directory
        if not self.create_export_directory():
            return False
        
        # Get Redis connection info
        connection_info = self.get_redis_connection_info()
        if not connection_info:
            return False
        
        # Export Redis dump
        if not self.export_redis_dump(connection_info):
            return False
        
        # Export keys as JSON
        keys_data = self.export_redis_keys_json(connection_info)
        if keys_data is None:
            return False
        
        # Export configuration
        if not self.export_redis_config(connection_info):
            return False
        
        # Export server info
        info_data = self.export_redis_info(connection_info)
        if info_data is None:
            return False
        
        # Create manifest
        if not self.create_migration_manifest(connection_info, keys_data, info_data):
            return False
        
        # Validate export
        validation_results = self.validate_export()
        if not validation_results:
            return False
        
        self.logger.info(f"Redis export completed successfully")
        self.logger.info(f"Export location: {self.export_path}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Export macOS Redis data for Docker migration')
    parser.add_argument('--export-dir', help='Export directory path', default='./migration_exports')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    exporter = MacOSRedisExporter(args.export_dir)
    success = exporter.run_export()
    
    if success:
        print(f"\n✅ Redis export completed successfully")
        print(f"📁 Export location: {exporter.export_path}")
        print(f"📋 Next step: Run import script on Docker environment")
    else:
        print(f"\n❌ Redis export failed")
        print(f"📋 Check log file: redis_export_{exporter.timestamp}.log")
        sys.exit(1)

if __name__ == "__main__":
    main()