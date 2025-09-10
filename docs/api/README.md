# Vedfolnir API Documentation

This directory contains comprehensive API documentation for all Vedfolnir modules, organized by functionality and purpose.

📋 **[Documentation Summary](DOCUMENTATION_SUMMARY.md)** - Complete overview of the 277 documented modules and documentation structure

## Documentation Structure

### Core Application Modules
- **[Core Modules API](core_modules.md)** - Main application components
  - Main Application (Vedfolnir class)
  - Web Application (Flask routes and forms)
  - Configuration Management
  - Database Models and Manager
  - ActivityPub Client
  - Ollama Caption Generator
  - Image Processor
  - Session Manager

### Utility and Service Modules
- **[Utility Modules API](utility_modules.md)** - Supporting services and utilities
  - Utilities (retry logic, statistics)
  - Platform Context Management
  - Progress Tracking System
  - Rate Limiting System

### Security System
- **[Security Modules API](security_modules.md)** - Comprehensive security framework
  - Security Utilities (sanitization, validation)
  - Security Middleware (headers, rate limiting, CSRF)
  - Session Security (fingerprinting, audit logging)

## Quick Reference

### Most Common APIs

#### Database Operations
```python
from app.core.database.core.database_manager import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)

# Get posts needing alt text
posts = db_manager.get_posts_without_alt_text('user123', limit=10)
```

#### Caption Generation
```python
from app.utils.processing.ollama_caption_generator import OllamaCaptionGenerator

generator = OllamaCaptionGenerator(config.ollama)
await generator.initialize()

caption, metadata = await generator.generate_caption('/path/to/image.jpg')
```

#### Platform Context
```python
from app.services.platform.core.platform_context import PlatformContextManager

context_manager = PlatformContextManager(session)
context = context_manager.set_context(user_id=123, platform_connection_id=456)
```

#### Security Utilities
```python
from app.core.security.core.security_utils import sanitize_for_log, sanitize_filename

# Safe logging
logger.info(f"User input: {sanitize_for_log(user_input)}")

# Safe file operations
safe_filename = sanitize_filename(uploaded_filename)
```

### Error Handling Patterns

All modules implement consistent error handling:

```python
try:
    result = await some_operation()
except SpecificModuleError as e:
    logger.error(f"Module-specific error: {e}")
    # Handle specific error
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle general error
```

### Testing Patterns

Use standardized mock user helpers for testing:

```python
import unittest
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user

class TestModule(unittest.TestCase):
    def setUp(self):
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, username="test_user"
        )
    
    def tearDown(self):
        cleanup_test_user(self.user_helper)
```

## Module Dependencies

### Core Dependencies
```
config.py → models.py → database.py → session_manager.py
                    ↓
            activitypub_client.py → platform_context.py
                    ↓
            ollama_caption_generator.py
                    ↓
            image_processor.py
                    ↓
            web_app.py (Flask application)
```

### Utility Dependencies
```
utils.py (retry logic) → rate_limiter.py → progress_tracker.py
                                      ↓
                              security modules
```

### Security Dependencies
```
security_utils.py → security_middleware.py → session_security.py
                                        ↓
                              Flask application integration
```

## Configuration Examples

### Environment Variables
```bash
# Core Configuration
DATABASE_URL=sqlite:///storage/database/vedfolnir.db
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b

# Security Configuration
FLASK_SECRET_KEY=your-secret-key-here
PLATFORM_ENCRYPTION_KEY=your-encryption-key-here
CSRF_ENABLED=true
RATE_LIMITING_ENABLED=true

# Caption Configuration
CAPTION_MAX_LENGTH=500
CAPTION_OPTIMAL_MIN_LENGTH=150
CAPTION_OPTIMAL_MAX_LENGTH=450
```

### Python Configuration
```python
from config import Config, RetryConfig, RateLimitConfig

# Load configuration
config = Config()

# Access nested configurations
retry_config = config.retry
rate_limit_config = config.rate_limit
ollama_config = config.ollama
```

## Performance Considerations

### Database Operations
- Use connection pooling (configured in DatabaseManager)
- Implement proper session management with context managers
- Use platform-aware filtering to reduce query scope

### API Calls
- Implement retry logic with exponential backoff
- Use rate limiting to prevent API abuse
- Cache responses where appropriate

### Security Operations
- Sanitize all user inputs
- Use secure session management
- Implement comprehensive audit logging

## Development Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints for all function signatures
- Include comprehensive docstrings
- Implement proper error handling

### Testing Requirements
- Maintain >80% test coverage
- Use mock user helpers for user-related tests
- Test both success and failure scenarios
- Include security-focused tests

### Documentation Standards
- Document all public APIs
- Include usage examples
- Specify parameter types and return values
- Document exceptions that may be raised

## Migration and Compatibility

### Database Migrations
Use the migration system for schema changes:
```python
from migrations.script import run_migration
run_migration('add_new_column.py')
```

### API Versioning
APIs maintain backward compatibility within major versions. Breaking changes are documented in migration guides.

### Configuration Changes
Environment variable changes are documented with migration paths and default values.

## Support and Troubleshooting

### Common Issues
1. **Database Connection Errors**: Check DATABASE_URL and file permissions
2. **Ollama Connection Errors**: Verify OLLAMA_URL and model availability
3. **Platform Authentication Errors**: Check encrypted credentials and API endpoints
4. **Security Validation Errors**: Review input sanitization and CSRF tokens

### Debug Mode
Enable debug logging for troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Monitoring
Use built-in monitoring for performance analysis:
```python
from app.services.platform.components.platform_health import PlatformHealthMonitor
monitor = PlatformHealthMonitor(config)
health_status = monitor.check_system_health()
```

---

For detailed implementation examples and advanced usage patterns, refer to the individual module documentation files and the source code in the project repository.