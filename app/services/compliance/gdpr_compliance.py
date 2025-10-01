# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
GDPR Compliance Service

Implements GDPR compliance features including:
- Data anonymization
- Data export (Right to Data Portability)
- Data deletion (Right to be Forgotten)
- Consent management
- Data processing records
"""

import json
import hashlib
import zipfile
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text

class GDPRRequestType(Enum):
    """Types of GDPR requests"""
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    DATA_ANONYMIZATION = "data_anonymization"
    CONSENT_WITHDRAWAL = "consent_withdrawal"
    DATA_RECTIFICATION = "data_rectification"
    PROCESSING_RESTRICTION = "processing_restriction"

class GDPRRequestStatus(Enum):
    """Status of GDPR requests"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class GDPRRequest:
    """GDPR request record"""
    request_id: str
    user_id: int
    request_type: GDPRRequestType
    status: GDPRRequestStatus
    created_at: str
    completed_at: Optional[str] = None
    details: Dict[str, Any] = None
    result_path: Optional[str] = None
    error_message: Optional[str] = None

class GDPRComplianceService:
    """
    GDPR Compliance Service
    
    Provides comprehensive GDPR compliance capabilities including:
    - Right to Data Portability (Article 20)
    - Right to be Forgotten (Article 17)
    - Right to Rectification (Article 16)
    - Right to Restrict Processing (Article 18)
    - Data anonymization
    - Consent management
    """
    
    def __init__(self, db_manager, audit_logger, config: Dict[str, Any]):
        self.db_manager = db_manager
        self.audit_logger = audit_logger
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # GDPR configuration
        self.data_retention_days = config.get('data_retention_days', 2555)  # 7 years default
        self.anonymization_enabled = config.get('anonymization_enabled', True)
        self.export_format = config.get('export_format', 'json')
        self.export_path = Path(config.get('export_path', '/app/storage/gdpr_exports'))
        
        # Ensure export directory exists
        self.export_path.mkdir(parents=True, exist_ok=True)
    
    def create_gdpr_request(self, user_id: int, request_type: GDPRRequestType,
                           details: Dict[str, Any] = None) -> str:
        """
        Create a new GDPR request
        
        Args:
            user_id: User ID making the request
            request_type: Type of GDPR request
            details: Additional request details
            
        Returns:
            Request ID
        """
        # Generate unique request ID
        request_id = hashlib.sha256(
            f"{user_id}{request_type.value}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Create request record
        request = GDPRRequest(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            status=GDPRRequestStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            details=details or {}
        )
        
        # Store request in database
        with self.db_manager.get_session() as session:
            session.execute(text("""
                INSERT INTO gdpr_requests 
                (request_id, user_id, request_type, status, created_at, details)
                VALUES (:request_id, :user_id, :request_type, :status, :created_at, :details)
            """), {
                'request_id': request.request_id,
                'user_id': request.user_id,
                'request_type': request.request_type.value,
                'status': request.status.value,
                'created_at': request.created_at,
                'details': json.dumps(request.details)
            })
            session.commit()
        
        # Log GDPR request
        self.audit_logger.log_gdpr_request(
            user_id=user_id,
            username=self._get_username(user_id),
            request_type=request_type.value,
            outcome="SUCCESS",
            details={
                'request_id': request_id,
                'request_details': details
            }
        )
        
        self.logger.info(f"Created GDPR request {request_id} for user {user_id}")
        return request_id
    
    def process_data_export_request(self, request_id: str) -> Tuple[bool, Optional[str]]:
        """
        Process data export request (Right to Data Portability)
        
        Args:
            request_id: GDPR request ID
            
        Returns:
            Tuple of (success, export_file_path)
        """
        try:
            # Update request status
            self._update_request_status(request_id, GDPRRequestStatus.IN_PROGRESS)
            
            # Get request details
            request = self._get_request(request_id)
            if not request:
                return False, "Request not found"
            
            user_id = request.user_id
            
            # Collect all user data
            user_data = self._collect_user_data(user_id)
            
            # Create export file
            export_filename = f"gdpr_export_{user_id}_{request_id}.zip"
            export_path = self.export_path / export_filename
            
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add user data as JSON
                zipf.writestr('user_data.json', json.dumps(user_data, indent=2, default=str))
                
                # Add metadata
                metadata = {
                    'export_date': datetime.now(timezone.utc).isoformat(),
                    'user_id': user_id,
                    'request_id': request_id,
                    'data_categories': list(user_data.keys()),
                    'gdpr_article': 'Article 20 - Right to Data Portability'
                }
                zipf.writestr('export_metadata.json', json.dumps(metadata, indent=2))
                
                # Add user images if they exist
                self._add_user_images_to_export(zipf, user_id)
            
            # Update request with completion
            self._update_request_status(
                request_id, 
                GDPRRequestStatus.COMPLETED,
                result_path=str(export_path)
            )
            
            # Log completion
            self.audit_logger.log_gdpr_request(
                user_id=user_id,
                username=self._get_username(user_id),
                request_type="data_export_completed",
                outcome="SUCCESS",
                details={
                    'request_id': request_id,
                    'export_file': export_filename,
                    'data_categories': list(user_data.keys())
                }
            )
            
            self.logger.info(f"Completed data export for request {request_id}")
            return True, str(export_path)
            
        except Exception as e:
            self.logger.error(f"Failed to process data export request {request_id}: {e}")
            self._update_request_status(
                request_id, 
                GDPRRequestStatus.FAILED,
                error_message=str(e)
            )
            return False, str(e)
    
    def process_data_deletion_request(self, request_id: str) -> Tuple[bool, Optional[str]]:
        """
        Process data deletion request (Right to be Forgotten)
        
        Args:
            request_id: GDPR request ID
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update request status
            self._update_request_status(request_id, GDPRRequestStatus.IN_PROGRESS)
            
            # Get request details
            request = self._get_request(request_id)
            if not request:
                return False, "Request not found"
            
            user_id = request.user_id
            username = self._get_username(user_id)
            
            # Collect data before deletion for audit
            user_data_summary = self._get_user_data_summary(user_id)
            
            # Delete user data
            deletion_results = self._delete_user_data(user_id)
            
            # Update request with completion
            self._update_request_status(
                request_id, 
                GDPRRequestStatus.COMPLETED,
                result_path="data_deleted"
            )
            
            # Log completion
            self.audit_logger.log_gdpr_request(
                user_id=user_id,
                username=username,
                request_type="data_deletion_completed",
                outcome="SUCCESS",
                details={
                    'request_id': request_id,
                    'deleted_records': deletion_results,
                    'data_summary': user_data_summary
                }
            )
            
            self.logger.info(f"Completed data deletion for request {request_id}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Failed to process data deletion request {request_id}: {e}")
            self._update_request_status(
                request_id, 
                GDPRRequestStatus.FAILED,
                error_message=str(e)
            )
            return False, str(e)
    
    def process_data_anonymization_request(self, request_id: str) -> Tuple[bool, Optional[str]]:
        """
        Process data anonymization request
        
        Args:
            request_id: GDPR request ID
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update request status
            self._update_request_status(request_id, GDPRRequestStatus.IN_PROGRESS)
            
            # Get request details
            request = self._get_request(request_id)
            if not request:
                return False, "Request not found"
            
            user_id = request.user_id
            username = self._get_username(user_id)
            
            # Anonymize user data
            anonymization_results = self._anonymize_user_data(user_id)
            
            # Update request with completion
            self._update_request_status(
                request_id, 
                GDPRRequestStatus.COMPLETED,
                result_path="data_anonymized"
            )
            
            # Log completion
            self.audit_logger.log_gdpr_request(
                user_id=user_id,
                username=username,
                request_type="data_anonymization_completed",
                outcome="SUCCESS",
                details={
                    'request_id': request_id,
                    'anonymized_records': anonymization_results
                }
            )
            
            self.logger.info(f"Completed data anonymization for request {request_id}")
            return True, None
            
        except Exception as e:
            self.logger.error(f"Failed to process data anonymization request {request_id}: {e}")
            self._update_request_status(
                request_id, 
                GDPRRequestStatus.FAILED,
                error_message=str(e)
            )
            return False, str(e)
    
    def _collect_user_data(self, user_id: int) -> Dict[str, Any]:
        """Collect all user data for export"""
        user_data = {}
        
        with self.db_manager.get_session() as session:
            # User profile data
            user_result = session.execute(text("""
                SELECT * FROM users WHERE id = :user_id
            """), {'user_id': user_id}).fetchone()
            
            if user_result:
                user_data['profile'] = dict(user_result._mapping)
                # Remove sensitive fields
                user_data['profile'].pop('password_hash', None)
            
            # Platform connections
            platforms_result = session.execute(text("""
                SELECT id, platform_name, username, created_at, updated_at, is_active
                FROM platform_connections WHERE user_id = :user_id
            """), {'user_id': user_id}).fetchall()
            
            user_data['platform_connections'] = [
                dict(row._mapping) for row in platforms_result
            ]
            
            # Posts and images
            posts_result = session.execute(text("""
                SELECT p.*, i.filename, i.caption, i.ai_generated_caption
                FROM posts p
                LEFT JOIN images i ON p.id = i.post_id
                WHERE p.user_id = :user_id
            """), {'user_id': user_id}).fetchall()
            
            user_data['posts_and_images'] = [
                dict(row._mapping) for row in posts_result
            ]
            
            # Processing runs
            runs_result = session.execute(text("""
                SELECT * FROM processing_runs WHERE user_id = :user_id
            """), {'user_id': user_id}).fetchall()
            
            user_data['processing_runs'] = [
                dict(row._mapping) for row in runs_result
            ]
            
            # User sessions (recent)
            sessions_result = session.execute(text("""
                SELECT session_id, created_at, last_activity, ip_address, user_agent
                FROM user_sessions 
                WHERE user_id = :user_id 
                AND created_at > :cutoff_date
            """), {
                'user_id': user_id,
                'cutoff_date': datetime.now(timezone.utc) - timedelta(days=90)
            }).fetchall()
            
            user_data['recent_sessions'] = [
                dict(row._mapping) for row in sessions_result
            ]
        
        return user_data
    
    def _get_user_data_summary(self, user_id: int) -> Dict[str, int]:
        """Get summary of user data for audit purposes"""
        summary = {}
        
        with self.db_manager.get_session() as session:
            # Count records in each table
            tables = [
                'platform_connections',
                'posts', 
                'images',
                'processing_runs',
                'user_sessions'
            ]
            
            for table in tables:
                result = session.execute(text(f"""
                    SELECT COUNT(*) as count FROM {table} WHERE user_id = :user_id
                """), {'user_id': user_id}).fetchone()
                summary[table] = result.count if result else 0
        
        return summary
    
    def _delete_user_data(self, user_id: int) -> Dict[str, int]:
        """Delete all user data"""
        deletion_results = {}
        
        with self.db_manager.get_session() as session:
            # Delete in order to respect foreign key constraints
            tables = [
                'user_sessions',
                'processing_runs', 
                'images',
                'posts',
                'platform_connections',
                'gdpr_requests'
            ]
            
            for table in tables:
                result = session.execute(text(f"""
                    DELETE FROM {table} WHERE user_id = :user_id
                """), {'user_id': user_id})
                deletion_results[table] = result.rowcount
            
            # Finally delete user record
            result = session.execute(text("""
                DELETE FROM users WHERE id = :user_id
            """), {'user_id': user_id})
            deletion_results['users'] = result.rowcount
            
            session.commit()
        
        return deletion_results
    
    def _anonymize_user_data(self, user_id: int) -> Dict[str, int]:
        """Anonymize user data instead of deleting"""
        anonymization_results = {}
        
        # Generate anonymous identifier
        anon_id = f"anon_{hashlib.sha256(str(user_id).encode()).hexdigest()[:8]}"
        
        with self.db_manager.get_session() as session:
            # Anonymize user profile
            result = session.execute(text("""
                UPDATE users SET 
                    username = :anon_username,
                    email = :anon_email,
                    first_name = 'Anonymous',
                    last_name = 'User',
                    updated_at = :updated_at
                WHERE id = :user_id
            """), {
                'anon_username': anon_id,
                'anon_email': f"{anon_id}@anonymized.local",
                'updated_at': datetime.now(timezone.utc),
                'user_id': user_id
            })
            anonymization_results['users'] = result.rowcount
            
            # Anonymize platform connections
            result = session.execute(text("""
                UPDATE platform_connections SET
                    username = :anon_username,
                    updated_at = :updated_at
                WHERE user_id = :user_id
            """), {
                'anon_username': anon_id,
                'updated_at': datetime.now(timezone.utc),
                'user_id': user_id
            })
            anonymization_results['platform_connections'] = result.rowcount
            
            session.commit()
        
        return anonymization_results
    
    def _add_user_images_to_export(self, zipf: zipfile.ZipFile, user_id: int):
        """Add user images to export archive"""
        try:
            with self.db_manager.get_session() as session:
                images_result = session.execute(text("""
                    SELECT i.filename, i.caption, i.ai_generated_caption
                    FROM images i
                    JOIN posts p ON i.post_id = p.id
                    WHERE p.user_id = :user_id
                """), {'user_id': user_id}).fetchall()
                
                for image in images_result:
                    image_path = Path(f"/app/storage/images/{image.filename}")
                    if image_path.exists():
                        zipf.write(image_path, f"images/{image.filename}")
        except Exception as e:
            self.logger.warning(f"Failed to add images to export: {e}")
    
    def _get_request(self, request_id: str) -> Optional[GDPRRequest]:
        """Get GDPR request by ID"""
        with self.db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT * FROM gdpr_requests WHERE request_id = :request_id
            """), {'request_id': request_id}).fetchone()
            
            if result:
                return GDPRRequest(
                    request_id=result.request_id,
                    user_id=result.user_id,
                    request_type=GDPRRequestType(result.request_type),
                    status=GDPRRequestStatus(result.status),
                    created_at=result.created_at,
                    completed_at=result.completed_at,
                    details=json.loads(result.details) if result.details else {},
                    result_path=result.result_path,
                    error_message=result.error_message
                )
        return None
    
    def _update_request_status(self, request_id: str, status: GDPRRequestStatus,
                              result_path: str = None, error_message: str = None):
        """Update GDPR request status"""
        with self.db_manager.get_session() as session:
            update_data = {
                'status': status.value,
                'request_id': request_id
            }
            
            if status == GDPRRequestStatus.COMPLETED:
                update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            if result_path:
                update_data['result_path'] = result_path
            
            if error_message:
                update_data['error_message'] = error_message
            
            session.execute(text("""
                UPDATE gdpr_requests SET 
                    status = :status,
                    completed_at = :completed_at,
                    result_path = :result_path,
                    error_message = :error_message
                WHERE request_id = :request_id
            """), {
                'status': update_data['status'],
                'completed_at': update_data.get('completed_at'),
                'result_path': update_data.get('result_path'),
                'error_message': update_data.get('error_message'),
                'request_id': request_id
            })
            session.commit()
    
    def _get_username(self, user_id: int) -> Optional[str]:
        """Get username for user ID"""
        with self.db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT username FROM users WHERE id = :user_id
            """), {'user_id': user_id}).fetchone()
            return result.username if result else None
    
    def get_gdpr_requests(self, user_id: int = None, 
                         status: GDPRRequestStatus = None) -> List[GDPRRequest]:
        """Get GDPR requests with optional filtering"""
        requests = []
        
        with self.db_manager.get_session() as session:
            query = "SELECT * FROM gdpr_requests WHERE 1=1"
            params = {}
            
            if user_id:
                query += " AND user_id = :user_id"
                params['user_id'] = user_id
            
            if status:
                query += " AND status = :status"
                params['status'] = status.value
            
            query += " ORDER BY created_at DESC"
            
            results = session.execute(text(query), params).fetchall()
            
            for result in results:
                requests.append(GDPRRequest(
                    request_id=result.request_id,
                    user_id=result.user_id,
                    request_type=GDPRRequestType(result.request_type),
                    status=GDPRRequestStatus(result.status),
                    created_at=result.created_at,
                    completed_at=result.completed_at,
                    details=json.loads(result.details) if result.details else {},
                    result_path=result.result_path,
                    error_message=result.error_message
                ))
        
        return requests