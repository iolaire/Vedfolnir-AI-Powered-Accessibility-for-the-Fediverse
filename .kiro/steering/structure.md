# Project Structure

## Copyright and License Compliance

**CRITICAL**: All source code files in this project MUST include copyright and license headers. When creating or modifying any source code file, ensure it includes the proper header at the top using the correct comment syntax. See `.kiro/steering/copyright-license.md` for detailed requirements.


## Core Components

### Main Application
- `main.py`: Entry point for the bot, handles command-line arguments and orchestrates the processing flow
- `config.py`: Configuration management using environment variables
- `models.py`: SQLAlchemy data models for database entities
- `database.py`: Database connection and operations management

### ActivityPub Integration
- `activitypub_client.py`: Client for interacting with Pixelfed/ActivityPub API
- `post_service.py`: Service for handling post-related operations

### Image Processing
- `image_processor.py`: Handles image downloading, storage, and optimization
- `ollama_caption_generator.py`: Generates image captions using Ollama with LLaVA model

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

### Web Interface
- `web_app.py`: Main Flask web application for reviewing and managing captions
- `admin/`: Administrative functionality module
  - `routes/`: Admin route handlers (user management, system health, cleanup, monitoring)
  - `services/`: Admin business logic services
  - `templates/`: Admin-specific HTML templates
  - `static/`: Admin-specific static assets
  - `forms/`: Admin form definitions
- `templates/`: Main application HTML templates
- `static/`: Main application static assets (CSS, JavaScript)

### Utilities
- `utils.py` / `utils_new.py`: Utility functions and helpers
- `add_batch_id_column.py`: Database migration script
- `check_db.py`: Database inspection utility

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
  - `database/`: SQLite database files
  - `images/`: Downloaded and processed images
- `templates/`: Main application HTML templates
- `admin/templates/`: Admin-specific HTML templates
- `tests/`: Test files and test utilities
  - All test files should be placed here with naming convention `test_*.py`
- `__pycache__/`: Python bytecode cache (not tracked in version control)

## Data Flow
1. **User Authentication**: Users log in and receive a session cookie with unique session ID
2. **Session Storage**: Session data is stored in Redis using the session ID as the key
3. **Post Retrieval**: The bot retrieves posts from ActivityPub platforms via API
4. **Image Processing**: Images without alt text are identified and downloaded
5. **Caption Generation**: The Ollama LLaVA model generates captions for these images
6. **Data Persistence**: Generated captions are stored in the database
7. **Session Management**: User sessions are maintained in Redis with database fallback
8. **Human Review**: Reviewers approve, edit, or reject captions via the web interface
9. **Caption Publishing**: Approved captions are posted back to platforms via API
10. **Session Cleanup**: Expired sessions are automatically cleaned up from Redis

## Development Patterns
- **Configuration**: Environment variables with dotenv
- **Database Access**: SQLAlchemy ORM with session management
- **Error Handling**: Comprehensive logging and graceful error recovery
- **API Interaction**: Async HTTP requests with retry mechanisms
- **Web Interface**: Flask with Jinja2 templates