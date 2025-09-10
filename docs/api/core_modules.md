# Core Modules API Documentation

This document provides comprehensive API documentation for Vedfolnir's core modules, including function signatures, parameters, return types, and usage examples.

## Table of Contents

- [Main Application (main.py)](#main-application)
- [Web Application (web_app.py)](#web-application)
- [Configuration (config.py)](#configuration)
- [Database Models (models.py)](#database-models)
- [Database Manager (database.py)](#database-manager)
- [ActivityPub Client (activitypub_client.py)](#activitypub-client)
- [Ollama Caption Generator (ollama_caption_generator.py)](#ollama-caption-generator)
- [Image Processor (image_processor.py)](#image-processor)
- [Session Manager (session_manager.py)](#session-manager)

---

## Main Application

### Class: Vedfolnir

The main orchestrator class for the alt text generation process.

#### Constructor

```python
def __init__(self, config: Config, reprocess_all: bool = False)
```

**Parameters:**
- `config` (Config): Application configuration object
- `reprocess_all` (bool, optional): Whether to reprocess existing images. Defaults to False.

**Attributes:**
- `config` (Config): Application configuration
- `db` (DatabaseManager): Database manager instance
- `current_run` (ProcessingRun): Current processing run
- `reprocess_all` (bool): Reprocessing flag
- `stats` (dict): Processing statistics

#### Methods

##### run_multi_user

```python
async def run_multi_user(self, user_ids: List[str], skip_ollama: bool = False) -> Dict[str, Any]
```

Process multiple users in a single run.

**Parameters:**
- `user_ids` (List[str]): List of user IDs to process
- `skip_ollama` (bool, optional): Skip Ollama caption generation. Defaults to False.

**Returns:**
- `Dict[str, Any]`: Processing results and statistics

**Example:**
```python
from main import Vedfolnir
from config import Config

config = Config()
bot = Vedfolnir(config)
results = await bot.run_multi_user(['user1', 'user2'], skip_ollama=False)
print(f"Processed {results['posts_processed']} posts")
```

---

## Web Application

### Flask Application Setup

The web application provides a comprehensive interface for managing captions and platform connections.

#### Key Components

##### Security Configuration

```python
# CSRF Protection
csrf = CSRFProtect(app)

# Session Configuration
app.config.update({
    'SESSION_TYPE': 'filesystem',
    'SESSION_PERMANENT': False,
    'SESSION_USE_SIGNER': True,
    'SESSION_KEY_PREFIX': 'vedfolnir:',
    'SESSION_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax'
})
```

##### Authentication System

```python
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
```

#### Main Routes

##### Index Route

```python
@app.route('/')
@login_required
def index() -> str
```

Main dashboard displaying system status and recent activity.

**Returns:**
- `str`: Rendered HTML template

##### Login Route

```python
@app.route('/login', methods=['GET', 'POST'])
def login() -> Union[str, Response]
```

User authentication endpoint.

**Returns:**
- `str`: Login form (GET)
- `Response`: Redirect to dashboard or error (POST)

##### Caption Generation Route

```python
@app.route('/caption_generation')
@login_required
@require_platform_context
def caption_generation() -> str
```

Caption generation interface with real-time progress tracking.

**Returns:**
- `str`: Rendered caption generation template

---

## Configuration

### Class: Config

Main configuration class that loads settings from environment variables.

#### Nested Configuration Classes

##### RetryConfig

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_server_error: bool = True
    retry_on_rate_limit: bool = True
    retry_specific_errors: list = None
```

**Class Methods:**

```python
@classmethod
def from_env(cls) -> RetryConfig
```

Create RetryConfig from environment variables.

**Returns:**
- `RetryConfig`: Configuration instance with values from environment

##### RateLimitConfig

```python
@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    burst_limit: int = 10
    window_size: int = 60
    enabled: bool = True
```

#### Usage Example

```python
from config import Config, RetryConfig

# Load configuration
config = Config()

# Access nested configurations
retry_config = config.retry
rate_limit_config = config.rate_limit

# Create from environment
retry_from_env = RetryConfig.from_env()
```

---

## Database Models

### Base Models

All models inherit from SQLAlchemy's declarative base:

```python
Base = declarative_base()
```

### Enums

#### UserRole

```python
class UserRole(Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
```

#### ProcessingStatus

```python
class ProcessingStatus(Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    ERROR = "error"
```

#### TaskStatus

```python
class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Core Models

#### User Model

```python
class User(Base):
    __tablename__ = 'users'
    
    # Primary fields
    id: int
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime
    
    # Relationships
    platform_connections: List[PlatformConnection]
    user_sessions: List[UserSession]
```

**Key Methods:**

```python
def set_password(self, password: str) -> None
```

Set user password with secure hashing.

```python
def check_password(self, password: str) -> bool
```

Verify password against stored hash.

```python
def get_default_platform(self) -> Optional[PlatformConnection]
```

Get user's default platform connection.

#### PlatformConnection Model

```python
class PlatformConnection(Base):
    __tablename__ = 'platform_connections'
    
    # Primary fields
    id: int
    user_id: int
    name: str
    platform_type: str
    instance_url: str
    username: str
    access_token_encrypted: str
    is_default: bool
    is_active: bool
    created_at: datetime
    last_used: datetime
    
    # Relationships
    user: User
```

**Key Methods:**

```python
def encrypt_access_token(self, token: str) -> None
```

Encrypt and store access token.

```python
def decrypt_access_token(self) -> str
```

Decrypt and return access token.

```python
def to_activitypub_config(self) -> ActivityPubConfig
```

Convert to ActivityPub configuration object.

#### Image Model

```python
class Image(Base):
    __tablename__ = 'images'
    
    # Primary fields
    id: int
    post_id: int
    image_url: str
    local_path: str
    media_id: str
    alt_text: str
    generated_caption: str
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    post: Post
```

---

## Database Manager

### Class: DatabaseManager

Handles platform-aware database operations with connection pooling and error handling.

#### Constructor

```python
def __init__(self, config: Config)
```

**Parameters:**
- `config` (Config): Application configuration

#### Core Methods

##### get_session

```python
def get_session(self) -> Session
```

Get a database session with proper configuration.

**Returns:**
- `Session`: SQLAlchemy session object

##### create_tables

```python
def create_tables(self) -> None
```

Create all database tables if they don't exist.

##### get_posts_without_alt_text

```python
def get_posts_without_alt_text(self, user_id: str, limit: int = None) -> List[Post]
```

Get posts that need alt text generation.

**Parameters:**
- `user_id` (str): User identifier
- `limit` (int, optional): Maximum number of posts to return

**Returns:**
- `List[Post]`: List of posts without alt text

##### save_image

```python
def save_image(self, image_data: Dict[str, Any]) -> Image
```

Save image data to database.

**Parameters:**
- `image_data` (Dict[str, Any]): Image information dictionary

**Returns:**
- `Image`: Saved image object

#### Usage Example

```python
from app.core.database.core.database_manager import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)

# Create tables
db_manager.create_tables()

# Get session
with db_manager.get_session() as session:
    posts = db_manager.get_posts_without_alt_text('user123', limit=10)
    print(f"Found {len(posts)} posts needing alt text")
```

---

## ActivityPub Client

### Class: ActivityPubClient

Platform-agnostic client for interacting with ActivityPub servers.

#### Constructor

```python
def __init__(self, config, platform_connection=None)
```

**Parameters:**
- `config`: ActivityPubConfig object or PlatformConnection object
- `platform_connection` (PlatformConnection, optional): Platform connection for platform-aware operations

#### Core Methods

##### initialize

```python
async def initialize(self) -> None
```

Initialize the client and validate connection.

##### get_user_posts

```python
async def get_user_posts(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]
```

Retrieve posts for a specific user.

**Parameters:**
- `user_id` (str): User identifier
- `limit` (int, optional): Maximum number of posts. Defaults to 20.

**Returns:**
- `List[Dict[str, Any]]`: List of post objects

##### update_media_description

```python
async def update_media_description(self, media_id: str, description: str) -> bool
```

Update media description (alt text) for a media item.

**Parameters:**
- `media_id` (str): Media identifier
- `description` (str): New description text

**Returns:**
- `bool`: True if successful, False otherwise

#### Usage Example

```python
from app.services.activitypub.components.activitypub_client import ActivityPubClient
from models import PlatformConnection

# Initialize with platform connection
platform_conn = get_user_platform_connection(user_id)
client = ActivityPubClient(None, platform_connection=platform_conn)

await client.initialize()

# Get user posts
posts = await client.get_user_posts('user123', limit=10)

# Update media description
success = await client.update_media_description('media456', 'A beautiful sunset')
```

---

## Ollama Caption Generator

### Class: OllamaCaptionGenerator

Generate image captions using Ollama with LLaVA model.

#### Constructor

```python
def __init__(self, config)
```

**Parameters:**
- `config`: Ollama configuration object

#### Core Methods

##### initialize

```python
async def initialize(self) -> None
```

Initialize connection to Ollama and validate model availability.

##### generate_caption

```python
async def generate_caption(self, image_path: str, image_category: str = None, 
                         custom_prompt: str = None) -> Tuple[str, Dict[str, Any]]
```

Generate caption for an image.

**Parameters:**
- `image_path` (str): Path to image file
- `image_category` (str, optional): Image category for specialized prompts
- `custom_prompt` (str, optional): Custom prompt override

**Returns:**
- `Tuple[str, Dict[str, Any]]`: Generated caption and metadata

##### get_stats

```python
def get_stats(self) -> Dict[str, Any]
```

Get generation statistics.

**Returns:**
- `Dict[str, Any]`: Statistics including retry and fallback counts

#### Usage Example

```python
from ollama_caption_generator import OllamaCaptionGenerator
from config import Config

config = Config()
generator = OllamaCaptionGenerator(config.ollama)

await generator.initialize()

# Generate caption
caption, metadata = await generator.generate_caption(
    '/path/to/image.jpg',
    image_category='nature',
    custom_prompt='Describe this landscape photo'
)

print(f"Generated caption: {caption}")
print(f"Confidence: {metadata['confidence']}")
```

---

## Image Processor

### Class: ImageProcessor

Handle image downloading and processing with persistent storage.

#### Constructor

```python
def __init__(self, config: Config)
```

**Parameters:**
- `config` (Config): Application configuration

#### Core Methods

##### download_image

```python
async def download_image(self, url: str, media_type: str = None) -> Tuple[str, bool]
```

Download image from URL with caching.

**Parameters:**
- `url` (str): Image URL
- `media_type` (str, optional): MIME type of image

**Returns:**
- `Tuple[str, bool]`: Local file path and whether it was newly downloaded

##### validate_image

```python
def validate_image(self, image_path: str) -> Tuple[bool, str]
```

Validate an image file.

**Parameters:**
- `image_path` (str): Path to image file

**Returns:**
- `Tuple[bool, str]`: Validation result and error message if invalid

##### optimize_image

```python
def optimize_image(self, image_path: str, max_size: Tuple[int, int] = (1024, 1024)) -> str
```

Optimize image for processing.

**Parameters:**
- `image_path` (str): Path to image file
- `max_size` (Tuple[int, int], optional): Maximum dimensions. Defaults to (1024, 1024).

**Returns:**
- `str`: Path to optimized image

#### Usage Example

```python
from image_processor import ImageProcessor
from config import Config

config = Config()

async with ImageProcessor(config) as processor:
    # Download image
    local_path, is_new = await processor.download_image(
        'https://example.com/image.jpg',
        media_type='image/jpeg'
    )
    
    # Validate image
    is_valid, error = processor.validate_image(local_path)
    if is_valid:
        # Optimize for processing
        optimized_path = processor.optimize_image(local_path)
        print(f"Image ready at: {optimized_path}")
```

---

## Session Manager

### Class: SessionManager

Manages platform-aware user sessions with security and monitoring.

#### Constructor

```python
def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig] = None)
```

**Parameters:**
- `db_manager` (DatabaseManager): Database manager instance
- `config` (SessionConfig, optional): Session configuration

#### Core Methods

##### get_db_session

```python
@contextmanager
def get_db_session(self) -> Session
```

Context manager for database sessions with error handling.

**Returns:**
- `Session`: SQLAlchemy session object

##### create_user_session

```python
def create_user_session(self, user_id: int, platform_id: int = None, 
                       session_data: Dict[str, Any] = None) -> UserSession
```

Create a new user session.

**Parameters:**
- `user_id` (int): User identifier
- `platform_id` (int, optional): Platform connection ID
- `session_data` (Dict[str, Any], optional): Additional session data

**Returns:**
- `UserSession`: Created session object

##### cleanup_expired_sessions

```python
def cleanup_expired_sessions(self) -> int
```

Clean up expired sessions.

**Returns:**
- `int`: Number of sessions cleaned up

#### Usage Example

```python
from app.core.session.core.session_manager import SessionManager
from app.core.database.core.database_manager import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
session_manager = SessionManager(db_manager)

# Create user session
with session_manager.get_db_session() as db_session:
    user_session = session_manager.create_user_session(
        user_id=123,
        platform_id=456,
        session_data={'theme': 'dark', 'language': 'en'}
    )
    
    print(f"Created session: {user_session.session_id}")

# Cleanup expired sessions
cleaned = session_manager.cleanup_expired_sessions()
print(f"Cleaned up {cleaned} expired sessions")
```

---

## Error Handling

All modules implement comprehensive error handling with custom exception classes:

### Common Exceptions

- `DatabaseOperationError`: Database operation failures
- `PlatformValidationError`: Platform validation failures
- `SessionDatabaseError`: Session database errors
- `SessionError`: General session errors
- `PlatformAdapterError`: Platform adapter errors

### Error Recovery

Most operations include automatic retry mechanisms with exponential backoff and jitter for resilience against transient failures.

---

## Testing

All modules include comprehensive test coverage. See the testing guidelines for mock user management and test execution patterns.

### Example Test Structure

```python
import unittest
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from config import Config
from app.core.database.core.database_manager import DatabaseManager

class TestCoreModule(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager,
            username="test_user",
            role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        cleanup_test_user(self.user_helper)
    
    def test_functionality(self):
        # Test implementation
        pass
```

---

This documentation provides a comprehensive reference for Vedfolnir's core modules. For implementation details and advanced usage patterns, refer to the source code and additional documentation in the `docs/` directory.