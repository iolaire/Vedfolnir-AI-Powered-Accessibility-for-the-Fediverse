# Project Structure

## Copyright and License Compliance

**CRITICAL**: All source code files in this project MUST include copyright and license headers. When creating or modifying any source code file, ensure it includes the proper header at the top using the correct comment syntax. See `.kiro/steering/copyright-license.md` for detailed requirements.


## Core Components

### Main Application
- `main.py`: Entry point for the bot, handles command-line arguments and orchestrates the processing flow
- `config.py`: Configuration management using environment variables with MySQL support
- `models.py`: SQLAlchemy data models for MySQL database entities
- `database.py`: MySQL database connection and operations management with connection pooling

### ActivityPub Integration
- `activitypub_client.py`: Client for interacting with Pixelfed/Mastodon/ActivityPub API
- `post_service.py`: Service for handling post-related operations
- `platform_adapter_factory.py`: Factory for creating platform-specific adapters

### Image Processing
- `image_processor.py`: Handles image downloading, storage, and optimization
- `ollama_caption_generator.py`: Generates image captions using Ollama with LLaVA model
- `caption_quality_assessment.py`: Quality assessment and validation for generated captions

### Session Management
- `redis_session_manager.py`: Primary session manager using Redis backend
- `session_config.py`: Session configuration and settings management
- `session_cookie_manager.py`: Flask session cookie handling and security
- `session_performance_optimizer.py`: Session performance monitoring and optimization
- `session_state_api.py`: Session state management API
- `session_aware_user.py`: User context integration with sessions
- `session_error_handlers.py`: Session-specific error handling
- `redis_session_middleware.py`: Redis session middleware for Flask
- `unified_session_manager.py`: Legacy session manager (database fallback)

### Security System
- `security/core/`: Core security functionality (CSRF, rate limiting, encryption)
- `security/validation/`: Input validation and sanitization
- `security/monitoring/`: Security event logging and monitoring
- `security_decorators.py`: Security decorators for routes and functions

### Web Interface
- `web_app.py`: Main Flask web application for reviewing and managing captions
- `routes/`: Route handlers for different application areas
  - `user_management_routes.py`: User authentication and management
  - `admin_routes.py`: Administrative functionality
  - `platform_routes.py`: Platform connection management
- `admin/`: Administrative functionality module
  - `routes/`: Admin route handlers (user management, system health, cleanup, monitoring)
  - `services/`: Admin business logic services
  - `templates/`: Admin-specific HTML templates
  - `static/`: Admin-specific static assets
  - `forms/`: Admin form definitions
- `templates/`: Main application HTML templates
- `static/`: Main application static assets (CSS, JavaScript)

### Services Layer
- `services/`: Business logic services
  - `user_service.py`: User management and authentication services
  - `platform_service.py`: Platform connection management
  - `email_service.py`: Email notifications and communications

### Utilities and Scripts
- `utils.py`: Utility functions and helpers
- `scripts/setup/`: Environment and database setup scripts
- `scripts/maintenance/`: Application maintenance and cleanup scripts
- `scripts/mysql_migration/`: MySQL migration tools for SQLite users
- `scripts/testing/`: Testing utilities and comprehensive test runners

## Directory Structure
- `.devcontainer/`: Development container configuration
- `.kiro/`: Kiro specifications and steering files
- `static/`: Main application static assets
  - `css/`: Main application stylesheets
  - `js/`: Main application JavaScript files
- `admin/static/`: Admin-specific static assets
  - `css/`: Admin stylesheets
  - `js/`: Admin JavaScript files
- `storage/`: Data storage
  - `backups/mysql/`: MySQL database backups
  - `images/`: Downloaded and processed images
  - `temp/`: Temporary files for processing
- `templates/`: Main application HTML templates
- `admin/templates/`: Admin-specific HTML templates
- `tests/`: Test files and test utilities
  - All test files should be placed here with naming convention `test_*.py`
- `scripts/`: Utility and setup scripts
  - `setup/`: Environment and database setup scripts
  - `maintenance/`: Application maintenance and cleanup scripts
  - `mysql_migration/`: MySQL migration tools
  - `testing/`: Testing utilities and runners
- `docs/`: Comprehensive documentation
  - `api/`: API documentation
  - `security/`: Security guides and documentation
  - `summary/`: Summary reports and audits
- `security/`: Security modules and components
  - `core/`: Core security functionality
  - `validation/`: Input validation and sanitization
  - `monitoring/`: Security monitoring and logging
- `routes/`: Flask route handlers
- `services/`: Business logic services
- `__pycache__/`: Python bytecode cache (not tracked in version control)

## Data Flow
1. **User Authentication**: Users log in through the web interface with secure password validation
2. **Session Creation**: Session data is stored in Redis using unique session IDs with database fallback
3. **Platform Management**: Users configure platform connections (Pixelfed, Mastodon) through the web interface
4. **Post Retrieval**: The bot retrieves posts from ActivityPub platforms via authenticated API calls
5. **Image Processing**: Images without alt text are identified, downloaded, and processed
6. **Caption Generation**: The Ollama LLaVA model generates captions with quality assessment
7. **Data Persistence**: Generated captions and metadata are stored in MySQL database
8. **Session Management**: User sessions are maintained in Redis with automatic cleanup
9. **Human Review**: Reviewers approve, edit, or reject captions via the web interface
10. **Caption Publishing**: Approved captions are posted back to platforms via API
11. **Security Monitoring**: All actions are logged and monitored for security events
12. **Performance Tracking**: System performance and health metrics are continuously monitored

## Development Patterns
- **Configuration**: Environment variables with dotenv and secure credential management
- **Database Access**: SQLAlchemy ORM with MySQL connection pooling and session management
- **Error Handling**: Comprehensive logging, graceful error recovery, and security event monitoring
- **API Interaction**: Async HTTP requests with retry mechanisms and rate limiting
- **Web Interface**: Flask with Jinja2 templates, CSRF protection, and input validation
- **Security**: Enterprise-grade security with encryption, audit logging, and threat monitoring
- **Testing**: Comprehensive test suite with unittest framework and mock user management
- **Performance**: Built-in performance monitoring, optimization, and health checks
- **Multi-Platform**: Support for multiple ActivityPub platforms with unified management interface