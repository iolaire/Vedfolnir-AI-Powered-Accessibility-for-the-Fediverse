# models

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/models.py`

## Classes

### UserRole

```python
class UserRole(Enum)
```

**Class Variables:**
- `ADMIN`
- `MODERATOR`
- `REVIEWER`
- `VIEWER`

### ProcessingStatus

```python
class ProcessingStatus(Enum)
```

**Class Variables:**
- `PENDING`
- `REVIEWED`
- `APPROVED`
- `REJECTED`
- `POSTED`
- `ERROR`

### TaskStatus

```python
class TaskStatus(Enum)
```

**Class Variables:**
- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

### Post

```python
class Post(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `post_id`
- `user_id`
- `post_url`
- `post_content`
- `created_at`
- `updated_at`
- `platform_connection_id`
- `platform_type`
- `instance_url`
- `images`
- `platform_connection`
- `__table_args__`

**Methods:**

#### validate_platform_consistency

```python
def validate_platform_consistency(self)
```

Validate that platform information is consistent

**Type:** Instance method

#### get_platform_info

```python
def get_platform_info(self)
```

Get platform information, preferring connection over compatibility fields

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### Image

```python
class Image(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `post_id`
- `image_url`
- `local_path`
- `original_filename`
- `media_type`
- `image_post_id`
- `attachment_index`
- `platform_connection_id`
- `platform_type`
- `instance_url`
- `original_caption`
- `generated_caption`
- `reviewed_caption`
- `final_caption`
- `image_category`
- `prompt_used`
- `status`
- `created_at`
- `updated_at`
- `reviewed_at`
- `posted_at`
- `original_post_date`
- `reviewer_notes`
- `processing_error`
- `caption_quality_score`
- `needs_special_review`
- `post`
- `platform_connection`
- `__table_args__`

**Methods:**

#### validate_platform_consistency

```python
def validate_platform_consistency(self)
```

Validate that platform information is consistent with post

**Type:** Instance method

#### get_platform_info

```python
def get_platform_info(self)
```

Get platform information, preferring connection over compatibility fields

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### User

```python
class User(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `username`
- `email`
- `password_hash`
- `role`
- `is_active`
- `created_at`
- `last_login`
- `platform_connections`
- `sessions`

**Properties:**
- `is_authenticated`
- `is_anonymous`

**Methods:**

#### set_password

```python
def set_password(self, password)
```

**Type:** Instance method

#### check_password

```python
def check_password(self, password)
```

**Type:** Instance method

#### has_permission

```python
def has_permission(self, required_role)
```

Check if user has the required role or higher

**Type:** Instance method

#### active_platforms

```python
def active_platforms(self)
```

Get active platforms for this user with session safety

**Decorators:**
- `@hybrid_property`

**Type:** Instance method

#### default_platform

```python
def default_platform(self)
```

Get the default platform for this user with session safety

**Decorators:**
- `@hybrid_property`

**Type:** Instance method

#### get_default_platform

```python
def get_default_platform(self)
```

Get user's default platform connection (legacy method)

**Type:** Instance method

#### get_active_platforms

```python
def get_active_platforms(self)
```

Get all active platform connections for user (legacy method)

**Type:** Instance method

#### get_platform_by_type

```python
def get_platform_by_type(self, platform_type)
```

Get platform connection by type

**Type:** Instance method

#### get_platform_by_name

```python
def get_platform_by_name(self, name)
```

Get platform connection by name

**Type:** Instance method

#### set_default_platform

```python
def set_default_platform(self, platform_connection_id)
```

Set a platform as the default, unsetting others

**Type:** Instance method

#### has_platform_access

```python
def has_platform_access(self, platform_type, instance_url)
```

Check if user has access to a specific platform instance

**Type:** Instance method

#### get_id

```python
def get_id(self)
```

Return the user ID as a string for Flask-Login

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### ProcessingRun

```python
class ProcessingRun(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `user_id`
- `batch_id`
- `started_at`
- `completed_at`
- `posts_processed`
- `images_processed`
- `captions_generated`
- `errors_count`
- `status`
- `platform_connection_id`
- `platform_type`
- `instance_url`
- `retry_attempts`
- `retry_successes`
- `retry_failures`
- `retry_total_time`
- `retry_stats_json`
- `platform_connection`
- `__table_args__`

**Methods:**

#### validate_platform_consistency

```python
def validate_platform_consistency(self)
```

Validate that platform information is consistent

**Type:** Instance method

#### get_platform_info

```python
def get_platform_info(self)
```

Get platform information, preferring connection over compatibility fields

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### PlatformConnection

```python
class PlatformConnection(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `user_id`
- `name`
- `platform_type`
- `instance_url`
- `username`
- `_access_token`
- `_client_key`
- `_client_secret`
- `is_active`
- `is_default`
- `created_at`
- `updated_at`
- `last_used`
- `user`
- `posts`
- `images`
- `processing_runs`
- `user_sessions`
- `__table_args__`

**Properties:**
- `access_token`
- `client_key`
- `client_secret`

**Methods:**

#### _get_encryption_key

```python
def _get_encryption_key(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

#### _get_cipher

```python
def _get_cipher(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

#### access_token

```python
def access_token(self, value)
```

**Decorators:**
- `@access_token.setter`

**Type:** Instance method

#### client_key

```python
def client_key(self, value)
```

**Decorators:**
- `@client_key.setter`

**Type:** Instance method

#### client_secret

```python
def client_secret(self, value)
```

**Decorators:**
- `@client_secret.setter`

**Type:** Instance method

#### to_activitypub_config

```python
def to_activitypub_config(self)
```

Convert to ActivityPubConfig for client usage (works with detached instances)

**Type:** Instance method

#### test_connection

```python
def test_connection(self)
```

Test the platform connection (works with detached instances)

**Type:** Instance method

#### to_dict

```python
def to_dict(self, include_sensitive)
```

Convert to dictionary for safe serialization without session dependency

**Type:** Instance method

#### safe_get_user

```python
def safe_get_user(self)
```

Safely get user object, handling detached instances

**Type:** Instance method

#### safe_get_posts_count

```python
def safe_get_posts_count(self)
```

Safely get posts count, handling detached instances

**Type:** Instance method

#### safe_get_images_count

```python
def safe_get_images_count(self)
```

Safely get images count, handling detached instances

**Type:** Instance method

#### is_accessible

```python
def is_accessible(self)
```

Check if platform connection is accessible (works with detached instances)

**Type:** Instance method

#### get_display_name

```python
def get_display_name(self)
```

Get display name for UI (works with detached instances)

**Type:** Instance method

#### matches_platform

```python
def matches_platform(self, platform_type, instance_url)
```

Check if this connection matches given platform details (works with detached instances)

**Type:** Instance method

#### can_be_default

```python
def can_be_default(self)
```

Check if this connection can be set as default (works with detached instances)

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### UserSession

```python
class UserSession(Base)
```

User session tracking for platform-aware session management

**Class Variables:**
- `__tablename__`
- `id`
- `session_id`
- `user_id`
- `active_platform_id`
- `created_at`
- `updated_at`
- `user_agent`
- `ip_address`
- `user`
- `active_platform`

**Methods:**

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### CaptionGenerationSettings

```python
class CaptionGenerationSettings
```

**Decorators:**
- `@dataclass`

**Methods:**

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

**Type:** Instance method

#### from_dict

```python
def from_dict(cls, data: Dict[str, Any]) -> 'CaptionGenerationSettings'
```

**Decorators:**
- `@classmethod`

**Type:** Class method

#### to_json

```python
def to_json(self) -> str
```

**Type:** Instance method

#### from_json

```python
def from_json(cls, json_str: str) -> 'CaptionGenerationSettings'
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### GenerationResults

```python
class GenerationResults
```

**Decorators:**
- `@dataclass`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

**Type:** Instance method

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

**Type:** Instance method

#### from_dict

```python
def from_dict(cls, data: Dict[str, Any]) -> 'GenerationResults'
```

**Decorators:**
- `@classmethod`

**Type:** Class method

#### to_json

```python
def to_json(self) -> str
```

**Type:** Instance method

#### from_json

```python
def from_json(cls, json_str: str) -> 'GenerationResults'
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### CaptionGenerationTask

```python
class CaptionGenerationTask(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `user_id`
- `platform_connection_id`
- `status`
- `settings_json`
- `created_at`
- `started_at`
- `completed_at`
- `error_message`
- `results_json`
- `progress_percent`
- `current_step`
- `user`
- `platform_connection`

**Properties:**
- `settings`
- `results`

**Methods:**

#### settings

```python
def settings(self, value: CaptionGenerationSettings)
```

**Decorators:**
- `@settings.setter`

**Type:** Instance method

#### results

```python
def results(self, value: GenerationResults)
```

**Decorators:**
- `@results.setter`

**Type:** Instance method

#### is_active

```python
def is_active(self) -> bool
```

Check if task is in an active state

**Type:** Instance method

#### is_completed

```python
def is_completed(self) -> bool
```

Check if task is in a completed state

**Type:** Instance method

#### can_be_cancelled

```python
def can_be_cancelled(self) -> bool
```

Check if task can be cancelled

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

### CaptionGenerationUserSettings

```python
class CaptionGenerationUserSettings(Base)
```

**Class Variables:**
- `__tablename__`
- `id`
- `user_id`
- `platform_connection_id`
- `max_posts_per_run`
- `max_caption_length`
- `optimal_min_length`
- `optimal_max_length`
- `reprocess_existing`
- `processing_delay`
- `created_at`
- `updated_at`
- `user`
- `platform_connection`
- `__table_args__`

**Methods:**

#### to_settings_dataclass

```python
def to_settings_dataclass(self) -> CaptionGenerationSettings
```

Convert to CaptionGenerationSettings dataclass

**Type:** Instance method

#### update_from_dataclass

```python
def update_from_dataclass(self, settings: CaptionGenerationSettings)
```

Update from CaptionGenerationSettings dataclass

**Type:** Instance method

#### __repr__

```python
def __repr__(self)
```

**Type:** Instance method

