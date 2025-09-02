#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform migration rollback script

Safely rolls back platform-aware migration.
"""

import sys
import os
import shutil
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class PlatformMigrationRollback:
    """Handles rollback of platform-aware migration"""
    
    def __init__(self, backup_path=None):
        self.backup_path = backup_path
        self.rollback_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"logs/rollback_{self.rollback_timestamp}.log"
    
    def log(self, message):
        """Log message to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        print(log_message)
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')
    
    def find_latest_backup(self):
        """Find the latest backup if none specified"""
        if self.backup_path:
            return self.backup_path
        
        self.log("🔍 Looking for latest backup...")
        
        backups_dir = "backups"
        if not os.path.exists(backups_dir):
            self.log("❌ No backups directory found")
            return None
        
        # Find all backup directories
        backup_dirs = []
        for item in os.listdir(backups_dir):
            item_path = os.path.join(backups_dir, item)
            if os.path.isdir(item_path) and item.startswith('platform_backup_'):
                backup_dirs.append(item_path)
        
        if not backup_dirs:
            self.log("❌ No platform backups found")
            return None
        
        # Get the latest backup
        latest_backup = max(backup_dirs, key=os.path.getctime)
        self.log(f"📁 Found latest backup: {latest_backup}")
        
        return latest_backup
    
    def validate_backup(self, backup_path):
        """Validate backup integrity"""
        self.log(f"🔍 Validating backup: {backup_path}")
        
        if not os.path.exists(backup_path):
            self.log(f"❌ Backup path does not exist: {backup_path}")
            return False
        
        # Check for manifest file
        manifest_path = os.path.join(backup_path, 'backup_manifest.json')
        if not os.path.exists(manifest_path):
            self.log("❌ Backup manifest not found")
            return False
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Check required components
            required_components = ['database']
            for component in required_components:
                if not manifest['components'].get(component, False):
                    self.log(f"❌ Required component missing: {component}")
                    return False
            
            self.log("✅ Backup validation passed")
            return True
            
        except Exception as e:
            self.log(f"❌ Backup validation failed: {e}")
            return False
    
    def create_pre_rollback_backup(self):
        """Create backup of current state before rollback"""
        self.log("💾 Creating pre-rollback backup...")
        
        current_db = "MySQL database"
        if os.path.exists(current_db):
            backup_name = f"MySQL database"
            backup_path = f"backups/{backup_name}"
            
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(current_db, backup_path)
            
            self.log(f"✅ Pre-rollback backup created: {backup_path}")
            return backup_path
        else:
            self.log("ℹ️ No current database to backup")
            return None
    
    def restore_database(self, backup_path):
        """Restore database from backup"""
        self.log("🔄 Restoring database...")
        
        backup_db = os.path.join(backup_path, 'database', "MySQL database")
        if not os.path.exists(backup_db):
            self.log("❌ Backup database not found")
            return False
        
        current_db = "MySQL database"
        
        try:
            # Ensure storage directory exists
            os.makedirs(os.path.dirname(current_db), exist_ok=True)
            
            # Restore database
            shutil.copy2(backup_db, current_db)
            
            self.log("✅ Database restored successfully")
            return True
            
        except Exception as e:
            self.log(f"❌ Database restore failed: {e}")
            return False
    
    def restore_configuration(self, backup_path):
        """Restore configuration files"""
        self.log("⚙️ Restoring configuration...")
        
        config_backup_dir = os.path.join(backup_path, 'config')
        if not os.path.exists(config_backup_dir):
            self.log("ℹ️ No configuration backup found")
            return True
        
        try:
            # Restore .env file (if exists)
            env_backup = os.path.join(config_backup_dir, '.env')
            if os.path.exists(env_backup):
                self.log("⚠️ .env file found in backup but contains redacted values")
                self.log("⚠️ Manual configuration update may be required")
            
            self.log("✅ Configuration restore completed")
            return True
            
        except Exception as e:
            self.log(f"❌ Configuration restore failed: {e}")
            return False
    
    def validate_rollback(self):
        """Validate rollback was successful"""
        self.log("🔍 Validating rollback...")
        
        try:
            # Check database exists
            current_db = "MySQL database"
            if not os.path.exists(current_db):
                self.log("❌ Database not found after rollback")
                return False
            
            # Try to connect to database
            import MySQL3
            conn = engine.connect()
            cursor = conn.cursor()
            
            # Check for basic tables
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['users', 'posts', 'images']
            for table in required_tables:
                if table not in tables:
                    self.log(f"❌ Required table missing: {table}")
                    conn.close()
                    return False
            
            conn.close()
            
            self.log("✅ Rollback validation passed")
            return True
            
        except Exception as e:
            self.log(f"❌ Rollback validation failed: {e}")
            return False
    
    def run_rollback(self):
        """Run complete rollback process"""
        self.log("🔄 Starting platform migration rollback...")
        self.log(f"📅 Rollback timestamp: {self.rollback_timestamp}")
        self.log("=" * 60)
        
        try:
            # Find backup to restore from
            backup_path = self.find_latest_backup()
            if not backup_path:
                self.log("❌ No backup found for rollback")
                return False
            
            # Validate backup
            if not self.validate_backup(backup_path):
                self.log("❌ Backup validation failed")
                return False
            
            # Create pre-rollback backup
            self.create_pre_rollback_backup()
            
            # Restore from backup
            if not self.restore_database(backup_path):
                self.log("❌ Database restore failed")
                return False
            
            if not self.restore_configuration(backup_path):
                self.log("❌ Configuration restore failed")
                return False
            
            # Validate rollback
            if not self.validate_rollback():
                self.log("❌ Rollback validation failed")
                return False
            
            self.log("=" * 60)
            self.log("🎉 Rollback completed successfully!")
            self.log(f"📁 Restored from: {backup_path}")
            self.log(f"📝 Rollback log: {self.log_file}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Rollback failed with exception: {e}")
            return False

def main():
    """Main rollback function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Platform migration rollback')
    parser.add_argument('--backup', '-b', help='Specific backup path to restore from')
    parser.add_argument('--force', '-f', action='store_true', help='Force rollback without confirmation')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet output')
    
    args = parser.parse_args()
    
    if not args.force and not args.quiet:
        print("⚠️ WARNING: This will rollback the platform-aware migration!")
        print("⚠️ Current data may be lost if not backed up.")
        response = input("Continue with rollback? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Rollback cancelled")
            return 1
    
    rollback = PlatformMigrationRollback(args.backup)
    
    try:
        success = rollback.run_rollback()
        return 0 if success else 1
    except Exception as e:
        if not args.quiet:
            print(f"❌ Rollback failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())