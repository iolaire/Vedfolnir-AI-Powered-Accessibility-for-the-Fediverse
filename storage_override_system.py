# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Storage Override System for managing manual storage limit overrides.

This service provides time-limited override functionality for administrators,
allowing temporary bypassing of storage limits during emergency situations.
Includes automatic expiration, cleanup, and comprehensive audit logging.
"""

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from database import DatabaseManager
from models import StorageOverride, StorageEventLog, User, UserRole
from storage_configuration_service import StorageConfigurationService
from storage_monitor_service import StorageMonitorService

logger = logging.getLogger(__name__)


@dataclass
class OverrideInfo:
    """Information about a storage override"""
    id: int
    admin_user_id: int
    admin_username: str
    activated_at: datetime
    expires_at: datetime
    duration_hours: int
    reason: str
    is_active: bool
    is_expired: bool
    remaining_time: Optional[timedelta]
    storage_gb_at_activation: Optional[float]
    limit_gb_at_activation: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'admin_user_id': self.admin_user_id,
            'admin_username': self.admin_username,
            'activated_at': self.activated_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'duration_hours': self.duration_hours,
            'reason': self.reason,
            'is_active': self.is_active,
            'is_expired': self.is_expired,
            'remaining_time_seconds': self.remaining_time.total_seconds() if self.remaining_time else None,
            'storage_gb_at_activation': self.storage_gb_at_activation,
            'limit_gb_at_activation': self.limit_gb_at_activation
        }


class StorageOverrideSystemError(Exception):
    """Base storage override system error"""
    pass


class OverrideValidationError(StorageOverrideSystemError):
    """Override validation failed"""
    pass


class OverrideNotFoundError(StorageOverrideSystemError):
    """Override not found"""
    pass


class StorageOverrideSystem:
    """
    Storage override system with time-limited override functionality.
    
    This service provides:
    - Time-limited storage limit overrides for administrators
    - Automatic override expiration and cleanup
    - Comprehensive audit logging for all override actions
    - Admin authorization and validation
    - Thread-safe operations with proper locking
    """
    
    # Default and maximum override durations
    DEFAULT_OVERRIDE_DURATION_HOURS = 1
    MAX_OVERRIDE_DURATION_HOURS = 24
    MIN_OVERRIDE_DURATION_HOURS = 1
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 config_service: Optional[StorageConfigurationService] = None,
                 monitor_service: Optional[StorageMonitorService] = None):
        """
        Initialize the storage override system.
        
        Args:
            db_manager: Database manager instance
            config_service: Storage configuration service instance
            monitor_service: Storage monitor service instance
        """
        self.db_manager = db_manager
        self.config_service = config_service or StorageConfigurationService()
        self.monitor_service = monitor_service or StorageMonitorService(self.config_service)
        
        # Thread safety
        self._override_lock = threading.RLock()
        
        logger.info("Storage override system initialized")
    
    def _validate_admin_user(self, admin_user_id: int) -> User:
        """
        Validate that the user is an admin and can create overrides.
        
        Args:
            admin_user_id: ID of the admin user
            
        Returns:
            User: The validated admin user
            
        Raises:
            OverrideValidationError: If user is not valid admin
        """
        with self.db_manager.get_session() as session:
            user = session.query(User).filter_by(id=admin_user_id).first()
            
            if not user:
                raise OverrideValidationError(f"User with ID {admin_user_id} not found")
            
            if not user.is_active:
                raise OverrideValidationError(f"User {user.username} is not active")
            
            if user.role != UserRole.ADMIN:
                raise OverrideValidationError(f"User {user.username} does not have admin privileges")
            
            return user
    
    def _validate_override_duration(self, duration_hours: int) -> None:
        """
        Validate override duration is within acceptable limits.
        
        Args:
            duration_hours: Duration in hours
            
        Raises:
            OverrideValidationError: If duration is invalid
        """
        if not isinstance(duration_hours, int):
            raise OverrideValidationError("Duration must be an integer")
        
        if duration_hours < self.MIN_OVERRIDE_DURATION_HOURS:
            raise OverrideValidationError(f"Duration must be at least {self.MIN_OVERRIDE_DURATION_HOURS} hour(s)")
        
        if duration_hours > self.MAX_OVERRIDE_DURATION_HOURS:
            raise OverrideValidationError(f"Duration cannot exceed {self.MAX_OVERRIDE_DURATION_HOURS} hours")
    
    def activate_override(self, 
                         admin_user_id: int, 
                         duration_hours: int = DEFAULT_OVERRIDE_DURATION_HOURS,
                         reason: Optional[str] = None) -> OverrideInfo:
        """
        Activate a time-limited storage override.
        
        Args:
            admin_user_id: ID of the admin user activating the override
            duration_hours: Duration of the override in hours (1-24)
            reason: Optional reason for the override
            
        Returns:
            OverrideInfo: Information about the activated override
            
        Raises:
            OverrideValidationError: If validation fails
            StorageOverrideSystemError: If activation fails
        """
        with self._override_lock:
            try:
                # Validate admin user
                admin_user = self._validate_admin_user(admin_user_id)
                
                # Validate duration
                self._validate_override_duration(duration_hours)
                
                # Check if there's already an active override
                existing_override = self.get_active_override()
                if existing_override:
                    raise OverrideValidationError(
                        f"An override is already active (ID: {existing_override.id}, "
                        f"expires: {existing_override.expires_at})"
                    )
                
                # Get current storage metrics for context
                try:
                    metrics = self.monitor_service.get_storage_metrics()
                    storage_gb = metrics.total_gb
                    limit_gb = metrics.limit_gb
                except Exception as e:
                    logger.warning(f"Could not get storage metrics for override context: {e}")
                    storage_gb = None
                    limit_gb = None
                
                # Create the override
                with self.db_manager.get_session() as session:
                    activated_at = datetime.utcnow()
                    expires_at = activated_at + timedelta(hours=duration_hours)
                    
                    override = StorageOverride(
                        admin_user_id=admin_user_id,
                        activated_at=activated_at,
                        expires_at=expires_at,
                        duration_hours=duration_hours,
                        reason=reason or f"Manual override by {admin_user.username}",
                        is_active=True,
                        storage_gb_at_activation=storage_gb,
                        limit_gb_at_activation=limit_gb
                    )
                    
                    session.add(override)
                    session.flush()  # Get the ID
                    
                    # Log the activation event
                    event = StorageEventLog.log_event(
                        session=session,
                        event_type="override_activated",
                        storage_gb=storage_gb or 0,
                        limit_gb=limit_gb or 0,
                        user_id=admin_user_id,
                        details={
                            'override_id': override.id,
                            'duration_hours': duration_hours,
                            'reason': override.reason,
                            'admin_username': admin_user.username
                        },
                        storage_override_id=override.id
                    )
                    
                    session.commit()
                    
                    logger.info(f"Storage override activated by {admin_user.username} "
                              f"(ID: {override.id}, duration: {duration_hours}h, reason: {override.reason})")
                    
                    # Create and return override info
                    return OverrideInfo(
                        id=override.id,
                        admin_user_id=admin_user_id,
                        admin_username=admin_user.username,
                        activated_at=activated_at,
                        expires_at=expires_at,
                        duration_hours=duration_hours,
                        reason=override.reason,
                        is_active=True,
                        is_expired=False,
                        remaining_time=expires_at - datetime.utcnow(),
                        storage_gb_at_activation=storage_gb,
                        limit_gb_at_activation=limit_gb
                    )
                    
            except OverrideValidationError:
                raise
            except Exception as e:
                logger.error(f"Error activating storage override: {e}")
                raise StorageOverrideSystemError(f"Failed to activate override: {e}")
    
    def deactivate_override(self, 
                           admin_user_id: int,
                           override_id: Optional[int] = None,
                           reason: Optional[str] = None) -> bool:
        """
        Manually deactivate a storage override.
        
        Args:
            admin_user_id: ID of the admin user deactivating the override
            override_id: Specific override ID to deactivate (optional, defaults to active override)
            reason: Optional reason for deactivation
            
        Returns:
            bool: True if override was deactivated, False if no active override found
            
        Raises:
            OverrideValidationError: If validation fails
            StorageOverrideSystemError: If deactivation fails
        """
        with self._override_lock:
            try:
                # Validate admin user
                admin_user = self._validate_admin_user(admin_user_id)
                
                with self.db_manager.get_session() as session:
                    # Find the override to deactivate
                    if override_id:
                        override = session.query(StorageOverride).filter_by(id=override_id).first()
                        if not override:
                            raise OverrideNotFoundError(f"Override with ID {override_id} not found")
                    else:
                        # Find the currently active override
                        override = session.query(StorageOverride).filter_by(
                            is_active=True
                        ).filter(
                            StorageOverride.expires_at > datetime.utcnow()
                        ).first()
                        
                        if not override:
                            logger.info(f"No active override found to deactivate by {admin_user.username}")
                            return False
                    
                    # Check if override is already deactivated
                    if not override.is_active:
                        logger.info(f"Override {override.id} is already deactivated")
                        return False
                    
                    # Deactivate the override
                    deactivation_reason = reason or f"Manual deactivation by {admin_user.username}"
                    override.deactivate(admin_user_id, deactivation_reason)
                    
                    # Get current storage metrics for logging
                    try:
                        metrics = self.monitor_service.get_storage_metrics()
                        storage_gb = metrics.total_gb
                        limit_gb = metrics.limit_gb
                    except Exception as e:
                        logger.warning(f"Could not get storage metrics for deactivation logging: {e}")
                        storage_gb = override.storage_gb_at_activation or 0
                        limit_gb = override.limit_gb_at_activation or 0
                    
                    # Log the deactivation event
                    event = StorageEventLog.log_event(
                        session=session,
                        event_type="override_deactivated",
                        storage_gb=storage_gb,
                        limit_gb=limit_gb,
                        user_id=admin_user_id,
                        details={
                            'override_id': override.id,
                            'deactivation_reason': deactivation_reason,
                            'admin_username': admin_user.username,
                            'original_duration_hours': override.duration_hours,
                            'time_remaining_minutes': (override.expires_at - datetime.utcnow()).total_seconds() / 60
                        },
                        storage_override_id=override.id
                    )
                    
                    session.commit()
                    
                    logger.info(f"Storage override {override.id} deactivated by {admin_user.username}: {deactivation_reason}")
                    return True
                    
            except (OverrideValidationError, OverrideNotFoundError):
                raise
            except Exception as e:
                logger.error(f"Error deactivating storage override: {e}")
                raise StorageOverrideSystemError(f"Failed to deactivate override: {e}")
    
    def is_override_active(self) -> bool:
        """
        Check if there is currently an active storage override.
        
        Returns:
            bool: True if an active override exists, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                active_override = session.query(StorageOverride).filter_by(
                    is_active=True
                ).filter(
                    StorageOverride.expires_at > datetime.utcnow()
                ).first()
                
                return active_override is not None
                
        except Exception as e:
            logger.error(f"Error checking override status: {e}")
            # Default to False (no override) on error
            return False
    
    def get_active_override(self) -> Optional[OverrideInfo]:
        """
        Get information about the currently active override.
        
        Returns:
            OverrideInfo: Information about the active override, or None if no active override
        """
        try:
            with self.db_manager.get_session() as session:
                override = session.query(StorageOverride).filter_by(
                    is_active=True
                ).filter(
                    StorageOverride.expires_at > datetime.utcnow()
                ).first()
                
                if not override:
                    return None
                
                # Get admin user info
                admin_user = session.query(User).filter_by(id=override.admin_user_id).first()
                admin_username = admin_user.username if admin_user else f"User {override.admin_user_id}"
                
                # Calculate remaining time
                now = datetime.utcnow()
                remaining_time = override.expires_at - now if override.expires_at > now else None
                
                return OverrideInfo(
                    id=override.id,
                    admin_user_id=override.admin_user_id,
                    admin_username=admin_username,
                    activated_at=override.activated_at,
                    expires_at=override.expires_at,
                    duration_hours=override.duration_hours,
                    reason=override.reason or "",
                    is_active=override.is_active,
                    is_expired=override.is_expired(),
                    remaining_time=remaining_time,
                    storage_gb_at_activation=override.storage_gb_at_activation,
                    limit_gb_at_activation=override.limit_gb_at_activation
                )
                
        except Exception as e:
            logger.error(f"Error getting active override: {e}")
            return None
    
    def get_override_remaining_time(self) -> Optional[timedelta]:
        """
        Get remaining time for the active override.
        
        Returns:
            timedelta: Remaining time, or None if no active override
        """
        active_override = self.get_active_override()
        return active_override.remaining_time if active_override else None
    
    def cleanup_expired_overrides(self) -> int:
        """
        Clean up expired overrides by marking them as inactive.
        
        This method should be called periodically to ensure expired overrides
        are properly cleaned up and logged.
        
        Returns:
            int: Number of overrides cleaned up
        """
        try:
            with self.db_manager.get_session() as session:
                # Find expired but still active overrides
                expired_overrides = session.query(StorageOverride).filter_by(
                    is_active=True
                ).filter(
                    StorageOverride.expires_at <= datetime.utcnow()
                ).all()
                
                cleanup_count = 0
                
                for override in expired_overrides:
                    # Mark as inactive
                    override.is_active = False
                    override.deactivated_at = datetime.utcnow()
                    
                    # Get current storage metrics for logging
                    try:
                        metrics = self.monitor_service.get_storage_metrics()
                        storage_gb = metrics.total_gb
                        limit_gb = metrics.limit_gb
                    except Exception as e:
                        logger.warning(f"Could not get storage metrics for cleanup logging: {e}")
                        storage_gb = override.storage_gb_at_activation or 0
                        limit_gb = override.limit_gb_at_activation or 0
                    
                    # Log the expiration event
                    event = StorageEventLog.log_event(
                        session=session,
                        event_type="override_expired",
                        storage_gb=storage_gb,
                        limit_gb=limit_gb,
                        user_id=override.admin_user_id,
                        details={
                            'override_id': override.id,
                            'duration_hours': override.duration_hours,
                            'reason': override.reason,
                            'expired_at': datetime.utcnow().isoformat()
                        },
                        storage_override_id=override.id
                    )
                    
                    cleanup_count += 1
                    logger.info(f"Cleaned up expired storage override {override.id}")
                
                session.commit()
                
                if cleanup_count > 0:
                    logger.info(f"Cleaned up {cleanup_count} expired storage override(s)")
                
                return cleanup_count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired overrides: {e}")
            return 0
    
    def get_override_history(self, 
                           limit: int = 50,
                           admin_user_id: Optional[int] = None) -> List[OverrideInfo]:
        """
        Get history of storage overrides.
        
        Args:
            limit: Maximum number of overrides to return
            admin_user_id: Filter by specific admin user (optional)
            
        Returns:
            List[OverrideInfo]: List of override information, ordered by most recent first
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(StorageOverride)
                
                if admin_user_id:
                    query = query.filter_by(admin_user_id=admin_user_id)
                
                overrides = query.order_by(StorageOverride.activated_at.desc()).limit(limit).all()
                
                history = []
                for override in overrides:
                    # Get admin user info
                    admin_user = session.query(User).filter_by(id=override.admin_user_id).first()
                    admin_username = admin_user.username if admin_user else f"User {override.admin_user_id}"
                    
                    # Calculate remaining time (if still active and not expired)
                    now = datetime.utcnow()
                    remaining_time = None
                    if override.is_active and override.expires_at > now:
                        remaining_time = override.expires_at - now
                    
                    history.append(OverrideInfo(
                        id=override.id,
                        admin_user_id=override.admin_user_id,
                        admin_username=admin_username,
                        activated_at=override.activated_at,
                        expires_at=override.expires_at,
                        duration_hours=override.duration_hours,
                        reason=override.reason or "",
                        is_active=override.is_active,
                        is_expired=override.is_expired(),
                        remaining_time=remaining_time,
                        storage_gb_at_activation=override.storage_gb_at_activation,
                        limit_gb_at_activation=override.limit_gb_at_activation
                    ))
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting override history: {e}")
            return []
    
    def get_override_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about storage overrides.
        
        Returns:
            Dict[str, Any]: Override statistics
        """
        try:
            with self.db_manager.get_session() as session:
                # Basic counts
                total_overrides = session.query(StorageOverride).count()
                active_overrides = session.query(StorageOverride).filter_by(is_active=True).filter(
                    StorageOverride.expires_at > datetime.now(timezone.utc)
                ).count()
                expired_overrides = session.query(StorageOverride).filter(
                    StorageOverride.expires_at <= datetime.now(timezone.utc)
                ).count()
                
                # Recent activity (last 30 days)
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                recent_overrides = session.query(StorageOverride).filter(
                    StorageOverride.activated_at >= thirty_days_ago
                ).count()
                
                # Average duration
                avg_duration = session.query(StorageOverride).with_entities(
                    StorageOverride.duration_hours
                ).all()
                avg_duration_hours = sum(d[0] for d in avg_duration) / len(avg_duration) if avg_duration else 0
                
                # Most active admin
                from sqlalchemy import func
                most_active_admin = session.query(
                    StorageOverride.admin_user_id,
                    func.count(StorageOverride.id).label('count')
                ).group_by(StorageOverride.admin_user_id).order_by(
                    func.count(StorageOverride.id).desc()
                ).first()
                
                most_active_admin_info = None
                if most_active_admin:
                    admin_user = session.query(User).filter_by(id=most_active_admin[0]).first()
                    most_active_admin_info = {
                        'user_id': most_active_admin[0],
                        'username': admin_user.username if admin_user else f"User {most_active_admin[0]}",
                        'override_count': most_active_admin[1]
                    }
                
                return {
                    'total_overrides': total_overrides,
                    'active_overrides': active_overrides,
                    'expired_overrides': expired_overrides,
                    'recent_overrides_30_days': recent_overrides,
                    'average_duration_hours': round(avg_duration_hours, 2),
                    'most_active_admin': most_active_admin_info,
                    'current_override': self.get_active_override().to_dict() if self.is_override_active() else None
                }
                
        except Exception as e:
            logger.error(f"Error getting override statistics: {e}")
            return {
                'total_overrides': 0,
                'active_overrides': 0,
                'expired_overrides': 0,
                'recent_overrides_30_days': 0,
                'average_duration_hours': 0,
                'most_active_admin': None,
                'current_override': None,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the storage override system.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        health = {
            'database_accessible': False,
            'config_service_healthy': False,
            'monitor_service_healthy': False,
            'override_cleanup_needed': False,
            'overall_healthy': False
        }
        
        try:
            # Check database access
            with self.db_manager.get_session() as session:
                session.query(StorageOverride).count()
                health['database_accessible'] = True
        except Exception as e:
            health['database_error'] = str(e)
        
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
            # Check for expired overrides that need cleanup
            with self.db_manager.get_session() as session:
                expired_count = session.query(StorageOverride).filter_by(
                    is_active=True
                ).filter(
                    StorageOverride.expires_at <= datetime.utcnow()
                ).count()
                health['override_cleanup_needed'] = expired_count > 0
                health['expired_overrides_count'] = expired_count
        except Exception as e:
            health['cleanup_check_error'] = str(e)
        
        # Overall health
        health['overall_healthy'] = all([
            health['database_accessible'],
            health['config_service_healthy'],
            health['monitor_service_healthy']
        ])
        
        return health