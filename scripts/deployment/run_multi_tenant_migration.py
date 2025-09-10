# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Multi-Tenant Caption Management Migration Runner
Safely executes database migrations for admin features
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User
import importlib.util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MigrationRunner:
    """Handles safe execution of multi-tenant admin migrations"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
    def backup_database(self):
        """Create database backup before migration"""
        logger.info("Creating database backup...")
        
        backup_dir = Path("storage/backups/mysql")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"pre_migration_backup_{timestamp}.sql"
        
        # MySQL backup command
        db_config = self.config.get_database_config()
        backup_cmd = f"""mysqldump -h {db_config.get('host', 'localhost')} \
                        -P {db_config.get('port', 3306)} \
                        -u {db_config.get('user')} \
                        -p{db_config.get('password')} \
                        {db_config.get('database')} > {backup_file}"""
        
        try:
            os.system(backup_cmd)
            logger.info(f"Database backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def verify_prerequisites(self):
        """Verify system is ready for migration"""
        logger.info("Verifying migration prerequisites...")
        
        # Check database connection
        try:
            with self.db_manager.get_session() as session:
                session.execute("SELECT 1")
            logger.info("✓ Database connection verified")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            return False
        
        # Check for admin user
        try:
            with self.db_manager.get_session() as session:
                admin_count = session.query(User).filter_by(role='admin').count()
                if admin_count == 0:
                    logger.warning("⚠ No admin users found - consider creating one after migration")
                else:
                    logger.info(f"✓ Found {admin_count} admin user(s)")
        except Exception as e:
            logger.warning(f"Could not verify admin users: {e}")
        
        # Check available disk space
        try:
            import shutil
            free_space = shutil.disk_usage('.').free / (1024**3)  # GB
            if free_space < 1:
                logger.warning(f"⚠ Low disk space: {free_space:.2f}GB available")
            else:
                logger.info(f"✓ Sufficient disk space: {free_space:.2f}GB available")
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
        
        return True
    
    def run_migration(self, backup=True):
        """Execute the multi-tenant admin migration"""
        logger.info("Starting multi-tenant admin migration...")
        
        if not self.verify_prerequisites():
            logger.error("Prerequisites check failed")
            return False
        
        backup_file = None
        if backup:
            try:
                backup_file = self.backup_database()
            except Exception as e:
                logger.error(f"Backup failed: {e}")
                return False
        
        try:
            # Load and execute migration
            migration_path = project_root / "migrations" / "multi_tenant_admin_migration.py"
            spec = importlib.util.spec_from_file_location("migration", migration_path)
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # Execute upgrade
            logger.info("Executing migration upgrade...")
            migration_module.upgrade()
            
            logger.info("✓ Migration completed successfully!")
            
            # Verify migration
            self.verify_migration()
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            
            if backup_file and os.path.exists(backup_file):
                logger.info(f"Backup available for rollback: {backup_file}")
                
            return False
    
    def verify_migration(self):
        """Verify migration was successful"""
        logger.info("Verifying migration results...")
        
        try:
            with self.db_manager.get_session() as session:
                # Check new tables exist
                tables_to_check = [
                    'system_configuration',
                    'job_audit_log', 
                    'alert_configuration',
                    'system_alerts',
                    'performance_metrics'
                ]
                
                for table in tables_to_check:
                    result = session.execute(f"SHOW TABLES LIKE '{table}'").fetchone()
                    if result:
                        logger.info(f"✓ Table {table} created successfully")
                    else:
                        logger.error(f"✗ Table {table} not found")
                
                # Check new columns in caption_generation_tasks
                columns_to_check = [
                    'priority', 'admin_notes', 'cancelled_by_admin',
                    'admin_user_id', 'cancellation_reason', 'retry_count',
                    'max_retries', 'resource_usage'
                ]
                
                result = session.execute("DESCRIBE caption_generation_tasks").fetchall()
                existing_columns = [row[0] for row in result]
                
                for column in columns_to_check:
                    if column in existing_columns:
                        logger.info(f"✓ Column {column} added successfully")
                    else:
                        logger.error(f"✗ Column {column} not found")
                
                logger.info("Migration verification completed")
                
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
    
    def rollback_migration(self, backup_file=None):
        """Rollback migration using backup or downgrade"""
        logger.info("Rolling back multi-tenant admin migration...")
        
        if backup_file and os.path.exists(backup_file):
            logger.info(f"Restoring from backup: {backup_file}")
            
            db_config = self.config.get_database_config()
            restore_cmd = f"""mysql -h {db_config.get('host', 'localhost')} \
                            -P {db_config.get('port', 3306)} \
                            -u {db_config.get('user')} \
                            -p{db_config.get('password')} \
                            {db_config.get('database')} < {backup_file}"""
            
            try:
                os.system(restore_cmd)
                logger.info("✓ Database restored from backup")
                return True
            except Exception as e:
                logger.error(f"Backup restore failed: {e}")
        
        # Fallback to migration downgrade
        try:
            migration_path = project_root / "migrations" / "multi_tenant_admin_migration.py"
            spec = importlib.util.spec_from_file_location("migration", migration_path)
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            logger.info("Executing migration downgrade...")
            migration_module.downgrade()
            
            logger.info("✓ Migration rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Migration rollback failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Multi-Tenant Admin Migration Runner')
    parser.add_argument('--action', choices=['migrate', 'rollback', 'verify'], 
                       default='migrate', help='Action to perform')
    parser.add_argument('--no-backup', action='store_true', 
                       help='Skip database backup (not recommended)')
    parser.add_argument('--backup-file', type=str, 
                       help='Backup file to use for rollback')
    
    args = parser.parse_args()
    
    runner = MigrationRunner()
    
    if args.action == 'migrate':
        success = runner.run_migration(backup=not args.no_backup)
        sys.exit(0 if success else 1)
        
    elif args.action == 'rollback':
        success = runner.rollback_migration(args.backup_file)
        sys.exit(0 if success else 1)
        
    elif args.action == 'verify':
        runner.verify_migration()
        sys.exit(0)

if __name__ == '__main__':
    main()