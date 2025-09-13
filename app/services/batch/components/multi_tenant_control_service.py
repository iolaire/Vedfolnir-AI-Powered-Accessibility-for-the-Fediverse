# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import json
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database.core.database_manager import DatabaseManager
from models import (
    User, UserRole, CaptionGenerationTask, TaskStatus, JobPriority, 
    SystemConfiguration, JobAuditLog
)
from app.services.monitoring.system.system_monitor import ResourceUsage
from app.core.security.core.rate_limiter import RateLimitConfig

logger = logging.getLogger(__name__)

@dataclass
class UserJobLimits:
    """User-specific job limits and quotas"""
    max_concurrent_jobs: int = 1
    max_jobs_per_hour: int = 10
    max_jobs_per_day: int = 50
    max_processing_time_minutes: int = 60
    priority_override: Optional[JobPriority] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        if self.priority_override:
            data['priority_override'] = self.priority_override.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserJobLimits':
        """Create from dictionary"""
        if 'priority_override' in data and data['priority_override']:
            data['priority_override'] = JobPriority(data['priority_override'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UserJobLimits':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

@dataclass
class RateLimits:
    """System-wide rate limiting configuration"""
    global_max_concurrent_jobs: int = 10
    max_jobs_per_minute: int = 5
    max_jobs_per_hour: int = 100
    max_jobs_per_day: int = 1000
    cooldown_period_minutes: int = 5
    burst_allowance: int = 3
    
    # Per-user rate limits
    user_rate_limits: Dict[int, UserJobLimits] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert user_rate_limits to serializable format
        data['user_rate_limits'] = {
            str(user_id): limits.to_dict() 
            for user_id, limits in self.user_rate_limits.items()
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RateLimits':
        """Create from dictionary"""
        # Convert user_rate_limits back from serialized format
        if 'user_rate_limits' in data:
            user_limits = {}
            for user_id_str, limits_data in data['user_rate_limits'].items():
                user_limits[int(user_id_str)] = UserJobLimits.from_dict(limits_data)
            data['user_rate_limits'] = user_limits
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RateLimits':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

class MultiTenantControlService:
    """System-wide controls and multi-tenant management service"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def _verify_admin_authorization(self, session: Session, admin_user_id: int) -> User:
        """
        Verify that the user has admin authorization
        
        Args:
            session: Database session
            admin_user_id: User ID to verify
            
        Returns:
            User object if authorized
            
        Raises:
            ValueError: If user is not authorized
        """
        admin_user = session.query(User).filter_by(id=admin_user_id).first()
        if not admin_user:
            raise ValueError(f"User {admin_user_id} not found")
        
        if admin_user.role != UserRole.ADMIN:
            raise ValueError(f"User {admin_user_id} is not authorized for admin operations")
        
        return admin_user
    
    def _log_admin_action(self, session: Session, admin_user_id: int, action: str, 
                         details: Dict[str, Any], target_user_id: Optional[int] = None,
                         task_id: Optional[str] = None):
        """
        Log administrative action for audit trail
        
        Args:
            session: Database session
            admin_user_id: Admin user performing the action
            action: Action being performed
            details: Action details
            target_user_id: Target user ID if applicable
            task_id: Task ID if applicable
        """
        try:
            audit_log = JobAuditLog(
                task_id=task_id,
                user_id=target_user_id,
                admin_user_id=admin_user_id,
                action=action,
                details=json.dumps(details),
                timestamp=datetime.utcnow()
            )
            session.add(audit_log)
            logger.info(f"Admin action logged: {action} by user {admin_user_id}")
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
    
    def set_user_job_limits(self, admin_user_id: int, target_user_id: int, 
                           limits: UserJobLimits) -> bool:
        """
        Set job limits for a specific user
        
        Args:
            admin_user_id: Admin user ID performing the action
            target_user_id: Target user ID to set limits for
            limits: Job limits configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                admin_user = self._verify_admin_authorization(session, admin_user_id)
                
                # Verify target user exists
                target_user = session.query(User).filter_by(id=target_user_id).first()
                if not target_user:
                    raise ValueError(f"Target user {target_user_id} not found")
                
                # Store user limits in system configuration
                config_key = f"user_job_limits_{target_user_id}"
                config_entry = session.query(SystemConfiguration).filter_by(key=config_key).first()
                
                if config_entry:
                    config_entry.value = limits.to_json()
                    config_entry.updated_by = admin_user_id
                    config_entry.updated_at = datetime.utcnow()
                else:
                    config_entry = SystemConfiguration(
                        key=config_key,
                        value=limits.to_json(),
                        description=f"Job limits for user {target_user.username}",
                        updated_by=admin_user_id,
                        updated_at=datetime.utcnow()
                    )
                    session.add(config_entry)
                
                # Log the action
                self._log_admin_action(
                    session, admin_user_id, "set_user_job_limits",
                    {
                        "target_user_id": target_user_id,
                        "target_username": target_user.username,
                        "limits": limits.to_dict()
                    },
                    target_user_id=target_user_id
                )
                
                session.commit()
                logger.info(f"Job limits set for user {target_user_id} by admin {admin_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set user job limits: {e}")
            return False
    
    def pause_system_jobs(self, admin_user_id: int, reason: str) -> bool:
        """
        Pause all system jobs for maintenance mode
        
        Args:
            admin_user_id: Admin user ID performing the action
            reason: Reason for pausing jobs
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                admin_user = self._verify_admin_authorization(session, admin_user_id)
                
                # Set maintenance mode flag
                maintenance_config = session.query(SystemConfiguration).filter_by(
                    key="maintenance_mode"
                ).first()
                
                if maintenance_config:
                    maintenance_config.value = "true"
                    maintenance_config.updated_by = admin_user_id
                    maintenance_config.updated_at = datetime.utcnow()
                else:
                    maintenance_config = SystemConfiguration(
                        key="maintenance_mode",
                        value="true",
                        description="System maintenance mode flag",
                        updated_by=admin_user_id,
                        updated_at=datetime.utcnow()
                    )
                    session.add(maintenance_config)
                
                # Store maintenance reason
                reason_config = session.query(SystemConfiguration).filter_by(
                    key="maintenance_reason"
                ).first()
                
                if reason_config:
                    reason_config.value = reason
                    reason_config.updated_by = admin_user_id
                    reason_config.updated_at = datetime.utcnow()
                else:
                    reason_config = SystemConfiguration(
                        key="maintenance_reason",
                        value=reason,
                        description="Reason for current maintenance mode",
                        updated_by=admin_user_id,
                        updated_at=datetime.utcnow()
                    )
                    session.add(reason_config)
                
                # Log the action
                self._log_admin_action(
                    session, admin_user_id, "pause_system_jobs",
                    {"reason": reason}
                )
                
                session.commit()
                logger.info(f"System jobs paused by admin {admin_user_id}: {reason}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to pause system jobs: {e}")
            return False
    
    def resume_system_jobs(self, admin_user_id: int) -> bool:
        """
        Resume system jobs after maintenance
        
        Args:
            admin_user_id: Admin user ID performing the action
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                admin_user = self._verify_admin_authorization(session, admin_user_id)
                
                # Clear maintenance mode flag
                maintenance_config = session.query(SystemConfiguration).filter_by(
                    key="maintenance_mode"
                ).first()
                
                if maintenance_config:
                    maintenance_config.value = "false"
                    maintenance_config.updated_by = admin_user_id
                    maintenance_config.updated_at = datetime.utcnow()
                else:
                    maintenance_config = SystemConfiguration(
                        key="maintenance_mode",
                        value="false",
                        description="System maintenance mode flag",
                        updated_by=admin_user_id,
                        updated_at=datetime.utcnow()
                    )
                    session.add(maintenance_config)
                
                # Clear maintenance reason
                reason_config = session.query(SystemConfiguration).filter_by(
                    key="maintenance_reason"
                ).first()
                
                if reason_config:
                    reason_config.value = ""
                    reason_config.updated_by = admin_user_id
                    reason_config.updated_at = datetime.utcnow()
                
                # Log the action
                self._log_admin_action(
                    session, admin_user_id, "resume_system_jobs", {}
                )
                
                session.commit()
                logger.info(f"System jobs resumed by admin {admin_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to resume system jobs: {e}")
            return False
    
    def set_job_priority(self, admin_user_id: int, task_id: str, 
                        priority: JobPriority) -> bool:
        """
        Set priority for a specific job
        
        Args:
            admin_user_id: Admin user ID performing the action
            task_id: Task ID to update priority for
            priority: New job priority
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                admin_user = self._verify_admin_authorization(session, admin_user_id)
                
                # Find the task
                task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
                if not task:
                    raise ValueError(f"Task {task_id} not found")
                
                # Store old priority for logging
                old_priority = task.priority
                
                # Update task priority
                task.priority = priority
                
                # Add admin notes
                admin_note = f"Priority changed from {old_priority.value if old_priority else 'None'} to {priority.value} by admin {admin_user.username}"
                if task.admin_notes:
                    task.admin_notes += f"\n{datetime.utcnow().isoformat()}: {admin_note}"
                else:
                    task.admin_notes = f"{datetime.utcnow().isoformat()}: {admin_note}"
                
                # Log the action
                self._log_admin_action(
                    session, admin_user_id, "set_job_priority",
                    {
                        "task_id": task_id,
                        "old_priority": old_priority.value if old_priority else None,
                        "new_priority": priority.value,
                        "user_id": task.user_id
                    },
                    target_user_id=task.user_id,
                    task_id=task_id
                )
                
                session.commit()
                logger.info(f"Task {task_id} priority set to {priority.value} by admin {admin_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set job priority: {e}")
            return False
    
    def get_resource_usage(self) -> ResourceUsage:
        """
        Get current system resource usage
        
        Returns:
            ResourceUsage object with current system metrics
        """
        try:
            # Import here to avoid circular imports
            from system_monitor import SystemMonitor
            
            # Create a temporary system monitor instance
            system_monitor = SystemMonitor(self.db_manager)
            
            # Get current resource usage
            return system_monitor.check_resource_usage()
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            # Return default/empty resource usage on error
            return ResourceUsage(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_total_mb=0.0,
                disk_percent=0.0,
                disk_used_gb=0.0,
                disk_total_gb=0.0,
                network_io={},
                database_connections=0,
                redis_memory_mb=0.0,
                timestamp=datetime.utcnow()
            )
    
    def configure_rate_limits(self, admin_user_id: int, limits: RateLimits) -> bool:
        """
        Configure system-wide rate limits
        
        Args:
            admin_user_id: Admin user ID performing the action
            limits: Rate limits configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify admin authorization
                admin_user = self._verify_admin_authorization(session, admin_user_id)
                
                # Store rate limits in system configuration
                config_key = "system_rate_limits"
                config_entry = session.query(SystemConfiguration).filter_by(key=config_key).first()
                
                if config_entry:
                    config_entry.value = limits.to_json()
                    config_entry.updated_by = admin_user_id
                    config_entry.updated_at = datetime.utcnow()
                else:
                    config_entry = SystemConfiguration(
                        key=config_key,
                        value=limits.to_json(),
                        description="System-wide rate limiting configuration",
                        updated_by=admin_user_id,
                        updated_at=datetime.utcnow()
                    )
                    session.add(config_entry)
                
                # Log the action
                self._log_admin_action(
                    session, admin_user_id, "configure_rate_limits",
                    {"limits": limits.to_dict()}
                )
                
                session.commit()
                logger.info(f"Rate limits configured by admin {admin_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to configure rate limits: {e}")
            return False
    
    def get_user_job_limits(self, user_id: int) -> UserJobLimits:
        """
        Get job limits for a specific user
        
        Args:
            user_id: User ID to get limits for
            
        Returns:
            UserJobLimits object with user's limits
        """
        try:
            with self.db_manager.get_session() as session:
                config_key = f"user_job_limits_{user_id}"
                config_entry = session.query(SystemConfiguration).filter_by(key=config_key).first()
                
                if config_entry and config_entry.value:
                    return UserJobLimits.from_json(config_entry.value)
                else:
                    # Return default limits
                    return UserJobLimits()
                    
        except Exception as e:
            logger.error(f"Failed to get user job limits: {e}")
            return UserJobLimits()
    
    def get_system_rate_limits(self) -> RateLimits:
        """
        Get current system-wide rate limits
        
        Returns:
            RateLimits object with current system limits
        """
        try:
            with self.db_manager.get_session() as session:
                config_key = "system_rate_limits"
                config_entry = session.query(SystemConfiguration).filter_by(key=config_key).first()
                
                if config_entry and config_entry.value:
                    return RateLimits.from_json(config_entry.value)
                else:
                    # Return default limits
                    return RateLimits()
                    
        except Exception as e:
            logger.error(f"Failed to get system rate limits: {e}")
            return RateLimits()
    
    def is_maintenance_mode(self) -> bool:
        """
        Check if system is in maintenance mode
        
        Returns:
            True if in maintenance mode, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                config_entry = session.query(SystemConfiguration).filter_by(
                    key="maintenance_mode"
                ).first()
                
                if config_entry and config_entry.value:
                    return config_entry.value.lower() == "true"
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to check maintenance mode: {e}")
            return False
    
    def get_maintenance_reason(self) -> Optional[str]:
        """
        Get the reason for current maintenance mode
        
        Returns:
            Maintenance reason string or None if not in maintenance mode
        """
        try:
            with self.db_manager.get_session() as session:
                config_entry = session.query(SystemConfiguration).filter_by(
                    key="maintenance_reason"
                ).first()
                
                if config_entry and config_entry.value:
                    return config_entry.value
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get maintenance reason: {e}")
            return None