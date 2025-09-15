# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Complete User Data Deletion Script

This script completely removes all data associated with a user, including:
- Posts and images (database records and files)
- Caption generation tasks and results
- Processing runs and audit logs
- User sessions (Redis and database)
- Platform connections
- User settings and preferences
- GDPR audit logs
- Job audit logs
- Storage events
- All associated files and directories

Usage:
    python3 scripts/maintenance/delete_user_data.py --user-id 1 [--dry-run] [--confirm]
    python3 scripts/maintenance/delete_user_data.py --username does [--dry-run] [--confirm]
"""

import os
import sys
import argparse
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import (
    User, Post, Image, ProcessingRun, PlatformConnection, UserSession,
    CaptionGenerationTask, CaptionGenerationUserSettings, JobAuditLog,
    GDPRAuditLog, StorageEventLog, StorageOverride
)
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class UserDataDeleter:
    """Complete user data deletion manager"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.redis_client = None
        
        # Initialize Redis if available
        try:
            import redis
            # Use the same Redis configuration as the app
            redis_url = config.redis.url if hasattr(config, 'redis') else os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            redis_password = os.getenv('REDIS_PASSWORD')
            
            # Parse Redis URL to get connection details
            if redis_url.startswith('redis://'):
                # Extract password from URL if present
                if '@' in redis_url:
                    # Format: redis://:password@host:port/db
                    parts = redis_url.split('@')
                    if len(parts) == 2:
                        auth_part = parts[0].replace('redis://:', '')
                        if auth_part:
                            redis_password = auth_part
                
                # Connect to Redis with proper authentication
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                
                # Test connection
                self.redis_client.ping()
                logger.info("Redis client initialized successfully for session cleanup")
            else:
                logger.warning("Invalid Redis URL format")
                
        except Exception as e:
            logger.warning(f"Redis not available for session cleanup: {e}")
            self.redis_client = None
    
    def delete_user_data(self, user_id: int, dry_run: bool = True) -> Dict[str, int]:
        """
        Completely delete all data for a user
        
        Args:
            user_id: The user ID to delete data for
            dry_run: If True, only count what would be deleted
            
        Returns:
            Dict with counts of deleted items
        """
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Deleting all data for user ID: {user_id}")
        
        results = {
            'posts': 0,
            'images': 0,
            'image_files': 0,
            'processing_runs': 0,
            'platform_connections': 0,
            'caption_tasks': 0,
            'caption_settings': 0,
            'user_sessions_db': 0,
            'user_sessions_redis': 0,
            'job_audit_logs': 0,
            'gdpr_audit_logs': 0,
            'storage_events': 0,
            'storage_overrides': 0,
            'directories_removed': 0
        }
        
        with self.db_manager.get_session() as session:
            # Verify user exists
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            logger.info(f"Found user: {user.username} ({user.email}) - {user.role.value}")
            
            # 1. Delete posts and images
            results.update(self._delete_posts_and_images(session, user_id, dry_run))
            
            # 2. Delete processing runs
            results['processing_runs'] = self._delete_processing_runs(session, user_id, dry_run)
            
            # 3. Delete platform connections
            results['platform_connections'] = self._delete_platform_connections(session, user_id, dry_run)
            
            # 4. Delete caption generation tasks and settings
            caption_results = self._delete_caption_data(session, user_id, dry_run)
            results.update(caption_results)
            
            # 5. Delete user sessions (this will also expire active sessions to clear stale platform context)
            session_results = self._delete_user_sessions(session, user_id, dry_run)
            results.update(session_results)
            
            # 6. Delete audit logs
            audit_results = self._delete_audit_logs(session, user_id, dry_run)
            results.update(audit_results)
            
            # 7. Delete storage events and overrides
            storage_results = self._delete_storage_data(session, user_id, dry_run)
            results.update(storage_results)
            
            # 8. Delete user-specific directories
            results['directories_removed'] = self._delete_user_directories(user_id, dry_run)
            
            if not dry_run:
                session.commit()
                logger.info(f"✅ Successfully deleted all data for user {user_id}")
            else:
                logger.info(f"📊 Dry run completed - no data was actually deleted")
        
        return results
    
    def _delete_posts_and_images(self, session, user_id: int, dry_run: bool) -> Dict[str, int]:
        """Delete posts and associated images"""
        # Get posts for this user using proper foreign key relationship
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            posts = []
        else:
            # Use proper foreign key relationship - Post.user_id is now an integer FK to User.id
            posts = session.query(Post).filter_by(user_id=user_id).all()
        
        post_count = len(posts)
        
        # Get user's platform connections to find all associated images
        user_platforms = session.query(PlatformConnection).filter_by(user_id=user_id).all()
        platform_ids = [p.id for p in user_platforms]
        
        # Get ALL images for this user - both through posts and platform connections
        images = []
        
        # Images associated with posts
        if post_count > 0:
            post_ids = [post.id for post in posts]
            post_images = session.query(Image).filter(Image.post_id.in_(post_ids)).all()
            images.extend(post_images)
        
        # Images associated with platform connections (including pending images)
        if platform_ids:
            platform_images = session.query(Image).filter(Image.platform_connection_id.in_(platform_ids)).all()
            # Avoid duplicates by checking if image is already in the list
            existing_image_ids = {img.id for img in images}
            for img in platform_images:
                if img.id not in existing_image_ids:
                    images.append(img)
        
        image_count = len(images)
        
        if post_count == 0 and image_count == 0:
            logger.info(f"No posts or images found for user {user_id}")
            return {'posts': 0, 'images': 0, 'image_files': 0}
        
        # Count images by status for logging
        status_counts = {}
        for image in images:
            status = image.status.value if image.status else 'unknown'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            status_summary = ', '.join([f"{status}: {count}" for status, count in status_counts.items()])
            logger.info(f"Image status breakdown: {status_summary}")
        
        # Delete image files
        image_files_deleted = 0
        for image in images:
            if image.local_path and os.path.exists(image.local_path):
                if not dry_run:
                    try:
                        os.remove(image.local_path)
                        logger.debug(f"Deleted image file: {sanitize_for_log(image.local_path)}")
                    except Exception as e:
                        logger.error(f"Error deleting image file {sanitize_for_log(image.local_path)}: {e}")
                image_files_deleted += 1
        
        if not dry_run:
            # Delete images first (foreign key constraint)
            for image in images:
                session.delete(image)
            
            # Delete posts
            for post in posts:
                session.delete(post)
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {post_count} posts, {image_count} images, {image_files_deleted} image files")
        return {'posts': post_count, 'images': image_count, 'image_files': image_files_deleted}
    
    def _delete_processing_runs(self, session, user_id: int, dry_run: bool) -> int:
        """Delete processing runs"""
        # Use proper foreign key relationship - ProcessingRun.user_id is now an integer FK to User.id
        runs = session.query(ProcessingRun).filter_by(user_id=user_id).all()
        count = len(runs)
        
        if not dry_run and count > 0:
            for run in runs:
                session.delete(run)
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {count} processing runs")
        return count
    
    def _delete_platform_connections(self, session, user_id: int, dry_run: bool) -> int:
        """Delete platform connections"""
        platforms = session.query(PlatformConnection).filter_by(user_id=user_id).all()
        count = len(platforms)
        
        if not dry_run and count > 0:
            for platform in platforms:
                session.delete(platform)
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {count} platform connections")
        return count
    
    def _delete_caption_data(self, session, user_id: int, dry_run: bool) -> Dict[str, int]:
        """Delete caption generation tasks and settings"""
        # Caption generation tasks
        tasks = session.query(CaptionGenerationTask).filter_by(user_id=user_id).all()
        task_count = len(tasks)
        
        # Caption generation user settings
        settings = session.query(CaptionGenerationUserSettings).filter_by(user_id=user_id).all()
        settings_count = len(settings)
        
        if not dry_run:
            for task in tasks:
                session.delete(task)
            for setting in settings:
                session.delete(setting)
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {task_count} caption tasks, {settings_count} caption settings")
        return {'caption_tasks': task_count, 'caption_settings': settings_count}
    
    def _delete_user_sessions(self, session, user_id: int, dry_run: bool) -> Dict[str, int]:
        """Delete user sessions from database and Redis, and expire active sessions"""
        # Database sessions
        db_sessions = session.query(UserSession).filter_by(user_id=user_id).all()
        db_count = len(db_sessions)
        
        # Redis sessions
        redis_count = 0
        redis_keys_deleted = []
        
        if self.redis_client:
            try:
                # Get all session keys
                pattern = f"vedfolnir:session:*"
                session_keys = self.redis_client.keys(pattern)
                logger.debug(f"Found {len(session_keys)} total Redis session keys")
                
                for key in session_keys:
                    try:
                        # Get session data
                        session_data = self.redis_client.hgetall(key)
                        
                        # Check if this session belongs to our user
                        stored_user_id = session_data.get(b'user_id')
                        if stored_user_id:
                            # Handle both string and bytes
                            if isinstance(stored_user_id, bytes):
                                stored_user_id = stored_user_id.decode()
                            
                            if str(stored_user_id) == str(user_id):
                                redis_keys_deleted.append(key.decode() if isinstance(key, bytes) else key)
                                if not dry_run:
                                    deleted = self.redis_client.delete(key)
                                    logger.debug(f"Deleted Redis session {key}: {deleted}")
                                redis_count += 1
                                
                    except Exception as e:
                        logger.debug(f"Error checking Redis session {key}: {e}")
                        
            except Exception as e:
                logger.warning(f"Error accessing Redis sessions: {e}")
        
        # Force expire any remaining active sessions for this user
        if not dry_run:
            self._expire_active_user_sessions(user_id)
        
        # Delete database sessions
        if not dry_run and db_count > 0:
            for db_session in db_sessions:
                session.delete(db_session)
        
        # Log what was found/deleted
        if redis_keys_deleted:
            logger.debug(f"Redis sessions for user {user_id}: {redis_keys_deleted}")
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {db_count} database sessions, {redis_count} Redis sessions")
        return {'user_sessions_db': db_count, 'user_sessions_redis': redis_count}
    
    def _expire_active_user_sessions(self, user_id: int):
        """Force expire any active sessions for the user to clear stale platform context"""
        if not self.redis_client:
            logger.debug("Redis not available for session expiration")
            return
        
        try:
            # Look for any remaining session keys that might contain user data
            pattern = f"vedfolnir:session:*"
            session_keys = self.redis_client.keys(pattern)
            
            expired_count = 0
            for key in session_keys:
                try:
                    session_data = self.redis_client.hgetall(key)
                    stored_user_id = session_data.get(b'user_id')
                    
                    if stored_user_id:
                        if isinstance(stored_user_id, bytes):
                            stored_user_id = stored_user_id.decode()
                        
                        if str(stored_user_id) == str(user_id):
                            # Set session to expire immediately
                            self.redis_client.expire(key, 1)
                            expired_count += 1
                            logger.debug(f"Set session {key} to expire in 1 second")
                            
                except Exception as e:
                    logger.debug(f"Error expiring session {key}: {e}")
            
            if expired_count > 0:
                logger.info(f"Set {expired_count} active sessions to expire for user {user_id}")
                
            # Also clear any platform-specific session data
            self._clear_platform_session_data(user_id)
            
        except Exception as e:
            logger.warning(f"Error expiring active sessions: {e}")
    
    def _clear_platform_session_data(self, user_id: int):
        """Clear platform-specific session data that might be cached"""
        if not self.redis_client:
            return
        
        try:
            # Clear platform manager cache for this user
            platform_cache_key = f"vedfolnir:platform:user:{user_id}"
            deleted = self.redis_client.delete(platform_cache_key)
            if deleted:
                logger.debug(f"Cleared platform cache for user {user_id}")
            
            # Clear any other user-specific cache keys
            user_cache_pattern = f"vedfolnir:*:user:{user_id}*"
            cache_keys = self.redis_client.keys(user_cache_pattern)
            if cache_keys:
                deleted_count = self.redis_client.delete(*cache_keys)
                logger.debug(f"Cleared {deleted_count} cached entries for user {user_id}")
            
            # Clear platform-specific cache patterns
            platform_patterns = [
                f"vedfolnir:platform:*:user:{user_id}",
                f"vedfolnir:user:{user_id}:platform:*",
                f"vedfolnir:session:platform:user:{user_id}*",
                f"user_platforms:{user_id}",  # Direct platform cache keys
                f"platform:*"  # All platform cache keys (will filter by user_id)
            ]
            
            for pattern in platform_patterns:
                try:
                    if pattern.startswith("platform:*"):
                        # Special handling for platform:* keys - check user_id
                        platform_keys = self.redis_client.keys("platform:*")
                        for pkey in platform_keys:
                            try:
                                data = self.redis_client.get(pkey)
                                if data and (f'"user_id": {user_id}' in data or f'"user_id":{user_id}' in data):
                                    deleted = self.redis_client.delete(pkey)
                                    if deleted:
                                        logger.debug(f"Cleared platform cache key {pkey}")
                            except Exception as e:
                                logger.debug(f"Error checking platform key {pkey}: {e}")
                    else:
                        keys = self.redis_client.keys(pattern)
                        if keys:
                            deleted = self.redis_client.delete(*keys)
                            logger.debug(f"Cleared {deleted} keys matching pattern: {pattern}")
                except Exception as e:
                    logger.debug(f"Error clearing pattern {pattern}: {e}")
                
        except Exception as e:
            logger.debug(f"Error clearing platform session data: {e}")
    
    def _delete_audit_logs(self, session, user_id: int, dry_run: bool) -> Dict[str, int]:
        """Delete audit logs"""
        # Job audit logs
        job_logs = session.query(JobAuditLog).filter_by(user_id=user_id).all()
        job_count = len(job_logs)
        
        # GDPR audit logs
        gdpr_logs = session.query(GDPRAuditLog).filter_by(user_id=user_id).all()
        gdpr_count = len(gdpr_logs)
        
        if not dry_run:
            for log in job_logs:
                session.delete(log)
            for log in gdpr_logs:
                session.delete(log)
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {job_count} job audit logs, {gdpr_count} GDPR audit logs")
        return {'job_audit_logs': job_count, 'gdpr_audit_logs': gdpr_count}
    
    def _delete_storage_data(self, session, user_id: int, dry_run: bool) -> Dict[str, int]:
        """Delete storage events and overrides"""
        # Storage events
        events = session.query(StorageEventLog).filter_by(user_id=user_id).all()
        events_count = len(events)
        
        # Storage overrides
        overrides = session.query(StorageOverride).filter_by(admin_user_id=user_id).all()
        overrides_count = len(overrides)
        
        if not dry_run:
            for event in events:
                session.delete(event)
            for override in overrides:
                session.delete(override)
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {events_count} storage events, {overrides_count} storage overrides")
        return {'storage_events': events_count, 'storage_overrides': overrides_count}
    
    def _delete_user_directories(self, user_id: int, dry_run: bool) -> int:
        """Delete user-specific directories"""
        directories_removed = 0
        
        # User-specific image directories
        user_dirs = [
            f"storage/images/user_{user_id}",
            f"storage/temp/user_{user_id}",
            f"storage/backups/user_{user_id}"
        ]
        
        for dir_path in user_dirs:
            if os.path.exists(dir_path):
                if not dry_run:
                    try:
                        shutil.rmtree(dir_path)
                        logger.debug(f"Deleted directory: {dir_path}")
                    except Exception as e:
                        logger.error(f"Error deleting directory {dir_path}: {e}")
                directories_removed += 1
        
        if directories_removed > 0:
            logger.info(f"{'Would delete' if dry_run else 'Deleted'} {directories_removed} user directories")
        
        return directories_removed
    
    def expire_user_sessions_only(self, user_id: int) -> Dict[str, int]:
        """
        Only expire/delete active sessions for a user without deleting other data.
        Useful when platform connections change and session context needs to be refreshed.
        
        Args:
            user_id: The user ID to expire sessions for
            
        Returns:
            Dict with counts of expired/deleted sessions
        """
        logger.info(f"Expiring active sessions for user ID: {user_id}")
        
        results = {'redis_sessions': 0, 'database_sessions': 0}
        
        # Handle Redis sessions
        if self.redis_client:
            try:
                # Get all session keys
                pattern = f"vedfolnir:session:*"
                session_keys = self.redis_client.keys(pattern)
                
                for key in session_keys:
                    try:
                        session_data = self.redis_client.hgetall(key)
                        stored_user_id = session_data.get(b'user_id')
                        
                        if stored_user_id:
                            if isinstance(stored_user_id, bytes):
                                stored_user_id = stored_user_id.decode()
                            
                            if str(stored_user_id) == str(user_id):
                                # Clear platform-specific data from the session before expiring
                                platform_keys = [
                                    b'platform_connection_id', 
                                    b'platform_name', 
                                    b'platform_type',
                                    b'platform_instance_url'
                                ]
                                
                                for pkey in platform_keys:
                                    try:
                                        self.redis_client.hdel(key, pkey)
                                    except Exception:
                                        pass
                                
                                # Set session to expire in 1 second (immediate expiration)
                                self.redis_client.expire(key, 1)
                                results['redis_sessions'] += 1
                                logger.debug(f"Cleared platform data and set session {key} to expire in 1 second")
                                
                    except Exception as e:
                        logger.debug(f"Error expiring session {key}: {e}")
                
                # Clear platform cache
                self._clear_platform_session_data(user_id)
                
            except Exception as e:
                logger.error(f"Error expiring Redis sessions: {e}")
        else:
            logger.warning("Redis not available - cannot expire Redis sessions")
        
        # Handle database sessions
        try:
            with self.db_manager.get_session() as session:
                # Delete database sessions for this user
                db_sessions = session.query(UserSession).filter_by(user_id=user_id).all()
                results['database_sessions'] = len(db_sessions)
                
                for db_session in db_sessions:
                    session.delete(db_session)
                
                session.commit()
                
                if results['database_sessions'] > 0:
                    logger.info(f"Deleted {results['database_sessions']} database sessions for user {user_id}")
                    
        except Exception as e:
            logger.error(f"Error deleting database sessions: {e}")
        
        total_expired = results['redis_sessions'] + results['database_sessions']
        logger.info(f"✅ Expired/deleted {total_expired} total sessions for user {user_id} (Redis: {results['redis_sessions']}, DB: {results['database_sessions']})")
        
        return results
    
    def print_summary(self, results: Dict[str, int], dry_run: bool):
        """Print deletion summary"""
        total_items = sum(results.values())
        
        print(f"\n{'=' * 60}")
        print(f"{'DRY RUN SUMMARY' if dry_run else 'DELETION SUMMARY'}")
        print(f"{'=' * 60}")
        
        for category, count in results.items():
            if count > 0:
                category_name = category.replace('_', ' ').title()
                print(f"{category_name:.<40} {count}")
        
        print(f"{'.' * 40}")
        print(f"{'Total Items':.<40} {total_items}")
        print(f"{'=' * 60}")
        
        if dry_run:
            print("⚠️  This was a DRY RUN - no data was actually deleted")
            print("   Run with --confirm to actually delete the data")
        else:
            print("✅ All user data has been permanently deleted")

def main():
    parser = argparse.ArgumentParser(description='Delete all data for a user or expire their sessions')
    parser.add_argument('--user-id', type=int, help='User ID to delete data for')
    parser.add_argument('--username', help='Username to delete data for')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Only show what would be deleted (default)')
    parser.add_argument('--confirm', action='store_true',
                        help='Actually delete the data (overrides --dry-run)')
    parser.add_argument('--expire-sessions-only', action='store_true',
                        help='Only expire active sessions without deleting data (useful after platform changes)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO', help='Set logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate arguments
    if not args.user_id and not args.username:
        print("❌ Error: Must specify either --user-id or --username")
        sys.exit(1)
    
    if args.user_id and args.username:
        print("❌ Error: Cannot specify both --user-id and --username")
        sys.exit(1)
    
    # Determine if this is a dry run
    dry_run = not args.confirm
    
    try:
        config = Config()
        deleter = UserDataDeleter(config)
        
        # Get user ID if username was provided
        user_id = args.user_id
        if args.username:
            with deleter.db_manager.get_session() as session:
                user = session.query(User).filter_by(username=args.username).first()
                if not user:
                    print(f"❌ Error: User '{args.username}' not found")
                    sys.exit(1)
                user_id = user.id
                print(f"Found user: {user.username} (ID: {user.id})")
        
        # Handle session expiration only
        if args.expire_sessions_only:
            print(f"🔄 Expiring active sessions for user ID {user_id}")
            session_results = deleter.expire_user_sessions_only(user_id)
            total_expired = session_results['redis_sessions'] + session_results['database_sessions']
            print(f"✅ Expired/deleted {total_expired} total sessions:")
            print(f"   - Redis sessions: {session_results['redis_sessions']}")
            print(f"   - Database sessions: {session_results['database_sessions']}")
            print("💡 User will need to refresh their browser to see updated platform context")
            return
        
        # Confirmation for actual deletion
        if not dry_run:
            print(f"\n⚠️  WARNING: This will PERMANENTLY DELETE all data for user ID {user_id}")
            print("This includes:")
            print("  - All posts and images")
            print("  - All caption generation tasks and settings")
            print("  - All processing runs and audit logs")
            print("  - All platform connections")
            print("  - All user sessions")
            print("  - All associated files and directories")
            print("\nThis action CANNOT be undone!")
            
            confirm = input("\nType 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                print("❌ Deletion cancelled")
                sys.exit(0)
        
        # Perform deletion
        results = deleter.delete_user_data(user_id, dry_run)
        deleter.print_summary(results, dry_run)
        
    except Exception as e:
        logger.error(f"Error during user data deletion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()