#!/usr/bin/env python3
"""
MySQL Database Initialization and Migration Script for Vedfolnir

This script replaces any SQLite-based database initialization and provides
comprehensive MySQL database setup, migration, and validation.
"""

import os
import sys
import logging
import argparse
import pymysql
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, run_migrations, get_db_connection
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLInitializer:
    """MySQL database initializer and migrator for Vedfolnir."""
    
    def __init__(self, config=None):
        """Initialize with configuration."""
        self.config = config or Config()
        self.connection = None
        
    def connect(self):
        """Establish MySQL connection."""
        try:
            self.connection = get_db_connection()
            logger.info("✅ MySQL connection established")
            return True
        except Exception as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close MySQL connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("🔌 MySQL connection closed")
    
    def check_database_exists(self):
        """Check if the database exists and has tables."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (self.config.database.database_name,))
            
            table_count = cursor.fetchone()[0]
            cursor.close()
            
            logger.info(f"📊 Database contains {table_count} tables")
            return table_count > 0
            
        except Exception as e:
            logger.error(f"❌ Database check failed: {e}")
            return False
    
    def initialize_database(self):
        """Initialize the MySQL database schema."""
        try:
            logger.info("🔧 Initializing MySQL database schema...")
            init_db()
            logger.info("✅ Database schema initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def run_migrations(self):
        """Run database migrations."""
        try:
            logger.info("🔄 Running database migrations...")
            run_migrations()
            logger.info("✅ Database migrations completed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Database migrations failed: {e}")
            return False
    
    def validate_schema(self):
        """Validate the database schema."""
        required_tables = [
            'users', 'platform_connections', 'posts', 
            'captions', 'images', 'sessions'
        ]
        
        try:
            cursor = self.connection.cursor()
            
            # Check for required tables
            missing_tables = []
            for table in required_tables:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                """, (self.config.database.database_name, table))
                
                if cursor.fetchone()[0] == 0:
                    missing_tables.append(table)
            
            cursor.close()
            
            if missing_tables:
                logger.error(f"❌ Missing required tables: {missing_tables}")
                return False
            
            logger.info("✅ All required tables exist")
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema validation failed: {e}")
            return False
    
    def optimize_database(self):
        """Optimize database performance."""
        try:
            logger.info("⚡ Optimizing database performance...")
            cursor = self.connection.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
            """, (self.config.database.database_name,))
            
            tables = [row[0] for row in cursor.fetchall()]
            
            # Analyze and optimize each table
            for table in tables:
                try:
                    cursor.execute(f"ANALYZE TABLE {table}")
                    cursor.execute(f"OPTIMIZE TABLE {table}")
                    logger.debug(f"✅ Optimized table: {table}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to optimize table {table}: {e}")
            
            cursor.close()
            logger.info("✅ Database optimization completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database optimization failed: {e}")
            return False
    
    def create_admin_user(self):
        """Create admin user if it doesn't exist."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", ('admin',))
            admin_count = cursor.fetchone()[0]
            cursor.close()
            
            if admin_count == 0:
                logger.info("👤 Creating admin user...")
                import subprocess
                result = subprocess.run([
                    sys.executable, 'scripts/setup/init_admin_user.py'
                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
                
                if result.returncode == 0:
                    logger.info("✅ Admin user created successfully")
                    return True
                else:
                    logger.error(f"❌ Admin user creation failed: {result.stderr}")
                    return False
            else:
                logger.info("ℹ️ Admin user already exists")
                return True
                
        except Exception as e:
            logger.error(f"❌ Admin user creation failed: {e}")
            return False
    
    def cleanup_sqlite_files(self):
        """Clean up any remaining SQLite files."""
        try:
            logger.info("🧹 Cleaning up SQLite files...")
            
            # Find and remove SQLite files
            sqlite_patterns = ['*.db', '*.db-wal', '*.db-shm']
            removed_count = 0
            
            for pattern in sqlite_patterns:
                for file_path in Path('.').rglob(pattern):
                    if 'storage' in str(file_path) or 'backup' in str(file_path):
                        try:
                            file_path.unlink()
                            logger.debug(f"🗑️ Removed: {file_path}")
                            removed_count += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to remove {file_path}: {e}")
            
            if removed_count > 0:
                logger.info(f"✅ Removed {removed_count} SQLite files")
            else:
                logger.info("ℹ️ No SQLite files found to remove")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ SQLite cleanup failed: {e}")
            return False
    
    def generate_summary(self):
        """Generate initialization summary."""
        try:
            cursor = self.connection.cursor()
            
            # Get database info
            cursor.execute("SELECT VERSION()")
            mysql_version = cursor.fetchone()[0]
            
            # Get table counts
            cursor.execute("""
                SELECT 
                    table_name,
                    table_rows
                FROM information_schema.tables 
                WHERE table_schema = %s
                ORDER BY table_name
            """, (self.config.database.database_name,))
            
            tables = cursor.fetchall()
            cursor.close()
            
            # Generate summary
            summary = f"""
=== MySQL Initialization Summary ===
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🗄️ MySQL Version: {mysql_version}
🏷️ Database: {self.config.database.database_name}
📊 Tables: {len(tables)}

Table Details:
"""
            for table_name, row_count in tables:
                summary += f"  • {table_name}: {row_count} rows\n"
            
            summary += "\n✅ MySQL initialization completed successfully!"
            
            logger.info(summary)
            return summary
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            return None

def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(
        description='Initialize and migrate Vedfolnir MySQL database'
    )
    parser.add_argument('--skip-init', action='store_true',
                       help='Skip database initialization')
    parser.add_argument('--skip-migrate', action='store_true',
                       help='Skip database migrations')
    parser.add_argument('--skip-optimize', action='store_true',
                       help='Skip database optimization')
    parser.add_argument('--skip-admin', action='store_true',
                       help='Skip admin user creation')
    parser.add_argument('--skip-cleanup', action='store_true',
                       help='Skip SQLite cleanup')
    parser.add_argument('--force', action='store_true',
                       help='Force initialization even if database exists')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    logger.info("🚀 Starting MySQL database initialization for Vedfolnir")
    
    # Initialize the MySQL initializer
    initializer = MySQLInitializer()
    
    # Connect to MySQL
    if not args.dry_run and not initializer.connect():
        logger.error("❌ Failed to connect to MySQL")
        return 1
    
    success = True
    
    try:
        # Check if database needs initialization
        if not args.dry_run:
            db_exists = initializer.check_database_exists()
        else:
            db_exists = False
            logger.info("🔍 Would check if database exists")
        
        # Initialize database if needed
        if not args.skip_init and (not db_exists or args.force):
            if args.dry_run:
                logger.info("🔍 Would initialize database schema")
            else:
                if not initializer.initialize_database():
                    success = False
        
        # Run migrations
        if not args.skip_migrate and success:
            if args.dry_run:
                logger.info("🔍 Would run database migrations")
            else:
                if not initializer.run_migrations():
                    success = False
        
        # Validate schema
        if success and not args.dry_run:
            if not initializer.validate_schema():
                success = False
        
        # Optimize database
        if not args.skip_optimize and success:
            if args.dry_run:
                logger.info("🔍 Would optimize database performance")
            else:
                if not initializer.optimize_database():
                    logger.warning("⚠️ Database optimization failed (non-critical)")
        
        # Create admin user
        if not args.skip_admin and success:
            if args.dry_run:
                logger.info("🔍 Would create admin user")
            else:
                if not initializer.create_admin_user():
                    logger.warning("⚠️ Admin user creation failed (non-critical)")
        
        # Clean up SQLite files
        if not args.skip_cleanup:
            if args.dry_run:
                logger.info("🔍 Would clean up SQLite files")
            else:
                if not initializer.cleanup_sqlite_files():
                    logger.warning("⚠️ SQLite cleanup failed (non-critical)")
        
        # Generate summary
        if success and not args.dry_run:
            initializer.generate_summary()
        
    finally:
        if not args.dry_run:
            initializer.disconnect()
    
    if success:
        logger.info("🎉 MySQL initialization completed successfully!")
        return 0
    else:
        logger.error("❌ MySQL initialization failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
