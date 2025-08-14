# Database Schema Documentation

This document describes the database schema for the Vedfolnir application.

## Overview

Vedfolnir uses SQLite as its primary database with SQLAlchemy ORM for data modeling. The schema is designed to support multi-platform ActivityPub integration with comprehensive session management and performance optimization.

## Core Tables

### users
User account management table.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique user identifier |
| username | VARCHAR(64) | UNIQUE, NOT NULL, INDEX | User's login name |
| email | VARCHAR(120) | UNIQUE, NOT NULL, INDEX | User's email address |
| password_hash | VARCHAR(256) | NOT NULL | Hashed password |
| role | ENUM | DEFAULT 'viewer' | User role (admin, moderator, reviewer, viewer) |
| is_active | BOOLEAN | DEFAULT TRUE | Account active status |
| created_at | DATETIME | DEFAULT NOW | Account creation timestamp |
| last_login | DATETIME | NULL | Last login timestamp |

### platform_connections
Platform connection management for ActivityPub instances.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique connection identifier |
| user_id | INTEGER | FK(users.id), NOT NULL | Owner user ID |
| name | VARCHAR(100) | NOT NULL | Friendly connection name |
| platform_type | VARCHAR(50) | NOT NULL | Platform type (pixelfed, mastodon) |
| instance_url | VARCHAR(500) | NOT NULL | Platform instance URL |
| username | VARCHAR(200) | NULL | Platform username |
| access_token | TEXT | NOT NULL, ENCRYPTED | API access token |
| client_key | TEXT | ENCRYPTED | OAuth client key |
| client_secret | TEXT | ENCRYPTED | OAuth client secret |
| is_active | BOOLEAN | DEFAULT TRUE | Connection active status |
| is_default | BOOLEAN | DEFAULT FALSE | Default connection flag |
| created_at | DATETIME | DEFAULT NOW | Connection creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |
| last_used | DATETIME | NULL | Last usage timestamp |

**Indexes:**
- `ix_platform_user_active` (user_id, is_active)
- `ix_platform_type_active` (platform_type, is_active)
- `ix_platform_instance_type` (instance_url, platform_type)

**Constraints:**
- `uq_user_platform_name` (user_id, name)
- `uq_user_instance_username` (user_id, instance_url, username)

### user_sessions
Enhanced session management with performance optimization.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique session identifier |
| session_id | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Flask session ID |
| user_id | INTEGER | FK(users.id), NOT NULL, INDEX | Session owner user ID |
| active_platform_id | INTEGER | FK(platform_connections.id) | Currently active platform |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | Session creation timestamp |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW, INDEX | Last update timestamp |
| last_activity | DATETIME | NOT NULL, DEFAULT NOW, INDEX | Last activity timestamp |
| expires_at | DATETIME | NOT NULL, INDEX | Session expiration timestamp |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE, INDEX | Session active status |
| session_fingerprint | TEXT | NULL | Browser fingerprint |
| user_agent | TEXT | NULL | User agent string |
| ip_address | VARCHAR(45) | NULL | Client IP address |

**Performance Indexes:**
- `idx_user_sessions_last_activity` (last_activity, is_active)
- `idx_user_sessions_expires_at` (expires_at, is_active)
- `idx_user_sessions_user_active` (user_id, is_active, last_activity)

### posts
Social media post tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique post identifier |
| post_id | VARCHAR(500) | NOT NULL, INDEX | Platform-specific post ID |
| user_id | VARCHAR(200) | NOT NULL | Post author user ID |
| post_url | VARCHAR(500) | NOT NULL | Post URL |
| post_content | TEXT | NULL | Post content |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |
| platform_connection_id | INTEGER | FK(platform_connections.id) | Associated platform connection |
| platform_type | VARCHAR(50) | NULL | Platform type (legacy) |
| instance_url | VARCHAR(500) | NULL | Instance URL (legacy) |

**Constraints:**
- `uq_post_platform` (post_id, platform_connection_id)

### images
Image attachment management with caption processing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique image identifier |
| post_id | INTEGER | FK(posts.id), NOT NULL | Parent post ID |
| image_url | VARCHAR(1000) | NOT NULL | Original image URL |
| local_path | VARCHAR(500) | NOT NULL | Local storage path |
| original_filename | VARCHAR(200) | NULL | Original filename |
| media_type | VARCHAR(100) | NULL | MIME type |
| image_post_id | VARCHAR(100) | NULL | Platform-specific image ID |
| attachment_index | INTEGER | NOT NULL | Image order in post |
| platform_connection_id | INTEGER | FK(platform_connections.id) | Associated platform connection |
| platform_type | VARCHAR(50) | NULL | Platform type (legacy) |
| instance_url | VARCHAR(500) | NULL | Instance URL (legacy) |
| original_caption | TEXT | NULL | Original alt text |
| generated_caption | TEXT | NULL | AI-generated caption |
| reviewed_caption | TEXT | NULL | Human-reviewed caption |
| final_caption | TEXT | NULL | Final approved caption |
| image_category | VARCHAR(50) | NULL | Classified image category |
| prompt_used | TEXT | NULL | Generation prompt used |
| status | ENUM | DEFAULT 'pending' | Processing status |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |
| reviewed_at | DATETIME | NULL | Review completion timestamp |
| posted_at | DATETIME | NULL | Post update timestamp |
| original_post_date | DATETIME | NULL | Original post date |
| reviewer_notes | TEXT | NULL | Human reviewer notes |
| processing_error | TEXT | NULL | Error details |
| caption_quality_score | INTEGER | NULL | Quality score (1-100) |
| needs_special_review | BOOLEAN | DEFAULT FALSE | Special review flag |

**Constraints:**
- `uq_image_platform` (image_post_id, platform_connection_id)

### processing_runs
Batch processing tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique run identifier |
| user_id | VARCHAR(200) | NOT NULL | Processing user ID |
| batch_id | VARCHAR(200) | NULL | Batch identifier |
| started_at | DATETIME | DEFAULT NOW | Processing start timestamp |
| completed_at | DATETIME | NULL | Processing completion timestamp |
| posts_processed | INTEGER | DEFAULT 0 | Number of posts processed |
| images_processed | INTEGER | DEFAULT 0 | Number of images processed |
| captions_generated | INTEGER | DEFAULT 0 | Number of captions generated |
| errors_count | INTEGER | DEFAULT 0 | Number of errors encountered |
| status | VARCHAR(50) | DEFAULT 'running' | Processing status |
| platform_connection_id | INTEGER | FK(platform_connections.id) | Associated platform connection |
| platform_type | VARCHAR(50) | NULL | Platform type (legacy) |
| instance_url | VARCHAR(500) | NULL | Instance URL (legacy) |
| retry_attempts | INTEGER | DEFAULT 0 | Number of retry attempts |
| retry_successes | INTEGER | DEFAULT 0 | Successful retries |
| retry_failures | INTEGER | DEFAULT 0 | Failed retries |
| retry_total_time | INTEGER | DEFAULT 0 | Total retry time (seconds) |
| retry_stats_json | TEXT | NULL | Detailed retry statistics |

**Constraints:**
- `uq_batch_platform` (batch_id, platform_connection_id)

### caption_generation_tasks
Asynchronous caption generation task tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID task identifier |
| user_id | INTEGER | FK(users.id), NOT NULL | Task owner user ID |
| platform_connection_id | INTEGER | FK(platform_connections.id), NOT NULL | Target platform |
| status | ENUM | DEFAULT 'queued' | Task status |
| settings_json | TEXT | NULL | Serialized task settings |
| created_at | DATETIME | DEFAULT NOW | Task creation timestamp |
| started_at | DATETIME | NULL | Task start timestamp |
| completed_at | DATETIME | NULL | Task completion timestamp |
| error_message | TEXT | NULL | Error details |
| results_json | TEXT | NULL | Serialized task results |
| progress_percent | INTEGER | DEFAULT 0 | Completion percentage |
| current_step | VARCHAR(200) | NULL | Current processing step |

### caption_generation_user_settings
User-specific caption generation preferences.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique settings identifier |
| user_id | INTEGER | FK(users.id), NOT NULL | Settings owner user ID |
| platform_connection_id | INTEGER | FK(platform_connections.id), NOT NULL | Target platform |
| max_posts_per_run | INTEGER | DEFAULT 50 | Maximum posts per batch |
| max_caption_length | INTEGER | DEFAULT 500 | Maximum caption length |
| optimal_min_length | INTEGER | DEFAULT 80 | Optimal minimum length |
| optimal_max_length | INTEGER | DEFAULT 200 | Optimal maximum length |
| reprocess_existing | BOOLEAN | DEFAULT FALSE | Reprocess existing captions |
| processing_delay | FLOAT | DEFAULT 1.0 | Delay between requests |
| created_at | DATETIME | DEFAULT NOW | Settings creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |

**Constraints:**
- `uq_user_platform_settings` (user_id, platform_connection_id)

## Enums

### UserRole
- `ADMIN`: Full system access
- `MODERATOR`: Content moderation access
- `REVIEWER`: Caption review access
- `VIEWER`: Read-only access

### ProcessingStatus
- `PENDING`: Awaiting processing
- `REVIEWED`: Human reviewed
- `APPROVED`: Approved for posting
- `REJECTED`: Rejected by reviewer
- `POSTED`: Successfully posted
- `ERROR`: Processing error

### TaskStatus
- `QUEUED`: Waiting to start
- `RUNNING`: Currently processing
- `COMPLETED`: Successfully completed
- `FAILED`: Failed with error
- `CANCELLED`: Cancelled by user

## Security Features

### Encryption
- Platform credentials (access_token, client_key, client_secret) are encrypted using Fernet symmetric encryption
- Encryption key is stored in environment variable `PLATFORM_ENCRYPTION_KEY`

### Data Isolation
- Platform-aware queries ensure users only see their own data
- Context managers enforce platform boundaries
- Validation prevents cross-platform data access

### Session Security
- Session fingerprinting for security
- Automatic session expiration
- Activity tracking for security monitoring
- Performance-optimized session queries

## Performance Optimizations

### Indexes
- Strategic indexes on frequently queried columns
- Composite indexes for complex queries
- Session performance indexes for fast lookups

### Query Optimization
- Platform-aware filtering at database level
- Lazy loading strategies for relationships
- Connection pooling and session management

### Caching
- Session data caching
- Platform connection caching
- Query result caching where appropriate

## Migration Support

The schema supports both Alembic migrations and custom migration scripts:
- Standard Alembic migrations for model changes
- Custom migration script for session performance optimization
- Backward compatibility with legacy platform fields

## Maintenance

### Cleanup Operations
- Automatic expired session cleanup
- Old processing run cleanup
- Orphaned record cleanup

### Monitoring
- Query performance logging
- Connection health monitoring
- Error tracking and reporting