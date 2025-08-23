# Technical Stack

## Copyright and License Headers

**IMPORTANT**: All source code files MUST include the copyright and license header at the very top. See `.kiro/steering/copyright-license.md` for complete requirements and examples.

### Required Header for New Files
When creating any new source code file (.py, .js, .html, .css, .sh, .sql), ALWAYS add the appropriate copyright header as the very first content using the correct comment syntax for that file type.

## Development Practices

### Test-Driven Development (TDD) - MANDATORY
**Requirement:** All code must be developed using strict Test-Driven Development practices.

#### TDD Cycle (Red-Green-Refactor)
1. **Red:** Write a failing test that describes the desired behavior
2. **Green:** Write the minimal code to make the test pass
3. **Refactor:** Improve code quality while keeping tests green

#### TDD Implementation Rules
- **No Production Code:** Write no production code without a failing test
- **Minimal Test Code:** Write only enough test code to demonstrate a failure
- **Minimal Production Code:** Write only enough production code to pass the failing test
- **Test First:** Always write tests before implementation code
- **Full Test Suite:** The complete test suite MUST be passing before marking any task as complete

## Core Technologies
- **Language**: Python 3.8+
- **Web Framework**: Flask 2.0+
- **Database**: MySQL/MariaDB with SQLAlchemy ORM
- **Session Management**: Redis sessions with database fallback (NOT Flask sessions)
- **AI Model**: Ollama with LLaVA model for image caption generation
- **HTTP Client**: httpx for async HTTP requests
- **Image Processing**: Pillow (PIL)
- **Security**: Enterprise-grade security with CSRF protection, input validation, and rate limiting
- **Performance Monitoring**: Built-in performance tracking and optimization
- **Multi-Platform Support**: ActivityPub platforms (Pixelfed, Mastodon)

## Session Management Architecture

**IMPORTANT**: This application uses **Redis** as the primary session storage backend with **Flask session cookies** for session ID management. This architecture provides high performance, scalability, and reliability.

**📖 [Complete Redis Session Management Guide →](.kiro/steering/redis-session-management.md)**

### Redis Session Implementation
- **Session Storage**: Redis stores all session data on the server
- **Session Identification**: Flask manages session cookies containing unique session IDs
- **Session Retrieval**: Session IDs are used to retrieve corresponding session data from Redis
- **Session Security**: HTTP-only, secure cookies with proper SameSite configuration
- **Session Persistence**: Redis provides fast, in-memory session storage with optional persistence
- **Cross-Tab Sync**: Real-time synchronization via Redis pub/sub mechanisms
- **Fallback Storage**: Database fallback for session audit trails and recovery
- **Session Manager**: RedisSessionManager handles all Redis operations

### Session Management Components
- **UserSession Model**: Database table for session backup and audit trail
- **RedisSessionManager**: Primary session management system using Redis
- **UnifiedSessionManager**: Fallback session management system using database
- **RequestSessionManager**: Request-scoped session handling for database operations
- **Session Decorators**: Authentication and platform context decorators
- **Session Middleware**: Automatic session validation and cleanup using Redis manager
- **Session Security**: Built-in fingerprinting, audit logging, and security validation

### Database Session Patterns

**IMPORTANT**: After the MySQL migration and Redis session manager implementation, database operations should use `db_manager` directly for optimal performance and compatibility.

#### Pattern 1: Web Routes with User Context (Recommended)
```python
@app.route('/some_route')
@login_required
def some_function():
    with db_manager.get_session() as session:
        # Database operations with proper session management
        result = session.query(Model).filter_by(user_id=current_user.id).all()
        return render_template('template.html', data=result)
```

#### Pattern 2: Service Layer Operations (Recommended)
```python
class SomeService:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_data(self):
        with self.db_manager.get_session() as session:
            return session.query(Model).all()
```

#### Pattern 3: Admin Routes with Error Handling
```python
@admin_bp.route('/admin_route')
@login_required
@require_admin
def admin_function():
    try:
        with db_manager.get_session() as session:
            result = session.query(Model).all()
            return render_template('admin_template.html', data=result)
    except Exception as e:
        logger.error(f"Admin operation failed: {e}")
        flash("Operation failed. Please try again.", "error")
        return redirect(url_for('admin.dashboard'))
```

#### Pattern 4: Batch Operations with Transaction Management
```python
def batch_operation(items):
    with db_manager.get_session() as session:
        try:
            for item in items:
                # Process each item
                session.add(process_item(item))
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Batch operation failed: {e}")
            return False
```

### Migration from Legacy Patterns

**Deprecated Pattern (No longer recommended):**
```python
# DON'T USE - Unified session manager for database operations
with unified_session_manager.get_db_session() as session:
    result = session.query(Model).all()
```

**Current Best Practice:**
```python
# USE - Direct db_manager usage with context manager
with db_manager.get_session() as session:
    result = session.query(Model).all()
```

### Benefits of Current Database Patterns
- **MySQL Optimization**: Optimized for MySQL connection pooling and performance
- **Error Handling**: Automatic rollback and cleanup with proper exception handling
- **Resource Management**: Efficient connection pool utilization
- **Security**: Built-in audit trails and validation
- **Performance**: Optimized for high-volume operations
- **Maintainability**: Consistent patterns across the application

### Redis Session Manager Migration

**Recent Update**: The application has been migrated from database-only sessions to Redis sessions with database fallback. This change affects how database operations are performed in service layers.

#### Key Changes:
- **Session Storage**: Primary storage moved from database to Redis
- **Database Operations**: Service layers now use `db_manager` directly instead of `unified_session_manager.get_db_session()`
- **Compatibility**: Fixed `'RedisSessionManager' object has no attribute 'get_db_session'` errors
- **Architecture**: Clear separation between session management (Redis) and database operations (db_manager)

#### Migration Impact:
- **UserService**: Updated to use `db_manager` directly for all database operations
- **Admin Routes**: Continue to work with Redis session management
- **Performance**: Improved session performance with Redis caching
- **Reliability**: Database fallback ensures session persistence

### Benefits of Unified Session Management
- **Consistent Error Handling**: Automatic rollback and cleanup
- **Session Context Awareness**: User and platform context integration
- **Security**: Built-in audit trails and validation
- **Performance**: Optimized connection pooling and resource management
- **Maintainability**: Single pattern for all database operations

### Key Session Features
- **Platform Context**: Sessions maintain current platform selection
- **Multi-Platform Support**: Users can switch between platforms within sessions
- **Automatic Cleanup**: Expired sessions automatically removed
- **Security**: Secure token generation and validation
- **Scalability**: Database sessions support multiple application instances

### Redis Configuration
```bash
# Redis Connection Settings
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional, leave empty for no auth
REDIS_SSL=false

# Redis Session Configuration
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200  # 2 hours
REDIS_SESSION_CLEANUP_INTERVAL=3600  # 1 hour

# Session Cookie Configuration (Flask)
SESSION_COOKIE_NAME=session
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SECURE=true  # Set to false for development over HTTP
SESSION_COOKIE_SAMESITE=Lax

# Database fallback settings
DB_SESSION_FALLBACK=true
DB_SESSION_SYNC=true
```

### Session Architecture Benefits
- **Performance**: Redis provides sub-millisecond session access times
- **Scalability**: Supports horizontal scaling across multiple application instances
- **Reliability**: Database fallback ensures session persistence during Redis outages
- **Security**: Session data stored server-side, only session ID in client cookie
- **Real-time**: Redis pub/sub enables instant cross-tab synchronization
- **Memory Efficiency**: Redis optimized memory usage with automatic expiration

## Key Dependencies
- **pymysql**: MySQL database connector for Python
- **requests**: HTTP client for synchronous requests
- **httpx**: Async HTTP client
- **Pillow**: Image processing and optimization
- **SQLAlchemy**: ORM for database operations
- **Flask**: Web interface and API
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous I/O
- **aiofiles**: Asynchronous file operations
- **redis**: Redis client for session management
- **cryptography**: Encryption for platform credentials
- **werkzeug**: WSGI utilities and security
- **flask-login**: User session management

## Environment Configuration
The application uses environment variables for configuration, loaded from a `.env` file:

### Database Configuration (MySQL)
- `DATABASE_URL`: MySQL connection string (e.g., `mysql+pymysql://user:password@localhost/vedfolnir?charset=utf8mb4`)
- `DB_TYPE`: Database type (always `mysql`)
- `DB_NAME`: MySQL database name
- `DB_USER`: MySQL username
- `DB_PASSWORD`: MySQL password
- `DB_HOST`: MySQL host (default: localhost)
- `DB_PORT`: MySQL port (default: 3306)
- `DB_POOL_SIZE`: Connection pool size (default: 20)
- `DB_MAX_OVERFLOW`: Maximum overflow connections (default: 30)

### Platform Configuration
- Platform connections are now managed through the web interface for security
- `PLATFORM_ENCRYPTION_KEY`: Key for encrypting stored platform credentials
- Supports multiple ActivityPub platforms (Pixelfed, Mastodon)

### Redis Session Configuration
- `REDIS_URL`: Redis connection string
- `REDIS_SESSION_PREFIX`: Session key prefix
- `REDIS_SESSION_TIMEOUT`: Session timeout in seconds
- `SESSION_COOKIE_HTTPONLY`: HTTP-only cookies (true)
- `SESSION_COOKIE_SECURE`: Secure cookies for HTTPS (true)

### Security Configuration
- `FLASK_SECRET_KEY`: Flask secret key for session security
- `SECURITY_CSRF_ENABLED`: Enable CSRF protection
- `SECURITY_RATE_LIMITING_ENABLED`: Enable rate limiting
- `SECURITY_INPUT_VALIDATION_ENABLED`: Enable input validation
- `SECURITY_HEADERS_ENABLED`: Enable security headers

### AI/ML Configuration
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: LLaVA model name (default: llava:7b)
- `OLLAMA_TIMEOUT`: Request timeout in seconds

### Processing Configuration
- `MAX_POSTS_PER_RUN`: Maximum number of posts to process per user
- `MAX_USERS_PER_RUN`: Maximum number of users to process in a batch
- `USER_PROCESSING_DELAY`: Delay in seconds between processing users
- `CAPTION_MAX_LENGTH`: Maximum caption length (default: 500)
- `CAPTION_OPTIMAL_MIN_LENGTH`: Minimum optimal length (default: 150)
- `CAPTION_OPTIMAL_MAX_LENGTH`: Maximum optimal length (default: 450)

### Logging and Monitoring
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)
- `HEALTH_CHECK_ENABLED`: Enable health checks
- `METRICS_ENABLED`: Enable metrics collection

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up MySQL database (see docs/mysql-installation-guide.md)
mysql -u root -p
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vedfolnir_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'localhost';
FLUSH PRIVILEGES;

# Set up environment and create admin user
python scripts/setup/generate_env_secrets.py

# Verify setup
python scripts/setup/verify_env_setup.py
python scripts/setup/verify_redis_session_setup.py
```

### Running the Bot
```bash
# Process a single user
python main.py --users username1

# Process multiple users
python main.py --users username1 username2 username3

# Process users from a file
python main.py --file users.txt

# Set custom log level
python main.py --users username1 --log-level DEBUG
```

### Web Interface
```bash
# Start the web server (non-blocking for testing)
python web_app.py & sleep 10

# Start the web server (blocking for production)
python web_app.py

# Stop the web server (if running in background)
ps aux | grep "python.*web_app.py" | grep -v grep  # Find the process ID
kill <process_id>  # Replace <process_id> with the actual PID

# Restart the web server
# Step 1: Find and stop the current process
ps aux | grep "python.*web_app.py" | grep -v grep
kill <process_id>

# Step 2: Wait a moment for cleanup
sleep 2

# Step 3: Start the server again (non-blocking)
python web_app.py & sleep 10
```

### Database Management
```bash
# Check database contents and user status
python -c "
from dotenv import load_dotenv
load_dotenv()
from config import Config
from database import DatabaseManager
from models import User
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    users = session.query(User).all()
    print(f'Found {len(users)} users in database')
    for user in users:
        print(f'  - {user.username} ({user.email}) - Role: {user.role.value}')
"

# Reset and cleanup options
python scripts/maintenance/reset_app.py --status          # Check application status
python scripts/maintenance/reset_app.py --cleanup        # Clean up old data
python scripts/maintenance/reset_app.py --reset-complete # Complete reset (nuclear option)

# MySQL migration (for existing SQLite users)
python scripts/mysql_migration/migrate_to_mysql.py --backup
python scripts/mysql_migration/verify_migration.py

# Admin user management
python scripts/setup/init_admin_user.py                  # Create/update admin user
python scripts/setup/update_admin_user.py               # Update admin credentials
```

## Recent Major Updates

### MySQL Migration (2025)
- **Complete migration from SQLite to MySQL/MariaDB**
- **Performance improvements**: Significantly faster queries and concurrent access
- **Enterprise features**: Connection pooling, advanced indexing, and optimization
- **Migration tools**: Comprehensive migration scripts with backup and verification
- **Backward compatibility**: Migration tools for existing SQLite users

### Security Enhancements (2025)
- **Enterprise-grade security**: 100% security score with comprehensive protection
- **CSRF Protection**: Complete protection against Cross-Site Request Forgery attacks
- **Input Validation**: Advanced sanitization against XSS and SQL injection
- **Rate Limiting**: Protection against brute force and abuse
- **Audit Logging**: Comprehensive security event logging
- **Encrypted Credentials**: Platform credentials encrypted with Fernet encryption

### Performance Optimization (2025)
- **Redis Session Management**: High-performance session storage with database fallback
- **Connection Pooling**: Optimized MySQL connection management
- **Performance Monitoring**: Built-in performance tracking and optimization
- **Health Checks**: Comprehensive system health monitoring
- **Metrics Collection**: Real-time performance metrics and alerting

### Multi-Platform Support (2025)
- **ActivityPub Platforms**: Support for Pixelfed, Mastodon, and other ActivityPub platforms
- **Platform Management**: Web-based platform connection management
- **Multi-Account Support**: Multiple platform accounts per user
- **Unified Interface**: Single interface for managing multiple platforms

## Caption Configuration

The maximum caption length has been changed from 255 to 500 characters and is now configurable:

```bash
# Environment variables for caption configuration
CAPTION_MAX_LENGTH=500                    # Maximum caption length (default: 500)
CAPTION_OPTIMAL_MIN_LENGTH=150            # Minimum optimal length (default: 150)  
CAPTION_OPTIMAL_MAX_LENGTH=450           # Maximum optimal length (default: 450)
```

This affects:
- Caption generation prompts
- Caption formatting and truncation
- Web interface character limits
- Quality assessment thresholds

## Enhanced Image Classification

The system now uses a hybrid approach combining computer vision with LLaVA model analysis:

```bash
# Enhanced classification settings
USE_ENHANCED_CLASSIFICATION=true
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
LLAVA_CLASSIFICATION_TEMPERATURE=0.1
```

**Classification Pipeline:**
1. **Computer Vision Analysis**: Colors, textures, composition, lighting
2. **Advanced Scene Analysis**: Rule of thirds, depth cues, color harmony
3. **LLaVA Model Analysis**: Scene understanding using vision-language model
4. **Hybrid Decision**: Combines CV confidence with LLaVA insights

**Benefits:**
- Reduces "general" classifications significantly
- More accurate category detection
- Better specialized prompts
- Improved caption quality
```

### Testing

**Testing Framework**: This project uses Python's built-in `unittest` framework. **Do not use pytest** - stick to unittest for consistency.

```bash
# Run a specific test file
python -m unittest tests.test_configuration_examples -v

# Run a specific test class
python -m unittest tests.test_session_management.TestSessionManagement -v

# Run a specific test method
python -m unittest tests.test_session_management.TestSessionManagement.test_create_user_session -v

# Run all tests (requires proper .env configuration)
python -m unittest discover tests

# Run tests with verbose output
python -m unittest discover -v tests

# Run configuration tests (always work, no .env required)
python -m unittest tests.test_configuration_examples tests.test_config_validation_script -v

# Run platform adapter tests
python -m unittest tests.test_platform_adapter_factory -v

# Run session management tests
python -m unittest tests.test_session_management -v

# Run session integration tests
python -m unittest tests.test_session_integration -v

# Use the test runner script (recommended)
python run_tests.py --suite safe --verbose    # Safe tests (no config required)
python run_tests.py --suite config --verbose  # Configuration tests only
python run_tests.py --suite all --verbose     # All tests (requires .env)
```

**Testing Guidelines:**
- Always use `unittest` framework, not pytest
- Test files should be named `test_*.py` and placed in the `tests/` directory
- Test classes should inherit from `unittest.TestCase`
- Use descriptive test method names starting with `test_`
- Include docstrings for test methods explaining what is being tested
- Use `setUp()` and `tearDown()` methods for test initialization and cleanup
- Mock external dependencies and database connections in tests

**Mock User Management:**
For tests involving user sessions, authentication, or platform connections, **always use the standardized mock user helpers**:

```python
# Import the helpers
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestUserFeature(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create mock user with platforms
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, username="test_user", role=UserRole.REVIEWER
        )
    
    def tearDown(self):
        # Always clean up mock users
        cleanup_test_user(self.user_helper)
```

**Standalone Test Scripts:**
```bash
# Create mock user for manual testing
python tests/scripts/create_mock_user.py --username test_reviewer --role reviewer

# Clean up mock users after testing
python tests/scripts/cleanup_mock_user.py
```

See `.kiro/steering/testing-guidelines.md` for complete mock user management documentation and `tests/test_helpers/README.md` for API reference.

**Session Testing:**
For session-related tests, always use database sessions:

```python
# Test database session functionality
from session_manager import SessionManager
from request_session_manager import RequestSessionManager

class TestDatabaseSessions(unittest.TestCase):
    def setUp(self):
        self.session_manager = SessionManager(self.db_manager)
        self.request_session_manager = RequestSessionManager(self.db_manager)
    
    def test_session_creation(self):
        # Test database session creation
        session = self.session_manager.create_session(user_id=1)
        self.assertIsNotNone(session.session_token)
        self.assertEqual(session.user_id, 1)
```

**Note:** Many tests require environment variables to be set. If you encounter configuration errors, either:
1. Set up your `.env` file with valid configuration
2. Run specific test suites that don't require full configuration (like configuration tests)
3. Use a test environment file: `cp .env.example.pixelfed .env.test` and export those variables
4. Use the test runner script: `python run_tests.py --suite safe` for tests that don't require configuration