# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Data Cleanup Service"""

import logging
from typing import Dict, Any, Optional
from models import ProcessingRun, Post, Image, ProcessingStatus

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for admin data cleanup operations with storage monitoring integration"""
    
    def __init__(self, db_manager, config=None):
        self.db_manager = db_manager
        self.config = config
        
        # Initialize storage cleanup integration
        self.storage_integration = None
        try:
            from storage_cleanup_integration import StorageCleanupIntegration
            self.storage_integration = StorageCleanupIntegration(db_manager=db_manager)
            logger.info("Storage cleanup integration initialized")
        except ImportError as e:
            logger.warning(f"Storage cleanup integration not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize storage cleanup integration: {e}")
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get statistics for cleanup operations with storage information"""
        # Use direct database manager for service operations
        session = self.db_manager.get_session()
        try:
            stats = {
                'processing_runs': session.query(ProcessingRun).count(),
                'total_posts': session.query(Post).count(),
                'total_images': session.query(Image).count(),
                'rejected_images': session.query(Image).filter_by(status=ProcessingStatus.REJECTED).count(),
                'posted_images': session.query(Image).filter_by(status=ProcessingStatus.POSTED).count(),
                'error_images': session.query(Image).filter_by(status=ProcessingStatus.ERROR).count(),
                'pending_review': session.query(Image).filter_by(status=ProcessingStatus.PENDING).count(),
                'approved': session.query(Image).filter_by(status=ProcessingStatus.APPROVED).count()
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
            
            # Add storage information if available
            if self.storage_integration:
                try:
                    storage_warnings = self.storage_integration.get_storage_cleanup_warnings()
                    stats['storage_warnings'] = storage_warnings
                    stats['storage_available'] = True
                except Exception as e:
                    logger.error(f"Error getting storage warnings: {e}")
                    stats['storage_available'] = False
                    stats['storage_error'] = str(e)
            else:
                stats['storage_available'] = False
            
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
        """Run full cleanup with storage monitoring"""
        try:
            # Use storage integration if available for enhanced monitoring
            if self.storage_integration:
                logger.info("Running full cleanup with storage monitoring")
                summary = self.storage_integration.run_full_cleanup_with_monitoring(dry_run=dry_run)
                
                return {
                    'success': True,
                    'results': summary.to_dict(),
                    'total_items': summary.total_items_cleaned,
                    'storage_freed_gb': summary.total_storage_freed_gb,
                    'limit_lifted': summary.limit_lifted,
                    'dry_run': dry_run,
                    'message': f'{"Would clean up" if dry_run else "Cleaned up"} {summary.total_items_cleaned} items, {"would free" if dry_run else "freed"} {summary.total_storage_freed_gb:.2f}GB'
                }
            else:
                # Fallback to basic cleanup manager
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
            logger.error(f"Error in run_full_cleanup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_images_with_storage_monitoring(self, status: ProcessingStatus, days: int = None, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old images with storage monitoring and automatic limit lifting"""
        try:
            if self.storage_integration:
                logger.info(f"Running cleanup for {status.value} images with storage monitoring")
                result = self.storage_integration.cleanup_old_images_with_monitoring(
                    status=status, days=days, dry_run=dry_run
                )
                
                # Check if limits were lifted after cleanup
                if not dry_run and result.success and result.storage_freed_gb > 0:
                    # Recalculate and check limits
                    storage_after = self.storage_integration.recalculate_storage_after_cleanup()
                    limit_lifted = self.storage_integration.check_and_lift_storage_limits(storage_after)
                    
                    message = f'{"Would clean up" if dry_run else "Cleaned up"} {result.items_cleaned} {status.value} images'
                    if not dry_run:
                        message += f', freed {result.storage_freed_gb:.2f}GB'
                        if limit_lifted:
                            message += ', storage limits automatically lifted'
                else:
                    message = f'{"Would clean up" if dry_run else "Cleaned up"} {result.items_cleaned} {status.value} images'
                
                return {
                    'success': result.success,
                    'count': result.items_cleaned,
                    'storage_freed_gb': result.storage_freed_gb,
                    'dry_run': dry_run,
                    'message': message,
                    'error': result.error_message
                }
            else:
                # Fallback to basic cleanup
                return self.cleanup_old_images(status=status, days=days, dry_run=dry_run)
                
        except Exception as e:
            logger.error(f"Error in cleanup_old_images_with_storage_monitoring: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_storage_images_with_monitoring(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up storage images with monitoring and automatic limit lifting"""
        try:
            if self.storage_integration:
                logger.info("Running storage images cleanup with monitoring")
                result = self.storage_integration.cleanup_storage_images_with_monitoring(dry_run=dry_run)
                
                # Check if limits were lifted after cleanup
                if not dry_run and result.success and result.storage_freed_gb > 0:
                    storage_after = self.storage_integration.recalculate_storage_after_cleanup()
                    limit_lifted = self.storage_integration.check_and_lift_storage_limits(storage_after)
                    
                    message = f'{"Would delete" if dry_run else "Deleted"} {result.items_cleaned} storage files, {"would free" if dry_run else "freed"} {result.storage_freed_gb:.2f}GB'
                    if limit_lifted:
                        message += ', storage limits automatically lifted'
                else:
                    message = f'{"Would delete" if dry_run else "Deleted"} {result.items_cleaned} storage files'
                
                return {
                    'success': result.success,
                    'count': result.items_cleaned,
                    'storage_freed_gb': result.storage_freed_gb,
                    'dry_run': dry_run,
                    'message': message,
                    'error': result.error_message
                }
            else:
                # Fallback - this would need to be implemented
                return {
                    'success': False,
                    'error': 'Storage cleanup not available without storage integration'
                }
                
        except Exception as e:
            logger.error(f"Error in cleanup_storage_images_with_monitoring: {e}")
            return {
                'success': False,
                'error': str(e)
            }