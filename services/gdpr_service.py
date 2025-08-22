# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
GDPR Compliance Service

This module provides comprehensive GDPR compliance functionality including
data subject rights, privacy management, and consent tracking.
"""

import logging
import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import User, UserRole, UserAuditLog, GDPRAuditLog, PlatformConnection, Post, Image, ProcessingRun
from services.email_service import email_service

logger = logging.getLogger(__name__)

class GDPRDataSubjectService:
    """Service for handling GDPR data subject rights"""
    
    def __init__(self, db_session: Session, base_url: str = "http://localhost:5000"):
        """Initialize GDPR data subject service"""
        self.db_session = db_session
        self.base_url = base_url
    
    def export_personal_data(self, user_id: int, 
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Export user's personal data in machine-readable format (GDPR Article 20)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Get comprehensive user data
            user_data = user.export_personal_data()
            
            # Get platform connections with decrypted credentials
            platform_data = []
            for pc in user.platform_connections:
                platform_info = {
                    'id': pc.id,
                    'name': pc.name,
                    'platform_type': pc.platform_type,
                    'instance_url': pc.instance_url,
                    'username': pc.username,
                    'is_default': pc.is_default,
                    'is_active': pc.is_active,
                    'created_at': pc.created_at.isoformat() if pc.created_at else None,
                    'last_used': pc.last_used.isoformat() if pc.last_used else None
                }
                # Note: We don't export access tokens for security reasons
                platform_data.append(platform_info)
            
            # Get user's posts
            posts_data = []
            posts = self.db_session.query(Post).join(Post.platform_connection).filter(
                Post.platform_connection.has(user_id=user_id)
            ).all()
            
            for post in posts:
                posts_data.append({
                    'post_id': post.post_id,
                    'post_url': post.post_url,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                    'platform_type': post.platform_type,
                    'instance_url': post.instance_url,
                    'has_images': len(post.images) > 0,
                    'image_count': len(post.images)
                })
            
            # Get user's images and captions
            images_data = []
            images = self.db_session.query(Image).join(Image.platform_connection).filter(
                Image.platform_connection.has(user_id=user_id)
            ).all()
            
            for image in images:
                images_data.append({
                    'image_id': image.id,
                    'image_url': image.image_url,
                    'original_caption': image.original_caption,
                    'generated_caption': image.generated_caption,
                    'reviewed_caption': image.reviewed_caption,
                    'final_caption': image.final_caption,
                    'status': image.status.value if image.status else None,
                    'created_at': image.created_at.isoformat() if image.created_at else None,
                    'reviewed_at': image.reviewed_at.isoformat() if image.reviewed_at else None,
                    'reviewer_notes': image.reviewer_notes,
                    'quality_score': image.quality_score,
                    'processing_metadata': image.processing_metadata
                })
            
            # Get processing runs
            processing_runs_data = []
            processing_runs = self.db_session.query(ProcessingRun).join(ProcessingRun.platform_connection).filter(
                ProcessingRun.platform_connection.has(user_id=user_id)
            ).all()
            
            for run in processing_runs:
                processing_runs_data.append({
                    'run_id': run.id,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'posts_processed': run.posts_processed,
                    'images_processed': run.images_processed,
                    'captions_generated': run.captions_generated,
                    'status': run.status,
                    'error_message': run.error_message
                })
            
            # Get audit log entries
            audit_logs = []
            user_audit_entries = self.db_session.query(UserAuditLog).filter_by(user_id=user_id).all()
            
            for entry in user_audit_entries:
                audit_logs.append({
                    'action': entry.action,
                    'details': entry.details,
                    'created_at': entry.created_at.isoformat() if entry.created_at else None,
                    'ip_address': entry.ip_address,
                    'user_agent': entry.user_agent
                })
            
            # Compile complete data export in machine-readable format
            complete_data = {
                'data_export_info': {
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'export_format': 'JSON',
                    'gdpr_article': 'Article 20 - Right to data portability',
                    'data_controller': 'Vedfolnir Application',
                    'export_version': '1.0'
                },
                'personal_data': {
                    'user_profile': user_data,
                    'platform_connections': platform_data,
                    'content_data': {
                        'posts': posts_data,
                        'images': images_data,
                        'processing_runs': processing_runs_data
                    },
                    'activity_log': audit_logs
                },
                'data_categories': {
                    'identity_data': ['username', 'email', 'first_name', 'last_name'],
                    'contact_data': ['email'],
                    'technical_data': ['platform_connections', 'processing_runs'],
                    'usage_data': ['activity_log', 'posts', 'images'],
                    'consent_data': ['data_processing_consent', 'data_processing_consent_date']
                }
            }
            
            # Log data export in both audit logs
            UserAuditLog.log_action(
                self.db_session,
                action="gdpr_data_exported",
                user_id=user.id,
                details=f"Personal data exported under GDPR Article 20 from {ip_address or 'unknown IP'}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            GDPRAuditLog.log_gdpr_action(
                self.db_session,
                action_type="data_export",
                gdpr_article="Article 20",
                user_id=user.id,
                action_details="Personal data exported for portability",
                response_data={"export_size": len(str(complete_data)), "categories_included": list(complete_data['data_categories'].keys())},
                status="completed",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"GDPR data export completed for user {user.username}")
            return True, "Personal data exported successfully", complete_data
            
        except Exception as e:
            logger.error(f"Error exporting personal data for user {user_id}: {e}")
            return False, "Data export failed due to system error", None
    
    def rectify_personal_data(self, user_id: int, rectification_data: Dict[str, Any],
                            ip_address: Optional[str] = None,
                            user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Rectify (correct) user's personal data (GDPR Article 16)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Store original values for audit logging
            original_values = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            
            changes_made = []
            
            # Validate and apply rectifications
            if 'first_name' in rectification_data:
                new_first_name = rectification_data['first_name']
                if new_first_name != user.first_name:
                    # Validate first name
                    if new_first_name and len(new_first_name.strip()) > 100:
                        return False, "First name must be no more than 100 characters", None
                    
                    user.first_name = new_first_name.strip() if new_first_name else None
                    changes_made.append(f"first_name: '{original_values['first_name']}' -> '{user.first_name}'")
            
            if 'last_name' in rectification_data:
                new_last_name = rectification_data['last_name']
                if new_last_name != user.last_name:
                    # Validate last name
                    if new_last_name and len(new_last_name.strip()) > 100:
                        return False, "Last name must be no more than 100 characters", None
                    
                    user.last_name = new_last_name.strip() if new_last_name else None
                    changes_made.append(f"last_name: '{original_values['last_name']}' -> '{user.last_name}'")
            
            if 'email' in rectification_data:
                new_email = rectification_data['email']
                if new_email != user.email:
                    # Validate email
                    from services.user_management_service import UserRegistrationService
                    registration_service = UserRegistrationService(self.db_session)
                    email_valid, email_result = registration_service.validate_email_address(new_email)
                    
                    if not email_valid:
                        return False, f"Invalid email address: {email_result}", None
                    
                    normalized_email = email_result
                    
                    # Check if email is already in use by another user
                    existing_user = self.db_session.query(User).filter(
                        User.email == normalized_email,
                        User.id != user_id
                    ).first()
                    
                    if existing_user:
                        return False, "Email address is already in use by another user", None
                    
                    # Update email and mark as unverified
                    user.email = normalized_email
                    user.email_verified = False
                    user.email_verification_token = None
                    user.email_verification_sent_at = None
                    
                    changes_made.append(f"email: '{original_values['email']}' -> '{user.email}' (requires re-verification)")
            
            # If no changes were made, return success without database update
            if not changes_made:
                return True, "No rectifications were needed", {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'changes_made': []
                }
            
            # Save changes
            self.db_session.commit()
            
            # Log data rectification
            UserAuditLog.log_action(
                self.db_session,
                action="gdpr_data_rectified",
                user_id=user.id,
                details=f"Personal data rectified under GDPR Article 16: {'; '.join(changes_made)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"GDPR data rectification completed for user {user.username}: {'; '.join(changes_made)}")
            
            return True, "Personal data rectified successfully", {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'changes_made': changes_made
            }
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error rectifying personal data for user {user_id}: {e}")
            return False, "Data rectification failed due to system error", None
    
    def erase_personal_data(self, user_id: int, 
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          admin_user_id: Optional[int] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Erase user's personal data with cascading deletion (GDPR Article 17)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Prevent deletion of the last admin user
            if user.role == UserRole.ADMIN:
                admin_count = self.db_session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
                if admin_count <= 1:
                    return False, "Cannot delete the last admin user", None
            
            # Store user info for logging before deletion
            username = user.username
            email = user.email
            
            # Get all related data for deletion summary
            platform_connections = list(user.platform_connections)
            
            # Get all posts through platform connections
            posts_to_delete = []
            for pc in platform_connections:
                posts_to_delete.extend(pc.posts)
            
            # Get all images through platform connections
            images_to_delete = []
            for pc in platform_connections:
                images_to_delete.extend(pc.images)
            
            # Get all processing runs through platform connections
            processing_runs_to_delete = []
            for pc in platform_connections:
                processing_runs_to_delete.extend(pc.processing_runs)
            
            # Delete physical image files from storage
            deleted_files = []
            for image in images_to_delete:
                if image.local_path and os.path.exists(image.local_path):
                    try:
                        os.remove(image.local_path)
                        deleted_files.append(image.local_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete image file {image.local_path}: {e}")
            
            # Delete user directory if it exists
            user_storage_dir = f"storage/images/user_{user_id}"
            if os.path.exists(user_storage_dir):
                try:
                    shutil.rmtree(user_storage_dir)
                    deleted_files.append(user_storage_dir)
                except Exception as e:
                    logger.warning(f"Failed to delete user storage directory {user_storage_dir}: {e}")
            
            # Create deletion summary before actual deletion
            deletion_summary = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'deletion_timestamp': datetime.utcnow().isoformat(),
                'deleted_data': {
                    'platform_connections': len(platform_connections),
                    'posts': len(posts_to_delete),
                    'images': len(images_to_delete),
                    'processing_runs': len(processing_runs_to_delete),
                    'files_deleted': len(deleted_files)
                },
                'gdpr_article': 'Article 17 - Right to erasure',
                'deletion_method': 'complete_erasure'
            }
            
            # Log deletion before actual deletion (so we have the user_id)
            UserAuditLog.log_action(
                self.db_session,
                action="gdpr_data_erasure_initiated",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"Complete data erasure initiated under GDPR Article 17 for user {username} ({email})",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            # Delete user (cascading will handle related records)
            self.db_session.delete(user)
            self.db_session.commit()
            
            # Log completion (without user_id since user is deleted)
            UserAuditLog.log_action(
                self.db_session,
                action="gdpr_data_erasure_completed",
                admin_user_id=admin_user_id,
                details=f"Complete data erasure completed for user {username} ({email}). Deleted: {len(platform_connections)} platforms, {len(posts_to_delete)} posts, {len(images_to_delete)} images, {len(processing_runs_to_delete)} runs, {len(deleted_files)} files",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"GDPR complete data erasure completed for user {username}")
            return True, "Personal data erased successfully", deletion_summary
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error erasing personal data for user {user_id}: {e}")
            return False, "Data erasure failed due to system error", None
    
    def anonymize_personal_data(self, user_id: int,
                              ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None,
                              admin_user_id: Optional[int] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Anonymize user's personal data while preserving system integrity (GDPR Article 17 alternative)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Prevent anonymization of the last admin user
            if user.role == UserRole.ADMIN:
                admin_count = self.db_session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
                if admin_count <= 1:
                    return False, "Cannot anonymize the last admin user", None
            
            # Store original info for logging
            original_username = user.username
            original_email = user.email
            
            # Anonymize user data
            anonymous_id = user.anonymize_data()
            
            # Delete physical image files but keep database records for system integrity
            deleted_files = []
            for pc in user.platform_connections:
                for image in pc.images:
                    if image.local_path and os.path.exists(image.local_path):
                        try:
                            os.remove(image.local_path)
                            deleted_files.append(image.local_path)
                            # Clear the local path but keep the record
                            image.local_path = None
                        except Exception as e:
                            logger.warning(f"Failed to delete image file {image.local_path}: {e}")
            
            # Delete user storage directory
            user_storage_dir = f"storage/images/user_{user_id}"
            if os.path.exists(user_storage_dir):
                try:
                    shutil.rmtree(user_storage_dir)
                    deleted_files.append(user_storage_dir)
                except Exception as e:
                    logger.warning(f"Failed to delete user storage directory {user_storage_dir}: {e}")
            
            # Anonymize platform connections
            for pc in user.platform_connections:
                pc.name = f"anonymized_platform_{anonymous_id}"
                pc.username = f"anonymized_user_{anonymous_id}"
                pc.is_active = False
                # Keep encrypted credentials for system integrity but mark as inactive
            
            self.db_session.commit()
            
            # Create anonymization summary
            anonymization_summary = {
                'user_id': user_id,
                'original_username': original_username,
                'original_email': original_email,
                'anonymous_id': anonymous_id,
                'new_username': user.username,
                'new_email': user.email,
                'anonymization_timestamp': datetime.utcnow().isoformat(),
                'anonymized_data': {
                    'platform_connections': len(user.platform_connections),
                    'files_deleted': len(deleted_files)
                },
                'gdpr_article': 'Article 17 - Right to erasure (anonymization)',
                'anonymization_method': 'data_anonymization'
            }
            
            # Log anonymization
            UserAuditLog.log_action(
                self.db_session,
                action="gdpr_data_anonymized",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"Personal data anonymized under GDPR Article 17 for user {original_username} ({original_email}) -> {user.username} ({user.email})",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"GDPR data anonymization completed for user {original_username} -> {user.username}")
            return True, "Personal data anonymized successfully", anonymization_summary
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error anonymizing personal data for user {user_id}: {e}")
            return False, "Data anonymization failed due to system error", None
    
    def get_data_processing_info(self, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Get information about data processing for the user (GDPR Article 13/14)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Get data processing information
            processing_info = {
                'data_controller': {
                    'name': 'Vedfolnir Application',
                    'purpose': 'Accessibility enhancement for social media platforms',
                    'legal_basis': 'Consent (GDPR Article 6(1)(a))'
                },
                'data_categories': {
                    'identity_data': ['username', 'email', 'first_name', 'last_name'],
                    'contact_data': ['email'],
                    'technical_data': ['platform_connections', 'access_tokens'],
                    'usage_data': ['posts', 'images', 'captions', 'processing_runs'],
                    'consent_data': ['data_processing_consent', 'consent_date']
                },
                'processing_purposes': [
                    'User authentication and authorization',
                    'Platform connection management',
                    'Image caption generation and review',
                    'Accessibility improvement for social media content',
                    'System audit and security monitoring'
                ],
                'data_retention': {
                    'user_data': 'Until account deletion or consent withdrawal',
                    'audit_logs': '7 years for security and compliance',
                    'session_data': '30 days or until logout',
                    'temporary_files': '24 hours or until processing complete'
                },
                'user_rights': [
                    'Right to access (Article 15)',
                    'Right to rectification (Article 16)',
                    'Right to erasure (Article 17)',
                    'Right to restrict processing (Article 18)',
                    'Right to data portability (Article 20)',
                    'Right to object (Article 21)',
                    'Right to withdraw consent (Article 7(3))'
                ],
                'data_sharing': {
                    'third_parties': ['Connected social media platforms'],
                    'purpose': 'Caption posting and content accessibility',
                    'legal_basis': 'User consent and legitimate interest'
                },
                'user_consent_status': {
                    'consent_given': user.data_processing_consent,
                    'consent_date': user.data_processing_consent_date.isoformat() if user.data_processing_consent_date else None,
                    'can_withdraw': True
                }
            }
            
            return True, "Data processing information retrieved successfully", processing_info
            
        except Exception as e:
            logger.error(f"Error getting data processing info for user {user_id}: {e}")
            return False, "Failed to retrieve data processing information", None
    
    async def send_data_export_email(self, user: User, export_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Send data export via email for GDPR compliance"""
        try:
            # Create a secure download link or attach the data
            # For security, we'll send a notification email rather than the actual data
            success = await email_service.send_data_export_notification(
                user_email=user.email,
                username=user.username,
                export_timestamp=export_data['data_export_info']['export_timestamp'],
                base_url=self.base_url
            )
            
            if success:
                logger.info(f"Data export notification sent to {user.email}")
                return True, "Data export notification sent successfully"
            else:
                logger.error(f"Failed to send data export notification to {user.email}")
                return False, "Failed to send data export notification"
                
        except Exception as e:
            logger.error(f"Error sending data export email to {user.email}: {e}")
            return False, f"Error sending data export email: {str(e)}"

class GDPRPrivacyService:
    """Service for handling GDPR privacy and consent management"""
    
    def __init__(self, db_session: Session):
        """Initialize GDPR privacy service"""
        self.db_session = db_session
    
    def record_consent(self, user_id: int, consent_type: str, consent_given: bool,
                      ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Record user consent for data processing"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found"
            
            if consent_given:
                user.give_consent()
                action = "consent_given"
                message = "Data processing consent recorded"
            else:
                user.withdraw_consent()
                action = "consent_withdrawn"
                message = "Data processing consent withdrawn"
            
            self.db_session.commit()
            
            # Log consent action
            UserAuditLog.log_action(
                self.db_session,
                action=f"gdpr_{action}",
                user_id=user.id,
                details=f"Data processing consent {action} for {consent_type}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"GDPR consent {action} for user {user.username}")
            return True, message
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error recording consent for user {user_id}: {e}")
            return False, "Failed to record consent"
    
    def get_consent_history(self, user_id: int) -> Tuple[bool, str, Optional[List[Dict[str, Any]]]]:
        """Get user's consent history"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Get consent-related audit log entries
            consent_entries = self.db_session.query(UserAuditLog).filter(
                UserAuditLog.user_id == user_id,
                UserAuditLog.action.like('%consent%')
            ).order_by(UserAuditLog.created_at.desc()).all()
            
            consent_history = []
            for entry in consent_entries:
                consent_history.append({
                    'action': entry.action,
                    'details': entry.details,
                    'timestamp': entry.created_at.isoformat() if entry.created_at else None,
                    'ip_address': entry.ip_address
                })
            
            # Add current consent status
            current_status = {
                'current_consent': user.data_processing_consent,
                'consent_date': user.data_processing_consent_date.isoformat() if user.data_processing_consent_date else None,
                'consent_history': consent_history
            }
            
            return True, "Consent history retrieved successfully", current_status
            
        except Exception as e:
            logger.error(f"Error getting consent history for user {user_id}: {e}")
            return False, "Failed to retrieve consent history", None
    
    def validate_gdpr_compliance(self, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Validate GDPR compliance for a user"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            compliance_status = {
                'user_id': user_id,
                'username': user.username,
                'compliance_check_timestamp': datetime.utcnow().isoformat(),
                'checks': {
                    'consent_given': {
                        'status': user.data_processing_consent,
                        'date': user.data_processing_consent_date.isoformat() if user.data_processing_consent_date else None,
                        'compliant': user.data_processing_consent
                    },
                    'data_minimization': {
                        'status': 'Data collection limited to necessary fields',
                        'compliant': True
                    },
                    'data_accuracy': {
                        'status': 'User can update profile data',
                        'compliant': True
                    },
                    'storage_limitation': {
                        'status': 'Data retained until account deletion',
                        'compliant': True
                    },
                    'security': {
                        'status': 'Password hashed, tokens encrypted',
                        'compliant': True
                    },
                    'transparency': {
                        'status': 'Privacy policy and data processing info available',
                        'compliant': True
                    }
                },
                'overall_compliant': user.data_processing_consent,
                'recommendations': []
            }
            
            if not user.data_processing_consent:
                compliance_status['recommendations'].append(
                    'User has not given consent for data processing'
                )
            
            if not user.email_verified:
                compliance_status['recommendations'].append(
                    'Email address not verified - may affect communication'
                )
            
            return True, "GDPR compliance validation completed", compliance_status
            
        except Exception as e:
            logger.error(f"Error validating GDPR compliance for user {user_id}: {e}")
            return False, "Failed to validate GDPR compliance", None
    
    def generate_privacy_report(self, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Generate comprehensive privacy report for user"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Get data processing info
            data_subject_service = GDPRDataSubjectService(self.db_session)
            success, message, processing_info = data_subject_service.get_data_processing_info(user_id)
            
            if not success:
                return False, message, None
            
            # Get consent history
            success, message, consent_info = self.get_consent_history(user_id)
            
            if not success:
                return False, message, None
            
            # Get compliance status
            success, message, compliance_info = self.validate_gdpr_compliance(user_id)
            
            if not success:
                return False, message, None
            
            # Compile privacy report
            privacy_report = {
                'report_info': {
                    'user_id': user_id,
                    'username': user.username,
                    'report_timestamp': datetime.utcnow().isoformat(),
                    'report_type': 'GDPR Privacy Report'
                },
                'data_processing': processing_info,
                'consent_management': consent_info,
                'compliance_status': compliance_info,
                'user_rights_exercised': self._get_rights_exercised(user_id)
            }
            
            return True, "Privacy report generated successfully", privacy_report
            
        except Exception as e:
            logger.error(f"Error generating privacy report for user {user_id}: {e}")
            return False, "Failed to generate privacy report", None
    
    def _get_rights_exercised(self, user_id: int) -> List[Dict[str, Any]]:
        """Get list of GDPR rights exercised by user"""
        try:
            gdpr_actions = self.db_session.query(UserAuditLog).filter(
                UserAuditLog.user_id == user_id,
                UserAuditLog.action.like('gdpr_%')
            ).order_by(UserAuditLog.created_at.desc()).all()
            
            rights_exercised = []
            for action in gdpr_actions:
                rights_exercised.append({
                    'right': action.action.replace('gdpr_', '').replace('_', ' ').title(),
                    'action': action.action,
                    'timestamp': action.created_at.isoformat() if action.created_at else None,
                    'details': action.details
                })
            
            return rights_exercised
            
        except Exception as e:
            logger.error(f"Error getting rights exercised for user {user_id}: {e}")
            return []