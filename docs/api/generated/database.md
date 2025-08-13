# database

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/database.py`

## Classes

### DatabaseOperationError

```python
class DatabaseOperationError(Exception)
```

Raised when database operations fail due to invalid conditions

### PlatformValidationError

```python
class PlatformValidationError(Exception)
```

Raised when platform-related validation fails

### DatabaseManager

```python
class DatabaseManager
```

Handles platform-aware database operations

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### _setup_query_logging

```python
def _setup_query_logging(self)
```

Set up query logging for performance analysis

**Type:** Instance method

#### create_tables

```python
def create_tables(self)
```

Create database tables

**Type:** Instance method

#### _create_performance_indexes

```python
def _create_performance_indexes(self)
```

Create additional indexes for better performance

**Type:** Instance method

#### get_session

```python
def get_session(self)
```

Get database session

**Type:** Instance method

#### close_session

```python
def close_session(self)
```

Close database session

**Type:** Instance method

#### get_context_manager

```python
def get_context_manager(self) -> PlatformContextManager
```

Get or create platform context manager

**Type:** Instance method

#### set_platform_context

```python
def set_platform_context(self, user_id: int, platform_connection_id: Optional[int], session_id: Optional[str])
```

Set platform context for database operations

**Type:** Instance method

#### clear_platform_context

```python
def clear_platform_context(self)
```

Clear platform context

**Type:** Instance method

#### require_platform_context

```python
def require_platform_context(self)
```

Require platform context for operations

**Type:** Instance method

#### _apply_platform_filter

```python
def _apply_platform_filter(self, query, model_class)
```

Apply platform filtering to a query

**Type:** Instance method

#### _inject_platform_data

```python
def _inject_platform_data(self, data: Dict[str, Any]) -> Dict[str, Any]
```

Inject platform data into a dictionary

**Type:** Instance method

#### get_or_create_post

```python
def get_or_create_post(self, post_id: str, user_id: str, post_url: str, post_content: str)
```

Get existing post or create new one with platform validation.

Args:
    post_id: Platform-specific post ID
    user_id: User ID who owns the post
    post_url: URL of the post
    post_content: Optional post content
    
Returns:
    Post object
    
Raises:
    PlatformValidationError: If validation fails
    DatabaseOperationError: If database operation fails

**Type:** Instance method

#### save_image

```python
def save_image(self, post_id: int, image_url: str, local_path: str, attachment_index: int, media_type: str, original_filename: str, image_post_id: str, original_post_date)
```

Save image record to database and return the image ID (platform-aware)

**Type:** Instance method

#### update_image_caption

```python
def update_image_caption(self, image_id: int, generated_caption: str, quality_metrics: dict, prompt_used: str)
```

Update image with generated caption and quality metrics with validation.

Args:
    image_id: ID of the image to update
    generated_caption: Generated caption text
    quality_metrics: Optional quality metrics dictionary
    prompt_used: Optional prompt that was used for generation
    
Returns:
    True if update successful, False otherwise
    
Raises:
    PlatformValidationError: If validation fails
    DatabaseOperationError: If database operation fails

**Type:** Instance method

#### get_pending_images

```python
def get_pending_images(self, limit: int)
```

Get images pending review (platform-aware)

**Type:** Instance method

#### get_approved_images

```python
def get_approved_images(self, limit: int)
```

Get images approved for posting (platform-aware)

**Type:** Instance method

#### review_image

```python
def review_image(self, image_id: int, reviewed_caption: str, status: ProcessingStatus, reviewer_notes: str)
```

Update image with review results

**Type:** Instance method

#### mark_image_posted

```python
def mark_image_posted(self, image_id: int)
```

Mark image as posted

**Type:** Instance method

#### is_image_processed

```python
def is_image_processed(self, image_url: str) -> bool
```

Check if image has been processed before (platform-aware)

**Type:** Instance method

#### get_processing_stats

```python
def get_processing_stats(self, platform_aware: bool)
```

Get processing statistics (optionally platform-aware)

**Type:** Instance method

#### get_platform_processing_stats

```python
def get_platform_processing_stats(self, platform_connection_id: int)
```

Get processing statistics for a specific platform

**Type:** Instance method

#### get_platform_statistics

```python
def get_platform_statistics(self, user_id: Optional[int]) -> Dict[str, Any]
```

Get statistics for all platforms (for a specific user or globally)

**Type:** Instance method

#### get_user_platform_summary

```python
def get_user_platform_summary(self, user_id: int) -> Dict[str, Any]
```

Get summary of user's platform connections and their activity

**Type:** Instance method

#### get_user_by_username

```python
def get_user_by_username(self, username)
```

Get user by username

**Type:** Instance method

#### get_user_by_email

```python
def get_user_by_email(self, email)
```

Get user by email

**Type:** Instance method

#### create_user

```python
def create_user(self, username, email, password, role)
```

Create a new user

**Type:** Instance method

#### update_user

```python
def update_user(self, user_id, username, email, password, role, is_active)
```

Update an existing user

**Type:** Instance method

#### delete_user

```python
def delete_user(self, user_id)
```

Delete a user

**Type:** Instance method

#### get_all_users

```python
def get_all_users(self)
```

Get all users

**Type:** Instance method

#### create_platform_connection

```python
def create_platform_connection(self, user_id: int, name: str, platform_type: str, instance_url: str, username: str, access_token: str, client_key: Optional[str], client_secret: Optional[str], is_default: bool) -> Optional[PlatformConnection]
```

Create a new platform connection with comprehensive validation.

Args:
    user_id: ID of the user creating the connection
    name: Friendly name for the connection
    platform_type: Type of platform ('pixelfed', 'mastodon')
    instance_url: URL of the platform instance
    username: Username on the platform
    access_token: API access token
    client_key: Optional client key (for Mastodon)
    client_secret: Optional client secret (for Mastodon)
    is_default: Whether this should be the default platform
    
Returns:
    Created PlatformConnection object or None if creation failed
    
Raises:
    PlatformValidationError: If validation fails
    DatabaseOperationError: If database operation fails

**Type:** Instance method

#### get_platform_connection

```python
def get_platform_connection(self, connection_id: int) -> Optional[PlatformConnection]
```

Get platform connection by ID

**Type:** Instance method

#### get_user_platform_connections

```python
def get_user_platform_connections(self, user_id: int, active_only: bool) -> List[PlatformConnection]
```

Get all platform connections for a user

**Type:** Instance method

#### update_platform_connection

```python
def update_platform_connection(self, connection_id: int, user_id: Optional[int], **kwargs) -> bool
```

Update platform connection with validation.

Args:
    connection_id: ID of the platform connection to update
    user_id: Optional user ID for additional validation
    **kwargs: Fields to update
    
Returns:
    True if update successful, False otherwise
    
Raises:
    PlatformValidationError: If validation fails
    DatabaseOperationError: If database operation fails

**Type:** Instance method

#### delete_platform_connection

```python
def delete_platform_connection(self, connection_id: int, user_id: Optional[int], force: bool) -> bool
```

Delete platform connection with validation and data protection.

Args:
    connection_id: ID of the platform connection to delete
    user_id: Optional user ID for additional validation
    force: If True, delete even if there's associated data
    
Returns:
    True if deletion successful, False otherwise
    
Raises:
    PlatformValidationError: If validation fails
    DatabaseOperationError: If database operation fails

**Type:** Instance method

#### set_default_platform

```python
def set_default_platform(self, user_id: int, connection_id: int) -> bool
```

Set a platform connection as default for a user

**Type:** Instance method

#### test_platform_connection

```python
def test_platform_connection(self, connection_id: int, user_id: Optional[int]) -> Tuple[bool, str]
```

Test a platform connection with validation.

Args:
    connection_id: ID of the platform connection to test
    user_id: Optional user ID for ownership validation
    
Returns:
    Tuple of (success, message)
    
Raises:
    PlatformValidationError: If validation fails

**Type:** Instance method

#### switch_platform_context

```python
def switch_platform_context(self, user_id: int, platform_connection_id: int, session_id: Optional[str]) -> bool
```

Switch platform context for a user with validation.

Args:
    user_id: ID of the user
    platform_connection_id: ID of the platform connection to switch to
    session_id: Optional session ID for tracking
    
Returns:
    True if switch successful, False otherwise
    
Raises:
    PlatformValidationError: If validation fails
    DatabaseOperationError: If database operation fails

**Type:** Instance method

#### validate_data_isolation

```python
def validate_data_isolation(self, user_id: int) -> Dict[str, Any]
```

Validate that data isolation is working correctly for a user's platforms

**Type:** Instance method

