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
1. The bot retrieves posts from Pixelfed via the ActivityPub API
2. Images without alt text are identified and downloaded
3. The Ollama LLaVA model generates captions for these images
4. Generated captions are stored in the database
5. Human reviewers approve, edit, or reject captions via the web interface
6. Approved captions are posted back to Pixelfed via the API

## Development Patterns
- **Configuration**: Environment variables with dotenv
- **Database Access**: SQLAlchemy ORM with session management
- **Error Handling**: Comprehensive logging and graceful error recovery
- **API Interaction**: Async HTTP requests with retry mechanisms
- **Web Interface**: Flask with Jinja2 templates