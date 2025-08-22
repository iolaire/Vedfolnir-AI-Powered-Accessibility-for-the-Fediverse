# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Migration Runner

This script applies the session management optimization migration to improve
database performance for user authentication, platform context loading, and
session management operations.

Usage:
    python run_session_management_migration.py [--dry-run] [--rollback]
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from database import DatabaseManager

from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SessionManagementMigration:
    """Handles the session management optimization migration"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.db_path = config.storage.database_url.replace('mysql+pymysql://', '')
        
    def check_database_exists(self):
        """Check if the database file exists"""
        if not True  # MySQL server handles database existence:
            logger.error(f"Database file not found: {self.db_path}")
            return False
        return True
    
    def backup_database(self):
        """Create a backup of the database before migration"""
        backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return None
    
    def get_existing_indexes(self):
        """Get list of existing indexes"""
        conn = engine.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT name, tbl_name, sql 
                FROM MySQL_master 
                WHERE type='index' AND name NOT LIKE 'MySQL_%' 
                ORDER BY tbl_name, name
            """)
            indexes = cursor.fetchall()
            return indexes
        finally:
            conn.close()
    
    def check_migration_needed(self):
        """Check if the migration is needed by looking for key indexes"""
        existing_indexes = self.get_existing_indexes()
        index_names = [idx[0] for idx in existing_indexes]
        
        # Check for some key indexes that should exist after migration
        required_indexes = [
            'ix_users_is_active',
            'ix_platform_connections_user_active',
            'ix_user_sessions_user_platform'
        ]
        
        missing_indexes = [idx for idx in required_indexes if idx not in index_names]
        
        if missing_indexes:
            logger.info(f"Migration needed. Missing indexes: {missing_indexes}")
            return True
        else:
            logger.info("Migration appears to already be applied")
            return False
    
    def apply_migration(self, dry_run=False):
        """Apply the session management optimization migration"""
        if not self.check_database_exists():
            return False
        
        if dry_run:
            logger.info("DRY RUN: Would apply session management optimization migration")
            self.show_migration_plan()
            return True
        
        # Create backup
        backup_path = self.backup_database()
        if not backup_path:
            logger.error("Failed to create backup. Aborting migration.")
            return False
        
        try:
            # Apply the migration by executing the SQL directly
            conn = engine.connect()
            cursor = conn.cursor()
            
            logger.info("Applying session management optimization indexes...")
            
            # Execute the upgrade SQL from the migration
            migration_sql = self._get_upgrade_sql()
            
            for sql_statement in migration_sql:
                if sql_statement.strip():
                    try:
                        logger.debug(f"Executing: {sql_statement}")
                        cursor.execute(sql_statement)
                    except SQLAlchemyError as e:
                        if "already exists" in str(e).lower():
                            logger.warning(f"Index already exists, skipping: {sql_statement}")
                        else:
                            raise
            
            conn.commit()
            logger.info("Migration applied successfully")
            
            # Verify the migration
            if self.verify_migration():
                logger.info("Migration verification passed")
                return True
            else:
                logger.error("Migration verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def rollback_migration(self, dry_run=False):
        """Rollback the session management optimization migration"""
        if not self.check_database_exists():
            return False
        
        if dry_run:
            logger.info("DRY RUN: Would rollback session management optimization migration")
            self.show_rollback_plan()
            return True
        
        # Create backup
        backup_path = self.backup_database()
        if not backup_path:
            logger.error("Failed to create backup. Aborting rollback.")
            return False
        
        try:
            conn = engine.connect()
            cursor = conn.cursor()
            
            logger.info("Rolling back session management optimization indexes...")
            
            # Execute the downgrade SQL from the migration
            rollback_sql = self._get_downgrade_sql()
            
            for sql_statement in rollback_sql:
                if sql_statement.strip():
                    try:
                        logger.debug(f"Executing: {sql_statement}")
                        cursor.execute(sql_statement)
                    except SQLAlchemyError as e:
                        if "no such index" in str(e).lower():
                            logger.warning(f"Index doesn't exist, skipping: {sql_statement}")
                        else:
                            raise
            
            conn.commit()
            logger.info("Migration rolled back successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def verify_migration(self):
        """Verify that the migration was applied correctly"""
        existing_indexes = self.get_existing_indexes()
        index_names = [idx[0] for idx in existing_indexes]
        
        # Check for key indexes that should exist after migration
        expected_indexes = [
            'ix_users_is_active',
            'ix_users_role',
            'ix_platform_connections_user_active',
            'ix_platform_connections_user_default',
            'ix_user_sessions_user_platform',
            'ix_posts_platform_connection_id',
            'ix_images_platform_connection_id'
        ]
        
        missing_indexes = [idx for idx in expected_indexes if idx not in index_names]
        
        if missing_indexes:
            logger.error(f"Migration verification failed. Missing indexes: {missing_indexes}")
            return False
        
        logger.info("All expected indexes are present")
        return True
    
    def show_migration_plan(self):
        """Show what the migration would do"""
        logger.info("Migration plan:")
        logger.info("- Add indexes for user authentication and role queries")
        logger.info("- Add indexes for platform connection queries")
        logger.info("- Add indexes for user session management")
        logger.info("- Add indexes for post and image platform relationships")
        logger.info("- Add indexes for processing run optimization")
    
    def show_rollback_plan(self):
        """Show what the rollback would do"""
        logger.info("Rollback plan:")
        logger.info("- Remove all session management optimization indexes")
        logger.info("- Restore database to pre-migration state")
    
    def _get_upgrade_sql(self):
        """Get the SQL statements for the upgrade"""
        return [
            # User table indexes
            "CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active)",
            "CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)",
            "CREATE INDEX IF NOT EXISTS ix_users_active_role ON users (is_active, role)",
            "CREATE INDEX IF NOT EXISTS ix_users_last_login ON users (last_login)",
            
            # Platform connections indexes
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_user_id ON platform_connections (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_user_active ON platform_connections (user_id, is_active)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_user_default ON platform_connections (user_id, is_default)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_platform_type ON platform_connections (platform_type)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_type_active ON platform_connections (platform_type, is_active)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_instance_url ON platform_connections (instance_url)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_type_instance_active ON platform_connections (platform_type, instance_url, is_active)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_last_used ON platform_connections (last_used)",
            "CREATE INDEX IF NOT EXISTS ix_platform_connections_created_at ON platform_connections (created_at)",
            
            # User sessions indexes
            "CREATE INDEX IF NOT EXISTS ix_user_sessions_active_platform_id ON user_sessions (active_platform_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_sessions_user_platform ON user_sessions (user_id, active_platform_id)",
            "CREATE INDEX IF NOT EXISTS ix_user_sessions_created_at ON user_sessions (created_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_sessions_ip_address ON user_sessions (ip_address)",
            
            # Posts indexes
            "CREATE INDEX IF NOT EXISTS ix_posts_platform_connection_id ON posts (platform_connection_id)",
            "CREATE INDEX IF NOT EXISTS ix_posts_platform_user ON posts (platform_connection_id, user_id)",
            "CREATE INDEX IF NOT EXISTS ix_posts_created_at ON posts (created_at)",
            "CREATE INDEX IF NOT EXISTS ix_posts_updated_at ON posts (updated_at)",
            
            # Images indexes
            "CREATE INDEX IF NOT EXISTS ix_images_platform_connection_id ON images (platform_connection_id)",
            "CREATE INDEX IF NOT EXISTS ix_images_post_id ON images (post_id)",
            "CREATE INDEX IF NOT EXISTS ix_images_platform_status ON images (platform_connection_id, status)",
            "CREATE INDEX IF NOT EXISTS ix_images_created_at ON images (created_at)",
            "CREATE INDEX IF NOT EXISTS ix_images_reviewed_at ON images (reviewed_at)",
            
            # Processing runs indexes
            "CREATE INDEX IF NOT EXISTS ix_processing_runs_platform_connection_id ON processing_runs (platform_connection_id)",
            "CREATE INDEX IF NOT EXISTS ix_processing_runs_platform_status ON processing_runs (platform_connection_id, status)",
            "CREATE INDEX IF NOT EXISTS ix_processing_runs_started_at ON processing_runs (started_at)",
            "CREATE INDEX IF NOT EXISTS ix_processing_runs_completed_at ON processing_runs (completed_at)"
        ]
    
    def _get_downgrade_sql(self):
        """Get the SQL statements for the downgrade"""
        return [
            # User table indexes
            "DROP INDEX IF EXISTS ix_users_is_active",
            "DROP INDEX IF EXISTS ix_users_role",
            "DROP INDEX IF EXISTS ix_users_active_role",
            "DROP INDEX IF EXISTS ix_users_last_login",
            
            # Platform connections indexes
            "DROP INDEX IF EXISTS ix_platform_connections_user_id",
            "DROP INDEX IF EXISTS ix_platform_connections_user_active",
            "DROP INDEX IF EXISTS ix_platform_connections_user_default",
            "DROP INDEX IF EXISTS ix_platform_connections_platform_type",
            "DROP INDEX IF EXISTS ix_platform_connections_type_active",
            "DROP INDEX IF EXISTS ix_platform_connections_instance_url",
            "DROP INDEX IF EXISTS ix_platform_connections_type_instance_active",
            "DROP INDEX IF EXISTS ix_platform_connections_last_used",
            "DROP INDEX IF EXISTS ix_platform_connections_created_at",
            
            # User sessions indexes
            "DROP INDEX IF EXISTS ix_user_sessions_active_platform_id",
            "DROP INDEX IF EXISTS ix_user_sessions_user_platform",
            "DROP INDEX IF EXISTS ix_user_sessions_created_at",
            "DROP INDEX IF EXISTS ix_user_sessions_ip_address",
            
            # Posts indexes
            "DROP INDEX IF EXISTS ix_posts_platform_connection_id",
            "DROP INDEX IF EXISTS ix_posts_platform_user",
            "DROP INDEX IF EXISTS ix_posts_created_at",
            "DROP INDEX IF EXISTS ix_posts_updated_at",
            
            # Images indexes
            "DROP INDEX IF EXISTS ix_images_platform_connection_id",
            "DROP INDEX IF EXISTS ix_images_post_id",
            "DROP INDEX IF EXISTS ix_images_platform_status",
            "DROP INDEX IF EXISTS ix_images_created_at",
            "DROP INDEX IF EXISTS ix_images_reviewed_at",
            
            # Processing runs indexes
            "DROP INDEX IF EXISTS ix_processing_runs_platform_connection_id",
            "DROP INDEX IF EXISTS ix_processing_runs_platform_status",
            "DROP INDEX IF EXISTS ix_processing_runs_started_at",
            "DROP INDEX IF EXISTS ix_processing_runs_completed_at"
        ]

def main():
    """Main function to run the migration"""
    parser = argparse.ArgumentParser(description='Session Management Migration Runner')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--rollback', action='store_true',
                       help='Rollback the migration instead of applying it')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if it appears to be already applied')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = Config()
        migration = SessionManagementMigration(config)
        
        logger.info("Session Management Migration Runner")
        logger.info(f"Database: {migration.db_path}")
        
        if args.rollback:
            logger.info("Rolling back session management optimization migration...")
            success = migration.rollback_migration(dry_run=args.dry_run)
        else:
            # Check if migration is needed
            if not args.force and not args.dry_run:
                if not migration.check_migration_needed():
                    logger.info("Migration not needed. Use --force to apply anyway.")
                    return 0
            
            logger.info("Applying session management optimization migration...")
            success = migration.apply_migration(dry_run=args.dry_run)
        
        if success:
            logger.info("Operation completed successfully")
            return 0
        else:
            logger.error("Operation failed")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())