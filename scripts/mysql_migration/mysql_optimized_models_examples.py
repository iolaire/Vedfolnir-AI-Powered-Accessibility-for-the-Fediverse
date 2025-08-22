
# Enhanced MySQL-specific table options for optimal performance
mysql_table_args = {
    'mysql_engine': 'InnoDB',
    'mysql_charset': 'utf8mb4',
    'mysql_collate': 'utf8mb4_unicode_ci',
    'mysql_row_format': 'DYNAMIC',  # Better for variable-length columns
}

# MySQL-specific index options for better performance
mysql_index_args = {
    'mysql_length': {'text_columns': 255},  # Limit index length for TEXT columns
    'mysql_using': 'BTREE',  # Explicit B-tree indexes
}


# Enhanced User model with MySQL optimizations
class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        # Composite indexes for common query patterns
        Index('ix_user_email_active', 'email', 'is_active'),
        Index('ix_user_username_active', 'username', 'is_active'),
        Index('ix_user_role_active', 'role', 'is_active'),
        Index('ix_user_created_login', 'created_at', 'last_login'),
        Index('ix_user_verification_status', 'email_verified', 'is_active'),
        
        # MySQL-specific table options
        mysql_table_args
    )
    
    # Optimized column definitions for MySQL
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)  # Optimal length for indexes
    email = Column(String(255), unique=True, nullable=False)    # Standard email length
    password_hash = Column(String(255), nullable=False)         # Standard bcrypt length
    
    # Use ENUM for better performance and data integrity
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Optimized timestamp columns
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Enhanced Post model with MySQL optimizations
class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (
        # Composite indexes for efficient queries
        Index('ix_post_platform_created', 'platform_connection_id', 'created_at'),
        Index('ix_post_user_platform', 'user_id', 'platform_connection_id'),
        Index('ix_post_status_created', 'created_at'),  # For chronological queries
        Index('ix_post_platform_type_url', 'platform_type', 'instance_url'),
        
        # Unique constraints with proper naming
        UniqueConstraint('post_id', 'platform_connection_id', name='uq_post_platform'),
        
        # MySQL-specific optimizations
        mysql_table_args
    )
    
    # Optimized column definitions
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(255), nullable=False)  # Reduced from 500 for better indexing
    user_id = Column(String(255), nullable=False)  # Consistent with platform limits
    post_url = Column(Text, nullable=False)        # URLs can be very long
    post_content = Column(Text, nullable=True)     # Content can be large
    
    # Optimized timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Foreign key with proper constraints
    platform_connection_id = Column(
        Integer, 
        ForeignKey('platform_connections.id', ondelete='CASCADE'), 
        nullable=False
    )


# Enhanced Image model with MySQL optimizations
class Image(Base):
    __tablename__ = 'images'
    __table_args__ = (
        # Composite indexes for efficient queries
        Index('ix_image_post_attachment', 'post_id', 'attachment_index'),
        Index('ix_image_platform_status', 'platform_connection_id', 'status'),
        Index('ix_image_status_created', 'status', 'created_at'),
        Index('ix_image_category_status', 'image_category', 'status'),
        Index('ix_image_quality_score', 'caption_quality_score'),
        
        # Unique constraints
        UniqueConstraint('image_post_id', 'platform_connection_id', name='uq_image_platform'),
        UniqueConstraint('post_id', 'attachment_index', name='uq_post_attachment'),
        
        # MySQL-specific optimizations
        mysql_table_args
    )
    
    # Optimized column definitions
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    
    # URLs and paths - use TEXT for potentially long values
    image_url = Column(Text, nullable=False)
    local_path = Column(String(500), nullable=False)  # File paths have OS limits
    
    # Metadata with appropriate lengths
    original_filename = Column(String(255), nullable=True)  # Standard filename limit
    media_type = Column(String(100), nullable=True)         # MIME type length
    image_post_id = Column(String(255), nullable=True)      # Platform-specific ID
    
    # Optimized integer columns
    attachment_index = Column(Integer, nullable=False, default=0)
    caption_quality_score = Column(Integer, nullable=True)  # 0-100 score
    
    # Status enum for data integrity
    status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    
    # Optimized text columns
    original_caption = Column(Text, nullable=True)
    generated_caption = Column(Text, nullable=True)
    reviewed_caption = Column(Text, nullable=True)
    final_caption = Column(Text, nullable=True)
    
    # Classification and processing
    image_category = Column(String(100), nullable=True)  # Reasonable category length
    prompt_used = Column(Text, nullable=True)            # Prompts can be long
    
    # Optimized timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)


# Enhanced PlatformConnection model with MySQL optimizations
class PlatformConnection(Base):
    __tablename__ = 'platform_connections'
    __table_args__ = (
        # Composite indexes for efficient platform queries
        Index('ix_platform_user_active', 'user_id', 'is_active'),
        Index('ix_platform_type_instance', 'platform_type', 'instance_url'),
        Index('ix_platform_user_default', 'user_id', 'is_default'),
        Index('ix_platform_last_used', 'last_used'),
        
        # Unique constraints for data integrity
        UniqueConstraint('user_id', 'name', name='uq_user_platform_name'),
        UniqueConstraint('user_id', 'instance_url', 'username', name='uq_user_instance_username'),
        
        # MySQL-specific optimizations
        mysql_table_args
    )
    
    # Optimized column definitions
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Platform identification with appropriate lengths
    name = Column(String(100), nullable=False)           # User-friendly name
    platform_type = Column(String(50), nullable=False)  # 'pixelfed', 'mastodon', etc.
    instance_url = Column(String(500), nullable=False)  # Full URL
    username = Column(String(255), nullable=True)       # Platform username
    
    # Encrypted credentials - use TEXT for encrypted data
    _access_token = Column('access_token', Text, nullable=False)
    _client_key = Column('client_key', Text, nullable=True)
    _client_secret = Column('client_secret', Text, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Optimized timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used = Column(DateTime, nullable=True)
