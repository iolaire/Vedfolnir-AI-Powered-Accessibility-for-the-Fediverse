# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, UniqueConstraint, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import DetachedInstanceError
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import logging
import json
import uuid
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

Base = declarative_base()

# Enhanced MySQL-specific table options for optimal performance
mysql_table_args = {
    'mysql_engine': 'InnoDB',
    'mysql_charset': 'utf8mb4',
    'mysql_collate': 'utf8mb4_unicode_ci',
    'mysql_row_format': 'DYNAMIC',  # Better for variable-length columns
}

class UserRole(Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

class ProcessingStatus(Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    ERROR = "error"

class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class AlertType(Enum):
    SYSTEM_ERROR = "system_error"
    RESOURCE_WARNING = "resource_warning"
    JOB_FAILURE = "job_failure"
    REPEATED_FAILURES = "repeated_failures"
    RESOURCE_LOW = "resource_low"
    AI_SERVICE_DOWN = "ai_service_down"
    QUEUE_BACKUP = "queue_backup"
    USER_ISSUE = "user_issue"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SECURITY_ALERT = "security_alert"

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = mysql_table_args
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(500), nullable=False, index=True)
    user_id = Column(String(200), nullable=False)
    post_url = Column(String(500), nullable=False)
    post_content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Platform identification
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id', ondelete='CASCADE'), nullable=True)
    platform_type = Column(String(50))  # For backward compatibility
    instance_url = Column(String(500))  # For backward compatibility
    
    # Relationships
    images = relationship("Image", back_populates="post", cascade="all, delete-orphan")
    platform_connection = relationship("PlatformConnection")
    
    # Table constraints and indexes for MySQL optimization
    __table_args__ = (
        UniqueConstraint('post_id', 'platform_connection_id', name='uq_post_platform'),
        Index('ix_post_platform_created', 'platform_connection_id', 'created_at'),
        Index('ix_post_created_at', 'created_at'),
        Index('ix_post_platform_type', 'platform_type'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    def validate_platform_consistency(self):
        """Validate that platform information is consistent"""
        if self.platform_connection_id:
            try:
                if self.platform_connection:
                    # If we have a platform connection, ensure compatibility fields match
                    if self.platform_type and self.platform_type != self.platform_connection.platform_type:
                        raise ValueError(f"Platform type mismatch: {self.platform_type} != {self.platform_connection.platform_type}")
                    if self.instance_url and self.instance_url != self.platform_connection.instance_url:
                        raise ValueError(f"Instance URL mismatch: {self.instance_url} != {self.platform_connection.instance_url}")
            except:
                # Skip validation if relationship access fails (detached object)
                pass
        elif not self.platform_type or not self.instance_url:
            raise ValueError("Post must have either platform_connection_id or both platform_type and instance_url")
    
    def get_platform_info(self):
        """Get platform information, preferring connection over compatibility fields"""
        try:
            if self.platform_connection:
                return {
                    'platform_type': self.platform_connection.platform_type,
                    'instance_url': self.platform_connection.instance_url,
                    'username': self.platform_connection.username
                }
        except:
            # Fall back to compatibility fields if relationship access fails
            pass
        
        return {
            'platform_type': self.platform_type,
            'instance_url': self.instance_url,
            'username': None
        }
    
    def __repr__(self):
        try:
            platform_info = self.get_platform_info()
            return f"<Post {self.post_id} on {platform_info['platform_type']}>"
        except:
            return f"<Post {self.post_id}>"

class Image(Base):
    __tablename__ = 'images'
    __table_args__ = mysql_table_args
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(Text, nullable=False)  # URLs can be very long, use TEXT
    local_path = Column(String(500), nullable=False)
    original_filename = Column(String(200))
    media_type = Column(String(100))
    image_post_id = Column(String(100))  # Pixelfed ID for updating descriptions
    attachment_index = Column(Integer, nullable=False)
    
    # Platform identification
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id', ondelete='CASCADE'), nullable=True)
    platform_type = Column(String(50))  # For backward compatibility
    instance_url = Column(String(500))  # For backward compatibility
    
    # Caption information
    original_caption = Column(Text)  # Original alt text if any
    generated_caption = Column(Text)  # AI-generated caption
    reviewed_caption = Column(Text)   # Human-reviewed caption
    final_caption = Column(Text)      # Final caption to be posted
    
    # Image classification and prompt information
    image_category = Column(String(50))  # Classified image category
    prompt_used = Column(Text)           # The prompt template used for generation
    
    # Processing status
    status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime)
    posted_at = Column(DateTime)
    original_post_date = Column(DateTime)  # Original Pixelfed post creation date
    
    # Metadata
    reviewer_notes = Column(Text)
    processing_error = Column(Text)
    caption_quality_score = Column(Integer)  # Score for caption quality (1-100)
    needs_special_review = Column(Boolean, default=False)  # Flag for captions needing special attention
    
    # Relationships
    post = relationship("Post", back_populates="images")
    platform_connection = relationship("PlatformConnection")
    
    # Table constraints and indexes for MySQL optimization
    __table_args__ = (
        UniqueConstraint('image_post_id', 'platform_connection_id', name='uq_image_platform'),
        UniqueConstraint('post_id', 'attachment_index', name='uq_post_attachment'),
        Index('ix_image_post_attachment', 'post_id', 'attachment_index'),
        Index('ix_image_platform_status', 'platform_connection_id', 'status'),
        Index('ix_image_status_created', 'status', 'created_at'),
        Index('ix_image_category', 'image_category'),
        Index('ix_image_quality_score', 'caption_quality_score'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    def validate_platform_consistency(self):
        """Validate that platform information is consistent with post"""
        if self.post:
            # Ensure image platform matches post platform
            if self.platform_connection_id != self.post.platform_connection_id:
                raise ValueError("Image platform connection must match post platform connection")
            if self.platform_type and self.platform_type != self.post.platform_type:
                raise ValueError("Image platform type must match post platform type")
            if self.instance_url and self.instance_url != self.post.instance_url:
                raise ValueError("Image instance URL must match post instance URL")
        
        # Validate platform connection consistency
        if self.platform_connection_id:
            try:
                if self.platform_connection:
                    if self.platform_type and self.platform_type != self.platform_connection.platform_type:
                        raise ValueError(f"Platform type mismatch: {self.platform_type} != {self.platform_connection.platform_type}")
                    if self.instance_url and self.instance_url != self.platform_connection.instance_url:
                        raise ValueError(f"Instance URL mismatch: {self.instance_url} != {self.platform_connection.instance_url}")
            except:
                # Skip validation if relationship access fails (detached object)
                pass
        elif not self.platform_type or not self.instance_url:
            raise ValueError("Image must have either platform_connection_id or both platform_type and instance_url")
    
    def get_platform_info(self):
        """Get platform information, preferring connection over compatibility fields"""
        try:
            if self.platform_connection:
                return {
                    'platform_type': self.platform_connection.platform_type,
                    'instance_url': self.platform_connection.instance_url,
                    'username': self.platform_connection.username
                }
        except:
            # Fall back if relationship access fails
            pass
        
        try:
            if self.post:
                return self.post.get_platform_info()
        except:
            # Fall back if post relationship access fails
            pass
        
        return {
            'platform_type': self.platform_type,
            'instance_url': self.instance_url,
            'username': None
        }
    
    def __repr__(self):
        try:
            platform_info = self.get_platform_info()
            return f"<Image {self.id} on {platform_info['platform_type']} - {self.image_url}>"
        except:
            return f"<Image {self.id} - {self.image_url}>"

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index('ix_user_email_active', 'email', 'is_active'),
        Index('ix_user_username_active', 'username', 'is_active'),
        Index('ix_user_role_active', 'role', 'is_active'),
        Index('ix_user_created_login', 'created_at', 'last_login'),
        Index('ix_user_verification_status', 'email_verified', 'is_active'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Email verification fields
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)
    
    # Profile management fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Password reset fields
    password_reset_token = Column(String(255), nullable=True)
    password_reset_sent_at = Column(DateTime, nullable=True)
    password_reset_used = Column(Boolean, default=False)
    
    # GDPR compliance fields
    data_processing_consent = Column(Boolean, default=False)
    data_processing_consent_date = Column(DateTime, nullable=True)
    
    # Account security fields
    account_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
    
    # Relationships with explicit loading strategies
    platform_connections = relationship(
        "PlatformConnection", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy='select',  # Use select loading instead of lazy loading
        order_by="PlatformConnection.created_at"
    )
    sessions = relationship(
        "UserSession", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy='select'  # Use select loading instead of lazy loading
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, required_role):
        """Check if user has the required role or higher"""
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.REVIEWER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    @hybrid_property
    def active_platforms(self):
        """Get active platforms for this user with session safety"""
        try:
            return [pc for pc in self.platform_connections if pc.is_active]
        except Exception:
            # If relationship access fails, return empty list to avoid DetachedInstanceError
            return []
    
    @hybrid_property
    def default_platform(self):
        """Get the default platform for this user with session safety"""
        try:
            active_platforms = self.active_platforms
            default = next((p for p in active_platforms if p.is_default), None)
            return default or (active_platforms[0] if active_platforms else None)
        except Exception:
            # If relationship access fails, return None to avoid DetachedInstanceError
            return None
    
    def get_default_platform(self):
        """Get user's default platform connection (legacy method)"""
        return self.default_platform
    
    def get_active_platforms(self):
        """Get all active platform connections for user (legacy method)"""
        return self.active_platforms
    
    def get_platform_by_type(self, platform_type):
        """Get platform connection by type"""
        return next((pc for pc in self.platform_connections if pc.platform_type == platform_type and pc.is_active), None)
    
    def get_platform_by_name(self, name):
        """Get platform connection by name"""
        return next((pc for pc in self.platform_connections if pc.name == name and pc.is_active), None)
    
    def set_default_platform(self, platform_connection_id):
        """Set a platform as the default, unsetting others"""
        for pc in self.platform_connections:
            pc.is_default = (pc.id == platform_connection_id)
    
    def has_platform_access(self, platform_type, instance_url):
        """Check if user has access to a specific platform instance"""
        return any(
            pc.platform_type == platform_type and 
            pc.instance_url == instance_url and 
            pc.is_active 
            for pc in self.platform_connections
        )
    
    # Email verification methods
    def generate_email_verification_token(self):
        """Generate a secure email verification token"""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = datetime.utcnow()
        return self.email_verification_token
    
    def verify_email_token(self, token):
        """Verify email verification token and mark email as verified"""
        if not self.email_verification_token or self.email_verification_token != token:
            return False
        
        # Check if token is expired (24 hours)
        if self.email_verification_sent_at:
            from datetime import timedelta
            if datetime.utcnow() - self.email_verification_sent_at > timedelta(hours=24):
                return False
        
        # Mark email as verified and clear token
        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_sent_at = None
        return True
    
    # Password reset methods
    def generate_password_reset_token(self):
        """Generate a secure password reset token"""
        import secrets
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_sent_at = datetime.utcnow()
        self.password_reset_used = False
        return self.password_reset_token
    
    def verify_password_reset_token(self, token):
        """Verify password reset token"""
        if not self.password_reset_token or self.password_reset_token != token:
            return False
        
        if self.password_reset_used:
            return False
        
        # Check if token is expired (1 hour)
        if self.password_reset_sent_at:
            from datetime import timedelta
            if datetime.utcnow() - self.password_reset_sent_at > timedelta(hours=1):
                return False
        
        return True
    
    def reset_password(self, new_password, token):
        """Reset password using token"""
        if not self.verify_password_reset_token(token):
            return False
        
        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_sent_at = None
        self.password_reset_used = True
        
        # Reset failed login attempts
        self.failed_login_attempts = 0
        self.account_locked = False
        self.last_failed_login = None
        
        return True
    
    # Account security methods
    def can_login(self):
        """Check if user can login (email verified and account not locked)"""
        return self.is_active and self.email_verified and not self.account_locked
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.utcnow()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked = True
    
    def unlock_account(self):
        """Unlock account and reset failed login attempts"""
        self.account_locked = False
        self.failed_login_attempts = 0
        self.last_failed_login = None
    
    # Profile methods
    def get_full_name(self):
        """Get formatted full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    def update_profile(self, first_name=None, last_name=None, email=None):
        """Update user profile information"""
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if email is not None and email != self.email:
            # Email change requires re-verification
            self.email = email
            self.email_verified = False
            self.email_verification_token = None
            self.email_verification_sent_at = None
    
    # GDPR compliance methods
    def give_consent(self):
        """Record user's data processing consent"""
        self.data_processing_consent = True
        self.data_processing_consent_date = datetime.utcnow()
    
    def withdraw_consent(self):
        """Withdraw user's data processing consent"""
        self.data_processing_consent = False
        self.data_processing_consent_date = datetime.utcnow()
    
    def export_personal_data(self):
        """Export user's personal data for GDPR compliance"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value if self.role else None,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'data_processing_consent': self.data_processing_consent,
            'data_processing_consent_date': self.data_processing_consent_date.isoformat() if self.data_processing_consent_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'platform_connections': [pc.to_dict() for pc in self.platform_connections if pc.is_active]
        }
    
    def anonymize_data(self):
        """Anonymize user data for GDPR compliance (soft delete)"""
        import uuid
        anonymous_id = str(uuid.uuid4())[:8]
        
        self.username = f"deleted_user_{anonymous_id}"
        self.email = f"deleted_{anonymous_id}@example.com"
        self.first_name = None
        self.last_name = None
        self.is_active = False
        self.email_verified = False
        self.data_processing_consent = False
        
        # Clear sensitive tokens
        self.email_verification_token = None
        self.password_reset_token = None
        
        # Keep audit trail but anonymize
        return anonymous_id
    
    # Flask-Login interface methods
    def get_id(self):
        """Return the user ID as a string for Flask-Login"""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """Return True if the user is authenticated"""
        return True
    
    @property
    def is_anonymous(self):
        """Return False as this is not an anonymous user"""
        return False
    
    def __repr__(self):
        return f"<User {self.username}>"

class UserAuditLog(Base):
    """Audit trail for user management actions"""
    __tablename__ = 'user_audit_log'
    __table_args__ = mysql_table_args
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    admin_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="audit_logs")
    admin_user = relationship("User", foreign_keys=[admin_user_id], backref="admin_actions")
    
    def __repr__(self):
        return f"<UserAuditLog {self.action} - User {self.user_id}>"
    
    @classmethod
    def log_action(cls, session, action, user_id=None, admin_user_id=None, 
                   details=None, ip_address=None, user_agent=None):
        """Create an audit log entry"""
        audit_entry = cls(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            admin_user_id=admin_user_id
        )
        session.add(audit_entry)
        return audit_entry

class GDPRAuditLog(Base):
    """Audit trail specifically for GDPR compliance actions"""
    __tablename__ = 'gdpr_audit_log'
    __table_args__ = mysql_table_args
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action_type = Column(String(50), nullable=False)  # export, rectification, erasure, consent, etc.
    gdpr_article = Column(String(20), nullable=True)  # Article 15, 16, 17, etc.
    action_details = Column(Text, nullable=True)
    request_data = Column(Text, nullable=True)  # JSON of request parameters
    response_data = Column(Text, nullable=True)  # JSON of response/result
    status = Column(String(20), default='pending')  # pending, completed, failed
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    admin_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="gdpr_audit_logs")
    admin_user = relationship("User", foreign_keys=[admin_user_id], backref="gdpr_admin_actions")
    
    def __repr__(self):
        return f"<GDPRAuditLog {self.action_type} - User {self.user_id}>"
    
    @classmethod
    def log_gdpr_action(cls, session, action_type, gdpr_article=None, user_id=None, 
                       admin_user_id=None, action_details=None, request_data=None,
                       response_data=None, status='pending', ip_address=None, user_agent=None):
        """Create a GDPR-specific audit log entry"""
        import json
        
        audit_entry = cls(
            user_id=user_id,
            action_type=action_type,
            gdpr_article=gdpr_article,
            action_details=action_details,
            request_data=json.dumps(request_data) if request_data else None,
            response_data=json.dumps(response_data) if response_data else None,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            admin_user_id=admin_user_id
        )
        session.add(audit_entry)
        return audit_entry
    
    def update_status(self, session, status, response_data=None, completed_at=None):
        """Update the status and completion details of a GDPR action"""
        import json
        from datetime import datetime
        
        self.status = status
        if response_data:
            self.response_data = json.dumps(response_data)
        if completed_at:
            self.completed_at = completed_at
        elif status in ['completed', 'failed']:
            self.completed_at = datetime.utcnow()
        
        session.commit()
        return self

class ProcessingRun(Base):
    __tablename__ = 'processing_runs'
    __table_args__ = (
        Index('ix_processing_run_user_started', 'user_id', 'started_at'),
        Index('ix_processing_run_platform_status', 'platform_connection_id', 'status'),
        Index('ix_processing_run_batch_id', 'batch_id'),
        Index('ix_processing_run_status_started', 'status', 'started_at'),
        UniqueConstraint('batch_id', 'platform_connection_id', name='uq_batch_platform'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(200), nullable=False)
    batch_id = Column(String(200), nullable=True)  # To group runs that are part of the same batch
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    posts_processed = Column(Integer, default=0)
    images_processed = Column(Integer, default=0)
    captions_generated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    status = Column(String(50), default="running")
    
    # Platform identification
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id', ondelete='CASCADE'), nullable=True)
    platform_type = Column(String(50))  # For backward compatibility
    instance_url = Column(String(500))  # For backward compatibility
    
    # Retry statistics
    retry_attempts = Column(Integer, default=0)
    retry_successes = Column(Integer, default=0)
    retry_failures = Column(Integer, default=0)
    retry_total_time = Column(Integer, default=0)  # Total time spent in retries (seconds)
    retry_stats_json = Column(Text)  # JSON serialized detailed retry statistics
    
    # Relationships
    platform_connection = relationship("PlatformConnection")
    
    def validate_platform_consistency(self):
        """Validate that platform information is consistent"""
        if self.platform_connection_id:
            try:
                if self.platform_connection:
                    # If we have a platform connection, ensure compatibility fields match
                    if self.platform_type and self.platform_type != self.platform_connection.platform_type:
                        raise ValueError(f"Platform type mismatch: {self.platform_type} != {self.platform_connection.platform_type}")
                    if self.instance_url and self.instance_url != self.platform_connection.instance_url:
                        raise ValueError(f"Instance URL mismatch: {self.instance_url} != {self.platform_connection.instance_url}")
            except:
                # Skip validation if relationship access fails (detached object)
                pass
        elif not self.platform_type or not self.instance_url:
            raise ValueError("ProcessingRun must have either platform_connection_id or both platform_type and instance_url")
    
    def get_platform_info(self):
        """Get platform information, preferring connection over compatibility fields"""
        try:
            if self.platform_connection:
                return {
                    'platform_type': self.platform_connection.platform_type,
                    'instance_url': self.platform_connection.instance_url,
                    'username': self.platform_connection.username
                }
        except:
            # Fall back to compatibility fields if relationship access fails
            pass
        
        return {
            'platform_type': self.platform_type,
            'instance_url': self.instance_url,
            'username': None
        }
    
    def __repr__(self):
        try:
            platform_info = self.get_platform_info()
            return f"<ProcessingRun {self.id} - {self.user_id} on {platform_info['platform_type']}>"
        except:
            return f"<ProcessingRun {self.id} - {self.user_id}>"

class PlatformConnection(Base):
    __tablename__ = 'platform_connections'
    __table_args__ = mysql_table_args
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    platform_type = Column(String(50), nullable=False)  # 'pixelfed', 'mastodon'
    instance_url = Column(String(500), nullable=False)
    username = Column(String(200))
    
    # Encrypted credentials
    _access_token = Column('access_token', Text, nullable=False)
    _client_key = Column('client_key', Text)
    _client_secret = Column('client_secret', Text)
    
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Relationships with explicit loading strategies
    user = relationship(
        "User", 
        back_populates="platform_connections",
        lazy='select'  # Use select loading instead of lazy loading
    )
    posts = relationship(
        "Post", 
        back_populates="platform_connection",
        lazy='select'  # Use select loading instead of lazy loading
    )
    images = relationship(
        "Image", 
        back_populates="platform_connection",
        lazy='select'  # Use select loading instead of lazy loading
    )
    processing_runs = relationship(
        "ProcessingRun", 
        back_populates="platform_connection",
        lazy='select'  # Use select loading instead of lazy loading
    )
    user_sessions = relationship(
        "UserSession", 
        back_populates="active_platform",
        lazy='select'  # Use select loading instead of lazy loading
    )
    
    # Table constraints and indexes for efficient platform queries
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_platform_name'),
        UniqueConstraint('user_id', 'instance_url', 'username', name='uq_user_instance_username'),
        Index('ix_platform_user_active', 'user_id', 'is_active'),
        Index('ix_platform_type_active', 'platform_type', 'is_active'),
        Index('ix_platform_instance_type', 'instance_url', 'platform_type'),
        Index('ix_platform_user_default', 'user_id', 'is_default'),
        Index('ix_platform_last_used', 'last_used'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    # Encryption key (should be stored securely in production)
    @classmethod
    def _get_encryption_key(cls):
        key = os.getenv('PLATFORM_ENCRYPTION_KEY')
        if not key:
            # In production, this should be a fatal error
            import sys
            if 'pytest' not in sys.modules:  # Allow tests to run without the key
                raise ValueError(
                    "PLATFORM_ENCRYPTION_KEY is required in .env file for platform credential encryption. "
                    "Please copy .env.example to .env and configure your security settings. "
                    "See docs/security/environment-setup.md for secure value generation."
                )
            else:
                # Generate a temporary key for testing
                key = Fernet.generate_key().decode()
                logging.warning("Using temporary encryption key for testing")
        if isinstance(key, str):
            key = key.encode()
        return key
    
    @classmethod
    def _get_cipher(cls):
        return Fernet(cls._get_encryption_key())
    
    @property
    def access_token(self):
        if self._access_token:
            try:
                cipher = self._get_cipher()
                return cipher.decrypt(self._access_token.encode()).decode()
            except Exception as e:
                logging.error(f"Failed to decrypt access token: {e}")
                return None
        return None
    
    @access_token.setter
    def access_token(self, value):
        if value:
            try:
                cipher = self._get_cipher()
                self._access_token = cipher.encrypt(value.encode()).decode()
            except Exception as e:
                logging.error(f"Failed to encrypt access token: {e}")
                raise
        else:
            self._access_token = None
    
    @property
    def client_key(self):
        if self._client_key:
            try:
                cipher = self._get_cipher()
                return cipher.decrypt(self._client_key.encode()).decode()
            except Exception as e:
                logging.error(f"Failed to decrypt client key: {e}")
                return None
        return None
    
    @client_key.setter
    def client_key(self, value):
        if value:
            try:
                cipher = self._get_cipher()
                self._client_key = cipher.encrypt(value.encode()).decode()
            except Exception as e:
                logging.error(f"Failed to encrypt client key: {e}")
                raise
        else:
            self._client_key = None
    
    @property
    def client_secret(self):
        if self._client_secret:
            try:
                cipher = self._get_cipher()
                return cipher.decrypt(self._client_secret.encode()).decode()
            except Exception as e:
                logging.error(f"Failed to decrypt client secret: {e}")
                return None
        return None
    
    @client_secret.setter
    def client_secret(self, value):
        if value:
            try:
                cipher = self._get_cipher()
                self._client_secret = cipher.encrypt(value.encode()).decode()
            except Exception as e:
                logging.error(f"Failed to encrypt client secret: {e}")
                raise
        else:
            self._client_secret = None
    
    def to_activitypub_config(self):
        """Convert to ActivityPubConfig for client usage (works with detached instances)"""
        # Check if we have required data
        if not self.instance_url or not self.platform_type:
            return None
            
        try:
            # Import here to avoid circular imports
            from config import ActivityPubConfig, RetryConfig, RateLimitConfig
            
            return ActivityPubConfig(
                instance_url=self.instance_url,
                access_token=self.access_token,
                api_type=self.platform_type,
                username=self.username,
                client_key=self.client_key,
                client_secret=self.client_secret,
                retry=RetryConfig.from_env(),
                rate_limit=RateLimitConfig.from_env()
            )
        except ImportError as e:
            logging.error(f"Failed to import config classes: {e}")
            return None
        except Exception as e:
            logging.error(f"Failed to create ActivityPub config: {e}")
            return None
    
    def test_connection(self):
        """Test the platform connection (works with detached instances)"""
        # Check basic requirements first
        if not self.is_accessible():
            return False, "Platform connection is not accessible (inactive or missing credentials)"
        
        try:
            # Import here to avoid circular imports
            from activitypub_client import ActivityPubClient
            import asyncio
            
            config = self.to_activitypub_config()
            if not config:
                return False, "Failed to create configuration"
            
            # Run the async test_connection method with proper context manager
            async def _test_async():
                async with ActivityPubClient(config) as client:
                    return await client.test_connection()
            
            # Create new event loop for the test
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(_test_async())
                loop.close()
                
                # Ensure we return a tuple
                if isinstance(result, tuple) and len(result) == 2:
                    return result
                else:
                    return False, f"Unexpected result format: {result}"
                    
            except Exception as e:
                return False, f"Connection test failed: {str(e)}"
                
        except Exception as e:
            logging.error(f"Connection test failed: {e}")
            return False, str(e)
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for safe serialization without session dependency"""
        result = {
            'id': self.id,
            'name': self.name,
            'platform_type': self.platform_type,
            'instance_url': self.instance_url,
            'username': self.username,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }
        
        if include_sensitive:
            # Only include sensitive data when explicitly requested
            result.update({
                'has_access_token': bool(self._access_token),
                'has_client_key': bool(self._client_key),
                'has_client_secret': bool(self._client_secret)
            })
        
        return result
    
    def safe_get_user(self):
        """Safely get user object, handling detached instances"""
        try:
            return self.user
        except DetachedInstanceError:
            return None
        except Exception:
            return None
    
    def safe_get_posts_count(self):
        """Safely get posts count, handling detached instances"""
        try:
            return len(self.posts) if self.posts else 0
        except DetachedInstanceError:
            return 0
        except Exception:
            return 0
    
    def safe_get_images_count(self):
        """Safely get images count, handling detached instances"""
        try:
            return len(self.images) if self.images else 0
        except DetachedInstanceError:
            return 0
        except Exception:
            return 0
    
    def is_accessible(self):
        """Check if platform connection is accessible (works with detached instances)"""
        return bool(self.is_active and self._access_token)
    
    def get_display_name(self):
        """Get display name for UI (works with detached instances)"""
        if self.name:
            return f"{self.name} ({self.platform_type})"
        return f"{self.username}@{self.instance_url} ({self.platform_type})"
    
    def matches_platform(self, platform_type, instance_url):
        """Check if this connection matches given platform details (works with detached instances)"""
        return (self.platform_type == platform_type and 
                self.instance_url == instance_url)
    
    def can_be_default(self):
        """Check if this connection can be set as default (works with detached instances)"""
        return self.is_active and bool(self._access_token)
    
    def __repr__(self):
        return f"<PlatformConnection {self.name} ({self.platform_type})>"

# UserSession model for enhanced session management
class UserSession(Base):
    """User session tracking for platform-aware session management"""
    __tablename__ = 'user_sessions'
    __table_args__ = mysql_table_args
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    active_platform_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, index=True)
    last_activity = Column(DateTime, default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    session_fingerprint = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships with explicit loading strategies
    user = relationship(
        'User', 
        back_populates='sessions',
        lazy='select'  # Use select loading instead of lazy loading
    )
    active_platform = relationship(
        'PlatformConnection', 
        back_populates='user_sessions',
        lazy='select'  # Use select loading instead of lazy loading
    )
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)
    
    def to_context_dict(self) -> Dict[str, Any]:
        """Convert session to context dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'platform_connection_id': self.active_platform_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'user_info': {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email,
                'role': self.user.role.value
            } if self.user else None,
            'platform_info': {
                'id': self.active_platform.id,
                'name': self.active_platform.name,
                'platform_type': self.active_platform.platform_type,
                'instance_url': self.active_platform.instance_url,
                'is_default': self.active_platform.is_default
            } if self.active_platform else None
        }
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
        from datetime import datetime, timezone
        self.last_activity = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def extend_expiration(self, hours: int = 24) -> None:
        """Extend session expiration by specified hours"""
        from datetime import datetime, timezone, timedelta
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.updated_at = datetime.now(timezone.utc)
    
    def time_until_expiry(self) -> int:
        """Get seconds until session expires"""
        from datetime import datetime, timezone
        if self.expires_at:
            delta = self.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
            return max(0, int(delta.total_seconds()))
        return 0
    
    def is_recently_active(self, minutes: int = 30) -> bool:
        """Check if session was active within specified minutes"""
        from datetime import datetime, timezone, timedelta
        if self.last_activity:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            return self.last_activity.replace(tzinfo=timezone.utc) > cutoff
        return False
    
    def get_session_duration(self) -> int:
        """Get session duration in seconds"""
        from datetime import datetime, timezone
        if self.created_at:
            delta = datetime.now(timezone.utc) - self.created_at.replace(tzinfo=timezone.utc)
            return int(delta.total_seconds())
        return 0
    
    @classmethod
    def find_by_session_id(cls, db_session, session_id: str):
        """Find active session by session ID"""
        return db_session.query(cls).filter_by(
            session_id=session_id,
            is_active=True
        ).first()
    
    @classmethod
    def find_user_sessions(cls, db_session, user_id: int, active_only: bool = True):
        """Find all sessions for a user"""
        query = db_session.query(cls).filter_by(user_id=user_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.last_activity.desc()).all()
    
    @classmethod
    def find_expired_sessions(cls, db_session):
        """Find all expired sessions"""
        from datetime import datetime, timezone
        return db_session.query(cls).filter(
            cls.expires_at < datetime.now(timezone.utc)
        ).all()
    
    @classmethod
    def cleanup_expired_sessions(cls, db_session) -> int:
        """Clean up expired sessions and return count"""
        expired_sessions = cls.find_expired_sessions(db_session)
        count = len(expired_sessions)
        
        for session in expired_sessions:
            db_session.delete(session)
        
        return count
    
    def __repr__(self):
        return f"<UserSession {self.session_id} - User {self.user_id}>"

# Data classes for caption generation
@dataclass
class CaptionGenerationSettings:
    max_posts_per_run: int = 50
    max_caption_length: int = 500
    optimal_min_length: int = 80
    optimal_max_length: int = 200
    reprocess_existing: bool = False
    processing_delay: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaptionGenerationSettings':
        return cls(**data)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CaptionGenerationSettings':
        return cls.from_dict(json.loads(json_str))

@dataclass
class GenerationResults:
    task_id: str
    posts_processed: int = 0
    images_processed: int = 0
    captions_generated: int = 0
    errors_count: int = 0
    skipped_existing: int = 0
    processing_time_seconds: float = 0.0
    error_details: List[Dict[str, Any]] = None
    generated_image_ids: List[int] = None
    
    def __post_init__(self):
        if self.error_details is None:
            self.error_details = []
        if self.generated_image_ids is None:
            self.generated_image_ids = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationResults':
        return cls(**data)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GenerationResults':
        return cls.from_dict(json.loads(json_str))

class CaptionGenerationTask(Base):
    __tablename__ = 'caption_generation_tasks'
    __table_args__ = (
        Index('ix_caption_task_user_status', 'user_id', 'status'),
        Index('ix_caption_task_platform_status', 'platform_connection_id', 'status'),
        Index('ix_caption_task_status_created', 'status', 'created_at'),
        Index('ix_caption_task_created_at', 'created_at'),
        Index('ix_caption_task_priority', 'priority'),
        Index('ix_caption_task_admin_cancelled', 'cancelled_by_admin'),
        Index('ix_caption_task_admin_user', 'admin_user_id'),
        Index('ix_caption_task_retry_count', 'retry_count'),
        Index('ix_caption_task_admin_managed', 'admin_managed'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id', ondelete='CASCADE'), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.QUEUED)
    settings_json = Column(Text)  # Serialized CaptionGenerationSettings
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    results_json = Column(Text)  # Serialized GenerationResults
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(200))
    
    # New fields for multi-tenant management
    priority = Column(SQLEnum(JobPriority, values_callable=lambda obj: [e.value for e in obj]), default=JobPriority.NORMAL)
    admin_notes = Column(Text)  # Admin comments/notes
    cancelled_by_admin = Column(Boolean, default=False)
    admin_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Admin who cancelled
    cancellation_reason = Column(String(500))
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    resource_usage = Column(Text)  # JSON: memory, CPU, processing time
    admin_managed = Column(Boolean, default=False)  # Whether job is managed by admin
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    platform_connection = relationship("PlatformConnection")
    cancelled_by = relationship("User", foreign_keys=[admin_user_id])
    
    # Note: Unique constraint on user_id removed to allow multiple tasks per user
    # Active task enforcement is handled in application logic
    
    @property
    def settings(self) -> Optional[CaptionGenerationSettings]:
        if self.settings_json:
            try:
                return CaptionGenerationSettings.from_json(self.settings_json)
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Failed to deserialize settings for task {self.id}: {e}")
                return None
        return None
    
    @settings.setter
    def settings(self, value: CaptionGenerationSettings):
        if value:
            self.settings_json = value.to_json()
        else:
            self.settings_json = None
    
    @property
    def results(self) -> Optional[GenerationResults]:
        if self.results_json:
            try:
                return GenerationResults.from_json(self.results_json)
            except (json.JSONDecodeError, TypeError) as e:
                logging.error(f"Failed to deserialize results for task {self.id}: {e}")
                return None
        return None
    
    @results.setter
    def results(self, value: GenerationResults):
        if value:
            self.results_json = value.to_json()
        else:
            self.results_json = None
    
    def is_active(self) -> bool:
        """Check if task is in an active state"""
        return self.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]
    
    def is_completed(self) -> bool:
        """Check if task is in a completed state"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    def can_be_cancelled(self) -> bool:
        """Check if task can be cancelled"""
        return self.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]
    
    def __repr__(self):
        return f"<CaptionGenerationTask {self.id} - User {self.user_id} - {self.status.value}>"

class CaptionGenerationUserSettings(Base):
    __tablename__ = 'caption_generation_user_settings'
    __table_args__ = (
        UniqueConstraint('user_id', 'platform_connection_id', name='uq_user_platform_settings'),
        Index('ix_caption_settings_user', 'user_id'),
        Index('ix_caption_settings_platform', 'platform_connection_id'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id', ondelete='CASCADE'), nullable=False)
    max_posts_per_run = Column(Integer, default=50)
    max_caption_length = Column(Integer, default=500)
    optimal_min_length = Column(Integer, default=80)
    optimal_max_length = Column(Integer, default=200)
    reprocess_existing = Column(Boolean, default=False)
    processing_delay = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    platform_connection = relationship("PlatformConnection")
    
    # Table constraints - one settings record per user per platform
    __table_args__ = (
        UniqueConstraint('user_id', 'platform_connection_id', name='uq_user_platform_settings'),
    )
    
    def to_settings_dataclass(self) -> CaptionGenerationSettings:
        """Convert to CaptionGenerationSettings dataclass"""
        return CaptionGenerationSettings(
            max_posts_per_run=self.max_posts_per_run,
            max_caption_length=self.max_caption_length,
            optimal_min_length=self.optimal_min_length,
            optimal_max_length=self.optimal_max_length,
            reprocess_existing=self.reprocess_existing,
            processing_delay=self.processing_delay
        )
    
    def update_from_dataclass(self, settings: CaptionGenerationSettings):
        """Update from CaptionGenerationSettings dataclass"""
        self.max_posts_per_run = settings.max_posts_per_run
        self.max_caption_length = settings.max_caption_length
        self.optimal_min_length = settings.optimal_min_length
        self.optimal_max_length = settings.optimal_max_length
        self.reprocess_existing = settings.reprocess_existing
        self.processing_delay = settings.processing_delay
    
    def __repr__(self):
        return f"<CaptionGenerationUserSettings User {self.user_id} Platform {self.platform_connection_id}>"

class SystemConfiguration(Base):
    """System-wide configuration settings with audit trail"""
    __tablename__ = 'system_configuration'
    __table_args__ = (
        Index('ix_system_config_key', 'key'),
        Index('ix_system_config_updated', 'updated_at'),
        Index('ix_system_config_updated_by', 'updated_by'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    data_type = Column(String(20), default='string')  # string, integer, float, boolean, json
    is_sensitive = Column(Boolean, default=False)  # For passwords, API keys, etc.
    category = Column(String(50))  # grouping: system, performance, security, etc.
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    updated_by_user = relationship("User")
    
    def get_typed_value(self):
        """Get the value converted to the appropriate type"""
        if not self.value:
            return None
            
        try:
            if self.data_type == 'integer':
                return int(self.value)
            elif self.data_type == 'float':
                return float(self.value)
            elif self.data_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.data_type == 'json':
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, json.JSONDecodeError):
            return self.value  # Return as string if conversion fails
    
    def set_typed_value(self, value):
        """Set the value with appropriate type conversion"""
        if value is None:
            self.value = None
        elif self.data_type == 'json':
            self.value = json.dumps(value)
        elif self.data_type == 'boolean':
            self.value = str(bool(value)).lower()
        else:
            self.value = str(value)
    
    def __repr__(self):
        return f"<SystemConfiguration {self.key}={self.value}>"

class JobAuditLog(Base):
    """Comprehensive audit logging of all job actions"""
    __tablename__ = 'job_audit_log'
    __table_args__ = (
        Index('ix_job_audit_task_id', 'task_id'),
        Index('ix_job_audit_user_id', 'user_id'),
        Index('ix_job_audit_admin_user_id', 'admin_user_id'),
        Index('ix_job_audit_action', 'action'),
        Index('ix_job_audit_timestamp', 'timestamp'),
        Index('ix_job_audit_task_action', 'task_id', 'action'),
        Index('ix_job_audit_user_timestamp', 'user_id', 'timestamp'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey('caption_generation_tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    admin_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(50), nullable=False)  # 'created', 'cancelled', 'completed', 'failed', 'restarted', etc.
    details = Column(Text)  # JSON with action details
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(255))  # For tracking user sessions
    
    # Additional context fields
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=True)
    previous_status = Column(String(50))  # Previous task status before action
    new_status = Column(String(50))  # New task status after action
    error_code = Column(String(50))  # Error code if applicable
    processing_time_ms = Column(Integer)  # Processing time in milliseconds
    
    # Relationships
    task = relationship("CaptionGenerationTask")
    user = relationship("User", foreign_keys=[user_id])
    admin_user = relationship("User", foreign_keys=[admin_user_id])
    platform_connection = relationship("PlatformConnection")
    
    @classmethod
    def log_action(cls, session, task_id, user_id, action, details=None, 
                   admin_user_id=None, ip_address=None, user_agent=None,
                   session_id=None, platform_connection_id=None,
                   previous_status=None, new_status=None, error_code=None,
                   processing_time_ms=None):
        """Create an audit log entry for a job action"""
        audit_entry = cls(
            task_id=task_id,
            user_id=user_id,
            admin_user_id=admin_user_id,
            action=action,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            platform_connection_id=platform_connection_id,
            previous_status=previous_status,
            new_status=new_status,
            error_code=error_code,
            processing_time_ms=processing_time_ms
        )
        session.add(audit_entry)
        return audit_entry
    
    def get_details_dict(self):
        """Get details as a dictionary"""
        if self.details:
            try:
                return json.loads(self.details)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def __repr__(self):
        return f"<JobAuditLog {self.action} - Task {self.task_id} - User {self.user_id}>"

class AlertConfiguration(Base):
    """Managing alert thresholds and notification settings"""
    __tablename__ = 'alert_configuration'
    __table_args__ = (
        Index('ix_alert_config_type', 'alert_type'),
        Index('ix_alert_config_enabled', 'enabled'),
        Index('ix_alert_config_severity', 'severity'),
        Index('ix_alert_config_created_by', 'created_by'),
        Index('ix_alert_config_updated', 'updated_at'),
        UniqueConstraint('alert_type', 'metric_name', name='uq_alert_type_metric'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    metric_name = Column(String(100), nullable=False)  # e.g., 'queue_length', 'error_rate', 'memory_usage'
    threshold_value = Column(Float, nullable=False)
    threshold_operator = Column(String(10), default='>')  # '>', '<', '>=', '<=', '==', '!='
    threshold_unit = Column(String(20))  # 'count', 'percent', 'mb', 'seconds', etc.
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    enabled = Column(Boolean, default=True)
    
    # Notification settings
    notification_channels = Column(Text)  # JSON array of channels: ['email', 'slack', 'webhook']
    notification_template = Column(Text)  # Custom notification message template
    cooldown_minutes = Column(Integer, default=60)  # Minimum time between alerts of same type
    escalation_minutes = Column(Integer, default=0)  # Time before escalating unacknowledged alerts
    
    # Metadata
    description = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    
    # Relationships
    created_by_user = relationship("User")
    
    def get_notification_channels(self):
        """Get notification channels as a list"""
        if self.notification_channels:
            try:
                return json.loads(self.notification_channels)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_notification_channels(self, channels):
        """Set notification channels from a list"""
        self.notification_channels = json.dumps(channels) if channels else None
    
    def should_trigger(self, current_value):
        """Check if alert should trigger based on threshold"""
        if not self.enabled:
            return False
            
        try:
            if self.threshold_operator == '>':
                return current_value > self.threshold_value
            elif self.threshold_operator == '<':
                return current_value < self.threshold_value
            elif self.threshold_operator == '>=':
                return current_value >= self.threshold_value
            elif self.threshold_operator == '<=':
                return current_value <= self.threshold_value
            elif self.threshold_operator == '==':
                return current_value == self.threshold_value
            elif self.threshold_operator == '!=':
                return current_value != self.threshold_value
            else:
                return False
        except (TypeError, ValueError):
            return False
    
    def is_in_cooldown(self):
        """Check if alert is in cooldown period"""
        if not self.last_triggered or self.cooldown_minutes <= 0:
            return False
        
        from datetime import timedelta
        cooldown_end = self.last_triggered + timedelta(minutes=self.cooldown_minutes)
        return datetime.utcnow() < cooldown_end
    
    def record_trigger(self, session):
        """Record that this alert was triggered"""
        self.last_triggered = datetime.utcnow()
        self.trigger_count += 1
        session.commit()
    
    def __repr__(self):
        return f"<AlertConfiguration {self.alert_type.value} - {self.metric_name} {self.threshold_operator} {self.threshold_value}>"

class SystemAlert(Base):
    """Active system alerts and their acknowledgment status"""
    __tablename__ = 'system_alerts'
    __table_args__ = (
        Index('ix_system_alert_type', 'alert_type'),
        Index('ix_system_alert_severity', 'severity'),
        Index('ix_system_alert_status', 'status'),
        Index('ix_system_alert_created', 'created_at'),
        Index('ix_system_alert_acknowledged', 'acknowledged_at'),
        Index('ix_system_alert_resolved', 'resolved_at'),
        Index('ix_system_alert_config', 'alert_configuration_id'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci',
            'mysql_row_format': 'DYNAMIC',
        }
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_configuration_id = Column(Integer, ForeignKey('alert_configuration.id'), nullable=False)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    status = Column(String(20), default='active')  # active, acknowledged, resolved, suppressed
    
    # Alert content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    metric_value = Column(Float)  # The value that triggered the alert
    context_data = Column(Text)  # JSON with additional context
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # User actions
    acknowledged_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    acknowledgment_note = Column(Text)
    resolution_note = Column(Text)
    
    # Notification tracking
    notifications_sent = Column(Text)  # JSON array of sent notifications
    last_notification_sent = Column(DateTime)
    notification_count = Column(Integer, default=0)
    
    # Relationships
    alert_configuration = relationship("AlertConfiguration")
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by])
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    
    def get_context_data(self):
        """Get context data as a dictionary"""
        if self.context_data:
            try:
                return json.loads(self.context_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_context_data(self, data):
        """Set context data from a dictionary"""
        self.context_data = json.dumps(data) if data else None
    
    def get_notifications_sent(self):
        """Get sent notifications as a list"""
        if self.notifications_sent:
            try:
                return json.loads(self.notifications_sent)
            except json.JSONDecodeError:
                return []
        return []
    
    def add_notification_sent(self, channel, timestamp=None):
        """Add a sent notification record"""
        notifications = self.get_notifications_sent()
        notifications.append({
            'channel': channel,
            'timestamp': (timestamp or datetime.utcnow()).isoformat()
        })
        self.notifications_sent = json.dumps(notifications)
        self.last_notification_sent = timestamp or datetime.utcnow()
        self.notification_count += 1
    
    def acknowledge(self, user_id, note=None):
        """Acknowledge the alert"""
        self.status = 'acknowledged'
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
        self.acknowledgment_note = note
    
    def resolve(self, user_id, note=None):
        """Resolve the alert"""
        self.status = 'resolved'
        self.resolved_by = user_id
        self.resolved_at = datetime.utcnow()
        self.resolution_note = note
    
    def is_active(self):
        """Check if alert is still active"""
        return self.status == 'active'
    
    def is_acknowledged(self):
        """Check if alert has been acknowledged"""
        return self.status in ['acknowledged', 'resolved']
    
    def __repr__(self):
        return f"<SystemAlert {self.alert_type.value} - {self.severity.value} - {self.status}>"