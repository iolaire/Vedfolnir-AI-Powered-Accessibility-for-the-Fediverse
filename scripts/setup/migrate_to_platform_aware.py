#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform-Aware Database Migration CLI

This script provides a command-line interface for migrating existing Vedfolnir
databases to support platform-aware operations with user-managed platform connections.

Usage:
    python migrate_to_platform_aware.py --up                    # Run migration
    python migrate_to_platform_aware.py --down                  # Rollback migration
    python migrate_to_platform_aware.py --status                # Check migration status
    python migrate_to_platform_aware.py --validate              # Validate migration
    python migrate_to_platform_aware.py --cleanup               # Clean up backup tables
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from migrations.platform_aware_migration import PlatformAwareMigration
from config import Config

def setup_logging(level=logging.INFO):
    """Set up logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('migration.log')
        ]
    )

def get_database_url_from_config():
    """Get database URL from configuration"""
    try:
        config = Config()
        return config.storage.database_url
    except Exception as e:
        # Fallback to environment variable or default
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # Default MySQL database
        db_path = os.getenv('DATABASE_PATH', "MySQL database")
        return f'mysql+pymysql://{db_path}'

def run_migration_up(database_url: str, verbose: bool = False) -> bool:
    """
    Run the migration to platform-aware schema.
    
    Args:
        database_url: Database connection URL
        verbose: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting platform-aware database migration")
        
        with PlatformAwareMigration(database_url) as migration:
            success = migration.migrate_up()
            
            if success:
                logger.info("Migration completed successfully!")
                
                # Show migration status
                status = migration.get_migration_status()
                logger.info(f"Migration Status:")
                logger.info(f"  Platform-aware: {status['platform_aware']}")
                logger.info(f"  Platform connections: {status['platform_connections_count']}")
                logger.info(f"  Migrated posts: {status['migrated_posts']}")
                logger.info(f"  Migrated images: {status['migrated_images']}")
                logger.info(f"  Migrated processing runs: {status['migrated_processing_runs']}")
                
                return True
            else:
                logger.error("Migration failed!")
                return False
                
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False

def run_migration_down(database_url: str, verbose: bool = False) -> bool:
    """
    Rollback the migration to previous state.
    
    Args:
        database_url: Database connection URL
        verbose: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting migration rollback")
        
        # Confirm rollback
        response = input("Are you sure you want to rollback the migration? This will remove platform-aware features. (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Rollback cancelled")
            return True
        
        with PlatformAwareMigration(database_url) as migration:
            success = migration.migrate_down()
            
            if success:
                logger.info("Rollback completed successfully!")
                return True
            else:
                logger.error("Rollback failed!")
                return False
                
    except Exception as e:
        logger.error(f"Rollback error: {e}")
        return False

def check_migration_status(database_url: str, verbose: bool = False) -> bool:
    """
    Check and display migration status.
    
    Args:
        database_url: Database connection URL
        verbose: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)
    
    logger = logging.getLogger(__name__)
    
    try:
        with PlatformAwareMigration(database_url) as migration:
            status = migration.get_migration_status()
            migration_needed = migration.check_migration_needed()
            
            print("\n" + "="*50)
            print("MIGRATION STATUS")
            print("="*50)
            print(f"Database URL: {database_url}")
            print(f"Platform-aware: {'Yes' if status['platform_aware'] else 'No'}")
            print(f"Migration needed: {'Yes' if migration_needed else 'No'}")
            print(f"Tables: {', '.join(status['tables'])}")
            
            if status['platform_aware']:
                print(f"\nPlatform Data:")
                print(f"  Platform connections: {status['platform_connections_count']}")
                print(f"  Migrated posts: {status['migrated_posts']}")
                print(f"  Migrated images: {status['migrated_images']}")
                print(f"  Migrated processing runs: {status['migrated_processing_runs']}")
            
            print("="*50)
            
            return True
            
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return False

def validate_migration(database_url: str, verbose: bool = False) -> bool:
    """
    Validate migration data integrity.
    
    Args:
        database_url: Database connection URL
        verbose: Enable verbose logging
        
    Returns:
        True if validation passes, False otherwise
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)
    
    logger = logging.getLogger(__name__)
    
    try:
        with PlatformAwareMigration(database_url) as migration:
            if migration.check_migration_needed():
                logger.error("Database is not migrated to platform-aware schema")
                return False
            
            validation_errors = migration.validate_data_integrity()
            
            if validation_errors:
                logger.error("Validation failed with errors:")
                for error in validation_errors:
                    logger.error(f"  - {error}")
                return False
            else:
                logger.info("Validation passed - data integrity is good!")
                return True
                
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False

def cleanup_backup_tables(database_url: str, verbose: bool = False) -> bool:
    """
    Clean up backup tables after successful migration.
    
    Args:
        database_url: Database connection URL
        verbose: Enable verbose logging
        
    Returns:
        True if successful, False otherwise
    """
    if verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Confirm cleanup
        response = input("Are you sure you want to clean up backup tables? This will remove rollback capability. (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Cleanup cancelled")
            return True
        
        with PlatformAwareMigration(database_url) as migration:
            migration.cleanup_backup_tables()
            logger.info("Backup tables cleaned up successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return False

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Platform-Aware Database Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_to_platform_aware.py --up                    # Run migration
  python migrate_to_platform_aware.py --down                  # Rollback migration
  python migrate_to_platform_aware.py --status                # Check status
  python migrate_to_platform_aware.py --validate              # Validate migration
  python migrate_to_platform_aware.py --cleanup               # Clean up backups
  python migrate_to_platform_aware.py --up --verbose          # Run with verbose logging
        """
    )
    
    # Action arguments (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--up', action='store_true', help='Run migration to platform-aware schema')
    action_group.add_argument('--down', action='store_true', help='Rollback migration to previous schema')
    action_group.add_argument('--status', action='store_true', help='Check migration status')
    action_group.add_argument('--validate', action='store_true', help='Validate migration data integrity')
    action_group.add_argument('--cleanup', action='store_true', help='Clean up backup tables')
    
    # Optional arguments
    parser.add_argument('--database-url', help='Database URL (defaults to config/environment)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or get_database_url_from_config()
    
    if args.dry_run:
        print(f"DRY RUN MODE - No changes will be made")
        print(f"Database URL: {database_url}")
        print(f"Action: {'up' if args.up else 'down' if args.down else 'status' if args.status else 'validate' if args.validate else 'cleanup'}")
        return 0
    
    # Execute requested action
    success = False
    
    if args.up:
        success = run_migration_up(database_url, args.verbose)
    elif args.down:
        success = run_migration_down(database_url, args.verbose)
    elif args.status:
        success = check_migration_status(database_url, args.verbose)
    elif args.validate:
        success = validate_migration(database_url, args.verbose)
    elif args.cleanup:
        success = cleanup_backup_tables(database_url, args.verbose)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())