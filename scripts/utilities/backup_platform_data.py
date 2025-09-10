#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform-aware backup script

Creates backups that preserve platform data integrity.
"""

import sys
import os
import shutil
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models import User, PlatformConnection, Post, Image
from app.core.database.core.database_manager import DatabaseManager

class PlatformDataBackup:
    """Platform-aware data backup utility"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = f"backups/platform_backup_{self.backup_timestamp}"
    
    def create_backup_directory(self):
        """Create backup directory structure"""
        print(f"📁 Creating backup directory: {self.backup_dir}")
        
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(f"{self.backup_dir}/database", exist_ok=True)
        os.makedirs(f"{self.backup_dir}/images", exist_ok=True)
        os.makedirs(f"{self.backup_dir}/logs", exist_ok=True)
        os.makedirs(f"{self.backup_dir}/config", exist_ok=True)
    
    def backup_database(self):
        """Backup database with platform data"""
        print("💾 Backing up database...")
        
        database_url = os.getenv("DATABASE_URL")
        if os.path.exists(db_path):
            backup_path = f"MySQL database"
            shutil.copy2(db_path, backup_path)
            print(f"  ✅ Database backed up to {backup_path}")
            
            # Create database info
            self._create_database_info(backup_path)
        else:
            print("  ⚠️ Database file not found")
    
    def _create_database_info(self, db_path):
        """Create database information file"""
        try:
            conn = engine.connect()
            cursor = conn.cursor()
            
            # Get table counts
            tables_info = {}
            tables = ['users', 'platform_connections', 'posts', 'images', 'user_sessions']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    tables_info[table] = count
                except SQLAlchemyError:
                    tables_info[table] = "table not found"
            
            conn.close()
            
            # Save database info
            db_info = {
                'backup_timestamp': self.backup_timestamp,
                'database_path': db_path,
                'table_counts': tables_info,
                'backup_size_bytes': os.path.getsize(db_path)
            }
            
            info_path = f"{self.backup_dir}/database/database_info.json"
            with open(info_path, 'w') as f:
                json.dump(db_info, f, indent=2)
            
            print(f"  📊 Database info saved to {info_path}")
            
        except Exception as e:
            print(f"  ⚠️ Could not create database info: {e}")
    
    def backup_platform_data(self):
        """Backup platform-specific data"""
        print("🔗 Backing up platform data...")
        
        try:
            session = self.db_manager.get_session()
            platforms = session.query(PlatformConnection).all()
            
            platform_data = []
            for platform in platforms:
                # Get platform statistics
                posts_count = session.query(Post).filter(
                    Post.platform_connection_id == platform.id
                ).count()
                
                images_count = session.query(Image).filter(
                    Image.platform_connection_id == platform.id
                ).count()
                
                platform_info = {
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type,
                    'instance_url': platform.instance_url,
                    'username': platform.username,
                    'is_default': platform.is_default,
                    'is_active': platform.is_active,
                    'created_at': platform.created_at.isoformat() if platform.created_at else None,
                    'posts_count': posts_count,
                    'images_count': images_count
                }
                
                platform_data.append(platform_info)
                print(f"  📊 {platform.name}: {posts_count} posts, {images_count} images")
            
            session.close()
            
            # Save platform data
            platform_file = f"{self.backup_dir}/platform_data.json"
            with open(platform_file, 'w') as f:
                json.dump({
                    'backup_timestamp': self.backup_timestamp,
                    'total_platforms': len(platform_data),
                    'platforms': platform_data
                }, f, indent=2)
            
            print(f"  ✅ Platform data saved to {platform_file}")
            
        except Exception as e:
            print(f"  ❌ Platform data backup failed: {e}")
    
    def backup_image_files(self):
        """Backup image files"""
        print("🖼️ Backing up image files...")
        
        image_storage_dir = "storage/images"
        if os.path.exists(image_storage_dir):
            backup_images_dir = f"{self.backup_dir}/images"
            
            try:
                # Copy all image files
                for root, dirs, files in os.walk(image_storage_dir):
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, image_storage_dir)
                        dst_path = os.path.join(backup_images_dir, rel_path)
                        
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                
                # Count backed up files
                total_files = sum([len(files) for r, d, files in os.walk(backup_images_dir)])
                print(f"  ✅ {total_files} image files backed up")
                
            except Exception as e:
                print(f"  ❌ Image backup failed: {e}")
        else:
            print("  ℹ️ No image storage directory found")
    
    def backup_configuration(self):
        """Backup configuration files"""
        print("⚙️ Backing up configuration...")
        
        config_files = ['.env', 'config.py', 'requirements.txt']
        
        for config_file in config_files:
            if os.path.exists(config_file):
                dst_path = f"{self.backup_dir}/config/{config_file}"
                
                if config_file == '.env':
                    # Sanitize .env file (remove sensitive data)
                    self._backup_env_file(config_file, dst_path)
                else:
                    shutil.copy2(config_file, dst_path)
                
                print(f"  ✅ {config_file} backed up")
            else:
                print(f"  ⚠️ {config_file} not found")
    
    def _backup_env_file(self, src_path, dst_path):
        """Backup .env file with sensitive data removed"""
        sensitive_keys = [
            'ACCESS_TOKEN', 'CLIENT_SECRET', 'CLIENT_KEY', 
            'ENCRYPTION_KEY', 'SECRET_KEY', 'PASSWORD'
        ]
        
        with open(src_path, 'r') as src_file:
            lines = src_file.readlines()
        
        with open(dst_path, 'w') as dst_file:
            for line in lines:
                if '=' in line and not line.strip().startswith('#'):
                    key = line.split('=')[0].strip()
                    if any(sensitive in key.upper() for sensitive in sensitive_keys):
                        dst_file.write(f"{key}=***REDACTED***\n")
                    else:
                        dst_file.write(line)
                else:
                    dst_file.write(line)
    
    def backup_logs(self):
        """Backup log files"""
        print("📝 Backing up logs...")
        
        logs_dir = "logs"
        if os.path.exists(logs_dir):
            backup_logs_dir = f"{self.backup_dir}/logs"
            
            try:
                shutil.copytree(logs_dir, backup_logs_dir, dirs_exist_ok=True)
                
                # Count log files
                log_files = [f for f in os.listdir(backup_logs_dir) if f.endswith('.log')]
                print(f"  ✅ {len(log_files)} log files backed up")
                
            except Exception as e:
                print(f"  ❌ Log backup failed: {e}")
        else:
            print("  ℹ️ No logs directory found")
    
    def create_backup_manifest(self):
        """Create backup manifest file"""
        print("📋 Creating backup manifest...")
        
        manifest = {
            'backup_timestamp': self.backup_timestamp,
            'backup_directory': self.backup_dir,
            'created_at': datetime.now().isoformat(),
            'components': {
                'database': True  # MySQL server handles database existence,
                'platform_data': os.path.exists(f"{self.backup_dir}/platform_data.json"),
                'images': os.path.exists(f"{self.backup_dir}/images"),
                'configuration': os.path.exists(f"{self.backup_dir}/config"),
                'logs': os.path.exists(f"{self.backup_dir}/logs")
            }
        }
        
        # Calculate backup size
        total_size = 0
        for root, dirs, files in os.walk(self.backup_dir):
            for file in files:
                total_size += os.path.getsize(os.path.join(root, file))
        
        manifest['total_size_bytes'] = total_size
        manifest['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        
        manifest_path = f"{self.backup_dir}/backup_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"  ✅ Backup manifest created: {manifest_path}")
        print(f"  📊 Total backup size: {manifest['total_size_mb']} MB")
        
        return manifest
    
    def run_backup(self):
        """Run complete backup process"""
        print("🚀 Starting platform-aware backup...")
        print(f"📅 Backup timestamp: {self.backup_timestamp}")
        print("=" * 60)
        
        try:
            self.create_backup_directory()
            self.backup_database()
            self.backup_platform_data()
            self.backup_image_files()
            self.backup_configuration()
            self.backup_logs()
            manifest = self.create_backup_manifest()
            
            print("=" * 60)
            print("🎉 Backup completed successfully!")
            print(f"📁 Backup location: {self.backup_dir}")
            print(f"📊 Backup size: {manifest['total_size_mb']} MB")
            
            return self.backup_dir
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None

def main():
    """Main backup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Platform-aware data backup')
    parser.add_argument('--output', '-o', help='Backup output directory')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet output')
    
    args = parser.parse_args()
    
    backup = PlatformDataBackup()
    
    if args.output:
        backup.backup_dir = args.output
    
    try:
        backup_path = backup.run_backup()
        return 0 if backup_path else 1
    except Exception as e:
        if not args.quiet:
            print(f"❌ Backup failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())