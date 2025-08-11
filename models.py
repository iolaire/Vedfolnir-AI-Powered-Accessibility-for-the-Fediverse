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

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(500), nullable=False, index=True)
    user_id = Column(String(200), nullable=False)
    post_url = Column(String(500), nullable=False)
    post_content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Platform identification
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=True)
    platform_type = Column(String(50))  # For backward compatibility
    instance_url = Column(String(500))  # For backward compatibility
    
    # Relationships
    images = relationship("Image", back_populates="post", cascade="all, delete-orphan")
    platform_connection = relationship("PlatformConnection")
    
    # Table constraints - make post_id unique per platform
    __table_args__ = (
        UniqueConstraint('post_id', 'platform_connection_id', name='uq_post_platform'),
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
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    image_url = Column(String(1000), nullable=False)
    local_path = Column(String(500), nullable=False)
    original_filename = Column(String(200))
    media_type = Column(String(100))
    image_post_id = Column(String(100))  # Pixelfed ID for updating descriptions
    attachment_index = Column(Integer, nullable=False)
    
    # Platform identification
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=True)
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
    
    # Table constraints - ensure image_post_id is unique per platform
    __table_args__ = (
        UniqueConstraint('image_post_id', 'platform_connection_id', name='uq_image_platform'),
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
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
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

class ProcessingRun(Base):
    __tablename__ = 'processing_runs'
    
    id = Column(Integer, primary_key=True)
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
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=True)
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
    
    # Table constraints - ensure batch_id is unique per platform if specified
    __table_args__ = (
        UniqueConstraint('batch_id', 'platform_connection_id', name='uq_batch_platform'),
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
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
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
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    active_platform_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, index=True)
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
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.QUEUED)
    settings_json = Column(Text)  # Serialized CaptionGenerationSettings
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    results_json = Column(Text)  # Serialized GenerationResults
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(200))
    
    # Relationships
    user = relationship("User")
    platform_connection = relationship("PlatformConnection")
    
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
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform_connection_id = Column(Integer, ForeignKey('platform_connections.id'), nullable=False)
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