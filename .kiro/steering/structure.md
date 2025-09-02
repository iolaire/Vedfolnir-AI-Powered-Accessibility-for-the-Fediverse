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
  - `backups/`: Application and database backup files
    - `mysql/`: MySQL database backups
  - `images/`: Downloaded and processed images
  - `temp/`: Temporary files for processing
- `templates/`: Main application HTML templates
- `admin/templates/`: Admin-specific HTML templates
- `tests/`: Test files and test utilities
  - All test files should be placed here with naming convention `test_*.py`
  - `admin/`: Admin functionality tests
  - `frontend/`: Frontend and UI tests
  - `integration/`: Integration tests
  - `migration/`: Migration tests
  - `monitoring/`: Monitoring and health tests
  - `performance/`: Performance tests
  - `reports/`: Test results and reports
  - `user/`: User functionality tests
  - `web_caption_generation/`: Caption generation tests
  - `websocket/`: WebSocket tests
- `scripts/`: Utility and setup scripts
  - `setup/`: Environment and database setup scripts
  - `maintenance/`: Application maintenance and cleanup scripts
  - `mysql_migration/`: MySQL migration tools
  - `testing/`: Testing utilities and runners
  - `debug/`: Debug and troubleshooting scripts
  - `examples/`: Demo and example scripts
  - `utilities/`: General utility scripts
- `docs/`: Comprehensive documentation
  - `api/`: API documentation
  - `security/`: Security guides and documentation
  - `summary/`: Summary reports and audits
  - `admin/`: Admin functionality documentation
  - `deployment/`: Deployment and setup documentation
  - `frontend/`: Frontend and UI documentation
  - `implementation/`: Implementation summaries
  - `integration/`: Integration documentation
  - `maintenance/`: Maintenance and cleanup documentation
  - `migration/`: Migration documentation
  - `monitoring/`: Monitoring and health documentation
  - `performance/`: Performance optimization documentation
  - `services/`: Service layer documentation
  - `storage/`: Storage system documentation
  - `testing/`: Testing documentation and results
  - `web-caption-generation/`: Caption generation documentation
  - `websocket/`: WebSocket system documentation
- `logs/`: Application log files
  - Runtime logs and debugging information
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

## File Organization Rules

### Documentation Files (`docs/`)
**RULE**: All documentation files must be organized by category in appropriate subdirectories:

- **Admin Documentation** → `docs/admin/`: Admin functionality, security, user management
- **Deployment Documentation** → `docs/deployment/`: Setup, configuration, deployment guides
- **Frontend Documentation** → `docs/frontend/`: UI components, user interface documentation
- **Implementation Documentation** → `docs/implementation/`: Implementation summaries and technical details
- **Integration Documentation** → `docs/integration/`: System integration and workflow documentation
- **Maintenance Documentation** → `docs/maintenance/`: System maintenance, cleanup, recovery procedures
- **Migration Documentation** → `docs/migration/`: Migration guides and summaries
- **Monitoring Documentation** → `docs/monitoring/`: System monitoring, health checks, alerting
- **Performance Documentation** → `docs/performance/`: Performance optimization and benchmarking
- **Security Documentation** → `docs/security/`: Security implementation, testing, and compliance
- **Service Documentation** → `docs/services/`: Service layer and business logic documentation
- **Storage Documentation** → `docs/storage/`: Storage systems, backup, and data management
- **Testing Documentation** → `docs/testing/`: Test results, procedures, and validation
- **WebSocket Documentation** → `docs/websocket/`: WebSocket implementation and configuration
- **Caption Generation Documentation** → `docs/web-caption-generation/`: Caption generation system documentation

### Test Files (`tests/`)
**RULE**: All test files must be organized by functionality in appropriate subdirectories:

- **Admin Tests** → `tests/admin/`: Admin functionality, security, user management tests
- **Frontend Tests** → `tests/frontend/`: UI, dashboard, and user interface tests
- **Integration Tests** → `tests/integration/`: Cross-system integration and workflow tests
- **Migration Tests** → `tests/migration/`: Migration and upgrade tests
- **Monitoring Tests** → `tests/monitoring/`: System monitoring and health check tests
- **Performance Tests** → `tests/performance/`: Performance benchmarking and load tests
- **User Tests** → `tests/user/`: User functionality and profile tests
- **WebSocket Tests** → `tests/websocket/`: WebSocket connection and communication tests
- **Caption Generation Tests** → `tests/web_caption_generation/`: Caption generation system tests
- **Test Reports** → `tests/reports/`: Test results, coverage reports, and analysis data

### Script Files (`scripts/`)
**RULE**: All script files must be organized by purpose in appropriate subdirectories:

- **Debug Scripts** → `scripts/debug/`: Debugging, troubleshooting, and diagnostic scripts
- **Example Scripts** → `scripts/examples/`: Demo scripts, examples, and proof-of-concept code
- **Utility Scripts** → `scripts/utilities/`: General utilities, validation, and helper scripts
- **Setup Scripts** → `scripts/setup/`: Environment setup and initialization scripts
- **Maintenance Scripts** → `scripts/maintenance/`: System maintenance and cleanup scripts
- **Testing Scripts** → `scripts/testing/`: Test runners and testing utilities
- **Migration Scripts** → `scripts/mysql_migration/`: Database migration tools

### Backup Files (`storage/backups/`)
**RULE**: All backup files must be stored in the storage/backups directory:

- **Application Backups** → `storage/backups/`: Code backups, configuration backups
- **Database Backups** → `storage/backups/mysql/`: MySQL database backups

### Log Files (`logs/`)
**RULE**: All log files must be stored in the logs directory:

- **Application Logs** → `logs/`: Runtime logs, error logs, debug logs
- **Component Logs** → `logs/`: Service-specific and component-specific logs

### File Naming Conventions
- **Test Files**: `test_*.py` - All test files must start with `test_`
- **Debug Scripts**: `debug_*.py` - All debug scripts must start with `debug_`
- **Demo Scripts**: `demo_*.py` - All demo/example scripts must start with `demo_`
- **Validation Scripts**: `validate_*.py` or `verify_*.py` - Validation utilities
- **Documentation**: `*_SUMMARY.md`, `*_IMPLEMENTATION.md` - Implementation and summary docs

### Git History Preservation
**RULE**: When moving files, always use `git mv` to preserve version control history:

```bash
# CORRECT - Preserves git history
git mv old_file.py new_location/old_file.py

# WRONG - Loses git history
mv old_file.py new_location/old_file.py
git add new_location/old_file.py
```

### Root Directory Policy
**RULE**: Keep the project root directory clean and organized:

- **Core Application Files**: Main application components remain in root
- **Configuration Files**: `.env`, `requirements.txt`, `docker-compose.yml` remain in root
- **Project Files**: `README.md`, `LICENSE`, `.gitignore` remain in root
- **Everything Else**: Must be organized into appropriate subdirectories

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
- **File Organization**: Strict adherence to directory structure and file organization rules