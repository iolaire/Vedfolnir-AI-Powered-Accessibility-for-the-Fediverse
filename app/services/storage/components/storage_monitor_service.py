# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Monitor Service for tracking image storage usage.

This service monitors the storage/images directory to calculate total storage usage,
implements caching to avoid excessive I/O operations, and provides storage metrics
for the storage limit management system.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from .storage_configuration_service import StorageConfigurationService

logger = logging.getLogger(__name__)


@dataclass
class StorageMetrics:
    """Storage metrics data structure"""
    total_bytes: int
    total_gb: float
    limit_gb: float
    usage_percentage: float
    is_limit_exceeded: bool
    is_warning_exceeded: bool
    last_calculated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'total_bytes': self.total_bytes,
            'total_gb': self.total_gb,
            'limit_gb': self.limit_gb,
            'usage_percentage': self.usage_percentage,
            'is_limit_exceeded': self.is_limit_exceeded,
            'is_warning_exceeded': self.is_warning_exceeded,
            'last_calculated': self.last_calculated.isoformat()
        }


class StorageMonitorService:
    """
    Service for monitoring storage usage in the images directory.
    
    This service provides:
    - Directory scanning and size calculation
    - 5-minute caching mechanism to reduce I/O operations
    - Error handling for missing directories and permission issues
    - Storage metrics calculation and validation
    """
    
    # Cache duration: 5 minutes as specified in requirements
    CACHE_DURATION_SECONDS = 300  # 5 minutes
    
    # Storage directory path
    STORAGE_IMAGES_DIR = "storage/images"
    
    # Bytes to GB conversion factor
    BYTES_TO_GB = 1024 ** 3
    
    def __init__(self, config_service: Optional[StorageConfigurationService] = None):
        """
        Initialize the storage monitor service.
        
        Args:
            config_service: Storage configuration service instance
        """
        self.config_service = config_service or StorageConfigurationService()
        self._cached_metrics: Optional[StorageMetrics] = None
        self._cache_timestamp: Optional[datetime] = None
        
        # Ensure storage directory exists
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self) -> None:
        """
        Ensure the storage/images directory exists.
        
        Creates the directory if it doesn't exist, as specified in error handling requirements.
        """
        try:
            storage_path = Path(self.STORAGE_IMAGES_DIR)
            if not storage_path.exists():
                logger.info(f"Creating storage directory: {self.STORAGE_IMAGES_DIR}")
                storage_path.mkdir(parents=True, exist_ok=True)
            elif not storage_path.is_dir():
                logger.error(f"Storage path exists but is not a directory: {self.STORAGE_IMAGES_DIR}")
                raise ValueError(f"Storage path is not a directory: {self.STORAGE_IMAGES_DIR}")
        except Exception as e:
            logger.error(f"Failed to ensure storage directory exists: {e}")
            raise
    
    def _is_cache_valid(self) -> bool:
        """
        Check if the cached metrics are still valid (within 5-minute window).
        
        Returns:
            bool: True if cache is valid, False otherwise
        """
        if self._cached_metrics is None or self._cache_timestamp is None:
            return False
        
        cache_age = datetime.now() - self._cache_timestamp
        return cache_age.total_seconds() < self.CACHE_DURATION_SECONDS
    
    def _scan_directory_recursive(self, directory_path: Path) -> int:
        """
        Recursively scan directory and calculate total size of all files.
        
        Args:
            directory_path: Path to directory to scan
            
        Returns:
            int: Total size in bytes
            
        Raises:
            OSError: If directory access fails
        """
        total_size = 0
        
        try:
            # Use os.walk for efficient recursive directory traversal
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Get file size, following symlinks
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        logger.debug(f"File: {file_path}, Size: {file_size} bytes")
                    except (OSError, IOError) as e:
                        # Log individual file errors but continue processing
                        logger.warning(f"Could not get size for file {file_path}: {e}")
                        continue
                        
        except (OSError, IOError) as e:
            logger.error(f"Failed to scan directory {directory_path}: {e}")
            raise
        
        return total_size
    
    def calculate_total_storage_bytes(self) -> int:
        """
        Calculate total storage usage in bytes by scanning the storage/images directory.
        
        This method scans all files recursively in the storage/images directory
        and sums their sizes to get total storage usage.
        
        Returns:
            int: Total storage usage in bytes
            
        Raises:
            OSError: If directory cannot be accessed
        """
        storage_path = Path(self.STORAGE_IMAGES_DIR)
        
        # Handle missing directory case
        if not storage_path.exists():
            logger.warning(f"Storage directory does not exist: {self.STORAGE_IMAGES_DIR}")
            self._ensure_storage_directory()
            return 0
        
        if not storage_path.is_dir():
            logger.error(f"Storage path is not a directory: {self.STORAGE_IMAGES_DIR}")
            raise ValueError(f"Storage path is not a directory: {self.STORAGE_IMAGES_DIR}")
        
        try:
            total_bytes = self._scan_directory_recursive(storage_path)
            logger.info(f"Calculated total storage usage: {total_bytes} bytes ({total_bytes / self.BYTES_TO_GB:.2f} GB)")
            return total_bytes
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing storage directory: {e}")
            # Use cached value if available, otherwise raise
            if self._cached_metrics is not None:
                logger.warning("Using cached storage value due to permission error")
                return self._cached_metrics.total_bytes
            raise
            
        except OSError as e:
            logger.error(f"I/O error calculating storage usage: {e}")
            # Retry once as specified in error handling requirements
            try:
                logger.info("Retrying storage calculation after I/O error")
                time.sleep(1)  # Brief delay before retry
                total_bytes = self._scan_directory_recursive(storage_path)
                logger.info(f"Retry successful: {total_bytes} bytes")
                return total_bytes
            except OSError as retry_error:
                logger.error(f"Retry failed: {retry_error}")
                # Use cached value if available, otherwise default to safe mode
                if self._cached_metrics is not None:
                    logger.warning("Using cached storage value due to I/O error")
                    return self._cached_metrics.total_bytes
                else:
                    logger.error("No cached value available, defaulting to safe mode (assuming limit exceeded)")
                    # Return a value that would trigger safe mode (block generation)
                    return int(self.config_service.get_max_storage_gb() * self.BYTES_TO_GB * 1.1)
    
    def get_storage_usage_gb(self) -> float:
        """
        Get current storage usage in GB.
        
        Returns:
            float: Storage usage in GB
        """
        total_bytes = self.calculate_total_storage_bytes()
        return total_bytes / self.BYTES_TO_GB
    
    def get_storage_usage_percentage(self) -> float:
        """
        Get current storage usage as a percentage of the configured limit.
        
        Returns:
            float: Usage percentage (0-100+)
        """
        usage_gb = self.get_storage_usage_gb()
        limit_gb = self.config_service.get_max_storage_gb()
        
        if limit_gb <= 0:
            logger.error("Storage limit is zero or negative, cannot calculate percentage")
            return 100.0  # Assume limit exceeded for safety
        
        return (usage_gb / limit_gb) * 100.0
    
    def is_storage_limit_exceeded(self) -> bool:
        """
        Check if storage usage has reached or exceeded the configured limit.
        
        Returns:
            bool: True if limit is exceeded, False otherwise
        """
        usage_gb = self.get_storage_usage_gb()
        limit_gb = self.config_service.get_max_storage_gb()
        
        is_exceeded = usage_gb >= limit_gb
        
        if is_exceeded:
            logger.warning(f"Storage limit exceeded: {usage_gb:.2f}GB >= {limit_gb:.2f}GB")
        
        return is_exceeded
    
    def is_warning_threshold_exceeded(self) -> bool:
        """
        Check if storage usage has exceeded the warning threshold (80% by default).
        
        Returns:
            bool: True if warning threshold is exceeded, False otherwise
        """
        usage_gb = self.get_storage_usage_gb()
        warning_threshold_gb = self.config_service.get_warning_threshold_gb()
        
        is_exceeded = usage_gb >= warning_threshold_gb
        
        if is_exceeded:
            logger.warning(f"Storage warning threshold exceeded: {usage_gb:.2f}GB >= {warning_threshold_gb:.2f}GB")
        
        return is_exceeded
    
    def get_storage_metrics(self) -> StorageMetrics:
        """
        Get comprehensive storage metrics with caching.
        
        This method implements 5-minute caching to avoid excessive I/O operations
        as specified in the requirements.
        
        Returns:
            StorageMetrics: Complete storage metrics
        """
        # Check if cached metrics are still valid
        if self._is_cache_valid():
            logger.debug("Using cached storage metrics")
            return self._cached_metrics
        
        # Calculate fresh metrics
        logger.debug("Calculating fresh storage metrics")
        
        try:
            total_bytes = self.calculate_total_storage_bytes()
            total_gb = total_bytes / self.BYTES_TO_GB
            limit_gb = self.config_service.get_max_storage_gb()
            usage_percentage = (total_gb / limit_gb) * 100.0 if limit_gb > 0 else 100.0
            
            # Create metrics object
            metrics = StorageMetrics(
                total_bytes=total_bytes,
                total_gb=total_gb,
                limit_gb=limit_gb,
                usage_percentage=usage_percentage,
                is_limit_exceeded=total_gb >= limit_gb,
                is_warning_exceeded=total_gb >= self.config_service.get_warning_threshold_gb(),
                last_calculated=datetime.now()
            )
            
            # Cache the metrics
            self._cached_metrics = metrics
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Storage metrics calculated: {total_gb:.2f}GB / {limit_gb:.2f}GB ({usage_percentage:.1f}%)")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate storage metrics: {e}")
            
            # If we have cached metrics, return them even if expired
            if self._cached_metrics is not None:
                logger.warning("Returning expired cached metrics due to calculation error")
                return self._cached_metrics
            
            # If no cached metrics available, create safe default metrics
            logger.error("No cached metrics available, creating safe default metrics")
            limit_gb = self.config_service.get_max_storage_gb()
            safe_metrics = StorageMetrics(
                total_bytes=int(limit_gb * self.BYTES_TO_GB * 1.1),  # Assume over limit for safety
                total_gb=limit_gb * 1.1,
                limit_gb=limit_gb,
                usage_percentage=110.0,
                is_limit_exceeded=True,
                is_warning_exceeded=True,
                last_calculated=datetime.now()
            )
            
            return safe_metrics
    
    def invalidate_cache(self) -> None:
        """
        Invalidate the cached storage metrics.
        
        This forces the next call to get_storage_metrics() to recalculate
        the storage usage. Useful after cleanup operations.
        """
        logger.debug("Invalidating storage metrics cache")
        self._cached_metrics = None
        self._cache_timestamp = None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the current cache state.
        
        Returns:
            dict: Cache information including validity and age
        """
        if self._cache_timestamp is None:
            return {
                'has_cache': False,
                'is_valid': False,
                'cache_age_seconds': None,
                'cache_expires_in_seconds': None
            }
        
        cache_age = datetime.now() - self._cache_timestamp
        cache_age_seconds = cache_age.total_seconds()
        expires_in_seconds = max(0, self.CACHE_DURATION_SECONDS - cache_age_seconds)
        
        return {
            'has_cache': True,
            'is_valid': self._is_cache_valid(),
            'cache_age_seconds': cache_age_seconds,
            'cache_expires_in_seconds': expires_in_seconds,
            'cache_duration_seconds': self.CACHE_DURATION_SECONDS
        }