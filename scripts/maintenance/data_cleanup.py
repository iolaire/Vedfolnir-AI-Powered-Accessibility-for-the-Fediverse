#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, or_, func

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models import Post, Image, ProcessingRun, ProcessingStatus
from app.core.database.core.database_manager import DatabaseManager
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataCleanupManager:
    """Manages data cleanup operations for the Vedfolnir database"""
    
    def __init__(self, db_manager: DatabaseManager, config: Config):
        self.db_manager = db_manager
        self.config = config
        
        # Default retention periods (in days)
        self.default_retention = {
            'processing_runs': 90,  # Keep processing runs for 90 days
            'rejected_images': 30,  # Keep rejected images for 30 days
            'posted_images': 180,   # Keep posted images for 180 days
            'error_images': 60      # Keep error images for 60 days
        }
        
        # Load custom retention periods from environment variables if available
        self._load_retention_config()
    
    def _load_retention_config(self):
        """Load retention configuration from environment variables"""
        retention_config = os.getenv('DATA_RETENTION_CONFIG')
        if retention_config:
            try:
                custom_retention = json.loads(retention_config)
                self.default_retention.update(custom_retention)
                logger.info(f"Loaded custom retention configuration: {self.default_retention}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in DATA_RETENTION_CONFIG: {retention_config}")
        else:
            # Try individual environment variables
            for key in self.default_retention:
                env_var = f"RETENTION_{key.upper()}"
                if os.getenv(env_var):
                    try:
                        days = int(os.getenv(env_var))
                        self.default_retention[key] = days
                        logger.info(f"Set {key} retention to {days} days from environment")
                    except ValueError:
                        logger.error(f"Invalid value for {env_var}: {os.getenv(env_var)}")
    
    def archive_old_processing_runs(self, days=None, dry_run=False):
        """Archive processing runs older than the specified number of days"""
        if days is None:
            days = self.default_retention['processing_runs']
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        logger.info(f"Archiving processing runs older than {cutoff_date} ({days} days)")
        
        session = self.db_manager.get_session()
        try:
            # Find processing runs older than the cutoff date
            old_runs = session.query(ProcessingRun).filter(
                ProcessingRun.completed_at < cutoff_date
            ).all()
            
            if not old_runs:
                logger.info("No old processing runs found to archive")
                return 0
            
            logger.info(f"Found {len(old_runs)} processing runs to archive")
            
            if dry_run:
                logger.info("Dry run - not archiving processing runs")
                return len(old_runs)
            
            # Archive the processing runs
            archive_dir = os.path.join(self.config.storage.base_dir, "archives")
            os.makedirs(archive_dir, exist_ok=True)
            
            archive_file = os.path.join(
                archive_dir, 
                f"processing_runs_archive_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Convert processing runs to dictionaries for JSON serialization
            archived_runs = []
            for run in old_runs:
                archived_runs.append({
                    'id': run.id,
                    'user_id': run.user_id,
                    'batch_id': run.batch_id,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'posts_processed': run.posts_processed,
                    'images_processed': run.images_processed,
                    'captions_generated': run.captions_generated,
                    'errors_count': run.errors_count,
                    'status': run.status,
                    'retry_attempts': run.retry_attempts,
                    'retry_successes': run.retry_successes,
                    'retry_failures': run.retry_failures,
                    'retry_total_time': run.retry_total_time,
                    'retry_stats_json': run.retry_stats_json
                })
            
            # Write the archive file
            with open(archive_file, 'w') as f:
                json.dump(archived_runs, f, indent=2)
            
            logger.info(f"Archived {len(old_runs)} processing runs to {archive_file}")
            
            # Delete the archived processing runs
            for run in old_runs:
                session.delete(run)
            
            session.commit()
            logger.info(f"Deleted {len(old_runs)} archived processing runs from database")
            
            return len(old_runs)
        except Exception as e:
            session.rollback()
            logger.error(f"Error archiving processing runs: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_old_images(self, status=None, days=None, dry_run=False):
        """Clean up old images with the specified status"""
        if status is None:
            # Default to cleaning up rejected images
            status = ProcessingStatus.REJECTED
            if days is None:
                days = self.default_retention['rejected_images']
        elif status == ProcessingStatus.POSTED:
            if days is None:
                days = self.default_retention['posted_images']
        elif status == ProcessingStatus.ERROR:
            if days is None:
                days = self.default_retention['error_images']
        else:
            if days is None:
                days = 30  # Default for other statuses
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        logger.info(f"Cleaning up {status.value} images older than {cutoff_date} ({days} days)")
        
        session = self.db_manager.get_session()
        try:
            # Find images with the specified status older than the cutoff date
            if status == ProcessingStatus.REJECTED:
                # For rejected images, use reviewed_at
                old_images = session.query(Image).filter(
                    Image.status == status,
                    Image.reviewed_at < cutoff_date
                ).all()
            elif status == ProcessingStatus.POSTED:
                # For posted images, use posted_at
                old_images = session.query(Image).filter(
                    Image.status == status,
                    Image.posted_at < cutoff_date
                ).all()
            else:
                # For other statuses, use updated_at
                old_images = session.query(Image).filter(
                    Image.status == status,
                    Image.updated_at < cutoff_date
                ).all()
            
            if not old_images:
                logger.info(f"No old {status.value} images found to clean up")
                return 0
            
            logger.info(f"Found {len(old_images)} {status.value} images to clean up")
            
            if dry_run:
                logger.info("Dry run - not cleaning up images")
                return len(old_images)
            
            # Delete the image files
            for image in old_images:
                if os.path.exists(image.local_path):
                    try:
                        os.remove(image.local_path)
                        logger.debug(f"Deleted image file: {image.local_path}")
                    except Exception as e:
                        logger.error(f"Error deleting image file {image.local_path}: {e}")
            
            # Delete the image records
            for image in old_images:
                session.delete(image)
            
            session.commit()
            logger.info(f"Deleted {len(old_images)} {status.value} images from database")
            
            return len(old_images)
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up images: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_orphaned_posts(self, dry_run=False):
        """Clean up posts that have no associated images"""
        session = self.db_manager.get_session()
        try:
            # Find posts with no associated images
            subquery = session.query(Image.post_id).distinct().subquery()
            orphaned_posts = session.query(Post).filter(
                ~Post.id.in_(subquery)
            ).all()
            
            if not orphaned_posts:
                logger.info("No orphaned posts found to clean up")
                return 0
            
            logger.info(f"Found {len(orphaned_posts)} orphaned posts to clean up")
            
            if dry_run:
                logger.info("Dry run - not cleaning up orphaned posts")
                return len(orphaned_posts)
            
            # Delete the orphaned posts
            for post in orphaned_posts:
                session.delete(post)
            
            session.commit()
            logger.info(f"Deleted {len(orphaned_posts)} orphaned posts from database")
            
            return len(orphaned_posts)
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up orphaned posts: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_user_data(self, user_id, dry_run=False):
        """Clean up all data for a specific user"""
        from app.core.security.core.security_utils import sanitize_for_log
        logger.info(f"Cleaning up all data for user: {sanitize_for_log(user_id)}")
        
        # Use parameterized queries to prevent SQL injection
        from sqlalchemy import text
        
        session = self.db_manager.get_session()
        try:
            # Count posts, images, and runs for this user
            post_count_result = session.execute(text("SELECT COUNT(*) FROM posts WHERE user_id = :user_id"), {'user_id': user_id}).scalar()
            post_count = post_count_result or 0
            
            if post_count == 0:
                logger.info(f"No posts found for user {sanitize_for_log(user_id)}")
                return {'posts': 0, 'images': 0, 'runs': 0}
            
            # Get post IDs for this user
            post_ids_result = session.execute(text("SELECT id FROM posts WHERE user_id = :user_id"), {'user_id': user_id}).fetchall()
            post_ids = [row[0] for row in post_ids_result]
            
            # Count images for these posts using parameterized query
            if post_ids:
                placeholders = ','.join([':id' + str(i) for i in range(len(post_ids))])
                params = {'id' + str(i): post_id for i, post_id in enumerate(post_ids)}
                image_count_result = session.query(Image).filter(Image.post_id.in_(post_ids)).count()
                image_count = image_count_result or 0
            else:
                image_count = 0
            
            # Count processing runs for this user
            run_count_result = session.execute(text("SELECT COUNT(*) FROM processing_runs WHERE user_id = :user_id"), {'user_id': user_id}).scalar()
            run_count = run_count_result or 0
            
            logger.info(f"Found {post_count} posts, {image_count} images, and {run_count} runs for user {sanitize_for_log(user_id)}")
            
            if dry_run:
                logger.info("Dry run - not deleting any data")
                return {'posts': post_count, 'images': image_count, 'runs': run_count}
            
            # Get image paths for deletion
            if post_ids:
                placeholders = ','.join([':id' + str(i) for i in range(len(post_ids))])
                params = {'id' + str(i): post_id for i, post_id in enumerate(post_ids)}
                image_paths_result = session.query(Image.local_path).filter(Image.post_id.in_(post_ids)).all()
                image_paths = [row[0] for row in image_paths_result if row[0]]
            else:
                image_paths = []
            
            # Delete image files
            for path in image_paths:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.debug(f"Deleted image file: {sanitize_for_log(path)}")
                    except Exception as e:
                        logger.error(f"Error deleting image file {sanitize_for_log(path)}: {sanitize_for_log(str(e))}")
            
            # Delete database records using parameterized queries
            # Delete images first (foreign key constraint)
            if post_ids:
                placeholders = ','.join([':id' + str(i) for i in range(len(post_ids))])
                params = {'id' + str(i): post_id for i, post_id in enumerate(post_ids)}
                session.query(Image).filter(Image.post_id.in_(post_ids)).delete(synchronize_session=False)
            
            # Delete posts
            session.execute(text("DELETE FROM posts WHERE user_id = :user_id"), {'user_id': user_id})
            
            # Delete processing runs
            session.execute(text("DELETE FROM processing_runs WHERE user_id = :user_id"), {'user_id': user_id})
            
            session.commit()
            logger.info(f"Deleted all data for user {sanitize_for_log(user_id)}: {post_count} posts, {image_count} images, {run_count} runs")
            
            return {'posts': post_count, 'images': image_count, 'runs': run_count}
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up user data: {sanitize_for_log(str(e))}")
            raise
        finally:
            session.close()
    
    def cleanup_orphan_processing_runs(self, hours=24.0, dry_run=False):
        """Clean up orphan processing runs that are stuck or abandoned"""
        from app.core.security.core.security_utils import sanitize_for_log
        if hours < 1:
            logger.info(f"Cleaning up orphan processing runs older than {hours} hours ({hours * 60:.0f} minutes)")
        else:
            logger.info(f"Cleaning up orphan processing runs older than {hours} hours")
        
        session = self.db_manager.get_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Find orphan processing runs:
            # 1. Runs with status "running" that started more than X hours ago
            # 2. Runs with no associated platform connection
            # 3. Runs that have no associated images
            
            orphan_runs = session.query(ProcessingRun).filter(
                or_(
                    # Long-running stuck processes
                    and_(
                        ProcessingRun.status == "running",
                        ProcessingRun.started_at < cutoff_time
                    ),
                    # Runs with deleted platform connections
                    and_(
                        ProcessingRun.platform_connection_id.isnot(None),
                        ~ProcessingRun.platform_connection_id.in_(
                            session.query(ProcessingRun.platform_connection_id).join(
                                ProcessingRun.platform_connection
                            ).filter(ProcessingRun.platform_connection_id.isnot(None))
                        )
                    )
                )
            ).all()
            
            if not orphan_runs:
                logger.info("No orphan processing runs found")
                return {'deleted': 0, 'errors': 0}
            
            deleted_count = 0
            error_count = 0
            
            for run in orphan_runs:
                try:
                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete orphan processing run: ID={run.id}, "
                                  f"User={sanitize_for_log(run.user_id)}, "
                                  f"Status={run.status}, Started={run.started_at}, "
                                  f"Platform={run.platform_connection_id}")
                    else:
                        logger.info(f"Deleting orphan processing run: ID={run.id}, "
                                  f"User={sanitize_for_log(run.user_id)}, "
                                  f"Status={run.status}, Started={run.started_at}")
                        
                        session.delete(run)
                        deleted_count += 1
                        
                except Exception as e:
                    logger.error(f"Error deleting processing run {run.id}: {e}")
                    error_count += 1
            
            if not dry_run:
                session.commit()
                logger.info(f"Successfully deleted {deleted_count} orphan processing runs")
            else:
                logger.info(f"[DRY RUN] Would delete {len(orphan_runs)} orphan processing runs")
            
            return {'deleted': deleted_count, 'errors': error_count}
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error during orphan processing runs cleanup: {e}")
            raise
        finally:
            session.close()
    
    def cleanup_storage_images(self, dry_run=False):
        """Clean up all stored images from the storage directory"""
        logger.info("Cleaning up storage/images directory")
        
        images_dir = self.config.storage.images_dir
        deleted_files = 0
        deleted_size = 0
        
        if not os.path.exists(images_dir):
            logger.info(f"Images directory {images_dir} does not exist")
            return 0
        
        try:
            # Get all files in the images directory
            for root, dirs, files in os.walk(images_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Get file size before deletion
                        file_size = os.path.getsize(file_path)
                        
                        if not dry_run:
                            os.remove(file_path)
                            logger.debug(f"Deleted image file: {file_path}")
                        else:
                            logger.debug(f"Would delete image file: {file_path}")
                        
                        deleted_files += 1
                        deleted_size += file_size
                        
                    except OSError as e:
                        logger.warning(f"Could not delete {file_path}: {e}")
            
            # Remove empty directories
            if not dry_run:
                for root, dirs, files in os.walk(images_dir, topdown=False):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            if not os.listdir(dir_path):  # Directory is empty
                                os.rmdir(dir_path)
                                logger.debug(f"Removed empty directory: {dir_path}")
                        except OSError as e:
                            logger.warning(f"Could not remove directory {dir_path}: {e}")
            
            logger.info(f"{'Would delete' if dry_run else 'Deleted'} {deleted_files} image files "
                       f"({deleted_size / 1024 / 1024:.1f} MB)")
            
        except Exception as e:
            logger.error(f"Error cleaning up storage images: {e}")
            raise
        
        return deleted_files
    
    def cleanup_log_files(self, dry_run=False):
        """Clean up log files"""
        logger.info("Cleaning up log files")
        
        log_patterns = [
            "logs/*.log",
            "logs/*.log.*",
            "logs/vedfolnir.log",
            "logs/vedfolnir.log.*",
            "logs/vedfolnir.log",
            "logs/vedfolnir.log.*",
            "logs/batch_update.log",
            "logs/batch_update.log.*",
            "logs/webapp.log",
            "logs/webapp.log.*",
            # Legacy patterns for backward compatibility
            "*.log",
            "vedfolnir.log",
            "vedfolnir.log.*",
            "vedfolnir.log",
            "vedfolnir.log.*"
        ]
        
        deleted_files = 0
        deleted_size = 0
        
        import glob
        
        for pattern in log_patterns:
            try:
                log_files = glob.glob(pattern)
                for log_file in log_files:
                    try:
                        # Get file size before deletion
                        file_size = os.path.getsize(log_file)
                        
                        if not dry_run:
                            # For the current log file, truncate instead of delete
                            if log_file.endswith('.log') and not any(c in log_file for c in ['1', '2', '3', '4', '5', '6', '7', '8', '9']):
                                with open(log_file, 'w') as f:
                                    f.write('')  # Truncate the file
                                logger.debug(f"Truncated current log file: {log_file}")
                            else:
                                os.remove(log_file)
                                logger.debug(f"Deleted log file: {log_file}")
                        else:
                            logger.debug(f"Would {'truncate' if log_file.endswith('.log') else 'delete'} log file: {log_file}")
                        
                        deleted_files += 1
                        deleted_size += file_size
                        
                    except OSError as e:
                        logger.warning(f"Could not process log file {log_file}: {e}")
                        
            except Exception as e:
                logger.warning(f"Error processing log pattern {pattern}: {e}")
        
        logger.info(f"{'Would process' if dry_run else 'Processed'} {deleted_files} log files "
                   f"({deleted_size / 1024 / 1024:.1f} MB)")
        
        return deleted_files

    def run_full_cleanup(self, dry_run=False):
        """Run all cleanup operations including database, storage, and logs"""
        logger.info("Running full system cleanup (database, storage, and logs)")
        
        # Database cleanup operations
        # Archive old processing runs
        archived_runs = self.archive_old_processing_runs(dry_run=dry_run)
        
        # Clean up orphan processing runs
        cleaned_orphan_runs = self.cleanup_orphan_processing_runs(dry_run=dry_run)
        
        # Clean up old rejected images
        cleaned_rejected = self.cleanup_old_images(
            status=ProcessingStatus.REJECTED, 
            dry_run=dry_run
        )
        
        # Clean up old posted images
        cleaned_posted = self.cleanup_old_images(
            status=ProcessingStatus.POSTED, 
            dry_run=dry_run
        )
        
        # Clean up old error images
        cleaned_error = self.cleanup_old_images(
            status=ProcessingStatus.ERROR, 
            dry_run=dry_run
        )
        
        # Clean up orphaned posts
        cleaned_posts = self.cleanup_orphaned_posts(dry_run=dry_run)
        
        # Storage cleanup operations
        # Clean up stored image files
        deleted_images = self.cleanup_storage_images(dry_run=dry_run)
        
        # Clean up log files
        deleted_logs = self.cleanup_log_files(dry_run=dry_run)
        
        logger.info(f"Full cleanup summary:")
        logger.info(f"Database cleanup:")
        logger.info(f"  - Archived processing runs: {archived_runs}")
        logger.info(f"  - Cleaned orphan processing runs: {cleaned_orphan_runs}")
        logger.info(f"  - Cleaned rejected images: {cleaned_rejected}")
        logger.info(f"  - Cleaned posted images: {cleaned_posted}")
        logger.info(f"  - Cleaned error images: {cleaned_error}")
        logger.info(f"  - Cleaned orphaned posts: {cleaned_posts}")
        logger.info(f"Storage cleanup:")
        logger.info(f"  - Deleted image files: {deleted_images}")
        logger.info(f"  - Processed log files: {deleted_logs}")
        
        return {
            'archived_runs': archived_runs,
            'cleaned_rejected': cleaned_rejected,
            'cleaned_posted': cleaned_posted,
            'cleaned_error': cleaned_error,
            'cleaned_posts': cleaned_posts,
            'deleted_images': deleted_images,
            'deleted_logs': deleted_logs
        }

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Vedfolnir Data Cleanup')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not actually delete anything')
    parser.add_argument('--runs', type=int, help='Archive processing runs older than N days')
    parser.add_argument('--rejected', type=int, help='Clean up rejected images older than N days')
    parser.add_argument('--posted', type=int, help='Clean up posted images older than N days')
    parser.add_argument('--error', type=int, help='Clean up error images older than N days')
    parser.add_argument('--orphaned', action='store_true', help='Clean up orphaned posts')
    parser.add_argument('--storage', action='store_true', help='Clean up storage/images directory')
    parser.add_argument('--logs', action='store_true', help='Clean up log files')
    parser.add_argument('--all', action='store_true', help='Run all cleanup operations (database, storage, and logs)')
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    config = Config()
    db_manager = DatabaseManager(config)
    cleanup_manager = DataCleanupManager(db_manager, config)
    
    if args.all:
        cleanup_manager.run_full_cleanup(dry_run=args.dry_run)
    else:
        if args.runs is not None:
            cleanup_manager.archive_old_processing_runs(days=args.runs, dry_run=args.dry_run)
        
        if args.rejected is not None:
            cleanup_manager.cleanup_old_images(
                status=ProcessingStatus.REJECTED, 
                days=args.rejected, 
                dry_run=args.dry_run
            )
        
        if args.posted is not None:
            cleanup_manager.cleanup_old_images(
                status=ProcessingStatus.POSTED, 
                days=args.posted, 
                dry_run=args.dry_run
            )
        
        if args.error is not None:
            cleanup_manager.cleanup_old_images(
                status=ProcessingStatus.ERROR, 
                days=args.error, 
                dry_run=args.dry_run
            )
        
        if args.orphaned:
            cleanup_manager.cleanup_orphaned_posts(dry_run=args.dry_run)
        
        if args.storage:
            cleanup_manager.cleanup_storage_images(dry_run=args.dry_run)
        
        if args.logs:
            cleanup_manager.cleanup_log_files(dry_run=args.dry_run)

if __name__ == "__main__":
    main()