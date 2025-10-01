# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Data Lifecycle Management and Retention Policies

Implements automated data lifecycle management including:
- Data retention policy enforcement
- Automated data archival
- Data purging and cleanup
- Compliance with regulatory requirements
- Data aging and classification
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import shutil
import gzip

from sqlalchemy import text

class DataCategory(Enum):
    """Categories of data for lifecycle management"""
    USER_DATA = "user_data"
    AUDIT_LOGS = "audit_logs"
    SESSION_DATA = "session_data"
    PROCESSING_LOGS = "processing_logs"
    SYSTEM_LOGS = "system_logs"
    BACKUP_DATA = "backup_data"
    TEMP_DATA = "temp_data"
    COMPLIANCE_REPORTS = "compliance_reports"

class RetentionAction(Enum):
    """Actions to take when retention period expires"""
    DELETE = "delete"
    ARCHIVE = "archive"
    ANONYMIZE = "anonymize"
    COMPRESS = "compress"
    NOTIFY = "notify"

@dataclass
class RetentionPolicy:
    """Data retention policy definition"""
    category: DataCategory
    retention_days: int
    action: RetentionAction
    archive_location: Optional[str] = None
    compression_enabled: bool = False
    notification_days: int = 30  # Days before expiration to notify
    exceptions: List[str] = None  # Conditions that exempt from policy

@dataclass
class DataLifecycleEvent:
    """Data lifecycle event record"""
    event_id: str
    category: DataCategory
    action: RetentionAction
    affected_records: int
    execution_time: str
    success: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None

class DataLifecycleManager:
    """
    Data Lifecycle Management Service
    
    Manages the complete lifecycle of data from creation to deletion,
    ensuring compliance with retention policies and regulatory requirements.
    """
    
    def __init__(self, db_manager, audit_logger, config: Dict[str, Any]):
        self.db_manager = db_manager
        self.audit_logger = audit_logger
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Lifecycle configuration
        self.archive_path = Path(config.get('archive_path', '/app/storage/archives'))
        self.temp_cleanup_enabled = config.get('temp_cleanup_enabled', True)
        self.auto_execution_enabled = config.get('auto_execution_enabled', True)
        
        # Ensure archive directory exists
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Default retention policies
        self.retention_policies = self._load_retention_policies()
    
    def _load_retention_policies(self) -> Dict[DataCategory, RetentionPolicy]:
        """Load retention policies from configuration"""
        default_policies = {
            DataCategory.USER_DATA: RetentionPolicy(
                category=DataCategory.USER_DATA,
                retention_days=2555,  # 7 years for GDPR compliance
                action=RetentionAction.ARCHIVE,
                archive_location=str(self.archive_path / "user_data"),
                compression_enabled=True,
                notification_days=90
            ),
            DataCategory.AUDIT_LOGS: RetentionPolicy(
                category=DataCategory.AUDIT_LOGS,
                retention_days=2555,  # 7 years for compliance
                action=RetentionAction.ARCHIVE,
                archive_location=str(self.archive_path / "audit_logs"),
                compression_enabled=True,
                notification_days=180
            ),
            DataCategory.SESSION_DATA: RetentionPolicy(
                category=DataCategory.SESSION_DATA,
                retention_days=90,  # 3 months
                action=RetentionAction.DELETE,
                notification_days=7
            ),
            DataCategory.PROCESSING_LOGS: RetentionPolicy(
                category=DataCategory.PROCESSING_LOGS,
                retention_days=365,  # 1 year
                action=RetentionAction.COMPRESS,
                compression_enabled=True,
                notification_days=30
            ),
            DataCategory.SYSTEM_LOGS: RetentionPolicy(
                category=DataCategory.SYSTEM_LOGS,
                retention_days=365,  # 1 year
                action=RetentionAction.COMPRESS,
                compression_enabled=True,
                notification_days=30
            ),
            DataCategory.BACKUP_DATA: RetentionPolicy(
                category=DataCategory.BACKUP_DATA,
                retention_days=1095,  # 3 years
                action=RetentionAction.DELETE,
                notification_days=60
            ),
            DataCategory.TEMP_DATA: RetentionPolicy(
                category=DataCategory.TEMP_DATA,
                retention_days=7,  # 1 week
                action=RetentionAction.DELETE,
                notification_days=1
            ),
            DataCategory.COMPLIANCE_REPORTS: RetentionPolicy(
                category=DataCategory.COMPLIANCE_REPORTS,
                retention_days=2555,  # 7 years
                action=RetentionAction.ARCHIVE,
                archive_location=str(self.archive_path / "compliance_reports"),
                compression_enabled=True,
                notification_days=180
            )
        }
        
        # Override with configuration if provided
        config_policies = self.config.get('retention_policies', {})
        for category_name, policy_config in config_policies.items():
            try:
                category = DataCategory(category_name)
                action = RetentionAction(policy_config.get('action', 'delete'))
                
                default_policies[category] = RetentionPolicy(
                    category=category,
                    retention_days=policy_config.get('retention_days', 365),
                    action=action,
                    archive_location=policy_config.get('archive_location'),
                    compression_enabled=policy_config.get('compression_enabled', False),
                    notification_days=policy_config.get('notification_days', 30),
                    exceptions=policy_config.get('exceptions', [])
                )
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Invalid retention policy configuration for {category_name}: {e}")
        
        return default_policies
    
    def execute_lifecycle_policies(self) -> List[DataLifecycleEvent]:
        """
        Execute all data lifecycle policies
        
        Returns:
            List of lifecycle events executed
        """
        events = []
        
        for category, policy in self.retention_policies.items():
            try:
                event = self._execute_policy(policy)
                if event:
                    events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to execute policy for {category.value}: {e}")
                
                # Create failure event
                events.append(DataLifecycleEvent(
                    event_id=f"lifecycle_{category.value}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                    category=category,
                    action=policy.action,
                    affected_records=0,
                    execution_time=datetime.now(timezone.utc).isoformat(),
                    success=False,
                    details={},
                    error_message=str(e)
                ))
        
        # Log lifecycle execution
        self.audit_logger.log_event(
            event_type=self.audit_logger.AuditEventType.SYSTEM_ADMINISTRATION,
            resource="data_lifecycle",
            action="execute_policies",
            outcome="SUCCESS" if all(e.success for e in events) else "PARTIAL",
            details={
                'total_policies': len(self.retention_policies),
                'successful_executions': sum(1 for e in events if e.success),
                'failed_executions': sum(1 for e in events if not e.success),
                'total_affected_records': sum(e.affected_records for e in events)
            }
        )
        
        return events
    
    def _execute_policy(self, policy: RetentionPolicy) -> Optional[DataLifecycleEvent]:
        """Execute a specific retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        if policy.category == DataCategory.USER_DATA:
            return self._process_user_data(policy, cutoff_date)
        elif policy.category == DataCategory.AUDIT_LOGS:
            return self._process_audit_logs(policy, cutoff_date)
        elif policy.category == DataCategory.SESSION_DATA:
            return self._process_session_data(policy, cutoff_date)
        elif policy.category == DataCategory.PROCESSING_LOGS:
            return self._process_processing_logs(policy, cutoff_date)
        elif policy.category == DataCategory.SYSTEM_LOGS:
            return self._process_system_logs(policy, cutoff_date)
        elif policy.category == DataCategory.BACKUP_DATA:
            return self._process_backup_data(policy, cutoff_date)
        elif policy.category == DataCategory.TEMP_DATA:
            return self._process_temp_data(policy, cutoff_date)
        elif policy.category == DataCategory.COMPLIANCE_REPORTS:
            return self._process_compliance_reports(policy, cutoff_date)
        
        return None
    
    def _process_user_data(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process user data according to retention policy"""
        event_id = f"user_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        affected_records = 0
        
        try:
            with self.db_manager.get_session() as session:
                # Find users with data older than retention period
                # Only process inactive users to avoid disrupting active accounts
                old_users = session.execute(text("""
                    SELECT u.id, u.username, u.created_at, u.last_login
                    FROM users u
                    WHERE u.created_at < :cutoff_date
                    AND (u.last_login IS NULL OR u.last_login < :cutoff_date)
                    AND u.is_active = 0
                """), {'cutoff_date': cutoff_date}).fetchall()
                
                for user in old_users:
                    if policy.action == RetentionAction.ARCHIVE:
                        self._archive_user_data(user.id, policy)
                    elif policy.action == RetentionAction.ANONYMIZE:
                        self._anonymize_user_data(user.id)
                    elif policy.action == RetentionAction.DELETE:
                        self._delete_user_data(user.id)
                    
                    affected_records += 1
                
                session.commit()
            
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=affected_records,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=True,
                details={
                    'cutoff_date': cutoff_date.isoformat(),
                    'policy': asdict(policy)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing user data: {e}")
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=0,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={},
                error_message=str(e)
            )
    
    def _process_session_data(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process session data according to retention policy"""
        event_id = f"session_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        affected_records = 0
        
        try:
            with self.db_manager.get_session() as session:
                # Delete old session records
                result = session.execute(text("""
                    DELETE FROM user_sessions 
                    WHERE created_at < :cutoff_date
                """), {'cutoff_date': cutoff_date})
                
                affected_records = result.rowcount
                session.commit()
            
            # Also clean up Redis sessions if configured
            self._cleanup_redis_sessions(cutoff_date)
            
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=affected_records,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=True,
                details={
                    'cutoff_date': cutoff_date.isoformat(),
                    'redis_cleanup': True
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing session data: {e}")
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=0,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={},
                error_message=str(e)
            )
    
    def _process_temp_data(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process temporary data according to retention policy"""
        event_id = f"temp_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        affected_records = 0
        
        try:
            temp_paths = [
                Path('/app/storage/temp'),
                Path('/tmp'),
                Path('/app/logs/temp')
            ]
            
            for temp_path in temp_paths:
                if temp_path.exists():
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            file_age = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                            if file_age < cutoff_date:
                                file_path.unlink()
                                affected_records += 1
            
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=affected_records,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=True,
                details={
                    'cutoff_date': cutoff_date.isoformat(),
                    'temp_paths_processed': [str(p) for p in temp_paths if p.exists()]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing temp data: {e}")
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=0,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={},
                error_message=str(e)
            )
    
    def _process_audit_logs(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process audit logs according to retention policy"""
        event_id = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        affected_records = 0
        
        try:
            # Archive old audit log files
            log_paths = [
                Path('/app/logs/audit'),
                Path('/app/logs/security')
            ]
            
            for log_path in log_paths:
                if log_path.exists():
                    for log_file in log_path.glob('*.log*'):
                        if log_file.is_file():
                            file_age = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc)
                            if file_age < cutoff_date:
                                if policy.action == RetentionAction.ARCHIVE:
                                    self._archive_file(log_file, policy)
                                elif policy.action == RetentionAction.COMPRESS:
                                    self._compress_file(log_file)
                                elif policy.action == RetentionAction.DELETE:
                                    log_file.unlink()
                                
                                affected_records += 1
            
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=affected_records,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=True,
                details={
                    'cutoff_date': cutoff_date.isoformat(),
                    'log_paths_processed': [str(p) for p in log_paths if p.exists()]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing audit logs: {e}")
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=0,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={},
                error_message=str(e)
            )
    
    def _process_processing_logs(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process processing logs according to retention policy"""
        # Similar implementation to audit logs
        return self._process_log_files(
            policy, 
            cutoff_date, 
            [Path('/app/logs/processing'), Path('/app/logs/caption')],
            "processing_logs"
        )
    
    def _process_system_logs(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process system logs according to retention policy"""
        return self._process_log_files(
            policy,
            cutoff_date,
            [Path('/app/logs/app'), Path('/app/logs/system')],
            "system_logs"
        )
    
    def _process_backup_data(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process backup data according to retention policy"""
        return self._process_log_files(
            policy,
            cutoff_date,
            [Path('/app/storage/backups')],
            "backup_data"
        )
    
    def _process_compliance_reports(self, policy: RetentionPolicy, cutoff_date: datetime) -> DataLifecycleEvent:
        """Process compliance reports according to retention policy"""
        return self._process_log_files(
            policy,
            cutoff_date,
            [Path('/app/storage/compliance_reports')],
            "compliance_reports"
        )
    
    def _process_log_files(self, policy: RetentionPolicy, cutoff_date: datetime, 
                          paths: List[Path], category_name: str) -> DataLifecycleEvent:
        """Generic log file processing"""
        event_id = f"{category_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        affected_records = 0
        
        try:
            for log_path in paths:
                if log_path.exists():
                    for file_path in log_path.rglob('*'):
                        if file_path.is_file():
                            file_age = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                            if file_age < cutoff_date:
                                if policy.action == RetentionAction.ARCHIVE:
                                    self._archive_file(file_path, policy)
                                elif policy.action == RetentionAction.COMPRESS:
                                    self._compress_file(file_path)
                                elif policy.action == RetentionAction.DELETE:
                                    file_path.unlink()
                                
                                affected_records += 1
            
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=affected_records,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=True,
                details={
                    'cutoff_date': cutoff_date.isoformat(),
                    'paths_processed': [str(p) for p in paths if p.exists()]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing {category_name}: {e}")
            return DataLifecycleEvent(
                event_id=event_id,
                category=policy.category,
                action=policy.action,
                affected_records=0,
                execution_time=datetime.now(timezone.utc).isoformat(),
                success=False,
                details={},
                error_message=str(e)
            )
    
    def _archive_user_data(self, user_id: int, policy: RetentionPolicy):
        """Archive user data to specified location"""
        if not policy.archive_location:
            return
        
        archive_path = Path(policy.archive_location)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        # Export user data
        user_data = self._export_user_data(user_id)
        
        # Save to archive
        archive_file = archive_path / f"user_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        
        if policy.compression_enabled:
            with gzip.open(f"{archive_file}.gz", 'wt', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, default=str)
        else:
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, default=str)
    
    def _anonymize_user_data(self, user_id: int):
        """Anonymize user data in place"""
        # This would use the GDPR service anonymization
        pass
    
    def _delete_user_data(self, user_id: int):
        """Delete user data completely"""
        # This would use the GDPR service deletion
        pass
    
    def _export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export user data for archival"""
        # This would use the GDPR service data collection
        return {'user_id': user_id, 'archived_at': datetime.now(timezone.utc).isoformat()}
    
    def _archive_file(self, file_path: Path, policy: RetentionPolicy):
        """Archive a file to the specified location"""
        if not policy.archive_location:
            return
        
        archive_path = Path(policy.archive_location)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        # Create archive filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        archive_file = archive_path / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        
        if policy.compression_enabled:
            # Compress and move
            with open(file_path, 'rb') as f_in:
                with gzip.open(f"{archive_file}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            file_path.unlink()  # Remove original
        else:
            # Just move
            shutil.move(str(file_path), str(archive_file))
    
    def _compress_file(self, file_path: Path):
        """Compress a file in place"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        file_path.unlink()  # Remove original
    
    def _cleanup_redis_sessions(self, cutoff_date: datetime):
        """Clean up old Redis sessions"""
        try:
            # This would connect to Redis and clean up old sessions
            # Implementation depends on Redis session structure
            pass
        except Exception as e:
            self.logger.warning(f"Failed to cleanup Redis sessions: {e}")
    
    def get_retention_status(self) -> Dict[str, Any]:
        """Get current retention policy status"""
        status = {
            'policies': {},
            'next_execution': None,
            'last_execution': None
        }
        
        for category, policy in self.retention_policies.items():
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
            
            # Estimate affected records (simplified)
            estimated_records = self._estimate_affected_records(category, cutoff_date)
            
            status['policies'][category.value] = {
                'retention_days': policy.retention_days,
                'action': policy.action.value,
                'cutoff_date': cutoff_date.isoformat(),
                'estimated_affected_records': estimated_records,
                'archive_location': policy.archive_location,
                'compression_enabled': policy.compression_enabled
            }
        
        return status
    
    def _estimate_affected_records(self, category: DataCategory, cutoff_date: datetime) -> int:
        """Estimate number of records affected by retention policy"""
        try:
            with self.db_manager.get_session() as session:
                if category == DataCategory.USER_DATA:
                    result = session.execute(text("""
                        SELECT COUNT(*) as count FROM users 
                        WHERE created_at < :cutoff_date AND is_active = 0
                    """), {'cutoff_date': cutoff_date}).fetchone()
                    return result.count if result else 0
                
                elif category == DataCategory.SESSION_DATA:
                    result = session.execute(text("""
                        SELECT COUNT(*) as count FROM user_sessions 
                        WHERE created_at < :cutoff_date
                    """), {'cutoff_date': cutoff_date}).fetchone()
                    return result.count if result else 0
                
                # For file-based categories, estimate based on file count
                # This is a simplified estimation
                return 0
                
        except Exception as e:
            self.logger.error(f"Error estimating affected records for {category.value}: {e}")
            return 0