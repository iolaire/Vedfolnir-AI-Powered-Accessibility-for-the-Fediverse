# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Cleanup Integration Service for real-time storage monitoring and cleanup operations.

This service integrates storage monitoring with existing cleanup tools, provides
real-time storage recalculation after cleanup operations, and automatically lifts
storage limits when cleanup frees sufficient space.
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService, StorageMetrics
from storage_limit_enforcer import StorageLimitEnforcer
from scripts.maintenance.data_cleanup import DataCleanupManager

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Result of cleanup operation with storage impact"""
    operation_name: str
    items_cleaned: int
    storage_freed_bytes: int
    storage_freed_gb: float
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_name': self.operation_name,
            'items_cleaned': self.items_cleaned,
            'storage_freed_bytes': self.storage_freed_bytes,
            'storage_freed_gb': self.storage_freed_gb,
            'success': self.success,
            'error_message': self.error_message
        }


@dataclass
class StorageCleanupSummary:
    """Summary of cleanup operations and storage impact"""
    total_items_cleaned: int
    total_storage_freed_bytes: int
    total_storage_freed_gb: float
    operations: list[CleanupResult]
    storage_before: StorageMetrics
    storage_after: StorageMetrics
    limit_lifted: bool
    cleanup_duration_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'total_items_cleaned': self.total_items_cleaned,
            'total_storage_freed_bytes': self.total_storage_freed_bytes,
            'total_storage_freed_gb': self.total_storage_freed_gb,
            'operations': [op.to_dict() for op in self.operations],
            'storage_before': self.storage_before.to_dict(),
            'storage_after': self.storage_after.to_dict(),
            'limit_lifted': self.limit_lifted,
            'cleanup_duration_seconds': self.cleanup_duration_seconds
        }


class StorageCleanupIntegration:
    """
    Integration service for storage monitoring and cleanup operations.
    
    This service provides:
    - Real-time storage recalculation after cleanup operations
    - Automatic storage limit lifting when cleanup frees sufficient space
    - Integration with existing cleanup tools and data cleanup manager
    - Storage impact tracking and reporting
    - Cleanup operation callbacks and hooks
    """
    
    def __init__(self, 
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None,
                 enforcer_service: Optional[StorageLimitEnforcer] = None,
                 cleanup_manager: Optional[DataCleanupManager] = None,
                 db_manager=None):
        """
        Initialize the storage cleanup integration service.
        
        Args:
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
            enforcer_service: Storage limit enforcer service instance
            cleanup_manager: Data cleanup manager instance
            db_manager: Database manager for cleanup operations
        """
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        self.enforcer_service = enforcer_service or StorageLimitEnforcer(
            self.config_service, 
            self.monitor_service,
            db_manager=db_manager
        )
        
        # Initialize cleanup manager if not provided
        if cleanup_manager is None and db_manager is not None:
            try:
                from config import Config
                config = Config()
                self.cleanup_manager = DataCleanupManager(db_manager, config)
            except Exception as e:
                logger.warning(f"Could not initialize cleanup manager: {e}")
                self.cleanup_manager = None
        else:
            self.cleanup_manager = cleanup_manager
        
        self.db_manager = db_manager
        
        # Cleanup operation callbacks
        self._pre_cleanup_callbacks: list[Callable] = []
        self._post_cleanup_callbacks: list[Callable] = []
        
        logger.info("Storage cleanup integration service initialized")
    
    def register_pre_cleanup_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called before cleanup operations.
        
        Args:
            callback: Function to call before cleanup
        """
        self._pre_cleanup_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', str(callback))
        logger.debug(f"Registered pre-cleanup callback: {callback_name}")
    
    def register_post_cleanup_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called after cleanup operations.
        
        Args:
            callback: Function to call after cleanup (receives CleanupResult)
        """
        self._post_cleanup_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', str(callback))
        logger.debug(f"Registered post-cleanup callback: {callback_name}")
    
    def _execute_pre_cleanup_callbacks(self) -> None:
        """Execute all registered pre-cleanup callbacks"""
        for callback in self._pre_cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in pre-cleanup callback {callback.__name__}: {e}")
    
    def _execute_post_cleanup_callbacks(self, result: CleanupResult) -> None:
        """Execute all registered post-cleanup callbacks"""
        for callback in self._post_cleanup_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in post-cleanup callback {callback.__name__}: {e}")
    
    def get_storage_metrics_before_cleanup(self) -> StorageMetrics:
        """
        Get storage metrics before cleanup operation.
        
        Returns:
            StorageMetrics: Current storage metrics
        """
        return self.monitor_service.get_storage_metrics()
    
    def recalculate_storage_after_cleanup(self) -> StorageMetrics:
        """
        Recalculate storage metrics after cleanup operation.
        
        This method invalidates the cache and forces a fresh calculation
        to get accurate post-cleanup storage usage.
        
        Returns:
            StorageMetrics: Updated storage metrics after cleanup
        """
        logger.debug("Recalculating storage metrics after cleanup")
        
        # Invalidate cache to force fresh calculation
        self.monitor_service.invalidate_cache()
        
        # Get fresh storage metrics
        updated_metrics = self.monitor_service.get_storage_metrics()
        
        logger.info(f"Storage recalculated after cleanup: {updated_metrics.total_gb:.2f}GB / {updated_metrics.limit_gb:.2f}GB ({updated_metrics.usage_percentage:.1f}%)")
        
        return updated_metrics
    
    def check_and_lift_storage_limits(self, storage_after: StorageMetrics) -> bool:
        """
        Check if storage limits should be lifted after cleanup.
        
        Args:
            storage_after: Storage metrics after cleanup
            
        Returns:
            bool: True if limits were lifted, False otherwise
        """
        try:
            # Check if storage is now under the limit
            if not storage_after.is_limit_exceeded:
                # Check if caption generation is currently blocked
                if self.enforcer_service.is_caption_generation_blocked():
                    logger.info("Storage is now under limit after cleanup, lifting storage blocking")
                    self.enforcer_service.unblock_caption_generation()
                    return True
                else:
                    logger.debug("Storage is under limit and caption generation is not blocked")
                    return False
            else:
                logger.info(f"Storage still exceeds limit after cleanup: {storage_after.total_gb:.2f}GB >= {storage_after.limit_gb:.2f}GB")
                return False
                
        except Exception as e:
            logger.error(f"Error checking and lifting storage limits: {e}")
            return False
    
    def cleanup_old_processing_runs_with_monitoring(self, days: int = None, dry_run: bool = False) -> CleanupResult:
        """
        Clean up old processing runs with storage monitoring.
        
        Args:
            days: Number of days for retention (optional)
            dry_run: Whether to perform a dry run
            
        Returns:
            CleanupResult: Result of cleanup operation
        """
        operation_name = "cleanup_old_processing_runs"
        logger.info(f"Starting {operation_name} with storage monitoring (dry_run={dry_run})")
        
        if not self.cleanup_manager:
            return CleanupResult(
                operation_name=operation_name,
                items_cleaned=0,
                storage_freed_bytes=0,
                storage_freed_gb=0.0,
                success=False,
                error_message="Cleanup manager not available"
            )
        
        try:
            # Execute pre-cleanup callbacks
            self._execute_pre_cleanup_callbacks()
            
            # Get storage before cleanup
            storage_before = self.get_storage_metrics_before_cleanup()
            
            # Perform cleanup operation
            items_cleaned = self.cleanup_manager.archive_old_processing_runs(days=days, dry_run=dry_run)
            
            # Calculate storage impact (processing runs don't directly free storage)
            storage_freed_bytes = 0
            storage_freed_gb = 0.0
            
            result = CleanupResult(
                operation_name=operation_name,
                items_cleaned=items_cleaned,
                storage_freed_bytes=storage_freed_bytes,
                storage_freed_gb=storage_freed_gb,
                success=True
            )
            
            # Execute post-cleanup callbacks
            self._execute_post_cleanup_callbacks(result)
            
            logger.info(f"Completed {operation_name}: {items_cleaned} items cleaned")
            return result
            
        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}")
            return CleanupResult(
                operation_name=operation_name,
                items_cleaned=0,
                storage_freed_bytes=0,
                storage_freed_gb=0.0,
                success=False,
                error_message=str(e)
            )
    
    def cleanup_old_images_with_monitoring(self, status=None, days: int = None, dry_run: bool = False) -> CleanupResult:
        """
        Clean up old images with storage monitoring and real-time recalculation.
        
        Args:
            status: Image status to clean up (optional)
            days: Number of days for retention (optional)
            dry_run: Whether to perform a dry run
            
        Returns:
            CleanupResult: Result of cleanup operation with storage impact
        """
        operation_name = f"cleanup_old_images_{status.value if status else 'all'}"
        logger.info(f"Starting {operation_name} with storage monitoring (dry_run={dry_run})")
        
        if not self.cleanup_manager:
            return CleanupResult(
                operation_name=operation_name,
                items_cleaned=0,
                storage_freed_bytes=0,
                storage_freed_gb=0.0,
                success=False,
                error_message="Cleanup manager not available"
            )
        
        try:
            # Execute pre-cleanup callbacks
            self._execute_pre_cleanup_callbacks()
            
            # Get storage before cleanup
            storage_before = self.get_storage_metrics_before_cleanup()
            
            # Perform cleanup operation
            items_cleaned = self.cleanup_manager.cleanup_old_images(status=status, days=days, dry_run=dry_run)
            
            # Recalculate storage after cleanup (only if not dry run)
            if not dry_run and items_cleaned > 0:
                storage_after = self.recalculate_storage_after_cleanup()
                
                # Calculate storage freed
                storage_freed_bytes = max(0, storage_before.total_bytes - storage_after.total_bytes)
                storage_freed_gb = storage_freed_bytes / (1024 ** 3)
                
                logger.info(f"Storage freed by {operation_name}: {storage_freed_gb:.2f}GB ({items_cleaned} items)")
            else:
                storage_freed_bytes = 0
                storage_freed_gb = 0.0
            
            result = CleanupResult(
                operation_name=operation_name,
                items_cleaned=items_cleaned,
                storage_freed_bytes=storage_freed_bytes,
                storage_freed_gb=storage_freed_gb,
                success=True
            )
            
            # Execute post-cleanup callbacks
            self._execute_post_cleanup_callbacks(result)
            
            logger.info(f"Completed {operation_name}: {items_cleaned} items cleaned, {storage_freed_gb:.2f}GB freed")
            return result
            
        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}")
            return CleanupResult(
                operation_name=operation_name,
                items_cleaned=0,
                storage_freed_bytes=0,
                storage_freed_gb=0.0,
                success=False,
                error_message=str(e)
            )
    
    def cleanup_storage_images_with_monitoring(self, dry_run: bool = False) -> CleanupResult:
        """
        Clean up storage images with monitoring and real-time recalculation.
        
        Args:
            dry_run: Whether to perform a dry run
            
        Returns:
            CleanupResult: Result of cleanup operation with storage impact
        """
        operation_name = "cleanup_storage_images"
        logger.info(f"Starting {operation_name} with storage monitoring (dry_run={dry_run})")
        
        if not self.cleanup_manager:
            return CleanupResult(
                operation_name=operation_name,
                items_cleaned=0,
                storage_freed_bytes=0,
                storage_freed_gb=0.0,
                success=False,
                error_message="Cleanup manager not available"
            )
        
        try:
            # Execute pre-cleanup callbacks
            self._execute_pre_cleanup_callbacks()
            
            # Get storage before cleanup
            storage_before = self.get_storage_metrics_before_cleanup()
            
            # Perform cleanup operation
            items_cleaned = self.cleanup_manager.cleanup_storage_images(dry_run=dry_run)
            
            # Recalculate storage after cleanup (only if not dry run)
            if not dry_run and items_cleaned > 0:
                storage_after = self.recalculate_storage_after_cleanup()
                
                # Calculate storage freed
                storage_freed_bytes = max(0, storage_before.total_bytes - storage_after.total_bytes)
                storage_freed_gb = storage_freed_bytes / (1024 ** 3)
                
                logger.info(f"Storage freed by {operation_name}: {storage_freed_gb:.2f}GB ({items_cleaned} files)")
            else:
                storage_freed_bytes = 0
                storage_freed_gb = 0.0
            
            result = CleanupResult(
                operation_name=operation_name,
                items_cleaned=items_cleaned,
                storage_freed_bytes=storage_freed_bytes,
                storage_freed_gb=storage_freed_gb,
                success=True
            )
            
            # Execute post-cleanup callbacks
            self._execute_post_cleanup_callbacks(result)
            
            logger.info(f"Completed {operation_name}: {items_cleaned} files cleaned, {storage_freed_gb:.2f}GB freed")
            return result
            
        except Exception as e:
            logger.error(f"Error in {operation_name}: {e}")
            return CleanupResult(
                operation_name=operation_name,
                items_cleaned=0,
                storage_freed_bytes=0,
                storage_freed_gb=0.0,
                success=False,
                error_message=str(e)
            )
    
    def run_full_cleanup_with_monitoring(self, dry_run: bool = False) -> StorageCleanupSummary:
        """
        Run full cleanup with comprehensive storage monitoring and automatic limit lifting.
        
        Args:
            dry_run: Whether to perform a dry run
            
        Returns:
            StorageCleanupSummary: Complete summary of cleanup operations and storage impact
        """
        logger.info(f"Starting full cleanup with storage monitoring (dry_run={dry_run})")
        start_time = datetime.now()
        
        # Get storage metrics before cleanup
        storage_before = self.get_storage_metrics_before_cleanup()
        logger.info(f"Storage before cleanup: {storage_before.total_gb:.2f}GB / {storage_before.limit_gb:.2f}GB ({storage_before.usage_percentage:.1f}%)")
        
        operations = []
        
        try:
            # Execute pre-cleanup callbacks
            self._execute_pre_cleanup_callbacks()
            
            # 1. Archive old processing runs
            result = self.cleanup_old_processing_runs_with_monitoring(dry_run=dry_run)
            operations.append(result)
            
            # 2. Clean up old rejected images
            from models import ProcessingStatus
            result = self.cleanup_old_images_with_monitoring(status=ProcessingStatus.REJECTED, dry_run=dry_run)
            operations.append(result)
            
            # 3. Clean up old posted images
            result = self.cleanup_old_images_with_monitoring(status=ProcessingStatus.POSTED, dry_run=dry_run)
            operations.append(result)
            
            # 4. Clean up old error images
            result = self.cleanup_old_images_with_monitoring(status=ProcessingStatus.ERROR, dry_run=dry_run)
            operations.append(result)
            
            # 5. Clean up orphaned posts
            if self.cleanup_manager:
                try:
                    items_cleaned = self.cleanup_manager.cleanup_orphaned_posts(dry_run=dry_run)
                    result = CleanupResult(
                        operation_name="cleanup_orphaned_posts",
                        items_cleaned=items_cleaned,
                        storage_freed_bytes=0,
                        storage_freed_gb=0.0,
                        success=True
                    )
                    operations.append(result)
                except Exception as e:
                    logger.error(f"Error cleaning up orphaned posts: {e}")
                    operations.append(CleanupResult(
                        operation_name="cleanup_orphaned_posts",
                        items_cleaned=0,
                        storage_freed_bytes=0,
                        storage_freed_gb=0.0,
                        success=False,
                        error_message=str(e)
                    ))
            
            # 6. Clean up storage images (major storage impact)
            result = self.cleanup_storage_images_with_monitoring(dry_run=dry_run)
            operations.append(result)
            
            # Get final storage metrics after all cleanup operations
            if not dry_run:
                storage_after = self.recalculate_storage_after_cleanup()
                
                # Check if storage limits should be lifted
                limit_lifted = self.check_and_lift_storage_limits(storage_after)
                
                if limit_lifted:
                    logger.info("Storage limits automatically lifted after cleanup")
                
            else:
                storage_after = storage_before  # No change in dry run
                limit_lifted = False
            
            # Calculate totals
            total_items_cleaned = sum(op.items_cleaned for op in operations if op.success)
            total_storage_freed_bytes = sum(op.storage_freed_bytes for op in operations if op.success)
            total_storage_freed_gb = total_storage_freed_bytes / (1024 ** 3)
            
            # Calculate cleanup duration
            cleanup_duration = (datetime.now() - start_time).total_seconds()
            
            # Create summary
            summary = StorageCleanupSummary(
                total_items_cleaned=total_items_cleaned,
                total_storage_freed_bytes=total_storage_freed_bytes,
                total_storage_freed_gb=total_storage_freed_gb,
                operations=operations,
                storage_before=storage_before,
                storage_after=storage_after,
                limit_lifted=limit_lifted,
                cleanup_duration_seconds=cleanup_duration
            )
            
            logger.info(f"Full cleanup completed in {cleanup_duration:.1f}s:")
            logger.info(f"  - Total items cleaned: {total_items_cleaned}")
            logger.info(f"  - Total storage freed: {total_storage_freed_gb:.2f}GB")
            logger.info(f"  - Storage before: {storage_before.total_gb:.2f}GB ({storage_before.usage_percentage:.1f}%)")
            logger.info(f"  - Storage after: {storage_after.total_gb:.2f}GB ({storage_after.usage_percentage:.1f}%)")
            logger.info(f"  - Limits lifted: {limit_lifted}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error during full cleanup: {e}")
            
            # Return partial summary with error
            cleanup_duration = (datetime.now() - start_time).total_seconds()
            
            return StorageCleanupSummary(
                total_items_cleaned=sum(op.items_cleaned for op in operations if op.success),
                total_storage_freed_bytes=sum(op.storage_freed_bytes for op in operations if op.success),
                total_storage_freed_gb=sum(op.storage_freed_bytes for op in operations if op.success) / (1024 ** 3),
                operations=operations,
                storage_before=storage_before,
                storage_after=storage_before,  # No change due to error
                limit_lifted=False,
                cleanup_duration_seconds=cleanup_duration
            )
    
    def get_storage_cleanup_warnings(self) -> Dict[str, Any]:
        """
        Get storage-related warnings for display in cleanup interface.
        
        Returns:
            Dict containing storage warnings and recommendations
        """
        try:
            # Get current storage metrics
            metrics = self.monitor_service.get_storage_metrics()
            
            warnings = []
            recommendations = []
            urgency_level = "normal"
            
            # Check storage status and generate warnings
            if metrics.is_limit_exceeded:
                warnings.append({
                    'type': 'critical',
                    'title': 'Storage Limit Exceeded',
                    'message': f'Storage usage ({metrics.total_gb:.1f}GB) has exceeded the limit ({metrics.limit_gb:.1f}GB). Caption generation is blocked.',
                    'icon': 'bi-exclamation-triangle-fill'
                })
                recommendations.append('Immediately clean up old images and files to restore normal operation')
                recommendations.append('Consider increasing the storage limit if cleanup is not sufficient')
                urgency_level = "critical"
                
            elif metrics.is_warning_exceeded:
                warning_threshold_gb = self.config_service.get_warning_threshold_gb()
                warnings.append({
                    'type': 'warning',
                    'title': 'Storage Warning Threshold Exceeded',
                    'message': f'Storage usage ({metrics.total_gb:.1f}GB) has exceeded the warning threshold ({warning_threshold_gb:.1f}GB).',
                    'icon': 'bi-exclamation-triangle'
                })
                recommendations.append('Clean up old images and files to prevent reaching the storage limit')
                recommendations.append('Monitor storage usage regularly')
                urgency_level = "warning"
                
            elif metrics.usage_percentage > 60:
                warnings.append({
                    'type': 'info',
                    'title': 'Storage Usage High',
                    'message': f'Storage usage is at {metrics.usage_percentage:.1f}%. Consider cleanup to maintain optimal performance.',
                    'icon': 'bi-info-circle'
                })
                recommendations.append('Regular cleanup helps maintain optimal system performance')
                urgency_level = "info"
            
            # Check if caption generation is blocked
            is_blocked = self.enforcer_service.is_caption_generation_blocked()
            if is_blocked:
                block_reason = self.enforcer_service.get_block_reason()
                warnings.append({
                    'type': 'critical',
                    'title': 'Caption Generation Blocked',
                    'message': f'Caption generation is currently blocked: {block_reason}',
                    'icon': 'bi-lock-fill'
                })
                recommendations.append('Clean up storage to automatically restore caption generation')
            
            # Estimate cleanup potential
            cleanup_potential = self._estimate_cleanup_potential()
            
            return {
                'warnings': warnings,
                'recommendations': recommendations,
                'urgency_level': urgency_level,
                'current_usage_gb': metrics.total_gb,
                'limit_gb': metrics.limit_gb,
                'usage_percentage': metrics.usage_percentage,
                'available_space_gb': max(0, metrics.limit_gb - metrics.total_gb),
                'is_blocked': is_blocked,
                'cleanup_potential': cleanup_potential,
                'last_calculated': metrics.last_calculated.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting storage cleanup warnings: {e}")
            return {
                'warnings': [{
                    'type': 'error',
                    'title': 'Storage Monitoring Error',
                    'message': f'Unable to check storage status: {str(e)}',
                    'icon': 'bi-exclamation-triangle-fill'
                }],
                'recommendations': ['Check storage monitoring system configuration'],
                'urgency_level': 'critical',
                'error': str(e)
            }
    
    def _estimate_cleanup_potential(self) -> Dict[str, Any]:
        """
        Estimate potential storage savings from cleanup operations.
        
        Returns:
            Dict containing cleanup potential estimates
        """
        try:
            if not self.cleanup_manager or not self.db_manager:
                return {'available': False, 'reason': 'Cleanup manager not available'}
            
            # This is a simplified estimation - in a real implementation,
            # you might query the database to get more accurate estimates
            
            with self.db_manager.get_session() as session:
                from models import Image, ProcessingStatus
                from datetime import timedelta
                
                # Estimate rejected images older than 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                rejected_count = session.query(Image).filter(
                    Image.status == ProcessingStatus.REJECTED,
                    Image.reviewed_at < cutoff_date
                ).count()
                
                # Estimate posted images older than 30 days
                cutoff_date = datetime.now() - timedelta(days=30)
                posted_count = session.query(Image).filter(
                    Image.status == ProcessingStatus.POSTED,
                    Image.posted_at < cutoff_date
                ).count()
                
                # Rough estimate: average image size ~500KB
                avg_image_size_bytes = 500 * 1024
                estimated_savings_bytes = (rejected_count + posted_count) * avg_image_size_bytes
                estimated_savings_gb = estimated_savings_bytes / (1024 ** 3)
                
                return {
                    'available': True,
                    'rejected_images_count': rejected_count,
                    'posted_images_count': posted_count,
                    'total_images_count': rejected_count + posted_count,
                    'estimated_savings_bytes': estimated_savings_bytes,
                    'estimated_savings_gb': estimated_savings_gb,
                    'note': 'Estimates based on default retention periods and average image sizes'
                }
                
        except Exception as e:
            logger.error(f"Error estimating cleanup potential: {e}")
            return {'available': False, 'reason': f'Error: {str(e)}'}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the storage cleanup integration system.
        
        Returns:
            Dict containing health check results
        """
        health = {
            'config_service_healthy': False,
            'monitor_service_healthy': False,
            'enforcer_service_healthy': False,
            'cleanup_manager_available': False,
            'overall_healthy': False
        }
        
        try:
            # Check config service
            self.config_service.validate_storage_config()
            health['config_service_healthy'] = True
        except Exception as e:
            health['config_error'] = str(e)
        
        try:
            # Check monitor service
            self.monitor_service.get_storage_metrics()
            health['monitor_service_healthy'] = True
        except Exception as e:
            health['monitor_error'] = str(e)
        
        try:
            # Check enforcer service
            enforcer_health = self.enforcer_service.health_check()
            health['enforcer_service_healthy'] = enforcer_health.get('overall_healthy', False)
            if not health['enforcer_service_healthy']:
                health['enforcer_error'] = enforcer_health
        except Exception as e:
            health['enforcer_error'] = str(e)
        
        # Check cleanup manager availability
        health['cleanup_manager_available'] = self.cleanup_manager is not None
        if not health['cleanup_manager_available']:
            health['cleanup_manager_error'] = 'Cleanup manager not initialized'
        
        # Overall health
        health['overall_healthy'] = all([
            health['config_service_healthy'],
            health['monitor_service_healthy'],
            health['enforcer_service_healthy'],
            health['cleanup_manager_available']
        ])
        
        return health