# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Comprehensive audit logging system for multi-tenant caption management.

This module provides comprehensive audit logging capabilities for tracking all
job-related actions, administrative interventions, and system events with
proper user context, IP address tracking, and compliance features.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from flask import request, session as flask_session

from models import JobAuditLog, User, CaptionGenerationTask, PlatformConnection
from app.core.database.core.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Comprehensive audit logging system for tracking all job-related actions.
    
    This class provides methods for logging job creation, cancellation, completion,
    admin interventions, and other system events with full context tracking.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the audit logger.
        
        Args:
            db_manager: Database manager instance for database operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def log_job_action(
        self,
        task_id: str,
        user_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        admin_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        platform_connection_id: Optional[int] = None,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        error_code: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> JobAuditLog:
        """
        Log a job-related action with full context.
        
        Args:
            task_id: Caption generation task ID
            user_id: ID of the user who owns the job
            action: Action being performed (created, cancelled, completed, etc.)
            details: Additional details about the action (stored as JSON)
            admin_user_id: ID of admin user if this is an administrative action
            ip_address: IP address of the user/admin performing the action
            user_agent: User agent string from the request
            session_id: Session ID for tracking user sessions
            platform_connection_id: Platform connection ID if applicable
            previous_status: Previous task status before action
            new_status: New task status after action
            error_code: Error code if applicable
            processing_time_ms: Processing time in milliseconds
            
        Returns:
            JobAuditLog: The created audit log entry
        """
        try:
            with self.db_manager.get_session() as db_session:
                # Auto-detect context from Flask request if not provided
                if not ip_address and request:
                    ip_address = self._get_client_ip()
                
                if not user_agent and request:
                    user_agent = request.headers.get('User-Agent', '')[:500]
                
                if not session_id and flask_session:
                    session_id = flask_session.get('session_id', '')
                
                # Create audit log entry
                audit_entry = JobAuditLog.log_action(
                    session=db_session,
                    task_id=task_id,
                    user_id=user_id,
                    action=action,
                    details=details,
                    admin_user_id=admin_user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                    platform_connection_id=platform_connection_id,
                    previous_status=previous_status,
                    new_status=new_status,
                    error_code=error_code,
                    processing_time_ms=processing_time_ms
                )
                
                db_session.commit()
                
                self.logger.info(
                    f"Audit log created: {action} for task {task_id} by user {user_id}"
                    + (f" (admin: {admin_user_id})" if admin_user_id else "")
                )
                
                return audit_entry
                
        except Exception as e:
            self.logger.error(f"Failed to create audit log entry: {e}")
            raise
    
    def log_job_creation(
        self,
        task_id: str,
        user_id: int,
        platform_connection_id: int,
        settings: Dict[str, Any],
        **kwargs
    ) -> JobAuditLog:
        """
        Log job creation with settings and context.
        
        Args:
            task_id: Caption generation task ID
            user_id: ID of the user creating the job
            platform_connection_id: Platform connection ID
            settings: Job settings and configuration
            **kwargs: Additional context parameters
            
        Returns:
            JobAuditLog: The created audit log entry
        """
        details = {
            'settings': settings,
            'platform_connection_id': platform_connection_id,
            'action_type': 'job_creation'
        }
        
        return self.log_job_action(
            task_id=task_id,
            user_id=user_id,
            action='created',
            details=details,
            platform_connection_id=platform_connection_id,
            new_status='queued',
            **kwargs
        )
    
    def log_job_completion(
        self,
        task_id: str,
        user_id: int,
        success: bool,
        results: Dict[str, Any],
        processing_time_ms: int,
        **kwargs
    ) -> JobAuditLog:
        """
        Log job completion with results and processing time.
        
        Args:
            task_id: Caption generation task ID
            user_id: ID of the user who owns the job
            success: Whether the job completed successfully
            results: Job results including counts and errors
            processing_time_ms: Total processing time in milliseconds
            **kwargs: Additional context parameters
            
        Returns:
            JobAuditLog: The created audit log entry
        """
        action = 'completed' if success else 'failed'
        details = {
            'results': results,
            'success': success,
            'action_type': 'job_completion'
        }
        
        return self.log_job_action(
            task_id=task_id,
            user_id=user_id,
            action=action,
            details=details,
            previous_status='running',
            new_status='completed' if success else 'failed',
            processing_time_ms=processing_time_ms,
            **kwargs
        )
    
    def log_job_cancellation(
        self,
        task_id: str,
        user_id: int,
        reason: str,
        admin_user_id: Optional[int] = None,
        **kwargs
    ) -> JobAuditLog:
        """
        Log job cancellation with reason and admin context.
        
        Args:
            task_id: Caption generation task ID
            user_id: ID of the user who owns the job
            reason: Reason for cancellation
            admin_user_id: ID of admin user if this is an administrative cancellation
            **kwargs: Additional context parameters
            
        Returns:
            JobAuditLog: The created audit log entry
        """
        details = {
            'reason': reason,
            'cancelled_by_admin': admin_user_id is not None,
            'action_type': 'job_cancellation'
        }
        
        return self.log_job_action(
            task_id=task_id,
            user_id=user_id,
            action='cancelled',
            details=details,
            admin_user_id=admin_user_id,
            previous_status='running',
            new_status='cancelled',
            **kwargs
        )
    
    def log_admin_intervention(
        self,
        task_id: str,
        user_id: int,
        admin_user_id: int,
        intervention_type: str,
        details: Dict[str, Any],
        **kwargs
    ) -> JobAuditLog:
        """
        Log administrative intervention on a job.
        
        Args:
            task_id: Caption generation task ID
            user_id: ID of the user who owns the job
            admin_user_id: ID of the admin user performing the intervention
            intervention_type: Type of intervention (restart, priority_change, etc.)
            details: Details about the intervention
            **kwargs: Additional context parameters
            
        Returns:
            JobAuditLog: The created audit log entry
        """
        audit_details = {
            'intervention_type': intervention_type,
            'action_type': 'admin_intervention',
            **details
        }
        
        return self.log_job_action(
            task_id=task_id,
            user_id=user_id,
            action=f'admin_{intervention_type}',
            details=audit_details,
            admin_user_id=admin_user_id,
            **kwargs
        )
    
    def query_audit_logs(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[int] = None,
        admin_user_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platform_connection_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'timestamp',
        order_direction: str = 'desc'
    ) -> List[JobAuditLog]:
        """
        Query audit logs with filtering and pagination.
        
        Args:
            task_id: Filter by specific task ID
            user_id: Filter by user ID
            admin_user_id: Filter by admin user ID
            action: Filter by action type
            start_date: Filter by start date
            end_date: Filter by end date
            platform_connection_id: Filter by platform connection
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Field to order by (timestamp, action, user_id)
            order_direction: Order direction (asc, desc)
            
        Returns:
            List[JobAuditLog]: List of matching audit log entries
        """
        try:
            with self.db_manager.get_session() as db_session:
                query = db_session.query(JobAuditLog)
                
                # Apply filters
                if task_id:
                    query = query.filter(JobAuditLog.task_id == task_id)
                
                if user_id:
                    query = query.filter(JobAuditLog.user_id == user_id)
                
                if admin_user_id:
                    query = query.filter(JobAuditLog.admin_user_id == admin_user_id)
                
                if action:
                    query = query.filter(JobAuditLog.action == action)
                
                if start_date:
                    query = query.filter(JobAuditLog.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(JobAuditLog.timestamp <= end_date)
                
                if platform_connection_id:
                    query = query.filter(JobAuditLog.platform_connection_id == platform_connection_id)
                
                # Apply ordering
                order_field = getattr(JobAuditLog, order_by, JobAuditLog.timestamp)
                if order_direction.lower() == 'asc':
                    query = query.order_by(asc(order_field))
                else:
                    query = query.order_by(desc(order_field))
                
                # Apply pagination
                query = query.offset(offset).limit(limit)
                
                return query.all()
                
        except Exception as e:
            self.logger.error(f"Failed to query audit logs: {e}")
            raise
    
    def get_audit_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics for reporting and monitoring.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            user_id: Filter by specific user
            
        Returns:
            Dict[str, Any]: Statistics including action counts, user activity, etc.
        """
        try:
            with self.db_manager.get_session() as db_session:
                query = db_session.query(JobAuditLog)
                
                # Apply date filters
                if start_date:
                    query = query.filter(JobAuditLog.timestamp >= start_date)
                
                if end_date:
                    query = query.filter(JobAuditLog.timestamp <= end_date)
                
                if user_id:
                    query = query.filter(JobAuditLog.user_id == user_id)
                
                # Get action counts
                action_counts = (
                    query.with_entities(JobAuditLog.action, func.count(JobAuditLog.id))
                    .group_by(JobAuditLog.action)
                    .all()
                )
                
                # Get user activity counts
                user_activity = (
                    query.with_entities(JobAuditLog.user_id, func.count(JobAuditLog.id))
                    .group_by(JobAuditLog.user_id)
                    .order_by(desc(func.count(JobAuditLog.id)))
                    .limit(10)
                    .all()
                )
                
                # Get admin activity counts
                admin_activity = (
                    query.filter(JobAuditLog.admin_user_id.isnot(None))
                    .with_entities(JobAuditLog.admin_user_id, func.count(JobAuditLog.id))
                    .group_by(JobAuditLog.admin_user_id)
                    .order_by(desc(func.count(JobAuditLog.id)))
                    .limit(10)
                    .all()
                )
                
                # Get total counts
                total_entries = query.count()
                admin_interventions = query.filter(JobAuditLog.admin_user_id.isnot(None)).count()
                
                return {
                    'total_entries': total_entries,
                    'admin_interventions': admin_interventions,
                    'action_counts': dict(action_counts),
                    'user_activity': dict(user_activity),
                    'admin_activity': dict(admin_activity),
                    'date_range': {
                        'start': start_date.isoformat() if start_date else None,
                        'end': end_date.isoformat() if end_date else None
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get audit statistics: {e}")
            raise
    
    def export_audit_logs(
        self,
        format_type: str = 'json',
        **filter_kwargs
    ) -> Union[str, bytes]:
        """
        Export audit logs for compliance requirements.
        
        Args:
            format_type: Export format ('json', 'csv')
            **filter_kwargs: Filtering parameters for query_audit_logs
            
        Returns:
            Union[str, bytes]: Exported data in requested format
        """
        try:
            # Remove pagination for export
            filter_kwargs.pop('limit', None)
            filter_kwargs.pop('offset', None)
            
            audit_logs = self.query_audit_logs(**filter_kwargs)
            
            if format_type.lower() == 'json':
                return self._export_to_json(audit_logs)
            elif format_type.lower() == 'csv':
                return self._export_to_csv(audit_logs)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to export audit logs: {e}")
            raise
    
    def cleanup_old_logs(
        self,
        retention_days: int = 365,
        batch_size: int = 1000
    ) -> int:
        """
        Clean up old audit logs based on retention policy.
        
        Args:
            retention_days: Number of days to retain logs
            batch_size: Number of records to delete in each batch
            
        Returns:
            int: Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            total_deleted = 0
            
            with self.db_manager.get_session() as db_session:
                while True:
                    # Delete in batches to avoid long-running transactions
                    deleted_count = (
                        db_session.query(JobAuditLog)
                        .filter(JobAuditLog.timestamp < cutoff_date)
                        .limit(batch_size)
                        .delete(synchronize_session=False)
                    )
                    
                    if deleted_count == 0:
                        break
                    
                    total_deleted += deleted_count
                    db_session.commit()
                    
                    self.logger.info(f"Deleted {deleted_count} audit log entries (total: {total_deleted})")
            
            self.logger.info(f"Audit log cleanup completed: {total_deleted} entries deleted")
            return total_deleted
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup audit logs: {e}")
            raise
    
    def _get_client_ip(self) -> str:
        """Get the client IP address from the request."""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'unknown'
    
    def _export_to_json(self, audit_logs: List[JobAuditLog]) -> str:
        """Export audit logs to JSON format."""
        export_data = []
        
        for log in audit_logs:
            export_data.append({
                'id': log.id,
                'task_id': log.task_id,
                'user_id': log.user_id,
                'admin_user_id': log.admin_user_id,
                'action': log.action,
                'details': log.get_details_dict(),
                'timestamp': log.timestamp.isoformat(),
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'session_id': log.session_id,
                'platform_connection_id': log.platform_connection_id,
                'previous_status': log.previous_status,
                'new_status': log.new_status,
                'error_code': log.error_code,
                'processing_time_ms': log.processing_time_ms
            })
        
        return json.dumps({
            'export_timestamp': datetime.utcnow().isoformat(),
            'total_records': len(export_data),
            'audit_logs': export_data
        }, indent=2)
    
    def _export_to_csv(self, audit_logs: List[JobAuditLog]) -> str:
        """Export audit logs to CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'id', 'task_id', 'user_id', 'admin_user_id', 'action',
            'timestamp', 'ip_address', 'user_agent', 'session_id',
            'platform_connection_id', 'previous_status', 'new_status',
            'error_code', 'processing_time_ms', 'details'
        ])
        
        # Write data
        for log in audit_logs:
            writer.writerow([
                log.id,
                log.task_id,
                log.user_id,
                log.admin_user_id,
                log.action,
                log.timestamp.isoformat(),
                log.ip_address,
                log.user_agent,
                log.session_id,
                log.platform_connection_id,
                log.previous_status,
                log.new_status,
                log.error_code,
                log.processing_time_ms,
                json.dumps(log.get_details_dict()) if log.details else ''
            ])
        
        return output.getvalue()