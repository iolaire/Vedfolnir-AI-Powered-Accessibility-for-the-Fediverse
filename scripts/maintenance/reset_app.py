#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Complete Application Reset Script for Vedfolnir

This script provides various levels of application reset, from cleaning up old data
to completely resetting the application to a fresh state.
"""

import os
import sys
import argparse
import shutil
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager
from data_cleanup import DataCleanupManager
from models import Base
from sqlalchemy import create_engine

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AppResetManager:
    """Manages different levels of application reset"""
    
    def __init__(self):
        try:
            self.config = Config()
            self.db_manager = DatabaseManager(self.config)
            self.cleanup_manager = DataCleanupManager(self.db_manager, self.config)
        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            logger.info("This might be due to missing environment variables.")
            logger.info("You can still perform file system cleanup operations.")
            self.config = None
            self.db_manager = None
            self.cleanup_manager = None
    
    def reset_database_only(self, dry_run=False):
        """Reset only the database, keeping files"""
        if not self.config:
            logger.error("Cannot reset database without valid configuration")
            return False
        
        logger.info("🗄️  Resetting database only (keeping image files)")
        
        if dry_run:
            logger.info("DRY RUN - Database would be reset")
            return True
        
        try:
            # Drop and recreate all tables
            engine = create_engine(self.config.storage.database_url)
            Base.metadata.drop_all(engine)
            
            # Use DatabaseManager to create tables with proper connection management
            self.db_manager.create_tables()
            
            logger.info("✅ Database reset successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reset database: {e}")
            return False
    
    def reset_storage_only(self, dry_run=False):
        """Reset only storage files, keeping database"""
        logger.info("📁 Resetting storage files only (keeping database)")
        
        storage_paths = [
            "storage/images",
            "logs"
        ]
        
        deleted_items = 0
        
        for path in storage_paths:
            if os.path.exists(path):
                try:
                    if dry_run:
                        # Count items that would be deleted
                        for root, dirs, files in os.walk(path):
                            deleted_items += len(files)
                        logger.info(f"DRY RUN - Would delete contents of {path}")
                    else:
                        # Delete contents but keep the directory
                        for root, dirs, files in os.walk(path, topdown=False):
                            for file in files:
                                os.remove(os.path.join(root, file))
                                deleted_items += 1
                            for dir in dirs:
                                dir_path = os.path.join(root, dir)
                                if os.path.exists(dir_path):
                                    os.rmdir(dir_path)
                        logger.info(f"✅ Cleaned {path}")
                except Exception as e:
                    logger.error(f"❌ Failed to clean {path}: {e}")
            else:
                logger.info(f"📂 {path} does not exist, skipping")
        
        if not dry_run:
            logger.info(f"✅ Storage reset complete - deleted {deleted_items} files")
        else:
            logger.info(f"DRY RUN - Would delete {deleted_items} files")
        
        return True
    
    def reset_complete(self, dry_run=False):
        """Complete application reset - database, storage, and environment"""
        logger.info("🔄 Performing complete application reset")
        
        success = True
        
        # Reset database
        if not self.reset_database_only(dry_run):
            success = False
        
        # Reset storage
        if not self.reset_storage_only(dry_run):
            success = False
        
        # Remove .env file
        env_file = ".env"
        if os.path.exists(env_file):
            try:
                if dry_run:
                    logger.info(f"DRY RUN - Would remove {env_file}")
                else:
                    os.remove(env_file)
                    logger.info(f"✅ Removed {env_file}")
            except Exception as e:
                logger.error(f"❌ Failed to remove {env_file}: {e}")
                success = False
        else:
            logger.info(f"📂 {env_file} does not exist, skipping")
        
        if success:
            if not dry_run:
                logger.info("🎉 Complete application reset successful!")
                logger.info("The application is now in a fresh state.")
                logger.info("Next steps:")
                logger.info("1. Generate new environment configuration: python scripts/setup/generate_env_secrets.py")
                logger.info("2. Start the web application: python web_app.py")
                logger.info("3. Log in and set up your platform connections")
            else:
                logger.info("DRY RUN - Complete reset would be successful")
        else:
            logger.error("❌ Complete reset failed - check errors above")
        
        return success
    
    def cleanup_old_data(self, dry_run=False):
        """Clean up old data using retention policies (non-destructive)"""
        if not self.cleanup_manager:
            logger.error("Cannot perform data cleanup without valid configuration")
            return False
        
        logger.info("🧹 Cleaning up old data using retention policies")
        
        try:
            results = self.cleanup_manager.run_full_cleanup(dry_run=dry_run)
            
            if not dry_run:
                logger.info("✅ Data cleanup completed successfully")
            else:
                logger.info("DRY RUN - Data cleanup would be successful")
            
            return True
        except Exception as e:
            logger.error(f"❌ Data cleanup failed: {e}")
            return False
    
    def reset_user_data(self, user_id, dry_run=False):
        """Reset data for a specific user"""
        if not self.cleanup_manager:
            logger.error("Cannot reset user data without valid configuration")
            return False
        
        logger.info(f"👤 Resetting data for user: {user_id}")
        
        try:
            results = self.cleanup_manager.cleanup_user_data(user_id, dry_run=dry_run)
            
            if not dry_run:
                logger.info(f"✅ User data reset completed: {results}")
            else:
                logger.info(f"DRY RUN - Would reset user data: {results}")
            
            return True
        except Exception as e:
            logger.error(f"❌ User data reset failed: {e}")
            return False
    
    def show_status(self):
        """Show current application status"""
        logger.info("📊 Application Status")
        logger.info("=" * 50)
        
        # Check configuration
        if self.config:
            logger.info("✅ Configuration: Valid")
        else:
            logger.info("❌ Configuration: Invalid (missing environment variables)")
        
        # Check database
        if self.config:
            db_path = self.config.storage.database_url.replace('sqlite:///', '')
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
                logger.info(f"✅ Database: Exists ({db_size / 1024 / 1024:.1f} MB)")
                
                # Get database stats if possible
                try:
                    session = self.db_manager.get_session()
                    from models import Post, Image, ProcessingRun
                    
                    post_count = session.query(Post).count()
                    image_count = session.query(Image).count()
                    run_count = session.query(ProcessingRun).count()
                    
                    logger.info(f"   - Posts: {post_count}")
                    logger.info(f"   - Images: {image_count}")
                    logger.info(f"   - Processing runs: {run_count}")
                    
                    session.close()
                except Exception as e:
                    logger.warning(f"   Could not get database stats: {e}")
            else:
                logger.info("❌ Database: Does not exist")
        else:
            logger.info("❓ Database: Cannot check (configuration invalid)")
        
        # Check storage directories
        storage_dirs = ["storage/images", "storage/database", "logs"]
        for dir_path in storage_dirs:
            if os.path.exists(dir_path):
                # Count files and calculate size
                file_count = 0
                total_size = 0
                for root, dirs, files in os.walk(dir_path):
                    file_count += len(files)
                    for file in files:
                        try:
                            total_size += os.path.getsize(os.path.join(root, file))
                        except OSError:
                            pass
                
                logger.info(f"✅ {dir_path}: {file_count} files ({total_size / 1024 / 1024:.1f} MB)")
            else:
                logger.info(f"❌ {dir_path}: Does not exist")
        
        # Check .env file
        env_file = ".env"
        if os.path.exists(env_file):
            env_size = os.path.getsize(env_file)
            logger.info(f"✅ {env_file}: Exists ({env_size / 1024:.1f} KB)")
        else:
            logger.info(f"❌ {env_file}: Does not exist")
        
        # Check environment variables
        required_env_vars = [
            "FLASK_SECRET_KEY",
            "AUTH_ADMIN_USERNAME",
            "AUTH_ADMIN_EMAIL", 
            "AUTH_ADMIN_PASSWORD",
            "PLATFORM_ENCRYPTION_KEY",
            "SECURITY_CSRF_ENABLED",
            "SECURITY_RATE_LIMITING_ENABLED",
            "SECURITY_INPUT_VALIDATION_ENABLED"
        ]
        
        logger.info("\n🔐 Environment Variables:")
        missing_vars = []
        for var in required_env_vars:
            if os.getenv(var):
                logger.info(f"✅ {var}: Set")
            else:
                logger.info(f"❌ {var}: Not set")
                missing_vars.append(var)
        
        if missing_vars:
            logger.info(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
            logger.info("Run: python scripts/setup/generate_env_secrets.py")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Vedfolnir Application Reset Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status                    # Show current application status
  %(prog)s --cleanup --dry-run         # Preview data cleanup (safe)
  %(prog)s --cleanup                   # Clean up old data using retention policies
  %(prog)s --reset-db --dry-run        # Preview database reset
  %(prog)s --reset-db                  # Reset database only (keep files)
  %(prog)s --reset-storage --dry-run   # Preview storage reset
  %(prog)s --reset-storage             # Reset storage only (keep database)
  %(prog)s --reset-complete --dry-run  # Preview complete reset
  %(prog)s --reset-complete            # Complete reset (database + storage)
  %(prog)s --reset-user user123        # Reset data for specific user
        """
    )
    
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without actually performing them')
    parser.add_argument('--status', action='store_true',
                       help='Show current application status')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up old data using retention policies (safe)')
    parser.add_argument('--reset-db', action='store_true',
                       help='Reset database only (keep image files)')
    parser.add_argument('--reset-storage', action='store_true',
                       help='Reset storage files only (keep database)')
    parser.add_argument('--reset-complete', action='store_true',
                       help='Complete reset - database and storage (DESTRUCTIVE)')
    parser.add_argument('--reset-user', type=str, metavar='USER_ID',
                       help='Reset data for specific user')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts (use with caution)')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    reset_manager = AppResetManager()
    
    # Show status
    if args.status:
        reset_manager.show_status()
        return 0
    
    # Confirmation for destructive operations
    destructive_ops = [args.reset_db, args.reset_storage, args.reset_complete]
    if any(destructive_ops) and not args.dry_run and not args.force:
        print("\n⚠️  WARNING: This operation will permanently delete data!")
        print("Make sure you have backups if needed.")
        response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return 0
    
    success = True
    
    # Perform requested operations
    if args.cleanup:
        success &= reset_manager.cleanup_old_data(dry_run=args.dry_run)
    
    if args.reset_db:
        success &= reset_manager.reset_database_only(dry_run=args.dry_run)
    
    if args.reset_storage:
        success &= reset_manager.reset_storage_only(dry_run=args.dry_run)
    
    if args.reset_complete:
        success &= reset_manager.reset_complete(dry_run=args.dry_run)
    
    if args.reset_user:
        success &= reset_manager.reset_user_data(args.reset_user, dry_run=args.dry_run)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())