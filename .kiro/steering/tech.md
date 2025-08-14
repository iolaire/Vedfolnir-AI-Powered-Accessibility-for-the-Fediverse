# Technical Stack

## Copyright and License Headers

**IMPORTANT**: All source code files MUST include the copyright and license header at the very top. See `.kiro/steering/copyright-license.md` for complete requirements and examples.

### Required Header for New Files
When creating any new source code file (.py, .js, .html, .css, .sh, .sql), ALWAYS add the appropriate copyright header as the very first content using the correct comment syntax for that file type.

## Core Technologies
- **Language**: Python 3
- **Web Framework**: Flask
- **Database**: SQLAlchemy with SQLite backend
- **AI Model**: Ollama with LLaVA model for image caption generation
- **HTTP Client**: httpx for async HTTP requests
- **Image Processing**: Pillow (PIL)

## Key Dependencies
- **requests**: HTTP client for synchronous requests
- **httpx**: Async HTTP client
- **Pillow**: Image processing and optimization
- **SQLAlchemy**: ORM for database operations
- **Flask**: Web interface and API
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous I/O
- **aiofiles**: Asynchronous file operations

## Environment Configuration
The application uses environment variables for configuration, loaded from a `.env` file:
- `ACTIVITYPUB_INSTANCE_URL`: URL of the Pixelfed instance
- `ACTIVITYPUB_USERNAME`: User name of the Pixelfed user 
- `ACTIVITYPUB_ACCESS_TOKEN`: Access token for the Pixelfed API
- `MAX_POSTS_PER_RUN`: Maximum number of posts to process per user
- `MAX_USERS_PER_RUN`: Maximum number of users to process in a batch
- `USER_PROCESSING_DELAY`: Delay in seconds between processing users
- `LOG_LEVEL`: Logging level

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run database migrations
python add_batch_id_column.py
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
# Start the web server
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

# Step 3: Start the server again
python web_app.py
```

### Database Management
```bash
# Check database contents
python check_db.py

# Empty the database (caution!)
python empty_db.py

# Data cleanup options
python data_cleanup.py --help                    # Show all cleanup options
python data_cleanup.py --all --dry-run          # Full cleanup (dry run)
python data_cleanup.py --all                    # Full cleanup (database, storage, logs)
python data_cleanup.py --storage --dry-run      # Clean storage/images only (dry run)
python data_cleanup.py --logs --dry-run         # Clean logs/ directory only (dry run)

# Migrate existing log files to logs directory
python migrate_logs.py

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

**Note:** Many tests require environment variables to be set. If you encounter configuration errors, either:
1. Set up your `.env` file with valid configuration
2. Run specific test suites that don't require full configuration (like configuration tests)
3. Use a test environment file: `cp .env.example.pixelfed .env.test` and export those variables
4. Use the test runner script: `python run_tests.py --suite safe` for tests that don't require configuration