# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Data Cleanup Service"""

from typing import Dict, Any
from models import ProcessingRun, Post, Image, ProcessingStatus

class CleanupService:
    """Service for admin data cleanup operations"""
    
    def __init__(self, db_manager, config=None):
        self.db_manager = db_manager
        self.config = config
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get statistics for cleanup operations"""
        # Use direct database manager for service operations
        session = self.db_manager.get_session()
        try:
            stats = {
                'processing_runs': session.query(ProcessingRun).count(),
                'total_posts': session.query(Post).count(),
                'total_images': session.query(Image).count(),
                'rejected_images': session.query(Image).filter_by(status=ProcessingStatus.REJECTED).count(),
                'posted_images': session.query(Image).filter_by(status=ProcessingStatus.POSTED).count(),
                'error_images': session.query(Image).filter_by(status=ProcessingStatus.ERROR).count()
            }
            
            # Get user statistics
            users = session.query(Post.user_id).distinct().all()
            user_ids = [user[0] for user in users if user[0]]
            
            user_stats = []
            for user_id in user_ids:
                post_count = session.query(Post).filter(Post.user_id == user_id).count()
                image_count = session.query(Image).join(Post).filter(Post.user_id == user_id).count()
                user_stats.append({
                    'user_id': user_id,
                    'post_count': post_count,
                    'image_count': image_count
                })
            
            stats['users'] = user_stats
            return stats
            
        finally:
            session.close()
    
    def cleanup_old_processing_runs(self, days: int, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old processing runs"""
        try:
            from scripts.maintenance.data_cleanup import DataCleanupManager
            cleanup_manager = DataCleanupManager(self.db_manager, self.config)
            count = cleanup_manager.archive_old_processing_runs(days=days, dry_run=dry_run)
            
            return {
                'success': True,
                'count': count,
                'dry_run': dry_run,
                'message': f'{"Would archive" if dry_run else "Archived"} {count} processing runs older than {days} days'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_images(self, status: ProcessingStatus, days: int, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old images by status"""
        try:
            from scripts.maintenance.data_cleanup import DataCleanupManager
            cleanup_manager = DataCleanupManager(self.db_manager, self.config)
            count = cleanup_manager.cleanup_old_images(status=status, days=days, dry_run=dry_run)
            
            return {
                'success': True,
                'count': count,
                'dry_run': dry_run,
                'message': f'{"Would clean up" if dry_run else "Cleaned up"} {count} {status.value} images older than {days} days'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_orphaned_posts(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up orphaned posts"""
        try:
            from scripts.maintenance.data_cleanup import DataCleanupManager
            cleanup_manager = DataCleanupManager(self.db_manager, self.config)
            count = cleanup_manager.cleanup_orphaned_posts(dry_run=dry_run)
            
            return {
                'success': True,
                'count': count,
                'dry_run': dry_run,
                'message': f'{"Would clean up" if dry_run else "Cleaned up"} {count} orphaned posts'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_user_data(self, user_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up all data for a specific user"""
        try:
            from scripts.maintenance.data_cleanup import DataCleanupManager
            cleanup_manager = DataCleanupManager(self.db_manager, self.config)
            results = cleanup_manager.cleanup_user_data(user_id=user_id, dry_run=dry_run)
            
            return {
                'success': True,
                'results': results,
                'dry_run': dry_run,
                'message': f'{"Would delete" if dry_run else "Deleted"} {results["posts"]} posts, {results["images"]} images, and {results["runs"]} processing runs for user {user_id}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_full_cleanup(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run full cleanup"""
        try:
            from scripts.maintenance.data_cleanup import DataCleanupManager
            cleanup_manager = DataCleanupManager(self.db_manager, self.config)
            results = cleanup_manager.run_full_cleanup(dry_run=dry_run)
            
            total_items = sum(results.values())
            
            return {
                'success': True,
                'results': results,
                'total_items': total_items,
                'dry_run': dry_run,
                'message': f'{"Would clean up" if dry_run else "Cleaned up"} {total_items} items'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }